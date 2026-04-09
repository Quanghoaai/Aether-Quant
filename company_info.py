"""
Company information helper using VNStock API.
"""
import os
import sys
import logging
import warnings
from io import StringIO

# Suppress all vnstock/vnai messages BEFORE importing vnstock
logging.getLogger("vnstock").setLevel(logging.CRITICAL)
logging.getLogger("vnstock.common.data").setLevel(logging.CRITICAL)
logging.getLogger("vnai").setLevel(logging.CRITICAL)
logging.getLogger("pip").setLevel(logging.CRITICAL)
warnings.filterwarnings("ignore")
os.environ["VNai_DISABLE_UPDATE_CHECK"] = "1"

# Suppress stdout temporarily to hide vnai update message
_original_stdout = sys.stdout
sys.stdout = StringIO()
try:
    from vnstock import Vnstock
finally:
    sys.stdout = _original_stdout

from datetime import datetime

# Cache for company info to reduce API calls
_company_cache = {}

def get_company_info(symbol: str) -> dict:
    """
    Get company information for a stock symbol.
    Returns dict with: name, sector, industry, exchange, market_cap, etc.
    """
    global _company_cache
    
    # Check cache first
    if symbol in _company_cache:
        return _company_cache[symbol]
    
    info = {
        "symbol": symbol,
        "name": "",
        "sector": "",
        "industry": "",
        "exchange": "HOSE/HNX/UPCOM",
        "market_cap": 0,
        "price": 0,
        "change_pct": 0,
        "volume": 0
    }
    
    try:
        # Get stock engine
        stock = Vnstock().stock(symbol=symbol, source='VCI')
        
        # Try to get company overview
        try:
            df_overview = stock.company.overview()
            if df_overview is not None and not df_overview.empty:
                # Parse overview data
                for _, row in df_overview.iterrows():
                    field = str(row.get('field', '')).lower()
                    value = row.get('value', '')
                    
                    if 'tên' in field or 'name' in field:
                        info['name'] = str(value)
                    elif 'ngành' in field or 'industry' in field:
                        info['industry'] = str(value)
                    elif 'sàn' in field or 'exchange' in field:
                        info['exchange'] = str(value)
                    elif 'vcp' in field or 'market cap' in field or 'v hóa' in field:
                        try:
                            info['market_cap'] = float(value) if value else 0
                        except:
                            pass
        except Exception as e:
            pass
        
        # Get current price
        try:
            df_price = stock.quote.intraday(symbol=symbol)
            if df_price is not None and not df_price.empty:
                latest = df_price.iloc[-1]
                info['price'] = float(latest.get('close', 0) or 0)
                info['volume'] = float(latest.get('volume', 0) or 0)
        except Exception as e:
            pass
        
        # If no name found, try another method
        if not info['name']:
            try:
                df_profile = stock.company.profile()
                if df_profile is not None and not df_profile.empty:
                    for _, row in df_profile.iterrows():
                        field = str(row.get('field', '')).lower()
                        value = row.get('value', '')
                        if 'tên' in field or 'name' in field:
                            info['name'] = str(value)
                            break
            except:
                pass
        
    except Exception as e:
        pass
    
    # Cache the result
    _company_cache[symbol] = info
    return info


def format_company_info(symbol: str) -> str:
    """
    Format company info for display in Telegram.
    Returns a short formatted string.
    """
    info = get_company_info(symbol)
    
    text = f"?? *{symbol}*"
    if info['name']:
        # Truncate long names
        name = info['name'][:40] + "..." if len(info['name']) > 40 else info['name']
        text += f" - {name}"
    
    if info['industry']:
        text += f"\n  Ng nh: {info['industry'][:30]}"
    
    if info['price'] > 0:
        text += f"\n  Gi : {info['price']:,.0f} VND"
    
    if info['market_cap'] > 0:
        # Format market cap in billions
        cap_b = info['market_cap'] / 1e9
        text += f"\n  VCP: {cap_b:.1f}B VND"
    
    return text


def get_company_name(symbol: str) -> str:
    """
    Get just the company name for a symbol.
    """
    info = get_company_info(symbol)
    return info.get('name', '')[:30] if info.get('name') else symbol


if __name__ == "__main__":
    # Test
    for sym in ["TCB", "VNM", "FPT", "HHV"]:
        print(format_company_info(sym))
        print()
