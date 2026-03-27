# Feature Landscape

**Domain:** Discord channel summarization bot
**Researched:** 2026-03-27

## Table Stakes

Features users expect from any Discord summarization bot. Missing any of these and users will switch to an existing solution (TLDRBot, Summary Bot, Wallubot, or Discord's native Summaries AI).

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| On-demand slash command summary (`/summary` or `/tldr`) | Every competitor has this. It is the core interaction. | Low | Single command, fetch messages, call LLM, return result. Already in project requirements. |
| Configurable time range | Summary Bot offers `/fromtosummary`; Wallubot auto-detects timespan since user's last message. Users need to specify "last 2 hours" or "since yesterday." | Medium | Slash command options for duration. Parsing relative times ("2h", "1d") is straightforward. |
| Bullet-point formatted output | Every bot returns structured bullet points or topic groupings. Raw paragraph summaries feel lazy. | Low | Prompt engineering concern, not code complexity. Already in project requirements. |
| Discord embed formatting | All serious bots use rich embeds, not plain text. Embeds look professional and handle the 4096-char limit gracefully. | Low | discord.py Embed objects. Split into multiple embeds if summary exceeds limit. |
| Scheduled/automatic summaries | Daily digest is standard. rauljordan/daily-discord-summarizer does 3-hour intervals. TLDRBot offers automatic summaries at intervals. | Medium | Async scheduler (discord.ext.tasks). Already in project requirements as the 9am overnight recap. |
| Post to dedicated channel | Standard pattern to avoid cluttering discussion channels. | Low | Already in project requirements. Simple channel ID config. |
| Multi-channel awareness | Bot should be able to summarize different channels, not just one hardcoded channel. Summary Bot and Wallubot both let users pick which channel to summarize. | Low | Slash command option to select target channel. Default to current channel. |
| Message pagination | Discord API returns max 100 messages per request. Busy overnight channels can have hundreds of messages. Every working bot handles this. | Medium | Loop with `before` parameter until time window is covered. |
| Token/length management | LLM context windows have limits; Discord embeds max 4096 chars for description. | Medium | Chunk messages if they exceed context window; split or truncate summary if over embed limit. |
| Error handling for empty/low-activity periods | "Nothing notable happened" is a valid summary. Bots that return errors or hallucinate content when channels are quiet look broken. | Low | Check message count before calling LLM. Return a "no significant activity" message if below threshold. |

## Differentiators

Features that set the bot apart. Not expected, but valued. These move the bot from "yet another summary bot" to something users prefer.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Topic-grouped summaries | Discord's native Summaries AI groups by topic with participant lists. Most third-party bots return flat bullet lists. Grouping by topic makes long summaries scannable. | Medium | Prompt engineering to instruct LLM to cluster by topic. May need post-processing to format topic headers as separate embed fields. |
| Action items / decisions extraction | elizaOS/discord-summarizer categorizes into Technical Tasks, Documentation Needs, Feature Requests. Optimum Web's bot extracts "key points, decisions made, action items, unresolved questions." High-value for project-oriented servers. | Medium | Separate prompt section or structured output from LLM. Format as distinct embed sections. |
| Smart filtering (ignore bot spam, system messages) | Wallubot filters out bot messages and system noise. Reduces LLM token waste and improves summary quality significantly. | Low | Filter by `message.author.bot` and message type before sending to LLM. Simple but impactful. |
| DM delivery option | Users who want personal catch-ups without posting in a channel. Already in project requirements. | Low | Send embed via DM instead of or in addition to channel post. |
| Unread summary (`/unreadsummary`) | Summary Bot's most clever feature: summarize everything since the user's last message in that channel. Wallubot does this automatically with no parameters. Solves "what did I miss?" precisely. | Medium | Query user's last message timestamp in channel, then fetch messages after that point. |
| Question-focused summaries | Wallubot's `question:` parameter lets users ask targeted questions about the conversation instead of getting a generic overview. Turns the bot into a conversational search tool. | Medium | Pass user's question as additional context to LLM alongside messages. More useful than it sounds. |
| Thread output mode | Summary Bot's `/setthread` toggles between posting summary as a thread or inline message. Threads keep channels cleaner for long summaries. | Low | `create_thread()` on the summary message. Simple toggle. |
| Participant attribution | Discord native Summaries AI shows who participated in each topic. Helps users know who to follow up with. | Medium | Track message authors per topic cluster. Include "@user" style attribution in output. |
| Configurable summary language | Summary Bot has `/setlanguage`. Valuable for international communities. | Low | Pass language preference to LLM prompt. Store per-server preference. |

## Anti-Features

Features to explicitly NOT build. These are tempting but wrong for a single-server self-hosted bot.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Per-request pricing / token metering | This is a personal/single-server bot, not a SaaS product. TLDRBot charges $0.02/request because they host the LLM. We use the user's own API key. | Track token usage in logs for cost awareness, but do not gate features behind payments. |
| Web dashboard for configuration | Explicitly out of scope per PROJECT.md. Adds massive complexity for a single-server bot. | Environment variables and optionally a `/config` slash command for runtime tweaks. |
| Voice channel transcription + summary | NotesBot and Memolin do this, but it requires audio processing, speech-to-text, and is an entirely different problem domain. | Stay focused on text channels. Voice summary is a different project. |
| Multi-server support | Out of scope per PROJECT.md. Adds database complexity, per-server config, sharding concerns. | Single-server config via env vars. Architecture should not preclude multi-server later, but do not build for it now. |
| Real-time streaming summaries | Out of scope per PROJECT.md. Continuous summarization is expensive and noisy. | On-demand and scheduled summaries are the right interaction model. |
| Visual/mind-map summaries | Mapify does this. Gimmick that adds image generation complexity with minimal value for a text-based Discord channel. | Bullet points and topic groupings are the right format for Discord. |
| Auto-moderation integration | Some community management bots bundle summarization with spam detection. These are separate concerns. | Keep the bot single-purpose. Moderation is a different bot. |
| Storing full message history in a database | Some bots (rauljordan's) store all messages locally. Adds storage management and privacy concerns. Unnecessary when Discord's API provides history access. | Fetch from Discord API on demand. Cache only during active summarization. |
| Custom AI model hosting | Out of scope -- user brings their own API key for their preferred provider. | Provide pluggable interface, user configures provider and key. |
| Role-based permissions | PROJECT.md says "any server member can use." Adding roles adds config burden for a single-server bot. | Let anyone use it. Can add via discord.py's built-in permission checks later if needed. |

## Feature Dependencies

```
Slash command infrastructure
  |-> On-demand summary (/summary)
  |     |-> Configurable time range (option on /summary command)
  |     |-> Multi-channel selection (option on /summary command)
  |     |-> Question-focused summary (option on /summary command)
  |     |-> Unread summary (/unreadsummary - separate command)
  |
  |-> Scheduled summary (discord.ext.tasks loop)
        |-> Dedicated output channel (config)
        |-> DM delivery (config toggle)

Message fetching + pagination
  |-> All summary features depend on this
  |-> Smart filtering (pre-processing step applied before LLM call)

LLM integration (pluggable provider interface)
  |-> Bullet-point formatting (prompt design)
  |-> Topic-grouped summaries (prompt design)
  |-> Action items extraction (prompt design / structured output)
  |-> Participant attribution (prompt + message metadata)
  |-> Language configuration (prompt parameter)
  |-> Question-focused summaries (prompt parameter)

Discord embed formatting
  |-> All output features depend on this
  |-> Thread output mode (post-processing option)
  |-> Multi-embed splitting for long summaries
```

## MVP Recommendation

Build these first -- they cover the core use case from PROJECT.md and match table-stakes expectations:

1. **Bot connection + slash command registration** -- foundation everything else depends on
2. **Message fetching with pagination** -- the data pipeline; handles Discord's 100-message limit
3. **Smart filtering** -- skip bot messages and system messages before sending to LLM (cheap win, big quality improvement)
4. **Pluggable LLM provider interface + first implementation** -- the intelligence layer; abstract interface with one concrete provider
5. **On-demand `/summary` command with time range option** -- wires 1-4 together, immediately testable
6. **Embed formatting with length handling** -- makes output presentable; handles the 4096-char limit
7. **Scheduled overnight summary** -- adds the `tasks.loop` trigger to existing summary logic, posts to dedicated channel
8. **Empty channel handling** -- graceful "no activity" response

**Defer to Phase 2:**
- Topic grouping and action item extraction (prompt engineering refinement once core loop works)
- DM delivery (low complexity but not core)
- `/unreadsummary` (requires tracking user's last message, adds complexity)
- Question-focused summaries (power-user feature)
- Thread output mode (config preference)
- Participant attribution (prompt complexity)
- Language configuration (single-server likely single-language)

## Feature Prioritization Matrix

| Feature | User Value | Effort | Priority |
|---------|-----------|--------|----------|
| On-demand `/summary` | Critical | Low | P0 - MVP |
| Message fetching + pagination | Critical | Medium | P0 - MVP |
| Pluggable LLM interface | Critical | Medium | P0 - MVP |
| Configurable time range | High | Low | P0 - MVP |
| Bullet-point embed output | High | Low | P0 - MVP |
| Scheduled overnight summary | High | Medium | P0 - MVP |
| Smart filtering (skip bots) | High | Low | P0 - MVP |
| Token/length management | High | Medium | P0 - MVP |
| Empty channel handling | Medium | Low | P0 - MVP |
| Multi-channel selection | Medium | Low | P1 - Soon after |
| Topic-grouped summaries | Medium | Medium | P1 - Soon after |
| Action items extraction | Medium | Medium | P1 - Soon after |
| DM delivery | Medium | Low | P1 - Soon after |
| Unread summary | Medium | Medium | P2 - Later |
| Question-focused summaries | Medium | Medium | P2 - Later |
| Thread output mode | Low | Low | P2 - Later |
| Participant attribution | Low | Medium | P2 - Later |
| Language configuration | Low | Low | P2 - Later |

## Sources

- [Summary Bot on top.gg](https://top.gg/bot/1058568749076185119) -- commands: /summary, /unreadsummary, /fromtosummary, /setlanguage, /setregion, /setthread
- [Wallubot documentation](https://docs.wallubot.com/blog/discord-conversation-summarizer) -- auto-detect timespan, question-focused queries, smart filtering
- [TLDRBot review](https://ai-productreviews.com/tldr-bot-review/) -- /tldr command, adjustable length, automatic intervals, $0.02/request pricing
- [elizaOS/discord-summarizer](https://github.com/elizaOS/discord-summarizer) -- action items categorization, FAQ extraction, local LLM processing
- [rauljordan/daily-discord-summarizer](https://github.com/rauljordan/daily-discord-summarizer) -- configurable digest intervals, message aggregation, HTTP API output
- [Discord native Summaries AI](https://support.discord.com/hc/en-us/articles/12926016807575-In-Channel-Conversation-Summaries) -- topic grouping, participant display, built-in feature
- [Optimum Web Discord AI Bot 2026](https://www.optimum-web.com/blog/discord-ai-bot-community-management-2026/) -- /summarize extracting key points, decisions, action items, unresolved questions
- [eesel.ai Discord AI bots ranking](https://www.eesel.ai/blog/discord-ai) -- ecosystem overview of 8 best bots
- [TLDRBot on top.gg](https://top.gg/bot/1079089748410376202) -- primary command and pricing details
