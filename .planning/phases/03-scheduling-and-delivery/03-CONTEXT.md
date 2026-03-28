# Phase 3: Scheduling and Delivery - Context

**Gathered:** 2026-03-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Bot automatically posts overnight summaries (10pm-9am window) to the dedicated #summaries channel at 9am daily using `discord.ext.tasks`. Users can opt in to receive scheduled summaries via DM through a slash command toggle. Thread posting is available as an optional env var toggle. This phase does NOT change the on-demand `/summary` command behavior (stays ephemeral).

</domain>

<decisions>
## Implementation Decisions

### Scheduled Summary Scope
- **D-01:** Overnight summary covers all channels in `ALLOWED_CHANNEL_IDS` — same allowlist used for `/summary`. No separate scheduled channel list.
- **D-02:** All overnight summaries post to `SUMMARY_CHANNEL_ID` (already in config). One central place to catch up.
- **D-03:** Channels with no significant overnight activity (below quiet threshold) are skipped silently — no "no activity" posts.

### DM Delivery
- **D-04:** Users opt in via slash command toggle (e.g., `/summary-dm`). Self-service, no admin involvement.
- **D-05:** DM opt-in state persisted to a local JSON file — survives bot restarts without requiring a database.
- **D-06:** DMs fire for scheduled summaries only. On-demand `/summary` remains ephemeral (already private to the requesting user).
- **D-07:** DMs re-use the already-generated summary embeds — zero additional LLM calls.

### Thread Delivery
- **D-08:** Default posting mode is regular messages (not threads).
- **D-09:** Optional `USE_THREADS` env var toggle (default `false`). When enabled, creates a daily thread (e.g., "Overnight Summary — Mar 27") and posts channel summaries inside it. Satisfies OUT-04.

### Multi-Channel Overnight
- **D-10:** One embed per channel, posted sequentially in #summaries. Uses existing `build_summary_embeds()` format per channel.
- **D-11:** Channels summarized sequentially (one LLM call at a time). For a daily job, speed is not a concern and this respects rate limits.
- **D-12:** If one channel's summary fails, continue with remaining channels and include an error note: "Failed to summarize #channel: [reason]". No abort, no retry.

### Claude's Discretion
- Exact slash command name and parameters for DM opt-in toggle
- JSON file location and format for DM subscriber persistence
- Thread naming convention and auto-archive duration
- Scheduling implementation details (discord.ext.tasks.loop with time parameter)
- Embed differentiation between scheduled and on-demand summaries (e.g., different footer text)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Specs
- `.planning/PROJECT.md` — Project vision, constraints, key decisions
- `.planning/REQUIREMENTS.md` — Full requirements with traceability (Phase 3: SCHED-01, SCHED-02, OUT-03, OUT-04)
- `.planning/ROADMAP.md` — Phase goals and success criteria

### Technology
- `CLAUDE.md` — Technology stack decisions (discord.py 2.7.1, discord.ext.tasks for scheduling, zoneinfo for timezone)

### Prior Phase Context
- `.planning/phases/01-foundation-and-pipeline/01-CONTEXT.md` — Provider interface, error handling (D-10: ephemeral errors, D-11: no retry), summarization pipeline
- `.planning/phases/02-on-demand-summarization/02-CONTEXT.md` — Embed formatting, channel allowlist, quiet threshold, command registration pattern

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/bot/summarizer.py`: `summarize_channel()` — full pipeline (fetch -> preprocess -> summarize) takes channel, after, before params — maps directly to overnight window
- `src/bot/formatting/embeds.py`: `build_summary_embeds()` — handles topic-boundary splitting, reusable for scheduled summary embeds
- `src/bot/config.py`: `Settings` class — already has `timezone`, `summary_channel_id`, `allowed_channel_ids`, `quiet_threshold`, `max_context_tokens`
- `src/bot/client.py`: `SummaryBot` with `setup_hook` — registration point for scheduled task and new commands
- `src/bot/commands/summary.py`: `register_summary_command(bot)` — pattern to follow for DM toggle command

### Established Patterns
- pydantic-settings for all config (validated from .env)
- `register_X_command(bot)` for slash command registration in `setup_hook`
- `SummaryProvider` Protocol for provider abstraction
- Logging via `logging.getLogger(__name__)`
- Ephemeral error messages for user-facing failures

### Integration Points
- `discord.ext.tasks.loop(time=...)` with `zoneinfo.ZoneInfo(settings.timezone)` for 9am scheduling
- `SummaryBot.setup_hook()` — start the scheduled task loop here
- `bot.provider` attribute — already available for summarization calls
- `bot.settings.allowed_channel_ids` — iterate for overnight batch
- `bot.settings.summary_channel_id` — destination for scheduled posts

</code_context>

<specifics>
## Specific Ideas

- DM delivery re-uses the same embeds as the channel post — no separate generation
- JSON file for DM subscribers was chosen over env var or in-memory to balance simplicity with restart persistence
- Regular messages (not threads) as default keeps #summaries browsable without extra clicks; thread toggle is there for users who prefer it

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-scheduling-and-delivery*
*Context gathered: 2026-03-27*
