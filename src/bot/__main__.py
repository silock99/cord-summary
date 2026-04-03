import logging
import sys

from bot.client import SummaryBot
from bot.config import Settings


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger = logging.getLogger("bot")

    try:
        settings = Settings()
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    bot = SummaryBot(settings)

    if settings.llm_provider == "anthropic":
        from bot.providers.anthropic_provider import AnthropicSummaryProvider

        bot.provider = AnthropicSummaryProvider(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
        )
    else:
        from bot.providers.openai_provider import OpenAISummaryProvider

        bot.provider = OpenAISummaryProvider(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.openai_model,
        )

    bot.run(settings.discord_token, log_handler=None)


if __name__ == "__main__":
    main()
