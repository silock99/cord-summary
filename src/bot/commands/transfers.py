"""Slash command handlers for /transfer-add, /transfer-remove, /transfer-list."""

import logging
from datetime import datetime, timezone

import discord
from discord import app_commands

from bot.storage.recruiting_store import get_sport_from_channel

logger = logging.getLogger(__name__)

SPORT_EMOJI = {"football": "\U0001f3c8", "basketball": "\U0001f3c0"}
SPORT_TITLE = {"football": "Football", "basketball": "Basketball"}
KU_BLUE = 0x0051BA
STAR_EMOJI = "\u2b50"
MAX_FIELDS_PER_EMBED = 25


def register_transfer_commands(bot) -> None:
    """Register the /transfer-add, /transfer-remove, /transfer-list commands."""

    def is_recruiting_editor():
        async def predicate(interaction: discord.Interaction) -> bool:
            editor_ids = interaction.client.settings.recruiting_editor_ids
            admin_ids = interaction.client.settings.admin_user_ids
            if interaction.user.id not in editor_ids and interaction.user.id not in admin_ids:
                raise app_commands.CheckFailure(
                    "You don't have permission to manage the transfer list."
                )
            return True
        return app_commands.check(predicate)

    def require_sport_channel():
        async def predicate(interaction: discord.Interaction) -> bool:
            sport = get_sport_from_channel(interaction.channel_id, interaction.client.settings)
            if sport is None:
                raise app_commands.CheckFailure(
                    "This command can only be used in a football or basketball channel."
                )
            return True
        return app_commands.check(predicate)

    @bot.tree.command(
        name="transfer-add",
        description="Add a player to the transfer list",
    )
    @app_commands.describe(
        name="Player name",
        position="Position (e.g., QB, WR, ATH, PG, C)",
        school="Previous/current school",
        stars="Star rating (0 for unrated, 1-5)",
    )
    @require_sport_channel()
    @is_recruiting_editor()
    async def transfer_add(
        interaction: discord.Interaction,
        name: str,
        position: str,
        school: str,
        stars: app_commands.Range[int, 0, 5] = 0,
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        sport = get_sport_from_channel(interaction.channel_id, interaction.client.settings)
        player = bot.transfer_store.add_player(sport, name, position, school, stars)
        if player is None:
            await interaction.edit_original_response(
                content=f"**{name}** is already on the {sport} transfer list."
            )
            return
        star_text = f" {STAR_EMOJI * stars}" if stars > 0 else ""
        await interaction.edit_original_response(
            content=f"Added **{name}** ({position}, {school}){star_text} to the {sport} transfer list."
        )
        logger.info(f"/transfer-add: {interaction.user} added {name} to {sport}")

    @bot.tree.command(
        name="transfer-remove",
        description="Remove a player from the transfer list",
    )
    @app_commands.describe(name="Player name to remove")
    @require_sport_channel()
    @is_recruiting_editor()
    async def transfer_remove(
        interaction: discord.Interaction,
        name: str,
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        sport = get_sport_from_channel(interaction.channel_id, interaction.client.settings)
        removed, suggestions = bot.transfer_store.remove_player(sport, name)
        if removed:
            await interaction.edit_original_response(
                content=f"Removed **{removed.name}** from the {sport} transfer list."
            )
            logger.info(f"/transfer-remove: {interaction.user} removed {removed.name} from {sport}")
        elif suggestions:
            await interaction.edit_original_response(
                content=f"**{name}** not found. Did you mean: {', '.join(suggestions)}?"
            )
        else:
            await interaction.edit_original_response(
                content=f"**{name}** not found on the {sport} transfer list."
            )

    @bot.tree.command(
        name="transfer-list",
        description="View the transfer list for this channel's sport",
    )
    @require_sport_channel()
    async def transfer_list(interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        sport = get_sport_from_channel(interaction.channel_id, interaction.client.settings)
        players = bot.transfer_store.list_players(sport)
        emoji = SPORT_EMOJI.get(sport, "")
        title = f"{emoji} KU {SPORT_TITLE.get(sport, sport.title())} Transfer List"

        if not players:
            embed = discord.Embed(
                title=title,
                description=f"No players on the {sport} transfer list yet.",
                color=KU_BLUE,
            )
            await interaction.edit_original_response(embeds=[embed])
            return

        embeds = []
        current_embed = discord.Embed(title=title, color=KU_BLUE)
        field_count = 0

        for player in players:
            if field_count >= MAX_FIELDS_PER_EMBED:
                embeds.append(current_embed)
                current_embed = discord.Embed(title=f"{title} (cont.)", color=KU_BLUE)
                field_count = 0

            star_display = STAR_EMOJI * player.stars if player.stars else "Unrated"
            field_name = f"{player.name} {star_display}"[:256]
            added_dt = datetime.fromisoformat(player.added_at)
            field_value = (
                f"{player.position} | {player.school}\n"
                f"Added {discord.utils.format_dt(added_dt, style='R')}"
            )
            current_embed.add_field(name=field_name, value=field_value, inline=False)
            field_count += 1

        now_str = datetime.now(timezone.utc).strftime("%b %d, %Y %I:%M %p UTC")
        current_embed.set_footer(text=f"Last updated: {now_str}")
        embeds.append(current_embed)

        await interaction.edit_original_response(embeds=embeds[:10])
        for i in range(10, len(embeds), 10):
            await interaction.followup.send(embeds=embeds[i:i + 10])

    # Error handler for all transfer commands
    async def transfer_error(
        interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        if isinstance(error, app_commands.CheckFailure):
            if interaction.response.is_done():
                await interaction.followup.send(str(error), ephemeral=True)
            else:
                await interaction.response.send_message(str(error), ephemeral=True)
        else:
            logger.error(f"Transfer command error: {error}", exc_info=error)
            msg = "Something went wrong. Please try again later."
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)

    transfer_add.error(transfer_error)
    transfer_remove.error(transfer_error)
    transfer_list.error(transfer_error)
