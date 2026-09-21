from pathlib import Path
from flashscore.parser import parse_records, labeled_pairs

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_records_splits_records_fields_and_kv():
    text = "AC÷3¬BA÷0¬BB÷3¬~BC÷0¬BD÷0¬~"
    records = parse_records(text)
    assert records == [
        [("AC", "3"), ("BA", "0"), ("BB", "3")],
        [("BC", "0"), ("BD", "0")],
    ]


def test_parse_records_preserves_duplicate_keys():
    text = "MIT÷REF¬MIV÷Dickinson D.¬MIT÷VEN¬MIV÷The SMISA Stadium¬~"
    [record] = parse_records(text)
    keys = [k for k, _ in record]
    assert keys.count("MIT") == 2
    assert keys.count("MIV") == 2


def test_parse_records_ignores_empty_and_valueless():
    # trailing empty record after final ~, and a bare "A1÷" (empty value) is kept
    text = "A1÷¬~"
    [record] = parse_records(text)
    assert record == [("A1", "")]


def test_labeled_pairs_collapses_mit_miv():
    text = (FIXTURES / "df_sur_jiBADrkI.txt").read_text(encoding="utf-8")
    records = parse_records(text)
    # the venue record is the one containing MIT/MIV pairs
    venue_record = next(r for r in records if any(k == "MIT" for k, _ in r))
    info = labeled_pairs(venue_record, "MIT", "MIV")
    assert info["VEN"] == "The SMISA Stadium"
    assert info["TWN"] == "Paisley"
    assert info["REF"] == "Dickinson D."
