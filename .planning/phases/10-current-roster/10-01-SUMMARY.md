---
phase: 10-current-roster
plan: 01
subsystem: roster-data-model
tags: [data-model, api-integration, roster]
dependency_graph:
  requires: [09-01, 07-01]
  provides: [PlayerEntry.jersey_number, PlayerEntry.class_year, fetch_football_roster, fetch_basketball_roster]
  affects: [10-02]
tech_stack:
  added: []
  patterns: [CFBD TeamsApi roster fetch, CBBD /roster endpoint, class_year derivation from start_season]
key_files:
  created: []
  modified:
    - src/bot/storage/models.py
    - src/bot/stats/football.py
    - src/bot/stats/basketball.py
decisions:
  - jersey_number defaults to 0 (unknown), class_year defaults to empty string for backward compat
  - Football roster uses CFBD TeamsApi.get_roster with year-to-class mapping (1=Fr through 5=R-Sr)
  - Basketball roster derives class_year from start_season field via arithmetic
metrics:
  duration: 1m
  completed: 2026-04-08
---

# Phase 10 Plan 01: PlayerEntry Extension and Roster Fetch Functions Summary

Extend PlayerEntry with jersey_number/class_year fields and add roster fetch functions to football.py and basketball.py for CFBD and CBBD APIs.

## What Was Done

### Task 1: Extend PlayerEntry with jersey_number and class_year fields
- Added `jersey_number: int = 0` and `class_year: str = ""` fields to PlayerEntry dataclass
- Updated `to_dict()` to include both new fields in output
- Backward compatible: `from_dict()` uses `__dataclass_fields__` filtering so old JSON loads cleanly
- **Commit:** db2608e
- **Files:** src/bot/storage/models.py

### Task 2: Add roster fetch functions to football.py and basketball.py
- Added `fetch_football_roster(settings)` using `cfbd.TeamsApi.get_roster(team="Kansas", year=year)`
- Added `fetch_basketball_roster(settings)` using CBBD `/roster` endpoint with aiohttp
- Both return `list[dict]` with keys: name, position, jersey_number, class_year
- Football maps year int (1-5) to class abbreviation via YEAR_MAP
- Basketball derives class_year from start_season arithmetic
- Both gracefully return empty list on missing API key or error
- **Commit:** a11442e
- **Files:** src/bot/stats/football.py, src/bot/stats/basketball.py

## Deviations from Plan

None - plan executed exactly as written.

## Decisions Made

1. **jersey_number=0 as unknown sentinel** -- matches plan spec, 0 is not a valid jersey number in practice
2. **YEAR_MAP pattern** -- simple dict lookup for class year derivation, shared approach across both sports

## Verification Results

- PlayerEntry creation with defaults: PASSED
- to_dict() includes jersey_number and class_year: PASSED
- from_dict() backward compatibility with old data: PASSED
- Import of fetch_football_roster: PASSED
- Import of fetch_basketball_roster: PASSED

## Known Stubs

None -- all functions are fully implemented with proper error handling.

## Self-Check: PASSED

- All 3 modified files exist on disk
- Commit db2608e found in git log
- Commit a11442e found in git log
