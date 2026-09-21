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

## NOT yet verified — discover via Playwright network capture (plan Task 1)

The following are needed but their exact feed names were not found by
guessing. Open the relevant Flashscore page in Playwright, capture the
XHR requests to `*.flashscore.ninja/.../x/feed/`, and record the feed
name + a saved response fixture:

1. **Player season stats** (goals, assists, minutes for current season)
   — open `https://www.flashscore.com/player/{slug}/{playerId}/`
2. **Player match log** (list of the player's matches with match IDs)
   — same player page, "Matches" tab
3. **Team results/fixtures** (a club's recent results, each with a match ID)
   — open `https://www.flashscore.com/team/{slug}/{teamId}/`

## YouTube highlight extraction — verify in Task 1

On a match page, Flashscore may embed a highlights/video link. Determine
via Playwright whether it appears in a feed (e.g. a `_hl_`/video feed) or
only in the rendered DOM, and record the selector or feed. Expect it to
be absent for many lower-tier leagues.
