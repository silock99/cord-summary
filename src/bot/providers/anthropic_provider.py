import logging

from anthropic import (
    AsyncAnthropic,
    APIError,
    APITimeoutError,
    RateLimitError,
    AuthenticationError,
)

from bot.models import SummaryError

logger = logging.getLogger(__name__)


class AnthropicSummaryProvider:
    """Anthropic Claude provider for summarization."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-haiku-4-5-20251001",
    ):
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model
        logger.info(f"Anthropic provider initialized: model={model}")

    async def summarize(self, text: str, prompt: str) -> str:
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=prompt,
                messages=[
                    {"role": "user", "content": text},
                ],
            )
            result = response.content[0].text
            if not result:
                raise SummaryError("LLM returned an empty response.")
            return result
        except AuthenticationError:
            raise SummaryError(
                "Invalid API key. Check your ANTHROPIC_API_KEY configuration."
            )
        except RateLimitError:
            raise SummaryError(
                "LLM rate limit exceeded. Please try again in a moment."
            )
        except APITimeoutError:
            raise SummaryError("LLM request timed out. Please try again.")
        except APIError as e:
            raise SummaryError(f"LLM API error: {e.message}")

    async def close(self) -> None:
        await self.client.close()
