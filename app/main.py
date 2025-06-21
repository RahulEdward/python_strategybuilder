"""
FastAPI Strategy Builder SaaS App Entry Point
Enhanced Version with Strategy Builder Integration
"""
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse, Response
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging
import os
from typing import Optional
from datetime import datetime

# Import routers with error handling
try:
    from app.api.routes import auth, builder, dashboard, debug
except ImportError as e:
    logging.warning(f"Could not import some routes: {e}")
    # Create minimal fallback modules
    class FallbackRouter:
        def __init__(self):
            from fastapi import APIRouter
            self.router = APIRouter()
    
    auth = FallbackRouter()
    builder = FallbackRouter()
    dashboard = FallbackRouter()
    debug = FallbackRouter()

try:
    from app.core.config import settings
except ImportError:
    # Fallback settings
    class Settings:
        debug = True
        domain = None
        frontend_url = None
    settings = Settings()

try:
    from app.db.session import engine, get_db
    from app.models import Base
    from app.services.auth_service import get_current_user_optional
except ImportError as e:
    logging.warning(f"Could not import database/auth modules: {e}")
    # Create fallback functions
    engine = None
    def get_db():
        return None
    class Base:
        metadata = None
    async def get_current_user_optional():
        return None

# Import strategy builder components
try:
    from app.parser import StrategyParser
    from app.generator import CodeGenerator
    from app.models.models import StrategyRequest, GeneratedStrategy, StrategyResponse
    strategy_parser = StrategyParser()
    code_generator = CodeGenerator()
    strategy_builder_available = True
    logging.info("Strategy builder components loaded successfully")
except ImportError as e:
    logging.warning(f"Strategy builder components not available: {e}")
    strategy_parser = None
    code_generator = None
    strategy_builder_available = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Create database tables with error handling
def initialize_database():
    """Initialize database tables"""
    try:
        if engine and Base and hasattr(Base, 'metadata'):
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables created successfully")
            
            # Test database connection
            with engine.connect() as connection:
                result = connection.execute(text("SELECT 1"))
                logger.info("Database connection test successful")
        else:
            logger.warning("Database not available - running without database")
            
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        logger.warning("Application will continue without database")

# Initialize database
initialize_database()

# Create FastAPI app
app = FastAPI(
    title="Strategy Builder SaaS",
    description="A powerful trading strategy builder platform with no-code visual interface",
    version="1.0.0",
    docs_url="/docs" if getattr(settings, 'debug', True) else None,
    redoc_url="/redoc" if getattr(settings, 'debug', True) else None,
    openapi_url="/openapi.json" if getattr(settings, 'debug', True) else None,
)

# Security middleware
allowed_hosts = ["localhost", "127.0.0.1", "*.localhost"]
if hasattr(settings, 'domain') and settings.domain:
    allowed_hosts.append(settings.domain)

app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=allowed_hosts
)

# CORS middleware - Configured for Next.js frontend
cors_origins = [
    "http://localhost:3000",  # Next.js default
    "http://127.0.0.1:3000",
    "http://localhost:3001",   # Common Next.js alternative port
    "http://127.0.0.1:3001",
    "http://localhost:5001",   # Keep FastAPI port for reference
    "http://127.0.0.1:5001",
]

# Add frontend URL from settings if available
if hasattr(settings, 'frontend_url') and settings.frontend_url:
    cors_origins.append(settings.frontend_url.rstrip('/'))

# Add CORS middleware with enhanced settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,  # Required for cookies/session
    allow_methods=["*"],     # Allow all methods
    allow_headers=["*"],     # Allow all headers
    expose_headers=[
        "Set-Cookie",
        "Authorization",
        "X-CSRF-Token",
        "Content-Type",
        "Content-Length",
        "X-Requested-With"
    ],
    max_age=86400,  # 24 hours for preflight cache
)

# Setup static files
def setup_static_files():
    """Setup static file serving"""
    static_paths = ["app/static", "static", "app/assets", "assets"]
    
    for static_dir in static_paths:
        if os.path.exists(static_dir):
            try:
                app.mount("/static", StaticFiles(directory=static_dir), name="static")
                logger.info(f"Static files mounted from {static_dir}")
                return True
            except Exception as e:
                logger.warning(f"Failed to mount static files from {static_dir}: {str(e)}")
                continue
    
    logger.warning("No static directory found")
    return False

setup_static_files()

# Include API routers
try:
    # Include authentication routes
    app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
    logger.info("Auth router included at /api/auth")
