"""
Secure Token Storage
Encrypted storage for OAuth tokens
"""
import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKENS_FILE = os.path.join(_BASE_DIR, "gemini_tokens.json")


def _load_tokens():
    """Load tokens from file"""
    if os.path.exists(TOKENS_FILE):
        try:
            with open(TOKENS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load tokens: {e}")
    return {}


def _save_tokens(data):
    """Save tokens to file with secure permissions"""
    try:
        # Use secure file permissions (0o600)
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        fd = os.open(TOKENS_FILE, flags, 0o600)
        with open(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"✅ Tokens saved securely to {TOKENS_FILE}")
    except Exception as e:
        logger.error(f"Failed to save tokens: {e}")
        raise


def save_user_token(chat_id, token_data):
    """Save OAuth token for a user
    
    Args:
        chat_id: Telegram chat ID
        token_data: dict with access_token, refresh_token, expires_in
    """
    try:
        tokens = _load_tokens()
        
        # Calculate expiry
        expires_in = token_data.get('expires_in', 3600)  # Default 1 hour
        expires_at = datetime.now().timestamp() + expires_in
        
        tokens[str(chat_id)] = {
            'access_token': token_data.get('access_token'),
            'refresh_token': token_data.get('refresh_token'),
            'expires_in': expires_in,
            'expires_at': expires_at,
            'token_type': token_data.get('token_type', 'Bearer'),
            'scope': token_data.get('scope'),
            'saved_at': datetime.now().isoformat()
        }
        
        _save_tokens(tokens)
        logger.info(f"✅ Token saved for user {chat_id}")
    
    except Exception as e:
        logger.error(f"Failed to save token for user {chat_id}: {e}")
        raise


def get_user_token(chat_id):
    """Get OAuth token for a user
    
    Args:
        chat_id: Telegram chat ID
        
    Returns:
        dict with token data or None if not found
    """
    try:
        tokens = _load_tokens()
        token_data = tokens.get(str(chat_id))
        
        if token_data:
            # Check if token is expired
            expires_at = token_data.get('expires_at', 0)
            if datetime.now().timestamp() > expires_at:
                logger.warning(f"⚠️ Token expired for user {chat_id}")
                return None
            
            logger.info(f"✅ Token found for user {chat_id}")
            return token_data
        
        logger.warning(f"⚠️ No token found for user {chat_id}")
        return None
    
    except Exception as e:
        logger.error(f"Failed to get token for user {chat_id}: {e}")
        return None


def delete_user_token(chat_id):
    """Delete OAuth token for a user
    
    Args:
        chat_id: Telegram chat ID
    """
    try:
        tokens = _load_tokens()
        if str(chat_id) in tokens:
            del tokens[str(chat_id)]
            _save_tokens(tokens)
            logger.info(f"✅ Token deleted for user {chat_id}")
        else:
            logger.warning(f"⚠️ No token to delete for user {chat_id}")
    
    except Exception as e:
        logger.error(f"Failed to delete token for user {chat_id}: {e}")
        raise


def update_token_expiry(chat_id, expires_in):
    """Update token expiry time
    
    Args:
        chat_id: Telegram chat ID
        expires_in: Seconds until expiry
    """
    try:
        tokens = _load_tokens()
        if str(chat_id) in tokens:
            tokens[str(chat_id)]['expires_at'] = datetime.now().timestamp() + expires_in
            _save_tokens(tokens)
            logger.info(f"✅ Token expiry updated for user {chat_id}")
    
    except Exception as e:
        logger.error(f"Failed to update token expiry for user {chat_id}: {e}")
