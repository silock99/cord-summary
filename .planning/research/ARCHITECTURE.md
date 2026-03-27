# Architecture Patterns

**Domain:** Discord bot with scheduled and on-demand LLM-powered channel summarization
**Researched:** 2026-03-27

## System Overview

```
+------------------+     +-------------------+     +------------------+
|   Discord API    |<--->|   Bot Core        |<--->|  Summarization   |
|                  |     |   (discord.py)    |     |  Service         |
| - Slash commands |     |                   |     |                  |
| - Message history|     | +---------------+ |     | +------------+  |
| - Send messages  |     | | Commands Cog  | |     | | Message    |  |
|                  |     | | (slash cmds)  | |---->| | Collector  |  |
|                  |     | +---------------+ |     | +-----+------+  |
|                  |     |                   |     |       |          |
|                  |     | +---------------+ |     | +-----v------+  |
|                  |     | | Scheduler Cog | |---->| | Formatter  |  |
|                  |     | | (daily 9am)   | |     | | (prompt    |  |
|                  |     | +---------------+ |     | |  builder)  |  |
|                  |     |                   |     | +-----+------+  |
|                  |     | +---------------+ |     |       |          |
|                  |     | | Delivery      | |<----| +-----v------+  |
|                  |     | | (embeds, DMs) | |     | | LLM Client |  |
|                  |     | +---------------+ |     | | (abstract) |  |
+------------------+     +-------------------+     | +-----+------+  |
                                                   |       |          |
                                                   | +-----v------+  |
                                                   | | OpenAI /   |  |
                                                   | | Claude /   |  |
                                                   | | Any LLM    |  |
                                                   | +------------+  |
                                                   +------------------+
```

## Component Responsibilities

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| **Bot Core** (`bot.py`) | Initialize discord.py `commands.Bot`, load cogs, manage lifecycle | Discord API, all cogs |
| **Commands Cog** (`cogs/commands.py`) | Register `/summarize` slash command, parse user input, invoke summarization service | Summarization Service, Delivery |
| **Scheduler Cog** (`cogs/scheduler.py`) | Run the 9am daily task via `discord.ext.tasks`, invoke summarization for overnight window | Summarization Service, Delivery |
| **Message Collector** (`services/collector.py`) | Fetch messages from Discord channels using `channel.history()`, handle pagination, filter by time range | Discord API (via bot instance) |
| **Formatter** (`services/formatter.py`) | Convert raw messages into a prompt suitable for the LLM, format the LLM response into Discord embeds | Message Collector output, LLM Client output |
| **LLM Client** (`services/llm/base.py` + providers) | Abstract interface for summarization -- `async def summarize(text) -> str` | External LLM APIs |
| **Delivery** (`services/delivery.py`) | Post summaries to the dedicated channel, optionally DM users, handle embed splitting for the 4096-char limit | Discord API (via bot instance) |
| **Config** (`config.py`) | Load environment variables, validate settings, expose typed config object | All components |

## Recommended Project Structure

```
discord-summary-bot/
|-- bot.py                    # Entry point: create Bot, load cogs, run
|-- config.py                 # Settings from env vars (pydantic-settings)
|-- requirements.txt
|-- .env.example
|
|-- cogs/
|   |-- __init__.py
|   |-- commands.py           # /summarize slash command
|   |-- scheduler.py          # Daily 9am overnight summary task
|
|-- services/
|   |-- __init__.py
|   |-- collector.py          # Fetch + paginate channel messages
|   |-- formatter.py          # Messages -> prompt, LLM response -> embed
|   |-- delivery.py           # Send embeds to channel / DM
|   |-- llm/
|       |-- __init__.py
|       |-- base.py           # Abstract SummarizerBackend class
|       |-- openai_backend.py # OpenAI implementation
|       |-- claude_backend.py # Anthropic implementation
|       |-- factory.py        # Create backend from config string
|
|-- tests/
    |-- test_collector.py
    |-- test_formatter.py
    |-- test_delivery.py
    |-- test_llm_backends.py
```

**Rationale for this layout:**

- **Cogs are thin.** They handle Discord interaction (slash commands, scheduled triggers) and delegate all logic to services. This keeps business logic testable without needing a live Discord connection.
- **Services are plain Python classes.** They receive a bot instance or channel reference as a dependency -- no inheritance from discord.py classes. This makes unit testing straightforward.
- **LLM backends live behind a factory.** `factory.py` reads `LLM_PROVIDER=openai` from config and returns the right backend. Adding a new provider means adding one file and one factory branch.

## Data Flow

### On-Demand Summary (`/summarize`)

