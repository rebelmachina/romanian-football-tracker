"""Group standings from Flashscore's `to_{template}_{season}_1` feed.

The feed lists every group's table as records with TR (rank), TN (team name),
TI (team id), TW (wins), TL (losses), TG ("gf:ga"), TP (points). Groups run
sequentially (rank resets to 1). We return the group containing `team_id`.
"""
from __future__ import annotations
import requests
from .parser import parse_records

FEED_HOST = "https://global.flashscore.ninja/2/x/feed/"
FSIGN = "SW9D1eZo"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def _int(v) -> int:
    try:
        return int(str(v).strip())
    except (ValueError, TypeError):
        return 0


def parse_standings(text: str, team_id: str) -> list[dict] | None:
    rows = [dict(r) for r in parse_records(text)
            if "TN" in dict(r) and "TP" in dict(r) and "TR" in dict(r)]
    groups: list[list[dict]] = []
    cur: list[dict] = []
    for d in rows:
        if d.get("TR") == "1" and cur:
            groups.append(cur)
            cur = []
        cur.append(d)
    if cur:
        groups.append(cur)

    target = next((g for g in groups if any(d.get("TI") == team_id for d in g)), None)
    if not target:
        return None

    table = []
    for d in target:
        w, l, pts = _int(d.get("TW")), _int(d.get("TL")), _int(d.get("TP"))
        draw = max(0, pts - 3 * w)
        gf, ga = (d.get("TG", "0:0").split(":") + ["0", "0"])[:2]
        table.append({
            "rank": _int(d.get("TR")), "team": d.get("TN", ""), "team_id": d.get("TI", ""),
            "played": w + draw + l, "win": w, "draw": draw, "loss": l,
            "gf": _int(gf), "ga": _int(ga), "points": pts,
            "is_romania": d.get("TI") == team_id,
        })
    return table


def fetch_standings(feed: str, team_id: str,
                    session: requests.Session | None = None) -> list[dict] | None:
    s = session or requests.Session()
    resp = s.get(FEED_HOST + feed,
                 headers={"x-fsign": FSIGN, "Referer": "https://www.flashscore.com/",
                          "User-Agent": UA}, timeout=20)
    if resp.status_code != 200:
        return None
    return parse_standings(resp.text, team_id)
