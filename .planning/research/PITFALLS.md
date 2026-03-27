# Domain Pitfalls

**Domain:** Discord bot with LLM-powered channel summarization
**Researched:** 2026-03-27

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: Message Content Intent Not Enabled

**What goes wrong:** The bot connects to Discord but `channel.history()` returns messages with empty `content` fields. Summaries come back blank or nonsensical. Everything looks like it works until you actually read the output.

**Why it happens:** Since September 2022, `message_content` is a Privileged Intent. Without enabling it in both the Developer Portal AND in code (`intents.message_content = True`), the bot receives message objects but the `content`, `embeds`, `attachments`, and `components` fields are empty. Developers test locally, see it working (because they have the intent toggled on in the portal from a previous project), and forget to document or verify it.

**How to avoid:**
- Enable Message Content Intent in the Discord Developer Portal under Bot settings
- Explicitly set `intents.message_content = True` in code
- Add a startup check that fetches one recent message and asserts `content` is non-empty
- Document this as a setup requirement in the README

**Warning signs:** Summaries are empty or say "no messages found" when the channel clearly has activity. LLM returns generic responses because it received no actual content.

**Phase to address:** Phase 1 (initial bot setup). This is a day-one configuration issue.

**Confidence:** HIGH -- well-documented in discord.py docs and Discord Developer Portal.

---

### Pitfall 2: Token Limit Overflow on Busy Channels

**What goes wrong:** A busy channel generates 500-3000 messages overnight. Naively concatenating all messages and sending them to an LLM exceeds the context window, causing API errors, truncated summaries that miss the second half of the night, or massive API bills.

**Why it happens:** Developers build with quiet test channels (20-50 messages) and never test with realistic volume. An overnight window (10pm-9am, 11 hours) in an active server can easily produce thousands of messages. At ~15-30 tokens per message (username + content), 2000 messages = 30,000-60,000 tokens of input alone.

**How to avoid:**
- Implement a chunking strategy from the start: split messages into groups that fit within ~70% of the model's context window (leaving room for system prompt + output)
- Use a map-reduce approach: summarize each chunk, then summarize the summaries
- Count tokens before sending (use tiktoken for OpenAI, or a simple word-count heuristic as ~1.3 tokens per word)
- Set a hard cap on messages processed (e.g., 2000 messages max) with a user-facing note when truncated

**Warning signs:** LLM API returns 400 errors about context length. Summaries suspiciously only cover early-evening topics but never late-night ones. API costs spike unexpectedly.

**Phase to address:** Phase 1/2 (core summarization logic). This must be designed into the summarization pipeline from the start, not bolted on later.

