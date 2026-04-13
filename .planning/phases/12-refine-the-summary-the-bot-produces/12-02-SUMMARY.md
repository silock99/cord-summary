---
phase: 12-refine-the-summary-the-bot-produces
plan: 02
subsystem: formatting
tags: [embeds, footer-stats, metadata, D-08]
dependency_graph:
  requires: [12-01]
  provides: [embed-footer-stats, caller-site-wiring]
  affects: [summary-command, overnight-scheduler, embeds]
tech_stack:
  added: []
  patterns: [optional-params-backward-compat, dataclass-result-wiring]
key_files:
  created: [conftest.py]
  modified: [src/bot/formatting/embeds.py, src/bot/commands/summary.py, src/bot/scheduling/overnight.py, tests/test_embeds.py]
decisions:
  - "Footer format: 'N messages from M participants | timerange' with fallback to 'Period: timerange'"
  - "Overnight scheduler footer override removed; stats now embedded via build_summary_embeds"
  - "On-demand /summary computes participant_count inline from processed messages"
metrics:
  duration: 6m
  completed: 2026-04-13
  tasks: 2
  files: 5
---

# Phase 12 Plan 02: Embed Footer Stats Summary

Stats footer wiring: message count and participant count displayed in embed footers for both on-demand and scheduled summaries, using SummaryResult metadata from Plan 01.

## What Was Done

### Task 1: Add stats parameters to embed building (TDD)

Added `message_count` and `participant_count` optional parameters to `build_summary_embeds()` and `_make_embed()`. When both are positive, footer shows "N messages from M participants | timerange". When omitted (defaults to 0), falls back to "Period: timerange" for backward compatibility.

Added 4 new tests in `TestFooterStats` class covering: stats footer, backward compat, continued embeds, empty summary.

### Task 2: Wire SummaryResult through caller sites

**summary.py:** Computes `message_count` and `participant_count` from processed messages before calling `summarize_messages`. Passes both to `build_summary_embeds`. Also passes `total_message_count` to `summarize_messages` for volume-aware preamble (Plan 01 feature).

**overnight.py:** Uses `summary_result.text`, `summary_result.message_count`, and `summary_result.participant_count` directly from the `SummaryResult` returned by `summarize_channel`. Removed the `embed.set_footer()` override that was clobbering stats (Pitfall 4 from RESEARCH.md resolved).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree sys.path conflict**
- **Found during:** Task 1 GREEN phase
- **Issue:** Editable install pointed to another parallel worktree's src/, causing tests to import old code without the new parameters
- **Fix:** Created `conftest.py` at project root that inserts this worktree's `src/` first in `sys.path` and clears cached bot module imports
- **Files created:** conftest.py
- **Commit:** 8f82e48

**2. [Rule 3 - Blocking] overnight.py already partially updated by Plan 01**
- **Found during:** Task 2
- **Issue:** Plan 01 agent had already changed `summarize_channel` call to use `summary_result` variable but left the old `build_summary_embeds` call and footer override
- **Fix:** Adapted edit to work with the partially-updated code (used `summary_result.text` etc. instead of introducing a new `result` variable)
- **Files modified:** src/bot/scheduling/overnight.py

### Pre-existing Test Failures (Out of Scope)

Two tests in `test_config_phase2.py` fail due to Plan 01's prompt rewrite removing the "Do not extract action items" text:
- `TestSystemPrompts::test_summary_prompt_no_action_items`
- `TestSystemPrompts::test_merge_prompt_no_action_items`

These are Plan 01 artifacts and not related to this plan's changes.

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 (RED) | af2814e | test(12-02): add failing tests for embed footer stats |
| 1 (GREEN) | 8f82e48 | feat(12-02): add message_count and participant_count to embed footer |
| 2 | ef9b0a5 | feat(12-02): wire stats through summary command and overnight scheduler |

## Verification

- 21/21 embed tests pass (including 4 new footer stats tests)
- 161/163 full suite tests pass (2 pre-existing failures from Plan 01 prompt rewrite)
- Footer shows "N messages from M participants | timerange" when stats provided
- Footer shows "Period: timerange" when stats omitted (backward compat)
- Overnight scheduler no longer overrides footer

## Known Stubs

None. All data paths are fully wired from SummaryResult through to embed footer.
