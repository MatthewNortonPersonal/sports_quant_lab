"""
Unit tests for infra/kalshi/utils.py

Run with: pytest tests/test_kalshi_utils.py -v
"""

import pytest

from infra.kalshi.utils import (
    implied_probability,
    taker_fee,
    edge_after_fees,
    mid_price,
    is_tradeable,
)


class TestImpliedProbability:

    def test_fifty_cents(self):
        assert implied_probability(50) == pytest.approx(0.5)

    def test_zero(self):
        assert implied_probability(0) == pytest.approx(0.0)

    def test_hundred(self):
        assert implied_probability(100) == pytest.approx(1.0)

    def test_arbitrary_value(self):
        assert implied_probability(72) == pytest.approx(0.72)


class TestTakerFee:

    def test_formula(self):
        p = 0.65
        assert taker_fee(p) == pytest.approx(0.07 * p * (1 - p))

    def test_max_at_fifty(self):
        fee_50 = taker_fee(0.5)
        assert fee_50 > taker_fee(0.4)
        assert fee_50 > taker_fee(0.6)

    def test_cents_input(self):
        """Should handle price in cents (> 1) identically to proportion."""
        assert taker_fee(65) == pytest.approx(taker_fee(0.65))

    def test_symmetry(self):
        assert taker_fee(0.3) == pytest.approx(taker_fee(0.7))


class TestEdgeAfterFees:

    def test_positive_edge(self):
        assert edge_after_fees(model_prob=0.75, kalshi_price=0.60) > 0

    def test_negative_edge(self):
        assert edge_after_fees(model_prob=0.55, kalshi_price=0.70) < 0

    def test_breakeven_is_negative(self):
        """model_prob == kalshi_price still yields negative edge due to fee."""
        p = 0.65
        assert edge_after_fees(p, p) < 0


class TestMidPrice:

    def test_symmetric(self):
        assert mid_price(0.60, 0.70) == pytest.approx(0.65)

    def test_no_spread(self):
        assert mid_price(0.50, 0.50) == pytest.approx(0.50)


class TestIsTradeable:

    def test_in_range(self):
        assert is_tradeable(0.50) is True
        assert is_tradeable(0.65) is True

    def test_below_floor(self):
        assert is_tradeable(0.03) is False

    def test_above_ceiling(self):
        assert is_tradeable(0.97) is False

    def test_boundary_values(self):
        assert is_tradeable(0.05) is True   # exactly at floor
        assert is_tradeable(0.95) is True   # exactly at ceiling

    def test_custom_thresholds(self):
        assert is_tradeable(0.08, min_price=0.10) is False
        assert is_tradeable(0.08, min_price=0.05) is True
