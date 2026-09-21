"""Scrape Flashscore for the tracked roster and write site/data.json.

Per player: resolve slug/position/club via the search API, fetch season
stats + recent matches from the player page, then fetch YouTube highlights
for recent matches (skipping ones already resolved or manually overridden).
All over plain HTTP — no browser.

Modes:
    (default)            full refresh of stats + results + highlights
    --highlights-only    re-check only null-youtube recent matches in data.json
"""
from __future__ import annotations
import argparse
import json
import sys
import time
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import requests

from config import load_players, load_history_years, PlayerConfig
from flashscore.search import search_players, PlayerHit
from flashscore.player import fetch_player_data, fetch_match_history, PlayerData
from flashscore.highlights import fetch_highlight
from flashscore.incidents import fetch_incidents, player_minutes

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "site" / "data.json"
LINKS_PATH = ROOT / "links.json"
CACHE_PATH = Path(__file__).resolve().parent / "cache.json"
INC_CACHE_PATH = Path(__file__).resolve().parent / "incidents_cache.json"

HIGHLIGHT_RECHECK_DAYS = 45    # re-check "no highlight yet" only for matches this recent
HIGHLIGHT_MAX_AGE_DAYS = 500   # don't look for highlights on older matches (they won't exist)
REQUEST_DELAY = 0.3


def group_label(league: str | None, country: str | None, fallback: str) -> str:
    if league and country:
        return f"{league} ({country})"
    if league:
        return league
    return fallback


def needs_highlight_check(match_date: str, today: date, window_days: int) -> bool:
    try:
        d = datetime.strptime(match_date, "%Y-%m-%d").date()
    except ValueError:
        return False
    return (today - d).days <= window_days


def merge_youtube(results: list[dict], overrides: dict[str, str],
                  scraped: dict[str, str]) -> None:
    for r in results:
        mid = r["match_id"]
        if mid in overrides:
            r["youtube_url"] = overrides[mid]
        elif mid in scraped:
            r["youtube_url"] = scraped[mid]


def build_player_record(cfg: PlayerConfig, hit: PlayerHit,
                        pdata: PlayerData) -> dict:
    team = pdata.team_name or hit.club_name
    league = pdata.league
    country = pdata.country
    return {
        "name": cfg.name,
        "flashscore_id": cfg.flashscore_id,
        "slug": hit.slug,
        "position": hit.position,
        "photo": hit.photo,
        "age": pdata.age,
        "market_value": pdata.market_value,
        "team": team,
        "team_logo": pdata.team_logo,
        "career_teams": pdata.career_teams,
        "league": league,
        "country": country,
        "group": group_label(league, country, fallback=cfg.country or "Other"),
        "nt": pdata.nt,
        "season_stats": asdict(pdata.season_stats),
        "results": [
            {**asdict(r),
             "flashscore_url": f"https://www.flashscore.com/match/{r.match_id}/",
             "youtube_url": None}
            for r in pdata.results
        ],
    }


