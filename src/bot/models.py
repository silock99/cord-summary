from dataclasses import dataclass
from datetime import datetime


@dataclass
class ProcessedMessage:
    author: str        # Display name (per D-07)
    content: str       # Cleaned text (per D-04)
    timestamp: datetime

    def to_line(self) -> str:
        return f"{self.author}: {self.content}"


class SummaryError(Exception):
    """Raised when summarization fails. Message is user-facing (per D-10)."""
    pass
