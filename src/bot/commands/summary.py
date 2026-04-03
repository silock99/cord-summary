"""Slash command handler for /summary (SUM-01, SUM-02, SUM-04, SUM-05)."""

import logging
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands

from bot.formatting.embeds import build_summary_embeds
from bot.models import ProcessedMessage, SummaryError
from bot.pipeline.fetcher import fetch_messages
from bot.pipeline.preprocessor import preprocess_message
from bot.summarizer import summarize_messages

logger = logging.getLogger(__name__)

# Per-user cooldown tracking: {user_id: last_usage_datetime}
_cooldowns: dict[int, datetime] = {}

TIMERANGE_CHOICES = [
    app_commands.Choice(name="Last 30 minutes", value=30),
    app_commands.Choice(name="Last 1 hour", value=60),
    app_commands.Choice(name="Last 4 hours", value=240),
    app_commands.Choice(name="Last 12 hours", value=720),
    app_commands.Choice(name="Last 24 hours", value=1440),
]

TIMERANGE_LABELS = {
    30: "Last 30 minutes",
    60: "Last 1 hour",
    240: "Last 4 hours",
    720: "Last 12 hours",
    1440: "Last 24 hours",
}


def register_summary_command(bot) -> None:
    """Register the /summary slash command on the bot's command tree."""

    async def channel_autocomplete(
        interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Only show channels from the allowlist."""
        choices = []
        for cid in bot.settings.allowed_channel_ids:
            ch = interaction.guild.get_channel(cid)
            if ch and current.lower() in ch.name.lower():
                choices.append(app_commands.Choice(name=f"#{ch.name}", value=str(cid)))
        return choices[:25]

    @bot.tree.command(name="summary", description="Summarize recent channel activity")
    @app_commands.describe(
        timerange="Time period to summarize",
        channel="Channel to summarize (defaults to current channel)",
    )
    @app_commands.choices(timerange=TIMERANGE_CHOICES)
    @app_commands.autocomplete(channel=channel_autocomplete)
    async def summary(
        interaction: discord.Interaction,
        timerange: int = 240,
        channel: str | None = None,
    ) -> None:
        # Step 0 - Cooldown check
        cooldown = bot.settings.summary_cooldown_seconds
        if cooldown > 0:
            user_id = interaction.user.id
            now = datetime.now(timezone.utc)
            last_used = _cooldowns.get(user_id)
            if last_used and (now - last_used).total_seconds() < cooldown:
                remaining = cooldown - int((now - last_used).total_seconds())
                minutes, seconds = divmod(remaining, 60)
                hours, minutes = divmod(minutes, 60)
                parts = []
                if hours:
                    parts.append(f"{hours}h")
                if minutes:
                    parts.append(f"{minutes}m")
                if seconds and not hours:
                    parts.append(f"{seconds}s")
                await interaction.response.send_message(
                    f"You can use `/summary` again in {' '.join(parts)}.",
                    ephemeral=True,
                )
                return

        # Step 1 - Defer immediately (per D-04)
        await interaction.response.defer(ephemeral=True)

        # Step 2 - Resolve target channel (per D-09)
        if channel:
            target = interaction.guild.get_channel(int(channel))
            if not target:
                await interaction.edit_original_response(content="Channel not found.")
                return
        else:
            target = interaction.channel

        # Step 3 - Validate allowlist (per D-08, D-10)
        if not bot.settings.allowed_channel_ids:
            await interaction.edit_original_response(
                content="No channels are configured for summaries. Ask an admin to set ALLOWED_CHANNEL_IDS."
            )
            return

        if target.id not in bot.settings.allowed_channel_ids:
            mentions = ", ".join(f"<#{cid}>" for cid in bot.settings.allowed_channel_ids)
            await interaction.edit_original_response(
                content=f"This channel isn't enabled for summaries. Available channels: {mentions}"
            )
            return

        # Step 4 - Calculate time range
        now = datetime.now(timezone.utc)
        after = now - timedelta(minutes=timerange)
        timerange_label = TIMERANGE_LABELS.get(timerange, f"Last {timerange} minutes")

        # Step 5 - Fetch and preprocess messages
        raw_messages = await fetch_messages(target, after)
        processed: list[ProcessedMessage] = []
        for msg in raw_messages:
            result = preprocess_message(msg, interaction.guild)
            if result is not None:
                processed.append(result)

        # Step 6 - Check quiet threshold (per D-11, D-12)
        if len(processed) < bot.settings.quiet_threshold:
            await interaction.edit_original_response(
                content=f"No significant activity in {target.mention} in the {timerange_label.lower()}."
            )
            return

        # Step 7 - Summarize via provider
        try:
            summary_text = await summarize_messages(
                bot.provider, processed, bot.settings.max_context_tokens
            )
        except SummaryError as e:
            await interaction.edit_original_response(content=f"Summary failed: {e}")
            return

        # Step 8 - Build embeds and send (per D-06)
        embeds = build_summary_embeds(summary_text, target.name, timerange_label)
        await interaction.edit_original_response(embed=embeds[0])
        for extra in embeds[1:]:
            await interaction.followup.send(embed=extra, ephemeral=True)

        # Record cooldown after successful summary
        if bot.settings.summary_cooldown_seconds > 0:
            _cooldowns[interaction.user.id] = datetime.now(timezone.utc)

        logger.info(
            f"/summary by {interaction.user} in #{target.name} "
            f"({timerange_label}): {len(processed)} messages -> {len(embeds)} embed(s)"
        )
