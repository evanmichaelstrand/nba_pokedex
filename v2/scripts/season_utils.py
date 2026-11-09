import re

SEASON_RE = re.compile(r"^(\d{4})-(\d{2})$")


def parse_season(season: str) -> int:
    """Validate a season like '2025-26' and return its start year (2025)."""
    match = SEASON_RE.match(season)
    if not match:
        raise ValueError(f"Season must be in the form 'YYYY-YY' (e.g. '2025-26'), got {season!r}")
    start_year, end_yy = match.groups()
    if (int(start_year) + 1) % 100 != int(end_yy):
        raise ValueError(f"Season {season!r} must span consecutive years (e.g. '2025-26')")
    return int(start_year)


def season_to_compact(season: str) -> str:
    """Convert a season like '2025-26' into its compact file-naming form '2526'."""
    parse_season(season)
    return season[2:4] + season[5:7]
