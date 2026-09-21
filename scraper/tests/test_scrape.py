from datetime import date, timedelta
from scrape import merge_youtube, build_player_record, group_label, needs_highlight_check
from config import PlayerConfig
from flashscore.search import PlayerHit
from flashscore.player import PlayerData, SeasonStats, MatchResult


def _result(match_id="m1", d="2026-09-14", yt=None):
    return {
        "match_id": match_id, "date": d, "home_team": "A", "away_team": "B",
        "score": "1-0", "competition": "L", "result": "W",
        "player_minutes": 90, "player_goals": 0,
        "flashscore_url": f"https://www.flashscore.com/match/{match_id}/",
        "youtube_url": yt,
    }


def test_merge_youtube_manual_overrides_win():
    results = [_result("m1"), _result("m2")]
    merge_youtube(results, overrides={"m1": "MANUAL"}, scraped={"m1": "AUTO", "m2": "AUTO2"})
    by_id = {r["match_id"]: r["youtube_url"] for r in results}
    assert by_id["m1"] == "MANUAL"
    assert by_id["m2"] == "AUTO2"


def test_merge_youtube_keeps_existing_when_nothing_new():
    results = [_result("m1", yt="EXISTING")]
    merge_youtube(results, overrides={}, scraped={})
    assert results[0]["youtube_url"] == "EXISTING"


def test_group_label_uses_live_league_and_country():
    assert group_label("Premiership", "Scotland", fallback="X") == "Premiership (Scotland)"


def test_group_label_falls_back_when_league_missing():
    assert group_label(None, None, fallback="Turcia") == "Turcia"


def test_needs_highlight_check_only_recent():
    today = date(2026, 9, 20)
    assert needs_highlight_check("2026-09-14", today, window_days=30) is True
    assert needs_highlight_check("2026-01-01", today, window_days=30) is False


def test_build_player_record_shape():
    cfg = PlayerConfig("Kevin Ciubotaru", "O2o2L2iA", "Scotland")
    hit = PlayerHit("O2o2L2iA", "Ciubotaru Kevin", "ciubotaru-kevin",
                    "Defender", "Romania", "Dundee Utd", "8QEB2FFp")
    pdata = PlayerData(
        "O2o2L2iA", "Dundee Utd", "Premiership", "Scotland",
        SeasonStats(1, 0, 3, 206, "6.8"),
        [MatchResult("jiBADrkI", "2026-09-19", "St. Mirren", "Dundee Utd",
                     "0-3", "Premiership (Scotland)", "W", 90, 1)],
    )
    rec = build_player_record(cfg, hit, pdata)
    assert rec["name"] == "Kevin Ciubotaru"
    assert rec["position"] == "Defender"
    assert rec["team"] == "Dundee Utd"
    assert rec["league"] == "Premiership"
    assert rec["group"] == "Premiership (Scotland)"
    assert rec["season_stats"] == {"goals": 1, "assists": 0, "appearances": 3,
                                   "minutes": 206, "rating": "6.8"}
    r0 = rec["results"][0]
    assert r0["match_id"] == "jiBADrkI"
    assert r0["youtube_url"] is None
    assert r0["flashscore_url"].endswith("jiBADrkI/")
