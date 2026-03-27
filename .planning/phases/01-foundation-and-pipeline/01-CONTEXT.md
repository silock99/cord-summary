# Phase 1: Foundation and Pipeline - Context

**Gathered:** 2026-03-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Bot connects to Discord with proper intents, registers slash commands, fetches and preprocesses channel messages with pagination, and produces summaries through a pluggable AI backend with at least one concrete provider (OpenAI). This phase delivers the complete pipeline from Discord messages to AI-generated summary text — but not the user-facing `/summary` command UX or formatted output (Phase 2).

</domain>

<decisions>
## Implementation Decisions

### Default LLM Provider
- **D-01:** OpenAI SDK as the first concrete provider implementation. The pluggable interface should be provider-agnostic (ABC/Protocol), with OpenAI as the shipped implementation.
- **D-02:** Default model is `gpt-4o-mini` — cheap, fast, sufficient for summarization. Configurable via env var.
- **D-03:** Support custom base URL via `OPENAI_BASE_URL` env var so users can point at Ollama, Azure OpenAI, or any OpenAI-compatible endpoint with zero code changes.

### Message Preprocessing
- **D-04:** Strip messages to plain text before sending to LLM. Convert @mentions to display names, remove embeds and attachments (replace with nothing or `[attachment]` marker), remove reactions.
- **D-05:** Filter out all bot messages and Discord system messages (joins, boosts, pins) before summarization. Only human conversation gets summarized.
- **D-06:** Preserve link URLs inline in message text — people discuss linked content, so the LLM needs to see what was referenced. Do NOT fetch linked content (tweet text, article previews, etc.).
- **D-07:** Represent message authors by their server display name: `"Alice: I think we should..."` format.

### Chunking Strategy
- **D-08:** Split large message sets into time-based windows (e.g., 1-hour chunks). Natural conversation boundaries.
- **D-09:** Two-pass summarization: summarize each time-window chunk independently, then pass all chunk summaries to a final LLM call that produces one unified summary. Higher quality, handles large volumes.

### Error Handling
- **D-10:** LLM errors (timeout, rate limit, bad API key) are shown as ephemeral Discord messages — only visible to the user who triggered the command. No channel spam.
- **D-11:** No auto-retry on LLM failures. Fail immediately and show the error. User can re-run the command manually.

### Claude's Discretion
- Project structure and module organization
- Provider interface design (ABC vs Protocol)
- Specific token estimation approach for determining when time windows are needed
- Logging strategy and log levels

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Specs
- `.planning/PROJECT.md` -- Project vision, constraints, key decisions
- `.planning/REQUIREMENTS.md` -- Full requirements with traceability (Phase 1: INFRA-01, INFRA-02, INFRA-03, PIPE-01, PIPE-02, PIPE-04, AI-01, AI-02, AI-03)
- `.planning/ROADMAP.md` -- Phase goals and success criteria

### Technology
- `CLAUDE.md` -- Technology stack decisions (discord.py 2.7.1, openai SDK, pydantic-settings, uv)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- No existing code — this is a greenfield project

### Established Patterns
- No patterns established yet. Phase 1 will set the conventions for the project.

### Integration Points
- Discord bot entry point (new)
- Settings/config module (new — pydantic-settings per CLAUDE.md)
- Provider interface + OpenAI implementation (new)
- Message fetching and preprocessing pipeline (new)

</code_context>

<specifics>
## Specific Ideas

- Links posted in channels should be preserved in the LLM input since people discuss them, but the bot should NOT fetch the linked content (no scraping tweets/articles)
- Bot messages sometimes post useful content (news feeds, alerts) but user explicitly chose to filter ALL bot messages for simplicity

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-foundation-and-pipeline*
*Context gathered: 2026-03-27*
