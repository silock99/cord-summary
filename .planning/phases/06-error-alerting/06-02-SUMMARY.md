---
phase: "06"
plan: "02"
subsystem: commands
tags: [slash-command, admin, discord, post-summary]
dependency_graph:
  requires:
    - phase: 06-01
      provides: admin_user_ids config field, alerting module
    - phase: 02-on-demand-summarization
      provides: TIMERANGE_CHOICES, TIMERANGE_LABELS, channel_autocomplete pattern
  provides:
    - /post-summary admin-only slash command
    - Public summary posting to summary channel
    - Thread support for manual summaries
  affects: [bot startup, command sync]
tech_stack:
  added: []
  patterns: [admin check decorator via app_commands.check, inline thread creation for non-overnight summaries]
key_files:
  created:
    - src/bot/commands/post_summary.py
  modified:
    - src/bot/client.py
key-decisions:
  - "D-07: Inline thread creation instead of reusing create_summary_thread to differentiate manual from overnight threads"
  - "D-13: CheckFailure error handler provides vague permission message to non-admins"
patterns-established:
  - "Admin-only command pattern: is_admin() decorator checking settings.admin_user_ids"
  - "Public summary posting pattern: ephemeral defer + public embed send to summary channel"
requirements-completed: []
duration: 2min
completed: 2026-04-04
---

# Phase 06 Plan 02: /post-summary Admin Command Summary

**Admin-only /post-summary slash command for public summary posting to the summary channel with thread support and CheckFailure error handling**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-04T07:25:52Z
- **Completed:** 2026-04-04T07:28:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Created /post-summary command with admin-only access via ADMIN_USER_IDS check
- Reuses TIMERANGE_CHOICES and channel_autocomplete from summary.py for consistency
- Posts public embeds to summary channel (or thread if use_threads=true) with "Requested by" footer
- Wired command registration into bot setup_hook before tree.sync

## Task Commits

Each task was committed atomically:

1. **Task 1: Create /post-summary command module** - `640ec2b` (feat)
2. **Task 2: Wire /post-summary into bot startup** - `204f742` (feat)

## Files Created/Modified
- `src/bot/commands/post_summary.py` - Admin-only /post-summary command with is_admin() decorator, channel autocomplete, public embed posting, thread support, and CheckFailure error handler
- `src/bot/client.py` - Added register_post_summary_command import and call in setup_hook

## Decisions Made
- Used inline thread creation (not create_summary_thread) to give manual summaries a distinct thread name format: "Summary -- #channel -- date" vs overnight's "Overnight Summary -- date"
- CheckFailure handler returns vague "You don't have permission" message -- no information disclosure about admin list

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## Known Stubs

None.

## User Setup Required
None - no external service configuration required. ADMIN_USER_IDS env var was already added in Plan 01.

## Next Phase Readiness
- /post-summary command ready for use once Plan 01 (config migration) is merged first
- Command depends on admin_user_ids field from Plan 01's Settings changes

## Self-Check: PASSED

All 3 key files found. Both commit hashes (640ec2b, 204f742) verified.

---
*Phase: 06-error-alerting*
*Completed: 2026-04-04*
