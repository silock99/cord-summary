# Phase 2: On-Demand Summarization - Research

**Researched:** 2026-03-27
**Domain:** discord.py slash commands, deferred interactions, embed formatting
**Confidence:** HIGH

## Summary

This phase wires the existing summarization pipeline (built in Phase 1) into a `/summary` slash command. The core technical challenges are: (1) registering a slash command with preset time-range choices and an optional channel parameter, (2) deferring the response to avoid Discord's 3-second interaction timeout, (3) formatting LLM output into Discord embeds with proper splitting when content exceeds limits, and (4) adding channel allowlist validation via config.

The existing code is well-structured for this. `summarize_channel()` already takes channel, guild, provider, and time range parameters that map directly to what the slash command needs. The `SummaryBot.setup_hook()` already syncs commands. The main new code is: the command handler itself, embed formatting/splitting logic, config additions for `ALLOWED_CHANNEL_IDS` and `DEFAULT_SUMMARY_HOURS`, and an updated system prompt that drops action items.

**Primary recommendation:** Register the `/summary` command on `bot.tree`, defer ephemeral immediately, call `summarize_channel()`, format result into embeds, and send via `interaction.edit_original_response` (first embed) plus `interaction.followup.send` for overflow.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Default time range is 4 hours when user doesn't specify one
- **D-02:** Time range presented as preset choices in a dropdown: 30 min, 1 hour, 4 hours, 12 hours, 24 hours
- **D-03:** Summary results are ephemeral -- only visible to the user who triggered the command. No public posting to a #summaries channel for on-demand summaries (that's Phase 3 scheduled posting only)
- **D-04:** Defer the slash command immediately with an ephemeral "Generating summary..." message, then follow up with the ephemeral summary embed once ready
- **D-05:** Summaries use bold topic headers with bullet points underneath (topic-grouped). No action items or decisions section -- just topic summaries
- **D-06:** When summary exceeds Discord's 4096-char embed description limit, split into multiple embeds in the same response, breaking at topic boundaries
- **D-07:** The LLM system prompt should instruct for topic-grouped bullet points without action items extraction (update SUMMARY_SYSTEM_PROMPT from Phase 1)
- **D-08:** Admin configures allowed channels via `ALLOWED_CHANNEL_IDS` env var (comma-separated channel IDs). Only these channels can be summarized
- **D-09:** Default behavior: summarize the current channel (if on the allowlist). Optional `channel` parameter to pick a different allowed channel
- **D-10:** If user runs /summary in a non-allowed channel (and doesn't specify a channel parameter), show ephemeral error listing the available channels: "This channel isn't enabled for summaries. Available channels: #general, #dev"
- **D-11:** Fewer than 5 human messages (after bot/system filtering) in the time range counts as "no significant activity"
- **D-12:** When below threshold, show a simple ephemeral message: "No significant activity in #channel-name in the last X hours." -- no LLM call, no message quoting
- **D-13:** SUM-04 (action items extraction) is removed from this phase -- summaries are topic-grouped bullets only
- **D-14:** OUT-01 (post to dedicated summary channel) moves to Phase 3 -- on-demand summaries are ephemeral only

### Claude's Discretion
- Embed color, footer text, and metadata styling
- Exact wording of the "generating..." deferred message
- How to split long summaries at topic boundaries (algorithm for multi-embed splitting)
- Whether the channel dropdown in /summary shows all allowed channels or only ones the user can see

### Deferred Ideas (OUT OF SCOPE)
- OUT-01 (dedicated summary channel posting) -- deferred to Phase 3 for scheduled summaries
- SUM-04 (action items extraction) -- removed from v1 scope per user decision
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SUM-01 | User can run `/summary` to get a bullet-point summary | Slash command registration via `@bot.tree.command()`, defer + followup pattern |
| SUM-02 | User can specify a time range via slash command option | `app_commands.choices` with `app_commands.Choice` for preset time ranges |
| SUM-03 | Summaries are grouped by discussion topic with clear headers | Updated `SUMMARY_SYSTEM_PROMPT` instructing topic-grouped format |
| SUM-05 | Empty/low-activity periods return "no significant activity" | Quiet threshold check (< 5 messages) before LLM call |
| PIPE-03 | User can choose which channel to summarize | Optional `discord.TextChannel` parameter with allowlist validation |
| OUT-02 | Summaries use Discord embed formatting with length handling | Embed construction + topic-boundary splitting algorithm |
</phase_requirements>

## Standard Stack

### Core (already installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| discord.py | 2.7.1 | Slash commands, embeds, interactions | Already installed. `app_commands` module provides all needed slash command infrastructure |
| openai | 1.x+ | LLM calls | Already installed. Used by `OpenAISummaryProvider` |
| pydantic-settings | 2.x | Config validation | Already installed. Extend `Settings` with new fields |

### No New Dependencies
This phase requires zero new packages. All functionality (slash commands, choices, embeds, deferred responses) is built into discord.py 2.7.1.

## Architecture Patterns

### Recommended Project Structure
```
src/bot/
  __main__.py          # Entry point (exists)
  client.py            # SummaryBot class (exists -- add provider init)
  config.py            # Settings (exists -- add ALLOWED_CHANNEL_IDS)
  models.py            # Data models (exists)
  summarizer.py        # Pipeline orchestrator (exists -- update system prompt)
  commands/
    __init__.py        # Package init
    summary.py         # /summary slash command handler (NEW)
  formatting/
    __init__.py        # Package init
    embeds.py          # Embed building + splitting logic (NEW)
  pipeline/            # (exists from Phase 1)
  providers/           # (exists from Phase 1)
```

### Pattern 1: Slash Command with Deferred Ephemeral Response
**What:** Register command on bot tree, defer immediately as ephemeral, do work, edit original response.
**When to use:** Any command that may take > 3 seconds (LLM calls always exceed this).
**Example:**
```python
# Source: discord.py masterclass guide + official docs
import discord
from discord import app_commands

@bot.tree.command(name="summary", description="Summarize recent channel activity")
@app_commands.describe(
    timerange="Time period to summarize",
    channel="Channel to summarize (defaults to current)"
)
@app_commands.choices(timerange=[
    app_commands.Choice(name="Last 30 minutes", value=30),
    app_commands.Choice(name="Last 1 hour", value=60),
    app_commands.Choice(name="Last 4 hours", value=240),
    app_commands.Choice(name="Last 12 hours", value=720),
    app_commands.Choice(name="Last 24 hours", value=1440),
])
async def summary(
    interaction: discord.Interaction,
    timerange: int = 240,  # Default 4 hours per D-01
    channel: discord.TextChannel | None = None,
):
    await interaction.response.defer(ephemeral=True)  # D-03, D-04

    # ... validation, summarization, embed building ...

    await interaction.edit_original_response(embed=first_embed)
    # Additional embeds via followup if needed
    for extra_embed in overflow_embeds:
        await interaction.followup.send(embed=extra_embed, ephemeral=True)
```

### Pattern 2: Command Registration via Cog-like Module
**What:** Define commands in a separate module, import and register in `setup_hook`.
**When to use:** When commands are complex enough to warrant their own file.
**Example:**
```python
# src/bot/commands/summary.py
import discord
from discord import app_commands

def register_summary_command(bot):
    @bot.tree.command(name="summary", description="...")
    async def summary(interaction: discord.Interaction, ...):
        ...

# src/bot/client.py
from bot.commands.summary import register_summary_command

class SummaryBot(commands.Bot):
    async def setup_hook(self) -> None:
        register_summary_command(self)
        # ... existing sync code ...
```

### Pattern 3: Channel Allowlist Validation
**What:** Check channel against configured allowlist before proceeding.
**When to use:** Every `/summary` invocation.
**Example:**
```python
# Determine target channel
target = channel or interaction.channel

# Validate against allowlist
if target.id not in bot.settings.allowed_channel_ids:
    allowed_mentions = ", ".join(
        f"<#{cid}>" for cid in bot.settings.allowed_channel_ids
    )
    await interaction.edit_original_response(
        content=f"This channel isn't enabled for summaries. "
                f"Available channels: {allowed_mentions}"
    )
    return
```

### Pattern 4: Quiet Channel Short-Circuit
**What:** Check message count before calling LLM to avoid wasting API calls.
**When to use:** After fetching and preprocessing messages, before summarization.
**Example:**
```python
QUIET_THRESHOLD = 5  # D-11

if len(processed_messages) < QUIET_THRESHOLD:
    await interaction.edit_original_response(
        content=f"No significant activity in {target.mention} "
                f"in the last {timerange_display}."
    )
    return
```

### Anti-Patterns to Avoid
- **Sending initial response then followup:** Do NOT use `interaction.response.send_message()` then `followup.send()`. Use `defer()` + `edit_original_response()` instead, since the summary always takes > 3 seconds.
- **Multiple embeds in one message assuming 4096 each:** The total across all embeds in a single message is capped at 6000 characters. Use separate messages (followup sends) for overflow.
- **Hardcoding time ranges:** Use `app_commands.choices` so Discord renders them as a dropdown, not free-text input.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Slash command registration | Manual HTTP calls to Discord API | `@bot.tree.command()` + `app_commands` decorators | discord.py handles parameter types, choices, descriptions, guild sync |
| Deferred response pattern | Manual webhook management | `interaction.response.defer()` + `interaction.edit_original_response()` | discord.py manages the interaction token lifecycle |
| Embed construction | Raw dict building | `discord.Embed()` class | Handles color, fields, footer, timestamp, character validation |
| Time range choices | Free-text parsing ("4 hours", "4h", etc.) | `app_commands.choices` with integer values (minutes) | Discord renders as dropdown, no parsing errors possible |
| Channel type filtering | Manual channel type checks | `discord.TextChannel` type hint on parameter | Discord only shows text channels in the picker |

## Common Pitfalls

### Pitfall 1: 3-Second Interaction Timeout
**What goes wrong:** Bot tries to summarize before responding to the interaction, Discord marks it as "interaction failed."
**Why it happens:** LLM calls take 5-30 seconds. Discord requires a response within 3 seconds.
**How to avoid:** Always `await interaction.response.defer(ephemeral=True)` as the very first line in the command handler. Do ALL work after deferring.
**Warning signs:** "This interaction failed" errors in Discord.

### Pitfall 2: 6000 Character Total Embed Limit Per Message
**What goes wrong:** Sending multiple embeds in one message, each with up to 4096 chars, hits the 6000 char combined limit.
**Why it happens:** Discord's limit is 6000 chars total across ALL embeds in a single message, not 4096 per embed.
**How to avoid:** First embed goes via `edit_original_response`. Additional embeds go via separate `followup.send` calls. Each followup message can have its own 6000-char budget.
**Warning signs:** HTTP 400 errors when sending multiple embeds.

### Pitfall 3: Ephemeral Followup Inheritance
**What goes wrong:** Followup messages after a deferred ephemeral response are visible to everyone.
**Why it happens:** Only the first followup inherits the ephemeral flag from defer. Subsequent followups default to non-ephemeral.
**How to avoid:** Always pass `ephemeral=True` explicitly on every `followup.send()` call after the first.
**Warning signs:** Summary overflow embeds visible to the whole channel.

### Pitfall 4: Default Parameter Not Triggering Choice Validation
**What goes wrong:** Optional choice parameter with a default value bypasses Discord's choice validation when omitted.
**Why it happens:** When a user omits the parameter, Discord sends nothing and the Python default kicks in. This is fine as long as the default is a valid value.
**How to avoid:** Set the default to 240 (4 hours) which matches one of the choices. Document this mapping clearly.
**Warning signs:** None -- this works correctly if default is set right.

### Pitfall 5: Embed Description vs Content Confusion
**What goes wrong:** Summary text placed in embed `content` instead of `description`, or vice versa.
**Why it happens:** `interaction.edit_original_response(content=...)` sets plain text. `embed=discord.Embed(description=...)` sets rich embed text.
**How to avoid:** Use `content=` only for simple status messages (errors, "no activity"). Use `embed=` for formatted summaries.
**Warning signs:** Summaries appear as plain text without formatting.

### Pitfall 6: Missing Provider Initialization
**What goes wrong:** `SummaryBot` has no provider instance, command handler can't call `summarize_channel()`.
**Why it happens:** Phase 1 built the provider and pipeline but `__main__.py` doesn't instantiate a provider and attach it to the bot.
**How to avoid:** Instantiate `OpenAISummaryProvider` from settings in `__main__.py` or `SummaryBot.__init__`, store as `self.provider`.
**Warning signs:** AttributeError at runtime.

## Code Examples

### Embed Building with Topic-Boundary Splitting
```python
# Source: Discord API docs (embed limits) + discord.py Embed API
import discord

EMBED_DESC_LIMIT = 4096
EMBED_COLOR = 0x5865F2  # Discord blurple

def build_summary_embeds(
    summary_text: str,
    channel_name: str,
    timerange_label: str,
) -> list[discord.Embed]:
    """Split summary into multiple embeds at topic boundaries.

    Topics are delimited by bold headers (lines starting with **).
    Each embed stays under 4096 chars.
    """
    # Split into topic sections (each starts with a bold header)
    sections = _split_into_topics(summary_text)

    embeds: list[discord.Embed] = []
    current_text = ""

    for section in sections:
        # If adding this section would exceed limit, finalize current embed
        if current_text and len(current_text) + len(section) + 2 > EMBED_DESC_LIMIT:
            embeds.append(_make_embed(current_text, channel_name, timerange_label, len(embeds)))
            current_text = ""

        # If a single section exceeds limit, truncate it
        if len(section) > EMBED_DESC_LIMIT:
            section = section[:EMBED_DESC_LIMIT - 20] + "\n*(...truncated)*"

        current_text += ("\n\n" if current_text else "") + section

    # Don't forget the last chunk
    if current_text:
        embeds.append(_make_embed(current_text, channel_name, timerange_label, len(embeds)))

    return embeds


def _split_into_topics(text: str) -> list[str]:
    """Split text at bold topic headers (lines starting with **)."""
    import re
    # Split before lines that start with ** (bold markdown)
    parts = re.split(r'(?=\n\*\*)', text)
    return [p.strip() for p in parts if p.strip()]


def _make_embed(
    description: str,
    channel_name: str,
    timerange_label: str,
    index: int,
) -> discord.Embed:
    embed = discord.Embed(
        description=description,
        color=EMBED_COLOR,
    )
    if index == 0:
        embed.title = f"Summary: #{channel_name}"
    else:
        embed.title = f"Summary: #{channel_name} (continued)"
    embed.set_footer(text=f"Period: {timerange_label}")
    return embed
```

### Pydantic Settings Extension for Allowlist
```python
# Source: pydantic-settings docs
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # ... existing fields ...

    # Channel allowlist (D-08): comma-separated IDs
    allowed_channel_ids: list[int] = []  # pydantic-settings parses JSON or comma-sep

    # Default summary hours (D-01)
    default_summary_minutes: int = 240
```

**Note on `list[int]` parsing:** pydantic-settings v2 can parse `ALLOWED_CHANNEL_IDS` from env as either JSON (`[123, 456]`) or comma-separated (`123,456`) depending on configuration. The simplest approach is to accept a comma-separated string and parse it with a validator, or use `str` type and split manually in a `@field_validator`.

### Updated System Prompt (D-05, D-07, D-13)
```python
SUMMARY_SYSTEM_PROMPT = (
    "You are a Discord channel summarizer. Given a conversation log, produce a concise "
    "summary organized by discussion topic. Format each topic with a bold header "
    "(**Topic Name**) followed by bullet points underneath. "
    "Keep language clear and brief. Do not include timestamps or repeat verbatim quotes. "
    "Do not extract action items or decisions as separate sections."
)
```

### Complete Command Handler Skeleton
```python
import discord
from discord import app_commands
from datetime import datetime, timedelta, timezone

TIMERANGE_CHOICES = [
    app_commands.Choice(name="Last 30 minutes", value=30),
    app_commands.Choice(name="Last 1 hour", value=60),
    app_commands.Choice(name="Last 4 hours", value=240),
    app_commands.Choice(name="Last 12 hours", value=720),
    app_commands.Choice(name="Last 24 hours", value=1440),
]

QUIET_THRESHOLD = 5

def register_summary_command(bot):
    @bot.tree.command(name="summary", description="Summarize recent channel activity")
    @app_commands.describe(
        timerange="Time period to summarize",
        channel="Channel to summarize (defaults to current channel)"
    )
    @app_commands.choices(timerange=TIMERANGE_CHOICES)
    async def summary(
        interaction: discord.Interaction,
        timerange: int = 240,
        channel: discord.TextChannel | None = None,
    ):
        # 1. Defer immediately (D-04)
        await interaction.response.defer(ephemeral=True)

        # 2. Resolve target channel (D-09)
        target = channel or interaction.channel

        # 3. Validate allowlist (D-08, D-10)
        if target.id not in bot.settings.allowed_channel_ids:
            mentions = ", ".join(f"<#{cid}>" for cid in bot.settings.allowed_channel_ids)
            await interaction.edit_original_response(
                content=f"This channel isn't enabled for summaries. Available channels: {mentions}"
            )
            return

        # 4. Calculate time range
        now = datetime.now(timezone.utc)
        after = now - timedelta(minutes=timerange)

        # 5. Fetch + preprocess (reuse pipeline)
        # 6. Check quiet threshold (D-11, D-12)
        # 7. Summarize via provider
        # 8. Build embeds with splitting (D-06)
        # 9. Send first embed via edit_original_response
        # 10. Send overflow embeds via followup.send(ephemeral=True)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `commands.command()` text commands | `app_commands.command()` slash commands | discord.py 2.0 (2022) | Must use interaction model, not message-based |
| `ctx.send()` for responses | `interaction.response` / `interaction.followup` | discord.py 2.0 | One response per interaction, followups for additional messages |
| Free-text time parsing | `app_commands.choices` dropdown | discord.py 2.0 | Discord UI renders choices, no parsing needed |

## Open Questions

1. **pydantic-settings `list[int]` from env var parsing**
   - What we know: pydantic-settings v2 can parse JSON lists from env vars. Comma-separated parsing depends on the separator config.
   - What's unclear: Whether `ALLOWED_CHANNEL_IDS=123,456` auto-parses to `list[int]` without a custom validator.
   - Recommendation: Use a `str` field with a `@field_validator` to split on commas. Simple, explicit, no surprises. Alternatively test the native parsing during implementation and fall back to validator if needed.

2. **Choice default value behavior when parameter is optional**
   - What we know: Setting `timerange: int = 240` makes it optional with a default. Discord won't show it as required.
   - What's unclear: Whether the choices dropdown still appears when the parameter is optional.
   - Recommendation: This is standard discord.py behavior -- optional choice parameters work. The choices still show when the user clicks the option. Verify during manual testing.

## Sources

### Primary (HIGH confidence)
- discord.py masterclass guide (https://fallendeity.github.io/discord.py-masterclass/slash-commands/) - slash command patterns, choices, defer, ephemeral
- Discord API docs issue #4047 (https://github.com/discord/discord-api-docs/issues/4047) - confirmed 6000 char total embed limit per message
- Discord developer docs (https://discord.com/developers/docs/interactions/receiving-and-responding) - interaction response model
- Existing codebase (src/bot/) - Phase 1 patterns and architecture

### Secondary (MEDIUM confidence)
- discord.py discussions #8236 (https://github.com/Rapptz/discord.py/discussions/8236) - Choice parameter patterns
- Python Discord embed limits guide (https://www.pythondiscord.com/pages/guides/python-guides/discord-embed-limits/) - embed character limits

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new dependencies, all discord.py built-in
- Architecture: HIGH - clear patterns from discord.py docs and existing codebase
- Pitfalls: HIGH - well-documented Discord API limitations (timeouts, embed limits, ephemeral inheritance)

**Research date:** 2026-03-27
**Valid until:** 2026-04-27 (stable -- discord.py 2.x API is mature)
