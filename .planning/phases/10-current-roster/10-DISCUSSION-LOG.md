# Phase 10: Current Roster - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-08
**Phase:** 10-current-roster
**Areas discussed:** Data source & import, Command design, Roster identity, Display & filtering

---

## Data Source & Import

### How should roster players be added?

| Option | Description | Selected |
|--------|-------------|----------|
| Bulk import from API | A /roster-import command pulls the full KU roster from CFBD/CBBD API in one shot | ✓ |
| Manual one-by-one | Same pattern as /recruit-add and /transfer-add — editors add players individually | |
| Hybrid | Bulk import plus manual /roster-add for corrections | |

**User's choice:** Bulk import from API
**Notes:** None

### Should /roster-import replace or merge?

| Option | Description | Selected |
|--------|-------------|----------|
| Replace | Each import wipes current roster and replaces with fresh API data | ✓ |
| Merge | Import adds new players and updates existing, keeps manually-added players | |

**User's choice:** Replace
**Notes:** None

### Should stats be fetched for every player during bulk import?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, fetch all stats | Import fetches career stats for every roster player (~85 API calls for football) | ✓ |
| Fetch on first /career lookup | Import stores roster data without stats, fetched lazily on first lookup | |
| No stats for roster | Roster is just a player directory, /career only works for recruits/transfers | |

**User's choice:** Yes, fetch all stats
**Notes:** None

### Who can run /roster-import?

| Option | Description | Selected |
|--------|-------------|----------|
| Editors + Admins | Same permission as /recruit-add and /transfer-add | ✓ |
| Admins only | Only ADMIN_USER_IDS can import | |

**User's choice:** Editors + Admins
**Notes:** None

---

## Command Design

### What commands should exist for roster management?

| Option | Description | Selected |
|--------|-------------|----------|
| /roster-import + /roster-list | Two commands: import pulls full roster, list displays it. No add/remove | ✓ |
| + /roster-remove | Three commands: import, list, and remove individual players | |
| Full CRUD | Import + add + remove + list — full management suite | |

**User's choice:** /roster-import + /roster-list
**Notes:** None

### How should /roster-import show progress?

| Option | Description | Selected |
|--------|-------------|----------|
| Deferred response with summary | Bot responds with 'Importing...' then edits message when done | |
| Ephemeral 'working' then final embed | Ephemeral 'Importing...' response, then final ephemeral embed with results | ✓ |
| You decide | Claude picks the best approach | |

**User's choice:** Ephemeral 'working' then final embed
**Notes:** None

### Does /roster-import need a year/season parameter?

| Option | Description | Selected |
|--------|-------------|----------|
| Current season only | Always imports latest/current season roster | ✓ |
| Optional year parameter | Defaults to current but allows specifying a year | |

**User's choice:** Current season only
**Notes:** None

---

## Roster Identity

### Where should roster data live?

| Option | Description | Selected |
|--------|-------------|----------|
| Separate roster.json | New data/roster.json with its own RecruitingStore instance | ✓ |
| Merge into transfers.json | Roster players as type='roster' in transfers.json | |
| Single unified players.json | Consolidate all three lists into one file | |

**User's choice:** Separate roster.json
**Notes:** User asked about performance with large football rosters. All options comparable in speed since JSON loads fully into memory. Separate file chosen for clean separation.

### What fields should roster players have?

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse PlayerEntry as-is | Name, position, stars, stats + jersey number in new field | ✓ |
| New RosterEntry dataclass | Separate dataclass with roster-specific fields | |
| You decide | Claude picks based on API data | |

**User's choice:** Reuse PlayerEntry but without school field (always Kansas, not needed)
**Notes:** User specified school field is unnecessary for roster players since they're all KU players.

---

## Display & Filtering

### How should /roster-list organize players?

| Option | Description | Selected |
|--------|-------------|----------|
| Grouped by position | Players grouped under position headers (QB, RB, WR, etc.) | |
| Alphabetical by name | Simple A-Z list | ✓ |
| By jersey number | Sorted by jersey number | |

**User's choice:** Alphabetical by name
**Notes:** None

### How should large rosters be paginated?

| Option | Description | Selected |
|--------|-------------|----------|
| Multi-embed split | Auto-split at 25 fields per embed, all sent in one response | ✓ |
| Button pagination | Interactive buttons to navigate pages | |
| Position filter parameter | Optional position param to reduce output size | |

**User's choice:** Multi-embed split
**Notes:** None

### What info should each roster player show?

| Option | Description | Selected |
|--------|-------------|----------|
| Name + Position + Jersey # | Compact: 'John Smith — QB #7' | |
| Name + Position only | Minimal, same as recruit/transfer format | |
| Name + Position + Jersey # + Class | Fuller: 'John Smith — QB #7 (Jr.)' | ✓ |

**User's choice:** Name + Position + Jersey # + Class
**Notes:** None

---

## Claude's Discretion

- API failure handling during bulk import (partial imports, retry logic)
- Jersey number and class year field additions to PlayerEntry
- CBBD player ID resolution for roster lookup
- Embed formatting details
- Error message wording

## Deferred Ideas

None — discussion stayed within phase scope
