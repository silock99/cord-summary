# Discord Summary Bot

## What This Is

A Discord bot that summarizes channel discussions on demand and on a schedule. Users can request a bullet-point summary of the last hour, and the bot automatically posts an overnight recap (10pm-9am) every morning at 9am. Built for a single server with summaries posted to a dedicated channel.

## Core Value

Users can quickly catch up on what they missed without reading through hundreds of messages.

## Requirements

### Validated

- [x] AI summarization backend is pluggable (provider-agnostic interface) — Validated in Phase 1: Foundation and Pipeline
- [x] Bot reads message history from Discord channels to feed into summarization — Validated in Phase 1: Foundation and Pipeline
- [x] Users can run a slash command to get a summary of recent discussion — Validated in Phase 2: On-Demand Summarization
- [x] Summaries are formatted as concise bullet-point recaps of key topics — Validated in Phase 2: On-Demand Summarization

### Active

- [ ] Bot automatically generates and posts an overnight summary (10pm-9am) at 9am daily
- [ ] Bot automatically generates and posts an overnight summary (10pm-9am) at 9am daily
- [ ] Summaries are posted to a dedicated #summaries channel
- [ ] Users can optionally receive the summary as a DM
- [ ] Any server member can use the summary commands (no role restrictions)

### Out of Scope

- Multi-server support — single server only for v1
- Real-time streaming summaries — on-demand and scheduled only
- Summarizing voice channels — text channels only
- Built-in AI model — bot provides the interface, user plugs in their preferred provider
- Web dashboard — all configuration via code/env vars

## Context

- Target platform: Discord (using bot token + slash commands)
- Language: Python with discord.py (mature Discord bot ecosystem)
- Scheduling: Built-in scheduler for the 9am automatic summary
- AI integration: Abstract interface that can wrap OpenAI, Claude, or other LLM APIs
- Message fetching: Discord API provides channel history access with timestamp filtering
- Single server deployment: Config values (server ID, channel IDs, timezone) stored in environment variables

## Constraints

- **Discord API**: Rate limits on message history fetching (100 messages per request, need pagination for busy channels)
- **Message length**: Discord embeds have a 4096 character limit for description — summaries may need truncation or splitting
- **Bot permissions**: Requires Read Message History, Send Messages, and Use Slash Commands permissions
- **Timezone**: Overnight window (10pm-9am) needs a configured timezone

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python + discord.py | Most mature Discord bot ecosystem, strong async support | — Pending |
| Pluggable AI backend | User wants to decide AI provider later; keeps options open | — Pending |
| Dedicated summary channel | Keeps summaries organized, doesn't clutter discussion channels | — Pending |
| Slash commands over prefix commands | Modern Discord standard, better UX with autocomplete | ✓ Validated Phase 2 |
| Ephemeral on-demand summaries | On-demand summaries are private; public posting reserved for scheduled summaries | ✓ Decided Phase 2 (D-03) |
| No action items extraction in v1 | Topic-grouped bullets only; action items deferred | ✓ Decided Phase 2 (D-13) |

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
*Last updated: 2026-03-27 after Phase 2 completion — on-demand /summary command with ephemeral topic-grouped embeds, channel allowlist, quiet detection*
