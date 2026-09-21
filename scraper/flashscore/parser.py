"""Parser for Flashscore's pipe-delimited feed format.

Records are separated by '~', fields by '¬', key/value by the first '÷'.
Keys may repeat within a record (e.g. MIT/MIV label/value sequences), so a
record is represented as an ordered list of (key, value) pairs.
"""
from __future__ import annotations

RECORD_SEP = "~"
FIELD_SEP = "¬"
KV_SEP = "÷"


def parse_records(text: str) -> list[list[tuple[str, str]]]:
    records: list[list[tuple[str, str]]] = []
    for raw in text.split(RECORD_SEP):
        raw = raw.strip()
        if not raw:
            continue
        pairs: list[tuple[str, str]] = []
        for field in raw.split(FIELD_SEP):
            if KV_SEP not in field:
                continue
            key, value = field.split(KV_SEP, 1)
            pairs.append((key, value))
        if pairs:
            records.append(pairs)
    return records


def labeled_pairs(
    pairs: list[tuple[str, str]], label_key: str, value_key: str
) -> dict[str, str]:
    """Collapse alternating label/value fields into a dict.

    e.g. [(MIT, VEN), (MIV, The SMISA Stadium)] -> {"VEN": "The SMISA Stadium"}
    """
    result: dict[str, str] = {}
    pending_label: str | None = None
    for key, value in pairs:
        if key == label_key:
            pending_label = value
        elif key == value_key and pending_label is not None:
            result[pending_label] = value
            pending_label = None
    return result
