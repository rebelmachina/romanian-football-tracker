from flashscore.incidents import parse_incidents, player_minutes

SAMPLE = (
    "IG÷2¬~IB÷10'¬IF÷Stanciu N.¬IK÷Goal¬~"
    "IB÷23'¬IF÷Gong Ruicong¬IK÷Assistance¬~"
    "IB÷67'¬IF÷Stanciu N.¬IK÷Assistance¬~"
    "IB÷80'¬IF÷Stanciu N.¬IK÷Goal¬~"
)


def test_parse_incidents_extracts_events():
    events = parse_incidents(SAMPLE)
    kinds = [e["kind"] for e in events]
    assert kinds.count("Goal") == 2 and kinds.count("Assistance") == 2


def test_player_minutes_matches_by_surname_and_initial():
    events = parse_incidents(SAMPLE)
    goals, assists = player_minutes(events, "Nicolae Stanciu")
    assert goals == ["10'", "80'"]        # ordered by minute
    assert assists == ["67'"]


def test_player_minutes_accent_insensitive_and_surname_first():
    events = parse_incidents("IB÷5'¬IF÷Mihaila V.¬IK÷Goal¬~")
    goals, _ = player_minutes(events, "Mihăilă Valentin")
    assert goals == ["5'"]


def test_player_minutes_ignores_other_players():
    events = parse_incidents("IB÷5'¬IF÷Gong Ruicong¬IK÷Goal¬~")
    goals, assists = player_minutes(events, "Nicolae Stanciu")
    assert goals == [] and assists == []


def test_player_minutes_counts_penalty_as_goal():
    events = parse_incidents("IB÷54'¬IF÷Stanciu N.¬IK÷Penalty¬~")
    goals, _ = player_minutes(events, "Nicolae Stanciu")
    assert goals == ["54'"]
