import json
from pathlib import Path
import pytest
from flashscore.search import parse_search, search_players, PlayerHit

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_search_extracts_player_hit():
    payload = json.loads((FIXTURES / "search_ciubotaru.json").read_text())
    hits = parse_search(payload)
    kevin = next(h for h in hits if h.id == "O2o2L2iA")
    assert kevin.name == "Ciubotaru Kevin"
    assert kevin.slug == "ciubotaru-kevin"
    assert kevin.position == "Defender"
    assert kevin.nationality == "Romania"
    assert kevin.club_name == "Dundee Utd"
    assert kevin.club_id == "8QEB2FFp"
    assert kevin.photo and kevin.photo.startswith(
        "https://static.flashscore.com/res/image/data/")


def test_parse_search_ignores_non_player_results():
    payload = json.loads((FIXTURES / "search_ciubotaru.json").read_text())
    hits = parse_search(payload)
    assert all(isinstance(h, PlayerHit) for h in hits)
    # national-team nominations must not become the club
    assert all(h.club_name != "Romania" for h in hits)


@pytest.mark.network
def test_search_players_live():
    hits = search_players("Ciubotaru")
    assert any(h.id == "O2o2L2iA" for h in hits)
