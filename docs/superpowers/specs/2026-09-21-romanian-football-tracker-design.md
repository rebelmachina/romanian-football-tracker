# Romanian Football Tracker — Design Spec

**Date:** 2026-09-21  
**Author:** whois.cris@gmail.com

---

## Overview

A personal web application that tracks ~80 Romanian football players competing in leagues worldwide. For each player it shows current season stats (goals, assists, minutes played, position), recent match results, and YouTube highlight links where available. Data is sourced from Flashscore. The site is hosted on GitHub Pages and updated automatically via a daily GitHub Actions scrape job.

---

## Implementation Update (2026-09-21)

Empirical discovery during implementation simplified the design from the
original plan:

- **No browser / Playwright.** The entire pipeline is plain HTTP. Player
  season stats + recent matches are read from the JSON blob embedded in the
  player page HTML; YouTube highlights come from Flashscore's `df_hi` feed
  (not a rendered page). See `docs/flashscore-api-notes.md`.
- **Grouping is by live league** (e.g. "Süper Lig (Turkey)"), read from
  Flashscore per player, not by a static country field. The `country` field
  in `players.yaml` is only a fallback section label.
- **Highlights refresh** is a fast HTTP re-fetch (`--highlights-only`), so the
  "Refresh Highlights" workflow no longer needs a browser.

The rest of this document reflects the original design; where it mentions
Playwright or pipe-delimited player feeds, the HTTP approach above supersedes it.

## Goals

- Track a configurable roster of Romanian players abroad
- Display current season G/A stats, playing time, and position per player
- Show recent match results per player, with YouTube highlight links when available
- Auto-detect team transfers (player follows their Flashscore ID, not a hardcoded club)
- Support backfilling historical data (YTD or multi-year)
- Zero ongoing cost (GitHub free tier)
- No manual intervention required for daily updates

---

## Non-Goals

- No user authentication or multi-user support
- No Transfermarkt integration (future consideration)
- No market value tracking
- No live scores (daily updates are sufficient)

---

## Repository Structure

```
romanian-football-tracker/
├── players.yaml                  # player roster config
├── links.json                    # manual YouTube link overrides
├── scraper/
│   ├── scrape.py                 # main scraper entrypoint
│   ├── flashscore.py             # Flashscore API client
│   ├── highlights.py             # Playwright-based YouTube extractor
│   ├── cache.json                # processed match IDs cache
│   └── requirements.txt
├── site/                         # GitHub Pages serves from this directory
│   ├── index.html
│   ├── app.js
│   └── data.json                 # generated output, committed by CI
└── .github/
    └── workflows/
        ├── scrape.yml            # daily full scrape + manual trigger
        └── highlights.yml        # highlights-only, triggered by UI button
```

---

## Configuration

### `players.yaml`

One entry per tracked player. The `flashscore_id` is the stable Flashscore player identifier — it survives transfers, so the config never needs updating when a player changes clubs.

```yaml
players:
  # Turkey
  - name: Andrei Borza
    flashscore_id: <id>
    country: Turkey

  - name: Matei Ilie
    flashscore_id: <id>
    country: Turkey

  - name: Deian Sorescu
    flashscore_id: <id>
    country: Turkey

  - name: Alexandru Maxim
    flashscore_id: <id>
    country: Turkey

  - name: Valentin Mihăilă
    flashscore_id: <id>
    country: Turkey

  - name: Iustin Doicaru
    flashscore_id: <id>
    country: Turkey

  - name: Horațiu Moldovan
    flashscore_id: <id>
    country: Turkey

  - name: Ianis Hagi
    flashscore_id: <id>
    country: Turkey

  # ... (all ~80 players follow the same pattern)
```

The `country` field controls which section the player appears under in the UI. It reflects the country of competition, not the player's nationality (all players are Romanian).

### `links.json`

Manual YouTube link overrides, keyed by Flashscore match ID. These persist across scrapes and take precedence over anything the Playwright extractor finds.

