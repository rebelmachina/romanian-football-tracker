# Romanian Football Tracker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A GitHub Pages site that tracks ~80 Romanian footballers abroad — season G/A/minutes/position, recent team results, and YouTube highlight links — updated daily by a GitHub Actions scraper reading Flashscore.

**Architecture:** A Python scraper (run in GitHub Actions) pulls data from Flashscore's undocumented API: a JSON search endpoint resolves player names → stable IDs + position + current club, and pipe-delimited feed endpoints provide stats/results. Playwright is used only to (a) discover the player/team feed names once and (b) extract YouTube links from match pages. The scraper writes `site/data.json`, which a static vanilla-JS frontend renders grouped by country. A manual `links.json` supplies YouTube overrides.

**Tech Stack:** Python 3.11 (`requests`, `PyYAML`, `playwright`), vanilla HTML/CSS/JS, GitHub Actions, GitHub Pages.

**Spec:** `docs/superpowers/specs/2026-09-21-romanian-football-tracker-design.md`
**API reference:** `docs/flashscore-api-notes.md` (verified endpoints — read this before Tasks 2–6)

## Global Constraints

- **Feed host:** `https://global.flashscore.ninja/2/x/feed/{feed}` — NOT `d.flashscore.com` (returns empty). Required header `x-fsign: SW9D1eZo` and `Referer: https://www.flashscore.com/`.
- **Search host:** `https://s.livesport.services/api/v2/search/` returns JSON.
- **Feed format:** records split on `~`, fields on `¬`, key/value on first `÷`. Keys can repeat within a record (e.g. `MIT`/`MIV` label/value pairs) — never parse a record into a plain dict without handling repeats.
- **Rate limiting:** ≥0.3s delay between Flashscore requests; reuse one `requests.Session`.
- **Python:** 3.11. **Line length / style:** default `ruff`/PEP8, no enforced formatter required.
- **All generated site output goes to `site/data.json`** (GitHub Pages serves from `site/`).
- **Player IDs are stable across transfers** — the config keys on `flashscore_id`; current club is re-fetched every run.
- **Tests:** `pytest`. Unit tests must not require network EXCEPT the explicitly-marked `@pytest.mark.network` integration tests.

---

### Task 1: Project scaffold + feed parser

The pipe-delimited parser is a pure function and the foundation for every feed. Fixtures for it are captured from the real (already-verified) match feed.

**Files:**
- Create: `scraper/requirements.txt`
- Create: `.gitignore`
- Create: `scraper/flashscore/__init__.py`
- Create: `scraper/flashscore/parser.py`
- Create: `scraper/tests/__init__.py`
- Create: `scraper/tests/fixtures/df_sur_jiBADrkI.txt`
- Test: `scraper/tests/test_parser.py`

**Interfaces:**
- Produces:
  - `parse_records(text: str) -> list[list[tuple[str, str]]]` — one inner list of (key, value) pairs per `~`-record, preserving order and duplicate keys.
  - `labeled_pairs(pairs: list[tuple[str, str]], label_key: str, value_key: str) -> dict[str, str]` — collapses alternating label/value fields (e.g. `MIT`/`MIV`) into a dict.

- [ ] **Step 1: Create `scraper/requirements.txt`**

```
requests==2.32.3
PyYAML==6.0.2
playwright==1.47.0
pytest==8.3.3
```

- [ ] **Step 2: Create `.gitignore`**

```
__pycache__/
*.pyc
.pytest_cache/
.venv/
scraper/tests/.cache/
```

- [ ] **Step 3: Create the fixture file `scraper/tests/fixtures/df_sur_jiBADrkI.txt`**

Paste this exact verified response (the St Mirren vs Dundee Utd match summary):

```
AC÷3¬BA÷0¬BB÷3¬~BC÷0¬BD÷0¬~MIT÷REF¬MIV÷Dickinson D.¬MIT÷RCO¬MIV÷199¬MIT÷RTY¬MIV÷23¬MIT÷RCC¬MIV÷Sco¬MIT÷VEN¬MIV÷The SMISA Stadium¬MIT÷TWN¬MIV÷Paisley¬MIT÷ATT¬MIV÷6 975¬MIT÷CAP¬MIV÷7 937¬A1÷¬~
```

- [ ] **Step 4: Write the failing test `scraper/tests/test_parser.py`**

```python
from pathlib import Path
from flashscore.parser import parse_records, labeled_pairs

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_records_splits_records_fields_and_kv():
    text = "AC÷3¬BA÷0¬BB÷3¬~BC÷0¬BD÷0¬~"
    records = parse_records(text)
    assert records == [
        [("AC", "3"), ("BA", "0"), ("BB", "3")],
        [("BC", "0"), ("BD", "0")],
    ]


def test_parse_records_preserves_duplicate_keys():
    text = "MIT÷REF¬MIV÷Dickinson D.¬MIT÷VEN¬MIV÷The SMISA Stadium¬~"
    [record] = parse_records(text)
    keys = [k for k, _ in record]
    assert keys.count("MIT") == 2
    assert keys.count("MIV") == 2


def test_parse_records_ignores_empty_and_valueless():
    # trailing empty record after final ~, and a bare "A1÷" (empty value) is kept
    text = "A1÷¬~"
    [record] = parse_records(text)
    assert record == [("A1", "")]


def test_labeled_pairs_collapses_mit_miv():
    text = (FIXTURES / "df_sur_jiBADrkI.txt").read_text(encoding="utf-8")
    records = parse_records(text)
    # the venue record is the one containing MIT/MIV pairs
    venue_record = next(r for r in records if any(k == "MIT" for k, _ in r))
    info = labeled_pairs(venue_record, "MIT", "MIV")
    assert info["VEN"] == "The SMISA Stadium"
    assert info["TWN"] == "Paisley"
    assert info["REF"] == "Dickinson D."
```

