"""Goal/assist minutes for a player from Flashscore's match incidents feed.

`df_sui_1_{matchId}` returns incident records. One record can bundle several
sub-incidents (a goal packs the scorer AND the assister), each delimited by an
`IE` field, sharing the record's `IB` minute. Per sub-incident: IF = person,
IK = kind ("Goal"/"Penalty"/"Assistance"/…), IM = participant id, IU = player
url. We match the player by url slug (robust) or surname+initial fallback.
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
    events: list[dict] = []
    for record in parse_records(text):
        minute = None
        subs: list[dict] = []
        cur: dict | None = None
        for k, v in record:
            if k == "IB":
                minute = v
            elif k == "IE":                 # each IE starts a new sub-incident
                cur = {}
                subs.append(cur)
            elif cur is not None and k in ("IF", "IK", "IM", "IU"):
                cur[k] = v
        for sub in subs:
            if sub.get("IK"):
                events.append({
                    "minute": minute or "",
                    "person": sub.get("IF", ""),
                    "kind": sub["IK"],
                    "id": sub.get("IM", ""),
                    "url": sub.get("IU", ""),
                })
    return events


def _name_match(person: str, tokens: list[str]) -> bool:
    etoks = person.split()
    if len(etoks) < 2:
        return _norm(person) in tokens
    surname = _norm(" ".join(etoks[:-1]))
    initial = _norm(etoks[-1]).rstrip(".")[:1]
    return surname in tokens and (not initial or any(t[:1] == initial for t in tokens if t != surname))


def _min_key(m: str) -> int:
    return int("".join(c for c in m if c.isdigit()) or 0)


def player_minutes(events: list[dict], name: str,
                   slug: str | None = None) -> tuple[list[str], list[str]]:
    """Return (goal_minutes, assist_minutes) for the given player."""
    tokens = [_norm(t) for t in name.split() if t]
    goals: list[str] = []
    assists: list[str] = []
    for e in events:
        is_me = (slug and slug in e.get("url", "")) or _name_match(e["person"], tokens)
        if not is_me:
            continue
        if e["kind"] in GOAL_KINDS:
            goals.append(e["minute"])
        elif e["kind"] == "Assistance":
            assists.append(e["minute"])
    return sorted(goals, key=_min_key), sorted(assists, key=_min_key)


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
