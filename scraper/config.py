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


def load_standings(path: str | Path) -> list[dict]:
    """Top-level `standings` list in players.yaml (key, name, team_id, feed)."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return data.get("standings", []) or []


def load_history_years(path: str | Path, default: float = 1.0) -> float:
    """Top-level `history_years` in players.yaml — how far back to scrape."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    try:
        return float(data.get("history_years", default))
    except (TypeError, ValueError):
        return default
