# Phase 11: Help Command - Context

**Gathered:** 2026-04-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can run a single slash command to see all bot capabilities and how to use each command. The command displays a categorized, permission-filtered overview of every registered command with parameter info.

</domain>

<decisions>
## Implementation Decisions

### Command Name & Structure
- **D-01:** Command is `/cordbot` (not `/help`) -- single command, no subcommands or arguments
- **D-02:** One invocation shows everything -- no per-command drill-down needed

### Help Format
- **D-03:** Single embed with commands grouped by category using field sections: Summaries, Recruiting, Transfers, Stats & Roster, Admin
- **D-04:** Each command shows name + parameters + one-liner description (e.g., `/summary [timerange] [channel] -- Summarize recent activity`)
- **D-05:** Category headers use emoji prefixes for visual grouping

### Visibility & Permissions
- **D-06:** Response is ephemeral (only the invoker sees it)
- **D-07:** Permission-filtered -- only shows commands the user has access to. Non-admins do not see admin-only commands like `/post-summary`
- **D-08:** Permission check uses the same role/permission logic already established in the codebase (e.g., `is_recruiting_editor`, `manage_guild` for admin commands)

### Claude's Discretion
- Exact emoji choice per category
- Embed footer content (e.g., bot version, tip text)
- How to detect admin status (check `manage_guild` permission, or check `ADMIN_USER_IDS`, or both)
- Whether to show channel-restricted commands (roster/recruiting) when not in a sport channel

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

No external specs -- requirements are fully captured in decisions above.

### Existing command patterns
- `src/bot/commands/transfers.py` -- Pattern for register_*_commands, permission decorators, embed building
- `src/bot/commands/roster.py` -- Most recent command module, embed formatting with KU_BLUE
- `src/bot/client.py` -- Command registration in setup_hook, all register_*_commands imports
- `src/bot/commands/post_summary.py` -- Admin-only command pattern using `@app_commands.default_permissions(manage_guild=True)`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- KU_BLUE (0x0051BA) embed color used across all command modules
- `is_recruiting_editor()` decorator in transfers.py/roster.py for editor permission checks
- `@app_commands.default_permissions(manage_guild=True)` pattern for admin commands

### Established Patterns
- All command modules use `register_*_commands(bot)` function pattern
- Ephemeral responses via `interaction.response.defer(ephemeral=True)` or `interaction.response.send_message(ephemeral=True)`
- Embeds use discord.Embed with KU_BLUE color

### Integration Points
- `src/bot/client.py` setup_hook: needs `register_help_commands(self)` (or similar)
- Existing command registrations: 6 modules (summary, post_summary, recruiting, transfers, career, roster)
- Permission checks: `interaction.user.guild_permissions.manage_guild` for admin detection

</code_context>

<specifics>
## Specific Ideas

No specific requirements -- open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 11-help-command*
*Context gathered: 2026-04-08*
