# Stochastic Project — Prediction Market Simulator + Interactive Dashboard

Final project for SHBI-GB.7301 (Stochastic Modeling & Simulation, NYU Summer 2026).

We simulate a Polymarket/Kalshi-style binary prediction market with a hidden true
probability, a noisy observed price, and settlement at the horizon, then evaluate
EMA-threshold trading policies against buy-and-hold and never-trade benchmarks.

## One-command run (Windows, macOS, Linux)

```bash
python run.py
```

That single command creates a local virtual environment, installs all
dependencies, runs the 37-test validation suite, and opens the interactive
dashboard in your browser. On **Windows** you can simply double-click
`run.bat`; on macOS/Linux `./run.sh` does the same. Useful flags:
`--experiments` regenerates every CSV and figure from the master seed,
`--slides` serves the presentation deck instead, `--no-dashboard` stops
after the tests. Requires only Python 3.11+ on the PATH.

## Manual setup (equivalent)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the test suite:

```bash
pytest
```

Launch the interactive dashboard:

```bash
streamlit run dashboard/app.py
```

Reproduce all experiment sweeps (writes CSVs to `results/` and figures to `report/figures/`):

```bash
python -m src.experiments
```

## Headline result

With realistic observation noise (σ_p ≈ 0.05), the best EMA-threshold policy
beats buy-and-hold with CI-significance at **every** mispricing-persistence
level κ ∈ [0.05, 1] — even with a 2¢ per-trade cost. The edge peaks at
moderate persistence (κ ≈ 0.2–0.3, ≈ +\$0.10 per \$1 contract) and vanishes
only when observation noise vanishes: **noise creates the edge; persistence
shapes it.** All numbers with 95% CIs in [results/summary.md](results/summary.md)
(master seed 20260812); analysis walkthrough in
[notebooks/analysis.ipynb](notebooks/analysis.ipynb).

**Optional extension (default off):** a "news jumps" toggle in the dashboard
adds rare zero-mean shocks to the hidden truth via Poisson arrivals
(Bernoulli per period). It is off by default and consumes no randomness when
off, so all reported results use the professor-approved model unchanged
(guarded by a golden-value test; see `results/review_log.md`).

## Layout

See [PROJECT.md](PROJECT.md) for the full specification, model definition, and build plan.

- `src/model.py` — three-layer simulation engine (hidden probability, observed price, settlement)
- `src/policies.py` — trading policies (EMA-threshold family, buy-and-hold, never-trade)
- `src/experiments.py` — batch runs, confidence intervals, run-length control, sensitivity sweeps
- `src/calibration.py` — Polymarket data fetch + parameter estimation (with offline fallback)
- `src/validation.py` — closed-form sanity checks backing the pytest suite
- `dashboard/app.py` — Streamlit dashboard (single path explorer, policy lab, policy grid, sensitivity, about)
- `tests/test_model.py` — validation checks from Section 7 of PROJECT.md
- `results/` — saved experiment outputs; `report/figures/` — exported figures
