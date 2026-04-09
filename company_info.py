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

# Static fallback data for common stocks (used when API fails)
_STATIC_DATA = {
    "HHV": {"name": "Hoang Han Viet Corp", "industry": "Bat dong san"},
    "TOS": {"name": "Toshiba Vietnam", "industry": "Dien tu"},
    "NKG": {"name": "Nong nghiep Song Hau", "industry": "Nong nghiep"},
    "AAS": {"name": "Aa Dung A", "industry": "Xay dung"},
    "MSB": {"name": "Maritime Bank", "industry": "Ngan hang"},
    "TCB": {"name": "Techcombank", "industry": "Ngan hang"},
    "VNM": {"name": "Vinamilk", "industry": "Thuc pham"},
    "FPT": {"name": "FPT Corp", "industry": "Cong nghe thong tin"},
    "VIC": {"name": "Vingroup", "industry": "Bat dong san"},
    "VHM": {"name": "Vinhomes", "industry": "Bat dong san"},
    "HPG": {"name": "Hoa Phat Group", "industry": "Thep"},
    "MWG": {"name": "Mobile World", "industry": "Ban le"},
    "SAB": {"name": "Sabeco", "industry": "Thuc pham"},
    "VCB": {"name": "Vietcombank", "industry": "Ngan hang"},
    "BID": {"name": "BIDV", "industry": "Ngan hang"},
    "CTG": {"name": "VietinBank", "industry": "Ngan hang"},
    "MBB": {"name": "Military Bank", "industry": "Ngan hang"},
    "ACB": {"name": "Asia Commercial Bank", "industry": "Ngan hang"},
    "VPB": {"name": "VPBank", "industry": "Ngan hang"},
    "EIB": {"name": "Eximbank", "industry": "Ngan hang"},
    "HDB": {"name": "HDBank", "industry": "Ngan hang"},
    "TPB": {"name": "TPBank", "industry": "Ngan hang"},
    "STB": {"name": "Sacombank", "industry": "Ngan hang"},
    "PVD": {"name": "Petrovietnam Drilling", "industry": "Dau khi"},
    "PVS": {"name": "Petrovietnam Tech", "industry": "Dau khi"},
    "GAS": {"name": "PV Gas", "industry": "Dau khi"},
    "PLX": {"name": "Petrolimex", "industry": "Dau khi"},
    "POW": {"name": "PV Power", "industry": "Dien"},
    "NT2": {"name": "Nghi Son 2 Power", "industry": "Dien"},
    "REE": {"name": "Ree Corp", "industry": "Dien"},
    "KDC": {"name": "KIDO Group", "industry": "Thuc pham"},
    "SBT": {"name": "La Vie", "industry": "Thuc pham"},
    "ANV": {"name": "Nam Viet", "industry": "Thuy san"},
    "VHC": {"name": "Viet Hung", "industry": "Thuy san"},
    "DBD": {"name": "Dong Bac", "industry": "Xay dung"},
    "HBC": {"name": "Hoang Bao", "industry": "Xay dung"},
    "FLC": {"name": "FLC Group", "industry": "Bat dong san"},
    "LDG": {"name": "LDG Group", "industry": "Bat dong san"},
    "DIG": {"name": "DIC Corp", "industry": "Bat dong san"},
    "DXG": {"name": "Dat Xanh", "industry": "Bat dong san"},
    "NVL": {"name": "No Va Land", "industry": "Bat dong san"},
    "PDR": {"name": "Phat Dat", "industry": "Bat dong san"},
    "NLG": {"name": "Nam Long", "industry": "Bat dong san"},
    "ITA": {"name": "ITA Corp", "industry": "Bat dong san"},
}

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
        "exchange": "",
        "market_cap": 0,
        "price": 0,
        "change_pct": 0,
        "volume": 0
    }
    
    # Check static data first (fast fallback)
    if symbol in _STATIC_DATA:
        info["name"] = _STATIC_DATA[symbol].get("name", "")
        info["industry"] = _STATIC_DATA[symbol].get("industry", "")
    
    # Try VNStock API
    try:
        stock = Vnstock().stock(symbol=symbol, source='VCI')
        
        # Try to get company overview
        try:
            df_overview = stock.company.overview()
            if df_overview is not None and not df_overview.empty:
                # Parse overview data - handle different formats
                for _, row in df_overview.iterrows():
                    field = str(row.get('field', '')).lower() if 'field' in row else ''
                    value = row.get('value', '')
                    
                    if not value:
                        continue
                    
                    if 't n' in field or 'name' in field:
                        info['name'] = str(value)
                    elif 'ng nh' in field or 'industry' in field:
                        info['industry'] = str(value)
                    elif 's n' in field or 'exchange' in field:
                        info['exchange'] = str(value)
                    elif 'vcp' in field or 'market cap' in field or 'v h a' in field:
                        try:
                            info['market_cap'] = float(value) if value else 0
                        except:
                            pass
        except:
            pass
        
        # Get current price
        try:
            df_price = stock.quote.intraday(symbol=symbol)
            if df_price is not None and not df_price.empty:
                latest = df_price.iloc[-1]
                if 'close' in latest:
                    info['price'] = float(latest['close'] or 0)
                if 'volume' in latest:
                    info['volume'] = float(latest['volume'] or 0)
        except:
            pass
        
    except:
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
    for sym in ["TCB", "VNM", "FPT", "HHV", "MSB"]:
        print(format_company_info(sym))
        print()
