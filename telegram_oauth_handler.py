import threading
import time
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse
from typing import Dict, Any, Optional
import requests
from oauth_service import GoogleOAuthService
from secure_storage import save_user_token

logger = logging.getLogger(__name__)

# Global state to track active OAuth sessions: state -> {chat_id, verifier, expires_at}
_active_sessions: Dict[str, Dict[str, Any]] = {}

# Redirect URI for local callback
REDIRECT_PORT = 3000
REDIRECT_URI = f"http://127.0.0.1:{REDIRECT_PORT}/"

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass # Suppress logs
        
    def do_GET(self):
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        
        if 'code' in query and 'state' in query:
            code = query['code'][0]
            state = query['state'][0]
            
            session = _active_sessions.get(state)
            if not session or time.time() > session["expires_at"]:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Invalid or expired state session.")
                return
            
            chat_id = session["chat_id"]
            verifier = session["verifier"]
            bot_token = session["bot_token"]
            oauth_service = session["service"]
            
            # Send success HTML
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write("""
                <html>
                <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                    <h1 style="color: #4CAF50;">Authentication Successful!</h1>
                    <p>Ban da cap quyen thanh cong. Vui long quay lai Telegram.</p>
                </body>
                </html>
            """.encode('utf-8'))
            
            # Exchange code in background
            def process_auth():
                token_data = oauth_service.exchange_code_for_token(code, verifier, REDIRECT_URI)
                if token_data:
                    save_user_token(chat_id, token_data)
                    # Notify user via Telegram
                    msg = "✅ *Ket noi Gemini AI thanh cong!*\n\nBan co the dung `/ask` de hoi AI ngay bay gio."
                    requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", 
                                  json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})
                
                # Cleanup session
                if state in _active_sessions:
                    del _active_sessions[state]
                
                # Shutdown server
                threading.Thread(target=self.server.shutdown).start()

            threading.Thread(target=process_auth).start()
            
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Missing code or state.")

def initiate_login(chat_id: int, bot_token: str, client_id: str) -> str:
    """Initiate OAuth flow and start callback server."""
    oauth_service = GoogleOAuthService(client_id)
    params = oauth_service.generate_pkce_params()
    
    # Store session
    state = params["state"]
    _active_sessions[state] = {
        "chat_id": chat_id,
        "verifier": params["code_verifier"],
        "bot_token": bot_token,
        "service": oauth_service,
        "expires_at": time.time() + 300 # 5 minutes timeout
    }
    
    # Start server in thread
    def run_server():
        try:
            server = HTTPServer(('127.0.0.1', REDIRECT_PORT), OAuthCallbackHandler)
            server.allow_reuse_address = True
            server.timeout = 300
            server.handle_request()
            server.server_close()
        except Exception as e:
            logger.error(f"Callback server error: {e}")

    threading.Thread(target=run_server, daemon=True).start()
    
    return oauth_service.build_authorization_url({
        "challenge": params["code_challenge"],
        "state": state
    }, REDIRECT_URI)
