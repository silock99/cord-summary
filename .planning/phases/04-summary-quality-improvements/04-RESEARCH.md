# Phase 4: Summary Quality Improvements - Research

**Researched:** 2026-04-03
**Domain:** Discord message enrichment, LLM prompt engineering, discord.py Message API
**Confidence:** HIGH

## Summary

Phase 4 enriches the data pipeline feeding the LLM summarizer. The current pipeline strips messages down to `author: content` lines, losing conversational structure (who replied to whom), importance signals (reactions, @here mentions), and content metadata (attachment types, embed previews). All the data needed is already available on the `discord.Message` object -- `reference`, `reactions`, `mention_everyone`, `embeds`, `attachments` -- so the work is entirely in the preprocessor, data model, chunk formatter, and system prompts. No new dependencies, no API changes, no config changes.

The primary challenge is designing the enriched LLM input format so the model can leverage the new signals without getting confused by the markup. Reply chain indentation and importance markers need to be clear, unambiguous, and well-explained in the system prompt.

**Primary recommendation:** Extend `ProcessedMessage` with new fields, enrich `preprocess_message()` to extract all new metadata from `discord.Message`, update `format_chunk_for_llm()` to render reply indentation and markers, and rewrite the system prompts to explicitly instruct the LLM on each signal.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Reply chains formatted with thread-style indentation in LLM input. Direct replies show indented under parent.
- **D-02:** Skip Discord thread channels entirely -- only summarize top-level channel messages.
- **D-03:** Messages containing @here or @everyone are flagged as high-importance; LLM must include them verbatim in summary output.
- **D-04:** "Popular" messages = 5+ total reactions OR 5+ replies. Marked as important in LLM input.
- **D-05:** Attachments as `[type: filename]` format (e.g., `[image: screenshot.png]`).
- **D-06:** Reaction counts as total count only (e.g., `[12 reactions]`) on popular messages (5+ reactions). Non-popular show nothing.
- **D-07:** Discord embed content (title + description) extracted from user messages only.
- **D-08:** Pinned messages are NOT treated differently. No special handling.
- **D-09:** System prompts remain code-managed (hardcoded in `summarizer.py`). No env var customization.
- **D-10:** Improved prompts include explicit instructions for new signals.
- **D-11:** Single model for both on-demand and scheduled summaries.
- **D-12:** Single provider for both on-demand and scheduled summaries.

### Claude's Discretion
- Reply chain nesting depth (how deep to indent before flattening)
- Exact format of the enriched LLM input (markers, delimiters, ordering)
- How to count replies to a message for the popularity threshold
- Embed extraction logic (which embed fields to include beyond title/description)
- Updated SUMMARY_SYSTEM_PROMPT and MERGE_SYSTEM_PROMPT wording

### Deferred Ideas (OUT OF SCOPE)
None

</user_constraints>

## Project Constraints (from CLAUDE.md)

- Python 3.12+, discord.py 2.7.1, openai SDK, pydantic-settings 2.x
- No LiteLLM, LangChain, Pycord, Nextcord, APScheduler, or databases
- Provider-agnostic interface (ABC/Protocol pattern)
- uv for package management, ruff for linting, pytest + pytest-asyncio for testing
- GSD workflow enforcement for all code changes
- Single-server bot, config via env vars

## Architecture Patterns

### Affected Files and Their Roles

```
src/bot/
  models.py              # ProcessedMessage dataclass -- add new fields
  pipeline/
    preprocessor.py      # preprocess_message() -- extract new metadata
    chunker.py           # format_chunk_for_llm() -- render enriched format
    fetcher.py           # Unchanged (already fetches full Message objects)
  summarizer.py          # SUMMARY_SYSTEM_PROMPT, MERGE_SYSTEM_PROMPT -- rewrite
tests/
  test_preprocessor.py   # Update mock helper, add new test cases
  test_chunker.py        # Test enriched formatting
```

### Pattern 1: ProcessedMessage Extension

**What:** Add fields to the `ProcessedMessage` dataclass for reply info, importance flags, reaction count, attachment metadata, and embed content.

