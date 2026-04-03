from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ProcessedMessage:
    author: str        # Display name (per D-07)
    content: str       # Cleaned text (per D-04)
    timestamp: datetime
    # Phase 4: enriched metadata
    message_id: int = 0
    reply_to_id: int | None = None
    is_important: bool = False      # @here/@everyone per D-03
    is_popular: bool = False        # 5+ reactions OR 5+ replies per D-04
    reaction_count: int = 0         # Total reaction count per D-06
    reply_count: int = 0            # Computed post-preprocessing per D-04
    embeds_text: list[str] = field(default_factory=list)  # Per D-07

    def to_line(self) -> str:
        parts = []
        if self.is_important:
            parts.append("[IMPORTANT]")
        if self.is_popular:
            parts.append("[POPULAR]")
        parts.append(f"{self.author}: {self.content}")
        if self.reaction_count >= 5:
            parts.append(f"[{self.reaction_count} reactions]")
        if self.embeds_text:
            parts.append("(" + "; ".join(self.embeds_text) + ")")
        return " ".join(parts)


class SummaryError(Exception):
    """Raised when summarization fails. Message is user-facing (per D-10)."""
    pass
