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

- [x] **RECRUIT-01**: Authorized users can add a player to the KU recruiting list (name, position, previous school, star rating, sport)
- [x] **RECRUIT-02**: Authorized users can remove a player from the KU recruiting list
- [x] **RECRUIT-03**: User can view the KU recruiting list filtered by sport
- [x] **RECRUIT-04**: Recruiting list entries show last-updated timestamps
- [x] **RECRUIT-05**: Sport selection uses autocomplete dropdown
- [x] **RECRUIT-06**: Recruiting data persisted in JSON files

### Career Stats

- [x] **STATS-01**: User can look up college career stats for any player on the KU recruiting list
- [x] **STATS-02**: Basketball stats formatted as PPG, RPG, APG, FG%, 3P% per season
- [x] **STATS-03**: Football stats formatted as passing, rushing, receiving yards and TDs per season
- [x] **STATS-04**: Player name resolution uses fuzzy matching to handle name variations

### Current Roster

- [x] **ROSTER-01**: Editors/admins can bulk-import current KU roster from CFBD (football) or CBBD (basketball) API
- [x] **ROSTER-02**: Each import replaces the existing roster for that sport (replace mode, not append)
- [x] **ROSTER-03**: Career stats auto-fetched for each imported player during import
- [x] **ROSTER-04**: /roster-list displays roster players alphabetically with name, position, jersey number, and class year
- [x] **ROSTER-05**: Roster players appear in /stats lookups and autocomplete alongside recruits and transfers
- [x] **ROSTER-06**: Roster data persists to JSON file and survives bot restarts

### Help Command

- [x] **HELP-01**: /cordbot slash command displays all available bot commands with descriptions, parameters, and usage examples in a categorized embed
- [x] **HELP-02**: Help output is permission-filtered -- non-admins do not see admin-only commands, non-editors do not see editor-only commands

### Infrastructure

- [ ] **INFRA-01**: CFBD API integration for football portal data and stats
- [x] **INFRA-02**: CBBD API integration for basketball stats
- [ ] **INFRA-03**: MBB transfer portal uses admin-curated entries (no API available)
- [x] **INFRA-04**: Channel-to-sport mapping configurable via environment variables
- [x] **INFRA-05**: Authorized user IDs configurable for recruiting list management

### Transfer Target Sheet Sync (Phase 13)

- [ ] **TRANSFER-SHEET-01**: Bot reads the basketball transfer target list from a configured Google Sheet on an hourly schedule via discord.ext.tasks.loop(hours=1)
- [ ] **TRANSFER-SHEET-02**: Service account credentials are loaded by pydantic-settings from env (inline JSON primary, file path fallback) with READONLY scopes
- [ ] **TRANSFER-SHEET-03**: Sheet-sourced targets are cached in memory with an atomic JSON snapshot at data/transfer_targets_basketball.json for restart continuity; added_at is preserved across refreshes on normalized name match
- [ ] **TRANSFER-SHEET-04**: Refresh failures keep the stale cache, log a warning, and DM admins via the existing Phase 6 error-alerting pipeline (no cache clearing on failure)
- [ ] **TRANSFER-SHEET-05**: /transfer-add and /transfer-remove are disabled for sport=basketball AND type=target with a clear "managed in the Google Sheet" message; other slices (basketball outgoing, football) are unchanged
- [ ] **TRANSFER-SHEET-06**: /transfer-list for basketball targets renders the TransferTarget field set (Name, Position, Former School, Height/Weight, KU Interest Level, Made Contact, Notes) with no stars display and a "Synced N ago" footer; football and basketball outgoing rendering is unchanged
- [ ] **TRANSFER-SHEET-07**: Bot startup self-heals data/transfers.json by removing any pre-existing sport=basketball, type=target entries so the sheet is the unambiguous source

## Future Requirements

### Potential Enhancements

- **PORTAL-F01**: Portal filtering by conference (e.g., Big 12 entries)
- **PORTAL-F02**: Real-time portal alerts when new players enter the portal
- **RECRUIT-F01**: School name autocomplete for add command
- **STATS-F01**: Player comparison features (side-by-side stats)
- **TRANSFER-SHEET-F01**: Two-way sync / write-through from Discord commands back to the sheet
- **TRANSFER-SHEET-F02**: Sheet-sourced recruits, roster, football transfers, and outgoing basketball transfers
- **TRANSFER-SHEET-F03**: Manual /refresh-transfer-targets admin command for on-demand pull
- **TRANSFER-SHEET-F04**: Env-configurable sheet column mapping (currently a code constant)

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
| RECRUIT-01 | Phase 7 | Complete |
| RECRUIT-02 | Phase 7 | Complete |
| RECRUIT-03 | Phase 7 | Complete |
| RECRUIT-04 | Phase 7 | Complete |
| RECRUIT-05 | Phase 7 | Complete |
| RECRUIT-06 | Phase 7 | Complete |
| STATS-01 | Phase 9 | Complete |
| STATS-02 | Phase 9 | Complete |
| STATS-03 | Phase 9 | Complete |
| STATS-04 | Phase 9 | Complete |
| ROSTER-01 | Phase 10 | Complete |
| ROSTER-02 | Phase 10 | Complete |
| ROSTER-03 | Phase 10 | Complete |
| ROSTER-04 | Phase 10 | Complete |
| ROSTER-05 | Phase 10 | Complete |
| ROSTER-06 | Phase 10 | Complete |
| HELP-01 | Phase 11 | Complete |
| HELP-02 | Phase 11 | Complete |
| INFRA-01 | Phase 8 | Pending |
| INFRA-02 | Phase 9 | Complete |
| INFRA-03 | Phase 8 | Pending |
| INFRA-04 | Phase 7 | Complete |
| INFRA-05 | Phase 7 | Complete |
| TRANSFER-SHEET-01 | Phase 13 | Pending |
| TRANSFER-SHEET-02 | Phase 13 | Pending |
| TRANSFER-SHEET-03 | Phase 13 | Pending |
| TRANSFER-SHEET-04 | Phase 13 | Pending |
| TRANSFER-SHEET-05 | Phase 13 | Pending |
| TRANSFER-SHEET-06 | Phase 13 | Pending |
| TRANSFER-SHEET-07 | Phase 13 | Pending |

**Coverage:**
- v1.1 requirements: 36 total
- Mapped to phases: 36
- Unmapped: 0

---
*Requirements defined: 2026-04-07*
*Last updated: 2026-04-14 after Phase 13 planning*
