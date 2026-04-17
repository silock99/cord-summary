"""Slash command handler for /cordbot help command."""

from dataclasses import dataclass

import discord
from discord import app_commands


KU_BLUE = 0x0051BA


@dataclass
class CommandInfo:
    name: str           # slash command name (e.g., "summary")
    params: str         # parameter display (e.g., "[timerange] [channel]")
    description: str    # one-liner description
    category: str       # one of: "summaries", "recruiting", "transfers", "stats_roster", "admin"
    permission: str     # one of: "public", "editor", "admin"


# Update this list when adding new commands.
COMMANDS: list[CommandInfo] = [
    CommandInfo("summary", "[timerange] [channel]", "Summarize recent channel activity", "summaries", "public"),
    CommandInfo("recruit-add", "<name> <position> <school> <stars> [sport]", "Add a player to the recruiting list", "recruiting", "editor"),
    CommandInfo("recruit-remove", "<name> [sport]", "Remove a player from the recruiting list", "recruiting", "editor"),
    CommandInfo("recruit-list", "[sport]", "View the recruiting list", "recruiting", "public"),
    CommandInfo("transfer-add", "<name> <position> <school> <stars> [sport]", "Add a player to the transfer list", "transfers", "editor"),
    CommandInfo("transfer-remove", "<name> [sport]", "Remove a player from the transfer list", "transfers", "editor"),
    CommandInfo("transfer-list", "[sport]", "View the transfer list", "transfers", "public"),
    CommandInfo("stats", "<player>", "Look up college career stats", "stats_roster", "public"),
    CommandInfo("roster-import", "<sport>", "Import the current KU roster from API", "stats_roster", "editor"),
    CommandInfo("roster-list", "[sport]", "View the current KU roster", "stats_roster", "public"),
    CommandInfo("post-summary", "<channel> [timerange]", "Post a public summary (admin only)", "admin", "admin"),
]

CATEGORIES = [
    ("summaries", "\U0001f4dd Summaries"),
    ("recruiting", "\U0001f3af Recruiting"),
    ("transfers", "\U0001f504 Transfers"),
    ("stats_roster", "\U0001f4ca Stats & Roster"),
    ("admin", "\U0001f6e1\ufe0f Admin"),
]


def get_visible_commands(interaction: discord.Interaction) -> list[CommandInfo]:
    """Filter commands based on the invoking user's permissions."""
    settings = interaction.client.settings
    is_admin = (
        interaction.user.id in settings.admin_user_ids
        or interaction.user.guild_permissions.manage_guild
    )
    is_editor = interaction.user.id in settings.recruiting_editor_ids or is_admin

    visible = []
    for cmd in COMMANDS:
        if cmd.permission == "public":
            visible.append(cmd)
        elif cmd.permission == "editor" and is_editor:
            visible.append(cmd)
        elif cmd.permission == "admin" and is_admin:
            visible.append(cmd)
    return visible


def build_help_embed(commands: list[CommandInfo]) -> discord.Embed:
    """Build a categorized embed listing the given commands."""
    embed = discord.Embed(title="CordBot Commands", color=KU_BLUE)

    for cat_key, cat_label in CATEGORIES:
        cat_commands = [c for c in commands if c.category == cat_key]
        if not cat_commands:
            continue

        lines = []
        for cmd in cat_commands:
            if cmd.params:
                lines.append(f"`/{cmd.name} {cmd.params}` -- {cmd.description}")
            else:
                lines.append(f"`/{cmd.name}` -- {cmd.description}")

        embed.add_field(name=cat_label, value="\n".join(lines), inline=False)

    embed.set_footer(text="Use commands in the appropriate channel. | /cordbot")
    return embed


def register_help_commands(bot) -> None:
    """Register the /cordbot help command."""

    @bot.tree.command(name="cordbot", description="Show all bot commands and how to use them")
    @app_commands.describe(public="Post the help publicly in the channel (admin only)")
    async def cordbot(interaction: discord.Interaction, public: bool = False) -> None:
        visible = get_visible_commands(interaction)
        embed = build_help_embed(visible)
        ephemeral = not (public and interaction.user.id in interaction.client.settings.admin_user_ids)
        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
