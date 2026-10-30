from datetime import date
from ig_post import caption, competition, contribution, pending


def test_contribution():
    assert contribution(1, 0) == "gol"
    assert contribution(2, 0) == "dublă"
    assert contribution(3, 0) == "hat-trick"
    assert contribution(4, 0) == "4 goluri"
    assert contribution(0, 2) == "2 pase de gol"
    assert contribution(1, 1) == "gol și pasă de gol"


def test_competition_translates_country():
    assert competition("Serie A (Italy)") == "Serie A, Italia"
    assert competition("AFC Champions League (Asia)") == "AFC Champions League, Asia"
    assert competition("Some Cup (Atlantis)") == "Some Cup, Atlantis"   # unknown: kept
    assert competition("Friendly") == "Friendly"


def test_caption():
    entries = [{"name": "Daniel Birligea", "goals": 2, "assists": 0, "home": "Frosinone",
                "score": "5-1", "away": "Lecce", "competition": "Serie A (Italy)"}]
    assert caption("2026-10-29", entries) == (
        "Românii din străinătate – joi, 29 octombrie\n\n"
        "Daniel Birligea – dublă în Frosinone 5-1 Lecce (Serie A, Italia)\n\n"
        "#tricolorii #fotbal #romania #stranieri")


def test_pending(tmp_path):
    for name in ["2026-10-27.jpg", "2026-10-27-post.jpg", "2026-10-28.jpg",
                 "2026-10-28-post.jpg", "2026-10-29.jpg", "2026-10-29-post.jpg",
                 "2026-10-30.jpg", "2026-10-30-post.jpg", "2026-10-20.jpg"]:
        (tmp_path / name).touch()
    log = {"2026-10-28": {"story": "1", "post": "2"}, "2026-10-29": {"story": "3"}}
    # today is excluded (unfinished), the 20th is past the lookback, the 28th is done,
    # the 29th still needs its feed post
    assert pending(date(2026, 10, 30), log, tmp_path) == ["2026-10-27", "2026-10-29"]
