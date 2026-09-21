from pathlib import Path
import textwrap
from config import load_players, load_history_years, PlayerConfig
from bootstrap import parse_roster


def test_load_players_parses_yaml(tmp_path: Path):
    p = tmp_path / "players.yaml"
    p.write_text(textwrap.dedent("""
        players:
          - name: Kevin Ciubotaru
            flashscore_id: O2o2L2iA
            country: Scotland
    """))
    players = load_players(p)
    assert players == [PlayerConfig("Kevin Ciubotaru", "O2o2L2iA", "Scotland")]


def test_load_players_skips_unresolved_ids(tmp_path: Path):
    p = tmp_path / "players.yaml"
    p.write_text(textwrap.dedent("""
        players:
          - name: Resolved
            flashscore_id: ABC123
            country: X
          - name: Unresolved
            flashscore_id: ""
            country: Y
    """))
    players = load_players(p)
    assert [pl.name for pl in players] == ["Resolved"]


def test_load_history_years(tmp_path):
    p = tmp_path / "players.yaml"
    p.write_text("history_years: 3\nplayers: []\n")
    assert load_history_years(p) == 3.0
    p.write_text("players: []\n")
    assert load_history_years(p, default=1.0) == 1.0


def test_parse_roster_groups_by_country():
    text = "# Scotland\nKevin Ciubotaru\n# Netherlands\nDennis Man\n"
    assert parse_roster(text) == {
        "Scotland": ["Kevin Ciubotaru"],
        "Netherlands": ["Dennis Man"],
    }
