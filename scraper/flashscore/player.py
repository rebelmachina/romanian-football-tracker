"""Player data from the Flashscore player page.

The player page embeds a `window.playerProfilePageEnvironment = {...}` JSON
blob containing career tables (season goals/assists/appearances) and the
player's recent matches (with per-match minutes/goals and match ids). We
fetch the page over plain HTTP and parse that blob — no browser needed.
"""
from __future__ import annotations
import json
import re
from dataclasses import dataclass, field
import requests

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

_ENV_RE = re.compile(
    r"window\.playerProfilePageEnvironment\s*=\s*(\{.*?\})\s*;\s*\n", re.DOTALL)


@dataclass
class SeasonStats:
    goals: int
    assists: int
    appearances: int
    minutes: int
    rating: str | None


@dataclass
class MatchResult:
    match_id: str
    date: str            # ISO YYYY-MM-DD
    home_team: str
    away_team: str
    score: str           # "0-3"
    competition: str     # e.g. "Premiership (Scotland)"
    result: str          # W / D / L
    player_minutes: int | None
    player_goals: int


@dataclass
class PlayerData:
    player_id: str
    team_name: str | None
    league: str | None
    country: str | None
    season_stats: SeasonStats
    results: list[MatchResult] = field(default_factory=list)


def _safe_int(value) -> int:
    """Flashscore uses '-' or '' for missing numeric stats."""
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return 0


def _parse_date(ddmmyy: str) -> str:
    """'19.09.26' -> '2026-09-19'."""
    d, m, y = ddmmyy.split(".")
    return f"20{y}-{m.zfill(2)}-{d.zfill(2)}"


def _league_table(career_tables: list[dict]) -> dict | None:
    for t in career_tables:
        if t.get("table_id") == "league":
            return t
    return career_tables[0] if career_tables else None


def _stat_minutes(stats: dict) -> int | None:
    for s in stats.values():
        if s.get("type") == "minutes-played":
            return int(re.sub(r"[^0-9]", "", s.get("value", "")) or 0)
    return None


def _stat_goals(stats: dict) -> int:
    for s in stats.values():
        if s.get("type") == "goal":
            return int(re.sub(r"[^0-9]", "", s.get("value", "")) or 0)
    return 0


def _parse_matches(last_matches: list[dict]) -> list[MatchResult]:
    out: list[MatchResult] = []
    for m in last_matches:
        stats = m.get("stats") or {}
        out.append(MatchResult(
            match_id=m.get("eventEncodedId", ""),
            date=_parse_date(m["eventStartTime"]),
            home_team=m.get("homeParticipantName", ""),
            away_team=m.get("awayParticipantName", ""),
            score=f"{m.get('homeScore')}-{m.get('awayScore')}",
            competition=m.get("tournamentTitle", ""),
            result=m.get("winLoseShort", ""),
            player_minutes=_stat_minutes(stats),
            player_goals=_stat_goals(stats),
        ))
    out.sort(key=lambda r: r.date, reverse=True)
    return out


def parse_player_env(env: dict, player_id: str) -> PlayerData:
    league_tbl = _league_table(env.get("careerTables", []))
    seasons = (league_tbl or {}).get("seasons", [])
    current = seasons[0] if seasons else {}

    league = current.get("tournament_name")
    country = current.get("flag_name")
    team_name = current.get("team_name")

    results = _parse_matches(
        (env.get("lastMatchesData") or {}).get("lastMatches", []))

    # Season minutes: sum per-match minutes over recent matches in this league.
    minutes = 0
    if league:
        for r in results:
            if league in r.competition and r.player_minutes:
                minutes += r.player_minutes

    stats = SeasonStats(
        goals=_safe_int(current.get("goals")),
        assists=_safe_int(current.get("assists")),
        appearances=_safe_int(current.get("matches_played")),
        minutes=minutes,
        rating=current.get("avg_fs_rating"),
    )
    return PlayerData(player_id, team_name, league, country, stats, results)


def fetch_player_data(player_id: str, slug: str,
                      session: requests.Session | None = None) -> PlayerData:
    s = session or requests.Session()
    url = f"https://www.flashscore.com/player/{slug}/{player_id}/"
    resp = s.get(url, headers={"Referer": "https://www.flashscore.com/",
                               "User-Agent": UA}, timeout=25)
    resp.raise_for_status()
    match = _ENV_RE.search(resp.text)
    if not match:
        raise ValueError(f"player env blob not found for {player_id}")
    env = json.loads(match.group(1))
    return parse_player_env(env, player_id)
