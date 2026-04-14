---
phase: 13-connect-a-google-sheet-to-the-recruit-list-function
plan: 02
subsystem: transfer-targets / slash-commands
tags: [google-sheets, transfers, slash-commands, embed-rendering, phase-13]
requires:
  - bot.sheet_target_store (SheetTransferTargetStore, Plan 01)
  - bot.transfer_store (RecruitingStore)
  - bot.storage.models.TransferTarget (Plan 01)
  - bot.storage.recruiting_store.get_sport_from_channel
provides:
  - SHEET_MANAGED_MSG constant (D-02 user-facing text)
  - _format_synced_ago helper (D-21)
  - /transfer-add guard for sport=basketball AND type=target
  - /transfer-remove guard for sport=basketball when candidate is absent or type==target
  - New basketball render branch in /transfer-list (TransferTarget field set, no stars, Synced-ago footer)
affects:
  - src/bot/commands/transfers.py (module-level constants + all three command handlers)
  - tests/test_transfers_sheet_integration.py (new, 14 tests)
tech-stack:
  added: []
  patterns:
    - Early-return guard pattern at command entry (no side effects before message)
    - Render-time merge of sheet-sourced data + locally-managed entries (D-04)
    - Section-kind-aware pagination (same embed loop renders two layouts)
key-files:
  created:
    - tests/test_transfers_sheet_integration.py
  modified:
    - src/bot/commands/transfers.py
decisions:
  - SHEET_MANAGED_MSG wording references the sheet explicitly and states a ≤1h sync window so users know what to do + how long to wait (D-02 discretion).
  - /transfer-remove's basketball branch blocks removal when the candidate is NOT found in the store (default-deny per threat model T-13-14). An outgoing entry must exist by exact case-insensitive name match to be removable in a basketball channel.
  - basketball render bypasses bot.transfer_cache entirely — sheet store is the in-memory cache. Football cache semantics are unchanged.
  - Field values routed through `[:1024]` defensively (T-13-11) even though gspread returns plain strings.
requirements:
  - TRANSFER-SHEET-05
  - TRANSFER-SHEET-06
metrics:
  completed: 2026-04-14
  duration: ~12m
  tasks: 2
  tests_added: 14
  files_created: 1
  files_modified: 1
---

# Phase 13 Plan 02: Wire Sheet Targets Into /transfer-* Commands — Summary

Basketball transfer targets become read-only at the command layer: `/transfer-add` and `/transfer-remove` return a clear "managed in the Google Sheet" message for the sport=basketball + type=target slice, and `/transfer-list` in a basketball channel now renders sheet-sourced targets with the TransferTarget field set (no stars, no "Unrated" filler) plus a "Synced N ago" footer — while football and basketball-outgoing paths remain byte-for-byte unchanged.

## What Changed

### Task 1 — Guards (commit `3278ccd`)

- New module constant `SHEET_MANAGED_MSG` in `src/bot/commands/transfers.py`:
  > "Basketball transfer targets are managed in the Google Sheet, not via slash commands. Edit the sheet and wait up to an hour for the bot to pick up the change."
- `transfer_add`: after `sport`/`transfer_type` resolution, early-returns with `SHEET_MANAGED_MSG` when `sport == "basketball" and transfer_type == "target"`. Runs BEFORE any store mutation or stats fetch.
- `transfer_remove`: in a basketball channel, looks up the candidate in `bot.transfer_store.list_players("basketball")` case-insensitively. If absent, or if its `type == "target"`, returns `SHEET_MANAGED_MSG` without calling `remove_player`. Outgoing entries remain removable.
- `_format_synced_ago(last_synced_at)` helper added at module scope (used by Task 2): returns "Synced just now" / "Synced N minute(s)/hour(s)/day(s) ago" / "Sync pending".

### Task 2 — Basketball render branch (commit `7e43106`)

- `transfer_list` now early-branches on `sport == "basketball"`:
  - Reads `bot.sheet_target_store.targets` (sheet-sourced) for the targets section.
  - Reads `bot.transfer_store.list_players("basketball", position=position)` and filters to `type == "outgoing"` for the outgoing section (D-04).
  - Applies position filter to both lists (case-insensitive).
  - `bot.transfer_cache` is intentionally bypassed — sheet store already caches in memory. Football path continues to use the TTLCache.
- Two sections ordered "Transfers Out" then "Transfer Targets"; each renders with a section-kind-aware field layout:
  - **outgoing:** existing PlayerEntry layout, keeps stars/`Unrated` filler.
  - **target:** TransferTarget layout — name-only field header, value lines for `Pos`, `From`, `H/W`, `KU Interest`, `Made Contact`, `Notes` (D-16). Blank optional fields are skipped; empty record falls back to `(no details)`. Values truncated to 1024 chars (T-13-11).
- Footer set on every embed (including continuation embeds) via `_format_synced_ago(bot.sheet_target_store.last_synced_at)`.
- Empty state (no targets + no outgoing) emits a single embed with the synced-ago footer; position-filtered empty message uses "No {POS} players..." wording.
- Pagination: targets count toward `MAX_PLAYERS_PER_EMBED=10`. 12 targets → 2 embeds (10 + 2).

### Tests — `tests/test_transfers_sheet_integration.py` (14 total)

