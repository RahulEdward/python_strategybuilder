"""
Authentication routes for login, register, and logout
Enhanced with better error handling, security, and strategy integration
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
import logging
import json
from typing import Optional
import re

from app.db.session import get_db
from app.schemas.user import UserCreate, UserLogin, UserResponse
from app.crud.user import create_user, authenticate_user, get_user_by_username, get_user_by_email
from app.core.security import create_access_token, verify_password, get_password_hash
from app.core.config import settings
from app.services.auth_service import get_current_user_optional, get_current_user

# Setup logging
logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Enhanced helper functions
def is_api_request(request: Request) -> bool:
    """Detect if request is from API client or browser form"""
    content_type = request.headers.get("content-type", "")
    accept_header = request.headers.get("accept", "")
    user_agent = request.headers.get("user-agent", "").lower()
    
    # Check for API indicators
    is_api = (
        "application/json" in content_type or 
        "application/json" in accept_header or
        request.headers.get("x-requested-with") == "XMLHttpRequest" or
        "postman" in user_agent or
        "insomnia" in user_agent or
        "curl" in user_agent or
        "python" in user_agent
    )
    
    logger.debug(f"Request type detection - API: {is_api}, Content-Type: {content_type}, Accept: {accept_header}")
    return is_api

def validate_email(email: str) -> bool:
    """Enhanced email validation"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password strength and return (is_valid, error_message)"""
    if len(password) < 6:
        return False, "Password must be at least 6 characters long"
    
    if len(password) > 128:
        return False, "Password must be less than 128 characters"
    
    # Check for at least one letter and one number for stronger passwords
    if len(password) >= 8:
        if not re.search(r'[A-Za-z]', password):
            return False, "Password should contain at least one letter"
        if not re.search(r'\d', password):
            return False, "Password should contain at least one number"
    
    return True, ""

def validate_username(username: str) -> tuple[bool, str]:
    """Validate username format"""
    if len(username) < 3:
        return False, "Username must be at least 3 characters long"
    
    if len(username) > 50:
        return False, "Username must be less than 50 characters"
    
    if not re.match(r'^[a-zA-Z0-9_.-]+$', username):
        return False, "Username can only contain letters, numbers, dots, hyphens, and underscores"
    
    return True, ""

def handle_error_response(request: Request, template_name: str, error_msg: str, status_code: int = 400):
    """Enhanced error response handler with better logging"""
    logger.warning(f"Error response: {error_msg} (Status: {status_code})")
    
    if is_api_request(request):
        return JSONResponse(
            content={
                "error": error_msg, 
                "status": "error",
                "code": status_code,
                "timestamp": str(timedelta())
            },
            status_code=status_code
        )
    else:
        return templates.TemplateResponse(
            template_name,
            {
                "request": request, 
                "error": error_msg,
                "error_type": "validation" if status_code == 400 else "server"
            },
            status_code=status_code
        )

def create_response_with_token(request: Request, user, redirect_url: str = "/dashboard"):
    """Create response with JWT token and proper security headers"""
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    user_data = {
        "username": user.username, 
        "email": user.email,
        "id": user.id,
        "is_active": user.is_active
    }
    
    if is_api_request(request):
        response = JSONResponse(content={
            "message": "Authentication successful", 
            "redirect": redirect_url,
            "status": "success",
            "user": user_data,
            "access_token": access_token,  # ✅ Include token for Next.js
            "token_type": "bearer",
            "token_expires": settings.access_token_expire_minutes
        })
    else:
        response = RedirectResponse(url=redirect_url, status_code=302)
    
    # ✅ Set cookie with proper settings for localhost
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,  # ✅ False for localhost development
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
        domain=None  # ✅ Don't set domain for localhost
    )
    
    # Add security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    return response

# ========== AUTHENTICATION ROUTES ==========

