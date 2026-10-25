from datetime import date
from stories import collect, weekend_dates, plural, render_html


def _data():
    def res(d, g, a, nat=False):
        return {"date": d, "player_goals": g, "player_assists": a, "is_national": nat,
                "home_team": "H", "away_team": "A", "score": "1-0", "competition": "L"}
    return {"players": [
        {"name": "A One", "team": "H", "results": [res("2026-10-24", 0, 1)]},
        {"name": "B Two", "team": "H", "results": [res("2026-10-24", 2, 0),
                                                    res("2026-10-25", 1, 0, nat=True)]},
        {"name": "C Three", "team": "H", "results": [res("2026-10-24", 0, 0)]},
    ]}


def test_collect_filters_and_orders_by_contribution():
    names = [e["name"] for e in collect(_data(), "2026-10-24")]
    assert names == ["B Two", "A One"]          # C had none; B has more


def test_collect_skips_national_team_games():
    assert collect(_data(), "2026-10-25") == []


def test_weekend_dates():
    assert weekend_dates(date(2026, 10, 24)) == ["2026-10-23", "2026-10-24"]   # Sat
    assert weekend_dates(date(2026, 10, 27)) == ["2026-10-23", "2026-10-24", "2026-10-25"]  # Tue
    assert weekend_dates(date(2026, 10, 23)) == ["2026-10-23"]                 # Fri


def test_plural_romanian():
    assert plural(1, "GOL", "GOLURI") == "1 GOL"
    assert plural(2, "GOL", "GOLURI") == "2 GOLURI"


def test_render_html_escapes_and_labels_day():
    entries = collect(_data(), "2026-10-24")
    entries[0]["name"] = "<b>X</b>"
    html = render_html("2026-10-24", entries)
    assert "SÂMBĂTĂ" in html and "24 OCTOMBRIE 2026" in html
    assert "<b>X</b>" not in html and "&lt;b&gt;X&lt;/b&gt;" in html


def test_card_shows_result():
    entries = collect(_data(), "2026-10-24")
    entries[0]["result"] = "L"
    html = render_html("2026-10-24", entries)
    assert 'class="card res-L"' in html and "ÎNFRÂNGERE" in html


def test_post_format_is_4_by_5():
    html = render_html("2026-10-24", collect(_data(), "2026-10-24"), "post")
    assert "height: 1350px" in html and '<body class="post' in html
