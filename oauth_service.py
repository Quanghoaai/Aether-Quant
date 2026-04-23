import os
import hashlib
import secrets
import base64
import urllib.parse
import requests
import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class GoogleOAuthService:
    def __init__(self, client_id: str, client_secret: str = ""):
        self.client_id = client_id
        self.client_secret = client_secret
        self.auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        self.token_url = "https://oauth2.googleapis.com/token"
        self.scopes = [
            "openid",
            "email",
            "profile",
            "https://www.googleapis.com/auth/generative-language",
            "https://www.googleapis.com/auth/cloud-platform"
        ]

    def generate_pkce_params(self) -> Dict[str, str]:
        """Generate PKCE parameters: code_verifier, code_challenge, and state."""
        # Code Verifier: high-entropy cryptographic random string
        # Recommended length is between 43 and 128 characters
        verifier = secrets.token_urlsafe(64)
        
        # Code Challenge: Base64URL encoded SHA256 hash of the code verifier
        sha256_hash = hashlib.sha256(verifier.encode('utf-8')).digest()
        challenge = base64.urlsafe_b64encode(sha256_hash).decode('utf-8').rstrip('=')
        
        # State: CSRF protection
        state = secrets.token_urlsafe(32)
        
        return {
            "code_verifier": verifier,
            "code_challenge": challenge,
            "state": state
        }

    def build_authorization_url(self, pkce_params: Dict[str, str], redirect_uri: str) -> str:
        """Build the Google OAuth 2.0 authorization URL."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "state": pkce_params["state"],
            "access_type": "offline",
            "prompt": "consent",
            "code_challenge": pkce_params["challenge"],
            "code_challenge_method": "S256"
        }
        return f"{self.auth_url}?{urllib.parse.urlencode(params)}"

    def exchange_code_for_token(self, code: str, code_verifier: str, redirect_uri: str) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for access and refresh tokens."""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "code_verifier": code_verifier,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri
        }
        
        try:
            response = requests.post(self.token_url, data=data)
            if response.status_code == 200:
                token_data = response.json()
                # Add expiry timestamp
                expires_in = token_data.get("expires_in", 3600)
                token_data["expires_at"] = datetime.now().timestamp() + expires_in
                return token_data
            else:
                logger.error(f"Token exchange failed: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error exchanging code for token: {e}")
            return None

    def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Refresh an expired access token using the refresh token."""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }
        
        try:
            response = requests.post(self.token_url, data=data)
            if response.status_code == 200:
                token_data = response.json()
                # If refresh_token is not in response, keep the old one
                if "refresh_token" not in token_data:
                    token_data["refresh_token"] = refresh_token
                
                expires_in = token_data.get("expires_in", 3600)
                token_data["expires_at"] = datetime.now().timestamp() + expires_in
                return token_data
            else:
                logger.error(f"Token refresh failed: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            return None
