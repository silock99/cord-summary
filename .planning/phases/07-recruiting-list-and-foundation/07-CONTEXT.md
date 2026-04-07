# Phase 7: Recruiting List and Foundation - Context

**Gathered:** 2026-04-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Admin-curated KU recruiting and transfer lists with JSON persistence, channel-based sport detection, and role-gated add/remove commands. Establishes the persistence pattern and config infrastructure for the entire v1.1 milestone.

Key distinction: This phase handles TWO separate list types — high school **recruits** and college **transfers** — with identical command structure but separate data stores.

</domain>

<decisions>
## Implementation Decisions

### List Display Format
- **D-01:** Field-per-player embed layout — each player gets their own embed field with name/stars as title, position/school as value, and added-date
- **D-02:** Lists sorted by position (not star rating), since transfers are the primary use case and star ratings apply mainly to HS recruits
- **D-03:** Single scrollable embed (auto-split at 4096 chars using existing embed split pattern), no button pagination

### Command Interface
- **D-04:** Two separate command sets — `/recruit-add`, `/recruit-remove`, `/recruit-list` for HS recruits AND `/transfer-add`, `/transfer-remove`, `/transfer-list` for college transfers (6 new commands total)
- **D-05:** Separate top-level commands (not subcommand groups), matching existing `/summary` + `/post-summary` pattern
- **D-06:** Add commands use slash command parameters: `name`, `position`, `school`, `stars` — all in one command
- **D-07:** Position is free text input (no dropdown/autocomplete) to accommodate edge cases (ATH, EDGE, etc.)
- **D-08:** Removal by player name with fuzzy matching — shows "did you mean?" when no exact match found

### Data Storage
- **D-09:** Separate JSON files: `data/recruits.json` and `data/transfers.json`
- **D-10:** Each file structured as `{"football": [...], "basketball": [...]}` with sport as top-level key

### Authorization
- **D-11:** New `RECRUITING_EDITOR_IDS` env var (comma-separated) — separate from `ADMIN_USER_IDS`
- **D-12:** `ADMIN_USER_IDS` implicitly inherit recruiting editor access (admins don't need to be in both lists)
- **D-13:** View commands (`/recruit-list`, `/transfer-list`) are public — any user in a mapped channel can view

### Channel-Sport Mapping
- **D-14:** Separate env vars per sport: `FOOTBALL_CHANNEL_IDS` and `BASKETBALL_CHANNEL_IDS` (comma-separated)
- **D-15:** Commands can ONLY be run in mapped channels — unmapped channels get a denial message
- **D-16:** No `sport` parameter on any command — sport is always determined from channel. This makes RECRUIT-05 (sport autocomplete dropdown) unnecessary.

### Claude's Discretion
- Error message wording for unauthorized users and unmapped channels
- Internal data model structure for player entries (fields, types, timestamps)
- File I/O pattern (atomic writes, error handling for corrupt JSON)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Patterns
- `src/bot/config.py` — Settings class with computed_field for comma-separated ID parsing (reuse pattern for RECRUITING_EDITOR_IDS, FOOTBALL_CHANNEL_IDS, BASKETBALL_CHANNEL_IDS)
- `src/bot/commands/post_summary.py` — Admin check pattern (is_admin decorator), autocomplete pattern, slash command registration pattern
- `src/bot/formatting/embeds.py` — Embed building and 4096-char split logic (reuse for list display)
- `src/bot/client.py` — Command registration in setup_hook (add new command registrations here)
- `src/bot/models.py` — Data model patterns (dataclasses)

### Requirements
- `.planning/REQUIREMENTS.md` — RECRUIT-01 through RECRUIT-06, INFRA-04, INFRA-05

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `config.py:Settings` — Computed field pattern for parsing comma-separated env vars into `list[int]`. Reuse for `recruiting_editor_ids`, `football_channel_ids`, `basketball_channel_ids`.
- `post_summary.py:is_admin()` — Check decorator pattern. Clone and adapt for `is_recruiting_editor()` that checks both RECRUITING_EDITOR_IDS and ADMIN_USER_IDS.
- `embeds.py:build_summary_embeds()` — Embed splitting at topic boundaries. Adapt split logic for player lists exceeding 4096 chars.
- `post_summary.py:channel_autocomplete()` — Autocomplete callback pattern (though not needed for sport since it's channel-derived).

### Established Patterns
- Commands registered as top-level slash commands via `register_*_command(bot)` functions in `src/bot/commands/`
- `pydantic-settings` for all configuration with `.env` file support
- Ephemeral responses for confirmations, public embeds for display
- Logging via `logging.getLogger(__name__)`

### Integration Points
- `client.py:setup_hook()` — Register new recruit/transfer commands here
- `config.py:Settings` — Add new env var fields here
- `data/` directory — New directory for JSON persistence files (currently only DM subscribers use file persistence)

</code_context>

<specifics>
## Specific Ideas

- Star rating displayed as emoji stars (e.g., ⭐⭐⭐⭐) in embed fields
- Sport emoji prefix in embed title (🏈 for football, 🏀 for basketball)
- "Did you mean?" fuzzy matching on removal when exact name not found
- Field-per-player layout with box-drawing characters (┌│└) for visual structure

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 07-recruiting-list-and-foundation*
*Context gathered: 2026-04-07*
