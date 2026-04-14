"""Tests for sheet transfer target store, scheduler, and self-heal (Phase 13)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.sources.sheets import (
    SheetTransferTargetStore,
    _normalize_name,
    map_rows_to_targets,
    self_heal_transfers_store,
)
from bot.storage.models import PlayerEntry, TransferTarget
from bot.storage.recruiting_store import RecruitingStore


# -------- map_rows_to_targets --------


def _make_sheet_rows(data_rows: list[list[str]]) -> list[list[str]]:
    """Prepend two metadata rows + one header row so data starts at index 3."""
    return [
        ["metadata-row-1"],
        ["metadata-row-2"],
        ["Name", "Position", "Former School", "Height/Weight",
         "KU Interest Level", "Made Contact", "Notes"],
        *data_rows,
    ]


def test_map_rows_skips_rows_3_and_above_until_header_row_4():
    rows = _make_sheet_rows([
        ["Jon Doe", "G", "UCLA", "6'4\" / 195", "HIGH", "Yes", "quick feet"],
    ])
    targets = map_rows_to_targets(rows)
    assert len(targets) == 1
    assert targets[0].name == "Jon Doe"


def test_map_rows_columns_in_fixed_order():
    rows = _make_sheet_rows([
        ["Jon Doe", "G", "UCLA", "6'4\" / 195", "HIGH", "Yes", "quick feet"],
    ])
    [t] = map_rows_to_targets(rows)
    assert t.name == "Jon Doe"
    assert t.position == "G"
    assert t.former_school == "UCLA"
    assert t.height_weight == "6'4\" / 195"
    assert t.ku_interest_level == "HIGH"
    assert t.made_contact == "Yes"
    assert t.notes == "quick feet"


def test_map_rows_skips_empty_name():
    rows = _make_sheet_rows([
        ["", "G", "UCLA", "", "", "", ""],
        ["   ", "G", "UCLA", "", "", "", ""],
        ["Valid Name", "F", "Duke", "", "", "", ""],
    ])
    targets = map_rows_to_targets(rows)
    assert len(targets) == 1
    assert targets[0].name == "Valid Name"


def test_map_rows_preserves_blank_optional_cells():
    rows = _make_sheet_rows([
        ["Short Row", "G"],  # short row — missing trailing cells
        ["All Blanks", "", "", "", "", "", ""],
    ])
    targets = map_rows_to_targets(rows)
    assert len(targets) == 2
    assert targets[0].position == "G"
    assert targets[0].former_school == ""
    assert targets[0].notes == ""
    assert targets[1].position == ""
    assert targets[1].notes == ""


# -------- SheetTransferTargetStore --------


def test_store_atomic_snapshot_roundtrip(tmp_path: Path):
    snap = tmp_path / "targets.json"
    store = SheetTransferTargetStore(snap)
    store._targets = [
        TransferTarget(name="A", position="G", former_school="UCLA"),
        TransferTarget(name="B", position="F", notes="athletic"),
    ]
    store.save_snapshot()
    assert snap.exists()

    store2 = SheetTransferTargetStore(snap)
    store2.load_snapshot()
    names = [t.name for t in store2.targets]
    assert names == ["A", "B"]
    assert store2.targets[0].former_school == "UCLA"


def test_store_preserves_added_at_across_refresh(tmp_path: Path):
    snap = tmp_path / "targets.json"
    store = SheetTransferTargetStore(snap)
    original = TransferTarget(name="Jon Doe", position="G", added_at="2026-01-01T00:00:00+00:00")
    store._targets = [original]

    new = [
        TransferTarget(name="Jon Doe", position="G"),
        TransferTarget(name="Brand New", position="F"),
    ]
    store.apply_refresh(new)
    by_name = {t.name: t for t in store.targets}
    assert by_name["Jon Doe"].added_at == "2026-01-01T00:00:00+00:00"
    # Fresh row got a current timestamp (simply not the legacy one)
    assert by_name["Brand New"].added_at != "2026-01-01T00:00:00+00:00"
    assert by_name["Brand New"].added_at  # non-empty


def test_store_normalized_name_match_for_preserve(tmp_path: Path):
    snap = tmp_path / "targets.json"
    store = SheetTransferTargetStore(snap)
    original = TransferTarget(name="Jon Doe", added_at="2026-01-01T00:00:00+00:00")
    store._targets = [original]

    new = [TransferTarget(name="  jon  doe  ", position="G")]
    store.apply_refresh(new)
    assert store.targets[0].added_at == "2026-01-01T00:00:00+00:00"


def test_store_failure_keeps_stale_cache(tmp_path: Path):
    snap = tmp_path / "targets.json"
    store = SheetTransferTargetStore(snap)
    store._targets = [TransferTarget(name="Stale But Cached")]
    store.save_snapshot()
    initial_count = len(store.targets)

    # Simulate failed refresh by patching _fetch_rows_sync to raise
    with patch("bot.sources.sheets._fetch_rows_sync", side_effect=RuntimeError("boom")):
        import asyncio
        with pytest.raises(RuntimeError):
            asyncio.run(store.refresh({"fake": "creds"}, "sheet-id", "tab"))

    # Cache and snapshot both intact
    assert len(store.targets) == initial_count
    assert store.targets[0].name == "Stale But Cached"
    assert snap.exists()
    payload = json.loads(snap.read_text(encoding="utf-8"))
    assert payload["targets"][0]["name"] == "Stale But Cached"


def test_normalize_name_collapses_whitespace():
    assert _normalize_name("Jon  Doe") == "jon doe"
    assert _normalize_name("  Jon Doe  ") == "jon doe"
    assert _normalize_name("JON DOE") == "jon doe"


# -------- Scheduler error hook --------


@pytest.mark.asyncio
async def test_scheduler_error_hook_calls_send_error_alerts():
    from bot.scheduling.sheet_sync import SheetSyncScheduler

    bot = MagicMock()
    bot.settings.sheet_service_account_info = None

    scheduler = SheetSyncScheduler(bot)

    with patch("bot.scheduling.sheet_sync.send_error_alerts", new_callable=AsyncMock) as mock_alert:
        await scheduler._on_error(RuntimeError("sheet down"))

    mock_alert.assert_awaited_once()
    args, _ = mock_alert.call_args
    # (bot, label, errors)
    assert args[0] is bot
    assert "Sheet Sync" in args[1] or "sheet" in args[1].lower()
    assert isinstance(args[2], list)
    assert len(args[2]) == 1
    # The error message should NOT contain credential markers
    assert "private_key" not in args[2][0]
    assert "BEGIN PRIVATE KEY" not in args[2][0]


# -------- Self-heal --------


def test_self_heal_removes_basketball_target_entries(tmp_path: Path):
    transfers_path = tmp_path / "transfers.json"
    store = RecruitingStore(transfers_path)
    # Seed with mixed entries
    store._data["basketball"] = [
        PlayerEntry(name="Sheet Target", position="G", school="UCLA", stars=0, type="target"),
        PlayerEntry(name="Out Player", position="F", school="KU", stars=0, type="outgoing"),
        PlayerEntry(name="Another Target", position="C", school="Duke", stars=0, type="target"),
    ]
    store._data["football"] = [
        PlayerEntry(name="FB Target", position="QB", school="Bama", stars=0, type="target"),
    ]
    store.save()

    removed = self_heal_transfers_store(store)
    assert removed == 2

    # Basketball only has outgoing now
    bball = store._data["basketball"]
    assert len(bball) == 1
    assert bball[0].name == "Out Player"
    assert bball[0].type == "outgoing"
    # Football untouched
    assert len(store._data["football"]) == 1
    assert store._data["football"][0].name == "FB Target"

    # Changes persisted
    reloaded = RecruitingStore(transfers_path)
    assert len(reloaded._data["basketball"]) == 1
    assert reloaded._data["basketball"][0].type == "outgoing"


def test_self_heal_noop_when_no_basketball_targets(tmp_path: Path):
    transfers_path = tmp_path / "transfers.json"
    store = RecruitingStore(transfers_path)
    store._data["basketball"] = [
        PlayerEntry(name="Out Player", position="F", school="KU", stars=0, type="outgoing"),
    ]
    store.save()

    removed = self_heal_transfers_store(store)
    assert removed == 0
    assert len(store._data["basketball"]) == 1
