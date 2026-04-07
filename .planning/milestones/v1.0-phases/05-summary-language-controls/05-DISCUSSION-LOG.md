# Phase 5: Summary Language Controls - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-04
**Phase:** 05-summary-language-controls
**Areas discussed:** Storage format, Default content, Prompt injection, Management UX, Allowlist format, Missing file behavior, File location, Variation handling

---

## Storage Format

| Option | Description | Selected |
|--------|-------------|----------|
| Separate text files | blocklist.txt and allowlist.txt, one term per line. Simple to edit, version-controllable. | ✓ |
| JSON config file | Single language_rules.json with both lists. Structured but harder to hand-edit. | |
| Env vars | Comma-separated in .env. Consistent pattern but awkward for long lists. | |

**User's choice:** Separate text files
**Notes:** None

---

## Default Content

| Option | Description | Selected |
|--------|-------------|----------|
| Empty by default | Ship empty files, operator builds own list. | |
| Example file included | Ship blocklist.example.txt as template, actual file starts empty. | |
| Pre-populated list | Ship with curated default blocklist of common slurs/insults. | ✓ |

**User's choice:** Pre-populated list
**Notes:** None

---

## Prompt Injection

| Option | Description | Selected |
|--------|-------------|----------|
| Appended section | Add "Language Guidelines" section at end of system prompts at runtime. No provider changes. | ✓ |
| Separate system message | Send language guidelines as second system message. Requires provider interface change. | |
| You decide | Let Claude choose during implementation. | |

**User's choice:** Appended section
**Notes:** User asked for clarification on functional differences between options. Explained that options 1 and 2 produce nearly identical LLM behavior — the difference is code complexity. Appended section requires zero interface changes.

---

## Management UX

| Option | Description | Selected |
|--------|-------------|----------|
| Edit files + restart | Operator edits text files and restarts bot. Consistent with .env pattern. | ✓ |
| Edit files + hot-reload | Bot watches files or re-reads before each summary. No restart needed. | |
| Slash commands | /blocklist add <term> commands for runtime management. | |

**User's choice:** Edit files + restart
**Notes:** None

---

## Allowlist Format

| Option | Description | Selected |
|--------|-------------|----------|
| Term + reason | Each line: "kill (process terminology)". Reason included in prompt for LLM context. | ✓ |
| Bare terms only | Just the term per line. Simpler but LLM gets no context. | |
| You decide | Let Claude choose during implementation. | |

**User's choice:** Term + reason
**Notes:** None

---

## Missing File Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Warn and continue | Log warning, run with no language rules. Bot still works. | ✓ |
| Auto-create empty files | Create missing files at startup. No warning. | |
| Fail at startup | Refuse to start if files missing. Forces explicit setup. | |

**User's choice:** Warn and continue
**Notes:** None

---

## File Location

| Option | Description | Selected |
|--------|-------------|----------|
| Project root | Next to .env and pyproject.toml. Consistent with existing config location. | ✓ |
| config/ subdirectory | In a config/ folder. More organized but adds a directory. | |
| Configurable via env var | BLOCKLIST_PATH/ALLOWLIST_PATH env vars. Most flexible but adds complexity. | |

**User's choice:** Project root
**Notes:** None

---

## Variation Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Prompt instruction | Tell LLM to avoid variations/misspellings/leetspeak. Zero code complexity. | |
| Operator lists all variations | Manually add each variation as separate blocklist entry. | |
| Both | Prompt instruction as baseline + operator adds specific missed variations. | ✓ |

**User's choice:** Both
**Notes:** User asked how to give the LLM instructions to block permutations of blocklist terms. Explained that modern LLMs handle fuzzy matching well when explicitly instructed, and operators can supplement with specific edge cases.

---

## Claude's Discretion

- Exact wording of the appended "Language Guidelines" prompt section
- How to parse allowlist entries (term vs reason splitting)
- Structure of the pre-populated default blocklist
- Loading logic integration point (startup in config or lazy in summarizer)

## Deferred Ideas

None — discussion stayed within phase scope
