from fifa import parse_fifa

PAGE = (
    '<html><body>'
    '<script id="__NEXT_DATA__" type="application/json">'
    '{"props":{"rows":['
    '{"rank":51,"countryCode":"CRC","name":"Costa Rica","totalPoints":1456.03,"previousRank":53},'
    '{"rank":52,"countryCode":"ROU","name":"Romania","totalPoints":1455.89,"previousRank":54},'
    '{"rank":53,"countryCode":"NGA","name":"Nigeria","totalPoints":1455.0,"previousRank":50}'
    ']}}'
    '</script></body></html>'
)


def test_parse_fifa_extracts_romania():
    r = parse_fifa(PAGE, "ROU")
    assert r == {"rank": 52, "points": 1455.89, "previous_rank": 54}


def test_parse_fifa_missing_country():
    assert parse_fifa(PAGE, "XXX") is None


def test_parse_fifa_no_next_data():
    assert parse_fifa("<html>no data</html>") is None
