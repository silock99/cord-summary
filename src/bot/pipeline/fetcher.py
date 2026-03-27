"""Message fetching from Discord channels with pagination."""

import logging
from datetime import datetime

import discord

logger = logging.getLogger(__name__)


async def fetch_messages(
    channel: discord.TextChannel,
    after: datetime,
    before: datetime | None = None,
) -> list[discord.Message]:
    """Fetch all messages in a time range.

    discord.py handles pagination internally (100 per API request).
    Messages are returned in oldest-first order for pipeline processing.
    """
    messages: list[discord.Message] = []
    async for message in channel.history(
        limit=None,
        after=after,
        before=before,
        oldest_first=True,
    ):
        messages.append(message)
    logger.info(f"Fetched {len(messages)} messages from #{channel.name}")
    return messages
