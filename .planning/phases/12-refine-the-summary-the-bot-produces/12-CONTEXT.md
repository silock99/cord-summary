# Phase 12: Refine the Summary the Bot Produces - Context

**Gathered:** 2026-04-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Improve the quality, structure, and usefulness of LLM-generated channel summaries by refining the system prompt, output format, and content prioritization logic. No new commands or features — this phase modifies how existing summaries look and read.

</domain>

<decisions>
## Implementation Decisions

### Summary Depth and Tone
- **D-01:** Summaries should be headline-depth — topic name + 1-line takeaway per bullet. Users skim in 10 seconds, not read paragraphs.
- **D-02:** Neutral/clean tone — clear English, no slang, no corporate jargon. Professional but not stiff.
- **D-03:** No usernames in summaries — focus on what was discussed, not who said it. Keeps summaries impersonal and scannable.
- **D-04:** Include URLs inline when links were shared during the summarized period. Users should be able to click through from the summary.

### Output Structure
- **D-05:** No TL;DR or key-takeaway section — jump straight into topic-grouped bullets. Keep it minimal.
- **D-06:** Links appear inline within their topic bullets, not collected into a separate section.
- **D-07:** Drop minor topics entirely — if a topic only had 1-2 messages with no engagement, skip it. Only include topics with meaningful discussion.
- **D-08:** Show message count and active participant count in the embed footer (e.g., "147 messages from 23 participants").

### Content Prioritization
- **D-09:** [IMPORTANT] messages (@here/@everyone) get pulled into a separate "Announcements" section at the top of the summary, before topic bullets.
- **D-10:** [POPULAR] topics appear first in the topic list (ordered by engagement), but no special formatting or markers — just ordering.

### Prompt Specialization
- **D-11:** One universal system prompt for all contexts (overnight, hourly, on-demand). No per-context prompt variants.
- **D-12:** Volume-aware summarization: the prompt (or pre-prompt logic) should adapt based on message count. Low volume = more detail per bullet. High volume = fewer topics shown + briefer bullets.
- **D-13:** No open-thread tracking — summaries report what was said without noting whether discussions were resolved.

### Claude's Discretion
- Claude determines the specific volume thresholds for "low" vs. "high" message counts
- Claude decides how to implement volume-awareness (prompt injection vs. multiple prompt tiers)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Summary Pipeline
- `src/bot/summarizer.py` — Orchestrator with SUMMARY_SYSTEM_PROMPT and MERGE_SYSTEM_PROMPT
- `src/bot/models.py` — ProcessedMessage dataclass with to_line() formatting
- `src/bot/pipeline/chunker.py` — Two-pass chunking and format_chunk_for_llm()
- `src/bot/pipeline/preprocessor.py` — Message preprocessing and signal extraction

### Formatting and Delivery
- `src/bot/formatting/embeds.py` — Embed building with topic-boundary splitting
- `src/bot/commands/summary.py` — On-demand /summary slash command
- `src/bot/scheduling/overnight.py` — Overnight and hourly scheduled summaries

### Language Controls
- `src/bot/language_filter.py` — Blocklist/allowlist guidelines appended to prompts

No external specs — requirements fully captured in decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SUMMARY_SYSTEM_PROMPT` in `summarizer.py` — the primary target for refinement
- `MERGE_SYSTEM_PROMPT` in `summarizer.py` — needs matching updates for two-pass consistency
- `build_summary_embeds()` in `embeds.py` — footer needs extending for message/participant stats
- `ProcessedMessage.to_line()` — already includes [IMPORTANT] and [POPULAR] markers

### Established Patterns
- System prompt is a module-level constant string concatenated with language guidelines at runtime
- Two-pass summarization: chunk summaries get the same prompt, then merge prompt combines them
- Embed splitting happens at topic boundaries (bold headers)

### Integration Points
- `summarize_channel()` computes reply counts and popularity flags — participant count can be computed here too
- `build_summary_embeds()` already has a footer (`set_footer`) — extend with stats metadata
- `format_chunk_for_llm()` formats messages for the LLM — no changes needed (input format stays the same)

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches for prompt refinement and structural changes.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 12-refine-the-summary-the-bot-produces*
*Context gathered: 2026-04-13*
