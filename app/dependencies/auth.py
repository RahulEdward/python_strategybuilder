# dependencies/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from models.user import User
import jwt
from typing import Optional

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """
    Dependency to get current authenticated user.
    Replace this with your actual authentication logic.
    """
    try:
        # Decode JWT token (replace with your actual logic)
        token = credentials.credentials
        # payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        # user_id = payload.get("user_id")
        
        # For demo purposes, return a mock user
        # In production, fetch user from database using user_id
        mock_user = User(
            id=1,
            email="user@example.com",
            username="testuser",
            is_active=True
        )
        return mock_user
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )