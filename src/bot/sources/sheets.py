"""Google Sheets ingress for basketball transfer targets (Phase 13, D-01..D-21)."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import gspread

from bot.storage.models import TransferTarget

logger = logging.getLogger(__name__)

HEADER_ROW = 3  # D-12: rows 1-2 metadata, row 3 header, data begins at row 4
COLUMN_ORDER = (
    "name",
    "position",
    "former_school",
    "height_weight",
    "ku_interest_level",
    "made_contact",
    "notes",
)  # D-13 — fixed, no env override


def _normalize_name(name: str) -> str:
    """Lowercase + collapse whitespace for stable added_at match (D-20)."""
    return " ".join(name.strip().lower().split())


def map_rows_to_targets(rows: list[list[str]]) -> list[TransferTarget]:
    """Skip metadata + header, map remaining rows to TransferTarget.

    Rows 1..HEADER_ROW are metadata/header; data begins at row HEADER_ROW+1.
    A row with empty/whitespace Name is skipped with a debug log (D-15, T-13-08).
    """
    targets: list[TransferTarget] = []
    for i, row in enumerate(rows[HEADER_ROW:], start=HEADER_ROW + 1):
        # Pad short rows so indexing is safe.
        padded = list(row) + [""] * (len(COLUMN_ORDER) - len(row))
        values = dict(zip(COLUMN_ORDER, padded[: len(COLUMN_ORDER)]))
        name = values["name"].strip()
        if not name:
            logger.debug("Sheet row %d skipped: empty name", i)
            continue
        targets.append(
            TransferTarget(
                name=name,
                position=values["position"],
                former_school=values["former_school"],
                height_weight=values["height_weight"],
                ku_interest_level=values["ku_interest_level"],
                made_contact=values["made_contact"],
                notes=values["notes"],
            )
        )
    return targets


def _build_gspread_client(service_account_info: dict) -> gspread.Client:
    """Build a READONLY gspread client (T-13-04). Raises on auth failure."""
    return gspread.service_account_from_dict(
        service_account_info,
        scopes=gspread.auth.READONLY_SCOPES,
    )


def _fetch_rows_sync(
    service_account_info: dict, sheet_id: str, tab: str
) -> list[list[str]]:
    """Blocking fetch — always call via asyncio.to_thread from async code."""
    client = _build_gspread_client(service_account_info)
    ws = client.open_by_key(sheet_id).worksheet(tab)
    return ws.get_all_values()


class SheetTransferTargetStore:
    """In-memory cache of sheet-sourced basketball transfer targets.

    Backed by an atomic JSON snapshot on disk (T-13-06) so the bot has
    data on cold start before the first refresh completes (D-07).
    On refresh failure, cache is NEVER cleared (D-08).
    """

    def __init__(self, filepath: Path) -> None:
        self.filepath = filepath
        self._targets: list[TransferTarget] = []
        self._last_synced_at: datetime | None = None

    @property
    def targets(self) -> list[TransferTarget]:
        return list(self._targets)

    @property
    def last_synced_at(self) -> datetime | None:
        return self._last_synced_at

    def load_snapshot(self) -> None:
        """Load snapshot from disk. On corruption, start empty — next refresh repopulates."""
        if not self.filepath.exists():
            return
        try:
            raw = json.loads(self.filepath.read_text(encoding="utf-8"))
            self._targets = [TransferTarget.from_dict(t) for t in raw.get("targets", [])]
            last = raw.get("last_synced_at")
            if last:
                self._last_synced_at = datetime.fromisoformat(last)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            logger.warning(
                "Corrupt sheet snapshot %s: %s — starting empty", self.filepath, exc
            )
            self._targets = []
            self._last_synced_at = None

    def save_snapshot(self) -> None:
        """Atomic write via tempfile + os.replace (T-13-06)."""
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "targets": [t.to_dict() for t in self._targets],
            "last_synced_at": (
                self._last_synced_at.isoformat() if self._last_synced_at else None
            ),
        }
        fd, tmp_path = tempfile.mkstemp(dir=self.filepath.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            os.replace(tmp_path, self.filepath)
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def apply_refresh(self, new_targets: list[TransferTarget]) -> None:
        """Replace cache, preserving added_at for matched names (D-20)."""
        existing_by_name: dict[str, str] = {
            _normalize_name(t.name): t.added_at for t in self._targets
        }
        merged: list[TransferTarget] = []
        for t in new_targets:
            key = _normalize_name(t.name)
            preserved = existing_by_name.get(key)
            if preserved:
                t.added_at = preserved
            merged.append(t)
        self._targets = merged
        self._last_synced_at = datetime.now(timezone.utc)
        self.save_snapshot()

    async def refresh(
        self, service_account_info: dict, sheet_id: str, tab: str
    ) -> int:
        """Fetch the sheet, map rows, apply. Raises on fetch/auth failure.

        Returns new cached count. Scheduler is responsible for keeping stale
        cache on exception (D-08).
        """
        rows = await asyncio.to_thread(
            _fetch_rows_sync, service_account_info, sheet_id, tab
        )
        new_targets = map_rows_to_targets(rows)
        self.apply_refresh(new_targets)
        return len(self._targets)


def self_heal_transfers_store(transfer_store) -> int:
    """Remove any basketball+target entries from data/transfers.json (D-19).

    Returns number of entries removed. Saves only if mutation occurred.
    """
    players = transfer_store._data.get("basketball", [])
    keep = [p for p in players if p.type != "target"]
    removed = len(players) - len(keep)
    if removed:
        transfer_store._data["basketball"] = keep
        transfer_store.save()
        logger.info(
            "Self-heal: removed %d basketball target(s) from transfer_store", removed
        )
    return removed