**Design:**
```python
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class ProcessedMessage:
    author: str
    content: str
    timestamp: datetime
    # New fields for Phase 4
    message_id: int = 0                      # For reply chain linking
    reply_to_id: int | None = None           # ID of parent message (if reply)
    is_important: bool = False               # @here/@everyone flag
    is_popular: bool = False                 # 5+ reactions OR 5+ replies
    reaction_count: int = 0                  # Total reaction count
    reply_count: int = 0                     # Number of replies to this message
    embeds_text: list[str] = field(default_factory=list)  # Extracted embed strings

    def to_line(self) -> str:
        """Format for LLM input with markers."""
        parts = []
        if self.is_important:
            parts.append("[IMPORTANT]")
        if self.is_popular:
            parts.append("[POPULAR]")
        parts.append(f"{self.author}: {self.content}")
        if self.reaction_count >= 5:
            parts.append(f"[{self.reaction_count} reactions]")
        return " ".join(parts)
```

### Pattern 2: Reply Chain Building in Chunk Formatter

**What:** `format_chunk_for_llm()` groups replies under their parent and indents them, giving the LLM conversational structure.

**Design approach:**
1. Build a message ID-to-message index from the chunk
2. For each message that is a reply, record the parent-child relationship
3. Render top-level messages first, then indent direct replies below them
4. Cap indentation depth at 2 levels (recommended) -- deeper replies flatten to level 2

```python
def format_chunk_for_llm(messages: list[ProcessedMessage]) -> str:
    """Format messages with reply indentation for LLM input."""
    by_id: dict[int, ProcessedMessage] = {m.message_id: m for m in messages if m.message_id}
    children: dict[int, list[ProcessedMessage]] = defaultdict(list)
    roots: list[ProcessedMessage] = []

    for msg in messages:
        if msg.reply_to_id and msg.reply_to_id in by_id:
            children[msg.reply_to_id].append(msg)
        else:
            roots.append(msg)

    lines = []
    for msg in roots:
        lines.append(msg.to_line())
        _render_replies(msg, children, lines, depth=1, max_depth=2)
    return "\n".join(lines)

def _render_replies(parent, children, lines, depth, max_depth):
    indent = "  " * min(depth, max_depth)
    for reply in children.get(parent.message_id, []):
        lines.append(f"{indent}> {reply.to_line()}")
        _render_replies(reply, children, lines, depth + 1, max_depth)
```

### Pattern 3: Attachment Type Detection

**What:** Map `Attachment.content_type` MIME types to human-readable categories.

```python
def classify_attachment(attachment: discord.Attachment) -> str:
    """Return a human-readable type for an attachment."""
    ct = attachment.content_type or ""
    if ct.startswith("image/"):
        return "image"
    elif ct.startswith("video/"):
        return "video"
    elif ct.startswith("audio/"):
        return "audio"
    else:
        return "file"
```

Format: `[image: screenshot.png]`, `[file: report.pdf]`, `[video: clip.mp4]`

### Pattern 4: Embed Extraction

**What:** Extract title + description from user message embeds.

```python
def extract_embed_text(embed: discord.Embed) -> str | None:
    """Extract readable text from an embed (title + description)."""
    parts = []
    if embed.title:
        parts.append(embed.title)
    if embed.description:
        parts.append(embed.description)
    return " - ".join(parts) if parts else None
```

### Anti-Patterns to Avoid
- **Hand-rolling reply tree from API calls:** Do NOT fetch referenced messages via API. Use `message.reference.message_id` to link within already-fetched messages. The parent may be outside the time window -- in that case, treat the reply as a root message.
- **Deep reply nesting:** Cap at 2 levels of indentation. Deeper chains produce unreadable LLM input.
- **Per-reaction emoji breakdown:** Decision D-06 says total count only. Do not enumerate emoji types.
- **Fetching reactions separately:** `message.reactions` is already populated on fetched messages. No additional API calls needed.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Reply chain resolution | Custom API calls to fetch referenced messages | `message.reference.message_id` + index into already-fetched messages | Referenced message is already in the batch if it's in the time window; if not, treat as root |
| Reaction counting | Per-emoji tracking or separate API calls | `sum(r.count for r in message.reactions)` | discord.py populates `message.reactions` automatically |
| Mention detection (@here/@everyone) | Regex scanning for `@here`/`@everyone` in text | `message.mention_everyone` boolean | discord.py pre-computes this; covers both @here and @everyone |
| MIME type classification | Manual extension-to-type mapping | `attachment.content_type` MIME prefix matching | discord.py provides MIME types from Discord API |

## discord.py API Reference (Verified)

### Message.reference
- Type: `Optional[MessageReference]`
- `reference.message_id`: `Optional[int]` -- ID of the message being replied to
- `reference.resolved`: `Optional[Union[Message, DeletedReferencedMessage]]` -- the actual message object (may be None if not cached)
- **Use `message_id` for linking, not `resolved`** -- resolved depends on cache state

