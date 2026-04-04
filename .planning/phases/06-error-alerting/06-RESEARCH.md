# Phase 06: Error Alerting - Research

**Researched:** 2026-04-04
**Domain:** discord.py error notification DMs, admin-restricted slash commands, config migration
**Confidence:** HIGH

## Summary

This phase adds two features to an existing discord.py 2.7.1 bot: (1) DM-based error alerts to admin users when scheduled summaries fail, and (2) a `/post-summary` admin-only slash command that posts public summaries. Both features build directly on existing codebase patterns -- the error collection list in `overnight.py`, the command registration pattern in `summary.py`, and the computed_field config pattern in `config.py`.

The technical surface is well-understood. Sending DMs uses `bot.fetch_user(user_id)` followed by `user.send(embed=...)`, with `discord.Forbidden` handling for users with DMs disabled. Admin access control uses `app_commands.check()` with a predicate that checks `interaction.user.id` against the configured admin list. The config migration from `COOLDOWN_EXEMPT_USER_IDS` to `ADMIN_USER_IDS` follows the identical `computed_field` pattern already established.

**Primary recommendation:** Structure as two waves -- (1) config migration + error alerting module, (2) `/post-summary` command. The error alerting module should be a standalone utility function, not embedded in OvernightScheduler, so it can be reused by any future error source.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Error alerts are sent as DMs to users listed in `ADMIN_USER_IDS` env var (comma-separated, same pattern as existing `COOLDOWN_EXEMPT_USER_IDS`)
- **D-02:** Remove existing red error embeds from the summary channel (overnight.py:132-146). All errors go to DMs only -- keeps the summary channel clean
- **D-03:** Error DMs use embed format with fields: error type, channel, timestamp, and traceback snippet
- **D-04:** Errors from a single scheduled run are batched into one DM (not one DM per error). Collect all errors, send a single embed with all of them
- **D-05:** All errors that prevent summary generation or delivery trigger alerts: LLM API failures (rate limits, timeouts, auth), channel/permission issues (channel not found, missing perms, guild not in cache), and scheduled task failures
- **D-06:** No severity levels -- all errors are treated equally. Single batched embed per run
- **D-07:** New `/post-summary` slash command, separate from `/summary`. Posts a public summary to the summary channel
- **D-08:** Reuse the same time range dropdown choices as `/summary` (30m, 1h, 4h, 12h, 24h)
- **D-09:** Admin picks one channel to summarize (channel parameter with same autocomplete as `/summary`)
- **D-10:** No confirmation step -- admin runs it, it posts immediately
- **D-11:** Respects `use_threads` setting -- if enabled, creates a thread in the summary channel like scheduled summaries do
- **D-12:** Exempt from summary cooldown -- admins can trigger as often as needed
- **D-13:** Command is visible to all users in the command list, but only admin user IDs can execute it. Non-admins get a vague "You don't have permission to use this command." ephemeral response
- **D-14:** Single `ADMIN_USER_IDS` env var controls both error alert DM recipients AND `/post-summary` access
- **D-15:** `ADMIN_USER_IDS` replaces `COOLDOWN_EXEMPT_USER_IDS` -- admins are automatically cooldown-exempt for `/summary` too. Remove the old env var
- **D-16:** If `ADMIN_USER_IDS` is empty or not set: error alerts are silently skipped (just logged), `/post-summary` rejects everyone. No startup warning needed

### Claude's Discretion
- Error embed color and field layout for DMs
- How to structure the batched error embed (numbered list vs fields)
- Internal error collection mechanism (list accumulation pattern already exists in overnight.py)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| discord.py | 2.7.1 | DM sending, embed building, app_commands.check | Already installed. `User.send()` for DMs, `app_commands.check()` for custom permission predicates |
| pydantic-settings | 2.x | ADMIN_USER_IDS config | Already installed. Same `computed_field` + `Field(alias=...)` pattern used for existing env vars |

### Supporting
No new dependencies needed. Everything required is already in the project.

