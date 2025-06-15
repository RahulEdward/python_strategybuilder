"""
Debug routes for troubleshooting
"""
from fastapi import APIRouter, Depends, Request, Response, Form
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.crud.user import get_user_by_username, authenticate_user
from app.core.security import verify_password
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
import os
import logging

logger = logging.getLogger(__name__)

# Initialize templates
templates_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates")
if os.path.exists(templates_dir):
    templates = Jinja2Templates(directory=templates_dir)
    logger.info(f"Debug templates loaded from {templates_dir}")
else:
    logger.error(f"Templates directory {templates_dir} not found")
    templates = None

router = APIRouter()

@router.get("/test-login/{username}/{password}")
async def test_login(username: str, password: str, db: Session = Depends(get_db)):
    """Test login functionality"""
    # Get user
    user = get_user_by_username(db, username)
    
    # Check if user exists
    if not user:
        return {"status": "error", "message": "User not found", "username": username}
    
    # Check password
    password_verified = verify_password(password, user.password_hash)
    
    # Return result
    return {
        "status": "success" if password_verified else "error",
        "message": "Password verified" if password_verified else "Password incorrect",
        "user_exists": True,
        "username": username,
        "password_field_in_db": "password_hash",
        "password_hash_in_db": user.password_hash[:10] + "..." if user.password_hash else None
    }

@router.get("/test-logout")
async def test_logout():
    """Test logout functionality"""
    # Create response
    response = RedirectResponse(url="/?message=Logged out successfully", status_code=302)
    
    # Clear the authentication cookie
    response.delete_cookie(key="access_token", path="/")
    
    # Add security headers
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    
    logger.info("Debug logout executed")
    
    return response

@router.post("/test-logout-form")
async def test_logout_form():
    """Test logout functionality with form submission"""
    # Create response
    response = RedirectResponse(url="/?message=Logged out successfully", status_code=302)
    
    # Clear the authentication cookie
    response.delete_cookie(key="access_token", path="/")
    
    # Add security headers
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    
    logger.info("Debug logout form executed")
    
    return response

@router.get("/test-logout-page")
async def test_logout_page(request: Request):
    """Serve a test page with various logout methods"""
    if templates:
        return templates.TemplateResponse("test_logout.html", {"request": request})
    else:
        return HTMLResponse(content="<html><body><h1>Templates not available</h1></body></html>")
