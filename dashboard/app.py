"""Interactive dashboard (PROJECT.md Section 8) — Streamlit.

Launch with:  streamlit run dashboard/app.py

Design goals from the spec: every control is live, every interaction stays
under ~2 seconds at default settings (vectorised batches, cached), a fixed
seed makes the demo repeatable, and the whole app works offline (bundled
sample markets stand in for the Polymarket API).
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import calibration as cal
from src.experiments import (
    compare_policies,
    paired_diff_vs_benchmark,
    profits_on_paths,
    run_until_precision,
    summarize,
)
from src.figures import (
    AQUA,
    BLUE,
    GREEN,
    GRID,
    INK,
    INK_2,
    MUTED,
    ORANGE,
    RED,
    SURFACE,
    _base_layout,
    fig_grid_heatmaps,
)
from src.model import MarketParams, simulate_market_seeded
from src.policies import BuyAndHoldPolicy, EMAThresholdPolicy, run_policy_path

st.set_page_config(page_title="Prediction Market Simulator", page_icon="🎲", layout="wide")


# ---------------------------------------------------------------------------
# Cached computation wrappers (primitives in, so st.cache_data hashes cheaply)
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def cached_paths(q0, T, sigma_q, sigma_p, kappa, variant, n_reps, seed,
                 jump_rate=0.0, jump_scale=0.15):
    params = MarketParams(q0=q0, T=T, sigma_q=sigma_q, sigma_p=sigma_p,
                          kappa=kappa, variant=variant,
                          jump_rate=jump_rate, jump_scale=jump_scale)
    return simulate_market_seeded(params, n_reps, seed)


@st.cache_data(show_spinner=False)
def cached_comparison(q0, T, sigma_q, sigma_p, kappa, variant, n_reps, seed, cost,
                      jump_rate=0.0, jump_scale=0.15):
    params = MarketParams(q0=q0, T=T, sigma_q=sigma_q, sigma_p=sigma_p,
                          kappa=kappa, variant=variant,
                          jump_rate=jump_rate, jump_scale=jump_scale)
    return compare_policies(params, n_reps, seed, cost)


@st.cache_data(show_spinner=False, ttl=600)
def cached_market(slug_or_url: str | None):
    """Polymarket fetch with graceful offline fallback (Section 6/8)."""
    md = cal.fetch_market_or_sample(slug_or_url)
    est = cal.estimate_params(md.prices)
    return {
        "question": md.question, "slug": md.slug, "url": md.url,
        "source": md.source, "prices": md.prices, "timestamps": md.timestamps,
        "est": est,
    }


def market_params_from_sidebar(s) -> MarketParams:
    return MarketParams(q0=s["q0"], T=s["T"], sigma_q=s["sigma_q"],
                        sigma_p=s["sigma_p"], kappa=s["kappa"], variant=s["variant"],
                        jump_rate=s["eff_jump_rate"], jump_scale=s["jump_scale"])


# ---------------------------------------------------------------------------
# Sidebar — all live controls (Section 8)
# ---------------------------------------------------------------------------

DEFAULTS = dict(q0=0.40, T=100, sigma_q=0.02, sigma_p=0.05, kappa=0.30,
                variant="B", alpha=0.30, delta=0.05, cost=0.00, unit=1,
                n_reps=2000, seed=42, jumps_on=False, jump_rate=0.04,
                jump_scale=0.20)

for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)
st.session_state.setdefault("resim_offset", 0)
st.session_state.setdefault("loaded_market", None)


def prefill_from_market(est: dict) -> None:
    """Callback: push calibrated values into the sidebar widgets."""
    st.session_state["q0"] = float(np.clip(round(est["q0"], 2), 0.01, 0.99))
    st.session_state["sigma_q"] = float(np.clip(round(est["sigma_q"], 3), 0.001, 0.10))
    if est["sigma_p"] > 0:
        st.session_state["sigma_p"] = float(np.clip(round(est["sigma_p"], 3), 0.0, 0.15))


with st.sidebar:
    st.title("🎲 Market Simulator")

    st.header("Market setup")
    st.slider("Starting probability q₀", 0.01, 0.99, key="q0", step=0.01,
              help="Where the hidden true probability starts at t=0.")
    st.slider("Horizon T (periods)", 20, 400, key="T", step=10)
    st.slider("Hidden volatility σ_q", 0.001, 0.10, key="sigma_q", step=0.001,
              format="%.3f", help="Step size of the unobservable truth q_t.")
    st.slider("Observation noise σ_p", 0.0, 0.15, key="sigma_p", step=0.005,
              format="%.3f", help="How noisily the market price tracks the truth.")
    st.radio("Price variant", ["A", "B"], key="variant", horizontal=True,
             help="A: price = truth + iid noise. B: price only partially "
                  "adjusts toward the truth each period (persistent mispricing).")
    st.slider("Persistence κ (variant B)", 0.05, 1.0, key="kappa", step=0.05,
              disabled=st.session_state["variant"] == "A",
              help="Price adjustment speed. κ=1 reproduces variant A; small κ "
                   "means mispricings decay slowly.")

    with st.expander("🗞️ News jumps (extension — default off)"):
        st.caption("Beyond the professor-approved model: rare big shocks to "
                   "the hidden truth, arriving as a Poisson process "
                   "(Bernoulli per period). Zero-mean, so settlement "
                   "calibration still holds. Off = the approved model, "
                   "bit-for-bit.")
        st.toggle("Enable news jumps", key="jumps_on")
        st.slider("News rate λ (events/period)", 0.01, 0.25, key="jump_rate",
                  step=0.01, disabled=not st.session_state["jumps_on"])
        st.slider("Jump size (std, before damping)", 0.05, 0.80,
                  key="jump_scale", step=0.05,
                  disabled=not st.session_state["jumps_on"])

    st.header("Trading policy (EMA-threshold)")
    st.slider("Smoothing α", 0.05, 1.0, key="alpha", step=0.05)
    st.slider("Entry threshold δ", 0.0, 0.20, key="delta", step=0.01)
    st.checkbox("Also exit when price looks rich", key="allow_exit", value=False)
    st.slider("Per-trade cost c", 0.0, 0.05, key="cost", step=0.005, format="%.3f")
    st.slider("Position size (units)", 1, 50, key="unit")

    st.header("Simulation")
    high_precision = st.toggle("High precision (20k reps)", value=False)
    st.slider("Replications", 100, 20000 if high_precision else 5000,
              key="n_reps", step=100)
    st.number_input("Seed", 0, 10**6, key="seed")
    use_rlc = st.toggle("Run-length control (Policy Lab)", value=False,
                        help="Keep adding replications until the CI half-width "
                             "falls below the tolerance (Lecture 3).")
    rlc_tol = st.slider("CI half-width tolerance", 0.002, 0.05, 0.01,
                        step=0.002, format="%.3f", disabled=not use_rlc)

    st.header("Load a real market")
    url_input = st.text_input("Polymarket URL or slug", "",
                              placeholder="paste a polymarket.com link…")
    sample_choice = st.selectbox("…or a bundled sample (offline)",
                                 ["(none)"] + cal.list_samples())
    if st.button("Fetch market", use_container_width=True):
        query = url_input.strip() or (sample_choice if sample_choice != "(none)" else None)
        if query is None:
            st.warning("Paste a URL or pick a sample first.")
        else:
            with st.spinner("Fetching…"):
                try:
                    if not url_input.strip() and sample_choice != "(none)":
                        md = cal.load_sample(sample_choice)
                        est = cal.estimate_params(md.prices)
                        st.session_state["loaded_market"] = {
                            "question": md.question, "slug": md.slug, "url": md.url,
                            "source": md.source, "prices": md.prices,
                            "timestamps": md.timestamps, "est": est,
                        }
                    else:
                        st.session_state["loaded_market"] = cached_market(query)
                except Exception as exc:  # noqa: BLE001 — surface, never crash
                    st.error(f"Could not load a market: {exc}")

    mkt = st.session_state["loaded_market"]
    if mkt:
        badge = "🟢 live" if mkt["source"] == "live" else "📦 bundled sample (offline)"
        st.markdown(f"**{mkt['question']}**  \n{badge} · {mkt['est']['n_obs']} points"
                    + (f" · [open ↗]({mkt['url']})" if mkt["url"] else ""))
        e = mkt["est"]
        st.caption(f"Implied: q₀≈{e['q0']:.2f} (now {e['q_last']:.2f}), "
                   f"σ_q≈{e['sigma_q']:.3f}, σ_p≈{e['sigma_p']:.3f} per step")
        st.button("Prefill q₀ and volatility from this market",
                  on_click=prefill_from_market, args=(e,), use_container_width=True)


S = {k: st.session_state[k] for k in DEFAULTS}
S["allow_exit"] = st.session_state.get("allow_exit", False)
# jump_rate=0 means the extension consumes no randomness at all (approved model)
S["eff_jump_rate"] = S["jump_rate"] if S["jumps_on"] else 0.0
params = market_params_from_sidebar(S)
policy = EMAThresholdPolicy(S["alpha"], S["delta"], S["allow_exit"])
POLICY_LABEL = f"EMA(α={S['alpha']:.2f}, δ={S['delta']:.2f})"


# ---------------------------------------------------------------------------
# Main panel tabs
# ---------------------------------------------------------------------------

tab_path, tab_lab, tab_grid, tab_sens, tab_about = st.tabs(
    ["📈 Single Path Explorer", "🧪 Policy Lab", "🗺️ Policy Grid",
     "🌡️ Sensitivity Explorer", "📖 About / Model"]
)


with tab_path:
    left, right = st.columns([4, 1])
    with right:
        if st.button("🔀 Resimulate", use_container_width=True):
            st.session_state["resim_offset"] += 1
        st.caption(f"seed {S['seed']} + path {st.session_state['resim_offset']}")

    path_seed = S["seed"] + 100_000 * st.session_state["resim_offset"]
    paths = cached_paths(S["q0"], S["T"], S["sigma_q"], S["sigma_p"],
                         S["kappa"], S["variant"], 1, path_seed,
                         S["eff_jump_rate"], S["jump_scale"])
    q, p, y = paths.q[0], paths.p[0], int(paths.y[0])
    profit, trades = run_policy_path(policy, p, y, S["cost"], S["unit"])

    # EMA series for the plot (same recursion the policy runs internally).
    f = np.empty_like(p)
    f[0] = p[0]
    for t in range(1, len(p)):
        f[t] = S["alpha"] * p[t] + (1 - S["alpha"]) * f[t - 1]

    fig = go.Figure(layout=_base_layout("", "period t", "probability / price"))
    tt = np.arange(len(p))
    fig.add_scatter(x=tt, y=q, name="hidden truth q_t — the truth you can't see",
                    line=dict(color=ORANGE, width=2, dash="dash"))
    if paths.jumps is not None and paths.jumps[0].any():
        jt = np.flatnonzero(paths.jumps[0]) + 1  # jump at t moves q[t+1]
        fig.add_scatter(x=jt, y=q[jt], mode="markers", name="news jump",
                        marker=dict(symbol="diamond-open", size=11,
                                    color=ORANGE, line=dict(width=2)))
    fig.add_scatter(x=tt, y=p, name="observed market price p_t",
                    line=dict(color=BLUE, width=2))
    fig.add_scatter(x=tt, y=f, name=f"EMA fair value f_t (α={S['alpha']:.2f})",
                    line=dict(color=AQUA, width=2))
    if mkt := st.session_state["loaded_market"]:
        rp = mkt["prices"]
        x_scaled = np.linspace(0, len(p) - 1, rp.size)
        fig.add_scatter(x=x_scaled, y=rp, name=f"real market (time-rescaled): {mkt['slug'][:30]}…",
                        line=dict(color=MUTED, width=1.5), opacity=0.8)
    buys = [tr for tr in trades if tr.units > 0]
    sells = [tr for tr in trades if tr.units < 0]
    if buys:
        fig.add_scatter(x=[tr.t for tr in buys], y=[tr.price for tr in buys],
                        mode="markers", name="buy",
                        marker=dict(symbol="triangle-up", size=14, color=GREEN,
                                    line=dict(color=SURFACE, width=2)))
    if sells:
        fig.add_scatter(x=[tr.t for tr in sells], y=[tr.price for tr in sells],
                        mode="markers", name="sell",
                        marker=dict(symbol="triangle-down", size=14, color=RED,
                                    line=dict(color=SURFACE, width=2)))
    fig.add_scatter(x=[len(p) - 1], y=[float(y)], mode="markers", name="settlement",
                    marker=dict(symbol="star", size=16, color=INK))
    fig.update_layout(height=480)
    with left:
        st.plotly_chart(fig, use_container_width=True)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Settlement", "YES ✅" if y else "NO ❌")
    m2.metric("Policy profit", f"${profit:+.3f}",
              delta=f"{profit:+.3f}", delta_color="normal")
    bh_profit = S["unit"] * (y - p[0] - S["cost"])
    m3.metric("Buy-and-hold profit", f"${bh_profit:+.3f}")
    m4.metric("Trades", len(trades))


with tab_lab:
    st.subheader(f"{POLICY_LABEL} vs buy-and-hold — "
                 f"{S['n_reps']:,} replications, common random numbers")
    with st.spinner("Simulating…"):
        if use_rlc:
            rlc = run_until_precision(params, policy, rlc_tol, S["seed"],
                                      S["cost"], S["unit"],
                                      initial_reps=max(1000, S["n_reps"]))
            profits = rlc["profits"]
            st.info(f"Run-length control: {'converged' if rlc['converged'] else 'hit the cap'} "
                    f"at n = {rlc['summary']['n']:,} replications "
                    f"(CI half-width {rlc['summary']['half_width']:.4f} vs tolerance {rlc_tol}).")
            # Paired comparison still uses one common batch at the slider size.
            common = cached_paths(S["q0"], S["T"], S["sigma_q"], S["sigma_p"],
                                  S["kappa"], S["variant"], S["n_reps"], S["seed"],
                                  S["eff_jump_rate"], S["jump_scale"])
            bh_profits = profits_on_paths(common, BuyAndHoldPolicy(), S["cost"], S["unit"])
            pol_on_common = profits_on_paths(common, policy, S["cost"], S["unit"])
        else:
            batch = cached_paths(S["q0"], S["T"], S["sigma_q"], S["sigma_p"],
                                 S["kappa"], S["variant"], S["n_reps"], S["seed"],
                                 S["eff_jump_rate"], S["jump_scale"])
            profits = profits_on_paths(batch, policy, S["cost"], S["unit"])
            bh_profits = profits_on_paths(batch, BuyAndHoldPolicy(), S["cost"], S["unit"])
            pol_on_common = profits

    s_pol = summarize(profits)
    s_bh = summarize(bh_profits)
    diff = paired_diff_vs_benchmark(pol_on_common, bh_profits)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(f"E[profit] — {POLICY_LABEL}",
              f"${s_pol['mean']:+.4f}", f"± {s_pol['half_width']:.4f} (95% CI)",
              delta_color="off")
    c2.metric("E[profit] — buy-and-hold",
              f"${s_bh['mean']:+.4f}", f"± {s_bh['half_width']:.4f} (95% CI)",
              delta_color="off")
    c3.metric("P(loss)", f"{s_pol['p_loss']:.1%}",
              f"BH: {s_bh['p_loss']:.1%}", delta_color="off")
    mll = s_pol["mean_loss_given_loss"]
    c4.metric("E[loss | loss]", "—" if np.isnan(mll) else f"${mll:.3f}",
              f"BH: ${s_bh['mean_loss_given_loss']:.3f}"
              if not np.isnan(s_bh["mean_loss_given_loss"]) else "BH: —",
              delta_color="off")

    if diff["beats_benchmark"]:
        st.success(f"**{POLICY_LABEL} beats buy-and-hold**: paired difference "
                   f"{diff['mean']:+.4f} per contract, 95% CI "
                   f"[{diff['ci_low']:+.4f}, {diff['ci_high']:+.4f}] — entirely above 0.")
    elif diff["loses_to_benchmark"]:
        st.error(f"**Buy-and-hold wins**: paired difference {diff['mean']:+.4f}, "
                 f"95% CI [{diff['ci_low']:+.4f}, {diff['ci_high']:+.4f}] — entirely below 0.")
    else:
        st.warning(f"**No significant difference** at these settings: paired difference "
                   f"{diff['mean']:+.4f}, 95% CI [{diff['ci_low']:+.4f}, {diff['ci_high']:+.4f}] "
                   f"straddles 0. Try more replications or run-length control.")

    hist = go.Figure(layout=_base_layout("Profit distribution", "profit per contract",
                                         "share of replications"))
    hist.add_histogram(x=profits, name=POLICY_LABEL, marker=dict(color=BLUE),
                       opacity=0.65, histnorm="probability")
    hist.add_histogram(x=bh_profits, name="buy-and-hold", marker=dict(color=ORANGE),
                       opacity=0.65, histnorm="probability")
    hist.update_layout(barmode="overlay", height=380)
    st.plotly_chart(hist, use_container_width=True)


with tab_grid:
    st.subheader("The 3×3 policy grid at the current market settings")
    with st.spinner("Evaluating 9 policies + benchmarks…"):
        comparison = cached_comparison(S["q0"], S["T"], S["sigma_q"], S["sigma_p"],
                                       S["kappa"], S["variant"],
                                       S["n_reps"], S["seed"], S["cost"],
                                       S["eff_jump_rate"], S["jump_scale"])
    fig_profit, fig_ploss = fig_grid_heatmaps(
        comparison, f"variant {S['variant']}"
        + (f", κ={S['kappa']:.2f}" if S["variant"] == "B" else ""))
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(fig_profit.update_layout(height=440), use_container_width=True)
    with col2:
        st.plotly_chart(fig_ploss.update_layout(height=440), use_container_width=True)

    ema_rows = comparison[comparison["alpha"].notna()]
    winner = ema_rows.loc[ema_rows["mean_profit"].idxmax()]
    star = "⭐ and its lead over buy-and-hold is CI-significant" if winner["beats_bh"] \
        else "…but its lead over buy-and-hold is NOT CI-significant"
    st.caption(f"Winner: **{winner['policy']}** with E[profit] = "
               f"{winner['mean_profit']:+.4f} {star}.")
    with st.expander("Full comparison table"):
        st.dataframe(comparison.round(4), use_container_width=True)


with tab_sens:
    st.subheader("Expected profit as one market assumption moves")
    n_sens = min(S["n_reps"], 4000)
    sigma_grid = [0.0, 0.02, 0.05, 0.08, 0.12]
    kappa_grid = [0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0]

    @st.cache_data(show_spinner=False)
    def sens_curves(q0, T, sigma_q, sigma_p, kappa, variant,
                    alpha, delta, allow_exit, cost, unit, n_reps, seed,
                    jump_rate=0.0, jump_scale=0.15):
        base = MarketParams(q0=q0, T=T, sigma_q=sigma_q, sigma_p=sigma_p,
                            kappa=kappa, variant=variant,
                            jump_rate=jump_rate, jump_scale=jump_scale)
        pol = EMAThresholdPolicy(alpha, delta, allow_exit)
        rows = []
        for i, sp in enumerate(sigma_grid):
            paths = simulate_market_seeded(replace(base, sigma_p=sp), n_reps, seed + i)
            for name, prof in (("policy", profits_on_paths(paths, pol, cost, unit)),
                               ("bh", profits_on_paths(paths, BuyAndHoldPolicy(), cost, unit))):
                s = summarize(prof)
                rows.append({"sweep": "sigma_p", "x": sp, "series": name,
                             "mean": s["mean"], "half": s["half_width"]})
        for i, k in enumerate(kappa_grid):
            paths = simulate_market_seeded(replace(base, kappa=k, variant="B"),
                                           n_reps, seed + 50 + i)
            for name, prof in (("policy", profits_on_paths(paths, pol, cost, unit)),
                               ("bh", profits_on_paths(paths, BuyAndHoldPolicy(), cost, unit))):
                s = summarize(prof)
                rows.append({"sweep": "kappa", "x": k, "series": name,
                             "mean": s["mean"], "half": s["half_width"]})
        return pd.DataFrame(rows)

    with st.spinner("Sweeping σ_p and κ…"):
        curves = sens_curves(S["q0"], S["T"], S["sigma_q"], S["sigma_p"], S["kappa"],
                             S["variant"], S["alpha"], S["delta"], S["allow_exit"],
                             S["cost"], S["unit"], n_sens, S["seed"],
                             S["eff_jump_rate"], S["jump_scale"])

    def sweep_fig(sweep: str, xlabel: str, title: str) -> go.Figure:
        fig = go.Figure(layout=_base_layout(title, xlabel,
                                            "expected profit (95% CI)"))
        for series, name, color in (("policy", POLICY_LABEL, BLUE),
                                    ("bh", "buy-and-hold", ORANGE)):
            d = curves[(curves["sweep"] == sweep) & (curves["series"] == series)]
            fig.add_scatter(x=d["x"], y=d["mean"], name=name, mode="lines+markers",
                            line=dict(color=color, width=2), marker=dict(size=8),
                            error_y=dict(type="data", array=d["half"],
                                         color=color, thickness=1.2, width=4))
        fig.add_hline(y=0, line=dict(color=MUTED, width=1, dash="dot"))
        fig.update_layout(height=420)
        return fig

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(sweep_fig("sigma_p", "σ_p (observation noise)",
                                  "vs market noisiness"), use_container_width=True)
    with col2:
        st.plotly_chart(sweep_fig("kappa", "κ (adjustment speed; 1 = variant A)",
                                  "vs mispricing persistence (variant B)"),
                        use_container_width=True)
    st.caption(f"{n_sens:,} replications per point, common random numbers within "
               f"each point; error bars are 95% CIs (κ sweep forces variant B).")


with tab_about:
    st.subheader("What this simulator does")
    st.markdown(
        r"""
