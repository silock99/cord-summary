import logging

import discord
from discord.ext import commands

from bot.commands.summary import register_summary_command
from bot.config import Settings
from bot.providers.base import SummaryProvider

logger = logging.getLogger(__name__)


class SummaryBot(commands.Bot):
    def __init__(self, settings: Settings):
        intents = discord.Intents.default()
        intents.message_content = True   # Privileged intent for INFRA-01
        intents.members = True           # For mention resolution (D-04)
        super().__init__(command_prefix="!", intents=intents)
        self.settings = settings
        self.provider: SummaryProvider | None = None

    async def setup_hook(self) -> None:
        """Register commands and sync to the configured guild (INFRA-03). Fires once before connecting."""
        register_summary_command(self)
        guild = discord.Object(id=self.settings.guild_id)
        self.tree.copy_global_to(guild=guild)
        synced = await self.tree.sync(guild=guild)
        logger.info(f"Synced {len(synced)} command(s) to guild {self.settings.guild_id}")

    async def on_ready(self) -> None:
        logger.info(f"Bot connected as {self.user} (ID: {self.user.id})")
        # Verify Message Content intent is working (INFRA-01 success criteria)
        guild = self.get_guild(self.settings.guild_id)
        if guild:
            logger.info(f"Connected to guild: {guild.name}")
        else:
            logger.warning(f"Guild {self.settings.guild_id} not found in cache")
