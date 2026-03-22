"""
server.py — WebSocket Server
Animus AI

Runs a WebSocket server that:
  1. Streams live market ticks from MarketFeed
  2. Runs the SignalEngine on each tick
  3. Auto-executes paper trades via Simulator when signals fire
  4. Broadcasts state updates to all connected clients

Client message format (JSON):
  { "action": "open",  "symbol": "BTC/USD", "direction": "LONG", "qty": 0.1 }
  { "action": "close", "symbol": "BTC/USD" }
  { "action": "summary" }

Server broadcast format (JSON):
  {
    "type":      "tick" | "signal" | "order" | "summary",
    "timestamp": "...",
    "data":      { ... }
  }
"""

import asyncio
import json
import logging
import signal
import sys
from datetime import datetime, timezone

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
except ImportError:
    print("websockets not installed. Run: pip install websockets")
    sys.exit(1)

sys.path.insert(0, ".")
from src.feed      import MarketFeed
from src.signals   import SignalEngine
from src.simulator import Simulator


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("animus")

# ── Config ─────────────────────────────────────────────────

HOST          = "localhost"
PORT          = 8765
TICK_INTERVAL = 1.0          # seconds between market ticks
AUTO_TRADE    = True         # auto-execute signals as paper trades
SIGNAL_QTY    = {            # default paper quantity per asset
    "BTC/USD": 0.05,
    "ETH/USD": 0.5,
    "SOL/USD": 2.0,
    "SPY":     2.0,
    "NVDA":    0.5,
    "TSLA":    1.0,
    "GOLD":    0.2,
    "EUR/USD": 1000.0,
}


# ── Helpers ────────────────────────────────────────────────

def now() -> str:
    return datetime.now(timezone.utc).isoformat()

def make_message(msg_type: str, data: dict) -> str:
    return json.dumps({"type": msg_type, "timestamp": now(), "data": data})


# ── Server ──────────────────────────────────────────────────

class AnimusServer:

    def __init__(self):
        self.feed      = MarketFeed(tick_interval=TICK_INTERVAL)
        self.engine    = SignalEngine()
        self.sim       = Simulator()
        self.clients:  set[WebSocketServerProtocol] = set()

    # ── Broadcast ──────────────────────────────────────────

    async def broadcast(self, message: str) -> None:
        if not self.clients:
            return
        await asyncio.gather(
            *[ws.send(message) for ws in self.clients],
            return_exceptions=True,
        )

    # ── Market loop ────────────────────────────────────────

    async def market_loop(self) -> None:
        log.info("Market loop started")
        loop = asyncio.get_event_loop()

        while True:
            ticks = await loop.run_in_executor(None, self.feed.snapshot)

            prices = {t.symbol: t.price for t in ticks}
            self.sim.update_prices(prices)

            tick_data = [t.to_dict() for t in ticks]
            await self.broadcast(make_message("tick", {"feeds": tick_data}))

            # Run signals and auto-trade
            signals_fired = []
            for tick in ticks:
                sig = self.engine.update(tick.symbol, tick.price)
                if sig is None:
                    continue

                await self.broadcast(make_message("signal", sig.to_dict()))

                if AUTO_TRADE and sig.direction != "FLAT":
                    await self._auto_trade(sig.symbol, sig.direction,
                                           sig.price, sig.confidence)
                    signals_fired.append(sig.to_dict())

            # Broadcast portfolio summary every tick
            await self.broadcast(make_message("summary", self.sim.summary()))

            await asyncio.sleep(TICK_INTERVAL)

    async def _auto_trade(
        self, symbol: str, direction: str, price: float, confidence: float
    ) -> None:
        """Auto-manage a paper position based on signal direction."""
        sim = self.sim

        if symbol in sim.positions:
            existing = sim.positions[symbol]
            # If signal flips direction, close existing first
            if existing.direction != direction:
                loop = asyncio.get_event_loop()
                order = await loop.run_in_executor(
                    None, sim.close_position, symbol, price
                )
                if order:
                    log.info(f"AUTO CLOSE  {symbol}  {existing.direction}  "
                             f"pnl={sim.trade_history[-1].realized_pnl:+.2f}")
                    await self.broadcast(make_message("order", order.to_dict()))
        else:
            qty = SIGNAL_QTY.get(symbol, 1.0)
            loop = asyncio.get_event_loop()
            order = await loop.run_in_executor(
                None, sim.open_position, symbol, direction, qty, price
            )
            if order.status in ("FILLED", "PARTIAL"):
                log.info(f"AUTO OPEN   {symbol}  {direction}  "
                         f"conf={confidence:.3f}  fill={order.fill_price:.4f}")
                await self.broadcast(make_message("order", order.to_dict()))

    # ── Client handler ─────────────────────────────────────

    async def handler(self, ws: WebSocketServerProtocol) -> None:
        self.clients.add(ws)
        addr = ws.remote_address
        log.info(f"Client connected    {addr}  (total: {len(self.clients)})")

        # Send current state immediately on connect
        await ws.send(make_message("summary", self.sim.summary()))

        try:
            async for raw in ws:
                await self._handle_message(ws, raw)
        except Exception:
            pass
        finally:
            self.clients.discard(ws)
            log.info(f"Client disconnected {addr}  (total: {len(self.clients)})")

    async def _handle_message(self, ws: WebSocketServerProtocol, raw: str) -> None:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            await ws.send(make_message("error", {"msg": "Invalid JSON"}))
            return

        action = msg.get("action")

        if action == "open":
            symbol    = msg.get("symbol", "")
            direction = msg.get("direction", "LONG")
            qty       = float(msg.get("qty", 1.0))
            price     = self.feed.states[symbol].price if symbol in self.feed.states else 0.0
            loop      = asyncio.get_event_loop()
            order     = await loop.run_in_executor(
                None, self.sim.open_position, symbol, direction, qty, price
            )
            await ws.send(make_message("order", order.to_dict()))

        elif action == "close":
            symbol = msg.get("symbol", "")
            price  = self.feed.states[symbol].price if symbol in self.feed.states else 0.0
            loop   = asyncio.get_event_loop()
            order  = await loop.run_in_executor(
                None, self.sim.close_position, symbol, price
            )
            if order:
                await ws.send(make_message("order", order.to_dict()))
            else:
                await ws.send(make_message("error", {"msg": f"No position in {symbol}"}))

        elif action == "summary":
            await ws.send(make_message("summary", self.sim.summary()))

        elif action == "positions":
            data = {s: p.to_dict() for s, p in self.sim.positions.items()}
            await ws.send(make_message("positions", data))

        elif action == "trades":
            data = [t.to_dict() for t in self.sim.trade_history[-50:]]
            await ws.send(make_message("trades", {"trades": data}))

        else:
            await ws.send(make_message("error", {"msg": f"Unknown action: {action}"}))

    # ── Start ──────────────────────────────────────────────

    async def start(self) -> None:
        log.info(f"Animus AI server starting on ws://{HOST}:{PORT}")

        async with websockets.serve(self.handler, HOST, PORT):
            await self.market_loop()


# ── Entry point ────────────────────────────────────────────

def main() -> None:
    server = AnimusServer()

    def _shutdown(sig, frame):
        log.info("Shutting down...")
        sys.exit(0)

    signal.signal(signal.SIGINT,  _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        log.info("Server stopped.")


if __name__ == "__main__":
    main()
