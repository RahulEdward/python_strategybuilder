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
            "token_expires": settings.access_token_expire_minutes
        })
    else:
        response = RedirectResponse(url=redirect_url, status_code=302)
    
    # Set secure HTTP-only cookie with enhanced security
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=getattr(settings, 'secure_cookies', False),  # Set to True in production with HTTPS
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        path="/"
    )
    
    # Add security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    return response

# ========== AUTHENTICATION ROUTES ==========

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, current_user = Depends(get_current_user_optional)):
    """Display login page with enhanced user experience"""
    try:
        if current_user:
            logger.info(f"User {current_user.username} already logged in, redirecting to dashboard")
            if is_api_request(request):
                return JSONResponse(content={
                    "message": "Already logged in", 
                    "redirect": "/dashboard",
                    "user": {"username": current_user.username, "email": current_user.email}
                })
            return RedirectResponse(url="/dashboard", status_code=302)
        
        # Check for previous messages
        message = request.query_params.get("message")
        error = request.query_params.get("error")
        
        if is_api_request(request):
            return JSONResponse(content={
                "message": "Login page", 
                "login_url": "/api/auth/login",
                "register_url": "/api/auth/register",
                "endpoints": {
                    "login": "POST /api/auth/login",
                    "register": "POST /api/auth/register"
                }
            })
            
        return templates.TemplateResponse("login.html", {
            "request": request,
            "message": message,
            "error": error,
            "app_name": "Strategy Builder SaaS"
        })
        
    except Exception as e:
        logger.error(f"Error in login_page: {str(e)}")
        if is_api_request(request):
            return JSONResponse(content={"error": "Internal server error"}, status_code=500)
        raise HTTPException(status_code=500, detail="Internal server error")

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
        logger.debug(f"Content-Type: {request.headers.get('content-type', 'not set')}")
        logger.debug(f"User-Agent: {request.headers.get('user-agent', 'not set')}")
        
        # Handle JSON requests
        request_data = {}
        if is_api_request(request):
            try:
                body = await request.body()
                if body:
                    request_data = json.loads(body.decode())
                    username = request_data.get("username")
                    password = request_data.get("password")
                    remember_me = request_data.get("remember_me", False)
                    logger.debug("JSON data extracted successfully")
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON body: {str(e)}")
                return handle_error_response(request, "login.html", "Invalid JSON data", 400)
            except Exception as e:
                logger.error(f"Error processing request body: {str(e)}")
                return handle_error_response(request, "login.html", "Request processing error", 400)
        
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
        
        # Create response with token (extended expiry if remember_me is checked)
        if remember_me:
            settings.access_token_expire_minutes = 60 * 24 * 7  # 7 days
        
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

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, current_user = Depends(get_current_user_optional)):
    """Enhanced registration page with better UX"""
    try:
        if current_user:
            logger.info(f"User {current_user.username} already logged in, redirecting to dashboard")
            if is_api_request(request):
                return JSONResponse(content={
                    "message": "Already logged in", 
                    "redirect": "/dashboard",
                    "user": {"username": current_user.username, "email": current_user.email}
                })
            return RedirectResponse(url="/dashboard", status_code=302)
        
        # Check for messages
        message = request.query_params.get("message")
        error = request.query_params.get("error")
        
        if is_api_request(request):
            return JSONResponse(content={
                "message": "Register page", 
                "register_url": "/api/auth/register",
                "login_url": "/api/auth/login",
                "requirements": {
                    "username": "3-50 characters, letters, numbers, dots, hyphens, underscores only",
                    "email": "Valid email address required",
                    "password": "Minimum 6 characters, recommended 8+ with letters and numbers"
                }
            })
            
        return templates.TemplateResponse("register.html", {
            "request": request,
            "message": message,
            "error": error,
            "app_name": "Strategy Builder SaaS"
        })
        
    except Exception as e:
        logger.error(f"Error in register_page: {str(e)}")
        if is_api_request(request):
            return JSONResponse(content={"error": "Internal server error"}, status_code=500)
        raise HTTPException(status_code=500, detail="Internal server error")

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
        
        # Check terms acceptance (if required)
        if hasattr(settings, 'require_terms_acceptance') and settings.require_terms_acceptance:
            if not terms_accepted:
                error_msg = "You must accept the terms and conditions"
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

