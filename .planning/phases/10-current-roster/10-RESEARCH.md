# Phase 10: Current Roster - Research

**Researched:** 2026-04-08
**Domain:** Discord bot roster management with CFBD/CBBD API integration
**Confidence:** HIGH

## Summary

Phase 10 adds bulk roster import for KU football and basketball via `/roster-import` and a `/roster-list` display command. The implementation follows established patterns from Phases 7-9 almost exactly -- a new `RecruitingStore` instance for `data/roster.json`, the same `PlayerEntry` dataclass (extended with `jersey_number` and `class_year` fields), and the same stats-on-add pattern from Phase 9.

The key new work is the bulk import logic: calling CFBD `TeamsApi.get_roster(team="Kansas", year=CURRENT)` for football and CBBD `GET /roster?team=Kansas&season=CURRENT` for basketball, iterating over all returned players, creating `PlayerEntry` objects, and fetching stats for each. The CFBD roster returns `Player` objects with `first_name`, `last_name`, `jersey`, `position`, `year` (class). The CBBD roster returns objects with `name`, `jersey`, `position`, `start_season` (class year must be derived). The career command must also be updated to search the roster store.

**Primary recommendation:** Follow the exact transfer-command pattern (transfers.py) for command structure, use existing stats fetch functions for the per-player stats loop, and extend PlayerEntry with two backward-compatible optional fields.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Bulk import from API -- a `/roster-import` command pulls the full KU roster from CFBD (football) or CBBD (basketball) in one shot
- **D-02:** Replace mode -- each import wipes the current roster for that sport and replaces with fresh API data
- **D-03:** Stats fetched for every player during import -- same add-time pattern as Phase 9. For an 85-player football roster this means ~85 API calls, but it's a one-time operation
- **D-04:** Current season only -- no year/season parameter, always imports the latest roster
- **D-05:** Editors + Admins can run /roster-import (same permission as /recruit-add, /transfer-add)
- **D-06:** Two commands only: `/roster-import` and `/roster-list`. No add/remove since import replaces everything
- **D-07:** Ephemeral "Importing..." response, then a final ephemeral embed with results (count summary like "Imported 85 players, fetched stats for 82")
- **D-08:** Sport derived from channel (Phase 7 D-16 carries forward). No sport parameter
- **D-09:** Separate `data/roster.json` file with its own RecruitingStore instance. Same pattern as recruits.json and transfers.json
- **D-10:** Reuse existing `PlayerEntry` dataclass -- name, position, stars (0 for unrated), stats. Jersey number stored in a new field on PlayerEntry
- **D-11:** School field not needed for roster players (always Kansas) -- roster entries can have school as empty string
- **D-12:** `/career` searches all three stores (recruit, transfer, roster) to find player stats
- **D-13:** `/roster-list` displays players alphabetically by name
- **D-14:** Multi-embed split for large rosters -- auto-split at 25 fields per embed, all sent in one response. Same pattern as recruit/transfer lists
- **D-15:** Each player displays: Name + Position + Jersey # + Class (e.g., "John Smith -- QB #7 (Jr.)")

### Claude's Discretion
- How to handle API failures during bulk import (partial import handling, retry logic)
- Jersey number and class year field additions to PlayerEntry (field names, types, defaults for backward compat)
- How to resolve CBBD player IDs for roster lookup (existing pattern in basketball.py)
- Embed formatting details for roster list display
- Error message wording for import failures and empty rosters

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

## Architecture Patterns

### Existing Project Structure (relevant files)
```
src/bot/
  commands/
    recruiting.py     # recruit-add/remove/list commands
    transfers.py      # transfer-add/remove/list commands
    career.py         # /stats command (searches recruit + transfer stores)
    roster.py         # NEW: roster-import and roster-list commands
  stats/
    football.py       # fetch_football_stats() -- reuse for roster import
    basketball.py     # fetch_basketball_stats() -- reuse for roster import
  storage/
    models.py         # PlayerEntry dataclass -- extend with jersey_number, class_year
    recruiting_store.py  # RecruitingStore class -- instantiate for roster
  client.py           # Bot setup -- add roster_store, register roster commands
data/
  recruits.json
  transfers.json
  roster.json         # NEW: roster persistence
```

### Pattern 1: PlayerEntry Extension (Backward Compatible)
**What:** Add `jersey_number` and `class_year` as optional fields with defaults
**When to use:** Extending a shared dataclass without breaking existing data files

Current `PlayerEntry` fields: `name`, `position`, `school`, `stars`, `added_at`, `type`, `stats`

