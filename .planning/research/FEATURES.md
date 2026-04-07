# Feature Landscape

**Domain:** College sports intelligence Discord bot (transfer portal, recruiting, career stats)
**Researched:** 2026-04-07
**Sports scope:** Men's college basketball (MBB) and men's college football (CFB)
**Context:** v1.1 milestone features for an existing KU athletics Discord bot

## Table Stakes

Features users expect in a KU athletics Discord bot with recruiting/portal commands. Missing any of these and the commands feel incomplete or useless.

| Feature | Why Expected | Complexity | Dependencies | Notes |
|---------|--------------|------------|--------------|-------|
| `/portal` command filtered by sport | Core use case -- "who's in the portal?" | Medium | Data source integration | Must support both MBB and CFB |
| Portal results show player name, position, original school, star rating | Bare minimum useful data per player | Low | Portal data source | Users need enough context to evaluate a player |
| `/recruit list` view command filtered by sport | Core use case -- "who are we tracking for KU?" | Low | JSON persistence (existing pattern) | Read-only for all users |
| `/recruit add` and `/recruit remove` with admin gating | Admins curate the list; prevents spam entries | Medium | ADMIN_USER_IDS (existing), JSON file | Reuse admin gating pattern from `/post-summary` |
| Recruit entry contains: name, position, previous school, star rating, sport | Minimum useful recruiting profile | Low | Pydantic models | Matches PROJECT.md spec exactly |
| `/stats` command for players on the recruiting list | "Show me career stats for Player X" | High | Career stats data source, recruiting list | Requires reliable player-to-stats matching |
| Embed-based output with consistent formatting | v1.0 established embed pattern; users expect it | Low | `formatting/embeds.py` (existing) | Reuse existing embed builder |
| Error handling with admin alerting | v1.0 pattern; data source failures must not crash bot | Low | `alerting.py` (existing) | Reuse existing admin DM alerting |

## Differentiators

Features that make this bot genuinely useful beyond a basic lookup. Not expected, but valued.

| Feature | Value Proposition | Complexity | Dependencies | Notes |
|---------|-------------------|------------|--------------|-------|
| Portal filtering by position | "Show me all guards in the portal" narrows noise | Low | Portal data already has position field | Simple filter on existing data |
| Portal filtering by conference | "Big 12 portal entries" useful for KU context | Medium | Need conference data per school | CFBD API has conference info for football |
| Recruit list with last-updated timestamps | Shows how fresh the data is | Low | Add timestamp field to JSON entries | Builds trust in curated data |
| Autocomplete for sport selection | discord.py `app_commands.Choice` -- cleaner UX than free text | Low | None beyond discord.py | Two choices: "basketball" and "football" |
| Stats formatted in readable embed tables | Career PPG/RPG/APG for basketball; passing/rushing/receiving for football | Medium | Stats data source | Raw stat dumps are useless without formatting |
| Pagination for large portal result sets | Portal can have 1000+ entries per sport | Medium | Discord UI buttons/views | discord.py has built-in View/Button support |
| Cache layer for portal/stats data | Avoid hitting APIs on every command; portal data changes slowly | Medium | In-memory TTL cache | 15-30 min TTL is reasonable for portal data |
| School name autocomplete | Type "Kan" and get "Kansas" suggested | Low-Medium | School name list from API | CFBD has school/team endpoints |

## Anti-Features

Features to explicitly NOT build. Each has a clear reason.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Real-time portal notifications/alerts | Requires continuous polling of data sources (rate limits, complexity, cost). Portal data changes infrequently enough that on-demand lookup is sufficient. | On-demand `/portal` command only |
| Scraping 247Sports or On3 directly | Both use Cloudflare anti-bot protection. Scraping is fragile (HTML changes break everything), legally gray (ToS violations), and maintenance-intensive. The cat-and-mouse game with Cloudflare is not worth it for a single-server bot. | Use structured APIs: CFBD, CBBD, NCAA API, ESPN hidden endpoints |
| Scraping Sports Reference | Explicit ToS prohibition on bots/scrapers. Rate limited to 20 req/min. Will get IP banned within hours. | Use CFBD/CBBD APIs or ESPN endpoints for stats |
| Database for recruiting data | PROJECT.md explicitly scopes databases out. JSON persistence is the established v1.0 pattern. Recruiting list will be small (tens of entries, not thousands). | JSON file persistence matching DM subscriber opt-in pattern |
| NIL valuation data | Only available behind On3 paywalls; would require scraping | Omit entirely; not core to career stats use case |
| Automated recruiting list updates from external sources | Recruiting lists are curated opinion ("who KU should target"), not objective data. Automation would import noise and remove the human judgment that makes the list valuable. | Manual add/remove by admins is the correct UX |
| Historical portal tracking or trends | Massively increases data scope and storage needs for minimal value | Current portal window only |
| Multi-sport beyond MBB/CFB | Scope creep. Women's basketball, baseball, etc. add API complexity without clear demand. | Two sports only per PROJECT.md: men's basketball and football |
| Player comparison features | Comparing two players side-by-side sounds useful but requires complex stat normalization across positions and sports | Simple per-player stats lookup only |