```
User runs /summarize [channel] [timeframe]
         |
         v
Commands Cog: parse args, determine time window
         |
         v
Message Collector: channel.history(after=start, before=end, oldest_first=True)
  - Paginate automatically (discord.py handles 100-msg batches)
  - Return list of Message objects
         |
         v
Formatter: build_prompt(messages) -> structured text
  - Format: "username (timestamp): content" per message
  - Add system prompt: "Summarize as concise bullet points..."
  - Truncate if total exceeds LLM context window
         |
         v
LLM Client: summarize(prompt) -> summary text
  - Call provider API (OpenAI, Claude, etc.)
  - Return plain text summary
         |
         v
Formatter: format_embed(summary) -> Discord Embed(s)
  - Split into multiple embeds if > 4096 chars
  - Add metadata (channel name, time range, message count)
         |
         v
Delivery: send to #summaries channel
  - Optionally DM the requesting user
```

### Scheduled Overnight Summary (9am daily)

```
discord.ext.tasks loop fires at 09:00 (configured timezone)
         |
         v
Scheduler Cog: calculate overnight window
  - start = today 10:00 PM - 11 hours (yesterday 10pm)
  - end   = today 09:00 AM
  - iterate over configured channels
         |
         v
(Same pipeline as on-demand from Message Collector onward)
         |
         v
Delivery: post to #summaries (no DM unless configured)
```

## Integration Points

### Discord API Integration

| Operation | API Method | Rate Limit Concern | Mitigation |
|-----------|-----------|-------------------|------------|
| Fetch messages | `channel.history()` | 100 msgs per request, auto-paginated by discord.py | discord.py handles pagination and rate limits internally; for very busy channels (1000+ messages overnight), expect 10+ API calls |
| Send embed | `channel.send(embed=)` | 5 messages per 5 seconds per channel | Batch into fewer embeds; split only when exceeding 4096 chars |
| Slash command registration | `bot.tree.sync()` | Once at startup | Sync on `on_ready`, not on every restart during dev (use guild-specific sync for dev) |
| DM a user | `user.send()` | Same as channel send | Only when requested |

### LLM Provider Integration

The abstract interface should be minimal -- a single method:

```python
from abc import ABC, abstractmethod

class SummarizerBackend(ABC):
    @abstractmethod
    async def summarize(self, prompt: str) -> str:
        """Send prompt to LLM, return summary text."""
        ...
```

Each provider implements this with their SDK:
- **OpenAI**: `openai.AsyncOpenAI().chat.completions.create()`
- **Anthropic**: `anthropic.AsyncAnthropic().messages.create()`

The factory pattern selects the backend at startup from an env var (`LLM_PROVIDER`), so zero provider code touches cogs or other services.

### Scheduling Integration

Use `discord.ext.tasks` with the `time` parameter -- it is purpose-built for this:

```python
import datetime
from discord.ext import commands, tasks

class SchedulerCog(commands.Cog):
    def __init__(self, bot, timezone):
        self.bot = bot
        run_time = datetime.time(hour=9, minute=0, tzinfo=timezone)
        # Dynamically set the time on the loop
        self.daily_summary.change_interval(time=run_time)
        self.daily_summary.start()

    def cog_unload(self):
        self.daily_summary.cancel()

    @tasks.loop(hours=24)  # overridden by change_interval above
    async def daily_summary(self):
        # trigger overnight summary pipeline
        ...

    @daily_summary.before_loop
    async def before_daily(self):
        await self.bot.wait_until_ready()
```

No need for APScheduler or external scheduling libraries -- `discord.ext.tasks` natively supports running at a specific time of day with timezone awareness. This avoids adding unnecessary dependencies.

## Patterns to Follow

### Pattern 1: Thin Cogs, Fat Services

**What:** Cogs contain only Discord interaction logic (command definitions, event listeners). All business logic lives in service classes.

**When:** Always. This is the single most important architectural decision for testability.

**Why:** Services can be unit-tested with mock data. Cogs require a live bot connection to test, making them expensive to verify.

### Pattern 2: Dependency Injection via Bot Instance

**What:** Attach services to the bot instance during setup. Cogs access them via `self.bot.summarizer`, `self.bot.collector`, etc.

**When:** When services need to be shared across cogs or configured at startup.

**Example:**
```python
# bot.py
bot = commands.Bot(command_prefix="!", intents=intents)
bot.collector = MessageCollector(bot)
bot.summarizer = SummarizerBackend.from_config(config)
bot.delivery = DeliveryService(bot)
```

### Pattern 3: Async Throughout

**What:** Every service method is `async def`. The LLM call, message fetching, and delivery are all I/O-bound.

**When:** Always. discord.py runs on asyncio -- blocking calls freeze the entire bot.

**Why:** A synchronous HTTP call to OpenAI would block the event loop, causing the bot to miss heartbeats and disconnect.

