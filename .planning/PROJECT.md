# Discord Summary Bot

## What This Is

A Discord bot that summarizes channel discussions on demand and on a schedule. Users can run `/summary` to get a topic-grouped bullet-point recap of recent messages, and the bot automatically posts an overnight recap (10pm-9am) every morning at 9am. Supports DM delivery, thread posting, configurable language controls, and admin error alerting. Built for a single server.

## Core Value

Users can quickly catch up on what they missed without reading through hundreds of messages.

## Requirements

### Validated

- ✓ AI summarization backend is pluggable (provider-agnostic interface) — v1.0
- ✓ Bot reads message history with pagination and filters bot/system messages — v1.0
- ✓ `/summary` slash command with time range selection and channel targeting — v1.0
- ✓ Summaries grouped by topic with bold headers and bullet points — v1.0
- ✓ Quiet channels return "no significant activity" message — v1.0
- ✓ Summaries posted as Discord embeds with 4096-char split handling — v1.0
- ✓ Automated overnight summary (10pm-9am) posted at 9am daily — v1.0
- ✓ Summaries posted to dedicated #summaries channel — v1.0
- ✓ Users can receive summaries via DM — v1.0
- ✓ Summaries can be posted as threads — v1.0
- ✓ Reply chains formatted with indentation in LLM input — v1.0
- ✓ @here/@everyone messages flagged as important — v1.0
- ✓ Popular messages (5+ reactions/replies) prioritized — v1.0
- ✓ Typed attachment metadata in LLM input — v1.0
- ✓ Embed content extracted and included — v1.0
- ✓ Signal-aware system prompts — v1.0
- ✓ Language controls via blocklist/allowlist — v1.0
- ✓ Admin error alerting via DM — v1.0
- ✓ `/post-summary` admin-only command — v1.0

### Active

- [ ] Transfer portal lookup command filtered by sport and school
- [ ] KU recruiting list with role-gated add/remove (name, position, previous school, star rating)
- [ ] KU recruiting list view command filterable by sport
- [ ] Career stats lookup for players on KU recruiting list
- [ ] JSON file persistence for recruiting data
- [ ] Two sports supported: men's college basketball and men's college football

### Out of Scope

- Multi-server support — single server only for v1
- Voice channel transcription — text channels only
- Web dashboard — config via env vars
- Message database storage — Discord API provides history on demand
- Real-time streaming summaries — on-demand and scheduled only
- Built-in AI model — user plugs in their preferred provider
- Role-based permissions — any server member can use (admin commands excepted)

## Current Milestone: v1.1 Athletics Intelligence

**Goal:** Add transfer portal monitoring, KU recruiting tracking, and career stats lookup for men's basketball and football.

**Target features:**
- Transfer portal lookup — user picks sport + school, sees players currently in the portal
- KU recruiting list — authorized users can manage players; anyone can view by sport
- Career stats — college career stats for players on the KU recruiting list
- Data sourced from web (research needed for best sources)

## Context

Shipped v1.0 with 2,490 lines Python across 43 files.
Tech stack: Python 3.12+, discord.py 2.7.1, OpenAI SDK, pydantic-settings.
Scheduling: discord.ext.tasks with zoneinfo timezone support.
Config: pydantic-settings with .env file support.
Persistence: JSON file for DM subscriber opt-ins, text files for language blocklist/allowlist.

## Constraints

- **Discord API**: Rate limits on message history fetching (100 messages per request, need pagination)
- **Message length**: Discord embeds have a 4096 character limit — summaries split at topic boundaries
- **Bot permissions**: Requires Read Message History, Send Messages, Use Slash Commands
- **Timezone**: Overnight window (10pm-9am) needs configured timezone
- **Single server**: Config values (server ID, channel IDs, timezone) in environment variables

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python + discord.py | Most mature Discord bot ecosystem, strong async support | ✓ Validated v1.0 |
| Pluggable AI backend | User decides AI provider; keeps options open | ✓ Validated v1.0 |
| Dedicated summary channel | Keeps summaries organized, doesn't clutter discussion | ✓ Validated v1.0 |
| Slash commands over prefix | Modern Discord standard, better UX with autocomplete | ✓ Validated v1.0 |
| Ephemeral on-demand summaries | Private responses; public posting reserved for scheduled | ✓ Decided Phase 2 |
| Dynamic task loop for scheduling | `tasks.loop(time=)` pattern for runtime timezone config | ✓ Decided Phase 3 |
| JSON file persistence for DM opt-ins | Avoids database dependency per project constraints | ✓ Decided Phase 3 |
| ADMIN_USER_IDS unified admin concept | Single admin identity: error DMs, /post-summary, cooldown exemption | ✓ Decided Phase 6 |
| Error alerts via DM, not channel | Keeps summary channel clean; errors only visible to admins | ✓ Decided Phase 6 |
| Reply indentation depth-2 cap | Keeps LLM input readable without deep nesting | ✓ Decided Phase 4 |
| Popularity threshold: 5+ reactions OR 5+ replies | Clear, simple threshold for flagging popular messages | ✓ Decided Phase 4 |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-07 after v1.1 milestone start*
