"""
FastAPI Strategy Builder SaaS App Entry Point
MINIMAL FIX - Only fixing the is_active error
"""
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text  # Add this import for raw SQL
import logging
import json
import os
from typing import Optional
from datetime import datetime  # Add this import

from app.api.routes import auth, builder, dashboard, debug
from app.core.config import settings
from app.db.session import engine, get_db
from app.models import Base
from app.services.auth_service import get_current_user_optional

# Setup logging
logger = logging.getLogger(__name__)

# Create database tables
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
except Exception as e:
    logger.error(f"Error creating database tables: {str(e)}")

# Create FastAPI app
app = FastAPI(
    title="Strategy Builder SaaS",
    description="A powerful trading strategy builder platform",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Add security middleware for trusted hosts
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["localhost", "127.0.0.1", "*.localhost", settings.domain] if hasattr(settings, 'domain') else ["*"]
)

# CORS Middleware - CRITICAL for fixing network errors
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5001",
        "http://127.0.0.1:5001",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        # Add your production domain here
        # "https://yourdomain.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Accept",
        "Accept-Language",
        "Content-Language",
        "Content-Type",
        "Authorization",
        "Cookie",
        "Set-Cookie",
        "X-Requested-With",
        "X-CSRF-Token",
    ],
    expose_headers=["Set-Cookie"],
)

# Mount static files with error handling
static_dir = "app/static"
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    logger.info(f"Static files mounted from {static_dir}")
else:
    logger.warning(f"Static directory {static_dir} not found")

# Setup templates with error handling
templates_dir = "app/templates"
if os.path.exists(templates_dir):
    templates = Jinja2Templates(directory=templates_dir)
    logger.info(f"Templates loaded from {templates_dir}")
else:
    logger.error(f"Templates directory {templates_dir} not found")
    templates = None

# Include routers with error handling
try:
    app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
    app.include_router(auth.router, prefix="/auth", tags=["authentication-legacy"])  # Legacy support
    logger.info("Auth router included")
except Exception as e:
    logger.error(f"Error including auth router: {str(e)}")

try:
    app.include_router(builder.router, prefix="/api/builder", tags=["strategy-builder"])
    logger.info("Builder router included")
except Exception as e:
    logger.error(f"Error including builder router: {str(e)}")

try:
    app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
    logger.info("Dashboard router included")
except Exception as e:
    logger.error(f"Error including dashboard router: {str(e)}")

try:
    app.include_router(debug.router, prefix="/api/debug", tags=["debug"])
    logger.info("Debug router included")
except Exception as e:
    logger.error(f"Error including debug router: {str(e)}")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Application health check"""
    return {
        "status": "healthy",
        "application": "Strategy Builder SaaS",
        "version": "1.0.0",
        "database": "connected"
    }

# API status endpoint
@app.get("/api/status")
async def api_status():
    """API status check for frontend"""
    return JSONResponse(content={
        "status": "online",
        "timestamp": "2025-06-14",
        "version": "1.0.0"
    })

# API Dashboard endpoint
@app.get("/api/dashboard")
async def api_dashboard(current_user = Depends(get_current_user_optional)):
    """Dashboard API endpoint"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    return {
        "user": {
            "username": current_user.username,
            "email": current_user.email,
            "is_active": getattr(current_user, 'is_active', True)  # 🔧 FIX: Use getattr with default
        },
        "dashboard_data": {
            "total_strategies": 0,  # Placeholder
            "active_trades": 0,     # Placeholder
            "portfolio_value": 0    # Placeholder
        },
        "status": "success"
    }

@app.get("/", response_class=HTMLResponse)
async def root(request: Request, current_user = Depends(get_current_user_optional)):
    """Home page"""
    try:
        if not templates:
            return HTMLResponse(content="<h1>Template system not available</h1>", status_code=500)
        
        # If user is logged in, redirect to dashboard
        if current_user:
            return RedirectResponse(url="/dashboard", status_code=302)
        
        return templates.TemplateResponse(
            "home.html", 
            {
                "request": request,
                "user": current_user,
                "app_name": "Strategy Builder SaaS",
                "version": "1.0.0"
            }
        )
    except Exception as e:
        logger.error(f"Error in root endpoint: {str(e)}")
        return HTMLResponse(
            content=f"<h1>Welcome to Strategy Builder SaaS</h1><p>Error: {str(e)}</p>",
            status_code=200
        )

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, current_user = Depends(get_current_user_optional)):
    """Dashboard page"""
    try:
        # Check if user is authenticated
        if not current_user:
            return RedirectResponse(url="/auth/login", status_code=302)
        
        if not templates:
            return HTMLResponse(
                content=f"""
                <h1>Dashboard - Welcome {current_user.username}!</h1>
                <p>Strategy Builder Dashboard</p>
                <a href="/auth/logout">Logout</a>
                """, 
                status_code=200
            )
        
        return templates.TemplateResponse(
            "dashboard.html", 
            {
                "request": request,
                "user": current_user,
                "app_name": "Strategy Builder SaaS",
                "username": current_user.username,
                "email": current_user.email
            }
        )
    except Exception as e:
        logger.error(f"Error in dashboard endpoint: {str(e)}")
        return HTMLResponse(
            content=f"""
            <h1>Dashboard Error</h1>
            <p>Error: {str(e)}</p>
            <a href="/auth/login">Back to Login</a>
            """,
            status_code=500
        )

# Import already added at the top of the file

# Startup event
@app.on_event("startup")
async def startup_event():
    """Application startup tasks"""
    logger.info("Strategy Builder SaaS application starting up...")
    logger.info(f"Running on: http://127.0.0.1:5001")
    logger.info(f"Documentation: http://127.0.0.1:5001/docs")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown tasks"""
    logger.info("Strategy Builder SaaS application shutting down...")

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Global exception: {str(exc)} for URL: {request.url}")
    
    if templates:
        try:
            return templates.TemplateResponse(
                "error.html",
                {"request": request, "error": "Internal server error"},
                status_code=500
            )
        except:
            pass
    
    return JSONResponse(
        content={"detail": "Internal server error"},
        status_code=500
    )

# 404 Handler
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """404 error handler"""
    logger.warning(f"404 error for URL: {request.url}")
    
    if templates:
        try:
            return templates.TemplateResponse(
                "404.html",
                {"request": request},
                status_code=404
            )
        except:
            pass
    
    return JSONResponse(
        content={"detail": "Page not found"},
        status_code=404
    )

# CORS preflight handler
@app.options("/{full_path:path}")
async def options_handler(request: Request):
    """Handle CORS preflight requests"""
    return JSONResponse(
        content={},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )

if __name__ == "__main__":
    import uvicorn
    
    # Development configuration
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=5001,
        reload=True,
        log_level="info",
        access_log=True,
        use_colors=True
    )