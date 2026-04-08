# Phase 9: Career Stats - Research

**Researched:** 2026-04-08
**Domain:** Sports data API integration, monospace table formatting, fuzzy name matching
**Confidence:** HIGH

## Summary

This phase adds a `/career` command that displays per-season college stats for players on the recruiting and transfer lists, plus freeform name fallback. The core challenge splits into two parts: (1) fetching stats from CFBD (football) and CBBD (basketball) APIs at player-add time, and (2) formatting those stats into sport-appropriate monospace code-block tables in Discord embeds.

Both APIs use Bearer token auth and have auto-generated Python SDKs (`cfbd` v5.13.2, `cbbd` v1.26.3). CFBD returns stats as flat rows with `category`/`stat_type`/`stat` fields that must be assembled per-player. CBBD returns richer typed objects with nested field goal/rebound models. Neither SDK is currently installed -- both must be added to `pyproject.toml`.

The `PlayerEntry` dataclass needs a new `stats` field (dict or None) and its `to_dict`/`from_dict` must handle the new field. The add-time fetch hook integrates into existing `recruit_add()` and `transfer_add()` command handlers. The `/career` command is a new public command with autocomplete from both lists.

**Primary recommendation:** Use simple async functions (not a Protocol) for the stats fetching layer -- each sport's API is different enough that a unified interface adds complexity without value. Keep CFBD and CBBD as two separate modules in `src/bot/stats/`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-01: New `/career` command (standalone, not `/stats`). Takes a player name parameter.
- D-02: Player name parameter uses autocomplete, populated from both recruiting and transfer lists for the channel's sport.
- D-03: Scope is all three sources: recruiting list, transfer list, and freeform name input as fallback.
- D-04: Sport derived from channel (Phase 7 D-16 carries forward). No sport parameter.
- D-05: Stats fetched at add-time. No on-demand API lookup from `/career`.
- D-06: Stats embedded directly in PlayerEntry as a `stats` field. No separate stats file.
- D-07: Fetch once at add-time only. No auto-refresh.
- D-08: If API call fails during add, player is still added without stats. `/career` shows "no stats available."
- D-09: Season-per-row monospace table in a code block. Column headers, one row per season, separator line before career totals.
- D-10: Career totals row shown only when player has 2+ seasons.
- D-11: Basketball stats: GP, PPG, RPG, APG, FG%, 3P% per season.
- D-12: Football stats: position-relevant categories only. QBs see passing + rushing, RBs see rushing + receiving, WRs see receiving. Show categories with actual stats.
- D-13: Sport emoji in embed title.
- D-14: Use official Python SDKs: `cfbd` for football, `cbbd` for basketball.
- D-15: CFBD has no "career stats" endpoint -- query `/stats/player/season` per year and assemble career data locally.
- D-16: CBBD uses `get_player_season_stats()` for season totals. Roster lookup needed to find player IDs.
- D-17: API keys configured via environment variables (CFBD_API_KEY, CBBD_API_KEY) in Settings.
- D-18: At add-time: Call CFBD `/player/search` with the player name. If exactly 1 result, use it. If multiple, pick the one matching the school. If none, add player without stats.
- D-19: At /career time: Autocomplete handles most cases. For freeform input, use difflib.get_close_matches with cutoff=0.6. Show "did you mean?" when no exact match.

### Claude's Discretion
- Internal structure of the `stats` field in PlayerEntry
- Error message wording
- CBBD player ID resolution flow (roster lookup)
- Whether to use Protocol interface or simple functions for stats fetching layer

### Deferred Ideas (OUT OF SCOPE)
- Manual /career-refresh command
- Daily auto-refresh of stored stats
- General school-wide portal lookup
- Player comparison features
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| STATS-01 | User can look up college career stats for any player on KU recruiting list | `/career` command with autocomplete from recruit+transfer lists; stats pre-fetched at add-time and stored in PlayerEntry |
| STATS-02 | Basketball stats formatted as PPG, RPG, APG, FG%, 3P% per season | CBBD `get_player_season_stats()` returns `points`, `assists`, `games`, `rebounds.total`, `field_goals.pct`, `three_point_field_goals.pct` -- compute per-game averages |
| STATS-03 | Football stats formatted as passing, rushing, receiving yards and TDs per season | CFBD `get_player_season_stats()` with category filter returns flat `stat_type`/`stat` rows; query `passing`, `rushing`, `receiving` categories |
| STATS-04 | Player name resolution uses fuzzy matching | Existing `difflib.get_close_matches` pattern from Phase 7; autocomplete for list players; CFBD `search_players()` for API lookup |
| INFRA-02 | CBBD API integration for basketball stats | `cbbd` v1.26.3 SDK with Bearer auth; `StatsApi.get_player_season_stats()` + `TeamsApi.get_team_roster()` for player ID resolution |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| cfbd | 5.13.2 | CFBD API client (football) | Official Python SDK, auto-generated from OpenAPI spec. Bearer token auth, typed responses. |
| cbbd | 1.26.3 | CBBD API client (basketball) | Official Python SDK, same maintainer (CFBD org). Bearer token auth, typed responses. |