**The market, in three layers** *(professor-approved model — Section 3 of PROJECT.md)*

1. **A hidden truth.** Each contract has a true probability of paying out,
   `q_t`, that drifts every period as a bounded random walk. Steps shrink near
   0 and 1 (the `√(q(1−q))` factor), so the truth stays a probability. **No
   trader ever sees this line** — on the Single Path chart it's the dashed one.
2. **A noisy price.** What you *can* see is the market price `p_t`.
   In **variant A** the price is the truth plus fresh noise each period.
   In **variant B** the price only closes a fraction **κ** of its gap to the
   truth each period, so mispricings *persist* — the smaller κ, the longer a
   cheap contract stays cheap. κ = 1 is exactly variant A.
3. **Settlement.** At the horizon T the contract pays \$1 with probability
   `q_T` (drawn by inverse transform, Lecture 2), else \$0. Profit per unit =
   payout − entry price − transaction cost.

**The trading idea.** The EMA policy smooths the price into a fair-value
estimate `f_t` and buys one unit when the price sits more than δ *below* the
smoothed estimate — betting that the dip is noise, not news. The benchmarks
are buy-and-hold (buy at t=0, ignore the path) and never-trade (profit 0).

**What the tabs demonstrate**

| Tab | Question it answers | Course material |
|---|---|---|
| Single Path Explorer | What does one life of a contract look like? | model structure, inverse transform (Lec 2) |
| Policy Lab | Is this policy's edge real or noise? | CLT confidence intervals, run-length control (Lec 3) |
| Policy Grid | Which (α, δ) cell wins here? | comparing alternatives, common random numbers (Lec 7–8) |
| Sensitivity Explorer | When does the edge appear/disappear? | sensitivity analysis (Lec 8) |
| Load a real market | Are our parameters realistic? | input modelling / moment matching (Lec 8) |

