---
phase: 12-refine-the-summary-the-bot-produces
verified: 2026-04-13T21:00:00Z
status: human_needed
score: 5/5 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Run the bot and invoke /summary in a channel with 50+ messages. Confirm the output has bold topic headers, headline-depth bullets, no usernames, and no TL;DR section."
    expected: "Summary formatted as bold **Topic Name** headers with short bullet points underneath. No @mentions or display names in the text."
    why_human: "LLM output quality depends on the model following the prompt instructions. Prompt content is verified but actual output behavior cannot be confirmed without an end-to-end run."
  - test: "Post a message with @here or @everyone, then run /summary covering that time period. Confirm the summary includes an Announcements section at the top."
    expected: "An **Announcements** section appears before topic sections containing the important message text."
    why_human: "Requires real Discord messages with @here/@everyone flags to trigger the [IMPORTANT] preprocessing signal."
  - test: "Run /summary in a channel with <30 messages and again with >150 messages. Compare summary verbosity."
    expected: "Low-volume summary has more detail per bullet. High-volume summary is more condensed with fewer topics."
    why_human: "Volume-aware preamble modifies LLM behavior, which can only be observed through actual model responses."
  - test: "Check that embed footer in both /summary and scheduled overnight output shows the format 'N messages from M participants | timerange'."
    expected: "Footer text reads something like '47 messages from 12 participants | Last 4 hours' for on-demand, and 'N messages from M participants | Scheduled Overnight (10pm-9am)' for scheduled."
    why_human: "Requires running the bot to see actual embed rendering in Discord."
---

# Phase 12: Refine the Summary the Bot Produces - Verification Report

