"""Slash command handler for /summary-dm toggle (OUT-03, D-04)."""

import logging

import discord

logger = logging.getLogger(__name__)


def register_summary_dm_command(bot) -> None:
    """Register the /summary-dm slash command on the bot's command tree."""

    @bot.tree.command(
        name="summary-dm",
        description="Toggle receiving overnight summaries via DM",
    )
    async def summary_dm(interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        if bot.dm_manager is None:
            await interaction.edit_original_response(
                content="DM delivery is not available."
            )
            return

        user_id = interaction.user.id
        now_subscribed = await bot.dm_manager.toggle(user_id)

        if now_subscribed:
            await interaction.edit_original_response(
                content="You will now receive overnight summaries via DM each morning."
            )
            logger.info(f"User {interaction.user} ({user_id}) subscribed to DM summaries")
        else:
            await interaction.edit_original_response(
                content="You will no longer receive overnight summaries via DM."
            )
            logger.info(f"User {interaction.user} ({user_id}) unsubscribed from DM summaries")