New fields to add:
```python
jersey_number: int = 0       # 0 means unknown/not applicable
class_year: str = ""          # "Fr.", "So.", "Jr.", "Sr.", "R-Fr.", etc. Empty = unknown
```

**Why this works:** `PlayerEntry.from_dict()` already uses `__dataclass_fields__` filtering, so old JSON files without these fields will load fine (defaults apply). The `to_dict()` method needs updating to include the new fields.

### Pattern 2: Bulk Import with Replace Semantics
**What:** Wipe sport roster, rebuild from API response, fetch stats per player
**When to use:** `/roster-import` command

```python
async def do_roster_import(bot, sport: str, interaction):
    # 1. Fetch roster from API
    players = await fetch_roster_from_api(bot.settings, sport)
    
    # 2. Replace: clear current roster for this sport
    bot.roster_store._data[sport] = []
    
    # 3. Add each player and fetch stats
    stats_success = 0
    for p in players:
        entry = PlayerEntry(
            name=p["name"], position=p["position"],
            school="", stars=0, jersey_number=p["jersey"],
            class_year=p["class_year"], type="roster",
        )
        # Fetch stats (fire-and-forget per D-03/Phase 9 pattern)
        try:
            stats = await fetch_stats(bot.settings, sport, p["name"], "Kansas")
            if stats:
                entry.stats = stats
                stats_success += 1
        except Exception:
            pass
        bot.roster_store._data[sport].append(entry)
    
    # 4. Save once at the end (not per player)
    bot.roster_store.save()
    return len(players), stats_success
```

**Key insight:** Save once after all players are added, not per player. The existing `add_player()` calls `save()` after each add -- for 85 players that's 85 disk writes. Direct `_data` manipulation with a single `save()` at the end is correct for bulk operations.

### Pattern 3: Career Command Integration
**What:** Add roster store to the search chain in career.py
**When to use:** `/stats` command player lookup

```python
# In career.py stats command -- add roster_store
all_players = (
    bot.recruit_store.list_players(sport)
    + bot.transfer_store.list_players(sport)
    + bot.roster_store.list_players(sport)  # NEW
)
```

Also update the autocomplete callback the same way.

### Anti-Patterns to Avoid
- **Calling add_player() in a loop:** Each call triggers save(). For 85 players = 85 JSON writes. Manipulate `_data` directly and save once.
- **Blocking on stats fetch per player sequentially:** 85 sequential API calls will take minutes. Consider batching or accepting sequential with progress updates.
- **Not deferring the interaction:** Import will take 30+ seconds for football. Must defer with ephemeral response immediately.

## API Response Shapes

### CFBD Roster (Football)
**Method:** `cfbd.TeamsApi.get_roster(team="Kansas", year=2026)`
**Returns:** `list[Player]` where each Player has:

| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Player ID |
| `first_name` | str | First name |
| `last_name` | str | Last name |
| `jersey` | int | Jersey number |
| `position` | str | Position (QB, WR, etc.) |
| `year` | int | Class year (1=Fr, 2=So, 3=Jr, 4=Sr, 5=R-Sr) |
| `height` | int | Height in inches |
| `weight` | int | Weight in pounds |
| `team` | str | Team name |
| `home_city` | str | Hometown city |
| `home_state` | str | Hometown state |

**Confidence:** HIGH -- verified from installed cfbd package introspection

**Class year mapping for football:**
```python
YEAR_MAP = {1: "Fr.", 2: "So.", 3: "Jr.", 4: "Sr.", 5: "R-Sr."}
```

### CBBD Roster (Basketball)
**Endpoint:** `GET /roster?team=Kansas&season=2026`
**Returns:** JSON array where each object has:

| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Player ID |
| `name` | str | Full name |
| `first_name` | str | First name |
| `last_name` | str | Last name |
| `jersey` | str | Jersey number (string!) |
| `position` | str | Position (G, F, C, etc.) |
| `height` | float | Height |
| `weight` | float | Weight |
| `start_season` | float | Season they started (derive class from this) |

**Confidence:** HIGH -- verified from CBBD GitHub docs (TeamRosterPlayer model)

**Class year derivation for basketball:**
```python
# CBBD has start_season but no explicit class_year
# Derive: current_year - start_season + 1 = years in school
import datetime
current_year = datetime.datetime.now().year
years_in = current_year - int(player["start_season"]) + 1
YEAR_MAP = {1: "Fr.", 2: "So.", 3: "Jr.", 4: "Sr."}
class_year = YEAR_MAP.get(years_in, "Sr." if years_in > 4 else "Fr.")
```

