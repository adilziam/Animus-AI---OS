Animus AI — ML-Powered Trading Simulation Platform
-----------------------------------------------------------
A real-time trading simulation platform powered by proprietary machine learning. Live market data, zero capital risk.


What Is Animus AI?
Animus AI is a full-stack trading simulation platform that connects to live market feeds, runs ML-generated signals across equities, crypto, and forex, and lets users simulate trades in a realistic paper environment — without putting real capital on the line.
Built from zero to live as a solo product: scoped requirements, designed the data ingestion pipeline, led engineering, and launched to 5,000 users with a live frontend.
The signal engine is proprietary and not included in this repository. This repo contains the frontend, data pipeline scaffolding, and simulation infrastructure.

Features
--------------------------------------------------------------------------------------
Live market data ingestion — real-time price feeds across crypto, equities, and forex
Realistic paper execution — fill modeling with simulated slippage and latency
ML signal integration — directional signals surfaced via a proprietary backend (76% accuracy)
Performance dashboard — live P&L, win rate, drawdown, and attribution tracking
Multi-asset coverage — 14+ markets in a unified portfolio view
Responsive frontend — ships as a single index.html, deployable anywhere


Tech Stack
LayerTechnologyFrontendVanilla HTML/CSS/JS (zero dependencies)FontsGoogle Fonts — Syne + DM MonoData pipelinePython (see /src)DeploymentAny static host (Vercel, Netlify, GitHub Pages)

Repository Structure
animus-ai/
├── public/
│   └── index.html          # Full frontend (self-contained)
├── src/
│   ├── feed.py             # Market data ingestion scaffold
│   ├── simulator.py        # Paper trade execution engine
│   └── signals.py          # Signal interface (proprietary logic not included)
├── data/
│   └── sample_feed.json    # Sample market data for local dev
├── .gitignore
├── LICENSE
├── package.json
└── README.md

Getting Started
1. Clone the repo
bashgit clone https://github.com/your-username/animus-ai.git
cd animus-ai
2. Run the frontend locally
The frontend is a single self-contained HTML file — no build step required.
bash# Option A: open directly
open public/index.html

# Option B: serve locally
npx serve public
# or
python3 -m http.server 8080 --directory public
3. Run the data pipeline (optional)
Requires Python 3.9+.
bashpip install -r requirements.txt
python src/feed.py

Deployment
Deploy to GitHub Pages
bash# From repo root
git subtree push --prefix public origin gh-pages
Then enable GitHub Pages in your repo settings → branch: gh-pages → folder: /root.
Deploy to Vercel / Netlify
Both platforms auto-detect the public/ folder. Just connect your repo and deploy.

Signal Engine
The ML signal engine that powers Animus AI — including model architecture, feature pipeline, and weighting logic — is proprietary and not open-sourced.
This repo exposes only the signal interface contract. To connect your own model:
python# src/signals.py

def get_signal(asset: str, market_state: dict) -> dict:
    """
    Replace this stub with your own signal logic.

    Returns:
        {
            "asset": str,
            "direction": "LONG" | "SHORT" | "FLAT",
            "confidence": float,   # 0.0 – 1.0
        }
    """
    raise NotImplementedError("Plug in your own signal engine here.")

Sample Data
A sample market feed is included at data/sample_feed.json for local development and testing.
json{
  "timestamp": "2026-03-21T14:32:00Z",
  "feeds": [
    { "symbol": "BTC/USD", "price": 67420.50, "change_pct": 2.14 },
    { "symbol": "ETH/USD", "price": 3512.30,  "change_pct": 1.87 },
    { "symbol": "SPY",     "price": 524.71,   "change_pct": 0.32 },
    { "symbol": "NVDA",    "price": 902.18,   "change_pct": -0.64 },
    { "symbol": "GOLD",    "price": 2341.40,  "change_pct": 0.51 }
  ]
}

License
MIT — see LICENSE.
The signal engine and proprietary ML logic are excluded from this license and are not part of this repository.

Contact
Built by the Animus AI team. For partnership or licensing inquiries: hello@animusai.com
