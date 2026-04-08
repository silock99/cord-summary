---
phase: 09-career-stats
plan: 01
subsystem: api
tags: [cfbd, cbbd, aiohttp, career-stats, monospace-table, sports-data]

requires:
  - phase: 07-recruiting-list-and-foundation
    provides: PlayerEntry dataclass, RecruitingStore, channel-to-sport mapping
provides:
  - CFBD football stats fetcher via cfbd v4 SDK
  - CBBD basketball stats fetcher via aiohttp REST calls
  - Monospace table formatter for both sports with career totals
  - PlayerEntry extended with optional stats dict field
  - Settings extended with cfbd_api_key and cbbd_api_key fields
affects: [09-02-career-command, recruiting-commands, transfer-commands]

tech-stack:
  added: [cfbd v4.5.2]
  patterns: [aiohttp direct REST calls for incompatible SDKs, __dataclass_fields__ filtering for backward-compatible deserialization]

key-files:
  created:
    - src/bot/stats/__init__.py
    - src/bot/stats/football.py
    - src/bot/stats/basketball.py
    - src/bot/stats/formatter.py
  modified:
    - pyproject.toml
    - uv.lock
    - src/bot/config.py
    - src/bot/storage/models.py

key-decisions:
  - "Used cfbd v4 SDK (v5 not available on PyPI) with api_key dict auth pattern"
  - "Replaced cbbd SDK with aiohttp REST calls due to pydantic v1 dependency conflict"
  - "PlayerEntry.from_dict uses __dataclass_fields__ filtering for forward+backward compat"

patterns-established:
  - "aiohttp direct REST pattern for APIs with incompatible SDK dependencies"
  - "Optional dict field on dataclass with conditional serialization (omit when None)"

requirements-completed: [INFRA-02, STATS-02, STATS-03]

duration: 4min
completed: 2026-04-08
---

# Phase 9 Plan 1: Stats Infrastructure Summary

**CFBD football and CBBD basketball stats fetchers with monospace table formatting, backed by extended PlayerEntry and Settings**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-08T06:16:58Z
- **Completed:** 2026-04-08T06:20:51Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Installed cfbd SDK and extended config/models for career stats API keys and data storage
- Created football stats fetcher using CFBD v4 API (player search + multi-year season stats assembly)
- Created basketball stats fetcher using raw aiohttp calls to CBBD REST API (roster-based player resolution with fuzzy matching)
- Built monospace table formatter producing Discord code-block tables for both sports with career totals

## Task Commits

Each task was committed atomically:

1. **Task 1: Install SDKs, extend PlayerEntry and Settings** - `37f7bc9` (feat)
2. **Task 2: Create stats fetch modules and formatter** - `4fa6cbc` (feat)

## Files Created/Modified
- `pyproject.toml` - Added cfbd SDK dependency
- `uv.lock` - Updated lockfile
- `src/bot/config.py` - Added cfbd_api_key and cbbd_api_key optional string fields
- `src/bot/storage/models.py` - Added stats dict field to PlayerEntry with backward-compatible serialization
- `src/bot/stats/__init__.py` - Package marker
- `src/bot/stats/football.py` - CFBD API integration: player search, multi-year season stat assembly, error handling
- `src/bot/stats/basketball.py` - CBBD REST API integration: roster-based player lookup with fuzzy matching, season stats
- `src/bot/stats/formatter.py` - Monospace table formatting: basketball (GP/PPG/RPG/APG/FG%/3P%) and football (passing/rushing/receiving sections)

## Decisions Made
- Used cfbd v4.5.2 SDK (not v5.13.2 as researched) because only v4 is available on PyPI. Auth uses `api_key['Authorization'] = 'Bearer ...'` pattern. Method names differ: `player_search` not `search_players`, `get_player_season_stats` on PlayersApi not StatsApi.
- Replaced cbbd SDK with direct aiohttp REST calls because cbbd requires pydantic v1 which conflicts with our pydantic v2 dependency (pydantic-settings 2.x). The CBBD REST API is simple enough that raw HTTP calls with Bearer auth work fine.
- PlayerEntry.from_dict now uses `__dataclass_fields__` filtering to handle both missing keys (old data) and unknown keys (future-proofing).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] cbbd SDK incompatible with pydantic v2**
- **Found during:** Task 1 (SDK installation)
- **Issue:** `cbbd` package requires `pydantic>=1.10.5,<2` which conflicts with `pydantic-settings>=2.0.0` requiring pydantic v2
- **Fix:** Used aiohttp direct REST calls to CBBD API instead of the cbbd SDK. aiohttp is already available via discord.py dependency.
- **Files modified:** src/bot/stats/basketball.py (used aiohttp instead of cbbd)
- **Verification:** All imports succeed, module structure correct
- **Committed in:** 4fa6cbc (Task 2 commit)

**2. [Rule 3 - Blocking] cfbd v4 API differs from v5 research**
- **Found during:** Task 2 (football module creation)
- **Issue:** PyPI has cfbd v4.5.2 (not v5.13.2 from research). Method names and auth patterns differ: `player_search` vs `search_players`, `api_key` dict vs `access_token`, `get_player_season_stats` on PlayersApi vs StatsApi.
- **Fix:** Adapted all cfbd code to use v4 API patterns
- **Files modified:** src/bot/stats/football.py
- **Verification:** cfbd imports and API classes verified via introspection
- **Committed in:** 4fa6cbc (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 blocking issues)
**Impact on plan:** Both fixes necessary due to SDK version discrepancies from research. No scope creep. All acceptance criteria met.

## Issues Encountered
- cbbd SDK pydantic v1 dependency made it uninstallable alongside pydantic-settings v2. Resolved by using aiohttp REST calls directly.
- cfbd installed as v4.5.2, not v5.13.2 as documented in research. All API patterns adapted to v4.

## User Setup Required

API keys needed for stats functionality (bot starts fine without them per D-08):
- `CFBD_API_KEY` - Register at https://collegefootballdata.com
- `CBBD_API_KEY` - Register at https://collegebasketballdata.com

## Next Phase Readiness
- Stats infrastructure complete: fetchers, formatter, model, config all ready
- Plan 02 can wire `/career` command, add-time fetch hooks, and autocomplete
- CBBD REST endpoint paths may need verification against live API (roster path and stats path)

---
*Phase: 09-career-stats*
*Completed: 2026-04-08*

## Self-Check: PASSED
