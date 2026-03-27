---
phase: 01-foundation-and-pipeline
plan: 01
subsystem: core
tags: [scaffolding, config, models, bot-client]
dependency_graph:
  requires: []
  provides: [bot-package, settings-config, data-models, bot-client, command-sync]
  affects: [01-02, 01-03]
tech_stack:
  added: [discord.py-2.7.1, openai-2.30.0, pydantic-settings-2.13.1, hatchling]
  patterns: [src-layout, pydantic-settings-config, dataclass-models, commands.Bot-subclass]
key_files:
  created:
    - pyproject.toml
    - .python-version
    - .env.example
    - .gitignore
    - src/bot/__init__.py
    - src/bot/__main__.py
    - src/bot/config.py
    - src/bot/models.py
    - src/bot/client.py
    - src/bot/pipeline/__init__.py
    - src/bot/providers/__init__.py
    - uv.lock
  modified: []
decisions:
  - Used hatchling build backend with src layout for proper package installation
  - Used dependency-groups.dev instead of deprecated tool.uv.dev-dependencies
metrics:
  duration: 3m
  completed: "2026-03-27T19:28:42Z"
---

# Phase 01 Plan 01: Project Scaffolding and Bot Client Summary

Initialized Python project with uv and hatchling build system using src layout, pydantic-settings-based configuration with validated env vars, shared data models (ProcessedMessage, SummaryError), and a SummaryBot class with Message Content/Members intents and guild-scoped slash command sync.

## What Was Built

### Task 1: Project scaffolding and configuration module
- Initialized project with `uv init`, configured hatchling build backend for src layout
- Added core dependencies: discord.py>=2.7.1, openai>=1.0.0, pydantic-settings>=2.0.0
- Added dev dependencies: ruff, pytest, pytest-asyncio
- Created `Settings` class with pydantic-settings for type-safe env var loading (discord_token, guild_id, summary_channel_id, openai_api_key, openai_base_url, openai_model, timezone, max_context_tokens)
- Created `ProcessedMessage` dataclass with author, content, timestamp fields and `to_line()` method
- Created `SummaryError` exception for user-facing summarization failures
- Created package structure: bot, bot.pipeline, bot.providers
- Created `.env.example` documenting all required environment variables

**Commit:** `61e3b7c` feat(01-01): project scaffolding and configuration module

### Task 2: Bot client with intent configuration and slash command sync
- Created `SummaryBot(commands.Bot)` with Message Content and Members privileged intents
- Implemented `setup_hook` that copies global commands to guild and syncs them
- Added `on_ready` handler with connection status and guild verification logging
- Created `__main__.py` entry point with logging config, Settings validation, and bot.run()

**Commit:** `29fa7f5` feat(01-01): bot client with intent config and slash command sync

## Decisions Made

1. **Hatchling build backend with src layout** - uv init creates a flat layout by default; switched to hatchling with `packages = ["src/bot"]` so the `bot` package is properly installable and importable via `uv run`.
2. **dependency-groups.dev over tool.uv.dev-dependencies** - The latter is deprecated in uv 0.11+; used the PEP 735 standard format instead.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added build system for src layout**
- **Found during:** Task 1 verification
- **Issue:** `uv run python -c "from bot.config import Settings"` failed with ModuleNotFoundError because uv init does not configure a build backend for src layout
- **Fix:** Added `[build-system]` with hatchling and `[tool.hatch.build.targets.wheel] packages = ["src/bot"]`
- **Files modified:** pyproject.toml
- **Commit:** 61e3b7c

**2. [Rule 2 - Missing] Added .gitignore**
- **Found during:** Post-task cleanup
- **Issue:** No .gitignore existed; __pycache__ and .venv would be committed
- **Fix:** Created .gitignore with standard Python exclusions
- **Files modified:** .gitignore (new)

## Verification Results

```
$ uv run python -c "from bot.config import Settings; from bot.models import ProcessedMessage, SummaryError; from bot.client import SummaryBot; print('All imports OK')"
All imports OK
```

## Known Stubs

None - all code is fully functional. Configuration requires real env vars to run the bot against Discord.

## Self-Check: PASSED

- All 12 created files verified present on disk
- Both commits (61e3b7c, 29fa7f5) verified in git log
