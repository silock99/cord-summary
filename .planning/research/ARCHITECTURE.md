# Architecture Patterns

**Domain:** Athletics intelligence features (transfer portal, recruiting, career stats) integrated into existing Discord summary bot
**Researched:** 2026-04-07

## Existing Architecture Summary

The v1.0 bot follows a clean modular pattern:

```
src/bot/
  client.py           # SummaryBot(commands.Bot) — setup_hook registers commands, starts scheduler
  config.py           # Settings(BaseSettings) — pydantic-settings, all config from .env
  models.py           # ProcessedMessage dataclass, SummaryError
  summarizer.py       # Orchestrator: fetch -> preprocess -> chunk -> summarize
  alerting.py         # Admin error DMs
  language_filter.py  # Blocklist/allowlist for summary language
  commands/
    summary.py        # /summary slash command (register_summary_command pattern)
    post_summary.py   # /post-summary admin command (register_post_summary_command pattern)
  delivery/
    threads.py        # Thread creation for summary posting
  formatting/
    embeds.py         # build_summary_embeds() — topic-boundary splitting
  pipeline/
    fetcher.py        # Discord message history pagination
    preprocessor.py   # Raw message -> ProcessedMessage
    chunker.py        # Token-aware chunking for LLM context
  providers/
    base.py           # SummaryProvider Protocol (summarize + close)
    openai_provider.py
    anthropic_provider.py
  scheduling/
    overnight.py      # OvernightScheduler with tasks.loop
```

**Key patterns established:**
- Command registration: `register_X_command(bot)` functions called in `setup_hook`
- Admin gating: `ADMIN_USER_IDS` parsed from env, checked via `interaction.client.settings.admin_user_ids`
- JSON persistence: `data/` directory, `json.loads`/`json.dumps`, `asyncio.Lock` for concurrency
- Embed formatting: `build_summary_embeds()` handles 4096-char splitting
- Settings: All config via pydantic-settings `Settings` class

## Recommended Architecture for v1.1

### New Component Map

```
src/bot/
  commands/
    portal.py          # NEW: /portal slash command
    recruiting.py      # NEW: /recruit-add, /recruit-remove, /recruit-list commands
    stats.py           # NEW: /career-stats slash command
  data/
    recruiting_store.py # NEW: JSON CRUD for KU recruiting list
  scrapers/
    base.py            # NEW: BaseScraper protocol/ABC
    portal_scraper.py  # NEW: Transfer portal data fetching
    stats_scraper.py   # NEW: Career stats fetching
  formatting/
    embeds.py          # MODIFY: Add athletics embed builders (or new file athletics_embeds.py)
  config.py            # MODIFY: Add new settings (scraper configs, admin role IDs)
  client.py            # MODIFY: Register new commands in setup_hook
```

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `commands/portal.py` | `/portal` slash command — user picks sport + school, sees transfer portal players | `scrapers/portal_scraper.py`, `formatting/` |
| `commands/recruiting.py` | `/recruit-add`, `/recruit-remove`, `/recruit-list` — CRUD for KU recruiting list | `data/recruiting_store.py`, `formatting/` |
| `commands/stats.py` | `/career-stats` — lookup career stats for a player on the recruiting list | `data/recruiting_store.py`, `scrapers/stats_scraper.py`, `formatting/` |
| `data/recruiting_store.py` | JSON file CRUD with asyncio.Lock — stores recruiting list | Filesystem (`data/recruiting.json`) |
| `scrapers/portal_scraper.py` | Fetch transfer portal data from external source | aiohttp (bundled with discord.py), external APIs |
| `scrapers/stats_scraper.py` | Fetch career stats from external source | aiohttp, external APIs |
| `formatting/athletics_embeds.py` | Build Discord embeds for portal results, recruiting list, stats | discord.py Embed API |

### Data Flow

**Transfer Portal Lookup:**
```
User /portal sport:basketball school:Kansas
  -> commands/portal.py validates input, defers response
  -> scrapers/portal_scraper.py fetches portal data (filtered by sport + school)
  -> formatting/athletics_embeds.py builds embed table
  -> Discord embed response (ephemeral)
```

**Recruiting List Management:**
```
User /recruit-add name:"Player Name" position:PG school:"Duke" stars:5 sport:basketball
  -> commands/recruiting.py checks admin permission
  -> data/recruiting_store.py adds player to JSON, acquires asyncio.Lock
  -> Confirmation embed response

User /recruit-list sport:basketball
  -> commands/recruiting.py (no admin check — anyone can view)
  -> data/recruiting_store.py reads current list
  -> formatting/athletics_embeds.py builds list embed
  -> Discord embed response
```

