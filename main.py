"""
main.py — Animus AI Entry Point

Usage:
    python main.py           # start the WebSocket server
    python main.py --demo    # run a quick feed + signal demo in the terminal
"""

import sys


def run_server():
    from src.server import main
    main()


def run_demo():
    from src.feed    import MarketFeed
    from src.signals import SignalEngine
    from src.simulator import Simulator

    feed   = MarketFeed(tick_interval=0.3)
    engine = SignalEngine()
    sim    = Simulator(starting_capital=100_000)

    print("Animus AI — Demo Mode  |  Ctrl+C to stop")
    print("─" * 60)

    ticks_processed = 0
    try:
        for ticks in feed.stream():
            prices = {t.symbol: t.price for t in ticks}
            sim.update_prices(prices)

            for tick in ticks:
                sig = engine.update(tick.symbol, tick.price)
                if sig and sig.direction != "FLAT":
                    print(
                        f"  SIGNAL  {sig.symbol:<10}  {sig.direction:<6}  "
                        f"conf={sig.confidence:.3f}  price={sig.price:.4f}"
                    )
                    # Auto paper trade
                    if sig.symbol not in sim.positions:
                        qty = {"BTC/USD": 0.05, "ETH/USD": 0.5}.get(sig.symbol, 1.0)
                        sim.open_position(sig.symbol, sig.direction, qty, sig.price)

            ticks_processed += 1
            if ticks_processed % 20 == 0:
                s = sim.summary()
                print(f"\n  Portfolio  equity={s['equity']:,.2f}  "
                      f"pnl={s['realized_pnl']:+.2f}  "
                      f"trades={s['total_trades']}  "
                      f"win_rate={s['win_rate']}\n")

    except KeyboardInterrupt:
        print("\nStopped. Final summary:")
        for k, v in sim.summary().items():
            print(f"  {k:<22} {v}")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        run_demo()
    else:
        run_server()
