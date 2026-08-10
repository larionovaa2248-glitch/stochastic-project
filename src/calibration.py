"""Polymarket data calibration (Section 6).

Phase 0 stub — signatures only; implemented in Phase 3.
"""

from __future__ import annotations


def fetch_market(slug_or_url: str):
    """Fetch metadata + price series for a Polymarket market (offline fallback)."""
    raise NotImplementedError


def estimate_params(price_series):
    """Map realized volatility of a price series onto model parameters."""
    raise NotImplementedError