Guards (Task 1):
1. `test_transfer_add_basketball_target_is_blocked` — default type (None → "target") blocked, no store mutation.
2. `test_transfer_add_basketball_target_explicit_type_is_blocked` — explicit `Choice(value="target")` blocked.
3. `test_transfer_add_basketball_outgoing_still_works` — basketball+outgoing still reaches `add_player`, returns "Added..." message.
4. `test_transfer_add_football_target_still_works` — football+target default path unchanged.
5. `test_transfer_remove_basketball_target_is_blocked` — unknown name in basketball channel → sheet-managed message, `remove_player` never called.
6. `test_transfer_remove_basketball_outgoing_still_works` — seeded outgoing basketball entry is removed normally.
7. `test_transfer_remove_football_still_works` — football path unchanged.

Render (Task 2):
8. `test_transfer_list_basketball_renders_sheet_target_fields` — all 7 TransferTarget fields render; `⭐` and `"Unrated"` are absent.
9. `test_transfer_list_basketball_footer_contains_synced_ago` — 5min-ago footer contains "synced" + "minute".
10. `test_transfer_list_basketball_footer_sync_pending_when_none` — `last_synced_at=None` → footer contains "sync" + "pending".
11. `test_transfer_list_basketball_includes_outgoing_section_from_transfer_store` — both sections render, stars present on outgoing side only.
12. `test_transfer_list_football_unchanged_does_not_consult_sheet` — sheet targets not leaked into football embed.
13. `test_transfer_list_basketball_empty_shows_empty_state_with_footer` — empty state still sets synced-ago footer.
14. `test_transfer_list_basketball_targets_count_toward_pagination_cap` — 12 targets → 2 embeds.

Test infrastructure: `_make_bot` builds a `SimpleNamespace`-based fake bot (fake tree captures command registrations, real `RecruitingStore`/`TTLCache`, `SimpleNamespace` sheet store). `_make_interaction(bot, channel_id)` produces a `MagicMock` with AsyncMock response helpers and exposes `interaction.client.settings` (handlers read through that path).

## Verification

- `uv run pytest tests/test_transfers_sheet_integration.py -x -q` → **14 passed**.
- `uv run pytest -x -q --ignore=tests/test_config_phase2.py` → **177 passed** (whole suite minus the pre-existing Phase 12 regression documented in Plan 01's deferred-items).
- `uv run ruff check src/bot/commands/transfers.py` → **All checks passed**.
- Wave 1's `tests/test_sheet_sync.py` → **12 passed** (no regressions to the ingress layer).

## Threat Model Mitigations Applied

| Threat ID | Mitigation | Where |
|-----------|------------|-------|
| T-13-11 | TransferTarget field values treated as plain strings; field value truncated to 1024 chars before `add_field`; no `eval`/format-string on cell content | `transfers.py::transfer_list` basketball branch |
| T-13-12 | `SHEET_MANAGED_MSG` is a static string — does not echo user input or store contents | `transfers.py::SHEET_MANAGED_MSG` |
| T-13-13 | `MAX_PLAYERS_PER_EMBED=10` cap preserved; pagination loop sends embeds in batches of 10 via `followup.send` | `transfers.py::transfer_list` basketball branch |
| T-13-14 | Guards run AFTER `get_sport_from_channel` resolves sport from the channel ID and AFTER `type` is normalized. `/transfer-remove` default-denies when candidate is absent from the basketball store | `transfers.py::transfer_add`, `::transfer_remove` |

## Commits

| Task | Message | Hash |
|------|---------|------|
| 1 | `feat(13-02): guard /transfer-add and /transfer-remove for basketball+target` | `3278ccd` |
| 2 | `feat(13-02): wire sheet targets into /transfer-list basketball render` | `7e43106` |

## Deviations from Plan

None of substance. Minor mechanical items:

1. **Worktree base mismatch at start** — Initial HEAD was at `62e966c` rather than the expected `87c40a6`. Applied `git reset --soft` then re-checked out working tree from HEAD per the worktree_branch_check protocol. Pre-existing `.planning/{STATE,ROADMAP,REQUIREMENTS}.md` edits from the orchestrator were left untouched (orchestrator owns those writes after the wave).
2. **Tests initially written to wrong path** — First Write tool invocation landed in the main repo's `tests/` directory instead of the worktree's `tests/` directory because I used the `Discord Bot/tests/...` absolute path rather than the worktree path. Moved the file to the correct location (`.claude/worktrees/agent-a28f484e/tests/`) and retried. No changes to the file content, no scope impact.
3. **`_make_interaction` signature** — Plan's behavior block suggested patching `get_sport_from_channel`, but the existing handlers read the settings object through `interaction.client.settings`. I exposed `bot.settings` on the mock's `interaction.client` instead and let the real `get_sport_from_channel` run. Equivalent outcome, fewer monkeypatches.

## Deferred Issues

None. All planned scope landed; no auto-fixes needed beyond Task 1's test-helper signature adjustment.

Pre-existing `tests/test_config_phase2.py::TestSystemPrompts::test_summary_prompt_no_action_items` failure is documented in Plan 01's `deferred-items.md` (Phase 12 summarizer prompt change). Not caused by Plan 02; not fixed here per scope-boundary rule.

## Known Stubs

None. All new code paths are wired end-to-end and consumed by real command handlers + real tests.

## Self-Check: PASSED

**Files verified on disk:**
- `src/bot/commands/transfers.py` — FOUND (modified)
- `tests/test_transfers_sheet_integration.py` — FOUND (new)

**Commits verified in `git log`:**
- `3278ccd` — FOUND (`feat(13-02): guard /transfer-add and /transfer-remove for basketball+target`)
- `7e43106` — FOUND (`feat(13-02): wire sheet targets into /transfer-list basketball render`)

**Tests:** 14/14 pass on the new file; 177/177 pass on the full suite (minus the documented Phase 12 pre-existing failure); 12/12 pass on Wave 1's `tests/test_sheet_sync.py` (no regression to the ingress layer).
