"""Validation suite for the simulation engine (PROJECT.md Section 7).

Each required Section-7 check is a named test.  Statistical assertions use
CLT confidence bands with z = 4 and fixed seeds (Lecture 3 output analysis):
with the seeds pinned, a failure means a real bug, not sampling luck.
"""

from __future__ import annotations

import inspect

import numpy as np
import pytest

from src.model import MarketParams, simulate_market, simulate_market_seeded
from src.policies import (
    EMA_GRID,
    BuyAndHoldPolicy,
    EMAThresholdPolicy,
    NeverTradePolicy,
    Policy,
    buy_and_hold_profits,
    ema_profits,
    never_trade_profits,
    run_policy_path,
)
from src.validation import (
    calibration_check,
    martingale_check,
    no_lookahead_check,
    seed_reproducibility_check,
    zero_noise_check,
)

Z = 4.0  # width of the CLT acceptance band, in standard errors


# ---------------------------------------------------------------------------
# Section 7, check 1 — zero-noise limit
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def zero_noise_result():
    return zero_noise_check()


@pytest.fixture(scope="module")
def martingale_result():
    return martingale_check()


class TestZeroNoise:
    @pytest.fixture()
    def result(self, zero_noise_result):
        return zero_noise_result

    def test_price_equals_hidden_probability_exactly(self, result):
        assert result["max_price_gap"] == 0.0

    def test_degenerate_ema_never_finds_a_mispricing(self, result):
        # alpha=1 makes f_t = p_t, so f_t - p_t > 0 never fires.
        assert result["degenerate_max_abs_profit"] == 0.0
        assert result["degenerate_trades_on_subsample"] == 0

    def test_all_ema_expected_profits_match_buy_and_hold(self, result):
        # With p_t = q_t every entry happens at a fair price, so by optional
        # stopping on the martingale q_t all policies (including buy-and-hold)
        # have expected profit 0; the sample means must agree within 4 SE.
        # The policy-vs-BH comparison uses the PAIRED difference on common
        # paths (CRN, Lecture 7) — the correlated marginals would give an
        # SE ~3x too wide and much weaker power to catch a real bias.
        assert abs(result["bh_mean"]) < Z * result["bh_se"]
        for key, mean in result["grid_means"].items():
            se = result["grid_ses"][key]
            assert abs(mean) < Z * max(se, 1e-12), f"policy {key} mean {mean}"
            diff = result["grid_diff_means"][key]
            diff_se = result["grid_diff_ses"][key]
            assert abs(diff) < Z * max(diff_se, 1e-12), (
                f"policy {key} paired diff vs BH {diff} exceeds {Z} SE {diff_se}"
            )


# ---------------------------------------------------------------------------
# Section 7, check 2 — martingale property of the hidden walk
# ---------------------------------------------------------------------------

class TestMartingale:
    @pytest.fixture()
    def result(self, martingale_result):
        return martingale_result

    def test_mean_qT_covers_q0(self, result):
        assert abs(result["mean_qT"] - result["q0"]) < Z * result["se_qT"]

    def test_settlement_frequency_covers_q0(self, result):
        assert abs(result["settle_freq"] - result["q0"]) < Z * result["se_settle"]


# ---------------------------------------------------------------------------
# Section 7, check 3 — calibration across a grid of starting probabilities
# ---------------------------------------------------------------------------

def test_calibration_settlement_frequency_matches_q0_grid():
    for row in calibration_check():
        gap = abs(row["settle_freq"] - row["q0"])
        assert gap < Z * row["se"], (
            f"q0={row['q0']}: settle_freq={row['settle_freq']:.4f} "
            f"(gap {gap:.4f} > {Z} SE = {Z * row['se']:.4f})"
        )


# ---------------------------------------------------------------------------
# Section 7, check 4 — no lookahead
# ---------------------------------------------------------------------------

class TestNoLookahead:
    def test_future_prices_cannot_affect_decisions(self):
        # Runs the REAL harness (run_policy_path) on full series with a shocked
        # future tail; includes a future-hungry probe policy that would flip
        # immediately if the harness leaked any future price.
        result = no_lookahead_check()
        assert not result["future_perturbation_changed_decisions"]
        assert result["probe_active_on_shocked_series"], (
            "probe never trades — the leak canary has no detection power"
        )

    def test_past_prices_do_affect_decisions(self):
        result = no_lookahead_check()
        assert result["past_perturbation_changed_decisions"]

    def test_policy_interface_only_accepts_price_history(self):
        # Structural guarantee: decide() takes exactly one input — the price
        # history.  There is no channel through which q_t, the settlement
        # outcome, or future prices could reach a policy.
        for cls in (EMAThresholdPolicy, BuyAndHoldPolicy, NeverTradePolicy, Policy):
            sig = inspect.signature(cls.decide)
            assert list(sig.parameters) == ["self", "price_history"]

    def test_policies_receive_a_copy_not_a_view(self):
        # run_policy_path hands each policy a copy, so even a hostile policy
        # cannot reach the parent buffer or anything beyond index t.
        seen_lengths: list[int] = []

        class Recorder(Policy):
            def reset(self) -> None:
                pass

            def decide(self, price_history: np.ndarray) -> int:
                assert price_history.base is None  # a copy, not a view
                seen_lengths.append(len(price_history))
                return 0

        prices = np.linspace(0.4, 0.6, 21)
        run_policy_path(Recorder(), prices, outcome=1)
        assert seen_lengths == list(range(1, 22))  # p[0..t] each period, no more