## Data Source Assessment

This is the critical constraint for the entire milestone. Data source availability determines what features are actually buildable.

### Transfer Portal Data

| Source | Sport | Access | Data Quality | Reliability | Cost | Verdict |
|--------|-------|--------|-------------|-------------|------|---------|
| **CFBD API** (`cfbd-python`) | CFB | REST API + Python SDK | HIGH -- name, position, origin, destination, rating, stars, transfer date, eligibility | HIGH -- maintained, versioned, documented | Free: 1,000 calls/month | **PRIMARY for CFB portal** |
| **CBBD API** (`cbbd-python`) | MBB | REST API + Python SDK | MEDIUM -- roster/player data but NO transfer portal endpoint | MEDIUM -- newer than CFBD, less mature | Free tier (limits unclear) | Use for MBB stats; **portal gap** |
| **NCAA API** (henrygd) | Both | REST (no SDK) | MEDIUM -- stats/scores; portal coverage unclear | MEDIUM -- community project, 5 req/s | Free | **Supplement** for stats |
| **ESPN Hidden API** | Both | Undocumented REST | LOW-MEDIUM -- rosters, stats; no explicit portal endpoint | LOW -- undocumented, breaks without notice | Free | **Fallback** only |
| 247Sports | Both | Web scraping only | HIGH | LOW -- Cloudflare, fragile | Fragile | **DO NOT USE** |
| On3 | Both | Web scraping only | HIGH | LOW -- Cloudflare, paywall | Fragile | **DO NOT USE** |

### Career Stats Data

| Source | Sport | Access | Data Quality | Reliability | Verdict |
|--------|-------|--------|-------------|-------------|---------|
| **CFBD API** | CFB | REST API | HIGH -- season stats, player search by name | HIGH | **PRIMARY for CFB stats** |
| **CBBD API** | MBB | REST API | HIGH -- season stats, player search, box scores | MEDIUM | **PRIMARY for MBB stats** |
| **NCAA API** | Both | REST | MEDIUM -- individual stats endpoints exist | MEDIUM | **Supplement** |
| **ESPN Hidden API** | Both | Undocumented REST | MEDIUM -- athlete endpoints with per-season stats | LOW | **Fallback** |

### Critical Data Gap: MBB Transfer Portal

The biggest risk for this milestone is **men's basketball transfer portal data**. The CBBD API (basketball equivalent of CFBD) does NOT have a transfer portal endpoint. Options to fill this gap, in priority order:

1. **NCAA API** -- investigate whether basketball stats paths expose portal-like data (needs hands-on verification during implementation)
2. **ESPN Hidden API** -- athlete roster endpoints may indicate transfer status indirectly via team changes
3. **Admin-curated portal entries** -- treat MBB portal like the recruiting list: admins manually enter portal players they care about. This is the most reliable fallback and may actually be the best UX for a single-server KU-focused bot (users only care about a subset of portal players anyway).
4. **Web scraping as absolute last resort** -- only if all API options fail, with explicit acceptance of maintenance burden

**Recommendation:** Start with option 3 (admin-curated) as the default for MBB portal. Investigate API options during Phase 1. If a reliable API source exists, migrate to it. This avoids blocking the entire milestone on an unresolved data source question.

## Feature Dependencies

```
API key configuration (env vars)
  |-> CFBD client setup → /portal (CFB), /stats (CFB)
  |-> CBBD client setup → /stats (MBB), /portal (MBB if API available)

JSON persistence (existing pattern from v1.0)
  |-> Recruiting list storage
  |-> MBB portal entries (if admin-curated fallback)

ADMIN_USER_IDS (existing from v1.0)
  |-> /recruit add, /recruit remove gating

Embed formatting (existing from v1.0)
  |-> All new command output

Feature chain:
  /recruit add → /recruit list (list needs entries to display)
  /recruit list → /stats (stats lookup references players on recruiting list)
  Caching layer → /portal, /stats (prevents API rate limit exhaustion)
  Pagination UI → /portal (results can exceed single embed capacity)
```

## MVP Recommendation

### Phase 1: Foundation + CFB Portal (lowest risk, proves the pattern)

