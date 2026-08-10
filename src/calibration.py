"""Real-data calibration from Polymarket (PROJECT.md Section 6).

Purpose: choose realistic default parameters for the simulator and power the
dashboard's "load a real market" feature.  We use two public read-only
endpoints (no API key):

- Gamma API,  https://gamma-api.polymarket.com/markets?slug=...  (metadata)
- CLOB API,   https://clob.polymarket.com/prices-history         (price series)

SCOPE GUARD (per spec): calibration only sets simulation INPUTS (q0 and the
volatility parameters).  We do NOT fit the model to real data and we do NOT
backtest policies on real data — that is out of scope and the report says so.

Failure handling: if the endpoints are unreachable or their shape changed,
``fetch_market_or_sample`` degrades to bundled sample CSVs committed under
results/sample_markets/, so the offline demo works end to end.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
import pandas as pd

GAMMA_URL = "https://gamma-api.polymarket.com/markets"
CLOB_URL = "https://clob.polymarket.com/prices-history"
SAMPLES_DIR = Path(__file__).resolve().parent.parent / "results" / "sample_markets"
TIMEOUT = 12  # seconds per HTTP call — the dashboard must never hang


class PolymarketUnavailable(Exception):
    """Raised when the live API cannot be reached or returns unusable data."""


@dataclass
class MarketData:
    """A (real) market price series plus display metadata."""

    question: str
    slug: str
    timestamps: np.ndarray          # unix seconds, ascending
    prices: np.ndarray              # traded YES price in (0, 1)
    source: str                     # "live" or "sample"
    url: str = ""
    meta: dict = field(default_factory=dict)


def parse_slug(slug_or_url: str) -> str:
    """Extract a market slug from a pasted Polymarket URL (or pass one through).

    Accepts e.g.
      https://polymarket.com/event/some-event/actual-market-slug?tid=123
      https://polymarket.com/market/actual-market-slug
      actual-market-slug
    Strategy: take the last non-empty path segment and drop any query string.
    """
    s = slug_or_url.strip()
    if not s:
        raise ValueError("empty market slug/URL")
    if "//" in s or s.startswith("polymarket.com"):
        if "//" not in s:
            s = "https://" + s
        path = urlparse(s).path
        segments = [seg for seg in path.split("/") if seg]
        if not segments:
            raise ValueError(f"no slug found in URL: {slug_or_url!r}")
        return segments[-1]
    return s.split("?")[0]


def _fetch_json(url: str, params: dict) -> object:
    import requests

    resp = requests.get(url, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def fetch_market(slug_or_url: str, fidelity_minutes: int = 60) -> MarketData:
    """Fetch metadata + YES price history for one market from the live API.

    Raises PolymarketUnavailable on any network/shape problem so callers can
    degrade gracefully (the dashboard uses fetch_market_or_sample instead).
    """
    slug = parse_slug(slug_or_url)
    try:
        markets = _fetch_json(GAMMA_URL, {"slug": slug})
        if not markets:
            raise PolymarketUnavailable(f"no market found for slug {slug!r}")
        m = markets[0]
        token_ids = json.loads(m["clobTokenIds"])  # JSON-encoded list, YES first
        history = _fetch_json(
            CLOB_URL,
            {"market": token_ids[0], "interval": "max", "fidelity": fidelity_minutes},
        )["history"]
        if len(history) < 5:
            raise PolymarketUnavailable(f"history too short for {slug!r} ({len(history)} pts)")
        ts = np.array([h["t"] for h in history], dtype=np.int64)
        prices = np.array([h["p"] for h in history], dtype=float)
        order = np.argsort(ts)
        return MarketData(
            question=m.get("question", slug),
            slug=slug,
            timestamps=ts[order],
            prices=np.clip(prices[order], 0.001, 0.999),
            source="live",
            url=f"https://polymarket.com/market/{slug}",
            meta={k: m.get(k) for k in ("endDate", "volume", "liquidity", "closed")},
        )
    except PolymarketUnavailable:
        raise
    except Exception as exc:  # noqa: BLE001 — any failure means "degrade"
        raise PolymarketUnavailable(f"Polymarket fetch failed for {slug!r}: {exc}") from exc


def list_samples() -> list[str]:
    """Names of the bundled offline sample markets."""
    if not SAMPLES_DIR.exists():
        return []
    return sorted(p.stem for p in SAMPLES_DIR.glob("*.csv"))


def load_sample(name: str | None = None) -> MarketData:
    """Load a bundled sample market (committed CSV) for offline demos.

    Each CSV has columns (timestamp, price); display metadata lives in
    results/sample_markets/index.json.
    """
    names = list_samples()
    if not names:
        raise FileNotFoundError(f"no sample markets bundled in {SAMPLES_DIR}")
    if name is None:
        name = names[0]
    if name not in names:
        raise FileNotFoundError(f"unknown sample {name!r}; available: {names}")
    df = pd.read_csv(SAMPLES_DIR / f"{name}.csv")
    index = {}
    index_path = SAMPLES_DIR / "index.json"
    if index_path.exists():
        index = json.loads(index_path.read_text()).get(name, {})
    return MarketData(
        question=index.get("question", name),
        slug=index.get("slug", name),
        timestamps=df["timestamp"].to_numpy(np.int64),
        prices=np.clip(df["price"].to_numpy(float), 0.001, 0.999),
        source="sample",
        url=index.get("url", ""),
        meta=index,
    )


def fetch_market_or_sample(slug_or_url: str | None) -> MarketData:
    """Live fetch with graceful offline degradation (spec Section 6).

    With a slug/URL: try the live API, fall back to a bundled sample on any
    failure.  With None/empty input: go straight to the first bundled sample.
    """
    if slug_or_url:
        try:
            return fetch_market(slug_or_url)
        except (PolymarketUnavailable, ValueError):
            pass
    return load_sample()


def estimate_params(price_series: np.ndarray) -> dict:
    """Map a real price series onto model parameters (method of moments).

    Under Variant A, the observed increment is
        dp_t = dq_t + eta_t - eta_{t-1},
    an MA(1) in the noise, so (Lecture 8, input modelling / moment matching):
        Cov(dp_t, dp_{t-1}) = -sigma_p^2           -> sigma_p estimate,
        Var(dp_t) = Var(dq_t) + 2 * sigma_p^2      -> sigma_q estimate, using
        Var(dq_t) ≈ sigma_q^2 * mean(q(1-q)) with p as the observable proxy
        for q.
    Negative moment estimates are floored at 0 (possible in small samples).
    These are INPUT-SETTING heuristics, not a fitted model — see scope guard.

    Returns q0 (first price), sigma_q, sigma_p, n_obs, and the realized
    per-step volatility for display.
    """
    p = np.asarray(price_series, dtype=float)
    if p.size < 5:
        raise ValueError(f"need at least 5 prices, got {p.size}")
    dp = np.diff(p)
    var_dp = float(np.var(dp, ddof=1))
    # lag-1 autocovariance of the increments
    dbar = dp.mean()
    autocov1 = float(np.mean((dp[1:] - dbar) * (dp[:-1] - dbar)))
    sigma_p2 = max(0.0, -autocov1)
    var_dq = max(1e-10, var_dp - 2.0 * sigma_p2)
    damping = float(np.mean(p * (1.0 - p)))  # E[q(1-q)] proxy
    return {
        "q0": float(np.clip(p[0], 0.01, 0.99)),
        "q_last": float(np.clip(p[-1], 0.01, 0.99)),
        "sigma_q": float(np.sqrt(var_dq / damping)),
        "sigma_p": float(np.sqrt(sigma_p2)),
        "realized_step_vol": float(np.std(dp, ddof=1)),
        "n_obs": int(p.size),
    }


def bundle_samples(slugs: list[str], out_dir: Path = SAMPLES_DIR) -> list[str]:
    """Developer utility: fetch live markets and commit them as offline samples."""
    out_dir.mkdir(parents=True, exist_ok=True)
    index_path = out_dir / "index.json"
    index = json.loads(index_path.read_text()) if index_path.exists() else {}
    saved = []
    for slug in slugs:
        md = fetch_market(slug)
        name = md.slug[:60]
        pd.DataFrame({"timestamp": md.timestamps, "price": md.prices}).to_csv(
            out_dir / f"{name}.csv", index=False
        )
        index[name] = {
            "question": md.question,
            "slug": md.slug,
            "url": md.url,
            "n_obs": int(md.prices.size),
            **{k: v for k, v in md.meta.items() if v is not None},
        }
        saved.append(name)
    index_path.write_text(json.dumps(index, indent=2))
    return saved