**Important difference:** CBBD jersey is a string, CFBD jersey is an int. Normalize to int in PlayerEntry.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON persistence | Custom file I/O | Existing `RecruitingStore` | Already handles atomic writes, load, save, sport separation |
| Stats fetching | New API client | Existing `fetch_football_stats()` / `fetch_basketball_stats()` | Already handles auth, error handling, response parsing |
| Permission checks | New decorator | Existing `is_recruiting_editor()` pattern | Same editor+admin check from transfers.py |
| Sport resolution | Manual channel mapping | Existing `get_sport_from_channel()` | Already reads config |
| Multi-embed split | Custom pagination | Existing pattern from transfers.py | Just adapt embed field count threshold |

## Common Pitfalls

### Pitfall 1: Discord Interaction Timeout
**What goes wrong:** `/roster-import` takes 2+ minutes for 85 football players with stats. Discord interactions timeout after 15 minutes, but the initial response must happen within 3 seconds.
**Why it happens:** Sequential API calls for stats (85 players x ~1-2 seconds each = 85-170 seconds).
**How to avoid:** `await interaction.response.defer(ephemeral=True)` immediately. Then do all work. Then `edit_original_response()` with results. The existing pattern in transfers.py already does this.
**Warning signs:** "Unknown interaction" or "Interaction expired" errors.

### Pitfall 2: CFBD Rate Limiting (1000 calls/month)
**What goes wrong:** Each football roster import triggers ~85 stats fetches, each of which calls `get_player_season_stats` up to 7 times per category (3 categories x 7 years = 21 calls per player worst case). 85 players x 21 = 1,785 API calls for one import.
**Why it happens:** The `fetch_football_stats` function searches by team+year+category, iterating over 7 years and 3 categories.
**How to avoid:** The stats fetch has an early exit (2 consecutive empty years), which helps. But a full football roster import could still use a large chunk of the monthly budget. Consider: (1) warning the user about API usage, (2) making stats fetch optional for roster import, or (3) accepting the cost since imports are infrequent.
**Warning signs:** 403 errors from CFBD API.

### Pitfall 3: Saving Per-Player Instead of Per-Batch
**What goes wrong:** Using `add_player()` in a loop causes 85 JSON writes.
**Why it happens:** `add_player()` auto-saves after each mutation.
**How to avoid:** Directly manipulate `_data[sport]` list and call `save()` once at the end.
**Warning signs:** Slow import, excessive disk I/O.

### Pitfall 4: CBBD Jersey Number is String
**What goes wrong:** Jersey number stored inconsistently -- int from CFBD, string from CBBD.
**Why it happens:** Different API response types.
**How to avoid:** Normalize to int during import. Use `int(jersey)` with a try/except for non-numeric values (some players may have no jersey number).

### Pitfall 5: Player Name Format Differences
**What goes wrong:** CFBD returns `first_name` + `last_name` separately; CBBD returns `name` as full name. Stats lookups later may fail if name format doesn't match what stats APIs expect.
**Why it happens:** Different API conventions.
**How to avoid:** For CFBD, concatenate as `f"{first_name} {last_name}"`. For CBBD, use `name` directly. Both stats functions already accept full name strings.

### Pitfall 6: Empty Roster Response
**What goes wrong:** API returns empty roster (offseason, wrong team name, API issue). User runs import and wipes existing roster with nothing.
**Why it happens:** Replace mode (D-02) clears first.
**How to avoid:** Check if API returned players BEFORE clearing existing data. If API returns 0 players, abort and report error rather than wiping the roster.

## Code Examples

### CFBD Roster Fetch
```python
# Source: cfbd SDK introspection + existing football.py pattern
import cfbd
from datetime import datetime

async def fetch_football_roster(settings) -> list[dict]:
    if not settings.cfbd_api_key:
        return []
    configuration = cfbd.Configuration()
    configuration.api_key["Authorization"] = f"Bearer {settings.cfbd_api_key}"
    
    with cfbd.ApiClient(configuration) as api_client:
        teams_api = cfbd.TeamsApi(api_client)
        year = datetime.now().year
        roster = teams_api.get_roster(team="Kansas", year=year)
        
        YEAR_MAP = {1: "Fr.", 2: "So.", 3: "Jr.", 4: "Sr.", 5: "R-Sr."}
        return [
            {
                "name": f"{p.first_name} {p.last_name}",
                "position": p.position or "ATH",
                "jersey_number": p.jersey or 0,
                "class_year": YEAR_MAP.get(p.year, ""),
            }
            for p in roster
        ]
```

