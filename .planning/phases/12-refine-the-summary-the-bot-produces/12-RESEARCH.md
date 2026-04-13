# Phase 12: Refine the Summary the Bot Produces - Research

**Researched:** 2026-04-13
**Domain:** LLM prompt engineering, Discord embed formatting, summary content structure
**Confidence:** HIGH

## Summary

This phase is a prompt engineering and formatting refinement effort -- no new features, no new libraries, no new commands. The work targets four files: `summarizer.py` (system prompts), `embeds.py` (footer stats and embed structure), `summarizer.py`/`summarize_channel()` (participant counting and volume metadata), and potentially `models.py` (if `to_line()` needs URL extraction changes). All decisions are well-defined in CONTEXT.md and map directly to specific code edits.

The main technical considerations are: (1) crafting a prompt that reliably produces headline-depth bullets without usernames and with inline URLs, (2) implementing volume-aware summarization that adapts detail level based on message count, and (3) ensuring the merge prompt (two-pass) produces output consistent with the single-pass prompt including the Announcements section for [IMPORTANT] messages. The existing codebase already has the signal markers ([IMPORTANT], [POPULAR]) flowing through the pipeline, so the work is primarily about telling the LLM how to use them differently.

**Primary recommendation:** Rewrite `SUMMARY_SYSTEM_PROMPT` and `MERGE_SYSTEM_PROMPT` to enforce the D-01 through D-13 decisions, add participant counting to `summarize_channel()`, extend `build_summary_embeds()` footer with stats, and inject volume context as a preamble before the message text sent to the LLM.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Summaries should be headline-depth -- topic name + 1-line takeaway per bullet. Users skim in 10 seconds, not read paragraphs.
- **D-02:** Neutral/clean tone -- clear English, no slang, no corporate jargon. Professional but not stiff.
- **D-03:** No usernames in summaries -- focus on what was discussed, not who said it. Keeps summaries impersonal and scannable.
- **D-04:** Include URLs inline when links were shared during the summarized period. Users should be able to click through from the summary.
- **D-05:** No TL;DR or key-takeaway section -- jump straight into topic-grouped bullets. Keep it minimal.
- **D-06:** Links appear inline within their topic bullets, not collected into a separate section.
- **D-07:** Drop minor topics entirely -- if a topic only had 1-2 messages with no engagement, skip it. Only include topics with meaningful discussion.
- **D-08:** Show message count and active participant count in the embed footer (e.g., "147 messages from 23 participants").
- **D-09:** [IMPORTANT] messages (@here/@everyone) get pulled into a separate "Announcements" section at the top of the summary, before topic bullets.
- **D-10:** [POPULAR] topics appear first in the topic list (ordered by engagement), but no special formatting or markers -- just ordering.
- **D-11:** One universal system prompt for all contexts (overnight, hourly, on-demand). No per-context prompt variants.
- **D-12:** Volume-aware summarization: the prompt (or pre-prompt logic) should adapt based on message count. Low volume = more detail per bullet. High volume = fewer topics shown + briefer bullets.
- **D-13:** No open-thread tracking -- summaries report what was said without noting whether discussions were resolved.

### Claude's Discretion
- Claude determines the specific volume thresholds for "low" vs. "high" message counts
- Claude decides how to implement volume-awareness (prompt injection vs. multiple prompt tiers)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| D-01 | Headline-depth bullets | Prompt rewrite with explicit format instructions |
| D-02 | Neutral/clean tone | Prompt tone directive |
| D-03 | No usernames in output | Prompt instruction to omit attribution |
| D-04 | Inline URLs from shared links | Prompt instruction to preserve and inline URLs |
| D-05 | No TL;DR section | Prompt negative instruction |
| D-06 | Links inline, not separate section | Prompt formatting instruction |
| D-07 | Drop minor topics (<3 messages, no engagement) | Prompt instruction with threshold guidance |
| D-08 | Message + participant count in footer | Code change in embeds.py + metadata from summarize_channel() |
| D-09 | Announcements section for [IMPORTANT] | Prompt structure instruction for dedicated section |
| D-10 | Popular topics ordered first | Prompt ordering instruction based on [POPULAR] markers |
| D-11 | One universal prompt | Single SUMMARY_SYSTEM_PROMPT, no branching |
| D-12 | Volume-aware summarization | Volume context preamble injected before messages |
| D-13 | No open-thread tracking | Prompt negative instruction |

</phase_requirements>

## Architecture Patterns

