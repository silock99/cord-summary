"""DM subscriber management and delivery (OUT-03, D-04 through D-07)."""

import asyncio
import json
import logging
from pathlib import Path

import discord

logger = logging.getLogger(__name__)

DEFAULT_DM_SUBSCRIBERS_PATH = Path("data/dm_subscribers.json")


class DMManager:
    """Manages DM subscriber list with JSON file persistence.

    Uses asyncio.Lock to prevent race conditions on concurrent
    toggle commands (Pitfall 6 from RESEARCH.md).
    """

    def __init__(self, path: Path = DEFAULT_DM_SUBSCRIBERS_PATH) -> None:
        self._path = path
        self._lock = asyncio.Lock()
        self._subscribers: set[int] = set()
        self._load()

    def _load(self) -> None:
        """Load subscriber IDs from JSON file."""
        if not self._path.exists():
            self._subscribers = set()
            return
        try:
            data = json.loads(self._path.read_text())
            self._subscribers = set(data.get("user_ids", []))
            logger.info(f"Loaded {len(self._subscribers)} DM subscriber(s)")
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load DM subscribers: {e}")
            self._subscribers = set()

    def _save(self) -> None:
        """Persist subscriber IDs to JSON file."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps({"user_ids": sorted(self._subscribers)}, indent=2)
        )

    @property
    def subscribers(self) -> set[int]:
        """Current subscriber user IDs (read-only copy)."""
        return set(self._subscribers)

    async def toggle(self, user_id: int) -> bool:
        """Toggle a user's DM subscription. Returns True if now subscribed, False if unsubscribed.

        Uses asyncio.Lock for safe concurrent access (Pitfall 6).
        """
        async with self._lock:
            if user_id in self._subscribers:
                self._subscribers.discard(user_id)
                self._save()
                return False
            else:
                self._subscribers.add(user_id)
                self._save()
                return True

    def is_subscribed(self, user_id: int) -> bool:
        """Check if a user is subscribed."""
        return user_id in self._subscribers

    async def send_dm_summaries(
        self, bot, embeds: list[discord.Embed]
    ) -> None:
        """Send summary embeds to all DM subscribers.

        Per D-07: reuses the same embeds, zero additional LLM calls.
        Per D-06: only called from scheduled summaries, not on-demand.
        Handles discord.Forbidden gracefully (Pitfall 3).
        """
        if not self._subscribers or not embeds:
            return

        logger.info(f"Sending DM summaries to {len(self._subscribers)} subscriber(s)")
        success = 0
        failed = 0

        for user_id in self._subscribers:
            user = bot.get_user(user_id)
            if user is None:
                try:
                    user = await bot.fetch_user(user_id)
                except discord.NotFound:
                    logger.warning(f"DM subscriber {user_id} not found, skipping")
                    failed += 1
                    continue

            try:
                for embed in embeds:
                    await user.send(embed=embed)
                success += 1
            except discord.Forbidden:
                logger.warning(f"Cannot DM user {user_id} (DMs disabled)")
                failed += 1
            except discord.HTTPException as e:
                logger.warning(f"Failed to DM user {user_id}: {e}")
                failed += 1

        logger.info(f"DM delivery complete: {success} sent, {failed} failed")