## Architecture Patterns

### Recommended Project Structure
```
src/bot/
  config.py              # Add admin_user_ids, remove cooldown_exempt_user_ids
  client.py              # Register new post_summary command in setup_hook
  alerting.py            # NEW: error DM notification utility
  commands/
    summary.py           # Update cooldown check: cooldown_exempt -> admin_user_ids
    post_summary.py      # NEW: /post-summary command
  scheduling/
    overnight.py         # Replace red error embeds with alerting.send_error_alerts()
```

### Pattern 1: Error Alert Module (`alerting.py`)
**What:** A standalone async function that takes the bot instance and a list of error strings, builds a batched embed, and DMs it to all admin users.
**When to use:** Called at the end of `_post_summary()` in overnight.py (replacing lines 132-146), and from the task-level error handlers.
**Example:**
```python
# src/bot/alerting.py
import logging
import traceback
from datetime import datetime, timezone

import discord

logger = logging.getLogger(__name__)

ERROR_EMBED_COLOR = 0xED4245  # Discord red


async def send_error_alerts(
    bot,
    label: str,
    errors: list[str],
) -> None:
    """Send batched error DM to all configured admin users.

    If ADMIN_USER_IDS is empty, errors are logged only (D-16).
    DM failures (user has DMs disabled) are caught and logged.
    """
    admin_ids = bot.settings.admin_user_ids
    if not admin_ids:
        logger.warning(f"No admin users configured, skipping error DM for: {label}")
        return

    # Build batched embed (D-04, D-06)
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
            logger.warning(f"Cannot DM admin user {uid} (DMs disabled)")
        except Exception as e:
            logger.error(f"Failed to DM admin user {uid}: {e}")
```

### Pattern 2: Admin Check for App Commands
**What:** A custom `app_commands.check()` predicate that verifies `interaction.user.id` is in the admin list.
**When to use:** Applied as a decorator to `/post-summary`.
**Example:**
```python
from discord import app_commands

def is_admin():
    """App command check: user must be in ADMIN_USER_IDS."""
    async def predicate(interaction: discord.Interaction) -> bool:
        admin_ids = interaction.client.settings.admin_user_ids
        if interaction.user.id not in admin_ids:
            # D-13: vague denial
            raise app_commands.CheckFailure(
                "You don't have permission to use this command."
            )
        return True
    return app_commands.check(predicate)
```

### Pattern 3: Config Migration (COOLDOWN_EXEMPT -> ADMIN)
**What:** Replace `cooldown_exempt_user_ids_raw` with `admin_user_ids_raw` in Settings, using the identical pattern.
**When to use:** config.py modification.
**Example:**
```python
# Replace in config.py:
admin_user_ids_raw: str = Field(default="", alias="ADMIN_USER_IDS")

@computed_field
@property
def admin_user_ids(self) -> list[int]:
    """Parse comma-separated admin user IDs."""
    raw = self.admin_user_ids_raw
    if not raw:
        return []
    parts = [p.strip() for p in raw.split(",")]
    return [int(p) for p in parts if p]
```

### Pattern 4: /post-summary Command Structure
**What:** Mirrors `/summary` but posts publicly to the summary channel instead of ephemerally to the user.
**When to use:** New command file.
**Key differences from `/summary`:**
- Uses `is_admin()` check instead of cooldown check
- Defers ephemerally (so only admin sees "generating..." status)
- Posts result to `bot.settings.summary_channel_id` (not to interaction response)
- Respects `use_threads` setting (creates thread if enabled)
- Sends confirmation to admin via `interaction.edit_original_response()`

