"""
Gemini AI Integration for Aether-Quant Bot.
Supports 2 modes:
1. OAuth 2.0 (Admin configures GOOGLE_CLIENT_ID/SECRET) - click to login
2. API Key (User creates their own key) - paste key
"""
import os
import json
import logging
import secrets
import urllib.parse
import re
import time
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Files
GEMINI_KEYS_FILE = os.path.join(_BASE_DIR, "gemini_keys.json")
GEMINI_TOKENS_FILE = os.path.join(_BASE_DIR, "gemini_tokens.json")

# OAuth Config (Mode 1 - Admin configured)
# NOTE: do not read env at import time because .env may be loaded after imports.
def _get_google_client_id() -> str:
    # Use exact Client ID from user's Gemini CLI example
    return os.environ.get("GOOGLE_CLIENT_ID", "681255809395-oo8ft2oprdrnp9e3aqf6av3hmdib135j.apps.googleusercontent.com")


def _get_google_client_secret() -> str:
    # Secret is usually not needed for this specific public client ID in this flow,
    # but we keep the env override just in case.
    return os.environ.get("GOOGLE_CLIENT_SECRET", "")


# URLs
GEMINI_API_URL = "https://aistudio.google.com/app/apikey"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
# Using 127.0.0.1 for local HTTP browser-to-bot auth handoff
GOOGLE_REDIRECT_URI = "http://127.0.0.1:8080/"

# Pending OAuth states
_pending_oauth: Dict[str, int] = {}

# Per-user client cache
_user_clients: Dict[str, Any] = {}

# Per-user last error
_last_error: Dict[str, str] = {}


def is_oauth_mode() -> bool:
    """Check if OAuth mode is enabled."""
    return True


def _set_last_error(chat_id: int, code: str):
    _last_error[str(chat_id)] = code


def get_last_error(chat_id: int) -> str:
    return _last_error.get(str(chat_id), "")


def is_valid_gemini_api_key(api_key: str) -> bool:
    # Google API keys typically start with 'AIza' and are URL-safe.
    return bool(re.match(r"^AIza[0-9A-Za-z\-_]{20,}$", api_key or ""))


# ==================== API KEY MODE ====================

