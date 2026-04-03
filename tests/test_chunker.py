"""Unit tests for the time-based chunker and token estimation."""

from datetime import datetime, timedelta, timezone

from bot.models import ProcessedMessage
from bot.pipeline.chunker import (
    chunk_by_time_window,
    estimate_tokens,
    format_chunk_for_llm,
    needs_chunking,
)


def _msg(content: str, minutes_offset: int = 0, *, message_id: int = 0,
         reply_to_id: int | None = None, is_important: bool = False,
         is_popular: bool = False, reaction_count: int = 0) -> ProcessedMessage:
    """Create a ProcessedMessage at a given minute offset from a base time."""
    base = datetime(2026, 3, 27, 10, 0, 0, tzinfo=timezone.utc)
    return ProcessedMessage(
        author="User",
        content=content,
        timestamp=base + timedelta(minutes=minutes_offset),
        message_id=message_id,
        reply_to_id=reply_to_id,
        is_important=is_important,
        is_popular=is_popular,
        reaction_count=reaction_count,
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


def test_reply_indentation():
    """Reply to a message in the same chunk renders indented with '  > ' prefix."""
    parent = _msg("parent message", 0, message_id=1)
    reply = _msg("reply message", 1, message_id=2, reply_to_id=1)
    result = format_chunk_for_llm([parent, reply])
    assert result == "User: parent message\n  > User: reply message"


def test_reply_depth_cap_at_two():
    """Reply chains deeper than depth 2 flatten to depth 2 indentation."""
    a = _msg("msg A", 0, message_id=1)
    b = _msg("msg B", 1, message_id=2, reply_to_id=1)
    c = _msg("msg C", 2, message_id=3, reply_to_id=2)
    d = _msg("msg D", 3, message_id=4, reply_to_id=3)
    result = format_chunk_for_llm([a, b, c, d])
    lines = result.split("\n")
    assert lines[0] == "User: msg A"
    assert lines[1] == "  > User: msg B"       # depth 1
    assert lines[2] == "    > User: msg C"      # depth 2
    assert lines[3] == "    > User: msg D"      # depth 3 capped at 2


def test_reply_parent_missing():
    """Reply to a message not in the chunk renders as root (no indentation)."""
    reply = _msg("orphan reply", 0, message_id=5, reply_to_id=999)
    result = format_chunk_for_llm([reply])
    assert result == "User: orphan reply"


def test_mixed_roots_and_replies():
    """Mixed roots and replies: reply appears indented after parent, other roots after."""
    root1 = _msg("first root", 0, message_id=1)
    reply1 = _msg("reply to first", 1, message_id=2, reply_to_id=1)
    root2 = _msg("second root", 2, message_id=3)
    result = format_chunk_for_llm([root1, reply1, root2])
    lines = result.split("\n")
    assert lines[0] == "User: first root"
    assert lines[1] == "  > User: reply to first"
    assert lines[2] == "User: second root"


def test_important_marker_in_formatted_output():
    """Message with is_important=True includes [IMPORTANT] in output."""
    msg = _msg("announcement", 0, message_id=1, is_important=True)
    result = format_chunk_for_llm([msg])
    assert "[IMPORTANT]" in result


def test_popular_marker_in_formatted_output():
    """Message with is_popular=True includes [POPULAR] in output."""
    msg = _msg("hot take", 0, message_id=1, is_popular=True)
    result = format_chunk_for_llm([msg])
    assert "[POPULAR]" in result


def test_reaction_count_in_formatted_output():
    """Message with reaction_count=8 includes [8 reactions] in output."""
    msg = _msg("reacted msg", 0, message_id=1, reaction_count=8)
    result = format_chunk_for_llm([msg])
    assert "[8 reactions]" in result
