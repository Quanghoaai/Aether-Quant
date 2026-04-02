import os
import pandas as pd
import numpy as np
import time
import ta
from vnstock import Vnstock
from datetime import datetime, timedelta

def fetch_data(tickers, start_date=None, end_date=None, period="6mo"):
    """
    Fetch EOD data for a list of tickers using VNStock.
    """
    if not start_date or not end_date:
        today = datetime.today()
        # Parse period
        if period == "6mo":
            lookback_days = 180
        elif period == "1y":
            lookback_days = 365
        else:
            lookback_days = 120
            
        start_date = (today - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")

    # Initialize stock object without api_key parameter
    stock = Vnstock().stock(symbol='VN30', source='KBS')
    delay = 1

    data_dict = {}
    
    for symbol in tickers:
        try:
            print(f"Fetching data for {symbol}...")
            time.sleep(delay)
            # Fetch data
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
    Calculate required technical indicators:
    - MA20, MA50
    - 20-day Volume Average
    - ATR
    """
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    if "Date" in df.columns:
        df = df.sort_values("Date")
        
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA50'] = df['Close'].rolling(window=50).mean()
    df['Vol_SMA20'] = df['Volume'].rolling(window=20).mean()
    
    # Daily returns
    df['Return'] = df['Close'].pct_change()
    
    # ATR
    try:
        indicator_atr = ta.volatility.AverageTrueRange(high=df['High'], low=df['Low'], close=df['Close'], window=14)
        df['ATR'] = indicator_atr.average_true_range()
    except Exception as e:
        df['ATR'] = np.nan
        
    return df

if __name__ == "__main__":
    tickers = ["HHV", "TOS", "NKG", "AAS", "VNINDEX"]
    data = fetch_data(tickers, period="3mo")
    for symbol, df in data.items():
        print(f"--- {symbol} ---")
        print(df.tail(2))
