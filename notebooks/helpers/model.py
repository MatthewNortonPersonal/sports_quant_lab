"""
Core model functions for the Sports Quant Lab.

This is the bridge between Matthew's notebook work and David's infra.

Rules for this file:
- Pure functions only — no database access, no side effects
- Every function must have type hints and a docstring
- Once a notebook function is stable and tested, extract it here
- This module is imported by infra/orchestrator.py for live use

Key model:
    Score differential X(t) follows Brownian motion with drift:
        dX(t) = μ dt + σ dW(t)

    Win probability (home wins) at time t with τ = time remaining:
        P(home wins) = Φ((X(t) + μτ) / (σ√τ))
"""

import numpy as np
from scipy.stats import norm


# ---------------------------------------------------------------------------
# Win probability
# ---------------------------------------------------------------------------

def win_probability(
    margin: float,
    time_remaining: float,
    drift: float,
    sigma: float,
) -> float:
    """
    Compute P(home wins) using the Brownian motion model.

    Models the score differential as:
        X(T) | X(t) = margin  ~  Normal(margin + drift * τ,  σ² * τ)

    where τ = time_remaining in minutes.

    Args:
        margin: Current score differential, home − away (positive = home leading)
        time_remaining: Minutes remaining in regulation (0–48)
        drift: Expected margin change per minute = pre_game_spread / 48
        sigma: Volatility parameter in points per √minute (NBA ≈ 1.5–2.0)

    Returns:
        Home win probability in [0, 1]
    """
    if time_remaining <= 0:
        if margin > 0:
            return 1.0
        elif margin < 0:
            return 0.0
        else:
            return 0.5  # Tie → overtime (treat as coin flip for now)

    tau = time_remaining
    z = (margin + drift * tau) / (sigma * np.sqrt(tau))
    return float(norm.cdf(z))


# ---------------------------------------------------------------------------
# Parameter estimation  (Matthew implements these in notebooks first)
# ---------------------------------------------------------------------------

def estimate_sigma(pbp_df, bucket_minutes: int = 1) -> float:
    """
    Estimate the volatility parameter σ from historical play-by-play data.

    Method: compute the std dev of score margin changes over 1-minute buckets
    across all games. This gives σ in units of points per √minute.

    Args:
        pbp_df: DataFrame with columns [game_id, elapsed_minutes, score_margin]
        bucket_minutes: time bucket size for computing margin changes (default 1)

    Returns:
        σ estimate in points per √minute

    TODO: Matthew implements this in 02_parameter_estimation.ipynb.
          Extract the final version here once it's validated.
    """
    raise NotImplementedError(
        "estimate_sigma not yet implemented. "
        "See notebooks/02_parameter_estimation.ipynb."
    )


def estimate_drift(pre_game_spread: float, total_minutes: float = 48.0) -> float:
    """
    Convert a pre-game spread into a per-minute drift parameter.

    The spread represents the expected final score margin. Dividing by
    total game length gives the expected margin change per minute.

    Args:
        pre_game_spread: Expected final margin from home team's perspective
                         (negative = home favored, e.g. -6.5)
        total_minutes: Total game length in minutes (48 for NBA regulation)

    Returns:
        Drift μ in points per minute
    """
    return pre_game_spread / total_minutes


# ---------------------------------------------------------------------------
# Kalshi pricing
# ---------------------------------------------------------------------------

def implied_probability(kalshi_price: float) -> float:
    """
    Convert a Kalshi contract price to implied probability.

    Args:
        kalshi_price: Price in cents (0–100) or as a proportion (0–1)

    Returns:
        Implied probability in [0, 1]
    """
    if kalshi_price > 1:
        return kalshi_price / 100.0
    return float(kalshi_price)


def kalshi_taker_fee(price: float) -> float:
    """
    Compute the Kalshi taker fee for a given contract price.

    Fee = 0.07 × P × (1 − P), where P is on a 0–1 scale.
    Maximized at P = 0.5 (≈ 1.75¢). Maker orders are fee-free.

    Args:
        price: Contract price (0–1 scale, or cents if > 1)

    Returns:
        Taker fee as a proportion (0–1 scale)
    """
    p = price / 100.0 if price > 1 else price
    return 0.07 * p * (1 - p)


def edge_after_fees(model_prob: float, kalshi_price: float) -> float:
    """
    Compute net edge after Kalshi taker fees.

    A positive value means the model thinks the contract is underpriced
    enough to cover the taker fee — a buy signal.

    Args:
        model_prob: Model's home win probability estimate (0–1)
        kalshi_price: Current Kalshi mid price (0–1 scale)

    Returns:
        Net edge. Positive = buy signal. Negative = pass (or fade on 'no' side).
    """
    fee = kalshi_taker_fee(kalshi_price)
    return model_prob - kalshi_price - fee
