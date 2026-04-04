---
status: testing
phase: 05-summary-language-controls
source: [05-01-SUMMARY.md]
started: 2026-04-04T08:00:00Z
updated: 2026-04-04T08:00:00Z
---

## Current Test

number: 1
name: Blocklist Terms Filtered from Summary
expected: |
  When channel messages contain terms from blocklist.txt, the LLM-generated summary avoids using those blocked terms. The summary uses neutral alternatives instead.
awaiting: user response

## Tests

### 1. Blocklist Terms Filtered from Summary
expected: When channel messages contain terms from blocklist.txt, the LLM-generated summary avoids using those blocked terms. The summary uses neutral alternatives instead.
result: [pending]

### 2. Allowlist Exceptions Preserved
expected: If allowlist.txt contains terms with reasons (e.g., "execute (technical term)"), those terms ARE allowed in summaries even if they'd normally be filtered. Edit allowlist.txt to add an exception and verify it appears in output.
result: [pending]

### 3. Missing Config Files Graceful Degradation
expected: If blocklist.txt or allowlist.txt is deleted/renamed, the bot starts without errors and summaries still generate normally (just without language filtering).
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps

