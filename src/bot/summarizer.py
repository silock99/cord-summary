"""Summarizer orchestrator: fetch -> preprocess -> chunk -> summarize (PIPE-04)."""

import logging
from collections import Counter
from dataclasses import dataclass
from datetime import datetime

import discord

from bot.models import ProcessedMessage, SummaryError
from bot.providers.base import SummaryProvider
from bot.pipeline.fetcher import fetch_messages
from bot.pipeline.preprocessor import preprocess_message
from bot.language_filter import get_language_guidelines
from bot.pipeline.chunker import (
    chunk_by_time_window,
    format_chunk_for_llm,
    needs_chunking,
)

logger = logging.getLogger(__name__)


@dataclass
class SummaryResult:
    """Result of a channel summarization including metadata for embed footer."""
    text: str
    message_count: int
    participant_count: int


SUMMARY_SYSTEM_PROMPT = (
    "You are a Discord channel summarizer. Given a conversation log, produce a concise "
    "summary organized by discussion topic.\n\n"
    "## Output Rules\n"
    "- Focus on WHAT was discussed, not WHO said it. Never include usernames, "
    "display names, or @mentions in the summary.\n"
    "- Each topic: bold header (**Topic Name**) followed by bullet points.\n"
    "- Each bullet: topic name + one-line takeaway. Headline depth only -- no paragraphs.\n"
    "- If any messages are marked [IMPORTANT], create an **Announcements** section at the "
    "very top (before all topic sections). List each announcement as a bullet with the "
    "verbatim message text.\n"
    "- Order remaining topics by engagement: topics with [POPULAR] markers appear first. "
    "Do not add any special formatting to popular topics -- just list them earlier.\n"
    "- Drop minor topics that had only 1-2 messages with no reactions or replies.\n"
    "- When messages contain URLs, include them inline in the relevant bullet. "
    "Never collect links into a separate section.\n"
    "- Do NOT include a TL;DR, key takeaways, or executive summary section.\n"
    "- Do NOT note whether discussions are resolved or ongoing.\n"
    "- Tone: clear, neutral English. No slang, no corporate jargon.\n\n"
    "## Input Signal Reference\n"
    "- [IMPORTANT]: @here/@everyone message -- MUST appear in Announcements section.\n"
    "- [POPULAR]: High-engagement message -- prioritize its topic.\n"
    "- [N reactions]: Community engagement level.\n"
    "- Indented > lines: Replies showing conversation flow.\n"
    "- [image/video/file: name]: Shared media -- mention briefly.\n"
    "- Parenthetical text: Embed content from links.\n"
)

MERGE_SYSTEM_PROMPT = (
    "You are a Discord channel summarizer. Given multiple time-period summaries from "
    "the same channel, produce one unified summary organized by discussion topic.\n\n"
    "## Output Rules\n"
    "- If any input summaries contain an **Announcements** section, consolidate all "
    "announcements into a single **Announcements** section at the top.\n"
    "- Each topic: bold header (**Topic Name**) followed by headline-depth bullets.\n"
    "- Merge related topics and remove redundancy.\n"
    "- Order topics by engagement level (most-discussed first).\n"
    "- Never include usernames or @mentions.\n"
    "- Preserve all URLs inline within their topic bullets.\n"
    "- Do NOT include TL;DR, key takeaways, or resolution status.\n"
    "- Tone: clear, neutral English. No slang, no corporate jargon.\n"
)


async def summarize_messages(
    provider: SummaryProvider,
    messages: list[ProcessedMessage],
    max_context_tokens: int = 120_000,
) -> str:
    """Orchestrate summarization with optional two-pass chunking (per D-09).

    If messages fit in token budget: single LLM call.
    If messages exceed budget: chunk by time window, summarize each, then merge.
    """
    if not messages:
        return "No messages to summarize."

    # Append language guidelines to prompts at runtime (Phase 5: LANG-01, LANG-05)
    guidelines = get_language_guidelines()
    summary_prompt = SUMMARY_SYSTEM_PROMPT + guidelines
    merge_prompt = MERGE_SYSTEM_PROMPT + guidelines

    if not needs_chunking(messages, max_context_tokens):
        # Single-pass: all messages fit
        text = format_chunk_for_llm(messages)
        logger.info(f"Single-pass summarization: {len(messages)} messages")
        return await provider.summarize(text, summary_prompt)

    # Two-pass (D-09): chunk -> summarize each -> merge
    chunks = chunk_by_time_window(messages)
    logger.info(f"Two-pass summarization: {len(messages)} messages in {len(chunks)} chunks")

    chunk_summaries: list[str] = []
    for i, chunk in enumerate(chunks):
        text = format_chunk_for_llm(chunk)
        summary = await provider.summarize(text, summary_prompt)
        chunk_summaries.append(summary)
        logger.info(f"Chunk {i+1}/{len(chunks)} summarized")

    # Merge pass
    merged_input = "\n\n---\n\n".join(
        f"Period {i+1} summary:\n{s}" for i, s in enumerate(chunk_summaries)
    )
    return await provider.summarize(merged_input, merge_prompt)


async def summarize_channel(
    channel: discord.TextChannel,
    guild: discord.Guild,
    provider: SummaryProvider,
    after: datetime,
    before: datetime | None = None,
    max_context_tokens: int = 120_000,
) -> SummaryResult:
    """Full pipeline: fetch -> preprocess -> summarize."""
    raw_messages = await fetch_messages(channel, after, before)

    processed: list[ProcessedMessage] = []
    for msg in raw_messages:
        result = preprocess_message(msg, guild)
        if result is not None:
            processed.append(result)

    logger.info(f"Preprocessed: {len(processed)}/{len(raw_messages)} messages kept")

    # Phase 4: Compute reply counts and set popularity flags (D-04)
    reply_counts: Counter[int] = Counter()
    for msg in processed:
        if msg.reply_to_id:
            reply_counts[msg.reply_to_id] += 1

    for msg in processed:
        msg.reply_count = reply_counts.get(msg.message_id, 0)
        if msg.reply_count >= 5 or msg.reaction_count >= 5:
            msg.is_popular = True

    participant_count = len({msg.author for msg in processed})
    message_count = len(processed)

    summary_text = await summarize_messages(provider, processed, max_context_tokens)
    return SummaryResult(
        text=summary_text,
        message_count=message_count,
        participant_count=participant_count,
    )