**Confidence:** HIGH -- fundamental LLM integration constraint. Sources: [Deepchecks: 5 Approaches to Solve LLM Token Limits](https://www.deepchecks.com/5-approaches-to-solve-llm-token-limits/), [Agenta: Top Techniques to Manage Context Length](https://agenta.ai/blog/top-6-techniques-to-manage-context-length-in-llms).

---

### Pitfall 3: Silent Embed Truncation

**What goes wrong:** Discord silently truncates embed descriptions that exceed 4096 characters (or 6000 total across all embed fields). The summary gets cut off mid-sentence with no error raised. The bot appears to work but users get incomplete summaries.

**Why it happens:** The Discord API does not return an error when embed content is too long -- it just truncates. Developers send the LLM response directly into an embed without checking length. The 6000-character total limit applies across ALL fields in ALL embeds in a single message, which is a non-obvious constraint.

**How to avoid:**
- Always validate summary length before sending
- If the summary exceeds 4000 characters (leave margin), split into multiple embeds or multiple messages
- Instruct the LLM to keep summaries concise (set `max_tokens` and include length constraints in the prompt)
- Implement a `split_embed()` utility that breaks content at logical points (paragraph/bullet boundaries, not mid-word)

**Warning signs:** Summaries end abruptly. Users report "the summary seems incomplete." No errors in bot logs.

**Phase to address:** Phase 1 (message sending logic). Build the embed splitter as a utility from day one.

**Confidence:** HIGH -- documented Discord API limit. Source: [Discord Embed Limits](https://www.pythondiscord.com/pages/guides/python-guides/discord-embed-limits/).

---

### Pitfall 4: Slash Command Sync Confusion

**What goes wrong:** Developer registers slash commands but they never appear in Discord. Or old commands persist after being removed from code. Or commands work in the test server but not in production.

**Why it happens:** discord.py requires explicit `CommandTree.sync()` calls to register slash commands with Discord. Global commands can take up to an hour to propagate. Guild-specific commands are instant but scoped. Developers often call `sync()` on every startup (which hits rate limits) or never call it (commands never appear). The bot must also be invited with the `applications.commands` scope.

**How to avoid:**
- Use guild-specific sync during development (instant), global sync for production
- Create a manual sync command (owner-only) rather than syncing on every `on_ready`
- Verify the bot invite URL includes the `applications.commands` scope
- Never sync in `on_ready` without a guard (it fires on reconnects too, causing redundant syncs)

**Warning signs:** Commands don't appear in Discord's slash command autocomplete. "This interaction failed" errors. Commands appear in one server but not another.

**Phase to address:** Phase 1 (bot scaffolding). Get sync right from the start.

**Confidence:** HIGH -- extensively documented issue. Source: [discord.py slash command guide](https://gist.github.com/AbstractUmbra/a9c188797ae194e592efe05fa129c57f).

---

### Pitfall 5: Timezone and DST Scheduling Bugs

**What goes wrong:** The 9am daily summary fires at the wrong time, fires twice, or skips entirely when daylight saving time transitions occur. During spring-forward, 2:00-2:59 AM doesn't exist; during fall-back, 1:00-1:59 AM happens twice.

**Why it happens:** Developers use naive datetime objects or pytz (deprecated since Python 3.9) instead of `zoneinfo`. APScheduler's cron trigger with DST-observing timezones can cause jobs to execute unexpectedly during transitions. The 10pm-9am overnight window spans midnight, adding another edge case.

**How to avoid:**
- Use `zoneinfo` (stdlib since Python 3.9), not pytz
- Store the configured timezone as a string, create `ZoneInfo` objects at runtime
- For APScheduler, be aware that DST transitions can cause missed or double firings -- the 9am trigger is safe (DST transitions typically happen at 2am) but document the assumption
- Store all internal timestamps in UTC; convert to local time only for display and scheduling
- Use discord.py's built-in `tasks.loop` with `time=` parameter as an alternative to APScheduler for simple daily schedules

**Warning signs:** Summary posted at 8am or 10am after a clock change. Two summaries posted on the same day. Summary never fires after a deployment that happened near a DST boundary.

**Phase to address:** Phase 2 (scheduling). Decide on scheduling approach early and test with mocked time.

**Confidence:** HIGH -- well-known scheduling issue. Source: [APScheduler timezone issue #315](https://github.com/agronholm/apscheduler/issues/315).

---

## Moderate Pitfalls

### Pitfall 6: Rate Limiting During Message Fetching

**What goes wrong:** Fetching history from a busy channel requires pagination (100 messages per API call). For 2000 messages, that is 20 sequential API requests. If the bot also fetches from multiple channels, it can hit Discord's rate limits (50 requests/second global, but per-route limits are lower), causing 429 errors and slow or failed summary generation.

**Prevention:**
- Use `channel.history(limit=N)` which handles pagination internally in discord.py, but set reasonable limits
- Fetch channels sequentially, not in parallel
- Add a configurable message limit per channel (e.g., 1500 messages max)
- Log when rate limits are hit so you can tune the limits
- discord.py handles 429s with automatic retry, but high-volume fetches can still cause delays of 30-60 seconds

**Phase to address:** Phase 1 (message fetching). Design with limits from the start.

**Confidence:** HIGH -- documented in Discord API rate limit docs.

---

### Pitfall 7: LLM API Costs Spiraling Uncontrolled

**What goes wrong:** Each overnight summary processes thousands of messages through an LLM. Without cost controls, a busy server could cost $1-5 per summary (depending on model and message volume), adding up to $30-150/month for a single bot in a single server.

**Prevention:**
- Count tokens before sending and log the count
- Set `max_tokens` on output to prevent verbose responses
- Use a cheaper model for summarization (GPT-4o-mini, Claude Haiku) -- summarization doesn't need the most powerful model
- Implement a message cap and inform users when it's hit
- Cache summaries so repeated requests for the same time window don't re-invoke the LLM
- Add per-day and per-month cost tracking with alerts

**Phase to address:** Phase 2 (after basic summarization works). But design the interface to accept cost parameters from the start.

**Confidence:** MEDIUM -- cost varies heavily by provider and usage. Source: [LLM Cost Optimization Guide](https://blog.premai.io/llm-cost-optimization-8-strategies-that-cut-api-spend-by-80-2026-guide/).

---

### Pitfall 8: Noise in Summaries (Bot Messages, Reactions, Low-Quality Content)

**What goes wrong:** The summary includes bot command outputs, automated messages, emoji-only messages, "lol" and "same" one-word replies, and other noise. The resulting summary is cluttered and unhelpful.

**Prevention:**
- Filter out bot messages (`message.author.bot`)
- Filter out system messages (joins, boosts, pins)
- Filter messages shorter than a threshold (e.g., under 5 characters)
- Consider filtering messages that are purely emoji or URLs with no commentary
- Include filtering rules in the prompt: "Ignore trivial messages, focus on substantive discussion"

**Phase to address:** Phase 1 (message fetching/preprocessing). Build the filter pipeline before connecting to the LLM.

**Confidence:** HIGH -- directly mentioned in summarization project post-mortems. Source: [Alibaba: How to Run a Local LLM That Summarizes Discord](https://www.alibaba.com/product-insights/how-to-run-a-local-llm-that-summarizes-discord-server-threads-respecting-privacy-ignoring-bots-highlighting-actionable-decisions.html).

---

### Pitfall 9: Slash Command Interaction Timeout (3-Second Rule)

**What goes wrong:** Discord requires an initial response to a slash command within 3 seconds. LLM summarization takes 5-30 seconds. The interaction expires, the user sees "This interaction failed," and then the bot posts the summary as a regular message that looks disconnected.

**Prevention:**
- Use `interaction.response.defer()` immediately upon receiving the command -- this buys you 15 minutes to send a followup
- Show a "Generating summary..." deferred response, then edit it with the actual summary via `interaction.followup.send()`
- Never do any I/O (message fetching, LLM calls) before deferring

**Phase to address:** Phase 1 (slash command handler). This is the first thing the command handler should do.

**Confidence:** HIGH -- fundamental Discord interaction constraint.

---

## Minor Pitfalls

### Pitfall 10: `on_ready` Fires Multiple Times

**What goes wrong:** Code in `on_ready` (like scheduling setup or command sync) runs multiple times because `on_ready` fires on every reconnect, not just initial startup.

**Prevention:** Use a boolean flag (`self.synced = False`) and check it in `on_ready`. Or use `setup_hook()` which runs exactly once.

**Phase to address:** Phase 1 (bot lifecycle).

---

### Pitfall 11: No Graceful Error Handling for LLM API Failures

**What goes wrong:** The LLM API is down or returns an error, and the scheduled summary silently fails. Nobody notices until someone asks "where's the morning summary?"

**Prevention:**
- Wrap all LLM calls in try/except with retry logic (exponential backoff, max 3 retries)
- On final failure, post a message to the summary channel: "Summary generation failed. Will retry in 15 minutes."
- Log all failures with enough context to debug

**Phase to address:** Phase 2 (robustness).

---

### Pitfall 12: No Message History When Bot Joins After Activity

**What goes wrong:** The bot can only read messages that exist in the channel history. If the channel was created or messages were sent before the bot had the Read Message History permission, those messages may not be accessible. Also, deleted messages won't appear in history.

**Prevention:**
- Document this limitation for users
- Handle the case where `channel.history()` returns fewer messages than expected
- Don't assume message count = time coverage

**Phase to address:** Phase 1 (documentation and edge case handling).

---

## Technical Debt Patterns

| Pattern | How It Starts | How It Hurts | Prevention |
|---------|--------------|--------------|------------|
| Hardcoded LLM prompts | "Just get it working" | Can't tune summary quality without code changes | Store prompts in config/env from day one |
| No message preprocessing | Send raw messages to LLM | Wasted tokens on noise, poor summaries | Build a filter/transform pipeline before LLM integration |
| Monolithic bot file | Single `bot.py` with everything | Can't test summarization logic independently | Separate into: bot layer, message fetcher, summarizer, formatter |
| No token counting | "The model handles it" | Silent truncation or 400 errors in production | Count tokens before every LLM call |

## Integration Gotchas

| Integration Point | Gotcha | Mitigation |
|-------------------|--------|------------|
| Discord API + Message History | `channel.history(after=datetime)` requires UTC-aware datetime. Naive datetimes silently misbehave. | Always pass `datetime.datetime.now(datetime.timezone.utc)` or use `discord.utils.utcnow()` |
| Discord API + Embeds | Embed field values cannot be empty strings. Sending `value=""` raises HTTPException. | Always validate embed fields are non-empty before sending |
| LLM API + Streaming | Streaming responses need different handling than complete responses. Switching later requires refactoring. | Design the summarizer interface to return complete text; add streaming later if needed |
| APScheduler + discord.py event loop | APScheduler's AsyncIOScheduler must share the same event loop as discord.py. Starting it before `bot.run()` or in a separate thread causes errors. | Start scheduler inside `setup_hook()` or `on_ready` (with guard). Or prefer discord.py's `tasks.loop`. |
| discord.py + Python 3.12+ | Some older discord.py versions had compatibility issues with Python 3.12. | Use discord.py >= 2.3.0 with Python 3.11 or 3.12. Check compatibility before picking versions. |

## Performance Traps

| Trap | Impact | Solution |
|------|--------|---------|
| Fetching all messages into memory at once | Memory spike on busy channels (2000+ messages = significant memory) | Use async iteration with `channel.history()` and process in batches |
| Not setting LLM `max_tokens` | Model generates 2000-token summaries when 500 tokens suffice | Set `max_tokens=800` and instruct the model to be concise |
| Synchronous LLM calls blocking the bot | Bot stops responding to commands while generating a summary | Use `asyncio`-compatible HTTP client (aiohttp/httpx) for LLM API calls; never use blocking `requests` |
| Re-summarizing the same time window | User runs `/summary` twice for the same period, doubling LLM costs | Cache summaries keyed by (channel_id, start_time, end_time) with a short TTL |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Bot token in source code | Token leaked via git = bot hijacked | Use `.env` file + `python-dotenv`, add `.env` to `.gitignore` immediately |
| LLM API key in source code | Same as above but for LLM provider | Same: `.env` file, never commit secrets |
| Sending private channel messages to LLM API | User messages leave your infrastructure, potential privacy violation | Document which channels are summarized; consider a channel allowlist in config |
| No input sanitization in summaries | Malicious users craft messages that inject instructions into the LLM prompt | Wrap user messages in clear delimiters in the prompt; don't let message content break out of the "messages to summarize" section |
| Logging full message content | Debug logs contain private user conversations | Log message IDs and metadata only; never log full message content in production |

## "Looks Done But Isn't" Checklist

These items are commonly skipped during development but cause problems in real usage:

- [ ] **Empty channel handling** -- What happens when the overnight window has zero messages? (Should post "No activity" rather than sending empty input to the LLM)
- [ ] **Single message handling** -- What if there's only 1 message? (Don't waste an LLM call; just repost it)
- [ ] **Summary of summaries** -- If the bot's own summary messages are in the channel, does it summarize its own summaries on the next run? (Filter by bot author ID)
- [ ] **Long messages** -- A single message can be up to 2000 characters. Ten long messages = 20K characters before you even think about token limits.
- [ ] **Threads and forums** -- Does `channel.history()` include thread messages? (No -- threads are separate. Decide if you want to summarize them.)
- [ ] **Message edits** -- `channel.history()` returns the latest version. Edited messages are fine, but deleted messages are gone.
- [ ] **Attachments and images** -- Messages with only images and no text appear as empty content. Filter or note them.
- [ ] **Mentions and formatting** -- Raw messages contain `<@123456789>` for mentions and `<#channel_id>` for channels. These are meaningless in a summary. Resolve them to display names.
- [ ] **Connection loss recovery** -- If the bot disconnects and reconnects, does the scheduler still fire? Does it double-fire?
- [ ] **Overnight window edge case** -- 10pm-9am spans two calendar days. The `after` and `before` parameters in `channel.history()` must account for this correctly.
- [ ] **DM summary delivery** -- Discord rate-limits DMs aggressively. If many users request DM delivery, the bot will hit rate limits. Queue and stagger DM sends.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Bot scaffolding | Message Content Intent not enabled | Startup self-test that verifies message content is accessible |
| Slash commands | Sync issues, 3-second timeout | Defer immediately, use guild sync for dev |
| Message fetching | Rate limits, UTC datetime confusion | Use `discord.utils.utcnow()`, set reasonable limits |
| LLM integration | Token overflow, no error handling | Chunking strategy, retry logic, token counting |
| Prompt engineering | Noisy summaries, inconsistent format | Message preprocessing, structured prompts with examples |
| Scheduling | DST bugs, double-firing on reconnect | Use `zoneinfo`, guard `on_ready`, prefer `tasks.loop` |
| Embed formatting | Silent truncation, empty fields | Validate length, split utility, test with long output |
| Cost management | Uncontrolled API spending | Token counting, model selection, caching |

## Sources

- [Discord Developer Portal: Message Content Privileged Intent FAQ](https://support-dev.discord.com/hc/en-us/articles/4404772028055-Message-Content-Privileged-Intent-FAQ)
- [discord.py Intents Primer](https://discordpy.readthedocs.io/en/latest/intents.html)
- [discord.py Slash Command Guide (AbstractUmbra)](https://gist.github.com/AbstractUmbra/a9c188797ae194e592efe05fa129c57f)
- [Discord API Rate Limits](https://discord.com/developers/docs/topics/rate-limits)
- [Python Discord: Embed Limits](https://www.pythondiscord.com/pages/guides/python-guides/discord-embed-limits/)
- [APScheduler Timezone Issue](https://github.com/agronholm/apscheduler/issues/315)
- [Deepchecks: 5 Approaches to Solve LLM Token Limits](https://www.deepchecks.com/5-approaches-to-solve-llm-token-limits/)
- [LLM Cost Optimization Guide](https://blog.premai.io/llm-cost-optimization-8-strategies-that-cut-api-spend-by-80-2026-guide/)
- [discord.py Rate Limit Issue #5806](https://github.com/Rapptz/discord.py/issues/5806)
