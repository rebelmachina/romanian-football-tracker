import json
from pathlib import Path
import pytest
from flashscore.player import (
    parse_player_env, fetch_player_data, parse_info, _parse_date, _safe_int,
    SeasonStats, MatchResult, PlayerData,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _env():
    return json.loads((FIXTURES / "player_env_O2o2L2iA.json").read_text(encoding="utf-8"))


def test_parse_date_ddmmyy_to_iso():
    assert _parse_date("19.09.26") == "2026-09-19"
    assert _parse_date("01.01.25") == "2025-01-01"


def test_safe_int_handles_missing_dash():
    assert _safe_int("-") == 0
    assert _safe_int("") == 0
    assert _safe_int(None) == 0
    assert _safe_int("7") == 7
    assert _safe_int(3) == 3


def test_parse_player_env_tolerates_dash_stats():
    env = {"careerTables": [{"table_id": "league", "seasons": [
        {"team_name": "X", "tournament_name": "L", "flag_name": "C",
         "goals": "-", "assists": "-", "matches_played": "-",
         "avg_fs_rating": "-"}]}],
        "lastMatchesData": {"lastMatches": []}}
    data = parse_player_env(env, "pid")
    assert data.season_stats == SeasonStats(0, 0, 0, 0, "-")


def test_parse_player_env_current_season_and_team():
    data = parse_player_env(_env(), player_id="O2o2L2iA")
    assert isinstance(data, PlayerData)
    assert data.team_name == "Dundee Utd"
    assert data.league == "Premiership"
    assert data.country == "Scotland"
    assert data.season_stats.goals == 1
    assert data.season_stats.assists == 0
    assert data.season_stats.appearances == 3
    assert data.season_stats.rating == "6.8"


def test_parse_player_env_results():
    data = parse_player_env(_env(), player_id="O2o2L2iA")
    assert data.results, "expected recent matches"
    top = next(r for r in data.results if r.match_id == "jiBADrkI")
    assert top.date == "2026-09-19"
    assert top.home_team == "St. Mirren"
    assert top.away_team == "Dundee Utd"
    assert top.score == "0-3"
    assert top.competition == "Premiership (Scotland)"
    assert top.result == "W"
    assert top.player_minutes == 90
    assert top.player_goals == 1
    assert top.player_assists == 0
    # results newest-first
    dates = [r.date for r in data.results]
    assert dates == sorted(dates, reverse=True)


def test_parse_player_env_prefers_current_club_row():
    # seasons[0] is a stale higher-division row; the current club (by id) is row 2
    env = {"careerTables": [{"table_id": "league", "seasons": [
        {"season_name": "2025/2026", "tournament_name": "Serie A", "flag_name": "Italy",
         "team_name": "Verona", "url": "/team/verona/AAAAAAAA/", "matches_played": 6,
         "goals": 0, "assists": 0},
        {"season_name": "2026/2027", "tournament_name": "Ekstraklasa", "flag_name": "Poland",
         "team_name": "Widzew Lodz", "url": "/team/widzew-lodz/BBBBBBBB/", "matches_played": 5,
         "goals": 2, "assists": 1}]}],
        "lastMatchesData": {"lastMatches": []}}
    data = parse_player_env(env, "pid", club_id="BBBBBBBB")
    assert data.team_name == "Widzew Lodz"
    assert data.league == "Ekstraklasa"
    assert data.country == "Poland"


def test_parse_player_env_stale_transfer_uses_recent_games():
    # careerTables only has the OLD club; current club (by id) has no row, so
    # we derive from recent games at the current club and leave league unset.
    env = {"careerTables": [{"table_id": "league", "seasons": [
        {"season_name": "2025/2026", "tournament_name": "Serie A", "flag_name": "Italy",
         "team_name": "Verona", "url": "/team/verona/AAAAAAAA/", "matches_played": 6,
         "goals": 0, "assists": 0}]}],
        "lastMatchesData": {"lastMatches": [
            {"eventEncodedId": "m1", "eventStartTime": "18.09.26",
             "homeParticipantName": "Widzew Lodz", "awayParticipantName": "Legia",
             "homeScore": 2, "awayScore": 2, "tournamentTitle": "Ekstraklasa (Poland)",
             "winLoseShort": "D", "stats": {"595": {"type": "minutes-played", "value": "90'"},
                                            "596": {"type": "goal", "value": "1"}}}]}}
    data = parse_player_env(env, "pid", club_id="ZZZZZZZZ", club_name="Widzew Lodz")
    assert data.team_name == "Widzew Lodz"
    assert data.league is None          # falls back to config group
    assert data.season_stats.goals == 1
    assert data.season_stats.appearances == 1


def test_parse_info_age_and_market_value():
    html = (
        '<div class="playerInfoItem"><span>Age</span><span>:</span>'
        '<span>22</span><span>(02.02.2004)</span></div></div>'
        '<div class="playerInfoItem"><span>Market value</span><span>:</span>'
        '<span>€570k</span></div></div>'
    )
    assert parse_info(html) == {"age": 22, "market_value": "€570k"}


def test_parse_info_missing_returns_none():
    assert parse_info("<div>nothing</div>") == {"age": None, "market_value": None}


def test_parse_matches_reads_per_game_goals_and_assists():
    env = {"careerTables": [{"table_id": "league", "seasons": [
        {"team_name": "Z", "tournament_name": "L", "flag_name": "C"}]}],
        "lastMatchesData": {"lastMatches": [{
            "eventEncodedId": "x1", "eventStartTime": "18.09.26",
            "homeParticipantName": "Z", "awayParticipantName": "W",
            "homeScore": 4, "awayScore": 1, "tournamentTitle": "L",
            "winLoseShort": "W",
            "stats": {"595": {"type": "minutes-played", "value": "90'"},
                      "596": {"type": "goal", "value": "1"},
                      "599": {"type": "grey", "value": "0"},
                      "541": {"type": "assist", "value": "2"}}}]}}
    data = parse_player_env(env, "pid")
    r = data.results[0]
    assert r.player_goals == 1
    assert r.player_assists == 2


def test_season_minutes_summed_from_league_matches():
    data = parse_player_env(_env(), player_id="O2o2L2iA")
    # minutes is a best-effort sum over current-league recent matches; must be > 0
    assert data.season_stats.minutes > 0


@pytest.mark.network
def test_fetch_player_data_live():
    data = fetch_player_data("O2o2L2iA", "ciubotaru-kevin")
    assert data.team_name == "Dundee Utd"
    assert data.results
    assert all(r.match_id for r in data.results)
