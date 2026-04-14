# Phase 13: Connect a Google Sheet to the Recruit List Function — Research

**Researched:** 2026-04-14
**Domain:** Google Sheets API integration (read-only) inside an async discord.py bot
**Confidence:** HIGH for library/auth/scheduling; MEDIUM for quota headroom; LOW pending user-supplied sheet metadata (ID, tab, columns)

## Summary

The phase wires an existing Google Sheet in as the read-only source of truth for the basketball transfer-target slice of `bot.transfer_store`. An hourly `discord.ext.tasks.loop(hours=1)` fetches the sheet via a service account, normalizes rows into `PlayerEntry` objects, and caches them in memory plus a JSON snapshot on disk. `/transfer-list` reads from cache; `/transfer-add` and `/transfer-remove` are refused for `sport=basketball AND type=target` only.

The ecosystem winner is **gspread 6.2.1 + `service_account_from_dict` + `READONLY_SCOPES`**, wrapped with `asyncio.to_thread` to keep the event loop clean. The JSON snapshot piggybacks on the atomic-write pattern already in `RecruitingStore`. Scheduling uses the same `discord.ext.tasks.loop` primitive already in `OvernightScheduler`. Failures pipe through the existing `send_error_alerts` DM path.

**Primary recommendation:** Build a new `src/bot/sources/sheets.py` module that owns (a) the gspread client factory, (b) the row→`PlayerEntry` mapper, (c) an in-memory cache + atomic JSON snapshot, and (d) a small `SheetSyncScheduler` class that mirrors `OvernightScheduler`'s shape. Do NOT reuse `RecruitingStore` for the basketball-target slice — keep sheet-sourced data in a separate store and merge at read time in the `/transfer-list` handler. This avoids collision with locally-managed outgoing entries that share `data/transfers.json`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Sheet → Bot, read-only. Sheet is the single source of truth for basketball transfer targets.
- **D-02:** `/transfer-add`, `/transfer-remove` are disabled for `sport=basketball AND type=target`. They return a clear message indicating this data is managed in the Google Sheet. Other slices (basketball outgoing, football transfers) continue to work as before.
- **D-03:** Only basketball transfers with `type=target` are sourced from the sheet. Outgoing basketball transfers stay admin-curated via existing commands.
- **D-04:** The sheet does not replace the entire `transfer_store` — it feeds one slice. Store must be able to merge sheet-sourced targets with locally managed outgoing entries without collision.
- **D-05:** Scheduled hourly refresh via `discord.ext.tasks.loop(hours=1)` (no new scheduler).
- **D-06:** On bot startup, perform an initial fetch before the scheduled loop begins so the first `/transfer-list` call isn't empty.
- **D-07:** Cache strategy: in-memory list + JSON snapshot on disk. `/transfer-list` always serves from memory. Snapshot enables last-known-good startup if the first refresh fails.
- **D-08:** On refresh failure: keep serving stale cache, log warning via Phase 6 error alerting. Do NOT clear the cache.
- **D-09:** Google service account with a JSON key. Key path or inline JSON loaded via `pydantic-settings`.
- **D-10:** Sheet must be shared (viewer access) with the service account email — operational step documented in README/notes.
- **D-11:** Existing sheet, fixed schema. Sheet ID, tab name, column layout needed before planning completes.
- **D-12:** Column mapping → `PlayerEntry` fields: `name`, `position`, `school`, `stars`. Extra columns ignored. Missing required columns = row skipped with warning.
- **D-13:** Row validation: missing `name` → skip. Invalid `stars` (non-int, out-of-range 0–5) → default 0 with warning.

### Claude's Discretion

- Exact module layout (e.g., `src/bot/sheets/` vs extending `src/bot/storage/`).
- Library choice (`gspread`, `google-api-python-client`, etc.) — must be async-friendly or wrapped in `asyncio.to_thread`.
- Retry/backoff policy for transient API failures within a single refresh attempt.
- Log format and verbosity of refresh-loop output.
- Exact wording of the "managed in Google Sheet" message returned by disabled commands.

### Deferred Ideas (OUT OF SCOPE)

- Two-way sync / write-through to the sheet.
- Sheet-sourced recruits, roster, football transfers.
- Manual `/refresh-transfers` admin command.
- Configurable/flexible sheet column mapping.
- Renaming the phase in the roadmap.
</user_constraints>

<phase_requirements>
## Phase Requirements

Planner should propose these TRANSFER-SHEET-* IDs in REQUIREMENTS.md. None exist yet.

| Proposed ID | Description | Research Support |
|-------------|-------------|------------------|
| TRANSFER-SHEET-01 | Bot reads basketball transfer-target list from a Google Sheet on an hourly schedule | gspread + `tasks.loop(hours=1)` — both verified below |
| TRANSFER-SHEET-02 | `/transfer-list` (basketball, type=target) serves from in-memory cache; never hits Sheets API per-request | In-memory snapshot pattern + existing `RecruitingStore` read path |
| TRANSFER-SHEET-03 | JSON snapshot of sheet-sourced targets persists across restarts; startup loads snapshot then triggers initial fetch | Atomic-write pattern from `recruiting_store.py` |
| TRANSFER-SHEET-04 | `/transfer-add` and `/transfer-remove` reject basketball + type=target with a clear "managed in Google Sheet" message; other slices unaffected | Command guard pattern shown below |
| TRANSFER-SHEET-05 | Refresh failures are logged and DM'd to admins via existing `send_error_alerts`; cache is NOT cleared on failure | `alerting.py` + `tasks.loop.error()` hook precedent in `OvernightScheduler` |
| TRANSFER-SHEET-06 | Row validation: missing `name` skipped; invalid `stars` default 0 with warning | D-13 |
| TRANSFER-SHEET-07 | Service account credentials configurable via env (inline JSON or file path) using `pydantic-settings` | gspread `service_account_from_dict` verified below |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

