# Requirements: Discord Summary Bot

**Defined:** 2026-03-27
**Core Value:** Users can quickly catch up on what they missed without reading through hundreds of messages

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Summarization

- [ ] **SUM-01**: User can run `/summary` to get a bullet-point summary of recent channel messages
- [ ] **SUM-02**: User can specify a time range (e.g., "last 2 hours") via slash command option
- [ ] **SUM-03**: Summaries are grouped by discussion topic with clear headers
- [ ] **SUM-04**: Action items and decisions are extracted as a separate section in the summary
- [ ] **SUM-05**: Empty or low-activity periods return a "no significant activity" message

### Message Pipeline

- [ ] **PIPE-01**: Bot fetches messages with pagination to handle channels with 100+ messages
- [ ] **PIPE-02**: Bot filters out bot messages and system messages before summarizing
- [ ] **PIPE-03**: User can choose which channel to summarize via slash command option
- [ ] **PIPE-04**: Large message sets are chunked to fit within LLM context window limits

### AI Backend

- [ ] **AI-01**: Summarization uses a pluggable provider interface (abstract backend)
- [ ] **AI-02**: At least one concrete LLM provider implementation is included
- [ ] **AI-03**: Bot handles LLM errors gracefully (timeout, rate limit, API errors)

### Output & Delivery

- [ ] **OUT-01**: Summaries are posted to a configurable dedicated #summaries channel
- [ ] **OUT-02**: Summaries use Discord embed formatting with proper length handling (split if > 4096 chars)
- [ ] **OUT-03**: User can optionally receive the summary as a DM
- [ ] **OUT-04**: Summaries can be posted as a thread to keep channels clean

### Scheduling

- [ ] **SCHED-01**: Bot automatically generates and posts an overnight summary (10pm-9am) at 9am daily
- [ ] **SCHED-02**: Timezone is configurable via environment variable

### Infrastructure

- [ ] **INFRA-01**: Bot connects to Discord with proper intents (including Message Content)
- [ ] **INFRA-02**: Configuration via environment variables (bot token, channel IDs, timezone, LLM API key)
- [ ] **INFRA-03**: Slash commands are registered and synced on bot startup

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Enhanced Summaries

- **ESUM-01**: User can ask question-focused summaries ("what was decided about X?")
- **ESUM-02**: Summaries include participant attribution (who said what per topic)
- **ESUM-03**: User can get unread summary (everything since their last message)
- **ESUM-04**: Summary language is configurable per-server

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Multi-server support | Single server only for v1; adds database and per-server config complexity |
| Voice channel transcription | Entirely different problem domain (audio processing, speech-to-text) |
| Web dashboard | Config via env vars is sufficient for single-server bot |
| Message database storage | Discord API provides history access on demand; no need to store locally |
| Real-time streaming summaries | On-demand and scheduled are the right interaction model |
| Per-request pricing / metering | Personal bot using user's own API key, not a SaaS product |
| Custom AI model hosting | User brings their own API key for their preferred provider |
| Role-based permissions | Any server member can use; simplicity over configurability |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| SUM-01 | — | Pending |
| SUM-02 | — | Pending |
| SUM-03 | — | Pending |
| SUM-04 | — | Pending |
| SUM-05 | — | Pending |
| PIPE-01 | — | Pending |
| PIPE-02 | — | Pending |
| PIPE-03 | — | Pending |
| PIPE-04 | — | Pending |
| AI-01 | — | Pending |
| AI-02 | — | Pending |
| AI-03 | — | Pending |
| OUT-01 | — | Pending |
| OUT-02 | — | Pending |
| OUT-03 | — | Pending |
| OUT-04 | — | Pending |
| SCHED-01 | — | Pending |
| SCHED-02 | — | Pending |
| INFRA-01 | — | Pending |
| INFRA-02 | — | Pending |
| INFRA-03 | — | Pending |

**Coverage:**
- v1 requirements: 21 total
- Mapped to phases: 0
- Unmapped: 21 ⚠️

---
*Requirements defined: 2026-03-27*
*Last updated: 2026-03-27 after initial definition*
