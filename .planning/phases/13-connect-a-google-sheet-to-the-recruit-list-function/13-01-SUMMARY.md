---
phase: 13-connect-a-google-sheet-to-the-recruit-list-function
plan: 01
subsystem: transfer-targets / sheet-ingress
tags: [google-sheets, gspread, scheduler, tdd, phase-13]
requires:
  - bot.config.Settings
  - bot.alerting.send_error_alerts
  - bot.scheduling.overnight.OvernightScheduler (pattern)
  - bot.storage.recruiting_store.RecruitingStore
provides:
  - bot.storage.models.TransferTarget
  - bot.sources.sheets.SheetTransferTargetStore
  - bot.sources.sheets.map_rows_to_targets
  - bot.sources.sheets.self_heal_transfers_store
  - bot.scheduling.sheet_sync.SheetSyncScheduler
  - SummaryBot.sheet_target_store
  - SummaryBot.sheet_sync_scheduler
  - data/transfer_targets_basketball.json (runtime snapshot)
affects:
  - src/bot/config.py (+4 env-sourced fields, 1 computed property)
  - src/bot/storage/models.py (+TransferTarget dataclass, PlayerEntry untouched)
  - src/bot/client.py (wiring + self-heal + initial fetch + scheduler)
  - pyproject.toml / uv.lock (gspread 6.2.1 + transitives)
tech-stack:
  added:
    - gspread==6.2.1
    - google-auth (transitive)
    - google-auth-oauthlib (transitive)
    - requests (transitive)
  patterns:
    - Atomic JSON snapshot (tempfile + os.replace) — reuses RecruitingStore idiom
    - discord.ext.tasks.loop + before_loop(wait_until_ready) + error hook → send_error_alerts (mirrors OvernightScheduler)
    - asyncio.to_thread wrapping for sync gspread calls (non-blocking event loop)
    - Stale-cache-on-failure (never clear on refresh error)
key-files:
  created:
    - src/bot/sources/__init__.py
    - src/bot/sources/sheets.py
    - src/bot/scheduling/sheet_sync.py
    - tests/test_sheet_sync.py
    - data/.gitkeep
  modified:
    - pyproject.toml
    - uv.lock
    - src/bot/config.py
    - src/bot/storage/models.py
    - src/bot/client.py
decisions:
  - Use gspread.auth.READONLY_SCOPES exclusively (T-13-04) so a compromised key cannot mutate sheets.
  - On JSONDecodeError of SHEET_SERVICE_ACCOUNT_JSON, log fixed message only — never raw value / exception msg (T-13-01).
  - added_at preservation keyed on lowercased + whitespace-collapsed name (D-20) — survives cosmetic edits.
  - Fail-open initial fetch in setup_hook — snapshot continues to serve if first refresh errors; bot still boots (D-06 + D-08).
  - Self-heal only writes back when a removal occurred (skip needless I/O on clean state).
metrics:
  completed: 2026-04-14
  duration: ~15m
  tasks: 2
  tests_added: 12
  files_created: 5
  files_modified: 5
requirements:
  - TRANSFER-SHEET-01
  - TRANSFER-SHEET-02
  - TRANSFER-SHEET-03
  - TRANSFER-SHEET-04
  - TRANSFER-SHEET-07
---

# Phase 13 Plan 01: Google Sheet Ingress for Basketball Transfer Targets — Summary

Read-only hourly Google Sheet sync stands up `SheetTransferTargetStore` with atomic JSON snapshot, a tasks-loop scheduler that mirrors `OvernightScheduler`, and a one-shot self-heal that strips stale basketball+target entries from `transfers.json` so the sheet becomes the unambiguous source.

## What Changed

### Task 1 — Dependencies, Settings, Model (commit 7b85f52)

