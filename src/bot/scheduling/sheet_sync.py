"""Hourly Google Sheet sync for basketball transfer targets (Phase 13)."""

from __future__ import annotations

import logging

from discord.ext import tasks

from bot.alerting import send_error_alerts

logger = logging.getLogger(__name__)


class SheetSyncScheduler:
    """Refresh the basketball transfer target cache every hour.

    Errors log a warning and pipe to send_error_alerts. The in-memory
    cache and on-disk snapshot are NEVER cleared on failure (D-08).

    SECURITY (T-13-02): The error hook logs only `type(error).__name__`
    and `str(error)` — NEVER the full traceback or any content that could
    include `service_account_info`, `credentials.private_key`, or the raw
    SHEET_SERVICE_ACCOUNT_JSON env value. gspread exceptions do not echo
    credentials today; if future retry/debug logging is added, scrub first.
    """

    def __init__(self, bot) -> None:
        self.bot = bot
        self._task = tasks.loop(hours=1)(self._refresh_once)
        self._task.before_loop(self._wait_ready)
        self._task.error(self._on_error)

    async def _wait_ready(self) -> None:
        await self.bot.wait_until_ready()

    async def _on_error(self, error: Exception) -> None:
        # SECURITY T-13-02: NEVER log raw service_account_info or private_key.
        logger.error(
            "Sheet sync task failed: %s", type(error).__name__, exc_info=error
        )
        msg = f"Sheet sync failure: {type(error).__name__}: {error}"
        await send_error_alerts(self.bot, "Transfer Target Sheet Sync", [msg])

    async def _refresh_once(self) -> None:
        info = self.bot.settings.sheet_service_account_info
        if info is None:
            logger.warning("Sheet sync skipped: no service account configured")
            return
        sheet_id = self.bot.settings.transfer_target_sheet_id
        tab = self.bot.settings.transfer_target_sheet_tab
        # Exception propagates to tasks.loop error hook — cache stays stale per D-08.
        count = await self.bot.sheet_target_store.refresh(info, sheet_id, tab)
        logger.info("Sheet sync OK: %d basketball targets cached", count)

    def start(self) -> None:
        self._task.start()

    def cancel(self) -> None:
        self._task.cancel()
