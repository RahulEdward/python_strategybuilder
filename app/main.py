"""
FastAPI Strategy Builder SaaS App Entry Point
"""
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from app.api.routes import auth, builder, dashboard
from app.core.config import settings
from app.db.session import engine
from app.models import Base
from app.services.auth_service import get_current_user_optional

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Strategy Builder SaaS",
    description="A powerful trading strategy builder platform",
    version="1.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="app/templates")

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(builder.router, prefix="/builder", tags=["strategy-builder"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])

@app.get("/", response_class=HTMLResponse)
async def root(request: Request, current_user = Depends(get_current_user_optional)):
    """Home page"""
    return templates.TemplateResponse(
        "home.html", 
        {
            "request": request,
            "user": current_user
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001, reload=True)
