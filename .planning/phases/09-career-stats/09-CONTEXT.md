# Phase 9: Career Stats - Context

**Gathered:** 2026-04-08
**Status:** Ready for planning

<domain>
## Phase Boundary

College career stats lookup for players on the KU recruiting and transfer lists (plus freeform name fallback). Stats are fetched from CFBD (football) and CBBD (basketball) APIs at add-time and stored locally in the player entry JSON. A new `/career` command reads from local storage and displays sport-appropriate formatted stats in monospace embed tables.

Key architectural decision: Stats are pre-fetched and cached locally when a player is added, NOT looked up on-demand. This minimizes API calls (1,000/month free tier) and eliminates latency on the /career command.

</domain>

<decisions>
## Implementation Decisions

### Command Interface
- **D-01:** New `/career` command (standalone, not `/stats`). Takes a player name parameter. Follows the separate-command pattern from Phase 7.
- **D-02:** Player name parameter uses autocomplete, populated from both the recruiting list AND transfer list for the channel's sport.
- **D-03:** Scope is all three sources: recruiting list players, transfer list players, and freeform name input as fallback (any player name, hits API directly).
- **D-04:** Sport derived from channel (Phase 7 D-16 carries forward). No sport parameter.

### Stats Data Architecture
- **D-05:** Stats fetched at add-time — when `/recruit-add` or `/transfer-add` is called, the bot immediately calls the CFBD/CBBD API and stores stats in the player's JSON entry. No on-demand API lookup from `/career`.
- **D-06:** Stats embedded directly in the PlayerEntry (recruits.json / transfers.json) as a `stats` field. No separate stats file.
- **D-07:** Fetch once at add-time only. No auto-refresh, no scheduled updates. Stats are a snapshot at time of addition.
- **D-08:** If the API call fails during add, the player is still added without stats. `/career` shows "no stats available" for that player.

### Stats Display Format
- **D-09:** Season-per-row monospace table in a code block. Column headers for stat categories, one row per season, separator line before career totals.
- **D-10:** Career totals row shown only when player has 2+ seasons. Single-season players show just their one season row.
- **D-11:** Basketball stats: GP, PPG, RPG, APG, FG%, 3P% per season (per STATS-02).
- **D-12:** Football stats: position-relevant categories only — QBs see passing + rushing, RBs see rushing + receiving, WRs see receiving. Show categories where the player has actual stats, don't show zero-filled categories.
- **D-13:** Sport emoji in embed title (basketball/football, carrying forward Phase 7 pattern).

### API Integration
- **D-14:** Use official Python SDKs: `cfbd` for football, `cbbd` for basketball. They handle auth, pagination, and response typing.
- **D-15:** CFBD has no "career stats" endpoint — query `/stats/player/season` per year and assemble career data locally.
- **D-16:** CBBD uses `get_player_season_stats()` for season totals. Roster lookup needed to find player IDs (no dedicated player search endpoint).
- **D-17:** API keys configured via environment variables (CFBD_API_KEY, CBBD_API_KEY) in Settings.

### Name Matching
- **D-18:** At add-time (API lookup): Call CFBD `/player/search` with the player name. If exactly 1 result, use it. If multiple results, pick the one matching the school from the add command. If no results, add player without stats.
- **D-19:** At /career time (local lookup): Autocomplete handles most cases. For freeform input, use difflib.get_close_matches with cutoff=0.6 (Phase 7 D-08 pattern). Show "did you mean?" when no exact match found.

### Claude's Discretion
- Internal structure of the `stats` field in PlayerEntry (dict of seasons, list of stat objects, etc.)
- Error message wording when stats not available or API fails
- How to handle the CBBD player ID resolution (roster lookup flow)
- Whether to use a Protocol interface or simple functions for the stats fetching layer

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Code (Phase 7 + 8 outputs)
- `src/bot/commands/transfers.py` — Transfer commands to modify with stats-fetch-on-add hook
- `src/bot/commands/recruiting.py` — Recruit commands to modify with stats-fetch-on-add hook
- `src/bot/storage/models.py` — PlayerEntry dataclass to extend with `stats` field
- `src/bot/storage/recruiting_store.py` — RecruitingStore (add_player needs post-add stats fetch)
- `src/bot/storage/cache.py` — TTLCache module (may be useful for API response deduplication)
- `src/bot/client.py` — Bot client with store initialization and transfer_cache
- `src/bot/config.py` — Settings class (add CFBD_API_KEY, CBBD_API_KEY)
- `src/bot/providers/base.py` — SummaryProvider Protocol pattern (reference for stats provider if needed)

### API Documentation
- CFBD API: `https://api.collegefootballdata.com` — Bearer token auth, `/player/search`, `/stats/player/season`
- CBBD API: `https://api.collegebasketballdata.com` — Bearer token auth, `get_player_season_stats()`, roster lookups
- Python SDKs: `cfbd` (football), `cbbd` (basketball)

### Requirements
- `.planning/REQUIREMENTS.md` — STATS-01 through STATS-04, INFRA-02

### Prior Context
- `.planning/phases/07-recruiting-list-and-foundation/07-CONTEXT.md` — D-08 (fuzzy matching), D-16 (channel-derived sport)
- `.planning/phases/08-transfer-portal/08-CONTEXT.md` — D-05 (CFBD deferred to Phase 9), D-08/D-09 (cache infrastructure)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `TTLCache` in `src/bot/storage/cache.py` — Could cache API search results during add-time to avoid duplicate calls if same player is added to both lists
- `difflib.get_close_matches` — Already used in recruit/transfer remove commands for fuzzy matching
- `get_sport_from_channel()` — Sport resolution from channel ID, reuse for /career
- Embed building patterns in recruiting.py and transfers.py — Adapt for stats display
- `is_recruiting_editor()` decorator — /career is public (view-only), but add-time fetch runs within editor-gated commands

### Established Patterns
- Commands registered as top-level slash commands via `register_*_command(bot)` in `src/bot/commands/`
- `pydantic-settings` for all configuration with `.env` file support
- Ephemeral responses for slash commands
- `app_commands.autocomplete()` decorator for autocomplete callbacks

### Integration Points
- `client.py:setup_hook()` — Register new /career command
- `config.py:Settings` — Add CFBD_API_KEY, CBBD_API_KEY fields
- `recruiting.py:recruit_add()` and `transfers.py:transfer_add()` — Hook stats fetch after successful player add
- `storage/models.py:PlayerEntry` — Extend with `stats` field (dict or None)
- `data/recruits.json` and `data/transfers.json` — Existing files gain stats data per player

</code_context>

<specifics>
## Specific Ideas

- Monospace code block table with aligned columns for stats display
- Sport emoji prefix in embed title (Phase 7 pattern)
- Separator line (unicode box-drawing) before career totals row
- Position-relevant football stat categories (don't show zeros for irrelevant categories)
- Autocomplete searches both recruiting and transfer lists simultaneously

</specifics>

<deferred>
## Deferred Ideas

- Manual /career-refresh command to re-fetch stats for a player (if seasons update)
- Daily auto-refresh of stored stats during active seasons
- General school-wide portal lookup (not KU-focused)
- Player comparison features (side-by-side stats)

</deferred>

---

*Phase: 09-career-stats*
*Context gathered: 2026-04-08*
