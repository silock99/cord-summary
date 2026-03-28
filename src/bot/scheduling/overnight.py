"""Automated overnight summary scheduler (SCHED-01, SCHED-02)."""

import logging
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import discord
from discord.ext import tasks

from bot.delivery.threads import create_summary_thread
from bot.formatting.embeds import build_summary_embeds
from bot.models import SummaryError
from bot.summarizer import summarize_channel

logger = logging.getLogger(__name__)


def get_overnight_window(tz: ZoneInfo) -> tuple[datetime, datetime]:
    """Return (start=10pm yesterday, end=9am today) in timezone-aware datetimes."""
    now = datetime.now(tz)
    today_9am = now.replace(hour=9, minute=0, second=0, microsecond=0)
    yesterday_10pm = today_9am - timedelta(hours=11)
    return yesterday_10pm, today_9am


class OvernightScheduler:
    """Manages the daily 9am overnight summary task.

    Uses discord.ext.tasks.loop with zoneinfo for DST-correct scheduling (SCHED-02).
    Iterates allowed channels sequentially (D-11), skips quiet channels (D-03),
    and continues past failures (D-12).
    """

    def __init__(self, bot) -> None:
        self.bot = bot
        tz = ZoneInfo(bot.settings.timezone)
        self.tz = tz
        schedule_time = time(hour=9, minute=0, tzinfo=tz)

        # Create the task loop dynamically with the configured timezone
        self._task = tasks.loop(time=schedule_time)(self._post_overnight_summary)
        self._task.before_loop(self._wait_ready)
        self._task.error(self._on_error)

    async def _wait_ready(self) -> None:
        """Wait until bot is connected before first iteration (Pitfall 2)."""
        await self.bot.wait_until_ready()

    async def _on_error(self, error: Exception) -> None:
        """Log task errors without crashing the loop."""
        logger.error(f"Overnight summary task failed: {error}", exc_info=error)

    async def _post_overnight_summary(self) -> None:
        """Main scheduled job: summarize all allowed channels and post to #summaries."""
        logger.info("Starting overnight summary generation")

        after, before = get_overnight_window(self.tz)
        logger.info(f"Overnight window: {after} to {before}")

        guild = self.bot.get_guild(self.bot.settings.guild_id)
        if guild is None:
            logger.error(f"Guild {self.bot.settings.guild_id} not found")
            return

        summary_channel = self.bot.get_channel(self.bot.settings.summary_channel_id)
        if summary_channel is None:
            logger.error(f"Summary channel {self.bot.settings.summary_channel_id} not found")
            return

        # Determine posting target: thread or channel (D-08, D-09)
        if self.bot.settings.use_threads:
            now = datetime.now(self.tz)
            target = await create_summary_thread(summary_channel, now)
        else:
            target = summary_channel

        all_embeds: list[discord.Embed] = []
        errors: list[str] = []

        # Sequential channel iteration (D-01, D-11)
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

                # Check quiet threshold (D-03): skip silently
                if summary_text == "No messages to summarize.":
                    logger.info(f"#{channel.name}: no messages in overnight window, skipping")
                    continue

                embeds = build_summary_embeds(
                    summary_text, channel.name, "Overnight (10pm\u20139am)"
                )
                all_embeds.extend(embeds)

                # Post per-channel embeds (D-10)
                for embed in embeds:
                    embed.set_footer(text="Scheduled overnight summary | 10pm\u20139am")
                    await target.send(embed=embed)

            except SummaryError as e:
                # D-12: continue with remaining channels, log error
                error_msg = f"Failed to summarize #{channel.name}: {e}"
                errors.append(error_msg)
                logger.warning(error_msg)
                continue
            except Exception as e:
                error_msg = f"Failed to summarize #{channel.name}: {e}"
                errors.append(error_msg)
                logger.error(error_msg, exc_info=e)
                continue

        # Post error summary if any channels failed (D-12)
        if errors:
            error_text = "\n".join(f"- {e}" for e in errors)
            error_embed = discord.Embed(
                title="Overnight Summary Errors",
                description=error_text,
                color=0xFF0000,
            )
            await target.send(embed=error_embed)

        # Send DMs to opted-in subscribers (D-06, D-07)
        if all_embeds and hasattr(self.bot, 'dm_manager') and self.bot.dm_manager is not None:
            await self.bot.dm_manager.send_dm_summaries(self.bot, all_embeds)

        posted_count = len(all_embeds)
        logger.info(
            f"Overnight summary complete: {posted_count} embed(s) posted, "
            f"{len(errors)} error(s)"
        )

    def start(self) -> None:
        """Start the scheduled task loop."""
        self._task.start()

    def cancel(self) -> None:
        """Stop the scheduled task loop."""
        self._task.cancel()
