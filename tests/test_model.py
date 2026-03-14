"""
Unit tests for notebooks/helpers/model.py

Run with: pytest tests/test_model.py -v
"""

import pytest
import numpy as np

from notebooks.helpers.model import (
    win_probability,
    estimate_drift,
    implied_probability,
    kalshi_taker_fee,
    edge_after_fees,
)


class TestWinProbability:
    """Tests for the core Brownian motion win probability model."""

    SIGMA = 1.7  # NBA baseline

    def test_leading_team_is_heavy_favorite(self):
        """Team up 10 with 5 minutes left should be a heavy favorite."""
        prob = win_probability(margin=10, time_remaining=5, drift=0, sigma=self.SIGMA)
        assert prob > 0.90

    def test_trailing_team_is_heavy_underdog(self):
        """Team down 10 with 5 minutes left should be a heavy underdog."""
        prob = win_probability(margin=-10, time_remaining=5, drift=0, sigma=self.SIGMA)
        assert prob < 0.10

    def test_zero_margin_zero_drift_is_fifty_fifty(self):
        """Tied game, no drift → exactly 50%."""
        prob = win_probability(margin=0, time_remaining=10, drift=0, sigma=self.SIGMA)
        assert abs(prob - 0.5) < 1e-9

    def test_game_over_win(self):
        """Positive margin at time=0 → certain home win."""
        assert win_probability(margin=1, time_remaining=0, drift=0, sigma=self.SIGMA) == 1.0

    def test_game_over_loss(self):
        """Negative margin at time=0 → certain away win."""
        assert win_probability(margin=-1, time_remaining=0, drift=0, sigma=self.SIGMA) == 0.0

    def test_game_over_tie(self):
        """Tie at time=0 → 0.5 (overtime coin flip)."""
        assert win_probability(margin=0, time_remaining=0, drift=0, sigma=self.SIGMA) == 0.5

    def test_positive_drift_pushes_above_fifty(self):
        """Positive drift (home favored) should make prob > 0.5 when tied."""
        prob = win_probability(margin=0, time_remaining=10, drift=0.5, sigma=self.SIGMA)
        assert prob > 0.5

    def test_negative_drift_pushes_below_fifty(self):
        """Negative drift (away favored) should make prob < 0.5 when tied."""
        prob = win_probability(margin=0, time_remaining=10, drift=-0.5, sigma=self.SIGMA)
        assert prob < 0.5

    def test_probability_always_in_unit_interval(self):
        """Win probability must be in [0, 1] for all reasonable inputs."""
        for margin in [-30, -10, -1, 0, 1, 10, 30]:
            for t in [0.5, 1, 5, 10, 24, 48]:
                p = win_probability(margin=margin, time_remaining=t, drift=0, sigma=self.SIGMA)
                assert 0.0 <= p <= 1.0, f"OOB: margin={margin}, t={t}, p={p}"

    def test_more_time_means_more_uncertainty(self):
        """With a fixed lead, probability should be higher (more certain) with less time."""
        p_little_time = win_probability(margin=5, time_remaining=2, drift=0, sigma=self.SIGMA)
        p_lot_of_time = win_probability(margin=5, time_remaining=20, drift=0, sigma=self.SIGMA)
        assert p_little_time > p_lot_of_time

    def test_higher_sigma_means_more_uncertainty(self):
        """Higher volatility should pull probabilities toward 0.5."""
        p_low_sigma = win_probability(margin=10, time_remaining=5, drift=0, sigma=1.0)
        p_high_sigma = win_probability(margin=10, time_remaining=5, drift=0, sigma=3.0)
        assert p_low_sigma > p_high_sigma


class TestEstimateDrift:

    def test_home_favorite_has_positive_drift(self):
        """
        Pre-game spread convention: positive spread = home favored.
        e.g. spread=+6 means home expected to win by 6 → positive drift.
        """
        drift = estimate_drift(pre_game_spread=6.0)
        assert drift > 0

    def test_away_favorite_has_negative_drift(self):
        drift = estimate_drift(pre_game_spread=-6.0)
        assert drift < 0

    def test_pick_em_has_zero_drift(self):
        assert estimate_drift(0.0) == 0.0

    def test_drift_formula(self):
        """drift = spread / total_minutes."""
        spread = -6.5
        drift = estimate_drift(spread, total_minutes=48.0)
        assert drift == pytest.approx(spread / 48.0)

    def test_custom_game_length(self):
        """NCAAW games are 40 minutes."""
        drift = estimate_drift(pre_game_spread=4.0, total_minutes=40.0)
        assert drift == pytest.approx(4.0 / 40.0)


class TestImpliedProbability:

    def test_fifty_cents(self):
        assert implied_probability(50) == pytest.approx(0.5)

    def test_cents_input(self):
        assert implied_probability(65) == pytest.approx(0.65)

    def test_proportion_input(self):
        """If passed a value already in [0,1], should pass through."""
        assert implied_probability(0.72) == pytest.approx(0.72)

    def test_zero(self):
        assert implied_probability(0) == pytest.approx(0.0)

    def test_hundred(self):
        assert implied_probability(100) == pytest.approx(1.0)


class TestKalshiTakerFee:

    def test_fee_is_maximized_at_fifty(self):
        fee_50 = kalshi_taker_fee(0.5)
        fee_40 = kalshi_taker_fee(0.4)
        fee_60 = kalshi_taker_fee(0.6)
        assert fee_50 > fee_40
        assert fee_50 > fee_60

    def test_fee_near_zero_at_extremes(self):
        assert kalshi_taker_fee(0.01) < 0.001
        assert kalshi_taker_fee(0.99) < 0.001

    def test_fee_formula(self):
        p = 0.65
        assert kalshi_taker_fee(p) == pytest.approx(0.07 * p * (1 - p))

    def test_accepts_cents_input(self):
        """Fee function should handle price in cents (> 1) as well."""
        assert kalshi_taker_fee(65) == pytest.approx(kalshi_taker_fee(0.65))

    def test_fee_is_symmetric(self):
        """Fee at P and 1-P should be the same."""
        assert kalshi_taker_fee(0.3) == pytest.approx(kalshi_taker_fee(0.7))


class TestEdgeAfterFees:

    def test_positive_edge_when_model_above_market(self):
        """Model says 70%, market says 60% → positive edge."""
        edge = edge_after_fees(model_prob=0.70, kalshi_price=0.60)
        assert edge > 0

    def test_negative_edge_when_model_below_market(self):
        """Model says 60%, market says 70% → negative edge."""
        edge = edge_after_fees(model_prob=0.60, kalshi_price=0.70)
        assert edge < 0

    def test_breakeven_price_below_model_prob(self):
        """
        Even if model_prob == kalshi_price, edge is negative because of the fee.
        You need model_prob > kalshi_price + fee to have positive edge.
        """
        price = 0.65
        edge = edge_after_fees(model_prob=price, kalshi_price=price)
        assert edge < 0

    def test_edge_formula(self):
        model = 0.72
        price = 0.60
        expected = model - price - kalshi_taker_fee(price)
        assert edge_after_fees(model, price) == pytest.approx(expected)