- [ ] **Step 5: Run test to verify it fails**

Run: `cd scraper && python -m pytest tests/test_parser.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'flashscore.parser'`

- [ ] **Step 6: Implement `scraper/flashscore/parser.py`**

```python
"""Parser for Flashscore's pipe-delimited feed format.

Records are separated by '~', fields by '¬', key/value by the first '÷'.
Keys may repeat within a record (e.g. MIT/MIV label/value sequences), so a
record is represented as an ordered list of (key, value) pairs.
"""
from __future__ import annotations

RECORD_SEP = "~"
FIELD_SEP = "¬"  # ¬
KV_SEP = "÷"     # ÷


def parse_records(text: str) -> list[list[tuple[str, str]]]:
    records: list[list[tuple[str, str]]] = []
    for raw in text.split(RECORD_SEP):
        raw = raw.strip()
        if not raw:
            continue
        pairs: list[tuple[str, str]] = []
        for field in raw.split(FIELD_SEP):
            if KV_SEP not in field:
                continue
            key, value = field.split(KV_SEP, 1)
            pairs.append((key, value))
        if pairs:
            records.append(pairs)
    return records


def labeled_pairs(
    pairs: list[tuple[str, str]], label_key: str, value_key: str
) -> dict[str, str]:
    """Collapse alternating label/value fields into a dict.

    e.g. [(MIT, VEN), (MIV, The SMISA Stadium)] -> {"VEN": "The SMISA Stadium"}
    """
    result: dict[str, str] = {}
    pending_label: str | None = None
    for key, value in pairs:
        if key == label_key:
            pending_label = value
        elif key == value_key and pending_label is not None:
            result[pending_label] = value
            pending_label = None
    return result
```

- [ ] **Step 7: Run test to verify it passes**

Run: `cd scraper && python -m pytest tests/test_parser.py -v`
Expected: PASS (4 tests)

- [ ] **Step 8: Commit**

```bash
git add scraper/ .gitignore
git commit -m "feat: add Flashscore pipe-delimited feed parser + scaffold"
```

---

### Task 2: Search client — resolve player name → ID, position, club, nationality

Uses the verified JSON search endpoint. This is the source of truth for config bootstrapping and for current-club (transfer) detection.

**Files:**
- Create: `scraper/flashscore/search.py`
- Test: `scraper/tests/test_search.py`
- Create: `scraper/tests/fixtures/search_ciubotaru.json`

**Interfaces:**
- Consumes: nothing from prior tasks.
- Produces:
  - `@dataclass PlayerHit` with fields: `id: str`, `name: str`, `slug: str`, `position: str | None`, `nationality: str | None`, `club_name: str | None`, `club_id: str | None`.
  - `parse_search(payload: list[dict]) -> list[PlayerHit]` — pure, parses a search JSON array.
  - `search_players(query: str, session: requests.Session | None = None) -> list[PlayerHit]` — hits the live endpoint.
  - `POSITION_TYPES: dict[int, str]` mapping participantType id → position name (`13→"Defender"`, `12→"Goalkeeper"`, `14→"Midfielder"`, `15→"Forward"`). Discover the exact ids for GK/MF/FW during this task (Defender=13 is verified) using the queries in Step 1; assert them in the test.

- [ ] **Step 1: Capture fixtures and confirm participantType ids**

Run these and save the first as the fixture; use the others to fill `POSITION_TYPES`:

```bash
cd scraper
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
Q="https://s.livesport.services/api/v2/search/?lang-id=1&project-id=2&project-type-id=1&sport-ids=1&type-ids=1,2,3,4&q="
curl -sSL -H "Referer: https://www.flashscore.com/" -A "$UA" "${Q}Ciubotaru" -o tests/fixtures/search_ciubotaru.json
# Inspect a keeper, a midfielder, a forward to learn their participantType ids:
for name in Moldovan Stanciu Coman; do
  echo "== $name =="
  curl -sSL -H "Referer: https://www.flashscore.com/" -A "$UA" "${Q}${name}" \
    | python3 -c "import sys,json;[print(r['name'],[t for t in r.get('participantTypes',[])]) for r in json.load(sys.stdin) if r.get('type',{}).get('name')=='PlayerInTeam'][:5]"
done
```

Record the id→name mapping you observe in `POSITION_TYPES`.

- [ ] **Step 2: Write the failing test `scraper/tests/test_search.py`**

```python
import json
from pathlib import Path
import pytest
from flashscore.search import parse_search, search_players, PlayerHit

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_search_extracts_player_hit():
    payload = json.loads((FIXTURES / "search_ciubotaru.json").read_text())
    hits = parse_search(payload)
    kevin = next(h for h in hits if h.id == "O2o2L2iA")
    assert kevin.name == "Ciubotaru Kevin"
    assert kevin.slug == "ciubotaru-kevin"
    assert kevin.position == "Defender"
    assert kevin.nationality == "Romania"
    assert kevin.club_name == "Dundee Utd"
    assert kevin.club_id == "8QEB2FFp"


def test_parse_search_ignores_non_player_results():
    payload = json.loads((FIXTURES / "search_ciubotaru.json").read_text())
    hits = parse_search(payload)
    assert all(isinstance(h, PlayerHit) for h in hits)
    # national-team nominations must not become the club
    assert all(h.club_name != "Romania" for h in hits)


@pytest.mark.network
def test_search_players_live():
    hits = search_players("Ciubotaru")
    assert any(h.id == "O2o2L2iA" for h in hits)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd scraper && python -m pytest tests/test_search.py -v -m "not network"`
