"""Batch experiments, confidence intervals, run-length control, sweeps (Section 5).

Output-analysis conventions (Lecture 3):
- every estimate is reported with a CLT-based 95% confidence interval
  mean ± z_{0.975} * s / sqrt(n);
- the run-length control procedure grows the sample until the CI half-width
  falls below a user tolerance (sequential run-length control, Lecture 3).

Comparison conventions (Lectures 7-8, variance reduction / comparing systems):
- all policies at a given parameter point are evaluated on the SAME simulated
  paths (common random numbers), and comparisons against buy-and-hold use the
  paired differences, whose CI is much tighter than two independent CIs.

Run everything (sweeps + CSVs + report figures) with:
    python -m src.experiments
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from .model import MarketParams, MarketPaths, simulate_market_seeded
from .policies import (
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

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
FIGURES_DIR = Path(__file__).resolve().parent.parent / "report" / "figures"

#: Documented master seed for every result shipped in results/ and the report.
MASTER_SEED = 20260812

#: Baseline market used by the sweeps (variant B so kappa matters; kappa=1
#: recovers variant A as one end of the sweep).
BASELINE = MarketParams(q0=0.40, T=100, sigma_q=0.02, sigma_p=0.05, kappa=1.0, variant="B")


# ---------------------------------------------------------------------------
# Core batch machinery
# ---------------------------------------------------------------------------

def profits_on_paths(
    paths: MarketPaths, policy: Policy, cost: float = 0.0, unit: float = 1.0
) -> np.ndarray:
    """Evaluate one policy on an already-simulated batch of paths.

    Uses the fast vectorised evaluators for the known policy classes and falls
    back to the transparent per-path loop for anything else (the two are
    asserted equal in the test suite).
    """
    if isinstance(policy, EMAThresholdPolicy):
        return ema_profits(paths, policy.alpha, policy.delta, cost, unit, policy.allow_exit)
    if isinstance(policy, BuyAndHoldPolicy):
        return buy_and_hold_profits(paths, cost, unit)
    if isinstance(policy, NeverTradePolicy):
        return never_trade_profits(paths)
    return np.array(
        [
            run_policy_path(policy, paths.p[i], int(paths.y[i]), cost, unit)[0]
            for i in range(paths.n_reps)
        ]
    )


def run_batch(
    params: MarketParams,
    policy: Policy,
    n_reps: int,
    seed: int,
    cost: float = 0.0,
    unit: float = 1.0,
) -> np.ndarray:
    """Simulate n_reps contracts and return per-replication profits (Section 5)."""
    paths = simulate_market_seeded(params, n_reps, seed)
    return profits_on_paths(paths, policy, cost, unit)


def summarize(profits: np.ndarray, confidence: float = 0.95) -> dict:
    """The professor's three measures + CI (Section 5, Lecture 3).

    Returns expected profit, P(loss), mean loss given loss (a negative number;
    NaN when no replication lost money), and a CLT-based confidence interval
    on the expected profit.
    """
    profits = np.asarray(profits, dtype=float)
    n = profits.size
    mean = float(profits.mean())
    se = float(profits.std(ddof=1) / np.sqrt(n)) if n > 1 else float("nan")
    z = float(stats.norm.ppf(0.5 + confidence / 2.0))
    losses = profits[profits < 0.0]
    return {
        "n": n,
        "mean": mean,
        "se": se,
        "ci_low": mean - z * se,
        "ci_high": mean + z * se,
        "half_width": z * se,
        "p_loss": float((profits < 0.0).mean()),
        "mean_loss_given_loss": float(losses.mean()) if losses.size else float("nan"),
    }


def paired_diff_vs_benchmark(policy_profits: np.ndarray, bench_profits: np.ndarray) -> dict:
    """CI on E[policy - benchmark] using paired differences on common paths.

    Common random numbers (Lecture 7): both P&L vectors come from the same
    simulated paths, so the difference has far lower variance than the two
    marginal estimates, and 'significant' means the 95% CI excludes 0.
    """
    diff = summarize(np.asarray(policy_profits) - np.asarray(bench_profits))
    diff["beats_benchmark"] = bool(diff["ci_low"] > 0.0)
    diff["loses_to_benchmark"] = bool(diff["ci_high"] < 0.0)
    return diff


def run_until_precision(
    params: MarketParams,
    policy: Policy,
    tol: float,
    seed: int,
    cost: float = 0.0,
    unit: float = 1.0,
    initial_reps: int = 1000,
    max_reps: int = 512_000,
) -> dict:
    """Sequential run-length control (Lecture 3).

    Grow the number of replications (doubling each round, each round an
    independent batch via an offset seed) until the 95% CI half-width on the
    expected profit falls below ``tol`` or ``max_reps`` is reached.  Returns
    the pooled profits, the final summary, and the per-round history so the
    procedure itself can be shown in the report/dashboard.
    """
    if tol <= 0:
        raise ValueError(f"tol must be > 0, got {tol}")
    chunks: list[np.ndarray] = []
    history: list[dict] = []
    n_next = initial_reps
    round_idx = 0
    while True:
        chunks.append(run_batch(params, policy, n_next, seed + round_idx, cost, unit))
        pooled = np.concatenate(chunks)
        s = summarize(pooled)
        history.append({"round": round_idx, "n_total": s["n"], "half_width": s["half_width"]})
        if s["half_width"] <= tol or s["n"] >= max_reps:
            return {"profits": pooled, "summary": s, "history": history, "converged": s["half_width"] <= tol}
        n_next = s["n"]  # double the total each round
        round_idx += 1


# ---------------------------------------------------------------------------
# Policy comparison tables and sweeps
# ---------------------------------------------------------------------------

def grid_policies(allow_exit: bool = False) -> list[EMAThresholdPolicy]:
    """The nine Section-4 EMA policies."""
    return [EMAThresholdPolicy(a, d, allow_exit) for a, d in EMA_GRID]


def compare_policies(
    params: MarketParams, n_reps: int, seed: int, cost: float = 0.0
) -> pd.DataFrame:
    """One row per policy (9 EMA + buy-and-hold + never-trade) on common paths.

    Columns: the Section-5 measures plus the paired difference vs buy-and-hold.
    """
    paths = simulate_market_seeded(params, n_reps, seed)
    bh = buy_and_hold_profits(paths, cost)
    rows = []
    policies: list[Policy] = [*grid_policies(), BuyAndHoldPolicy(), NeverTradePolicy()]
    for pol in policies:
        profits = profits_on_paths(paths, pol, cost)
        s = summarize(profits)
        d = paired_diff_vs_benchmark(profits, bh)
        alpha = getattr(pol, "alpha", np.nan)
        delta = getattr(pol, "delta", np.nan)
        rows.append(
            {
                "policy": pol.name,
                "alpha": alpha,
                "delta": delta,
                "mean_profit": s["mean"],
                "ci_low": s["ci_low"],
                "ci_high": s["ci_high"],
                "p_loss": s["p_loss"],
                "mean_loss_given_loss": s["mean_loss_given_loss"],
                "diff_vs_bh": d["mean"],
                "diff_ci_low": d["ci_low"],
                "diff_ci_high": d["ci_high"],
                "beats_bh": d["beats_benchmark"],
            }
        )
    return pd.DataFrame(rows)


def _sweep(
    param_name: str,
    values: list,
    base: MarketParams,
    n_reps: int,
    seed: int,
    cost: float = 0.0,
) -> pd.DataFrame:
    """Run compare_policies at each value of one market parameter.

    Each sweep point gets an offset seed (independent batches across points);
    within a point every policy shares the same paths (CRN, Lecture 7).
    """
    frames = []
    for i, v in enumerate(values):
        params = replace(base, **{param_name: v})
        df = compare_policies(params, n_reps, seed + 1000 * i, cost)
        df.insert(0, param_name, v)
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def sweep_sigma_p(
    values=(0.0, 0.01, 0.02, 0.05, 0.08, 0.12),
    base: MarketParams = BASELINE,
    n_reps: int = 20000,
    seed: int = MASTER_SEED,
    cost: float = 0.0,
) -> pd.DataFrame:
    """Sensitivity to market noisiness sigma_p (Section 5)."""
    return _sweep("sigma_p", list(values), base, n_reps, seed + 1, cost)


def sweep_kappa(
    values=(0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0),
    base: MarketParams = BASELINE,
    n_reps: int = 20000,
    seed: int = MASTER_SEED,
    cost: float = 0.0,
) -> pd.DataFrame:
    """Sensitivity to mispricing persistence kappa (Section 5, headline input)."""
    return _sweep("kappa", list(values), base, n_reps, seed + 2, cost)


def sweep_cost(
    values=(0.0, 0.01, 0.02),
    base: MarketParams = BASELINE,
    n_reps: int = 20000,
    seed: int = MASTER_SEED,
) -> pd.DataFrame:
    """Sensitivity to per-trade cost c (Section 5)."""
    frames = []
    for i, c in enumerate(values):
        df = compare_policies(base, n_reps, seed + 3 + 1000 * i, cost=c)
        df.insert(0, "cost", c)
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def headline_kappa_table(
    kappas=(0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0),
    costs=(0.0, 0.01, 0.02),
    base: MarketParams = BASELINE,
    n_reps: int = 20000,
    seed: int = MASTER_SEED,
) -> pd.DataFrame:
    """Headline experiment (Section 5): how much persistence does the market
    need before ANY EMA policy beats buy-and-hold?

    For every (kappa, cost) cell, evaluate the whole EMA grid and buy-and-hold
    on common paths and record the best policy's paired difference vs
    buy-and-hold with its 95% CI.  'any_ema_beats_bh' is True when that CI
    lies strictly above 0.
    """
    rows = []
    for i, kappa in enumerate(kappas):
        params = replace(base, kappa=kappa, variant="B")
        paths = simulate_market_seeded(params, n_reps, seed + 7 + 1000 * i)
        for c in costs:
            bh = buy_and_hold_profits(paths, c)
            best = None
            for pol in grid_policies():
                profits = profits_on_paths(paths, pol, c)
                d = paired_diff_vs_benchmark(profits, bh)
                if best is None or d["mean"] > best["diff_vs_bh"]:
                    best = {
                        "kappa": kappa,
                        "cost": c,
                        "best_policy": pol.name,
                        "alpha": pol.alpha,
                        "delta": pol.delta,
                        "best_mean_profit": float(np.mean(profits)),
                        "bh_mean_profit": float(np.mean(bh)),
                        "diff_vs_bh": d["mean"],
                        "diff_ci_low": d["ci_low"],
                        "diff_ci_high": d["ci_high"],
                        "any_ema_beats_bh": d["beats_benchmark"],
                    }
                elif d["beats_benchmark"] and not best["any_ema_beats_bh"]:
                    # 'any' means any: keep the best-by-mean row but record
                    # that at least one grid policy is CI-significant.
                    best["any_ema_beats_bh"] = True
            rows.append(best)
    return pd.DataFrame(rows)


def headline_interaction_table(
    kappas=(0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0),
    sigma_ps=(0.01, 0.02, 0.05, 0.08),
    cost: float = 0.01,
    base: MarketParams = BASELINE,
    n_reps: int = 20000,
    seed: int = MASTER_SEED,
) -> pd.DataFrame:
    """Supplementary headline: the persistence needed depends on the noise size.

    A (kappa, sigma_p) grid at a fixed realistic cost, recording the best EMA
    policy's paired edge over buy-and-hold and whether it is CI-significant.
    This shows the answer to 'how small a kappa do you need?' is really a
    frontier in (kappa, sigma_p) space, not a single number.
    """
    rows = []
    i = 0
    for kappa in kappas:
        for sp in sigma_ps:
            params = replace(base, kappa=kappa, sigma_p=sp, variant="B")
            paths = simulate_market_seeded(params, n_reps, seed + 31 + 1000 * i)
            i += 1
            bh = buy_and_hold_profits(paths, cost)
            best = None
            any_sig = False
            for pol in grid_policies():
                profits = profits_on_paths(paths, pol, cost)
                d = paired_diff_vs_benchmark(profits, bh)
                any_sig = any_sig or d["beats_benchmark"]
                if best is None or d["mean"] > best["diff_vs_bh"]:
                    best = {
                        "kappa": kappa,
                        "sigma_p": sp,
                        "cost": cost,
                        "best_policy": pol.name,
                        "diff_vs_bh": d["mean"],
                        "diff_ci_low": d["ci_low"],
                        "diff_ci_high": d["ci_high"],
                    }
            best["any_ema_beats_bh"] = any_sig
            rows.append(best)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# EXTENSION experiments (news jumps — beyond the locked Section-3 model).
# Kept separate from the approved-model suite: everything above this line
# uses jump_rate = 0 and is untouched by the extension.
# ---------------------------------------------------------------------------

def _best_cell_row(paths: MarketPaths, cost: float) -> dict:
    """Best grid policy by paired edge vs buy-and-hold on one batch."""
    bh = buy_and_hold_profits(paths, cost)
    best = None
    any_sig = False
    for pol in grid_policies():
        profits = profits_on_paths(paths, pol, cost)
        d = paired_diff_vs_benchmark(profits, bh)
        any_sig = any_sig or d["beats_benchmark"]
        if best is None or d["mean"] > best["diff_vs_bh"]:
            s = summarize(profits)
            best = {
                "best_policy": pol.name,
                "best_mean_profit": s["mean"],
                "best_p_loss": s["p_loss"],
                "bh_mean_profit": float(np.mean(bh)),
                "diff_vs_bh": d["mean"],
                "diff_ci_low": d["ci_low"],
                "diff_ci_high": d["ci_high"],
                "best_beats_bh": d["beats_benchmark"],
            }
    best["any_ema_beats_bh"] = any_sig
    return best


def model_case_matrix(
    n_reps: int = 20000,
    seed: int = MASTER_SEED,
    cost: float = 0.01,
    jump_rate: float = 0.05,
    jump_scale: float = 0.20,
) -> pd.DataFrame:
    """The four model cases side by side: variant A/B x jumps off/on.

    Same sigma_p, horizon, and cost everywhere, so the only thing changing
    across rows is the price-adjustment mechanism and whether the hidden
    truth can jump on news.  Answers 'which model world are we in, and does
    the EMA edge survive in each?' in one table.
    """
    cases = [
        ("A", 1.0, 0.0, "Variant A · no jumps"),
        ("B", 0.3, 0.0, "Variant B (kappa=0.3) · no jumps"),
        ("A", 1.0, jump_rate, "Variant A · jumps"),
        ("B", 0.3, jump_rate, "Variant B (kappa=0.3) · jumps"),
    ]
    rows = []
    for i, (variant, kappa, lam, label) in enumerate(cases):
        params = replace(BASELINE, variant=variant, kappa=kappa,
                         jump_rate=lam, jump_scale=jump_scale)
        paths = simulate_market_seeded(params, n_reps, seed + 211 + 1000 * i)
        row = {"case": label, "variant": variant, "kappa": kappa,
               "jump_rate": lam, "jump_scale": jump_scale if lam > 0 else 0.0,
               "cost": cost, **_best_cell_row(paths, cost)}
        rows.append(row)
    return pd.DataFrame(rows)


def sweep_jump_rate(
    rates=(0.0, 0.02, 0.05, 0.10, 0.20),
    jump_scale: float = 0.20,
    cost: float = 0.01,
    n_reps: int = 20000,
    seed: int = MASTER_SEED,
) -> pd.DataFrame:
    """EXTENSION headline: how news intensity erodes the dip-buying edge.

    Baseline persistent market (variant B, kappa = 0.3) with the Poisson
    news-jump rate lambda swept from 0 (the approved model) upward.  Each
    point is an independent seeded batch; policies share paths (CRN).
    """
    rows = []
    for i, lam in enumerate(rates):
        params = replace(BASELINE, kappa=0.3, jump_rate=lam, jump_scale=jump_scale)
        paths = simulate_market_seeded(params, n_reps, seed + 307 + 1000 * i)
        rows.append({"jump_rate": lam, "jump_scale": jump_scale, "cost": cost,
                     **_best_cell_row(paths, cost)})
    return pd.DataFrame(rows)


def jump_frontier_table(
    rates=(0.02, 0.05, 0.10, 0.20),
    scales=(0.10, 0.20, 0.40, 0.60),
    cost: float = 0.01,
    n_reps: int = 20000,
    seed: int = MASTER_SEED,
) -> pd.DataFrame:
    """EXTENSION: map the news frontier over (lambda, jump size).

    For each cell of the grid, record the best EMA policy's paired edge over
    buy-and-hold and whether any grid policy is CI-significant — locating the
    boundary where a dip becomes more likely news than noise and dip-buying
    stops working.  Variant B, kappa = 0.3, as in the other jump experiments.
    """
    rows = []
    i = 0
    for lam in rates:
        for sc in scales:
            params = replace(BASELINE, kappa=0.3, jump_rate=lam, jump_scale=sc)
            paths = simulate_market_seeded(params, n_reps, seed + 409 + 1000 * i)
            i += 1
            rows.append({"jump_rate": lam, "jump_scale": sc, "cost": cost,
                         **_best_cell_row(paths, cost)})
    return pd.DataFrame(rows)


def run_extension(n_reps: int = 20000, seed: int = MASTER_SEED, verbose: bool = True) -> dict[str, pd.DataFrame]:
    """Run the extension experiments and save their CSVs (clearly separated
    from the approved-model outputs)."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = {
        "model_case_matrix": model_case_matrix(n_reps=n_reps, seed=seed),
        "sweep_jump_rate": sweep_jump_rate(n_reps=n_reps, seed=seed),
        "jump_frontier": jump_frontier_table(n_reps=n_reps, seed=seed),
    }
    for name, df in out.items():
        df.to_csv(RESULTS_DIR / f"{name}.csv", index=False)
        if verbose:
            print(f"[experiments] wrote results/{name}.csv ({len(df)} rows, EXTENSION)")
    return out


