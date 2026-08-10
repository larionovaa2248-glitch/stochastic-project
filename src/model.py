"""Three-layer prediction-market simulation engine (PROJECT.md Section 3).

Layer 1: hidden true probability q_t (bounded random walk, never observed).
Layer 2: observed market price p_t (variant A iid noise / variant B partial adjustment).
Layer 3: settlement Y ~ Bernoulli(q_T), contract pays $1 if Y = 1.

Phase 0 stub — signatures only; implemented in Phase 1.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class MarketParams:
    """Parameters of the simulated market (see PROJECT.md Section 3)."""

    q0: float = 0.40
    T: int = 100
    sigma_q: float = 0.02
    sigma_p: float = 0.02
    kappa: float = 1.0
    variant: str = "A"


def simulate_market(params: MarketParams, n_reps: int, rng: np.random.Generator):
    """Simulate n_reps independent market paths. Implemented in Phase 1."""
    raise NotImplementedError


def settle(q_T: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Draw settlement outcomes Y ~ Bernoulli(q_T). Implemented in Phase 1."""
    raise NotImplementedError
