# Phase 1: Foundation and Pipeline - Research

**Researched:** 2026-03-27
**Domain:** Discord bot foundation, message pipeline, LLM integration
**Confidence:** HIGH

## Summary

Phase 1 is a greenfield build of a Discord bot that connects, registers slash commands, fetches channel messages with pagination, preprocesses them, and produces summaries through a pluggable AI backend. The technology stack is fully locked by CLAUDE.md: discord.py 2.7.1, OpenAI Python SDK, pydantic-settings, Python 3.12+. The user's system has Python 3.13.7 installed, which is compatible with discord.py 2.7.1 (audioop compatibility was resolved in 2.6.0+).

The core technical challenges are: (1) properly configuring Discord privileged intents for message content access, (2) implementing async pagination for message history fetching, (3) designing a clean provider-agnostic LLM interface, and (4) implementing time-based chunking with token estimation for large message sets. All decisions from CONTEXT.md are clear and actionable -- no ambiguity remains.

**Primary recommendation:** Use a subclassed `commands.Bot` with `setup_hook` for command syncing, `channel.history()` async iterator for pagination, a `Protocol`-based LLM provider interface with OpenAI as the concrete implementation, and simple character-ratio token estimation (not tiktoken) to keep the interface provider-agnostic.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** OpenAI SDK as the first concrete provider implementation. The pluggable interface should be provider-agnostic (ABC/Protocol), with OpenAI as the shipped implementation.
- **D-02:** Default model is `gpt-4o-mini` -- cheap, fast, sufficient for summarization. Configurable via env var.
- **D-03:** Support custom base URL via `OPENAI_BASE_URL` env var so users can point at Ollama, Azure OpenAI, or any OpenAI-compatible endpoint with zero code changes.
- **D-04:** Strip messages to plain text before sending to LLM. Convert @mentions to display names, remove embeds and attachments (replace with nothing or `[attachment]` marker), remove reactions.
- **D-05:** Filter out all bot messages and Discord system messages (joins, boosts, pins) before summarization. Only human conversation gets summarized.
- **D-06:** Preserve link URLs inline in message text -- people discuss linked content, so the LLM needs to see what was referenced. Do NOT fetch linked content.
- **D-07:** Represent message authors by their server display name: `"Alice: I think we should..."` format.
- **D-08:** Split large message sets into time-based windows (e.g., 1-hour chunks). Natural conversation boundaries.
- **D-09:** Two-pass summarization: summarize each time-window chunk independently, then pass all chunk summaries to a final LLM call that produces one unified summary.
- **D-10:** LLM errors (timeout, rate limit, bad API key) are shown as ephemeral Discord messages -- only visible to the user who triggered the command. No channel spam.
- **D-11:** No auto-retry on LLM failures. Fail immediately and show the error. User can re-run the command manually.

### Claude's Discretion
- Project structure and module organization
- Provider interface design (ABC vs Protocol)
- Specific token estimation approach for determining when time windows are needed
- Logging strategy and log levels

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INFRA-01 | Bot connects to Discord with proper intents (including Message Content) | Intents setup pattern documented; Message Content is a privileged intent requiring portal toggle + code flag |
| INFRA-02 | Configuration via environment variables (bot token, channel IDs, timezone, LLM API key) | pydantic-settings 2.13.1 with `.env` file support; type-safe validation at startup |
| INFRA-03 | Slash commands are registered and synced on bot startup | `setup_hook` + `CommandTree.sync()` pattern documented; guild-specific sync for dev, global for prod |
| PIPE-01 | Bot fetches messages with pagination to handle channels with 100+ messages | `channel.history(limit=N, after=datetime)` async iterator handles pagination automatically |
| PIPE-02 | Bot filters out bot messages and system messages before summarizing | `Message.author.bot` flag + `Message.type` enum for system message filtering |
| PIPE-04 | Large message sets are chunked to fit within LLM context window limits | Time-based windowing (D-08) with character-ratio token estimation; two-pass summarization (D-09) |
| AI-01 | Summarization uses a pluggable provider interface (abstract backend) | Protocol-based interface recommended; minimal surface area (single `summarize` method) |
| AI-02 | At least one concrete LLM provider implementation is included | OpenAI `AsyncOpenAI` with `gpt-4o-mini` default; supports custom base_url for Ollama/Azure |
| AI-03 | Bot handles LLM errors gracefully (timeout, rate limit, API errors) | OpenAI SDK raises typed exceptions (`APIError`, `RateLimitError`, `APITimeoutError`); catch and surface as ephemeral messages |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Package manager:** uv (not pip+venv) -- NOTE: uv is not currently installed on the system; must be installed first
- **Discord library:** discord.py 2.7.1 only (not Pycord, Nextcord, interactions.py)
- **LLM integration:** OpenAI Python SDK for provider client; own ABC/Protocol for abstraction (NOT LiteLLM, NOT LangChain)
- **Scheduling:** discord.ext.tasks only (NOT APScheduler, NOT Celery) -- not needed in Phase 1 but sets context
- **Config:** pydantic-settings 2.x (NOT python-dotenv alone)
- **No database:** Discord API provides history on demand
- **Linting:** ruff
- **Testing:** pytest + pytest-asyncio

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| discord.py | 2.7.1 | Discord API wrapper | Locked in CLAUDE.md. Latest stable, Python 3.13 compatible, built-in slash commands and task scheduling |
| openai | 2.30.0 | LLM provider client | Locked in CLAUDE.md. AsyncOpenAI for async Discord bot context. Supports custom base_url for Ollama/Azure |
| pydantic-settings | 2.13.1 | Configuration management | Locked in CLAUDE.md. Type-safe env var loading with .env file support |
| pydantic | 2.x | Data models | Dependency of pydantic-settings. Use for structured message/summary models |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tiktoken | 0.12.0 | Token counting | OPTIONAL. Only if precise token counting is needed. Simple char/4 estimation may suffice for provider-agnostic design |
| aiohttp | (bundled) | HTTP client | Already a discord.py dependency. Available if needed |

