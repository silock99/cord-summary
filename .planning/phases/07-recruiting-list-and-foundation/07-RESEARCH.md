# Phase 7: Recruiting List and Foundation - Research

**Researched:** 2026-04-07
**Domain:** Discord slash commands, JSON file persistence, channel-sport mapping, role-gated commands
**Confidence:** HIGH

## Summary

Phase 7 adds 6 new slash commands (recruit-add/remove/list and transfer-add/remove/list) with JSON file persistence, channel-based sport detection, and editor-role authorization. The existing codebase provides strong patterns to follow: `register_*_command(bot)` for command registration, `is_admin()` check decorator for authorization, `pydantic-settings` computed fields for comma-separated env vars, and embed building utilities.

The primary technical challenges are: (1) atomic JSON file writes for crash safety, (2) fuzzy name matching for player removal, and (3) embed field layout for player lists respecting Discord's 25-field-per-embed limit. All three are solvable with Python stdlib (no new dependencies needed).

**Primary recommendation:** Build a shared `RecruitingStore` class handling JSON I/O for both recruits and transfers, a shared `is_recruiting_editor()` check, and a shared `get_sport_from_channel()` helper. Then wire 6 thin command functions that compose these building blocks.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Field-per-player embed layout -- each player gets their own embed field with name/stars as title, position/school as value, and added-date
- **D-02:** Lists sorted by position (not star rating), since transfers are the primary use case and star ratings apply mainly to HS recruits
- **D-03:** Single scrollable embed (auto-split at 4096 chars using existing embed split pattern), no button pagination
- **D-04:** Two separate command sets -- `/recruit-add`, `/recruit-remove`, `/recruit-list` for HS recruits AND `/transfer-add`, `/transfer-remove`, `/transfer-list` for college transfers (6 new commands total)
- **D-05:** Separate top-level commands (not subcommand groups), matching existing `/summary` + `/post-summary` pattern
- **D-06:** Add commands use slash command parameters: `name`, `position`, `school`, `stars` -- all in one command
- **D-07:** Position is free text input (no dropdown/autocomplete)
- **D-08:** Removal by player name with fuzzy matching -- shows "did you mean?" when no exact match found
- **D-09:** Separate JSON files: `data/recruits.json` and `data/transfers.json`
- **D-10:** Each file structured as `{"football": [...], "basketball": [...]}` with sport as top-level key
- **D-11:** New `RECRUITING_EDITOR_IDS` env var (comma-separated) -- separate from `ADMIN_USER_IDS`
- **D-12:** `ADMIN_USER_IDS` implicitly inherit recruiting editor access
- **D-13:** View commands (`/recruit-list`, `/transfer-list`) are public -- any user in a mapped channel can view
- **D-14:** Separate env vars per sport: `FOOTBALL_CHANNEL_IDS` and `BASKETBALL_CHANNEL_IDS` (comma-separated)
- **D-15:** Commands can ONLY be run in mapped channels -- unmapped channels get a denial message
- **D-16:** No `sport` parameter on any command -- sport is always determined from channel

### Claude's Discretion
- Error message wording for unauthorized users and unmapped channels
- Internal data model structure for player entries (fields, types, timestamps)
- File I/O pattern (atomic writes, error handling for corrupt JSON)

### Deferred Ideas (OUT OF SCOPE)
None
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RECRUIT-01 | Authorized users can add a player to the KU recruiting list (name, position, previous school, star rating, sport) | Config pattern for RECRUITING_EDITOR_IDS (reuse computed_field), is_recruiting_editor() check, channel-sport mapping, JSON store add method |
| RECRUIT-02 | Authorized users can remove a player from the KU recruiting list | Fuzzy matching via difflib.get_close_matches (stdlib), JSON store remove method |
| RECRUIT-03 | User can view the KU recruiting list filtered by sport | Embed field-per-player layout, 25-field Discord limit handling, channel-derived sport filter |
| RECRUIT-04 | Recruiting list entries show last-updated timestamps | Player data model includes `added_at` ISO timestamp, displayed via discord.utils.format_dt() |
| RECRUIT-05 | Sport selection uses autocomplete dropdown | **Superseded by D-16** -- sport is channel-derived, no autocomplete needed. Requirement satisfied by channel-sport mapping. |
| RECRUIT-06 | Recruiting data persisted in JSON files | Atomic JSON write pattern (tempfile + os.replace), data/recruits.json and data/transfers.json |
| INFRA-04 | Channel-to-sport mapping configurable via environment variables | FOOTBALL_CHANNEL_IDS and BASKETBALL_CHANNEL_IDS env vars, parsed via pydantic-settings computed_field |
| INFRA-05 | Authorized user IDs configurable for recruiting list management | RECRUITING_EDITOR_IDS env var, combined with ADMIN_USER_IDS for authorization check |
</phase_requirements>

