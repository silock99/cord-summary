"""Slash command handlers for /transfer-add, /transfer-remove, /transfer-list."""

import logging
from datetime import datetime, timezone

import discord
from discord import app_commands

from bot.stats.basketball import fetch_basketball_stats
from bot.stats.football import fetch_football_stats
from bot.storage.recruiting_store import get_sport_from_channel

logger = logging.getLogger(__name__)

SPORT_EMOJI = {"football": "\U0001f3c8", "basketball": "\U0001f3c0"}
SPORT_TITLE = {"football": "Football", "basketball": "Basketball"}
KU_BLUE = 0x0051BA
STAR_EMOJI = "\u2b50"
MAX_PLAYERS_PER_EMBED = 10

# Phase 13 / D-02: basketball transfer targets are read-only from the Google Sheet.
SHEET_MANAGED_MSG = (
    "Basketball transfer targets are managed in the Google Sheet, not via slash "
    "commands. Edit the sheet and wait up to an hour for the bot to pick up the change."
)


def _format_synced_ago(last_synced_at) -> str:
    """Return a human-friendly 'Synced N ago' or 'Sync pending' string (D-21).

    last_synced_at: datetime | None (UTC-aware)
    """
    if last_synced_at is None:
        return "Sync pending"
    delta = datetime.now(timezone.utc) - last_synced_at
    seconds = int(delta.total_seconds())
    if seconds < 45:
        return "Synced just now"
    minutes = seconds // 60
    if minutes < 60:
        unit = "minute" if minutes == 1 else "minutes"
        return f"Synced {minutes} {unit} ago"
    hours = minutes // 60
    if hours < 24:
        unit = "hour" if hours == 1 else "hours"
        return f"Synced {hours} {unit} ago"
    days = hours // 24
    unit = "day" if days == 1 else "days"
    return f"Synced {days} {unit} ago"


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
        type="Transfer type: outgoing (leaving KU) or target (coming to KU)",
    )
    @app_commands.choices(type=[
        app_commands.Choice(name="Outgoing (leaving KU)", value="outgoing"),
        app_commands.Choice(name="Target (coming to KU)", value="target"),
    ])
    @require_sport_channel()
    @is_recruiting_editor()
    async def transfer_add(
        interaction: discord.Interaction,
        name: str,
        position: str,
        school: str,
        stars: app_commands.Range[int, 0, 5] = 0,
        type: app_commands.Choice[str] | None = None,
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        sport = get_sport_from_channel(interaction.channel_id, interaction.client.settings)
        transfer_type = type.value if type else "target"
        # Phase 13 / D-02: basketball transfer targets are sheet-managed.
        if sport == "basketball" and transfer_type == "target":
            await interaction.edit_original_response(content=SHEET_MANAGED_MSG)
            return
        player = bot.transfer_store.add_player(sport, name, position, school, stars, player_type=transfer_type)
        if player is not None:
            bot.transfer_cache.clear()
            # Fetch career stats (non-fatal on failure)
            try:
                if sport == "football":
                    stats = await fetch_football_stats(bot.settings, name, school)
                else:
                    stats = await fetch_basketball_stats(bot.settings, name, school)
                if stats:
                    player.stats = stats
                    bot.transfer_store.save()
                    logger.info(f"Fetched career stats for {name}")
            except Exception:
                logger.warning(f"Failed to fetch stats for {name}", exc_info=True)
        if player is None:
            await interaction.edit_original_response(
                content=f"**{name}** is already on the {sport} transfer list."
            )
            return
        star_text = f" {STAR_EMOJI * stars}" if stars > 0 else ""
        stats_note = " (career stats loaded)" if player.stats else ""
        await interaction.edit_original_response(
            content=f"Added **{name}** ({position}, {school}){star_text} to the {sport} transfer list.{stats_note}"
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
        # Phase 13 / D-02: basketball targets are sheet-managed. Remove only allowed
        # when the matching entry is explicitly "outgoing"; any "target" match — or
        # an unknown name in a basketball channel — returns the sheet-managed message.
        if sport == "basketball":
            existing = next(
                (p for p in bot.transfer_store.list_players("basketball")
                 if p.name.lower() == name.lower()),
                None,
            )
            if existing is None or existing.type == "target":
                await interaction.edit_original_response(content=SHEET_MANAGED_MSG)
                return
        removed, suggestions = bot.transfer_store.remove_player(sport, name)
        if removed:
            bot.transfer_cache.clear()
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
    @app_commands.describe(
        position="Filter by position (e.g., QB, WR, PG)",
    )
    @require_sport_channel()
    async def transfer_list(
        interaction: discord.Interaction,
        position: str | None = None,
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        sport = get_sport_from_channel(interaction.channel_id, interaction.client.settings)
        cache_key = f"transfer:{sport}:{position.lower()}" if position else f"transfer:{sport}"
        cached = bot.transfer_cache.get(cache_key)
        if cached is not None:
            players = cached
        else:
            players = bot.transfer_store.list_players(sport, position=position)
            bot.transfer_cache.set(cache_key, players)
        emoji = SPORT_EMOJI.get(sport, "")
        title = f"{emoji} KU {SPORT_TITLE.get(sport, sport.title())} Transfer List"

        if not players and position:
            embed = discord.Embed(
                title=title,
                description=f"No {position.upper()} players on the {sport} transfer list.",
                color=KU_BLUE,
            )
            await interaction.edit_original_response(embeds=[embed])
            return

        if not players:
            embed = discord.Embed(
                title=title,
                description=f"No players on the {sport} transfer list yet.",
                color=KU_BLUE,
            )
            await interaction.edit_original_response(embeds=[embed])
            return

        # Separate players by type
        outgoing = [p for p in players if p.type == "outgoing"]
        targets = [p for p in players if p.type == "target"]

        sections = []
        if outgoing:
            sections.append(("\U0001f6aa Transfers Out", outgoing))
        if targets:
            sections.append(("\U0001f3af Transfer Targets", targets))

        embeds = []
        current_embed = discord.Embed(title=title, color=KU_BLUE)
        player_count = 0

        for section_title, section_players in sections:
            # Add section header (does NOT count toward player limit)
            current_embed.add_field(
                name=section_title,
                value=f"*{len(section_players)} player(s)*",
                inline=False,
            )
            for idx, player in enumerate(section_players):
                if player_count >= MAX_PLAYERS_PER_EMBED:
                    embeds.append(current_embed)
                    current_embed = discord.Embed(title=f"{title} (cont.)", color=KU_BLUE)
                    player_count = 0
                    # Re-add section header on continuation embed
                    current_embed.add_field(
                        name=section_title,
                        value="*continued*",
                        inline=False,
                    )
                star_display = STAR_EMOJI * player.stars if player.stars else "Unrated"
                field_name = f"{player.name} {star_display}"[:256]
                added_dt = datetime.fromisoformat(player.added_at)
                field_value = (
                    f"{player.position} | {player.school}\n"
                    f"Added {discord.utils.format_dt(added_dt, style='R')}"
                )
                current_embed.add_field(name=field_name, value=field_value, inline=False)
                player_count += 1

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
