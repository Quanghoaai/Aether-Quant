"""
Gemini AI Integration for Aether-Quant Bot.
Each user connects their personal Gemini API key.
"""
import os
import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

GEMINI_KEYS_FILE = "gemini_keys.json"
GEMINI_API_URL = "https://aistudio.google.com/app/apikey"

# Per-user client cache
_user_clients: Dict[str, Any] = {}


def load_gemini_keys() -> dict:
    """Load all Gemini API keys from file."""
    if os.path.exists(GEMINI_KEYS_FILE):
        with open(GEMINI_KEYS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_gemini_keys(data: dict):
    """Save Gemini API keys to file."""
    with open(GEMINI_KEYS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_user_gemini_key(chat_id: int) -> Optional[str]:
    """Get Gemini API key for a user."""
    keys = load_gemini_keys()
    return keys.get(str(chat_id), {}).get("api_key")


def set_user_gemini_key(chat_id: int, api_key: str) -> bool:
    """Save Gemini API key for a user."""
    try:
        keys = load_gemini_keys()
        keys[str(chat_id)] = {"api_key": api_key, "active": True}
        save_gemini_keys(keys)
        # Clear cached client
        if str(chat_id) in _user_clients:
            del _user_clients[str(chat_id)]
        return True
    except Exception as e:
        logger.error(f"Failed to save Gemini key: {e}")
        return False


def get_gemini_client(chat_id: int):
    """Get or create Gemini client for a specific user."""
    chat_str = str(chat_id)
    
    if chat_str in _user_clients:
        return _user_clients[chat_str]
    
    api_key = get_user_gemini_key(chat_id)
    if not api_key:
        return None
    
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        client = genai.GenerativeModel('gemini-1.5-flash')
        _user_clients[chat_str] = client
        return client
    except ImportError:
        logger.error("google-generativeai not installed")
        return None
    except Exception as e:
        logger.error(f"Failed to init Gemini: {e}")
        return None


def has_gemini_key(chat_id: int) -> bool:
    """Check if user has configured Gemini API key."""
    return get_user_gemini_key(chat_id) is not None


def get_api_key_url() -> str:
    """Get Google AI Studio API key URL."""
    return GEMINI_API_URL


def revoke_gemini_key(chat_id: int) -> bool:
    """Revoke user's Gemini API key."""
    try:
        keys = load_gemini_keys()
        if str(chat_id) in keys:
            del keys[str(chat_id)]
            save_gemini_keys(keys)
        if str(chat_id) in _user_clients:
            del _user_clients[str(chat_id)]
        return True
    except Exception as e:
        logger.error(f"Failed to revoke key: {e}")
        return False


def ask_gemini(question: str, chat_id: int, context: Optional[str] = None) -> str:
    """Ask Gemini a question for a specific user."""
    client = get_gemini_client(chat_id)
    if not client:
        return "NEED_LOGIN"
    
    system_prompt = """Ban la AI Assistant cua Aether-Quant - he thong phan tich chung khoan Viet Nam.

Nhiem vu:
- Tra loi cau hoi ve dau tu, chung khoan, phan tich ky thuat
- Giai thich cac chi bao: RSI, MACD, MA, ATR, BB...
- Tu van ve quan ly rui ro, danh muc dau tu

Quy tac:
- Tra loi ngan gon, de hieu (duoi 500 tu)
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
        if "401" in str(e) or "403" in str(e) or "API_KEY" in str(e):
            return "NEED_LOGIN"
        return f"Loi AI: {str(e)[:100]}"


def analyze_stock_with_gemini(symbol: str, score_data: dict, price: float, chat_id: int) -> str:
    """Get AI analysis for a specific stock."""
    context = f"""
Ma chung khoan: {symbol}
Gia hien tai: {price:,.0f} VND
Diem tong: {score_data.get('score', 0):.2f}/5.0
- RS: {score_data.get('RS_score', 0):.1f}
- Price Action: {score_data.get('Price_Action_score', 0):.1f}
- Volume: {score_data.get('Volume_Profile_score', 0):.1f}"""
    
    question = f"Phan tich ngan gon {symbol}: nen mua hay cho?"
    return ask_gemini(question, chat_id, context)
