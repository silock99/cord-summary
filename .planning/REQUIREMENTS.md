# Requirements: Discord Summary Bot

**Defined:** 2026-04-07
**Core Value:** Users can quickly catch up on what they missed without reading through hundreds of messages

## v1.1 Requirements

Requirements for Athletics Intelligence milestone. Each maps to roadmap phases.

### Transfer Portal

- [ ] **PORTAL-01**: User can look up transfer portal players filtered by sport and school
- [ ] **PORTAL-02**: User can optionally filter portal results by position
- [ ] **PORTAL-03**: Portal results display player name, position, original school, and star rating in embed format
- [ ] **PORTAL-04**: Portal results paginate with button navigation when exceeding one embed
- [ ] **PORTAL-05**: Portal API responses are cached (15-30 min TTL) to reduce API call usage
- [ ] **PORTAL-06**: Sport auto-detected from channel-to-sport mapping config, with manual override

### Recruiting

- [ ] **RECRUIT-01**: Authorized users can add a player to the KU recruiting list (name, position, previous school, star rating, sport)
- [ ] **RECRUIT-02**: Authorized users can remove a player from the KU recruiting list
- [ ] **RECRUIT-03**: User can view the KU recruiting list filtered by sport
- [ ] **RECRUIT-04**: Recruiting list entries show last-updated timestamps
- [ ] **RECRUIT-05**: Sport selection uses autocomplete dropdown
- [x] **RECRUIT-06**: Recruiting data persisted in JSON files

### Career Stats

- [ ] **STATS-01**: User can look up college career stats for any player on the KU recruiting list
- [ ] **STATS-02**: Basketball stats formatted as PPG, RPG, APG, FG%, 3P% per season
- [ ] **STATS-03**: Football stats formatted as passing, rushing, receiving yards and TDs per season
- [ ] **STATS-04**: Player name resolution uses fuzzy matching to handle name variations

### Infrastructure

- [ ] **INFRA-01**: CFBD API integration for football portal data and stats
- [ ] **INFRA-02**: CBBD API integration for basketball stats
- [ ] **INFRA-03**: MBB transfer portal uses admin-curated entries (no API available)
- [x] **INFRA-04**: Channel-to-sport mapping configurable via environment variables
- [x] **INFRA-05**: Authorized user IDs configurable for recruiting list management

## Future Requirements

### Potential Enhancements

- **PORTAL-F01**: Portal filtering by conference (e.g., Big 12 entries)
- **PORTAL-F02**: Real-time portal alerts when new players enter the portal
- **RECRUIT-F01**: School name autocomplete for add command
- **STATS-F01**: Player comparison features (side-by-side stats)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Scraping 247Sports/On3/Sports Reference | Cloudflare anti-bot protection, ToS violations, fragile maintenance |
| Real-time portal notifications | Requires continuous polling; on-demand lookup is sufficient |
| NIL valuation data | Only available behind paywalls |
| Historical portal tracking/trends | Increases data scope and storage for minimal value |
| Multi-sport beyond MBB/CFB | Scope creep without clear demand |
| Player comparison features | Complex stat normalization; defer to future |
| Database storage | JSON persistence is sufficient for recruiting list scale |
| Automated recruiting list updates | Recruiting lists are curated opinion; automation adds noise |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PORTAL-01 | Phase 8 | Pending |
| PORTAL-02 | Phase 8 | Pending |
| PORTAL-03 | Phase 8 | Pending |
| PORTAL-04 | Phase 8 | Pending |
| PORTAL-05 | Phase 8 | Pending |
| PORTAL-06 | Phase 8 | Pending |
| RECRUIT-01 | Phase 7 | Pending |
| RECRUIT-02 | Phase 7 | Pending |
| RECRUIT-03 | Phase 7 | Pending |
| RECRUIT-04 | Phase 7 | Pending |
| RECRUIT-05 | Phase 7 | Pending |
| RECRUIT-06 | Phase 7 | Complete |
| STATS-01 | Phase 9 | Pending |
| STATS-02 | Phase 9 | Pending |
| STATS-03 | Phase 9 | Pending |
| STATS-04 | Phase 9 | Pending |
| INFRA-01 | Phase 8 | Pending |
| INFRA-02 | Phase 9 | Pending |
| INFRA-03 | Phase 8 | Pending |
| INFRA-04 | Phase 7 | Complete |
| INFRA-05 | Phase 7 | Complete |

**Coverage:**
- v1.1 requirements: 21 total
- Mapped to phases: 21
- Unmapped: 0

---
*Requirements defined: 2026-04-07*
*Last updated: 2026-04-07 after roadmap creation*