def load_gemini_keys() -> dict:
    """Load all Gemini API keys from file."""
    if os.path.exists(GEMINI_KEYS_FILE):
        with open(GEMINI_KEYS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_gemini_keys(data: dict):
    """Save Gemini API keys to file with secure permissions."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    # 0o600 ensures only the owner can read/write the file
    fd = os.open(GEMINI_KEYS_FILE, flags, 0o600)
    with open(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_user_gemini_key(chat_id: int) -> Optional[str]:
    """Get Gemini API key for a user. Fallback to global .env key."""
    keys = load_gemini_keys()
    user_key = keys.get(str(chat_id), {}).get("api_key")
    if user_key:
        return user_key
        
    global_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if global_key and is_valid_gemini_api_key(global_key):
        return global_key
        
    return None


def set_user_gemini_key(chat_id: int, api_key: str) -> bool:
    """Save Gemini API key for a user."""
    try:
        keys = load_gemini_keys()
        keys[str(chat_id)] = {"api_key": api_key, "active": True}
        save_gemini_keys(keys)
        if str(chat_id) in _user_clients:
            del _user_clients[str(chat_id)]
        return True
    except Exception as e:
        logger.error(f"Failed to save Gemini key: {e}")
        return False


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


# ==================== OAUTH MODE ====================

def load_gemini_tokens() -> dict:
    """Load all Gemini OAuth tokens from file."""
    if os.path.exists(GEMINI_TOKENS_FILE):
        with open(GEMINI_TOKENS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_gemini_tokens(data: dict):
    """Save Gemini OAuth tokens to file with secure permissions."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    # 0o600 ensures only the owner can read/write the file
    fd = os.open(GEMINI_TOKENS_FILE, flags, 0o600)
    with open(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_user_tokens(chat_id: int) -> Optional[dict]:
    """Get Gemini OAuth tokens for a user."""
    tokens = load_gemini_tokens()
    return tokens.get(str(chat_id))


def save_user_tokens(chat_id: int, tokens: dict) -> bool:
    """Save Gemini OAuth tokens for a user."""
    try:
        data = load_gemini_tokens()
        data[str(chat_id)] = {
            "access_token": tokens.get("access_token"),
            "refresh_token": tokens.get("refresh_token"),
            "expires_at": tokens.get("expires_at"),
            "created_at": datetime.now().isoformat()
        }
        save_gemini_tokens(data)
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
        "client_id": _get_google_client_id(),
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/cloud-platform https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile",
        "state": state,
        "access_type": "offline",
        "prompt": "consent"
    }
    
    return f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"


def start_local_oauth_server(chat_id: int, bot_token: str):
    """Start an ephemeral local HTTP server to automatically capture the OAuth code."""
    import threading
    import urllib.parse
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class OAuthHandler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass # Suppress HTTP logs
            
        def do_GET(self):
            parsed_path = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(parsed_path.query)
            
            if 'code' in query:
                code = query['code'][0]
                state = query.get('state', [''])[0]
                
                # Check state for security
                expected_chat_id = get_chat_id_from_state(state)
                if expected_chat_id != chat_id:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"Invalid state security token.")
                    return
                
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                
                html = """
                <html>
                <head><title>Authentication Successful</title></head>
                <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                    <h2 style="color: #4CAF50;">Authentication Successful!</h2>
                    <p>Ban da cap quyen thanh cong cho Bot. Vui long dong cua so trinh duyet nay va quay lai Telegram nhe!</p>
                </body>
                </html>
                """
                self.wfile.write(html.encode("utf-8"))
                
                # Process the backend handshake autonomously
                def process_and_notify():
                    tokens = exchange_code_for_tokens(code)
                    if tokens:
                        save_user_tokens(str(chat_id), tokens)
                        # Remove pending state
                        for s, c in list(_pending_oauth.items()):
                            if c == chat_id:
                                del _pending_oauth[s]
                        
                        import requests
                        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                        msg = "🎉 *Dang nhap OAuth thanh cong!*\n\nBan da hien ngang su dung API qua Google Code Assist (han muc tang cuong). Thu nhan `/ask` ngay nao!"
                        requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})
                
                threading.Thread(target=process_and_notify).start()
                
                # Shut down the local mini-server
                threading.Thread(target=self.server.shutdown).start()
                
            elif 'error' in query:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(f"Authentication Error: {query['error'][0]}".encode('utf-8'))
                threading.Thread(target=self.server.shutdown).start()
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Waiting for auth...")

    # Boot the server asynchronously
    def run_server():
        try:
            server = HTTPServer(('127.0.0.1', 8080), OAuthHandler)
            server.timeout = 180 # Close after 3 minutes if no traffic
            try:
                server.handle_request() # Wait for exactly one valid ping
            except Exception:
                pass
            finally:
                server.server_close()
        except OSError:
            # Port might be blocked by another attempt, that's fine
            pass

    threading.Thread(target=run_server, daemon=True).start()


def exchange_code_for_tokens(code: str) -> Optional[dict]:
    """Exchange OAuth code for access tokens."""
    import requests
    
    data = {
        "client_id": _get_google_client_id(),
        "client_secret": _get_google_client_secret(),
        "code": code,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code"
    }
    
    try:
        logger.info(f"Attempting token exchange with code: {code[:10]}...")
        resp = requests.post(GOOGLE_TOKEN_URL, data=data)
        if resp.status_code == 200:
            token_data = resp.json()
            expires_in = token_data.get("expires_in", 3600)
            token_data["expires_at"] = datetime.now().timestamp() + expires_in
            logger.info("Token exchange successful")
            return token_data
        else:
            logger.error(f"Token exchange failed (HTTP {resp.status_code}): {resp.text}")
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
        "client_id": _get_google_client_id(),
        "client_secret": _get_google_client_secret(),
        "refresh_token": tokens["refresh_token"],
        "grant_type": "refresh_token"
    }
    
    try:
        resp = requests.post(GOOGLE_TOKEN_URL, data=data)
        if resp.status_code == 200:
            token_data = resp.json()
            expires_in = token_data.get("expires_in", 3600)
            token_data["expires_at"] = datetime.now().timestamp() + expires_in
            token_data["refresh_token"] = tokens["refresh_token"]
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
    
    expires_at = tokens.get("expires_at", 0)
    if datetime.now().timestamp() >= expires_at - 60:
        return refresh_access_token(chat_id)
    
    return tokens.get("access_token")


def revoke_gemini_oauth(chat_id: int) -> bool:
    """Revoke user's Gemini OAuth tokens."""
    try:
        data = load_gemini_tokens()
        if str(chat_id) in data:
            del data[str(chat_id)]
            save_gemini_tokens(data)
        if str(chat_id) in _user_clients:
            del _user_clients[str(chat_id)]
        return True
    except Exception as e:
        logger.error(f"Failed to revoke OAuth: {e}")
        return False


