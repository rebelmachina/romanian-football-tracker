"""Goal/assist minutes for a player from Flashscore's match incidents feed.

`df_sui_1_{matchId}` returns incident records: IB = minute ("10'"), IF = person
("Stanciu N."), IK = kind ("Goal" / "Assistance"). We match the incident person
to the tracked player by surname + first initial (accent-insensitive).
"""
from __future__ import annotations
import unicodedata
import requests
from .parser import parse_records

FEED_HOST = "https://global.flashscore.ninja/2/x/feed/"
FSIGN = "SW9D1eZo"
GOAL_KINDS = {"Goal", "Penalty", "Goal (Penalty)"}  # not "Own Goal"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def _norm(s: str) -> str:
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower().strip()


def parse_incidents(text: str) -> list[dict]:
    events = []
    for record in parse_records(text):
        d = dict(record)
        if d.get("IB") and d.get("IF") and d.get("IK"):
            events.append({"minute": d["IB"], "person": d["IF"], "kind": d["IK"]})
    return events


def player_minutes(events: list[dict], name: str) -> tuple[list[str], list[str]]:
    """Return (goal_minutes, assist_minutes) for the player named `name`."""
    tokens = [_norm(t) for t in name.split() if t]
    goals: list[str] = []
    assists: list[str] = []
    for e in events:
        etoks = e["person"].split()
        if len(etoks) < 2:
            surname, initial = _norm(e["person"]), ""
        else:
            surname = _norm(" ".join(etoks[:-1]))
            initial = _norm(etoks[-1]).rstrip(".")[:1]
        surname_ok = surname in tokens
        initial_ok = (not initial) or any(t[:1] == initial for t in tokens if t != surname)
        if surname_ok and initial_ok:
            if e["kind"] in GOAL_KINDS:
                goals.append(e["minute"])
            elif e["kind"] == "Assistance":
                assists.append(e["minute"])

    def _key(m):
        return int("".join(c for c in m if c.isdigit()) or 0)
    return sorted(goals, key=_key), sorted(assists, key=_key)


def fetch_incidents(match_id: str, session: requests.Session | None = None) -> list[dict]:
    s = session or requests.Session()
    resp = s.get(
        FEED_HOST + f"df_sui_1_{match_id}",
        headers={"x-fsign": FSIGN, "Referer": "https://www.flashscore.com/", "User-Agent": UA},
        timeout=20,
    )
    if resp.status_code != 200:
        return []
    return parse_incidents(resp.text)
