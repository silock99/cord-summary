# Phase 8: Transfer Portal - Research

**Researched:** 2026-04-07
**Domain:** discord.py command extension, in-memory caching, data model evolution
**Confidence:** HIGH

## Summary

Phase 8 extends the existing `/transfer-*` commands (built in Phase 7) to support two transfer categories: "outgoing" (KU players entering the portal) and "target" (players KU is pursuing). The work is primarily additive: a new `type` field on `PlayerEntry`, a `type` parameter on `/transfer-add`, grouped display in `/transfer-list` (10 players per page), and a standalone cache module for Phase 9 CFBD API readiness.

The codebase is well-structured and the patterns are fully established. `RecruitingStore`, `PlayerEntry`, `transfers.py`, and `recruiting.py` all follow identical patterns. The changes are mechanical: extend the dataclass, extend the store method signatures, update the display logic, and build a simple TTL cache utility.

**Primary recommendation:** Extend the existing `PlayerEntry` dataclass with a `type` field defaulting to `"target"` for backward compatibility, add a `type` choice parameter to `/transfer-add`, rewrite `/transfer-list` display to group by type with section headers, reduce per-embed limit from 25 to 10, and create a standalone `src/bot/storage/cache.py` module with TTL-based in-memory caching.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** No separate `/portal` command. Transfer portal functionality lives entirely within existing `/transfer-add`, `/transfer-remove`, `/transfer-list` commands from Phase 7.
- **D-02:** `/transfer-add` gets a new `type` parameter: "outgoing" (KU player leaving) or "target" (player KU wants). This distinguishes the two transfer categories.
- **D-03:** Sport remains channel-derived (Phase 7 D-16 carries forward). No sport parameter on commands.
- **D-04:** All data is admin-curated for both sports. No API integration in this phase. Editors manually add all transfer entries via `/transfer-add`.
- **D-05:** CFBD API integration deferred to Phase 9 (career stats). Cache infrastructure built now to prepare for it.
- **D-06:** `/transfer-list` groups players by type -- "Transfers Out" section header then those players, followed by "Transfer Targets" section header then those players.
- **D-07:** Identical field handling for both sports. Same fields: name, position, school, stars, type. No sport-specific metadata differences.
- **D-08:** Build cache infrastructure now for future CFBD API use in Phase 9. In-memory cache with TTL support, even though current phase doesn't call external APIs.
- **D-09:** PORTAL-05 (cache API responses 15-30 min TTL) is reinterpreted as forward infrastructure investment, not an active requirement for this phase.
- **D-10:** 10 players per page in `/transfer-list`.
- **D-11:** No button pagination. Large lists split into multiple embeds sent in one response (same pattern as Phase 7 recruit-list with 25-field split, but now at 10 fields per embed).
- **D-12:** PORTAL-04 (button navigation) is replaced by multi-embed splitting. Simpler UX without interactive components.

### Claude's Discretion
- Cache implementation details (dict with timestamps, dataclass wrapper, etc.)
- How to handle the `type` field in the existing JSON storage structure
- Error messages for invalid type values
- Embed section header formatting for type grouping

### Deferred Ideas (OUT OF SCOPE)
- CFBD API integration for auto-populating football portal data (Phase 9)
- General school-wide portal lookup (not KU-focused) -- potential future phase
- Button-based pagination -- could revisit if lists grow very large
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PORTAL-01 | User can look up transfer portal players filtered by sport and school | Fulfilled via existing `/transfer-list` with channel-derived sport (D-01, D-03). School is implicit -- all entries are KU-focused. |
| PORTAL-02 | User can optionally filter portal results by position | Can add optional `position` parameter to `/transfer-list` and filter `list_players()` results. Straightforward string match. |
| PORTAL-03 | Portal results display player name, position, original school, and star rating in embed format | Already displayed in current embed fields. Type grouping (D-06) adds section headers. |
| PORTAL-04 | Portal results paginate with button navigation when exceeding one embed | Reinterpreted per D-12: multi-embed splitting at 10 players/page, no button navigation. |
| PORTAL-05 | Portal API responses are cached (15-30 min TTL) | Reinterpreted per D-09: build cache module infrastructure for Phase 9; no active API calls this phase. |
| PORTAL-06 | Sport auto-detected from channel-to-sport mapping config, with manual override | Already implemented in Phase 7 via `get_sport_from_channel()`. Manual override not needed per D-03 (channel-derived only). |
| INFRA-01 | CFBD API integration for football portal data and stats | Deferred per D-05. Cache infrastructure built now; actual API integration in Phase 9. |
| INFRA-03 | MBB transfer portal uses admin-curated entries (no API available) | Fulfilled by D-04: all data admin-curated via `/transfer-add` for both sports. |
</phase_requirements>