### CBBD Roster Fetch
```python
# Source: existing basketball.py _cbbd_get pattern + CBBD docs
import aiohttp
from datetime import datetime

CBBD_BASE_URL = "https://api.collegebasketballdata.com"

async def fetch_basketball_roster(settings) -> list[dict]:
    if not settings.cbbd_api_key:
        return []
    headers = {"Authorization": f"Bearer {settings.cbbd_api_key}"}
    year = datetime.now().year
    YEAR_MAP = {1: "Fr.", 2: "So.", 3: "Jr.", 4: "Sr."}
    
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(
            f"{CBBD_BASE_URL}/roster",
            params={"team": "Kansas", "season": year},
        ) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
        
        return [
            {
                "name": p.get("name", f"{p.get('first_name', '')} {p.get('last_name', '')}"),
                "position": p.get("position", ""),
                "jersey_number": int(p.get("jersey", 0) or 0),
                "class_year": YEAR_MAP.get(
                    year - int(p.get("start_season", year)) + 1, "Sr."
                ),
            }
            for p in data
        ]
```

### Roster List Embed (D-14, D-15)
```python
# Adapted from transfers.py pattern
MAX_FIELDS_PER_EMBED = 25  # D-14

def build_roster_embeds(players, sport):
    emoji = SPORT_EMOJI.get(sport, "")
    title = f"{emoji} KU {sport.title()} Roster"
    embeds = []
    current = discord.Embed(title=title, color=KU_BLUE)
    count = 0
    
    for p in sorted(players, key=lambda x: x.name):  # D-13: alphabetical
        if count >= MAX_FIELDS_PER_EMBED:
            embeds.append(current)
            current = discord.Embed(title=f"{title} (cont.)", color=KU_BLUE)
            count = 0
        
        jersey = f"#{p.jersey_number}" if p.jersey_number else ""
        class_yr = f"({p.class_year})" if p.class_year else ""
        # D-15: "John Smith -- QB #7 (Jr.)"
        field_name = f"{p.name} -- {p.position} {jersey} {class_yr}".strip()
        current.add_field(name=field_name, value="\u200b", inline=False)
        count += 1
    
    embeds.append(current)
    return embeds
```

## Discretion Recommendations

### API Failure Handling During Bulk Import
**Recommendation:** Import all players regardless of stats fetch failures. Track successes/failures and report in the summary embed: "Imported 85 players. Stats loaded for 78, failed for 7." Never abort the entire import because some stats failed -- the player data itself (name, position, jersey) is already valuable. This matches the Phase 9 "fire-and-forget" pattern (D-09 context: stats fetch failure never blocks player addition).

### Jersey Number and Class Year Fields
**Recommendation:**
- `jersey_number: int = 0` -- 0 means unknown, display as empty in that case
- `class_year: str = ""` -- empty means unknown, display as empty
- Update `to_dict()` to always include both fields (they have defaults so omission in old data is fine)

### Empty Roster Safety Check
**Recommendation:** If the API returns 0 players, do NOT wipe the existing roster. Instead, return an error: "API returned no players for Kansas {sport}. The existing roster has been preserved. This may be an offseason issue -- try again later."

### Progress Feedback During Long Imports
**Recommendation:** For football (85+ players), edit the deferred response partway through: "Importing... 42/85 players processed" at ~50% mark. This reassures the user the bot isn't hung. Use `interaction.edit_original_response()` -- it can be called multiple times.

## Sources

### Primary (HIGH confidence)
- `cfbd` Python package -- introspected locally, `Player` model fields verified: first_name, last_name, jersey, position, year, id, team, height, weight
- `cfbd.TeamsApi.get_roster()` -- verified via `help()` on installed package: params are team (str), year (int)
- CBBD TeamRosterPlayer model -- GitHub docs: id, name, first_name, last_name, jersey, position, height, weight, start_season, end_season
- Existing codebase: models.py, recruiting_store.py, transfers.py, career.py, football.py, basketball.py, client.py -- all read and analyzed

### Secondary (MEDIUM confidence)
- [CFBD Python SDK GitHub](https://github.com/CFBD/cfbd-python) -- API patterns and usage
- [CBBD Python SDK GitHub](https://github.com/CFBD/cbbd-python) -- TeamRosterPlayer model docs
- [CollegeBasketballData.com](https://collegebasketballdata.com/) -- API key and rate limit info

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already installed and in use (cfbd, aiohttp, discord.py)
- Architecture: HIGH -- follows established Phase 7-9 patterns exactly
- API shapes: HIGH (football) / HIGH (basketball) -- verified from SDK introspection and GitHub docs
- Pitfalls: HIGH -- derived from reading actual codebase and understanding API rate limits

**Research date:** 2026-04-08
**Valid until:** 2026-05-08 (stable -- APIs and SDK unlikely to change)
