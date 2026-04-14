# Phase 13: Connect a Google Sheet to the Recruit List Function - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire an existing Google Sheet into the bot as the authoritative source for the **basketball transfer target** list. The bot reads the sheet on an hourly schedule, caches the result in memory with a JSON snapshot, and serves `/transfer-list` (basketball, type=target) from that cache. Manual editing commands for this specific slice are disabled — the sheet becomes the single source of truth.

**Explicitly NOT in scope (despite phase name):**
- The actual recruiting list (`/recruit-*` commands, `bot.recruit_store`) is untouched. User corrected mid-discussion: "it's only transfer targets we're connecting to at the moment." The roadmap phase name is misleading — the real subject is the basketball transfer-target slice of `bot.transfer_store`.
- Football transfers (CFBD API remains the source), outgoing basketball transfers, recruits, and roster are all untouched.
- Two-way sync, write-through to sheet, OAuth, or lazy-per-request fetching.

</domain>

<decisions>
## Implementation Decisions

### Sync direction
- **D-01:** Sheet → Bot, read-only. Sheet is the single source of truth for basketball transfer targets.
- **D-02:** `/transfer-add`, `/transfer-remove` are disabled for `sport=basketball AND type=target`. They return a clear message indicating this data is managed in the Google Sheet. Other slices (basketball outgoing, football transfers) continue to work as before.

### Scope of data pulled from sheet
- **D-03:** Only basketball transfers with `type=target` are sourced from the sheet. Outgoing basketball transfers stay admin-curated via existing commands.
- **D-04:** The sheet does not replace the entire `transfer_store` — it feeds one slice. Store must be able to merge sheet-sourced targets with locally managed outgoing entries without collision.

### Refresh model
- **D-05:** Scheduled hourly refresh via `discord.ext.tasks.loop(hours=1)` (matches project pattern — no new scheduler dependency).
- **D-06:** On bot startup, perform an initial fetch before the scheduled loop begins so the first `/transfer-list` call isn't empty.
- **D-07:** Cache strategy: in-memory list + JSON snapshot on disk. `/transfer-list` always serves from memory (no per-request API call). Snapshot lets bot start with last-known-good data if the first refresh fails.
- **D-08:** On refresh failure (network error, auth error, sheet unavailable): keep serving stale cache, log a warning via existing error-alerting pipeline (Phase 6). Do NOT clear the cache.

### Authentication
- **D-09:** Google service account with a JSON key. Key path or inline JSON loaded via `pydantic-settings` from env/`.env` (consistent with existing secrets like bot token, OpenAI key).
- **D-10:** Sheet must be shared (viewer access) with the service account's email. This is an operational step the user performs — document it in the phase README/notes.

### Sheet schema (concrete)
- **D-11:** Sheet URL: `https://docs.google.com/spreadsheets/d/1wnI1UQ_YvSXuQUS7AqCNb2tp_1Gf45zUPYPX3FiPMog/edit` — Sheet ID `1wnI1UQ_YvSXuQUS7AqCNb2tp_1Gf45zUPYPX3FiPMog`.
- **D-12:** Worksheet/tab: `Master List 2025`. Header row is **row 3**; data begins at **row 4**. Rows 1–2 are metadata and must be skipped.
- **D-13:** Columns (left to right): `Name | Position | Former School | Height/Weight | KU Interest Level | Made Contact | Notes`. Mapping is a **code constant** — no env configuration.
- **D-14:** Existing `PlayerEntry` fields (`school`, `stars`, etc.) do NOT constrain the basketball-target model. Replace with a sheet-aligned model: `name`, `position`, `former_school`, `height_weight`, `ku_interest_level`, `made_contact`, `notes`. `PlayerEntry` remains unchanged — do not edit it. A new dataclass (e.g., `TransferTarget`) holds sheet-sourced basketball targets separately.
- **D-15:** Row-level validation: rows missing `Name` (trimmed empty) are skipped with a debug log. All other fields may be empty strings — preserve as-is.
- **D-16:** Stars display is suppressed entirely for sheet-backed basketball targets — no "Unrated" filler. The `/transfer-list` renderer for this slice uses the new field set instead of the existing PlayerEntry layout.

### Data model & storage layout
- **D-17:** New module `src/bot/sources/sheets.py` (or equivalent per research) owns: `TransferTarget` dataclass, `SheetTransferTargetStore` (in-memory + atomic JSON snapshot at `data/transfer_targets_basketball.json`), and the hourly refresh scheduler.
- **D-18:** Do NOT write sheet data into `data/transfers.json` or share `RecruitingStore` with the sheet sync path. `/transfer-list` merges the two sources at render time: sheet store for basketball+target, existing `transfer_store` for everything else.
- **D-19:** On bot startup, a self-heal step removes any pre-existing `sport=basketball, type=target` entries from `data/transfers.json` so the sheet is the unambiguous source going forward.
- **D-20:** Preserve `added_at` across refreshes by diffing against the previous snapshot (match on normalized `name`). New rows get the current timestamp; existing rows keep their original `added_at`.

### List display
- **D-21:** `/transfer-list` for basketball targets shows a footer: "Synced {relative time} ago" based on the last successful refresh timestamp. Other slices keep their current footer.