Binding directives the planner must honor:

- **Python 3.12+**, `discord.py >= 2.7.1` already pinned in `pyproject.toml`.
- **No new scheduler** — use `discord.ext.tasks`. APScheduler / Celery forbidden.
- **No database** — JSON persistence only. Atomic-write pattern already in-repo.
- **Config via `pydantic-settings`**, env vars, `.env` files — not hand-rolled.
- **Package manager: `uv`**. Add dependencies with `uv add`, not `pip install`.
- **Lint: `ruff`**. Tests: `pytest` + `pytest-asyncio`.
- **GSD workflow enforced** — planner drives, no direct edits outside a GSD command.
- **No multi-provider abstraction layers** (no LiteLLM/LangChain ethos) — but this phase isn't LLM-adjacent, so the concern here translates to: don't pull in a bloated "sheet abstraction" library. gspread is narrow enough.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| gspread | 6.2.1 | Google Sheets API wrapper | Highest-level Python library for Sheets. Supports service-account JSON file AND in-memory dict auth. Has explicit `READONLY_SCOPES`. Narrow dependency (pulls `google-auth` + `requests`). Actively maintained. [VERIFIED: PyPI shows 6.2.1 released 2025-05-14] |
| google-auth | >=2.x (gspread dep) | Service account OAuth2 | Transitive dep of gspread. `google.oauth2.service_account.Credentials` is the underlying primitive. [VERIFIED: gspread/auth.py source] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| asyncio (stdlib) | 3.12+ | `asyncio.to_thread` wrapping | gspread is sync; wrap each refresh call in `to_thread` — matches project's existing convention for sync SDKs (see `stats/basketball.py` comment about cbbd SDK) [VERIFIED: codebase grep] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| gspread | `google-api-python-client` (googleapiclient.discovery.build) | Lower-level, no ergonomics. Means you build row-to-dict mapping yourself, handle A1 notation manually, deal with the discovery document. gspread already solves all of that. Pick only if gspread had a security issue (none known as of 2026-04). [CITED: gspread docs introduction] |
| gspread | `pygsheets` | Smaller community, less current. gspread's last release is more recent and its scope matches exactly what we need. [ASSUMED] |
| gspread (sync + `to_thread`) | `gspread-asyncio` | gspread-asyncio hasn't had a release in >12 months as of search. Wrapping gspread in `to_thread` is trivial (one refresh per hour) and keeps us on the actively-maintained library. [VERIFIED: PyPI / web search] |
| gspread (sync + `to_thread`) | `aiospread` | Smaller, less maintained. Same reasoning as gspread-asyncio. [ASSUMED] |

**Installation:**

```bash
uv add gspread
```

`google-auth` comes in transitively. No extra explicit pin needed unless version conflict surfaces.

**Version verification note for planner:** Before committing the plan, run `uv add gspread` and record the resolved version in the plan. At research time the latest PyPI release is **6.2.1** (published 2025-05-14). [VERIFIED: PyPI + libraries.io]

### Transitive dependency check

- gspread pulls `google-auth` and `requests`. Neither conflicts with the bot's current deps (`discord.py`, `openai`, `anthropic`, `cfbd`, `pydantic-settings`, `tzdata`). `requests` is not currently a direct dep — adding it as a transitive is fine. `google-auth` is small and stable. [VERIFIED: PyPI metadata for gspread]

## Architecture Patterns

### Recommended Project Structure

```
src/bot/
├── sources/
│   ├── __init__.py
│   └── sheets.py              # NEW: gspread client + row mapper + in-memory cache + snapshot
├── scheduling/
│   ├── overnight.py           # EXISTING
│   └── sheet_sync.py          # NEW: SheetSyncScheduler class (mirrors OvernightScheduler shape)
├── commands/
│   └── transfers.py           # MODIFIED: guard in /transfer-add, /transfer-remove; /transfer-list merge
├── storage/
│   └── recruiting_store.py    # UNCHANGED
└── client.py                  # MODIFIED: instantiate sheet store, wire scheduler, trigger initial fetch

data/
└── transfer_targets_basketball.json   # NEW: snapshot of sheet-sourced entries
```

Rationale for `src/bot/sources/` rather than extending `storage/`: the sheet is an **ingress source**, not a local store. The stats modules (`src/bot/stats/`) already precedent a "where data comes in from" folder. Keeping it separate makes "sheet is read-only upstream" self-documenting.

### Pattern 1: Authentication from env (inline JSON OR file path)

**What:** Support both deployment styles — file path for local dev (easier), inline JSON for Railway/Procfile/Heroku-style single-env-blob deployments (no filesystem).

**When to use:** Always — user's deployment uses `nixpacks.toml` + `Procfile`, which is Railway-flavored. Railway does not give you a persistent-filesystem-mounted secret file by default; the path-only option will corner the user. Inline JSON is the robust default.

**Example:**