**Headline finding** *(seed 20260812, n = 20,000/point — see results/)*:
with realistic observation noise (σ_p ≈ 0.05), the best EMA policy beats
buy-and-hold **at every persistence level κ ∈ [0.05, 1]**, even with a 2-cent
per-trade cost; the edge peaks near κ ≈ 0.2–0.3 (≈ +\$0.10 per \$1 contract) and
vanishes only when observation noise vanishes. Persistence shapes the edge —
noise creates it.

**Optional extension — news jumps (default off).** The sidebar's 🗞️ toggle
adds rare, large, zero-mean shocks to the hidden truth, arriving as a Poisson
process (Bernoulli per period, geometric interarrivals — the discrete
analogue of exponential ones). This goes *beyond* the professor-approved
model, so it ships off by default and every headline result uses the
approved model. We then quantified it (results/model\_case\_matrix.csv and
results/sweep\_jump\_rate.csv, seed 20260812): across **all four model
cases** — variant A/B × jumps off/on — the EMA edge stays CI-significant,
but news is expensive: at λ = 0.05 the edge drops ≈ 24%, at λ = 0.20 it
drops ≈ 62%, decaying roughly linearly, because the rule buys downward
repricings it cannot distinguish from noise and cannot buy the upward ones.
Under variant A with jumps the winning cell shifts from slow (α=0.1) to fast
(α=0.6) smoothing — when the world can jump, long memory becomes a stale
anchor. Try it live: toggle jumps on and watch the Policy Lab verdict.

