# Phase 3: Scheduling and Delivery - Research

**Researched:** 2026-03-27
**Domain:** discord.py task scheduling, thread creation, DM delivery, JSON persistence
**Confidence:** HIGH

## Summary

Phase 3 adds three capabilities to the existing bot: (1) automated overnight summaries posted at 9am daily using `discord.ext.tasks`, (2) optional DM delivery for opted-in users, and (3) optional thread-based posting toggled by environment variable. The entire stack is already decided and available -- `discord.ext.tasks` with `zoneinfo` for scheduling, `TextChannel.create_thread()` for threads, `User.send()` for DMs, and a JSON file for subscriber persistence. No new dependencies are needed.

The existing codebase provides strong reuse: `summarize_channel()` already takes `after`/`before` datetime params (maps directly to the 10pm-9am window), `build_summary_embeds()` handles embed formatting, and `Settings` already has `timezone`, `summary_channel_id`, and `allowed_channel_ids`. The primary new code is the scheduling loop, the multi-channel orchestration, the DM toggle command, and the JSON persistence layer.

**Primary recommendation:** Build the scheduled task as a Cog or standalone module that registers via `setup_hook`, iterates `allowed_channel_ids`, calls existing `summarize_channel()` per channel, and posts embeds to `summary_channel_id`. DM delivery and thread posting are layered on top of the same generated embeds.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Overnight summary covers all channels in `ALLOWED_CHANNEL_IDS` -- same allowlist used for `/summary`. No separate scheduled channel list.
- **D-02:** All overnight summaries post to `SUMMARY_CHANNEL_ID` (already in config). One central place to catch up.
- **D-03:** Channels with no significant overnight activity (below quiet threshold) are skipped silently -- no "no activity" posts.
- **D-04:** Users opt in via slash command toggle (e.g., `/summary-dm`). Self-service, no admin involvement.
- **D-05:** DM opt-in state persisted to a local JSON file -- survives bot restarts without requiring a database.
- **D-06:** DMs fire for scheduled summaries only. On-demand `/summary` remains ephemeral.
- **D-07:** DMs re-use the already-generated summary embeds -- zero additional LLM calls.
- **D-08:** Default posting mode is regular messages (not threads).
- **D-09:** Optional `USE_THREADS` env var toggle (default `false`). When enabled, creates a daily thread and posts channel summaries inside it.
- **D-10:** One embed per channel, posted sequentially in #summaries. Uses existing `build_summary_embeds()` format per channel.
- **D-11:** Channels summarized sequentially (one LLM call at a time). Speed is not a concern for a daily job.
- **D-12:** If one channel's summary fails, continue with remaining channels and include an error note. No abort, no retry.

### Claude's Discretion
- Exact slash command name and parameters for DM opt-in toggle
- JSON file location and format for DM subscriber persistence
- Thread naming convention and auto-archive duration
- Scheduling implementation details (discord.ext.tasks.loop with time parameter)
- Embed differentiation between scheduled and on-demand summaries (e.g., different footer text)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SCHED-01 | Bot automatically generates and posts an overnight summary (10pm-9am) at 9am daily | `discord.ext.tasks.loop(time=...)` with `zoneinfo.ZoneInfo` for timezone-aware scheduling; `summarize_channel()` with `after`/`before` params for the overnight window |
| SCHED-02 | Timezone is configurable via environment variable | `Settings.timezone` already exists; pass `zoneinfo.ZoneInfo(settings.timezone)` as `tzinfo` to `datetime.time` -- handles DST correctly |
| OUT-03 | User can optionally receive the summary as a DM | `User.send(embed=embed)` for DM delivery; JSON file for subscriber persistence; `discord.Forbidden` handling for users with DMs disabled |
| OUT-04 | Summaries can be posted as a thread to keep channels clean | `TextChannel.create_thread(name=..., auto_archive_duration=1440)` with `type=ChannelType.public_thread`; toggled by `USE_THREADS` env var |
</phase_requirements>

## Standard Stack

