"""Tests for the summarizer orchestrator (plan 01-03, Task 2)."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from bot.models import ProcessedMessage, SummaryError


class MockProvider:
    """Mock LLM provider that records calls and returns canned responses."""

    def __init__(self, responses: list[str]):
        self.responses = responses
        self.calls: list[tuple[str, str]] = []
        self._idx = 0

    async def summarize(self, text: str, prompt: str) -> str:
        self.calls.append((text, prompt))
        result = self.responses[self._idx]
        self._idx += 1
        return result

    async def close(self) -> None:
        pass


def _make_messages(count: int, start: datetime | None = None) -> list[ProcessedMessage]:
    """Create a list of ProcessedMessages for testing."""
    base = start or datetime(2026, 3, 27, 10, 0, 0)
    return [
        ProcessedMessage(
            author=f"user{i}",
            content=f"Message number {i}",
            timestamp=base + timedelta(minutes=i),
        )
        for i in range(count)
    ]


@pytest.mark.asyncio
async def test_summarize_empty_messages():
    """Empty message list returns a 'no messages' response without calling provider."""
    from bot.summarizer import summarize_messages

    provider = MockProvider(responses=[])
    result = await summarize_messages(provider, [])
    assert result == "No messages to summarize."
    assert len(provider.calls) == 0


@pytest.mark.asyncio
async def test_summarize_small_set():
    """Messages fitting in token budget produce a single LLM call (no chunking)."""
    from bot.summarizer import summarize_messages, SUMMARY_SYSTEM_PROMPT

    messages = _make_messages(5)
    provider = MockProvider(responses=["Summary of 5 messages"])

    result = await summarize_messages(provider, messages, max_context_tokens=120_000)

    assert result == "Summary of 5 messages"
    assert len(provider.calls) == 1
    # The single call should use the summary system prompt
    _, prompt = provider.calls[0]
    assert prompt == SUMMARY_SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_summarize_large_set_two_pass():
    """Messages exceeding token budget trigger chunk summaries then a final merge (D-09)."""
    from bot.summarizer import summarize_messages, MERGE_SYSTEM_PROMPT

    # Create messages spread across multiple hours so chunking kicks in
    messages = _make_messages(10, start=datetime(2026, 3, 27, 8, 0, 0))
    # Add messages in a second time window
    messages += _make_messages(
        10, start=datetime(2026, 3, 27, 10, 0, 0)
    )

    # Responses: one per chunk summary + one merge
    provider = MockProvider(
        responses=["Chunk 1 summary", "Chunk 2 summary", "Final merged summary"]
    )

    # Set max_tokens very low to force chunking
    result = await summarize_messages(provider, messages, max_context_tokens=1)

    assert result == "Final merged summary"
    # Should have 3 calls: 2 chunk summaries + 1 merge
    assert len(provider.calls) == 3
    # Last call should use merge prompt
    _, last_prompt = provider.calls[-1]
    assert last_prompt == MERGE_SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_provider_error_propagates():
    """SummaryError from provider propagates unchanged."""
    from bot.summarizer import summarize_messages

    class ErrorProvider:
        async def summarize(self, text: str, prompt: str) -> str:
            raise SummaryError("Provider failed badly")

        async def close(self) -> None:
            pass

    messages = _make_messages(3)
    with pytest.raises(SummaryError, match="Provider failed badly"):
        await summarize_messages(ErrorProvider(), messages)


@pytest.mark.asyncio
async def test_preprocess_filters_applied():
    """Raw discord messages are filtered through preprocessor in summarize_channel."""
    from bot.summarizer import summarize_channel

    # Create mock discord objects
    mock_channel = MagicMock()
    mock_guild = MagicMock()
    provider = MockProvider(responses=["Channel summary"])

    fake_msg1 = MagicMock()
    fake_msg2 = MagicMock()
    fake_msg3 = MagicMock()

    processed1 = ProcessedMessage(
        author="alice", content="Hello", timestamp=datetime(2026, 3, 27, 10, 0)
    )
    processed2 = ProcessedMessage(
        author="bob", content="Hi there", timestamp=datetime(2026, 3, 27, 10, 1)
    )

    after = datetime(2026, 3, 27, 9, 0)

    with patch("bot.summarizer.fetch_messages", new_callable=AsyncMock) as mock_fetch, \
         patch("bot.summarizer.preprocess_message") as mock_preprocess:
        mock_fetch.return_value = [fake_msg1, fake_msg2, fake_msg3]
        # First two pass preprocessing, third is filtered (returns None)
        mock_preprocess.side_effect = [processed1, processed2, None]

        result = await summarize_channel(
            mock_channel, mock_guild, provider, after, max_context_tokens=120_000
        )

    assert result == "Channel summary"
    assert mock_fetch.called
    assert mock_preprocess.call_count == 3
    # Provider should have been called with 2 messages (one filtered out)
    assert len(provider.calls) == 1
