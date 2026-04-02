import pandas as pd
import numpy as np

# ===========================
# FACTOR 1: Relative Strength (Multi-Timeframe)
# ===========================
def score_rs(stock_df, benchmark_df):
    """Multi-timeframe RS: 5D(20%) + 20D(50%) + 60D(30%)"""
    if benchmark_df is None or benchmark_df.empty or len(stock_df) < 60:
        return 2.5
    
    def _rs_at_window(w):
        if len(stock_df) < w or len(benchmark_df) < w:
            return 0
        sr = stock_df['Close'].pct_change(w).iloc[-1]
        br = benchmark_df['Close'].pct_change(w).iloc[-1]
        return sr - br if not (pd.isna(sr) or pd.isna(br)) else 0
    
    rs_5d = _rs_at_window(5)
    rs_20d = _rs_at_window(20)
    rs_60d = _rs_at_window(60)
    
    composite = (rs_5d * 0.20) + (rs_20d * 0.50) + (rs_60d * 0.30)
    
    if composite > 0.08: return 5.0
    elif composite > 0.04: return 4.5
    elif composite > 0.02: return 4.0
    elif composite > 0: return 3.5
    elif composite > -0.02: return 2.5
    elif composite > -0.05: return 2.0
    else: return 1.0

# ===========================
# FACTOR 2: Price Action + Breakout Detection
# ===========================
def score_price_action(stock_df):
    """Enhanced: MA alignment + Breakout + Pullback + Golden/Death Cross."""
    if len(stock_df) < 50: return 2.5
    
    close = stock_df['Close'].iloc[-1]
    ma10 = stock_df['MA10'].iloc[-1] if 'MA10' in stock_df.columns else stock_df['MA20'].iloc[-1]
    ma20 = stock_df['MA20'].iloc[-1]
    ma50 = stock_df['MA50'].iloc[-1]
    
    score = 0.0
    
    # MA Alignment (0-2 points)
    if close > ma20 and close > ma50:
        score += 1.5
        if ma20 > ma50:  # Perfect alignment
            score += 0.5
    elif close < ma20 and close < ma50:
        score += 0.0  # Bearish
    else:
        score += 0.75  # Mixed
    
    # Breakout Detection (0-1.5 points)
    if 'High_20D' in stock_df.columns:
        high_20d = stock_df['High_20D'].iloc[-2]  # Yesterday's 20D high
        if not pd.isna(high_20d) and close > high_20d:
            score += 1.5  # Fresh breakout!
        elif close > high_20d * 0.97:  # Within 3% of breakout
            score += 0.75
    
    # Pullback to MA20 (0-0.5 points)
    if abs(close - ma20) / ma20 < 0.02 and close > ma50:
        score += 0.5  # Healthy pullback to support
    
    # Golden/Death Cross (0-0.5 points)
    if len(stock_df) >= 3:
        prev_ma20 = stock_df['MA20'].iloc[-3]
        prev_ma50 = stock_df['MA50'].iloc[-3]
        if not pd.isna(prev_ma20) and not pd.isna(prev_ma50):
            if prev_ma20 < prev_ma50 and ma20 > ma50:
                score += 0.5  # Golden Cross
            elif prev_ma20 > prev_ma50 and ma20 < ma50:
                score -= 0.5  # Death Cross penalty
    
    return min(5.0, max(0.0, score))

# ===========================
# FACTOR 3: Volume Profile
# ===========================
def score_vol_profile(stock_df):
    """Volume expansion detection with RSI confirmation."""
    if len(stock_df) < 20: return 2.5
    vol = stock_df['Volume'].iloc[-1]
    vol_sma = stock_df['Vol_SMA20'].iloc[-1]
    
    if pd.isna(vol) or pd.isna(vol_sma) or vol_sma == 0:
        return 2.5
        
    ratio = vol / vol_sma
    
    # Bonus: Volume spike WITH price up = strong signal
    ret_today = stock_df['Return'].iloc[-1] if 'Return' in stock_df.columns else 0
    
    base_score = 0
    if ratio > 2.5: base_score = 5.0
    elif ratio > 2.0: base_score = 4.5
    elif ratio > 1.5: base_score = 4.0
    elif ratio > 1.0: base_score = 3.0
    elif ratio > 0.5: base_score = 2.0
    else: base_score = 1.0
    
    # Confirmation: high volume + positive return = bullish
    if ratio > 1.5 and ret_today > 0.01:
        base_score = min(5.0, base_score + 0.5)
    # Warning: high volume + negative return = distribution
    elif ratio > 1.5 and ret_today < -0.01:
        base_score = max(1.0, base_score - 1.0)
    
    return base_score

