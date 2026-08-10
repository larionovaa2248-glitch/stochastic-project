# Stochastic Project — Prediction Market Simulator + Interactive Dashboard

Final project for SHBI-GB.7301 (Stochastic Modeling & Simulation, NYU Summer 2026).

We simulate a Polymarket/Kalshi-style binary prediction market with a hidden true
probability, a noisy observed price, and settlement at the horizon, then evaluate
EMA-threshold trading policies against buy-and-hold and never-trade benchmarks.

## Quickstart

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