## Architecture Patterns

### Recommended Project Structure
```
src/bot/
  commands/
    recruiting.py       # /recruit-add, /recruit-remove, /recruit-list
    transfers.py         # /transfer-add, /transfer-remove, /transfer-list
  storage/
    __init__.py
    recruiting_store.py  # RecruitingStore class (JSON I/O, CRUD, fuzzy match)
    models.py            # PlayerEntry dataclass
  config.py              # Add new env var fields
  client.py              # Register new commands in setup_hook
data/
  recruits.json          # Created on first write
  transfers.json         # Created on first write
```

### Pattern 1: Command Registration (existing pattern)
**What:** Each command module exports a `register_*_command(bot)` function called from `setup_hook()`
**When to use:** All 6 new commands follow this
**Example (from existing codebase):**
```python
# src/bot/commands/recruiting.py
def register_recruit_commands(bot) -> None:
    """Register /recruit-add, /recruit-remove, /recruit-list."""

    def is_recruiting_editor():
        async def predicate(interaction: discord.Interaction) -> bool:
            editor_ids = interaction.client.settings.recruiting_editor_ids
            admin_ids = interaction.client.settings.admin_user_ids
            if interaction.user.id not in editor_ids and interaction.user.id not in admin_ids:
                raise app_commands.CheckFailure(
                    "You don't have permission to manage the recruiting list."
                )
            return True
        return app_commands.check(predicate)

    def require_sport_channel():
        async def predicate(interaction: discord.Interaction) -> bool:
            sport = get_sport_from_channel(interaction.channel.id, interaction.client.settings)
            if sport is None:
                raise app_commands.CheckFailure(
                    "This command can only be used in a football or basketball channel."
                )
            return True
        return app_commands.check(predicate)
```

### Pattern 2: Channel-Sport Resolution
**What:** Helper function that maps channel ID to sport string
**When to use:** Every command needs this to determine which sport list to operate on
```python
def get_sport_from_channel(channel_id: int, settings) -> str | None:
    """Return 'football' or 'basketball' based on channel mapping, or None."""
    if channel_id in settings.football_channel_ids:
        return "football"
    if channel_id in settings.basketball_channel_ids:
        return "basketball"
    return None
```

### Pattern 3: Atomic JSON Persistence
**What:** Write to temp file then os.replace for crash safety
**When to use:** Every write operation to recruits.json / transfers.json
```python
import json
import os
import tempfile
from pathlib import Path

def _save_atomic(data: dict, filepath: Path) -> None:
    """Write JSON atomically using temp file + os.replace."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=filepath.parent, prefix=filepath.name + ".", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, filepath)
    except Exception:
        # Clean up temp file on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
```

### Pattern 4: Player Data Model
**What:** Dataclass for player entries stored in JSON
```python
from dataclasses import dataclass, field
from datetime import datetime, timezone

@dataclass
class PlayerEntry:
    name: str
    position: str
    school: str
    stars: int  # 1-5, 0 for unrated
    added_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {"name": self.name, "position": self.position, "school": self.school,
                "stars": self.stars, "added_at": self.added_at}

    @classmethod
    def from_dict(cls, data: dict) -> "PlayerEntry":
        return cls(**data)
```

### Pattern 5: Embed Field Layout for Player Lists
**What:** Field-per-player embed with position sort and 25-field limit handling
**Key constraint:** Discord allows max 25 fields per embed. If a sport has >25 players, must split into multiple embeds.
```python
def build_recruiting_embed(players: list[PlayerEntry], sport: str, list_type: str) -> list[discord.Embed]:
    """Build embed(s) with field-per-player layout."""
    sport_emoji = "\U0001f3c8" if sport == "football" else "\U0001f3c0"
    sorted_players = sorted(players, key=lambda p: p.position)

    embeds = []
    current = discord.Embed(
        title=f"{sport_emoji} KU {sport.title()} {list_type}",
        color=0x0051BA,  # KU blue
    )
    field_count = 0

    for player in sorted_players:
        if field_count >= 25:
            embeds.append(current)
            current = discord.Embed(title=f"{sport_emoji} KU {sport.title()} {list_type} (cont.)", color=0x0051BA)
            field_count = 0

        stars_display = "\u2b50" * player.stars if player.stars else "Unrated"
        current.add_field(
            name=f"{player.name} {stars_display}",
            value=f"{player.position} | {player.school}",
            inline=False,
        )
        field_count += 1

    if field_count > 0 or not embeds:
        current.set_footer(text=f"Last updated: {datetime.now(timezone.utc).strftime('%b %d, %Y %I:%M %p UTC')}")
        embeds.append(current)

    return embeds
```

