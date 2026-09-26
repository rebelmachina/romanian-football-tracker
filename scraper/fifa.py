"""Romania's current FIFA/Coca-Cola World Ranking, from inside.fifa.com.

The page is a Next.js app; the ranking is embedded in the __NEXT_DATA__ JSON.
We pull the entry for country code ROU (rank, points, previous rank).
"""
from __future__ import annotations
import json
import re
import requests

URL = "https://inside.fifa.com/en/fifa-rankings/world-ranking/ROU?gender=men"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
_NEXT = re.compile(r'id="__NEXT_DATA__"[^>]*>(\{.*?\})</script>', re.DOTALL)


def _find_country(obj, country: str) -> dict | None:
    """First dict with a rank for the given country code (the current overview row)."""
    if isinstance(obj, dict):
        if "rank" in obj and obj.get("countryCode") == country:
            return obj
        for v in obj.values():
            hit = _find_country(v, country)
            if hit:
                return hit
    elif isinstance(obj, list):
        for v in obj:
            hit = _find_country(v, country)
            if hit:
                return hit
    return None


def parse_fifa(html: str, country: str = "ROU") -> dict | None:
    m = _NEXT.search(html)
    if not m:
        return None
    entry = _find_country(json.loads(m.group(1)), country)
    if not entry:
        return None
    return {
        "rank": entry.get("rank"),
        "points": round(float(entry["totalPoints"]), 2) if entry.get("totalPoints") is not None else None,
        "previous_rank": entry.get("previousRank"),
    }


def fetch_fifa_ranking(session: requests.Session | None = None,
                       country: str = "ROU") -> dict | None:
    s = session or requests.Session()
    try:
        resp = s.get(URL, headers={"User-Agent": UA}, timeout=25)
        if resp.status_code != 200:
            return None
        return parse_fifa(resp.text, country)
    except Exception:
        return None
