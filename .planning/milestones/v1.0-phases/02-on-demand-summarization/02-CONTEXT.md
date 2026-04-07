# Phase 2: On-Demand Summarization - Context

**Gathered:** 2026-03-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire the existing summarization pipeline into a working `/summary` slash command. Users get ephemeral (private) topic-grouped bullet-point summaries of recent channel activity. Admin controls which channels are summarizable via env var allowlist. No action items extraction. No public posting to a #summaries channel — that's Phase 3 (scheduled summaries only).

</domain>

<decisions>
## Implementation Decisions

### Slash Command UX
- **D-01:** Default time range is 4 hours when user doesn't specify one
- **D-02:** Time range presented as preset choices in a dropdown: 30 min, 1 hour, 4 hours, 12 hours, 24 hours
- **D-03:** Summary results are ephemeral — only visible to the user who triggered the command. No public posting to a #summaries channel for on-demand summaries (that's Phase 3 scheduled posting only)
- **D-04:** Defer the slash command immediately with an ephemeral "Generating summary..." message, then follow up with the ephemeral summary embed once ready

### Summary Formatting
- **D-05:** Summaries use bold topic headers with bullet points underneath (topic-grouped). No action items or decisions section — just topic summaries
- **D-06:** When summary exceeds Discord's 4096-char embed description limit, split into multiple embeds in the same response, breaking at topic boundaries
- **D-07:** The LLM system prompt should instruct for topic-grouped bullet points without action items extraction (update SUMMARY_SYSTEM_PROMPT from Phase 1)

### Channel Targeting
- **D-08:** Admin configures allowed channels via `ALLOWED_CHANNEL_IDS` env var (comma-separated channel IDs). Only these channels can be summarized
- **D-09:** Default behavior: summarize the current channel (if on the allowlist). Optional `channel` parameter to pick a different allowed channel
- **D-10:** If user runs /summary in a non-allowed channel (and doesn't specify a channel parameter), show ephemeral error listing the available channels: "This channel isn't enabled for summaries. Available channels: #general, #dev"

### Quiet Channel Handling
- **D-11:** Fewer than 5 human messages (after bot/system filtering) in the time range counts as "no significant activity"
- **D-12:** When below threshold, show a simple ephemeral message: "No significant activity in #channel-name in the last X hours." — no LLM call, no message quoting

### Scope Adjustments
- **D-13:** SUM-04 (action items extraction) is removed from this phase — summaries are topic-grouped bullets only
- **D-14:** OUT-01 (post to dedicated summary channel) moves to Phase 3 — on-demand summaries are ephemeral only

### Claude's Discretion
- Embed color, footer text, and metadata styling
- Exact wording of the "generating..." deferred message
- How to split long summaries at topic boundaries (algorithm for multi-embed splitting)
- Whether the channel dropdown in /summary shows all allowed channels or only ones the user can see

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Specs
- `.planning/PROJECT.md` — Project vision, constraints, key decisions
- `.planning/REQUIREMENTS.md` — Full requirements with traceability (Phase 2: SUM-01, SUM-02, SUM-03, SUM-05, PIPE-03, OUT-02)
- `.planning/ROADMAP.md` — Phase goals and success criteria

### Technology
- `CLAUDE.md` — Technology stack decisions (discord.py 2.7.1, openai SDK, pydantic-settings, uv)

### Phase 1 Context
- `.planning/phases/01-foundation-and-pipeline/01-CONTEXT.md` — Prior decisions (D-10: ephemeral errors, D-11: no retry, D-07: display names, D-09: two-pass summarization)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/bot/summarizer.py`: `summarize_channel()` — full pipeline (fetch -> preprocess -> summarize) ready to wire into the slash command
- `src/bot/summarizer.py`: `summarize_messages()` — handles single-pass and two-pass chunking automatically
- `src/bot/client.py`: `SummaryBot` class with `setup_hook` for command sync — add the /summary command tree here
- `src/bot/config.py`: `Settings` class — add `ALLOWED_CHANNEL_IDS` field here
- `src/bot/models.py`: `SummaryError` exception — already designed for user-facing error messages
- `src/bot/providers/openai_provider.py`: `OpenAISummaryProvider` — maps LLM errors to SummaryError

### Established Patterns
- pydantic-settings for all config (validated from .env)
- discord.py `commands.Bot` subclass with `setup_hook` for guild command sync
- `SummaryProvider` Protocol for provider abstraction
- Logging via `logging.getLogger(__name__)`

### Integration Points
- Slash command registers via `@discord.app_commands.command()` on the bot's command tree
- `SummaryBot.setup_hook()` already syncs commands to the configured guild
- `summarize_channel()` takes channel, guild, provider, after/before — maps directly to command parameters
- Provider instantiation needed in bot startup (Settings -> OpenAISummaryProvider)

</code_context>

<specifics>
## Specific Ideas

- On-demand summaries are private (ephemeral) — the dedicated #summaries channel is reserved for Phase 3's automated scheduled posts only
- Admin controls which channels are summarizable, not individual users — single env var allowlist
- When user is in an allowed channel, it should "just work" without extra clicks (default to current channel)

</specifics>

<deferred>
## Deferred Ideas

- OUT-01 (dedicated summary channel posting) — deferred to Phase 3 for scheduled summaries
- SUM-04 (action items extraction) — removed from v1 scope per user decision

</deferred>

---

*Phase: 02-on-demand-summarization*
*Context gathered: 2026-03-27*
