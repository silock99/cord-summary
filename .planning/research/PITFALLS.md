# Pitfalls Research

**Domain:** Adding web-scraped college sports data (transfer portal, career stats) and role-gated list management to an existing Discord summary bot
**Researched:** 2026-04-07
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: Web Scraping Sources Break Without Warning

**What goes wrong:**
The bot scrapes transfer portal data or career stats from sites like 247sports.com or sports-reference.com. The site changes its HTML structure, adds Cloudflare protection, or starts returning 403s. The bot silently returns empty results or crashes. Users see "no players found" when the portal is actually full of entries.

**Why it happens:**
College sports sites have no obligation to maintain scrapable HTML. 247sports uses Cloudflare bot detection. Sports-Reference.com explicitly blocks scrapers exceeding 20 requests/minute and jails sessions for an hour on violation. Sites redesign constantly during peak transfer portal windows (April-May for basketball, December-January for football). Developers test against today's HTML and assume it will stay stable.

**How to avoid:**
- Build a scraping abstraction layer: each data source gets its own module with a `fetch()` method returning normalized data models. When HTML changes, only one module needs updating.
- Implement response validation: if the parsed result has zero players when it previously had many, flag it as a likely scraping failure rather than "no data."
- Add a staleness check: if the last successful scrape was more than N hours ago, alert the admin rather than silently serving stale data.
- Cache successful results so users still get data (marked as "last updated X hours ago") when scraping temporarily fails.
- Set proper User-Agent headers and respect robots.txt. Sports-Reference.com specifically bans scrapers that don't identify themselves.

**Warning signs:**
Commands return empty results that previously worked. HTTP 403/429 status codes in logs. Parsing returns None or empty lists without raising errors.

**Phase to address:**
Phase 1 (data source foundation). The abstraction layer and error handling must be designed before any scraping code is written.

---

### Pitfall 2: JSON File Corruption on Concurrent Writes

**What goes wrong:**
Two users add players to the KU recruiting list at the same time. Both reads happen before either write completes. The second write overwrites the first user's addition. Or worse: a write fails mid-operation (bot crash, disk full) and the JSON file is left in a partial/corrupt state -- all recruiting data is lost.

**Why it happens:**
The existing bot uses a `register_X_command(bot)` pattern where commands are closures that capture the bot instance. In an async context, two `/recruit add` commands can interleave: both read the JSON file, both get the same data, both write back with only their own addition. Python's asyncio is single-threaded but yields at every `await` -- so `await file.read()` followed by `await file.write()` is NOT atomic. The v1.0 bot has no JSON persistence in its codebase yet (DM subscriber opt-ins are mentioned in PROJECT.md but not implemented), so there's no existing safe pattern to follow.

**How to avoid:**
- Keep the authoritative data in memory (a dict/list on the bot instance), not on disk. Load from JSON on startup, write to JSON as a backup after mutations.
- Use an `asyncio.Lock` to serialize all write operations to the recruiting list.
- Write to a temporary file first, then atomically rename it over the original (`os.replace()` is atomic on most OS). This prevents corruption from partial writes.
- Keep a backup: before each write, copy the current file to `recruiting_data.backup.json`.
- Validate JSON on load: if the file is corrupt, fall back to the backup.

**Warning signs:**
Players disappear from the list after being added. JSON decode errors in logs. File contains truncated JSON.

**Phase to address:**
Phase 1 (persistence layer). Build the safe read/write pattern as a utility before any feature uses it.

---

### Pitfall 3: Slash Command Bloat Breaking Command Sync

**What goes wrong:**
Adding 4-6 new slash commands (portal lookup, recruit add, recruit remove, recruit list, career stats, possibly more) to the existing 2 commands requires a re-sync. The new commands don't appear, or the old commands disappear. Guild command limit is 100, but the real issue is the sync itself -- it can fail silently, partially succeed, or hit rate limits if called too aggressively.

**Why it happens:**
The existing bot syncs in `setup_hook()` with `tree.copy_global_to(guild=guild)` followed by `tree.sync(guild=guild)`. This pattern re-registers ALL commands every startup. Adding new command modules requires them to be registered BEFORE `setup_hook()` runs `tree.sync()`. If a new command module has a syntax error or import failure, it silently fails to register while the rest of the bot starts up. The developer sees the bot online but the new commands are missing.

**How to avoid:**
- Register all new commands in `setup_hook()` before the `tree.sync()` call, following the existing pattern (`register_summary_command`, `register_post_summary_command`, then the new ones).
- Add a startup log line that lists all registered commands by name so you can verify the count matches expectations.
- Test command registration in isolation before integrating: import the registration function and verify it adds the expected commands to the tree.
- If moving to Cogs later (which the bot does NOT currently use), do it as a dedicated refactoring phase, not mixed in with feature work.

