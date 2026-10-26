import re

SEASON_RE = re.compile(r"^(\d{4})-(\d{2})$")


def season_to_compact(season: str) -> str:
    """Convert a season like '2024-25' into its compact file-naming form '2425'."""
    match = SEASON_RE.match(season)
    if not match:
        raise ValueError(f"Season must be in the form 'YYYY-YY' (e.g. '2024-25'), got {season!r}")
    start_year, end_yy = match.groups()
    return start_year[-2:] + end_yy
