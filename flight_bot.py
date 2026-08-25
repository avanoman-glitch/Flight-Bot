"""
Muscat Flight Price Tracker
----------------------------
Tracks cheapest fares from Muscat (MCT) to major expat-corridor cities using
Travelpayouts' Data API (an official, free-to-register endpoint for
Travelpayouts affiliates, not a scrape). Posts a Telegram alert when a
route's cheapest cached fare drops notably below its recent average, and
publishes a public page showing today's best fare per route.

Run manually:      python flight_bot.py
Run on a schedule:  see .github/workflows/flight-bot.yml (runs daily via
                     GitHub Actions, free, no server needed)
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime, timezone

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("flight_bot")

# ---- Config, edit freely --------------------------------------------------
ORIGIN = "MCT"  # Muscat
DESTINATIONS = [
    ("DEL", "Delhi, India"),
    ("MNL", "Manila, Philippines"),
    ("KHI", "Karachi, Pakistan"),
    ("DAC", "Dhaka, Bangladesh"),
    ("CAI", "Cairo, Egypt"),
]
CURRENCY = "usd"
ALERT_DROP_PCT = 0.0           # flag a route if today's cheapest fare beats the trailing average by this much
HISTORY_DAYS_FOR_AVERAGE = 7
CHEAP_PRICES_URL = "http://api.travelpayouts.com/v1/prices/cheap"

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
TRAVELPAYOUTS_TOKEN = os.environ.get("TRAVELPAYOUTS_TOKEN")
# Your Travelpayouts "marker" — the tracking link shown in your dashboard's
# "Get link" tool. Simplest safe form is the Aviasales homepage with your
# marker attached; swap in the exact link your dashboard gives you if it
# differs.
AVIASALES_LINK = os.environ.get("AVIASALES_LINK", "")

HISTORY_STORE = Path("docs/price_history.json")
INDEX_HTML = Path("docs/index.html")
MAX_HISTORY_DAYS = 90


def fetch_cheapest(destination: str):
    """Pull the cheapest cached fares for one route from Travelpayouts'
    Data API. Official, free-to-register endpoint, not a scrape."""
    params = {
        "origin": ORIGIN,
        "destination": destination,
        "currency": CURRENCY,
        "token": TRAVELPAYOUTS_TOKEN,
    }
    resp = requests.get(CHEAP_PRICES_URL, params=params, timeout=15)
    resp.raise_for_status()
    payload = resp.json()
    if not payload.get("success"):
        log.warning("No data for %s: %s", destination, payload)
        return None

    options = payload.get("data", {}).get(destination, {})
    if not options:
        return None

    # options is a dict like {"0": {...}, "1": {...}}; take the cheapest
    cheapest = min(options.values(), key=lambda o: o["price"])
    return cheapest


def load_history():
    if HISTORY_STORE.exists():
        try:
            return json.loads(HISTORY_STORE.read_text())
        except json.JSONDecodeError:
            log.warning("price_history.json unreadable, starting fresh.")
    return []


def save_history(history):
    HISTORY_STORE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_STORE.write_text(json.dumps(history, indent=2))


def trailing_average(history, code, days):
    values = [entry["prices"][code]["price"] for entry in history[-days:] if code in entry.get("prices", {})]
    return sum(values) / len(values) if values else None


def format_alert(name, code, fare, avg, pct_drop):
    link_line = f"\nBook via Aviasales: {AVIASALES_LINK}" if AVIASALES_LINK else ""
    return (
        f"✈️ <b>Good fare spotted: Muscat → {name}</b>\n"
        f"${fare['price']:.0f} on {fare.get('airline', '?')} "
        f"(departing {fare.get('departure_at', '?')[:10]})\n"
        f"That's {pct_drop:.0f}% below the last {HISTORY_DAYS_FOR_AVERAGE}-day average (${avg:.0f})."
        f"{link_line}"
    )


def send_to_telegram(text: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        log.error("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID; skipping send.")
        return
    api_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    resp = requests.post(
        api_url,
        data={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"},
        timeout=15,
    )
    if resp.status_code != 200:
        log.error("Telegram send failed: %s", resp.text)


def render_page(history):
    today = history[-1] if history else None
    rows = ""
    if today:
        for code, name in DESTINATIONS:
            fare = today["prices"].get(code)
            if not fare:
                continue
            avg = trailing_average(history[:-1], code, HISTORY_DAYS_FOR_AVERAGE)
            trend = ""
            if avg:
                pct = (fare["price"] - avg) / avg * 100
                trend = f'<span class="trend {"down" if pct <= 0 else "up"}">{pct:+.0f}% vs 7d avg</span>'
            rows += (
                f'<li><span class="route">Muscat → {name}</span>'
                f'<span class="fare">${fare["price"]:.0f}</span>{trend}</li>'
            )

    updated = today["fetched_at"] if today else ""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Muscat Flight Price Tracker</title>
<meta name="description" content="Daily cheapest fares from Muscat to major expat destinations, updated automatically.">
<style>
  body{{font-family:system-ui,sans-serif;max-width:640px;margin:40px auto;padding:0 16px;background:#0B1E3A;color:#EAF2F7;}}
  h1{{font-size:22px;color:#fff;}}
  p.sub{{color:#93A9C4;font-size:13px;}}
  ul{{list-style:none;padding:0;}}
  li{{display:flex;justify-content:space-between;align-items:center;padding:14px 0;border-bottom:1px solid #1C3358;gap:10px;flex-wrap:wrap;}}
  .route{{font-weight:600;}}
  .fare{{font-family:monospace;font-size:16px;color:#FFB454;}}
  .trend{{font-size:12px;padding:2px 8px;border-radius:10px;}}
  .trend.down{{background:#1E4A3D;color:#6EE7B7;}}
  .trend.up{{background:#4A1E1E;color:#F87171;}}
  a.cta{{display:inline-block;margin-top:20px;color:#FFB454;font-weight:600;text-decoration:none;}}
</style>
</head>
<body>
  <h1>✈️ Muscat Flight Price Tracker</h1>
  <p class="sub">Cheapest cached fares, updated automatically once a day. Data via Travelpayouts. Last update: {updated}</p>
  <ul>
  {rows}
  </ul>
  {"<a class='cta' href='" + AVIASALES_LINK + "'>Search flights on Aviasales →</a>" if AVIASALES_LINK else ""}
</body>
</html>"""
    INDEX_HTML.parent.mkdir(parents=True, exist_ok=True)
    INDEX_HTML.write_text(html)