### Core (already installed -- no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| discord.ext.tasks | bundled with discord.py 2.7.1 | Daily 9am scheduling | Built-in, zero deps, `time=` parameter with `zoneinfo` tzinfo handles DST correctly |
| zoneinfo | stdlib (Python 3.12+) | Timezone-aware scheduling | Standard library, includes DST transition data unlike `astimezone()` |
| pydantic-settings | 2.x (already installed) | New config fields (`USE_THREADS`) | Already in use for `Settings` class |
| json | stdlib | DM subscriber persistence | D-05 requires JSON file, stdlib handles this |

### No new packages needed

This phase uses only existing dependencies. No `pip install` required.

## Architecture Patterns

### Recommended Project Structure

```
src/bot/
  commands/
    summary.py          # Existing /summary command
    summary_dm.py       # NEW: /summary-dm toggle command
  scheduling/
    __init__.py
    overnight.py        # NEW: Scheduled task loop + multi-channel orchestration
  delivery/
    __init__.py
    dm_manager.py       # NEW: JSON persistence + DM sending
    threads.py          # NEW: Thread creation helper
  formatting/
    embeds.py           # Existing (minor update: footer text for scheduled vs on-demand)
  config.py             # Existing (add USE_THREADS field)
  client.py             # Existing (register scheduled task + new command in setup_hook)
```

### Pattern 1: Task Loop with `before_loop` Wait

**What:** Use `@tasks.loop(time=...)` with `before_loop` to wait until bot is ready before scheduling starts.
**When to use:** Always -- the task loop must not fire before the bot is connected and has access to guilds/channels.

```python
from datetime import time
from zoneinfo import ZoneInfo

from discord.ext import tasks

# Inside a Cog or module that has access to bot
tz = ZoneInfo(bot.settings.timezone)
schedule_time = time(hour=9, minute=0, tzinfo=tz)

@tasks.loop(time=schedule_time)
async def overnight_summary():
    # ... orchestration logic
    pass

@overnight_summary.before_loop
async def before_overnight():
    await bot.wait_until_ready()
```

**Key detail:** The `time` parameter with a `zoneinfo.ZoneInfo` tzinfo handles DST transitions correctly. The library recalculates the UTC offset for each iteration using the timezone's transition data. Do NOT use `datetime.timezone(timedelta(hours=X))` or `astimezone()` -- these create fixed offsets that break across DST.

### Pattern 2: Overnight Window Calculation

**What:** Calculate the 10pm-9am overnight window relative to the 9am trigger time.
**When to use:** Every scheduled execution to determine `after` and `before` params for `summarize_channel()`.

```python
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

def get_overnight_window(tz: ZoneInfo) -> tuple[datetime, datetime]:
    """Return (start=10pm yesterday, end=9am today) in UTC."""
    now = datetime.now(tz)
    today_9am = now.replace(hour=9, minute=0, second=0, microsecond=0)
    yesterday_10pm = today_9am - timedelta(hours=11)  # 10pm previous day
    return yesterday_10pm, today_9am
```

### Pattern 3: Sequential Multi-Channel with Error Isolation (D-10, D-11, D-12)

**What:** Iterate allowed channels, summarize each, post results. If one fails, log error and continue.
**When to use:** The overnight summary orchestration loop.

```python
results: list[tuple[str, list[discord.Embed]]] = []
errors: list[str] = []

for channel_id in bot.settings.allowed_channel_ids:
    channel = bot.get_channel(channel_id)
    if channel is None:
        errors.append(f"Channel {channel_id} not found")
        continue
    try:
        summary_text = await summarize_channel(
            channel, guild, bot.provider, after, before,
            bot.settings.max_context_tokens,
        )
        # Check quiet threshold (D-03)
        # ... build embeds if not quiet
        embeds = build_summary_embeds(summary_text, channel.name, "Overnight (10pm-9am)")
        results.append((channel.name, embeds))
    except SummaryError as e:
        errors.append(f"Failed to summarize #{channel.name}: {e}")
        continue
```

### Pattern 4: DM Subscriber JSON Persistence (D-05)