### Anti-Patterns to Avoid
- **Loading JSON on every command:** Load once at bot startup, keep in memory, persist on writes. JSON files are small enough to hold in memory.
- **Non-atomic writes:** Never `json.dump` directly to the target file -- a crash mid-write corrupts the file permanently.
- **Separate sport parameter:** D-16 explicitly forbids it. Sport is ALWAYS channel-derived.
- **Subcommand groups:** D-05 explicitly requires top-level commands matching existing `/summary` + `/post-summary` pattern.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Fuzzy name matching | Custom string similarity | `difflib.get_close_matches()` (stdlib) | Handles case-insensitive matching, returns ranked results, cutoff tuning. Zero dependencies. |
| Atomic file writes | Direct json.dump to file | `tempfile.mkstemp` + `os.replace` pattern | Prevents data corruption on crash/power loss. Standard POSIX-safe pattern. |
| Timestamp formatting | Manual strftime in embeds | `discord.utils.format_dt()` | Renders as Discord dynamic timestamps that adapt to each user's timezone |
| Comma-separated env parsing | Manual str.split logic | pydantic-settings `computed_field` pattern | Already established in config.py for admin_user_ids and allowed_channel_ids |

## Common Pitfalls

### Pitfall 1: Discord 25-Field Embed Limit
**What goes wrong:** Adding >25 fields to an embed silently truncates or raises an error
**Why it happens:** A popular sport recruiting list could exceed 25 players
**How to avoid:** Count fields per embed, split into continuation embeds at 25
**Warning signs:** Embed appears to be missing players at the bottom

### Pitfall 2: Race Condition on JSON Writes
**What goes wrong:** Two concurrent add/remove commands corrupt the JSON file
**Why it happens:** Both read the file, modify in memory, write back -- second write overwrites first
**How to avoid:** Keep data in memory (single authoritative copy), serialize writes. discord.py runs on a single asyncio event loop so as long as writes don't yield between read-modify-write, this is safe. Use a simple asyncio.Lock if any step involves an `await`.
**Warning signs:** Players disappearing from the list after rapid-fire adds

### Pitfall 3: Embed Field Name 256-Char Limit
**What goes wrong:** A player name + star emojis exceeding 256 chars crashes the embed
**Why it happens:** Unlikely but possible with very long names
**How to avoid:** Truncate field name to 256 chars
**Warning signs:** HTTPException from Discord API

### Pitfall 4: Empty JSON File on First Run
**What goes wrong:** FileNotFoundError when trying to load recruits.json before any player is added
**Why it happens:** JSON files don't exist until first write
**How to avoid:** Load with fallback: if file missing or empty, return default `{"football": [], "basketball": []}`
**Warning signs:** Bot crashes on first `/recruit-list` command

### Pitfall 5: os.replace on Windows Cross-Drive
**What goes wrong:** `os.replace` fails if temp file and target are on different drives
**Why it happens:** Windows limitation for cross-filesystem moves
**How to avoid:** Use `tempfile.mkstemp(dir=filepath.parent)` to ensure same directory (already in the pattern above)
**Warning signs:** OSError on Windows during save

### Pitfall 6: Star Rating Validation
**What goes wrong:** User enters stars=0 or stars=6
**Why it happens:** No input validation on the slash command parameter
**How to avoid:** Use `@app_commands.describe` with `app_commands.Range[int, 0, 5]` type annotation to enforce 0-5 range at the Discord level
**Warning signs:** Invalid star displays in embeds

## Code Examples

### Fuzzy Matching for Player Removal
```python
from difflib import get_close_matches

def find_player(name: str, players: list[PlayerEntry]) -> tuple[PlayerEntry | None, list[str]]:
    """Find exact match or suggest close matches.

    Returns (player, []) for exact match, or (None, suggestions) for fuzzy matches.
    """
    # Exact match (case-insensitive)
    for p in players:
        if p.name.lower() == name.lower():
            return p, []

    # Fuzzy match
    names = [p.name for p in players]
    suggestions = get_close_matches(name, names, n=3, cutoff=0.6)
    return None, suggestions
```

