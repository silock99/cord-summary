# Project Research Summary

**Project:** Discord Summary Bot
**Domain:** Discord bot with scheduled and on-demand LLM-powered channel summarization
**Researched:** 2026-03-27
**Confidence:** HIGH

## Executive Summary

This is a single-server Discord bot that fetches channel message history, preprocesses it, sends it to a configurable LLM provider, and posts formatted summaries back to Discord — both on-demand via slash command and automatically on a daily 9am schedule. The domain is well-understood: multiple open-source reference implementations exist (elizaOS/discord-summarizer, rauljordan/daily-discord-summarizer), and the two major commercial bots (TLDRBot, Summary Bot) define the feature baseline users expect. The recommended approach is Python 3.12 + discord.py 2.7.1 + pydantic-settings, with a thin custom `SummarizerBackend` ABC to stay provider-agnostic. Avoid LiteLLM (supply chain attack March 2026, 800+ open issues), LangChain (massive overkill), and APScheduler (use discord.py's built-in `tasks.loop` instead).

The architecture is well-established: thin Cogs delegate to plain Python service classes (MessageCollector, Formatter, Delivery, LLM backends). This is the only approach that keeps business logic independently testable without a live Discord connection. The data flow is linear: fetch messages from Discord API → filter noise → build prompt → call LLM → format embed → post to channel. No database is needed; Discord's API serves as the message store. The factory pattern for LLM backends means swapping providers is adding one file and one config value.

The critical risks are all known and mitigable: Message Content Intent must be explicitly enabled in both the Developer Portal and code (silent failure otherwise); token overflow on busy overnight channels requires a chunking/map-reduce strategy from day one; Discord silently truncates embeds over 4096 chars without raising errors; slash commands expire in 3 seconds so `interaction.defer()` must be the very first thing every command handler does. None of these are novel problems — they are extensively documented in the discord.py ecosystem and all have clear, established solutions.

## Key Findings

### Recommended Stack

The stack is deliberately minimal. discord.py 2.7.1 (March 2026, actively maintained) handles Discord API, slash commands, scheduling, and rate limiting. pydantic-settings 2.x provides type-validated config from `.env` files at startup — catching misconfiguration before the bot runs. The `openai` Python SDK (1.x+) serves as the "universal" LLM client since virtually all providers expose OpenAI-compatible endpoints; the `anthropic` SDK is added only if the user chooses Claude. All scheduling uses `discord.ext.tasks` built into discord.py, eliminating APScheduler entirely. `uv` replaces pip+venv for package management. No database, no multi-provider library, no external scheduler.

**Core technologies:**
- **Python 3.12+**: Runtime — `zoneinfo` stdlib support for timezone-aware scheduling, latest stable
- **discord.py 2.7.1**: Discord API wrapper — slash commands, `channel.history()`, `tasks.loop`, rate limit handling built-in
- **openai SDK 1.x**: LLM client — async-native, works with OpenAI-compatible endpoints (Ollama, local models, etc.)
- **pydantic-settings 2.x**: Config — type-validated env vars, catches missing tokens at startup, reads `.env` natively
- **discord.ext.tasks**: Scheduling — built into discord.py, `time=` parameter with timezone support, no extra deps
- **zoneinfo** (stdlib): Timezone handling — IANA timezone support, replaces deprecated pytz
- **uv**: Package manager — 10-100x faster than pip, handles venv + lockfiles in one tool

### Expected Features

The competitive landscape (TLDRBot, Summary Bot, Wallubot, Discord native Summaries AI) defines clear table-stakes expectations. Any bot missing on-demand `/summary`, configurable time range, Discord embed formatting, and a daily digest will feel incomplete compared to existing options.

**Must have (table stakes):**
- On-demand `/summary` slash command with time range option — core interaction every competitor has
- Message pagination (100 msgs per API call) — mandatory for any real channel volume
- Discord embed formatting with length splitting — 4096-char limit requires active handling
- Scheduled 9am overnight summary — daily digest is standard, already in project requirements
- Smart filtering (skip bot messages, system messages) — improves LLM quality, reduces token waste
- Empty/low-activity handling — bot that errors on quiet channels looks broken
- Token/context window management — chunking strategy required before any real usage
- Post to dedicated `#summaries` channel — standard pattern to avoid cluttering discussion

**Should have (competitive differentiators):**
- Topic-grouped summaries — Discord's native AI does this; flat bullet lists feel inferior
- Action items / decisions extraction — high-value for project-oriented servers
- Multi-channel selection (slash command option) — users want to choose which channel
- DM delivery option — already in project requirements, low complexity
- Unread summary (`/unreadsummary`) — "what did I miss since I was last here?" is the killer use case

**Defer (v2+):**
- Question-focused summaries — power-user feature, adds prompt complexity
- Thread output mode — config preference, low priority
- Participant attribution — requires per-topic author tracking
- Language configuration — single-server bot likely single-language

### Architecture Approach

The architecture follows a clear layered pattern: a thin Bot Core loads two Cogs (Commands, Scheduler) that delegate entirely to four service classes (MessageCollector, Formatter, LLM backends, Delivery). Cogs contain zero business logic — they parse Discord interactions and call services. Services are plain Python classes injected via the bot instance at startup, making them unit-testable with mock data. The LLM layer uses an abstract `SummarizerBackend` ABC with a factory that reads `LLM_PROVIDER` from config to instantiate the right backend. No database, no message cache, no `on_message` listener — all fetching happens at summary time via `channel.history(after=..., before=...)`.

**Major components:**
1. **Bot Core** (`bot.py`) — initializes `commands.Bot`, attaches service instances, loads cogs, manages lifecycle
2. **Commands Cog** (`cogs/commands.py`) — registers `/summarize` slash command, defers immediately, delegates to services
3. **Scheduler Cog** (`cogs/scheduler.py`) — `discord.ext.tasks` loop at 09:00, calculates overnight window, reuses same pipeline
4. **Message Collector** (`services/collector.py`) — `channel.history()` pagination, time-range filtering, bot/system message filtering
5. **Formatter** (`services/formatter.py`) — builds LLM prompt from messages, converts LLM output to Discord embeds, handles splitting at bullet boundaries
6. **LLM Client** (`services/llm/`) — abstract `SummarizerBackend` ABC + OpenAI/Claude implementations + factory pattern
7. **Delivery** (`services/delivery.py`) — posts embeds to channel, optional DM delivery, handles embed splitting
8. **Config** (`config.py`) — pydantic-settings, typed, validated at startup

### Critical Pitfalls

1. **Message Content Intent not enabled** — Enable `intents.message_content = True` in code AND in the Developer Portal; add a startup self-test that fetches one message and asserts `content` is non-empty. Silent failure: summaries appear to work but contain no content.

2. **Token limit overflow on busy channels** — Design a chunking/map-reduce strategy from the start. 2000 messages overnight = 30-60K tokens of input. Implement token counting, chunk messages to 70% of context window, summarize-then-summarize. Cannot be bolted on later without restructuring the pipeline.

3. **Silent embed truncation** — Discord silently truncates embed descriptions over 4096 chars with no error raised. Build a `split_embed()` utility on day one that splits at bullet-point boundaries. Also set `max_tokens` on LLM output.

4. **3-second slash command timeout** — `interaction.response.defer()` must be the first line of every slash command handler, before any I/O. Never fetch messages or call the LLM before deferring. Use `interaction.followup.send()` for the result.

5. **Slash command sync confusion** — Use guild-specific sync during development (instant) and global sync for production. Provide an owner-only `!sync` command. Never call `tree.sync()` in `on_ready` without a guard (fires on every reconnect). Verify bot invite URL includes `applications.commands` scope.

## Implications for Roadmap

Based on research, the architecture's own suggested build order aligns with feature dependencies. The pipeline (collect → filter → format → LLM → deliver) is the value core; everything else wires into it.

### Phase 1: Foundation and Bot Scaffolding
**Rationale:** Config, bot setup, and slash command infrastructure are prerequisites for every other component. Three critical pitfalls (intent, sync, defer) must be solved here or they silently corrupt everything downstream.
**Delivers:** Bot connects to Discord, registers slash commands correctly, responds to a health-check command. Message Content Intent verified at startup.
**Addresses:** Bot connection and slash command framework (foundation for all FEATURES.md table stakes)
**Avoids:** Message Content Intent silent failure, slash command sync issues, `on_ready` double-firing

### Phase 2: Core Summarization Pipeline
**Rationale:** The message collection and LLM integration pipeline is the product's core value. Build and test it as isolated service classes (without slash command glue) so it can be verified with unit tests before wiring into Discord interactions.
**Delivers:** `MessageCollector` fetches and paginates channel messages; preprocessing filters bot/system messages; `Formatter` builds prompts; one LLM backend (OpenAI) produces a summary; result formatted into embed(s) with splitting.
**Addresses:** Message pagination, smart filtering, token/length management, pluggable LLM interface, bullet-point embed output (FEATURES.md P0 items)
**Avoids:** Token overflow (chunking strategy built here), silent embed truncation (split utility built here), LLM cost spiral (token counting and `max_tokens` configured here)

### Phase 3: On-Demand Slash Command
**Rationale:** Wires Phase 2 pipeline to a Discord interaction. At this point the bot becomes immediately useful and testable by real users.
**Delivers:** `/summary [channel] [timeframe]` slash command works end-to-end. Deferred response with "Generating..." placeholder, followed by embed result.
**Addresses:** On-demand `/summary` with time range, multi-channel selection, empty channel handling (FEATURES.md P0/P1)
**Avoids:** 3-second timeout (defer on entry), rate limit errors during message fetch

### Phase 4: Scheduled Overnight Summary
**Rationale:** Reuses the entire Phase 2-3 pipeline; only adds the `discord.ext.tasks` trigger and overnight window calculation. Since the pipeline already works, this phase is low-risk.
**Delivers:** 9am daily summary auto-posts to `#summaries` channel covering the overnight window.
**Addresses:** Scheduled daily digest, dedicated output channel (FEATURES.md P0)
**Avoids:** DST scheduling bugs (use `zoneinfo`, `tasks.loop time=` parameter), double-firing on reconnect (guard in `setup_hook`)

### Phase 5: Polish and Robustness
**Rationale:** These items are independent of each other and add resilience, cost control, and usability improvements. Do after the core loop is confirmed working.
**Delivers:** DM delivery option, second LLM backend (Claude), LLM error handling with retry and fallback notification to summary channel, cost tracking logs, edge case handling (mention resolution, attachment handling documentation, thread scope clarification).
**Addresses:** DM delivery (FEATURES.md P1), second LLM provider, graceful error handling (PITFALLS.md moderate pitfalls)

### Phase 6: Enhanced Summaries
**Rationale:** Topic grouping, action item extraction, and unread summaries are prompt engineering and pipeline refinements. They require the core loop to be stable before investing time in tuning output quality.
**Delivers:** Topic-grouped summaries, action items/decisions extraction, `/unreadsummary` command.
**Addresses:** FEATURES.md P1/P2 differentiators — topic grouping, action items, unread summary

### Phase Ordering Rationale

- Config before everything: pydantic-settings catches misconfiguration at startup; every other component depends on valid, typed config
- Pipeline before commands: the collect→LLM→deliver pipeline is fully unit-testable in isolation; building it first means slash commands and scheduler are integration work, not design work
- Slash command before scheduler: the scheduler reuses the slash command's pipeline; verify the pipeline end-to-end with human-triggered commands before running it automatically
- Core before polish: error handling, retries, and cost controls are independent of pipeline correctness and can be layered in after the happy path works
- Prompt engineering last: topic grouping and action items are refinements that require a working baseline to tune against

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (Core Pipeline):** Token chunking strategy specifics — exact tiktoken usage with OpenAI and heuristics for other providers; map-reduce prompt design for multi-chunk summarization
- **Phase 4 (Scheduling):** Verify `discord.ext.tasks` `change_interval` behavior with `time=` parameter in discord.py 2.7.1 — alternative is to pass `time=` directly at loop definition

Phases with standard patterns (skip research-phase):
- **Phase 1 (Foundation):** discord.py bot setup and cog loading is extensively documented with no ambiguity
- **Phase 3 (Slash Command):** discord.py slash command patterns and `interaction.defer()` are well-established
- **Phase 5 (Polish):** Standard Python retry/error handling; no Discord-specific research needed

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All technology choices verified against official docs and recent PyPI releases. LiteLLM exclusion backed by documented supply chain incident (March 2026). discord.py 2.7.1 confirmed active as of March 2026. |
| Features | HIGH | Feature expectations derived from 7+ live competitor bots and official Discord documentation. Table stakes are unambiguous. |
| Architecture | HIGH | Cog/service separation is official discord.py recommended pattern. Multiple reference implementations confirm the approach. Data flow is straightforward with no ambiguous design decisions. |
| Pitfalls | HIGH | All critical pitfalls are documented with official sources (Discord Developer Portal, discord.py docs, Discord API docs). Message Content Intent, embed limits, and 3-second timeout are well-known issues with verified solutions. |

**Overall confidence:** HIGH

### Gaps to Address

- **Exact chunking thresholds**: Token limits vary by model (GPT-4o: 128K, GPT-4o-mini: 128K, Claude Haiku: 200K). The chunking strategy should be configurable per provider rather than hardcoded. Validate during Phase 2.
- **Overnight window definition**: The exact window (10pm–9am vs. midnight–9am) should be confirmed and made configurable. Address in Phase 4 planning.
- **`tasks.loop change_interval` behavior**: Verify this pattern works as expected in discord.py 2.7.1 before relying on it in Phase 4. Low risk, quick to validate.
- **Thread/forum channel scope**: `channel.history()` does not include thread messages. Whether threads should be summarized is a product decision not yet addressed. Document the limitation and decide before Phase 3 ships.
- **Prompt engineering iteration**: Summary quality depends heavily on system prompt design. This needs iteration with real message data; upfront research will not resolve it. Treat Phase 6 as iterative.

## Sources

### Primary (HIGH confidence)
- [discord.py PyPI](https://pypi.org/project/discord.py/) — v2.7.1, March 2026 release confirmed
- [discord.ext.tasks docs](https://discordpy.readthedocs.io/en/stable/ext/tasks/index.html) — scheduling patterns, `time=` parameter
- [Discord Developer Portal: Message Content Intent FAQ](https://support-dev.discord.com/hc/en-us/articles/4404772028055-Message-Content-Privileged-Intent-FAQ) — privileged intent requirements
- [Discord API Rate Limits](https://discord.com/developers/docs/topics/rate-limits) — rate limit specifics
- [Python Discord: Embed Limits](https://www.pythondiscord.com/pages/guides/python-guides/discord-embed-limits/) — 4096-char limit documented
- [discord.py Slash Command Guide (AbstractUmbra)](https://gist.github.com/AbstractUmbra/a9c188797ae194e592efe05fa129c57f) — sync patterns and gotchas
- [Pydantic Settings docs](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) — config management

### Secondary (MEDIUM confidence)
- [elizaOS/discord-summarizer](https://github.com/elizaOS/discord-summarizer) — reference implementation: action items, topic categorization, local LLM processing
- [rauljordan/daily-discord-summarizer](https://github.com/rauljordan/daily-discord-summarizer) — reference implementation: configurable digest intervals, message aggregation
- [Wallubot documentation](https://docs.wallubot.com/blog/discord-conversation-summarizer) — competitor features: smart filtering, question-focused queries, auto-timespan detection
- [Summary Bot on top.gg](https://top.gg/bot/1058568749076185119) — competitor features: /unreadsummary, /setlanguage, /setthread, /fromtosummary
- [TLDRBot on top.gg](https://top.gg/bot/1079089748410376202) — competitor features: automatic intervals, adjustable length, $0.02/request pricing model
- [Deepchecks: 5 Approaches to Solve LLM Token Limits](https://www.deepchecks.com/5-approaches-to-solve-llm-token-limits/) — chunking strategies
- [Architecting Discord bot the right way - DEV Community](https://dev.to/itsnikhil/architecting-discord-bot-the-right-way-383e) — cog/service separation pattern

### Tertiary (LOW confidence)
- [LiteLLM supply chain attack](https://docs.litellm.ai/blog/security-update-march-2026) — March 24, 2026 incident; justification for excluding LiteLLM
- [Datadog security analysis of LiteLLM attack](https://securitylabs.datadoghq.com/articles/litellm-compromised-pypi-teampcp-supply-chain-campaign/) — corroboration of supply chain incident
- [LLM Cost Optimization Guide](https://blog.premai.io/llm-cost-optimization-8-strategies-that-cut-api-spend-by-80-2026-guide/) — cost figures are estimates, vary heavily by usage and model selection

---
*Research completed: 2026-03-27*
*Ready for roadmap: yes*
