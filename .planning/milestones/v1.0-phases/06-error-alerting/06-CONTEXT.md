# Phase 6: Error Alerting - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers two capabilities:
1. **Error alerting** — DM-based error notifications to configured admins when summary generation or delivery fails
2. **Admin-only manual summary trigger** — A `/post-summary` slash command that posts a public summary to the summary channel, restricted to admin users

</domain>

<decisions>
## Implementation Decisions

### Error Notification Target
- **D-01:** Error alerts are sent as DMs to users listed in `ADMIN_USER_IDS` env var (comma-separated, same pattern as existing `COOLDOWN_EXEMPT_USER_IDS`)
- **D-02:** Remove existing red error embeds from the summary channel (overnight.py:132-146). All errors go to DMs only — keeps the summary channel clean
- **D-03:** Error DMs use embed format with fields: error type, channel, timestamp, and traceback snippet
- **D-04:** Errors from a single scheduled run are batched into one DM (not one DM per error). Collect all errors, send a single embed with all of them

### Alert Triggers & Severity
- **D-05:** All errors that prevent summary generation or delivery trigger alerts: LLM API failures (rate limits, timeouts, auth), channel/permission issues (channel not found, missing perms, guild not in cache), and scheduled task failures
- **D-06:** No severity levels — all errors are treated equally. Single batched embed per run

### Manual Summary Command
- **D-07:** New `/post-summary` slash command, separate from `/summary`. Posts a public summary to the summary channel
- **D-08:** Reuse the same time range dropdown choices as `/summary` (30m, 1h, 4h, 12h, 24h)
- **D-09:** Admin picks one channel to summarize (channel parameter with same autocomplete as `/summary`)
- **D-10:** No confirmation step — admin runs it, it posts immediately
- **D-11:** Respects `use_threads` setting — if enabled, creates a thread in the summary channel like scheduled summaries do
- **D-12:** Exempt from summary cooldown — admins can trigger as often as needed
- **D-13:** Command is visible to all users in the command list, but only admin user IDs can execute it. Non-admins get a vague "You don't have permission to use this command." ephemeral response

### Admin Access Control
- **D-14:** Single `ADMIN_USER_IDS` env var controls both error alert DM recipients AND `/post-summary` access
- **D-15:** `ADMIN_USER_IDS` replaces `COOLDOWN_EXEMPT_USER_IDS` — admins are automatically cooldown-exempt for `/summary` too. Remove the old env var
- **D-16:** If `ADMIN_USER_IDS` is empty or not set: error alerts are silently skipped (just logged), `/post-summary` rejects everyone. No startup warning needed

### Claude's Discretion
- Error embed color and field layout for DMs
- How to structure the batched error embed (numbered list vs fields)
- Internal error collection mechanism (list accumulation pattern already exists in overnight.py)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Error Handling
- `src/bot/scheduling/overnight.py` — Current error handling in `_post_summary()` (lines 86-147): error collection, red embed posting, error handlers for tasks. This is where error DMs replace the existing summary channel embeds
- `src/bot/scheduling/overnight.py` — `_on_overnight_error` and `_on_hourly_error` handlers (lines 57-60)

### Command Pattern
- `src/bot/commands/summary.py` — Existing `/summary` command: registration pattern, time range choices, channel autocomplete, cooldown logic, ephemeral response pattern. `/post-summary` mirrors much of this
- `src/bot/client.py` — `setup_hook()` command registration pattern (line 27)

### Config Pattern
- `src/bot/config.py` — Settings class with `.env` loading: `COOLDOWN_EXEMPT_USER_IDS` pattern (lines 38-48) to replicate for `ADMIN_USER_IDS`. This env var gets replaced/merged

### Delivery
- `src/bot/delivery/threads.py` — Thread creation for `use_threads` support
- `src/bot/formatting/embeds.py` — Embed building utilities

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `OvernightScheduler._post_summary()` — Contains the full pipeline (fetch channels, summarize, post embeds, collect errors). The manual summary command can reuse `summarize_channel()` directly
- `TIMERANGE_CHOICES` and `channel_autocomplete` in summary.py — Reusable for `/post-summary` command
- `build_summary_embeds()` — Embed formatting, reusable for public posting
- `create_summary_thread()` — Thread creation, reusable when `use_threads` is enabled

### Established Patterns
- Command registration: `register_X_command(bot)` function called in `setup_hook()`
- Config parsing: `computed_field` with raw string field + comma split for list env vars
- Cooldown tracking: dict-based `{user_id: datetime}` pattern (can be bypassed for admins)
- Error handling: `SummaryError` exception for LLM failures, generic `Exception` catch for others

### Integration Points
- `setup_hook()` in client.py — Register new `/post-summary` command
- `config.py` Settings — Add `ADMIN_USER_IDS`, remove `COOLDOWN_EXEMPT_USER_IDS`
- `overnight.py` `_post_summary()` — Replace error embed posting with DM-based alerting
- `summary.py` cooldown check — Replace `cooldown_exempt_user_ids` with `admin_user_ids`

</code_context>

<specifics>
## Specific Ideas

- The error DM batching should mirror how overnight.py already collects errors in a list and posts them at the end — same pattern, different destination (DM instead of channel embed)
- `/post-summary` should feel like a targeted version of the overnight task: same summarize_channel pipeline, same embed formatting, same thread behavior — just triggered manually for one channel

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 06-error-alerting*
*Context gathered: 2026-04-04*
