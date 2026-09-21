from pathlib import Path
import pytest
from flashscore.highlights import parse_highlight, fetch_highlight

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_highlight_extracts_youtube_watch_url():
    text = (FIXTURES / "df_hi_jiBADrkI.txt").read_text(encoding="utf-8")
    url = parse_highlight(text)
    assert url == "https://www.youtube.com/watch?v=ECitipBT3P8"


def test_parse_highlight_returns_none_when_empty():
    assert parse_highlight("A1÷¬~") is None
    assert parse_highlight("") is None


@pytest.mark.network
def test_fetch_highlight_known_match():
    # jiBADrkI has a YouTube highlight
    url = fetch_highlight("jiBADrkI")
    assert url is not None and "youtube.com" in url


@pytest.mark.network
def test_fetch_highlight_missing_returns_none():
    # a bogus id has no highlight -> None (feed 404s)
    assert fetch_highlight("ZZZZZZZZ") is None
