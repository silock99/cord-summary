# Phase 10: Current Roster - Context

**Gathered:** 2026-04-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Import and manage the current KU roster for both football and basketball, with career stats auto-fetched on add. Roster data is bulk-imported from CFBD (football) and CBBD (basketball) APIs via a single command, replacing the entire roster each time. Roster players appear in /career lookups alongside recruits and transfers.

Key distinction from recruits/transfers: Roster is API-sourced (bulk import), not admin-curated one-by-one. No manual add/remove commands — import replaces everything.

</domain>

<decisions>
## Implementation Decisions

### Data Source & Import
- **D-01:** Bulk import from API — a `/roster-import` command pulls the full KU roster from CFBD (football) or CBBD (basketball) in one shot
- **D-02:** Replace mode — each import wipes the current roster for that sport and replaces with fresh API data
- **D-03:** Stats fetched for every player during import — same add-time pattern as Phase 9. For an 85-player football roster this means ~85 API calls, but it's a one-time operation
- **D-04:** Current season only — no year/season parameter, always imports the latest roster
- **D-05:** Editors + Admins can run /roster-import (same permission as /recruit-add, /transfer-add)

### Command Design
- **D-06:** Two commands only: `/roster-import` and `/roster-list`. No add/remove since import replaces everything
- **D-07:** Ephemeral "Importing..." response, then a final ephemeral embed with results (count summary like "Imported 85 players, fetched stats for 82")
- **D-08:** Sport derived from channel (Phase 7 D-16 carries forward). No sport parameter

### Roster Identity & Storage
- **D-09:** Separate `data/roster.json` file with its own RecruitingStore instance. Same pattern as recruits.json and transfers.json
- **D-10:** Reuse existing `PlayerEntry` dataclass — name, position, stars (0 for unrated), stats. Jersey number stored in a new field on PlayerEntry
- **D-11:** School field not needed for roster players (always Kansas) — roster entries can have school as empty string
- **D-12:** `/career` searches all three stores (recruit, transfer, roster) to find player stats

### Display & Filtering
- **D-13:** `/roster-list` displays players alphabetically by name
- **D-14:** Multi-embed split for large rosters — auto-split at 25 fields per embed, all sent in one response. Same pattern as recruit/transfer lists
- **D-15:** Each player displays: Name + Position + Jersey # + Class (e.g., "John Smith — QB #7 (Jr.)")

### Claude's Discretion
- How to handle API failures during bulk import (partial import handling, retry logic)
- Jersey number and class year field additions to PlayerEntry (field names, types, defaults for backward compat)
- How to resolve CBBD player IDs for roster lookup (existing pattern in basketball.py)
- Embed formatting details for roster list display
- Error message wording for import failures and empty rosters

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Code (Phase 7-9 outputs)
- `src/bot/commands/recruiting.py` — Command registration pattern, permission checks, embed building
- `src/bot/commands/transfers.py` — Transfer command pattern (closest analog to roster commands)
- `src/bot/commands/career.py` — Career stats command that must search roster store too
- `src/bot/storage/recruiting_store.py` — RecruitingStore class to instantiate for roster data
- `src/bot/storage/models.py` — PlayerEntry dataclass to extend with jersey_number and class_year fields
- `src/bot/config.py` — Settings class (CFBD_API_KEY, CBBD_API_KEY already present)
- `src/bot/client.py` — Bot client with store initialization and command registration
- `src/bot/stats/basketball.py` — CBBD roster lookup pattern (already uses /roster endpoint for player matching)
- `src/bot/stats/football.py` — CFBD stats fetching pattern

### API Endpoints
- CFBD API: roster endpoint for football player data
- CBBD API: `/roster` endpoint (already used in basketball.py for player matching)

### Prior Context
- `.planning/phases/07-recruiting-list-and-foundation/07-CONTEXT.md` — D-16 (channel-derived sport), D-05 (separate commands), D-09/D-10 (JSON persistence pattern)
- `.planning/phases/09-career-stats/09-CONTEXT.md` — D-05/D-06 (stats at add-time), D-14-D-17 (API integration patterns)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `RecruitingStore` — Instantiate a third instance for roster data. Already handles add/remove/list/save/load with JSON persistence
- `PlayerEntry` — Extend with jersey_number and class_year fields for roster-specific data
- `get_sport_from_channel()` — Sport resolution from channel ID, reuse for roster commands
- `is_recruiting_editor()` — Permission decorator, reuse for /roster-import
- CBBD roster lookup in `basketball.py` — Already fetches roster data from CBBD API, can be adapted for bulk import
- CFBD stats fetching in `football.py` — Stats fetch pattern to reuse during import
- Embed building patterns in recruiting.py/transfers.py — Adapt for roster list display

### Established Patterns
- Commands registered as top-level slash commands via `register_*_command(bot)` functions
- `pydantic-settings` for all configuration
- Ephemeral responses for slash commands
- `app_commands.autocomplete()` for autocomplete callbacks
- Multi-embed split at 25 fields per embed

### Integration Points
- `client.py:setup_hook()` — Register new roster commands, initialize roster store
- `career.py` — Add roster store to the search chain (currently searches recruit + transfer stores)
- `data/roster.json` — New file for roster persistence
- `storage/models.py:PlayerEntry` — Add jersey_number and class_year fields with backward-compatible defaults

</code_context>

<specifics>
## Specific Ideas

- Sport emoji prefix in embed title (Phase 7 pattern: basketball/football)
- Import summary showing count of players imported and stats fetched successfully
- Jersey number displayed with # prefix in roster list
- Class year as abbreviated form (Fr., So., Jr., Sr., R-Fr., etc.)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 10-current-roster*
*Context gathered: 2026-04-08*
