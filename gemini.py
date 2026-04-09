"""
Gemini AI Integration for Aether-Quant Bot.
"""
import os
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Cache for Gemini client
_gemini_client = None
_user_api_keys = {}  # Cache user-specific API keys

GEMINI_API_URL = "https://makersuite.google.com/app/apikey"

def load_user_api_keys():
    """Load user API keys from file."""
    try:
        if os.path.exists("gemini_keys.json"):
            with open("gemini_keys.json", "r") as f:
                return json.load(f)
    except:
        pass
    return {}

def save_user_api_keys(keys):
    """Save user API keys to file."""
    try:
        with open("gemini_keys.json", "w") as f:
            json.dump(keys, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save API keys: {e}")

def set_user_api_key(chat_id: str, api_key: str) -> bool:
    """Set API key for a specific user."""
    keys = load_user_api_keys()
    keys[str(chat_id)] = api_key
    save_user_api_keys(keys)
    # Clear cached client for this user
    global _gemini_client
    _gemini_client = None
    return True

def get_user_api_key(chat_id: str) -> Optional[str]:
    """Get API key for a specific user."""
    # Check user-specific key first
    keys = load_user_api_keys()
    chat_str = str(chat_id)
    if chat_str in keys:
        return keys[chat_str]
    # Fall back to global env var
    return os.environ.get("GEMINI_API_KEY", "")

def get_gemini_client(chat_id: str = None):
    """Get or create Gemini client."""
    global _gemini_client
    
    api_key = get_user_api_key(chat_id) if chat_id else os.environ.get("GEMINI_API_KEY", "")
    
    if not api_key:
        return None
    
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        _gemini_client = genai.GenerativeModel('gemini-1.5-flash')
        return _gemini_client
    except ImportError:
        logger.error("google-generativeai not installed. Run: pip install google-generativeai")
        return None
    except Exception as e:
        logger.error(f"Failed to initialize Gemini: {e}")
        return None


def ask_gemini(question: str, chat_id: str = None, context: Optional[str] = None) -> str:
    """
    Ask Gemini a question and return the response.
    
    Args:
        question: User's question
        chat_id: User's chat ID for per-user API key
        context: Optional context (e.g., market data, portfolio info)
    
    Returns:
        Gemini's response or error message
    """
    client = get_gemini_client(chat_id)
    if not client:
        return f"Chua cau hinh Gemini API Key.\n\nLay API key tai: {GEMINI_API_URL}\n\nDung `/setgemini <api_key>` de nhap key."
    
    # Build prompt with context
    system_prompt = """Ban la AI Assistant cua Aether-Quant - mot he thong phan tich chung khoan Viet Nam.
    
Nhiem vu:
- Tra loi cau hoi ve dau tu, chung khoan, phan tich ky thuat
- Giai thich cac chi bao: RSI, MACD, MA, ATR, BB...
- Tu van ve quan ly rui ro, danh muc dau tu
- Phan tich xu huong thi truong

Quy tac:
- Tra loi ngan gon, de hieu (duoi 500 tu)
- Neu khong chac, noi "Toi khong chac ve dieu nay"
- Luon nhan manh: Day la thong tin tham khao, khong phai loi khuyen dau tu
- Su dung tieng Viet"""

    full_prompt = f"{system_prompt}\n\n"
    if context:
        full_prompt += f"Thong tin bo sung:\n{context}\n\n"
    full_prompt += f"Nguoi dung hoi: {question}"
    
    try:
        response = client.generate_content(full_prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return f"Loi ket noi AI: {str(e)[:100]}"


def analyze_stock_with_gemini(symbol: str, score_data: dict, price: float, chat_id: str = None) -> str:
    """
    Get AI analysis for a specific stock.
    """
    context = f"""
Ma chung khoan: {symbol}
Gia hien tai: {price:,.0f} VND
Diem tong: {score_data.get('score', 0):.2f}/5.0
- RS (Relative Strength): {score_data.get('RS_score', 0):.1f}
- Price Action: {score_data.get('Price_Action_score', 0):.1f}
- Volume: {score_data.get('Volume_Profile_score', 0):.1f}
- Volatility: {score_data.get('Volatility_score', 0):.1f}
- Sector Flow: {score_data.get('Sector_Flow_score', 0):.1f}
"""
    
    question = f"Phan tich ngan gon {symbol}: nen mua hay cho? Vi sao?"
    return ask_gemini(question, chat_id=chat_id, context=context)


if __name__ == "__main__":
    # Test
    print("Testing Gemini...")
    response = ask_gemini("RSI la gi? Khi nao nen mua?")
    print(response)