# ---------------------------------------------------------------------------
# End-to-end driver: python -m src.experiments
# ---------------------------------------------------------------------------

def run_all(n_reps: int = 20000, seed: int = MASTER_SEED, verbose: bool = True) -> dict[str, pd.DataFrame]:
    """Run every Section-5 experiment and save CSVs into results/."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out: dict[str, pd.DataFrame] = {}

    baseline_a = replace(BASELINE, variant="A")
    jobs = {
        "policy_comparison_variantA": lambda: compare_policies(baseline_a, n_reps, seed),
        "policy_comparison_variantB_kappa03": lambda: compare_policies(
            replace(BASELINE, kappa=0.3), n_reps, seed
        ),
        "sweep_sigma_p": lambda: sweep_sigma_p(n_reps=n_reps, seed=seed),
        "sweep_kappa": lambda: sweep_kappa(n_reps=n_reps, seed=seed),
        "sweep_cost": lambda: sweep_cost(n_reps=n_reps, seed=seed),
        "headline_kappa": lambda: headline_kappa_table(n_reps=n_reps, seed=seed),
        "headline_interaction": lambda: headline_interaction_table(n_reps=n_reps, seed=seed),
    }
    for name, job in jobs.items():
        df = job()
        df.to_csv(RESULTS_DIR / f"{name}.csv", index=False)
        out[name] = df
        if verbose:
            print(f"[experiments] wrote results/{name}.csv ({len(df)} rows)")

    # Run-length control demo (Lecture 3): tighten the headline cell to ±0.005.
    rlc = run_until_precision(
        replace(BASELINE, kappa=0.2),
        EMAThresholdPolicy(0.3, 0.05),
        tol=0.005,
        seed=seed + 99,
    )
    rlc_df = pd.DataFrame(rlc["history"])
    rlc_df.to_csv(RESULTS_DIR / "run_length_control.csv", index=False)
    out["run_length_control"] = rlc_df
    if verbose:
        s = rlc["summary"]
        print(
            f"[experiments] run-length control: n={s['n']} reps for half-width "
            f"{s['half_width']:.4f} (target 0.005), mean={s['mean']:.4f}"
        )
    return out


if __name__ == "__main__":
    from . import figures  # local import: figure generation needs kaleido

    tables = run_all()
    figures.generate_all(tables)
    ext = run_extension()
    figures.generate_extension(ext)
    print("[experiments] done — CSVs in results/, figures in report/figures/")
