"""Report figures (PROJECT.md Phase 2/5) — exported as PNGs into report/figures/.

Styling follows the course dataviz conventions: a small fixed categorical
palette assigned by entity (observed price = blue, hidden truth = orange,
EMA estimate = aqua; buy = green, sell = red), one axis per chart, a
diverging blue<->red scale only where sign matters (profit), a one-hue
sequential scale for magnitudes (P(loss)), recessive grid, direct labels.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .experiments import BASELINE, MASTER_SEED, FIGURES_DIR
from .model import MarketParams, simulate_market_seeded
from .policies import EMAThresholdPolicy, run_policy_path

# --- palette (light mode; validated set) -----------------------------------
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BLUE = "#2a78d6"    # slot 1 — observed price / primary series
ORANGE = "#eb6834"  # slot 2 — hidden truth / benchmark
AQUA = "#1baf7a"    # slot 3 — EMA estimate / third series
GREEN = "#008300"   # buy marker
RED = "#e34948"     # sell marker / diverging negative pole
DIVERGING = [[0.0, "#d03b3b"], [0.5, "#f0efec"], [1.0, "#2a78d6"]]  # loss<->gain
SEQ_BLUE = [[0.0, "#cde2fb"], [0.5, "#3987e5"], [1.0, "#0d366b"]]   # magnitude

FONT = dict(family="Helvetica, Arial, sans-serif", size=13, color=INK)


def _base_layout(title: str, xaxis_title: str, yaxis_title: str) -> go.Layout:
    return go.Layout(
        title=dict(text=title, font=dict(size=15, color=INK)),
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=FONT,
        xaxis=dict(title=xaxis_title, gridcolor=GRID, zerolinecolor=GRID, tickcolor=MUTED),
        yaxis=dict(title=yaxis_title, gridcolor=GRID, zerolinecolor="#c3c2b7", tickcolor=MUTED),
        legend=dict(orientation="h", yanchor="top", y=-0.22, x=0),
        margin=dict(l=70, r=30, t=60, b=120),
    )


def _save(fig: go.Figure, name: str, width: int = 900, height: int = 520) -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig.write_image(str(FIGURES_DIR / name), width=width, height=height, scale=2)
    print(f"[figures] wrote report/figures/{name}")


def fig_single_path(seed: int = MASTER_SEED + 5) -> go.Figure:
    """One simulated contract: hidden q (dashed), observed p, EMA f, trades."""
    params = replace(BASELINE, kappa=0.2, variant="B")
    paths = simulate_market_seeded(params, 1, seed)
    q, p, y = paths.q[0], paths.p[0], int(paths.y[0])
    pol = EMAThresholdPolicy(alpha=0.3, delta=0.05)
    profit, trades = run_policy_path(pol, p, y)
    # Recompute the EMA series for plotting (same recursion as the policy).
    f = np.empty_like(p)
    f[0] = p[0]
    for t in range(1, len(p)):
        f[t] = 0.3 * p[t] + 0.7 * f[t - 1]
    tt = np.arange(len(p))

    fig = go.Figure(layout=_base_layout(
        f"One contract, period by period (kappa={params.kappa}, settles "
        f"{'YES' if y else 'NO'}, EMA policy profit {profit:+.3f})",
        "period t", "probability / price",
    ))
    fig.add_scatter(x=tt, y=q, name="hidden truth q_t (never observable)",
                    line=dict(color=ORANGE, width=2, dash="dash"))
    fig.add_scatter(x=tt, y=p, name="observed market price p_t",
                    line=dict(color=BLUE, width=2))
    fig.add_scatter(x=tt, y=f, name="EMA fair-value estimate f_t (alpha=0.3)",
                    line=dict(color=AQUA, width=2))
    buys = [tr for tr in trades if tr.units > 0]
    sells = [tr for tr in trades if tr.units < 0]
    if buys:
        fig.add_scatter(x=[tr.t for tr in buys], y=[tr.price for tr in buys],
                        mode="markers", name="buy",
                        marker=dict(symbol="triangle-up", size=13, color=GREEN,
                                    line=dict(color=SURFACE, width=2)))
    if sells:
        fig.add_scatter(x=[tr.t for tr in sells], y=[tr.price for tr in sells],
                        mode="markers", name="sell",
                        marker=dict(symbol="triangle-down", size=13, color=RED,
                                    line=dict(color=SURFACE, width=2)))
    fig.add_scatter(x=[len(p) - 1], y=[float(y)], mode="markers", name="settlement",
                    marker=dict(symbol="star", size=15, color=INK))
    return fig


def fig_headline_kappa(headline: pd.DataFrame) -> go.Figure:
    """THE headline: best EMA edge over buy-and-hold vs kappa, per cost level."""
    fig = go.Figure(layout=_base_layout(
        "How much mispricing persistence does an EMA trader need?",
        "kappa (price adjustment speed; 1 = no persistence)",
        "best EMA policy profit minus buy-and-hold (per contract, 95% CI)",
    ))
    colors = {0.0: BLUE, 0.01: ORANGE, 0.02: AQUA}
    for c, color in colors.items():
        d = headline[headline["cost"] == c].sort_values("kappa")
        if d.empty:
            continue
        rgba = f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.15)"
        fig.add_scatter(x=pd.concat([d["kappa"], d["kappa"][::-1]]),
                        y=pd.concat([d["diff_ci_high"], d["diff_ci_low"][::-1]]),
                        fill="toself", fillcolor=rgba, line=dict(width=0),
                        showlegend=False, hoverinfo="skip")
        fig.add_scatter(x=d["kappa"], y=d["diff_vs_bh"], name=f"cost = {c:.2f}",
                        line=dict(color=color, width=2), mode="lines+markers",
                        marker=dict(size=8))
    fig.add_hline(y=0, line=dict(color=MUTED, width=1, dash="dot"))
    return fig


def fig_sigma_p_sweep(sweep: pd.DataFrame) -> go.Figure:
    """Expected profit vs market noisiness for the best EMA cell and BH."""
    ema = sweep[sweep["alpha"].notna()]
    best = ema.loc[ema.groupby("sigma_p")["mean_profit"].idxmax()].sort_values("sigma_p")
    bh = sweep[sweep["policy"] == "Buy-and-hold"].sort_values("sigma_p")
    fig = go.Figure(layout=_base_layout(
        "More market noise = more for a smoothing rule to exploit",
        "sigma_p (observation noise std dev)", "expected profit per contract (95% CI)",
    ))
    for d, name, color in ((best, "best EMA policy at each point", BLUE),
                           (bh, "buy-and-hold", ORANGE)):
        fig.add_scatter(x=d["sigma_p"], y=d["mean_profit"], name=name,
                        mode="lines+markers", line=dict(color=color, width=2),
                        marker=dict(size=8),
                        error_y=dict(type="data", visible=True,
                                     array=d["ci_high"] - d["mean_profit"],
                                     color=color, thickness=1.2, width=4))
    fig.add_hline(y=0, line=dict(color=MUTED, width=1, dash="dot"))
    return fig


def fig_cost_sweep(sweep: pd.DataFrame) -> go.Figure:
    """Expected profit by per-trade cost: best EMA vs buy-and-hold."""
    ema = sweep[sweep["alpha"].notna()]
    best = ema.loc[ema.groupby("cost")["mean_profit"].idxmax()].sort_values("cost")
    bh = sweep[sweep["policy"] == "Buy-and-hold"].sort_values("cost")
    fig = go.Figure(layout=_base_layout(
        "Transaction costs eat the edge",
        "per-trade cost c", "expected profit per contract (95% CI)",
    ))
    fig.add_bar(x=best["cost"], y=best["mean_profit"], name="best EMA policy",
                marker=dict(color=BLUE),
                error_y=dict(type="data", array=best["ci_high"] - best["mean_profit"],
                             color=INK, thickness=1.2, width=4))
    fig.add_bar(x=bh["cost"], y=bh["mean_profit"], name="buy-and-hold",
                marker=dict(color=ORANGE),
                error_y=dict(type="data", array=bh["ci_high"] - bh["mean_profit"],
                             color=INK, thickness=1.2, width=4))
    fig.update_layout(barmode="group", bargap=0.35)
    fig.update_xaxes(type="category")
    return fig


def _grid_matrix(comparison: pd.DataFrame, value_col: str) -> tuple[np.ndarray, list, list]:
    ema = comparison[comparison["alpha"].notna()]
    alphas = sorted(ema["alpha"].unique())
    deltas = sorted(ema["delta"].unique())
    M = np.full((len(alphas), len(deltas)), np.nan)
    for _, row in ema.iterrows():
        M[alphas.index(row["alpha"]), deltas.index(row["delta"])] = row[value_col]
    return M, alphas, deltas


def fig_grid_heatmaps(comparison: pd.DataFrame, suffix: str) -> tuple[go.Figure, go.Figure]:
    """3x3 (alpha, delta) heatmaps: expected profit (diverging) and P(loss)."""
    M, alphas, deltas = _grid_matrix(comparison, "mean_profit")
    lim = float(np.nanmax(np.abs(M))) or 1.0
    ema = comparison[comparison["alpha"].notna()]
    winner = ema.loc[ema["mean_profit"].idxmax()]
    win_sig = bool(winner["beats_bh"])

    f1 = go.Figure(layout=_base_layout(
        f"Expected profit over the policy grid ({suffix})",
        "delta (entry threshold)", "alpha (EMA smoothing)",
    ))
    f1.add_heatmap(z=M, x=[str(d) for d in deltas], y=[str(a) for a in alphas],
                   colorscale=DIVERGING, zmin=-lim, zmax=lim,
                   colorbar=dict(title="E[profit]"),
                   texttemplate="%{z:.3f}", textfont=dict(color=INK), xgap=2, ygap=2)
    # Outline the winning cell (shapes take category-INDEX coordinates, so
    # the border hugs the cell without covering its printed value).
    j, i = deltas.index(winner["delta"]), alphas.index(winner["alpha"])
    f1.add_shape(type="rect", x0=j - 0.5, x1=j + 0.5, y0=i - 0.5, y1=i + 0.5,
                 line=dict(color=INK, width=3))
    star_note = ("outlined cell = winner; its lead over buy-and-hold is "
                 "CI-significant" if win_sig else
                 "outlined cell = winner; lead over buy-and-hold NOT CI-significant")
    f1.add_annotation(xref="paper", yref="paper", x=0, y=1.06, showarrow=False,
                      text=star_note, font=dict(size=12, color=INK_2))
    f1.update_xaxes(type="category")
    f1.update_yaxes(type="category")

    P, _, _ = _grid_matrix(comparison, "p_loss")
    f2 = go.Figure(layout=_base_layout(
        f"P(loss) over the policy grid ({suffix})",
        "delta (entry threshold)", "alpha (EMA smoothing)",
    ))
    f2.add_heatmap(z=P, x=[str(d) for d in deltas], y=[str(a) for a in alphas],
                   colorscale=SEQ_BLUE, zmin=0, zmax=float(np.nanmax(P)) or 1.0,
                   colorbar=dict(title="P(loss)"),
                   texttemplate="%{z:.3f}", textfont=dict(color=SURFACE), xgap=2, ygap=2)
    f2.update_xaxes(type="category")
    f2.update_yaxes(type="category")
    return f1, f2


def fig_headline_interaction(interaction: pd.DataFrame) -> go.Figure:
    """(kappa, sigma_p) heatmap of the best EMA edge over buy-and-hold."""
    kappas = sorted(interaction["kappa"].unique())
    sigmas = sorted(interaction["sigma_p"].unique())
    M = np.full((len(sigmas), len(kappas)), np.nan)
    sig = np.zeros_like(M, dtype=bool)
    for _, r in interaction.iterrows():
        i, j = sigmas.index(r["sigma_p"]), kappas.index(r["kappa"])
        M[i, j] = r["diff_vs_bh"]
        sig[i, j] = bool(r["any_ema_beats_bh"])
    lim = float(np.nanmax(np.abs(M))) or 1.0
    fig = go.Figure(layout=_base_layout(
        f"Best EMA edge over buy-and-hold across (kappa, sigma_p), cost = "
        f"{interaction['cost'].iloc[0]:.2f} — X = not CI-significant",
        "kappa (adjustment speed)", "sigma_p (observation noise)",
    ))
    fig.add_heatmap(z=M, x=[str(k) for k in kappas], y=[str(s) for s in sigmas],
                    colorscale=DIVERGING, zmin=-lim, zmax=lim,
                    colorbar=dict(title="edge"),
                    texttemplate="%{z:.3f}", textfont=dict(color=INK), xgap=2, ygap=2)
    xs = [str(kappas[j]) for i in range(len(sigmas)) for j in range(len(kappas)) if not sig[i, j]]
    ys = [str(sigmas[i]) for i in range(len(sigmas)) for j in range(len(kappas)) if not sig[i, j]]
    if xs:
        fig.add_scatter(x=xs, y=ys, mode="markers", showlegend=False,
                        marker=dict(symbol="x-thin", size=18, color=INK,
                                    line=dict(color=INK, width=2)))
    fig.update_xaxes(type="category")
    fig.update_yaxes(type="category")
    return fig


def fig_profit_distribution(seed: int = MASTER_SEED + 6) -> go.Figure:
    """Profit distribution, best-cell EMA vs buy-and-hold, persistent market."""
    from .experiments import profits_on_paths
    from .policies import BuyAndHoldPolicy, buy_and_hold_profits

    params = replace(BASELINE, kappa=0.2, variant="B")
    paths = simulate_market_seeded(params, 20000, seed)
    ema = profits_on_paths(paths, EMAThresholdPolicy(0.3, 0.05), cost=0.01)
    bh = buy_and_hold_profits(paths, cost=0.01)
    fig = go.Figure(layout=_base_layout(
        "Profit distributions are bimodal — settlement is all or nothing "
        f"(kappa={params.kappa}, cost=0.01)",
        "profit per contract", "share of replications",
    ))
    fig.add_histogram(x=ema, name="EMA(alpha=0.3, delta=0.05)",
                      marker=dict(color=BLUE), opacity=0.65,
                      histnorm="probability", xbins=dict(size=0.05))
    fig.add_histogram(x=bh, name="buy-and-hold", marker=dict(color=ORANGE),
                      opacity=0.65, histnorm="probability", xbins=dict(size=0.05))
    fig.update_layout(barmode="overlay")
    return fig


def fig_run_length(rlc: pd.DataFrame) -> go.Figure:
    """Sequential run-length control: CI half-width shrinking toward tolerance."""
    fig = go.Figure(layout=_base_layout(
        "Run-length control: replications until the CI is tight enough (Lecture 3)",
        "total replications n", "95% CI half-width on expected profit",
    ))
    fig.add_scatter(x=rlc["n_total"], y=rlc["half_width"], name="CI half-width",
                    mode="lines+markers", line=dict(color=BLUE, width=2),
                    marker=dict(size=9))
    fig.add_hline(y=0.005, line=dict(color=RED, width=1.5, dash="dash"),
                  annotation_text="tolerance 0.005", annotation_font_color=INK_2)
    fig.update_xaxes(type="log")
    fig.update_yaxes(type="log")
    return fig


def generate_all(tables: dict[str, pd.DataFrame]) -> None:
    """Export every report figure from the experiment tables."""
    _save(fig_single_path(), "fig_single_path.png")
    _save(fig_headline_kappa(tables["headline_kappa"]), "fig_headline_kappa.png")
    _save(fig_sigma_p_sweep(tables["sweep_sigma_p"]), "fig_sigma_p_sweep.png")
    _save(fig_cost_sweep(tables["sweep_cost"]), "fig_cost_sweep.png")
    p1, p2 = fig_grid_heatmaps(tables["policy_comparison_variantB_kappa03"],
                               "variant B, kappa=0.3")
    _save(p1, "fig_grid_profit.png", width=700, height=560)
    _save(p2, "fig_grid_ploss.png", width=700, height=560)
    _save(fig_headline_interaction(tables["headline_interaction"]),
          "fig_headline_interaction.png", width=800, height=520)
    _save(fig_profit_distribution(), "fig_profit_distribution.png")
    _save(fig_run_length(tables["run_length_control"]), "fig_run_length.png")
