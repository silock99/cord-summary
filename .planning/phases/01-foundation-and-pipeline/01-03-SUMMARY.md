---
phase: 01-foundation-and-pipeline
plan: 03
subsystem: ai
tags: [openai, llm, provider-protocol, summarization, two-pass-chunking]

requires:
  - phase: 01-foundation-and-pipeline/01
    provides: "ProcessedMessage model, SummaryError, Settings with LLM config"
provides:
  - "SummaryProvider Protocol for pluggable LLM backends"
  - "OpenAISummaryProvider with error handling and configurable base_url"
  - "summarize_messages orchestrator with single-pass and two-pass modes"
  - "summarize_channel full pipeline (fetch -> preprocess -> summarize)"
affects: [02-bot-commands, 02-scheduling]

tech-stack:
  added: [openai-sdk]
  patterns: [provider-protocol, two-pass-summarization, error-mapping]

key-files:
  created:
    - src/bot/providers/base.py
    - src/bot/providers/openai_provider.py
    - src/bot/providers/__init__.py
    - src/bot/summarizer.py
    - src/bot/pipeline/chunker.py
    - tests/test_summarizer.py
  modified: []

key-decisions:
  - "Provider Protocol uses @runtime_checkable for isinstance verification"
  - "OpenAI errors mapped to user-facing SummaryError with no retry (per D-11)"
  - "Two-pass merge uses separator-delimited period summaries for context"

patterns-established:
  - "Provider Protocol: any LLM backend implements summarize(text, prompt) -> str and close()"
  - "Error mapping: LLM SDK exceptions caught at provider boundary, re-raised as SummaryError"
  - "Two-pass summarization: chunk by time window -> summarize each -> merge summaries"

requirements-completed: [AI-01, AI-02, AI-03]

duration: 4min
completed: 2026-03-27
---

# Phase 01 Plan 03: AI Provider and Summarizer Summary

**Pluggable LLM provider protocol with OpenAI implementation and two-pass summarization orchestrator for large message sets**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-27T19:30:39Z
- **Completed:** 2026-03-27T19:34:22Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- SummaryProvider Protocol defined with summarize and close methods, runtime-checkable
- OpenAISummaryProvider wraps AsyncOpenAI with configurable base_url (D-03), model (D-02), and full error mapping to SummaryError (AI-03)
- Summarizer orchestrator handles single-pass (small sets) and two-pass chunked summarization (D-09) for large message sets
- Full pipeline function summarize_channel: fetch -> preprocess -> summarize

## Task Commits

Each task was committed atomically:

1. **Task 1: Provider protocol and OpenAI implementation** - `4959409` (feat)
2. **Task 2 RED: Failing summarizer tests** - `9554431` (test)
3. **Task 2 GREEN: Summarizer implementation** - `657c6eb` (feat)

## Files Created/Modified
- `src/bot/providers/base.py` - SummaryProvider Protocol with summarize and close methods
- `src/bot/providers/openai_provider.py` - OpenAI implementation with error handling for auth, rate limit, timeout, and generic API errors
- `src/bot/providers/__init__.py` - Public API exports for provider module
- `src/bot/summarizer.py` - Orchestrator with single-pass and two-pass summarization modes
- `src/bot/pipeline/chunker.py` - Time-window chunking, token estimation, and LLM formatting
- `tests/test_summarizer.py` - 5 tests covering empty, single-pass, two-pass, error propagation, and preprocessing

## Decisions Made
- Provider Protocol uses @runtime_checkable for isinstance verification at import time
- OpenAI errors mapped to user-facing SummaryError messages with no retry per D-11
- Two-pass merge input uses "Period N summary:" format with separator for clear context
- System prompts defined as module constants (SUMMARY_SYSTEM_PROMPT, MERGE_SYSTEM_PROMPT)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Created chunker.py for missing pipeline dependency**
- **Found during:** Task 2 (Summarizer implementation)
- **Issue:** Plan 02 (parallel wave) had not yet committed chunker.py; summarizer imports would fail
- **Fix:** Created src/bot/pipeline/chunker.py implementing the expected interface (estimate_tokens, needs_chunking, chunk_by_time_window, format_chunk_for_llm)
- **Files modified:** src/bot/pipeline/chunker.py
- **Verification:** All 26 tests pass (including plan 02's chunker tests)
- **Committed in:** 657c6eb (Task 2 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Chunker creation was necessary to unblock parallel execution. Implementation matches the interface spec from plan 02 and passes all plan 02 chunker tests.

## Issues Encountered
None beyond the blocking dependency handled above.

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all functions are fully implemented with real logic.

## Next Phase Readiness
- Provider interface ready for bot commands to use
- summarize_channel ready for slash command and scheduled task integration
- Any OpenAI-compatible endpoint can be used via base_url configuration

## Self-Check: PASSED

- All 6 created files verified on disk
- All 3 commit hashes verified in git log

---
*Phase: 01-foundation-and-pipeline*
*Completed: 2026-03-27*