### Development
| Tool | Version | Purpose |
|------|---------|---------|
| uv | latest | Package management + venv (must install first) |
| ruff | latest | Linting + formatting |
| pytest | latest | Testing |
| pytest-asyncio | latest | Async test support |

**Installation (after uv is installed):**
```bash
uv init
uv add discord.py openai pydantic-settings
uv add --dev ruff pytest pytest-asyncio
```

## Architecture Patterns

### Recommended Project Structure
```
src/
  bot/
    __init__.py
    __main__.py          # Entry point: create bot, run
    client.py            # Bot subclass with setup_hook
    config.py            # pydantic-settings Settings class
    pipeline/
      __init__.py
      fetcher.py         # Message fetching with pagination
      preprocessor.py    # Message cleaning, filtering, formatting
      chunker.py         # Time-based windowing + token estimation
    providers/
      __init__.py
      base.py            # Provider Protocol/ABC
      openai_provider.py # OpenAI implementation
    summarizer.py        # Orchestrates pipeline: fetch -> preprocess -> chunk -> summarize
```

### Pattern 1: Bot Subclass with setup_hook
**What:** Subclass `commands.Bot` and override `setup_hook` to sync commands before the bot connects to the gateway.
**When to use:** Always -- this is the standard discord.py 2.x pattern for slash command registration.
**Example:**
```python
import discord
from discord import app_commands
from discord.ext import commands

class SummaryBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True  # Privileged intent -- must enable in portal too
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # For development: sync to a specific guild (instant)
        # For production: await self.tree.sync() (takes up to 1 hour to propagate)
        guild = discord.Object(id=self.guild_id)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
```

### Pattern 2: Async Message History Iteration
**What:** Use `channel.history()` async iterator which handles pagination internally (100 messages per API request).
**When to use:** Fetching messages for summarization.
**Example:**
```python
from datetime import datetime, timezone

async def fetch_messages(
    channel: discord.TextChannel,
    after: datetime,
    before: datetime | None = None,
) -> list[discord.Message]:
    messages = []
    async for message in channel.history(
        limit=None,  # No limit -- fetch all in range
        after=after,
        before=before,
        oldest_first=True,
    ):
        messages.append(message)
    return messages
```

### Pattern 3: Provider Protocol
**What:** Define a minimal async Protocol for LLM providers. Concrete implementations wrap specific SDKs.
**When to use:** AI-01 requires pluggable provider interface.
**Example:**
```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class SummaryProvider(Protocol):
    async def summarize(self, text: str, prompt: str) -> str:
        """Send text to LLM and return summary."""
        ...

    async def close(self) -> None:
        """Clean up resources."""
        ...
```

### Pattern 4: pydantic-settings Configuration
**What:** Single Settings class that loads from env vars and .env file with type validation.
**When to use:** INFRA-02 configuration requirement.
**Example:**
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Discord
    discord_token: str
    guild_id: int
    summary_channel_id: int

    # LLM
    openai_api_key: str
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"

    # Bot behavior
    timezone: str = "America/New_York"
    max_context_tokens: int = 120_000  # Conservative limit for gpt-4o-mini (128k context)