except Exception as e:
    logger.error(f"Failed to include auth router: {str(e)}")

try:
    # Include builder routes  
    app.include_router(builder.router, prefix="/api/builder", tags=["strategy-builder"])
    logger.info("Builder router included at /api/builder")
except Exception as e:
    logger.error(f"Failed to include builder router: {str(e)}")

try:
    # Include dashboard routes
    app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
    logger.info("Dashboard router included at /api/dashboard")
except Exception as e:
    logger.error(f"Failed to include dashboard router: {str(e)}")

try:
    # Include debug routes
    app.include_router(debug.router, prefix="/api/debug", tags=["debug"])
    logger.info("Debug router included at /api/debug")
except Exception as e:
    logger.error(f"Failed to include debug router: {str(e)}")

# Setup templates
def setup_templates():
    """Setup Jinja2 templates"""
    template_paths = ["app/templates", "templates"]
    
    for templates_dir in template_paths:
        if os.path.exists(templates_dir):
            try:
                templates = Jinja2Templates(directory=templates_dir)
                logger.info(f"Templates loaded from {templates_dir}")
                return templates
            except Exception as e:
                logger.warning(f"Failed to load templates from {templates_dir}: {str(e)}")
                continue
    
    logger.error("No templates directory found")
    return None

templates = setup_templates()

# Favicon handler
@app.get("/favicon.ico")
async def favicon():
    """Serve favicon or return 204 if not found"""
    favicon_paths = [
        "app/static/favicon.ico",
        "static/favicon.ico", 
        "app/assets/favicon.ico",
        "assets/favicon.ico"
    ]
    
    for path in favicon_paths:
        if os.path.exists(path):
            return FileResponse(path)
    
    return Response(status_code=204)

# Enhanced health endpoint with strategy builder status
@app.get("/health")
async def health_check():
    """Application health check with strategy builder status"""
    try:
        if engine:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
                db_status = "connected"
        else:
            db_status = "not_configured"
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        db_status = "disconnected"
    
    # Check strategy builder components
    strategy_builder_status = {
        "available": strategy_builder_available,
        "parser": strategy_parser is not None,
        "generator": code_generator is not None,
        "templates": "unknown"
    }
    
    if code_generator:
        try:
            template_status = code_generator.validate_templates()
            strategy_builder_status["templates"] = "loaded" if any(template_status.values()) else "missing"
            strategy_builder_status["template_details"] = template_status
        except Exception as e:
            strategy_builder_status["templates"] = f"error: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "application": "Strategy Builder SaaS",
        "version": "1.0.0",
        "database": db_status,
        "timestamp": datetime.utcnow().isoformat(),
        "templates": "loaded" if templates else "not_loaded",
        "strategy_builder": strategy_builder_status
    }

# API status endpoint
@app.get("/api/status")
async def api_status():
    """API status check"""
    return JSONResponse(content={
        "status": "online",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "service": "Strategy Builder API",
        "strategy_builder_available": strategy_builder_available
    })