### Supporting (already installed)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| difflib (stdlib) | -- | Fuzzy name matching | `get_close_matches` for freeform `/career` input and remove commands |
| discord.py | 2.7.1 | Bot framework | Slash commands, autocomplete, embeds |
| pydantic-settings | 2.x | Config management | Adding CFBD_API_KEY, CBBD_API_KEY fields |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| cfbd/cbbd SDKs | Raw aiohttp calls | SDKs handle auth, pagination, response typing. Raw calls would need manual Bearer header, URL construction, and response parsing. SDKs are the clear choice per D-14. |
| Protocol interface | Simple functions | Two sport APIs have completely different response shapes. A Protocol would force an artificial common interface. Simple per-sport functions are clearer. |

**Installation:**
```bash
uv add cfbd cbbd
```

## Architecture Patterns

### Recommended Project Structure
```
src/bot/
  stats/
    __init__.py
    football.py       # CFBD API: search_players, fetch_football_stats
    basketball.py     # CBBD API: roster lookup, fetch_basketball_stats
    formatter.py      # Monospace table formatting for both sports
  commands/
    career.py         # /career command handler
  storage/
    models.py         # PlayerEntry with stats field (modified)
  config.py           # Settings with CFBD/CBBD API keys (modified)
```

### Pattern 1: Stats Field Structure in PlayerEntry

**What:** Store fetched stats as a dict in PlayerEntry, keyed by season year, with sport-specific stat values.

**Recommended structure:**
```python
# Football stats stored as:
{
    "sport": "football",
    "player_id": "12345",
    "seasons": {
        "2022": {
            "team": "Oklahoma",
            "categories": {
                "passing": {"COMPLETIONS": "180", "ATT": "290", "YDS": "2500", "TD": "20", "INT": "5"},
                "rushing": {"CAR": "80", "YDS": "350", "TD": "3"},
            }
        },
        "2023": { ... }
    }
}

# Basketball stats stored as:
{
    "sport": "basketball",
    "player_id": "67890",
    "seasons": {
        "2023": {
            "team": "Duke",
            "games": 32,
            "points": 480,
            "assists": 128,
            "rebounds_total": 192,
            "fg_pct": 0.455,
            "fg3_pct": 0.372,
        },
        "2024": { ... }
    }
}
```

**Why this structure:** Store raw totals, compute per-game averages at display time. This avoids rounding errors accumulating and allows career totals to be computed by summing raw values.

### Pattern 2: Add-Time Stats Fetch Hook

**What:** After a player is successfully added via `/recruit-add` or `/transfer-add`, fire an async stats fetch. If it fails, the player is still added (D-08).

```python
# In recruit_add handler, after successful add:
player = bot.recruit_store.add_player(sport, name, position, school, stars)
if player is not None:
    # Fire stats fetch -- failure is non-fatal
    try:
        if sport == "football":
            stats = await fetch_football_stats(bot.settings, name, school)
        else:
            stats = await fetch_basketball_stats(bot.settings, name, school)
        if stats:
            player.stats = stats
            bot.recruit_store.save()
    except Exception:
        logger.warning(f"Failed to fetch stats for {name}", exc_info=True)
```

### Pattern 3: CFBD Player Search + Stats Assembly

**What:** CFBD has no career stats endpoint. Search for the player, get their ID, then query season stats across multiple years.

```python
# 1. Search for player
results = players_api.search_players(search_term=name)
# Filter by school if multiple results
match = next((r for r in results if r.team.lower() == school.lower()), None)
if not match and len(results) == 1:
    match = results[0]

# 2. Query season stats by player name + team
# CFBD get_player_season_stats accepts: year, team, category, player
# Must query per-year, per-category
for year in range(start_year, current_year + 1):
    for category in ["passing", "rushing", "receiving"]:
        stats = stats_api.get_player_season_stats(
            year=year, team=match.team, category=category, player=match.name
        )
```

### Pattern 4: CBBD Roster-Based Player ID Resolution

