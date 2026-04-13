---
phase: 12-refine-the-summary-the-bot-produces
reviewed: 2026-04-13T00:00:00Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - conftest.py
  - src/bot/commands/post_summary.py
  - src/bot/commands/summary.py
  - src/bot/formatting/embeds.py
  - src/bot/scheduling/overnight.py
  - src/bot/summarizer.py
  - tests/test_embeds.py
  - tests/test_summarizer.py
findings:
  critical: 0
  warning: 3
  info: 3
  total: 6
status: issues_found
---

# Phase 12: Code Review Report

**Reviewed:** 2026-04-13
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found

## Summary

Reviewed the summarizer pipeline, embed formatting, slash commands, overnight scheduler, and associated tests. The codebase is well-structured with good separation of concerns. No critical security issues found. Three warnings relate to missing input validation, fragile magic-string coupling, and unbounded in-memory state. Three info items cover logging best practices and minor code quality.

## Warnings

### WR-01: Unchecked int() conversion on user-supplied channel string

**File:** `src/bot/commands/summary.py:91`
**Issue:** `int(channel)` is called on the autocomplete-provided channel string without a try/except. While Discord autocomplete normally provides valid values, a malformed or tampered value will raise an unhandled `ValueError`, causing the interaction to fail silently (no user-facing error message, just a timeout). The same pattern exists in `src/bot/commands/post_summary.py:63`.
**Fix:**
```python
try:
    target = interaction.guild.get_channel(int(channel))
except (ValueError, TypeError):
    await interaction.edit_original_response(content="Invalid channel.")
    return
if not target:
    await interaction.edit_original_response(content="Channel not found.")
    return
```

### WR-02: Fragile magic-string comparison for empty summary detection

**File:** `src/bot/commands/post_summary.py:101`
**Issue:** The check `summary_text == "No messages to summarize."` is coupled to the exact string returned by `summarize_messages()` in `src/bot/summarizer.py:111`. If that string ever changes, this check silently breaks, and empty summaries get posted publicly. This is a maintenance hazard.
**Fix:** Use a sentinel on `SummaryResult` instead of string comparison. For example, add a boolean field:
```python
@dataclass
class SummaryResult:
    text: str
    message_count: int
    participant_count: int
    is_empty: bool = False
```
Then in `summarize_channel`, set `is_empty=True` when there are no processed messages, and check `summary_result.is_empty` in `post_summary.py` instead of comparing strings.

### WR-03: Unbounded cooldown dictionary grows without limit

**File:** `src/bot/commands/summary.py:18`
**Issue:** The module-level `_cooldowns` dict accumulates an entry for every user who ever runs `/summary`, but entries are never evicted. On a long-running bot in a large server, this grows indefinitely. While primarily a memory concern, it is also a correctness issue: stale entries for users who left the server persist forever.
**Fix:** Evict expired entries periodically, or use a bounded cache. A simple approach:
```python
# After recording cooldown (line 155), prune old entries
now = datetime.now(timezone.utc)
expired = [uid for uid, ts in _cooldowns.items()
           if (now - ts).total_seconds() >= cooldown]
for uid in expired:
    del _cooldowns[uid]
```
Alternatively, use `functools.lru_cache` or a TTL-based dict wrapper.

## Info

### IN-01: f-string in logger.exception() prevents lazy evaluation

**File:** `src/bot/commands/post_summary.py:94`
**Issue:** `logger.exception(f"/post-summary error summarizing #{target.name}")` uses an f-string. Logger methods support lazy formatting with `%s` substitution, which avoids string interpolation cost when the log level is disabled. Same pattern at `src/bot/scheduling/overnight.py:59`, `overnight.py:64`.
**Fix:**
```python
logger.exception("/post-summary error summarizing #%s", target.name)
```

### IN-02: conftest.py module deletion is fragile

**File:** `conftest.py:10-12`
**Issue:** Deleting `bot.*` modules from `sys.modules` on every test session import is a workaround for path issues. This can cause subtle test failures if modules cache references to the deleted module objects (stale references). The comment explains the intent but the approach is fragile.
**Fix:** Consider using proper package installation (`pip install -e .`) instead of sys.path manipulation, which would eliminate the need for this workaround entirely.

### IN-03: Duplicate channel_autocomplete function

**File:** `src/bot/commands/post_summary.py:31-40` and `src/bot/commands/summary.py:40-49`
**Issue:** The `channel_autocomplete` function is duplicated identically in both command files. This is minor code duplication that could drift over time.
**Fix:** Extract to a shared utility, e.g., `src/bot/commands/_common.py`:
```python
def make_channel_autocomplete(bot):
    async def channel_autocomplete(interaction, current):
        choices = []
        for cid in bot.settings.allowed_channel_ids:
            ch = interaction.guild.get_channel(cid)
            if ch and current.lower() in ch.name.lower():
                choices.append(app_commands.Choice(name=f"#{ch.name}", value=str(cid)))
        return choices[:25]
    return channel_autocomplete
```

---

_Reviewed: 2026-04-13_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
