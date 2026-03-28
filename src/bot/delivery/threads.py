"""Thread creation for daily overnight summaries (OUT-04, D-09)."""

import logging
from datetime import datetime

import discord

logger = logging.getLogger(__name__)


async def create_summary_thread(
    channel: discord.TextChannel,
    tz_now: datetime,
) -> discord.Thread:
    """Create a public thread for today's overnight summary.

    Uses auto_archive_duration=1440 (24 hours) so threads
    auto-archive and keep the channel clean.
    """
    date_str = tz_now.strftime("%b %d")
    thread = await channel.create_thread(
        name=f"Overnight Summary — {date_str}",
        type=discord.ChannelType.public_thread,
        auto_archive_duration=1440,
    )
    logger.info(f"Created summary thread: {thread.name}")
    return thread