**What:** CBBD has no player search endpoint. Resolve player ID via roster lookup, then query stats by season.

```python
# 1. Get team roster to find player ID
roster = teams_api.get_team_roster(season=current_year, team=school)
player_match = next(
    (p for p in roster if p.name.lower() == name.lower()),
    None
)

# 2. If no exact match, try fuzzy
if not player_match:
    names = [p.name for p in roster]
    close = difflib.get_close_matches(name, names, n=1, cutoff=0.6)
    if close:
        player_match = next(p for p in roster if p.name == close[0])

# 3. Query stats by team + season (then filter by player)
stats = stats_api.get_player_season_stats(season=year, team=school)
player_stats = [s for s in stats if s.name.lower() == player_match.name.lower()]
```

### Pattern 5: Monospace Table Formatting

**What:** Discord code blocks with aligned columns for stats display.

```python
def format_basketball_table(stats_data: dict) -> str:
    """Format basketball stats as monospace table."""
    header = "Season  GP   PPG   RPG   APG   FG%   3P%"
    sep    = "------  --  ----  ----  ----  ----  ----"
    lines = [header, sep]

    for year, s in sorted(stats_data["seasons"].items()):
        gp = s["games"]
        ppg = s["points"] / gp if gp else 0
        rpg = s["rebounds_total"] / gp if gp else 0
        apg = s["assists"] / gp if gp else 0
        fg = s["fg_pct"] * 100
        fg3 = s["fg3_pct"] * 100
        lines.append(f"{year}    {gp:>2}  {ppg:>4.1f}  {rpg:>4.1f}  {apg:>4.1f}  {fg:>4.1f}  {fg3:>4.1f}")

    if len(stats_data["seasons"]) >= 2:
        # Career totals line
        lines.append("------  --  ----  ----  ----  ----  ----")
        # ... compute totals ...
        lines.append(f"Career  {total_gp:>2}  {career_ppg:>4.1f}  ...")

    return "```\n" + "\n".join(lines) + "\n```"
```

### Anti-Patterns to Avoid
- **Fetching stats on every /career call:** Wastes API quota. Stats are fetched once at add-time (D-05).
- **Storing pre-computed per-game averages:** Store raw totals, compute averages at display time. This allows accurate career totals.
- **Single unified stats model for both sports:** Football and basketball have completely different stat shapes. Use sport-specific storage.
- **Blocking player add on stats failure:** D-08 explicitly says add succeeds even if stats fetch fails.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CFBD API calls | Raw HTTP client | `cfbd` SDK v5.13.2 | Auth, response typing, pagination handled |
| CBBD API calls | Raw HTTP client | `cbbd` SDK v1.26.3 | Auth, response typing handled |
| Fuzzy name matching | Custom string similarity | `difflib.get_close_matches` | Already established in Phase 7 with cutoff=0.6 |
| Monospace alignment | Manual string padding | Python f-string format specs (`{val:>4.1f}`) | Built-in alignment with `>`, `<`, `^` |

**Key insight:** The SDKs are auto-generated from OpenAPI specs and handle all the HTTP plumbing. The only complexity is assembling CFBD's flat stat rows into a per-player career structure.

## Common Pitfalls

### Pitfall 1: CFBD API Rate Limits (1,000 calls/month free tier)
**What goes wrong:** Querying multiple years x multiple categories per player add burns through quota fast.
**Why it happens:** Need to query per-year + per-category since there's no career aggregate endpoint.
**How to avoid:** Query with `team` + `player` name filter to get specific results. Minimize year range -- only query years the player was active (use search result to determine years). Consider batching: get all categories for a year in one call if no category filter gives all stats.
**Warning signs:** HTTP 429 responses from CFBD API.

### Pitfall 2: CBBD Player ID Resolution Complexity
**What goes wrong:** Player name doesn't match roster exactly (nickname vs legal name, suffixes like "Jr.", "III").
**Why it happens:** CBBD has no player search endpoint -- must match against roster names.
**How to avoid:** Use fuzzy matching on roster names. Try current year roster first, then previous years. Store the matched player name from the API so subsequent lookups are reliable.
**Warning signs:** Stats returning empty for players who obviously have college stats.

### Pitfall 3: CFBD stat values are strings, not numbers
**What goes wrong:** Arithmetic on stat values fails or produces wrong results.
**Why it happens:** The CFBD `PlayerStat.stat` field is type `str`, not `int` or `float`.
**How to avoid:** Convert all stat values to float/int at fetch time before storing.
**Warning signs:** TypeError when computing career totals.

