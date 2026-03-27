"""Summarizer orchestrator: fetch -> preprocess -> chunk -> summarize (PIPE-04)."""

import logging
from datetime import datetime

import discord

from bot.models import ProcessedMessage, SummaryError
from bot.providers.base import SummaryProvider
from bot.pipeline.fetcher import fetch_messages
from bot.pipeline.preprocessor import preprocess_message
from bot.pipeline.chunker import (
    chunk_by_time_window,
    format_chunk_for_llm,
    needs_chunking,
)

logger = logging.getLogger(__name__)

SUMMARY_SYSTEM_PROMPT = (
    "You are a Discord channel summarizer. Given a conversation log, produce a concise "
    "bullet-point summary organized by topic. Include key decisions and action items. "
    "Use clear, brief language. Do not include timestamps or repeat verbatim quotes."
)

MERGE_SYSTEM_PROMPT = (
    "You are a Discord channel summarizer. Given multiple time-period summaries from the same channel, "
    "produce one unified bullet-point summary organized by topic. Merge related topics, remove redundancy, "
    "and highlight key decisions and action items."
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

    if not needs_chunking(messages, max_context_tokens):
        # Single-pass: all messages fit
        text = format_chunk_for_llm(messages)
        logger.info(f"Single-pass summarization: {len(messages)} messages")
        return await provider.summarize(text, SUMMARY_SYSTEM_PROMPT)

    # Two-pass (D-09): chunk -> summarize each -> merge
    chunks = chunk_by_time_window(messages)
    logger.info(f"Two-pass summarization: {len(messages)} messages in {len(chunks)} chunks")

    chunk_summaries: list[str] = []
    for i, chunk in enumerate(chunks):
        text = format_chunk_for_llm(chunk)
        summary = await provider.summarize(text, SUMMARY_SYSTEM_PROMPT)
        chunk_summaries.append(summary)
        logger.info(f"Chunk {i+1}/{len(chunks)} summarized")

    # Merge pass
    merged_input = "\n\n---\n\n".join(
        f"Period {i+1} summary:\n{s}" for i, s in enumerate(chunk_summaries)
    )
    return await provider.summarize(merged_input, MERGE_SYSTEM_PROMPT)


async def summarize_channel(
    channel: discord.TextChannel,
    guild: discord.Guild,
    provider: SummaryProvider,
    after: datetime,
    before: datetime | None = None,
    max_context_tokens: int = 120_000,
) -> str:
    """Full pipeline: fetch -> preprocess -> summarize."""
    raw_messages = await fetch_messages(channel, after, before)

    processed: list[ProcessedMessage] = []
    for msg in raw_messages:
        result = preprocess_message(msg, guild)
        if result is not None:
            processed.append(result)

    logger.info(f"Preprocessed: {len(processed)}/{len(raw_messages)} messages kept")
    return await summarize_messages(provider, processed, max_context_tokens)
