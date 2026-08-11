"""Build and execute notebooks/analysis.ipynb from the saved experiment CSVs.

Run from the repo root:  .venv/bin/python notebooks/build_notebook.py
Committed so the notebook is regenerable; the executed .ipynb is what the
report figures quote.
"""

from __future__ import annotations

from pathlib import Path

import nbformat as nbf
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parent.parent

nb = nbf.v4.new_notebook()
cells = []

md = nbf.v4.new_markdown_cell
code = nbf.v4.new_code_cell

cells.append(md(
    "# Prediction Market Simulator — Analysis\n"
    "SHBI-GB.7301 final project. This notebook reproduces the report's tables "
    "and figures from the saved experiment outputs in `results/` "
    "(master seed **20260812**, n = 20,000 replications per point).\n\n"
    "Regenerate the CSVs first if needed: `python -m src.experiments`."
))

cells.append(code(
    "import sys\n"
    "from pathlib import Path\n"
    "sys.path.insert(0, str(Path.cwd().parent))\n\n"
    "import numpy as np\n"
    "import pandas as pd\n"
    "import plotly.io as pio\n\n"
    "pd.set_option('display.float_format', lambda v: f'{v:,.4f}')\n"
    "RESULTS = Path.cwd().parent / 'results'\n"
    "tables = {p.stem: pd.read_csv(p) for p in sorted(RESULTS.glob('*.csv'))}\n"
    "sorted(tables)"
))

cells.append(md(
    "## 1. Policy comparison at the baseline market\n"
    "Variant B, κ = 0.3, σ_p = 0.05, σ_q = 0.02, T = 100, no costs. "
    "Each row reports the professor's three measures + the 95% CI, and the "
    "paired difference vs buy-and-hold on common random numbers (Lecture 7)."
))

cells.append(code(
    "comp = tables['policy_comparison_variantB_kappa03']\n"
    "comp[['policy','mean_profit','ci_low','ci_high','p_loss',\n"
    "      'mean_loss_given_loss','diff_vs_bh','beats_bh']]"
))

cells.append(md(
    "**Reading it:** every EMA cell except (α=0.6, δ=0.10) — which almost "
    "never trades — significantly beats buy-and-hold here. The winner is "
    "EMA(α=0.1, δ=0.10): slow smoothing plus a wide entry threshold waits for "
    "large, persistent dips."
))

cells.append(md(
    "## 2. Headline: how much persistence does an EMA trader need?\n"
    "Best-cell edge over buy-and-hold per (κ, cost); `any_ema_beats_bh` marks "
    "CI-significance of at least one grid cell."
))

cells.append(code(
    "head = tables['headline_kappa']\n"
    "head[['kappa','cost','best_policy','best_mean_profit','bh_mean_profit',\n"
    "      'diff_vs_bh','diff_ci_low','diff_ci_high','any_ema_beats_bh']]"
))

cells.append(code(
    "import plotly.graph_objects as go\n"
    "fig = go.Figure()\n"
    "for c, color in [(0.0, '#2a78d6'), (0.01, '#eb6834'), (0.02, '#1baf7a')]:\n"
    "    d = head[head['cost'] == c].sort_values('kappa')\n"
    "    fig.add_scatter(x=d['kappa'], y=d['diff_vs_bh'], name=f'cost = {c:.2f}',\n"
    "                    mode='lines+markers', line=dict(color=color, width=2),\n"
    "                    error_y=dict(type='data',\n"
    "                                 array=d['diff_ci_high'] - d['diff_vs_bh']))\n"
    "fig.add_hline(y=0, line=dict(dash='dot', color='#898781'))\n"
    "fig.update_layout(title='Best EMA edge over buy-and-hold vs kappa (95% CI)',\n"
    "                  xaxis_title='kappa (adjustment speed; 1 = variant A)',\n"
    "                  yaxis_title='paired profit difference per contract',\n"
    "                  template='plotly_white', height=420)\n"
    "fig.show(renderer='png')"
))

cells.append(md(
    "**Answer to the headline question:** at σ_p = 0.05 the market does *not* "
    "need any persistence — the best EMA cell beats buy-and-hold at every "
    "κ ∈ [0.05, 1], even at a 2¢ per-trade cost. The edge *peaks* at moderate "
    "persistence (κ ≈ 0.2–0.3, ≈ +\\$0.10 per \\$1 contract): slow enough "
    "adjustment that dips persist long enough to catch, fast enough that the "
    "mispricing still corrects before settlement. At κ = 0.05 the correction "
    "is slower than the horizon and the edge shrinks."
))

cells.append(md(
    "## 3. The interaction that actually drives the answer: noise × persistence\n"
    "The κ×σ_p grid (fixed cost 0.01) shows exploitability is created by "
    "observation noise and only *shaped* by persistence — with σ_p = 0 there "
    "is nothing to exploit at any κ (zero-noise sweep row), and the edge "
    "grows monotonically in σ_p at every κ."
))