### Message.mention_everyone
- Type: `bool`
- Covers BOTH `@everyone` AND `@here` -- a single boolean for both
- Only `True` if the mention actually resolved (user has permission)
- **Confidence: HIGH** (verified from discord.py source)

### Message.reactions
- Type: `list[Reaction]`
- Each `Reaction` has `.count` (int) -- total of normal + burst reactions
- Total reactions: `sum(r.count for r in message.reactions)`
- **Confidence: HIGH** (verified from discord.py source and issues)

### Attachment attributes
- `attachment.filename`: `str` -- original filename
- `attachment.content_type`: `Optional[str]` -- MIME type (e.g., `"image/png"`)
- Content type can be `None` -- need fallback to `"file"` category
- **Confidence: HIGH** (verified from discord.py source)

### Embed attributes
- `embed.title`: `Optional[str]`
- `embed.description`: `Optional[str]`
- User messages can have embeds auto-generated by Discord (link previews)
- **Confidence: HIGH**

## Reply Count Tracking Strategy

Decision D-04 requires counting replies to each message (5+ replies = popular). Since we process messages in order:

1. First pass: scan all messages, build `reply_to_id` -> count mapping
2. Second pass (or inline): set `reply_count` on each message based on how many other messages reference it

This is a two-pass approach within `summarize_channel()`:
```python
# After preprocessing all messages:
reply_counts: dict[int, int] = Counter()
for msg in processed:
    if msg.reply_to_id:
        reply_counts[msg.reply_to_id] += 1

for msg in processed:
    msg.reply_count = reply_counts.get(msg.message_id, 0)
    if msg.reply_count >= 5 or msg.reaction_count >= 5:
        msg.is_popular = True
```

## Common Pitfalls

### Pitfall 1: Reply parent outside time window
**What goes wrong:** A message replies to a message from 3 hours ago, but the summary only covers the last hour. The parent message isn't in the batch.
**Why it happens:** Time-windowed fetching doesn't include the original message.
**How to avoid:** If `reply_to_id` is not found in the message index, treat the reply as a root-level message. Do NOT make additional API calls to fetch it.
**Warning signs:** Messages appearing orphaned with indentation but no parent context.

### Pitfall 2: mention_everyone requires permission
**What goes wrong:** `message.mention_everyone` is `False` even though the text contains `@here`.
**Why it happens:** Discord only sets `mention_everyone` to `True` if the user has permission to mention everyone. A user without the permission typing `@here` won't trigger it.
**How to avoid:** This is actually correct behavior -- if the mention didn't resolve, it wasn't an actual notification, so not marking it as important is fine.

### Pitfall 3: Embed spam from link previews
**What goes wrong:** A message with 5 URLs generates 5 embeds, each with title/description, making the LLM input unnecessarily long.
**Why it happens:** Discord auto-generates embeds for URLs.
**How to avoid:** Limit embed extraction to first 2-3 embeds per message. Also keep extracted text short (truncate long descriptions).

### Pitfall 4: content_type is None
**What goes wrong:** `attachment.content_type` is `None` for some attachments, causing a crash or incorrect classification.
**Why it happens:** Not all attachments have MIME types provided by Discord.
**How to avoid:** Default to `"file"` when `content_type` is None or empty.

### Pitfall 5: Token budget increase from enriched format
**What goes wrong:** Indentation, markers, and embed text significantly increase the token count per message, causing more chunks and more LLM calls.
**Why it happens:** Each message now generates more text than before.
**How to avoid:** The existing chunking system handles this automatically (it estimates tokens from the formatted text). But be aware that the same message set will now chunk more aggressively. No action needed beyond awareness.

### Pitfall 6: Breaking existing tests
**What goes wrong:** Adding fields to ProcessedMessage or changing `to_line()` breaks existing test assertions.
**Why it happens:** Tests assert exact string matches on `to_line()` output and construct ProcessedMessage without new fields.
**How to avoid:** New fields have defaults, so existing tests constructing ProcessedMessage should still work. Update `_make_message()` helper in tests to support new mock attributes (reactions, reference, embeds). Tests that assert `to_line()` output may need updating for markers.

## Code Examples