# ==================== COMMON ====================

def has_gemini_auth(chat_id: int) -> bool:
    """Check if user has Gemini auth (OAuth or API key)."""
    tokens = get_user_tokens(chat_id)
    if tokens is not None and tokens.get("refresh_token") is not None:
        return True
    return get_user_gemini_key(chat_id) is not None


def get_gemini_client(chat_id: int):
    """Get or create Gemini client for a specific user."""
    chat_str = str(chat_id)
    
    try:
        import google.generativeai as genai
        
        # Check OAuth mode first
        tokens = get_user_tokens(chat_id)
        if tokens and tokens.get("refresh_token"):
            access_token = get_valid_access_token(chat_id)
            if not access_token:
                _set_last_error(chat_id, "AUTH_REQUIRED")
                return None
            
            from google.oauth2.credentials import Credentials
            creds = Credentials(
                token=access_token,
                refresh_token=tokens.get("refresh_token"),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=_get_google_client_id(),
                client_secret=_get_google_client_secret()
            )
            genai.configure(credentials=creds)
        else:
            # API Key mode - use user's API key
            api_key = get_user_gemini_key(chat_id)
            if not api_key:
                _set_last_error(chat_id, "NO_KEY")
                return None
            if not is_valid_gemini_api_key(api_key):
                _set_last_error(chat_id, "API_KEY_INVALID")
                return None
            genai.configure(api_key=api_key)
        
        # Resolve model from user configs
        model_name = 'gemini-2.5-flash'
        config_path = "user_configs.json"
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    cfg_data = json.load(f)
                    if "users" in cfg_data and chat_str in cfg_data["users"]:
                        model_name = cfg_data["users"][chat_str].get("ai_model", model_name)
            except Exception:
                pass
                
        logger.info(f"Initializing Gemini model: {model_name} for chat {chat_id}")
        client = genai.GenerativeModel(model_name)
        _user_clients[chat_str] = client
        _set_last_error(chat_id, "")
        return client
    except ImportError:
        logger.error("google-generativeai not installed")
        _set_last_error(chat_id, "MISSING_LIB")
        return None
    except Exception as e:
        logger.error(f"Failed to init Gemini: {e}")
        _set_last_error(chat_id, "INIT_FAILED")
        return None


def list_available_models(chat_id: int):
    """List all models available for the current user's credentials."""
    get_gemini_client(chat_id)  # Ensure configured
    try:
        import google.generativeai as genai
        models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                models.append(m.name.replace('models/', ''))
        return models
    except Exception as e:
        logger.error(f"Failed to list models: {e}")
        return [f"Lỗi truy vấn: {str(e)}"]


def get_api_key_url() -> str:
    """Get Google AI Studio API key URL."""
    return GEMINI_API_URL


def ask_gemini(question: str, chat_id: int, context: Optional[str] = None) -> str:
    """Ask Gemini a question for a specific user."""
    client = get_gemini_client(chat_id)
    if not client:
        return get_last_error(chat_id) or "AUTH_REQUIRED"
    
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

    max_retries = 3
    base_delay = 5  # Start with 5 seconds

    for attempt in range(max_retries):
        try:
            response = client.generate_content(full_prompt)
            # Attempt to bypass any internal safety blocks
            response.resolve()
            return response.text.strip()
        except Exception as e:
            error_msg = str(e).lower()
            logger.error(f"Gemini API error (Attempt {attempt + 1}/{max_retries}): {error_msg}")
            
            # Check if we should retry
            if "429" in error_msg or "too many requests" in error_msg or "404" in error_msg or "not found" in error_msg:
                if attempt < max_retries - 1:
                    sleep_time = base_delay * (2 ** attempt)
                    logger.warning(f"Rate limited or model error. Retrying in {sleep_time}s...")
                    time.sleep(sleep_time)
                    
                    # On last attempt, fallback to lighter model if possible
                    if attempt == max_retries - 2:
                        logger.info("Attempting fallback to gemini-2.0-flash-lite for final try")
                        try:
                            import google.generativeai as genai
                            client = genai.GenerativeModel("gemini-2.0-flash-lite")
                        except Exception:
                            pass
                    continue
                else:
                    return f"Bot dang qua tai. Chi tiet loi: {error_msg[:300]}"
                    
            if "401" in error_msg or "403" in error_msg or "api_key" in error_msg:
                return "AUTH_REQUIRED"
                
            return f"Loi AI: {str(e)[:100]}"
            
    return "Bot dang qua tai. Vui long thu lai sau."


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
