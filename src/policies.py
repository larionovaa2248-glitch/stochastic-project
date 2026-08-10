"""Trading policies (PROJECT.md Section 4).

Phase 0 stub — signatures only; implemented in Phase 1.
"""

from __future__ import annotations

import numpy as np


class Policy:
    """Common interface: decide(price_history) -> action."""

    def reset(self) -> None:
        raise NotImplementedError

    def decide(self, price_history: np.ndarray) -> int:
        raise NotImplementedError


class EMAThresholdPolicy(Policy):
    """EMA fair-value estimate with entry threshold delta."""


class BuyAndHoldPolicy(Policy):
    """Buy 1 unit at t=0, hold to settlement."""


class NeverTradePolicy(Policy):
    """Never trades; profit is always 0 (sanity floor)."""