**Warning signs:**
New commands don't appear in Discord's autocomplete. Old commands stop working after adding new ones. Bot starts but logs show fewer synced commands than expected.

**Phase to address:**
Phase 1 (first new command). Verify the registration pattern works for new commands before building all of them.

---

### Pitfall 4: Scraping Blocks the Event Loop

**What goes wrong:**
A user runs `/portal basketball kansas` and the bot freezes for 5-15 seconds while it scrapes and parses an external website. During this time, all other commands and the scheduled summary are blocked. If the external site is slow or down, the freeze can last 30+ seconds or until timeout.

**Why it happens:**
Developers use `requests` (synchronous) or even `urllib` for HTTP calls out of habit. Or they use `aiohttp` correctly but call a synchronous HTML parser (like BeautifulSoup with a large document) without yielding. discord.py runs on a single asyncio event loop -- any blocking call freezes the entire bot.

**How to avoid:**
- Use `aiohttp` (already a dependency of discord.py) for all HTTP requests. Never import `requests`.
- For HTML parsing with BeautifulSoup, if the document is large, run the parse in a thread executor: `await asyncio.get_event_loop().run_in_executor(None, parse_function, html)`.
- Set HTTP request timeouts (10 seconds max). Better to fail fast than block the bot.
- Defer the slash command interaction immediately before any scraping begins (the existing bot already follows this pattern for `/summary`).

**Warning signs:**
Bot becomes unresponsive while scraping is in progress. Other users' commands time out with "This interaction failed." Scheduled tasks fire late.

**Phase to address:**
Phase 1 (HTTP client setup). Establish the async HTTP pattern in the first scraping module and reuse it everywhere.

---

### Pitfall 5: Transfer Portal Data Is Ephemeral and Inconsistent

**What goes wrong:**
A user looks up the transfer portal for Kansas basketball. The bot returns a list. An hour later, the same query returns different results -- not because someone transferred, but because the source site updated its data, restructured the page, or the bot scraped a cached/stale version. Users report "the bot is wrong" when it's actually the source data that's in flux.

**Why it happens:**
Transfer portal data is inherently volatile during portal windows. Players enter and withdraw daily. Different sources (247sports, On3, ESPN) disagree on who is "in" the portal at any given moment. There is no canonical API -- these are journalism sites with editorial judgment about what to list. The NCAA's official portal is not publicly accessible via API.

**How to avoid:**
- Always display "Data from [source] as of [timestamp]" on every portal response. Make the source and freshness visible to users.
- Cache results with a reasonable TTL (15-30 minutes for portal data, longer for career stats which change less often).
- Don't present scraped data as authoritative fact. Frame it as "according to [source]."
- Pick ONE primary source per data type rather than trying to aggregate multiple sources (aggregation multiplies scraping complexity and inconsistency).
- Store the last successful scrape so the bot can serve stale-but-present data with a warning rather than failing entirely.

**Warning signs:**
Users questioning data accuracy. Different results on repeated queries within short time spans. Arguments in the Discord about whether the bot is "right."

**Phase to address:**
Phase 1 (data source selection) and Phase 2 (caching layer). Source selection is a design decision; caching is implementation.

---

### Pitfall 6: Role-Gated Access Implemented Wrong