### Anti-Patterns to Avoid
- **Embedding error DM logic inside OvernightScheduler:** Makes it unreusable. Extract to a standalone module.
- **Using `guild.get_member()` instead of `bot.fetch_user()` for DMs:** `get_member()` requires the member to be cached and in the guild. `fetch_user()` is an API call that works regardless of cache state.
- **Using `default_permissions` for admin restriction:** This is a server-side hint that server admins can override. D-13 requires runtime enforcement based on exact user IDs, not Discord roles.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Embed character limits | Manual string slicing | Truncate description at 4096 with ellipsis marker | Embed description limit is 4096; embed fields have 1024 limit each. Simple truncation is sufficient for error messages |
| DM channel creation | `create_dm()` then `dm.send()` | `user.send()` directly | `User.send()` handles DM channel creation internally |
| Admin permission system | Role-based or database-backed | Simple `interaction.user.id in list` check | Per D-14, it is just a list of user IDs from env var |

## Common Pitfalls

### Pitfall 1: fetch_user() Rate Limits
**What goes wrong:** Calling `bot.fetch_user()` in a loop for many admin IDs hits Discord API rate limits.
**Why it happens:** Each `fetch_user()` is an HTTP API call, not a cache lookup.
**How to avoid:** For a small admin list (typical: 1-3 users), this is not a real concern. If the list grows, cache User objects or use `bot.get_user()` first (cache hit) with `fetch_user()` as fallback.
**Warning signs:** 429 responses in logs.

### Pitfall 2: DM Forbidden Not Caught
**What goes wrong:** Bot crashes or silently fails when an admin has DMs disabled.
**Why it happens:** `user.send()` raises `discord.Forbidden` if the user has disabled DMs from server members.
**How to avoid:** Always wrap `user.send()` in try/except for `discord.Forbidden` and `discord.NotFound`. Log the failure and continue to the next admin.
**Warning signs:** Unhandled exception in error handler (meta-error).

### Pitfall 3: CheckFailure Error Handler Missing
**What goes wrong:** Non-admins running `/post-summary` see a generic Discord error instead of the vague denial message.
**Why it happens:** `app_commands.CheckFailure` exceptions need to be handled. Without an error handler on the command tree or command itself, Discord shows a generic "The application did not respond" error.
**How to avoid:** Add an error handler on the command that catches `CheckFailure` and sends the ephemeral denial. Can be done via `@post_summary.error` decorator or via the bot's `tree.on_error`.
**Warning signs:** Users see "The application did not respond" instead of the permission denial.

### Pitfall 4: Config Migration Breaking Existing .env Files
**What goes wrong:** Users who have `COOLDOWN_EXEMPT_USER_IDS` in their `.env` file get no warning that it is no longer read.
**Why it happens:** Renaming the env var means the old one is silently ignored.
**How to avoid:** During the config migration, the old field should be removed entirely. Document in commit message that `.env` files need updating. The IDs should be moved to `ADMIN_USER_IDS`.
**Warning signs:** Cooldown exemptions stop working after update.

### Pitfall 5: Embed Timestamp Timezone
**What goes wrong:** Error embed shows wrong timestamp.
**Why it happens:** `discord.Embed(timestamp=...)` expects a timezone-aware datetime. Using `datetime.now()` (naive) will cause issues.
**How to avoid:** Always use `datetime.now(timezone.utc)` for embed timestamps. Discord renders these in the viewer's local timezone automatically.
**Warning signs:** Timestamps show as epoch or wrong time.

## Code Examples

### Error Handler for CheckFailure on /post-summary
```python
# Inside the register function, after defining the command:
@post_summary.error
async def post_summary_error(
    interaction: discord.Interaction, error: app_commands.AppCommandError
) -> None:
    if isinstance(error, app_commands.CheckFailure):
        if interaction.response.is_done():
            await interaction.followup.send(str(error), ephemeral=True)
        else:
            await interaction.response.send_message(str(error), ephemeral=True)
    else:
        logger.error(f"/post-summary error: {error}", exc_info=error)
        msg = "Something went wrong. Please try again later."
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
```

### Overnight.py Integration Point
```python
# Replace lines 132-146 in overnight.py:
# OLD:
#   if errors:
#       error_embed = discord.Embed(...)
#       await target.send(embed=error_embed)
#
# NEW:
if errors:
    from bot.alerting import send_error_alerts
    await send_error_alerts(self.bot, label, errors)
```

