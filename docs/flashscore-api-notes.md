# Flashscore API Notes (reverse-engineered)

> These are undocumented endpoints verified empirically on 2026-09-21.
> Flashscore may change them without notice. Treat feed names as
> discovery targets, not contracts. When a feed breaks, re-run the
> Playwright network-capture spike (see the implementation plan, Task 1).

## Verified: Search API (JSON) ✅

Resolves a player name → stable player ID, position, nationality, and
current club. This is the source of truth for the config-setup tooling
and for transfer detection (it reflects the player's current club).

```
GET https://s.livesport.services/api/v2/search/
      ?q={query}
      &lang-id=1
      &project-id=2
      &project-type-id=1
      &sport-ids=1
      &type-ids=1,2,3,4
Headers: Referer: https://www.flashscore.com/   (User-Agent: normal browser)
```

Response: JSON array of matches. Filter to `type.name == "PlayerInTeam"`.

Relevant fields per result:
- `id` — stable player ID (e.g. `O2o2L2iA` for Kevin Ciubotaru)
- `url` — slug (e.g. `ciubotaru-kevin`)
- `name` — "Ciubotaru Kevin" (surname-first)
- `participantTypes` — e.g. `[{id:2,name:"Player"},{id:13,name:"Defender"}]`
  → the non-"Player" entry is the **position** (Goalkeeper/Defender/Midfielder/Forward)
- `defaultCountry.name` — nationality (e.g. "Romania")
- `teams` — array; the entry with `kind == "TEAM"` (participantType "Team")
  is the **current club**: `{id:"8QEB2FFp", name:"Dundee Utd", kind:"TEAM"}`.
  Entries with `kind == "NOMINATION"` are national-team call-ups — ignore.

The club `id` (e.g. `8QEB2FFp`) also appears in match URLs and is the key
for team-results feeds.

## Verified: Match feeds (pipe-delimited) ✅

Host + auth that works:
```
https://global.flashscore.ninja/2/x/feed/{FEED}
  (mirror: https://local-global.flashscore.ninja/2/x/feed/{FEED})
Header REQUIRED: x-fsign: SW9D1eZo
Header: Referer: https://www.flashscore.com/
```

NOTE: the older `https://d.flashscore.com/x/feed/...` host now returns a
1-byte body — do **not** use it. Use the `*.flashscore.ninja` host.

Confirmed working match feeds (for match id `jiBADrkI`):
- `df_sur_1_{matchId}` — match summary: referee, venue, town, attendance, capacity
- `dc_1_{matchId}` — match detail header: timestamps, status, stage
- `df_st_1_{matchId}` — match statistics (possession, shots, etc.)
- `df_ln_1_{matchId}` — lineups (often EMPTY [1 byte] for lower leagues)

### Response format

Pipe-delimited key-value text, not JSON:
- Field separator: `¬`
- Key/value separator: `÷`
- Row/record separator: `~`

Example (`df_sur`): `MIT÷VEN¬MIV÷The SMISA Stadium¬MIT÷TWN¬MIV÷Paisley¬...`
Here `MIT` is a label key and `MIV` its value, so this reads as pairs:
VEN=The SMISA Stadium, TWN=Paisley, etc.

Parse strategy: split on `~` into records, split each on `¬` into fields,
split each field on the first `÷` into (key, value).

## Verified: Player data is embedded in the player page HTML ✅

The player page does NOT use per-player `/x/feed/` calls for its data —
the whole dataset is embedded in the initial HTML as a JSON blob:

```
GET https://www.flashscore.com/player/{slug}/{playerId}/
Headers: Referer + normal User-Agent   (no x-fsign needed; plain HTML)
```

Extract with a regex:
`window.playerProfilePageEnvironment\s*=\s*(\{.*?\})\s*;\s*\n`

Useful keys in that object:
- `careerTables` — list of tables (`table_id` ∈ league / nacional-cup /
  international-cups / national-team). The **league** table's `seasons[0]`
  is the current season row, with: `tournament_name` (league), `flag_name`
  (country), `season_name`, `matches_played`, `goals`, `assists`,
  `avg_fs_rating`, `team_name`, `url` (team), `team_id`. Missing numbers
  come through as `"-"` — coerce to 0.
- `lastMatchesData.lastMatches` — recent matches, each with:
  `eventEncodedId` (8-char match id), `eventStartTime` ("DD.MM.YY"),
  `homeParticipantName`/`awayParticipantName`, `homeScore`/`awayScore`,
  `tournamentTitle` (e.g. "Premiership (Scotland)"), `winLoseShort`
  (W/D/L), `rating`, and `stats` — a dict of `{type, value}` where
  `type == "minutes-played"` gives e.g. "90'" and `type == "goal"` gives
  the player's goals in that match. (Assists that are 0 show as
  `type == "grey"`, so per-match assists are unreliable; use the season
  `assists` from careerTables instead.)

No minutes field exists at season level — we sum per-match minutes over
recent league matches as a best-effort "minutes" figure.

## Verified: YouTube highlights feed ✅

```
GET https://global.flashscore.ninja/2/x/feed/df_hi_1_{matchId}
Header REQUIRED: x-fsign: SW9D1eZo   + Referer
```

Pipe-delimited. `HUO` = YouTube watch URL, `HUR` = embed URL,
`HHV` = provider ("YouTube"), `HTI` = title. A match with no highlight
returns HTTP 404 (HTML error body). Works over plain HTTP — no browser.

## Consequence: no browser needed

Player stats+matches (player page HTML), position/club/nationality
(search API), and highlights (`df_hi` feed) are all plain HTTP. Playwright
was used only for one-time discovery and is NOT a runtime dependency.

## Still open (future): deep backfill

`lastMatchesData` has `hasMoreLastMatches`/`rowsLimitNext` (pagination for
older matches); the exact "load more" feed was not pinned down. Recent
matches cover the primary view; multi-year backfill is a future addition.
