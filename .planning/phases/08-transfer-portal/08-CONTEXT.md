# Phase 8: Transfer Portal - Context

**Gathered:** 2026-04-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Enhance the existing `/transfer-*` commands (from Phase 7) to support two transfer categories: **transfers out** (KU players entering the portal) and **transfer targets** (players KU is pursuing). Add a `type` parameter to `/transfer-add`, group display by type in `/transfer-list`, build cache infrastructure for future CFBD API integration, and split large lists into multiple embeds. Both sports (football and basketball) use identical admin-curated workflows.

Key constraint: This is KU-focused only. No general school-wide portal lookup. The `/transfer-*` commands already exist and work -- this phase extends them, not replaces them.

</domain>

<decisions>
## Implementation Decisions

### Command Design
- **D-01:** No separate `/portal` command. Transfer portal functionality lives entirely within existing `/transfer-add`, `/transfer-remove`, `/transfer-list` commands from Phase 7.
- **D-02:** `/transfer-add` gets a new `type` parameter: "outgoing" (KU player leaving) or "target" (player KU wants). This distinguishes the two transfer categories.
- **D-03:** Sport remains channel-derived (Phase 7 D-16 carries forward). No sport parameter on commands.

### Data Source
- **D-04:** All data is admin-curated for both sports. No API integration in this phase. Editors manually add all transfer entries via `/transfer-add`.
- **D-05:** CFBD API integration deferred to Phase 9 (career stats). Cache infrastructure built now to prepare for it.

### Display Format
- **D-06:** `/transfer-list` groups players by type -- "Transfers Out" section header then those players, followed by "Transfer Targets" section header then those players.
- **D-07:** Identical field handling for both sports. Same fields: name, position, school, stars, type. No sport-specific metadata differences.

### Caching
- **D-08:** Build cache infrastructure now for future CFBD API use in Phase 9. In-memory cache with TTL support, even though current phase doesn't call external APIs.
- **D-09:** PORTAL-05 (cache API responses 15-30 min TTL) is reinterpreted as forward infrastructure investment, not an active requirement for this phase.

### Pagination
- **D-10:** 10 players per page in `/transfer-list`.
- **D-11:** No button pagination. Large lists split into multiple embeds sent in one response (same pattern as Phase 7 recruit-list with 25-field split, but now at 10 fields per embed).
- **D-12:** PORTAL-04 (button navigation) is replaced by multi-embed splitting. Simpler UX without interactive components.

### Claude's Discretion
- Cache implementation details (dict with timestamps, dataclass wrapper, etc.)
- How to handle the `type` field in the existing JSON storage structure
- Error messages for invalid type values
- Embed section header formatting for type grouping

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Code (Phase 7 outputs)
- `src/bot/commands/transfers.py` -- Current transfer commands to extend with `type` param and grouped display
- `src/bot/commands/recruiting.py` -- Reference for command patterns (identical structure)
- `src/bot/storage/recruiting_store.py` -- RecruitingStore class to extend with type-aware operations
- `src/bot/storage/models.py` -- PlayerEntry dataclass to extend with `type` field
- `src/bot/config.py` -- Settings class (no changes expected)
- `src/bot/client.py` -- Bot client with store initialization

### Requirements
- `.planning/REQUIREMENTS.md` -- PORTAL-01 through PORTAL-06, INFRA-01, INFRA-03

### Prior Context
- `.planning/phases/07-recruiting-list-and-foundation/07-CONTEXT.md` -- Phase 7 decisions that carry forward

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `RecruitingStore` -- Already handles add/remove/list/save/load. Extend to support `type` field on PlayerEntry.
- `transfers.py:register_transfer_commands()` -- Working command registration. Extend `/transfer-add` with type param, extend `/transfer-list` display logic.
- `PlayerEntry` dataclass -- Add `type` field (default "target" for backward compat with existing entries).
- Embed building pattern in both `recruiting.py` and `transfers.py` -- Adapt for grouped sections.

### Established Patterns
- `app_commands.Range[int, 0, 5]` for constrained params -- use similar for type choices
- `app_commands.describe()` for param descriptions
- Ephemeral responses for all commands (confirmed in Phase 7 testing)
- `get_sport_from_channel()` for sport resolution

### Integration Points
- `PlayerEntry.to_dict()` / `from_dict()` -- Must handle new `type` field with backward compat for existing JSON data
- `data/transfers.json` -- Existing file, entries gain `type` field
- `RecruitingStore.list_players()` -- May need type-filtering or type-grouping variant

</code_context>

<specifics>
## Specific Ideas

- Type grouping in embeds: "Transfers Out" header with outgoing emoji, "Transfer Targets" header with target emoji
- Backward compatibility: existing transfer entries without a `type` field default to "target"
- Cache module as standalone utility in `src/bot/storage/cache.py` for Phase 9 reuse

</specifics>

<deferred>
## Deferred Ideas

- CFBD API integration for auto-populating football portal data (Phase 9)
- General school-wide portal lookup (not KU-focused) -- potential future phase
- Button-based pagination -- could revisit if lists grow very large

</deferred>

---

*Phase: 08-transfer-portal*
*Context gathered: 2026-04-07*
