from __future__ import annotations
from dataclasses import dataclass
import requests

SEARCH_URL = "https://s.livesport.services/api/v2/search/"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# participantType id -> position name. Verified 2026-09-21.
POSITION_TYPES: dict[int, str] = {
    12: "Goalkeeper",
    13: "Defender",
    14: "Midfielder",
    15: "Forward",
}


@dataclass
class PlayerHit:
    id: str
    name: str
    slug: str
    position: str | None
    nationality: str | None
    club_name: str | None
    club_id: str | None


def _position_from_types(participant_types: list[dict]) -> str | None:
    for t in participant_types:
        name = POSITION_TYPES.get(t.get("id"))
        if name:
            return name
    return None


def _club_from_teams(teams: list[dict]) -> tuple[str | None, str | None]:
    for t in teams:
        if t.get("kind") == "TEAM":
            return t.get("name"), t.get("id")
    return None, None


def parse_search(payload: list[dict]) -> list[PlayerHit]:
    hits: list[PlayerHit] = []
    for r in payload:
        if r.get("type", {}).get("name") != "PlayerInTeam":
            continue
        club_name, club_id = _club_from_teams(r.get("teams", []))
        hits.append(PlayerHit(
            id=r["id"],
            name=r.get("name", ""),
            slug=r.get("url", ""),
            position=_position_from_types(r.get("participantTypes", [])),
            nationality=r.get("defaultCountry", {}).get("name"),
            club_name=club_name,
            club_id=club_id,
        ))
    return hits


def search_players(query: str, session: requests.Session | None = None) -> list[PlayerHit]:
    s = session or requests.Session()
    resp = s.get(
        SEARCH_URL,
        params={
            "q": query, "lang-id": 1, "project-id": 2,
            "project-type-id": 1, "sport-ids": 1, "type-ids": "1,2,3,4",
        },
        headers={"Referer": "https://www.flashscore.com/", "User-Agent": UA},
        timeout=20,
    )
    resp.raise_for_status()
    return parse_search(resp.json())
