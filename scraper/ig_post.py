"""Publish the daily story + feed post to Instagram (@renasterea.nationalei).

Posts the JPEGs stories.py renders, from their public GitHub Pages URLs
(Instagram's servers fetch them). Only finished days are posted: before
today and at most LOOKBACK_DAYS back. ig_posted.json records what went up,
per day and per format, so re-runs never post twice.

Usage:
    python ig_post.py --check                 # prints days=<pending days> (no API calls)
    python ig_post.py --post 2026-10-29       # needs IG_TOKEN and IG_USER_ID
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

from stories import DATA_PATH, OUT_DIR, FORMATS, collect

GRAPH = "https://graph.facebook.com/v26.0"
PUBLIC_BASE = "https://rebelmachina.github.io/romanian-football-tracker/stories"
LOG_PATH = Path(__file__).resolve().parent / "ig_posted.json"
LOOKBACK_DAYS = 3
HASHTAGS = "#tricolorii #fotbal #romania #stranieri"

WEEKDAYS = ["luni", "marți", "miercuri", "joi", "vineri", "sâmbătă", "duminică"]
MONTHS = ["ianuarie", "februarie", "martie", "aprilie", "mai", "iunie", "iulie",
          "august", "septembrie", "octombrie", "noiembrie", "decembrie"]
COUNTRIES = {
    "Armenia": "Armenia", "Asia": "Asia", "Azerbaijan": "Azerbaidjan", "Bulgaria": "Bulgaria",
    "China": "China", "Cyprus": "Cipru", "England": "Anglia", "Europe": "Europa",
    "France": "Franța", "Germany": "Germania", "Greece": "Grecia", "Hungary": "Ungaria",
    "Israel": "Israel", "Italy": "Italia", "Kazakhstan": "Kazahstan", "Lithuania": "Lituania",
    "Malta": "Malta", "Netherlands": "Olanda", "Poland": "Polonia", "Portugal": "Portugalia",
    "Qatar": "Qatar", "Russia": "Rusia", "Saudi Arabia": "Arabia Saudită",
    "Scotland": "Scoția", "Serbia": "Serbia", "Slovakia": "Slovacia", "Slovenia": "Slovenia",
    "Spain": "Spania", "Thailand": "Thailanda", "Turkey": "Turcia", "USA": "SUA",
    "World": "Internațional",
}


# ----------------------------------------------------------------------------
# Captions
# ----------------------------------------------------------------------------
def contribution(goals: int, assists: int) -> str:
    g = {0: "", 1: "gol", 2: "dublă", 3: "hat-trick"}.get(goals, f"{goals} goluri")
    a = {0: "", 1: "pasă de gol"}.get(assists, f"{assists} pase de gol")
    return " și ".join(x for x in (g, a) if x)


def competition(name: str) -> str:
    """'Serie A (Italy)' -> 'Serie A, Italia'."""
    if name.endswith(")") and " (" in name:
        league, country = name[:-1].rsplit(" (", 1)
        return f"{league}, {COUNTRIES.get(country, country)}"
    return name


def caption(day: str, entries: list[dict]) -> str:
    d = date.fromisoformat(day)
    lines = [f"{e['name']} – {contribution(e['goals'], e['assists'])} în "
             f"{e['home']} {e['score']} {e['away']} ({competition(e['competition'])})"
             for e in entries]
    head = f"Românii din străinătate – {WEEKDAYS[d.weekday()]}, {d.day} {MONTHS[d.month - 1]}"
    return "\n\n".join([head, "\n".join(lines), HASHTAGS])


# ----------------------------------------------------------------------------
# What to post
# ----------------------------------------------------------------------------
def load_log() -> dict:
    return json.loads(LOG_PATH.read_text(encoding="utf-8")) if LOG_PATH.exists() else {}


def save_log(log: dict) -> None:
    LOG_PATH.write_text(json.dumps(log, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def pending(today: date, log: dict, out_dir: Path = OUT_DIR) -> list[str]:
    """Finished days (before today, within LOOKBACK_DAYS) with rendered JPEGs
    and at least one format not yet posted, oldest first."""
    days = []
    for i in range(LOOKBACK_DAYS, 0, -1):
        day = str(today - timedelta(days=i))
        done = log.get(day, {})
        missing = [f for f, spec in FORMATS.items()
                   if f not in done and (out_dir / f"{day}{spec['suffix']}.jpg").exists()]
        if missing:
            days.append(day)
    return days


# ----------------------------------------------------------------------------
# Graph API
# ----------------------------------------------------------------------------
def api(method: str, path: str, **params) -> dict:
    params["access_token"] = os.environ["IG_TOKEN"]
    url = f"{GRAPH}/{path}"
    r = (requests.get(url, params=params, timeout=60) if method == "GET"
         else requests.post(url, data=params, timeout=120))
    data = r.json()
    if r.status_code >= 400 or "error" in data:
        raise RuntimeError(f"{method} {path}: {json.dumps(data.get('error', data))}")
    return data


def publish(image_url: str, caption_text: str | None) -> str:
    user = os.environ["IG_USER_ID"]
    fields = {"image_url": image_url}
    if caption_text is None:
        fields["media_type"] = "STORIES"
    else:
        fields["caption"] = caption_text
    cid = api("POST", f"{user}/media", **fields)["id"]
    for _ in range(60):
        status = api("GET", cid, fields="status_code")["status_code"]
        if status == "FINISHED":
            break
        if status in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"container {cid} {status}")
        time.sleep(5)
    else:
        raise RuntimeError(f"container {cid} not ready after 5 min")
    return api("POST", f"{user}/media_publish", creation_id=cid)["id"]


def post_day(day: str, data: dict, log: dict) -> None:
    entries = collect(data, day)
    if not entries:
        print(f"  {day}: no goals/assists — nothing to post")
        return
    done = log.setdefault(day, {})
    for fmt, spec in FORMATS.items():          # story first, then the feed post
        if fmt in done:
            continue
        url = f"{PUBLIC_BASE}/{day}{spec['suffix']}.jpg"
        if requests.head(url, timeout=30).status_code != 200:
            raise RuntimeError(f"{url} is not live yet")
        media_id = publish(url, None if fmt == "story" else caption(day, entries))
        done[fmt] = media_id
        done[f"{fmt}_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        save_log(log)                           # record each format as soon as it's up
        print(f"  {day} {fmt}: {media_id}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true", help="print days=<pending days>")
    g.add_argument("--post", nargs="+", metavar="DAY", help="publish these days")
    ap.add_argument("--dry-run", action="store_true", help="print captions, post nothing")
    args = ap.parse_args(argv)

    log = load_log()
    if args.check:
        print("days=" + " ".join(pending(date.today(), log)))
        return 0
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    for day in args.post:
        if args.dry_run:
            print(f"--- {day}\n{caption(day, collect(data, day))}")
        else:
            post_day(day, data, log)
    return 0


if __name__ == "__main__":
    sys.exit(main())
