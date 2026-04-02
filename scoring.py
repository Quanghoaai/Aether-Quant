import pandas as pd
import numpy as np

def score_rs(stock_df, benchmark_df, window=20):
    if benchmark_df is None or benchmark_df.empty or len(stock_df) < window:
        return 2.5
    
    stock_return = stock_df['Close'].pct_change(window).iloc[-1]
    bench_return = benchmark_df['Close'].pct_change(window).iloc[-1]
    
    rs = stock_return - bench_return
    if rs > 0.10: return 5.0
    elif rs > 0.05: return 4.0
    elif rs > 0: return 3.5
    elif rs > -0.05: return 2.0
    else: return 1.0

def score_price_action(stock_df):
    if len(stock_df) < 50: return 2.5
    close = stock_df['Close'].iloc[-1]
    ma20 = stock_df['MA20'].iloc[-1]
    ma50 = stock_df['MA50'].iloc[-1]
    
    score = 0
    if close > ma20: score += 2.5
    if close > ma50: score += 2.5
    
    if close < ma20 and close < ma50: score = 1.0
    return min(5.0, max(0.0, score))

def score_vol_profile(stock_df):
    if len(stock_df) < 20: return 2.5
    vol = stock_df['Volume'].iloc[-1]
    vol_sma = stock_df['Vol_SMA20'].iloc[-1]
    
    if pd.isna(vol) or pd.isna(vol_sma) or vol_sma == 0:
        return 2.5
        
    ratio = vol / vol_sma
    if ratio > 2.0: return 5.0
    elif ratio > 1.5: return 4.0
    elif ratio > 1.0: return 3.0
    elif ratio > 0.5: return 2.0
    else: return 1.0

def score_volatility(stock_df):
    if len(stock_df) < 14: return 2.5
    atr = stock_df['ATR'].iloc[-1]
    close = stock_df['Close'].iloc[-1]
    
    if pd.isna(atr) or pd.isna(close) or close == 0:
        return 2.5
        
    atr_pct = atr / close
    if atr_pct < 0.02: return 5.0
    elif atr_pct < 0.03: return 4.0
    elif atr_pct < 0.04: return 3.0
    elif atr_pct < 0.06: return 2.0
    else: return 1.0

def score_sector_flow(stock_df):
    if len(stock_df) < 10: return 2.5
    ret = stock_df['Close'].pct_change(5).iloc[-1]
    
    if ret > 0.05: return 5.0
    elif ret > 0.02: return 4.0
    elif ret > 0: return 3.0
    elif ret > -0.02: return 2.0
    else: return 1.0

def calculate_multi_factor_score(stock_df, benchmark_df):
    weights = {
        'RS': 0.35,
        'Price_Action': 0.25,
        'Volume_Profile': 0.20,
        'Volatility': 0.10,
        'Sector_Flow': 0.10
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
