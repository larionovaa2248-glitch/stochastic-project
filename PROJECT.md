# Stochastic Project: Prediction Market Simulator + Interactive Dashboard

> **Instruction to Claude Code:** Create a new git repository named `stochastic-project` and do all work inside it. Initialize with this file at the repo root as `PROJECT.md`. Commit in small, labeled increments as you complete each phase.

---

## 1. What This Is

Final project for SHBI-GB.7301 (Stochastic Modeling & Simulation, NYU Summer 2026). We simulate a prediction market (Polymarket/Kalshi style binary contracts) and evaluate trading policies. The professor approved this exact model structure, so **do not change the model design** — build it as specified in Section 3.

Deliverables due August 12:
1. Final report (PDF)
2. Simulation model (code)
3. Presentation slides
4. **Interactive dashboard** (our differentiator for the 20% presentation-quality grade)

Grading rubric: problem formulation 20%, model implementation and simulation design 30%, analysis and interpretation 30%, presentation quality 20%.

---

## 2. Repo Layout

```
stochastic-project/
├── PROJECT.md                  # this file
├── README.md                   # quickstart: install, run tests, launch dashboard
├── requirements.txt            # numpy, pandas, scipy, streamlit, plotly, pytest, requests
├── src/
│   ├── model.py                # the three-layer simulation engine (Section 3)
│   ├── policies.py             # trading rules (Section 4)
│   ├── experiments.py          # batch runs, CIs, run-length control (Section 5)
│   ├── calibration.py         # pull real Polymarket data to set default params (Section 6)
│   └── validation.py           # closed-form sanity checks (Section 7)
├── dashboard/
│   └── app.py                  # Streamlit dashboard (Section 8)
├── tests/
│   └── test_model.py           # pytest suite (Section 7)
├── notebooks/
│   └── analysis.ipynb          # figures for the report
├── results/                    # saved experiment outputs (CSV/parquet)
└── report/
    └── figures/                # exported PNGs for report and slides
```

---

## 3. The Model (LOCKED — professor approved this structure)

Three layers, simulated in order each period `t = 0, 1, ..., T`:

### Layer 1: Hidden true probability `q_t`
- Starts at `q_0` (user input, default 0.40).
- Evolves as a bounded random walk: `q_{t+1} = clip(q_t + sigma_q * sqrt(q_t * (1 - q_t)) * Z_t, eps, 1 - eps)` where `Z_t ~ N(0,1)` iid, `eps = 0.001`.
- The `sqrt(q(1-q))` term shrinks steps near the barriers so the probability stays in (0,1) naturally, not just via clipping.
- The trader NEVER observes this process.

### Layer 2: Observed market price `p_t`
Two variants, both required:
- **Variant A (iid noise):** `p_t = clip(q_t + eta_t, 0.01, 0.99)` with `eta_t ~ N(0, sigma_p^2)` iid.
- **Variant B (partial adjustment / persistent mispricing):** `p_t = clip(p_{t-1} + kappa * (q_t - p_{t-1}) + eta_t, 0.01, 0.99)` with `kappa` in (0,1]. Small `kappa` = mispricings persist = smoothing rules have something to exploit. `kappa = 1` recovers Variant A.

### Layer 3: Settlement
- At `t = T`: outcome `Y ~ Bernoulli(q_T)`. Contract pays `$1` if `Y = 1`, else `$0`.
- Profit per unit held = payout − entry price (− transaction cost if enabled).

**Random number generation:** use `numpy.random.Generator` with an explicit seed everywhere. All randomness flows through inverse-transform or standard normal draws (course requirement: cite Lecture 2 inverse transform method in comments where applicable).

---

## 4. Trading Policies

Implement in `src/policies.py`, each as a class with a common interface `decide(price_history) -> action`:

1. **EMA-threshold (the main policy family):** fair-value estimate `f_t = alpha * p_t + (1 - alpha) * f_{t-1}`. Buy 1 unit if `f_t - p_t > delta` (price looks cheap vs smoothed estimate). Optionally close/stay out if `p_t - f_t > delta`. Hold to settlement.
   - Grid: `alpha ∈ {0.1, 0.3, 0.6}` × `delta ∈ {0.02, 0.05, 0.10}` = 9 policies.