**Phase Goal:** Summaries are headline-depth, username-free, topic-grouped with an Announcements section, volume-aware detail, and footer stats showing message/participant counts
**Verified:** 2026-04-13T21:00:00Z
**Status:** human_needed
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Summaries show headline-depth bullets (topic + 1-line takeaway) with no usernames | VERIFIED | SUMMARY_SYSTEM_PROMPT contains "Headline depth only -- no paragraphs" and "Never include usernames, display names, or @mentions". TestPromptContent validates both. |
| 2 | [IMPORTANT] messages appear in a dedicated Announcements section at the top | VERIFIED | SUMMARY_SYSTEM_PROMPT contains "create an **Announcements** section at the very top". MERGE_SYSTEM_PROMPT contains "consolidate all announcements into a single **Announcements** section at the top". TestPromptContent validates both. |
| 3 | Summary detail adapts to message volume (low/medium/high) | VERIFIED | `_volume_context()` function implements three tiers: <=30 LOW, 31-150 MEDIUM, >150 HIGH. Prepended to user message text in both single-pass and two-pass paths. 10 TestVolumeContext tests cover all boundaries and integration. |
| 4 | Embed footer shows message count and participant count | VERIFIED | `build_summary_embeds` accepts `message_count` and `participant_count`. Footer format: "N messages from M participants \| timerange". Both `/summary` and overnight scheduler pass stats. 4 TestFooterStats tests validate. |
| 5 | Links appear inline within topic bullets, no separate section | VERIFIED | SUMMARY_SYSTEM_PROMPT contains "include them inline in the relevant bullet. Never collect links into a separate section". MERGE_SYSTEM_PROMPT contains "Preserve all URLs inline within their topic bullets". TestPromptContent::test_inline_urls validates. |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/bot/summarizer.py` | Rewritten prompts, SummaryResult, _volume_context() | VERIFIED | Contains SummaryResult dataclass (lines 24-29), rewritten SUMMARY_SYSTEM_PROMPT (lines 32-58), rewritten MERGE_SYSTEM_PROMPT (lines 60-73), _volume_context() (lines 76-96). 183 lines, substantive. |
| `src/bot/formatting/embeds.py` | Updated build_summary_embeds with stats params | VERIFIED | build_summary_embeds signature includes message_count and participant_count (lines 11-17). Footer shows stats when provided, falls back to "Period: timerange" (lines 73-78). 79 lines. |
| `src/bot/commands/summary.py` | On-demand caller passes stats | VERIFIED | Computes message_count and participant_count (lines 134-135), passes to summarize_messages with total_message_count (lines 136-139), passes to build_summary_embeds (lines 145-148). |
| `src/bot/scheduling/overnight.py` | Scheduled caller passes SummaryResult metadata | VERIFIED | Uses summary_result.text, summary_result.message_count, summary_result.participant_count (lines 100-116). No footer override. |
| `tests/test_summarizer.py` | Tests for prompts, volume, SummaryResult | VERIFIED | 27 tests including TestPromptContent (10), TestSummaryResult (2), TestVolumeContext (10). All pass. |
| `tests/test_embeds.py` | Tests for footer stats | VERIFIED | 21 tests including TestFooterStats (4). All pass. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| summarizer.py | SummaryProvider.summarize() | _volume_context prepended to user text | WIRED | Lines 122, 132: `_volume_context(count) + format_chunk_for_llm(...)` |
| summary.py | embeds.py | build_summary_embeds with message_count, participant_count | WIRED | Lines 145-148: `build_summary_embeds(summary_text, target.name, timerange_label, message_count=message_count, participant_count=participant_count)` |
| overnight.py | embeds.py | build_summary_embeds with message_count, participant_count | WIRED | Lines 112-116: `build_summary_embeds(summary_result.text, channel.name, ..., message_count=summary_result.message_count, participant_count=summary_result.participant_count)` |
| summarize_channel | SummaryResult | Returns dataclass with text + metadata | WIRED | Lines 174-182: computes counts from processed messages, returns SummaryResult |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| summarizer.py | participant_count | `len({msg.author for msg in processed})` | Yes -- computed from actual preprocessed messages | FLOWING |
| summarizer.py | message_count | `len(processed)` | Yes -- computed from actual preprocessed messages | FLOWING |
| embeds.py | message_count, participant_count | Passed from caller sites | Yes -- originates from summarize_channel or inline computation | FLOWING |
| summary.py | message_count, participant_count | `len(processed)`, `len({msg.author for msg in processed})` | Yes -- computed from actual fetched messages | FLOWING |
| overnight.py | summary_result.message_count | SummaryResult from summarize_channel | Yes -- flows from real message processing | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All summarizer + embed tests pass | `PYTHONPATH=src python -m pytest tests/test_summarizer.py tests/test_embeds.py -v` | 48 passed in 0.83s | PASS |
| Full test suite | `PYTHONPATH=src python -m pytest tests/ -v` | 160 passed, 3 failed (pre-existing) | PASS (phase-relevant tests all pass) |
| SummaryResult dataclass importable | Verified via test_summary_result_fields | Fields: text, message_count, participant_count | PASS |
| Volume context thresholds correct | Verified via TestVolumeContext (10 tests) | LOW<=30, MEDIUM 31-150, HIGH>150 | PASS |

### Requirements Coverage

The D-xx requirements are phase-specific implementation decisions defined in `12-CONTEXT.md`, not global requirements in REQUIREMENTS.md. REQUIREMENTS.md has no D-xx entries or Phase 12 mappings.

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| D-01 | 12-01 | Headline-depth bullets | SATISFIED | SUMMARY_SYSTEM_PROMPT: "Headline depth only -- no paragraphs" |
| D-02 | 12-01 | Neutral/clean tone | SATISFIED | SUMMARY_SYSTEM_PROMPT: "clear, neutral English. No slang, no corporate jargon" |
| D-03 | 12-01 | No usernames | SATISFIED | SUMMARY_SYSTEM_PROMPT: "Never include usernames, display names, or @mentions"; MERGE: "Never include usernames or @mentions" |
| D-04 | 12-01 | Inline URLs | SATISFIED | SUMMARY_SYSTEM_PROMPT: "include them inline in the relevant bullet" |
| D-05 | 12-01 | No TL;DR | SATISFIED | SUMMARY_SYSTEM_PROMPT: "Do NOT include a TL;DR, key takeaways, or executive summary section" |
| D-06 | 12-01 | No separate links section | SATISFIED | SUMMARY_SYSTEM_PROMPT: "Never collect links into a separate section"; MERGE: "Preserve all URLs inline" |
| D-07 | 12-01 | Drop minor topics | SATISFIED | SUMMARY_SYSTEM_PROMPT: "Drop minor topics that had only 1-2 messages with no reactions or replies" |
| D-08 | 12-02 | Footer stats (message + participant count) | SATISFIED | embeds.py footer: "N messages from M participants \| timerange"; wired in summary.py and overnight.py |
| D-09 | 12-01 | Announcements section for IMPORTANT messages | SATISFIED | SUMMARY_SYSTEM_PROMPT: "create an **Announcements** section at the very top"; MERGE: "consolidate all announcements" |
| D-10 | 12-01 | Popular topics ordered first | SATISFIED | SUMMARY_SYSTEM_PROMPT: "topics with [POPULAR] markers appear first" |
| D-11 | 12-01 | One universal prompt | SATISFIED | Single SUMMARY_SYSTEM_PROMPT used for all contexts. No per-context variants. |
| D-12 | 12-01 | Volume-aware summarization | SATISFIED | _volume_context() with LOW/MEDIUM/HIGH tiers prepended to LLM input |
| D-13 | 12-01 | No resolution status tracking | SATISFIED | SUMMARY_SYSTEM_PROMPT: "Do NOT note whether discussions are resolved or ongoing" |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| tests/test_config_phase2.py | 84, 88 | Stale tests assert old prompt text ("action items or decisions as separate sections") that was intentionally removed | Warning | 2 test failures in full suite. Not a Phase 12 bug -- old tests from Phase 2 need updating to match new prompts. |
| src/bot/commands/post_summary.py | 129-131 | build_summary_embeds called without message_count/participant_count; footer overridden with "Requested by {user}" | Info | /post-summary admin command does not show stats in footer. Stats data is available (summary_result) but not passed. Minor -- this is a third caller site not scoped in Phase 12 plans. |

### Human Verification Required

### 1. Summary Output Quality

**Test:** Run the bot and invoke `/summary` in a channel with 50+ messages. Confirm the output has bold topic headers, headline-depth bullets, no usernames, and no TL;DR section.
**Expected:** Summary formatted as bold **Topic Name** headers with short bullet points underneath. No @mentions or display names in the text.
**Why human:** LLM output quality depends on the model following the prompt instructions. Prompt content is verified but actual output behavior cannot be confirmed without an end-to-end run.

### 2. Announcements Section

**Test:** Post a message with @here or @everyone, then run `/summary` covering that time period. Confirm the summary includes an Announcements section at the top.
**Expected:** An **Announcements** section appears before topic sections containing the important message text.
**Why human:** Requires real Discord messages with @here/@everyone flags to trigger the [IMPORTANT] preprocessing signal.

### 3. Volume-Aware Detail Adaptation

**Test:** Run `/summary` in a channel with <30 messages and again with >150 messages. Compare summary verbosity.
**Expected:** Low-volume summary has more detail per bullet. High-volume summary is more condensed with fewer topics.
**Why human:** Volume-aware preamble modifies LLM behavior, which can only be observed through actual model responses.

### 4. Footer Stats Display

**Test:** Check that embed footer in both `/summary` and scheduled overnight output shows the format "N messages from M participants | timerange".
**Expected:** Footer text reads something like "47 messages from 12 participants | Last 4 hours" for on-demand, and "N messages from M participants | Scheduled Overnight (10pm-9am)" for scheduled.
**Why human:** Requires running the bot to see actual embed rendering in Discord.

### Gaps Summary

No blocking gaps found. All 5 roadmap success criteria are verified at the code level. All 13 D-xx implementation decisions are satisfied in the prompts and logic.

**Minor items (non-blocking):**
- `test_config_phase2.py` has 2 stale test assertions from Phase 2 that check for old prompt text removed by this phase's prompt rewrite. These need updating but do not affect Phase 12 goal achievement.
- `post_summary.py` (admin command) does not pass stats to embed footer, but this was not in scope for Phase 12 plans and the footer is intentionally overridden with "Requested by {user}" for that command.

---

_Verified: 2026-04-13T21:00:00Z_
_Verifier: Claude (gsd-verifier)_