# ---------------------------------------------------------------------------
# Section 7, check 5 — seed reproducibility
# ---------------------------------------------------------------------------

def test_seed_reproducibility():
    result = seed_reproducibility_check()
    assert result["same_seed_identical"]
    assert result["different_seed_differs"]


# ---------------------------------------------------------------------------
# Engine internals — consistency checks beyond the required five
# ---------------------------------------------------------------------------

def test_variant_b_with_kappa_1_recovers_variant_a():
    seed = 7
    pa = MarketParams(q0=0.4, T=80, sigma_q=0.03, sigma_p=0.04, kappa=1.0, variant="A")
    pb = MarketParams(q0=0.4, T=80, sigma_q=0.03, sigma_p=0.04, kappa=1.0, variant="B")
    a = simulate_market_seeded(pa, 300, seed)
    b = simulate_market_seeded(pb, 300, seed)
    np.testing.assert_allclose(a.p, b.p, rtol=0, atol=1e-12)
    assert np.array_equal(a.y, b.y)


def test_paths_respect_bounds():
    params = MarketParams(q0=0.05, T=200, sigma_q=0.10, sigma_p=0.10, kappa=0.2, variant="B")
    paths = simulate_market_seeded(params, 500, seed=11)
    assert np.all(paths.q >= 0.001) and np.all(paths.q <= 0.999)
    assert np.all(paths.p >= 0.01) and np.all(paths.p <= 0.99)
    assert set(np.unique(paths.y)).issubset({0, 1})


def test_vectorized_ema_matches_stepwise_loop():
    # The fast 2-D evaluator used by the dashboard/experiments must agree
    # bit-for-bit in P&L with the transparent per-period interface.
    params = MarketParams(q0=0.45, T=60, sigma_q=0.03, sigma_p=0.05, kappa=0.3, variant="B")
    paths = simulate_market_seeded(params, 50, seed=23)
    for allow_exit in (False, True):
        for alpha, delta in EMA_GRID:
            fast = ema_profits(paths, alpha, delta, cost=0.01, allow_exit=allow_exit)
            pol = EMAThresholdPolicy(alpha, delta, allow_exit=allow_exit)
            for i in range(paths.n_reps):
                slow, _ = run_policy_path(pol, paths.p[i], int(paths.y[i]), cost=0.01)
                assert fast[i] == pytest.approx(slow, abs=1e-12), (
                    f"alpha={alpha}, delta={delta}, exit={allow_exit}, rep={i}"
                )


def test_vectorized_benchmarks_match_stepwise_loop():
    params = MarketParams(q0=0.45, T=60, sigma_q=0.03, sigma_p=0.05)
    paths = simulate_market_seeded(params, 50, seed=29)
    fast_bh = buy_and_hold_profits(paths, cost=0.02)
    for i in range(paths.n_reps):
        slow, trades = run_policy_path(BuyAndHoldPolicy(), paths.p[i], int(paths.y[i]), cost=0.02)
        assert len(trades) == 1 and trades[0].t == 0
        assert fast_bh[i] == pytest.approx(slow, abs=1e-12)
    assert np.all(never_trade_profits(paths) == 0.0)


def test_never_trade_is_exactly_zero_stepwise():
    params = MarketParams()
    paths = simulate_market_seeded(params, 10, seed=31)
    for i in range(10):
        profit, trades = run_policy_path(NeverTradePolicy(), paths.p[i], int(paths.y[i]))
        assert profit == 0.0 and trades == []


def test_param_validation_rejects_bad_inputs():
    with pytest.raises(ValueError):
        MarketParams(q0=1.5)
    with pytest.raises(ValueError):
        MarketParams(kappa=0.0)
    with pytest.raises(ValueError):
        MarketParams(variant="C")
    with pytest.raises(ValueError):
        MarketParams(T=0)
    with pytest.raises(ValueError):
        EMAThresholdPolicy(alpha=0.0, delta=0.05)


def test_explicit_rng_flows_through():
    # Same Generator state in → same batch out; the module never touches
    # global numpy random state.
    params = MarketParams()
    a = simulate_market(params, 20, np.random.default_rng(99))
    b = simulate_market(params, 20, np.random.default_rng(99))
    assert np.array_equal(a.p, b.p) and np.array_equal(a.y, b.y)
