import os
import pandas as pd
import numpy as np
import time
import ta
import socket
import requests
import requests.packages.urllib3.util.connection as urllib3_cn
from vnstock import Vnstock
from datetime import datetime, timedelta

# Force IPv4 STRICTLY to avoid ConnectionResetError on Linux/WSL
def allowed_gai_family():
    return socket.AF_INET
urllib3_cn.allowed_gai_family = allowed_gai_family

def fetch_data(tickers, start_date=None, end_date=None, period="6mo"):
    """
    Fetch EOD data for a list of tickers using VNStock with high reliability.
    """
    if not start_date or not end_date:
        today = datetime.today()
        # Ensure 6 months of data (approx 180 days)
        lookback_days = 180 if period == "6mo" else 365 if period == "1y" else 120
        start_date = (today - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")

    # Use VCI source - more stable for EOD history
    stock_engine = Vnstock().stock(symbol='VN30', source='VCI')
    
    data_dict = {}
    max_retries = 2 # Reduced retries to save time, but keeps it robust

    for symbol in tickers:
        if symbol == "VNINDEX": continue # Handle separately
        
        success = False
        for attempt in range(max_retries):
            try:
                print(f"Fetching data for {symbol} (Attempt {attempt + 1})...")
                # Increase timeout via requests if possible (vnstock uses requests)
                df = stock_engine.quote.history(symbol=symbol, start=start_date, end=end_date)
                
                if df is not None and not df.empty:
                    # Column standardization
                    rename_map = {
                        "time": "Date", "open": "Open", "high": "High", 
                        "low": "Low", "close": "Close", "volume": "Volume"
                    }
                    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
                    
                    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
                    if all(col in df.columns for col in required_cols):
                        # Ensure numeric
                        for col in required_cols:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                        df = df.dropna(subset=required_cols)
                        
                        # AGENT 1.5: Calculate Indicators (Essential for Scoring)
                        df = calculate_indicators(df)
                        
                        data_dict[symbol] = df
                        print(f"✅ Successful: {symbol} ({len(df)} days)")
                        success = True
                        break
                
                print(f"⚠️ No data for {symbol}, retrying...")
                time.sleep(1)
                
            except Exception as e:
                print(f"❌ Error {symbol}: {e}")
                time.sleep(2)
        
        if not success:
            print(f"🛑 Failed to fetch {symbol}")

    # Always fetch VNINDEX for Market Regime analysis
    try:
        print("Fetching data for VNINDEX...")
        df_vni = stock_engine.quote.history(symbol='VNINDEX', start=start_date, end=end_date)
        if df_vni is not None and not df_vni.empty:
            df_vni = df_vni.rename(columns={"time": "Date", "open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"})
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                df_vni[col] = pd.to_numeric(df_vni[col], errors='coerce')
            df_vni = calculate_indicators(df_vni)
            data_dict['VNINDEX'] = df_vni
            print("✅ VNINDEX fetched.")
    except Exception as e:
        print(f"⚠️ Warning: Could not fetch VNINDEX: {e}")

    return data_dict

def calculate_indicators(df):
    """
    Calculate technical indicators needed for scoring.
    """
    if df is None or df.empty:
        return df
        
    if "Date" in df.columns:
        df = df.sort_values("Date")
        
    # Moving Averages
    df['MA10'] = df['Close'].rolling(window=10).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA50'] = df['Close'].rolling(window=50).mean()
    df['Vol_SMA20'] = df['Volume'].rolling(window=20).mean()
    
    # Returns
    df['Return'] = df['Close'].pct_change()
    
    # ATR(14)
    try:
        indicator_atr = ta.volatility.AverageTrueRange(high=df['High'], low=df['Low'], close=df['Close'], window=14)
        df['ATR'] = indicator_atr.average_true_range()
    except:
        df['ATR'] = np.nan
    
    # RSI(14)
    try:
        indicator_rsi = ta.momentum.RSIIndicator(close=df['Close'], window=14)
        df['RSI'] = indicator_rsi.rsi()
    except:
        df['RSI'] = np.nan
    
    # MACD
    try:
        macd_ind = ta.trend.MACD(close=df['Close'], window_slow=26, window_fast=12, window_sign=9)
        df['MACD'] = macd_ind.macd()
        df['MACD_Signal'] = macd_ind.macd_signal()
        df['MACD_Hist'] = macd_ind.macd_diff()
    except:
        df['MACD'] = np.nan
        df['MACD_Signal'] = np.nan
        df['MACD_Hist'] = np.nan
    
    # Breakout & Range
    df['High_20D'] = df['High'].rolling(window=20).max()
    df['Low_20D'] = df['Low'].rolling(window=20).min()
    
    # BB Width
    try:
        bb = ta.volatility.BollingerBands(close=df['Close'], window=20, window_dev=2)
        df['BB_Width'] = (bb.bollinger_hband() - bb.bollinger_lband()) / df['MA20']
    except:
        df['BB_Width'] = np.nan
        
    return df

if __name__ == "__main__":
    tickers = ["HHV", "TCB", "VNINDEX"]
    data = fetch_data(tickers, period="6mo")
    for symbol, df in data.items():
        print(f"--- {symbol} ---")
        print(df.tail(3))
