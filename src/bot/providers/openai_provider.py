import logging

from openai import (
    AsyncOpenAI,
    APIError,
    APITimeoutError,
    RateLimitError,
    AuthenticationError,
)

from bot.models import SummaryError

logger = logging.getLogger(__name__)


class OpenAISummaryProvider:
    """OpenAI-compatible provider. Supports any OpenAI-compatible endpoint via base_url (per D-03)."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
    ):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        logger.info(f"OpenAI provider initialized: model={model}, base_url={base_url}")

    async def summarize(self, text: str, prompt: str) -> str:
        """Send text to OpenAI and return summary. No retry per D-11."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text},
                ],
            )
            result = response.choices[0].message.content
            if result is None:
                raise SummaryError("LLM returned an empty response.")
            return result
        except AuthenticationError:
            raise SummaryError(
                "Invalid API key. Check your OPENAI_API_KEY configuration."
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
