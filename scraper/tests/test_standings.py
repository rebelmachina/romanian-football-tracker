from flashscore.standings import parse_standings

# Two groups; ranks reset to 1 at each group start. Romania is in group 2.
FEED = (
    "TR÷1¬TN÷Spain U21¬TI÷aaa¬TW÷7¬TL÷1¬TG÷27:4¬TP÷21¬~"
    "TR÷2¬TN÷Kosovo U21¬TI÷bbb¬TW÷3¬TL÷3¬TG÷15:6¬TP÷11¬~"
    "TR÷1¬TN÷Portugal U21¬TI÷ccc¬TW÷6¬TL÷1¬TG÷29:2¬TP÷19¬~"
    "TR÷2¬TN÷Romania U21¬TI÷dhDp7QEq¬TW÷5¬TL÷2¬TG÷11:4¬TP÷16¬~"
    "TR÷3¬TN÷Cyprus U21¬TI÷ddd¬TW÷1¬TL÷7¬TG÷5:27¬TP÷3¬~"
)


def test_parse_standings_returns_romanias_group():
    table = parse_standings(FEED, "dhDp7QEq")
    assert [t["team"] for t in table] == ["Portugal U21", "Romania U21", "Cyprus U21"]
    ro = next(t for t in table if t["is_romania"])
    assert ro["rank"] == 2
    assert ro["win"] == 5 and ro["loss"] == 2
    assert ro["draw"] == 1          # 16 pts - 3*5 wins
    assert ro["played"] == 8
    assert ro["gf"] == 11 and ro["ga"] == 4
    assert ro["points"] == 16


def test_parse_standings_missing_team_returns_none():
    assert parse_standings(FEED, "nope") is None
