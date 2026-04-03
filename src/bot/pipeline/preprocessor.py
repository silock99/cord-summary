"""Message preprocessing: filtering, mention resolution, and text cleaning."""

import re

import discord

from bot.models import ProcessedMessage


def classify_attachment(attachment: discord.Attachment) -> str:
    """Classify attachment type from MIME content_type prefix."""
    ct = attachment.content_type or ""
    if ct.startswith("image/"):
        return "image"
    elif ct.startswith("video/"):
        return "video"
    elif ct.startswith("audio/"):
        return "audio"
    return "file"


def extract_embed_text(embed: discord.Embed) -> str | None:
    """Extract title and description from an embed, truncating long descriptions."""
    parts = []
    if embed.title:
        parts.append(embed.title)
    if embed.description:
        desc = embed.description[:200] if len(embed.description) > 200 else embed.description
        parts.append(desc)
    return " - ".join(parts) if parts else None


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

    # D-05: Typed attachment markers
    for att in message.attachments:
        att_type = classify_attachment(att)
        marker = f"[{att_type}: {att.filename}]"
        content = f"{content} {marker}" if content else marker

    # D-07: Extract embed text (limit to first 3)
    embeds_text = []
    for embed in message.embeds[:3]:
        text = extract_embed_text(embed)
        if text:
            embeds_text.append(text)

    # D-03: Importance flag
    is_important = message.mention_everyone

    # D-06: Reaction count
    reaction_count = sum(r.count for r in message.reactions)

    # D-06: Links preserved (naturally present in content)

    content = content.strip()
    if not content:
        return None

    # D-07: Author display name, enriched with Phase 4 metadata
    return ProcessedMessage(
        author=message.author.display_name,
        content=content,
        timestamp=message.created_at,
        message_id=message.id,
        reply_to_id=message.reference.message_id if message.reference else None,
        is_important=is_important,
        reaction_count=reaction_count,
        embeds_text=embeds_text,
    )