Expected: FAIL with `ModuleNotFoundError: No module named 'flashscore.search'`

- [ ] **Step 4: Implement `scraper/flashscore/search.py`**

```python
from __future__ import annotations
from dataclasses import dataclass
import requests

SEARCH_URL = "https://s.livesport.services/api/v2/search/"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# participantType id -> position name. Defender=13 verified 2026-09-21;
# fill the rest from Task 2 Step 1 before relying on them.
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
```

- [ ] **Step 5: Run tests (unit + live) to verify they pass**

Run: `cd scraper && python -m pytest tests/test_search.py -v`
Expected: PASS (3 tests, including the live network test)

- [ ] **Step 6: Commit**

```bash
git add scraper/flashscore/search.py scraper/tests/test_search.py scraper/tests/fixtures/search_ciubotaru.json
git commit -m "feat: add Flashscore search client for player resolution"
```

---

### Task 3: Roster config + bootstrap tool

Provides `players.yaml` loading and a CLI that resolves the user's player list into `flashscore_id`s (via Task 2), writing a candidates file for human confirmation of ambiguous names.

**Files:**
- Create: `players.yaml` (seed with a few players; full roster populated by running the tool)
- Create: `scraper/config.py`
- Create: `scraper/bootstrap.py`
- Test: `scraper/tests/test_config.py`

**Interfaces:**
- Consumes: `search_players` (Task 2), `PlayerHit`.
- Produces:
  - `@dataclass PlayerConfig` with `name: str`, `flashscore_id: str`, `country: str`.
  - `load_players(path: str | Path) -> list[PlayerConfig]`.
  - `bootstrap.resolve(names_by_country: dict[str, list[str]]) -> list[dict]` — returns, per input name, `{"query": name, "country": country, "candidates": [PlayerHit-as-dict...]}` (top 3), for human review.

- [ ] **Step 1: Create seed `players.yaml`**

```yaml
players:
  - name: Kevin Ciubotaru
    flashscore_id: O2o2L2iA
    country: Scotland
  - name: Dennis Man
    flashscore_id: ""      # to be filled by bootstrap
    country: Netherlands
```

- [ ] **Step 2: Write the failing test `scraper/tests/test_config.py`**

```python
from pathlib import Path
import textwrap
from config import load_players, PlayerConfig


def test_load_players_parses_yaml(tmp_path: Path):
    p = tmp_path / "players.yaml"
    p.write_text(textwrap.dedent("""
        players:
          - name: Kevin Ciubotaru
            flashscore_id: O2o2L2iA
            country: Scotland
    """))
    players = load_players(p)
    assert players == [PlayerConfig("Kevin Ciubotaru", "O2o2L2iA", "Scotland")]


def test_load_players_skips_unresolved_ids(tmp_path: Path):
    p = tmp_path / "players.yaml"
    p.write_text(textwrap.dedent("""
        players:
          - name: Resolved
            flashscore_id: ABC123
            country: X
          - name: Unresolved
            flashscore_id: ""
            country: Y
    """))
    players = load_players(p)
    assert [pl.name for pl in players] == ["Resolved"]
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd scraper && python -m pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'config'`

- [ ] **Step 4: Implement `scraper/config.py`**

```python
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd scraper && python -m pytest tests/test_config.py -v`
Expected: PASS (2 tests)

- [ ] **Step 6: Implement `scraper/bootstrap.py` (CLI to resolve the roster)**

```python
"""Resolve player names to Flashscore IDs for players.yaml.

Usage:
    python bootstrap.py            # reads roster.txt, writes candidates.yaml
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


def main() -> None:
    roster = parse_roster(open("roster.txt", encoding="utf-8").read())
    resolved = resolve(roster)
    # Emit a players.yaml draft using the top candidate, plus a review file.
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


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 7: Add a unit test for `parse_roster` and run all config tests**

Append to `scraper/tests/test_config.py`:

```python
from bootstrap import parse_roster


def test_parse_roster_groups_by_country():
    text = "# Scotland\nKevin Ciubotaru\n# Netherlands\nDennis Man\n"
    assert parse_roster(text) == {
        "Scotland": ["Kevin Ciubotaru"],
        "Netherlands": ["Dennis Man"],
    }
```

Run: `cd scraper && python -m pytest tests/test_config.py -v`
Expected: PASS (3 tests)

- [ ] **Step 8: Commit**

```bash
git add scraper/config.py scraper/bootstrap.py scraper/tests/test_config.py players.yaml
git commit -m "feat: add roster config loader and bootstrap resolver"
```

> **Setup note (run during Task 8 / final assembly, not now):** paste the user's full 80-player roster into `scraper/roster.txt`, run `python bootstrap.py`, review `candidates.yaml` for ambiguous names (e.g. common surnames), and commit the finalized `players.yaml`.

---

### Task 4 (SPIKE): Discover player-stats, match-log, and team-results feeds

**This is a discovery spike, not TDD.** Its deliverables are (a) the real feed names written into `docs/flashscore-api-notes.md`, and (b) saved response fixtures under `scraper/tests/fixtures/`. Tasks 5–6 depend on these fixtures. Requires Playwright with Chromium; if Chromium cannot run locally, run this step's script in a scratch GitHub Actions job and download the artifacts.

**Files:**
- Create: `scraper/spike_discover.py` (throwaway discovery helper; may be deleted after)
- Modify: `docs/flashscore-api-notes.md` (fill the "NOT yet verified" section)
- Create fixtures: `scraper/tests/fixtures/player_stats_O2o2L2iA.txt`, `scraper/tests/fixtures/player_matches_O2o2L2iA.txt`, `scraper/tests/fixtures/team_results_8QEB2FFp.txt`

- [ ] **Step 1: Install Playwright Chromium**

Run: `cd scraper && pip install -r requirements.txt && python -m playwright install chromium`

- [ ] **Step 2: Write `scraper/spike_discover.py` to capture feed requests**

```python
"""Open Flashscore player/team pages and log every feed XHR + its body."""
import sys
from playwright.sync_api import sync_playwright