**Scope guard.** Real Polymarket data only *sets inputs* (q₀ and volatilities,
estimated by method of moments). We do **not** fit the model to real data or
backtest policies on real series — that is out of scope by design.

**Reproducibility.** Every simulation takes an explicit seed
(`numpy.random.Generator`); the same seed always reproduces the same paths,
trades, and CIs. The engine passes a 37-test validation suite (zero-noise
limit, martingale property, settlement calibration, no-lookahead, seed
reproducibility — Section 7).

**Team:** _add team member names here before the presentation._
        """
    )

    with st.expander("📚 Every control, explained (open during Q&A)"):
        st.markdown(
            r"""
**Market setup**

| Control | What it does | Intuition |
|---|---|---|
| Starting probability q₀ | Where the hidden truth begins at t=0 — also the fair price of the contract on day one. | A 0.40 contract "should" cost \$0.40. |
| Horizon T | Number of periods until settlement. | Longer horizons let the truth wander further and give policies more chances to act. |
| Hidden volatility σ_q | Step size of the truth's random walk, per period (damped by √(q(1−q)) near 0/1). | How fast the world actually changes. Real Polymarket estimates: 0.002–0.019/step. |
| Observation noise σ_p | Standard deviation of the price's error around the truth, each period. | How wrong the market is allowed to be. **This is what creates the trading edge.** |
| Price variant A/B | A: errors are fresh each period and vanish next period. B: the price only closes a fraction κ of its gap to the truth per period, so errors persist. | A = instantly self-correcting market; B = sluggish market. |
| Persistence κ | Variant B's adjustment speed. κ=1 reproduces variant A exactly; κ=0.05 means a mispricing takes ~20 periods to fade. | Smaller κ = stickier mispricings. The edge peaks at κ≈0.2–0.3. |
| 🗞️ News jumps (λ, size) | Extension, default off: with probability λ each period the truth takes an extra zero-mean shock of the given size. | Rare big news. Zero-mean ⇒ settlement calibration still holds; λ=0 is bit-for-bit the approved model. |

