from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import yaml


@dataclass
class PlayerConfig:
    name: str
    flashscore_id: str
    country: str


def load_players(path: str | Path) -> list[PlayerConfig]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    result: list[PlayerConfig] = []
    for entry in data.get("players", []):
        fid = (entry.get("flashscore_id") or "").strip()
        if not fid:
            continue
        result.append(PlayerConfig(entry["name"], fid, entry.get("country", "")))
    return result
