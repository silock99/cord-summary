import logging
from datetime import datetime, timezone

import discord

logger = logging.getLogger(__name__)

ERROR_EMBED_COLOR = 0xED4245


async def send_error_alerts(bot, label: str, errors: list[str]) -> None:
    """Send batched error details as DMs to all configured admin users.

    If no admin users are configured, logs a warning and returns.
    Errors in DM delivery are caught per-user so one failure doesn't
    block alerts to other admins.
    """
    admin_ids: list[int] = bot.settings.admin_user_ids
    if not admin_ids:
        logger.warning(
            f"No admin users configured, skipping error DM for: {label}"
        )
        return

    description = "\n".join(f"{i+1}. {e}" for i, e in enumerate(errors))
    if len(description) > 4096:
        description = description[:4080] + "\n...(truncated)"

    embed = discord.Embed(
        title=f"Summary Errors: {label}",
        description=description,
        color=ERROR_EMBED_COLOR,
        timestamp=datetime.now(timezone.utc),
    )

    for uid in admin_ids:
        try:
            user = await bot.fetch_user(uid)
            await user.send(embed=embed)
        except discord.NotFound:
            logger.warning(f"Admin user {uid} not found, skipping error DM")
        except discord.Forbidden:
            logger.warning(
                f"Cannot DM admin user {uid} (DMs disabled)"
            )
        except Exception as e:
            logger.error(f"Failed to DM admin user {uid}: {e}")
