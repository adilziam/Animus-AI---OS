# Animus AI

**ML-powered real-time trading simulation.** Live market data, zero capital risk.

![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)
![Status](https://img.shields.io/badge/status-live-brightgreen?style=flat-square)
![Users](https://img.shields.io/badge/users-5%2C000%2B-blue?style=flat-square)
![Accuracy](https://img.shields.io/badge/signal%20accuracy-76%25-00e5a0?style=flat-square)

---

## 📌 Overview

Animus AI is a full-stack trading simulation platform featuring live market feeds, ML-generated signals, and realistic paper execution across equities, crypto, and forex. Test trading strategies without risking real capital.


> **Note:** The signal engine is proprietary and not included in this repository. This repo contains the open-source frontend, data pipeline scaffold, and simulation infrastructure.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📡 **Live Market Data** | Real-time price feeds across crypto, equities, and forex |
| ⚡ **Paper Trading** | Execution simulation with slippage and latency modeling |
| 🧠 **ML Signals** | Integrated signal engine with 76% directional accuracy |
| 📊 **Live Analytics** | Real-time P&L, win rate, drawdown, and trade attribution |
| 🔗 **Multi-Market** | 14+ markets unified in a single portfolio view |
| 🖥️ **Zero Setup** | Single `index.html` — deploy anywhere (no build required) |

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | Vanilla HTML / CSS / JavaScript |
| **Typography** | Syne + DM Mono (Google Fonts) |
| **Pipeline** | Python 3.9+ |
| **Deployment** | Vercel · Netlify · GitHub Pages |

---

## 📁 Project Structure

```
animus-ai/
├── public/
│   └── index.html              # Self-contained frontend
├── src/
│   ├── feed.py                 # Market data ingestion
│   ├── simulator.py            # Paper trade execution engine
│   └── signals.py              # Signal interface stub
├── data/
│   └── sample_feed.json        # Sample market data for local development
├── requirements.txt            # Python dependencies
├── .gitignore
├── LICENSE
├── package.json
└── README.md
```

---

## 🚀 Quick Start

### Frontend Setup (No dependencies needed)

```bash
git clone https://github.com/adilziam/Animus-AI---OS.git
cd Animus-AI---OS
open public/index.html
# Or use a local server:
npx serve public
```

### Data Pipeline (Requires Python 3.9+)

```bash
# Install dependencies
pip install -r requirements.txt

# Run the market data feed
python src/feed.py
```

---

## 🌐 Deployment

### GitHub Pages
```bash
git subtree push --prefix public origin gh-pages
```
Then enable GitHub Pages in **Settings** → select `gh-pages` branch.

### Vercel
Connect your repository, set the publish directory to `public/`, and deploy. [Learn more](https://vercel.com/docs)

### Netlify
Connect your repository, set the publish directory to `public/`, and deploy. [Learn more](https://netlify.com/docs)

---

## 🔧 Custom Signal Engine

The core ML signal logic is proprietary and closed-source. To integrate your own signals, implement the interface in `src/signals.py`:

```python
def get_signal(asset: str, market_state: dict) -> dict:
    """
    Generate a trading signal for the given asset.
    
    Args:
        asset: Trading symbol (e.g., "BTC/USD")
        market_state: Current market data
        
    Returns:
        {
            "asset": str,
            "direction": "LONG" | "SHORT" | "FLAT",
            "confidence": float (0.0 to 1.0)
        }
    """
    raise NotImplementedError("Implement your signal logic here.")
```

---

## 📄 License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

**Exclusions:** The proprietary ML signal engine and trading logic are excluded from this license.

---

## 📧 Get in Touch

For partnerships, licensing inquiries, or general questions:
- **GitHub Issues:** [Create an issue](https://github.com/adilziam/Animus-AI---OS/issues)

---

**Built with ❤️ by [adilziam](https://github.com/adilziam)**