```python
# src/bot/config.py — add to Settings
from pydantic import Field, computed_field
import json

class Settings(BaseSettings):
    # ... existing ...

    # Phase 13: Google Sheets for basketball transfer targets
    sheet_service_account_json_raw: str = Field(default="", alias="SHEET_SERVICE_ACCOUNT_JSON")
    sheet_service_account_file: str = Field(default="", alias="SHEET_SERVICE_ACCOUNT_FILE")
    transfer_target_sheet_id: str = Field(default="", alias="TRANSFER_TARGET_SHEET_ID")
    transfer_target_sheet_tab: str = Field(default="", alias="TRANSFER_TARGET_SHEET_TAB")
    # Column letters (A, B, C, ...) or 1-indexed numbers — TBD after user supplies schema.
    # Research recommends env-configurable even though D-11 fixes the schema, so a minor
    # sheet tweak doesn't require a code change.
    transfer_target_sheet_col_name: str = Field(default="A", alias="TRANSFER_TARGET_SHEET_COL_NAME")
    transfer_target_sheet_col_position: str = Field(default="B", alias="TRANSFER_TARGET_SHEET_COL_POSITION")
    transfer_target_sheet_col_school: str = Field(default="C", alias="TRANSFER_TARGET_SHEET_COL_SCHOOL")
    transfer_target_sheet_col_stars: str = Field(default="D", alias="TRANSFER_TARGET_SHEET_COL_STARS")
    transfer_target_sheet_header_row: int = 1  # Rows 1..N are headers; data starts at N+1

    @computed_field
    @property
    def sheet_service_account_info(self) -> dict | None:
        """Return parsed service account info or None if not configured.

        Prefers inline JSON env; falls back to file path.
        """
        raw = self.sheet_service_account_json_raw
        if raw:
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                # Planner: decide whether to raise at startup or warn and degrade.
                # Recommendation: warn + return None — bot still boots, just without sheet sync.
                return None
        path = self.sheet_service_account_file
        if path:
            from pathlib import Path
            p = Path(path)
            if p.exists():
                return json.loads(p.read_text(encoding="utf-8"))
        return None
```

[VERIFIED: gspread/auth.py — `service_account_from_dict(info: Mapping[str, Any], scopes=...)`]

### Pattern 2: gspread client factory (read-only scopes)

```python
# src/bot/sources/sheets.py
import gspread
from gspread.auth import READONLY_SCOPES

def build_sheets_client(service_account_info: dict) -> gspread.Client:
    """Build a read-only gspread client from a service account info dict.

    READONLY_SCOPES restricts the credential to spreadsheets.readonly + drive.readonly
    even if the service account has broader permissions in IAM.
    """
    return gspread.service_account_from_dict(service_account_info, scopes=READONLY_SCOPES)
```

[VERIFIED: gspread/auth.py source shows `READONLY_SCOPES = ("spreadsheets.readonly", "drive.readonly")`]

### Pattern 3: Refresh loop mirrors `OvernightScheduler`

`OvernightScheduler` in `src/bot/scheduling/overnight.py` is the canonical precedent. Mirror its shape:

```python
# src/bot/scheduling/sheet_sync.py
import logging
from discord.ext import tasks
from bot.alerting import send_error_alerts

logger = logging.getLogger(__name__)


class SheetSyncScheduler:
    def __init__(self, bot) -> None:
        self.bot = bot
        self._task = tasks.loop(hours=1)(self._refresh)
        self._task.before_loop(self._wait_ready)
        self._task.error(self._on_error)

    async def _wait_ready(self) -> None:
        await self.bot.wait_until_ready()

    async def _on_error(self, error: Exception) -> None:
        logger.error("Sheet refresh task crashed", exc_info=error)
        await send_error_alerts(
            self.bot,
            "Basketball transfer-target sheet sync",
            [f"Task-level failure: {type(error).__name__}: {error}"],
        )
        # Critical: restart the loop so one crash doesn't kill the hourly schedule.
        self._task.restart()

    async def _refresh(self) -> None:
        try:
            await self.bot.transfer_target_sheet_store.refresh()
        except Exception as e:
            logger.warning("Sheet refresh failed, keeping stale cache: %s", e, exc_info=True)
            await send_error_alerts(
                self.bot,
                "Basketball transfer-target sheet sync",
                [f"Refresh failed (stale cache retained): {type(e).__name__}: {e}"],
            )

    def start(self) -> None:
        self._task.start()

    def cancel(self) -> None:
        self._task.cancel()
```

**Startup ordering in `client.py` `setup_hook`:**

```python
# After existing store setup and BEFORE command registration:
self.transfer_target_sheet_store = SheetTransferTargetStore(
    settings=self.settings,
    snapshot_path=Path("data/transfer_targets_basketball.json"),
)
self.transfer_target_sheet_store.load_snapshot()  # Sync, fast — gives us last-known-good immediately.

# Later, AFTER self.scheduler start, trigger initial fetch but don't block setup_hook:
async def _initial_fetch():
    await self.wait_until_ready()
    try:
        await self.transfer_target_sheet_store.refresh()
    except Exception:
        logger.warning("Initial sheet fetch failed; serving from snapshot", exc_info=True)

asyncio.create_task(_initial_fetch())
self.sheet_sync_scheduler = SheetSyncScheduler(self)
self.sheet_sync_scheduler.start()
```

**Important:** `tasks.loop(hours=1)` fires its FIRST iteration immediately after `start()` unless you pass `reconnect=True` + `before_loop`. But "immediately" still happens after `await bot.wait_until_ready()` because of the `before_loop` hook. The independent `asyncio.create_task(_initial_fetch())` guarantees a refresh attempt on boot even if the task loop's first tick races the first user request. The snapshot-on-disk fallback means a cold start with no network still serves data. [VERIFIED: existing `OvernightScheduler._wait_ready` pattern + discord.py `tasks.loop` docs]

### Pattern 4: Row → PlayerEntry mapping with validation

