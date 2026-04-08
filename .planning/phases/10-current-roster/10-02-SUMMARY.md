---
phase: 10-current-roster
plan: 02
subsystem: roster-commands
tags: [slash-commands, roster, import, client-wiring]
dependency_graph:
  requires: [10-01]
  provides: [roster-import-command, roster-list-command, roster-store-in-client, career-roster-search]
  affects: []
tech_stack:
  added: []
  patterns: [replace-mode roster import, empty API safety guard, fire-and-forget stats fetch]
key_files:
  created:
    - src/bot/commands/roster.py
  modified:
    - src/bot/client.py
    - src/bot/commands/career.py
decisions:
  - Roster import uses replace mode with empty-response safety guard
  - Stats fetched per player during import with fire-and-forget error handling
  - Progress update at 50% for rosters with 20+ players
metrics:
  duration: 2m
  completed: 2026-04-08
---

# Phase 10 Plan 02: Roster Import/List Commands and Client Wiring Summary

/roster-import and /roster-list slash commands with roster store in client and career command searching all three stores (recruit, transfer, roster).

## What Was Done

### Task 1: Create roster commands module
- Created `src/bot/commands/roster.py` with `register_roster_commands(bot)` function
- `/roster-import`: defers ephemeral, fetches roster from CFBD/CBBD API, replaces sport data with empty-response safety guard, fetches stats per player (fire-and-forget), saves once after loop, reports count
- `/roster-list`: displays players alphabetically by name, multi-embed split at 25 fields, shows name/position/jersey/class per D-15 format
- Editor/admin permission on import, public access on list
- Error handler registered on both commands
- **Commit:** ac6f26b
- **Files:** src/bot/commands/roster.py

### Task 2: Wire roster store into client and update career command
- Added `roster_store = RecruitingStore(Path("data/roster.json"))` to SummaryBot.__init__
- Added `self.roster_store.load()` and `register_roster_commands(self)` to setup_hook
- Updated /stats command to search all three stores (recruit + transfer + roster)
- Updated autocomplete to include roster store players
- Updated player parameter description to mention roster
- **Commit:** 0299819
- **Files:** src/bot/client.py, src/bot/commands/career.py

## Deviations from Plan

None - plan executed exactly as written.

## Decisions Made

1. **Replace mode with safety guard** -- empty API response preserves existing roster rather than wiping it
2. **Fire-and-forget stats** -- individual player stats failures do not block import; count reported at end
3. **50% progress update** -- only for rosters with 20+ players to avoid unnecessary API calls

## Verification Results

- `from bot.commands.roster import register_roster_commands`: PASSED
- `from bot.client import SummaryBot`: PASSED
- career.py AST parse: PASSED
- roster.py contains both slash commands: PASSED
- career.py searches roster_store in stats and autocomplete: PASSED

## Known Stubs

None -- all functions are fully implemented with proper error handling.

## Self-Check: PASSED

- All 3 source files exist on disk
- Commit ac6f26b found in git log
- Commit 0299819 found in git log