### Config Fields (add to Settings class)
```python
# In config.py Settings class:

# Recruiting editor IDs (comma-separated)
recruiting_editor_ids_raw: str = Field(default="", alias="RECRUITING_EDITOR_IDS")

# Channel-to-sport mapping
football_channel_ids_raw: str = Field(default="", alias="FOOTBALL_CHANNEL_IDS")
basketball_channel_ids_raw: str = Field(default="", alias="BASKETBALL_CHANNEL_IDS")

@computed_field
@property
def recruiting_editor_ids(self) -> list[int]:
    raw = self.recruiting_editor_ids_raw
    if not raw:
        return []
    return [int(p.strip()) for p in raw.split(",") if p.strip()]

@computed_field
@property
def football_channel_ids(self) -> list[int]:
    raw = self.football_channel_ids_raw
    if not raw:
        return []
    return [int(p.strip()) for p in raw.split(",") if p.strip()]

@computed_field
@property
def basketball_channel_ids(self) -> list[int]:
    raw = self.basketball_channel_ids_raw
    if not raw:
        return []
    return [int(p.strip()) for p in raw.split(",") if p.strip()]
```

### Discord Dynamic Timestamps
```python
from datetime import datetime, timezone
import discord

# Convert ISO string to discord timestamp
added_dt = datetime.fromisoformat(player.added_at)
timestamp_str = discord.utils.format_dt(added_dt, style="R")  # "2 days ago"
# Or style="f" for "April 5, 2026 3:45 PM"
```

### Star Rating Parameter with Range Validation
```python
@bot.tree.command(name="recruit-add", description="Add a player to the KU recruiting list")
@app_commands.describe(
    name="Player name",
    position="Position (e.g., QB, WR, ATH, PG, C)",
    school="Previous/current school",
    stars="Star rating (0 for unrated, 1-5)",
)
@require_sport_channel()
@is_recruiting_editor()
async def recruit_add(
    interaction: discord.Interaction,
    name: str,
    position: str,
    school: str,
    stars: app_commands.Range[int, 0, 5] = 0,
) -> None:
    ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `discord.py` hybrid commands | `app_commands` (slash commands only) | discord.py 2.0 (2022) | All new commands should use `@bot.tree.command`, not `@bot.command` |
| Manual timezone with pytz | `zoneinfo` (stdlib) | Python 3.9 (2020) | No pytz needed; timestamps use `datetime.now(timezone.utc)` |
| `json.dump` direct to file | tempfile + `os.replace` | Best practice | Prevents corruption on crash |

## Open Questions

1. **Embed field layout vs description text**
   - What we know: D-01 specifies field-per-player layout, D-03 says auto-split at 4096 chars
   - What's unclear: D-03 references "existing embed split pattern" which splits by description text (embeds.py), but D-01 uses fields (not description). The 25-field limit is the actual constraint, not 4096 chars.
   - Recommendation: Split at 25 fields per embed (the Discord hard limit). The 4096-char description limit is irrelevant when using fields. D-03's spirit (auto-split, single scrollable view, no pagination buttons) is preserved.

2. **Data directory creation**
   - What we know: `data/` directory exists with `dm_subscribers.json`
   - What's unclear: Whether the data directory is git-tracked or created at runtime
   - Recommendation: Ensure `_save_atomic` creates `data/` directory if missing. Add `data/*.json` to `.gitignore` (except maybe a `.gitkeep`).

## Sources

### Primary (HIGH confidence)
- Existing codebase: `src/bot/config.py`, `src/bot/commands/post_summary.py`, `src/bot/formatting/embeds.py`, `src/bot/client.py`, `src/bot/models.py` -- all patterns verified by direct code reading
- [Python difflib docs](https://docs.python.org/3/library/difflib.html) -- get_close_matches API
- [Discord embed limits](https://www.pythondiscord.com/pages/guides/python-guides/discord-embed-limits/) -- 25 fields, 256 name, 1024 value, 4096 description

### Secondary (MEDIUM confidence)
- [Atomic file write pattern](https://sahmanish20.medium.com/better-file-writing-in-python-embrace-atomic-updates-593843bfab4f) -- tempfile + os.replace pattern verified against Python stdlib docs
- [discord.py embed fields issue](https://github.com/Rapptz/discord.py/issues/8054) -- 25-field limit behavior

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all stdlib + existing discord.py features
- Architecture: HIGH -- follows established codebase patterns exactly
- Pitfalls: HIGH -- Discord embed limits well-documented, JSON atomicity is standard pattern

**Research date:** 2026-04-07
**Valid until:** 2026-05-07 (stable domain, no fast-moving dependencies)
