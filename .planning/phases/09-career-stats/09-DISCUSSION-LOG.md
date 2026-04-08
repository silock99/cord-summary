# Phase 9: Career Stats - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-08
**Phase:** 09-career-stats
**Areas discussed:** Command interface, Stats display format, API integration approach, Name matching strategy

---

## Command Interface

| Option | Description | Selected |
|--------|-------------|----------|
| New /stats command | Standalone /stats with player name param | |
| Extend /recruit-list | Add stats button/param to existing list command | |
| New /career command | Standalone /career emphasizing college career stats | ✓ |

**User's choice:** New /career command
**Notes:** None

---

### Player Input Method

| Option | Description | Selected |
|--------|-------------|----------|
| Name parameter with autocomplete | Autocomplete from recruiting list, discord.py callback pattern | ✓ |
| Name parameter, no autocomplete | Free-text with fuzzy matching | |
| Dropdown from recruiting list | Select menu, limited to 25 choices | |

**User's choice:** Name parameter with autocomplete
**Notes:** None

---

### Player Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Recruiting list only | Only show/search recruiting list players | |
| Any player name | Accept any name, hit API directly | |

**User's choice:** Recruiting list only (initially)
**Notes:** None

---

### Which Lists

| Option | Description | Selected |
|--------|-------------|----------|
| Both lists | Recruiting + transfer list players | |
| Recruiting list only | Only high school recruits | |
| All three: recruits + transfers + any name | Search lists first, freeform API lookup as fallback | ✓ |

**User's choice:** All three: recruits + transfers + any name
**Notes:** User expanded scope beyond initial "recruiting list only" to include transfer list and freeform fallback

---

## Stats Display Format

| Option | Description | Selected |
|--------|-------------|----------|
| Season-per-row table | Monospace code block, one row per season, column headers | ✓ |
| Field-per-season | One embed field per season, pipe-separated stats | |
| Single summary line | Career totals only, no per-season breakdown | |

**User's choice:** Season-per-row table
**Notes:** User confirmed via preview showing aligned monospace table with separator line

---

### Career Totals

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, always | Career totals row always shown | |
| Only if multiple seasons | Totals row when 2+ seasons exist | ✓ |
| No totals row | Per-season data only | |

**User's choice:** Only if multiple seasons
**Notes:** None

---

### Football Stat Categories

| Option | Description | Selected |
|--------|-------------|----------|
| Position-relevant only | QB=passing+rushing, RB=rushing+receiving, WR=receiving | ✓ |
| All categories always | Show passing, rushing, receiving for every player | |
| Data-driven | Show any non-zero category | |

**User's choice:** Position-relevant only
**Notes:** None

---

## API Integration Approach

**Major pivot:** User rejected all three proposed architectural options (Protocol interface, single client, direct API calls) and specified a fundamentally different approach: fetch stats at add-time and store locally in JSON.

| Option | Description | Selected |
|--------|-------------|----------|
| Protocol interface | StatsProvider Protocol with CFBD/CBBD implementations | |
| Single client, sport switch | One class routing to CFBD/CBBD internally | |
| Direct API calls in command | aiohttp in command handler | |
| Fetch at add-time, store locally | (User-proposed) Call API when player is added, store in JSON, delete on remove | ✓ |

**User's choice:** Fetch at add-time, store locally in JSON
**Notes:** This changes the architecture from on-demand lookup to pre-fetch. Stats become a data layer concern embedded in player entries.

---

### Stats Freshness

| Option | Description | Selected |
|--------|-------------|----------|
| Fetch once at add-time | Never updated after initial fetch | ✓ |
| Fetch at add-time + manual refresh | Re-fetch command available | |
| Fetch at add-time + daily auto-refresh | Background task refreshes daily | |

**User's choice:** Fetch once at add-time
**Notes:** Simplest, minimizes API calls within 1,000/month limit

---

### API Failure Policy

| Option | Description | Selected |
|--------|-------------|----------|
| Add player anyway, no stats | Player added, /career shows "no stats available" | ✓ |
| Warn but still add | Add with explicit warning about failed fetch | |
| Block the add | Don't add if stats can't be fetched | |

**User's choice:** Add player anyway, no stats
**Notes:** List management should not depend on API availability

---

### Stats Storage Location

| Option | Description | Selected |
|--------|-------------|----------|
| Embedded in player entry | Stats field in PlayerEntry within recruits.json / transfers.json | ✓ |
| Separate stats JSON file | data/stats.json keyed by player | |
| Per-player files | data/stats/{sport}/{name}.json | |

**User's choice:** Embedded in player entry
**Notes:** Stats travel with the player, no separate file to sync

---

### SDK Choice

User asked "What is the CFBD structure" before answering — triggered research into CFBD and CBBD API documentation.

| Option | Description | Selected |
|--------|-------------|----------|
| Use official SDKs (cfbd + cbbd) | Python SDKs handle auth, pagination, response typing | ✓ |
| Direct aiohttp calls | Skip SDKs, call REST APIs directly | |
| You decide | Claude picks | |

**User's choice:** Use official SDKs (cfbd + cbbd)
**Notes:** After reviewing API structure (endpoints, auth, response format)

---

## Name Matching Strategy

### At Add-Time (API Lookup)

| Option | Description | Selected |
|--------|-------------|----------|
| Search API + auto-match | 1 result = use it, multiple = match by school, none = no stats | ✓ |
| Search API + disambiguation | Multiple results shown to user for selection | |
| Exact name match only | No fuzzy, exact API name match | |

**User's choice:** Search API + auto-match
**Notes:** None

---

### At /career Time (Local Lookup)

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, reuse Phase 7 fuzzy matching | difflib.get_close_matches, cutoff=0.6, "did you mean?" | ✓ |
| Exact match only | Autocomplete handles it, no fuzzy fallback | |
| You decide | Claude picks | |

**User's choice:** Yes, reuse Phase 7 fuzzy matching
**Notes:** Consistent with existing remove-command pattern

---

## Claude's Discretion

- Internal structure of the `stats` field in PlayerEntry
- Error message wording for stats not available / API failures
- CBBD player ID resolution flow (roster lookup)
- Whether to use Protocol interface or simple functions for stats fetching layer

## Deferred Ideas

- Manual /career-refresh command for re-fetching stats
- Daily auto-refresh during active seasons
- General school-wide portal lookup
- Player comparison features