TARGETS = {
    "player": "https://www.flashscore.com/player/ciubotaru-kevin/O2o2L2iA/",
    "team": "https://www.flashscore.com/team/dundee-utd/8QEB2FFp/",
}


def run(kind: str) -> None:
    url = TARGETS[kind]
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        captured = []

        def on_response(resp):
            if "/x/feed/" in resp.url:
                try:
                    body = resp.text()
                except Exception:
                    body = ""
                captured.append((resp.url, body))

        page.on("response", on_response)
        page.goto(url, wait_until="networkidle", timeout=60000)
        # click through the player's "Matches" tab if present
        page.wait_for_timeout(3000)
        browser.close()

    for u, body in captured:
        feed = u.rsplit("/x/feed/", 1)[-1]
        print(f"FEED {feed}  ({len(body)} bytes)")
        print(body[:200])
        print("-" * 60)


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "player")
```

- [ ] **Step 3: Run discovery for player and team pages**

Run:
```bash
cd scraper
python spike_discover.py player | tee /tmp/player_feeds.txt
python spike_discover.py team | tee /tmp/team_feeds.txt
```
Identify the feeds carrying: season stats (goals/assists/minutes), the player's match list (with match IDs), and the team's recent results.

- [ ] **Step 4: Save fixtures and document**

For each identified feed, fetch it directly and save the body to the fixture path listed above:
```bash
cd scraper
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
curl -sSL -H "x-fsign: SW9D1eZo" -H "Referer: https://www.flashscore.com/" -A "$UA" \
  "https://global.flashscore.ninja/2/x/feed/<PLAYER_STATS_FEED>" \
  -o tests/fixtures/player_stats_O2o2L2iA.txt