```python
# src/bot/sources/sheets.py
import logging
from datetime import datetime, timezone
from bot.storage.models import PlayerEntry

logger = logging.getLogger(__name__)


def row_to_player(row: dict, now_iso: str) -> PlayerEntry | None:
    """Map a sheet row (dict keyed by column letter or header) to a PlayerEntry.

    Returns None if the row is invalid (missing name). Invalid stars default to 0.
    """
    name = (row.get("name") or "").strip()
    if not name:
        logger.warning("Skipping sheet row with missing name: %r", row)
        return None
    position = (row.get("position") or "").strip()
    school = (row.get("school") or "").strip()
    stars_raw = row.get("stars", 0)
    try:
        stars = int(stars_raw)
        if stars < 0 or stars > 5:
            raise ValueError("out of range 0-5")
    except (TypeError, ValueError) as e:
        logger.warning("Invalid stars %r for %s, defaulting to 0: %s", stars_raw, name, e)
        stars = 0
    return PlayerEntry(
        name=name,
        position=position,
        school=school,
        stars=stars,
        type="target",
        added_at=now_iso,  # Sheet rows don't carry a stable "added_at" — use refresh time.
    )
```

### Pattern 5: Disable commands for sport=basketball + type=target slice

**Placement:** guard in the command handler, not the store. Reason: the store is generic (`RecruitingStore`), and callers may legitimately add basketball-outgoing or football entries. Only the `/transfer-add` command handler knows the `type` value the user picked.

```python
# src/bot/commands/transfers.py — inside transfer_add, AFTER sport is resolved
if sport == "basketball" and transfer_type == "target":
    await interaction.edit_original_response(
        content=(
            "Basketball transfer targets are managed in the team Google Sheet. "
            "Edit the sheet and the bot will pick up the change within an hour."
        )
    )
    return
```

For `/transfer-remove`: same sport check, but the user doesn't supply a `type`. Reject if sport is basketball AND the matched player's `type == "target"` (look it up first, then decide). Alternatively reject any basketball remove targeting a sheet-backed entry.

**Do NOT** push this guard into `RecruitingStore.add_player` / `remove_player` — the guard is a UX concern, not a data-integrity one, and the store is shared across recruits, transfers, and roster.

### Pattern 6: Merge read path for `/transfer-list`

`/transfer-list` basketball needs to combine:

- `bot.transfer_store.list_players("basketball")` → yields only `type == "outgoing"` entries (once the sheet takes over targets, the local store should not contain basketball targets — see "Data migration" below).
- `bot.transfer_target_sheet_store.get_targets()` → yields all sheet-sourced `type == "target"` entries.

Merge into a single list before the existing sectioning logic (`outgoing` vs `targets`) runs. The rest of the embed code in `transfers.py` is untouched.

### Anti-Patterns to Avoid

- **Per-request Sheets API fetch.** The user picked hourly explicitly (D-05). Fetching on every `/transfer-list` call will (a) destroy response latency, (b) hit Google quota limits on a busy server. Serve from memory always.
- **Writing sheet data into the existing `data/transfers.json`.** Two systems writing to one file = race. Separate JSON snapshot file for sheet-sourced data.
- **Blocking `setup_hook` on the initial fetch.** If the Sheets API is slow/down at boot, the bot never comes online. Fire-and-forget the initial fetch with snapshot fallback.
- **Global try/except that swallows and returns empty list.** That silently wipes the cache on transient failure. D-08 explicitly says keep stale cache; log; alert.
- **Using `gspread.service_account()` with a file path only.** Railway/Procfile deployments won't have a persistent file. Support inline JSON first.
- **Using `DEFAULT_SCOPES`.** Those are read/write. Principle of least privilege: pass `scopes=READONLY_SCOPES` explicitly.
- **Polling with `tasks.loop(minutes=1)` "just in case."** User picked hourly. Minute-granularity polling burns quota and signals over-engineering.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Google OAuth2 service-account token minting | Direct JWT signing + refresh logic | `google-auth` (via gspread) | Token refresh, clock skew, scope handling are easy to get subtly wrong |
| A1 notation → row/col arithmetic | Custom column-letter parser | gspread's `worksheet.get_all_records()` / `worksheet.col_values()` | gspread handles A1 and paginates internally |
| Async wrapper for a sync library | Threading pool / custom executor | `asyncio.to_thread(func, *args)` (stdlib) | One-liner, correct event-loop semantics, already used in the codebase pattern |
| Atomic JSON write | `open()` + `write()` + `rename()` | Reuse the pattern in `recruiting_store.py` (`tempfile.mkstemp` + `os.replace`) | Already proven, handles Windows/POSIX differences |
| Scheduled repeating task | Thread + `time.sleep` | `discord.ext.tasks.loop(hours=1)` | Integrates with event loop, handles reconnection, already used in `OvernightScheduler` |
| Retry/backoff | Hand-rolled counters | Within one refresh attempt, just try once; rely on the hourly cadence for retries | Don't over-engineer — a missed hour is fine given D-08 (stale cache OK) |

**Key insight:** Every major concern in this phase has a precedent in the repo. The research instinct "can I mirror an existing module?" is right in 90% of cases here.

## Runtime State Inventory

