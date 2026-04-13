---
phase: 12-refine-the-summary-the-bot-produces
plan: 01
subsystem: summarizer
tags: [llm-prompts, summarization, volume-awareness]
dependency_graph:
  requires: []
  provides: [SummaryResult-dataclass, volume-preamble, refined-prompts]
  affects: [post_summary-command, overnight-scheduler, plan-02-embed-footer]
tech_stack:
  added: []
  patterns: [volume-tiered-prompting, dataclass-return-type]
key_files:
  created: []
  modified:
    - src/bot/summarizer.py
    - src/bot/commands/post_summary.py
    - src/bot/scheduling/overnight.py
    - tests/test_summarizer.py
decisions:
  - "Volume thresholds: <=30 LOW, 31-150 MEDIUM, >150 HIGH"
  - "Total message count used for all chunks in two-pass (not per-chunk)"
  - "SummaryResult dataclass added at module level for Plan 02 consumption"
metrics:
  duration: "~9 minutes"
  completed: "2026-04-13"
  tasks: 2
  files: 4
---

# Phase 12 Plan 01: Rewrite System Prompts and Add Volume-Aware Summarization

Rewrote SUMMARY_SYSTEM_PROMPT and MERGE_SYSTEM_PROMPT to enforce all content/tone decisions (D-01 through D-07, D-09 through D-11, D-13), added volume-tiered preamble function for D-12, and introduced SummaryResult dataclass for Plan 02 footer stats.

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| `07e3cfb` | test | Add failing tests for prompt content, SummaryResult, and metadata |
| `9af4af4` | feat | Rewrite system prompts and add SummaryResult dataclass |
| `200f4aa` | test | Add failing tests for volume-aware preamble |
| `af7c8d2` | feat | Add volume-aware summarization preamble |

## Task Results

### Task 1: Rewrite system prompts and add SummaryResult dataclass

- Replaced SUMMARY_SYSTEM_PROMPT with structured Output Rules and Input Signal Reference sections
- Replaced MERGE_SYSTEM_PROMPT with announcement consolidation and engagement ordering rules
- Added SummaryResult dataclass (text, message_count, participant_count) at module level
- Changed summarize_channel return type from str to SummaryResult
- Updated callers in post_summary.py and overnight.py for new return type
- 17 tests pass including 10 new TestPromptContent and TestSummaryResult tests

### Task 2: Add volume-aware summarization preamble

- Added _volume_context() function with LOW/MEDIUM/HIGH thresholds (<=30, 31-150, >150)
- Prepends volume preamble to user message text in both single-pass and two-pass paths
- Uses total message count for all chunks in two-pass (not per-chunk count)
- Added total_message_count parameter to summarize_messages()
- 10 new TestVolumeContext tests (27 total pass)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated callers of summarize_channel for SummaryResult return type**
- **Found during:** Task 1
- **Issue:** post_summary.py and overnight.py assigned summarize_channel result to summary_text expecting str, but it now returns SummaryResult
- **Fix:** Changed both callers to extract .text from SummaryResult
- **Files modified:** src/bot/commands/post_summary.py, src/bot/scheduling/overnight.py
- **Commit:** 9af4af4

## Decisions Made

1. Volume thresholds set at <=30 (LOW), 31-150 (MEDIUM), >150 (HIGH) messages -- matches research recommendations
2. Total message count passed to all chunks in two-pass mode to give LLM accurate volume calibration
3. SummaryResult is a plain dataclass (not pydantic) to match existing ProcessedMessage pattern

## Verification

- All 27 tests pass: `PYTHONPATH=src python -m pytest tests/test_summarizer.py -v`
- SUMMARY_SYSTEM_PROMPT enforces D-01 through D-07, D-09, D-10, D-11, D-13
- MERGE_SYSTEM_PROMPT consolidates Announcements and enforces tone rules
- _volume_context() returns correct tier for boundary values
- summarize_channel() returns SummaryResult with correct metadata

## Self-Check: PASSED

All 4 files found. All 4 commits verified.