**Trading policy**

| Control | What it does | Intuition |
|---|---|---|
| Smoothing α | EMA weight on today's price: f = α·p + (1−α)·f. | Small α = long memory / slow estimate; α=1 makes f ≡ p (never trades). |
| Entry threshold δ | Buy 1 unit when f − p > δ; hold to settlement. | How big a dip counts as mispricing, not wiggle. δ=0.10 ≈ act only on ~2σ dips at σ_p=0.05. |
| Exit when rich | Optionally also sell when p − f > δ (re-entry allowed). | Off in all reported results — the spec's pure buy-and-hold-to-settlement family. |
| Per-trade cost c | Fee per unit each time you trade. | Hits EMA and buy-and-hold nearly equally (both trade ≤ once), so the *edge* barely moves. |
| Position size | Units per trade. | Scales all P&L linearly — shapes, CIs, and verdicts are unchanged. |

**Simulation**

| Control | What it does | Intuition |
|---|---|---|
| Replications | How many independent contracts stand behind every statistic. | More reps = tighter CIs (half-width ∝ 1/√n). Default 2,000 keeps every interaction <2s. |
| Seed | Fixes every random draw. | Same seed ⇒ identical paths, trades, and CIs — the demo is repeatable. |
| Run-length control + tolerance | Doubles the replication count until the 95% CI half-width falls below tolerance (Lecture 3). | "How many runs do I actually need?" — answered automatically in Policy Lab. |
| Load a real market | Paste a polymarket.com URL (live) or pick a bundled sample (offline); prefill maps the series onto q₀/σ_q/σ_p by method of moments. | Grounds the dials in reality. Inputs only — never fitting or backtesting. |
"""
        )

    st.divider()
    st.markdown("**Rubric mapping** — problem formulation: Sections 1–3 of "
                "PROJECT.md and this page · model implementation & simulation "
                "design (30%): `src/model.py`, `src/policies.py`, the test "
                "suite, seeded vectorised batches · analysis & interpretation "
                "(30%): Policy Lab CIs, Policy Grid, Sensitivity Explorer, "
                "results/ CSVs · presentation quality (20%): this dashboard.")
