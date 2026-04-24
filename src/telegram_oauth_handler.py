import threading
import time
import logging
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse
from typing import Dict, Any, Optional
import requests

from .oauth_service import GoogleOAuthService
from .token_storage import save_user_token

logger = logging.getLogger(__name__)

_active_sessions: Dict[str, Dict[str, Any]] = {}
REDIRECT_PORT = 3000
REDIRECT_URI = f"http://127.0.0.1:{REDIRECT_PORT}/"

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass
        
    def do_GET(self):
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if 'code' in query and 'state' in query:
            code = query['code'][0]
            state = query['state'][0]
            session = _active_sessions.get(state)
            if not session or time.time() > session["expires_at"]:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Invalid or expired session.")
                return
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(b"<h1>Success!</h1><p>Return to Telegram.</p>")
            
            def process_auth():
                oauth_service = session["service"]
                token_data = oauth_service.exchange_code_for_token(code, session["verifier"], REDIRECT_URI)
                if token_data:
                    save_user_token(session["chat_id"], token_data)
                    msg = "✅ *Ket noi Gemini AI thanh cong!*"
                    requests.post(f"https://api.telegram.org/bot{session['bot_token']}/sendMessage", 
                                  json={"chat_id": session["chat_id"], "text": msg, "parse_mode": "Markdown"})
                if state in _active_sessions:
                    del _active_sessions[state]
                threading.Thread(target=self.server.shutdown).start()

            threading.Thread(target=process_auth).start()
        else:
            self.send_response(400); self.end_headers(); self.wfile.write(b"Missing code/state")

def initiate_login(chat_id: int, bot_token: str, client_id: str, client_secret: str = "") -> str:
    """Start OAuth flow."""
    service = GoogleOAuthService(client_id, client_secret)
    params = service.generate_pkce_params()
    state = params["state"]
    _active_sessions[state] = {
        "chat_id": chat_id,
        "verifier": params["code_verifier"],
        "bot_token": bot_token,
        "service": service,
        "expires_at": time.time() + 300
    }
    
    def run_server():
        try:
            server = HTTPServer(('127.0.0.1', REDIRECT_PORT), OAuthCallbackHandler)
            server.allow_reuse_address = True
            server.timeout = 300
            server.handle_request()
            server.server_close()
        except Exception as e:
            logger.error(f"Server error: {e}")

    threading.Thread(target=run_server, daemon=True).start()
    return service.build_authorization_url(params["code_challenge"], state, REDIRECT_URI)