```

### Pattern 5: Two-Pass Summarization with Time Windows
**What:** Split messages into time-based chunks, summarize each independently, then produce a final unified summary from all chunk summaries.
**When to use:** PIPE-04 and D-08/D-09 -- when message volume exceeds a single LLM context window.
**Example:**
```python
from datetime import timedelta

def chunk_by_time_window(
    messages: list[ProcessedMessage],
    window: timedelta = timedelta(hours=1),
) -> list[list[ProcessedMessage]]:
    """Split messages into time-based windows."""
    if not messages:
        return []
    chunks = []
    current_chunk = [messages[0]]
    window_start = messages[0].timestamp

    for msg in messages[1:]:
        if msg.timestamp - window_start >= window:
            chunks.append(current_chunk)
            current_chunk = [msg]
            window_start = msg.timestamp
        else:
            current_chunk.append(msg)

    if current_chunk:
        chunks.append(current_chunk)
    return chunks
```

### Anti-Patterns to Avoid
- **Global sync in on_ready:** `on_ready` can fire multiple times (reconnections). Sync commands in `setup_hook` which fires exactly once.
- **Blocking calls in async context:** Never use `openai.OpenAI` (sync client) in a discord.py bot. Always use `AsyncOpenAI`.
- **Fetching all messages then filtering:** Filter during iteration or immediately after. Don't hold thousands of unneeded messages in memory.
- **Hardcoded token limits:** Make `max_context_tokens` configurable -- different models and providers have different limits.
- **Creating new AsyncOpenAI per request:** Create one client instance at startup and reuse it. The SDK manages connection pools internally.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Discord message pagination | Manual offset/cursor tracking | `channel.history()` async iterator | discord.py handles the 100-per-request API limit internally, including rate limit backoff |
| Environment configuration | `os.getenv()` with manual parsing | pydantic-settings `BaseSettings` | Type validation, .env file support, missing key detection at startup |
| Slash command registration | Manual HTTP calls to Discord API | `@app_commands.command()` + `CommandTree.sync()` | discord.py handles the entire registration lifecycle |
| OpenAI API interaction | Raw HTTP with aiohttp | `AsyncOpenAI` client | Handles retries, auth, streaming, error typing |
| Timezone handling | Manual UTC offset math | `zoneinfo.ZoneInfo` (stdlib) | IANA timezone database, DST-aware, no third-party dependency |

**Key insight:** discord.py and the OpenAI SDK handle the most complex parts (pagination, rate limiting, auth, connection management). The custom code should focus on the pipeline logic: preprocessing messages and orchestrating the summarization flow.

## Common Pitfalls

### Pitfall 1: Message Content Intent Not Enabled
**What goes wrong:** Bot connects successfully but `message.content` is empty string for all messages.
**Why it happens:** Message Content is a privileged intent. Must be enabled in BOTH the Discord Developer Portal AND in code (`intents.message_content = True`).
**How to avoid:** Enable in portal first, then set in code. Add a startup check that fetches one message and verifies content is non-empty.
**Warning signs:** Empty summaries, messages appearing to have no text.

### Pitfall 2: Command Sync Takes Up to 1 Hour for Global Commands
**What goes wrong:** Bot starts, no slash commands appear in Discord.
**Why it happens:** Global command sync propagates slowly (up to 1 hour). Guild-specific sync is instant.
**How to avoid:** During development, use guild-specific sync with `copy_global_to(guild=...)`. For production, sync globally but understand the delay.
**Warning signs:** Commands work in dev (guild sync) but not in prod (global sync) -- just wait.

### Pitfall 3: Rate Limits on Large History Fetches
**What goes wrong:** Bot gets temporarily rate-limited when fetching thousands of messages.
**Why it happens:** Discord API returns 100 messages per request. 3000 messages = 30 API calls, subject to rate limiting.
**How to avoid:** discord.py handles rate limits automatically (sleeps and retries). But set reasonable limits -- a time-based `after` parameter prevents unbounded fetches.
**Warning signs:** Slow response times when summarizing very active channels.

### Pitfall 4: OpenAI SDK Exceptions in Async Context
**What goes wrong:** Unhandled exception crashes the bot or produces cryptic error.
**Why it happens:** The OpenAI SDK raises specific exception types (`openai.APIError`, `openai.RateLimitError`, `openai.APITimeoutError`, `openai.AuthenticationError`). Not catching these properly leads to unhandled errors.
**How to avoid:** Catch `openai.APIError` as the base class for all API errors. Map to user-friendly ephemeral messages per D-10.
**Warning signs:** Bot becomes unresponsive after an LLM API failure.

### Pitfall 5: Token Estimation Inaccuracy
**What goes wrong:** Chunks are too large and the LLM call fails with context length exceeded.
**Why it happens:** Simple character/4 estimation is approximate. Non-English text, code, and URLs tokenize differently.
**How to avoid:** Use a conservative multiplier (e.g., chars/3 instead of chars/4) to leave safety margin. Or use tiktoken for OpenAI-specific precision. Keep max_context_tokens well below the model's actual limit (e.g., 120k for a 128k model).
**Warning signs:** `context_length_exceeded` errors from the LLM API.

### Pitfall 6: Mention Resolution Without Guild Cache
**What goes wrong:** `@mentions` show as raw IDs (`<@123456>`) instead of display names.
**Why it happens:** The bot needs guild member cache to resolve user IDs to display names. With large servers and without the Members intent, the cache may be incomplete.
**How to avoid:** For this single-server bot, enable `Intents.members` (another privileged intent) OR resolve mentions by fetching the member when a raw mention is encountered. Since D-04 requires resolving mentions to display names, the Members intent is the cleaner approach.
**Warning signs:** Raw `<@12345>` strings appearing in LLM input.

## Code Examples

### Message Preprocessing (D-04, D-05, D-06, D-07)
```python
import re
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ProcessedMessage:
    author: str
    content: str
    timestamp: datetime

