"""Message chunking for two-pass summarization (D-09)."""

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


def format_chunk_for_llm(messages: list[ProcessedMessage]) -> str:
    """Format a list of ProcessedMessages into a single text block for LLM input."""
    return "\n".join(msg.to_line() for msg in messages)
