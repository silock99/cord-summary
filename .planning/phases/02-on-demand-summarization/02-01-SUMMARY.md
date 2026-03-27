---
phase: 02-on-demand-summarization
plan: 01
subsystem: config, formatting
tags: [pydantic-settings, discord-embeds, topic-splitting]

# Dependency graph
requires:
  - phase: 01-foundation-and-pipeline
    provides: Settings class, summarizer system prompts, SummaryError model
provides:
  - Extended Settings with allowed_channel_ids, default_summary_minutes, quiet_threshold
  - Updated system prompts for topic-grouped bullets without action items
  - Embed formatting module with topic-boundary splitting
affects: [02-02-slash-command]

# Tech tracking
tech-stack:
  added: []
  patterns: [computed_field for comma-separated env var parsing, topic-boundary embed splitting]

key-files:
  created:
    - src/bot/formatting/__init__.py
    - src/bot/formatting/embeds.py
    - tests/test_embeds.py
    - tests/test_config_phase2.py
  modified:
    - src/bot/config.py
    - src/bot/summarizer.py
    - .env.example

key-decisions:
  - "Used pydantic computed_field with raw str field + alias for comma-separated ALLOWED_CHANNEL_IDS parsing (pydantic-settings JSON-decodes list[int] before validators run)"

patterns-established:
  - "Embed splitting: split at bold (**) topic headers, truncate oversized sections with (...truncated) marker"
  - "Config extension: use str field with alias + computed_field for complex env var types that pydantic-settings would JSON-decode"

requirements-completed: [SUM-03, SUM-05, OUT-02]

# Metrics
duration: 5min
completed: 2026-03-27
---

# Phase 2 Plan 1: Config, Prompts, and Embed Formatting Summary

**Extended Settings with channel allowlist and quiet threshold, topic-grouped system prompts, and embed formatter with 4096-char topic-boundary splitting**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-27T23:34:06Z
- **Completed:** 2026-03-27T23:39:35Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Settings extended with allowed_channel_ids (comma-separated env var), default_summary_minutes (240), and quiet_threshold (5)
- Both system prompts updated to instruct topic-grouped bullets with bold headers, no action items extraction
- Embed formatting module splits summaries at topic boundaries respecting Discord's 4096-char embed limit
- 29 new tests (12 config + 17 embeds), all 55 total tests passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend Settings and update system prompts** - `0027147` (test RED), `91c3793` (feat GREEN)
2. **Task 2: Create embed formatting module** - `ba6af26` (test RED), `e88d694` (feat GREEN)

_TDD tasks have separate test and implementation commits._

## Files Created/Modified
- `src/bot/config.py` - Added allowed_channel_ids (computed_field), default_summary_minutes, quiet_threshold
- `src/bot/summarizer.py` - Updated SUMMARY_SYSTEM_PROMPT and MERGE_SYSTEM_PROMPT for topic-grouped format
- `.env.example` - Added ALLOWED_CHANNEL_IDS, DEFAULT_SUMMARY_MINUTES, QUIET_THRESHOLD
- `src/bot/formatting/__init__.py` - Package init exporting build_summary_embeds
- `src/bot/formatting/embeds.py` - build_summary_embeds with _split_into_topics and _make_embed
- `tests/test_config_phase2.py` - 12 tests for config extensions and prompt updates
- `tests/test_embeds.py` - 17 tests for embed building and splitting

## Decisions Made
- Used pydantic `computed_field` with a raw `str` field (aliased to ALLOWED_CHANNEL_IDS) instead of `list[int]` with `field_validator` -- pydantic-settings v2 JSON-decodes complex types from env vars before validators run, causing parse errors on comma-separated strings like "123,456"

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Changed allowed_channel_ids from field_validator to computed_field**
- **Found during:** Task 1 (Settings extension)
- **Issue:** pydantic-settings v2 treats `list[int]` as a complex type and attempts JSON decoding of the env var value before any field_validator runs, causing `JSONDecodeError` on comma-separated input like "123,456"
- **Fix:** Changed to `allowed_channel_ids_raw: str` field with `alias="ALLOWED_CHANNEL_IDS"` plus a `@computed_field` property that parses the string into `list[int]`
- **Files modified:** src/bot/config.py
- **Verification:** All 12 config tests pass including comma-separated, empty, and default cases
- **Committed in:** 91c3793

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Implementation approach changed for pydantic-settings compatibility. The external API (`settings.allowed_channel_ids`) returns `list[int]` as planned -- only the internal storage mechanism differs.

## Issues Encountered
None beyond the pydantic-settings parsing issue documented above.

## User Setup Required
None - no external service configuration required. New env vars documented in .env.example.

## Next Phase Readiness
- Config fields ready for slash command handler to validate channels against allowlist
- System prompts ready to produce topic-grouped output format
- Embed formatter ready to receive LLM output and build Discord embeds
- Plan 02-02 (slash command) can wire these components together

---
*Phase: 02-on-demand-summarization*
*Completed: 2026-03-27*
