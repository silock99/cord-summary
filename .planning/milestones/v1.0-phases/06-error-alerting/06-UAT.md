---
status: complete
phase: 06-error-alerting
source: [06-01-SUMMARY.md, 06-02-SUMMARY.md]
started: 2026-04-04T08:00:00Z
updated: 2026-04-04T08:20:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Admin Error DM on Overnight Failure
expected: When the overnight summary task encounters an error (e.g., LLM provider down), admins listed in ADMIN_USER_IDS receive a DM with a red embed describing the error. The error is NOT posted publicly to the summary channel.
result: skipped

### 2. Empty Admin List Graceful Handling
expected: With ADMIN_USER_IDS unset or empty, the bot logs a warning on error but does not crash. No DMs sent, bot continues running.
result: skipped

### 3. /post-summary Admin Access
expected: Running /post-summary as an admin (user ID in ADMIN_USER_IDS) generates and posts a public summary to the summary channel with a "Requested by" footer.
result: issue
reported: "Nope. Something went wrong."
severity: major

### 4. /post-summary Non-Admin Rejection
expected: Running /post-summary as a non-admin user shows an ephemeral "You don't have permission" error. No summary is generated or posted.
result: pass

### 5. /post-summary Thread Delivery
expected: With USE_THREADS=true, /post-summary creates a thread named "Summary -- #channel -- date" and posts embeds inside it (distinct from overnight thread naming).
result: blocked
blocked_by: other
reason: "Cannot test"

### 6. Admin Cooldown Exemption
expected: Admins (ADMIN_USER_IDS) can use /summary without cooldown restrictions. Non-admins still have the cooldown applied.
result: pass

## Summary

total: 6
passed: 2
issues: 1
pending: 0
skipped: 2
blocked: 1

## Gaps

- truth: "Running /post-summary as admin generates and posts a public summary to the summary channel with a Requested by footer"
  status: failed
  reason: "User reported: Nope. Something went wrong."
  severity: major
  test: 3
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
