# Phase 5: Summary Language Controls - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Add configurable language guidelines to AI summary system prompts — a blocklist of insulting/inappropriate terms the LLM must avoid in its output, with an allowlist for context-specific exceptions (phrases that seem harmful but are acceptable in the server's culture). No new slash commands, no changes to the summarization pipeline or provider interface.

</domain>

<decisions>
## Implementation Decisions

### Storage Format
- **D-01:** Blocklist and allowlist are stored as separate text files (`blocklist.txt` and `allowlist.txt`), one term per line. Simple to edit, version-controllable, no size limits.
- **D-02:** Files live in the project root, next to `.env` and `pyproject.toml`. Consistent with where operators already look for config.

### Default Content
- **D-03:** Ship with a pre-populated `blocklist.txt` containing a curated default list of common slurs and insults. Operator can modify as needed for their server.

### Allowlist Format
- **D-04:** Allowlist entries include a parenthetical reason/context note: `kill (process terminology)`. The reason is included in the prompt so the LLM understands why the exception exists.

### Prompt Injection
- **D-05:** Language guidelines are appended as a "Language Guidelines" section at the end of `SUMMARY_SYSTEM_PROMPT` and `MERGE_SYSTEM_PROMPT` at runtime. No provider interface changes. String concatenation only.
- **D-06:** The appended prompt section instructs the LLM to also avoid obvious variations, misspellings, abbreviations, and leetspeak substitutions of blocked terms. Operators can additionally list specific missed variations as separate blocklist entries.

### Management
- **D-07:** Operator manages lists by editing the text files and restarting the bot. No hot-reload, no slash commands. Consistent with existing .env config pattern.

### Missing File Behavior
- **D-08:** If `blocklist.txt` or `allowlist.txt` doesn't exist at startup, log a warning and continue with no language rules applied. Bot still functions, operator just hasn't set up filtering yet.

### Claude's Discretion
- Exact wording of the appended "Language Guidelines" prompt section
- How to parse allowlist entries (term vs reason splitting)
- Structure of the pre-populated default blocklist
- Loading logic integration point (startup in config or lazy in summarizer)

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
- `.planning/phases/04-summary-quality-improvements/04-CONTEXT.md` — System prompt decisions (D-09: code-managed prompts, D-10: explicit signal instructions)

### Key Source Files
- `src/bot/summarizer.py` — Contains `SUMMARY_SYSTEM_PROMPT` and `MERGE_SYSTEM_PROMPT` where language guidelines will be appended
- `src/bot/config.py` — Settings class (pydantic-settings) — may need path config or loading logic

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/bot/summarizer.py`: `SUMMARY_SYSTEM_PROMPT` and `MERGE_SYSTEM_PROMPT` — the two prompt strings that will have language guidelines appended at runtime
- `src/bot/config.py`: `Settings` class — pydantic-settings pattern for validated config from `.env`

### Established Patterns
- All config via pydantic-settings `BaseSettings` with `.env` file
- System prompts are module-level string constants in `summarizer.py`
- `SummaryProvider.summarize(text, prompt)` — prompt passed at call time, language guidelines can be appended before passing

### Integration Points
- `summarize_messages()` in `summarizer.py` calls `provider.summarize(text, SUMMARY_SYSTEM_PROMPT)` and `provider.summarize(merged_input, MERGE_SYSTEM_PROMPT)` — these are the injection points where the appended language guidelines section gets added
- Bot startup in `setup_hook` — potential place to load and validate the text files

</code_context>

<specifics>
## Specific Ideas

- Allowlist entries use format: `term (reason)` — e.g., `kill (process terminology)` — reason is passed to the LLM for context
- LLM prompt should explicitly instruct: "Also avoid obvious variations, misspellings, abbreviations, and leetspeak substitutions of blocked terms"
- Both prompt-level variation catching AND operator-managed explicit variations work together as a layered approach

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-summary-language-controls*
*Context gathered: 2026-04-04*
