# Phase 2: On-Demand Summarization - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-27
**Phase:** 02-on-demand-summarization
**Areas discussed:** Slash command UX, Summary formatting, Channel targeting, Quiet channel handling

---

## Slash Command UX

### Default Time Range
| Option | Description | Selected |
|--------|-------------|----------|
| 1 hour | Covers recent discussion | |
| 2 hours | Wider window | |
| 30 minutes | Tight window | |
| 4 hours (Other) | User-specified custom value | ✓ |

**User's choice:** 4 hours
**Notes:** User specified custom value rather than picking a preset

### Time Range Input Style
| Option | Description | Selected |
|--------|-------------|----------|
| Preset choices | Dropdown with options like '30 min', '1 hour', '4 hours', '12 hours', '24 hours' | ✓ |
| Free number input | User types a number of hours | |
| Both presets and custom | Preset dropdown plus custom_hours option | |

**User's choice:** Preset choices

### Response Destination
| Option | Description | Selected |
|--------|-------------|----------|
| Summary channel only | Post to #summaries, user gets ephemeral confirmation | |
| Summary channel + preview | Post to #summaries AND ephemeral preview | |
| Ephemeral to user only | Only the user sees it | ✓ |

**User's choice:** Ephemeral only. User clarified: "User-initiated summaries are only ephemeral. The summaries channel should post automatically at specified intervals."
**Notes:** This changes OUT-01 scope — dedicated channel posting moves to Phase 3

### Deferral Strategy
| Option | Description | Selected |
|--------|-------------|----------|
| Defer + ephemeral thinking | Ephemeral 'Generating summary...' then follow up | ✓ |
| Defer + public thinking | Public thinking indicator | |
| Defer silently | No indicator | |

**User's choice:** Ephemeral defer (inferred from ephemeral-only decision)

---

## Summary Formatting

### Structure
| Option | Description | Selected |
|--------|-------------|----------|
| Bold topic headers + bullets | Topics as bold headers with bullet points | ✓ |
| Flat bullets, no grouping | Simple chronological list | |

**User's choice:** Bold topic headers + bullets
**Notes:** User explicitly removed action items from scope before this question was asked ("For this implementation, there won't be action items")

### Long Summary Handling
| Option | Description | Selected |
|--------|-------------|----------|
| Multiple embeds | Split into multiple embeds, breaking at topic boundaries | ✓ |
| Truncate with note | Cut at 4096 chars | |
| Ask LLM to be shorter | Re-prompt with length constraint | |

**User's choice:** Multiple embeds

---

## Channel Targeting

### Channel Selection
| Option | Description | Selected |
|--------|-------------|----------|
| Default to current channel | /summary in #general summarizes #general, optional channel param | ✓ (modified) |
| Always require pick | Must choose every time | |
| Summarize all channels | One command, all channels | |

**User's choice:** Default to current channel IF on admin allowlist
**Notes:** "Admin can control the channels you can summarize, but user will default to current channel, if available from admin"

### Allowlist Configuration
| Option | Description | Selected |
|--------|-------------|----------|
| Env var with channel IDs | ALLOWED_CHANNEL_IDS in .env | ✓ |
| Slash command for admins | /summary-config add #channel | |
| All channels by default | No allowlist | |

**User's choice:** Env var with channel IDs

### Non-Allowed Channel Response
| Option | Description | Selected |
|--------|-------------|----------|
| Ephemeral error + list allowed | Show error with available channels | ✓ |
| Ephemeral error only | Just error, no guidance | |
| Silently allow current channel | Ignore allowlist for current | |

**User's choice:** Ephemeral error + list allowed channels

---

## Quiet Channel Handling

### Activity Threshold
| Option | Description | Selected |
|--------|-------------|----------|
| Zero messages | Only 'no activity' with zero messages | |
| Fewer than 3 messages | 1-2 messages not worth summarizing | |
| Fewer than 5 messages | Higher threshold | ✓ |

**User's choice:** Fewer than 5 messages

### Below-Threshold Response
| Option | Description | Selected |
|--------|-------------|----------|
| Quote messages directly | Show actual messages, no LLM call | |
| Simple 'no activity' message | Just say no significant activity | ✓ |
| Summarize anyway | Send to LLM regardless | |

**User's choice:** Simple 'no activity' message

---

## Claude's Discretion

- Embed color, footer text, metadata styling
- Exact wording of deferred "generating..." message
- Multi-embed splitting algorithm at topic boundaries
- Channel dropdown visibility (all allowed vs user-visible only)

## Deferred Ideas

- OUT-01 (dedicated summary channel posting) — moved to Phase 3 for scheduled auto-posts
- SUM-04 (action items extraction) — removed from scope per user decision