```json
{
  "jiBADrkI": "https://www.youtube.com/watch?v=example"
}
```

---

## Data Pipeline

### Flashscore API Client (`flashscore.py`)

Uses Flashscore's internal (undocumented) API — the same endpoints the web app uses. No browser needed for the parts that work over plain HTTP. See `docs/flashscore-api-notes.md` for the verified endpoint details captured on 2026-09-21.

Two verified data sources:

1. **Search API (JSON)** — resolves a player name → stable player ID, position, nationality, and **current club** (transfer-aware):
   ```
   GET https://s.livesport.services/api/v2/search/?q={name}&lang-id=1&project-id=2&project-type-id=1&sport-ids=1&type-ids=1,2,3,4
   ```
   Filter results to `type.name == "PlayerInTeam"`. Position comes from the non-"Player" entry in `participantTypes`; current club is the `teams` entry with `kind == "TEAM"`.

2. **Match/team feeds (pipe-delimited)** — host `https://global.flashscore.ninja/2/x/feed/{feed}` with required header `x-fsign: SW9D1eZo` and `Referer: https://www.flashscore.com/`. Format: records separated by `~`, fields by `¬`, key/value by `÷`. (The older `d.flashscore.com` host now returns empty — do not use it.)

The exact feed names for **player season stats**, **player match log**, and **team results** were not found by guessing and must be discovered empirically via a Playwright network-capture spike (see implementation plan Task 1). Once discovered, they are fetched with plain HTTP `requests` (fast); Playwright is only needed for the one-time discovery and for YouTube extraction.

The client handles:
- Request headers (standard browser UA + `x-fsign` + Referer)
- Rate limiting (small delay between requests)
- Parsing the pipe-delimited response format

### Highlights Extractor (`highlights.py`)

Uses Playwright (headless Chromium) to visit individual Flashscore match pages and extract any embedded YouTube URL. Only runs on matches where `youtube_url` is currently null — skips already-processed matches using `cache.json`.

Playwright is used here because YouTube embeds are injected by Flashscore's JavaScript after page load and are not present in the raw HTTP response.

### Main Scraper (`scrape.py`)

```
1. Load players.yaml + links.json
2. For each player:
   a. GET player profile → current club, league, position
   b. GET match history → results since backfill_from date (or last known date on incremental runs)
   c. For each new match not in cache.json → add to queue for highlight extraction
3. Run highlights extractor on queued matches
4. Merge: scraped YouTube links + links.json overrides (manual wins)
5. Write site/data.json
6. Update cache.json
```

**Backfill mode:** triggered by `--backfill-from YYYY-MM-DD` flag. Fetches all matches from that date to today for every player. Intended as a one-time operation after initial setup.

**Incremental mode (default):** fetches only matches newer than the most recent result already stored in `data.json`.

**Highlights-only mode:** triggered by `--highlights-only` flag. Skips Flashscore API calls entirely. Only runs Playwright on matches where `youtube_url` is null. Used by the `highlights.yml` workflow.

---

## Data Model

### `data.json`

```json
{
  "updated_at": "2026-09-21T06:12:00Z",
  "players": [
    {
      "name": "Kevin Ciubotaru",
      "flashscore_id": "jiBADrkI",
      "country": "Scotland",
      "team": "Dundee United",
      "league": "Scottish Premiership",
      "position": "MF",
      "season_stats": {
        "goals": 2,
        "assists": 1,
        "minutes": 430
      },
      "results": [
        {
          "match_id": "abc123",
          "date": "2026-09-14",
          "home_team": "Dundee Utd",
          "away_team": "St Mirren",
          "score": "2-1",
          "flashscore_url": "https://www.flashscore.com/match/...",
          "youtube_url": "https://www.youtube.com/watch?v=..."
        }
      ]
    }
  ]
}
```

Results are stored in reverse-chronological order (newest first). All historical results from the backfill date are stored; the UI shows the 5 most recent by default.

---

## Frontend

### Tech Stack

