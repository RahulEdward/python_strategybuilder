"""
Dashboard routes for authenticated users
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """User dashboard page - requires authentication"""
    return templates.TemplateResponse(
        "dashboard.html", 
        {
            "request": request,
            "user": current_user,
            "username": current_user.username,
            "email": current_user.email
        }
    )