This phase is **greenfield integration, not a rename/refactor**, so most categories are trivially "nothing." Listed explicitly for completeness:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `data/transfers.json` currently contains whatever basketball target entries were manually added via `/transfer-add`. These would shadow/conflict with sheet-sourced entries. | **One-time cleanup at deploy:** remove all `sport=basketball AND type=target` entries from `data/transfers.json` after the sheet store is online. Planner should include a one-shot migration task or an admin command. OR: change `/transfer-list` merge logic to prefer sheet over local when both exist. Recommended: clean the file — simpler, no ambiguity. |
| Live service config | None — no external service stores this string. | None. |
| OS-registered state | None — bot is a process, no scheduled tasks or services registered against it. | None. |
| Secrets / env vars | New env vars introduced: `SHEET_SERVICE_ACCOUNT_JSON` (or `SHEET_SERVICE_ACCOUNT_FILE`), `TRANSFER_TARGET_SHEET_ID`, `TRANSFER_TARGET_SHEET_TAB`, `TRANSFER_TARGET_SHEET_COL_*`. | Add to `.env.example`. Document in README/phase notes. Operational step: share the sheet with the service account email (D-10). |
| Build artifacts | None — no compiled artifacts. `uv sync` regenerates lockfile. | After merging, run `uv sync` on deploy target (already in `nixpacks.toml`). |

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| gspread (PyPI) | Sheet reads | To be installed | 6.2.1 latest | — (blocking) |
| google-auth (PyPI, transitive) | gspread | Auto via gspread | >=2.x | — |
| requests (PyPI, transitive) | gspread | Auto via gspread | >=2.x | — |
| Google Cloud project + service account | Runtime auth | **User action required** | — | None — blocking until user provisions |
| Sheet shared with service account email | Runtime auth | **User action required** (D-10) | — | None — blocking until user does this |
| Sheet ID, tab name, column layout | Row mapping | **User action required** (D-11) | — | Planner should collect before finalizing plan |
| Internet egress to `sheets.googleapis.com` | Refresh | Presumed yes (same egress as Discord/OpenAI) | — | — |

**Missing dependencies with no fallback:**

- Google service account JSON — without this the feature cannot work. Planner must list this as a pre-execution user task.
- Sheet ID + tab + column letters from the user — planner should collect during the first planning interaction.

**Missing dependencies with fallback:**

- If `SHEET_SERVICE_ACCOUNT_JSON` is empty at startup: log a warning, skip `SheetSyncScheduler.start()`, leave `/transfer-list` basketball to return whatever is in the local store. Bot still boots. This is the graceful-degradation shape.

## Common Pitfalls

### Pitfall 1: Service account has access but the sheet wasn't shared with it

**What goes wrong:** gspread call raises `gspread.exceptions.APIError` with HTTP 403. Looks like an auth failure but the JSON key is valid.

**Why it happens:** Operator forgot D-10 — the service account's email (`...@...iam.gserviceaccount.com`, found in the JSON's `client_email` field) must be added as a Viewer on the sheet from the Google Sheets "Share" UI.

**How to avoid:** Document the service-account email in the startup log on first successful auth. Include it in the error message on 403. Planner should include this in deployment notes.

**Warning signs:** Refresh fails immediately on every attempt; auth token fetch succeeds (no 401); reads return 403.

### Pitfall 2: Quota exhaustion

**What goes wrong:** HTTP 429 from Sheets API.