2. **Buy-and-hold benchmark:** buy at `t=0`, hold to settlement. Ignores the path.
3. **Never-trade benchmark:** profit 0 always (sanity floor).

Keep the interface generic so the dashboard can construct a policy from slider values.

---

## 5. Experiments (`src/experiments.py`)

- `run_batch(params, policy, n_reps, seed)` → per-replication profits.
- Report per policy: **expected profit, P(loss), mean loss given loss, 95% CI on expected profit** (CLT-based; these three measures + CI are explicitly what the professor asked for).
- **Run-length control:** function that increases `n_reps` until the CI half-width falls below a user-set tolerance (course Lecture 3 material — must be present and cited in comments).
- Sensitivity sweeps (save results to `results/` as CSV):
  - vary `sigma_p` (market noisiness),
  - vary `kappa` (mispricing persistence),
  - add per-trade cost `c ∈ {0, 0.01, 0.02}`.
- Key headline experiment: **how much persistence (how small a kappa) does the market need before any EMA policy beats buy-and-hold?**

---

## 6. Real Data Calibration (`src/calibration.py`)

Purpose: choose realistic default parameters, and give the dashboard a "load a real market" feature.

- Use Polymarket's public **Gamma API** (`https://gamma-api.polymarket.com`) and **CLOB price history** endpoint (`https://clob.polymarket.com/prices-history`). No API key needed for reads. Handle failures gracefully — if endpoints have changed, degrade to bundled sample CSVs (commit 3–5 example price series into `results/sample_markets/`).
- Functions:
  - `fetch_market(slug_or_url)` → metadata + price series. Accept a full Polymarket URL pasted by the user and parse the slug out of it.
  - `estimate_params(price_series)` → implied `sigma` estimates (realized volatility of the series, mapped onto model params).
- **Scope guard:** calibration sets inputs; we do NOT fit or backtest the model on real data. That is out of scope and the report should say so.

---

## 7. Validation & Tests (`src/validation.py`, `tests/`)

The 30% implementation grade hinges on demonstrable correctness. Required checks, each as a pytest:

1. **Zero-noise check:** `sigma_p = 0, kappa = 1` → price equals hidden probability exactly; EMA with `alpha=1, delta=0` never finds a mispricing; all EMA profits ≈ buy-and-hold.
2. **Martingale check:** with the Layer-1 walk, sample mean of `q_T` across many reps ≈ `q_0` (CI covers it). Settlement frequency ≈ `q_0`.
3. **Calibration check:** contracts starting at `q_0 = x` settle YES a fraction ≈ `x` of the time, across a grid of `x` values.
4. **No-lookahead check:** shift the price series by one period inside a policy and confirm results change — proves policies only use past data. (Simplest: assert the policy interface literally cannot see `q_t` or future prices.)
5. **Seed reproducibility:** same seed → identical results.

`pytest` must pass before the dashboard phase starts.

---

## 8. Interactive Dashboard (`dashboard/app.py`) — Streamlit

This is the user-facing showpiece. Design for a classmate or the professor to play with during the presentation. Launch with `streamlit run dashboard/app.py`.

### Sidebar controls (all live)
- **Market setup:** starting probability `q_0`, horizon `T` (periods), hidden volatility `sigma_q`, noise `sigma_p`, persistence `kappa`, variant A/B toggle.
- **Trading policy:** smoothing `alpha` slider, threshold `delta` slider, per-trade cost, position size.
- **Simulation:** number of replications, seed, run-length-control tolerance toggle.
- **Load real market:** text box to paste a Polymarket URL → fetch its history, overlay it on simulated paths, and prefill `q_0` and volatility from it. Show market question + link. Cache API responses (`st.cache_data`).

### Main panel tabs
1. **Single Path Explorer:** one simulated contract; three lines on one chart — hidden `q_t` (dashed, "the truth you can't see"), observed `p_t`, EMA `f_t`; markers where the policy bought/sold; settlement outcome and profit shown as a big colored metric. Button: "resimulate" (new seed).
2. **Policy Lab:** run N replications for the current slider policy vs buy-and-hold; show expected profit with 95% CI error bars, P(loss), profit distribution histogram. This is where users "play with assumptions and see return."
3. **Policy Grid:** heatmap of expected profit over the 3×3 (alpha, delta) grid at current market params, with the CI-significant winner highlighted. Second heatmap for P(loss).
4. **Sensitivity Explorer:** line charts of expected profit vs `sigma_p` and vs `kappa` for the current policy and buy-and-hold — makes the headline finding visual.
5. **About / Model:** a plain-language explanation of the three layers (crib from the proposal), the rubric mapping, and team names.

