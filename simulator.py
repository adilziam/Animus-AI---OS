"""
simulator.py — Paper Trade Execution Engine
Animus AI

Full paper trading engine with:
  - Realistic fill modeling (slippage, partial fills, latency)
  - Position and portfolio management
  - P&L tracking (realized + unrealized)
  - Performance metrics (Sharpe, win rate, max drawdown)
  - Risk limits (max position size, max drawdown circuit breaker)
"""

import math
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal


Direction   = Literal["LONG", "SHORT"]
OrderStatus = Literal["PENDING", "FILLED", "PARTIAL", "REJECTED"]


# ── Risk parameters ────────────────────────────────────────

DEFAULT_CAPITAL        = 100_000.0
MAX_POSITION_PCT       = 0.10      # max 10% of capital per position
MAX_DRAWDOWN_PCT       = 0.20      # circuit breaker: halt at 20% drawdown
SLIPPAGE_BPS           = 5.0       # basis points of slippage
MIN_LATENCY_MS         = 2
MAX_LATENCY_MS         = 15
FILL_RATE              = 0.95      # probability of full fill


# ── Order / Position ───────────────────────────────────────

@dataclass
class Order:
    id:         int
    symbol:     str
    direction:  Direction
    quantity:   float
    price:      float
    timestamp:  str   = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status:     OrderStatus = "PENDING"
    fill_price: float = 0.0
    fill_qty:   float = 0.0
    latency_ms: int   = 0

    def to_dict(self) -> dict:
        return {
            "id":         self.id,
            "symbol":     self.symbol,
            "direction":  self.direction,
            "quantity":   self.quantity,
            "fill_price": self.fill_price,
            "fill_qty":   self.fill_qty,
            "status":     self.status,
            "latency_ms": self.latency_ms,
            "timestamp":  self.timestamp,
        }


@dataclass
class Position:
    symbol:        str
    direction:     Direction
    quantity:      float
    entry_price:   float
    current_price: float = 0.0
    opened_at:     str   = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def unrealized_pnl(self) -> float:
        mult = 1 if self.direction == "LONG" else -1
        return mult * (self.current_price - self.entry_price) * self.quantity

    @property
    def notional(self) -> float:
        return self.entry_price * self.quantity

    def to_dict(self) -> dict:
        return {
            "symbol":        self.symbol,
            "direction":     self.direction,
            "quantity":      round(self.quantity, 6),
            "entry_price":   round(self.entry_price, 4),
            "current_price": round(self.current_price, 4),
            "unrealized_pnl": round(self.unrealized_pnl, 2),
            "notional":      round(self.notional, 2),
            "opened_at":     self.opened_at,
        }


@dataclass
class Trade:
    """A completed round-trip (open + close)."""
    symbol:       str
    direction:    Direction
    quantity:     float
    entry_price:  float
    exit_price:   float
    realized_pnl: float
    opened_at:    str
    closed_at:    str

    @property
    def is_winner(self) -> bool:
        return self.realized_pnl > 0

    def to_dict(self) -> dict:
        return {
            "symbol":       self.symbol,
            "direction":    self.direction,
            "quantity":     round(self.quantity, 6),
            "entry_price":  round(self.entry_price, 4),
            "exit_price":   round(self.exit_price, 4),
            "realized_pnl": round(self.realized_pnl, 2),
            "opened_at":    self.opened_at,
            "closed_at":    self.closed_at,
        }


# ── Portfolio metrics ──────────────────────────────────────

class PerformanceTracker:
    """Tracks equity curve and computes rolling performance metrics."""

    def __init__(self, starting_capital: float):
        self.starting_capital = starting_capital
        self.equity_curve: list[float] = [starting_capital]
        self.peak_equity = starting_capital

    def record(self, equity: float) -> None:
        self.equity_curve.append(equity)
        if equity > self.peak_equity:
            self.peak_equity = equity

    @property
    def max_drawdown(self) -> float:
        if not self.equity_curve:
            return 0.0
        peak = self.equity_curve[0]
        max_dd = 0.0
        for e in self.equity_curve:
            if e > peak:
                peak = e
            dd = (peak - e) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)
        return round(max_dd, 4)

    def sharpe_ratio(self, risk_free_rate: float = 0.05) -> float:
        if len(self.equity_curve) < 2:
            return 0.0
        returns = [
            (self.equity_curve[i] - self.equity_curve[i - 1]) / self.equity_curve[i - 1]
            for i in range(1, len(self.equity_curve))
        ]
        if not returns:
            return 0.0
        mean_r = sum(returns) / len(returns)
        std_r  = math.sqrt(sum((r - mean_r) ** 2 for r in returns) / len(returns)) or 1e-9
        daily_rf = risk_free_rate / 252
        return round((mean_r - daily_rf) / std_r * math.sqrt(252), 3)

    def total_return_pct(self) -> float:
        if len(self.equity_curve) < 2:
            return 0.0
        return round(
            (self.equity_curve[-1] - self.starting_capital) / self.starting_capital * 100, 2
        )