### Files to Modify

```
src/bot/
  summarizer.py          # SUMMARY_SYSTEM_PROMPT, MERGE_SYSTEM_PROMPT, summarize_channel()
  formatting/embeds.py   # build_summary_embeds() footer + _make_embed()
```

No new files needed. No new dependencies.

### Pattern 1: Volume-Aware Prompt Injection

**What:** Instead of multiple prompt tiers, inject a volume context line before the message text that tells the LLM how to calibrate detail. This keeps D-11 (one universal prompt) intact while satisfying D-12. [ASSUMED]

**When to use:** Every call to the LLM -- both single-pass and chunk-pass.

**Recommended thresholds:**
- Low volume: <= 30 messages -- more detail per bullet, include minor observations
- Medium volume: 31-150 messages -- standard headline-depth bullets
- High volume: > 150 messages -- only major topics, ultra-brief bullets

These thresholds are based on typical Discord server activity patterns where 30 messages represents a quiet period and 150+ represents a busy day. [ASSUMED]

**Example:**
```python
def _volume_context(message_count: int) -> str:
    """Generate volume-awareness preamble for the LLM."""
    if message_count <= 30:
        return (
            f"[Volume: {message_count} messages — LOW. "
            "Include more detail per topic. Up to 2 sentences per bullet is acceptable.]"
        )
    elif message_count <= 150:
        return (
            f"[Volume: {message_count} messages — MEDIUM. "
            "Standard headline-depth: 1 sentence per bullet.]"
        )
    else:
        return (
            f"[Volume: {message_count} messages — HIGH. "
            "Show only the most significant topics. Keep bullets to sentence fragments.]"
        )
```

This preamble gets prepended to the user message (the formatted message text), not added to the system prompt -- keeping the system prompt universal per D-11.

### Pattern 2: Participant Counting in summarize_channel()

**What:** Count unique authors from processed messages and pass that count alongside message count to embed building. [VERIFIED: codebase inspection]

**Current state:** `summarize_channel()` already iterates all processed messages and has access to `ProcessedMessage.author`. A simple `set()` comprehension extracts unique participants.

**Example:**
```python
participant_count = len({msg.author for msg in processed})
message_count = len(processed)
```

This metadata needs to flow from `summarize_channel()` through to `build_summary_embeds()`. Options:
1. Return a result dataclass instead of a bare string
2. Pass metadata separately alongside the summary text

Option 1 is cleaner -- create a small `SummaryResult` dataclass or namedtuple.

### Pattern 3: Embed Footer Stats (D-08)

**What:** Replace the current footer text with message/participant stats.

**Current footer in embeds.py:** `embed.set_footer(text=f"Period: {timerange_label}")` [VERIFIED: codebase inspection]

**Current footer in overnight.py:** Overrides with `embed.set_footer(text=f"Scheduled {label} summary")` [VERIFIED: codebase inspection]

Both need updating. The footer should combine period info with stats: `"147 messages from 23 participants | Last 4 hours"` or similar.

### Pattern 4: Prompt Structure for Announcements (D-09)

**What:** The system prompt must instruct the LLM to extract [IMPORTANT] messages into a top-level **Announcements** section before the topic bullets.

**Current behavior:** The existing prompt says to include [IMPORTANT] messages verbatim but doesn't specify a separate section. [VERIFIED: codebase inspection]

The prompt should specify:
1. If any [IMPORTANT] messages exist, create an **Announcements** section at the very top
2. Each announcement is the verbatim message text (not paraphrased)
3. After announcements, proceed with topic-grouped bullets

### Anti-Patterns to Avoid
- **Splitting the prompt into variants:** D-11 explicitly locks a single universal prompt. Volume awareness must come from injected context, not prompt branching.
- **Putting metadata in the system prompt:** Message count and volume context are per-invocation data. They belong in the user message, not the system prompt.
- **Relying on LLM for ordering:** The prompt says "popular first" (D-10), but LLMs are unreliable at sorting. The prompt instruction is sufficient since we already mark [POPULAR] -- the LLM just needs to list those topics before others.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| URL extraction | Regex to find URLs in messages | LLM prompt instruction to preserve inline URLs | URLs are already in the message text; the LLM just needs to not strip them |
| Topic ordering | Post-processing to reorder LLM output | Prompt instruction with [POPULAR] markers | Reordering LLM markdown output is fragile; prompt instructions with clear markers work well enough |
| Participant counting | Complex user tracking | `len({msg.author for msg in processed})` | Already have author on every ProcessedMessage |