# Strategy Builder API endpoints (integrated into main app)
if strategy_builder_available:
    
    @app.post("/api/strategy/generate")
    async def generate_strategy_direct(
        strategy_request: StrategyRequest,
        current_user = Depends(get_current_user_optional),
        db: Session = Depends(get_db)
    ):
        """Generate strategy code from JSON configuration"""
        try:
            if not current_user:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            # Validate the strategy
            validation_result = strategy_parser.validate_strategy(strategy_request)
            if not validation_result["is_valid"]:
                return StrategyResponse(
                    success=False,
                    message="Strategy validation failed",
                    errors=validation_result["errors"]
                )
            
            # Parse the strategy
            parsed_data = strategy_parser.parse_strategy(strategy_request)
            
            # Generate code
            strategy_code = code_generator.generate_strategy(parsed_data)
            
            # Prepare response
            generated_strategy = GeneratedStrategy(
                strategy_name=parsed_data["strategy_name"],
                code=strategy_code,
                indicators_used=parsed_data["indicators_used"],
                conditions_count={
                    "buy": len(parsed_data["buy_conditions"]),
                    "sell": len(parsed_data["sell_conditions"])
                }
            )
            
            # Save to database if available
            if db:
                try:
                    from models.strategy import Strategy
                    
                    db_strategy = Strategy.create_advanced_strategy(
                        user_id=current_user.id,
                        name=parsed_data["strategy_name"],
                        description=f"Auto-generated strategy with {len(parsed_data['indicators_used'])} indicators",
                        timeframe=str(parsed_data["timeframe"]),
                        buy_conditions=parsed_data["buy_conditions"],
                        sell_conditions=parsed_data["sell_conditions"],
                        money_management=parsed_data["money_management"],
                        indicators_used=parsed_data["indicators_used"],
                        generated_code=strategy_code,
                        capital=parsed_data["money_management"].get("initial_capital", 100000)
                    )
                    
                    db.add(db_strategy)
                    db.commit()
                    db.refresh(db_strategy)
                    
                    logger.info(f"Strategy saved to database with ID: {db_strategy.id}")
                    
                except Exception as db_error:
                    logger.error(f"Failed to save strategy to database: {str(db_error)}")
                    # Continue without database save
            
            return StrategyResponse(
                success=True,
                message="Strategy generated successfully",
                strategy=generated_strategy
            )
            
        except Exception as e:
            logger.error(f"Strategy generation failed: {str(e)}")
            return StrategyResponse(
                success=False,
                message=f"Code generation failed: {str(e)}",
                errors=[str(e)]
            )
    
    @app.get("/api/strategy/indicators")
    async def list_indicators():
        """List available indicators"""
        try:
            indicators = [
                {"name": "RSI", "description": "Relative Strength Index", "parameters": ["period"], "default_values": {"period": 14}},
                {"name": "EMA", "description": "Exponential Moving Average", "parameters": ["period"], "default_values": {"period": 20}},
                {"name": "SMA", "description": "Simple Moving Average", "parameters": ["period"], "default_values": {"period": 50}},
                {"name": "MACD", "description": "Moving Average Convergence Divergence", "parameters": ["fast", "slow", "signal"], "default_values": {"fast": 12, "slow": 26, "signal": 9}},
                {"name": "BB", "description": "Bollinger Bands", "parameters": ["period", "std"], "default_values": {"period": 20, "std": 2}},
                {"name": "STOCH", "description": "Stochastic Oscillator", "parameters": ["k_period", "d_period", "smooth"], "default_values": {"k_period": 14, "d_period": 3, "smooth": 3}},
                {"name": "CCI", "description": "Commodity Channel Index", "parameters": ["period"], "default_values": {"period": 20}},
                {"name": "WILLIAMS", "description": "Williams %R", "parameters": ["period"], "default_values": {"period": 14}}
            ]
            
            operators = [
                {"name": "above", "symbol": ">", "description": "Greater than", "type": "comparison"},
                {"name": "below", "symbol": "<", "description": "Less than", "type": "comparison"},
                {"name": "equal", "symbol": "==", "description": "Equal to", "type": "comparison"},
                {"name": "crosses_above", "symbol": "crossover", "description": "Crosses above", "type": "cross"},
                {"name": "crosses_below", "symbol": "crossunder", "description": "Crosses below", "type": "cross"}
            ]
            
            return {
                "indicators": indicators,
                "operators": operators,
                "timeframes": ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"],
                "available_templates": code_generator.get_available_templates() if code_generator else []
            }
            
        except Exception as e:
            logger.error(f"Failed to list indicators: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to retrieve indicators")
    
    @app.post("/api/strategy/validate")
    async def validate_strategy_endpoint(strategy_request: StrategyRequest):
        """Validate strategy configuration without generating code"""
        try:
            validation_result = strategy_parser.validate_strategy(strategy_request)
            
            # Count unique indicators
            all_indicators = []
            for cond in strategy_request.buy_conditions + strategy_request.sell_conditions:
                all_indicators.extend([cond.left.indicator.value, cond.right.indicator.value])
            
            unique_indicators = len(set([ind for ind in all_indicators if ind != "CUSTOM"]))
            
            return {
                "is_valid": validation_result["is_valid"],
                "errors": validation_result["errors"],
                "warnings": validation_result["warnings"],
                "indicators_count": unique_indicators,
                "conditions_count": {
                    "buy": len(strategy_request.buy_conditions),
                    "sell": len(strategy_request.sell_conditions)
                }
            }
        except Exception as e:
            logger.error(f"Strategy validation failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")