# ── Simulator ──────────────────────────────────────────────

class Simulator:
    """
    Paper trading simulator.

    Usage:
        sim = Simulator()
        order = sim.open_position("BTC/USD", "LONG", 0.1, 67000.0)
        sim.update_prices({"BTC/USD": 68000.0})
        sim.close_position("BTC/USD", 68000.0)
        print(sim.summary())
    """

    def __init__(
        self,
        starting_capital: float = DEFAULT_CAPITAL,
        slippage_bps:     float = SLIPPAGE_BPS,
        fill_rate:        float = FILL_RATE,
        max_position_pct: float = MAX_POSITION_PCT,
        max_drawdown_pct: float = MAX_DRAWDOWN_PCT,
    ):
        self.starting_capital = starting_capital
        self.capital          = starting_capital
        self.slippage_bps     = slippage_bps
        self.fill_rate        = fill_rate
        self.max_position_pct = max_position_pct
        self.max_drawdown_pct = max_drawdown_pct

        self.positions:     dict[str, Position] = {}
        self.order_history: list[Order]         = []
        self.trade_history: list[Trade]         = []
        self.tracker        = PerformanceTracker(starting_capital)
        self._order_id      = 0
        self.halted         = False

    # ── Internal helpers ───────────────────────────────────

    def _next_id(self) -> int:
        self._order_id += 1
        return self._order_id

    def _apply_slippage(self, price: float, direction: Direction) -> float:
        slip = price * (self.slippage_bps / 10_000)
        sign = 1 if direction == "LONG" else -1
        return price + sign * random.uniform(0, slip)

    def _simulate_fill(self, order: Order) -> Order:
        latency_ms    = random.randint(MIN_LATENCY_MS, MAX_LATENCY_MS)
        fill_price    = self._apply_slippage(order.price, order.direction)
        full_fill     = random.random() <= self.fill_rate
        fill_qty      = order.quantity if full_fill else order.quantity * random.uniform(0.5, 0.95)

        order.fill_price  = round(fill_price, 6)
        order.fill_qty    = round(fill_qty, 6)
        order.latency_ms  = latency_ms
        order.status      = "FILLED" if full_fill else "PARTIAL"
        return order

    def _check_risk(self, symbol: str, quantity: float, price: float) -> str | None:
        """Return an error string if the order would breach risk limits, else None."""
        if self.halted:
            return "Trading halted — max drawdown exceeded"
        cost = price * quantity
        if cost > self.capital * self.max_position_pct:
            return f"Position size {cost:.0f} exceeds {self.max_position_pct*100:.0f}% limit"
        if cost > self.capital:
            return "Insufficient capital"
        return None

    def _record_equity(self) -> None:
        equity = self.equity
        self.tracker.record(equity)
        if (self.starting_capital - equity) / self.starting_capital >= self.max_drawdown_pct:
            self.halted = True

    # ── Public API ─────────────────────────────────────────

    def open_position(
        self, symbol: str, direction: Direction, quantity: float, price: float
    ) -> Order:
        """Open a new paper position."""
        order = Order(
            id=self._next_id(),
            symbol=symbol,
            direction=direction,
            quantity=quantity,
            price=price,
        )

        err = self._check_risk(symbol, quantity, price)
        if err:
            order.status = "REJECTED"
            self.order_history.append(order)
            return order

        if symbol in self.positions:
            order.status = "REJECTED"
            self.order_history.append(order)
            return order

        order = self._simulate_fill(order)
        cost  = order.fill_price * order.fill_qty
        self.capital -= cost

        self.positions[symbol] = Position(
            symbol=symbol,
            direction=direction,
            quantity=order.fill_qty,
            entry_price=order.fill_price,
            current_price=order.fill_price,
        )
        self.order_history.append(order)
        self._record_equity()
        return order

    def close_position(self, symbol: str, price: float) -> Order | None:
        """Close an existing paper position."""
        pos = self.positions.pop(symbol, None)
        if pos is None:
            return None

        direction_close: Direction = "SHORT" if pos.direction == "LONG" else "LONG"
        order = Order(
            id=self._next_id(),
            symbol=symbol,
            direction=direction_close,
            quantity=pos.quantity,
            price=price,
        )
        order = self._simulate_fill(order)

        proceeds      = order.fill_price * order.fill_qty
        mult          = 1 if pos.direction == "LONG" else -1
        realized_pnl  = mult * (order.fill_price - pos.entry_price) * order.fill_qty
        self.capital += proceeds

        self.trade_history.append(Trade(
            symbol=symbol,
            direction=pos.direction,
            quantity=order.fill_qty,
            entry_price=pos.entry_price,
            exit_price=order.fill_price,
            realized_pnl=realized_pnl,
            opened_at=pos.opened_at,
            closed_at=datetime.now(timezone.utc).isoformat(),
        ))
        self.order_history.append(order)
        self._record_equity()
        return order

    def update_prices(self, prices: dict[str, float]) -> None:
        """Push latest market prices into open positions."""
        for symbol, price in prices.items():
            if symbol in self.positions:
                self.positions[symbol].current_price = price
        self._record_equity()

    # ── Derived properties ─────────────────────────────────

    @property
    def equity(self) -> float:
        return self.capital + sum(p.unrealized_pnl for p in self.positions.values())

    @property
    def total_realized_pnl(self) -> float:
        return sum(t.realized_pnl for t in self.trade_history)

    @property
    def total_unrealized_pnl(self) -> float:
        return sum(p.unrealized_pnl for p in self.positions.values())

    @property
    def win_rate(self) -> float:
        if not self.trade_history:
            return 0.0
        wins = sum(1 for t in self.trade_history if t.is_winner)
        return round(wins / len(self.trade_history), 4)

    def summary(self) -> dict:
        return {
            "equity":           round(self.equity, 2),
            "capital":          round(self.capital, 2),
            "starting_capital": self.starting_capital,
            "total_return_pct": self.tracker.total_return_pct(),
            "realized_pnl":     round(self.total_realized_pnl, 2),
            "unrealized_pnl":   round(self.total_unrealized_pnl, 2),
            "open_positions":   len(self.positions),
            "total_trades":     len(self.trade_history),
            "win_rate":         f"{self.win_rate * 100:.1f}%",
            "sharpe_ratio":     self.tracker.sharpe_ratio(),
            "max_drawdown":     f"{self.tracker.max_drawdown * 100:.2f}%",
            "halted":           self.halted,
        }


# ── Standalone demo ────────────────────────────────────────

if __name__ == "__main__":
    sim = Simulator(starting_capital=100_000)
    print("Animus AI — Simulator demo\n")

    orders = [
        ("BTC/USD", "LONG",  0.05,  67_000.0),
        ("ETH/USD", "LONG",  1.0,    3_500.0),
        ("SPY",     "LONG",  5.0,      524.0),
    ]

    for symbol, direction, qty, price in orders:
        o = sim.open_position(symbol, direction, qty, price)
        print(f"  OPEN  {symbol:<10}  {direction:<6}  qty={o.fill_qty}  "
              f"fill={o.fill_price:.2f}  [{o.status}]  latency={o.latency_ms}ms")

    # Simulate a price move
    sim.update_prices({"BTC/USD": 68_500, "ETH/USD": 3_420, "SPY": 528})

    for symbol in list(sim.positions.keys()):
        price = sim.positions[symbol].current_price
        o = sim.close_position(symbol, price)
        if o:
            t = sim.trade_history[-1]
            print(f"  CLOSE {symbol:<10}  pnl={t.realized_pnl:+.2f}")

    print("\nPortfolio summary:")
    for k, v in sim.summary().items():
        print(f"  {k:<22} {v}")
