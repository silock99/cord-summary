"""Embed building and topic-boundary splitting for Discord summaries."""

import re

import discord

EMBED_DESC_LIMIT = 4096
EMBED_COLOR = 0x5865F2  # Discord blurple


def build_summary_embeds(
    summary_text: str,
    channel_name: str,
    timerange_label: str,
) -> list[discord.Embed]:
    """Build Discord embeds from summary text, splitting at topic boundaries.

    Topics are delimited by bold headers (lines starting with **).
    Each embed stays under EMBED_DESC_LIMIT (4096) characters.
    """
    if not summary_text or not summary_text.strip():
        return [_make_embed("No summary content generated.", channel_name, timerange_label, 0)]

    sections = _split_into_topics(summary_text)

    embeds: list[discord.Embed] = []
    current_text = ""

    for section in sections:
        # If adding this section would exceed the limit, finalize current embed
        if current_text and len(current_text) + len(section) + 2 > EMBED_DESC_LIMIT:
            embeds.append(_make_embed(current_text, channel_name, timerange_label, len(embeds)))
            current_text = ""

        # If a single section exceeds the limit, truncate it
        if len(section) > EMBED_DESC_LIMIT:
            section = section[: EMBED_DESC_LIMIT - 20] + "\n*(...truncated)*"

        current_text += ("\n\n" if current_text else "") + section

    # Finalize the last chunk
    if current_text:
        embeds.append(_make_embed(current_text, channel_name, timerange_label, len(embeds)))

    return embeds


def _split_into_topics(text: str) -> list[str]:
    """Split text at bold topic headers (lines starting with **)."""
    parts = re.split(r"(?=\n\*\*)", text)
    return [p.strip() for p in parts if p.strip()]


def _make_embed(
    description: str,
    channel_name: str,
    timerange_label: str,
    index: int,
) -> discord.Embed:
    """Create a single Discord embed for a summary chunk."""
    embed = discord.Embed(
        description=description,
        color=EMBED_COLOR,
    )
    if index == 0:
        embed.title = f"Summary: #{channel_name}"
    else:
        embed.title = f"Summary: #{channel_name} (continued)"
    embed.set_footer(text=f"Period: {timerange_label}")
    return embed
