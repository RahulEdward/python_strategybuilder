"""
Authentication service for handling JWT tokens and user authentication
"""
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt
import logging

from app.core.config import settings
from app.db.session import get_db
from app.crud.user import get_user_by_username
from app.models.user import User

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

def get_token_from_cookie(request: Request) -> Optional[str]:
    """Extract JWT token from HTTP-only cookie"""
    token = request.cookies.get("access_token")
    logger.info(f"🍪 Cookie check - Token: {'Found' if token else 'Not found'}")
    if token:
        logger.info(f"🍪 Cookie token preview: {token[:50]}...")
    return token

def get_token_from_header(credentials: Optional[HTTPAuthorizationCredentials]) -> Optional[str]:
    """Extract JWT token from Authorization header"""
    if credentials:
        logger.info(f"📋 Header token preview: {credentials.credentials[:50]}...")
        return credentials.credentials
    logger.info("📋 No Authorization header found")
    return None

async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if authenticated, return None if not.
    Supports both cookie and header-based authentication.
    """
    try:
        logger.info("🔍 AUTH SERVICE: Starting authentication check...")
        
        # Try to get token from cookie first (preferred for web)
        token = get_token_from_cookie(request)
        token_source = "cookie"
        
        # If no cookie token, try header token (for API clients)
        if not token:
            token = get_token_from_header(credentials)
            token_source = "header"
        
        if not token:
            logger.info("❌ No token found in cookies or headers")
            return None
        
        logger.info(f"🔑 Token found in {token_source}, attempting verification...")
        
        # Debug: Check settings
        logger.info(f"⚙️ JWT Settings - Secret: {'***' + settings.secret_key[-4:] if len(settings.secret_key) > 4 else 'SHORT'}")
        logger.info(f"⚙️ JWT Algorithm: {settings.algorithm}")
        
        # Verify and decode token
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
            logger.info(f"✅ Token decoded successfully. Payload keys: {list(payload.keys())}")
            
            username: str = payload.get("sub")
            if username is None:
                logger.warning("❌ No 'sub' field found in token payload")
                logger.info(f"Available payload fields: {payload}")
                return None
                
            logger.info(f"✅ Token verification successful for user: {username}")
            
        except JWTError as e:
            logger.warning(f"❌ JWT verification failed: {str(e)}")
            logger.info(f"Failed token preview: {token[:50]}...")
            return None
        
        # Get user from database
        logger.info(f"🔍 Looking up user in database: {username}")
        user = get_user_by_username(db, username)
        if user is None:
            logger.warning(f"❌ User not found in database: {username}")
            return None
            
        if not user.is_active:
            logger.warning(f"❌ User is not active: {username}")
            return None
            
        logger.info(f"🎉 Successfully authenticated user: {username}")
        return user
        
    except Exception as e:
        logger.error(f"💥 Unexpected error in get_current_user_optional: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user or raise 401.
    Required for protected endpoints.
    """
    user = await get_current_user_optional(request, credentials, db)
    
    if user is None:
        logger.warning("❌ Authentication failed - raising 401")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user