def preprocess_message(message: discord.Message, guild: discord.Guild) -> ProcessedMessage | None:
    """Convert a Discord message to clean text for summarization."""
    # D-05: Filter bot and system messages
    if message.author.bot:
        return None
    if message.type != discord.MessageType.default and message.type != discord.MessageType.reply:
        return None

    content = message.content

    # D-04: Resolve @mentions to display names
    for mention in message.mentions:
        member = guild.get_member(mention.id)
        display = member.display_name if member else mention.name
        content = content.replace(f"<@{mention.id}>", f"@{display}")
        content = content.replace(f"<@!{mention.id}>", f"@{display}")

    # D-04: Resolve channel mentions
    for channel_mention in message.channel_mentions:
        content = content.replace(f"<#{channel_mention.id}>", f"#{channel_mention.name}")

    # D-04: Resolve role mentions
    for role in message.role_mentions:
        content = content.replace(f"<@&{role.id}>", f"@{role.name}")

    # D-04: Replace attachment references
    if message.attachments:
        content += " [attachment]" if content else "[attachment]"

    # D-06: Links are preserved naturally (they're already in content)
    # D-04: Remove custom emoji markup, keep the name
    content = re.sub(r"<a?:(\w+):\d+>", r":\1:", content)

    # Skip empty messages after processing
    content = content.strip()
    if not content:
        return None

    # D-07: Author display name format
    return ProcessedMessage(
        author=message.author.display_name,
        content=content,
        timestamp=message.created_at,
    )
```

### OpenAI Provider Implementation
```python
from openai import AsyncOpenAI, APIError, APITimeoutError, RateLimitError, AuthenticationError

class OpenAISummaryProvider:
    def __init__(self, api_key: str, base_url: str, model: str):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    async def summarize(self, text: str, prompt: str) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text},
            ],
        )
        return response.choices[0].message.content

    async def close(self) -> None:
        await self.client.close()
```

### Error Handling Pattern (D-10, D-11, AI-03)
```python
from openai import APIError, APITimeoutError, RateLimitError, AuthenticationError

async def safe_summarize(provider, text: str, prompt: str) -> str:
    """Call provider with error mapping. No retry per D-11."""
    try:
        return await provider.summarize(text, prompt)
    except AuthenticationError:
        raise SummaryError("Invalid API key. Check your OPENAI_API_KEY configuration.")
    except RateLimitError:
        raise SummaryError("LLM rate limit exceeded. Please try again in a moment.")
    except APITimeoutError:
        raise SummaryError("LLM request timed out. Please try again.")
    except APIError as e:
        raise SummaryError(f"LLM API error: {e.message}")
