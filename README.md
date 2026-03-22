# Animus AI

**ML-powered real-time trading simulation.** Live market data, zero capital risk.

![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)
![Status](https://img.shields.io/badge/status-live-brightgreen?style=flat-square)
![Users](https://img.shields.io/badge/users-5%2C000%2B-blue?style=flat-square)
![Accuracy](https://img.shields.io/badge/signal%20accuracy-76%25-00e5a0?style=flat-square)

---

## Overview

Animus AI is a full-stack trading simulation platform — live market feeds, ML-generated signals, and realistic paper execution across equities, crypto, and forex. No real capital required.

Built solo from zero to launch: scoped requirements, designed the data ingestion pipeline, led engineering, and shipped to **5,000 users** with a live frontend.

> The signal engine is proprietary and not included here. This repo contains the frontend, data pipeline scaffold, and simulation infrastructure.

---

## Features

| | |
|---|---|
| 📡 | Live price feeds across crypto, equities, and forex |
| ⚡ | Paper execution with slippage + latency modeling |
| 🧠 | ML signal integration — 76% directional accuracy |
| 📊 | Live P&L, win rate, drawdown, and attribution |
| 🔗 | 14+ markets in a unified portfolio view |
| 🖥️ | Single `index.html` — deployable anywhere |

---

## Stack

| Layer | Tech |
|---|---|
| Frontend | Vanilla HTML / CSS / JS |
| Fonts | Syne + DM Mono (Google Fonts) |
| Pipeline | Python 3.9+ |
| Deploy | Vercel · Netlify · GitHub Pages |

---

## Structure

```
animus-ai/
├── public/
│   └── index.html        # Self-contained frontend
├── src/
│   ├── feed.py           # Market data ingestion
│   ├── simulator.py      # Paper trade execution
│   └── signals.py        # Signal interface stub
├── data/
│   └── sample_feed.json  # Sample data for local dev
├── .gitignore
├── LICENSE
├── package.json
└── README.md
```

---

## Quick Start

**Frontend** — no build step needed:

```bash
git clone https://github.com/your-username/animus-ai.git
cd animus-ai
open public/index.html
# or: npx serve public
```

**Data pipeline** — requires Python 3.9+:

```bash
pip install -r requirements.txt
python src/feed.py
```

---

## Deploy

**GitHub Pages**
```bash
git subtree push --prefix public origin gh-pages
```
Then enable Pages in repo Settings → branch `gh-pages`.

**Vercel / Netlify** — connect the repo, set publish dir to `public/`, deploy.

---

## Signal Engine

The ML signal logic is **proprietary and not included**. Plug in your own via `src/signals.py`:

```python
def get_signal(asset: str, market_state: dict) -> dict:
    # Return: { "asset", "direction": LONG|SHORT|FLAT, "confidence": 0–1 }
    raise NotImplementedError("Add your signal logic here.")
```

---

## License


Signal engine and proprietary ML logic are excluded.

---

*For partnerships or licensing: Contact Me