Build the data fetching infrastructure and the command with the best API support first.

1. **CFBD API integration** -- API key config in pydantic-settings, async client wrapper, transfer portal fetch, player stats fetch
2. **`/portal` command (CFB first)** -- sport filter (autocomplete), optional school filter, optional position filter
3. **Embed formatting for portal results** -- reuse existing embed patterns, add pagination if result set is large
4. **TTL caching layer** -- simple in-memory cache to avoid burning 1,000 monthly API calls on repeated lookups

### Phase 2: Recruiting List (zero external data dependency)

Entirely within our control. Ships reliably regardless of API availability.

1. **JSON file persistence for recruiting data** -- Pydantic models for recruit entries, load/save pattern matching DM opt-in code
2. **`/recruit add`** -- admin-gated, validates required fields (name, position, previous school, star rating, sport)
3. **`/recruit remove`** -- admin-gated, by player name
4. **`/recruit list`** -- filterable by sport, available to all users, embed output

### Phase 3: MBB Portal + Career Stats (highest risk, depends on Phase 1 + 2)

1. **CBBD API integration** -- API key config, player/roster/stats fetch
2. **`/portal` extended to MBB** -- using CBBD or admin-curated fallback
3. **`/stats` command** -- lookup career stats for players on the recruiting list
4. **Player name-to-ID matching** -- fuzzy match user-entered names against API player records

### Phase ordering rationale

- **CFB portal first** because CFBD has an explicit, well-documented transfer portal endpoint with rich data (name, position, origin, destination, stars, rating, eligibility). Starting here proves the architecture works before tackling the harder MBB case.
- **Recruiting list second** because it has zero external dependencies. It ships reliably even if API integrations hit snags. It also establishes the data model that `/stats` depends on.
- **MBB portal and stats last** because MBB portal has a confirmed data gap (no CBBD portal endpoint), and career stats require player name-to-ID matching -- a fuzzy matching problem that is harder than it sounds. Deferring these lets us solve the hard problems last, with the simpler features already working.

## Complexity Estimates

| Feature | Complexity | Key Challenge |
|---------|------------|---------------|
| CFBD/CBBD API integration | Medium | Async HTTP, response parsing, API key management, error handling for rate limits |
| `/portal` command | Medium | Multiple optional filters, pagination for large result sets, caching |
| Recruiting list CRUD | Low-Medium | JSON file I/O (existing pattern), Pydantic models, admin gating (existing pattern) |
| `/stats` command | High | Player name matching (fuzzy), multiple API calls per lookup, sport-specific stat formatting (basketball vs football stats are entirely different) |
| Pagination UI | Medium | discord.py View/Button pattern, interaction timeouts, state management across pages |
| Caching layer | Low | Simple dict with TTL or `cachetools.TTLCache` -- straightforward |
| Player name fuzzy matching | Medium-High | Names may not match exactly between user input and API records. "DJ" vs "D.J.", nicknames, suffixes (Jr., III). Need fuzzy matching without heavy dependencies. |
| Sport-specific stat formatting | Medium | Basketball (PPG, RPG, APG, FG%, 3P%) vs football (passing yards, TDs, rushing yards, receptions) require entirely different embed layouts |

## Sources

- [CFBD Python SDK -- PlayerTransfer model](https://github.com/CFBD/cfbd-python/blob/main/docs/PlayerTransfer.md) -- transfer portal data fields (confidence: HIGH)
- [CBBD Python SDK](https://github.com/CFBD/cbbd-python) -- college basketball data, confirmed no portal endpoint (confidence: HIGH)
- [NCAA API (henrygd)](https://github.com/henrygd/ncaa-api) -- free API for NCAA data, 5 req/s limit (confidence: MEDIUM)
- [ESPN Hidden API docs](https://github.com/pseudo-r/Public-ESPN-API) -- undocumented endpoints, may break (confidence: LOW)
- [Sports-Reference bot/scraping policy](https://www.sports-reference.com/bot-traffic.html) -- explicit prohibition (confidence: HIGH)
- [CFBD API tiers](https://collegefootballdata.com/api-tiers) -- free tier at 1,000 calls/month (confidence: HIGH)
- [247Sports transfer portal](https://247sports.com/season/2026-football/transferportal/) -- web only, no API (confidence: HIGH)
- [On3 transfer portal](https://www.on3.com/transfer-portal/wire/football/) -- web only, no API (confidence: HIGH)
- [Cloudflare anti-bot difficulty](https://scrapfly.io/blog/posts/how-to-bypass-cloudflare-anti-scraping) -- scraping fragility context (confidence: HIGH)
