import os
import json
import logging
import time
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# File path for tokens
TOKENS_FILE = "gemini_tokens.json"

def save_user_token(user_id: str, token_data: Dict[str, Any]):
    """Save user token securely with 0o600 permissions."""
    try:
        all_tokens = {}
        if os.path.exists(TOKENS_FILE):
            try:
                with open(TOKENS_FILE, "r") as f:
                    all_tokens = json.load(f)
            except:
                all_tokens = {}
        
        all_tokens[str(user_id)] = token_data
        
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        fd = os.open(TOKENS_FILE, flags, 0o600)
        with os.fdopen(fd, 'w') as f:
            json.dump(all_tokens, f, indent=2)
            
        logger.info(f"Token saved for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to save token for user {user_id}: {e}")

def get_user_token(user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve user token from storage."""
    try:
        if not os.path.exists(TOKENS_FILE):
            return None
        with open(TOKENS_FILE, "r") as f:
            all_tokens = json.load(f)
        return all_tokens.get(str(user_id))
    except Exception as e:
        logger.error(f"Failed to get token for user {user_id}: {e}")
        return None

def delete_user_token(user_id: str):
    """Delete user token."""
    try:
        if not os.path.exists(TOKENS_FILE):
            return
        with open(TOKENS_FILE, "r") as f:
            all_tokens = json.load(f)
        chat_str = str(user_id)
        if chat_str in all_tokens:
            del all_tokens[chat_str]
            flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
            fd = os.open(TOKENS_FILE, flags, 0o600)
            with os.fdopen(fd, 'w') as f:
                json.dump(all_tokens, f, indent=2)
        logger.info(f"Token deleted for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to delete token for user {user_id}: {e}")

def is_token_expired(token_data: Dict[str, Any]) -> bool:
    """Check if token is expired or about to expire (within 60 seconds)."""
    return token_data.get('expires_at', 0) < time.time() + 60
