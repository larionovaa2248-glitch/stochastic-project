# Presentation Outline (drafted from the experiment results)

Target: ~10 minutes + live dashboard demo. Figures referenced from
`report/figures/`; numbers from `results/summary.md` (seed 20260812).

1. **The question** — Can a simple smoothing rule make money in a prediction
   market, and how much market "sluggishness" does it need?
   (Rubric: problem formulation.)
2. **The model in one picture** — `fig_single_path.png`: hidden truth q_t
   (dashed), noisy price p_t, EMA estimate f_t, one buy, settlement.
   Three layers: bounded random walk → variant A/B price → Bernoulli(q_T)
   payout. Emphasize: the trader never sees q_t. (Rubric: model.)
3. **Why you can trust the code** — 31 tests: zero-noise limit, martingale,
   settlement calibration, no-lookahead (probe-policy canary through the real
   harness), seed reproducibility. One slide, five bullets.
   (Rubric: implementation.)
4. **The policy lab** — EMA-threshold family on a 3×3 (alpha, delta) grid vs
   buy-and-hold and never-trade; all comparisons paired on common random
   numbers. `fig_grid_profit.png` + `fig_grid_ploss.png`: winner
   EMA(0.1, 0.10), E[profit] +0.10 vs BH ≈ 0 at the baseline.
5. **Headline result** — `fig_headline_kappa.png`: the edge exists at EVERY
   kappa, peaks at kappa ≈ 0.2–0.3, survives 2¢ costs. Then the twist,
   `fig_headline_interaction.png`: noise creates the edge (nothing at
   sigma_p = 0), persistence only shapes it. (Rubric: analysis.)
6. **Statistical discipline** — `fig_run_length.png`: run-length control to a
   ±0.005 CI (64,000 reps); every claim carries a 95% CI.
7. **Reality check** — real Polymarket data sets q0 and sigma_q
   (five bundled markets, sigma_q ≈ 0.002–0.019/step ⇒ default 0.02 is
   realistic). Scope guard: inputs only, no backtesting.
8. **Live demo** — dashboard: (a) resimulate a single path, (b) Policy Lab
   verdict banner flips as delta moves, (c) load the NVIDIA market and
   prefill, (d) Sensitivity Explorer. Offline fallback if the venue Wi-Fi
   dies.
9. **Limitations & what we'd do next** — model is stylized (no order book,
   no price impact, binary only); kappa/sigma_p not identified separately
   from real hourly data; edge assumes the market doesn't learn.
10. **Takeaway** — "In this model, mispricing noise is the profit source;
    persistence just decides how easy it is to harvest. Quantified with CIs,
    reproducible with one seed."
