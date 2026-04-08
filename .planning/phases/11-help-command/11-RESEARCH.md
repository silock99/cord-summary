# Phase 11: Help Command - Research

**Researched:** 2026-04-08
**Domain:** discord.py slash commands, embed formatting, permission introspection
**Confidence:** HIGH

## Summary

Phase 11 adds a `/cordbot` help command that displays all bot commands in a single categorized embed with permission filtering. This is a pure UI/presentation task using existing discord.py embed APIs -- no new libraries, no external dependencies, no data layer changes.

The implementation requires building a static command registry (a data structure mapping commands to categories, descriptions, parameters, and permission levels) and rendering it as a filtered embed based on the invoker's permissions. The key architectural decision is whether to dynamically introspect registered commands vs. maintaining a static definition -- given that the CONTEXT.md decisions specify exact categories and formatting, a static registry with curated descriptions is the correct approach.

**Primary recommendation:** Create a static command metadata registry (list of dicts or dataclasses) organized by category, filter by permission at render time, output as a single embed with field sections per category.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-01: Command is `/cordbot` (not `/help`) -- single command, no subcommands or arguments
- D-02: One invocation shows everything -- no per-command drill-down needed
- D-03: Single embed with commands grouped by category using field sections: Summaries, Recruiting, Transfers, Stats & Roster, Admin
- D-04: Each command shows name + parameters + one-liner description (e.g., `/summary [timerange] [channel] -- Summarize recent activity`)
- D-05: Category headers use emoji prefixes for visual grouping
- D-06: Response is ephemeral (only the invoker sees it)
- D-07: Permission-filtered -- only shows commands the user has access to. Non-admins do not see admin-only commands like `/post-summary`
- D-08: Permission check uses the same role/permission logic already established in the codebase (e.g., `is_recruiting_editor`, `manage_guild` for admin commands)

### Claude's Discretion
- Exact emoji choice per category
- Embed footer content (e.g., bot version, tip text)
- How to detect admin status (check `manage_guild` permission, or check `ADMIN_USER_IDS`, or both)
- Whether to show channel-restricted commands (roster/recruiting) when not in a sport channel

### Deferred Ideas (OUT OF SCOPE)
None
</user_constraints>

## Standard Stack

### Core
No new libraries needed. Everything is built with discord.py's existing APIs.

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| discord.py | 2.7.1 (already installed) | Embed building, slash commands, permission checks | Already the bot's framework |

### Supporting
No additional libraries needed.

## Architecture Patterns

### Recommended Project Structure
```
src/bot/commands/
    help.py              # New file: /cordbot command + command registry
```

Single new file. No new directories, no new modules.

### Pattern 1: Static Command Registry
**What:** Define command metadata as a structured list rather than dynamically introspecting `bot.tree.get_commands()`.
**When to use:** When help output needs curated descriptions, specific parameter formatting, and category grouping that differs from raw command metadata.
**Why not dynamic:** discord.py's `CommandTree.get_commands()` returns `AppCommand` objects but their parameter descriptions and grouping don't match the curated format specified in D-03/D-04. Dynamic introspection would require post-processing that's more complex than a static list.

```python
from dataclasses import dataclass

@dataclass
class CommandInfo:
    name: str
    params: str          # e.g., "[timerange] [channel]"
    description: str     # one-liner
    category: str        # "summaries", "recruiting", etc.
    permission: str      # "public", "editor", "admin"

COMMANDS: list[CommandInfo] = [
    CommandInfo("summary", "[timerange] [channel]", "Summarize recent channel activity", "summaries", "public"),
    CommandInfo("post-summary", "<channel> [timerange]", "Post a public summary to the summary channel", "admin", "admin"),
    # ... etc
]
```

### Pattern 2: Permission Filtering at Render Time
**What:** Check the invoker's permissions once, then filter the command list before building the embed.
**When to use:** Always -- per D-07.

