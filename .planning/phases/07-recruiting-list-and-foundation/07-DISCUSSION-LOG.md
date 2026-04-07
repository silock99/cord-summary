# Phase 7: Recruiting List and Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-07
**Phase:** 07-recruiting-list-and-foundation
**Areas discussed:** List display format, Add/remove interface, Authorization scope, Channel-sport mapping

---

## List Display Format

### Layout Style

| Option | Description | Selected |
|--------|-------------|----------|
| Table-style embed | Aligned columns — Name, Pos, School, Stars | |
| Field-per-player embed | Each player gets own embed field with visual separation | ✓ |
| Compact bullet list | Simple bulleted list in embed description | |

**User's choice:** Field-per-player embed
**Notes:** None

### Sorting

| Option | Description | Selected |
|--------|-------------|----------|
| By star rating (highest first) | Best recruits at top | |
| By date added (newest first) | Most recent additions at top | |
| By position | Grouped by position | ✓ |
| You decide | Claude picks | |

**User's choice:** By position
**Notes:** "These are transfers. Star ratings are good, but they are only for high school players, not necessarily college transfers."

### Pagination

| Option | Description | Selected |
|--------|-------------|----------|
| Button navigation | Next/Previous buttons, ~5 players per page | |
| Single scrollable embed | All players in one embed, auto-split if needed | ✓ |
| You decide | Claude picks | |

**User's choice:** Single scrollable embed

---

## Add/Remove Interface

### Add Command Style

| Option | Description | Selected |
|--------|-------------|----------|
| Single slash command | All params in one command | ✓ |
| Discord modal (form popup) | Form popup with labeled fields | |
| Subcommand group | /recruit add, /recruit remove, /recruit list | |

**User's choice:** Single slash command

### Removal Method

| Option | Description | Selected |
|--------|-------------|----------|
| By player name | Fuzzy match if no exact match | ✓ |
| Interactive selection | Numbered list, user picks | |
| By name with confirmation | Name-based with confirmation button | |

**User's choice:** By player name with fuzzy matching

### Command Naming

| Option | Description | Selected |
|--------|-------------|----------|
| Separate commands | /recruit-add, /recruit-remove, /recruit-list | ✓ |
| Subcommand group | /recruit add, /recruit remove, /recruit list | |

**User's choice:** Separate top-level commands

### Position Input

| Option | Description | Selected |
|--------|-------------|----------|
| Free text | User types any position string | ✓ |
| Autocomplete with presets | Suggests common positions, allows custom | |
| You decide | Claude picks | |

**User's choice:** Free text

### Recruits vs Transfers Separation

| Option | Description | Selected |
|--------|-------------|----------|
| Separate commands | /recruit-* and /transfer-* as distinct command sets | ✓ |
| Type parameter | Single command set with type:recruit or type:transfer param | |
| Single list with label | Unified list, players tagged as recruit or transfer | |

**User's choice:** Separate commands (6 total)
**Notes:** "We might need a separate command and list for recruits vs transfers. Same structure but recruit is for high school recruits and transfer is for college transfers."

### Storage

| Option | Description | Selected |
|--------|-------------|----------|
| Separate JSON files | recruits.json and transfers.json | ✓ |
| Single JSON file | One file with type field per entry | |
| You decide | Claude picks | |

**User's choice:** Separate JSON files

---

## Authorization Scope

### Editor Permissions

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse ADMIN_USER_IDS | Same admins manage lists | |
| Separate RECRUITING_EDITOR_IDS | New env var for recruiting editors | ✓ |
| Discord role-based | Check for Discord role | |

**User's choice:** Separate RECRUITING_EDITOR_IDS

### Admin Inheritance

| Option | Description | Selected |
|--------|-------------|----------|
| Admins inherit editor access | ADMIN_USER_IDS automatically includes editor perms | ✓ |
| Strictly separate | Must be in RECRUITING_EDITOR_IDS even if admin | |

**User's choice:** Admins inherit editor access

---

## Channel-Sport Mapping

### Config Format

| Option | Description | Selected |
|--------|-------------|----------|
| Env var with channel:sport pairs | CHANNEL_SPORT_MAP="123:football,456:basketball" | |
| Separate env vars per sport | FOOTBALL_CHANNEL_IDS and BASKETBALL_CHANNEL_IDS | ✓ |
| You decide | Claude picks | |

**User's choice:** Separate env vars per sport

### Unmapped Channel Behavior

**User's choice:** Commands cannot be run in unmapped channels — denied with error message.
**Notes:** "Unmapped channels should not be able to have the commands run in them"

### Sport Parameter

**User's choice:** Drop sport parameter entirely — sport is always determined from channel.
**Notes:** This makes RECRUIT-05 (sport autocomplete dropdown) unnecessary since sport is implicit.

---

## Claude's Discretion

- Error message wording for unauthorized users and unmapped channels
- Internal data model structure for player entries
- File I/O pattern (atomic writes, error handling)

## Deferred Ideas

None — discussion stayed within phase scope
