"""
Constants for Aether-Quant HCA System.
Centralized configuration to avoid magic numbers.
"""

# Trading Constants
DEFAULT_CAPITAL = 50_000_000  # 50M VND
MIN_CASH_RESERVE_PCT = 0.20  # 20% cash reserve
MAX_POSITIONS = 3  # Max concurrent positions
MIN_SCORE_BUY = 3.8  # Minimum score to buy
LOT_SIZE = 100  # VN market lot size

# Risk Management
HARD_STOP_PCT = -0.07  # -7% hard stop
TRAILING_STOP_TRIGGER_PCT = 0.08  # +8% profit to enable trailing
TRAILING_STOP_PCT = 0.03  # 3% drop from high triggers sell
TP1_PCT = 0.10  # Take Profit 1: +10%
TP2_PCT = 0.15  # Take Profit 2: +15%

# Fees
BUY_FEE_PCT = 0.0015  # 0.15% broker fee
SELL_FEE_PCT = 0.0025  # 0.25% broker + tax

# Data Pipeline
LOOKBACK_DAYS_6MO = 180
LOOKBACK_DAYS_1Y = 365
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2  # seconds

# Scoring Weights
SCORING_WEIGHTS = {
    'RS': 0.30,
    'Price_Action': 0.25,
    'Volume_Profile': 0.20,
    'Volatility': 0.10,
    'Sector_Flow': 0.15
}

RANKING_WEIGHTS = {
    'score': 0.45,
    'rs_rank': 0.35,
    'liquidity': 0.20
}

# Subscription
FREE_TRIAL_DAYS = 7

# Logging
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = "hca.log"