## Architecture Patterns

### Current Structure (Phase 7 output)
```
src/bot/
  commands/
    transfers.py       # /transfer-add, /transfer-remove, /transfer-list
    recruiting.py      # /recruit-add, /recruit-remove, /recruit-list (reference)
  storage/
    models.py          # PlayerEntry dataclass
    recruiting_store.py # RecruitingStore class + get_sport_from_channel()
  config.py            # Settings (pydantic-settings)
  client.py            # SummaryBot with store initialization
data/
  transfers.json       # Persisted transfer entries
```

### Changes Required
```
src/bot/
  commands/
    transfers.py       # MODIFY: add type param, position filter, grouped display, 10/page
  storage/
    models.py          # MODIFY: add type field to PlayerEntry
    recruiting_store.py # MODIFY: add_player() accepts type param
    cache.py           # NEW: standalone TTL cache module
```

### Pattern 1: PlayerEntry Type Extension
**What:** Add `type` field to `PlayerEntry` dataclass with backward-compatible deserialization.
**When to use:** Extending existing data models with new fields that must coexist with old persisted data.
**Example:**
```python
@dataclass
class PlayerEntry:
    name: str
    position: str
    school: str
    stars: int  # 0 for unrated, 1-5 for rated
    added_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    type: str = "target"  # "target" or "outgoing", default for backward compat

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "position": self.position,
            "school": self.school,
            "stars": self.stars,
            "added_at": self.added_at,
            "type": self.type,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PlayerEntry":
        # Backward compat: old entries without 'type' default to "target"
        return cls(**data)  # Works because type has a default value
```

**Key insight:** Because `type` has a default value and `from_dict()` uses `**data`, old JSON entries without a `type` key will deserialize correctly with `type="target"`. No data migration needed.

### Pattern 2: discord.py Choice Parameter
**What:** Use `app_commands.Choice` for the `type` parameter to provide a dropdown.
**When to use:** When a parameter has a fixed set of valid values.
**Example:**
```python
@app_commands.describe(
    type="Transfer type: outgoing (leaving KU) or target (coming to KU)",
)
@app_commands.choices(type=[
    app_commands.Choice(name="Outgoing (leaving KU)", value="outgoing"),
    app_commands.Choice(name="Target (coming to KU)", value="target"),
])
async def transfer_add(
    interaction: discord.Interaction,
    name: str,
    position: str,
    school: str,
    stars: app_commands.Range[int, 0, 5] = 0,
    type: app_commands.Choice[str] = None,  # default to "target" if omitted
) -> None:
    transfer_type = type.value if type else "target"
    ...
```

**Confidence:** HIGH -- `app_commands.Choice` is the standard discord.py pattern for constrained parameter values, already documented in discord.py stable docs.

### Pattern 3: Grouped Embed Display
**What:** Split `/transfer-list` output into type-grouped sections with section headers.
**When to use:** When displaying categorized data in Discord embeds.
**Example:**
```python
TYPE_SECTIONS = [
    ("outgoing", "Transfers Out", "\U0001f6aa"),   # door emoji
    ("target", "Transfer Targets", "\U0001f3af"),   # target emoji
]

# For each type section, filter players and add a section header field
for type_key, section_title, section_emoji in TYPE_SECTIONS:
    typed_players = [p for p in players if p.type == type_key]
    if not typed_players:
        continue
    # Add section header as a field with no value
    current_embed.add_field(
        name=f"{section_emoji} {section_title}",
        value=f"*{len(typed_players)} player(s)*",
        inline=False,
    )
    for player in typed_players:
        # Add player field (counts toward 10-per-page limit)
        ...
```