**What goes wrong:**
The `/recruit add` command should be restricted to authorized users, but the check is implemented incorrectly -- either too permissive (anyone can add/remove players) or too restrictive (even admins can't use it). Or the check works in testing but fails in production because Discord role IDs differ between the test server and production server.

**Why it happens:**
The existing bot uses `ADMIN_USER_IDS` (user IDs in env vars) for admin gating on `/post-summary`. But the v1.1 requirements say "role-gated" for recruiting list management, which implies Discord roles, not hardcoded user IDs. Mixing the two patterns creates confusion. Discord role IDs are server-specific, so a role-based check needs the guild's actual role IDs, not a hardcoded list. Developers test with their own admin account and never test the "unauthorized user" path.

**How to avoid:**
- Decide early: use the existing `ADMIN_USER_IDS` pattern (simpler, matches v1.0) OR use Discord role IDs in config (more flexible but requires new config). Do not mix both.
- If using roles, make the authorized role ID(s) a config setting (`RECRUIT_MANAGER_ROLE_IDS`), not hardcoded.
- Use discord.py's `app_commands.checks` or `default_permissions` decorator for the slash command itself, matching the existing `is_admin()` pattern in `post_summary.py`.
- Test both the authorized AND unauthorized paths. The existing `/post-summary` error handler pattern is a good template.

**Warning signs:**
"You don't have permission" errors for users who should have access. No permission errors for users who should NOT have access. The check works locally but not after deployment.

**Phase to address:**
Phase 2 (recruiting list commands). Define the access model before implementing the commands.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcoding the scraping source URL | Works immediately | URL changes = bot breaks, no way to switch sources without code change | Never -- put base URLs in config |
| Storing scraped HTML in cache instead of parsed data | Faster to implement | Re-parsing on every cache hit, larger cache, HTML changes break cached data | Never -- always cache the parsed/normalized data model |
| Skipping the persistence abstraction | Fewer files to write | Every new feature that needs persistence re-invents file I/O with its own bugs | Never -- build the JSON read/write utility once |
| Not normalizing player names | Scraping "works" | "De'Aaron Fox" vs "DeAaron Fox" vs "De'aaron fox" causes duplicate entries and failed lookups | MVP only -- normalize before v1.1 ships |
| Using `bot.tree.command()` closures for all new commands | Matches v1.0 pattern | 6+ commands in closures makes `client.py` and `setup_hook()` unwieldy | Acceptable for v1.1 but plan a Cog refactor for v1.2 |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| aiohttp + external sports sites | Not setting a User-Agent header, getting blocked as a bot | Set `User-Agent` to a descriptive string; respect `robots.txt` |
| aiohttp + Cloudflare-protected sites | Expecting raw HTML back, getting a JS challenge page instead | Detect Cloudflare challenge responses (check for `cf-` headers or challenge page markers) and fail gracefully with a user-facing message |
| BeautifulSoup + asyncio | Calling `BeautifulSoup(html, 'html.parser')` synchronously in an async function | For large documents, run parsing in `run_in_executor()`. For small pages (< 100KB), synchronous is fine since parsing is CPU-bound and fast |
| JSON persistence + bot shutdown | Data in memory never written to disk if bot crashes | Write after every mutation, not just on shutdown. Use atomic writes (`write temp + rename`) |
| New commands + existing `setup_hook()` | Adding imports/registration calls to `setup_hook()` in wrong order | New `register_X_command(bot)` calls must come BEFORE `tree.sync()`. Follow existing ordering pattern |
| Discord embeds + scraped data | Putting raw scraped text (with HTML entities, weird formatting) into embed fields | Sanitize and normalize all scraped text before embedding. Strip HTML tags, decode entities, limit field lengths |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Scraping on every command invocation | Bot takes 5-10 seconds per portal lookup; external site rate-limits the bot | Cache scrape results with a 15-30 minute TTL. Serve from cache, scrape in background | Immediately -- even with 2-3 users hitting the command |
| Loading the entire JSON file for every read | Noticeable for small files but degrades with 100+ players in the recruiting list | Keep data in memory, persist to disk only on writes | At 500+ entries (unlikely for KU recruiting, but the pattern matters) |
| No request deduplication | Two users run `/portal basketball kansas` simultaneously, triggering two identical scrapes | Use an `asyncio.Lock` per (source, query) to coalesce concurrent identical requests | First time two users query the same thing |
| Parsing full player career stats pages when only summary stats are needed | Unnecessary HTTP requests and parse time for detailed stats pages | Scrape summary/overview pages first; only fetch detailed stats on explicit user request | When career stats pages are 200KB+ of HTML |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Storing scraped data with unsanitized HTML in JSON files | If data is later displayed or processed, could contain unexpected content | Strip all HTML tags and entities before storing. Use `html.unescape()` then remove tags |
| Not validating user input in slash command parameters (player name, school name) | Injection into scraping URLs or file paths | Use discord.py's `Choices` for constrained inputs (sport, school). For free-text (player name), sanitize and URL-encode before using in requests |
| Serving stale cached data without indication | Users make decisions (recruiting interest, transfer monitoring) based on outdated information | Always display data freshness timestamp. Mark stale data visually (different embed color, warning text) |
| Logging scraped content including player personal information | Potential exposure of PII if logs are shared or leaked | Log scrape success/failure metadata only, not the actual player data |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Returning raw scraped data without formatting | Wall of text, hard to scan, looks amateurish | Format as Discord embeds with fields: Player Name, Position, Previous School, Stats. Use inline fields for compact display |
| No feedback during slow scrape operations | User thinks the bot is broken after 5 seconds of silence | Defer immediately, then edit with "Fetching transfer portal data..." status before the actual scrape |
| Not handling "no results" distinctly from "scraping failed" | User can't tell if there are genuinely no Kansas players in the portal or if the bot is broken | Explicit messages: "No Kansas basketball players currently in the transfer portal" vs "Could not fetch portal data -- try again later" |
| Showing ALL portal entries in one response | 50+ players for a popular school creates a massive embed that's hard to read | Paginate results (10-15 per page) with reaction-based or button navigation. Or filter by position |
| Requiring exact name matches for player lookups | "Jalen" doesn't match "Jalen Wilson" -- user gives up | Implement fuzzy matching or substring search. Display "Did you mean...?" for close matches |
| Career stats with no context | Raw numbers are meaningless without context (games played, averages vs totals) | Always show per-game averages alongside totals. Include games played count |

## "Looks Done But Isn't" Checklist

- [ ] **Transfer portal lookup:** What happens when the source site is down? Verify it shows an error message, not an empty list that implies no one is in the portal
- [ ] **Transfer portal lookup:** Does it handle schools with no players in the portal? Verify "no players found" message appears, not a crash
- [ ] **Recruiting list add:** What happens when adding a player who already exists? Verify duplicate detection by normalized name
- [ ] **Recruiting list remove:** What happens when removing a player not on the list? Verify graceful "player not found" response
- [ ] **Recruiting list persistence:** Restart the bot and verify the list survives. Then kill the bot process (SIGKILL) and verify the list survives
- [ ] **Career stats lookup:** What happens when a player's stats page doesn't exist or has no college stats? Verify graceful handling
- [ ] **Career stats lookup:** Does it work for both basketball AND football? The stats page structure is completely different between sports
- [ ] **Sport parameter:** Is the sport parameter validated? What happens if someone passes "hockey"?
- [ ] **Embed field limits:** Embed fields have a 1024-character value limit (not just the 4096 description limit). Stats tables can easily exceed this
- [ ] **Concurrent scraping:** What happens if `/portal` is called 10 times in 30 seconds? Verify caching prevents 10 simultaneous scrapes
- [ ] **JSON file on first run:** Does the bot handle the case where the JSON file doesn't exist yet? Verify it creates the file rather than crashing

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Scraping source breaks (HTML change) | LOW | Update the parsing selectors in the source module. Cached data continues serving until fix is deployed |
| JSON file corrupted | LOW (if backups exist) / HIGH (if not) | Restore from `.backup.json`. If no backup, manually recreate from memory or logs. Prevention is far cheaper |
| Wrong data displayed (stale cache) | LOW | Clear cache, re-scrape. Users may need to be told the previous data was stale |
| Command sync broken (new commands missing) | LOW | Run manual sync via owner command or restart bot. Check import errors in logs |
| Rate-limited by scraping source | MEDIUM | Wait for rate limit to expire (1 hour for Sports-Reference). Serve cached data. Reduce scrape frequency |
| Event loop blocked by synchronous scraping | LOW | Fix the blocking call to async. Restart bot. No data loss |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Scraping sources break | Phase 1 (data source abstraction) | Each source module has a `fetch()` returning a typed data model, with error handling tested |
| JSON file corruption | Phase 1 (persistence utility) | Write utility has atomic writes + backup. Test concurrent writes with asyncio.Lock |
| Slash command sync issues | Phase 1 (first new command) | Log output shows correct command count after sync |
| Blocking event loop | Phase 1 (HTTP client setup) | All HTTP calls use aiohttp. No `import requests` in codebase |
| Data inconsistency/staleness | Phase 2 (caching layer) | Every response includes source and timestamp. Stale data flagged visually |
| Role-gated access wrong | Phase 2 (recruiting commands) | Both authorized and unauthorized paths tested. Config-driven, not hardcoded |
| Portal data ephemeral | Phase 2 (user-facing responses) | "Data from [source] as of [time]" on every embed |
| Embed field overflow | Phase 2 (formatting) | Stats and player lists paginated. Field values checked against 1024 char limit |
| No results vs scrape failure | Phase 2 (error messaging) | Distinct error messages for empty results vs fetch failures |
| Player name matching | Phase 3 (polish) | Fuzzy/substring matching. Normalized names in storage |

## Sources

- [Sports-Reference.com bot traffic policy](https://www.sports-reference.com/bot-traffic.html) -- 20 req/min limit, 1-hour jail
- [Sports-Reference.com data use policy](https://www.sports-reference.com/data_use.html) -- explicit restrictions on scraping
- [247sports transfer portal pages](https://247sports.com/season/2026-basketball/transferportal/) -- Cloudflare-protected
- [NCAA API (henrygd)](https://github.com/henrygd/ncaa-api) -- free API for NCAA.com data, 5 req/sec limit
- [discord.py Cogs documentation](https://discordpy.readthedocs.io/en/stable/ext/commands/cogs.html) -- for future refactoring
- [discord.py slash command guide](https://gist.github.com/AbstractUmbra/a9c188797ae194e592efe05fa129c57f) -- sync patterns
- [Discord rate limit documentation](https://discord.com/developers/docs/topics/rate-limits)
- [Async web scraping guide 2026](https://dev.to/vhub_systems_ed5641f65d59/async-web-scraping-in-python-asyncio-aiohttp-httpx-complete-2026-guide-2ae6)

---
*Pitfalls research for: v1.1 Athletics Intelligence features on existing Discord summary bot*
*Researched: 2026-04-07*