### Claude's Discretion
- Exact module layout (e.g., `src/bot/sheets/` vs extending `src/bot/storage/`).
- Library choice for Google Sheets access (research to choose between `gspread`, `google-api-python-client`, etc. — must be async-friendly or wrapped in `asyncio.to_thread`).
- Retry/backoff policy for transient API failures within a single refresh attempt.
- Log format and verbosity of refresh-loop output.
- Exact wording of the "managed in Google Sheet" message returned by disabled commands.

</decisions>

<specifics>
## Specific Ideas

- Hourly refresh cadence is the user's explicit pick — not "as fresh as possible." Don't over-engineer toward real-time.
- Pattern match the existing transfer-store shape: same `PlayerEntry` model, same sport/type partitioning — the sheet is a different ingress point, not a different data model.
- The service-account-JSON-in-env pattern is already used throughout the project for external APIs (OpenAI, CBBD, CFBD) — follow that convention rather than inventing a new config shape.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing transfer/recruiting code this phase extends
- `src/bot/commands/transfers.py` — `/transfer-add`, `/transfer-remove`, `/transfer-list` command handlers. Needs edits to disable add/remove for basketball+target slice.
- `src/bot/storage/recruiting_store.py` — `RecruitingStore` (also used by `transfer_store`). Shared storage pattern — sheet sync layer should write into this or a parallel store cleanly.
- `src/bot/storage/models.py` — `PlayerEntry` model. Target fields for sheet column mapping.
- `src/bot/config.py` — `pydantic-settings` configuration. New sheet-related settings (sheet ID, service account key, tab name) go here.
- `src/bot/client.py` — bot startup wiring. Initial fetch and `tasks.loop` registration happen here.

### Prior phase context
- `.planning/phases/07-recruiting-list-and-foundation/07-CONTEXT.md` — JSON persistence / atomic write pattern precedent.
- `.planning/phases/08-transfer-portal/08-CONTEXT.md` — introduced admin-curated basketball transfers, `type` field, cache pattern (`TTLCache` — not reused here, but cache/fallback philosophy carries over).
- `.planning/ROADMAP.md` § Phase 13 — phase entry (note: title says "recruit list" but scope is transfer targets per this discussion).

### Project-level
- `.planning/PROJECT.md` — stack constraints (Python 3.12+, discord.py 2.7.1, pydantic-settings, discord.ext.tasks).
- `.planning/REQUIREMENTS.md` — no TRANSFER-SHEET-* requirements exist yet; planner should add them for this phase.

No pre-existing ADR or feature doc for Google Sheets integration — this phase establishes the pattern.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `RecruitingStore` in `src/bot/storage/recruiting_store.py`: atomic JSON write (`tempfile` + `os.replace`), sport-partitioned dict of `PlayerEntry`. Sheet-cache snapshot can follow the same atomic-write pattern.
- `discord.ext.tasks.loop` already used for the daily 9am summary (Phase 3) — same primitive powers the hourly sheet refresh. Zero new dependencies for scheduling.
- `pydantic-settings` config pattern in `src/bot/config.py` for secrets and channel IDs — extend with sheet settings.
- Error alerting pipeline from Phase 6 — refresh failures pipe through this, not a new alerting path.

### Established Patterns
- External API integrations (CFBD, CBBD, OpenAI) live in dedicated modules (`src/bot/stats/`, summarizer module). Sheets access should follow suit — probably `src/bot/sheets/` or `src/bot/sources/sheets.py`.
- Async wrapping convention: sync SDKs are wrapped via `asyncio.to_thread` when needed (see stats modules). Apply to whichever Sheets library is chosen if it's sync-only.
- Settings list fields (like `football_channel_ids`) use comma-separated env parsing. Sheet ID is a single string — straightforward.

### Integration Points
- `bot.transfer_store` is constructed in `client.py` setup. Sheet sync registers a refresh task alongside it.
- The `type` + `sport` filter key (`basketball` + `target`) becomes the partition that the sheet owns. Existing `list_players` / `add_player` / `remove_player` need guard rails that check this partition before allowing manual edits.

</code_context>

<deferred>
## Deferred Ideas

- **Two-way sync** — raised as an option, rejected for this phase. If the user later wants Discord commands to write back to the sheet, it becomes a follow-up phase with conflict/version handling.
- **Sheet-sourced recruits, roster, football transfers** — the original phase name implied recruits. User narrowed to transfer targets only. Expanding the sheet integration to other lists is a future phase, not scope creep into this one.
- **Manual `/refresh-transfers` admin command** — not requested. If refresh failures become common or users want instant pull-on-demand, add in a later phase.
- **Sheet-column flexibility / configurable mapping** — user picked fixed schema. Deferred unless the sheet structure changes often.
- **Rename the phase in the roadmap** — the roadmap title ("Connect a Google Sheet to the recruit list function") doesn't match the actual scope (basketball transfer targets). Worth a roadmap touch-up, but not blocking planning.

</deferred>

---

*Phase: 13-connect-a-google-sheet-to-the-recruit-list-function*
*Context gathered: 2026-04-14*
