# Roadmap: Discord Summary Bot

## Overview

This roadmap delivers a Discord bot that summarizes channel discussions on demand and on a schedule. Phase 1 builds the foundation: bot connectivity, message fetching pipeline, and the pluggable AI backend. Phase 2 wires everything into a working `/summary` slash command with formatted output. Phase 3 adds the automated overnight schedule and optional delivery mechanisms (DM, threads). By the end, users can catch up on what they missed with a single command or by reading the morning recap.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation and Pipeline** - Bot connects to Discord, fetches messages with pagination, and produces AI-generated summaries via pluggable backend
- [ ] **Phase 2: On-Demand Summarization** - Users can run `/summary` and get formatted, topic-grouped bullet-point recaps posted to a dedicated channel
- [ ] **Phase 3: Scheduling and Delivery** - Bot auto-posts overnight summaries at 9am and supports DM and thread delivery options
- [ ] **Phase 4: Summary Quality Improvements** - Enrich LLM input with reply chains, importance signals, typed attachments, embed content, and signal-aware prompts
- [ ] **Phase 5: Summary Language Controls** - Configurable language guidelines with blocklist/allowlist for AI summary output
- [ ] **Phase 6: Error Alerting** - Notify operator on scheduler failures via admin DM and optional webhook alerts

## Phase Details

### Phase 1: Foundation and Pipeline
**Goal**: The bot connects to Discord, registers slash commands, fetches and preprocesses channel messages, and can produce a summary through a pluggable AI backend
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01, INFRA-02, INFRA-03, PIPE-01, PIPE-02, PIPE-04, AI-01, AI-02, AI-03
**Success Criteria** (what must be TRUE):
  1. Bot starts up, connects to Discord, and verifies Message Content Intent is working (non-empty message content)
  2. Bot registers and syncs slash commands on startup without errors
  3. Bot can fetch 100+ messages from a channel with pagination and filter out bot/system messages
  4. A summary can be generated from a set of messages using at least one LLM provider, with graceful error handling on API failures
  5. Large message sets are chunked to stay within LLM context window limits
**Plans:** 3 plans

Plans:
- [x] 01-01-PLAN.md — Project scaffolding, config, shared models, and bot client with slash command sync
- [x] 01-02-PLAN.md — Message pipeline: fetcher, preprocessor, and time-based chunker
- [x] 01-03-PLAN.md — AI provider interface, OpenAI implementation, and summarizer orchestrator

### Phase 2: On-Demand Summarization
**Goal**: Users can run `/summary` and receive an ephemeral, topic-grouped bullet-point summary of recent channel activity with time range selection and channel targeting
**Depends on**: Phase 1
**Requirements**: SUM-01, SUM-02, SUM-03, SUM-05, PIPE-03, OUT-02 *(SUM-04 deferred per D-13, OUT-01 deferred per D-14 to Phase 3)*
**Success Criteria** (what must be TRUE):
  1. User can run `/summary` and receive a bullet-point recap of recent messages, with response deferred properly (no 3-second timeout)
  2. User can specify a time range and choose which channel to summarize via slash command options
  3. Summaries are grouped by discussion topic with bold headers and bullet points
  4. Summaries are posted as ephemeral Discord embeds, with proper splitting if content exceeds 4096 characters
  5. Quiet channels return a clear "no significant activity" message instead of an error
**Plans:** 2 plans

Plans:
- [x] 02-01-PLAN.md — Config extensions, updated system prompt, and embed formatting with topic-boundary splitting
- [x] 02-02-PLAN.md — /summary slash command handler with provider wiring and end-to-end verification

### Phase 3: Scheduling and Delivery
**Goal**: The bot automatically posts an overnight summary every morning and users can choose to receive summaries via DM or as threads
**Depends on**: Phase 2
**Requirements**: SCHED-01, SCHED-02, OUT-03, OUT-04
**Success Criteria** (what must be TRUE):
  1. Bot automatically generates and posts an overnight summary (10pm-9am) to the summaries channel at 9am daily
  2. The overnight window timezone is configurable via environment variable and handles DST correctly
  3. User can opt to receive a summary as a DM
  4. Summaries can be posted as a thread to keep channels clean
**Plans:** 2 plans

Plans:
- [x] 03-01-PLAN.md — Overnight scheduler with multi-channel orchestration and optional thread delivery
- [x] 03-02-PLAN.md — DM toggle command, subscriber persistence, and DM delivery wiring

### Phase 4: Summary Quality Improvements
**Goal:** Enrich the data pipeline feeding the LLM with reply chain context, @here/@everyone importance flags, reaction-based popularity signals, typed attachment metadata, embed content extraction, and signal-aware system prompts -- producing more accurate and context-rich summaries
**Depends on:** Phase 3
**Requirements**: QUAL-01, QUAL-02, QUAL-03, QUAL-04, QUAL-05, QUAL-06, QUAL-07
**Success Criteria** (what must be TRUE):
  1. Reply chains are formatted with indentation in LLM input, giving the model conversational structure
  2. Messages with @here/@everyone are flagged [IMPORTANT] and the LLM must include them verbatim
  3. Messages with 5+ reactions or 5+ replies are flagged [POPULAR] and prioritized
  4. Attachments show as typed markers ([image: file.png], [video: clip.mp4]) instead of generic [attachment]
  5. Embed content (title + description) from user messages is extracted and included in LLM input
  6. System prompts explicitly instruct the LLM on every signal marker
**Plans:** 2 plans

Plans:
- [x] 04-01-PLAN.md — Extend ProcessedMessage data model and enrich preprocessor with all new metadata extraction
- [x] 04-02-PLAN.md — Reply-chain formatting, popularity computation, and signal-aware system prompts

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation and Pipeline | 3/3 | Complete | - |
| 2. On-Demand Summarization | 2/2 | Complete | - |
| 3. Scheduling and Delivery | 2/2 | Complete | - |
| 4. Summary Quality Improvements | 2/2 | Complete | - |
| 5. Summary Language Controls | 0/1 | Planning complete | - |

### Phase 5: Summary Language Controls

**Goal:** Add configurable language guidelines to AI summary system prompts -- a blocklist of insulting/inappropriate terms the LLM must avoid, with an allowlist for context-specific exceptions (phrases that seem harmful but are acceptable in the server's culture)
**Requirements**: LANG-01, LANG-02, LANG-03, LANG-04, LANG-05
**Depends on:** Phase 4
**Success Criteria** (what must be TRUE):
  1. Blocked terms from blocklist.txt are injected into both system prompts as language guidelines
  2. Allowlist entries with reasons are parsed and included as exceptions in the prompt
  3. Missing blocklist.txt or allowlist.txt logs a warning and bot continues without language rules
  4. A default blocklist.txt ships with curated inappropriate terms
  5. Language guidelines are appended to both SUMMARY_SYSTEM_PROMPT and MERGE_SYSTEM_PROMPT
**Plans:** 1 plan

Plans:
- [ ] 05-01-PLAN.md — Language filter module, default blocklist/allowlist files, and integration into summarizer prompts and bot startup

### Phase 6: Error Alerting
**Goal:** Notify the bot operator when scheduled summaries fail silently -- DM a configured admin user on errors (permission denied, channel not found, thread creation failure, summarization crashes) and optionally forward alerts to a Discord webhook for a private ops channel or external service
**Requirements**: TBD
**Depends on:** Phase 4
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd:plan-phase 6 to break down)