def _load_json(path: Path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def _resolve_highlights(matches: list[tuple[str, str]], cache: dict[str, str],
                        session: requests.Session, today: date) -> dict[str, str]:
    """youtube urls for (match_id, date) pairs. Caches misses as "" so old matches
    with no highlight are only checked once; recent misses are re-checked."""
    found: dict[str, str] = {}
    for mid, mdate in matches:
        cached = cache.get(mid)
        if cached:                       # already have a url
            found[mid] = cached
            continue
        if not needs_highlight_check(mdate, today, HIGHLIGHT_MAX_AGE_DAYS):
            continue                     # too old to have a highlight
        if cached == "" and not needs_highlight_check(mdate, today, HIGHLIGHT_RECHECK_DAYS):
            continue                     # checked before, none found, and old
        url = fetch_highlight(mid, session=session)
        cache[mid] = url or ""
        if url:
            found[mid] = url
        time.sleep(REQUEST_DELAY)
    return found


def _fill_minutes(results: list[dict], player_name: str, player_id: str,
                  slug: str, inc_cache: dict, session: requests.Session) -> None:
    """Attach per-goal/assist minutes for matches where the player scored/assisted."""
    for r in results:
        if not (r["player_goals"] or r["player_assists"]):
            continue
        key = f"{r['match_id']}:{player_id}"
        if key in inc_cache:
            entry = inc_cache[key]
        else:
            events = fetch_incidents(r["match_id"], session)
            gm, am = player_minutes(events, player_name, slug=slug)
            entry = inc_cache[key] = {"g": gm, "a": am}
            time.sleep(REQUEST_DELAY)
        r["goal_minutes"] = entry["g"]
        r["assist_minutes"] = entry["a"]


def _merge_results(recent: list, history: list, since: str) -> list:
    """Union of blob-recent + plm-history matches, deduped, within window, newest first."""
    seen: set[str] = set()
    out = []
    for r in list(recent) + list(history):
        if since and r.date < since:
            continue
        if not r.match_id or r.match_id in seen:
            continue
        seen.add(r.match_id)
        out.append(r)
    out.sort(key=lambda r: r.date, reverse=True)
    return out


def run_full(session: requests.Session, players: list[PlayerConfig],
             overrides: dict, cache: dict, inc_cache: dict, today: date,
             since: str) -> dict:
    records = []
    for cfg in players:
        try:
            hits = search_players(cfg.name, session=session)
            hit = next((h for h in hits if h.id == cfg.flashscore_id), None)
            if hit is None:
                print(f"  ! no search match for {cfg.name} ({cfg.flashscore_id})")
                continue
            pdata = fetch_player_data(cfg.flashscore_id, hit.slug, session=session,
                                      club_id=hit.club_id, club_name=hit.club_name)
            history = fetch_match_history(cfg.flashscore_id, session, since=since,
                                          delay=REQUEST_DELAY)
            pdata.results = _merge_results(pdata.results, history, since)
        except Exception as exc:  # keep going; one bad player shouldn't kill the run
            print(f"  ! error for {cfg.name}: {exc}")
            continue
        rec = build_player_record(cfg, hit, pdata)
        matches = [(r["match_id"], r["date"]) for r in rec["results"]]
        scraped = _resolve_highlights(matches, cache, session, today)
        merge_youtube(rec["results"], overrides, scraped)
        _fill_minutes(rec["results"], hit.name, cfg.flashscore_id, hit.slug, inc_cache, session)
        records.append(rec)
        print(f"  ok {cfg.name}: {rec['team']} · {rec['league']} · "
              f"{len(rec['results'])} matches · {rec['season_stats']['goals']}G/"
              f"{rec['season_stats']['assists']}A")
        time.sleep(REQUEST_DELAY)
    return {"players": records}


def run_highlights_only(session: requests.Session, data: dict,
                        overrides: dict, cache: dict, today: date) -> dict:
    missing = [(r["match_id"], r["date"]) for pl in data.get("players", [])
               for r in pl["results"] if not r.get("youtube_url")]
    scraped = _resolve_highlights(missing, cache, session, today)
    for pl in data.get("players", []):
        merge_youtube(pl["results"], overrides, scraped)
    return data


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--highlights-only", action="store_true")
    parser.add_argument("--years", type=float,
                        help="how many years of history to scrape (overrides players.yaml)")
    parser.add_argument("--since", help="scrape matches on/after this date (YYYY-MM-DD)")
    args = parser.parse_args(argv)

    session = requests.Session()
    overrides = _load_json(LINKS_PATH, {})
    cache = _load_json(CACHE_PATH, {})
    inc_cache = _load_json(INC_CACHE_PATH, {})
    today = date.today()

    if args.highlights_only:
        data = _load_json(DATA_PATH, {"players": []})
        data = run_highlights_only(session, data, overrides, cache, today)
    else:
        players = load_players(ROOT / "players.yaml")
        years = args.years if args.years is not None else load_history_years(ROOT / "players.yaml")
        since = args.since or (today - timedelta(days=round(365.25 * years))).strftime("%Y-%m-%d")
        print(f"Scraping {len(players)} players since {since} (~{years:g} yr)…")
        data = run_full(session, players, overrides, cache, inc_cache, today, since)

    data["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    INC_CACHE_PATH.write_text(json.dumps(inc_cache, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {DATA_PATH} ({len(data.get('players', []))} players)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
