---
phase: 11-help-command
plan: 01
subsystem: commands
tags: [help, slash-command, permissions, embed]
dependency_graph:
  requires: []
  provides: ["/cordbot help command", "command registry"]
  affects: [src/bot/client.py]
tech_stack:
  added: []
  patterns: ["static command registry", "permission-filtered embed"]
key_files:
  created:
    - src/bot/commands/help.py
  modified:
    - src/bot/client.py
decisions:
  - "Static COMMANDS list over dynamic tree introspection -- simpler, predictable, manually maintained"
  - "KU_BLUE defined locally per command module convention (no shared constants module)"
metrics:
  duration: 1m
  completed: "2026-04-08"
---

# Phase 11 Plan 01: Help Command Summary

Static /cordbot command with 11-entry registry, 5 categories with emoji prefixes, and permission-filtered ephemeral embed.

## What Was Done

### Task 1: Create /cordbot help command module
Created `src/bot/commands/help.py` with:
- `CommandInfo` dataclass (name, params, description, category, permission)
- Static `COMMANDS` list with all 11 bot commands
- `CATEGORIES` list with 5 groups and emoji prefixes
- `get_visible_commands()` filtering by public/editor/admin roles
- `build_help_embed()` creating categorized Discord embed
- `register_help_commands()` registering the /cordbot slash command

**Commit:** b1e62d0

### Task 2: Wire help command into bot client
Modified `src/bot/client.py`:
- Added import for `register_help_commands`
- Added registration call in `setup_hook` after roster commands, before guild sync

**Commit:** 4898a55

## Verification Results

1. Module imports with 11 commands registered -- PASS
2. Client imports cleanly with help command wired -- PASS
3. `grep -c` returns 2 (import + call) -- PASS
4. ephemeral=True present in help.py -- PASS
5. "cordbot" command name confirmed -- PASS

## Deviations from Plan

None -- plan executed exactly as written.

## Known Stubs

None. All commands in the registry correspond to real implemented slash commands.
