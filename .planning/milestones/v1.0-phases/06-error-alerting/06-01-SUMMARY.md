---
phase: "06"
plan: "01"
subsystem: error-alerting
tags: [config, alerting, DM, error-handling]
dependency_graph:
  requires: [bot.config.Settings, bot.scheduling.overnight]
  provides: [bot.alerting.send_error_alerts, admin_user_ids config]
  affects: [bot.commands.summary cooldown exemption]
tech_stack:
  added: []
  patterns: [admin DM alerting, batched error embeds]
key_files:
  created:
    - src/bot/alerting.py
  modified:
    - src/bot/config.py
    - src/bot/scheduling/overnight.py
    - src/bot/commands/summary.py
    - .env.example
decisions:
  - "D-14/D-15: COOLDOWN_EXEMPT_USER_IDS replaced by ADMIN_USER_IDS as single admin identity source"
  - "D-16: Empty admin list logs warning and skips DM, no crash"
metrics:
  duration: "1m"
  completed: "2026-04-04"
---

# Phase 06 Plan 01: Config Migration and Error Alerting Summary

Replaced COOLDOWN_EXEMPT_USER_IDS with ADMIN_USER_IDS across config, env, and commands; created standalone alerting module that DMs batched error embeds to admins instead of posting red embeds to the summary channel.

## What Was Done

### Task 1: Config migration and error alerting module (a0fee9e)
- Removed `cooldown_exempt_user_ids_raw` field and computed property from Settings
- Added `admin_user_ids_raw` field (alias ADMIN_USER_IDS) with same comma-separated parsing pattern
- Created `src/bot/alerting.py` with `send_error_alerts()` async function
  - Reads admin IDs from `bot.settings.admin_user_ids`
  - Builds numbered error list as Discord embed (red, timestamped)
  - Truncates description at 4096 chars
  - Per-user error handling: NotFound, Forbidden, generic Exception
  - Empty admin list logs warning and returns silently
- Updated `.env.example`: replaced COOLDOWN_EXEMPT_USER_IDS with ADMIN_USER_IDS

### Task 2: Wire error alerting into overnight scheduler (7938d75)
- Added `from bot.alerting import send_error_alerts` import to overnight.py
- Replaced 8-line red error embed block with single `await send_error_alerts(self.bot, label, errors)` call
- Enhanced `_on_overnight_error` to DM admins on task-level failures
- Enhanced `_on_hourly_error` to DM admins on task-level failures
- Updated `summary.py` cooldown check from `cooldown_exempt_user_ids` to `admin_user_ids`

## Deviations from Plan

None - plan executed exactly as written.

## Decisions Made

1. **ADMIN_USER_IDS as single admin identity** - Replaces COOLDOWN_EXEMPT_USER_IDS; used for error DMs, cooldown exemption, and future /post-summary access
2. **Silent fallback on empty admin list** - Logs warning instead of raising, keeps bot running when no admins configured

## Verification Results

- alerting module imports successfully
- Settings.admin_user_ids returns empty list when unset
- No references to `cooldown_exempt_user_ids` remain in src/
- overnight.py and summary.py parse without syntax errors

## Known Stubs

None.

## Self-Check: PASSED

All 5 key files found. Both commit hashes (a0fee9e, 7938d75) verified.
