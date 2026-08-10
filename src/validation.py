"""Closed-form sanity checks (PROJECT.md Section 7).

Each function runs one of the required validation experiments and returns the
raw numbers; the pytest suite in tests/test_model.py asserts on them.  Keeping
the computations here (rather than inline in the tests) lets the dashboard's
About tab and the report re-use the same evidence of correctness.

Statistical checks use CLT-based confidence intervals (output analysis,
Lecture 3): an estimate passes when the true value lies inside a z * SE band.
Tests use z = 4 with fixed seeds, so failures indicate real bugs, not luck.
"""

from __future__ import annotations

import numpy as np

from .model import MarketParams, simulate_market_seeded
from .policies import (
    EMA_GRID,
    EMAThresholdPolicy,
    buy_and_hold_profits,
    ema_profits,
    run_policy_path,
)


def zero_noise_check(n_reps: int = 4000, seed: int = 20260810) -> dict:
    """Section 7 check 1: sigma_p = 0, kappa = 1.

    With no observation noise the price IS the hidden probability (up to the
    price clip bounds, which the chosen parameters never reach), so:
    - max |p_t - q_t| must be exactly 0;
    - EMA with alpha = 1, delta = 0 has f_t = p_t, never sees a mispricing,
      and therefore never trades;
    - every policy is then betting at fair prices: by optional stopping on the
      martingale q_t, every EMA policy and buy-and-hold all have expected
      profit 0, so their sample means must agree with 0 and with each other.
    """
    params = MarketParams(q0=0.40, T=50, sigma_q=0.02, sigma_p=0.0, kappa=1.0, variant="A")
    paths = simulate_market_seeded(params, n_reps, seed)

    max_price_gap = float(np.max(np.abs(paths.p - paths.q)))

    # alpha=1, delta=0 EMA must never trade on any path.
    degenerate_profit = ema_profits(paths, alpha=1.0, delta=0.0)
    trades = 0
    pol = EMAThresholdPolicy(alpha=1.0, delta=0.0)
    for i in range(min(n_reps, 200)):  # per-path double-check on a subsample
        _, path_trades = run_policy_path(pol, paths.p[i], int(paths.y[i]))
        trades += len(path_trades)

    bh = buy_and_hold_profits(paths)
    grid_means = {}
    grid_ses = {}
    grid_diff_means = {}
    grid_diff_ses = {}
    for alpha, delta in EMA_GRID:
        profits = ema_profits(paths, alpha=alpha, delta=delta)
        grid_means[(alpha, delta)] = float(profits.mean())
        grid_ses[(alpha, delta)] = float(profits.std(ddof=1) / np.sqrt(n_reps))
        # Paired difference on common paths (CRN, Lecture 7): the right SE for
        # comparing a policy with buy-and-hold, much tighter than combining
        # the two marginal SEs as if independent.
        diff = profits - bh
        grid_diff_means[(alpha, delta)] = float(diff.mean())
        grid_diff_ses[(alpha, delta)] = float(diff.std(ddof=1) / np.sqrt(n_reps))

    return {
        "max_price_gap": max_price_gap,
        "degenerate_max_abs_profit": float(np.max(np.abs(degenerate_profit))),
        "degenerate_trades_on_subsample": trades,
        "grid_means": grid_means,
        "grid_ses": grid_ses,
        "grid_diff_means": grid_diff_means,
        "grid_diff_ses": grid_diff_ses,
        "bh_mean": float(bh.mean()),
        "bh_se": float(bh.std(ddof=1) / np.sqrt(n_reps)),
    }


def martingale_check(
    params: MarketParams | None = None, n_reps: int = 20000, seed: int = 20260811
) -> dict:
    """Section 7 check 2: the Layer-1 walk is (numerically) a martingale.

    E[q_{t+1} | q_t] = q_t because the Z_t are symmetric and the barriers are
    far from the chosen q0, so the sample mean of q_T must be ≈ q0 and the
    settlement frequency must also be ≈ q0 (law of total expectation:
    P(Y=1) = E[q_T] = q0).  Returns means and CLT standard errors (Lecture 3).
    """
    if params is None:
        params = MarketParams(q0=0.40, T=50, sigma_q=0.02, sigma_p=0.02)
    paths = simulate_market_seeded(params, n_reps, seed)
    q_T = paths.q[:, -1]
    return {
        "q0": params.q0,
        "mean_qT": float(q_T.mean()),
        "se_qT": float(q_T.std(ddof=1) / np.sqrt(n_reps)),
        "settle_freq": float(paths.y.mean()),
        "se_settle": float(paths.y.std(ddof=1) / np.sqrt(n_reps)),
    }


