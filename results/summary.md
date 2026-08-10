# Numeric Results Summary

Everything below is reproducible with **master seed 20260812**, n = **20,000**
replications per parameter point (`python -m src.experiments`). CIs are
CLT-based 95% intervals (Lecture 3); policy-vs-benchmark comparisons are
paired differences on common random numbers (Lecture 7). Baseline market:
q0 = 0.40, T = 100, sigma_q = 0.02, sigma_p = 0.05, variant B.

## Headline: how much persistence does an EMA trader need?

**Answer: none — at realistic noise levels the edge exists at every kappa;
persistence shapes the edge, observation noise creates it.**

- The best EMA cell beats buy-and-hold with CI-significance at **every**
  kappa in {0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0} and every per-trade cost in
  {0, 0.01, 0.02}. Winner in almost every cell: **EMA(alpha=0.1, delta=0.1)**.
- The edge **peaks at moderate persistence**, kappa ≈ 0.2–0.3:
  paired difference vs buy-and-hold **+0.1023 per $1 contract**,
  95% CI [+0.1007, +0.1038] (kappa = 0.3, cost 0).
  Intuition: dips must persist long enough to be caught (kappa not too big)
  but still correct before settlement (kappa not too small).
- Even in the worst case for the trader — no persistence (kappa = 1) and a
  2¢ cost per trade — the edge is **+0.0939** [+0.0913, +0.0965]: the EMA
  policy earns +0.0705 while buy-and-hold loses −0.0233.
- **The real driver is noise, not persistence.** With sigma_p = 0 no EMA
  policy beats buy-and-hold (max |paired diff| 0.0027, not significant);
  across the kappa × sigma_p grid (cost 0.01) every one of the 28 cells is
  CI-significant, with the edge rising from +0.008 (sigma_p = 0.01) to
  +0.140 (sigma_p = 0.08, kappa = 1).

## Policy comparison at the baseline (variant B, kappa = 0.3, cost 0)

| Policy | E[profit] | 95% CI | P(loss) | E[loss \| loss] | Beats BH? |
|---|---|---|---|---|---|
| **EMA(0.1, 0.10) — winner** | **+0.1015** | [+0.0949, +0.1082] | 0.588 | −0.289 | **yes** (+0.1034 paired, CI [+0.1020, +0.1049]) |
| EMA(0.3, 0.10) | +0.0629 | [+0.0580, +0.0678] | 0.315 | −0.259 | yes |
| EMA(0.3, 0.05) | +0.0614 | [+0.0546, +0.0682] | 0.602 | −0.336 | yes |
| EMA(0.6, 0.05) | +0.0600 | [+0.0545, +0.0655] | 0.400 | −0.295 | yes |
| EMA(0.1, 0.05) | +0.0593 | [+0.0525, +0.0662] | 0.602 | −0.338 | yes |
| EMA(0.1, 0.02) | +0.0372 | [+0.0304, +0.0440] | 0.602 | −0.361 | yes |
| EMA(0.6, 0.02) | +0.0366 | [+0.0298, +0.0434] | 0.602 | −0.361 | yes |
| EMA(0.3, 0.02) | +0.0313 | [+0.0245, +0.0381] | 0.602 | −0.366 | yes |
| EMA(0.6, 0.10) | −0.0000 | [−0.0001, +0.0000] | 0.000 | −0.180 | no (rarely trades) |
| Buy-and-hold | −0.0019 | [−0.0087, +0.0049] | 0.602 | −0.400 | — |
| Never-trade | 0 | — | 0 | — | no |

Full table: `policy_comparison_variantB_kappa03.csv` (and `_variantA.csv`).

## Costs

Per-trade cost shifts levels but not the ranking: at the baseline the best
EMA cell earns +0.0922/+0.0825 at c = 0.01/0.02 while buy-and-hold drops to
−0.0119/−0.0219 (`sweep_cost.csv`). The paired edge actually *widens*
slightly with cost because the EMA policy sometimes stays out and saves the
fee.

## Noise sensitivity (kappa = 1)

| sigma_p | best-cell paired edge vs BH | significant? |
|---|---|---|
| 0.00 | +0.0027 | no |
| 0.01 | +0.0121 | yes |
| 0.02 | +0.0331 | yes |
| 0.05 | +0.0913 | yes |
| 0.08 | +0.1385 | yes |
| 0.12 | +0.2061 | yes |

## Run-length control (Lecture 3)

Target: CI half-width ≤ 0.005 on E[profit] for EMA(0.3, 0.05) at kappa = 0.2.
Doubling schedule: 1,000 → 0.0307; 2,000 → 0.0215; 4,000 → 0.0152;
8,000 → 0.0108; 16,000 → 0.0076; 32,000 → 0.0054; **64,000 → 0.0038 ✓**
(final estimate +0.0571 ± 0.0038). `run_length_control.csv`.

## Validation (Section 7) — all 31 tests green

- Zero noise: price = hidden probability exactly; EMA(1, 0) never trades;
  all grid policies' expected profits equal buy-and-hold's (paired CIs).
- Martingale: mean q_T = 0.3996 vs q0 = 0.40 (SE 0.0005); settlement
  frequency 0.4030 (SE 0.0035).
- Calibration grid: settlement frequency within 4 SE of q0 for
  q0 ∈ {0.10, 0.25, 0.50, 0.75, 0.90}.
- No-lookahead: future-price shocks cannot change pre-shock trades through
  the real evaluation harness (probe-policy canary); past shocks do.
- Seed reproducibility: identical batches from identical seeds.

## Real-data calibration (inputs only — no fitting/backtesting)

Five bundled Polymarket markets (fetched 2026-08-10, 418–743 hourly points):
implied sigma_q ≈ 0.002–0.019 per step, validating the simulator default
sigma_q = 0.02; implied iid observation noise on hourly closes is small
(sigma_p ≤ 0.002), so the interesting simulated regimes treat sigma_p as the
stress dimension. `sample_markets/`, estimates in `notebooks/analysis.ipynb`.
