# Phase 6: Error Alerting - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-04
**Phase:** 06-error-alerting
**Areas discussed:** Error notification target, Alert triggers & severity, Manual summary command, Admin access control

---

## Error Notification Target

| Option | Description | Selected |
|--------|-------------|----------|
| DM to bot owner | Errors DM a configured owner user ID. Private, doesn't clutter server. | |
| Dedicated error channel | New ALERT_CHANNEL_ID env var. Errors post to a separate channel. | |
| Summary channel | Post error embeds to same summary channel. Already partially happens. | |
| DM to list of users (Other) | DM to a list of allowed users defined in an .env variable | ✓ |

**User's choice:** DM to a list of allowed users defined in an .env variable

| Option | Description | Selected |
|--------|-------------|----------|
| DM only | Remove existing red error embeds from summary channel. All errors go to DMs only. | ✓ |
| Both DM and summary channel | Keep existing error embeds AND add DMs. Redundant but visible. | |

**User's choice:** DM only

| Option | Description | Selected |
|--------|-------------|----------|
| Simple text message | Plain text error message. Lightweight. | |
| Embed with details | Red embed with fields: error type, channel, timestamp, traceback snippet. | ✓ |
| Embed, no traceback | Red embed with error type, channel, timestamp. No debug detail. | |

**User's choice:** Embed with details

| Option | Description | Selected |
|--------|-------------|----------|
| One DM per error | Each failure sends its own DM immediately. | |
| Batch per run | Collect all errors from one scheduled run, send a single DM. | ✓ |
| Batch + individual for critical | Batch routine errors, send critical ones immediately. | |

**User's choice:** Batch per run

---

## Alert Triggers & Severity

| Option | Description | Selected |
|--------|-------------|----------|
| LLM API failures | Rate limits, timeouts, auth errors, model errors | |
| Channel/permission issues | Channel not found, missing permissions, guild not in cache | |
| Scheduled task failures | Overnight or hourly task crashes | |
| All of the above | Alert on any error that prevents summary generation or delivery | ✓ |

**User's choice:** All of the above

| Option | Description | Selected |
|--------|-------------|----------|
| All errors equal | Every error gets same treatment. Simple, no classification logic. | ✓ |
| Two levels: warning + critical | Warnings batch normally. Critical errors send immediately. | |

**User's choice:** All errors equal

---

## Manual Summary Command

| Option | Description | Selected |
|--------|-------------|----------|
| New /post-summary command | Separate slash command. Posts to summary channel on demand. | ✓ |
| Flag on existing /summary | Add "public: true" option to /summary. Overloads existing command. | |

**User's choice:** New /post-summary command

| Option | Description | Selected |
|--------|-------------|----------|
| Same choices as /summary | Reuse existing time range dropdown (30m, 1h, 4h, 12h, 24h). | ✓ |
| Fixed overnight window only | Always posts the 10pm-9am window. | |
| Custom start/end times | Let admin type specific start and end times. | |

**User's choice:** Same choices as /summary

| Option | Description | Selected |
|--------|-------------|----------|
| Admin picks one channel | Channel parameter with same autocomplete. One summary at a time. | ✓ |
| All allowed channels | Summarize every allowed channel in one go. | |
| Choice of one or all | Optional param — omit for all, specify for one. | |

**User's choice:** Admin picks one channel

| Option | Description | Selected |
|--------|-------------|----------|
| No confirmation | Just run it. Admin knows what they're doing. | ✓ |
| Ephemeral preview first | Show summary privately first, then "Post it" button. | |

**User's choice:** No confirmation

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, respect use_threads | Creates thread if enabled, consistent with scheduled summaries. | ✓ |
| Always post directly | Ignore thread setting, post as regular message. | |

**User's choice:** Yes, respect use_threads

| Option | Description | Selected |
|--------|-------------|----------|
| Exempt from cooldown | Admins can trigger as often as needed. Different use case. | ✓ |
| Respect cooldown | Same cooldown rules as /summary apply. | |

**User's choice:** Exempt from cooldown

| Option | Description | Selected |
|--------|-------------|----------|
| Hidden from non-admins | Command doesn't appear for regular users. | |
| Visible but rejected (Other) | Everyone sees it, but non-admins get rejection. | ✓ |

**User's choice:** Visible to all, but only .env-listed user IDs can trigger it. Non-admins get permission denied.

---

## Admin Access Control

| Option | Description | Selected |
|--------|-------------|----------|
| Single shared list | One ADMIN_USER_IDS env var for both error DMs and /post-summary. | ✓ |
| Separate lists | ALERT_USER_IDS for DMs, ADMIN_USER_IDS for /post-summary. | |

**User's choice:** Single shared list

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, merge | ADMIN_USER_IDS replaces COOLDOWN_EXEMPT_USER_IDS. Admins auto-exempt. | ✓ |
| Keep separate | Keep COOLDOWN_EXEMPT_USER_IDS alongside new ADMIN_USER_IDS. | |

**User's choice:** Yes, merge

| Option | Description | Selected |
|--------|-------------|----------|
| No alerts, command rejected | Silently skip alerts, reject everyone from /post-summary. | ✓ |
| Warn at startup | Log warning about missing config, then same behavior. | |

**User's choice:** No alerts, command rejected

| Option | Description | Selected |
|--------|-------------|----------|
| Vague message | "You don't have permission to use this command." | ✓ |
| Explicit message | "Only admins can use this command. Contact the bot owner." | |

**User's choice:** Vague message

---

## Claude's Discretion

- Error embed color and field layout for DMs
- Batched error embed structure (numbered list vs fields)
- Internal error collection mechanism

## Deferred Ideas

None — discussion stayed within phase scope