### Pattern 4: TTL Cache Module
**What:** Standalone in-memory cache with per-key TTL for future CFBD API responses.
**When to use:** Caching expensive API responses with configurable expiration.
**Recommendation (Claude's discretion):** Use a simple dict-based approach with a dataclass wrapper for cache entries. This is lightweight, has no dependencies, and is easy to test.
```python
"""In-memory TTL cache for API responses."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CacheEntry:
    value: Any
    expires_at: float


class TTLCache:
    """Simple in-memory cache with per-key TTL."""

    def __init__(self, default_ttl: float = 900.0) -> None:
        """Initialize cache with default TTL in seconds (default: 15 minutes)."""
        self._store: dict[str, CacheEntry] = {}
        self.default_ttl = default_ttl

    def get(self, key: str) -> Any | None:
        """Get a cached value, or None if missing/expired."""
        entry = self._store.get(key)
        if entry is None:
            return None
        if time.monotonic() > entry.expires_at:
            del self._store[key]
            return None
        return entry.value

    def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        """Store a value with TTL (seconds). Uses default_ttl if not specified."""
        actual_ttl = ttl if ttl is not None else self.default_ttl
        self._store[key] = CacheEntry(
            value=value,
            expires_at=time.monotonic() + actual_ttl,
        )

    def invalidate(self, key: str) -> bool:
        """Remove a specific key. Returns True if key existed."""
        return self._store.pop(key, None) is not None

    def clear(self) -> None:
        """Clear all cached entries."""
        self._store.clear()
```

**Design decisions (Claude's discretion):**
- `time.monotonic()` instead of `time.time()` -- immune to system clock changes.
- Per-key TTL override with a default -- Phase 9 can use different TTLs for different endpoints.
- No automatic eviction/cleanup thread -- entries evicted lazily on `get()`. For a bot serving a single Discord server, memory pressure is negligible.
- Standalone module at `src/bot/storage/cache.py` -- adjacent to the store modules, importable by Phase 9 CFBD integration.

### Anti-Patterns to Avoid
- **Overcomplicating the cache:** Do not use `functools.lru_cache` or `cachetools` -- they don't support TTL per key easily, and adding a dependency for a 40-line class is wasteful.
- **Modifying recruit commands:** The `type` field is for transfers only. `PlayerEntry` gains the field (shared dataclass), but `recruiting.py` should not expose or use it. Recruit entries will simply have `type="target"` (the default) which is harmless.
- **Breaking backward compatibility:** Do NOT require a data migration. The default value on `type` handles old entries automatically.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Choice parameters | Custom string validation | `app_commands.Choice[str]` | Built into discord.py, provides dropdown UI |
| Fuzzy name matching | Custom similarity algorithm | `difflib.get_close_matches` (already used) | Standard library, proven in Phase 7 |

## Common Pitfalls

### Pitfall 1: Field Order in Dataclass
**What goes wrong:** Adding `type: str = "target"` before `added_at` (which also has a default) works, but adding it after non-default fields causes a `TypeError` since default fields can't precede non-default fields.
**Why it happens:** Python dataclass field ordering rules.
**How to avoid:** `type` field goes after `added_at` (both have defaults). Current field order: `name, position, school, stars, added_at, type` -- all of `added_at` and `type` have defaults, so this is valid.
**Warning signs:** `TypeError: non-default argument follows default argument` at import time.

### Pitfall 2: app_commands.Choice Default Value
**What goes wrong:** Making `type` a required `Choice[str]` parameter breaks backward compat with existing `/transfer-add` usage patterns where editors are used to 4 parameters.
**Why it happens:** Forgetting to provide a default.
**How to avoid:** Make `type` optional with a default. If omitted, default to `"target"` (most common case -- KU is pursuing a player).
**Warning signs:** Users reporting the command now requires an extra field they don't understand.

### Pitfall 3: Embed Field Count with Section Headers
**What goes wrong:** Section headers ("Transfers Out", "Transfer Targets") consume embed field slots. If counting only player fields toward the 10-per-page limit, the actual field count exceeds expectations.
**Why it happens:** Section header fields are forgotten in the count.
**How to avoid:** Count player fields only toward the 10-per-page limit. Section headers are "free" -- they don't count. This means an embed might have 12 fields total (2 headers + 10 players) which is well under the 25-field Discord limit.
**Warning signs:** Embeds splitting too early or too late.

### Pitfall 4: `type` is a Python Builtin
**What goes wrong:** Using `type` as a parameter name shadows the builtin `type()` function.
**Why it happens:** `type` is a natural name for this field.
**How to avoid:** This is acceptable in the limited scope of a function parameter. The builtin is rarely needed inside these functions. Alternatively, use `transfer_type` as the internal variable name while keeping `type` as the Discord-facing parameter name.
**Warning signs:** Linting warnings about shadowing builtins.

### Pitfall 5: Position Filter Case Sensitivity
**What goes wrong:** User types "qb" but positions are stored as "QB" -- filter returns no results.
**Why it happens:** Case-sensitive string comparison.
**How to avoid:** Normalize both stored position and filter input to lowercase for comparison.
**Warning signs:** Users reporting empty results when filtering by position.

## Code Examples

### RecruitingStore.add_player with Type
```python
def add_player(
    self, sport: str, name: str, position: str, school: str, stars: int,
    player_type: str = "target",
) -> PlayerEntry | None:
    """Add a player to a sport list. Returns None if duplicate name."""
    players = self._data.get(sport, [])
    if any(p.name.lower() == name.lower() for p in players):
        return None
    entry = PlayerEntry(
        name=name, position=position, school=school,
        stars=stars, type=player_type,
    )
    players.append(entry)
    self._data[sport] = players
    self.save()
    return entry
```

### Position Filter on list_players
```python
def list_players(self, sport: str, position: str | None = None) -> list[PlayerEntry]:
    """Return players for a sport, optionally filtered by position, sorted by position."""
    players = self._data.get(sport, [])
    if position:
        players = [p for p in players if p.position.lower() == position.lower()]
    return sorted(players, key=lambda p: p.position)
```

### Transfer List Grouped Display (key logic)
```python
MAX_PLAYERS_PER_EMBED = 10

# Separate players by type
outgoing = [p for p in players if p.type == "outgoing"]
targets = [p for p in players if p.type == "target"]

sections = []
if outgoing:
    sections.append(("Transfers Out", "\U0001f6aa", outgoing))
if targets:
    sections.append(("Transfer Targets", "\U0001f3af", targets))

embeds = []
current_embed = discord.Embed(title=title, color=KU_BLUE)
player_count = 0

for section_title, section_emoji, section_players in sections:
    # Add section header
    current_embed.add_field(
        name=f"{section_emoji} {section_title}",
        value=f"*{len(section_players)} player(s)*",
        inline=False,
    )
    for player in section_players:
        if player_count >= MAX_PLAYERS_PER_EMBED:
            embeds.append(current_embed)
            current_embed = discord.Embed(title=f"{title} (cont.)", color=KU_BLUE)
            player_count = 0
        # ... add player field ...
        player_count += 1
```

## Open Questions

1. **Position filter on `/transfer-list` vs `/transfer-add`**
   - What we know: PORTAL-02 requires optional position filtering. D-02 adds a `type` parameter to `/transfer-add`.
   - What's unclear: Whether position filter should also apply when listing recruits (via `/recruit-list`). Currently it's only required for transfers.
   - Recommendation: Add position filter to `/transfer-list` only per PORTAL-02. If desired for recruits later, it can be added separately.

2. **Shared `PlayerEntry` impact on recruiting commands**
   - What we know: `PlayerEntry` is shared between recruiting and transfer stores. Adding `type` field affects both.
   - What's unclear: Whether existing `recruits.json` data will cause issues when loaded with the new `type` field.
   - Recommendation: No issue -- `type="target"` default means old recruit entries load fine. The `type` field is simply ignored in recruiting display. No changes needed to `recruiting.py`.

## Sources

### Primary (HIGH confidence)
- Existing codebase: `src/bot/commands/transfers.py`, `src/bot/storage/models.py`, `src/bot/storage/recruiting_store.py` -- direct code inspection
- Phase 7 patterns: `src/bot/commands/recruiting.py` -- identical command structure
- discord.py `app_commands.Choice` -- standard pattern from discord.py stable docs

### Secondary (MEDIUM confidence)
- Python `dataclasses` default field ordering rules -- standard library behavior
- `time.monotonic()` vs `time.time()` -- standard library documentation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries, all changes use existing patterns
- Architecture: HIGH -- extending established Phase 7 patterns mechanically
- Pitfalls: HIGH -- common Python/discord.py issues well-documented
- Cache module: HIGH -- simple standalone utility with no external dependencies

**Research date:** 2026-04-07
**Valid until:** 2026-05-07 (stable -- no external API integration this phase)
