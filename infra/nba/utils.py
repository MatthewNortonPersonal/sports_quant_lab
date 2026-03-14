"""
NBA game state utilities.

Pure helpers for parsing game clock strings and computing elapsed time.
No API calls, no database access.
"""

import re


def parse_game_clock(clock_str: str) -> float:
    """
    Parse a game clock string into minutes remaining in the current period.

    nba_api live endpoints return ISO 8601 duration strings like 'PT05M32.00S'.
    Historical PBP may use 'MM:SS' format like '5:32'.

    Args:
        clock_str: Clock string from nba_api

    Returns:
        Minutes remaining in the current period as a float

    Raises:
        ValueError: If the clock string cannot be parsed
    """
    if not clock_str:
        return 0.0

    # ISO 8601 format: PT05M32.00S (from nba_api live endpoints)
    iso_match = re.match(r"PT(\d+)M([\d.]+)S", clock_str.strip())
    if iso_match:
        minutes = int(iso_match.group(1))
        seconds = float(iso_match.group(2))
        return minutes + seconds / 60.0

    # MM:SS format (from historical PBP or older endpoints)
    colon_match = re.match(r"^(\d+):(\d{2})$", clock_str.strip())
    if colon_match:
        minutes = int(colon_match.group(1))
        seconds = int(colon_match.group(2))
        return minutes + seconds / 60.0

    raise ValueError(f"Cannot parse game clock: {clock_str!r}")


def compute_elapsed_minutes(quarter: int, clock_str: str) -> float:
    """
    Convert quarter number + game clock to elapsed minutes since tip-off.

    NBA regulation: 4 quarters × 12 minutes = 48 minutes.
    Overtime: each OT period is 5 minutes, starting at Q5.

    Args:
        quarter: Period number (1–4 for regulation, 5+ for overtime)
        clock_str: Remaining time in the current period

    Returns:
        Total elapsed minutes since tip-off
    """
    remaining = parse_game_clock(clock_str)

    if quarter <= 4:
        period_length = 12.0
        period_start = (quarter - 1) * 12.0
    else:
        # OT periods: Q5 starts at 48:00, Q6 at 53:00, etc.
        period_length = 5.0
        period_start = 48.0 + (quarter - 5) * 5.0

    elapsed_in_period = period_length - remaining
    return period_start + elapsed_in_period


def time_remaining_minutes(quarter: int, clock_str: str) -> float:
    """
    Compute minutes remaining in regulation (capped at 0).

    For overtime situations, returns 0 (regulation is already over).

    Args:
        quarter: Period number
        clock_str: Remaining time in the current period

    Returns:
        Minutes remaining in regulation (0 if in OT)
    """
    elapsed = compute_elapsed_minutes(quarter, clock_str)
    return max(0.0, 48.0 - elapsed)


def score_margin(home_score: int, away_score: int) -> int:
    """Compute score margin from home team's perspective."""
    return home_score - away_score