### Pattern 4: Graceful Embed Splitting

**What:** When a summary exceeds Discord's 4096-character embed description limit, split it into multiple embeds logically (at bullet point boundaries, not mid-sentence).

**When:** Any time the LLM returns a long summary (likely for overnight recaps of busy channels).

## Anti-Patterns to Avoid

### Anti-Pattern 1: Business Logic in Cogs

**What:** Putting message fetching, prompt building, or LLM calls directly in the slash command handler.

**Why bad:** Cannot unit test without Discord. Cannot reuse logic between on-demand and scheduled paths. Cog files become 500+ lines.

**Instead:** Cog calls `await self.bot.collector.fetch(channel, start, end)` and passes result to the next service.

### Anti-Pattern 2: Hardcoded LLM Provider

**What:** Importing `openai` directly in the summarization logic without an abstraction layer.

**Why bad:** Switching providers requires rewriting business logic. Cannot mock for tests.

**Instead:** Use the abstract `SummarizerBackend` + factory pattern.

### Anti-Pattern 3: Storing Messages in a Database

**What:** Building a message cache or database to store Discord messages for later summarization.

**Why bad:** For a single-server bot with on-demand + daily summaries, this adds significant complexity (schema, migrations, sync logic) with no benefit. Discord's API already stores all messages and provides efficient time-range queries.

**Instead:** Fetch directly from Discord API at summary time. The 10-second delay for paginating a busy channel is acceptable.

### Anti-Pattern 4: Using `on_message` Event for Collection

**What:** Listening to every message in real-time and building an in-memory or database cache.

**Why bad:** Requires the bot to be online 100% of the time or messages are lost. Memory grows unbounded. Adds complexity for no benefit when `channel.history()` exists.

**Instead:** Use `channel.history(after=..., before=...)` at summary time.

## Suggested Build Order

Dependencies between components dictate the build sequence:

```
Phase 1: Foundation
  config.py -> bot.py -> basic cog loading
  (Bot can start and respond to a health-check command)

Phase 2: Core Pipeline
  collector.py -> formatter.py -> one LLM backend
  (Can fetch messages and produce a summary in isolation)

Phase 3: Discord Integration
  commands.py cog -> delivery.py
  (/summarize works end-to-end)

Phase 4: Scheduling
  scheduler.py cog
  (Daily summaries work, reusing Phase 2-3 pipeline)

Phase 5: Polish
  DM delivery option
  Additional LLM backends
  Error handling / logging
  Embed splitting for long summaries
```

**Why this order:**
- Config and bot setup are prerequisites for everything.
- The summarization pipeline (collect -> format -> LLM -> deliver) is the core value -- build it next.
- Slash command integration connects the pipeline to users.
- Scheduling reuses the entire pipeline, so it comes after the pipeline works.
- Polish items are independent of each other and can be done in any order.

## Scalability Considerations

| Concern | Single Server (current) | 10+ Channels | Very Busy Channels (1000+ msgs/day) |
|---------|------------------------|--------------|--------------------------------------|
| Message fetching | ~1 API call | Sequential per channel, ~10 calls | 10+ paginated calls per channel; add concurrency with `asyncio.gather` |
| LLM token usage | One call per summary | One call per channel summary | May need to chunk messages and summarize in stages (map-reduce) |
| Discord embed limits | Rarely hit | More likely with multi-channel | Implement embed splitting from the start |
| Scheduling | Single 9am task | Loop over channels sequentially | Stagger to avoid rate limits |

For the stated single-server scope, none of these require special handling beyond basic embed splitting. The architecture supports future scaling without rewrites because each concern is isolated in its own service.

## Sources

- [discord.py Cogs documentation](https://discordpy.readthedocs.io/en/stable/ext/commands/cogs.html) -- HIGH confidence
- [discord.py Tasks extension](https://discordpy.readthedocs.io/en/stable/ext/tasks/index.html) -- HIGH confidence
- [Architecting Discord bot the right way - DEV Community](https://dev.to/itsnikhil/architecting-discord-bot-the-right-way-383e) -- MEDIUM confidence
- [elizaOS/discord-summarizer](https://github.com/elizaOS/discord-summarizer) -- reference implementation, MEDIUM confidence
- [discord.py Masterclass - Cogs](https://fallendeity.github.io/discord.py-masterclass/cogs/) -- MEDIUM confidence
- [LiteLLM unified interface](https://docs.litellm.ai/) -- reference for provider abstraction, MEDIUM confidence
- [LLM API Adapter](https://github.com/Inozem/llm_api_adapter) -- reference for lightweight adapter pattern, MEDIUM confidence
- [Discord API - Channels Resource](https://discord.com/developers/docs/resources/channel) -- HIGH confidence
