from datetime import date, timedelta
from scrape import merge_youtube, build_player_record, _previous_positions, group_label, needs_highlight_check, _merge_results
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


def test_merge_results_dedupes_filters_and_sorts():
    def mr(mid, d):
        return MatchResult(mid, d, "H", "A", "1-0", "L", "W", 90, 0)
    recent = [mr("m3", "2026-09-01"), mr("m2", "2026-06-01")]
    history = [mr("m2", "2026-06-01"), mr("m1", "2024-01-01"), mr("old", "2020-01-01")]
    out = _merge_results(recent, history, since="2023-01-01")
    ids = [r.match_id for r in out]
    assert ids == ["m3", "m2", "m1"]      # deduped, newest first, "old" filtered out


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


def _pos_record(hit_pos, page_pos, previous=None):
    cfg = PlayerConfig("X", "pid", "C")
    hit = PlayerHit("pid", "X", "x", hit_pos, "Romania", "T", "tid")
    pdata = PlayerData("pid", "T", "L", "C", SeasonStats(0, 0, 0, 0, None),
                       position=page_pos)
    return build_player_record(cfg, hit, pdata, previous_position=previous)


def test_position_prefers_player_page():
    assert _pos_record("Defender", "Forward")["position"] == "Forward"


def test_position_falls_back_to_search_then_previous():
    assert _pos_record("Defender", None, "Forward")["position"] == "Defender"
    assert _pos_record(None, None, "Forward")["position"] == "Forward"
    assert _pos_record(None, None)["position"] is None


def test_previous_positions_skips_missing():
    data = {"players": [{"flashscore_id": "a", "position": "Defender"},
                        {"flashscore_id": "b", "position": None}]}
    assert _previous_positions(data) == {"a": "Defender"}


def test_ascii_fold_strips_romanian_diacritics():
    from scrape import ascii_fold
    assert ascii_fold("Răzvan Marin") == "Razvan Marin"
    assert ascii_fold("Mihai Căpățînă") == "Mihai Capatina"
    assert ascii_fold("Ștefan Vlădoiu") == "Stefan Vladoiu"