**Why it happens:** Sheets API limits are **300 read requests per minute per project** and **60 per minute per user (service account)**. [CITED: https://developers.google.com/workspace/sheets/api/limits, updated 2026-03-02]

**Risk assessment:** Hourly refresh fetching one sheet is nowhere near these limits. Safe by 2+ orders of magnitude. The risk is a buggy refresh loop that spirals.

**How to avoid:**
- Do not retry-spin inside one refresh attempt — a single failure gives up and waits for the next hour.
- `tasks.loop.restart()` in the error hook should be called once, not in a loop.
- Log refresh count and duration — if refresh rate exceeds 1/hour, something is wrong.

**Warning signs:** `gspread.exceptions.APIError` with status 429. Sudden spike in refresh logs.

### Pitfall 3: `added_at` timestamp churn on every refresh

**What goes wrong:** Sheet rows don't carry a durable "when was this row added" timestamp. Naively setting `added_at = now()` on every refresh makes the UI's "Added {relative time}" always say "just now" — destroying the signal.

**Why it happens:** `PlayerEntry.added_at` defaults to current time; the sheet doesn't supply it.

**How to avoid:** On refresh, preserve `added_at` from the previous snapshot when the player name matches case-insensitively. Only new names get a new `added_at`. The `SheetTransferTargetStore` should diff the new fetch against the previous in-memory list before replacing it.

**Warning signs:** `/transfer-list` shows all players as "Added just now" right after a refresh.

### Pitfall 4: Sheet schema drift silently yields blank entries

**What goes wrong:** User reorders columns in the sheet, or a column becomes empty. Code happily creates `PlayerEntry(name="", position="", school="", stars=0)` entries.

**Why it happens:** We're trusting column letters. If column B was "position" but is now "email", we pull emails as positions until someone notices.

**How to avoid:** On refresh, validate the header row against `transfer_target_sheet_header_row`. If headers don't match expected names (case-insensitive), log a warning and abort the refresh (keep stale cache). Planner should pin expected header text as a configuration — but D-11 says fixed schema, so this is a sanity check, not configurability.

**Warning signs:** Suddenly all players have identical or nonsensical positions; refresh succeeds with N entries but the data is wrong.

### Pitfall 5: Blocking the event loop

**What goes wrong:** Calling `worksheet.get_all_records()` directly from an async function blocks the event loop for the duration of the HTTP request (typically 200–800ms, can spike on Google's side). Commands queued during that window stall.

**Why it happens:** gspread is synchronous.

**How to avoid:** Every gspread call goes through `await asyncio.to_thread(...)`. Never call gspread directly from an async context.

```python
import asyncio

worksheet = await asyncio.to_thread(
    lambda: client.open_by_key(sheet_id).worksheet(tab_name)
)
rows = await asyncio.to_thread(worksheet.get_all_records)
```

**Warning signs:** Bot latency spikes during the refresh minute of each hour; heartbeat warnings from discord.py.

### Pitfall 6: Snapshot written with partial data after crash mid-refresh

**What goes wrong:** Refresh fetches 40 rows, crashes mid-mapping after building 20 entries, then snapshot save runs with 20 entries — corrupts last-known-good.

**How to avoid:** Only save the snapshot AFTER a successful full fetch + mapping. Build the new list in a local variable; swap it into the in-memory cache atomically; then save snapshot.

### Pitfall 7: `type="target"` locally-added basketball entries persist post-migration

**What goes wrong:** `/transfer-list` shows duplicates: one from sheet store, one from old `data/transfers.json`.

**Why it happens:** D-04 merges two stores. The old local-file entries don't evaporate automatically.

**How to avoid:** One-time cleanup task in the plan that removes `sport=basketball AND type=target` entries from `data/transfers.json` when the phase goes live. See Runtime State Inventory.

## Code Examples

### Full refresh flow skeleton

```python
# src/bot/sources/sheets.py
from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import gspread
from gspread.auth import READONLY_SCOPES

from bot.storage.models import PlayerEntry

logger = logging.getLogger(__name__)


class SheetTransferTargetStore:
    """In-memory cache of sheet-sourced basketball transfer targets, with atomic JSON snapshot."""

    def __init__(self, settings, snapshot_path: Path) -> None:
        self.settings = settings
        self.snapshot_path = snapshot_path
        self._players: list[PlayerEntry] = []
        self._last_refresh: datetime | None = None

    def load_snapshot(self) -> None:
        """Load last-known-good snapshot from disk on startup. Safe if file missing/corrupt."""
        if not self.snapshot_path.exists():
            return
        try:
            raw = json.loads(self.snapshot_path.read_text(encoding="utf-8"))
            self._players = [PlayerEntry.from_dict(e) for e in raw.get("players", [])]
            last = raw.get("last_refresh")
            self._last_refresh = datetime.fromisoformat(last) if last else None
            logger.info("Loaded %d players from sheet snapshot (refreshed %s)", len(self._players), self._last_refresh)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning("Corrupt sheet snapshot %s: %s", self.snapshot_path, e)

    def get_targets(self) -> list[PlayerEntry]:
        """Return a copy of the current cached target list."""
        return list(self._players)

    async def refresh(self) -> None:
        """Fetch from sheet; on success, replace cache and save snapshot. On failure, raise (caller decides)."""
        info = self.settings.sheet_service_account_info
        if info is None:
            raise RuntimeError("No service account configured")

        sheet_id = self.settings.transfer_target_sheet_id
        tab = self.settings.transfer_target_sheet_tab

        def _sync_fetch() -> list[dict]:
            client = gspread.service_account_from_dict(info, scopes=READONLY_SCOPES)
            ws = client.open_by_key(sheet_id).worksheet(tab)
            return ws.get_all_records()  # Assumes first row is headers matching our column names

        rows = await asyncio.to_thread(_sync_fetch)
        now_iso = datetime.now(timezone.utc).isoformat()
        old_by_name = {p.name.lower(): p for p in self._players}

        new_players: list[PlayerEntry] = []
        for row in rows:
            # Row keys are header names from the first row (or row N where N = header_row).
            # Normalize to lowercase for robustness.
            normalized = {k.lower().strip(): v for k, v in row.items()}
            mapped = {
                "name": normalized.get("name", ""),
                "position": normalized.get("position", ""),
                "school": normalized.get("school", ""),
                "stars": normalized.get("stars", 0),
            }
            player = _row_to_player(mapped, now_iso)
            if player is None:
                continue
            # Preserve added_at across refreshes (Pitfall 3).
            prior = old_by_name.get(player.name.lower())
            if prior is not None:
                player.added_at = prior.added_at
            new_players.append(player)

        self._players = new_players
        self._last_refresh = datetime.now(timezone.utc)
        self._save_snapshot()
        logger.info("Sheet refresh OK: %d target(s)", len(new_players))

    def _save_snapshot(self) -> None:
        """Atomic JSON write — mirrors RecruitingStore.save."""
        self.snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "last_refresh": self._last_refresh.isoformat() if self._last_refresh else None,
            "players": [p.to_dict() for p in self._players],
        }
        fd, tmp_path = tempfile.mkstemp(dir=self.snapshot_path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            os.replace(tmp_path, self.snapshot_path)
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise


def _row_to_player(row: dict, now_iso: str) -> PlayerEntry | None:
    # (See Pattern 4 above for full implementation.)
    ...
```

[CITED: gspread API — `service_account_from_dict`, `open_by_key`, `worksheet`, `get_all_records` — verified via gspread source + docs]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `oauth2client` for Google auth | `google-auth` | Pre-2020 (oauth2client deprecated) | gspread already migrated — we get the modern path for free |
| gspread v3 scopes (manual `ServiceAccountCredentials.from_json_keyfile_dict`) | gspread v5+ `service_account_from_dict(info, scopes=...)` | gspread 5.x+ | Simpler, fewer lines of wiring code |
| gspread-asyncio wrapper | Plain gspread + `asyncio.to_thread` | Python 3.9+ (to_thread is stdlib) | Fewer deps, stays on actively-maintained upstream |
| `gspread.service_account(filename=...)` only | Dict-based auth for containerized envs | gspread 5.x | Railway/Procfile deployment can use inline JSON env var |

**Deprecated / outdated:**

- **`oauth2client`**: Archived by Google. Don't use. gspread no longer depends on it. [CITED: google-auth-library deprecation of oauth2client]
- **gspread `READONLY_SCOPE` (singular)**: older examples. Current name is `READONLY_SCOPES` (plural, tuple). [VERIFIED: gspread/auth.py master branch]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `pygsheets` is less current than gspread | Alternatives Considered | Low — even if both are fine, gspread remains a defensible choice |
| A2 | gspread `requests` transitive dep does not conflict with existing deps | Standard Stack → Transitive check | Low — worst case is a pip resolver complaint that planner can pin around |
| A3 | User's deployment (Railway/nixpacks) has no persistent filesystem for a mounted secret file | Pattern 1 | Low — inline JSON path works regardless; only affects which auth path is primary |
| A4 | Hourly refresh with one sheet is ~1/300th of quota — no throttling concerns | Pitfall 2 | Very low — Google's quota is 300/min/project; we use 1/hour |
| A5 | Sheet's first row is a header row usable by `get_all_records()` | Code Examples | Medium — if the user's sheet has metadata rows above headers, we need to use `worksheet.get_values()` starting at a specific row instead. Planner must confirm when collecting D-11 details from user |
| A6 | `PlayerEntry.from_dict` accepts a dict with only the subset we care about | Code Examples | Low — verified in `models.py`: it filters by `__dataclass_fields__` |

## Open Questions

1. **Sheet ID, tab name, column layout (D-11)** — user has not yet supplied these to planner.
   - What we know: schema is "existing and fixed" per user.
   - What's unclear: actual column positions (letter or header name), whether rows above the header contain metadata.
   - Recommendation: Planner's first action is a short interactive prompt to user: "Paste the sheet URL, the tab name, and the column headers for name / position / school / stars." Block the plan until received.

2. **Should the sheet column config be env-configurable or code-constant?**
   - D-11 says fixed schema, Claude's discretion says module layout is open.
   - Recommendation: env-configurable with sensible defaults. Cost: 4 extra settings lines. Benefit: user tweaks sheet without code change.

3. **Cleanup of pre-existing basketball-target entries in `data/transfers.json`.**
   - Options: (a) one-shot script run at deploy, (b) an admin `/clear-basketball-targets` command, (c) startup code that silently deletes them on boot.
   - Recommendation: (c) — a one-liner in `client.py` `setup_hook` right after the sheet store loads. Self-healing, no operator step. Log what was removed.

4. **Should `/transfer-list` display a "Last synced" footer for basketball targets?**
   - User did not specify. The existing "Last updated" footer reflects the command's runtime, not the sheet refresh time.
   - Recommendation: add a small "Targets synced from Google Sheet {relative time ago}" line to the basketball section header. Low cost, high clarity for users wondering why the list doesn't show their recent sheet edit.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (already in `[dependency-groups].dev` of `pyproject.toml`) |
| Config file | None detected — relies on pytest defaults; fixtures use `tmp_path` |
| Quick run command | `uv run pytest tests/test_sheet_store.py -x` (new file) |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TRANSFER-SHEET-01 | Hourly refresh triggers sheet fetch | unit (mock gspread) | `uv run pytest tests/test_sheet_sync_scheduler.py::test_loop_calls_refresh -x` | ❌ Wave 0 |
| TRANSFER-SHEET-02 | `/transfer-list` serves from cache without hitting API | unit | `uv run pytest tests/test_sheet_store.py::test_get_targets_no_network -x` | ❌ Wave 0 |
| TRANSFER-SHEET-03 | Snapshot round-trip preserves players + last_refresh | unit | `uv run pytest tests/test_sheet_store.py::test_snapshot_roundtrip -x` | ❌ Wave 0 |
| TRANSFER-SHEET-04 | `/transfer-add` basketball+target rejects with message | unit (command handler invoked with mock interaction) | `uv run pytest tests/test_transfer_commands.py::test_add_basketball_target_rejected -x` | ❌ Wave 0 |
| TRANSFER-SHEET-05 | Refresh failure keeps stale cache + alerts admin | unit | `uv run pytest tests/test_sheet_store.py::test_refresh_failure_preserves_cache -x` | ❌ Wave 0 |
| TRANSFER-SHEET-06 | Row with missing name skipped; invalid stars → 0 | unit | `uv run pytest tests/test_sheet_store.py::test_row_validation -x` | ❌ Wave 0 |
| TRANSFER-SHEET-07 | Settings accepts inline JSON; falls back to file path | unit | `uv run pytest tests/test_config_phase13.py -x` | ❌ Wave 0 |
| (integration) | Actual Sheets API call against a test sheet | manual-only | N/A | — |

**Mocking strategy:** gspread calls are synchronous and made through `asyncio.to_thread`. Tests mock at the `gspread.service_account_from_dict` boundary (patch to return a fake client whose `open_by_key().worksheet().get_all_records()` returns a fixture list of dicts). No real network needed for automated tests. The manual integration test is a one-off sanity check the operator runs after deploying.

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_sheet_store.py tests/test_sheet_sync_scheduler.py tests/test_transfer_commands.py -x` (scoped quick run, ~seconds)
- **Per wave merge:** `uv run pytest` (full suite — existing suite is tiny, under 10s)
- **Phase gate:** full suite green, plus a manual `uv run python -m bot` smoke that logs a successful sheet fetch from the real sheet in the dev env

### Wave 0 Gaps

- [ ] `tests/test_sheet_store.py` — covers TRANSFER-SHEET-02, 03, 05, 06
- [ ] `tests/test_sheet_sync_scheduler.py` — covers TRANSFER-SHEET-01
- [ ] `tests/test_transfer_commands.py` — covers TRANSFER-SHEET-04 (this file doesn't exist yet; basketball-target-guard tests would create it)
- [ ] `tests/test_config_phase13.py` (or extend `tests/test_config_phase2.py`) — covers TRANSFER-SHEET-07
- [ ] `tests/fixtures/sheet_rows.json` — shared fixture of representative row dicts (valid + invalid cases)
- [ ] Framework install: none — pytest + pytest-asyncio already in `[dependency-groups].dev`

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Google service account via `google-auth` (OAuth2 JWT bearer flow) — don't hand-roll |
| V3 Session Management | no | Bot uses short-lived OAuth tokens internally; no user sessions |
| V4 Access Control | yes | `READONLY_SCOPES` restricts credential to read-only. User-facing: existing `is_recruiting_editor` gate + new guard for basketball+target |
| V5 Input Validation | yes | Row validation per D-13 (missing name skipped, invalid stars normalized). Sheet input is operator-controlled, so low risk of injection — but still validate as defense-in-depth |
| V6 Cryptography | yes | Never hand-roll JWT signing — delegate to `google-auth` |
| V7 Error Handling | yes | Errors logged without leaking service-account JSON contents. Error DMs include exception type + message only, not the full credential |
| V10 Malicious Code | yes | Pin `gspread` version in `pyproject.toml` after `uv add`. Review transitive deps in `uv.lock` |
| V14 Configuration | yes | Secrets via env var, never committed. `.env` already in `.gitignore` presumably |

### Known Threat Patterns for {Python + discord.py + gspread}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Service-account JSON accidentally committed to git | Information Disclosure | Use env var (`SHEET_SERVICE_ACCOUNT_JSON`), confirm `.env` in `.gitignore`, add pre-commit hook optional |
| Service account over-permissioned (can edit sheet or access other sheets) | Elevation of Privilege | Create a dedicated service account used only for this bot; scope with `READONLY_SCOPES`; share only the one sheet with it |
| Service-account JSON logged in error traces | Information Disclosure | Error handling must not `repr()` the Settings object; `send_error_alerts` already only sends string error messages, not config. Review during code review |
| Malicious row content triggering Discord embed issues (e.g., massive strings, markdown injection) | Tampering / DoS | Truncate field values to embed-safe lengths (existing `[:256]` pattern in `transfers.py`). Strip/escape nothing else — operator owns the sheet |
| Quota exhaustion / DoS on our end | DoS | Hourly cap; single attempt per refresh; no retry-storm |
| Gspread dependency compromise (supply chain) | Tampering | Pin version, review `uv.lock` diff on update |

## Sources

### Primary (HIGH confidence)

- gspread source (`gspread/auth.py` on `master`) — verified signatures for `service_account`, `service_account_from_dict`, `READONLY_SCOPES`, `DEFAULT_SCOPES`. https://github.com/burnash/gspread/blob/master/gspread/auth.py
- gspread PyPI — confirmed latest 6.2.1 (2025-05-14). https://pypi.org/project/gspread/
- Google Sheets API "Usage limits" page (updated 2026-03-02) — 300 reads/min/project, 60/min/user. https://developers.google.com/workspace/sheets/api/limits
- discord.py `discord.ext.tasks` — `tasks.loop(hours=1)`, `before_loop`, `error`, `restart()`. Already used in `src/bot/scheduling/overnight.py`.
- In-repo precedents: `src/bot/scheduling/overnight.py`, `src/bot/storage/recruiting_store.py`, `src/bot/alerting.py`, `src/bot/config.py`, `src/bot/stats/basketball.py`, `src/bot/client.py`, `src/bot/commands/transfers.py`, `src/bot/storage/models.py`.

### Secondary (MEDIUM confidence)

- pydantic-settings docs — JSON env var parsing for complex types. https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- gspread docs (authentication overview) — confirms `READONLY_SCOPES` usage pattern. https://docs.gspread.org/en/latest/oauth2.html (403'd at fetch time but pattern verified through source).

### Tertiary (LOW confidence)

- Assumption that `pygsheets` is less actively maintained than gspread — not directly verified with PyPI side-by-side, but gspread's 6.2.1 release and ongoing master commits are the anchor.

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — gspread + `service_account_from_dict` + `READONLY_SCOPES` directly verified in source; in-repo async/scheduling/storage patterns already established.
- Architecture: HIGH — every pattern has a precedent in the codebase (`OvernightScheduler`, `RecruitingStore`, `asyncio.to_thread` convention, atomic JSON write).
- Pitfalls: MEDIUM-HIGH — quota numbers cited from Google's official page; `added_at` churn and schema-drift pitfalls are logical derivations from code inspection rather than documented incidents.
- Security: HIGH for the principles (scope minimization, env-var secrets, no hand-rolled crypto); MEDIUM for the deployment-specific concerns which depend on the operator's hosting discipline.
- Open user inputs: LOW until D-11 (sheet ID/tab/columns) is supplied. Planner must collect before finalizing.

**Research date:** 2026-04-14
**Valid until:** ~2026-07-14 (90 days — gspread is stable, Sheets API quotas rarely change, but verify `gspread` version on `uv add` just in case)

## RESEARCH COMPLETE