### Dashboard implementation notes
- Plotly for charts (hover values matter during a live demo).
- Keep every interaction under ~2 seconds at default settings: vectorize with NumPy (simulate all replications as one 2-D array, no Python loops over paths), cap default reps at ~2,000 with a "high precision" toggle.
- Progress spinner + seeded determinism so a demo is repeatable.
- Graceful behavior if Polymarket API is unreachable (offline demo must still work end to end).

---

## 9. AI Agents / Claude Code Sub-Agent Plan

Run this project with specialized sub-agents (Claude Code Task tool), each with a narrow charter. Suggested set:

| Agent | Charter | Definition of done |
|---|---|---|
| **model-engineer** | Implement `model.py`, `policies.py` exactly per Sections 3–4. No creative liberties with the math. | All functions typed, docstrings cite the relevant lecture, vectorized over replications. |
| **test-engineer** | Write `tests/test_model.py` per Section 7 BEFORE or alongside the model (red/green). Adversarial mindset: try to catch lookahead bias and barrier bugs. | `pytest` green; each Section-7 check is a named test. |
| **experiments-runner** | Implement `experiments.py`, run all sweeps, save CSVs to `results/`, generate the report figures into `report/figures/`. | CSVs + PNGs exist; headline kappa finding reproduced with seed documented. |
| **data-engineer** | Implement `calibration.py`, handle Polymarket API quirks, bundle fallback sample CSVs. | `fetch_market()` works on a live URL AND offline fallback path tested. |
| **dashboard-builder** | Build `dashboard/app.py` per Section 8. Owns UX polish. | All 5 tabs functional; cold start < 5 s; offline mode works. |
| **reviewer** | After each phase, review diffs for correctness vs this spec, statistical validity (CI math, seed hygiene), and rubric coverage. Blocks merge on model deviations. | Written review notes appended to `results/review_log.md`. |

Orchestration rules:
- Phases run in order (Section 10); test-engineer and model-engineer work in parallel within Phase 1.
- Any agent that believes the spec is wrong must flag it in `results/review_log.md`, not silently "fix" it — the model is professor-approved.
- Every phase ends with a git commit and a one-paragraph summary in the commit message.

---

## 10. Build Order

1. **Phase 0 — scaffold (30 min):** repo `stochastic-project`, layout above, `requirements.txt`, README stub, empty modules with signatures. Commit.
2. **Phase 1 — engine + tests:** Sections 3, 4, 7. `pytest` green. Commit.
3. **Phase 2 — experiments:** Section 5 sweeps run end to end; results saved. Commit.
4. **Phase 3 — data:** Section 6 calibration + fallback samples. Commit.
5. **Phase 4 — dashboard:** Section 8 complete, demo-ready. Commit.
6. **Phase 5 — outputs:** export report figures, draft README quickstart, generate a `results/summary.md` with the numeric headline results (expected profit tables with CIs) that we will paste into the report. Commit.

If time-boxed, priorities are: Phase 1 > Phase 2 > Phase 4 > Phase 3 > Phase 5. The dashboard with simulated data only is still a complete project; the Polymarket link-in is a bonus.

---

## 11. Constraints & Style

- Python 3.11+, NumPy/pandas/SciPy/Streamlit/Plotly only (no heavy ML deps).
- Every stochastic function takes an explicit `rng: numpy.random.Generator`.
- Comments cite course lectures where a technique comes from (Lectures 2, 3, 7, 8) — this feeds the report and shows rubric coverage.
- No look-ahead anywhere in policy code. This is the one bug that would invalidate the whole analysis.
- Plain-language docstrings — teammates who don't code need to follow the logic.
- Keep functions small; the report will include code excerpts.

## 12. Nice-to-haves (only if everything above is done)

- "Story mode" in the dashboard: a guided walkthrough that animates one path period by period.
- Compare two policies side by side in Policy Lab.
- Export any tab's chart as PNG for slides with one click.
- A `results/slides_outline.md` drafted from the experiment results.
