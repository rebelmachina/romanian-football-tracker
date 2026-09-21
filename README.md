# Jucători Români în Lume — Romanian Football Tracker

Tracks ~80 Romanian footballers playing abroad: current-season goals/assists,
appearances, minutes and position, each player's recent team results, and a
YouTube highlight link per match when Flashscore has one. Static site on GitHub
Pages, updated daily by a GitHub Actions scraper reading Flashscore.

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

### Refresh Highlights button

The button re-runs the highlights-only workflow. Two ways to wire it:

- **Link-out (default):** set `window.__OWNER_REPO__ = "owner/repo"` (e.g. in a
  small `site/config.js` you add to `index.html`). The button opens the Actions
  page where you click *Run workflow*.
- **One-click:** additionally set `window.__GH_TOKEN__` to a fine-grained PAT with
  only `actions: write` on this repo. Keep that in a git-ignored `site/token.js`
  loaded from `index.html`. Only do this for a private repo.

## Notes / limitations

- Coverage depends on Flashscore. A few exotic leagues (e.g. the Omani league)
  aren't well covered; such players stay unresolved in `players.yaml`.
- "Minutes" is summed from the recent league matches on the player page, so it
  reflects recent games rather than a guaranteed full-season total. Per-match
  minutes are exact.
- Deep historical backfill (multi-year) is a future addition; the tracker shows
  the recent matches Flashscore returns per player.
