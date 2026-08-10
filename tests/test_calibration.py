"""Calibration tests (PROJECT.md Section 6) — all offline-safe.

The live API is never hit here: network failure is simulated by monkeypatching,
and the bundled sample CSVs cover the offline path (the data-engineer
definition of done: fallback path tested).
"""

from __future__ import annotations

import numpy as np
import pytest

import src.calibration as cal
from src.model import MarketParams, simulate_market_seeded


class TestParseSlug:
    def test_full_event_url_with_query(self):
        assert cal.parse_slug("https://polymarket.com/event/x/my-market?tid=99") == "my-market"

    def test_market_url(self):
        assert cal.parse_slug("https://polymarket.com/market/my-market") == "my-market"

    def test_bare_slug_passthrough(self):
        assert cal.parse_slug("my-market") == "my-market"

    def test_url_without_scheme(self):
        assert cal.parse_slug("polymarket.com/event/e/my-market") == "my-market"

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            cal.parse_slug("   ")


class TestEstimateParams:
    def test_recovers_known_parameters_from_simulated_variant_a(self):
        # Moment estimator sanity: simulate variant A with known sigmas and a
        # long horizon, then check the estimates land near the truth.  The
        # dq variance uses p as a proxy for q, so tolerate ~25% relative error.
        params = MarketParams(q0=0.5, T=20000, sigma_q=0.02, sigma_p=0.03)
        paths = simulate_market_seeded(params, 1, seed=42)
        est = cal.estimate_params(paths.p[0])
        assert est["sigma_p"] == pytest.approx(0.03, rel=0.25)
        assert est["sigma_q"] == pytest.approx(0.02, rel=0.25)
        assert est["q0"] == pytest.approx(paths.p[0][0], abs=0.01)

    def test_zero_noise_series_gives_zero_sigma_p(self):
        params = MarketParams(q0=0.5, T=5000, sigma_q=0.02, sigma_p=0.0)
        paths = simulate_market_seeded(params, 1, seed=43)
        est = cal.estimate_params(paths.p[0])
        # sample lag-1 autocovariance can be slightly positive or negative;
        # the floor at 0 means sigma_p must come out tiny, not spurious.
        assert est["sigma_p"] < 0.005
        assert est["sigma_q"] == pytest.approx(0.02, rel=0.25)

    def test_too_short_series_raises(self):
        with pytest.raises(ValueError):
            cal.estimate_params(np.array([0.4, 0.5]))


class TestOfflineFallback:
    def test_bundled_samples_exist_and_load(self):
        names = cal.list_samples()
        assert len(names) >= 3, "spec requires 3-5 bundled sample markets"
        md = cal.load_sample(names[0])
        assert md.source == "sample"
        assert md.prices.size >= 100
        assert np.all((md.prices > 0) & (md.prices < 1))
        assert np.all(np.diff(md.timestamps) >= 0)

    def test_estimate_params_works_on_every_bundled_sample(self):
        for name in cal.list_samples():
            est = cal.estimate_params(cal.load_sample(name).prices)
            assert 0.0 < est["q0"] < 1.0
            assert est["sigma_q"] >= 0.0 and est["sigma_p"] >= 0.0

    def test_fetch_market_or_sample_degrades_when_api_down(self, monkeypatch):
        def boom(url, params):
            raise ConnectionError("simulated outage")

        monkeypatch.setattr(cal, "_fetch_json", boom)
        md = cal.fetch_market_or_sample("any-slug-at-all")
        assert md.source == "sample"

    def test_fetch_market_or_sample_with_no_input_uses_sample(self):
        assert cal.fetch_market_or_sample(None).source == "sample"

    def test_unknown_sample_name_raises(self):
        with pytest.raises(FileNotFoundError):
            cal.load_sample("no-such-sample")
