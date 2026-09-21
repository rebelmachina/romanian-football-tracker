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
    player_assists: int = 0
    goal_minutes: list[str] = field(default_factory=list)
    assist_minutes: list[str] = field(default_factory=list)
    is_national: bool = False


@dataclass
class PlayerData:
    player_id: str
    team_name: str | None
    league: str | None
    country: str | None
    season_stats: SeasonStats
    results: list[MatchResult] = field(default_factory=list)
    age: int | None = None
    market_value: str | None = None
    team_logo: str | None = None
    nt: dict | None = None
    career_teams: list[dict] = field(default_factory=list)


def _safe_int(value) -> int:
    """Flashscore uses '-' or '' for missing numeric stats."""
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return 0


def parse_info(html: str) -> dict:
    """Age and market value from the player page's info items."""
    info: dict = {"age": None, "market_value": None}
    for block in re.findall(r"playerInfoItem.*?</div>\s*</div>", html, re.S):
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", block)).strip()
        mv = re.search(r"Market value\s*:?\s*(€[\d.,]+\s*[A-Za-z]{0,3})", text)
        if mv:
            info["market_value"] = mv.group(1).replace(" ", "")
        ag = re.search(r"Age\s*:?\s*(\d{1,2}).*?\(\d{2}\.\d{2}\.\d{4}\)", text)
        if ag:
            info["age"] = int(ag.group(1))
    return info


def _parse_date(ddmmyy: str) -> str:
    """'19.09.26' -> '2026-09-19'."""
    d, m, y = ddmmyy.split(".")
    return f"20{y}-{m.zfill(2)}-{d.zfill(2)}"


def _league_table(career_tables: list[dict]) -> dict | None:
    for t in career_tables:
        if t.get("table_id") == "league":
            return t
    return career_tables[0] if career_tables else None


def _current_season(seasons: list[dict], club_id: str | None) -> dict | None:
    """The season row for the player's current club, or None if not present.

    careerTables is not reliably current-first (a past top-division stint can
    sit above the current club, and a just-joined club may be missing entirely),
    so when we know the current club id (from the search API) we pick the row
    whose team url carries that id; None means careerTables is stale.
    """
    if not seasons:
        return None
    if not club_id:
        return seasons[0]
    for s in seasons:
        m = re.search(r"/([A-Za-z0-9]{8})/?$", s.get("url", ""))
        if m and m.group(1) == club_id:
            return s
    return None


def _stat_minutes(stats: dict) -> int | None:
    for s in stats.values():
        if s.get("type") == "minutes-played":
            return int(re.sub(r"[^0-9]", "", s.get("value", "")) or 0)
    return None


def _stat_by_type(stats: dict, wanted: str) -> int:
    for s in stats.values():
        if s.get("type") == wanted:
            return int(re.sub(r"[^0-9]", "", s.get("value", "")) or 0)
    return 0


def _career_teams(career_tables: list[dict], club_id: str | None,
                  club_name: str | None) -> list[dict]:
    """Distinct clubs the player has played for, current club first.

    Deduped by crest so a club's senior + youth rows collapse to one badge.
    """
    seen: set[str] = set()
    out: list[dict] = []
    for t in career_tables:
        if t.get("table_id") == "national-team":
            continue
        for s in t.get("seasons", []):
            logo, name = s.get("logo"), s.get("team_name")
            if not logo or not name or logo in seen:
                continue
            seen.add(logo)
            m = re.search(r"/([A-Za-z0-9]{8})/?$", s.get("url", ""))
            tid = m.group(1) if m else None
            current = bool((club_id and tid == club_id) or _club_match(name, club_name))
            out.append({"name": name, "logo": logo, "current": current})
    out.sort(key=lambda x: not x["current"])  # current first, order otherwise stable
    return out[:7]


