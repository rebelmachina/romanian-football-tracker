# Jucători Români în Lume — Romanian Football Tracker

Tracks ~80 Romanian footballers playing abroad. Per player: photo, club crest,
position, age, market value, current-season goals/assists/appearances/minutes,
Romania national-team caps/goals/assists, and recent results — each with the
player's goal/assist minutes, W/D/L, an embedded YouTube highlight, and a
Flashscore link. Sections are ordered by league strength. Static site on GitHub
Pages, updated daily by a GitHub Actions scraper reading Flashscore.

Two views: **Classic** (cards grouped by league) and **Arcade** (a
fighter-select grid of faces navigated with the arrow keys, with the selected
player's card and an inline video beside it).

## How it works

```
players.yaml ──▶ scraper/scrape.py ──▶ site/data.json ──▶ GitHub Pages (site/)
links.json  ──┘   (search + player page + highlights feed, all plain HTTP)
```

- **Player stats + recent matches** come from the player page's embedded JSON.
- **Position, nationality and current club** come from the Flashscore search API
  (so transfers are picked up automatically — the config keys on a stable player id).
- **YouTube highlights** come from Flashscore's `df_hi` match feed.
- **`links.json`** lets you override/add a YouTube link by match id; it wins over
  whatever the scraper finds.

No browser/Playwright is needed — everything is plain HTTP. See
`docs/flashscore-api-notes.md` for the reverse-engineered endpoints.

## Local development

```bash
cd scraper
pip install -r requirements.txt
python -m pytest -m "not network"      # unit tests
python scrape.py                       # writes ../site/data.json

cd ../site && python -m http.server 8080   # open http://localhost:8080
```

## How far back to scrape

`players.yaml` has a top-level **`history_years`** setting — how many years of
match history to pull (results, YouTube highlights, and goal/assist minutes):

```yaml
history_years: 3      # last 3 years
```

Change it and re-run the scrape to backfill. You can also override per-run:

```bash
python scrape.py --years 3          # or: --since 2023-01-01
```

Or from GitHub: **Actions → Daily scrape → Run workflow → years: 3**.

Notes:
- Match history comes from Flashscore's paginated `plm` feed, merged with the
  latest matches. The first deep backfill is slow (it checks highlights and
  goal/assist minutes for every match) but results are cached, so later runs are
  fast. Highlights are only looked up for matches under ~500 days old — older
  ones don't have highlight embeds on Flashscore anyway (add them via `links.json`).
- A larger window makes `site/data.json` bigger; the UI still shows the 5 most
  recent per player with a "show all" toggle.

## Managing the roster

`players.yaml` holds `{name, flashscore_id, country}` per player. `country` is a
free-form section hint used only as a fallback — the UI groups by the **live
league** read from Flashscore.

To find a player's `flashscore_id`, search the API:

```bash
curl -s "https://s.livesport.services/api/v2/search/?q=NAME&lang-id=1&project-id=2&project-type-id=1&sport-ids=1&type-ids=1,2,3,4" \
  -H "Referer: https://www.flashscore.com/" | python3 -m json.tool
```

Use the `id` of the `PlayerInTeam` entry whose `teams` list shows the right club.
A player with an empty `flashscore_id` is skipped.

## Adding a YouTube link manually

Add the Flashscore match id (the 8-char code, e.g. `jiBADrkI`) and the URL to
`links.json`, then commit:

```json
{ "jiBADrkI": "https://www.youtube.com/watch?v=ECitipBT3P8" }
```

## Deployment (GitHub Pages + Actions)

1. Push this repo to GitHub (public, so free Pages works).
2. **Settings → Pages → Source: GitHub Actions.**
3. The **Deploy Pages** workflow publishes `site/` — on any push that changes
   `site/**`, and automatically after the scrape/highlights workflows finish.
   (Pages can only serve a branch's `/` or `/docs` folder directly, so this
   repo deploys via Actions instead, which can publish any folder.)
4. The **Daily scrape** workflow runs at 06:00 UTC (and on manual dispatch),
   commits `site/data.json`, and triggers a redeploy.
5. Trigger a first run: **Actions → Daily scrape → Run workflow**.

### Refresh Highlights button (one-click)

The repo is preset in `site/app.js` (`OWNER_REPO`). Click **↻ Highlights**:

- The first time, you're prompted for a **GitHub fine-grained PAT** with
  **Actions: Write** on this repo. It's saved in your browser's `localStorage`
  only — never committed or deployed — so it's safe even on a public repo, and
  it works only for whoever owns the token (a random visitor's token has no
  access to your repo).
- After that, one click dispatches the `Refresh highlights` workflow. An invalid
  token is cleared automatically so you can re-enter it. Cancel the prompt to
  just open the Actions page instead.

To pre-fill it for a private deployment, set `window.__GH_TOKEN__` from a
git-ignored `site/token.js` loaded in `index.html`.

### Views

- **▦ Clasic** (default) — player cards grouped by league, each with a profile photo.
- **🎮 Arcade** — a fighter-select-style grid of player faces; navigate with the
  arrow keys (← ↑ ↓ →) or click, and the selected player's card shows on the right.
  Sort the grid by goals / assists / minutes / age / market value.
- **🇷🇴 Naționala** — latest results for the senior national team and U21, plus
  the U21 qualifying group standings (see `standings` in `players.yaml`).

The choice is remembered per browser.

### Filtering

The header has a text search (name / team / league) plus two dropdowns —
**position** (Goalkeeper / Defender / Midfielder / Forward) and **league** —
which combine. Filtering works in both views.

### Theme

Top-right selector: 💻 system (follows your OS), ☀️ light, 🌙 dark. The choice
is remembered per browser. Colors come from the Romanian flag (blue #002B7F,
yellow #FCD116, red #CE1126). Player photos come from Flashscore.

## Notes / limitations

- Coverage depends on Flashscore. A few exotic leagues (e.g. the Omani league)
  aren't well covered; such players stay unresolved in `players.yaml`.
- "Minutes" is summed from the recent league matches on the player page, so it
  reflects recent games rather than a guaranteed full-season total. Per-match
  minutes are exact.
- Deep historical backfill (multi-year) is a future addition; the tracker shows
  the recent matches Flashscore returns per player.