# Main routes
@app.get("/", response_class=HTMLResponse)
async def root(request: Request, current_user = Depends(get_current_user_optional)):
    """Home page with strategy builder highlights"""
    try:
        if current_user:
            username = getattr(current_user, 'username', 'Unknown')
            logger.info(f"Authenticated user {username} accessing root, redirecting to dashboard")
            return RedirectResponse(url="/dashboard", status_code=302)
        
        if not templates:
            strategy_builder_section = ""
            if strategy_builder_available:
                strategy_builder_section = """
                    <div style="background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); border-radius: 15px; padding: 30px; margin: 20px 0;">
                        <h2 style="color: white; margin-bottom: 15px; font-size: 1.8em;">🚀 No-Code Strategy Builder</h2>
                        <p style="color: rgba(255, 255, 255, 0.9); font-size: 1.1em; line-height: 1.6;">
                            Build sophisticated trading strategies with our visual 5-column condition builder. 
                            No coding required - just drag, drop, and configure your indicators!
                        </p>
                        <div style="margin-top: 20px;">
                            <a href="/login" style="
                                background: rgba(255, 255, 255, 0.2); color: white; padding: 15px 30px;
                                text-decoration: none; border-radius: 25px; margin-right: 15px;
                                border: 2px solid rgba(255, 255, 255, 0.3); display: inline-block;
                                transition: all 0.3s ease; font-weight: 600;
                            ">Get Started →</a>
                        </div>
                    </div>
                """
            
            return HTMLResponse(
                content=f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Strategy Builder SaaS</title>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <style>
                        body {{ 
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                            margin: 0; padding: 20px; line-height: 1.6;
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            color: white; min-height: 100vh;
                        }}
                        .container {{
                            max-width: 1000px; margin: 50px auto; text-align: center;
                            background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px);
                            border-radius: 15px; padding: 40px;
                        }}
                        .header h1 {{ font-size: 3em; margin-bottom: 10px; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }}
                        .header p {{ font-size: 1.2em; opacity: 0.9; }}
                        .nav {{ margin: 30px 0; }}
                        .nav a {{ 
                            margin: 0 10px; padding: 12px 24px; 
                            background: rgba(255, 255, 255, 0.2); color: white; 
                            text-decoration: none; border-radius: 25px; 
                            border: 2px solid rgba(255, 255, 255, 0.3);
                            transition: all 0.3s ease; display: inline-block;
                        }}
                        .nav a:hover {{ 
                            background: rgba(255, 255, 255, 0.3); 
                            transform: translateY(-2px);
                            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
                        }}
                        .features {{
                            display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                            gap: 20px; margin: 30px 0; text-align: left;
                        }}
                        .feature {{
                            background: rgba(255, 255, 255, 0.1); border-radius: 10px;
                            padding: 20px; backdrop-filter: blur(5px);
                        }}
                        .feature h3 {{ margin-top: 0; color: #ffffff; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>Strategy Builder SaaS</h1>
                            <p>Build powerful algorithmic trading strategies with ease</p>
                        </div>
                        
                        {strategy_builder_section}
                        
                        <div class="features">
                            <div class="feature">
                                <h3>📊 Visual Builder</h3>
                                <p>Drag-and-drop interface for creating complex trading strategies without coding</p>
                            </div>
                            <div class="feature">
                                <h3>📈 Multiple Indicators</h3>
                                <p>Support for RSI, EMA, SMA, MACD, Bollinger Bands, and more technical indicators</p>
                            </div>
                            <div class="feature">
                                <h3>⚡ Real-time Testing</h3>
                                <p>Backtest your strategies with historical data and performance metrics</p>
                            </div>
                            <div class="feature">
                                <h3>🔧 Code Generation</h3>
                                <p>Automatically generate Python code for your strategies</p>
                            </div>
                        </div>
                        
                        <div class="nav">
                            <a href="/login">Login</a>
                            <a href="/register">Register</a>
                            <a href="/docs">API Documentation</a>
                            <a href="/health">System Health</a>
                        </div>
                    </div>
                </body>
                </html>
                """,
                status_code=200
            )
        
        return templates.TemplateResponse("home.html", {
            "request": request,
            "user": current_user,
            "app_name": "Strategy Builder SaaS",
            "version": "1.0.0",
            "year": datetime.now().year,
            "strategy_builder_available": strategy_builder_available
        })
        
    except Exception as e:
        logger.error(f"Error in root endpoint: {str(e)}")
        return HTMLResponse(
            content="""
            <!DOCTYPE html>
            <html>
            <head><title>Strategy Builder SaaS</title></head>
            <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px;">
                <h1>Welcome to Strategy Builder SaaS</h1>
                <p>A powerful platform for building trading strategies</p>
                <p><a href="/login">Login</a> | <a href="/docs">API Documentation</a></p>
            </body>
            </html>
            """,
            status_code=200
        )

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, current_user = Depends(get_current_user_optional)):
    """Enhanced dashboard page with strategy builder features"""
    try:
        if not current_user:
            logger.info("Unauthenticated user trying to access dashboard, redirecting to login")
            return RedirectResponse(url="/login?message=Please log in to access the dashboard", status_code=302)
        
        username = getattr(current_user, 'username', 'User')
        email = getattr(current_user, 'email', 'Unknown')
        
        if not templates:
            strategy_builder_nav = ""
            if strategy_builder_available:
                strategy_builder_nav = """
                    <a href="/builder" class="primary">🚀 Strategy Builder</a>
                    <a href="/api/strategy/indicators">📊 View Indicators</a>
                """
            
            return HTMLResponse(
                content=f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Dashboard - Strategy Builder SaaS</title>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <style>
                        body {{ 
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                            max-width: 1200px; margin: 0 auto; padding: 20px; 
                            background: #f5f5f5; line-height: 1.6;
                        }}
                        .header {{ 
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                            color: white; padding: 30px; border-radius: 15px; 
                            margin-bottom: 30px; text-align: center;
                        }}
                        .header h1 {{ margin-bottom: 10px; font-size: 2.5em; }}
                        .nav {{ 
                            background: white; padding: 20px; border-radius: 10px;
                            margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                        }}
                        .nav a {{ 
                            margin-right: 15px; padding: 10px 20px; 
                            background: #007bff; color: white; text-decoration: none; 
                            border-radius: 5px; transition: background 0.3s ease;
                        }}
                        .nav a:hover {{ background: #0056b3; }}
                        .nav a.primary {{ background: #28a745; }}
                        .nav a.primary:hover {{ background: #1e7e34; }}
                        .stats {{
                            display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                            gap: 20px; margin: 20px 0;
                        }}
                        .stat-card {{
                            background: white; padding: 20px; border-radius: 10px;
                            box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center;
                        }}
                        .stat-card h3 {{ margin-top: 0; color: #333; }}
                        .stat-value {{ font-size: 2em; font-weight: bold; color: #007bff; }}
                    </style>
                </head>
                <body>
                    <div class="header">
                        <h1>Welcome back, {username}!</h1>
                        <p>Email: {email}</p>
                    </div>
                    
                    <div class="stats">
                        <div class="stat-card">
                            <h3>🔧 Strategy Builder</h3>
                            <div class="stat-value">{"✅" if strategy_builder_available else "❌"}</div>
                            <p>{"Available" if strategy_builder_available else "Not Available"}</p>
                        </div>
                        <div class="stat-card">
                            <h3>📊 My Strategies</h3>
                            <div class="stat-value">0</div>
                            <p>Total Created</p>
                        </div>
                        <div class="stat-card">
                            <h3>📈 Backtests</h3>
                            <div class="stat-value">0</div>
                            <p>Completed</p>
                        </div>
                    </div>
                    
                    <div class="nav">
                        {strategy_builder_nav}
                        <a href="/health">System Health</a>
                        <a href="/docs">API Docs</a>
                        <a href="/logout">Logout</a>
                    </div>
                </body>
                </html>
                """,
                status_code=200
            )
        
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "user": current_user,
            "app_name": "Strategy Builder SaaS",
            "username": username,
            "email": email,
            "user_id": getattr(current_user, 'id', None),
            "is_active": getattr(current_user, 'is_active', True),
            "strategy_builder_available": strategy_builder_available
        })
        
    except Exception as e:
        logger.error(f"Error in dashboard endpoint: {str(e)}")
        return HTMLResponse(
            content="""
            <!DOCTYPE html>
            <html>
            <head><title>Dashboard Error</title></head>
            <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px;">
                <h1>Dashboard Error</h1>
                <p>Sorry, there was an error loading your dashboard.</p>
                <p><a href="/login">Back to Login</a></p>
            </body>
            </html>
            """,
            status_code=500
        )

