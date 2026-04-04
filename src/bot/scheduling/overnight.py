"""Automated summary scheduler: overnight at 9am + hourly recaps."""

import logging
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import discord
from discord.ext import tasks

from bot.alerting import send_error_alerts
from bot.delivery.threads import create_summary_thread
from bot.formatting.embeds import build_summary_embeds
from bot.models import SummaryError
from bot.summarizer import summarize_channel

logger = logging.getLogger(__name__)


def get_overnight_window(tz: ZoneInfo, start_hour: int, end_hour: int) -> tuple[datetime, datetime]:
    """Return (start, end) for the overnight window in timezone-aware datetimes."""
    now = datetime.now(tz)
    today_end = now.replace(hour=end_hour, minute=0, second=0, microsecond=0)
    hours_span = (24 - start_hour + end_hour) % 24
    window_start = today_end - timedelta(hours=hours_span)
    return window_start, today_end


class OvernightScheduler:
    """Manages the daily 9am overnight summary and hourly recap tasks.

    Uses discord.ext.tasks.loop with zoneinfo for DST-correct scheduling (SCHED-02).
    Iterates allowed channels sequentially, skips quiet channels,
    and continues past failures.
    """

    def __init__(self, bot) -> None:
        self.bot = bot
        tz = ZoneInfo(bot.settings.timezone)
        self.tz = tz
        self.overnight_start = bot.settings.overnight_start_hour
        self.overnight_end = bot.settings.overnight_end_hour
        schedule_time = time(hour=self.overnight_end, minute=0, tzinfo=tz)

        # Daily 9am overnight summary
        self._overnight_task = tasks.loop(time=schedule_time)(self._post_overnight_summary)
        self._overnight_task.before_loop(self._wait_ready)
        self._overnight_task.error(self._on_overnight_error)

        # Hourly recap
        self._hourly_task = tasks.loop(hours=1)(self._post_hourly_summary)
        self._hourly_task.before_loop(self._wait_ready)
        self._hourly_task.error(self._on_hourly_error)

    async def _wait_ready(self) -> None:
        """Wait until bot is connected before first iteration."""
        await self.bot.wait_until_ready()

    async def _on_overnight_error(self, error: Exception) -> None:
        logger.error(f"Overnight summary task failed: {error}", exc_info=error)
        error_msg = f"Task-level failure: {type(error).__name__}: {error}"
        await send_error_alerts(self.bot, "Overnight Task Error", [error_msg])

    async def _on_hourly_error(self, error: Exception) -> None:
        logger.error(f"Hourly summary task failed: {error}", exc_info=error)
        error_msg = f"Task-level failure: {type(error).__name__}: {error}"
        await send_error_alerts(self.bot, "Hourly Task Error", [error_msg])

    async def _post_summary(
        self, label: str, after: datetime, before: datetime | None = None
    ) -> None:
        """Summarize all allowed channels and post to the summary channel."""
        logger.info(f"Starting {label} summary generation")

        guild = self.bot.get_guild(self.bot.settings.guild_id)
        if guild is None:
            logger.error(f"Guild {self.bot.settings.guild_id} not found")
            return

        summary_channel = self.bot.get_channel(self.bot.settings.summary_channel_id)
        if summary_channel is None:
            logger.error(f"Summary channel {self.bot.settings.summary_channel_id} not found")
            return

        # Determine posting target: thread or channel
        if self.bot.settings.use_threads:
            now = datetime.now(self.tz)
            target = await create_summary_thread(summary_channel, now)
        else:
            target = summary_channel

        errors: list[str] = []

        for channel_id in self.bot.settings.allowed_channel_ids:
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                errors.append(f"Channel {channel_id} not found")
                continue

            try:
                summary_text = await summarize_channel(
                    channel,
                    guild,
                    self.bot.provider,
                    after,
                    before,
                    self.bot.settings.max_context_tokens,
                )

                if summary_text == "No messages to summarize.":
                    logger.info(f"#{channel.name}: no messages in {label} window, skipping")
                    continue

                embeds = build_summary_embeds(summary_text, channel.name, label)
                for embed in embeds:
                    embed.set_footer(text=f"Scheduled {label} summary")
                    await target.send(embed=embed)

            except SummaryError as e:
                error_msg = f"Failed to summarize #{channel.name}: {e}"
                errors.append(error_msg)
                logger.warning(error_msg)
                continue
            except Exception as e:
                error_msg = f"Failed to summarize #{channel.name}: {e}"
                errors.append(error_msg)
                logger.error(error_msg, exc_info=e)
                continue

        if errors:
            await send_error_alerts(self.bot, label, errors)

        logger.info(f"{label} summary complete, {len(errors)} error(s)")

    async def _post_overnight_summary(self) -> None:
        after, before = get_overnight_window(self.tz, self.overnight_start, self.overnight_end)
        label = f"Overnight ({self.overnight_start % 12 or 12}{'am' if self.overnight_start < 12 else 'pm'}–{self.overnight_end % 12 or 12}{'am' if self.overnight_end < 12 else 'pm'})"
        logger.info(f"Overnight window: {after} to {before}")
        await self._post_summary(label, after, before)

    async def _post_hourly_summary(self) -> None:
        now = datetime.now(self.tz)
        # Skip during overnight window — the overnight task covers that
        if self.overnight_start > self.overnight_end:
            # Wraps midnight (e.g. 22-9)
            in_overnight = now.hour >= self.overnight_start or now.hour < self.overnight_end
        else:
            # Same day (e.g. 1-6)
            in_overnight = self.overnight_start <= now.hour < self.overnight_end
        if in_overnight:
            logger.info("Skipping hourly summary during overnight window")
            return
        after = now - timedelta(hours=1)
        await self._post_summary("Hourly", after)

    def start(self) -> None:
        """Start the scheduled task loops."""
        self._overnight_task.start()
        self._hourly_task.start()

    def cancel(self) -> None:
        """Stop the scheduled task loops."""
        self._overnight_task.cancel()
        self._hourly_task.cancel()