### Task-Level Error Handler Enhancement
```python
async def _on_overnight_error(self, error: Exception) -> None:
    logger.error(f"Overnight summary task failed: {error}", exc_info=error)
    from bot.alerting import send_error_alerts
    error_msg = f"Task-level failure: {type(error).__name__}: {error}"
    await send_error_alerts(self.bot, "Overnight Task Error", [error_msg])
```

### /post-summary Posting to Summary Channel
```python
# After summarization succeeds:
summary_channel = bot.get_channel(bot.settings.summary_channel_id)

if bot.settings.use_threads:
    from bot.delivery.threads import create_summary_thread
    from zoneinfo import ZoneInfo
    tz = ZoneInfo(bot.settings.timezone)
    now = datetime.now(tz)
    target = await create_summary_thread(summary_channel, now)
else:
    target = summary_channel

embeds = build_summary_embeds(summary_text, source_channel.name, timerange_label)
for embed in embeds:
    embed.set_footer(text=f"Requested by {interaction.user.display_name}")
    await target.send(embed=embed)

await interaction.edit_original_response(
    content=f"Summary posted to {target.mention}."
)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Error embeds in public summary channel | DM errors to admins only | This phase | Keeps summary channel clean |
| COOLDOWN_EXEMPT_USER_IDS | ADMIN_USER_IDS (broader role) | This phase | Single env var for all admin privileges |
| No manual trigger for scheduled summaries | /post-summary command | This phase | Admins can trigger on-demand public summaries |

## Project Constraints (from CLAUDE.md)

- **Discord API rate limits:** 100 messages per request, pagination needed (already handled in fetcher)
- **Embed description limit:** 4096 characters -- applies to error DM embeds too
- **Bot permissions:** Requires Read Message History, Send Messages, Use Slash Commands
- **No database:** All config via env vars, no persistent state
- **No LiteLLM, LangChain, Pycord, Nextcord, APScheduler** -- per CLAUDE.md exclusion list
- **Provider pattern:** Use existing provider protocol, not multi-provider abstractions
- **Command registration:** `register_X_command(bot)` pattern called in `setup_hook()`

## Open Questions

1. **Thread naming for /post-summary**
   - What we know: Overnight threads use "Overnight Summary -- {date}" naming
   - What's unclear: Should /post-summary threads have a different name format?
   - Recommendation: Use "Summary -- {channel_name} -- {date}" to differentiate from overnight threads

2. **Error DM embed field layout**
   - What we know: D-03 specifies fields for error type, channel, timestamp, traceback snippet. D-04 says batch into one DM.
   - What's unclear: With batching, per-error fields could hit the 25-field embed limit
   - Recommendation: Use numbered list in description (simpler, no field limit). Add a single "Run" field for the label/timestamp context.

## Sources

### Primary (HIGH confidence)
- discord.py official docs -- [FAQ: Sending DMs](https://discordpy.readthedocs.io/en/stable/faq.html)
- discord.py official docs -- [API Reference: User.send](https://discordpy.readthedocs.io/en/stable/api.html)
- discord.py official docs -- [app_commands checks](https://discordpy.readthedocs.io/en/stable/interactions/api.html)
- Existing codebase -- `overnight.py`, `summary.py`, `config.py`, `client.py`, `embeds.py`

### Secondary (MEDIUM confidence)
- [Python Discord guide on app command checks](https://www.pythondiscord.com/pages/guides/python-guides/app-commands/)
- [discord.py issue #8289 on DM Forbidden handling](https://github.com/Rapptz/discord.py/issues/8289)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all patterns established in codebase
- Architecture: HIGH -- directly mirrors existing overnight.py and summary.py patterns
- Pitfalls: HIGH -- well-documented discord.py DM edge cases, straightforward config migration

**Research date:** 2026-04-04
**Valid until:** 2026-05-04 (stable domain, discord.py 2.x API unlikely to change)
