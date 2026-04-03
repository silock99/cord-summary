"""Message chunking for two-pass summarization (D-09)."""

from collections import defaultdict
from datetime import timedelta

from bot.models import ProcessedMessage


def estimate_tokens(text: str, chars_per_token: float = 3.5) -> int:
    """Estimate token count using character-based heuristic."""
    return int(len(text) / chars_per_token)


def needs_chunking(messages: list[ProcessedMessage], max_tokens: int) -> bool:
    """Check if messages exceed the token budget and need chunking."""
    text = format_chunk_for_llm(messages)
    return estimate_tokens(text) > max_tokens


def chunk_by_time_window(
    messages: list[ProcessedMessage],
    window: timedelta = timedelta(hours=1),
) -> list[list[ProcessedMessage]]:
    """Split messages into chunks based on time windows.

    Each chunk contains messages within a `window`-sized period.
    Messages must be sorted by timestamp (oldest first).
    """
    if not messages:
        return []

    chunks: list[list[ProcessedMessage]] = []
    current_chunk: list[ProcessedMessage] = [messages[0]]
    window_start = messages[0].timestamp

    for msg in messages[1:]:
        if msg.timestamp - window_start >= window:
            chunks.append(current_chunk)
            current_chunk = [msg]
            window_start = msg.timestamp
        else:
            current_chunk.append(msg)

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def _render_replies(
    parent: ProcessedMessage,
    children: dict[int, list[ProcessedMessage]],
    lines: list[str],
    depth: int,
    max_depth: int = 2,
) -> None:
    """Recursively render reply chains with indentation capped at max_depth.

    Stops at depth 50 to prevent stack overflow on adversarial reply chains.
    """
    if depth > 50:
        return
    indent = "  " * min(depth, max_depth)
    for reply in children.get(parent.message_id, []):
        lines.append(f"{indent}> {reply.to_line()}")
        _render_replies(reply, children, lines, depth + 1, max_depth)


def format_chunk_for_llm(messages: list[ProcessedMessage]) -> str:
    """Format messages with reply-chain indentation for LLM input (D-01)."""
    if not any(m.reply_to_id for m in messages):
        return "\n".join(m.to_line() for m in messages)

    # Build parent-child index
    by_id: dict[int, ProcessedMessage] = {
        m.message_id: m for m in messages if m.message_id
    }
    children: dict[int, list[ProcessedMessage]] = defaultdict(list)
    roots: list[ProcessedMessage] = []

    for msg in messages:
        if msg.reply_to_id and msg.reply_to_id in by_id:
            children[msg.reply_to_id].append(msg)
        else:
            roots.append(msg)

    lines: list[str] = []
    for msg in roots:
        lines.append(msg.to_line())
        if msg.message_id:
            _render_replies(msg, children, lines, depth=1)

    return "\n".join(lines)
