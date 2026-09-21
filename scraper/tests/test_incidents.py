from flashscore.incidents import parse_incidents, player_minutes

# A goal record bundles the scorer AND assister (two IE sub-incidents, one IB).
COMBINED = (
    "AC÷1st Half¬IG÷1¬IH÷1¬~"
    "III÷a¬IA÷2¬IB÷21'¬IE÷3¬IF÷Stoica I.¬IK÷Goal¬IM÷xx¬IU÷/player/stoica-ianis/CGYK9J8D/¬"
    "IE÷8¬IF÷Antonetti L.¬IK÷Assistance¬IM÷yy¬IU÷/player/antonetti-leandro/AA/¬~"
    "III÷b¬IA÷2¬IB÷62'¬IE÷8¬IF÷Stoica I.¬IK÷Assistance¬IM÷xx¬IU÷/player/stoica-ianis/CGYK9J8D/¬~"
    "III÷c¬IA÷2¬IB÷54'¬IE÷10¬IF÷Blesa J.¬IK÷Penalty¬IM÷zz¬IU÷/player/blesa/BB/¬~"
)


def test_parse_incidents_splits_bundled_goal_and_assist():
    events = parse_incidents(COMBINED)
    kinds = [(e["minute"], e["kind"], e["person"]) for e in events]
    assert ("21'", "Goal", "Stoica I.") in kinds        # scorer no longer lost
    assert ("21'", "Assistance", "Antonetti L.") in kinds
    assert ("62'", "Assistance", "Stoica I.") in kinds


def test_player_minutes_by_slug_gets_goal_and_assist():
    events = parse_incidents(COMBINED)
    goals, assists = player_minutes(events, "Ianis Stoica", slug="stoica-ianis")
    assert goals == ["21'"]
    assert assists == ["62'"]


def test_player_minutes_counts_penalty_as_goal():
    events = parse_incidents(COMBINED)
    goals, _ = player_minutes(events, "Jalen Blesa", slug="blesa")
    assert goals == ["54'"]


def test_player_minutes_name_fallback_when_no_slug():
    events = parse_incidents("III÷a¬IB÷10'¬IE÷3¬IF÷Mihaila V.¬IK÷Goal¬IU÷/player/x/Y/¬~")
    goals, _ = player_minutes(events, "Mihăilă Valentin")   # accent-insensitive
    assert goals == ["10'"]


def test_player_minutes_ignores_other_players():
    events = parse_incidents(COMBINED)
    goals, assists = player_minutes(events, "Someone Else", slug="nobody")
    assert goals == [] and assists == []