### Pitfall 4: PlayerEntry.to_dict/from_dict breaks with new stats field
**What goes wrong:** Existing JSON files without `stats` field fail to deserialize.
**Why it happens:** Adding a new required field to the dataclass breaks backward compatibility.
**How to avoid:** Make `stats` field optional with default `None`. Handle missing key in `from_dict`.
**Warning signs:** Bot crashes on startup when loading existing recruits.json/transfers.json.

### Pitfall 5: Discord code block character limits
**What goes wrong:** Long stat tables exceed embed description limit (4096 chars) or code block rendering breaks.
**Why it happens:** Players with many seasons + multiple stat categories generate wide/tall tables.
**How to avoid:** Football tables may need to be split by category (one table for passing, another for rushing). Keep column widths tight. Test with 5+ season players.
**Warning signs:** Embed appears empty or truncated in Discord.

### Pitfall 6: CFBD get_player_season_stats year range unknown
**What goes wrong:** Querying too many years wastes API calls. Querying too few misses early seasons.
**Why it happens:** No way to know a priori which years a player was active.
**How to avoid:** Use `search_players()` result -- it may indicate team affiliation. Alternatively, query the last 5-6 years (covers maximum college eligibility including COVID year). Stop early if a year returns no results.
**Warning signs:** Empty results for valid players, or excessive API calls.

## Code Examples

### CFBD Authentication and Player Search (v5.x)
```python
# Source: https://github.com/CFBD/cfbd-python/blob/main/docs/PlayersApi.md
import cfbd

configuration = cfbd.Configuration(
    host="https://api.collegefootballdata.com",
    access_token=settings.cfbd_api_key,
)

with cfbd.ApiClient(configuration) as api_client:
    players_api = cfbd.PlayersApi(api_client)
    results = players_api.search_players(search_term="Jalon Daniels", team="Kansas")
    # Returns list[PlayerSearchResult] with fields: id, team, name, first_name, last_name, position
```

### CFBD Season Stats Query
```python
# Source: https://github.com/CFBD/cfbd-python/blob/main/docs/StatsApi.md
with cfbd.ApiClient(configuration) as api_client:
    stats_api = cfbd.StatsApi(api_client)
    stats = stats_api.get_player_season_stats(
        year=2023, team="Kansas", category="passing", player="Jalon Daniels"
    )
    # Returns list[PlayerStat] with fields:
    #   season, player_id, player, position, team, conference, category, stat_type, stat
    # Example row: category="passing", stat_type="YDS", stat="2500"
```

### CBBD Authentication and Stats Query
```python
# Source: https://github.com/CFBD/cbbd-python/blob/main/docs/StatsApi.md
import cbbd

configuration = cbbd.Configuration(
    access_token=settings.cbbd_api_key,
)

with cbbd.ApiClient(configuration) as api_client:
    stats_api = cbbd.StatsApi(api_client)
    stats = stats_api.get_player_season_stats(season=2024, team="Kansas")
    # Returns list[PlayerSeasonStats] with fields:
    #   season, team, name, position, games, points, assists, steals, blocks,
    #   turnovers, rebounds (TeamSeasonUnitStatsRebounds: total, offensive, defensive),
    #   field_goals (TeamSeasonUnitStatsFieldGoals: made, attempted, pct),
    #   three_point_field_goals (same shape), free_throws (same shape)
```

### CBBD Roster Lookup for Player ID
```python
# Source: https://github.com/CFBD/cbbd-python/blob/main/docs/TeamsApi.md
with cbbd.ApiClient(configuration) as api_client:
    teams_api = cbbd.TeamsApi(api_client)
    roster = teams_api.get_team_roster(season=2024, team="Kansas")
    # Returns list[TeamRoster] -- filter by player name to get athlete ID
```

