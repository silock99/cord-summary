---
phase: 04-summary-quality-improvements
plan: 01
subsystem: pipeline
tags: [data-model, preprocessor, metadata-extraction, testing]
dependency_graph:
  requires: []
  provides: [enriched-processed-message, typed-attachments, embed-extraction, importance-flags, reply-tracking]
  affects: [src/bot/models.py, src/bot/pipeline/preprocessor.py, tests/test_preprocessor.py]
tech_stack:
  added: []
  patterns: [dataclass-field-defaults, mime-type-classification, embed-text-extraction]
key_files:
  created: []
  modified:
    - src/bot/models.py
    - src/bot/pipeline/preprocessor.py
    - tests/test_preprocessor.py
decisions:
  - "All new ProcessedMessage fields have defaults for backward compatibility"
  - "Attachment classification uses MIME content_type prefix (image/, video/, audio/) with file as fallback"
  - "Embed text extraction limited to first 3 embeds with 200-char description truncation"
  - "is_popular and reply_count left as defaults -- require second pass computed in Plan 02"
metrics:
  duration: 3m
  completed: "2026-04-03T08:42:18Z"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 3
---

# Phase 04 Plan 01: Extend ProcessedMessage and Enrich Preprocessor Summary

Extended ProcessedMessage with 7 metadata fields and enriched preprocessor to extract message IDs, reply references, importance flags, reaction counts, typed attachments, and embed content from Discord messages.

## What Was Done

### Task 1: Extend ProcessedMessage and enrich preprocessor
**Commit:** `87af8a3`

- Added 7 new fields to ProcessedMessage dataclass: message_id, reply_to_id, is_important, is_popular, reaction_count, reply_count, embeds_text (all with defaults for backward compatibility)
- Updated to_line() to output [IMPORTANT], [POPULAR], reaction count, and embed markers
- Added classify_attachment() helper for MIME-based typed attachment markers (image/video/audio/file)
- Added extract_embed_text() helper for embed title+description extraction with 200-char truncation
- Enriched preprocess_message() to extract message_id, reply references, mention_everyone importance, reaction sums, typed attachments, and embed text
- Replaced generic "[attachment]" marker with typed "[type: filename]" format
- Updated _make_message test helper with new mock attributes (id, reactions, embeds, reference, mention_everyone)

### Task 2: Add comprehensive preprocessor tests
**Commit:** `558b273`

- Added mock helpers: _make_attachment, _make_embed, _make_reaction, _make_reference
- Added 22 new test functions covering typed attachments (image, video, audio, no content_type), reaction counts, importance flags, reply references, embed extraction (title+desc, title only, desc only, limit 3, truncation, empty skip), message_id tracking, and to_line() markers
- Total test count: 36 preprocessor tests, 79 full suite -- all passing

## Deviations from Plan

None - plan executed exactly as written.

## Decisions Made

1. **Backward-compatible defaults**: All 7 new fields have defaults so existing ProcessedMessage(author, content, timestamp) construction works unchanged. This keeps chunker tests and summarizer tests passing without modification.
2. **is_popular and reply_count deferred**: These fields require a second pass across all messages (counting replies per message_id) and will be computed in Plan 02's formatter/summarizer updates.
3. **Attachment content_type=None fallback**: When Discord doesn't provide a content_type, defaults to "file" type rather than raising an error.

## Known Stubs

None -- all fields are either fully wired (message_id, reply_to_id, is_important, reaction_count, embeds_text) or intentionally left as defaults for Plan 02 to compute (is_popular, reply_count).

## Verification

- All 79 tests pass: `uv run python -m pytest tests/ -x` exits 0
- ProcessedMessage has all 7 new fields with defaults
- preprocess_message extracts all new metadata from discord.Message
- No new dependencies added
- Existing tests (chunker, summarizer) pass without modification
