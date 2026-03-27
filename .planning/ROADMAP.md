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
- [ ] 01-02-PLAN.md — Message pipeline: fetcher, preprocessor, and time-based chunker
- [ ] 01-03-PLAN.md — AI provider interface, OpenAI implementation, and summarizer orchestrator

### Phase 2: On-Demand Summarization
**Goal**: Users can run a slash command and receive a well-formatted summary of recent channel activity posted to a dedicated channel
**Depends on**: Phase 1
**Requirements**: SUM-01, SUM-02, SUM-03, SUM-04, SUM-05, PIPE-03, OUT-01, OUT-02
**Success Criteria** (what must be TRUE):
  1. User can run `/summary` and receive a bullet-point recap of recent messages, with response deferred properly (no 3-second timeout)
  2. User can specify a time range and choose which channel to summarize via slash command options
  3. Summaries are grouped by discussion topic with action items and decisions extracted as a separate section
  4. Summaries are posted to a configurable dedicated channel using Discord embeds, with proper splitting if content exceeds 4096 characters
  5. Quiet channels return a clear "no significant activity" message instead of an error
**Plans**: TBD

### Phase 3: Scheduling and Delivery
**Goal**: The bot automatically posts an overnight summary every morning and users can choose to receive summaries via DM or as threads
**Depends on**: Phase 2
**Requirements**: SCHED-01, SCHED-02, OUT-03, OUT-04
**Success Criteria** (what must be TRUE):
  1. Bot automatically generates and posts an overnight summary (10pm-9am) to the summaries channel at 9am daily
  2. The overnight window timezone is configurable via environment variable and handles DST correctly
  3. User can opt to receive a summary as a DM
  4. Summaries can be posted as a thread to keep channels clean
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation and Pipeline | 0/3 | Planning complete | - |
| 2. On-Demand Summarization | 0/0 | Not started | - |
| 3. Scheduling and Delivery | 0/0 | Not started | - |