@app.get("/login", response_class=HTMLResponse)
async def root_login(request: Request, current_user = Depends(get_current_user_optional)):
    """Login page"""
    try:
        if current_user:
            username = getattr(current_user, 'username', 'User')
            logger.info(f"User {username} already logged in, redirecting to dashboard")
            return RedirectResponse(url="/dashboard", status_code=302)
        
        message = request.query_params.get("message")
        error = request.query_params.get("error")
        
        if not templates:
            message_html = f"<div style='background: #d4edda; color: #155724; padding: 12px; margin: 15px 0; border-radius: 8px;'>{message}</div>" if message else ""
            error_html = f"<div style='background: #f8d7da; color: #721c24; padding: 12px; margin: 15px 0; border-radius: 8px;'>{error}</div>" if error else ""
            
            return HTMLResponse(
                content=f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Login - Strategy Builder SaaS</title>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <style>
                        body {{ 
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                            max-width: 400px; margin: 100px auto; padding: 20px; 
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            min-height: 100vh;
                        }}
                        .container {{
                            background: rgba(255, 255, 255, 0.95);
                            border-radius: 15px; padding: 40px;
                            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                        }}
                        .form-group {{ margin: 20px 0; }}
                        .form-group label {{ 
                            display: block; margin-bottom: 8px; 
                            font-weight: 600; color: #333;
                        }}
                        .form-group input {{ 
                            width: 100%; padding: 12px; border: 2px solid #e1e1e1; 
                            border-radius: 8px; box-sizing: border-box; 
                            font-size: 16px; transition: border-color 0.3s ease;
                        }}
                        .form-group input:focus {{
                            outline: none; border-color: #667eea;
                            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
                        }}
                        .btn {{ 
                            width: 100%; padding: 14px; 
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                            color: white; border: none; border-radius: 8px; 
                            cursor: pointer; font-size: 16px; font-weight: 600;
                            transition: transform 0.2s ease;
                        }}
                        .btn:hover {{ 
                            transform: translateY(-2px);
                            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
                        }}
                        .header {{ text-align: center; margin-bottom: 30px; }}
                        .header h1 {{ color: #333; margin-bottom: 10px; font-size: 2.2em; }}
                        .links {{ text-align: center; margin-top: 20px; }}
                        .links a {{ color: #667eea; text-decoration: none; margin: 0 10px; }}
                        .links a:hover {{ text-decoration: underline; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>Strategy Builder</h1>
                            <p style="color: #666;">Please log in to continue</p>
                        </div>
                        {message_html}
                        {error_html}
                        <form action="/api/auth/login" method="post">
                            <div class="form-group">
                                <label for="username">Username:</label>
                                <input type="text" id="username" name="username" required>
                            </div>
                            <div class="form-group">
                                <label for="password">Password:</label>
                                <input type="password" id="password" name="password" required>
                            </div>
                            <button type="submit" class="btn">Login</button>
                        </form>
                        <div class="links">
                            <a href="/register">Create Account</a> |
                            <a href="/">Back to Home</a> | 
                            <a href="/docs">API Docs</a>
                        </div>
                    </div>
                </body>
                </html>
                """,
                status_code=200
            )
            
        return templates.TemplateResponse("login.html", {
            "request": request,
            "message": message,
            "error": error,
            "app_name": "Strategy Builder SaaS"
        })
        
    except Exception as e:
        logger.error(f"Error in login page: {str(e)}")
        return HTMLResponse(
            content="<h1>Login Error</h1><p>Please try again later.</p>",
            status_code=500
        )

@app.get("/register", response_class=HTMLResponse)
async def root_register(request: Request, current_user = Depends(get_current_user_optional)):
    """Register page"""
    try:
        if current_user:
            username = getattr(current_user, 'username', 'User')
            logger.info(f"User {username} already logged in, redirecting to dashboard")
            return RedirectResponse(url="/dashboard", status_code=302)
        
        message = request.query_params.get("message")
        error = request.query_params.get("error")
        
        if not templates:
            message_html = f"<div style='background: #d4edda; color: #155724; padding: 12px; margin: 15px 0; border-radius: 8px;'>{message}</div>" if message else ""
            error_html = f"<div style='background: #f8d7da; color: #721c24; padding: 12px; margin: 15px 0; border-radius: 8px;'>{error}</div>" if error else ""
            
            return HTMLResponse(
                content=f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Register - Strategy Builder SaaS</title>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <style>
                        body {{ 
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                            max-width: 400px; margin: 100px auto; padding: 20px; 
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            min-height: 100vh;
                        }}
                        .container {{
                            background: rgba(255, 255, 255, 0.95);
                            border-radius: 15px; padding: 40px;
                            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                        }}
                        .form-group {{ margin: 20px 0; }}
                        .form-group label {{ 
                            display: block; margin-bottom: 8px; 
                            font-weight: 600; color: #333;
                        }}
                        .form-group input {{ 
                            width: 100%; padding: 12px; border: 2px solid #e1e1e1; 
                            border-radius: 8px; box-sizing: border-box; 
                            font-size: 16px; transition: border-color 0.3s ease;
                        }}
                        .form-group input:focus {{
                            outline: none; border-color: #667eea;
                            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
                        }}
                        .btn {{ 
                            width: 100%; padding: 14px; 
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                            color: white; border: none; border-radius: 8px; 
                            cursor: pointer; font-size: 16px; font-weight: 600;
                            transition: transform 0.2s ease;
                        }}
                        .btn:hover {{ 
                            transform: translateY(-2px);
                            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
                        }}
                        .header {{ text-align: center; margin-bottom: 30px; }}
                        .header h1 {{ color: #333; margin-bottom: 10px; font-size: 2.2em; }}
                        .links {{ text-align: center; margin-top: 20px; }}
                        .links a {{ color: #667eea; text-decoration: none; margin: 0 10px; }}
                        .links a:hover {{ text-decoration: underline; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>Strategy Builder</h1>
                            <p style="color: #666;">Create your account</p>
                        </div>
                        {message_html}
                        {error_html}
                        <form action="/api/auth/register" method="post">
                            <div class="form-group">
                                <label for="username">Username:</label>
                                <input type="text" id="username" name="username" required>
                            </div>
                            <div class="form-group">
                                <label for="email">Email:</label>
                                <input type="email" id="email" name="email" required>
                            </div>
                            <div class="form-group">
                                <label for="password">Password:</label>
                                <input type="password" id="password" name="password" required>
                            </div>
                            <div class="form-group">
                                <label for="confirm_password">Confirm Password:</label>
                                <input type="password" id="confirm_password" name="confirm_password" required>
                            </div>
                            <button type="submit" class="btn">Create Account</button>
                        </form>
                        <div class="links">
                            <a href="/login">Already have an account? Login</a> | 
                            <a href="/">Back to Home</a>
                        </div>
                    </div>
                </body>
                </html>
                """,
                status_code=200
            )
            
        return templates.TemplateResponse("register.html", {
            "request": request,
            "message": message,
            "error": error,
            "app_name": "Strategy Builder SaaS"
        })
        
    except Exception as e:
        logger.error(f"Error in register page: {str(e)}")
        return HTMLResponse(
            content="<h1>Register Error</h1><p>Please try again later.</p>",
            status_code=500
        )

@app.get("/logout")
async def root_logout(request: Request):
    """Logout endpoint"""
    try:
        response = RedirectResponse(url="/login?message=You have been logged out successfully", status_code=303)
        
        # Clear authentication cookies
        response.delete_cookie(key="access_token", path="/")
        response.delete_cookie(key="refresh_token", path="/")
        response.delete_cookie(key="session_id", path="/")
        
        # Security headers
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache" 
        response.headers["Expires"] = "0"
        response.headers["Clear-Site-Data"] = '"cookies", "storage"'
        
        logger.info("User logout successful")
        return response
        
    except Exception as e:
        logger.error(f"Error in logout: {str(e)}")
        raise HTTPException(status_code=500, detail="Logout failed")

# Enhanced builder route with fallback
@app.get("/builder", response_class=HTMLResponse)
async def builder_page(request: Request, current_user = Depends(get_current_user_optional)):
    """Strategy builder page with enhanced UI"""
    try:
        if not current_user:
            return RedirectResponse(url="/login?message=Please log in to access the strategy builder", status_code=302)
        
        if not strategy_builder_available:
            return HTMLResponse(
                content="""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Strategy Builder - Not Available</title>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <style>
                        body {
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                            max-width: 800px; margin: 100px auto; padding: 20px;
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            color: white; text-align: center; min-height: 100vh;
                        }
                        .container {
                            background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px);
                            border-radius: 15px; padding: 40px;
                        }
                        .btn {
                            background: rgba(255, 255, 255, 0.2); color: white;
                            padding: 12px 24px; text-decoration: none; border-radius: 25px;
                            border: 2px solid rgba(255, 255, 255, 0.3); display: inline-block;
                            margin: 10px; transition: all 0.3s ease;
                        }
                        .btn:hover {
                            background: rgba(255, 255, 255, 0.3);
                            transform: translateY(-2px);
                        }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>🚧 Strategy Builder Not Available</h1>
                        <p>The strategy builder components are not currently loaded.</p>
                        <p>Please check the system configuration and try again.</p>
                        <a href="/health" class="btn">Check System Health</a>
                        <a href="/dashboard" class="btn">Back to Dashboard</a>
                    </div>
                </body>
                </html>
                """,
                status_code=503
            )
        
        # If templates available, use template, otherwise redirect to API
        if templates and os.path.exists("templates/builder"):
            return templates.TemplateResponse("builder/builder.html", {
                "request": request,
                "user": current_user,
                "strategy_builder_available": strategy_builder_available
            })
        else:
            return RedirectResponse(url="/api/builder", status_code=302)
            
    except Exception as e:
        logger.error(f"Error in builder page: {str(e)}")
        return HTMLResponse(
            content="""
            <!DOCTYPE html>
            <html>
            <head><title>Builder Error</title></head>
            <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px;">
                <h1>Builder Error</h1>
                <p>Sorry, there was an error loading the strategy builder.</p>
                <p><a href="/dashboard">Back to Dashboard</a></p>
            </body>
            </html>
            """,
            status_code=500
        )

# Strategy management endpoints
@app.get("/strategies", response_class=HTMLResponse)
async def strategies_page(request: Request, current_user = Depends(get_current_user_optional)):
    """Strategies management page"""
    try:
        if not current_user:
            return RedirectResponse(url="/login?message=Please log in to view your strategies", status_code=302)
        
        if templates:
            return templates.TemplateResponse("strategy_view.html", {
                "request": request,
                "user": current_user,
                "strategy_builder_available": strategy_builder_available
            })
        else:
            return HTMLResponse(
                content="""
                <!DOCTYPE html>
                <html>
                <head><title>My Strategies</title></head>
                <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px;">
                    <h1>My Strategies</h1>
                    <p>Strategy management interface coming soon...</p>
                    <p><a href="/dashboard">Back to Dashboard</a> | <a href="/builder">Create New Strategy</a></p>
                </body>
                </html>
                """,
                status_code=200
            )
            
    except Exception as e:
        logger.error(f"Error in strategies page: {str(e)}")
        return HTMLResponse(
            content="<h1>Strategies Error</h1><p>Please try again later.</p>",
            status_code=500
        )

# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with enhanced logging"""
    logger.error(f"Global exception: {str(exc)} for URL: {request.url}")
    
    if templates:
        try:
            return templates.TemplateResponse(
                "error.html",
                {"request": request, "error": "Internal server error", "error_code": 500},
                status_code=500
            )
        except Exception as template_error:
            logger.error(f"Error template rendering failed: {str(template_error)}")
    
    return JSONResponse(
        content={
            "error": "Internal server error",
            "detail": str(exc) if getattr(settings, 'debug', False) else "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat(),
            "strategy_builder_available": strategy_builder_available
        },
        status_code=500
    )

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """404 error handler"""
    logger.warning(f"404 error for URL: {request.url}")
    
    return JSONResponse(
        content={
            "error": "Page not found",
            "detail": f"The requested URL {request.url} was not found",
            "timestamp": datetime.utcnow().isoformat(),
            "suggestion": "Try /dashboard, /builder, or /docs"
        },
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

# Application lifecycle events
@app.on_event("startup")
async def startup_event():
    """Enhanced startup tasks"""
    try:
        logger.info("Strategy Builder SaaS application starting up...")
        logger.info("Running on: http://127.0.0.1:5001")
        logger.info("Documentation: http://127.0.0.1:5001/docs")
        logger.info("Dashboard: http://127.0.0.1:5001/dashboard")
        logger.info("Builder: http://127.0.0.1:5001/builder")
        logger.info("Health: http://127.0.0.1:5001/health")
        
        if strategy_builder_available:
            logger.info("✅ Strategy Builder: Available")
            logger.info("   - Visual condition builder: Ready")
            logger.info("   - Code generation: Ready")
            logger.info("   - Template system: Ready")
        else:
            logger.warning("❌ Strategy Builder: Not Available")
            logger.warning("   - Check parser.py and generator.py imports")
            logger.warning("   - Verify templates directory exists")
            
    except Exception as e:
        logger.error(f"Error in startup event: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown tasks"""
    try:
        logger.info("Strategy Builder SaaS application shutting down...")
        logger.info("Cleaning up resources...")
    except Exception as e:
        logger.error(f"Error in shutdown event: {str(e)}")

# Development server
if __name__ == "__main__":
    import uvicorn
    
    try:
        logger.info("Starting Strategy Builder SaaS development server...")
        logger.info(f"Strategy Builder Available: {strategy_builder_available}")
        
        uvicorn.run(
            "app.main:app",
            host="127.0.0.1",
            port=5001,
            reload=True,
            log_level="info",
            access_log=True,
            use_colors=True,
            reload_dirs=["app"]
        )
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        print(f"Server startup failed: {str(e)}")
        print("Please check your configuration and try again.")