"""Message preprocessing: filtering, mention resolution, and text cleaning."""

import re

import discord

from bot.models import ProcessedMessage


def preprocess_message(
    message: discord.Message, guild: discord.Guild
) -> ProcessedMessage | None:
    """Transform a raw Discord message into a ProcessedMessage, or None if filtered.

    Filters out bot messages and system messages (D-05).
    Resolves mentions to display names (D-04).
    Preserves links (D-06).
    Uses author display_name (D-07).
    """
    # D-05: Filter bot and system messages
    if message.author.bot:
        return None
    if message.type not in (discord.MessageType.default, discord.MessageType.reply):
        return None

    content = message.content

    # D-04: Resolve @user mentions to display names
    for mention in message.mentions:
        member = guild.get_member(mention.id)
        display = member.display_name if member else mention.name
        content = content.replace(f"<@{mention.id}>", f"@{display}")
        content = content.replace(f"<@!{mention.id}>", f"@{display}")

    # D-04: Resolve #channel mentions
    for ch in message.channel_mentions:
        content = content.replace(f"<#{ch.id}>", f"#{ch.name}")

    # D-04: Resolve @role mentions
    for role in message.role_mentions:
        content = content.replace(f"<@&{role.id}>", f"@{role.name}")

    # D-04: Replace custom emoji markup, keep the name
    content = re.sub(r"<a?:(\w+):\d+>", r":\1:", content)

    # D-04: Attachment marker
    if message.attachments:
        content += " [attachment]" if content else "[attachment]"

    # D-06: Links preserved (naturally present in content)

    content = content.strip()
    if not content:
        return None

    # D-07: Author display name
    return ProcessedMessage(
        author=message.author.display_name,
        content=content,
        timestamp=message.created_at,
    )
