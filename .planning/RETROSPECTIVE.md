# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — MVP

**Shipped:** 2026-04-07
**Phases:** 6 | **Plans:** 12
**Timeline:** 8 days (2026-03-27 → 2026-04-04)

### What Was Built
- Complete Discord bot with `/summary` slash command, topic-grouped embed output, and time range selection
- Automated overnight scheduler (10pm-9am) with multi-channel support, thread delivery, and DM subscriptions
- Enriched message pipeline: reply chains, importance flags, reaction signals, typed attachments, embed extraction
- Configurable language controls via blocklist/allowlist injected into LLM system prompts
- Admin error alerting via DM and `/post-summary` admin-only command
- Pluggable AI backend with OpenAI implementation

### What Worked
- Phase-by-phase incremental delivery kept each step manageable and testable
- discord.py's built-in `tasks.loop(time=)` eliminated the need for external scheduling dependencies
- Pydantic-settings caught configuration errors at startup rather than runtime
- Provider Protocol pattern made the AI backend truly pluggable with minimal code
- Atomic TDD commits (RED→GREEN→refactor) in later phases produced clean, verified code

### What Was Inefficient
- Phases 5 and 6 were added mid-milestone but roadmap tracking didn't fully reflect them (checkbox/traceability drift)
- REQUIREMENTS.md LANG checkboxes weren't updated after Phase 5 execution — caught only at milestone completion
- Some SUMMARY.md files lacked clean one-liner extraction, making automated accomplishment gathering noisy

### Patterns Established
- `register_X_command(bot)` pattern in setup_hook for command registration
- Admin identity via ADMIN_USER_IDS (unified: error DMs, cooldown exemption, command access)
- Language filter with module-level caching and graceful degradation on missing files
- Pydantic computed_field with raw str + alias for comma-separated env var parsing

### Key Lessons
1. Keep REQUIREMENTS.md in sync with phase execution — check off requirements as phases complete, not retroactively at milestone end
2. Inserted phases (5, 6) need to be added to ROADMAP.md phase details section, not just the progress table
3. Reply chain depth should be capped early (depth-2) to keep LLM input readable

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.0 | 6 | 12 | Initial project — established GSD workflow patterns |

### Top Lessons (Verified Across Milestones)

1. (First milestone — lessons above will be cross-validated in future milestones)
