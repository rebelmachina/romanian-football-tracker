"""Resolve player names to Flashscore IDs for players.yaml.

Usage:
    python bootstrap.py            # reads roster.txt, writes drafts
Paste the user's country-grouped roster into roster.txt as:
    # Country
    Player One
    Player Two
"""
from __future__ import annotations
import sys
import time
from dataclasses import asdict
import yaml
from flashscore.search import search_players


def parse_roster(text: str) -> dict[str, list[str]]:
    by_country: dict[str, list[str]] = {}
    country = "Unknown"
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            country = line.lstrip("# ").strip()
            by_country.setdefault(country, [])
        else:
            by_country.setdefault(country, []).append(line)
    return by_country


def resolve(names_by_country: dict[str, list[str]]) -> list[dict]:
    out: list[dict] = []
    for country, names in names_by_country.items():
        for name in names:
            hits = search_players(name)[:3]
            out.append({
                "query": name,
                "country": country,
                "candidates": [asdict(h) for h in hits],
            })
            time.sleep(0.3)
    return out


def main() -> int:
    roster = parse_roster(open("roster.txt", encoding="utf-8").read())
    resolved = resolve(roster)
    players = []
    for item in resolved:
        top = item["candidates"][0] if item["candidates"] else None
        players.append({
            "name": item["query"],
            "flashscore_id": top["id"] if top else "",
            "country": item["country"],
        })
    yaml.safe_dump({"players": players}, open("players.draft.yaml", "w"),
                   allow_unicode=True, sort_keys=False)
    yaml.safe_dump(resolved, open("candidates.yaml", "w"),
                   allow_unicode=True, sort_keys=False)
    print(f"Wrote players.draft.yaml ({len(players)} players) and candidates.yaml")
    print("Review ambiguous names in candidates.yaml, then copy into players.yaml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