# repeat for player_matches_O2o2L2iA.txt and team_results_8QEB2FFp.txt
```
Then edit `docs/flashscore-api-notes.md`: replace the "NOT yet verified" section with the real feed names, the key codes that carry goals/assists/minutes/match-id/date/score, and note which YouTube/highlight mechanism the match page uses (feed vs DOM selector).

- [ ] **Step 5: Commit**

```bash
git add scraper/tests/fixtures/ docs/flashscore-api-notes.md scraper/spike_discover.py
git commit -m "chore: discover and fixture Flashscore player/team feeds"
```

---

### Task 5: Feed client — player stats, match log, team results

TDD parsers built against the fixtures captured in Task 4. **The exact field codes below (`GOALS_KEY`, etc.) are placeholders you replace with the real codes documented in Task 4** — the test assertions are written against the fixture's known real values (Ciubotaru at Dundee Utd; the St Mirren match on 2026-09-14 scored 2-1 / 3-0 per the fixture).

**Files:**
- Create: `scraper/flashscore/client.py`
- Test: `scraper/tests/test_client.py`

**Interfaces:**
- Consumes: `parse_records`, `labeled_pairs` (Task 1).
- Produces:
  - `@dataclass SeasonStats(goals: int, assists: int, minutes: int)`
  - `@dataclass MatchResult(match_id: str, date: str, home_team: str, away_team: str, score: str)` (`date` ISO `YYYY-MM-DD`)
  - `parse_player_stats(text: str) -> SeasonStats`
  - `parse_match_log(text: str) -> list[MatchResult]` (newest first)
  - `parse_team_results(text: str) -> list[MatchResult]`
  - `fetch_feed(feed: str, session) -> str` — GET `{FEED_HOST}{feed}` with required headers.
  - `FEED_HOST = "https://global.flashscore.ninja/2/x/feed/"`, `FSIGN = "SW9D1eZo"`.

- [ ] **Step 1: Write the failing test `scraper/tests/test_client.py`**

Write tests that load each Task-4 fixture and assert on the parsed dataclasses. Fill the expected numbers from the actual fixture contents you saved (inspect them first). Skeleton:

```python
from pathlib import Path
from flashscore.client import (
    parse_player_stats, parse_match_log, parse_team_results,
    SeasonStats, MatchResult,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_player_stats():
    text = (FIXTURES / "player_stats_O2o2L2iA.txt").read_text(encoding="utf-8")
    stats = parse_player_stats(text)
    assert isinstance(stats, SeasonStats)
    assert stats.goals >= 0 and stats.assists >= 0 and stats.minutes > 0
    # Replace with the exact values visible in the fixture:
    # assert stats == SeasonStats(goals=?, assists=?, minutes=?)


def test_parse_match_log_returns_results_newest_first():
    text = (FIXTURES / "player_matches_O2o2L2iA.txt").read_text(encoding="utf-8")
    results = parse_match_log(text)
    assert results and all(isinstance(r, MatchResult) for r in results)
    dates = [r.date for r in results]
    assert dates == sorted(dates, reverse=True)
    # A known match from the fixture:
    assert any(r.match_id == "jiBADrkI" for r in results)


def test_parse_team_results():
    text = (FIXTURES / "team_results_8QEB2FFp.txt").read_text(encoding="utf-8")
    results = parse_team_results(text)
    assert results and all(len(r.score.split("-")) == 2 for r in results)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd scraper && python -m pytest tests/test_client.py -v`
Expected: FAIL with import error.

- [ ] **Step 3: Implement `scraper/flashscore/client.py`**

Implement using the real field codes from Task 4. Structure:

```python
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
import requests
from .parser import parse_records, labeled_pairs

FEED_HOST = "https://global.flashscore.ninja/2/x/feed/"
FSIGN = "SW9D1eZo"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


@dataclass
class SeasonStats:
    goals: int
    assists: int
    minutes: int


@dataclass
class MatchResult:
    match_id: str
    date: str
    home_team: str
    away_team: str
    score: str


def _epoch_to_iso(epoch: str) -> str:
    return datetime.fromtimestamp(int(epoch), tz=timezone.utc).strftime("%Y-%m-%d")


def parse_player_stats(text: str) -> SeasonStats:
    # Map the real stat-row codes (from Task 4) to goals/assists/minutes.
    ...


def parse_match_log(text: str) -> list[MatchResult]:
    # Each match record exposes an id, an epoch date, both team names, and a score.
    # Convert epoch via _epoch_to_iso; sort newest first.
    ...


def parse_team_results(text: str) -> list[MatchResult]:
    ...


def fetch_feed(feed: str, session: requests.Session) -> str:
    resp = session.get(
        FEED_HOST + feed,
        headers={"x-fsign": FSIGN, "Referer": "https://www.flashscore.com/",
                 "User-Agent": UA},
        timeout=20,
    )
    resp.raise_for_status()
    return resp.text
```

Replace each `...` with parsing logic driven by the fixtures.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd scraper && python -m pytest tests/test_client.py -v`
Expected: PASS. Tighten the `assert stats == SeasonStats(...)` line with real values once green.

- [ ] **Step 5: Commit**

```bash
git add scraper/flashscore/client.py scraper/tests/test_client.py
git commit -m "feat: add Flashscore feed client for player stats and results"
```

---

### Task 6: Highlights extractor (Playwright)

Extracts a YouTube link from a Flashscore match page. Uses the mechanism identified in Task 4. Only invoked for matches whose `youtube_url` is unknown.

**Files:**
- Create: `scraper/highlights.py`
- Test: `scraper/tests/test_highlights.py`

**Interfaces:**
- Produces:
  - `extract_youtube_url(match_id: str) -> str | None` — opens the match page headless, returns a `https://www.youtube.com/...` URL or None.
  - `extract_many(match_ids: list[str], max_pages: int = 1) -> dict[str, str]` — returns only the found ones.

- [ ] **Step 1: Write the test `scraper/tests/test_highlights.py`**

The pure part (URL recognition) is unit-tested; the browser part is a marked network test.

```python
import pytest
from highlights import _is_youtube_url


def test_is_youtube_url_accepts_watch_and_short_forms():
    assert _is_youtube_url("https://www.youtube.com/watch?v=abc123")
    assert _is_youtube_url("https://youtu.be/abc123")


def test_is_youtube_url_rejects_others():
    assert not _is_youtube_url("https://www.flashscore.com/x")
    assert not _is_youtube_url(None)


@pytest.mark.network
def test_extract_youtube_url_smoke():
    from highlights import extract_youtube_url
    # jiBADrkI may or may not have a highlight; just assert it returns str|None
    result = extract_youtube_url("jiBADrkI")
    assert result is None or result.startswith("http")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd scraper && python -m pytest tests/test_highlights.py -v -m "not network"`
Expected: FAIL with import error.

- [ ] **Step 3: Implement `scraper/highlights.py`**

```python
from __future__ import annotations
from playwright.sync_api import sync_playwright

MATCH_URL = "https://www.flashscore.com/match/{match_id}/#/match-summary"


def _is_youtube_url(url: str | None) -> bool:
    if not url:
        return False
    return "youtube.com/watch" in url or "youtu.be/" in url


def extract_youtube_url(match_id: str) -> str | None:
    # Use the DOM selector / feed identified in Task 4.
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        try:
            page.goto(MATCH_URL.format(match_id=match_id),
                      wait_until="networkidle", timeout=60000)
            hrefs = page.eval_on_selector_all(
                "a[href]", "els => els.map(e => e.href)")
            for href in hrefs:
                if _is_youtube_url(href):
                    return href
            return None
        finally:
            browser.close()


def extract_many(match_ids: list[str], max_pages: int = 1) -> dict[str, str]:
    found: dict[str, str] = {}
    for mid in match_ids:
        url = extract_youtube_url(mid)
        if url:
            found[mid] = url
    return found
```

Adjust `MATCH_URL` and the selector to match Task 4 findings (the correct match URL form uses the team slugs + `mid`; if the short form does not resolve, build the URL from the match log's stored `flashscore_url`).

- [ ] **Step 4: Run unit tests to verify they pass**

Run: `cd scraper && python -m pytest tests/test_highlights.py -v -m "not network"`
Expected: PASS (2 unit tests). Run the network smoke test separately where Chromium is available.

- [ ] **Step 5: Commit**

```bash
git add scraper/highlights.py scraper/tests/test_highlights.py
git commit -m "feat: add Playwright YouTube highlight extractor"
```

---

### Task 7: Scraper orchestration → data.json

Ties everything together: load config, fetch each player's stats + results, extract highlights for new matches, merge manual overrides, write `site/data.json`, update `cache.json`. Supports incremental / backfill / highlights-only modes.

**Files:**
- Create: `scraper/scrape.py`
- Create: `links.json` (empty `{}` seed)
- Test: `scraper/tests/test_scrape.py`

**Interfaces:**
- Consumes: `load_players`, `search_players`, `fetch_feed`, `parse_player_stats`, `parse_match_log`/`parse_team_results`, `extract_many`.
- Produces:
  - `merge_youtube(results: list[dict], overrides: dict[str, str], scraped: dict[str, str]) -> list[dict]` — sets each result's `youtube_url`; `overrides` (from `links.json`) wins over `scraped`.
  - `build_player_record(cfg, hit, stats, results) -> dict` — the `data.json` per-player shape from the spec.
  - `main(argv)` with flags `--backfill-from YYYY-MM-DD`, `--highlights-only`.

- [ ] **Step 1: Write the failing test `scraper/tests/test_scrape.py`**

```python
from scrape import merge_youtube, build_player_record
from config import PlayerConfig
from flashscore.search import PlayerHit
from flashscore.client import SeasonStats, MatchResult


def test_merge_youtube_manual_overrides_win():
    results = [{"match_id": "m1", "youtube_url": None},
               {"match_id": "m2", "youtube_url": None}]
    merged = merge_youtube(results, overrides={"m1": "MANUAL"}, scraped={"m1": "AUTO", "m2": "AUTO2"})
    by_id = {r["match_id"]: r["youtube_url"] for r in merged}
    assert by_id["m1"] == "MANUAL"   # override beats scraped
    assert by_id["m2"] == "AUTO2"


def test_build_player_record_shape():
    cfg = PlayerConfig("Kevin Ciubotaru", "O2o2L2iA", "Scotland")
    hit = PlayerHit("O2o2L2iA", "Ciubotaru Kevin", "ciubotaru-kevin",
                    "Defender", "Romania", "Dundee Utd", "8QEB2FFp")
    stats = SeasonStats(2, 1, 430)
    results = [MatchResult("jiBADrkI", "2026-09-14", "St Mirren", "Dundee Utd", "3-0")]
    rec = build_player_record(cfg, hit, stats, results)
    assert rec["name"] == "Kevin Ciubotaru"
    assert rec["team"] == "Dundee Utd"
    assert rec["position"] == "Defender"
    assert rec["country"] == "Scotland"
    assert rec["season_stats"] == {"goals": 2, "assists": 1, "minutes": 430}
    assert rec["results"][0]["match_id"] == "jiBADrkI"
    assert rec["results"][0]["youtube_url"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd scraper && python -m pytest tests/test_scrape.py -v`
Expected: FAIL with import error.

- [ ] **Step 3: Implement `scraper/scrape.py`**

```python
from __future__ import annotations
import argparse
import json
import sys
import time
from dataclasses import asdict
from datetime import date
from pathlib import Path
import requests

from config import load_players, PlayerConfig
from flashscore.search import search_players, PlayerHit
from flashscore.client import (
    fetch_feed, parse_player_stats, parse_team_results, MatchResult,
)
from highlights import extract_many

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "site" / "data.json"
LINKS_PATH = ROOT / "links.json"
CACHE_PATH = Path(__file__).resolve().parent / "cache.json"


def merge_youtube(results, overrides, scraped):
    for r in results:
        mid = r["match_id"]
        r["youtube_url"] = overrides.get(mid) or scraped.get(mid) or r.get("youtube_url")
    return results


def build_player_record(cfg: PlayerConfig, hit: PlayerHit, stats, results) -> dict:
    return {
        "name": cfg.name,
        "flashscore_id": cfg.flashscore_id,
        "country": cfg.country,
        "team": hit.club_name,
        "league": None,
        "position": hit.position,
        "season_stats": asdict(stats),
        "results": [
            {**asdict(r), "flashscore_url":
                f"https://www.flashscore.com/match/{r.match_id}/",
             "youtube_url": None}
            for r in results
        ],
    }


def _load_json(path: Path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backfill-from")
    parser.add_argument("--highlights-only", action="store_true")
    args = parser.parse_args(argv)

    session = requests.Session()
    players = load_players(ROOT / "players.yaml")
    overrides = _load_json(LINKS_PATH, {})
    cache = _load_json(CACHE_PATH, {})
    data = _load_json(DATA_PATH, {"players": []})

    if args.highlights_only:
        # only refresh youtube_url on existing results where it is null
        missing = [r["match_id"] for pl in data["players"] for r in pl["results"]
                   if not r.get("youtube_url")]
        scraped = extract_many(missing)
        for pl in data["players"]:
            merge_youtube(pl["results"], overrides, scraped)
    else:
        records = []
        for cfg in players:
            hit = next((h for h in search_players(cfg.name) if h.id == cfg.flashscore_id), None)
            if hit is None:
                continue
            stats = parse_player_stats(fetch_feed(f"<player_stats_feed>{cfg.flashscore_id}", session))
            results = parse_team_results(fetch_feed(f"<team_results_feed>{hit.club_id}", session))
            if args.backfill_from:
                cutoff = args.backfill_from
                results = [r for r in results if r.date >= cutoff]
            new_ids = [r.match_id for r in results if r.match_id not in cache]
            scraped = extract_many(new_ids)
            rec = build_player_record(cfg, hit, stats, results)
            merge_youtube(rec["results"], overrides, scraped)
            records.append(rec)
            for mid in new_ids:
                cache[mid] = True
            time.sleep(0.3)
        data = {"players": records}

    from datetime import datetime, timezone
    data["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    CACHE_PATH.write_text(json.dumps(cache), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Replace `<player_stats_feed>` / `<team_results_feed>` with the real feed-name templates from Task 4.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd scraper && python -m pytest tests/test_scrape.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Run the full scraper end-to-end for the seed roster**

Run: `cd scraper && python scrape.py --backfill-from 2025-07-01`
Expected: `site/data.json` is written with the seed players and real results. Inspect it.

- [ ] **Step 6: Commit**

```bash
git add scraper/scrape.py scraper/tests/test_scrape.py links.json site/data.json scraper/cache.json
git commit -m "feat: add scraper orchestration writing site/data.json"
```

---

### Task 8: Frontend

Static site rendering `data.json` grouped by country, with collapsible sections, per-player cards, last-5-with-show-all, YouTube links, and a Refresh Highlights button.

**Files:**
- Create: `site/index.html`
- Create: `site/app.js`
- Create: `site/styles.css`
- Create: `site/data.sample.json` (fixture so the UI can be built before the scraper runs)
- Test: manual browser verification

**Interfaces:**
- Consumes: `site/data.json` (shape from spec / Task 7 `build_player_record`).

- [ ] **Step 1: Create `site/data.sample.json`**

```json
{
  "updated_at": "2026-09-21T06:00:00Z",
  "players": [
    {"name": "Kevin Ciubotaru", "flashscore_id": "O2o2L2iA", "country": "Scotland",
     "team": "Dundee Utd", "league": "Scottish Premiership", "position": "Defender",
     "season_stats": {"goals": 2, "assists": 1, "minutes": 430},
     "results": [
       {"match_id": "jiBADrkI", "date": "2026-09-14", "home_team": "St Mirren",
        "away_team": "Dundee Utd", "score": "3-0",
        "flashscore_url": "https://www.flashscore.com/match/jiBADrkI/",
        "youtube_url": "https://www.youtube.com/watch?v=demo"}
     ]}
  ]
}
```

- [ ] **Step 2: Create `site/index.html`**

```html
<!doctype html>
<html lang="ro">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Jucători Români în Lume</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <header>
    <h1>🇷🇴 Jucători Români în Lume</h1>
    <div class="meta">
      <span id="updated"></span>
      <button id="refresh">↻ Refresh Highlights</button>
    </div>
  </header>
  <main id="app">Loading…</main>
  <script src="app.js"></script>
</body>
</html>
```

- [ ] **Step 3: Create `site/styles.css`**

Responsive grid, cards, position badge, collapsible sections. Keep it self-contained (no CDN). Minimum: `.country{}`, `.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}`, `.card{}`, `.badge{}`, `.result{}`, `.result a{}`.

- [ ] **Step 4: Create `site/app.js`**

```javascript
const DATA_URL = "./data.json";

function fmtStats(s) { return `${s.goals}G / ${s.assists}A / ${s.minutes}'`; }

function resultRow(r) {
  const yt = r.youtube_url
    ? ` <a href="${r.youtube_url}" target="_blank" rel="noopener" title="Highlights">▶</a>`
    : "";
  return `<div class="result"><span>${r.date}</span> `
       + `<span>${r.home_team} ${r.score} ${r.away_team}</span>`
       + `<a href="${r.flashscore_url}" target="_blank" rel="noopener">↗</a>${yt}</div>`;
}

function card(p) {
  const shown = p.results.slice(0, 5).map(resultRow).join("");
  const rest = p.results.slice(5).map(resultRow).join("");
  const toggle = p.results.length > 5
    ? `<button class="showall">show all (${p.results.length})</button>
       <div class="more" hidden>${rest}</div>` : "";
  return `<div class="card">
    <div class="name">${p.name}</div>
    <div class="sub">${p.team ?? "—"} · <span class="badge">${p.position ?? "?"}</span></div>
    <div class="stats">${fmtStats(p.season_stats)}</div>
    <hr>${shown}${toggle}</div>`;
}

function render(data) {
  document.getElementById("updated").textContent =
    "Updated: " + new Date(data.updated_at).toLocaleString("ro-RO");
  const byCountry = {};
  for (const p of data.players) (byCountry[p.country] ??= []).push(p);
  const app = document.getElementById("app");
  app.innerHTML = Object.entries(byCountry).map(([country, players]) => {
    const open = localStorage.getItem("c:" + country) !== "closed";
    return `<section class="country" data-country="${country}">
      <h2 class="toggle">${open ? "▾" : "▸"} ${country} (${players.length})</h2>
      <div class="grid" ${open ? "" : "hidden"}>${players.map(card).join("")}</div>
    </section>`;
  }).join("");
}

document.addEventListener("click", (e) => {
  if (e.target.classList.contains("showall")) {
    const more = e.target.nextElementSibling;
    more.hidden = !more.hidden;
    e.target.textContent = more.hidden ? `show all` : "show less";
  }
  if (e.target.classList.contains("toggle")) {
    const section = e.target.closest(".country");
    const grid = section.querySelector(".grid");
    grid.hidden = !grid.hidden;
    e.target.textContent = (grid.hidden ? "▸ " : "▾ ")
      + e.target.textContent.slice(2);
    localStorage.setItem("c:" + section.dataset.country, grid.hidden ? "closed" : "open");
  }
});

document.getElementById("refresh").addEventListener("click", triggerHighlights);

async function triggerHighlights() { /* filled in Task 9 */ }

fetch(DATA_URL).then(r => r.ok ? r.json() : fetch("./data.sample.json").then(x => x.json()))
  .then(render)
  .catch(() => { document.getElementById("app").textContent = "Failed to load data."; });
```

- [ ] **Step 5: Verify in a browser**

Run: `cd site && python -m http.server 8080`
Open `http://localhost:8080/`. With no `data.json` yet it falls back to `data.sample.json`. Confirm: country sections render and collapse (state persists on reload), cards show name/team/position/stats, the ▶ link opens YouTube, the ↗ link opens Flashscore, and "show all" works when >5 results. Resize to mobile width — grid collapses to one column with no horizontal scroll.

- [ ] **Step 6: Commit**

```bash
git add site/index.html site/app.js site/styles.css site/data.sample.json
git commit -m "feat: add static frontend rendering data.json by country"
```

---

### Task 9: GitHub Actions + Pages + Refresh button wiring

Automates the daily scrape and the manual highlights refresh, and wires the frontend button to trigger the highlights workflow.

**Files:**
- Create: `.github/workflows/scrape.yml`
- Create: `.github/workflows/highlights.yml`
- Modify: `site/app.js` (implement `triggerHighlights`)
- Create: `README.md` (setup + secrets instructions)

- [ ] **Step 1: Create `.github/workflows/scrape.yml`**

```yaml
name: Daily scrape
on:
  schedule:
    - cron: "0 6 * * *"
  workflow_dispatch:
    inputs:
      backfill_from:
        description: "Backfill from YYYY-MM-DD (blank = incremental)"
        required: false
        default: ""
permissions:
  contents: write
jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -r scraper/requirements.txt
      - run: python -m playwright install --with-deps chromium
      - name: Scrape
        working-directory: scraper
        run: |
          if [ -n "${{ inputs.backfill_from }}" ]; then
            python scrape.py --backfill-from "${{ inputs.backfill_from }}"
          else
            python scrape.py
          fi
      - name: Commit data
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add site/data.json scraper/cache.json
          git diff --staged --quiet || git commit -m "data: daily update $(date -u +%FT%TZ)"
          git push
```

- [ ] **Step 2: Create `.github/workflows/highlights.yml`**

```yaml
name: Refresh highlights
on:
  workflow_dispatch: {}
permissions:
  contents: write
jobs:
  highlights:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -r scraper/requirements.txt
      - run: python -m playwright install --with-deps chromium
      - name: Extract highlights only
        working-directory: scraper
        run: python scrape.py --highlights-only
      - name: Commit data
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add site/data.json scraper/cache.json
          git diff --staged --quiet || git commit -m "data: highlights refresh $(date -u +%FT%TZ)"
          git push
```

- [ ] **Step 3: Implement `triggerHighlights` in `site/app.js`**

The button uses a fine-grained PAT (scope: `actions: write` on this repo only) injected at scrape time. Add to `build`/data output a top-level `repo` field, OR hardcode `OWNER/REPO`. Implementation:

```javascript
async function triggerHighlights() {
  const btn = document.getElementById("refresh");
  const OWNER_REPO = "OWNER/REPO";      // set to your repo
  const token = window.__GH_TOKEN__;    // injected; if absent, link out instead
  if (!token) {
    window.open(`https://github.com/${OWNER_REPO}/actions/workflows/highlights.yml`, "_blank");
    return;
  }
  btn.disabled = true; btn.textContent = "Triggering…";
  try {
    const res = await fetch(
      `https://api.github.com/repos/${OWNER_REPO}/actions/workflows/highlights.yml/dispatches`,
      { method: "POST",
        headers: { "Authorization": `Bearer ${token}`,
                   "Accept": "application/vnd.github+json" },
        body: JSON.stringify({ ref: "main" }) });
    btn.textContent = res.ok ? "Refresh triggered ✓ (~5 min)" : "Trigger failed";
  } catch { btn.textContent = "Trigger failed"; }
  finally { setTimeout(() => { btn.disabled = false; btn.textContent = "↻ Refresh Highlights"; }, 5000); }
}
```

For the token: the simplest secure-enough option for a private repo is to write `window.__GH_TOKEN__` into a git-ignored `site/token.js` locally, OR have `scrape.py` emit it from the `GH_ACTIONS_TOKEN` secret into `data.json`. Default to the **link-out fallback** (no token) unless the user opts in — document both in the README.

- [ ] **Step 4: Create `README.md`**

Document: repo setup, `players.yaml` bootstrap (`bootstrap.py`), enabling GitHub Pages (Settings → Pages → Source: `main`, folder `/site`), the optional `GH_ACTIONS_TOKEN` fine-grained PAT for the refresh button, running an initial backfill via workflow_dispatch, and how to add a manual YouTube link to `links.json`.

- [ ] **Step 5: Verify workflows lint**

Run: `python -c "import yaml,glob; [yaml.safe_load(open(f)) for f in glob.glob('.github/workflows/*.yml')]; print('workflows valid')"`
Expected: `workflows valid`

- [ ] **Step 6: Commit**

```bash
git add .github/workflows/ site/app.js README.md
git commit -m "feat: add scrape/highlights workflows and refresh button wiring"
```

---

## Final Assembly (after all tasks)

- [ ] Populate the full 80-player roster: paste the user's list into `scraper/roster.txt`, run `python bootstrap.py`, review `candidates.yaml` for ambiguous names, finalize `players.yaml`, commit.
- [ ] Run a full backfill via `scrape.yml` workflow_dispatch (`backfill_from: 2024-09-01` or chosen date).
- [ ] Enable GitHub Pages (Source `main`, `/site`), verify the live URL loads.
- [ ] Spot-check 3–4 players across different leagues (a big league like Turkey, a niche one like Cambodia) for correct stats and results.

---

## Self-Review Notes

- **Spec coverage:** grouped-by-country UI (Task 8) ✓; G/A/minutes/position (Tasks 2,5,7,8) ✓; team results (Task 5,7) ✓; YouTube links auto + manual override (Tasks 6,7) ✓; transfer-aware via re-fetched club (Task 2,7) ✓; backfill flag (Task 7) ✓; daily + highlights workflows + Pages (Task 9) ✓; refresh button (Task 9) ✓.
- **Known risk:** Tasks 5–6 depend on feed names discovered in the Task 4 spike; their parser bodies are intentionally left to be filled from real fixtures (documented, not placeholder-hidden). If the feed API proves unusable, the fallback is to scrape player/team pages via Playwright DOM in `client.py` — same interfaces, different internals.
- **Playwright locally:** the network/browser tests (Tasks 4, 6) may need to run in CI if Chromium can't launch in the dev sandbox; unit tests for every task run without network.