**What:** Store DM opt-in user IDs in a JSON file. Load on startup, save on toggle.
**When to use:** DM subscriber management.

```python
import json
from pathlib import Path

DM_SUBSCRIBERS_PATH = Path("data/dm_subscribers.json")

def load_subscribers() -> set[int]:
    if not DM_SUBSCRIBERS_PATH.exists():
        return set()
    data = json.loads(DM_SUBSCRIBERS_PATH.read_text())
    return set(data.get("user_ids", []))

def save_subscribers(user_ids: set[int]) -> None:
    DM_SUBSCRIBERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    DM_SUBSCRIBERS_PATH.write_text(json.dumps({"user_ids": sorted(user_ids)}))
```

### Pattern 5: Thread Creation (D-08, D-09)

**What:** Create a public thread in the summaries channel for the daily summary when `USE_THREADS` is enabled.
**When to use:** Conditionally, based on `USE_THREADS` env var.

```python
import discord
from datetime import datetime

async def create_summary_thread(
    channel: discord.TextChannel,
    date_str: str,
) -> discord.Thread:
    """Create a public thread for today's overnight summary."""
    return await channel.create_thread(
        name=f"Overnight Summary -- {date_str}",
        type=discord.ChannelType.public_thread,
        auto_archive_duration=1440,  # 24 hours (auto-hide from list)
    )
```

**auto_archive_duration values:** 60 (1hr), 1440 (24hr), 4320 (3 days), 10080 (1 week). Use 1440 -- thread stays visible for a day then archives itself, keeping the channel clean.

### Pattern 6: DM Delivery with Forbidden Handling (D-06, D-07)

**What:** Send summary embeds to DM subscribers, gracefully handling users who have DMs disabled.
**When to use:** After posting to #summaries, iterate DM subscribers and send same embeds.

```python
async def send_dm_summaries(
    bot, all_embeds: list[discord.Embed], subscribers: set[int]
) -> None:
    for user_id in subscribers:
        user = bot.get_user(user_id)
        if user is None:
            try:
                user = await bot.fetch_user(user_id)
            except discord.NotFound:
                continue
        try:
            for embed in all_embeds:
                await user.send(embed=embed)
        except discord.Forbidden:
            logger.warning(f"Cannot DM user {user_id} (DMs disabled)")
        except discord.HTTPException as e:
            logger.warning(f"Failed to DM user {user_id}: {e}")
```

### Anti-Patterns to Avoid

- **Fixed UTC offset for timezone:** Using `datetime.timezone(timedelta(hours=-5))` instead of `zoneinfo.ZoneInfo("America/New_York")` breaks across DST transitions. Always use `zoneinfo`.
- **Starting task loop outside `setup_hook`/`on_ready`:** The loop fires immediately -- if the bot is not connected, channel lookups return None. Use `before_loop` with `wait_until_ready()`.
- **Retrying failed channel summaries:** D-12 explicitly says no retry. Log the error and move on.
- **Separate LLM calls for DMs:** D-07 says reuse the same embeds. Never regenerate summaries for DM delivery.
- **In-memory only subscriber storage:** D-05 requires persistence across restarts. Always write to JSON file on toggle.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Daily scheduling at specific time | Custom sleep loop with `asyncio.sleep` | `discord.ext.tasks.loop(time=...)` | Built-in reconnection, error handling, DST support with zoneinfo |
| Timezone DST handling | Manual UTC offset calculation | `zoneinfo.ZoneInfo` with `datetime.time(tzinfo=...)` | DST transition data baked in; manual offsets break twice a year |
| Thread auto-cleanup | Custom thread archival task | `auto_archive_duration=1440` parameter | Discord handles archival automatically |

## Common Pitfalls

### Pitfall 1: DST Breaks Scheduling
**What goes wrong:** Bot scheduled for 9am local fires at 8am or 10am after DST transition.
**Why it happens:** Using `datetime.timezone(timedelta(...))` or `astimezone()` creates a fixed offset with no DST transition data.
**How to avoid:** Always use `zoneinfo.ZoneInfo("Region/City")` as the `tzinfo` for `datetime.time`. The discord.py task loop recalculates offsets correctly when `zoneinfo` is used.
**Warning signs:** Bot posts summary at wrong time in spring/fall.

