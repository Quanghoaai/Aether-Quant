"""
Telegram OAuth Handler
Manages OAuth flow for Telegram bot users
"""
import os
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
import time
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# OAuth callback redirect URI
REDIRECT_PORT = int(os.getenv('OAUTH_CALLBACK_PORT', '3000'))
REDIRECT_PATH = '/oauth/callback'
REDIRECT_URI = f'http://localhost:{REDIRECT_PORT}{REDIRECT_PATH}'

# Store active OAuth sessions: state -> (chat_id, code_verifier)
_active_sessions = {}
_callback_result = {}


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler for OAuth callback"""
    
    def do_GET(self):
        global _callback_result
        
        try:
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            
            code = query_params.get('code', [None])[0]
            state = query_params.get('state', [None])[0]
            error = query_params.get('error', [None])[0]
            error_desc = query_params.get('error_description', [''])[0]
            
            # Check if callback path is correct
            if parsed_url.path != REDIRECT_PATH:
                self.send_response(404)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'Not found')
                return
            
            # Handle OAuth error
            if error:
                logger.error(f"❌ OAuth error: {error} - {error_desc}")
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(f"""
                <html>
                    <body style="font-family: Arial; text-align: center; padding: 50px;">
                        <h1>❌ Xác thực thất bại</h1>
                        <p>Lỗi: <strong>{error}</strong></p>
                        <p>{error_desc}</p>
                        <p>Bạn có thể đóng cửa sổ này.</p>
                    </body>
                </html>
                """.encode('utf-8'))
                _callback_result = {'error': error}
                return
            
            # Validate code and state
            if not code or not state:
                logger.error(f"❌ Missing code or state - code: {code}, state: {state}")
                self.send_response(400)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'Missing code or state parameter')
                return
            
            # Validate state (CSRF protection)
            expected_state = _callback_result.get('expected_state')
            if state != expected_state:
                logger.error(f"❌ State mismatch - expected: {expected_state}, got: {state}")
                self.send_response(400)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'Invalid state parameter (CSRF attack?)')
                return
            
            # Success response
            logger.info(f"✅ OAuth callback received - code: {code[:20]}..., state: {state}")
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(b"""
            <html>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1>✅ Xác thực thành công!</h1>
                    <p>Bạn có thể đóng cửa sổ này và quay lại bot Telegram.</p>
                    <script>setTimeout(() => { window.close(); }, 2000);</script>
                </body>
            </html>
            """)
            
            _callback_result['code'] = code
            _callback_result['state'] = state
            _callback_result['received'] = True
        
        except Exception as e:
            logger.error(f"❌ Callback handler error: {e}")
            self.send_response(500)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Internal server error')
    
    def log_message(self, format, *args):
        """Suppress HTTP request logging"""
        pass


def start_callback_server(expected_state, port=REDIRECT_PORT):
    """Start local HTTP server to receive OAuth callback
    
    Args:
        expected_state: Expected state parameter (for CSRF validation)
        port: Port to listen on
        
    Returns:
        dict with code, state, and port when callback received
        
    Raises:
        TimeoutError: If callback not received within 5 minutes
    """
    global _callback_result
    _callback_result = {'expected_state': expected_state, 'received': False}
    
    try:
        server = HTTPServer(('127.0.0.1', port), OAuthCallbackHandler)
        logger.info(f"📍 OAuth callback server listening on http://127.0.0.1:{port}{REDIRECT_PATH}")
        
        # Start server in background thread with timeout
        def run_server():
            server.timeout = 1  # 1 second timeout per request
            start_time = time.time()
            while time.time() - start_time < 5 * 60:  # 5 minute total timeout
                server.handle_request()
                if _callback_result.get('received'):
                    logger.info("✅ OAuth callback received, closing server")
                    break
            server.server_close()
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
        # Wait for callback (with polling)
        timeout_seconds = 5 * 60  # 5 minutes
        poll_interval = 0.5  # 500ms polling
        elapsed = 0
        
        while elapsed < timeout_seconds:
            if _callback_result.get('received'):
                logger.info(f"✅ OAuth callback received: code={_callback_result['code'][:20]}...")
                return {
                    'code': _callback_result['code'],
                    'state': _callback_result['state'],
                    'port': port
                }
            time.sleep(poll_interval)
            elapsed += poll_interval
        
        logger.error(f"❌ OAuth callback timeout after {timeout_seconds} seconds")
        raise TimeoutError(f"OAuth callback timeout after {timeout_seconds} seconds")
    
    except Exception as e:
        logger.error(f"❌ Callback server error: {e}")
        raise


def initiate_login(chat_id, bot_token, client_id):
    """Initiate OAuth login for a user
    
    Args:
        chat_id: Telegram chat ID
        bot_token: Telegram bot token
        client_id: Google OAuth Client ID
        
    Returns:
        Authorization URL for user to click
    """
    from src.oauth_service import GoogleOAuthService
    
    try:
        service = GoogleOAuthService(client_id)
        pkce = service.generate_pkce_params()
        
        # Store session
        _active_sessions[pkce['state']] = (chat_id, pkce['code_verifier'])
        
        # Generate auth URL
        auth_url = service.build_authorization_url(
            pkce['code_challenge'],
            pkce['state'],
            REDIRECT_URI,
            scopes=['openid', 'email', 'profile']
        )
        
        logger.info(f"📄 Generated OAuth URL for user {chat_id}")
        return auth_url
    
    except Exception as e:
        logger.error(f"❌ Failed to initiate login: {e}")
        raise
