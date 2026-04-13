"""Tests for the summarizer orchestrator."""

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
    # The single call should use the summary system prompt (with language guidelines appended)
    _, prompt = provider.calls[0]
    assert SUMMARY_SYSTEM_PROMPT in prompt


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
    # Last call should use merge prompt (with language guidelines appended)
    _, last_prompt = provider.calls[-1]
    assert MERGE_SYSTEM_PROMPT in last_prompt


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

    assert result.text == "Channel summary"
    assert result.message_count == 2
    assert result.participant_count == 2
    assert mock_fetch.called
    assert mock_preprocess.call_count == 3
    # Provider should have been called with 2 messages (one filtered out)
    assert len(provider.calls) == 1


class TestPromptContent:
    """Verify SUMMARY_SYSTEM_PROMPT and MERGE_SYSTEM_PROMPT contain required instructions."""

    def test_no_usernames(self):
        from bot.summarizer import SUMMARY_SYSTEM_PROMPT
        assert "Never include usernames, display names, or @mentions" in SUMMARY_SYSTEM_PROMPT

    def test_announcements_section(self):
        from bot.summarizer import SUMMARY_SYSTEM_PROMPT
        assert "Announcements" in SUMMARY_SYSTEM_PROMPT

    def test_headline_depth(self):
        from bot.summarizer import SUMMARY_SYSTEM_PROMPT
        assert "Headline depth" in SUMMARY_SYSTEM_PROMPT

    def test_inline_urls(self):
        from bot.summarizer import SUMMARY_SYSTEM_PROMPT
        assert "include them inline in the relevant bullet" in SUMMARY_SYSTEM_PROMPT

    def test_no_action_items_old_remnant(self):
        from bot.summarizer import SUMMARY_SYSTEM_PROMPT
        assert "action items or decisions as separate" not in SUMMARY_SYSTEM_PROMPT

    def test_drop_minor_topics(self):
        from bot.summarizer import SUMMARY_SYSTEM_PROMPT
        assert "Drop minor topics" in SUMMARY_SYSTEM_PROMPT

    def test_no_tldr(self):
        from bot.summarizer import SUMMARY_SYSTEM_PROMPT
        assert "Do NOT include a TL;DR" in SUMMARY_SYSTEM_PROMPT

    def test_no_resolution_status(self):
        from bot.summarizer import SUMMARY_SYSTEM_PROMPT
        assert "Do NOT note whether discussions are resolved" in SUMMARY_SYSTEM_PROMPT

    def test_merge_consolidate_announcements(self):
        from bot.summarizer import MERGE_SYSTEM_PROMPT
        assert "consolidate all announcements" in MERGE_SYSTEM_PROMPT

    def test_merge_no_usernames(self):
        from bot.summarizer import MERGE_SYSTEM_PROMPT
        assert "Never include usernames" in MERGE_SYSTEM_PROMPT


class TestSummaryResult:
    """Verify SummaryResult dataclass and summarize_channel metadata."""

    def test_summary_result_fields(self):
        from bot.summarizer import SummaryResult
        result = SummaryResult(text="test", message_count=10, participant_count=3)
        assert result.text == "test"
        assert result.message_count == 10
        assert result.participant_count == 3

    @pytest.mark.asyncio
    async def test_summary_result_metadata(self):
        """summarize_channel returns SummaryResult with correct counts."""
        from bot.summarizer import summarize_channel

        mock_channel = MagicMock()
        mock_guild = MagicMock()
        provider = MockProvider(responses=["Summary text"])

        # 3 messages from 2 unique authors
        processed_msgs = [
            ProcessedMessage(author="alice", content="Hello", timestamp=datetime(2026, 3, 27, 10, 0)),
            ProcessedMessage(author="bob", content="Hi", timestamp=datetime(2026, 3, 27, 10, 1)),
            ProcessedMessage(author="alice", content="How are you", timestamp=datetime(2026, 3, 27, 10, 2)),
        ]

        after = datetime(2026, 3, 27, 9, 0)

        with patch("bot.summarizer.fetch_messages", new_callable=AsyncMock) as mock_fetch, \
             patch("bot.summarizer.preprocess_message") as mock_preprocess:
            mock_fetch.return_value = [MagicMock(), MagicMock(), MagicMock()]
            mock_preprocess.side_effect = processed_msgs

            result = await summarize_channel(
                mock_channel, mock_guild, provider, after, max_context_tokens=120_000
            )

        assert result.text == "Summary text"
        assert result.message_count == 3
        assert result.participant_count == 2


class TestVolumeContext:
    """Verify _volume_context() thresholds and output (D-12)."""

    def test_low_10(self):
        from bot.summarizer import _volume_context
        result = _volume_context(10)
        assert "LOW" in result
        assert "10" in result

    def test_low_30(self):
        from bot.summarizer import _volume_context
        result = _volume_context(30)
        assert "LOW" in result
        assert "30" in result

    def test_medium_31(self):
        from bot.summarizer import _volume_context
        result = _volume_context(31)
        assert "MEDIUM" in result
        assert "31" in result

    def test_medium_100(self):
        from bot.summarizer import _volume_context
        result = _volume_context(100)
        assert "MEDIUM" in result

    def test_medium_150(self):
        from bot.summarizer import _volume_context
        result = _volume_context(150)
        assert "MEDIUM" in result
        assert "150" in result

    def test_high_151(self):
        from bot.summarizer import _volume_context
        result = _volume_context(151)
        assert "HIGH" in result
        assert "151" in result

    def test_high_500(self):
        from bot.summarizer import _volume_context
        result = _volume_context(500)
        assert "HIGH" in result

    def test_always_includes_count(self):
        from bot.summarizer import _volume_context
        for count in [1, 30, 31, 150, 151, 999]:
            result = _volume_context(count)
            assert str(count) in result

    @pytest.mark.asyncio
    async def test_single_pass_prepends_volume_preamble(self):
        """In single-pass summarization, user message text starts with volume preamble."""
        from bot.summarizer import summarize_messages

        messages = _make_messages(5)
        provider = MockProvider(responses=["Summary"])

        await summarize_messages(provider, messages, max_context_tokens=120_000)

        text, _ = provider.calls[0]
        assert text.startswith("[Volume:")

    @pytest.mark.asyncio
    async def test_two_pass_uses_total_count_preamble(self):
        """In two-pass summarization, each chunk gets total message count preamble."""
        from bot.summarizer import summarize_messages

        # Create messages in two time windows
        messages = _make_messages(10, start=datetime(2026, 3, 27, 8, 0, 0))
        messages += _make_messages(10, start=datetime(2026, 3, 27, 10, 0, 0))

        provider = MockProvider(
            responses=["Chunk 1", "Chunk 2", "Merged"]
        )

        await summarize_messages(provider, messages, max_context_tokens=1)

        # Each chunk call should have total count (20) in volume preamble
        for i in range(2):
            text, _ = provider.calls[i]
            assert text.startswith("[Volume: 20 messages")
