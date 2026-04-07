# Phase 8: Transfer Portal - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md -- this log preserves the alternatives considered.

**Date:** 2026-04-07
**Phase:** 08-transfer-portal
**Areas discussed:** Portal command design, Basketball portal management, Caching strategy, Pagination UX

---

## Portal Command Design

| Option | Description | Selected |
|--------|-------------|----------|
| Single /portal (Recommended) | One command, sport auto-detected from channel | |
| Separate /portal-football + /portal-basketball | Dedicated commands per sport | |
| Single /portal with sport param | One command with required sport dropdown | |

**User's choice:** User clarified that /portal does not need to be separate from /transfer. Transfer portal is KU-focused only (transfers out of KU + portal targets for KU). The existing /transfer-* commands should handle this.

| Option | Description | Selected |
|--------|-------------|----------|
| Type param on /transfer-add (Recommended) | Add 'type' param: outgoing or target | ✓ |
| Separate commands | /transfer-out-add + /transfer-target-add | |
| Single list, no distinction | All transfers in one flat list | |

**Notes:** User's key insight: "We are only going to focus on transfers out of KU and portal targets for KU." This reframed the entire phase from a general portal lookup to an extension of existing transfer commands.

### School Selection

| Option | Description | Selected |
|--------|-------------|----------|
| Free text with autocomplete (Recommended) | User types and gets suggestions | ✓ |
| Free text only | Exact name required | |
| Dropdown of popular schools | Predefined ~25 schools | |

---

## Basketball Portal Management

| Option | Description | Selected |
|--------|-------------|----------|
| Identical handling (Recommended) | Same commands, fields, sport from channel | ✓ |
| Different fields per sport | Sport-specific metadata | |

### Display

| Option | Description | Selected |
|--------|-------------|----------|
| Grouped by type (Recommended) | Two sections: 'Transfers Out' then 'Transfer Targets' | ✓ |
| Mixed with type indicator | All in one list with emoji tags | |
| Separate embeds per type | Two distinct embeds | |

---

## Caching Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Drop PORTAL-05 (Recommended) | No API = no caching needed | |
| Reinterpret as query cache | Cache formatted embed results | |
| Keep for future CFBD | Build cache infrastructure now for Phase 9 | ✓ |

**Notes:** User wants forward investment in cache infrastructure even though this phase is all admin-curated.

---

## Pagination UX

### Page Size

| Option | Description | Selected |
|--------|-------------|----------|
| 10 players per page (Recommended) | Readable density | ✓ |
| 15 players per page | More compact | |
| 25 players per page | Discord max fields | |

### Button Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Prev/Next with timeout (Recommended) | Two buttons, expire after 2 min | |
| Prev/Next + Jump to page | Add page dropdown | |
| No pagination, just split embeds | Send all pages as separate embeds | ✓ |

---

## Claude's Discretion

- Cache implementation details
- Type field storage format in JSON
- Error messages for invalid inputs
- Embed section header formatting

## Deferred Ideas

- CFBD API auto-population for football portal (Phase 9)
- General school-wide portal lookup (future phase)
- Button-based pagination (if lists grow large)
