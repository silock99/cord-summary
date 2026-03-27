from typing import Protocol, runtime_checkable


@runtime_checkable
class SummaryProvider(Protocol):
    async def summarize(self, text: str, prompt: str) -> str:
        """Send text to an LLM with the given system prompt and return the summary text."""
        ...

    async def close(self) -> None:
        """Clean up provider resources (HTTP clients, etc.)."""
        ...
