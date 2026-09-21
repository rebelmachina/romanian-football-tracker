"""YouTube highlight links from Flashscore's `df_hi` match feed.

The feed returns pipe-delimited fields; `HUO` carries the YouTube watch URL
and `HHV` the provider name. A match with no highlight 404s. Plain HTTP —
no browser needed.
"""
from __future__ import annotations
import requests
from .parser import parse_records

FEED_HOST = "https://global.flashscore.ninja/2/x/feed/"
FSIGN = "SW9D1eZo"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def _normalize_youtube(url: str) -> str:
    return url.replace("http://", "https://").replace("www.youtube", "www.youtube")


def parse_highlight(text: str) -> str | None:
    for record in parse_records(text):
        fields = dict(record)
        watch = fields.get("HUO")
        if watch and ("youtube.com" in watch or "youtu.be" in watch):
            url = watch if watch.startswith("http") else "https://" + watch
            if url.startswith("http://"):
                url = "https://" + url[len("http://"):]
            return url
    return None


def fetch_highlight(match_id: str,
                    session: requests.Session | None = None) -> str | None:
    s = session or requests.Session()
    resp = s.get(
        FEED_HOST + f"df_hi_1_{match_id}",
        headers={"x-fsign": FSIGN, "Referer": "https://www.flashscore.com/",
                 "User-Agent": UA},
        timeout=20,
    )
    if resp.status_code != 200:
        return None
    return parse_highlight(resp.text)