# ===========================
# FACTOR 4: Volatility (Bell Curve)
# ===========================
def score_volatility(stock_df):
    """Bell-curve: ATR 2-4% = best for swing trading. Too low = dead, too high = risky."""
    if len(stock_df) < 14: return 2.5
    atr = stock_df['ATR'].iloc[-1]
    close = stock_df['Close'].iloc[-1]
    
    if pd.isna(atr) or pd.isna(close) or close == 0:
        return 2.5
        
    atr_pct = atr / close
    
    # Bell curve: sweet spot at 2-4%
    if 0.025 <= atr_pct <= 0.035:
        return 5.0  # Sweet spot
    elif 0.02 <= atr_pct < 0.025 or 0.035 < atr_pct <= 0.04:
        return 4.0  # Good range
    elif 0.015 <= atr_pct < 0.02 or 0.04 < atr_pct <= 0.05:
        return 3.0  # Acceptable
    elif 0.01 <= atr_pct < 0.015 or 0.05 < atr_pct <= 0.06:
        return 2.0  # Too calm or too wild
    else:
        return 1.0  # Dead stock or extremely volatile

# ===========================
# FACTOR 5: Sector Flow + Momentum
# ===========================
def score_sector_flow(stock_df):
    """5-day momentum + RSI + MACD confirmation."""
    if len(stock_df) < 10: return 2.5
    
    ret_5d = stock_df['Close'].pct_change(5).iloc[-1]
    rsi = stock_df['RSI'].iloc[-1] if 'RSI' in stock_df.columns else 50
    macd_hist = stock_df['MACD_Hist'].iloc[-1] if 'MACD_Hist' in stock_df.columns else 0
    
    # Base score from 5D return
    if ret_5d > 0.05: base = 4.5
    elif ret_5d > 0.02: base = 3.5
    elif ret_5d > 0: base = 3.0
    elif ret_5d > -0.02: base = 2.0
    else: base = 1.0
    
    # RSI confirmation bonus
    if not pd.isna(rsi):
        if 50 < rsi < 70:
            base = min(5.0, base + 0.5)  # Strong momentum zone
        elif rsi > 80:
            base = max(1.0, base - 1.0)  # Overbought penalty
        elif rsi < 30:
            base = min(5.0, base + 0.3)  # Oversold bounce potential
    
    # MACD histogram direction
    if not pd.isna(macd_hist):
        if macd_hist > 0:
            base = min(5.0, base + 0.25)
    
    return min(5.0, max(0.0, base))

# ===========================
# COMPOSITE SCORING
# ===========================
def calculate_multi_factor_score(stock_df, benchmark_df):
    weights = {
        'RS': 0.30,
        'Price_Action': 0.25,
        'Volume_Profile': 0.20,
        'Volatility': 0.10,
        'Sector_Flow': 0.15
    }
    
    s_rs = score_rs(stock_df, benchmark_df)
    s_pa = score_price_action(stock_df)
    s_vol = score_vol_profile(stock_df)
    s_vty = score_volatility(stock_df)
    s_sf = score_sector_flow(stock_df)
    
    total_score = (s_rs * weights['RS'] +
                   s_pa * weights['Price_Action'] +
                   s_vol * weights['Volume_Profile'] +
                   s_vty * weights['Volatility'] +
                   s_sf * weights['Sector_Flow'])
                   
    return {
        'score': round(total_score, 2),
        'RS_score': s_rs,
        'Price_Action_score': s_pa,
        'Volume_Profile_score': s_vol,
        'Volatility_score': s_vty,
        'Sector_Flow_score': s_sf
    }
