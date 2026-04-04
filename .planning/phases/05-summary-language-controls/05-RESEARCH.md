# Phase 5: Summary Language Controls - Research

**Researched:** 2026-04-04
**Domain:** Text file parsing, LLM prompt engineering, configuration management
**Confidence:** HIGH

## Summary

This phase adds configurable language guidelines (blocklist/allowlist) to the AI summarization prompts. The implementation is entirely self-contained: load two text files at startup, parse them into lists, build a "Language Guidelines" prompt section, and append it to the existing `SUMMARY_SYSTEM_PROMPT` and `MERGE_SYSTEM_PROMPT` strings before each LLM call.

No new dependencies are needed. The work uses Python stdlib for file I/O and string parsing, and integrates with the existing `summarizer.py` module where prompts are already defined as module-level constants. The existing pattern of "operator edits config files, restarts bot" (established with `.env`) applies directly.

**Primary recommendation:** Create a single new module (`src/bot/language_filter.py`) that handles loading, parsing, and prompt section generation. Modify `summarizer.py` to call this module and append the result to prompts before LLM calls. Ship default `blocklist.txt` in project root.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Blocklist and allowlist are stored as separate text files (`blocklist.txt` and `allowlist.txt`), one term per line. Simple to edit, version-controllable, no size limits.
- **D-02:** Files live in the project root, next to `.env` and `pyproject.toml`. Consistent with where operators already look for config.
- **D-03:** Ship with a pre-populated `blocklist.txt` containing a curated default list of common slurs and insults. Operator can modify as needed for their server.
- **D-04:** Allowlist entries include a parenthetical reason/context note: `kill (process terminology)`. The reason is included in the prompt so the LLM understands why the exception exists.
- **D-05:** Language guidelines are appended as a "Language Guidelines" section at the end of `SUMMARY_SYSTEM_PROMPT` and `MERGE_SYSTEM_PROMPT` at runtime. No provider interface changes. String concatenation only.
- **D-06:** The appended prompt section instructs the LLM to also avoid obvious variations, misspellings, abbreviations, and leetspeak substitutions of blocked terms. Operators can additionally list specific missed variations as separate blocklist entries.
- **D-07:** Operator manages lists by editing the text files and restarting the bot. No hot-reload, no slash commands. Consistent with existing .env config pattern.
- **D-08:** If `blocklist.txt` or `allowlist.txt` doesn't exist at startup, log a warning and continue with no language rules applied. Bot still functions, operator just hasn't set up filtering yet.

### Claude's Discretion
- Exact wording of the appended "Language Guidelines" prompt section
- How to parse allowlist entries (term vs reason splitting)
- Structure of the pre-populated default blocklist
- Loading logic integration point (startup in config or lazy in summarizer)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

## Project Constraints (from CLAUDE.md)

- Python 3.12+, discord.py 2.7.1, pydantic-settings 2.x
- No database -- all config via files and env vars
- No LiteLLM, LangChain, or APScheduler
- Package management via `uv`, linting via `ruff`, testing via `pytest + pytest-asyncio`
- Provider-agnostic interface (no provider changes needed for this phase per D-05)

## Standard Stack

### Core
No new libraries needed. This phase uses only Python stdlib.

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pathlib (stdlib) | Python 3.12+ | File path handling | Already used throughout the project |
| logging (stdlib) | Python 3.12+ | Warning on missing files | Already used throughout the project |

### Supporting
No additional dependencies required.

## Architecture Patterns

### Recommended Module Structure
```
src/bot/
    language_filter.py    # NEW: load, parse, build prompt section
    summarizer.py         # MODIFIED: append language guidelines to prompts
blocklist.txt             # NEW: project root, one term per line
allowlist.txt             # NEW: project root (optional), term (reason) per line
```

### Pattern 1: Language Filter Module
**What:** A standalone module that encapsulates all blocklist/allowlist logic.
**When to use:** This is the only pattern needed.

```python
# src/bot/language_filter.py
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def load_terms(filepath: Path) -> list[str]:
    """Load terms from a text file, one per line. Skip empty lines and comments."""
    if not filepath.exists():
        logger.warning(f"Language file not found: {filepath} -- no language rules from this file")
        return []
    lines = filepath.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]

def parse_allowlist_entry(entry: str) -> tuple[str, str]:
    """Parse 'term (reason)' into (term, reason). If no parens, reason is empty."""
    if "(" in entry and entry.endswith(")"):
        idx = entry.index("(")
        term = entry[:idx].strip()
        reason = entry[idx + 1:-1].strip()
        return term, reason
    return entry.strip(), ""

def build_language_guidelines(blocklist: list[str], allowlist: list[str]) -> str:
    """Build the Language Guidelines prompt section from loaded terms."""
    if not blocklist:
        return ""
    # ... build and return the prompt section string
```

