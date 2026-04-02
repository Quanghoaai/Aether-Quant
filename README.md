# 🚀 Aether Quant - Hybrid Capital Allocation (HCA)

A semi-automated algorithmic trading system tailored for the Vietnam Stock Market (HOSE/HNX). The pipeline utilizes a Multi-Factor Scoring Architecture to evaluate momentum, price action, and volume profiles, automatically optimizing a designated portfolio through automated alpha swapping constraints.

## 🌟 Key Features
- **Robust Data Pipeline (VNStock)**: Efficiently retrieves highly accurate historical EOD data for VNINDEX and specific trackers directly from KBS.
- **Multi-Factor Scoring Engine**: Evaluates assets based on:
  - Relative Strength against the benchmark (35%)
  - Price Action vs MA20/MA50 trends (25%)
  - Volume Profile breakout anomalies (20%)
  - Volatility assessment via ATR (10%)
  - Short-term Sector Flow & Momentum (10%)
- **Dynamic Execution Logic**: Enforces strict position sizing constraints, dynamic Stop-Loss thresholds, Trailing Stops, and executes automated "Alpha Swapping" to replace lagging primary picks with highly-ranked watchlist alternatives.
- **Serverless Automation**: Fully containerized schedule running daily on GitHub Actions to evaluate EoD portfolios, log historical metrics to `.csv`, output execution logs to `.json`, and send Email summaries without local compute environments.

## 📂 Architecture & Agents

| Component | Description |
|-----------|-------------|
| `data_pipeline.py` | Connects securely to the Vietnam market APIs using `vnstock`. |
| `scoring.py` | Consolidates variables and maps the quantitative scoring matrix. |
| `ranking.py` | Computes aggregate ranks and dynamically classifies roles (PRIMARY, ALPHA, SECONDARY). |
| `execution.py`| Simulates localized portfolio tracking constraints and evaluates risk models. |
| `reporting.py` | Structures reporting payloads and broadcasts HTML emails. |
| `main.py` | Argparse-driven entry logic for CLI execution. |

## 🚀 Quickstart & Deployment

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/Quanghoaai/Aether-Quant.git
   cd Aether-Quant
   ```
2. **Install Requirements:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Environment Setup:**
   Create a `.env` file at the root to store your `VNSTOCK_API_KEY`:
   ```env
   VNSTOCK_API_KEY=YOUR_API_KEY_HERE
   ```
4. **Execution Test:**
   ```bash
   python main.py --mode hybrid --primary HHV --watchlist "TOS,NKG,AAS" --cap 50000000 --min_score 3.8
   ```

## ⚙️ Automated Github Deployment 
To make this run reliably every morning at 07:00 AM (ICT):
- Create the following GitHub Repository Secrets under `Settings > Secrets and variables > Actions`:
  - `VNSTOCK_API_KEY`: Core API Key.
  - `EMAIL_USER`: Email sending the daily digest.
  - `EMAIL_PASS`: App password of the transmitting email.
  - `EMAIL_RECEIVER`: Recipient's destination email.
  - `TELEGRAM_BOT_TOKEN`: The token of your Telegram bot.
  - `TELEGRAM_CHAT_ID`: Your personal Telegram ID/Group ID to receive signals.
