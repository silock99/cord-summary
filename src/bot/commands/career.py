"""Slash command handler for /career."""

import difflib
import logging

import discord
from discord import app_commands

from bot.stats.basketball import fetch_basketball_stats
from bot.stats.football import fetch_football_stats
from bot.stats.formatter import format_stats_table
from bot.storage.recruiting_store import get_sport_from_channel

logger = logging.getLogger(__name__)

SPORT_EMOJI = {"football": "\U0001f3c8", "basketball": "\U0001f3c0"}
KU_BLUE = 0x0051BA


def register_career_commands(bot) -> None:
    """Register the /career command."""

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
        name="stats",
        description="Look up college career stats for a player",
    )
    @app_commands.describe(player="Player name (autocompletes from recruit/transfer/roster lists)")
    @require_sport_channel()
    async def stats(interaction: discord.Interaction, player: str) -> None:
        await interaction.response.defer(ephemeral=True)
        sport = get_sport_from_channel(interaction.channel_id, interaction.client.settings)
        emoji = SPORT_EMOJI.get(sport, "")

        # Search all three stores for the player
        all_players = (
            bot.recruit_store.list_players(sport)
            + bot.transfer_store.list_players(sport)
            + bot.roster_store.list_players(sport)
        )

        # Exact match (case-insensitive)
        match = next(
            (p for p in all_players if p.name.lower() == player.lower()),
            None,
        )

        if match is None:
            # Fuzzy match (cutoff=0.6)
            names = [p.name for p in all_players]
            close = difflib.get_close_matches(player, names, n=3, cutoff=0.6)
            if close:
                suggestions = ", ".join(f"**{s}**" for s in close)
                await interaction.edit_original_response(
                    content=f"Player **{player}** not found. Did you mean: {suggestions}?"
                )
                return

            # Freeform fallback: try API directly
            try:
                if sport == "football":
                    stats = await fetch_football_stats(bot.settings, player, "")
                else:
                    stats = await fetch_basketball_stats(bot.settings, player, "")
                if stats:
                    table = format_stats_table(stats)
                    player_name = stats.get("player_name", player)
                    embed = discord.Embed(
                        title=f"{emoji} {player_name} - Career Stats",
                        description=table,
                        color=KU_BLUE,
                    )
                    await interaction.edit_original_response(embeds=[embed])
                    return
            except Exception:
                logger.warning(f"Freeform stats lookup failed for {player}", exc_info=True)

            await interaction.edit_original_response(
                content=f"No stats found for **{player}**. Make sure the name is spelled correctly."
            )
            return

        # Found a matched player in stores
        if match.stats is None:
            await interaction.edit_original_response(
                content=f"No career stats available for **{match.name}**. Stats may not have been loaded when the player was added."
            )
            return

        table = format_stats_table(match.stats)
        player_name = match.stats.get("player_name", match.name)
        embed = discord.Embed(
            title=f"{emoji} {player_name} - Career Stats",
            description=table,
            color=KU_BLUE,
        )
        embed.set_footer(text=f"{match.school} | {match.position}")
        await interaction.edit_original_response(embeds=[embed])
        logger.info(f"/stats: {interaction.user} looked up {match.name}")

    # Autocomplete callback
    @stats.autocomplete("player")
    async def career_player_autocomplete(
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        sport = get_sport_from_channel(interaction.channel_id, interaction.client.settings)
        if sport is None:
            return []
        # Combine all three stores
        all_players = (
            bot.recruit_store.list_players(sport)
            + bot.transfer_store.list_players(sport)
            + bot.roster_store.list_players(sport)
        )
        # Deduplicate by name (case-insensitive)
        seen = set()
        unique = []
        for p in all_players:
            key = p.name.lower()
            if key not in seen:
                seen.add(key)
                unique.append(p)
        # Filter by current input
        if current:
            filtered = [p for p in unique if current.lower() in p.name.lower()]
        else:
            filtered = unique
        # Discord limits autocomplete to 25 choices
        return [
            app_commands.Choice(name=f"{p.name} ({p.position}, {p.school})", value=p.name)
            for p in filtered[:25]
        ]

    # Error handler (same pattern as recruiting.py)
    async def career_error(
        interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        if isinstance(error, app_commands.CheckFailure):
            if interaction.response.is_done():
                await interaction.followup.send(str(error), ephemeral=True)
            else:
                await interaction.response.send_message(str(error), ephemeral=True)
        else:
            logger.error(f"Career command error: {error}", exc_info=error)
            msg = "Something went wrong. Please try again later."
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)

    stats.error(career_error)