### Pattern 2: Prompt Assembly in Summarizer
**What:** Append the language guidelines section to prompts at call time, not by mutating the module-level constants.
**When to use:** In `summarize_messages()` before each `provider.summarize()` call.

```python
# In summarizer.py
from bot.language_filter import get_language_guidelines

# At call site:
guidelines = get_language_guidelines()  # cached string from startup load
effective_prompt = SUMMARY_SYSTEM_PROMPT + guidelines
await provider.summarize(text, effective_prompt)
```

**Rationale:** Keeping `SUMMARY_SYSTEM_PROMPT` and `MERGE_SYSTEM_PROMPT` as immutable constants preserves testability and clarity. The guidelines string is built once at load time and reused.

### Pattern 3: Loading at Startup vs Lazy Loading
**Recommendation:** Load at startup (in bot `setup_hook` or a module-level init function). This is consistent with how `.env` config is loaded -- fail fast, log warnings early.

```python
# In client.py setup_hook or a dedicated init:
from bot.language_filter import load_language_config
load_language_config()  # logs warnings, caches result
```

### Anti-Patterns to Avoid
- **Mutating module-level prompt constants:** Do not modify `SUMMARY_SYSTEM_PROMPT` in-place. Build the effective prompt at call time by concatenation.
- **Re-reading files on every summarize call:** Load once at startup, cache the result. Per D-07, changes require restart.
- **Complex regex for allowlist parsing:** A simple string split on `(` is sufficient. No regex needed.
- **Putting language filter logic inside config.py:** The Settings class handles `.env` vars. Text file loading is a different concern -- keep it in its own module.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Text file parsing | Custom tokenizer | `str.splitlines()` + `str.strip()` | One term per line is trivially parseable |
| Prompt template system | Jinja2 or custom templating | String concatenation | Per D-05, simple concatenation is the decision |

**Key insight:** This phase is intentionally simple. The complexity lives in prompt wording, not code architecture.

## Common Pitfalls

### Pitfall 1: Encoding Issues in Text Files
**What goes wrong:** Operator creates blocklist on Windows with different encoding, bot reads with wrong encoding.
**Why it happens:** Default encoding varies by platform.
**How to avoid:** Always specify `encoding="utf-8"` when reading the files.
**Warning signs:** UnicodeDecodeError on startup.

### Pitfall 2: Prompt Bloat with Large Blocklists
**What goes wrong:** An extremely large blocklist (hundreds of terms) could consume significant prompt tokens, reducing space for actual message content.
**Why it happens:** Every blocked term is injected into the system prompt.
**How to avoid:** Document a practical limit in comments (e.g., "recommended: under 50 terms"). The prompt should use category-level instructions ("avoid slurs, insults, and derogatory language") plus the specific blocklist as examples/overrides rather than relying solely on the list.
**Warning signs:** System prompt exceeds 500+ tokens from guidelines alone.

### Pitfall 3: Overly Rigid Prompt Wording
**What goes wrong:** The LLM interprets blocklist too literally and refuses to mention topics that use blocked words in context (e.g., discussing moderation of hate speech).
**Why it happens:** Prompt says "never use these words" without nuance.
**How to avoid:** The prompt should say "do not use these terms in your summary output" -- making clear it applies to the LLM's own word choice, not to describing what was discussed. The allowlist with reasons (D-04) also helps here.
**Warning signs:** Summaries omit entire discussion topics because they touched on sensitive subjects.

### Pitfall 4: Forgetting to Apply Guidelines to MERGE_SYSTEM_PROMPT
**What goes wrong:** Single-pass summaries are filtered, but merged summaries from chunked conversations are not.
**Why it happens:** Developer only modifies the single-pass code path.
**How to avoid:** Apply guidelines to both `SUMMARY_SYSTEM_PROMPT` and `MERGE_SYSTEM_PROMPT` per D-05.
**Warning signs:** Long conversations (that trigger chunking) produce unfiltered summaries.

### Pitfall 5: Comments and Blank Lines in Text Files
**What goes wrong:** Blank lines or `# comment` lines get treated as blocked terms.
**Why it happens:** Naive parsing that doesn't skip empty/comment lines.
**How to avoid:** Strip lines, skip empty strings, skip lines starting with `#`.
**Warning signs:** LLM gets instructed to avoid empty strings or comment text.

