"""Slash command handler for /post-summary (admin-only public summary posting)."""

import logging
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from zoneinfo import ZoneInfo

from bot.commands.summary import TIMERANGE_CHOICES, TIMERANGE_LABELS
from bot.formatting.embeds import build_summary_embeds
from bot.models import SummaryError
from bot.summarizer import summarize_channel

logger = logging.getLogger(__name__)


def register_post_summary_command(bot) -> None:
    """Register the /post-summary slash command on the bot's command tree."""

    def is_admin():
        async def predicate(interaction: discord.Interaction) -> bool:
            admin_ids = interaction.client.settings.admin_user_ids
            if interaction.user.id not in admin_ids:
                raise app_commands.CheckFailure(
                    "You don't have permission to use this command."
                )
            return True
        return app_commands.check(predicate)

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

    @bot.tree.command(
        name="post-summary",
        description="Post a public summary to the summary channel (admin only)",
    )
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(
        timerange="Time period to summarize",
        channel="Channel to summarize",
    )
    @app_commands.choices(timerange=TIMERANGE_CHOICES)
    @app_commands.autocomplete(channel=channel_autocomplete)
    @is_admin()
    async def post_summary(
        interaction: discord.Interaction,
        channel: str,
        timerange: int = 240,
    ) -> None:
        # Defer ephemerally -- only the admin sees progress/confirmation
        await interaction.response.defer(ephemeral=True)

        # Resolve target channel
        target = interaction.guild.get_channel(int(channel))
        if not target:
            await interaction.edit_original_response(content="Channel not found.")
            return

        # Validate target is in allowed channels
        if target.id not in bot.settings.allowed_channel_ids:
            await interaction.edit_original_response(
                content="This channel isn't enabled for summaries."
            )
            return

        # Calculate time range
        now = datetime.now(timezone.utc)
        after = now - timedelta(minutes=timerange)
        timerange_label = TIMERANGE_LABELS.get(timerange, f"Last {timerange} minutes")

        # Summarize
        try:
            summary_text = await summarize_channel(
                target,
                interaction.guild,
                bot.provider,
                after,
                max_context_tokens=bot.settings.max_context_tokens,
            )
        except SummaryError as e:
            await interaction.edit_original_response(content=f"Summary failed: {e}")
            return
        except Exception:
            logger.exception(f"/post-summary error summarizing #{target.name}")
            await interaction.edit_original_response(
                content="Something went wrong. Please try again later."
            )
            return

        # Check for empty result
        if summary_text == "No messages to summarize.":
            await interaction.edit_original_response(
                content=f"No significant activity in {target.mention} in the {timerange_label.lower()}."
            )
            return

        # Resolve summary channel
        summary_channel = bot.get_channel(bot.settings.summary_channel_id)
        if summary_channel is None:
            await interaction.edit_original_response(
                content="Summary channel not found."
            )
            return

        # Determine posting target (channel or thread)
        if bot.settings.use_threads:
            tz = ZoneInfo(bot.settings.timezone)
            now_tz = datetime.now(tz)
            date_str = now_tz.strftime("%b %d")
            posting_target = await summary_channel.create_thread(
                name=f"Summary \u2014 #{target.name} \u2014 {date_str}",
                type=discord.ChannelType.public_thread,
                auto_archive_duration=1440,
            )
        else:
            posting_target = summary_channel

        # Build and send embeds
        embeds = build_summary_embeds(summary_text, target.name, timerange_label)
        for embed in embeds:
            embed.set_footer(text=f"Requested by {interaction.user.display_name}")
            await posting_target.send(embed=embed)

        # Confirm to admin
        await interaction.edit_original_response(
            content=f"Summary posted to {posting_target.mention}."
        )

        logger.info(
            f"/post-summary by {interaction.user} for #{target.name} ({timerange_label})"
        )

    @post_summary.error
    async def post_summary_error(
        interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        if isinstance(error, app_commands.CheckFailure):
            if interaction.response.is_done():
                await interaction.followup.send(str(error), ephemeral=True)
            else:
                await interaction.response.send_message(str(error), ephemeral=True)
        else:
            logger.error(f"/post-summary error: {error}", exc_info=error)
            msg = "Something went wrong. Please try again later."
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