```python
async def get_visible_commands(interaction: discord.Interaction, commands: list[CommandInfo]) -> list[CommandInfo]:
    settings = interaction.client.settings
    user_id = interaction.user.id
    
    is_admin = (
        user_id in settings.admin_user_ids
        or interaction.user.guild_permissions.manage_guild
    )
    is_editor = (
        user_id in settings.recruiting_editor_ids
        or is_admin  # admins can do editor things
    )
    
    visible = []
    for cmd in commands:
        if cmd.permission == "public":
            visible.append(cmd)
        elif cmd.permission == "editor" and is_editor:
            visible.append(cmd)
        elif cmd.permission == "admin" and is_admin:
            visible.append(cmd)
    return visible
```

### Pattern 3: Embed Field Sections Per Category
**What:** Use embed fields with category headers as section dividers.
**When to use:** Per D-03 -- group commands by category.

```python
# Category display order and emoji
CATEGORIES = [
    ("summaries", "Summaries"),
    ("recruiting", "Recruiting"),
    ("transfers", "Transfers"),
    ("stats_roster", "Stats & Roster"),
    ("admin", "Admin"),
]

def build_help_embed(commands: list[CommandInfo]) -> discord.Embed:
    embed = discord.Embed(
        title="CordBot Commands",
        color=KU_BLUE,
    )
    
    for cat_key, cat_label in CATEGORIES:
        cat_commands = [c for c in commands if c.category == cat_key]
        if not cat_commands:
            continue  # Skip empty categories (permission-filtered out)
        
        lines = []
        for cmd in cat_commands:
            if cmd.params:
                lines.append(f"`/{cmd.name} {cmd.params}` -- {cmd.description}")
            else:
                lines.append(f"`/{cmd.name}` -- {cmd.description}")
        
        embed.add_field(
            name=f"{emoji} {cat_label}",  # emoji from discretion choices
            value="\n".join(lines),
            inline=False,
        )
    
    return embed
```

### Anti-Patterns to Avoid
- **Dynamic command introspection:** Don't use `bot.tree.get_commands()` to build help -- it returns raw AppCommand objects without curated categories or descriptions. Requires complex post-processing for no benefit.
- **Multiple embeds or pagination:** D-02 specifies one invocation shows everything. With 11 commands across 5 categories, content fits easily in a single embed (well under 6000 char total limit).
- **Non-ephemeral response:** D-06 requires ephemeral. Don't accidentally omit `ephemeral=True`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Permission checking | Custom permission system | Reuse `ADMIN_USER_IDS` and `recruiting_editor_ids` from settings | Already established pattern in all command modules |
| Embed color | New constant | Import `KU_BLUE = 0x0051BA` from existing modules | Consistent branding |

**Key insight:** This phase has no complex problems to solve. It's a straightforward data-display task using existing patterns.

## Common Pitfalls

### Pitfall 1: Embed Character Limits
**What goes wrong:** Embed total content exceeds 6000 characters or a single field value exceeds 1024 characters.
**Why it happens:** Verbose command descriptions or too many commands in one field.
**How to avoid:** With 11 commands and short descriptions, this is not a real risk. But verify: each field value (category section) stays under 1024 chars. A typical line is ~80 chars, and the largest category (Recruiting) has 3 commands = ~240 chars. Safe by a wide margin.
**Warning signs:** Field value truncation or embed send failure.

### Pitfall 2: Forgetting to Register in client.py
**What goes wrong:** Command exists in code but never shows up in Discord.
**Why it happens:** Missing the `register_help_commands(self)` call in `setup_hook()`.
**How to avoid:** Follow the exact same pattern as all other command modules -- add import and call in `setup_hook()`.

### Pitfall 3: Permission Check Inconsistency
**What goes wrong:** Help command shows a command as available but the user can't actually use it, or vice versa.
**Why it happens:** Permission logic in help differs from the actual command's permission checks.
**How to avoid:** Use the same source of truth -- `settings.admin_user_ids` and `settings.recruiting_editor_ids` -- that the actual commands use. The help command's permission filter must mirror the real checks.

### Pitfall 4: Stale Help Text After Adding Future Commands
**What goes wrong:** New commands are added in future phases but the help command doesn't list them.
**Why it happens:** Static registry requires manual updates.
**How to avoid:** Add a code comment at the top of the registry: "Update this list when adding new commands." This is an acceptable tradeoff for curated descriptions.

## Code Examples

