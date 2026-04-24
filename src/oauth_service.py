"""
Google OAuth 2.0 PKCE Service
Base implementation for Google OAuth with PKCE support
"""
import os
import requests
import secrets
import hashlib
import base64
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
GOOGLE_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'


class GoogleOAuthService:
    """Google OAuth 2.0 with PKCE implementation"""
    
    def __init__(self, client_id=None, client_secret=None):
        self.client_id = client_id or CLIENT_ID
        self.client_secret = client_secret or CLIENT_SECRET
        
        if not self.client_id:
            raise ValueError("❌ GOOGLE_CLIENT_ID not found in .env!")
    
    def generate_pkce_params(self):
        """Generate PKCE parameters (code_verifier, code_challenge, state)"""
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(64)).decode('utf-8').rstrip('=')
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode('utf-8').rstrip('=')
        state = base64.urlsafe_b64encode(secrets.token_bytes(16)).decode('utf-8').rstrip('=')
        
        return {
            'code_verifier': code_verifier,
            'code_challenge': code_challenge,
            'state': state
        }
    
    def build_authorization_url(self, code_challenge, state, redirect_uri, scopes=None):
        """Build Google OAuth authorization URL"""
        if scopes is None:
            scopes = ['openid', 'email', 'profile']
        
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'scope': ' '.join(scopes),
            'redirect_uri': redirect_uri,
            'state': state,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
        }
        
        from urllib.parse import urlencode
        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    
    def exchange_code_for_token(self, code, code_verifier, redirect_uri):
        """Exchange authorization code for access token
        
        Args:
            code: Authorization code from OAuth callback
            code_verifier: PKCE code verifier
            redirect_uri: Redirect URI used in authorization request
            
        Returns:
            dict with access_token, refresh_token, expires_in, token_type
        """
        
        if not self.client_secret:
            logger.warning("❌ GOOGLE_CLIENT_SECRET is empty - using public client mode")
        
        params = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': self.client_id,
            'code_verifier': code_verifier,
            'redirect_uri': redirect_uri,
        }
        
        # Include client_secret if available (required for confidential clients)
        if self.client_secret:
            params['client_secret'] = self.client_secret
        
        logger.info(f"📤 Exchanging code for token...")
        logger.info(f"   client_id: {self.client_id[:30]}...")
        logger.info(f"   client_secret: {'✅ Present' if self.client_secret else '⚠️ Empty (public client)'}")
        
        try:
            response = requests.post(
                GOOGLE_TOKEN_URL,
                data=params,
                headers={'Accept': 'application/json'},
                timeout=10
            )
            
            if not response.ok:
                error_data = response.json()
                error_desc = error_data.get('error_description', error_data.get('error', 'Unknown error'))
                logger.error(f"❌ Token exchange failed: {error_data}")
                raise Exception(f"Token exchange failed: {error_desc}")
            
            token_data = response.json()
            logger.info(f"✅ Token exchange successful!")
            logger.info(f"   access_token: {token_data.get('access_token', '')[:20]}...")
            logger.info(f"   refresh_token: {token_data.get('refresh_token', '')[:20] if token_data.get('refresh_token') else 'None'}...")
            logger.info(f"   expires_in: {token_data.get('expires_in', 'N/A')} seconds")
            
            return {
                'access_token': token_data.get('access_token'),
                'refresh_token': token_data.get('refresh_token'),
                'expires_in': token_data.get('expires_in'),
                'token_type': token_data.get('token_type', 'Bearer'),
                'scope': token_data.get('scope')
            }
        
        except requests.exceptions.Timeout:
            logger.error("❌ Token exchange timeout")
            raise Exception("Token exchange timeout (10s)")
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Network error during token exchange: {e}")
            raise Exception(f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"❌ Token exchange error: {e}")
            raise
    
    def refresh_access_token(self, refresh_token):
        """Refresh access token using refresh token
        
        Args:
            refresh_token: Refresh token from previous authentication
            
        Returns:
            dict with new access_token, expires_in, token_type
        """
        
        if not self.client_secret:
            logger.warning("❌ GOOGLE_CLIENT_SECRET is empty - token refresh may fail")
        
        params = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': self.client_id,
        }
        
        if self.client_secret:
            params['client_secret'] = self.client_secret
        
        logger.info("🔄 Refreshing access token...")
        
        try:
            response = requests.post(
                GOOGLE_TOKEN_URL,
                data=params,
                headers={'Accept': 'application/json'},
                timeout=10
            )
            
            if not response.ok:
                error_data = response.json()
                logger.error(f"❌ Token refresh failed: {error_data}")
                raise Exception(f"Token refresh failed: {error_data.get('error', 'Unknown')}")
            
            token_data = response.json()
            logger.info(f"✅ Token refresh successful!")
            
            return {
                'access_token': token_data.get('access_token'),
                'refresh_token': token_data.get('refresh_token') or refresh_token,
                'expires_in': token_data.get('expires_in'),
                'token_type': token_data.get('token_type', 'Bearer'),
            }
        
        except requests.exceptions.Timeout:
            logger.error("❌ Token refresh timeout")
            raise Exception("Token refresh timeout")
        except Exception as e:
            logger.error(f"❌ Token refresh error: {e}")
            raise
