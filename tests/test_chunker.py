"""Unit tests for the time-based chunker and token estimation."""

from datetime import datetime, timedelta, timezone

from bot.models import ProcessedMessage
from bot.pipeline.chunker import (
    chunk_by_time_window,
    estimate_tokens,
    format_chunk_for_llm,
    needs_chunking,
)


def _msg(content: str, minutes_offset: int = 0) -> ProcessedMessage:
    """Create a ProcessedMessage at a given minute offset from a base time."""
    base = datetime(2026, 3, 27, 10, 0, 0, tzinfo=timezone.utc)
    return ProcessedMessage(
        author="User",
        content=content,
        timestamp=base + timedelta(minutes=minutes_offset),
    )


def test_empty_messages_returns_empty():
    assert chunk_by_time_window([]) == []


def test_single_message_single_chunk():
    msgs = [_msg("hello", 0)]
    chunks = chunk_by_time_window(msgs)
    assert len(chunks) == 1
    assert len(chunks[0]) == 1


def test_messages_within_window_same_chunk():
    msgs = [_msg("first", 0), _msg("second", 30)]
    chunks = chunk_by_time_window(msgs, window=timedelta(hours=1))
    assert len(chunks) == 1
    assert len(chunks[0]) == 2


def test_messages_across_windows():
    msgs = [_msg("first", 0), _msg("second", 121)]  # 2h1m apart
    chunks = chunk_by_time_window(msgs, window=timedelta(hours=1))
    assert len(chunks) == 2
    assert len(chunks[0]) == 1
    assert len(chunks[1]) == 1


def test_custom_window_size():
    msgs = [_msg("a", 0), _msg("b", 20), _msg("c", 40)]
    chunks = chunk_by_time_window(msgs, window=timedelta(minutes=30))
    assert len(chunks) == 2  # a+b in first chunk, c in second


def test_estimate_tokens():
    text = "hello world"  # 11 chars
    tokens = estimate_tokens(text)
    assert tokens == int(11 / 3.5)  # 3


def test_needs_chunking_true():
    # Create messages that exceed a small token limit
    msgs = [_msg("x" * 100, i) for i in range(10)]
    assert needs_chunking(msgs, max_tokens=10) is True


def test_needs_chunking_false():
    msgs = [_msg("hi", 0)]
    assert needs_chunking(msgs, max_tokens=10000) is False


def test_format_chunk_for_llm():
    msgs = [
        ProcessedMessage(author="Alice", content="hello", timestamp=datetime.now(timezone.utc)),
        ProcessedMessage(author="Bob", content="world", timestamp=datetime.now(timezone.utc)),
    ]
    result = format_chunk_for_llm(msgs)
    assert result == "Alice: hello\nBob: world"
