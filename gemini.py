"""
Gemini AI Integration for Aether-Quant Bot.
Now uses the modular structure in src/
"""
import os
import json
import logging
import re
import time
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Import modular components from src
from src.token_storage import save_user_token as secure_save_token, get_user_token as secure_get_token, delete_user_token as secure_delete_token, is_token_expired
from src.oauth_service import GoogleOAuthService
from src.telegram_oauth_handler import initiate_login, REDIRECT_URI, _active_sessions

# Files
GEMINI_KEYS_FILE = os.path.join(_BASE_DIR, "gemini_keys.json")

def _get_google_client_id() -> str:
    return os.environ.get("GOOGLE_CLIENT_ID", "681255809395-oo8ft2oprdrnp9e3aqf6av3hmdib135j.apps.googleusercontent.com")

def _get_google_client_secret() -> str:
    return os.environ.get("GOOGLE_CLIENT_SECRET", "")

# URLs
GEMINI_API_URL = "https://aistudio.google.com/app/apikey"
_pending_oauth = _active_sessions
_user_clients: Dict[str, Any] = {}
_last_error: Dict[str, str] = {}

def is_oauth_mode() -> bool: return True
def _set_last_error(chat_id: int, code: str): _last_error[str(chat_id)] = code
def get_last_error(chat_id: int) -> str: return _last_error.get(str(chat_id), "")
def is_valid_gemini_api_key(api_key: str) -> bool: return bool(re.match(r"^AIza[0-9A-Za-z\-_]{20,}$", api_key or ""))

# --- API KEY MODE ---
def load_gemini_keys() -> dict:
    if os.path.exists(GEMINI_KEYS_FILE):
        with open(GEMINI_KEYS_FILE, "r", encoding="utf-8") as f: return json.load(f)
    return {}

def save_gemini_keys(data: dict):
    fd = os.open(GEMINI_KEYS_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with open(fd, "w", encoding="utf-8") as f: json.dump(data, f, indent=2)

def get_user_gemini_key(chat_id: int) -> Optional[str]:
    keys = load_gemini_keys()
    user_key = keys.get(str(chat_id), {}).get("api_key")
    if user_key: return user_key
    global_key = os.environ.get("GEMINI_API_KEY", "").strip()
    return global_key if global_key and is_valid_gemini_api_key(global_key) else None

def set_user_gemini_key(chat_id: int, api_key: str) -> bool:
    try:
        keys = load_gemini_keys(); keys[str(chat_id)] = {"api_key": api_key, "active": True}; save_gemini_keys(keys)
        if str(chat_id) in _user_clients: del _user_clients[str(chat_id)]
        return True
    except Exception as e: logger.error(f"Error: {e}"); return False

def revoke_gemini_key(chat_id: int) -> bool:
    try:
        keys = load_gemini_keys()
        if str(chat_id) in keys: del keys[str(chat_id)]; save_gemini_keys(keys)
        if str(chat_id) in _user_clients: del _user_clients[str(chat_id)]
        return True
    except Exception as e: logger.error(f"Error: {e}"); return False

# --- OAUTH MODE ---
def get_user_tokens(chat_id: int) -> Optional[dict]: return secure_get_token(chat_id)
def save_user_tokens(chat_id: int, tokens: dict) -> bool:
    try:
        secure_save_token(chat_id, tokens)
        if str(chat_id) in _user_clients: del _user_clients[str(chat_id)]
        return True
    except Exception as e: logger.error(f"Error: {e}"); return False

def get_oauth_login_url(chat_id: int) -> str:
    return initiate_login(chat_id, os.environ.get("TELEGRAM_BOT_TOKEN", ""), _get_google_client_id(), _get_google_client_secret())

def start_local_oauth_server(chat_id: int, bot_token: str): pass

def exchange_code_for_tokens(code: str, verifier: Optional[str] = None) -> Optional[dict]:
    service = GoogleOAuthService(_get_google_client_id(), _get_google_client_secret())
    return service.exchange_code_for_token(code, verifier, REDIRECT_URI)

def get_valid_access_token(chat_id: int) -> Optional[str]:
    token_data = secure_get_token(chat_id)
    if not token_data: return None
    if is_token_expired(token_data):
        service = GoogleOAuthService(_get_google_client_id(), _get_google_client_secret())
        new_token = service.refresh_access_token(token_data['refresh_token'])
        if new_token:
            secure_save_token(chat_id, new_token)
            return new_token['access_token']
        return None
    return token_data['access_token']

def revoke_gemini_oauth(chat_id: int) -> bool:
    try:
        secure_delete_token(chat_id)
        if str(chat_id) in _user_clients: del _user_clients[str(chat_id)]
        return True
    except Exception as e: logger.error(f"Error: {e}"); return False

# --- COMMON ---
def has_gemini_auth(chat_id: int) -> bool:
    tokens = get_user_tokens(chat_id)
    return (tokens and tokens.get("refresh_token")) or get_user_gemini_key(chat_id)

def get_gemini_client(chat_id: int):
    chat_str = str(chat_id)
    try:
        import google.generativeai as genai
        tokens = get_user_tokens(chat_id)
        if tokens and tokens.get("refresh_token"):
            access_token = get_valid_access_token(chat_id)
            if not access_token: _set_last_error(chat_id, "AUTH_REQUIRED"); return None
            from google.oauth2.credentials import Credentials
            creds = Credentials(token=access_token, refresh_token=tokens.get("refresh_token"),
                                token_uri="https://oauth2.googleapis.com/token",
                                client_id=_get_google_client_id(), client_secret=_get_google_client_secret())
            genai.configure(credentials=creds)
        else:
            api_key = get_user_gemini_key(chat_id)
            if not api_key: _set_last_error(chat_id, "NO_KEY"); return None
            genai.configure(api_key=api_key)
        
        model_name = 'gemini-2.0-flash'
        client = genai.GenerativeModel(model_name)
        _user_clients[chat_str] = client
        _set_last_error(chat_id, ""); return client
    except Exception as e: logger.error(f"Init Error: {e}"); _set_last_error(chat_id, "INIT_FAILED"); return None

def ask_gemini(question: str, chat_id: int, context: Optional[str] = None) -> str:
    client = get_gemini_client(chat_id)
    if not client: return get_last_error(chat_id) or "AUTH_REQUIRED"
    
    prompt = f"Ban la AI Assistant cua Aether-Quant.\n\n"
    if context: prompt += f"Context: {context}\n\n"
    prompt += f"Q: {question}"

    try:
        response = client.generate_content(prompt)
        response.resolve()
        return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini API Error: {e}")
        return f"Loi AI: {str(e)[:100]}"

def analyze_stock_with_gemini(symbol: str, score_data: dict, price: float, chat_id: int) -> str:
    context = f"Stock: {symbol}, Price: {price:,.0f}, Score: {score_data.get('score', 0):.2f}"
    return ask_gemini(f"Phan tich ngan gon {symbol}", chat_id, context)
