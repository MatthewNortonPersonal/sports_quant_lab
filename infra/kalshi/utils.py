"""
Kalshi-specific utility functions.

Pure math helpers — no database access, no API calls.
"""


def implied_probability(price_cents: float) -> float:
    """
    Convert a Kalshi contract price (in cents, 0–100) to an implied probability.

    Args:
        price_cents: contract price as cents (e.g. 65 means 65¢)

    Returns:
        Probability between 0 and 1
    """
    return price_cents / 100.0


def taker_fee(price: float) -> float:
    """
    Compute the Kalshi taker fee for a given contract price.

    Fee formula: 0.07 × P × (1 − P), where P is the price on a 0–1 scale.
    Fee is maximized at P = 0.5 (≈ 1.75¢) and approaches 0 at the extremes.

    Args:
        price: contract price on 0–1 scale (e.g. 0.65), or cents if > 1

    Returns:
        Fee as a proportion (0–1 scale)
    """
    p = price / 100.0 if price > 1 else price
    return 0.07 * p * (1 - p)


def edge_after_fees(model_prob: float, kalshi_price: float) -> float:
    """
    Compute net edge after Kalshi taker fees.

    Args:
        model_prob: model's win probability estimate (0–1 scale)
        kalshi_price: current Kalshi mid price (0–1 scale)

    Returns:
        Net edge. Positive = buy signal. Negative = pass or fade.
    """
    return model_prob - kalshi_price - taker_fee(kalshi_price)


def mid_price(bid: float, ask: float) -> float:
    """Compute mid price from bid and ask (both on 0–1 scale)."""
    return (bid + ask) / 2.0


def is_tradeable(price: float, min_price: float = 0.05, max_price: float = 0.95) -> bool:
    """
    Check whether a Kalshi price is worth trading.

    Contracts near 0¢ or 100¢ have very low edge potential: the fee eats most
    of the remaining room, and liquidity is usually thin.

    Args:
        price: contract price on 0–1 scale
        min_price: floor threshold (default 5¢)
        max_price: ceiling threshold (default 95¢)

    Returns:
        True if the price is in the tradeable range
    """
    return min_price <= price <= max_price
