<!-- GSD:project-start source:PROJECT.md -->
## Project

**Discord Summary Bot**

A Discord bot that summarizes channel discussions on demand and on a schedule. Users can request a bullet-point summary of the last hour, and the bot automatically posts an overnight recap (10pm-9am) every morning at 9am. Built for a single server with summaries posted to a dedicated channel.

**Core Value:** Users can quickly catch up on what they missed without reading through hundreds of messages.

### Constraints

- **Discord API**: Rate limits on message history fetching (100 messages per request, need pagination for busy channels)
- **Message length**: Discord embeds have a 4096 character limit for description — summaries may need truncation or splitting
- **Bot permissions**: Requires Read Message History, Send Messages, and Use Slash Commands permissions
- **Timezone**: Overnight window (10pm-9am) needs a configured timezone
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommended Stack
### Core Framework
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Python | 3.12+ | Runtime | Latest stable with best `zoneinfo` support (needed for timezone-aware scheduling). discord.py supports 3.8-3.12. | HIGH |
| discord.py | 2.7.1 | Discord API wrapper | The definitive Python Discord library. Production/Stable status, actively maintained (latest release March 3, 2026). Built-in slash command support via `discord.app_commands`, built-in task scheduling via `discord.ext.tasks`. | HIGH |
### LLM Integration
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| openai (Python SDK) | 1.x+ | LLM provider client | Use as the default provider SDK. Async support built-in (`AsyncOpenAI`). Most LLM providers (including local ones via Ollama) now expose OpenAI-compatible endpoints, making this a practical "universal" client without needing a multi-provider abstraction layer. | HIGH |
| anthropic (Python SDK) | 0.86.0 | Anthropic provider client | Install only if the user chooses Claude as their provider. Full async support via `AsyncAnthropic`. | MEDIUM |
### Scheduling
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| discord.ext.tasks | (bundled with discord.py) | Daily 9am summary trigger | Built into discord.py. The `@tasks.loop(time=...)` decorator accepts `datetime.time` objects with timezone info, which is exactly what the 9am daily schedule needs. Zero additional dependencies. Handles reconnection logic automatically. | HIGH |
| zoneinfo (stdlib) | (bundled with Python 3.9+) | Timezone handling | Standard library module for IANA timezone support. Use with `tasks.loop(time=...)` to schedule in the configured local timezone (e.g., `zoneinfo.ZoneInfo("America/New_York")`). No third-party timezone library needed. | HIGH |
### Configuration
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| pydantic-settings | 2.x | Settings management | Type-safe, validated configuration from environment variables and `.env` files. Catches misconfiguration at startup (e.g., missing bot token, invalid timezone) instead of at runtime. Reads `.env` files natively -- no separate `python-dotenv` needed. | HIGH |
### Supporting Libraries
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| aiohttp | (bundled with discord.py) | HTTP client | Already a dependency of discord.py. Use if you need to call external APIs beyond the LLM SDKs. |
| pydantic | 2.x | Data models | Already a dependency of pydantic-settings. Use for structured summary data models (message batches, summary results). |
### Development Tools
| Tool | Purpose | Why |
|------|---------|-----|
| uv | Package management + venv | Fastest Python package installer (replaces pip + venv). Single binary, no bootstrap issues. |
| ruff | Linting + formatting | Replaces flake8 + black + isort in one tool. Fast, opinionated, zero-config defaults. |
| pytest + pytest-asyncio | Testing | Standard Python testing. pytest-asyncio needed because discord.py is fully async. |
## Installation
# Create project with uv
# Core dependencies
# Optional: if using Anthropic as provider
# Dev dependencies
## Alternatives Considered
| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Discord library | discord.py | Pycord, Nextcord | discord.py is the original, most maintained, largest community. Pycord/Nextcord are forks created during discord.py's 2021 hiatus -- now that discord.py is back and actively releasing (2.7.1 as of March 2026), the forks have less reason to exist. |
| Discord library | discord.py | interactions.py | Smaller community, less documentation, fewer examples. discord.py covers the same features. |
| Multi-LLM abstraction | Own ABC/Protocol | LiteLLM | LiteLLM suffered a supply chain attack on March 24, 2026 (malicious versions 1.82.7-1.82.8 published to PyPI). While resolved, it signals supply chain risk. More importantly, for a single-server bot needing one provider at a time, LiteLLM's 100+ provider support is massive overkill. A 50-line provider protocol is simpler, safer, and easier to debug. |
| Multi-LLM abstraction | Own ABC/Protocol | LangChain | Enormous dependency tree for a simple summarization task. LangChain is designed for complex agent workflows, not "send text, get summary back." |
| Scheduling | discord.ext.tasks | APScheduler | APScheduler 3.x is end-of-life (no new features), APScheduler 4.x is still alpha. discord.py's built-in `tasks.loop(time=...)` handles the exact use case (run at specific time daily) with zero additional dependencies and native event loop integration. |
| Scheduling | discord.ext.tasks | Celery | Nuclear option for a single scheduled task. Requires a message broker (Redis/RabbitMQ). Absurd for this project. |
| Config | pydantic-settings | python-dotenv alone | No type validation, no structured settings object, manual string-to-type conversion. pydantic-settings does everything python-dotenv does plus validation. |
| Package manager | uv | pip + venv | uv is 10-100x faster, handles venv creation, lockfiles, and Python version management in one tool. pip + venv still works but uv is the modern standard. |
## What NOT to Use
### LiteLLM
### LangChain / LlamaIndex
### Pycord / Nextcord
### APScheduler
### SQLite / PostgreSQL / Any Database
## Architecture Note: Provider-Agnostic Interface
## Sources
- [discord.py PyPI](https://pypi.org/project/discord.py/) -- v2.7.1, March 2026
- [discord.py Releases](https://github.com/Rapptz/discord.py/releases) -- release history
- [discord.ext.tasks docs](https://discordpy.readthedocs.io/en/stable/ext/tasks/index.html) -- built-in scheduling
- [OpenAI Python SDK](https://pypi.org/project/openai/) -- v2.30.0
- [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python/releases) -- v0.86.0
- [APScheduler PyPI](https://pypi.org/project/APScheduler/) -- 3.11.2 stable, 4.0.0a1 alpha
- [Pydantic Settings docs](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [LiteLLM supply chain attack](https://docs.litellm.ai/blog/security-update-march-2026) -- March 24, 2026 incident
- [LiteLLM attack analysis (Datadog)](https://securitylabs.datadoghq.com/articles/litellm-compromised-pypi-teampcp-supply-chain-campaign/)
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
