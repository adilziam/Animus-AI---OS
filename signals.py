"""
signals.py — ML Signal Engine
Animus AI

A real logistic regression model trained online on price features.
Generates directional signals (LONG / SHORT / FLAT) with confidence scores.

Feature set per asset (computed from rolling price history):
  - momentum_5     : 5-tick return
  - momentum_20    : 20-tick return
  - rsi_14         : Relative Strength Index (14 periods)
  - vol_ratio      : short-term vol / long-term vol (vol regime)
  - mean_reversion : z-score of price vs 30-tick SMA
  - trend_strength : absolute slope of 10-tick linear regression

The model is updated incrementally (online learning) as new ticks arrive,
with a target label derived from the next-tick return sign.
"""

import math
import random
from collections import deque
from dataclasses import dataclass, field
from typing import Literal


Direction = Literal["LONG", "SHORT", "FLAT"]

# Signal confidence must exceed this threshold to act
CONFIDENCE_THRESHOLD = 0.54


# ── Feature engineering ────────────────────────────────────

def _sma(prices: list[float], n: int) -> float:
    window = prices[-n:]
    return sum(window) / len(window) if window else prices[-1]

def _std(prices: list[float], n: int) -> float:
    window = prices[-n:]
    if len(window) < 2:
        return 0.0
    mean = sum(window) / len(window)
    return math.sqrt(sum((x - mean) ** 2 for x in window) / len(window))

def _rsi(prices: list[float], n: int = 14) -> float:
    if len(prices) < n + 1:
        return 50.0
    gains, losses = [], []
    for i in range(-n, 0):
        delta = prices[i] - prices[i - 1]
        (gains if delta > 0 else losses).append(abs(delta))
    avg_gain = sum(gains) / n if gains else 0.0
    avg_loss = sum(losses) / n if losses else 0.0
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def _linreg_slope(prices: list[float], n: int) -> float:
    """Slope of OLS line through last n prices, normalized by mean price."""
    window = prices[-n:]
    if len(window) < 2:
        return 0.0
    n_  = len(window)
    x_  = list(range(n_))
    mx  = sum(x_) / n_
    my  = sum(window) / n_
    num = sum((x_[i] - mx) * (window[i] - my) for i in range(n_))
    den = sum((x_[i] - mx) ** 2 for i in range(n_)) or 1e-9
    return (num / den) / (my or 1e-9)

def extract_features(prices: list[float]) -> list[float] | None:
    """
    Returns a feature vector [f1..f6] or None if not enough history.
    All features are normalized to be roughly in [-1, 1].
    """
    if len(prices) < 30:
        return None

    p = prices
    # 1. Short momentum (5-tick return)
    mom5 = (p[-1] - p[-5]) / p[-5] * 100

    # 2. Medium momentum (20-tick return)
    mom20 = (p[-1] - p[-20]) / p[-20] * 100

    # 3. RSI (rescale 0-100 → -1 to 1)
    rsi = (_rsi(p, 14) - 50) / 50

    # 4. Vol ratio: 5-tick std / 20-tick std (regime indicator)
    std5  = _std(p, 5)
    std20 = _std(p, 20)
    vol_ratio = (std5 / std20 - 1.0) if std20 > 0 else 0.0
    vol_ratio = max(min(vol_ratio, 3.0), -3.0)

    # 5. Mean reversion z-score vs 30-tick SMA
    sma30 = _sma(p, 30)
    std30 = _std(p, 30)
    z_score = ((p[-1] - sma30) / std30) if std30 > 0 else 0.0
    z_score = max(min(z_score, 3.0), -3.0)

    # 6. Trend strength (normalized slope of 10-tick regression)
    slope = _linreg_slope(p, 10) * 1000
    slope = max(min(slope, 3.0), -3.0)

    return [mom5, mom20, rsi, vol_ratio, z_score, slope]


# ── Online logistic regression ─────────────────────────────

class OnlineLogisticRegression:
    """
    SGD-trained logistic regression for binary classification.
    Trained online: each new labeled sample updates weights immediately.
    """

    def __init__(self, n_features: int, lr: float = 0.05, l2: float = 0.0001):
        self.lr = lr
        self.l2 = l2
        # Small random init
        self.w = [random.gauss(0, 0.1) for _ in range(n_features)]
        self.b = 0.0
        self.n_updates = 0

    def _sigmoid(self, z: float) -> float:
        z = max(min(z, 20), -20)
        return 1.0 / (1.0 + math.exp(-z))

    def predict_proba(self, x: list[float]) -> float:
        """P(label=1 | x)"""
        z = sum(self.w[i] * x[i] for i in range(len(x))) + self.b
        return self._sigmoid(z)

    def update(self, x: list[float], y: int) -> float:
        """SGD update with L2 regularization. Returns loss."""
        p   = self.predict_proba(x)
        err = p - y
        # Decaying learning rate
        lr = self.lr / (1 + 0.0001 * self.n_updates)
        for i in range(len(x)):
            self.w[i] -= lr * (err * x[i] + self.l2 * self.w[i])
        self.b -= lr * err
        self.n_updates += 1
        # Binary cross-entropy loss
        eps = 1e-9
        return -(y * math.log(p + eps) + (1 - y) * math.log(1 - p + eps))


