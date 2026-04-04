import os
import pandas as pd
import numpy as np
import time
import ta
import socket
import requests.packages.urllib3.util.connection as urllib3_cn
from vnstock import Vnstock
from datetime import datetime, timedelta

# Force IPv4
def allowed_gai_family():
    return socket.AF_INET
urllib3_cn.allowed_gai_family = allowed_gai_family

def fetch_data(tickers, start_date=None, end_date=None, period="6mo"):
    """
    Fetch EOD data for a list of tickers using VNStock.
    """
    if not start_date or not end_date:
        today = datetime.today()
        if period == "6mo":
            lookback_days = 180
        elif period == "1y":
            lookback_days = 365
        else:
            lookback_days = 120
            
        start_date = (today - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")

    # Initialize stock object
    stock = Vnstock().stock(symbol='VN30', source='KBS')
    delay = 1

    data_dict = {}
    
    for symbol in tickers:
        try:
            print(f"Fetching data for {symbol}...")
            time.sleep(delay)
            df = stock.quote.history(symbol=symbol, start=start_date, end=end_date)
            
            if df is None or df.empty:
                print(f"Warning: No data fetched for {symbol}")
                continue
                
            # Rename columns to standard format
            rename_map = {
                "time": "Date",
                "open": "Open",
                "high": "High",
                "low": "Low",
                "close": "Close",
                "volume": "Volume"
            }
            
            df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
            
            for col in ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']:
                if col not in df.columns:
                    lower_match = [c for c in df.columns if c.lower() == col.lower()]
                    if lower_match:
                        df = df.rename(columns={lower_match[0]: col})
            
            df = calculate_indicators(df)
            data_dict[symbol] = df
            
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            
    return data_dict

def calculate_indicators(df):
    """
    Calculate technical indicators:
    - MA20, MA50, MA10
    - 20-day Volume Average
    - ATR(14)
    - RSI(14)
    - MACD Histogram
    - N-day High (20-day breakout)
    - Bollinger Bands Width
    """
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    if "Date" in df.columns:
        df = df.sort_values("Date")
        
    # Moving Averages
    df['MA10'] = df['Close'].rolling(window=10).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA50'] = df['Close'].rolling(window=50).mean()
    df['Vol_SMA20'] = df['Volume'].rolling(window=20).mean()
    
    # Daily returns
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
    
    # N-day High (for breakout detection)
    df['High_20D'] = df['High'].rolling(window=20).max()
    df['Low_20D'] = df['Low'].rolling(window=20).min()
    
    # Bollinger Bands Width (for squeeze detection)
    try:
        bb = ta.volatility.BollingerBands(close=df['Close'], window=20, window_dev=2)
        df['BB_Width'] = (bb.bollinger_hband() - bb.bollinger_lband()) / df['MA20']
    except:
        df['BB_Width'] = np.nan
        
    return df

if __name__ == "__main__":
    tickers = ["HHV", "TOS", "NKG", "AAS", "VNINDEX"]
    data = fetch_data(tickers, period="3mo")
    for symbol, df in data.items():
        print(f"--- {symbol} ---")
        print(df[['Close', 'MA20', 'RSI', 'MACD_Hist', 'ATR']].tail(3))
