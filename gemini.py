"""
Gemini AI Integration for Aether-Quant Bot.
Uses OAuth 2.0 Login with Google (like gemini-cli).
"""
import os
import json
import logging
import hashlib
import secrets
import urllib.parse
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

GEMINI_TOKENS_FILE = "gemini_tokens.json"

# Google OAuth 2.0 Config (for installed apps)
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

# OAuth endpoints
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"  # For CLI/bot apps

# Pending OAuth states (state -> chat_id)
_pending_oauth: Dict[str, int] = {}

# Per-user client cache
_user_clients: Dict[str, Any] = {}


def load_gemini_tokens() -> dict:
    """Load all Gemini tokens from file."""
    if os.path.exists(GEMINI_TOKENS_FILE):
        with open(GEMINI_TOKENS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_gemini_tokens(data: dict):
    """Save Gemini tokens to file."""
    with open(GEMINI_TOKENS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_user_tokens(chat_id: int) -> Optional[dict]:
    """Get Gemini tokens for a user."""
    tokens = load_gemini_tokens()
    return tokens.get(str(chat_id))


def save_user_tokens(chat_id: int, tokens: dict) -> bool:
    """Save Gemini tokens for a user."""
    try:
        data = load_gemini_tokens()
        data[str(chat_id)] = {
            "access_token": tokens.get("access_token"),
            "refresh_token": tokens.get("refresh_token"),
            "expires_at": tokens.get("expires_at"),
            "created_at": datetime.now().isoformat()
        }
        save_gemini_tokens(data)
        # Clear cached client
        if str(chat_id) in _user_clients:
            del _user_clients[str(chat_id)]
        return True
    except Exception as e:
        logger.error(f"Failed to save tokens: {e}")
        return False


def generate_oauth_state(chat_id: int) -> str:
    """Generate a secure OAuth state parameter."""
    state = secrets.token_urlsafe(32)
    _pending_oauth[state] = chat_id
    return state


def get_chat_id_from_state(state: str) -> Optional[int]:
    """Get chat_id from OAuth state."""
    return _pending_oauth.pop(state, None)


def get_oauth_login_url(chat_id: int) -> str:
    """Generate Google OAuth login URL."""
    state = generate_oauth_state(chat_id)
    
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/generative-language.retriever",
        "state": state,
        "access_type": "offline",
        "prompt": "consent"
    }
    
    return f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"


def exchange_code_for_tokens(code: str) -> Optional[dict]:
    """Exchange OAuth code for access tokens."""
    import requests
    
    data = {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "code": code,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code"
    }
    
    try:
        resp = requests.post(GOOGLE_TOKEN_URL, data=data)
        if resp.status_code == 200:
            token_data = resp.json()
            # Calculate expiry time
            expires_in = token_data.get("expires_in", 3600)
            expires_at = datetime.now().timestamp() + expires_in
            token_data["expires_at"] = expires_at
            return token_data
        else:
            logger.error(f"Token exchange failed: {resp.text}")
            return None
    except Exception as e:
        logger.error(f"Token exchange error: {e}")
        return None


def refresh_access_token(chat_id: int) -> Optional[str]:
    """Refresh expired access token."""
    import requests
    
    tokens = get_user_tokens(chat_id)
    if not tokens or not tokens.get("refresh_token"):
        return None
    
    data = {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "refresh_token": tokens["refresh_token"],
        "grant_type": "refresh_token"
    }
    
    try:
        resp = requests.post(GOOGLE_TOKEN_URL, data=data)
        if resp.status_code == 200:
            token_data = resp.json()
            expires_in = token_data.get("expires_in", 3600)
            token_data["expires_at"] = datetime.now().timestamp() + expires_in
            token_data["refresh_token"] = tokens["refresh_token"]  # Keep refresh token
            save_user_tokens(chat_id, token_data)
            return token_data.get("access_token")
        else:
            logger.error(f"Token refresh failed: {resp.text}")
            return None
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        return None


def get_valid_access_token(chat_id: int) -> Optional[str]:
    """Get valid access token, refresh if needed."""
    tokens = get_user_tokens(chat_id)
    if not tokens:
        return None
    
    # Check if expired
    expires_at = tokens.get("expires_at", 0)
    if datetime.now().timestamp() >= expires_at - 60:  # Refresh 1 min before expiry
        return refresh_access_token(chat_id)
    
    return tokens.get("access_token")


def get_gemini_client(chat_id: int):
    """Get or create Gemini client for a specific user."""
    chat_str = str(chat_id)
    
    if chat_str in _user_clients:
        return _user_clients[chat_str]
    
    access_token = get_valid_access_token(chat_id)
    if not access_token:
        return None
    
    try:
        import google.generativeai as genai
        # Configure with OAuth access token
        genai.configure(credentials=access_token)
        client = genai.GenerativeModel('gemini-1.5-flash')
        _user_clients[chat_str] = client
        return client
    except ImportError:
        logger.error("google-generativeai not installed")
        return None
    except Exception as e:
        logger.error(f"Failed to init Gemini: {e}")
        return None


def has_gemini_auth(chat_id: int) -> bool:
    """Check if user has authenticated with Google."""
    tokens = get_user_tokens(chat_id)
    return tokens is not None and tokens.get("refresh_token") is not None


def revoke_gemini_auth(chat_id: int) -> bool:
    """Revoke user's Gemini authentication."""
    try:
        data = load_gemini_tokens()
        if str(chat_id) in data:
            del data[str(chat_id)]
            save_gemini_tokens(data)
        if str(chat_id) in _user_clients:
            del _user_clients[str(chat_id)]
        return True
    except Exception as e:
        logger.error(f"Failed to revoke auth: {e}")
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
        # If unauthorized, may need re-auth
        if "401" in str(e) or "403" in str(e):
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


def is_oauth_configured() -> bool:
    """Check if OAuth is configured."""
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)
