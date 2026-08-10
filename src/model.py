"""Three-layer prediction-market simulation engine (PROJECT.md Section 3 — LOCKED).

The model has three layers, simulated in order each period t = 0, 1, ..., T:

Layer 1 — hidden true probability q_t:
    q_{t+1} = clip(q_t + sigma_q * sqrt(q_t * (1 - q_t)) * Z_t, eps, 1 - eps),
    Z_t ~ N(0, 1) iid, eps = 0.001.  The sqrt(q(1-q)) term shrinks steps near
    the barriers so the probability stays inside (0, 1) naturally, not just via
    clipping.  The trader NEVER observes this process.

Layer 2 — observed market price p_t (two variants, both required):
    Variant A (iid noise):          p_t = clip(q_t + eta_t, 0.01, 0.99)
    Variant B (partial adjustment): p_t = clip(p_{t-1} + kappa * (q_t - p_{t-1})
                                              + eta_t, 0.01, 0.99)
    with eta_t ~ N(0, sigma_p^2) iid and kappa in (0, 1].  Small kappa means
    mispricings persist; kappa = 1 recovers Variant A exactly (we initialise
    Variant B with p_0 = clip(q_0 + eta_0, ...), the same as Variant A, so the
    two variants coincide path-by-path when kappa = 1).

Layer 3 — settlement:
    At t = T the outcome is Y ~ Bernoulli(q_T).  The contract pays $1 if Y = 1,
    else $0.  Profit per unit held = payout - entry price (- transaction cost).

Every stochastic function takes an explicit rng: numpy.random.Generator, and
all randomness flows through standard normal draws or the inverse transform
method (course requirement; see the Lecture 2 citations inline).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# Layer-1 barrier for the hidden probability (spec: eps = 0.001).
EPS_Q = 0.001
# Layer-2 clip bounds for the observed price (spec: [0.01, 0.99]).
P_MIN = 0.01
P_MAX = 0.99


@dataclass(frozen=True)
class MarketParams:
    """Inputs of the simulated market (PROJECT.md Section 3).

    q0      : starting hidden probability (default 0.40 per spec)
    T       : horizon in periods; settlement happens at t = T
    sigma_q : volatility of the hidden probability walk (Layer 1)
    sigma_p : std dev of the observation noise eta_t (Layer 2)
    kappa   : partial-adjustment speed in (0, 1]; only used by Variant B
    variant : "A" (iid noise) or "B" (partial adjustment)
    """

    q0: float = 0.40
    T: int = 100
    sigma_q: float = 0.02
    sigma_p: float = 0.02
    kappa: float = 1.0
    variant: str = "A"

    def __post_init__(self) -> None:
        if not (0.0 < self.q0 < 1.0):
            raise ValueError(f"q0 must be in (0, 1), got {self.q0}")
        if self.T < 1:
            raise ValueError(f"T must be >= 1, got {self.T}")
        if self.sigma_q < 0 or self.sigma_p < 0:
            raise ValueError("sigma_q and sigma_p must be non-negative")
        if not (0.0 < self.kappa <= 1.0):
            raise ValueError(f"kappa must be in (0, 1], got {self.kappa}")
        if self.variant not in ("A", "B"):
            raise ValueError(f"variant must be 'A' or 'B', got {self.variant!r}")


@dataclass(frozen=True)
class MarketPaths:
    """Output of one batch simulation.

    q : (n_reps, T+1) hidden true probability paths — for analysis/plots only;
        trading policies must never receive this array.
    p : (n_reps, T+1) observed market price paths — the only thing traders see.
    y : (n_reps,) settlement outcomes in {0, 1}, Y ~ Bernoulli(q_T).
    """

    q: np.ndarray
    p: np.ndarray
    y: np.ndarray

    @property
    def n_reps(self) -> int:
        return self.q.shape[0]

    @property
    def T(self) -> int:
        return self.q.shape[1] - 1


def simulate_hidden(params: MarketParams, n_reps: int, rng: np.random.Generator) -> np.ndarray:
    """Layer 1: simulate the hidden true probability q_t for all replications.

    Vectorised over replications: the whole batch is one (n_reps, T+1) array
    and the only Python loop is over time (the recursion cannot be unrolled
    because of the state-dependent step size and clipping).

    Z_t are standard normal draws from the passed Generator (conceptually
    Z = Phi^{-1}(U), the inverse transform method of Lecture 2).
    """
    T = params.T
    # All shocks drawn up front in a fixed order so a fixed seed gives a
    # fully reproducible batch.
    Z = rng.standard_normal((n_reps, T))
    q = np.empty((n_reps, T + 1))
    q[:, 0] = params.q0
    for t in range(T):
        qt = q[:, t]
        step = params.sigma_q * np.sqrt(qt * (1.0 - qt)) * Z[:, t]
        q[:, t + 1] = np.clip(qt + step, EPS_Q, 1.0 - EPS_Q)
    return q


def observe_prices(
    q: np.ndarray, params: MarketParams, rng: np.random.Generator
) -> np.ndarray:
    """Layer 2: generate observed market prices p_t from hidden paths q.

    Variant A: p_t = clip(q_t + eta_t, 0.01, 0.99), eta_t iid N(0, sigma_p^2).
    Variant B: p_0 as in Variant A, then
               p_t = clip(p_{t-1} + kappa * (q_t - p_{t-1}) + eta_t, 0.01, 0.99).

    With kappa = 1 Variant B reproduces Variant A path-by-path (given the same
    draws), which the test suite checks.
    """
    n_reps, Tp1 = q.shape
    eta = params.sigma_p * rng.standard_normal((n_reps, Tp1))
    if params.variant == "A":
        return np.clip(q + eta, P_MIN, P_MAX)
    # Variant B — partial adjustment toward the (hidden) truth.
    p = np.empty_like(q)
    p[:, 0] = np.clip(q[:, 0] + eta[:, 0], P_MIN, P_MAX)
    k = params.kappa
    for t in range(1, Tp1):
        p[:, t] = np.clip(p[:, t - 1] + k * (q[:, t] - p[:, t - 1]) + eta[:, t], P_MIN, P_MAX)
    return p


def settle(q_T: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Layer 3: draw settlement outcomes Y ~ Bernoulli(q_T).

    Uses the inverse transform method for a Bernoulli variate (Lecture 2):
    draw U ~ Uniform(0, 1) and set Y = 1{U < q_T}, so P(Y = 1) = q_T.
    """
    U = rng.random(q_T.shape[0])
    return (U < q_T).astype(np.int64)


def simulate_market(params: MarketParams, n_reps: int, rng: np.random.Generator) -> MarketPaths:
    """Simulate n_reps independent contracts end to end (all three layers).

    Draw order is fixed (Layer-1 shocks, then Layer-2 noise, then settlement
    uniforms) so that a fixed seed reproduces the batch exactly, and so that
    Variant A and Variant B consume identical draws — which makes cross-variant
    comparisons use common random numbers (variance reduction, Lecture 7).
    """
    q = simulate_hidden(params, n_reps, rng)
    p = observe_prices(q, params, rng)
    y = settle(q[:, -1], rng)
    return MarketPaths(q=q, p=p, y=y)


def simulate_market_seeded(params: MarketParams, n_reps: int, seed: int) -> MarketPaths:
    """Convenience wrapper: build a fresh Generator from an explicit seed.

    Same (params, n_reps, seed) always returns the identical batch — this is
    the reproducibility contract the dashboard and experiments rely on.
    """
    return simulate_market(params, n_reps, np.random.default_rng(seed))
