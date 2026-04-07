# Roadmap: Discord Summary Bot

## Milestones

- ✅ **v1.0 MVP** — Phases 1-6 (shipped 2026-04-07) — [archive](milestones/v1.0-ROADMAP.md)
- 🚧 **v1.1 Athletics Intelligence** — Phases 7-9 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-6) — SHIPPED 2026-04-07</summary>

- [x] Phase 1: Foundation and Pipeline (3/3 plans)
- [x] Phase 2: On-Demand Summarization (2/2 plans)
- [x] Phase 3: Scheduling and Delivery (2/2 plans)
- [x] Phase 4: Summary Quality Improvements (2/2 plans)
- [x] Phase 5: Summary Language Controls (1/1 plan)
- [x] Phase 6: Error Alerting (2/2 plans)

</details>

### v1.1 Athletics Intelligence

- [x] **Phase 7: Recruiting List and Foundation** - Admin-curated KU recruiting list with JSON persistence, sport autocomplete, and channel-to-sport config (completed 2026-04-07)
- [ ] **Phase 8: Transfer Portal** - Portal lookup for football (CFBD API) and basketball (admin-curated), with caching, pagination, and position filtering
- [ ] **Phase 9: Career Stats** - College career stats for recruiting list players with fuzzy name matching and sport-specific formatting

## Phase Details

### Phase 7: Recruiting List and Foundation
**Goal**: Authorized users can manage a KU recruiting list and anyone can view it, establishing the persistence pattern and config infrastructure for the entire milestone
**Depends on**: Phase 6 (v1.0 complete)
**Requirements**: RECRUIT-01, RECRUIT-02, RECRUIT-03, RECRUIT-04, RECRUIT-05, RECRUIT-06, INFRA-04, INFRA-05
**Success Criteria** (what must be TRUE):
  1. An authorized user can add a player (name, position, previous school, star rating, sport) to the KU recruiting list and see a confirmation
  2. An authorized user can remove a player from the KU recruiting list; unauthorized users are denied with a clear message
  3. Any user can view the recruiting list filtered by sport, displayed as a formatted embed with last-updated timestamps
  4. Sport selection uses an autocomplete dropdown (basketball/football) and the bot auto-detects sport from channel when applicable
  5. Recruiting data survives bot restarts (persisted to JSON file)
**Plans**: 2 plans

Plans:
- [x] 07-01-PLAN.md — Config infrastructure, data model, and JSON persistence layer
- [x] 07-02-PLAN.md — Slash commands for recruiting and transfer lists, wired into bot client

### Phase 8: Transfer Portal
**Goal**: Users can look up transfer portal players by sport and school, with football data from the CFBD API and basketball data from admin-curated entries
**Depends on**: Phase 7
**Requirements**: PORTAL-01, PORTAL-02, PORTAL-03, PORTAL-04, PORTAL-05, PORTAL-06, INFRA-01, INFRA-03
**Success Criteria** (what must be TRUE):
  1. User can run /portal, pick a sport, and see transfer portal players filtered by school with name, position, original school, and star rating in embed format
  2. User can optionally filter portal results by position to narrow large result sets
  3. Portal results paginate with button navigation when exceeding one embed page
  4. Repeated portal queries within 15-30 minutes are served from cache (no redundant API calls); football data comes from CFBD API, basketball data from admin-curated JSON entries
  5. Sport auto-detects from the channel the command is run in, with manual override available
**Plans**: TBD

Plans:
- [ ] 08-01: TBD
- [ ] 08-02: TBD

### Phase 9: Career Stats
**Goal**: Users can look up college career stats for any player on the KU recruiting list, with sport-appropriate formatting and fuzzy name matching
**Depends on**: Phase 7, Phase 8
**Requirements**: STATS-01, STATS-02, STATS-03, STATS-04, INFRA-02
**Success Criteria** (what must be TRUE):
  1. User can look up career stats for a player on the recruiting list and see per-season college stats in embed format
  2. Basketball stats display as PPG, RPG, APG, FG%, 3P% per season; football stats display as passing, rushing, receiving yards and TDs per season
  3. Player name resolution handles variations (nicknames, abbreviations, suffixes) via fuzzy matching, surfacing "did you mean?" when no exact match is found
  4. Stats are fetched from CBBD API for basketball and CFBD API for football, behind a protocol interface that allows source swapping
**Plans**: TBD

Plans:
- [ ] 09-01: TBD
- [ ] 09-02: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 7 -> 8 -> 9

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation and Pipeline | v1.0 | 3/3 | Complete | 2026-03-28 |
| 2. On-Demand Summarization | v1.0 | 2/2 | Complete | 2026-03-29 |
| 3. Scheduling and Delivery | v1.0 | 2/2 | Complete | 2026-03-30 |
| 4. Summary Quality Improvements | v1.0 | 2/2 | Complete | 2026-04-03 |
| 5. Summary Language Controls | v1.0 | 1/1 | Complete | 2026-04-04 |
| 6. Error Alerting | v1.0 | 2/2 | Complete | 2026-04-04 |
| 7. Recruiting List and Foundation | v1.1 | 2/2 | Complete   | 2026-04-07 |
| 8. Transfer Portal | v1.1 | 0/0 | Not started | - |
| 9. Career Stats | v1.1 | 0/0 | Not started | - |