### PlayerEntry Extension
```python
@dataclass
class PlayerEntry:
    name: str
    position: str
    school: str
    stars: int
    added_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    type: str = "target"
    stats: dict | None = None  # NEW: career stats data

    def to_dict(self) -> dict:
        d = {
            "name": self.name,
            "position": self.position,
            "school": self.school,
            "stars": self.stars,
            "added_at": self.added_at,
            "type": self.type,
        }
        if self.stats is not None:
            d["stats"] = self.stats
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "PlayerEntry":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| cfbd v4.x (API key in header) | cfbd v5.x (Bearer token auth) | v5.0 | Configuration uses `access_token` not `api_key['Authorization']` |
| cfbd PlayersApi.get_player_season_stats | cfbd StatsApi.get_player_season_stats | v5.0 | Method moved to StatsApi class |
| Manual HTTP calls | Official SDKs | Ongoing | Both cfbd and cbbd provide auto-generated typed clients |

**Deprecated/outdated:**
- cfbd v4.x auth pattern (`configuration.api_key['Authorization'] = 'Bearer TOKEN'`) -- v5 uses `configuration.access_token` directly
- The `master` branch docs on GitHub show v4 patterns; `main` branch has v5 patterns

## Open Questions

1. **CFBD stat categories available per position**
   - What we know: Categories include "passing", "rushing", "receiving", "defensive", "kicking", "punting"
   - What's unclear: Exact `stat_type` values within each category (e.g., is it "YDS" or "YARDS"?)
   - Recommendation: Query the `get_categories()` endpoint at implementation time, or inspect one test response. This is LOW risk -- the formatter can adapt to whatever keys come back.

2. **CBBD player name matching across rosters**
   - What we know: Must do roster lookup per season to find a player
   - What's unclear: Whether `get_player_season_stats(team=X)` returns ALL players for that team-season, or if you need to pass a player ID filter
   - Recommendation: Query by team + season and filter client-side. One API call per season is acceptable.

3. **Year range for CFBD queries**
   - What we know: College eligibility is typically 4-5 years (6 with COVID waiver, rare)
   - What's unclear: Whether `search_players()` returns years active or just the latest team
   - Recommendation: Query last 6 years by default. Stop early when consecutive empty results. This uses at most 6 x 3 (categories) = 18 API calls per player worst case.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| cfbd | Football stats | Not installed | 5.13.2 (latest on PyPI) | Must install |
| cbbd | Basketball stats | Not installed | 1.26.3 (latest on PyPI) | Must install |
| CFBD API key | Football stats | Unknown (env var) | -- | Player added without stats |
| CBBD API key | Basketball stats | Unknown (env var) | -- | Player added without stats |
| difflib (stdlib) | Fuzzy matching | Available | -- | -- |

**Missing dependencies with no fallback:**
- cfbd and cbbd packages must be installed via `uv add cfbd cbbd`

**Missing dependencies with fallback:**
- API keys (CFBD_API_KEY, CBBD_API_KEY) -- if not configured, stats fetch silently fails and players are added without stats (per D-08)

## Sources

### Primary (HIGH confidence)
- [cfbd-python PlayersApi v5 docs](https://github.com/CFBD/cfbd-python/blob/main/docs/PlayersApi.md) - search_players method, auth pattern
- [cfbd-python StatsApi v5 docs](https://github.com/CFBD/cfbd-python/blob/main/docs/StatsApi.md) - get_player_season_stats method
- [cfbd-python PlayerStat model](https://github.com/CFBD/cfbd-python/blob/main/docs/PlayerStat.md) - Response fields: season, player_id, player, position, team, category, stat_type, stat (str)
- [cfbd-python PlayerSearchResult model](https://github.com/CFBD/cfbd-python/blob/main/docs/PlayerSearchResult.md) - Response fields: id, team, name, first_name, last_name, position
- [cbbd-python StatsApi docs](https://github.com/CFBD/cbbd-python/blob/main/docs/StatsApi.md) - get_player_season_stats method
- [cbbd-python PlayerSeasonStats model](https://github.com/CFBD/cbbd-python/blob/main/docs/PlayerSeasonStats.md) - All response fields including nested objects
- [cbbd-python TeamsApi docs](https://github.com/CFBD/cbbd-python/blob/main/docs/TeamsApi.md) - get_team_roster method
- [cfbd PyPI](https://pypi.org/project/cfbd/) - v5.13.2 verified
- [cbbd PyPI](https://pypi.org/project/cbbd/) - v1.26.3 verified

### Secondary (MEDIUM confidence)
- [cfbd-python README](https://github.com/CFBD/cfbd-python) - Full API class listing for v5
- [cbbd-python README](https://github.com/CFBD/cbbd-python) - Full API class listing, confirms no PlayersApi exists

### Tertiary (LOW confidence)
- CFBD stat_type values (e.g., "YDS", "TD", "ATT") -- inferred from common patterns, needs runtime verification

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Official SDKs verified on PyPI, version numbers confirmed
- Architecture: HIGH - Based on locked decisions from CONTEXT.md and existing codebase patterns
- API response shapes: MEDIUM - Model docs verified but exact stat_type string values need runtime confirmation
- Pitfalls: HIGH - Rate limits documented, backward compatibility is standard concern

**Research date:** 2026-04-08
**Valid until:** 2026-05-08 (SDKs are stable, APIs don't change frequently)