Plain HTML + vanilla JS. No build step, no framework. `index.html` + `app.js` fetch `data.json` on load and render the page client-side.

### Layout

- **Header:** app title, last-updated timestamp, "↻ Refresh Highlights" button
- **Country sections:** one collapsible section per country, labeled with player count (e.g. "Turcia — 8 jucători"). Sections are open by default. Collapse/expand state persisted in `localStorage`.
- **Player cards:** displayed in a responsive grid within each country section. Each card shows:
  - Player name (bold)
  - Club name · Position badge
  - Season stats row: `3G / 2A / 810'`
  - Divider
  - Last 5 results, each showing: date, home team, score, away team, and a ▶ icon (link to YouTube) if a highlight is available
  - "Show all results" toggle link (hidden if ≤5 results)

### Refresh Highlights Button

Calls the GitHub Actions API endpoint for `workflow_dispatch` on `highlights.yml`. Requires a fine-grained GitHub Personal Access Token with `actions: write` scope on this repository only. The token is written into `data.json` at build time by the scraper (sourced from the `GH_ACTIONS_TOKEN` secret). On click, the button shows a spinner and a "Refresh triggered — check back in ~5 minutes" message.

If the user prefers not to expose any token, the button falls back to a direct link to the GitHub Actions workflow page.

### Responsiveness

Cards use CSS Grid with `auto-fill` columns (min 280px). On mobile (single column), result rows are compact. No external CSS framework — custom styles only.

---

## GitHub Actions

### `scrape.yml`

```yaml
on:
  schedule:
    - cron: '0 6 * * *'   # 06:00 UTC daily
  workflow_dispatch:
    inputs:
      backfill_from:
        description: 'Backfill from date (YYYY-MM-DD), leave empty for incremental'
        required: false
```

Steps:
1. Checkout repo
2. Set up Python + install requirements (including Playwright + Chromium)
3. Run `scrape.py` (with `--backfill-from` if input provided)
4. Commit and push `data.json` + `cache.json` if changed
5. GitHub Pages auto-deploys from the updated `data.json`

### `highlights.yml`

```yaml
on:
  workflow_dispatch: {}
```

Steps:
1. Checkout repo
2. Set up Python + install requirements (Playwright only)
3. Run `scrape.py --highlights-only`
4. Commit and push `data.json` + `cache.json` if changed

Both workflows use `actions/checkout` with write permissions and commit via `git commit` + `git push`. The `GH_ACTIONS_TOKEN` secret is used for the UI trigger button.

### GitHub Pages

Configured to serve from the `site/` directory on the `main` branch. The scraper writes `site/data.json`, which is fetched by the frontend at the relative path `./data.json`.

---

## Operational Notes

### Initial Setup Checklist

1. Create GitHub repo (can be private)
2. Add all player Flashscore IDs to `players.yaml`
3. Configure GitHub Pages (Settings → Pages → Source: `main`, folder: `site/`)
4. Add `GH_ACTIONS_TOKEN` secret (fine-grained PAT, `actions: write` on this repo)
5. Run `scrape.yml` manually with `backfill_from: 2025-01-01` (or chosen date) to populate history
6. Verify `data.json` is committed and site loads

### Adding a Player

Add one entry to `players.yaml`, commit, push. The next daily scrape picks them up. Run a manual backfill if you want their history populated immediately.

### Handling a Transfer

No action needed. The scraper re-fetches the player's current club from their Flashscore profile on every run. The `country` field in `players.yaml` may need updating if the player moves to a different country.

### Adding a YouTube Link Manually

Add the Flashscore match ID + YouTube URL to `links.json`, commit, push. It appears on the site immediately (no scrape needed — the frontend reads `links.json` indirectly via `data.json`, which is rebuilt on next scrape; for immediate effect, trigger `highlights.yml`).

---

## Open Questions / Future Considerations

- **Transfermarkt integration:** market value display, earlier transfer alerts
- **Push notifications:** notify when a tracked player scores
- **Comparison view:** side-by-side stats for two players
- **International matches:** national team results for tracked players
