[README.md](https://github.com/user-attachments/files/31407015/README.md)
# Muscat Flight Price Tracker

Tracks cheapest cached fares from Muscat to five expat-corridor cities
(Delhi, Manila, Karachi, Dhaka, Cairo), alerts your Telegram channel when a
fare drops well below its recent average, and publishes a public page of
today's best fares. Same skeleton as the deal bot and rate tracker: poll →
compare to history → alert → publish.

## Before you start — one honest flag

Flight-price data is the trickiest source of anything we've built so far.
Amadeus's free developer API (the obvious first choice) was shut down in
July 2026, so this uses **Travelpayouts' Data API** instead — it's real,
free to access, and doubles as your monetization (Travelpayouts owns
Aviasales, a real flight booking site with a referral program). But it
serves *cached* prices — fares real users have recently searched for, not
a live-priced search — so some routes may come back empty on any given day,
especially less-searched ones like Muscat routes. That's expected, not
broken; treat empty results the same way we treated "0 new deals" on the
first bot — normal, not an error.

## Setup

### 1. Register with Travelpayouts (10 min)
1. Sign up free at travelpayouts.com
2. Log in → **Profile → API token** tab → copy your token
3. Also grab your **marker** (visible in the same dashboard) and your
   Aviasales referral link from their "Get link" tool — the simplest safe
   version is `https://www.aviasales.com/?marker=YOUR_MARKER`, but use
   whatever exact link their dashboard gives you.

### 2. Reuse your existing Telegram bot
Same bot and channel from the deal bot works fine here — no need to create
a new one, just point this bot at the same `TELEGRAM_BOT_TOKEN` and
`TELEGRAM_CHAT_ID`. If you'd rather keep flight alerts separate from pet
deals, create a second channel and add the bot as admin there instead.

### 3. Upload to GitHub (15 min)
Same pattern as before:
- New repo (or a new folder in your existing one)
- **Add file → Upload files**: `flight_bot.py`, `requirements.txt`, `README.md`
- **Add file → Create new file**: type `.github/workflows/flight-bot.yml` exactly (the folders get created from the slashes), paste in the workflow contents, commit

### 4. Add the secrets
Repo **Settings → Secrets and variables → Actions → New repository secret**:
- `TELEGRAM_BOT_TOKEN` — same as your deal bot, or a new one
- `TELEGRAM_CHAT_ID` — same channel, or a new one
- `TRAVELPAYOUTS_TOKEN` — from step 1
- `AVIASALES_LINK` — your referral link from step 1

### 5. Turn on GitHub Pages for this page too
If this is a separate repo from the deal bot: **Settings → Pages → Deploy
from branch → main → /docs**. If it's a folder inside your existing repo,
you'll need to adjust the Pages path or keep them in separate repos —
separate repos is simpler if you're not comfortable with subfolder Pages
config.

### 6. Run it
**Actions → Muscat Flight Price Tracker → Run workflow**. Check the log:
look for `Cheapest to ... : $X` lines. Some routes may log "No cached fare
found" — normal, not a failure. Check Telegram for an alert only if a fare
was both found and notably below its (still-building) average — with zero
history on day one, no alerts will fire yet; that starts once a handful of
days of data exist to compare against.

## Honest limitations
- Cached data, not live search — treat prices as directional, not
  guaranteed bookable at that exact number.
- Muscat is a lower-search-volume origin than major hubs, so expect gappier
  data than the deal bot's Amazon feed.
- The alert threshold (10% below the 7-day average) needs at least a week
  of accumulated history before it can flag anything — the first alerts
  won't appear until day 8 or so.
