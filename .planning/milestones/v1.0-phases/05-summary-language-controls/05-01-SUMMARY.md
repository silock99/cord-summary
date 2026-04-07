---
phase: 05-summary-language-controls
plan: 01
subsystem: language-filter
tags: [language-controls, prompt-engineering, content-moderation]
dependency_graph:
  requires: []
  provides: [language-filter-module, blocklist-allowlist-files, prompt-guidelines-injection]
  affects: [summarizer-prompts, bot-startup]
tech_stack:
  added: []
  patterns: [module-level-cache, file-based-config, prompt-concatenation]
key_files:
  created:
    - src/bot/language_filter.py
    - blocklist.txt
    - allowlist.txt
    - tests/test_language_filter.py
  modified:
    - src/bot/summarizer.py
    - src/bot/client.py
decisions:
  - "D-02: Blocklist/allowlist as plain text files in project root for operator simplicity"
  - "D-05: String concatenation at runtime to append guidelines, no mutation of module constants"
  - "D-08: Missing files log warning and continue with empty guidelines (graceful degradation)"
metrics:
  duration: 2m
  completed: "2026-04-04T06:22:00Z"
---

# Phase 05 Plan 01: Language Filter Module and Prompt Integration Summary

Configurable language guidelines via blocklist.txt/allowlist.txt injected into both LLM system prompts at runtime with module-level caching and graceful degradation on missing files.

## What Was Built

### language_filter.py Module
- `load_terms(filepath)`: Reads text file, strips comments/blanks, returns term list. Logs warning on missing file.
- `parse_allowlist_entry(entry)`: Parses "term (reason)" format into tuple.
- `build_language_guidelines(blocked, allowed)`: Builds "## Language Guidelines" prompt section with blocked terms, exceptions, and fallback instruction.
- `load_language_config()`: Loads both files, builds guidelines, caches in module-level variable. Logs token estimate warning if >200 tokens.
- `get_language_guidelines()`: Returns cached guidelines string.

### Default Configuration Files
- `blocklist.txt`: 15 curated inappropriate terms with comment documentation.
- `allowlist.txt`: Format documentation with commented example entries (kill, execute, master, slave, cripple).

### Integration
- `summarizer.py`: All 3 `provider.summarize()` calls now use `summary_prompt` / `merge_prompt` local variables with guidelines appended. Module-level constants unchanged.
- `client.py`: `load_language_config()` called in `setup_hook()` before scheduler start.

## Task Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 (RED) | 4bf5150 | Failing tests for language filter module |
| 1 (GREEN) | 1d03027 | Language filter module, blocklist.txt, allowlist.txt, all 9 tests pass |
| 2 | 78a66ce | Integrate guidelines into summarizer prompts and bot startup |

## Test Results

14 tests pass: 9 language filter + 5 existing summarizer tests.

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None. All functions are fully implemented with real file I/O and caching.

## Self-Check: PASSED

All 6 files verified present. All 3 commit hashes verified in git log.