@router.get("/logout")
async def logout_get(request: Request, current_user = Depends(get_current_user_optional)):
    """Logout via GET request for convenience"""
    try:
        user_info = ""
        if current_user:
            user_info = f" for user {current_user.username}"
            logger.info(f"User logout{user_info}")
        else:
            logger.info("Anonymous logout attempt")
        
        # Create a redirect response
        response = RedirectResponse(url="/login", status_code=303)
        
        # Clear the authentication cookie
        response.delete_cookie(key="access_token", path="/")
        
        # Add security headers
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        
        logger.info(f"Logout successful, redirecting to /login")
        return response
        
    except Exception as e:
        logger.error(f"Error in logout: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

# ========== USER MANAGEMENT ROUTES ==========

@router.get("/me")
async def get_current_user_info(current_user = Depends(get_current_user)):
    """Get current authenticated user information"""
    try:
        return {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "is_active": current_user.is_active,
            "created_at": current_user.created_at.isoformat() if hasattr(current_user, 'created_at') else None,
            "last_login": current_user.last_login.isoformat() if hasattr(current_user, 'last_login') else None
        }
    except Exception as e:
        logger.error(f"Error getting user info: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get user information")

@router.put("/me")
async def update_user_profile(
    request: Request,
    email: Optional[str] = Form(None),
    current_password: Optional[str] = Form(None),
    new_password: Optional[str] = Form(None),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile information"""
    try:
        # Handle JSON requests
        if is_api_request(request):
            body = await request.body()
            if body:
                data = json.loads(body.decode())
                email = data.get("email")
                current_password = data.get("current_password")
                new_password = data.get("new_password")
        
        # Update email if provided
        if email and email != current_user.email:
            if not validate_email(email):
                raise HTTPException(status_code=400, detail="Invalid email format")
            
            # Check if email already exists
            existing_email = get_user_by_email(db, email)
            if existing_email and existing_email.id != current_user.id:
                raise HTTPException(status_code=400, detail="Email already in use")
            
            current_user.email = email
        
        # Update password if provided
        if new_password:
            if not current_password:
                raise HTTPException(status_code=400, detail="Current password required to change password")
            
            # Verify current password
            if not verify_password(current_password, current_user.password_hash):
                raise HTTPException(status_code=400, detail="Current password is incorrect")
            
            # Validate new password
            is_valid, error_msg = validate_password_strength(new_password)
            if not is_valid:
                raise HTTPException(status_code=400, detail=error_msg)
            
            current_user.password_hash = get_password_hash(new_password)
        
        # Save changes
        db.commit()
        db.refresh(current_user)
        
        logger.info(f"Profile updated for user: {current_user.username}")
        
        return {
            "message": "Profile updated successfully",
            "user": {
                "username": current_user.username,
                "email": current_user.email
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating profile: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update profile")

# ========== UTILITY ROUTES ==========

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
            "update_profile": "PUT /api/auth/me"
        },
        "security_features": [
            "JWT tokens",
            "HTTP-only cookies",
            "Password strength validation",
            "Email validation",
            "Rate limiting ready",
            "CORS protection"
        ]
    }

@router.get("/test-db")
async def test_database_connection(db: Session = Depends(get_db)):
    """Enhanced database connection test"""
    try:
        # Test basic connection
        result = db.execute(text("SELECT 1 as test")).fetchone()
        
        # Test user table access
        user_count = db.execute(text("SELECT COUNT(*) as count FROM users")).fetchone()
        
        db_url = str(db.get_bind().url)
        # Hide password in URL for security
        if db.get_bind().url.password:
            db_url = db_url.replace(str(db.get_bind().url.password), "***")
        
        return {
            "status": "database_connected",
            "query_result": result[0] if result else None,
            "user_count": user_count[0] if user_count else 0,
            "database_url": db_url,
            "database_type": db.get_bind().name
        }
    except Exception as e:
        logger.error(f"Database connection test failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database connection failed: {str(e)}"
        )

@router.post("/create-test-user")
async def create_test_user(db: Session = Depends(get_db)):
    """Create enhanced test user for debugging"""
    try:
        # Check if test user already exists
        existing_user = get_user_by_username(db, "testuser")
        if existing_user:
            return JSONResponse(content={
                "message": "Test user already exists",
                "username": "testuser",
                "email": "test@example.com",
                "status": "exists",
                "login_credentials": {
                    "username": "testuser",
                    "password": "test123456"
                }
            })
        
        # Create test user with stronger password
        user_data = UserCreate(
            username="testuser",
            email="test@example.com",
            password="test123456"
        )
        
        user = create_user(db, user_data)
        
        logger.info("Test user created successfully")
        
        return JSONResponse(content={
            "message": "Test user created successfully",
            "username": user.username,
            "email": user.email,
            "status": "created",
            "login_credentials": {
                "username": "testuser",
                "password": "test123456"
            },
            "note": "Use these credentials to test login functionality"
        })
        
    except Exception as e:
        logger.error(f"Error creating test user: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@router.post("/forgot-password")
async def forgot_password(
    request: Request, 
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    """Enhanced password reset request"""
    try:
        # Validate email format
        if not validate_email(email):
            error_msg = "Please enter a valid email address"
            return handle_error_response(request, "login.html", error_msg, 400)
        
        # Check if user exists (don't reveal if email exists for security)
        user = get_user_by_email(db, email.strip().lower())
        
        # Always return success message for security
        success_msg = "If this email is registered, you will receive password reset instructions"
        
        if user:
            # In production, implement actual password reset logic here:
            # 1. Generate secure reset token
            # 2. Store token with expiration
            # 3. Send email with reset link
            logger.info(f"Password reset requested for existing email: {email}")
        else:
            logger.info(f"Password reset requested for non-existent email: {email}")
        
        if is_api_request(request):
            return JSONResponse(content={
                "message": success_msg,
                "status": "success"
            })
        else:
            return templates.TemplateResponse(
                "login.html",
                {
                    "request": request, 
                    "message": success_msg,
                    "app_name": "Strategy Builder SaaS"
                }
            )
            
    except Exception as e:
        logger.error(f"Error in forgot password: {str(e)}")
        error_msg = "Password reset service temporarily unavailable"
        return handle_error_response(request, "login.html", error_msg, 500)

# Rate limiting placeholder route
@router.get("/rate-limit-info")
async def rate_limit_info():
    """Information about rate limiting (for future implementation)"""
    return {
        "info": "Rate limiting not yet implemented",
        "future_limits": {
            "login_attempts": "5 per minute per IP",
            "registration": "3 per hour per IP",
            "password_reset": "3 per hour per email"
        },
        "recommendation": "Implement rate limiting with Redis or similar"
    }