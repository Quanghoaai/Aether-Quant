"""
OAuth Middleware
Handles token refresh and validation
"""
import logging
from datetime import datetime
from src.secure_storage import get_user_token, update_token_expiry
from src.oauth_service import GoogleOAuthService

logger = logging.getLogger(__name__)


def is_token_expired(chat_id):
    """Check if user's token is expired
    
    Args:
        chat_id: Telegram chat ID
        
    Returns:
        bool: True if expired or not found
    """
    token_data = get_user_token(chat_id)
    if not token_data:
        return True
    
    expires_at = token_data.get('expires_at', 0)
    return datetime.now().timestamp() > expires_at


def get_valid_token(chat_id):
    """Get valid access token, refreshing if necessary
    
    Args:
        chat_id: Telegram chat ID
        
    Returns:
        str: Valid access token or None
    """
    token_data = get_user_token(chat_id)
    if not token_data:
        logger.warning(f"⚠️ No token found for user {chat_id}")
        return None
    
    # Check if token is about to expire (within 5 minutes)
    expires_at = token_data.get('expires_at', 0)
    expires_in = expires_at - datetime.now().timestamp()
    
    if expires_in < 300:  # 5 minutes
        logger.info(f"🔄 Token expiring soon for user {chat_id}, refreshing...")
        return refresh_user_token(chat_id)
    
    return token_data.get('access_token')


def refresh_user_token(chat_id):
    """Refresh user's access token
    
    Args:
        chat_id: Telegram chat ID
        
    Returns:
        str: New access token or None
    """
    token_data = get_user_token(chat_id)
    if not token_data or not token_data.get('refresh_token'):
        logger.error(f"❌ Cannot refresh token for user {chat_id} - no refresh token")
        return None
    
    try:
        service = GoogleOAuthService()
        new_tokens = service.refresh_access_token(token_data['refresh_token'])
        
        if new_tokens:
            # Update stored token
            from src.secure_storage import save_user_token
            save_user_token(chat_id, new_tokens)
            logger.info(f"✅ Token refreshed for user {chat_id}")
            return new_tokens.get('access_token')
        else:
            logger.error(f"❌ Failed to refresh token for user {chat_id}")
            return None
    
    except Exception as e:
        logger.error(f"❌ Token refresh error for user {chat_id}: {e}")
        return None


def require_auth(chat_id):
    """Check if user is authenticated
    
    Args:
        chat_id: Telegram chat ID
        
    Returns:
        bool: True if authenticated
    """
    token_data = get_user_token(chat_id)
    if not token_data:
        return False
    
    expires_at = token_data.get('expires_at', 0)
    if datetime.now().timestamp() > expires_at:
        logger.warning(f"⚠️ Token expired for user {chat_id}")
        return False
    
    return True