### Pitfall 2: Task Fires Before Bot is Ready
**What goes wrong:** The task loop iteration runs before `on_ready`, so `bot.get_channel()` returns None and nothing gets posted.
**Why it happens:** `tasks.loop` starts when `.start()` is called, which may be before the bot has populated its cache.
**How to avoid:** Use `@task.before_loop` with `await bot.wait_until_ready()`.
**Warning signs:** "Channel not found" errors in logs at startup.

### Pitfall 3: DM Forbidden Not Caught
**What goes wrong:** One user with DMs disabled causes an unhandled exception that stops DM delivery to remaining subscribers.
**Why it happens:** `user.send()` raises `discord.Forbidden` when the user has server DMs disabled or has blocked the bot.
**How to avoid:** Wrap each `user.send()` in try/except `discord.Forbidden`. Log and continue.
**Warning signs:** Some subscribers stop receiving DMs; error logs show Forbidden.

### Pitfall 4: create_thread Defaults to Private
**What goes wrong:** Thread created without `type` parameter is private, meaning some users cannot see it.
**Why it happens:** `TextChannel.create_thread()` defaults to private when no `message` is provided.
**How to avoid:** Explicitly pass `type=discord.ChannelType.public_thread`.
**Warning signs:** Users report they cannot see the summary thread.

### Pitfall 5: Quiet Channel Spam
**What goes wrong:** Bot posts "no significant activity" for every quiet channel, cluttering #summaries.
**Why it happens:** Not checking quiet threshold before posting.
**How to avoid:** D-03 says skip silently. Check message count against `quiet_threshold` before generating summary. If below threshold, skip the channel entirely with no output.
**Warning signs:** #summaries filled with "no activity" posts every morning.

### Pitfall 6: Race Condition on JSON File
**What goes wrong:** Concurrent toggle commands could read stale data and overwrite each other.
**Why it happens:** Two users toggle at the exact same moment (unlikely but possible).
**How to avoid:** Use `asyncio.Lock` around read-modify-write operations on the JSON file. Since the bot runs in a single event loop, this is sufficient.
**Warning signs:** User toggles DM on but does not receive DMs.

## Code Examples

### Scheduling: Complete Task Loop Setup

```python
# Source: discord.py ext/tasks docs + zoneinfo stdlib
from datetime import time
from zoneinfo import ZoneInfo
from discord.ext import tasks

class ScheduledSummary:
    def __init__(self, bot):
        self.bot = bot
        tz = ZoneInfo(bot.settings.timezone)
        # Create the loop with timezone-aware time
        self._task = tasks.loop(time=time(hour=9, minute=0, tzinfo=tz))(self.post_overnight_summary)
        self._task.before_loop(self._wait_ready)
        self._task.error(self._on_error)

    async def _wait_ready(self):
        await self.bot.wait_until_ready()

    async def _on_error(self, error: Exception):
        logger.error(f"Overnight summary task failed: {error}", exc_info=error)

    async def post_overnight_summary(self):
        # ... orchestration logic
        pass

    def start(self):
        self._task.start()

    def cancel(self):
        self._task.cancel()
```

### Config: New Settings Fields

```python
# Added to existing Settings class
use_threads: bool = False  # D-08, D-09: thread posting toggle
```

### Thread Creation with Date

```python
from datetime import datetime
from zoneinfo import ZoneInfo

async def post_to_thread_or_channel(channel, embeds, tz, use_threads):
    if use_threads:
        date_str = datetime.now(tz).strftime("%b %d")
        thread = await channel.create_thread(
            name=f"Overnight Summary -- {date_str}",
            type=discord.ChannelType.public_thread,
            auto_archive_duration=1440,
        )
        target = thread
    else:
        target = channel

    for embed in embeds:
        await target.send(embed=embed)
    return target
```