cells.append(code(
    "inter = tables['headline_interaction']\n"
    "pivot = inter.pivot(index='sigma_p', columns='kappa', values='diff_vs_bh')\n"
    "sig = inter.pivot(index='sigma_p', columns='kappa', values='any_ema_beats_bh')\n"
    "print('best EMA edge over BH (per contract):')\n"
    "display(pivot.round(3))\n"
    "print('CI-significant in every cell:', bool(sig.all().all()))"
))

cells.append(md(
    "## 4. Sensitivity sweeps and costs"
))

cells.append(code(
    "sw = tables['sweep_sigma_p']\n"
    "ema = sw[sw['alpha'].notna()]\n"
    "best = ema.loc[ema.groupby('sigma_p')['diff_vs_bh'].idxmax()]\n"
    "best[['sigma_p','policy','mean_profit','diff_vs_bh','beats_bh']]"
))

cells.append(code(
    "sc = tables['sweep_cost']\n"
    "ema_c = sc[sc['alpha'].notna()]\n"
    "best_c = ema_c.loc[ema_c.groupby('cost')['mean_profit'].idxmax()]\n"
    "bh_c = sc[sc['policy'] == 'Buy-and-hold'][['cost','mean_profit']]\n"
    "best_c[['cost','policy','mean_profit','p_loss','beats_bh']].merge(\n"
    "    bh_c, on='cost', suffixes=('_best_ema', '_bh'))"
))

cells.append(md(
    "## 5. Run-length control (Lecture 3)\n"
    "Replications needed for a ±0.005 CI half-width on the κ = 0.2 headline "
    "cell — the doubling schedule from the course."
))

cells.append(code(
    "tables['run_length_control']"
))

cells.append(md(
    "## 6. Validation evidence (Section 7)\n"
    "The same checks the pytest suite asserts, shown numerically."
))

cells.append(code(
    "from src.validation import (martingale_check, calibration_check,\n"
    "                            seed_reproducibility_check)\n"
    "m = martingale_check()\n"
    "print(f\"martingale: mean q_T = {m['mean_qT']:.4f} vs q0 = {m['q0']} \"\n"
    "      f\"(SE {m['se_qT']:.4f}); settle freq = {m['settle_freq']:.4f} \"\n"
    "      f\"(SE {m['se_settle']:.4f})\")\n"
    "print('calibration grid:')\n"
    "display(pd.DataFrame(calibration_check()))\n"
    "print('seed check:', seed_reproducibility_check())"
))

cells.append(md(
    "## 7. Extension: the full model-case matrix and the news frontier\n"
    "Clearly-labelled results **beyond the approved model** (which is the "
    "λ = 0 row/case everywhere): variant A/B × Poisson news jumps on/off, "
    "then the jump-rate sweep. The approved-model headline results above are "
    "untouched by these."
))

cells.append(code(
    "cases = tables['model_case_matrix']\n"
    "cases[['case','best_policy','best_mean_profit','bh_mean_profit',\n"
    "       'diff_vs_bh','diff_ci_low','diff_ci_high','best_beats_bh']]"
))

cells.append(code(
    "js = tables['sweep_jump_rate']\n"
    "js = js.assign(erosion_vs_lambda0=1 - js['diff_vs_bh'] / js['diff_vs_bh'].iloc[0])\n"
    "js[['jump_rate','best_policy','diff_vs_bh','diff_ci_low','diff_ci_high',\n"
    "    'erosion_vs_lambda0','any_ema_beats_bh']]"
))

cells.append(md(
    "**Reading it:** the edge survives in all four model worlds at λ = 0.05 "
    "but news is expensive — the paired edge decays roughly linearly in λ "
    "(−24% at one event per 20 periods, −62% at one per 5). Under variant A "
    "with jumps the winning cell shifts from slow (α=0.1) to fast (α=0.6) "
    "smoothing: when the truth can jump, a long-memory EMA compares prices "
    "against a stale anchor. Mechanism figure: `report/figures/fig_jump_path.png`."
))

cells.append(md(
    "## 8. Real-data calibration (scope: inputs only)\n"
    "Bundled Polymarket samples and their implied model parameters — evidence "
    "that the simulator defaults (σ_q ≈ 0.02 per step) are realistic. We do "
    "not fit or backtest on real data."
))

cells.append(code(
    "from src.calibration import list_samples, load_sample, estimate_params\n"
    "rows = []\n"
    "for name in list_samples():\n"
    "    md_ = load_sample(name)\n"
    "    est = estimate_params(md_.prices)\n"
    "    rows.append({'market': md_.question[:60], 'n_obs': est['n_obs'],\n"
    "                 'q0': est['q0'], 'sigma_q_hat': est['sigma_q'],\n"
    "                 'sigma_p_hat': est['sigma_p']})\n"
    "pd.DataFrame(rows)"
))

nb["cells"] = cells
nb["metadata"]["kernelspec"] = {
    "display_name": "Python 3", "language": "python", "name": "python3",
}

out = ROOT / "notebooks" / "analysis.ipynb"
client = NotebookClient(nb, timeout=300, resources={"metadata": {"path": str(ROOT / "notebooks")}})
client.execute()
nbf.write(nb, out)
print(f"executed and wrote {out}")
