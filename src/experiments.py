"""Batch experiments, confidence intervals, run-length control, sweeps (Section 5).

Phase 0 stub — signatures only; implemented in Phase 2.
"""

from __future__ import annotations


def run_batch(params, policy, n_reps: int, seed: int):
    """Run n_reps replications; return per-replication profits."""
    raise NotImplementedError


def summarize(profits):
    """Expected profit, P(loss), mean loss given loss, 95% CI."""
    raise NotImplementedError


def run_until_precision(params, policy, tol: float, seed: int):
    """Increase n_reps until the CI half-width falls below tol (Lecture 3)."""
    raise NotImplementedError
