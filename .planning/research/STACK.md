# Stack Research: v1.1 Athletics Intelligence

**Domain:** College athletics data sourcing (transfer portal, career stats, recruiting list)
**Researched:** 2026-04-07
**Confidence:** MEDIUM -- ESPN API endpoints are undocumented and could change; 247Sports scraping approach relies on current page structure

## Existing Stack (Do Not Change)

Already validated in v1.0 -- these remain as-is:

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.12+ | Runtime |
| discord.py | 2.7.1 | Discord API wrapper, slash commands, task scheduling |
| openai SDK | 1.x+ | AI provider (pluggable) |
| pydantic-settings | 2.x | Configuration |
| aiohttp | 3.13.3 | HTTP client (bundled with discord.py) |
| pydantic | 2.x | Data models (bundled with pydantic-settings) |

## New Dependencies

### Core: HTML Parsing

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| beautifulsoup4 | 4.14.3 | HTML parsing for 247Sports transfer portal pages | Needed to extract `window.__INITIAL_DATA__` JSON from 247Sports HTML pages. BeautifulSoup is the right choice over selectolax/lxml because: (1) the parsing task is simple (find a script tag, extract JSON), not performance-critical; (2) BS4 handles malformed HTML gracefully; (3) massive ecosystem of examples and docs; (4) actively maintained (last release Nov 2025). selectolax would be overkill speed-wise for a few pages per command invocation. |

### No New Dependencies Needed

| Capability | How to Achieve | Why No New Library |
|------------|----------------|-------------------|
| HTTP requests | `aiohttp` (already installed) | Already a dependency of discord.py. Supports async GET requests natively. Create a dedicated `aiohttp.ClientSession` for external API calls. |
| JSON persistence | `json` (stdlib) | v1.0 already uses JSON file persistence for DM opt-ins. Same pattern for recruiting list data. Pydantic models serialize to/from JSON natively. |
| Data validation | `pydantic` (already installed) | Define models for Player, TransferEntry, CareerStats. Already a dependency. |
| Timezone handling | `zoneinfo` (stdlib) | Already in use for scheduling. |

## Data Source Architecture

### Transfer Portal Data: 247Sports (PRIMARY)

**Source:** `https://247sports.com/season/{year}-{sport}/transferportal/`
- Basketball: `https://247sports.com/season/2026-basketball/transferportal/`
- Football: `https://247sports.com/season/2026-football/transferportal/`

**How it works (verified 2026-04-07):**
- Pages embed full player data in `window.__INITIAL_DATA__` as JSON within a `<script>` tag
- No JavaScript rendering needed -- the JSON is in the initial HTML response
- Basketball: 626 entries; Football: 8,315+ entries (as of April 2026)
- Data includes: player name, position, height/weight, star rating, source school, destination school, status (Entered/Committed/Enrolled/Withdrawn), date entered

**Fetching approach:**
1. `aiohttp` GET request to the 247Sports URL
2. `beautifulsoup4` to find the `<script>` tag containing `__INITIAL_DATA__`
3. `json.loads()` to parse the embedded JSON
4. Filter by school parameter from user's slash command

**Rate limiting:** Be respectful -- cache results for 15-30 minutes per sport. One request per command is fine.

**Confidence:** MEDIUM -- this approach works today but 247Sports could change their page structure or add Cloudflare bot detection. The site currently serves the data in initial HTML without bot challenges.

### Career Stats: ESPN Hidden API (PRIMARY)

**Athlete overview endpoint (verified working 2026-04-07):**
```
https://site.web.api.espn.com/apis/common/v3/sports/{sport}/{league}/athletes/{athleteId}/overview
```

Where:
- Basketball: `sport=basketball`, `league=mens-college-basketball`
- Football: `sport=football`, `league=college-football`

**What it returns (verified):**
- **Basketball:** GP, MPG, FG%, 3PT%, FT%, RPG, APG, BPG, SPG, FPG, TOPG, PPG -- broken out by season
- **Football:** Rushing (ATT, YDS, Y/A, TD, LNG), Receiving (REC, YDS, Y/R, TD, LNG), Fumbles -- broken out by season

**Roster endpoint (verified working 2026-04-07):**
```
https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/teams/{teamId}/roster
```
- Returns full roster with athlete IDs, names, positions, height/weight, experience, headshot URLs
- Kansas team ID: `2305` (both sports)
- Athlete fields: id, firstName, lastName, fullName, displayName, position, jersey, height, weight, experience, headshot URL

**Teams endpoint (for school ID lookup):**
```
https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/teams
```
- Returns all teams with IDs, abbreviations, display names
- Cache on startup -- rarely changes

**No API key required.** Endpoints are unauthenticated.

**How career stats lookup works:**
1. User adds player to KU recruiting list (name, position, previous school)
2. Bot looks up previous school's team ID from cached teams list
3. Bot fetches roster for previous school to find athlete ID by name match
4. Bot calls athlete overview endpoint with athlete ID
5. Returns career stats formatted as Discord embed

**Confidence:** MEDIUM -- undocumented ESPN endpoints. Stable for years and used by multiple open-source projects (SportsDataverse, hoopR), but ESPN could change them. Build with a clean abstraction layer so the data source can be swapped.

## Installation

```bash
# Only new dependency
uv add beautifulsoup4
```