**Career Stats Lookup:**
```
User /career-stats player:"Player Name"
  -> commands/stats.py resolves player from recruiting list
  -> scrapers/stats_scraper.py fetches career stats from external source
  -> formatting/athletics_embeds.py builds stats embed
  -> Discord embed response
```

## Data Sources Strategy

### Transfer Portal Data

**Recommended: Sportradar Trial API** (MEDIUM confidence)

Sportradar added dedicated Transfer Portal endpoints in October 2025:
- Basketball (Men's): `https://api.sportradar.com/ncaamb/trial/v8/en/league/transfer_portal.json`
- Basketball (Women's): `https://api.sportradar.com/ncaawb/trial/v8/en/league/transfer_portal.json`
- Football: Similar endpoint exists

Returns structured JSON with player name, position, height, weight, experience, school. Free 30-day trial with API key. After trial expires, needs paid subscription or alternative.

**Fallback: Web scraping 247sports/On3** (LOW confidence)

Both sites use heavy JavaScript rendering and anti-bot measures. Would require headless browser (Playwright/Selenium) which adds significant complexity. Not recommended as primary approach.

**Fallback: ESPN undocumented API** (LOW confidence)

ESPN has undocumented public endpoints but no known transfer portal endpoint. Could break without notice. Not suitable for this feature.

**Decision: Start with Sportradar trial API.** Build scraper interface as a Protocol so the data source can be swapped later if Sportradar trial expires. The bot owner can register for a free Sportradar developer account. If Sportradar becomes unavailable, the scraper protocol allows plugging in a web scraper or alternative API without changing command code.

### Career Stats Data

**Recommended: ESPN undocumented API** (MEDIUM confidence)

ESPN provides publicly accessible JSON endpoints without authentication:
- Athlete lookup: `https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/teams/{team}/roster`
- Athlete stats: `https://sports.core.api.espn.com/v2/sports/basketball/leagues/mens-college-basketball/athletes/{id}/statistics`

No API key needed. Structured JSON. Covers both basketball and football.

**Caveat:** These are undocumented — ESPN can change them without notice. Build behind the scraper Protocol so a replacement source can be swapped in.

**Fallback: Sports-Reference.com scraping** (LOW confidence)

Sports-Reference has the best career stats data but actively blocks bots with Cloudflare, enforces 20 requests/minute rate limit, and charges $5,000+ for data access. Do NOT scrape.

**Fallback: NCAA API (henrygd)** (MEDIUM confidence)

Free, open-source API wrapping ncaa.com data. Has current-season team/individual stats but NOT player career stats. Useful as a supplementary source but cannot serve as primary career stats source.

**Decision: ESPN undocumented API for career stats, behind a Protocol interface.** Free, structured JSON, covers both sports. Accept the risk that endpoints may change; the Protocol interface means swapping sources is a code change in one file, not a rewrite.

## Patterns to Follow

### Pattern 1: Scraper Protocol (mirrors existing SummaryProvider pattern)

**What:** Define a Protocol for each data source type, matching the existing `SummaryProvider` pattern.
**When:** Any external data fetching.
**Why:** The bot already has this pattern for LLM providers. Consistency + swappability.

```python
from typing import Protocol, runtime_checkable
from dataclasses import dataclass

@dataclass
class PortalPlayer:
    name: str
    position: str
    previous_school: str
    sport: str  # "basketball" | "football"
    height: str | None = None
    experience: str | None = None

@runtime_checkable
class PortalSource(Protocol):
    async def get_portal_players(self, sport: str, school: str | None = None) -> list[PortalPlayer]:
        """Fetch players currently in the transfer portal."""
        ...

    async def close(self) -> None:
        """Clean up resources."""
        ...
```

### Pattern 2: JSON Store with asyncio.Lock (mirrors former DMManager)

**What:** JSON file persistence with async locking for concurrent access.
**When:** Recruiting list CRUD.
**Why:** The bot already used this exact pattern for DM subscribers. No database dependency.

```python
import asyncio
import json
from pathlib import Path
from dataclasses import dataclass, asdict

@dataclass
class Recruit:
    name: str
    position: str
    previous_school: str
    star_rating: int
    sport: str  # "basketball" | "football"

class RecruitingStore:
    def __init__(self, path: Path = Path("data/recruiting.json")):
        self._path = path
        self._lock = asyncio.Lock()
        self._recruits: list[Recruit] = []
        self._load()

    # _load(), _save(), add(), remove(), list_by_sport() methods
    # Follow same pattern as former DMManager
```

### Pattern 3: Command Registration (matches existing pattern)

**What:** Each command module exports a `register_X_command(bot)` function.
**When:** All new slash commands.
**Why:** Exact pattern used by existing `/summary` and `/post-summary`.

```python
# commands/portal.py
def register_portal_command(bot) -> None:
    @bot.tree.command(name="portal", description="Look up transfer portal players")
    @app_commands.describe(sport="Sport to search", school="Filter by school")
    @app_commands.choices(sport=[
        app_commands.Choice(name="Men's Basketball", value="basketball"),
        app_commands.Choice(name="Football", value="football"),
    ])
    async def portal(interaction: discord.Interaction, sport: str, school: str | None = None):
        await interaction.response.defer(ephemeral=True)
        # fetch, format, respond
```

### Pattern 4: Admin Gating (matches existing is_admin pattern)

**What:** Reuse the `is_admin()` check from `post_summary.py`.
**When:** `/recruit-add` and `/recruit-remove` (write operations).
**Why:** Same admin concept, same `ADMIN_USER_IDS` config. `/recruit-list` and `/portal` are open to all users.

Extract the `is_admin()` check into a shared utility (e.g., `bot/checks.py`) since it will now be used by multiple command modules.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Database for Simple List Storage
**What:** Adding SQLite/PostgreSQL for the recruiting list.
**Why bad:** The v1.0 project explicitly decided against databases. The recruiting list is a small dataset (dozens of players at most). JSON file persistence is the established pattern.
**Instead:** Use the `RecruitingStore` with JSON + asyncio.Lock, same as the former `DMManager`.

### Anti-Pattern 2: Scraping JavaScript-Heavy Sites Directly
**What:** Using Playwright/Selenium to scrape 247sports or On3 for portal data.
**Why bad:** Adds heavyweight dependencies (Chromium binary), increases memory/CPU, fragile selectors break on site updates, potential ToS violations.
**Instead:** Use structured APIs (Sportradar, ESPN) that return JSON. Fall back to scraping only if all API options fail.

### Anti-Pattern 3: Tight Coupling Commands to Data Sources
**What:** Having command handlers directly call `aiohttp.get("https://api.sportradar.com/...")`.
**Why bad:** When the data source changes (trial expires, API changes), you rewrite command logic.
**Instead:** Commands call Protocol-typed scrapers. Swap the implementation, not the commands.

### Anti-Pattern 4: One Monolithic Command File
**What:** Putting all new commands in a single file.
**Why bad:** The existing codebase separates `/summary` and `/post-summary` into distinct files. Three new feature areas (portal, recruiting, stats) should follow the same separation.
**Instead:** One file per feature area: `portal.py`, `recruiting.py`, `stats.py`.

## Integration Points with Existing Code

### Files to MODIFY

| File | Change | Reason |
|------|--------|--------|
| `client.py` | Add `register_portal_command`, `register_recruiting_command`, `register_stats_command` calls in `setup_hook`. Initialize `RecruitingStore` and scraper instances. | Command registration pattern |
| `config.py` | Add `sportradar_api_key: str = ""` and any other scraper config fields | New external API credentials |
| `commands/__init__.py` | Export new registration functions | Module interface |

### Files to CREATE

| File | Purpose |
|------|---------|
| `commands/portal.py` | `/portal` command |
| `commands/recruiting.py` | `/recruit-add`, `/recruit-remove`, `/recruit-list` commands |
| `commands/stats.py` | `/career-stats` command |
| `data/recruiting_store.py` | JSON CRUD for recruiting list |
| `scrapers/__init__.py` | Package init |
| `scrapers/base.py` | Protocol definitions for PortalSource and StatsSource |
| `scrapers/portal_scraper.py` | Sportradar API implementation of PortalSource |
| `scrapers/stats_scraper.py` | ESPN API implementation of StatsSource |
| `formatting/athletics_embeds.py` | Embed builders for all athletics features |
| `checks.py` | Extracted `is_admin()` check shared across commands |

### Files UNCHANGED

All existing summary pipeline files (`summarizer.py`, `pipeline/`, `providers/`, `scheduling/`, `delivery/`, `alerting.py`, `language_filter.py`) remain untouched. The new features are additive — they share the bot instance and settings but have no dependency on the summarization pipeline.

## Suggested Build Order

The build order respects dependencies and delivers testable increments:

### Phase 1: Foundation (recruiting store + shared utilities)
1. Extract `is_admin()` into `checks.py`
2. Build `data/recruiting_store.py` (JSON CRUD with asyncio.Lock)
3. Build `commands/recruiting.py` (`/recruit-add`, `/recruit-remove`, `/recruit-list`)
4. Build `formatting/athletics_embeds.py` (recruiting list embed)
5. Wire into `client.py`

**Rationale:** Recruiting list has zero external dependencies. Pure local CRUD. Can be fully tested without API keys or network access. Establishes the data model that career stats will reference later.

### Phase 2: Transfer Portal
1. Build `scrapers/base.py` (Protocol definitions)
2. Build `scrapers/portal_scraper.py` (Sportradar implementation)
3. Add `sportradar_api_key` to `config.py`
4. Build `commands/portal.py` (`/portal` command)
5. Add portal embed builder to `formatting/athletics_embeds.py`
6. Wire into `client.py`

**Rationale:** Portal lookup is independent of the recruiting list. Establishing the scraper Protocol pattern here makes Phase 3 straightforward.

### Phase 3: Career Stats
1. Build `scrapers/stats_scraper.py` (ESPN API implementation)
2. Build `commands/stats.py` (`/career-stats` — resolves player from recruiting list)
3. Add stats embed builder to `formatting/athletics_embeds.py`
4. Wire into `client.py`

**Rationale:** Career stats depends on the recruiting list (Phase 1) for player resolution and follows the scraper Protocol pattern (Phase 2). Must be last.

## Scalability Considerations

| Concern | Current (KU only) | If expanded to multiple teams |
|---------|-------------------|-------------------------------|
| Recruiting list size | ~20-30 players | Store per-team, still JSON-viable up to hundreds |
| Portal API calls | On-demand per user request | Add caching layer (in-memory TTL cache, 15-min expiry) |
| Stats API calls | On-demand, one player at a time | Add caching; ESPN has no auth but may rate-limit |
| Command count | 5 new slash commands | Discord allows 100 guild commands; no issue |
| Data file size | Single `recruiting.json`, <10KB | Still fine at <1MB; revisit if hitting hundreds of KB |

### Caching Recommendation

Add a simple in-memory TTL cache for scraper results to avoid hammering APIs on repeated lookups:

```python
from datetime import datetime, timedelta

class TTLCache:
    def __init__(self, ttl_minutes: int = 15):
        self._cache: dict[str, tuple[datetime, any]] = {}
        self._ttl = timedelta(minutes=ttl_minutes)

    def get(self, key: str):
        if key in self._cache:
            ts, value = self._cache[key]
            if datetime.now() - ts < self._ttl:
                return value
            del self._cache[key]
        return None

    def set(self, key: str, value):
        self._cache[key] = (datetime.now(), value)
```

This is especially important for transfer portal data during the portal window (April 7-21, 2026) when many users may query the same school/sport combination.

## Sources

- [Sportradar Transfer Portal Endpoint (Basketball)](https://developer.sportradar.com/sportradar-updates/changelog/ncaa-basketball-apis-transfer-portal-endpoint) — Transfer Portal API, October 2025
- [Sportradar Transfer Portal Endpoint (Football)](https://developer.sportradar.com/sportradar-updates/changelog/ncaafb-transfer-portal-endpoint) — Football portal API
- [Sportradar Developer Portal — Registration](https://developer.sportradar.com/member/register) — Free trial signup
- [ESPN Public API Documentation (unofficial)](https://github.com/pseudo-r/Public-ESPN-API) — Undocumented ESPN endpoints
- [ESPN Hidden API Gist](https://gist.github.com/akeaswaran/b48b02f1c94f873c6655e7129910fc3b) — Community-documented endpoints
- [NCAA API (henrygd)](https://github.com/henrygd/ncaa-api) — Free NCAA data API
- [Sports-Reference Bot Policy](https://www.sports-reference.com/bot-traffic.html) — Anti-scraping stance, rate limits
- [CollegeFootballData.com API](https://api.collegefootballdata.com/) — College football stats, 1000 calls/mo free
- [BallDontLie NCAAB API](https://ncaab.balldontlie.io/) — College basketball stats API
- [247Sports Transfer Portal](https://247sports.com/season/2026-basketball/transferportal/) — Portal tracking (web, not API)
