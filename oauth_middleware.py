import time
import logging
from typing import Optional
from secure_storage import get_user_token, save_user_token
from oauth_service import GoogleOAuthService
import os

logger = logging.getLogger(__name__)

def get_valid_token(chat_id: int) -> Optional[str]:
    """Get a valid access token for the user, refreshing it if necessary."""
    token_data = get_user_token(chat_id)
    if not token_data:
        return None
    
    access_token = token_data.get("access_token")
    expires_at = token_data.get("expires_at", 0)
    refresh_token = token_data.get("refresh_token")
    
    # Check if token is expired or about to expire (within 60 seconds)
    if time.time() > (expires_at - 60):
        if not refresh_token:
            return None
            
        logger.info(f"Refreshing token for user {chat_id}")
        client_id = os.environ.get("GOOGLE_CLIENT_ID", "681255809395-oo8ft2oprdrnp9e3aqf6av3hmdib135j.apps.googleusercontent.com")
        service = GoogleOAuthService(client_id)
        
        new_token_data = service.refresh_access_token(refresh_token)
        if new_token_data:
            # Preserve old refresh token if not provided in refresh response
            if "refresh_token" not in new_token_data:
                new_token_data["refresh_token"] = refresh_token
            
            save_user_token(chat_id, new_token_data)
            return new_token_data.get("access_token")
        else:
            logger.error(f"Failed to refresh token for user {chat_id}")
            return None
            
    return access_token

def require_auth(chat_id: int) -> bool:
    """Check if the user has a valid or refreshable token."""
    token_data = get_user_token(chat_id)
    if not token_data:
        return False
    return True