## Common Pitfalls

### Pitfall 1: LLM Ignoring Negative Instructions
**What goes wrong:** Telling the LLM "do NOT include usernames" often fails -- LLMs are better at positive instructions than negative ones.
**Why it happens:** Attention mechanism gives weight to the concept even when negated.
**How to avoid:** Frame as positive: "Focus on what was discussed, not who said it. Refer to topics and ideas, never to individual users." Reinforce with "Output must contain zero usernames or @mentions."
**Warning signs:** Summaries still containing "User X mentioned..." or "@someone said..."

### Pitfall 2: Merge Prompt Losing Announcements Section
**What goes wrong:** In two-pass summarization, chunk summaries may each have their own Announcements section. The merge prompt needs to consolidate these into a single Announcements section at the top.
**Why it happens:** The merge prompt is a different prompt and may not preserve the structure from chunk summaries.
**How to avoid:** The MERGE_SYSTEM_PROMPT must explicitly say: "If any input summaries contain an **Announcements** section, consolidate all announcements into a single **Announcements** section at the top of the merged summary."
**Warning signs:** Announcements appearing as regular bullets or duplicated across the merged output.

### Pitfall 3: Volume Preamble Token Waste
**What goes wrong:** Adding verbose volume instructions to every chunk in two-pass mode wastes tokens.
**Why it happens:** Each chunk gets the volume preamble even though volume context is about the total conversation.
**How to avoid:** For two-pass, use total message count for the volume preamble (applied to all chunks), not per-chunk count. The volume level is a property of the overall conversation, not each time window.
**Warning signs:** Inconsistent detail levels between chunks of the same conversation.

### Pitfall 4: Footer Override in Overnight Scheduler
**What goes wrong:** The overnight scheduler currently overwrites the footer set by `build_summary_embeds()`. If embed building adds stats to the footer, the scheduler's override will erase them.
**Why it happens:** Line 115 in overnight.py: `embed.set_footer(text=f"Scheduled {label} summary")` [VERIFIED: codebase inspection]
**How to avoid:** Either remove the footer override in overnight.py and have `build_summary_embeds()` handle all footer content, or combine the scheduled label with stats in the override.
**Warning signs:** Scheduled summaries missing the message/participant stats that on-demand summaries show.

### Pitfall 5: Embed Character Limit with Announcements
**What goes wrong:** Adding an Announcements section increases summary length, potentially causing more embed splits.
**Why it happens:** Announcements are verbatim message text (potentially long) added on top of topic bullets.
**How to avoid:** The existing embed splitting logic at topic boundaries already handles this -- **Announcements** is a bold-header section so it splits correctly. No code change needed, but worth verifying.
**Warning signs:** Announcements section getting truncated or split mid-announcement.

## Code Examples

### Revised SUMMARY_SYSTEM_PROMPT (D-01 through D-13)

```python
SUMMARY_SYSTEM_PROMPT = (
    "You are a Discord channel summarizer. Given a conversation log, produce a concise "
    "summary organized by discussion topic.\n\n"
    "## Output Rules\n"
    "- Focus on WHAT was discussed, not WHO said it. Never include usernames, "
    "display names, or @mentions in the summary.\n"
    "- Each topic: bold header (**Topic Name**) followed by bullet points.\n"
    "- Each bullet: topic name + one-line takeaway. Headline depth only -- no paragraphs.\n"
    "- If any messages are marked [IMPORTANT], create an **Announcements** section at the "
    "very top (before all topic sections). List each announcement as a bullet with the "
    "verbatim message text.\n"
    "- Order remaining topics by engagement: topics with [POPULAR] markers appear first. "
    "Do not add any special formatting to popular topics -- just list them earlier.\n"
    "- Drop minor topics that had only 1-2 messages with no reactions or replies.\n"
    "- When messages contain URLs, include them inline in the relevant bullet. "
    "Never collect links into a separate section.\n"
    "- Do NOT include a TL;DR, key takeaways, or executive summary section.\n"
    "- Do NOT note whether discussions are resolved or ongoing.\n"
    "- Tone: clear, neutral English. No slang, no corporate jargon.\n\n"
    "## Input Signal Reference\n"
    "- [IMPORTANT]: @here/@everyone message -- MUST appear in Announcements section.\n"
    "- [POPULAR]: High-engagement message -- prioritize its topic.\n"
    "- [N reactions]: Community engagement level.\n"
    "- Indented > lines: Replies showing conversation flow.\n"
    "- [image/video/file: name]: Shared media -- mention briefly.\n"
    "- Parenthetical text: Embed content from links.\n"
)
```