def run():
    HISTORY_STORE.parent.mkdir(parents=True, exist_ok=True)  # guarantee docs/ exists no matter what happens below

    if not TRAVELPAYOUTS_TOKEN:
        log.error("Missing TRAVELPAYOUTS_TOKEN; cannot query the API.")
        save_history(load_history())
        render_page(load_history())
        return

    history = load_history()
    today_prices = {}

    for code, name in DESTINATIONS:
        fare = fetch_cheapest(code)
        if fare:
            today_prices[code] = fare
            log.info("Cheapest to %s (%s): $%.0f on %s", name, code, fare["price"], fare.get("airline", "?"))
        else:
            log.info("No cached fare found for %s (%s) right now.", name, code)

    today_entry = {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "prices": today_prices,
    }

    if history and history[-1]["date"] == today_entry["date"]:
        history[-1] = today_entry
    else:
        history.append(today_entry)
    history = history[-MAX_HISTORY_DAYS:]

    alerts_sent = 0
    for code, name in DESTINATIONS:
        fare = today_prices.get(code)
        if not fare:
            continue
        avg = trailing_average(history[:-1], code, HISTORY_DAYS_FOR_AVERAGE)
        if avg is None:
            continue  # not enough history yet to judge a "good fare"
        pct_drop = (avg - fare["price"]) / avg * 100
        if pct_drop >= ALERT_DROP_PCT:
            send_to_telegram(format_alert(name, code, fare, avg, pct_drop))
            alerts_sent += 1

    save_history(history)
    render_page(history)
    log.info("Done. %d route(s) checked, %d alert(s) sent.", len(DESTINATIONS), alerts_sent)


if __name__ == "__main__":
    run()
