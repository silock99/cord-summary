# Phase 1: Foundation and Pipeline - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md -- this log preserves the alternatives considered.

**Date:** 2026-03-27
**Phase:** 01-foundation-and-pipeline
**Areas discussed:** Default LLM provider, Message preprocessing, Chunking strategy, Error handling UX

---

## Default LLM Provider

| Option | Description | Selected |
|--------|-------------|----------|
| OpenAI | OpenAI SDK with gpt-4o or similar. Most providers expose OpenAI-compatible endpoints. | Y |
| Anthropic (Claude) | Anthropic SDK with Claude. Strong summarization but fewer compatible endpoints. | |
| Both from the start | Ship both implementations in Phase 1. | |

**User's choice:** OpenAI (Recommended)
**Notes:** Doubles as universal fallback for Ollama, Azure, local endpoints.

### Default Model

| Option | Description | Selected |
|--------|-------------|----------|
| gpt-4o-mini | Cheap, fast, good enough for summarization. Override via env var. | Y |
| gpt-4o | Higher quality but more expensive. | |
| You decide | Claude picks a sensible default. | |

**User's choice:** gpt-4o-mini (Recommended)

### Custom Base URL Support

| Option | Description | Selected |
|--------|-------------|----------|
| Yes -- env var | OPENAI_BASE_URL env var for any compatible endpoint. | Y |
| No -- just OpenAI | Only support api.openai.com. | |

**User's choice:** Yes -- env var (Recommended)

---

## Message Preprocessing

### Discord Artifacts Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Strip to plain text | Convert mentions to names, strip embeds/attachments, remove reactions. | Y |
| Include metadata | Preserve attachment URLs, embed titles, reaction counts. | |
| You decide | Claude picks approach. | |

**User's choice:** Strip to plain text (Recommended)

### Bot/System Message Filtering

| Option | Description | Selected |
|--------|-------------|----------|
| Filter all bots + system | Remove bot and system messages entirely. | Y |
| Keep bot messages | Include bot messages in summary. | |
| Configurable filter | Env var to toggle bot inclusion. | |

**User's choice:** Filter bots, system messages and attachments. Keep link URLs since people discuss linked content, but original linked content (tweets, etc.) isn't necessary.

### Author Representation

| Option | Description | Selected |
|--------|-------------|----------|
| Display name | Server display name: "Alice: I think..." | Y |
| Username#discriminator | Discord username format. | |
| Anonymous | Strip author names entirely. | |

**User's choice:** Display name (Recommended)

---

## Chunking Strategy

### Chunk Method

| Option | Description | Selected |
|--------|-------------|----------|
| Token estimate | Estimate tokens per message, chunk at context limit. | |
| Fixed message count | Split every N messages. | |
| Time-based windows | Split by time periods (e.g., 1-hour windows). | Y |
| You decide | Claude picks approach. | |

**User's choice:** Time-based windows

### Chunk Merging

| Option | Description | Selected |
|--------|-------------|----------|
| Two-pass summarize | Summarize each chunk, then final LLM call merges. | Y |
| Concatenate summaries | Independent summaries concatenated with time headers. | |
| You decide | Claude picks approach. | |

**User's choice:** Two-pass summarize (Recommended)

---

## Error Handling UX

### Error Presentation

| Option | Description | Selected |
|--------|-------------|----------|
| Ephemeral error | Brief error only visible to command user. | Y |
| Error embed in channel | Visible error embed for admins. | |
| You decide | Claude picks approach. | |

**User's choice:** Ephemeral error (Recommended)

### Retry Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Retry once with backoff | One auto-retry after short delay. | |
| No retry -- fail immediately | Show error on first failure. User re-runs manually. | Y |
| You decide | Claude picks approach. | |

**User's choice:** No retry -- fail immediately

---

## Claude's Discretion

- Project structure and module organization
- Provider interface design (ABC vs Protocol)
- Token estimation approach for time window sizing
- Logging strategy

## Deferred Ideas

None -- discussion stayed within phase scope