### Revised MERGE_SYSTEM_PROMPT

```python
MERGE_SYSTEM_PROMPT = (
    "You are a Discord channel summarizer. Given multiple time-period summaries from "
    "the same channel, produce one unified summary organized by discussion topic.\n\n"
    "## Output Rules\n"
    "- If any input summaries contain an **Announcements** section, consolidate all "
    "announcements into a single **Announcements** section at the top.\n"
    "- Each topic: bold header (**Topic Name**) followed by headline-depth bullets.\n"
    "- Merge related topics and remove redundancy.\n"
    "- Order topics by engagement level (most-discussed first).\n"
    "- Never include usernames or @mentions.\n"
    "- Preserve all URLs inline within their topic bullets.\n"
    "- Do NOT include TL;DR, key takeaways, or resolution status.\n"
    "- Tone: clear, neutral English. No slang, no corporate jargon.\n"
)
```

### SummaryResult Dataclass

```python
@dataclass
class SummaryResult:
    text: str
    message_count: int
    participant_count: int
```

### Updated build_summary_embeds Signature

```python
def build_summary_embeds(
    summary_text: str,
    channel_name: str,
    timerange_label: str,
    message_count: int = 0,
    participant_count: int = 0,
) -> list[discord.Embed]:
```

Footer becomes: `f"{message_count} messages from {participant_count} participants | {timerange_label}"`

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Volume thresholds of 30/150 messages are good boundaries | Architecture Patterns | Summaries may be too detailed or too brief; thresholds are easy to adjust |
| A2 | Prompt injection (preamble) is better than multiple prompt tiers for volume awareness | Architecture Patterns | If prompt injection is unreliable, may need to switch to prompt tiers; low risk since single prompt is locked by D-11 |
| A3 | LLMs reliably order topics by engagement when given [POPULAR] markers | Architecture Patterns | Topics may appear in arbitrary order; acceptable since ordering is soft preference (D-10) |

## Open Questions

1. **Volume threshold calibration**
   - What we know: Thresholds need to exist but exact numbers are Claude's discretion
   - What's unclear: What typical message volumes look like in this specific server
   - Recommendation: Start with 30/150, make them configurable constants for easy tuning

2. **SummaryResult vs separate parameters**
   - What we know: Metadata (message_count, participant_count) needs to flow from summarize_channel to embeds
   - What's unclear: Whether the caller sites (summary.py command, overnight.py scheduler) should be updated to use a result object
   - Recommendation: Use a SummaryResult dataclass -- cleaner than adding parameters, and the calling code changes are minimal

## Project Constraints (from CLAUDE.md)

- **Stack:** Python 3.12+, discord.py 2.7.1, openai SDK, pydantic-settings
- **No databases:** JSON persistence only (not relevant to this phase)
- **Package manager:** uv
- **Linting:** ruff
- **Testing:** pytest + pytest-asyncio
- **No LiteLLM, LangChain, APScheduler, Pycord, Nextcord**
- **GSD workflow:** Must use GSD commands for file changes

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `src/bot/summarizer.py` -- current SUMMARY_SYSTEM_PROMPT, MERGE_SYSTEM_PROMPT, summarize_channel()
- Codebase inspection: `src/bot/formatting/embeds.py` -- current embed building and footer logic
- Codebase inspection: `src/bot/models.py` -- ProcessedMessage dataclass with to_line()
- Codebase inspection: `src/bot/scheduling/overnight.py` -- footer override on line 115
- Codebase inspection: `src/bot/commands/summary.py` -- on-demand summary flow
- Codebase inspection: `src/bot/pipeline/preprocessor.py` -- signal extraction (is_important, reaction_count)
- Codebase inspection: `src/bot/pipeline/chunker.py` -- format_chunk_for_llm()

### Secondary (MEDIUM confidence)
- LLM prompt engineering best practices for negative instructions [ASSUMED from training knowledge]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new libraries needed, pure code/prompt changes
- Architecture: HIGH - clear mapping from decisions to code locations, all files inspected
- Pitfalls: HIGH - identified from direct codebase inspection (footer override, two-pass merge)

**Research date:** 2026-04-13
**Valid until:** 2026-05-13 (stable -- no external dependency changes)
