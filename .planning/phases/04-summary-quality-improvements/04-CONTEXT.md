# Phase 4: Summary Quality Improvements - Context

**Gathered:** 2026-04-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Improve summary accuracy and richness by enriching the data fed to the LLM (reply chains, reactions, @here mentions, attachment metadata, embed content) and tuning the system prompts to leverage these new signals. No new slash commands, no scheduling changes, no UI changes. The existing `/summary` and overnight scheduler continue to work — they just produce better summaries.

</domain>

<decisions>
## Implementation Decisions

### Reply/Thread Context
- **D-01:** Reply chains are formatted with thread-style indentation in the LLM input. Direct replies show indented under their parent message, giving the LLM conversational structure. Nesting depth is at Claude's discretion.
- **D-02:** Skip Discord thread channels entirely — only summarize top-level channel messages. Thread participants already have context.
- **D-03:** Messages containing @here or @everyone mentions are flagged as high-importance and the LLM must include them verbatim in the summary output.
- **D-04:** "Popular" messages are those with 5+ total reactions OR 5+ replies. These are marked as important in the LLM input.

### Enriched Metadata
- **D-05:** Attachments represented as `[type: filename]` format (e.g., `[image: screenshot.png]`, `[file: report.pdf]`) instead of bare `[attachment]`. Gives the LLM context about what was shared.
- **D-06:** Reaction counts shown as total count only (e.g., `[12 reactions]`) on popular messages (5+ reactions). Non-popular messages show no reaction info.
- **D-07:** Discord embed content (title + description) extracted from user messages only. Consistent with Phase 1 D-05 (bot messages filtered). Captures link preview text, YouTube titles, etc.
- **D-08:** Pinned messages are NOT treated differently. No special handling or flagging.

### System Prompt Tuning
- **D-09:** System prompts remain code-managed (hardcoded in `summarizer.py`). No env var customization. Changes require a code update.
- **D-10:** Improved prompts include explicit instructions for new signals: "@here messages must be included verbatim", "Messages marked [POPULAR] are high-importance", "Reply indentation shows conversation flow". LLM should not have to infer what the markers mean.

### Model Selection
- **D-11:** Single model for both on-demand and scheduled summaries. No split config. Existing `openai_model` / `anthropic_model` settings apply everywhere.
- **D-12:** Single provider for both on-demand and scheduled summaries. No split config. Existing `llm_provider` setting applies everywhere.

### Claude's Discretion
- Reply chain nesting depth (how deep to indent before flattening)
- Exact format of the enriched LLM input (markers, delimiters, ordering)
- How to count replies to a message for the popularity threshold
- Embed extraction logic (which embed fields to include beyond title/description)
- Updated SUMMARY_SYSTEM_PROMPT and MERGE_SYSTEM_PROMPT wording

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Specs
- `.planning/PROJECT.md` — Project vision, constraints, key decisions
- `.planning/REQUIREMENTS.md` — Full requirements with traceability
- `.planning/ROADMAP.md` — Phase goals and success criteria

### Technology
- `CLAUDE.md` — Technology stack decisions (discord.py 2.7.1, openai SDK, pydantic-settings)

### Prior Phase Context
- `.planning/phases/01-foundation-and-pipeline/01-CONTEXT.md` — Preprocessing decisions (D-04: mention resolution, D-05: bot filtering, D-06: links preserved, D-07: display names, D-09: two-pass chunking)
- `.planning/phases/02-on-demand-summarization/02-CONTEXT.md` — Summary formatting (D-05: topic-grouped bullets, D-06: embed splitting, D-13: no action items)
- `.planning/phases/03-scheduling-and-delivery/03-CONTEXT.md` — Scheduler and delivery decisions (D-01: overnight uses same allowlist, D-03: skip quiet channels)

### Key Source Files
- `src/bot/pipeline/preprocessor.py` — Current preprocessing logic (the primary file being enhanced)
- `src/bot/summarizer.py` — System prompts and summarization orchestrator
- `src/bot/models.py` — ProcessedMessage dataclass (needs new fields)
- `src/bot/pipeline/fetcher.py` — Message fetching (may need reply reference data)
- `src/bot/pipeline/chunker.py` — Time-window chunking and token estimation
- `src/bot/formatting/embeds.py` — Embed building for Discord output
- `src/bot/config.py` — Settings class

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/bot/pipeline/preprocessor.py`: `preprocess_message()` — the primary function to enhance with reply context, reaction counts, embed extraction, attachment metadata
- `src/bot/summarizer.py`: `SUMMARY_SYSTEM_PROMPT` and `MERGE_SYSTEM_PROMPT` — static strings to update with explicit instructions for new signals
- `src/bot/models.py`: `ProcessedMessage` dataclass — needs new fields for reply info, reaction count, importance flags, embed content
- `src/bot/pipeline/chunker.py`: `format_chunk_for_llm()` — formats messages for LLM input, needs to incorporate new metadata and indentation

### Established Patterns
- pydantic-settings for all config (validated from .env)
- `ProcessedMessage.to_line()` for LLM formatting — simple `author: content` format
- `SummaryProvider.summarize(text, prompt)` — prompt passed at call time, easy to update
- Two-pass summarization: chunk summaries + merge pass

### Integration Points
- `preprocess_message()` receives raw `discord.Message` which has `.reference` (reply), `.reactions`, `.mentions`, `.embeds`, `.attachments` — all data available
- `format_chunk_for_llm()` builds the text sent to the LLM — needs to handle indentation and markers
- `summarize_messages()` and `summarize_channel()` — orchestrators that wire everything together

</code_context>

<specifics>
## Specific Ideas

- @here/@everyone messages must appear verbatim in the summary — this is a hard requirement, not a suggestion to the LLM
- Reaction counts are a "popularity" signal only — no emoji breakdown, just total count on messages crossing the 5+ threshold
- Reply chain indentation gives the LLM conversation structure it currently lacks — flat messages lose "who was responding to what"
- Embed extraction is limited to user messages only, consistent with existing bot message filtering

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-summary-quality-improvements*
*Context gathered: 2026-04-03*
