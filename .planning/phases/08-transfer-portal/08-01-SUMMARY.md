---
phase: 08-transfer-portal
plan: 01
subsystem: storage
tags: [data-model, caching, tdd]
dependency_graph:
  requires: []
  provides: [PlayerEntry-type-field, position-filtering, TTLCache-module]
  affects: [recruiting_store, models, cache]
tech_stack:
  added: []
  patterns: [TTL-cache-with-monotonic-clock, backward-compatible-dataclass-evolution]
key_files:
  created:
    - src/bot/storage/cache.py
    - tests/test_cache.py
  modified:
    - src/bot/storage/models.py
    - src/bot/storage/recruiting_store.py
    - tests/test_recruiting_store.py
decisions:
  - "PlayerEntry.type defaults to 'target' for backward-compatible deserialization of existing JSON"
  - "TTLCache uses time.monotonic() to avoid wall-clock drift issues"
  - "Position filtering is case-insensitive to match existing name-matching convention"
metrics:
  duration: 2m
  completed: "2026-04-08T00:44:00Z"
  tasks_completed: 1
  tasks_total: 1
  test_count: 36
  test_passed: 36
---

# Phase 8 Plan 1: Data Model Extension and TTL Cache Summary

Extended PlayerEntry with type field, added position filtering to RecruitingStore, and built TTLCache module using TDD -- backward-compatible deserialization preserves existing JSON data.

## Task Results

| Task | Name | Commit(s) | Files |
|------|------|-----------|-------|
| 1 (RED) | Failing tests for type field, position filter, TTLCache | bd7dc86 | tests/test_recruiting_store.py, tests/test_cache.py |
| 1 (GREEN) | Implement PlayerEntry.type, position filter, TTLCache | a54c75b | src/bot/storage/models.py, src/bot/storage/recruiting_store.py, src/bot/storage/cache.py |

## Changes Made

### PlayerEntry (src/bot/storage/models.py)
- Added `type: str = "target"` field after `added_at`
- `to_dict()` now includes `"type"` key
- `from_dict()` handles old dicts without `type` key via dataclass default

### RecruitingStore (src/bot/storage/recruiting_store.py)
- `add_player()` accepts `player_type: str = "target"` parameter, passes to PlayerEntry constructor
- `list_players()` accepts `position: str | None = None` parameter for case-insensitive filtering

### TTLCache (src/bot/storage/cache.py)
- New module with `CacheEntry` dataclass and `TTLCache` class
- Default TTL of 900 seconds (15 minutes) for future CFBD API response caching
- Uses `time.monotonic()` for reliable expiration checks
- Methods: `get()`, `set()`, `invalidate()`, `clear()`

## Test Coverage

- 19 new tests added (11 in test_recruiting_store.py, 7 in test_cache.py, 1 existing-behavior preservation)
- 17 existing tests continue to pass unchanged
- 36 total tests passing

## Deviations from Plan

None -- plan executed exactly as written.

## Known Stubs

None -- all code is fully functional with no placeholders.