That is it. One new package.

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| 247Sports HTML scraping | On3 transfer portal | On3 pages are more heavily JavaScript-rendered and use React hydration. 247Sports embeds data as `__INITIAL_DATA__` JSON in raw HTML, making extraction trivial without a headless browser. |
| 247Sports HTML scraping | ESPN transfer portal | ESPN does not have a transfer portal API endpoint. Their coverage is editorial articles, not structured data. |
| ESPN hidden API for stats | Sports-Reference.com scraping | Sports-Reference rate-limits to 20 requests/minute and requires HTML scraping of complex table structures. ESPN returns clean JSON with no rate limit headers observed. |
| ESPN hidden API for stats | sportsipy / sportsreference PyPI | Appears unmaintained (last meaningful activity ~2022). Relies on scraping Sports-Reference.com which has changed its page structure multiple times, breaking these packages. ESPN API is more reliable. |
| ESPN hidden API for stats | SportsDataverse (sdv-py) | Focused on play-by-play and box score data, not individual player career stat summaries. Adds a heavy dependency for a narrow use case ESPN handles directly. |
| ESPN hidden API for stats | SportsDataIO | Requires paid API key ($25+/month). ESPN hidden API is free and returns the same data. |
| beautifulsoup4 | selectolax | Selectolax is 30x faster but we parse 1-2 pages per command invocation, not thousands. BS4's better error handling and documentation win for this use case. |
| beautifulsoup4 | lxml | lxml requires C compilation and can have install issues on Windows. BS4 with the default html.parser (stdlib) has zero additional C dependencies. For extracting one script tag, XPath support is unnecessary. |
| aiohttp (existing) | httpx | Would add a new dependency when aiohttp is already installed and in the event loop. No benefit for simple GET requests. |
| JSON file persistence | SQLite | Project constraint from v1.0: avoid database dependencies. JSON files work fine for a single-server bot managing a recruiting list of ~50-100 players. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Selenium / Playwright | Headless browser is massive overkill. 247Sports embeds data as JSON in HTML; ESPN returns JSON directly. No JS rendering needed. | aiohttp + beautifulsoup4 |
| sportsipy / sportsreference | Unmaintained since ~2022. Depends on Sports-Reference.com page structure which breaks frequently. | ESPN hidden API via aiohttp |
| Scrapy | Full scraping framework with its own event loop (Twisted). Conflicts with discord.py's asyncio event loop. Designed for crawling thousands of pages, not fetching 2-3 endpoints. | aiohttp (already in your event loop) |
| requests (sync) | Blocks the asyncio event loop. discord.py is fully async; all HTTP calls must be async. | aiohttp |
| pandas | Sometimes suggested for sports data. Massive dependency for formatting a few stat tables. Pydantic models + string formatting handle this fine. | pydantic models |

## Integration Points with Existing Bot

### HTTP Session Management
Create a shared `aiohttp.ClientSession` in the bot's `setup_hook()` method, close it in `close()`. Do NOT create sessions per-request (connection pooling matters).

### Data Models (Pydantic)
```python
class TransferEntry(BaseModel):
    name: str
    position: str
    height: str | None
    weight: str | None
    stars: float | None
    source_school: str
    destination_school: str | None
    status: str  # "Entered", "Committed", "Enrolled", "Withdrawn"
    sport: Literal["basketball", "football"]

class Recruit(BaseModel):
    name: str
    position: str
    previous_school: str
    stars: int | None  # 1-5
    sport: Literal["basketball", "football"]
    espn_athlete_id: int | None  # resolved on first stats lookup
    added_by: int  # Discord user ID
    added_at: datetime

class SeasonStats(BaseModel):
    season: str
    stats: dict[str, str | float]

class CareerStats(BaseModel):
    athlete_name: str
    athlete_id: int
    sport: Literal["basketball", "football"]
    seasons: list[SeasonStats]
```

### JSON File Persistence
Same pattern as `dm_subscribers.json`:
- `data/recruits.json` -- KU recruiting list
- Load on startup, write on mutation
- Use `asyncio.Lock` for concurrent write protection (same pattern as DM subscriber persistence)

### Caching Strategy
- Transfer portal data: cache 30 minutes (portal updates are not real-time critical)
- ESPN team list: cache on startup, refresh daily
- Career stats: cache 24 hours (stats don't change mid-season frequently)
- Use a simple dict-based TTL cache; no need for redis/memcached for a single-server bot

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| beautifulsoup4 4.14.3 | Python 3.12+ | Uses stdlib `html.parser` by default; no lxml needed |
| aiohttp 3.13.3 | discord.py 2.7.1 | Already installed and working |
| pydantic 2.x | pydantic-settings 2.x | Already installed and working |

## Sources

- [247Sports Basketball Transfer Portal](https://247sports.com/season/2026-basketball/transferportal/) -- verified `__INITIAL_DATA__` JSON embedding (MEDIUM confidence)
- [247Sports Football Transfer Portal](https://247sports.com/season/2026-football/transferportal/) -- verified same pattern, 8,315+ entries
- [ESPN Hidden API Documentation (GitHub)](https://github.com/pseudo-r/Public-ESPN-API) -- endpoint patterns for athlete data
- [ESPN Hidden API Gist](https://gist.github.com/akeaswaran/b48b02f1c94f873c6655e7129910fc3b) -- community-maintained endpoint list
- ESPN athlete overview endpoint -- verified working for basketball and football career stats
- ESPN roster endpoint -- verified working for Kansas (team ID 2305)
- [beautifulsoup4 on PyPI](https://pypi.org/project/beautifulsoup4/) -- v4.14.3, released Nov 2025
- [sportsipy on GitHub](https://github.com/roclark/sportsipy) -- evaluated, unmaintained since ~2022
- [SportsDataverse Python](https://sportsdataverse-py.sportsdataverse.org/) -- evaluated, too focused on play-by-play
- [SportsDataIO](https://sportsdata.io/developers/api-documentation/ncaa-basketball) -- evaluated, requires paid API key

---
*Stack research for: v1.1 Athletics Intelligence (transfer portal, career stats, recruiting list)*
*Researched: 2026-04-07*