@router.post("/login")
async def login(
    request: Request,
    username: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    remember_me: Optional[bool] = Form(False),
    db: Session = Depends(get_db)
):
    """Enhanced user authentication with better security and logging"""
    try:
        # Enhanced logging
        client_ip = request.client.host if request.client else "unknown"
        logger.info(f"Login attempt from IP: {client_ip}")
        
        # Handle JSON requests from Next.js frontend
        content_type = request.headers.get('content-type', '')
        if 'application/json' in content_type.lower():
            try:
                data = await request.json()
                username = data.get('username')
                password = data.get('password')
                remember_me = data.get('remember_me', False)
                logger.info(f"Processing JSON login request for user: {username}")
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in request: {str(e)}")
                return JSONResponse(
                    content={"detail": "Invalid JSON format"}, 
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        
        logger.info(f"Login attempt for username: '{username}' (Remember me: {remember_me})")
        
        # Enhanced input validation
        if not username or not password:
            error_msg = "Username and password are required"
            logger.warning(f"Validation failed: {error_msg}")
            return handle_error_response(request, "login.html", error_msg, 400)
        
        # Clean and validate input
        username = username.strip()
        password = password.strip()
        
        # Enhanced validation
        is_valid_username, username_error = validate_username(username)
        if not is_valid_username:
            logger.warning(f"Username validation failed: {username_error}")
            return handle_error_response(request, "login.html", username_error, 400)
        
        if len(password) < 1:
            error_msg = "Password cannot be empty"
            logger.warning(f"Validation failed: {error_msg}")
            return handle_error_response(request, "login.html", error_msg, 400)
        
        # Test database connection
        try:
            db.execute(text("SELECT 1"))
            logger.debug("Database connection successful")
        except Exception as e:
            logger.error(f"Database connection failed: {str(e)}")
            error_msg = "Database connection error. Please try again."
            return handle_error_response(request, "login.html", error_msg, 500)
        
        # Authenticate user with enhanced error handling
        logger.info(f"Attempting authentication for user: '{username}'")
        try:
            user = authenticate_user(db, username, password)
        except Exception as e:
            logger.error(f"Authentication error for user '{username}': {str(e)}")
            error_msg = "Authentication service error. Please try again."
            return handle_error_response(request, "login.html", error_msg, 500)
        
        if not user:
            error_msg = "Incorrect username or password"
            logger.warning(f"Authentication failed for username: '{username}' from IP: {client_ip}")
            return handle_error_response(request, "login.html", error_msg, 401)
        
        # Check if user is active
        if not user.is_active:
            error_msg = "Account is deactivated. Please contact support."
            logger.warning(f"Login attempt for inactive user: '{username}'")
            return handle_error_response(request, "login.html", error_msg, 403)
        
        # Successful authentication
        logger.info(f"Successful login for username: '{username}' from IP: {client_ip}")
        
        return create_response_with_token(request, user, "/dashboard")
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error in login: {str(e)}")
        error_msg = "Database connection error. Please try again."
        return handle_error_response(request, "login.html", error_msg, 500)
    except Exception as e:
        logger.error(f"Unexpected error in login: {str(e)}")
        error_msg = "Internal server error. Please try again."
        return handle_error_response(request, "login.html", error_msg, 500)

@router.post("/register")
async def register(
    request: Request,
    username: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    confirm_password: Optional[str] = Form(None),
    terms_accepted: Optional[bool] = Form(False),
    db: Session = Depends(get_db)
):
    """Enhanced user registration with comprehensive validation"""
    try:
        client_ip = request.client.host if request.client else "unknown"
        logger.info(f"Registration attempt from IP: {client_ip}")
        
        # Handle JSON requests
        if is_api_request(request):
            try:
                body = await request.body()
                if body:
                    data = json.loads(body.decode())
                    username = data.get("username")
                    email = data.get("email")
                    password = data.get("password")
                    confirm_password = data.get("confirm_password")
                    terms_accepted = data.get("terms_accepted", False)
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON body: {str(e)}")
                return handle_error_response(request, "register.html", "Invalid JSON data", 400)
        
        logger.info(f"Registration attempt for username: '{username}', email: '{email}'")
        
        # Enhanced input validation
        if not username or not email or not password:
            error_msg = "Username, email, and password are required"
            return handle_error_response(request, "register.html", error_msg, 400)
        
        # Clean input
        username = username.strip()
        email = email.strip().lower()
        password = password.strip()
        
        # Validate username
        is_valid_username, username_error = validate_username(username)
        if not is_valid_username:
            return handle_error_response(request, "register.html", username_error, 400)
        
        # Validate email
        if not validate_email(email):
            error_msg = "Please enter a valid email address"
            return handle_error_response(request, "register.html", error_msg, 400)
        
        # Validate password strength
        is_valid_password, password_error = validate_password_strength(password)
        if not is_valid_password:
            return handle_error_response(request, "register.html", password_error, 400)
        
        # Check password confirmation
        if confirm_password and password != confirm_password:
            error_msg = "Passwords do not match"
            return handle_error_response(request, "register.html", error_msg, 400)
        
        # Test database connection
        try:
            db.execute(text("SELECT 1"))
        except Exception as e:
            logger.error(f"Database connection failed: {str(e)}")
            error_msg = "Database connection error. Please try again."
            return handle_error_response(request, "register.html", error_msg, 500)
        
        # Check if user already exists
        try:
            existing_user = get_user_by_username(db, username)
            if existing_user:
                error_msg = "Username already exists. Please choose a different username."
                logger.warning(f"Registration failed - username exists: {username}")
                return handle_error_response(request, "register.html", error_msg, 400)
            
            existing_email = get_user_by_email(db, email)
            if existing_email:
                error_msg = "Email already registered. Please use a different email or try logging in."
                logger.warning(f"Registration failed - email exists: {email}")
                return handle_error_response(request, "register.html", error_msg, 400)
        except Exception as e:
            logger.error(f"Error checking existing users: {str(e)}")
            error_msg = "Registration service error. Please try again."
            return handle_error_response(request, "register.html", error_msg, 500)
        
        # Create new user
        try:
            user_data = UserCreate(username=username, email=email, password=password)
            user = create_user(db, user_data)
            logger.info(f"User created successfully: {username} ({email})")
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            error_msg = "Failed to create user account. Please try again."
            return handle_error_response(request, "register.html", error_msg, 500)
        
        # Log successful registration
        logger.info(f"Successful registration for username: '{username}', email: '{email}' from IP: {client_ip}")
        
        # Create response with token and redirect to dashboard
        return create_response_with_token(request, user, "/dashboard")
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error in register: {str(e)}")
        error_msg = "Database connection error. Please try again."
        return handle_error_response(request, "register.html", error_msg, 500)
    except Exception as e:
        logger.error(f"Unexpected error in register: {str(e)}")
        error_msg = "Internal server error. Please try again."
        return handle_error_response(request, "register.html", error_msg, 500)

@router.get("/me")
async def get_current_user_info(current_user = Depends(get_current_user)):
    """Get current authenticated user information - FIXED VERSION"""
    try:
        return {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "is_active": current_user.is_active,
            # ✅ FIXED: Safe handling of None dates
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
            "last_login": current_user.last_login.isoformat() if current_user.last_login else None
        }
    except Exception as e:
        logger.error(f"Error getting user info: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get user information")

@router.post("/logout")
async def logout(request: Request, current_user = Depends(get_current_user_optional)):
    """Enhanced logout with proper cleanup"""
    try:
        user_info = ""
        if current_user:
            user_info = f" for user {current_user.username}"
            logger.info(f"User logout{user_info}")
        else:
            logger.info("Anonymous logout attempt")
        
        # Always use a redirect response for browser requests
        response = RedirectResponse(url="/?message=Logged out successfully", status_code=303)
        
        # Clear the authentication cookie
        response.delete_cookie(key="access_token", path="/")
        
        # Add security headers
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        
        logger.info(f"Logout successful, redirecting to /")
        return response
        
    except Exception as e:
        logger.error(f"Error in logout: {str(e)}")
        if is_api_request(request):
            return JSONResponse(content={"error": "Internal server error"}, status_code=500)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/health")
async def health_check():
    """Enhanced health check endpoint"""
    return {
        "status": "healthy", 
        "service": "auth",
        "version": "2.0.0",
        "endpoints": {
            "login": "POST /api/auth/login",
            "register": "POST /api/auth/register",
            "logout": "POST /api/auth/logout",
            "profile": "GET /api/auth/me",
        }
    }