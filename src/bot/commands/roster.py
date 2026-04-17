"""Slash command handlers for /roster-import and /roster-list."""

import logging
from datetime import datetime, timezone

import discord
from discord import app_commands

from bot.stats.basketball import fetch_basketball_roster, fetch_basketball_stats
from bot.stats.football import fetch_football_roster, fetch_football_stats
from bot.storage.models import PlayerEntry
from bot.storage.recruiting_store import get_sport_from_channel

logger = logging.getLogger(__name__)

SPORT_EMOJI = {"football": "\U0001f3c8", "basketball": "\U0001f3c0"}
SPORT_TITLE = {"football": "Football", "basketball": "Basketball"}
KU_BLUE = 0x0051BA
MAX_FIELDS_PER_EMBED = 25


def register_roster_commands(bot) -> None:
    """Register the /roster-import and /roster-list commands."""

    def is_recruiting_editor():
        async def predicate(interaction: discord.Interaction) -> bool:
            editor_ids = interaction.client.settings.recruiting_editor_ids
            admin_ids = interaction.client.settings.admin_user_ids
            if interaction.user.id not in editor_ids and interaction.user.id not in admin_ids:
                raise app_commands.CheckFailure(
                    "You don't have permission to import rosters."
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
        name="roster-import",
        description="Import the current KU roster from the API",
    )
    @require_sport_channel()
    @is_recruiting_editor()
    async def roster_import(interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        sport = get_sport_from_channel(interaction.channel_id, interaction.client.settings)

        # Fetch roster from API
        if sport == "football":
            players = await fetch_football_roster(bot.settings)
        else:
            players = await fetch_basketball_roster(bot.settings)

        # Empty roster safety (Pitfall 6): do NOT wipe existing roster
        if not players:
            sport_title = SPORT_TITLE.get(sport, sport.title())
            await interaction.edit_original_response(
                content=f"API returned no players for Kansas {sport_title}. "
                "Existing roster preserved. This may be an offseason issue."
            )
            return

        # Replace mode (D-02): clear existing roster for this sport
        bot.roster_store._data[sport] = []

        stats_success = 0
        for i, p in enumerate(players):
            entry = PlayerEntry(
                name=p["name"],
                position=p["position"],
                school="",  # D-11: always Kansas, store empty
                stars=0,    # D-10: unrated for roster
                type="roster",
                jersey_number=p["jersey_number"],
                class_year=p["class_year"],
            )

            # Fetch stats per player (D-03), fire-and-forget on failure
            try:
                if sport == "football":
                    stats = await fetch_football_stats(bot.settings, p["name"], "Kansas")
                else:
                    stats = await fetch_basketball_stats(bot.settings, p["name"], "Kansas")
                if stats:
                    entry.stats = stats
                    stats_success += 1
            except Exception:
                logger.warning(f"Failed to fetch stats for {p['name']}", exc_info=True)

            bot.roster_store._data[sport].append(entry)

            # Progress update at 50% for large rosters
            if len(players) > 20 and i == len(players) // 2:
                await interaction.edit_original_response(
                    content=f"Importing... {i}/{len(players)} players processed"
                )

        # Save once after all players (not per player -- Pitfall 3)
        bot.roster_store.save()

        stats_failed = len(players) - stats_success
        await interaction.edit_original_response(
            content=f"Imported {len(players)} {sport} players. "
            f"Stats loaded for {stats_success}, failed for {stats_failed}."
        )
        logger.info(
            f"/roster-import: {interaction.user} imported {len(players)} {sport} players "
            f"(stats: {stats_success} ok, {stats_failed} failed)"
        )

    @bot.tree.command(
        name="roster-list",
        description="View the current KU roster for this channel's sport",
    )
    @app_commands.describe(public="Post the list publicly in the channel (admin only)")
    @require_sport_channel()
    async def roster_list(interaction: discord.Interaction, public: bool = False) -> None:
        ephemeral = not (public and interaction.user.id in interaction.client.settings.admin_user_ids)
        await interaction.response.defer(ephemeral=ephemeral)
        sport = get_sport_from_channel(interaction.channel_id, interaction.client.settings)
        players = bot.roster_store.list_players(sport)
        emoji = SPORT_EMOJI.get(sport, "")
        title = f"{emoji} KU {SPORT_TITLE.get(sport, sport.title())} Roster"

        if not players:
            embed = discord.Embed(
                title=title,
                description=f"No roster players imported for {sport} yet. "
                "An editor can run /roster-import to load the roster.",
                color=KU_BLUE,
            )
            await interaction.edit_original_response(embeds=[embed])
            return

        # Sort alphabetically by name (D-13)
        players = sorted(players, key=lambda p: p.name.lower())

        embeds = []
        current_embed = discord.Embed(title=title, color=KU_BLUE)
        field_count = 0

        for player in players:
            if field_count >= MAX_FIELDS_PER_EMBED:
                embeds.append(current_embed)
                current_embed = discord.Embed(title=f"{title} (cont.)", color=KU_BLUE)
                field_count = 0

            # Build field name per D-15: "Name -- Position #Jersey (ClassYear)"
            parts = [f"{player.name} \u2014 {player.position}"]
            if player.jersey_number:
                parts.append(f"#{player.jersey_number}")
            if player.class_year:
                parts.append(f"({player.class_year})")
            field_name = " ".join(parts)[:256]

            current_embed.add_field(
                name=field_name,
                value="\u200b",  # zero-width space
                inline=False,
            )
            field_count += 1

        now_str = datetime.now(timezone.utc).strftime("%b %d, %Y %I:%M %p UTC")
        current_embed.set_footer(text=f"Last updated: {now_str}")
        embeds.append(current_embed)

        await interaction.edit_original_response(embeds=embeds[:10])
        for i in range(10, len(embeds), 10):
            await interaction.followup.send(embeds=embeds[i:i + 10])

    # Error handler for roster commands
    async def roster_error(
        interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        if isinstance(error, app_commands.CheckFailure):
            if interaction.response.is_done():
                await interaction.followup.send(str(error), ephemeral=True)
            else:
                await interaction.response.send_message(str(error), ephemeral=True)
        else:
            logger.error(f"Roster command error: {error}", exc_info=error)
            msg = "Something went wrong. Please try again later."
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)

    roster_import.error(roster_error)
    roster_list.error(roster_error)