## Code Examples

### Loading and Parsing

```python
from pathlib import Path

def load_terms(filepath: Path) -> list[str]:
    """Load terms from text file. Skip blanks and # comments."""
    if not filepath.exists():
        return []
    lines = filepath.read_text(encoding="utf-8").splitlines()
    return [
        line.strip()
        for line in lines
        if line.strip() and not line.strip().startswith("#")
    ]

def parse_allowlist_entry(entry: str) -> tuple[str, str]:
    """Parse 'term (reason)' -> (term, reason)."""
    if "(" in entry and entry.rstrip().endswith(")"):
        idx = entry.index("(")
        return entry[:idx].strip(), entry[idx + 1:-1].strip()
    return entry.strip(), ""
```

### Building the Language Guidelines Prompt Section

```python
def build_language_guidelines(blocked: list[str], allowed: list[str]) -> str:
    """Build prompt section from blocked/allowed terms. Returns empty string if no terms."""
    if not blocked:
        return ""

    parts = [
        "\n\n## Language Guidelines\n",
        "When writing your summary, do NOT use any of the following terms or phrases. "
        "Also avoid obvious variations, misspellings, abbreviations, and leetspeak "
        "substitutions of these terms:\n",
    ]

    for term in blocked:
        parts.append(f"- {term}\n")

    if allowed:
        parts.append(
            "\nExceptions -- the following terms ARE acceptable in this server's context "
            "and may appear in summaries when relevant:\n"
        )
        for entry in allowed:
            term, reason = parse_allowlist_entry(entry)
            if reason:
                parts.append(f"- \"{term}\" (acceptable because: {reason})\n")
            else:
                parts.append(f"- \"{term}\"\n")

    parts.append(
        "\nIf a discussion topic involved blocked language, summarize the topic's "
        "substance without using the blocked terms themselves.\n"
    )

    return "".join(parts)
```

### Integration in summarizer.py

```python
# At the call sites in summarize_messages():
from bot.language_filter import get_language_guidelines

guidelines = get_language_guidelines()  # returns cached string or ""
summary_prompt = SUMMARY_SYSTEM_PROMPT + guidelines
merge_prompt = MERGE_SYSTEM_PROMPT + guidelines

# Then use summary_prompt / merge_prompt instead of the raw constants
```

## Default Blocklist Content (D-03)

The default `blocklist.txt` should contain a curated set of common slurs and insults. Recommended approach:

```text
# Default language blocklist for Discord Summary Bot
# One term per line. Lines starting with # are comments.
# Operator should customize for their server's needs.
#
# Common slurs and insults
retard
retarded
```

Keep the default list short and focused on the most universally inappropriate terms. The operator will extend it for their server context. Avoid making the default list so long that it becomes unwieldy or controversial to ship.

**Note:** The implementer should use judgment on the exact terms. A reasonable default is 10-20 widely recognized slurs/insults. The operator customizes from there.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No content filtering | Prompt-level language guidelines | This phase | LLM output avoids specified terms |

This is a straightforward prompt engineering pattern. No evolving ecosystem or library concerns.

## Open Questions

1. **Module-level caching vs explicit init**
   - What we know: Files should be loaded once, not on every call (D-07)
   - What's unclear: Whether to use a module-level global or pass the guidelines string through function parameters
   - Recommendation: Use a module-level cached value loaded via an explicit `load_language_config()` function called in `setup_hook`. This matches the existing pattern where `Settings()` is instantiated at startup.

2. **Prompt token budget awareness**
   - What we know: Large blocklists consume system prompt tokens
   - What's unclear: Whether to enforce a hard limit or just document guidance
   - Recommendation: Log the token count (rough estimate) of the language guidelines section at startup. No hard limit -- operator responsibility. Log a warning if guidelines exceed ~200 tokens.

## Sources

### Primary (HIGH confidence)
- `src/bot/summarizer.py` -- current prompt constants and summarize_messages flow
- `src/bot/config.py` -- existing Settings pattern for configuration
- `.planning/phases/05-summary-language-controls/05-CONTEXT.md` -- all locked decisions

### Secondary (MEDIUM confidence)
- Python pathlib and str documentation (stdlib, well-known APIs)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, pure stdlib
- Architecture: HIGH -- simple module with clear integration points in existing code
- Pitfalls: HIGH -- straightforward domain, pitfalls are well-understood encoding and prompt engineering concerns

**Research date:** 2026-04-04
**Valid until:** 2026-05-04 (stable -- no external dependencies to go stale)