### Enriched preprocess_message()
```python
def preprocess_message(
    message: discord.Message, guild: discord.Guild
) -> ProcessedMessage | None:
    # ... existing filtering and mention resolution ...

    # D-05: Typed attachment markers
    for att in message.attachments:
        att_type = classify_attachment(att)
        marker = f"[{att_type}: {att.filename}]"
        content = f"{content} {marker}" if content else marker

    # D-07: Embed extraction (user messages only, already filtered bots above)
    embeds_text = []
    for embed in message.embeds[:3]:  # Limit to avoid spam
        text = extract_embed_text(embed)
        if text:
            embeds_text.append(text)

    # D-03: @here/@everyone importance flag
    is_important = message.mention_everyone

    # D-06: Reaction count
    reaction_count = sum(r.count for r in message.reactions)

    return ProcessedMessage(
        author=message.author.display_name,
        content=content.strip(),
        timestamp=message.created_at,
        message_id=message.id,
        reply_to_id=message.reference.message_id if message.reference else None,
        is_important=is_important,
        reaction_count=reaction_count,
        embeds_text=embeds_text,
    )
```

### Updated System Prompts
```python
SUMMARY_SYSTEM_PROMPT = (
    "You are a Discord channel summarizer. Given a conversation log, produce a concise "
    "summary organized by discussion topic. Format each topic with a bold header "
    "(**Topic Name**) followed by bullet points underneath.\n\n"
    "Signal markers in the input:\n"
    "- [IMPORTANT]: Messages with @here or @everyone mentions. You MUST include "
    "these verbatim in the summary -- do not paraphrase or omit them.\n"
    "- [POPULAR]: Messages with high engagement (many reactions or replies). "
    "Prioritize these in the summary.\n"
    "- [N reactions]: Shows total reaction count, indicating community engagement.\n"
    "- Indented lines starting with > are replies to the message above them, "
    "showing conversation flow.\n"
    "- [image: file], [video: file], [file: file]: Attachment metadata.\n"
    "- Embed content appears after the message text in parentheses.\n\n"
    "Keep language clear and brief. Do not include timestamps. "
    "Do not extract action items or decisions as separate sections."
)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Flat `author: content` lines | Indented reply chains with markers | Phase 4 | LLM gets conversational structure |
| Generic `[attachment]` marker | `[type: filename]` with MIME detection | Phase 4 | LLM understands what was shared |
| No reaction/mention signals | `[IMPORTANT]` and `[POPULAR]` markers | Phase 4 | LLM can prioritize by engagement |
| Generic system prompt | Signal-aware prompt with explicit instructions | Phase 4 | LLM knows how to use each marker |

## Open Questions

1. **Reply indentation depth cap**
   - What we know: Deep reply chains (5+ levels) create unreadable indentation
   - Recommendation: Cap at depth 2 (indent, double-indent). Deeper replies render at depth 2. This is in Claude's discretion.

2. **Embed description truncation**
   - What we know: Some embeds have very long descriptions (article previews)
   - Recommendation: Truncate embed descriptions to 200 characters to prevent token bloat. In Claude's discretion.

3. **Reply count computation location**
   - What we know: Reply counts need a second pass after preprocessing
   - Recommendation: Do the counting in `summarize_channel()` or a new helper between preprocessing and chunking. The preprocessor processes one message at a time, so it can't count replies across messages.

## Sources

### Primary (HIGH confidence)
- [discord.py message.py source](https://github.com/Rapptz/discord.py/blob/master/discord/message.py) -- Message.reference, MessageReference.resolved, mention_everyone, embeds, attachments
- [discord.py reaction.py source](https://github.com/Rapptz/discord.py/blob/master/discord/reaction.py) -- Reaction.count attribute
- [discord.py API reference](https://discordpy.readthedocs.io/en/stable/api.html) -- Message, Attachment, Embed class docs

### Secondary (MEDIUM confidence)
- [discord.py issue #1181](https://github.com/Rapptz/discord.py/issues/1181) -- reaction counting patterns
- [discord.py discussion #6572](https://github.com/Rapptz/discord.py/discussions/6572) -- message reply reference usage

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all existing discord.py APIs verified
- Architecture: HIGH -- extending existing patterns (dataclass, preprocessor, formatter, prompts)
- Pitfalls: HIGH -- based on verified API behavior (mention_everyone semantics, content_type nullability)
- discord.py API: HIGH -- verified against source code on GitHub

**Research date:** 2026-04-03
**Valid until:** 2026-05-03 (stable -- discord.py 2.x API unlikely to change)