### DM Toggle Command

```python
@bot.tree.command(name="summary-dm", description="Toggle overnight summary DM delivery")
async def summary_dm(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    user_id = interaction.user.id
    # Toggle subscription
    if user_id in subscribers:
        subscribers.discard(user_id)
        save_subscribers(subscribers)
        await interaction.edit_original_response(
            content="You will no longer receive overnight summaries via DM."
        )
    else:
        subscribers.add(user_id)
        save_subscribers(subscribers)
        await interaction.edit_original_response(
            content="You will now receive overnight summaries via DM each morning."
        )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `astimezone()` for task scheduling | `zoneinfo.ZoneInfo` with `tasks.loop(time=...)` | Python 3.9+ / discord.py 2.0+ | Correct DST handling -- no more twice-yearly schedule drift |
| APScheduler for daily tasks | `discord.ext.tasks` built-in | discord.py 2.0 | Zero additional deps, native event loop integration |
| `create_thread(message=None)` = private | Must pass `type=ChannelType.public_thread` explicitly | discord.py 2.0+ | Default is private thread when no message anchor is provided |

## Open Questions

1. **Thread naming collision**
   - What we know: `create_thread` with a duplicate name does not error -- Discord allows duplicate thread names.
   - What's unclear: If the bot restarts mid-day and the task fires again, it could create a second thread with the same name.
   - Recommendation: The `tasks.loop` with `time=` parameter only fires once per day, and `before_loop` ensures it waits until ready. If the bot restarts after 9am, the task will not fire again until the next day. This is a non-issue for normal operation. For defensive coding, could check if a thread with today's date already exists before creating one.

2. **JSON file location**
   - What we know: D-05 requires local JSON file for subscriber persistence.
   - What's unclear: Best location relative to project root.
   - Recommendation: Use `data/dm_subscribers.json` relative to working directory. Create `data/` directory if it does not exist. Add `data/` to `.gitignore` since it contains runtime state.

## Project Constraints (from CLAUDE.md)

- **discord.py 2.7.1** is the Discord library -- no alternatives
- **discord.ext.tasks** for scheduling -- no APScheduler, no Celery
- **zoneinfo** for timezone -- no third-party timezone libraries
- **pydantic-settings** for all configuration -- type-safe, validated from `.env`
- **No database** -- JSON file for simple persistence is consistent with project constraints
- **Single server** -- no multi-guild considerations
- **Rate limits:** 100 messages per request with pagination (already handled by `fetch_messages`)
- **Embed limit:** 4096 chars (already handled by `build_summary_embeds`)
- **Register commands via** `register_X_command(bot)` pattern in `setup_hook`
- **Logging via** `logging.getLogger(__name__)`
- **uv** for package management, **ruff** for linting

## Sources

### Primary (HIGH confidence)
- discord.py GitHub source (`ext/tasks/__init__.py`) -- Loop class, time parameter handling, DST support with zoneinfo
- discord.py GitHub source (`discord/channel.py`) -- `TextChannel.create_thread()` full signature and defaults
- discord.py GitHub Discussion #9315 -- DST issue confirmed and zoneinfo solution verified
- Existing codebase (`src/bot/`) -- all reusable assets verified by direct code reading

### Secondary (MEDIUM confidence)
- discord.py GitHub Discussion #9547 -- `tasks.loop(time=...)` usage patterns
- discord.py GitHub Issue #940, #8289 -- DM Forbidden error behavior confirmed
- Discord API docs (threads) -- `auto_archive_duration` values: 60, 1440, 4320, 10080

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in use, no new dependencies
- Architecture: HIGH -- existing codebase patterns are clear; `summarize_channel()` API maps perfectly to overnight use case
- Pitfalls: HIGH -- DST issue well-documented in discord.py discussions; DM Forbidden is a known pattern; private thread default confirmed in source

**Research date:** 2026-03-27
**Valid until:** 2026-04-27 (stable -- discord.py 2.7.1 is current, no breaking changes expected)
