# Deferred Items — Phase 13

Pre-existing issues discovered during Phase 13 execution that are out of scope
for this phase.

## Test: test_summary_prompt_no_action_items (tests/test_config_phase2.py)

- **Status:** Failing BEFORE Phase 13 work began (regression from Phase 12 summarizer changes).
- **Symptom:** `SUMMARY_SYSTEM_PROMPT` no longer contains the string
  "Do not extract action items or decisions as separate sections".
- **Why deferred:** Unrelated to Google Sheet ingress. Should be addressed
  in a Phase 12 follow-up or test-update plan — either re-introduce the
  sentence in the system prompt or update the test to match the current
  prompt contract.
- **Discovered:** 2026-04-14 during Phase 13 Plan 01 full-suite run.