# ── Signal state per asset ─────────────────────────────────

@dataclass
class AssetSignalState:
    symbol:  str
    prices:  deque = field(default_factory=lambda: deque(maxlen=200))
    model_long:  OnlineLogisticRegression = field(
        default_factory=lambda: OnlineLogisticRegression(6))
    model_short: OnlineLogisticRegression = field(
        default_factory=lambda: OnlineLogisticRegression(6))
    pending_features: list[float] | None = None
    pending_price:    float = 0.0
    total_signals:    int = 0
    correct_signals:  int = 0


@dataclass
class Signal:
    symbol:     str
    direction:  Direction
    confidence: float
    price:      float
    features:   dict

    def to_dict(self) -> dict:
        return {
            "symbol":     self.symbol,
            "direction":  self.direction,
            "confidence": self.confidence,
            "price":      self.price,
        }


# ── Signal engine ──────────────────────────────────────────

class SignalEngine:
    """
    Online ML signal engine. One logistic regression model per asset
    for LONG signals, one for SHORT signals.

    Each tick:
      1. Label the previous tick's features using the realized return.
      2. Update both models with the new label.
      3. Extract features for the current tick.
      4. Generate a signal if confidence > threshold.
    """

    def __init__(self, confidence_threshold: float = CONFIDENCE_THRESHOLD):
        self.threshold = confidence_threshold
        self.states: dict[str, AssetSignalState] = {
            symbol: AssetSignalState(symbol=symbol)
            for symbol in [
                "BTC/USD", "ETH/USD", "SOL/USD",
                "SPY", "NVDA", "TSLA", "GOLD", "EUR/USD",
            ]
        }

    def update(self, symbol: str, price: float) -> Signal | None:
        """
        Ingest a new price tick and return a signal if one fires.
        """
        state = self.states.get(symbol)
        if state is None:
            return None

        state.prices.append(price)
        prices = list(state.prices)

        # ── Label and train on previous tick ──
        if state.pending_features is not None and state.pending_price > 0:
            ret = (price - state.pending_price) / state.pending_price
            y_long  = 1 if ret > 0 else 0
            y_short = 1 if ret < 0 else 0
            state.model_long.update(state.pending_features, y_long)
            state.model_short.update(state.pending_features, y_short)

        # ── Extract features for current tick ──
        features = extract_features(prices)
        state.pending_features = features
        state.pending_price    = price

        if features is None:
            return None

        # ── Generate signal ──
        p_long  = state.model_long.predict_proba(features)
        p_short = state.model_short.predict_proba(features)

        if p_long > self.threshold and p_long > p_short:
            direction  = "LONG"
            confidence = p_long
        elif p_short > self.threshold and p_short > p_long:
            direction  = "SHORT"
            confidence = p_short
        else:
            direction  = "FLAT"
            confidence = max(p_long, p_short)

        state.total_signals += 1

        return Signal(
            symbol=symbol,
            direction=direction,
            confidence=round(confidence, 4),
            price=round(price, 6),
            features={
                "momentum_5":     round(features[0], 4),
                "momentum_20":    round(features[1], 4),
                "rsi_14":         round(features[2], 4),
                "vol_ratio":      round(features[3], 4),
                "mean_reversion": round(features[4], 4),
                "trend_strength": round(features[5], 4),
            },
        )

    def accuracy(self, symbol: str) -> float:
        state = self.states.get(symbol)
        if state is None or state.total_signals == 0:
            return 0.0
        return round(state.correct_signals / state.total_signals, 4)


# ── Standalone test ────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from src.feed import MarketFeed

    feed   = MarketFeed(tick_interval=0.2)
    engine = SignalEngine()

    print("Animus AI — Signal Engine  |  Ctrl+C to stop\n")
    print(f"{'SYMBOL':<12} {'DIR':<8} {'CONF':>6} {'PRICE':>12}")
    print("─" * 46)

    try:
        for ticks in feed.stream():
            for tick in ticks:
                sig = engine.update(tick.symbol, tick.price)
                if sig and sig.direction != "FLAT":
                    print(
                        f"{sig.symbol:<12} {sig.direction:<8} "
                        f"{sig.confidence:>6.3f} {sig.price:>12.4f}"
                    )
    except KeyboardInterrupt:
        print("\nStopped.")
