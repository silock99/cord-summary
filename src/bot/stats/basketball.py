"""CBBD API integration for basketball career stats.

Uses aiohttp directly instead of the cbbd SDK because the cbbd package
requires pydantic v1, which conflicts with our pydantic v2 dependency.
The REST API is straightforward: Bearer token auth, JSON responses.
"""

import difflib
import logging
from datetime import datetime

import aiohttp

from bot.config import Settings

logger = logging.getLogger(__name__)

CBBD_BASE_URL = "https://api.collegebasketballdata.com"


async def _cbbd_get(
    session: aiohttp.ClientSession, path: str, params: dict | None = None
) -> list[dict] | None:
    """Make a GET request to the CBBD API. Returns parsed JSON or None on error."""
    url = f"{CBBD_BASE_URL}{path}"
    try:
        async with session.get(url, params=params) as resp:
            if resp.status != 200:
                logger.debug("CBBD API returned %d for %s", resp.status, path)
                return None
            return await resp.json()
    except Exception:
        logger.warning("CBBD API request failed for %s", path, exc_info=True)
        return None


async def fetch_basketball_stats(
    settings: Settings, player_name: str, school: str
) -> dict | None:
    """Fetch basketball career stats from CBBD API.

    Returns stats dict or None if player not found or API key missing.
    """
    if not settings.cbbd_api_key:
        logger.debug("CBBD API key not configured, skipping stats fetch")
        return None

    try:
        headers = {"Authorization": f"Bearer {settings.cbbd_api_key}"}
        current_year = datetime.now().year

        async with aiohttp.ClientSession(headers=headers) as session:
            # Step 1: Find the player via roster lookup
            player_match_name = None

            for year_offset in range(0, 2):
                year = current_year - year_offset
                roster = await _cbbd_get(
                    session,
                    "/roster",
                    params={"season": year, "team": school},
                )
                if not roster:
                    continue

                # Try exact match first
                for p in roster:
                    name = p.get("name", "")
                    if name.lower() == player_name.lower():
                        player_match_name = name
                        break

                # Try fuzzy match
                if not player_match_name:
                    names = [p.get("name", "") for p in roster if p.get("name")]
                    close = difflib.get_close_matches(
                        player_name, names, n=1, cutoff=0.6
                    )
                    if close:
                        player_match_name = close[0]

                if player_match_name:
                    break

            if not player_match_name:
                logger.debug(
                    "No CBBD roster match for '%s' at '%s'", player_name, school
                )
                return None

            # Step 2: Query season stats for last 6 years
            seasons: dict[str, dict] = {}

            for year in range(current_year, current_year - 7, -1):
                stats_list = await _cbbd_get(
                    session,
                    "/stats/player/season",
                    params={"season": year, "team": school},
                )
                if not stats_list:
                    continue

                # Filter to our player
                player_stats = [
                    s
                    for s in stats_list
                    if s.get("name", "").lower() == player_match_name.lower()
                ]

                for s in player_stats:
                    games = s.get("games", 0) or 0
                    if games == 0:
                        continue

                    # Extract nested stats safely
                    rebounds = s.get("rebounds") or {}
                    fg = s.get("fieldGoals") or {}
                    fg3 = s.get("threePointFieldGoals") or {}

                    seasons[str(year)] = {
                        "team": school,
                        "games": games,
                        "points": s.get("points", 0) or 0,
                        "assists": s.get("assists", 0) or 0,
                        "rebounds_total": rebounds.get("total", 0) or 0,
                        "fg_pct": fg.get("pct", 0.0) or 0.0,
                        "fg3_pct": fg3.get("pct", 0.0) or 0.0,
                    }

            if not seasons:
                logger.debug(
                    "No season stats found for '%s' at '%s'",
                    player_match_name,
                    school,
                )
                return None

            return {
                "sport": "basketball",
                "player_id": "",
                "player_name": player_match_name,
                "seasons": seasons,
            }

    except Exception:
        logger.warning(
            "Failed to fetch basketball stats for '%s'",
            player_name,
            exc_info=True,
        )
        return None