- `uv add gspread` pulled in **gspread 6.2.1** plus `google-auth`, `google-auth-oauthlib`, `requests` transitively.
- `src/bot/config.py` gained four env-sourced fields and one computed property:
  - `SHEET_SERVICE_ACCOUNT_JSON` (primary, inline JSON for Railway/nixpacks).
  - `SHEET_SERVICE_ACCOUNT_FILE` (optional fallback path for local dev).
  - `TRANSFER_TARGET_SHEET_ID` (defaults to the locked D-11 sheet).
  - `TRANSFER_TARGET_SHEET_TAB` (defaults to `Master List 2025` per D-12).
  - `sheet_service_account_info` computed property: inline JSON wins; else file path if present; else `None`. On JSONDecodeError the property logs the fixed string `"SHEET_SERVICE_ACCOUNT_JSON is not valid JSON"` — never the raw value or exception text (T-13-01).
- `src/bot/storage/models.py` gained the `TransferTarget` dataclass with 7 sheet-aligned fields (`name`, `position`, `former_school`, `height_weight`, `ku_interest_level`, `made_contact`, `notes`) plus ISO-timestamp `added_at`. `PlayerEntry` was intentionally left unmodified per D-14.

### Task 2 — Store, Scheduler, Wiring, Tests (commit 8cefc7d, TDD)

- `src/bot/sources/sheets.py`:
  - `map_rows_to_targets(rows)` skips the two metadata rows + header row (indices 0-2), maps the fixed 7-column order, skips rows whose `Name` is blank/whitespace (with debug log per T-13-08), pads short rows so indexing is safe.
  - `SheetTransferTargetStore` holds the in-memory list, atomic JSON snapshot at `data/transfer_targets_basketball.json` (tempfile + `os.replace` per T-13-06), and tracks `last_synced_at`. `apply_refresh` preserves `added_at` on normalized-name match (lowercased, whitespace-collapsed — D-20), and `refresh` is an async wrapper around the blocking gspread fetch via `asyncio.to_thread` (event loop never blocks).
  - `_build_gspread_client` always uses `gspread.auth.READONLY_SCOPES` (T-13-04).
  - `self_heal_transfers_store(store)` walks `store._data["basketball"]`, drops entries with `type == "target"`, and saves only when something actually changed.
- `src/bot/scheduling/sheet_sync.py`:
  - `SheetSyncScheduler` mirrors `OvernightScheduler` — `tasks.loop(hours=1)`, `before_loop(wait_until_ready)`, `error(_on_error)`.
  - `_on_error` logs only `type(error).__name__` + `str(error)` and pipes to `send_error_alerts("Transfer Target Sheet Sync", [...])`. Comment in the module reminds future contributors never to log `service_account_info` or `private_key` (T-13-02).
  - `_refresh_once` no-ops (with warning) when no service account is configured.
- `src/bot/client.py` wires it all together in `setup_hook` (after stores load, before the overnight scheduler starts):
  1. Construct `SheetTransferTargetStore` and `load_snapshot()` in `__init__` so `/transfer-list` has data even if the first refresh fails.
  2. `self_heal_transfers_store(self.transfer_store)` — D-19.
  3. Initial fetch (guarded by `sheet_service_account_info is not None`), wrapped in try/except — failures log a warning and continue with the snapshot (D-06 + D-08).
  4. `SheetSyncScheduler(self).start()`.
- `data/.gitkeep` force-added (directory was `.gitignore`d) so the runtime path exists in fresh clones.
- `tests/test_sheet_sync.py` — 12 new tests, TDD flow (RED confirmed on `ModuleNotFoundError` before implementation, then all GREEN):
  - Row mapping: skips metadata + header, fixed column order, skips blank names, preserves blanks on short rows.
  - Store: atomic snapshot roundtrip, `added_at` preservation across refresh, whitespace+case-insensitive name match for preservation, refresh failure keeps stale cache + snapshot intact.
  - Helpers: `_normalize_name` whitespace/case behavior.
  - Scheduler: `_on_error` awaits `send_error_alerts` with the expected label and no credential leakage in the error message.
  - Self-heal: removes only `basketball + type=target`, leaves `outgoing` basketball rows and football untouched, persists across reload; no-op when there's nothing to remove.

## Verification

