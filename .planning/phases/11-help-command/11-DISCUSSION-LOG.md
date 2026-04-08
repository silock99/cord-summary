# Phase 11: Help Command - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md -- this log preserves the alternatives considered.

**Date:** 2026-04-08
**Phase:** 11-help-command
**Areas discussed:** Help format, Command detail, Access method, Visibility

---

## Help Format

| Option | Description | Selected |
|--------|-------------|----------|
| Categorized embeds | One embed with fields grouped by category (Summaries, Recruiting, Transfers, Stats/Roster, Admin) | ✓ |
| Flat list | Single embed, all commands listed alphabetically | |
| Multi-embed | Separate embed per category | |

**User's choice:** Categorized embeds
**Notes:** User selected the preview showing grouped categories with emoji headers.

---

## Command Detail

| Option | Description | Selected |
|--------|-------------|----------|
| Name + one-liner | Just command name and short description | |
| Name + params + one-liner | Show parameters inline with description | ✓ |
| Full usage block | Multi-line block with description, parameters, and example | |

**User's choice:** Name + params + one-liner
**Notes:** None

---

## Access Method

| Option | Description | Selected |
|--------|-------------|----------|
| /help <command> | Main /help shows overview, /help <cmd> shows per-command detail | |
| Overview only | Just /help with no arguments | |
| Both + autocomplete | Like option 1 but with autocomplete on command parameter | |

**User's choice:** Other -- "Call it /cordbot help and then it shows the full detail for all commands"
**Notes:** User wants the command named `/cordbot` instead of `/help`. Single command showing all detail, no per-command drill-down. Confirmed in follow-up: single `/cordbot` command, one response showing everything.

---

## Visibility

| Option | Description | Selected |
|--------|-------------|----------|
| Ephemeral | Only the invoker sees the response | ✓ |
| Public | Everyone in the channel sees the help output | |

**User's choice:** Ephemeral, with permission filtering
**Notes:** User explicitly wants permission-filtered output: "it only shows what a user has access to. So, if they aren't an admin, for example, it won't show /post-summary."

| Option | Description | Selected |
|--------|-------------|----------|
| Show all commands | Everyone sees all commands, admin noted with marker | |
| Hide admin commands | Non-admins only see commands they can use | ✓ |

**User's choice:** Hide admin commands
**Notes:** Consistent with ephemeral + filtered approach.

---

## Claude's Discretion

- Exact emoji choice per category
- Embed footer content
- Admin detection method
- Channel-restricted command visibility

## Deferred Ideas

None