def calibration_check(
    x_grid: tuple[float, ...] = (0.10, 0.25, 0.50, 0.75, 0.90),
    n_reps: int = 20000,
    seed: int = 20260812,
) -> list[dict]:
    """Section 7 check 3: contracts starting at q0 = x settle YES ≈ x of the time.

    Runs the martingale/settlement check across a grid of starting
    probabilities.  Seeds are offset per grid point so the batches are
    independent.
    """
    out = []
    for i, x in enumerate(x_grid):
        params = MarketParams(q0=x, T=50, sigma_q=0.02, sigma_p=0.02)
        paths = simulate_market_seeded(params, n_reps, seed + i)
        freq = float(paths.y.mean())
        se = float(paths.y.std(ddof=1) / np.sqrt(n_reps))
        out.append({"q0": x, "settle_freq": freq, "se": se})
    return out


class _FutureSensitiveProbe:
    """A canary policy whose decisions depend on the WHOLE history it is shown.

    It trades on max(price_history), so if the evaluation harness ever leaks
    any future price into price_history — even one index — its pre-leak
    decisions change immediately.  Used only by no_lookahead_check; it mirrors
    the Policy interface (reset/decide) without being a real strategy.
    """

    name = "future-sensitive probe"

    def reset(self) -> None:
        self._bought = False

    def decide(self, price_history: np.ndarray) -> int:
        if not self._bought and float(np.max(price_history)) > 0.60:
            self._bought = True
            return +1
        return 0


def no_lookahead_check(seed: int = 20260813) -> dict:
    """Section 7 check 4: policies can only use PAST data.

    Structural argument: Policy.decide receives a copy of p_0..p_t and nothing
    else — there is no way to read q_t, the outcome, or future prices (the
    test suite additionally asserts the interface signature and that the real
    harness hands each policy exactly p[0..t] as a fresh copy).

    Behavioural check — run through the REAL evaluation harness
    (run_policy_path) on full price series, never a re-implementation of its
    slicing: (a) shock all prices from t_perturb onward (+0.30) and confirm
    every trade decision strictly BEFORE t_perturb is identical to the
    unshocked run, for both the EMA policy and a deliberately future-hungry
    probe policy that trades on max(history) and would flip immediately if the
    harness leaked even one future price; (b) shock only PAST prices and
    confirm decisions do change, showing the check has power to detect
    dependence on the data it perturbs.
    """
    params = MarketParams(q0=0.40, T=60, sigma_q=0.03, sigma_p=0.05)
    paths = simulate_market_seeded(params, 1, seed)
    prices = paths.p[0].copy()
    y = int(paths.y[0])
    t_perturb = 40

    future_shocked = prices.copy()
    future_shocked[t_perturb:] = np.clip(future_shocked[t_perturb:] + 0.30, 0.01, 0.99)
    # The shock must actually change the data for leg (a) to mean anything.
    assert not np.array_equal(prices, future_shocked)

    past_shocked = prices.copy()
    past_shocked[: t_perturb - 5] = np.clip(past_shocked[: t_perturb - 5] - 0.30, 0.01, 0.99)

    def early_trades(policy, p: np.ndarray) -> list[tuple[int, int]]:
        _, trades = run_policy_path(policy, p, y)
        return [(tr.t, tr.units) for tr in trades if tr.t < t_perturb]

    ema = EMAThresholdPolicy(alpha=0.3, delta=0.02, allow_exit=True)
    probe = _FutureSensitiveProbe()

    future_leak_detected = any(
        early_trades(pol, prices) != early_trades(pol, future_shocked)
        for pol in (ema, probe)
    )
    past_changed = early_trades(ema, prices) != early_trades(ema, past_shocked)
    # The probe must be live (it does buy somewhere on the shocked series) —
    # otherwise it could not have detected a leak even if one existed.
    _, probe_trades = run_policy_path(probe, future_shocked, y)

    return {
        "future_perturbation_changed_decisions": future_leak_detected,
        "past_perturbation_changed_decisions": past_changed,
        "probe_active_on_shocked_series": len(probe_trades) > 0,
    }


def seed_reproducibility_check(seed: int = 20260814, n_reps: int = 500) -> dict:
    """Section 7 check 5: same seed → identical results; new seed → new paths."""
    params = MarketParams(q0=0.40, T=50, sigma_q=0.02, sigma_p=0.03, kappa=0.3, variant="B")
    a = simulate_market_seeded(params, n_reps, seed)
    b = simulate_market_seeded(params, n_reps, seed)
    c = simulate_market_seeded(params, n_reps, seed + 1)
    return {
        "same_seed_identical": bool(
            np.array_equal(a.q, b.q) and np.array_equal(a.p, b.p) and np.array_equal(a.y, b.y)
        ),
        "different_seed_differs": bool(not np.array_equal(a.p, c.p)),
    }
