"""Trading policies (PROJECT.md Section 4).

Every policy implements the common interface ``decide(price_history) -> action``
where ``price_history`` is the array of observed prices p_0 .. p_t up to and
including the current period.  The action is an integer number of units to
trade *now* at price p_t: +1 buys one unit, -1 sells (closes) one unit, 0 does
nothing.  Positions are held to settlement unless the optional exit rule fires.

No-lookahead guarantee: ``decide`` receives ONLY past-and-present prices.  It
never sees the hidden probability q_t, future prices, or settlement outcomes.
This is enforced structurally (the interface has no other inputs) and checked
by the test suite (PROJECT.md Section 7, check 4).

Two evaluation paths are provided and tested against each other:
- ``run_policy_path``: transparent per-period loop for one path (used by the
  dashboard's Single Path Explorer and by the tests);
- ``ema_profits`` / ``buy_and_hold_profits`` / ``never_trade_profits``:
  vectorised over all replications at once (one 2-D array, no Python loop over
  paths — dashboard performance requirement, PROJECT.md Section 8).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .model import MarketPaths

# The 3x3 policy grid from PROJECT.md Section 4.
ALPHA_GRID = (0.1, 0.3, 0.6)
DELTA_GRID = (0.02, 0.05, 0.10)
EMA_GRID = tuple((a, d) for a in ALPHA_GRID for d in DELTA_GRID)


class Policy:
    """Common interface: decide(price_history) -> units to trade now."""

    name: str = "policy"

    def reset(self) -> None:
        """Clear all internal state before a new path."""
        raise NotImplementedError

    def decide(self, price_history: np.ndarray) -> int:
        """Return the number of units to trade at the current price.

        price_history contains p_0 .. p_t (the current price is the last
        element).  This is the ONLY information a policy may use.
        """
        raise NotImplementedError


class EMAThresholdPolicy(Policy):
    """EMA fair-value estimate with an entry threshold (the main policy family).

    Fair value follows an exponential moving average of observed prices:
        f_0 = p_0,   f_t = alpha * p_t + (1 - alpha) * f_{t-1}  (t >= 1).

    Rule: buy 1 unit when flat and f_t - p_t > delta (price looks cheap versus
    the smoothed estimate), then hold to settlement.  If ``allow_exit`` is set,
    additionally close the position when p_t - f_t > delta (price looks rich);
    after an exit the policy may re-enter if the buy signal fires again.
    The 3x3 (alpha, delta) grid uses the default allow_exit=False, i.e. the
    pure "buy cheap, hold to settlement" family from the spec.
    """

    def __init__(self, alpha: float, delta: float, allow_exit: bool = False) -> None:
        if not (0.0 < alpha <= 1.0):
            raise ValueError(f"alpha must be in (0, 1], got {alpha}")
        if delta < 0.0:
            raise ValueError(f"delta must be >= 0, got {delta}")
        self.alpha = alpha
        self.delta = delta
        self.allow_exit = allow_exit
        self.name = f"EMA(alpha={alpha}, delta={delta})"
        self.reset()

    def reset(self) -> None:
        self._f: float | None = None  # current EMA fair-value estimate
        self._pos: int = 0            # units currently held (0 or 1)

    @property
    def fair_value(self) -> float | None:
        """Current EMA estimate (exposed so the dashboard can plot f_t)."""
        return self._f

    def decide(self, price_history: np.ndarray) -> int:
        p_t = float(price_history[-1])
        if self._f is None:
            self._f = p_t  # f_0 = p_0: no opinion before any smoothing exists
        else:
            self._f = self.alpha * p_t + (1.0 - self.alpha) * self._f
        if self._pos == 0 and self._f - p_t > self.delta:
            self._pos = 1
            return +1
        if self.allow_exit and self._pos == 1 and p_t - self._f > self.delta:
            self._pos = 0
            return -1
        return 0


class BuyAndHoldPolicy(Policy):
    """Benchmark: buy 1 unit at t = 0, hold to settlement.  Ignores the path."""

    name = "Buy-and-hold"

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._bought = False

    def decide(self, price_history: np.ndarray) -> int:
        if not self._bought:
            self._bought = True
            return +1
        return 0


class NeverTradePolicy(Policy):
    """Benchmark: never trades; profit is always exactly 0 (sanity floor)."""

    name = "Never-trade"

    def reset(self) -> None:
        pass

    def decide(self, price_history: np.ndarray) -> int:
        return 0


@dataclass
class Trade:
    """One executed trade, for plotting markers in the dashboard."""

    t: int
    units: int    # +1 buy, -1 sell
    price: float


def run_policy_path(
    policy: Policy,
    prices: np.ndarray,
    outcome: int,
    cost: float = 0.0,
    unit: float = 1.0,
) -> tuple[float, list[Trade]]:
    """Run one policy over one price path, period by period.

    At each t the policy sees a COPY of p_0 .. p_t only (a copy so it cannot
    even index into the parent buffer).  Trades execute at the current price
    p_t; a per-trade cost is charged per unit traded.  At settlement each unit
    held pays $1 if outcome == 1, else $0.

    Returns (total profit, list of executed trades).
    """
    policy.reset()
    cash = 0.0
    position = 0.0
    trades: list[Trade] = []
    for t in range(len(prices)):
        action = int(policy.decide(prices[: t + 1].copy()))
        if action != 0:
            p_t = float(prices[t])
            cash -= unit * action * p_t          # pay p_t per unit bought (receive if selling)
            cash -= unit * abs(action) * cost    # transaction cost per unit traded
            position += unit * action
            trades.append(Trade(t=t, units=action, price=p_t))
    cash += position * float(outcome)            # settlement payout: $1 per unit iff Y = 1
    return cash, trades


def ema_profits(
    paths: MarketPaths,
    alpha: float,
    delta: float,
    cost: float = 0.0,
    unit: float = 1.0,
    allow_exit: bool = False,
) -> np.ndarray:
    """Vectorised P&L of an EMA-threshold policy over all replications.

    Implements exactly the same decision rule as EMAThresholdPolicy but as one
    sweep over time with all replications in a 2-D array (no Python loop over
    paths).  The test suite asserts equality with the per-path loop.

    Note the EMA recursion only ever uses prices up to the current period —
    the loop index t is the "now", and nothing indexed beyond t is touched.
    """
    p = paths.p
    n_reps, Tp1 = p.shape
    f = p[:, 0].copy()                     # f_0 = p_0
    pos = np.zeros(n_reps)
    cash = np.zeros(n_reps)
    for t in range(Tp1):
        p_t = p[:, t]
        if t > 0:
            f = alpha * p_t + (1.0 - alpha) * f
        buy = (pos == 0.0) & (f - p_t > delta)
        cash[buy] -= unit * (p_t[buy] + cost)
        pos[buy] = unit
        if allow_exit:
            # note: a path cannot buy and exit in the same period (buy just set
            # pos > 0, and the exit signal p - f > delta contradicts the buy
            # signal f - p > delta for delta >= 0)
            sell = (pos > 0.0) & (p_t - f > delta) & ~buy
            cash[sell] += unit * (p_t[sell] - cost)
            pos[sell] = 0.0
    cash += pos * paths.y                  # settlement payout
    return cash


def buy_and_hold_profits(paths: MarketPaths, cost: float = 0.0, unit: float = 1.0) -> np.ndarray:
    """Vectorised P&L of buy-and-hold: buy at p_0, collect payout at T."""
    return unit * (paths.y - paths.p[:, 0] - cost)


def never_trade_profits(paths: MarketPaths) -> np.ndarray:
    """Vectorised P&L of never-trade: identically zero."""
    return np.zeros(paths.n_reps)
