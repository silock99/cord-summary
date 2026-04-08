"""Monospace table formatting for career stats display."""


def format_stats_table(stats: dict) -> str:
    """Format stats dict into a Discord code-block monospace table.

    Returns the formatted string including ``` delimiters.
    """
    sport = stats.get("sport", "")
    if sport == "basketball":
        return _format_basketball(stats)
    elif sport == "football":
        return _format_football(stats)
    else:
        return f"```\nUnknown sport: {sport}\n```"


def _format_basketball(stats: dict) -> str:
    """Format basketball stats as monospace table.

    Columns: Season, GP, PPG, RPG, APG, FG%, 3P%
    Career totals row shown only when 2+ seasons.
    """
    header = "Season  GP   PPG   RPG   APG   FG%   3P%"
    sep = "------  --  ----  ----  ----  ----  ----"
    lines = [header, sep]

    seasons = stats.get("seasons", {})

    # Accumulators for career totals
    total_games = 0
    total_points = 0
    total_rebounds = 0
    total_assists = 0
    # For career FG%/3P%, we'd need made/attempted totals.
    # Since we only store pct, we weight by games played.
    weighted_fg = 0.0
    weighted_fg3 = 0.0

    for year in sorted(seasons.keys()):
        s = seasons[year]
        gp = s.get("games", 0) or 0
        points = s.get("points", 0) or 0
        rebounds = s.get("rebounds_total", 0) or 0
        assists = s.get("assists", 0) or 0
        fg_pct = s.get("fg_pct", 0.0) or 0.0
        fg3_pct = s.get("fg3_pct", 0.0) or 0.0

        ppg = points / gp if gp else 0.0
        rpg = rebounds / gp if gp else 0.0
        apg = assists / gp if gp else 0.0
        fg = fg_pct * 100
        fg3 = fg3_pct * 100

        lines.append(
            f"{year:<6}  {gp:>2}  {ppg:>4.1f}  {rpg:>4.1f}  {apg:>4.1f}  {fg:>4.1f}  {fg3:>4.1f}"
        )

        total_games += gp
        total_points += points
        total_rebounds += rebounds
        total_assists += assists
        weighted_fg += fg_pct * gp
        weighted_fg3 += fg3_pct * gp

    # Career totals only if 2+ seasons
    if len(seasons) >= 2 and total_games > 0:
        career_ppg = total_points / total_games
        career_rpg = total_rebounds / total_games
        career_apg = total_assists / total_games
        career_fg = (weighted_fg / total_games) * 100
        career_fg3 = (weighted_fg3 / total_games) * 100

        lines.append(sep)
        lines.append(
            f"{'Career':<6}  {total_games:>2}  {career_ppg:>4.1f}  {career_rpg:>4.1f}  {career_apg:>4.1f}  {career_fg:>4.1f}  {career_fg3:>4.1f}"
        )

    return "```\n" + "\n".join(lines) + "\n```"


def _format_football(stats: dict) -> str:
    """Format football stats as monospace table with separate category sections.

    Shows only categories where the player has actual data.
    Career totals row shown only when 2+ seasons per category.
    """
    seasons = stats.get("seasons", {})
    sorted_years = sorted(seasons.keys())

    # Determine which categories have data across any season
    all_categories: set[str] = set()
    for year_data in seasons.values():
        cats = year_data.get("categories", {})
        all_categories.update(cats.keys())

    category_sections: list[str] = []

    # Passing
    if "passing" in all_categories:
        section = _format_football_category(
            sorted_years,
            seasons,
            "passing",
            header="Season  CMP  ATT   YDS  TD  INT",
            sep=   "------  ---  ---  ----  --  ---",
            columns=["COMPLETIONS", "ATT", "YDS", "TD", "INT"],
            widths=[3, 3, 4, 2, 3],
        )
        if section:
            category_sections.append(section)

    # Rushing
    if "rushing" in all_categories:
        section = _format_football_category(
            sorted_years,
            seasons,
            "rushing",
            header="Season  CAR   YDS  TD",
            sep=   "------  ---  ----  --",
            columns=["CAR", "YDS", "TD"],
            widths=[3, 4, 2],
        )
        if section:
            category_sections.append(section)

    # Receiving
    if "receiving" in all_categories:
        section = _format_football_category(
            sorted_years,
            seasons,
            "receiving",
            header="Season  REC   YDS  TD",
            sep=   "------  ---  ----  --",
            columns=["REC", "YDS", "TD"],
            widths=[3, 4, 2],
        )
        if section:
            category_sections.append(section)

    if not category_sections:
        return "```\nNo stats available\n```"

    return "```\n" + "\n\n".join(category_sections) + "\n```"


def _format_football_category(
    sorted_years: list[str],
    seasons: dict,
    category: str,
    header: str,
    sep: str,
    columns: list[str],
    widths: list[int],
) -> str | None:
    """Format a single football stat category section.

    Returns None if no data exists for this category.
    """
    lines = [header, sep]
    has_data = False
    totals: dict[str, int] = {col: 0 for col in columns}
    years_with_data = 0

    for year in sorted_years:
        cats = seasons[year].get("categories", {})
        if category not in cats:
            continue

        cat_data = cats[category]
        has_data = True
        years_with_data += 1

        values = []
        for col, width in zip(columns, widths):
            val = cat_data.get(col, 0)
            if isinstance(val, float):
                val = int(val)
            totals[col] = totals.get(col, 0) + val
            values.append(f"{val:>{width}}")

        lines.append(f"{year:<6}  {'  '.join(values)}")

    if not has_data:
        return None

    # Career totals only if 2+ seasons
    if years_with_data >= 2:
        total_values = []
        for col, width in zip(columns, widths):
            total_values.append(f"{totals[col]:>{width}}")
        lines.append(sep)
        lines.append(f"{'Career':<6}  {'  '.join(total_values)}")

    return "\n".join(lines)
