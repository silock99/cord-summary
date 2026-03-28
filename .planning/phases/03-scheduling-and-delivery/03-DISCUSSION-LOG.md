# Phase 3: Scheduling and Delivery - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-27
**Phase:** 03-scheduling-and-delivery
**Areas discussed:** Scheduled summary scope, DM opt-in mechanism, Thread delivery, Multi-channel overnight

---

## Scheduled Summary Scope

### Q1: Channel coverage

| Option | Description | Selected |
|--------|-------------|----------|
| All allowed channels | Every channel in ALLOWED_CHANNEL_IDS gets summarized overnight. Same allowlist as /summary. | ✓ |
| Separate scheduled list | New env var controls which channels get overnight summaries independently. | |
| All server channels | Summarize every text channel that had activity. No allowlist filtering. | |

**User's choice:** All allowed channels (Recommended)
**Notes:** None

### Q2: Posting destination

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated #summaries channel | All overnight summaries go to SUMMARY_CHANNEL_ID. One central place. | ✓ |
| Back to each source channel | Each channel's summary posted in that channel. | |
| Both | Post to #summaries AND each source channel. | |

**User's choice:** Dedicated #summaries channel (Recommended)
**Notes:** None

### Q3: Quiet channel handling

| Option | Description | Selected |
|--------|-------------|----------|
| Skip silently | Only post for channels with activity above quiet threshold. | ✓ |
| List quiet channels | Include a note naming channels with no activity. | |
| Always post per channel | Post an embed for every allowed channel, even if quiet. | |

**User's choice:** Skip silently (Recommended)
**Notes:** None

---

## DM Opt-in Mechanism

### Q1: Opt-in method (initial)

| Option | Description | Selected |
|--------|-------------|----------|
| Slash command toggle | /summary-dm on/off. State in memory, resets on restart. | |
| Env var user list | Admin lists user IDs in env var. No self-service. | |
| Reaction-based | React with 📩 on a summary to get it DM'd. One-time. | |

**User's choice:** Other — "No DM option if it costs more tokens"
**Notes:** User was concerned about additional LLM token cost. Clarified that DMs re-use already-generated summaries (zero extra LLM calls).

### Q2: Opt-in method (after clarification)

| Option | Description | Selected |
|--------|-------------|----------|
| Slash command toggle | /summary-dm toggle. Same embed sent to DMs. No extra tokens. | ✓ |
| Reaction-based | React with 📩 on posted summary to get DM'd. No persistent state. | |
| Skip DMs entirely | Drop OUT-03. Users read in #summaries only. | |

**User's choice:** Slash command toggle (Recommended)
**Notes:** None

### Q3: Persistence

| Option | Description | Selected |
|--------|-------------|----------|
| Accept reset on restart | Users re-run /summary-dm after restart. Simple. | |
| JSON file persistence | Save opted-in user IDs to local JSON. Survives restarts. | ✓ |
| Env var list instead | Admin pre-configures recipients. Always persistent. | |

**User's choice:** JSON file persistence
**Notes:** None

### Q4: DM trigger

| Option | Description | Selected |
|--------|-------------|----------|
| Scheduled only | DMs fire with 9am overnight summary. On-demand stays ephemeral. | ✓ |
| Both scheduled and on-demand | DM opted-in users get copies of all summaries. | |
| User chooses per-command | Add 'dm' option to /summary for on-demand DM. | |

**User's choice:** Scheduled only (Recommended)
**Notes:** None

---

## Thread Delivery

### Q1: Thread usage

| Option | Description | Selected |
|--------|-------------|----------|
| Daily thread | 9am post creates a thread. All channel summaries inside it. | |
| Regular messages, no threads | Post embeds directly in #summaries. Simple. | ✓ |
| Admin-configurable | Env var toggle for threaded vs flat posting. | |

**User's choice:** Regular messages, no threads
**Notes:** None

### Q2: OUT-04 compliance

| Option | Description | Selected |
|--------|-------------|----------|
| Optional env var toggle | USE_THREADS=true/false (default false). Satisfies OUT-04 while respecting flat preference. | ✓ |
| Drop OUT-04 | Remove thread support entirely from v1. | |

**User's choice:** Optional env var toggle (Recommended)
**Notes:** User prefers flat messages but accepted toggle to satisfy requirement OUT-04.

---

## Multi-Channel Overnight

### Q1: Post structure

| Option | Description | Selected |
|--------|-------------|----------|
| One embed per channel | Separate embed per active channel, posted sequentially. | ✓ |
| One combined summary | Single LLM call merges all channels. Fewer messages. | |
| One message with sections | Single embed with channel-labeled sections. | |

**User's choice:** One embed per channel (Recommended)
**Notes:** None

### Q2: Concurrency

| Option | Description | Selected |
|--------|-------------|----------|
| Sequential | One channel at a time. Simpler, respects rate limits. | ✓ |
| Parallel with limit | Concurrent calls with semaphore. Faster. | |

**User's choice:** Sequential (Recommended)
**Notes:** None

### Q3: Error handling

| Option | Description | Selected |
|--------|-------------|----------|
| Continue others, report failure | Skip failed channel, post others, include error note. | ✓ |
| Abort entire batch | If any fails, skip whole overnight post. | |
| Retry once, then skip | Retry failed channel once before skipping. | |

**User's choice:** Continue others, report failure (Recommended)
**Notes:** None

---

## Claude's Discretion

- Exact slash command name/params for DM toggle
- JSON file location and format for DM subscribers
- Thread naming convention and auto-archive duration
- Scheduling implementation details
- Embed visual differentiation between scheduled and on-demand

## Deferred Ideas

None — discussion stayed within phase scope