### Complete Command Registration Pattern
```python
KU_BLUE = 0x0051BA

def register_help_commands(bot) -> None:
    """Register the /cordbot help command."""

    @bot.tree.command(
        name="cordbot",
        description="Show all bot commands and how to use them",
    )
    async def cordbot(interaction: discord.Interaction) -> None:
        visible = get_visible_commands(interaction)
        embed = build_help_embed(visible)
        await interaction.response.send_message(embed=embed, ephemeral=True)
```

### Existing Permission Check Patterns (from codebase)

**Admin check (post_summary.py):**
```python
admin_ids = interaction.client.settings.admin_user_ids
is_admin = interaction.user.id in admin_ids
```

**Editor check (recruiting.py, transfers.py, roster.py):**
```python
editor_ids = interaction.client.settings.recruiting_editor_ids
admin_ids = interaction.client.settings.admin_user_ids
is_editor = interaction.user.id in editor_ids or interaction.user.id in admin_ids
```

### Complete Command Inventory (for static registry)

| Command | Parameters | Description | Category | Permission |
|---------|-----------|-------------|----------|------------|
| `/summary` | `[timerange] [channel]` | Summarize recent channel activity | summaries | public |
| `/post-summary` | `<channel> [timerange]` | Post a public summary (admin only) | admin | admin |
| `/recruit-add` | `<name> <position> <school> <stars> [sport]` | Add a player to the recruiting list | recruiting | editor |
| `/recruit-remove` | `<name> [sport]` | Remove a player from the recruiting list | recruiting | editor |
| `/recruit-list` | `[sport]` | View the recruiting list | recruiting | public |
| `/transfer-add` | `<name> <position> <school> <stars> [sport]` | Add a player to the transfer list | transfers | editor |
| `/transfer-remove` | `<name> [sport]` | Remove a player from the transfer list | transfers | editor |
| `/transfer-list` | `[sport]` | View the transfer list | transfers | public |
| `/stats` | `<player>` | Look up college career stats | stats_roster | public |
| `/roster-import` | (none) | Import the current KU roster from API | stats_roster | editor |
| `/roster-list` | (none) | View the current KU roster | stats_roster | public |

### Embed Field Limits (discord.py)

| Limit | Value | Relevance |
|-------|-------|-----------|
| Embed title | 256 chars | "CordBot Commands" = 17 chars. Safe. |
| Field name | 256 chars | Category headers are ~20 chars. Safe. |
| Field value | 1024 chars | Largest category has 3 commands at ~80 chars each = ~240. Safe. |
| Total fields | 25 | 5 categories + footer = 6. Safe. |
| Total embed chars | 6000 | ~11 commands * ~80 chars + headers = ~1200. Safe. |

## State of the Art

No relevant changes. discord.py 2.7.1 embed API has been stable since 2.0. No deprecated methods in use.

## Open Questions

1. **Admin detection: ADMIN_USER_IDS vs manage_guild permission**
   - What we know: `post_summary.py` checks `ADMIN_USER_IDS` only. The `@app_commands.default_permissions(manage_guild=True)` decorator is a UI hint, not enforcement.
   - Recommendation: Check both `ADMIN_USER_IDS` and `manage_guild` permission for maximum safety. If a user has either, they see admin commands. This matches CONTEXT.md discretion area.

2. **Show sport-channel commands outside sport channels?**
   - What we know: Commands like `/recruit-list`, `/stats`, `/roster-list` require a sport channel to execute.
   - Recommendation: Show all commands regardless of current channel. Users should see the full capability set. The commands themselves enforce channel restrictions. This avoids confusing "where did the commands go?" behavior.

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `src/bot/commands/*.py` -- all 7 command modules reviewed
- Codebase inspection: `src/bot/client.py` -- registration pattern confirmed
- discord.py embed limits: well-established (title 256, field name 256, field value 1024, total 6000, 25 fields max)

### Secondary (MEDIUM confidence)
- discord.py 2.7.1 API stability -- based on CLAUDE.md sources and project history

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new libraries, using existing discord.py
- Architecture: HIGH - follows exact patterns from 6 existing command modules
- Pitfalls: HIGH - embed limits are well-documented, permission patterns verified in codebase

**Research date:** 2026-04-08
**Valid until:** 2026-05-08 (stable domain, no moving parts)