def _nt_stats(career_tables: list[dict]) -> dict | None:
    """Aggregate senior Romania national-team caps/goals/assists."""
    caps = goals = assists = 0
    for t in career_tables:
        if t.get("table_id") != "national-team":
            continue
        for s in t.get("seasons", []):
            if s.get("team_name") == "Romania":
                caps += _safe_int(s.get("matches_played"))
                goals += _safe_int(s.get("goals"))
                assists += _safe_int(s.get("assists"))
    return {"caps": caps, "goals": goals, "assists": assists} if caps else None


def _parse_matches(last_matches: list[dict]) -> list[MatchResult]:
    out: list[MatchResult] = []
    for m in last_matches:
        stats = m.get("stats") or {}
        names = m.get("homeParticipantName", "") + "|" + m.get("awayParticipantName", "")
        out.append(MatchResult(
            match_id=m.get("eventEncodedId", ""),
            date=_parse_date(m["eventStartTime"]),
            home_team=m.get("homeParticipantName", ""),
            away_team=m.get("awayParticipantName", ""),
            score=f"{m.get('homeScore')}-{m.get('awayScore')}",
            competition=m.get("tournamentTitle", ""),
            result=m.get("winLoseShort", ""),
            player_minutes=_stat_minutes(stats),
            player_goals=_stat_by_type(stats, "goal"),
            player_assists=_stat_by_type(stats, "assist"),
            is_national="Romania" in names,
        ))
    out.sort(key=lambda r: r.date, reverse=True)
    return out


def _club_match(name: str, club: str | None) -> bool:
    if not club:
        return False
    a, b = name.lower(), club.lower()
    return a in b or b in a


def parse_player_env(env: dict, player_id: str, club_id: str | None = None,
                     club_name: str | None = None) -> PlayerData:
    league_tbl = _league_table(env.get("careerTables", []))
    seasons = (league_tbl or {}).get("seasons", [])
    current = _current_season(seasons, club_id)

    results = _parse_matches(
        (env.get("lastMatchesData") or {}).get("lastMatches", []))

    if current is not None:
        league = current.get("tournament_name")
        country = current.get("flag_name")
        team_name = current.get("team_name")
        team_logo = current.get("logo")
        minutes = sum(r.player_minutes for r in results
                      if league and league in r.competition and r.player_minutes)
        stats = SeasonStats(
            goals=_safe_int(current.get("goals")),
            assists=_safe_int(current.get("assists")),
            appearances=_safe_int(current.get("matches_played")),
            minutes=minutes,
            rating=current.get("avg_fs_rating"),
        )
    else:
        # careerTables has no row for the current club (recent transfer) — derive
        # from the current club's recent matches; group falls back to the config.
        league = country = team_logo = None
        team_name = club_name
        club_games = [r for r in results
                      if _club_match(r.home_team, club_name) or _club_match(r.away_team, club_name)]
        stats = SeasonStats(
            goals=sum(r.player_goals for r in club_games),
            assists=sum(r.player_assists for r in club_games),
            appearances=sum(1 for r in club_games if r.player_minutes),
            minutes=sum(r.player_minutes or 0 for r in club_games),
            rating=None,
        )

    career = env.get("careerTables", [])
    return PlayerData(player_id, team_name, league, country, stats, results,
                      team_logo=team_logo, nt=_nt_stats(career),
                      career_teams=_career_teams(career, club_id, club_name))


def fetch_player_data(player_id: str, slug: str,
                      session: requests.Session | None = None,
                      club_id: str | None = None,
                      club_name: str | None = None) -> PlayerData:
    s = session or requests.Session()
    url = f"https://www.flashscore.com/player/{slug}/{player_id}/"
    resp = s.get(url, headers={"Referer": "https://www.flashscore.com/",
                               "User-Agent": UA}, timeout=25)
    resp.raise_for_status()
    match = _ENV_RE.search(resp.text)
    if not match:
        raise ValueError(f"player env blob not found for {player_id}")
    env = json.loads(match.group(1))
    data = parse_player_env(env, player_id, club_id=club_id, club_name=club_name)
    info = parse_info(resp.text)
    data.age = info["age"]
    data.market_value = info["market_value"]
    return data
