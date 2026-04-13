# Phase 12: Refine the Summary the Bot Produces - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-13
**Phase:** 12-refine-the-summary-the-bot-produces
**Areas discussed:** Summary depth and tone, Output structure, Content prioritization, Prompt specialization

---

## Summary Depth and Tone

| Option | Description | Selected |
|--------|-------------|----------|
| Headlines only | Just the topic and 1-line takeaway per bullet — skim in 10 seconds | ✓ |
| Key context included | Topic + enough detail to understand what happened without reading the original messages | |
| Comprehensive | Detailed recap with specifics (names, links, decisions made) — almost a transcript substitute | |

**User's choice:** Headlines only
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Casual/Discord-native | Matches how people actually talk in Discord — informal, may use slang or shorthand | |
| Neutral/clean | Professional but not stiff — clear English, no slang, no corporate jargon | ✓ |
| You decide | Claude picks the best tone for this bot's context | |

**User's choice:** Neutral/clean
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Include usernames | Attribute key points to the person who said them | |
| No usernames | Focus on what was discussed, not who said it | ✓ |
| Only for important | Name people only for [IMPORTANT] or [POPULAR] messages, anonymous otherwise | |

**User's choice:** No usernames
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Mention they exist | e.g., 'A highlight video was shared' — no URLs in summary | |
| Include the URLs | Embed the actual links so readers can click through from the summary | ✓ |
| You decide | Claude picks based on context | |

**User's choice:** Include the URLs
**Notes:** None

---

## Output Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, add a TL;DR | 1-2 sentence overview at the very top, then topic bullets below | |
| No, topics only | Jump straight into topic-grouped bullets — keep it minimal | ✓ |
| You decide | Claude decides based on message volume | |

**User's choice:** No, topics only
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, separate section | Dedicated section at the bottom listing all shared URLs with brief labels | |
| Inline only | Links appear within their topic bullets, no separate collection | ✓ |
| You decide | Claude picks the best approach | |

**User's choice:** Inline only
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Group into 'Also mentioned' | Low-activity topics become a single line: 'Also mentioned: X, Y, Z' | |
| Every topic gets a section | Even 1-message topics get their own bold header and bullet | |
| Drop minor topics | Only include topics with meaningful discussion — skip single-message mentions entirely | ✓ |

**User's choice:** Drop minor topics
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, in footer | Show message count and active participant count in the embed footer | ✓ |
| No stats | Keep the embed clean — just the summary content and time period | |
| You decide | Claude picks what makes sense | |

**User's choice:** Yes, in footer
**Notes:** None

---

## Content Prioritization

| Option | Description | Selected |
|--------|-------------|----------|
| Verbatim, inline | Keep current behavior — include the exact text within whatever topic it belongs to | |
| Highlighted in topic | Still within topics, but visually called out | |
| Separate section at top | Pull all @here/@everyone messages into their own 'Announcements' section before topics | ✓ |

**User's choice:** Separate section at top
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Just prioritize ordering | Popular topics appear first in the summary, but no special formatting | ✓ |
| Mark them visually | Popular items get a marker or emphasis within the bullet list | |
| You decide | Claude handles popular content however fits best | |

**User's choice:** Just prioritize ordering
**Notes:** None

---

## Prompt Specialization

| Option | Description | Selected |
|--------|-------------|----------|
| Different prompts per context | Overnight gets a broader framing; hourly gets a quick update; on-demand is neutral | |
| One prompt for all | Keep a single refined prompt — simpler to maintain, consistent output | ✓ |
| You decide | Claude picks based on what improves quality most | |

**User's choice:** One prompt for all
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, volume-aware | Low-volume: more detail per message. High-volume: more aggressive filtering and brevity | ✓ |
| No, fixed behavior | Same summarization approach regardless of how many messages | |
| You decide | Claude picks the best approach | |

**User's choice:** Yes, volume-aware
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Detail level only | Low volume: include more context per bullet. High volume: headlines only, drop minor topics more aggressively | |
| Detail + topic count | Also limit the number of topics shown at high volume — surface only the top N most active discussions | ✓ |
| You decide | Claude determines the best adaptation strategy | |

**User's choice:** Detail + topic count
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, flag open threads | If a discussion had no conclusion, note it | |
| No, just summarize | Report what was said without tracking resolution status | ✓ |
| You decide | Claude picks what makes sense | |

**User's choice:** No, just summarize
**Notes:** None

---

## Claude's Discretion

- Volume thresholds for low vs. high message counts
- Implementation strategy for volume-awareness (prompt injection vs. multiple prompt tiers)

## Deferred Ideas

None — discussion stayed within phase scope.
