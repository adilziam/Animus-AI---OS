"""
feed.py — Market Data Ingestion Engine
Animus AI

Generates a realistic simulated market feed using:
  - Geometric Brownian Motion for price paths
  - Volatility clustering (GARCH-like variance process)
  - Correlated asset movements via a common market shock
  - Bid/ask spread simulation
"""

import math
import random
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Generator


# ── Asset universe ─────────────────────────────────────────

ASSETS = {
    "BTC/USD": {"price": 67_000.00, "vol": 0.025, "drift": 0.0001,  "spread_bps": 3},
    "ETH/USD": {"price":  3_500.00, "vol": 0.028, "drift": 0.00008, "spread_bps": 4},
    "SOL/USD": {"price":    183.00, "vol": 0.035, "drift": 0.00012, "spread_bps": 6},
    "SPY":     {"price":    524.00, "vol": 0.008, "drift": 0.00003, "spread_bps": 1},
    "NVDA":    {"price":    900.00, "vol": 0.022, "drift": 0.00006, "spread_bps": 2},
    "TSLA":    {"price":    241.00, "vol": 0.030, "drift": 0.00004, "spread_bps": 3},
    "GOLD":    {"price":  2_340.00, "vol": 0.006, "drift": 0.00002, "spread_bps": 2},
    "EUR/USD": {"price":      1.08, "vol": 0.004, "drift": 0.00001, "spread_bps": 1},
}


# ── Data structures ────────────────────────────────────────

@dataclass
class Tick:
    symbol:     str
    price:      float
    bid:        float
    ask:        float
    change_pct: float
    volume:     float
    timestamp:  str

    def to_dict(self) -> dict:
        return {
            "symbol":     self.symbol,
            "price":      self.price,
            "bid":        self.bid,
            "ask":        self.ask,
            "change_pct": self.change_pct,
            "volume":     self.volume,
            "timestamp":  self.timestamp,
        }


@dataclass
class AssetState:
    symbol:       str
    price:        float
    prev_close:   float
    base_vol:     float
    drift:        float
    spread_bps:   float
    returns:      deque = field(default_factory=lambda: deque(maxlen=60))
    vol_variance: float = 0.0

    @property
    def vol(self) -> float:
        return max(math.sqrt(self.vol_variance), self.base_vol * 0.3)

    def to_tick(self) -> Tick:
        spread = self.price * (self.spread_bps / 10_000)
        half   = spread / 2
        change = ((self.price - self.prev_close) / self.prev_close) * 100
        volume = max(abs(random.gauss(1_000, 300)) * (self.vol / self.base_vol), 1)
        return Tick(
            symbol=self.symbol,
            price=round(self.price, 6),
            bid=round(self.price - half, 6),
            ask=round(self.price + half, 6),
            change_pct=round(change, 4),
            volume=round(volume, 2),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


# ── Feed engine ────────────────────────────────────────────

class MarketFeed:
    """
    Simulated market data feed with GBM + GARCH volatility.
    Correlated assets share a common market shock factor.
    """

    GARCH_ALPHA = 0.10
    GARCH_BETA  = 0.85

    def __init__(self, tick_interval: float = 1.0):
        self.tick_interval = tick_interval
        self.states: dict[str, AssetState] = {}
        self._init_states()

    def _init_states(self) -> None:
        for symbol, cfg in ASSETS.items():
            p = cfg["price"]
            state = AssetState(
                symbol=symbol,
                price=p,
                prev_close=p,
                base_vol=cfg["vol"],
                drift=cfg["drift"],
                spread_bps=cfg["spread_bps"],
            )
            state.vol_variance = cfg["vol"] ** 2
            self.states[symbol] = state

    def _step(self, state: AssetState, market_shock: float) -> None:
        """Advance one tick: GARCH variance update + GBM price step."""
        # Use minimum 1 second of "trading time" for sim mode (tick_interval=0)
        effective_interval = max(self.tick_interval, 1.0)
        dt = effective_interval / (252 * 6.5 * 3600)

        # GARCH(1,1) variance update
        omega = (1 - self.GARCH_ALPHA - self.GARCH_BETA) * state.base_vol ** 2
        last_ret = state.returns[-1] if state.returns else 0.0
        state.vol_variance = (
            self.GARCH_ALPHA * last_ret ** 2
            + self.GARCH_BETA * state.vol_variance
            + omega
        )

        idio = random.gauss(0, state.vol * math.sqrt(dt))
        beta = 0.6 if state.symbol not in ("GOLD", "EUR/USD") else 0.1
        ret  = state.drift * dt + idio + beta * market_shock * math.sqrt(dt)

        state.returns.append(ret)
        state.price = max(state.price * math.exp(ret), 0.0001)

    def snapshot(self) -> list[Tick]:
        shock = random.gauss(0, 0.004)
        ticks = []
        for state in self.states.values():
            self._step(state, shock)
            ticks.append(state.to_tick())
        return ticks

    def stream(self) -> Generator[list[Tick], None, None]:
        while True:
            yield self.snapshot()
            time.sleep(self.tick_interval)

    def prices(self) -> dict[str, float]:
        return {s: st.price for s, st in self.states.items()}

    def reset_close(self) -> None:
        for state in self.states.values():
            state.prev_close = state.price


# ── Standalone runner ──────────────────────────────────────

if __name__ == "__main__":
    feed = MarketFeed(tick_interval=1.0)
    print("Animus AI — Feed  |  Ctrl+C to stop\n")
    print(f"{'SYMBOL':<12} {'PRICE':>12} {'CHG%':>8} {'VOL':>8}")
    print("─" * 50)
    try:
        for ticks in feed.stream():
            for t in ticks:
                chg = f"+{t.change_pct:.3f}%" if t.change_pct >= 0 else f"{t.change_pct:.3f}%"
                print(f"{t.symbol:<12} {t.price:>12.4f} {chg:>8} {t.volume:>8.1f}")
            print()
    except KeyboardInterrupt:
        print("\nStopped.")