```

### Token Estimation (Provider-Agnostic)
```python
def estimate_tokens(text: str, chars_per_token: float = 3.5) -> int:
    """Estimate token count using conservative character ratio.

    Uses 3.5 chars/token (more conservative than the typical 4.0)
    to provide safety margin across different tokenizers.
    """
    return int(len(text) / chars_per_token)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `on_ready` for command sync | `setup_hook` for command sync | discord.py 2.0+ | `setup_hook` fires once; `on_ready` can fire multiple times on reconnect |
| `message.content` always available | Message Content privileged intent required | September 2022 | Must enable in portal AND code or content is empty |
| `asyncio.get_event_loop()` | `asyncio.run()` or let discord.py manage loop | Python 3.10+ | Simpler entry point, no manual loop management |
| `openai.ChatCompletion.create()` | `client.chat.completions.create()` | openai SDK 1.0+ | New resource-based API; old module-level functions removed |
| pip + requirements.txt | uv + pyproject.toml | 2024-2025 | Faster, lockfile support, venv management built-in |

## Open Questions

1. **Members Intent for Mention Resolution**
   - What we know: D-04 requires resolving @mentions to display names. This needs the guild member cache.
   - What's unclear: Whether `Intents.members` (another privileged intent) is needed, or if the default cache from message events is sufficient for a single-server bot.
   - Recommendation: Enable `Intents.members` -- it's a privileged intent but trivial for an unverified single-server bot. Keeps mention resolution simple.

2. **tiktoken vs Character Estimation**
   - What we know: tiktoken gives exact counts for OpenAI models. Character/3.5 ratio is a rough approximation.
   - What's unclear: Whether the approximation is good enough or will cause context window overflows in practice.
   - Recommendation: Start with character estimation (provider-agnostic, zero dependency). The conservative ratio of 3.5 chars/token plus a max_context_tokens set at ~80% of model limit provides sufficient margin. tiktoken can be added later if needed.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Runtime | Yes | 3.13.7 | -- |
| uv | Package management (CLAUDE.md) | No | -- | pip works but CLAUDE.md specifies uv; install via `pip install uv` or `powershell -c "irm https://astral.sh/uv/install.ps1 \| iex"` |
| pip | Fallback package manager | Yes | 25.2 | -- |
| Discord Bot Token | INFRA-01 | Unknown | -- | User must create bot in Discord Developer Portal and provide token |
| OpenAI API Key | AI-02 | Unknown | -- | User must provide; or use Ollama with custom base_url |

**Missing dependencies with no fallback:**
- Discord Bot Token -- user must provide via `.env` file
- OpenAI API Key (or compatible endpoint) -- user must provide via `.env` file

**Missing dependencies with fallback:**
- uv -- install via `pip install uv` or the official installer script. CLAUDE.md mandates uv, so this should be an early setup step.

## Sources

### Primary (HIGH confidence)
- [discord.py PyPI](https://pypi.org/project/discord.py/) -- verified v2.7.1 latest, Python 3.13 compatible
- [openai PyPI](https://pypi.org/project/openai/) -- verified v2.30.0 latest
- [pydantic-settings PyPI](https://pypi.org/project/pydantic-settings/) -- verified v2.13.1 latest
- [tiktoken PyPI](https://pypi.org/project/tiktoken/) -- verified v0.12.0 latest
- [discord.py slash command patterns](https://gist.github.com/AbstractUmbra/a9c188797ae194e592efe05fa129c57f) -- setup_hook and sync patterns
- [OpenAI cookbook: token counting](https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb) -- tiktoken usage and encoding mapping
- [Pydantic Settings docs](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) -- v2 .env file configuration

### Secondary (MEDIUM confidence)
- [discord.py intents primer](https://discordpy.readthedocs.io/en/latest/intents.html) -- privileged intent setup (blocked by Cloudflare, verified via search results)
- [discord.py audioop Python 3.13 fix](https://github.com/Rapptz/discord.py/discussions/10031) -- confirmed compatibility
- [OpenAI Python SDK GitHub](https://github.com/openai/openai-python) -- AsyncOpenAI patterns

### Tertiary (LOW confidence)
- Token estimation heuristic (chars/4 rule of thumb) -- widely cited but approximate; recommend conservative 3.5 ratio

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all versions verified against PyPI, compatibility confirmed
- Architecture: HIGH -- patterns drawn from official discord.py examples and standard Python async patterns
- Pitfalls: HIGH -- based on documented discord.py issues (privileged intents, sync timing) and known OpenAI SDK error types

**Research date:** 2026-03-27
**Valid until:** 2026-04-27 (stable ecosystem, no major releases expected)
