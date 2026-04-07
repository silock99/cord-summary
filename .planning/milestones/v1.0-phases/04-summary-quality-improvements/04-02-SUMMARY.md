---
phase: 04-summary-quality-improvements
plan: 02
subsystem: pipeline
tags: [chunker, reply-chains, system-prompts, popularity, signal-markers]
dependency_graph:
  requires: [enriched-processed-message]
  provides: [reply-chain-formatting, popularity-computation, signal-aware-prompts]
  affects: [src/bot/pipeline/chunker.py, src/bot/summarizer.py, tests/test_chunker.py]
tech_stack:
  added: []
  patterns: [reply-tree-indentation, post-preprocessing-computation, signal-marker-prompts]
key_files:
  created: []
  modified:
    - src/bot/pipeline/chunker.py
    - src/bot/summarizer.py
    - tests/test_chunker.py
decisions:
  - "Reply indentation capped at depth 2 to keep LLM input readable"
  - "Messages with message_id=0 treated as roots for backward compatibility"
  - "Popularity threshold: 5+ reactions OR 5+ replies (per D-04)"
metrics:
  duration: 2m
  completed: "2026-04-03T08:48:45Z"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 3
---

# Phase 04 Plan 02: Reply Chain Formatting and Signal-Aware Prompts Summary

Reply-tree-aware chunk formatting with depth-2 indentation cap, post-preprocessing popularity computation, and rewritten system prompts with explicit signal marker instructions for [IMPORTANT], [POPULAR], reactions, indentation, attachments, and embeds.

## What Was Done

### Task 1: Add reply-chain-aware formatting to chunker (TDD)
**Commit:** `50b0083`

- Added `_render_replies` recursive helper for reply-chain indentation capped at depth 2
- Replaced flat `format_chunk_for_llm` with reply-tree-aware version using parent-child index
- Messages with `message_id=0` (old-style) treated as roots with no children -- backward compatible
- Orphan replies (parent not in chunk) render as root messages without indentation
- Added 7 new tests: reply indentation, depth cap at 2, missing parent, mixed roots/replies, [IMPORTANT] marker, [POPULAR] marker, reaction count marker
- All 16 chunker tests pass

### Task 2: Update system prompts and add reply count computation
**Commit:** `6c7fb5f`

- Rewrote `SUMMARY_SYSTEM_PROMPT` with explicit signal marker instructions: [IMPORTANT] requires verbatim inclusion, [POPULAR] gets priority, [N reactions] shows engagement, indented replies show conversation flow, attachment types and embed content explained
- Rewrote `MERGE_SYSTEM_PROMPT` with verbatim @here/@everyone preservation and popular topic prioritization
- Added reply count computation in `summarize_channel` using `Counter` -- counts replies per message_id
- Added popularity flagging: `is_popular = True` when `reply_count >= 5` or `reaction_count >= 5`
- All 86 tests pass

## Deviations from Plan

None -- plan executed exactly as written.

## Decisions Made

1. **Depth cap at 2**: Reply chains deeper than 2 levels flatten to depth-2 indentation to keep LLM input readable without losing structure.
2. **Backward-compatible root handling**: Messages with `message_id=0` (pre-Phase-4 format) are treated as roots with no children, ensuring existing tests pass unchanged.
3. **Post-preprocessing popularity**: `reply_count` and `is_popular` computed after the preprocessing loop in `summarize_channel`, as replies need a full pass across all messages.

## Known Stubs

None -- all functionality is fully wired.

## Verification

- All 86 tests pass: `uv run python -m pytest tests/ -x` exits 0
- Reply chains render indented in LLM input (verified by test_reply_indentation)
- Depth cap at 2 verified by test_reply_depth_cap_at_two
- Signal markers ([IMPORTANT], [POPULAR], reactions) appear in formatted output
- System prompts contain explicit instructions for all signal types
- No new dependencies added

## Self-Check: PASSED
