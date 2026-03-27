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
    bot.run(settings.discord_token, log_handler=None)


if __name__ == "__main__":
    main()
