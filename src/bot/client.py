import logging

import discord
from discord.ext import commands

from pathlib import Path

from bot.commands.post_summary import register_post_summary_command
from bot.commands.recruiting import register_recruit_commands
from bot.commands.summary import register_summary_command
from bot.commands.transfers import register_transfer_commands
from bot.config import Settings
from bot.language_filter import load_language_config
from bot.providers.base import SummaryProvider
from bot.scheduling.overnight import OvernightScheduler
from bot.storage.recruiting_store import RecruitingStore

logger = logging.getLogger(__name__)


class SummaryBot(commands.Bot):
    def __init__(self, settings: Settings):
        intents = discord.Intents.default()
        intents.message_content = True   # Privileged intent for INFRA-01
        intents.members = True           # For mention resolution (D-04)
        super().__init__(command_prefix="!", intents=intents)
        self.settings = settings
        self.provider: SummaryProvider | None = None
        self.scheduler: OvernightScheduler | None = None
        self.recruit_store = RecruitingStore(Path("data/recruits.json"))
        self.transfer_store = RecruitingStore(Path("data/transfers.json"))

    async def setup_hook(self) -> None:
        """Register commands and sync to the configured guild (INFRA-03). Fires once before connecting."""
        register_summary_command(self)
        register_post_summary_command(self)

        # Load recruiting/transfer data from JSON files
        self.recruit_store.load()
        self.transfer_store.load()

        # Register recruiting and transfer commands (Phase 7)
        register_recruit_commands(self)
        register_transfer_commands(self)

        guild = discord.Object(id=self.settings.guild_id)
        self.tree.copy_global_to(guild=guild)
        synced = await self.tree.sync(guild=guild)
        logger.info(f"Synced {len(synced)} command(s) to guild {self.settings.guild_id}")

        # Load language filter configuration (Phase 5: LANG-01, LANG-02)
        load_language_config()

        # Start scheduled summary tasks (overnight + hourly)
        self.scheduler = OvernightScheduler(self)
        self.scheduler.start()
        logger.info("Summary schedulers started")

    async def on_ready(self) -> None:
        logger.info(f"Bot connected as {self.user} (ID: {self.user.id})")
        # Verify Message Content intent is working (INFRA-01 success criteria)
        guild = self.get_guild(self.settings.guild_id)
        if guild:
            logger.info(f"Connected to guild: {guild.name}")
        else:
            logger.warning(f"Guild {self.settings.guild_id} not found in cache")
