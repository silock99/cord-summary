"""CFBD API integration for football career stats."""

import logging
from datetime import datetime

import cfbd

from bot.config import Settings

logger = logging.getLogger(__name__)


async def fetch_football_stats(
    settings: Settings, player_name: str, school: str
) -> dict | None:
    """Fetch football career stats from CFBD API.

    Returns stats dict or None if player not found or API key missing.
    """
    if not settings.cfbd_api_key:
        logger.debug("CFBD API key not configured, skipping stats fetch")
        return None

    try:
        configuration = cfbd.Configuration()
        configuration.api_key["Authorization"] = f"Bearer {settings.cfbd_api_key}"

        with cfbd.ApiClient(configuration) as api_client:
            players_api = cfbd.PlayersApi(api_client)

            # Search for the player
            results = players_api.player_search(search_term=player_name)
            if not results:
                logger.debug("No CFBD results for player '%s'", player_name)
                return None

            # If multiple results, filter by school
            match = None
            if len(results) == 1:
                match = results[0]
            else:
                for r in results:
                    if r.team and r.team.lower() == school.lower():
                        match = r
                        break
                if match is None:
                    # Fall back to first result if no school match
                    match = results[0]

            # Query season stats for the last 6 years
            current_year = datetime.now().year
            seasons: dict[str, dict] = {}
            consecutive_empty = 0

            for year in range(current_year, current_year - 7, -1):
                year_has_data = False
                categories: dict[str, dict] = {}

                for category in ("passing", "rushing", "receiving"):
                    try:
                        stats = players_api.get_player_season_stats(
                            year=year,
                            team=match.team,
                            category=category,
                        )
                    except Exception:
                        continue

                    # Filter to our player
                    player_stats = [
                        s
                        for s in stats
                        if s.player and s.player.lower() == match.name.lower()
                    ]

                    if player_stats:
                        year_has_data = True
                        cat_data: dict[str, int | float] = {}
                        for s in player_stats:
                            # Convert string stat values to numbers (Pitfall 3)
                            try:
                                val = float(s.stat)
                                cat_data[s.stat_type] = (
                                    int(val) if val == int(val) else val
                                )
                            except (ValueError, TypeError):
                                cat_data[s.stat_type] = 0
                        categories[category] = cat_data

                if year_has_data:
                    consecutive_empty = 0
                    seasons[str(year)] = {
                        "team": match.team,
                        "categories": categories,
                    }
                else:
                    consecutive_empty += 1
                    if consecutive_empty >= 2:
                        break

            if not seasons:
                logger.debug(
                    "No season stats found for '%s' at '%s'",
                    match.name,
                    match.team,
                )
                return None

            return {
                "sport": "football",
                "player_id": str(match.id) if match.id else "",
                "player_name": match.name,
                "seasons": seasons,
            }

    except Exception:
        logger.warning(
            "Failed to fetch football stats for '%s'", player_name, exc_info=True
        )
        return None


async def fetch_football_roster(settings: Settings) -> list[dict]:
    """Fetch the current KU football roster from CFBD API.

    Returns list of dicts with keys: name, position, jersey_number, class_year.
    Returns empty list if API key missing or API error.
    """
    if not settings.cfbd_api_key:
        logger.debug("CFBD API key not configured, skipping roster fetch")
        return []

    YEAR_MAP = {1: "Fr.", 2: "So.", 3: "Jr.", 4: "Sr.", 5: "R-Sr."}

    try:
        configuration = cfbd.Configuration()
        configuration.api_key["Authorization"] = f"Bearer {settings.cfbd_api_key}"

        with cfbd.ApiClient(configuration) as api_client:
            teams_api = cfbd.TeamsApi(api_client)
            year = datetime.now().year
            roster = teams_api.get_roster(team="Kansas", year=year)

            return [
                {
                    "name": f"{p.first_name} {p.last_name}",
                    "position": p.position or "ATH",
                    "jersey_number": p.jersey or 0,
                    "class_year": YEAR_MAP.get(p.year, ""),
                }
                for p in roster
            ]

    except Exception:
        logger.warning("Failed to fetch football roster from CFBD", exc_info=True)
        return []