- `uv run pytest tests/test_sheet_sync.py -x -q` → **12 passed**.
- `uv run pytest -x -q --ignore=tests/test_config_phase2.py` → **163 passed** (whole suite minus one pre-existing Phase 12 regression documented under Deferred Issues).
- `uv run ruff check src/bot/sources src/bot/scheduling/sheet_sync.py src/bot/client.py src/bot/config.py src/bot/storage/models.py tests/test_sheet_sync.py` → **All checks passed**.
- `uv run python -c "from bot.sources.sheets import SheetTransferTargetStore, self_heal_transfers_store, map_rows_to_targets; from bot.scheduling.sheet_sync import SheetSyncScheduler; print('OK')"` → OK.
- `uv run python -c "import gspread; print(gspread.__version__)"` → `6.2.1`.

## Security Checklist (Threat Model Mitigations Applied)

| Threat ID | Mitigation | Verified |
|-----------|------------|----------|
| T-13-01 | JSONDecodeError logs fixed string only, never raw env / exception msg | `config.py::sheet_service_account_info` |
| T-13-02 | Error hook logs `type(error).__name__` + `str(error)` only; explicit comment forbids future credential logging | `sheet_sync.py::_on_error` + test asserts no `private_key` / `BEGIN PRIVATE KEY` substrings |
| T-13-04 | `gspread.auth.READONLY_SCOPES` only | `sheets.py::_build_gspread_client` |
| T-13-06 | Atomic write (tempfile + `os.replace`); JSONDecodeError on load starts empty + next refresh repopulates | `sheets.py::save_snapshot`, `load_snapshot` |
| T-13-08 | Skipped rows logged at debug with 1-indexed sheet row number | `sheets.py::map_rows_to_targets` |
| T-13-10 | Missing `SHEET_SERVICE_ACCOUNT_FILE` path returns `None` silently — no INFO log of path contents | `config.py::sheet_service_account_info` |

No code path logs `service_account_info`, `private_key`, or the raw `SHEET_SERVICE_ACCOUNT_JSON` env value.

## Commits

| Task | Message | Hash |
|------|---------|------|
| 1 | `feat(13-01): add gspread dep, sheet settings, TransferTarget model` | `7b85f52` |
| 2 | `feat(13-01): SheetTransferTargetStore + hourly sync scheduler` | `8cefc7d` |

## Deviations from Plan

None of substance. Minor mechanical adjustments:

1. **`data/` is `.gitignore`d in this repo** — Had to `git add -f data/.gitkeep` to include the placeholder. No scope impact; the runtime directory still materializes when the bot writes its snapshot.
2. **Worktree base mismatch at start** — Initial branch was at `62e966c` instead of the expected `bb8da37`. Applied `git reset --soft bb8da37` per the `worktree_branch_check` protocol before any edits. Pre-existing `.planning/STATE.md` and `.planning/ROADMAP.md` modifications were left unstaged (orchestrator owns those writes).

## Deferred Issues

- `tests/test_config_phase2.py::TestSystemPrompts::test_summary_prompt_no_action_items` was already failing before Phase 13 work began (Phase 12 summarizer prompt no longer contains the asserted sentence). Logged to `deferred-items.md` in this phase directory per the scope-boundary rule — it is not caused by this plan's changes.

## Known Stubs

None. No placeholder data, hardcoded empty arrays surfaced to UI, or TODOs introduced. All new code paths are fully wired end-to-end; the only "empty" code is `src/bot/sources/__init__.py` (intentional package marker) and `data/.gitkeep` (intentional directory placeholder).

## Self-Check: PASSED

**Files created (verified on disk):**
- `src/bot/sources/__init__.py` — FOUND
- `src/bot/sources/sheets.py` — FOUND
- `src/bot/scheduling/sheet_sync.py` — FOUND
- `tests/test_sheet_sync.py` — FOUND
- `data/.gitkeep` — FOUND

**Commits (verified in `git log`):**
- `7b85f52` — FOUND
- `8cefc7d` — FOUND

**Tests:** 12/12 pass on `tests/test_sheet_sync.py`; 163/163 pass on the rest of the suite (excluding the one pre-existing Phase 12 failure).
