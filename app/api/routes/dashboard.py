"""
Dashboard routes for authenticated users
"""
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
from datetime import datetime, timedelta

from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import get_current_user

# Try to import strategy-related modules
try:
    from app.models.strategy import Strategy
    from app.crud.strategy import strategy_crud
except ImportError:
    Strategy = None
    strategy_crud = None

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger(__name__)

# Sample strategies data for demo (remove when database is ready)
SAMPLE_STRATEGIES = [
    {
        "id": 1,
        "name": "RSI Momentum Strategy",
        "description": "Buy/Sell based on RSI levels",
        "indicator": "RSI",
        "operator": "greater_than",
        "value": 70.0,
        "stop_loss": 5.0,
        "target": 10.0,
        "capital": 10000.0,
        "created_at": datetime.now() - timedelta(days=2),
        "updated_at": datetime.now() - timedelta(days=1),
        "generated_code": "# RSI Strategy Code\nimport pandas as pd\n\ndef rsi_strategy():\n    print('RSI Strategy Implementation')\n    return 'Strategy executed'",
        "user_id": None  # Will be set to current user
    },
    {
        "id": 2,
        "name": "Moving Average Crossover",
        "description": "SMA 20/50 crossover signals",
        "indicator": "SMA",
        "operator": "crosses_above",
        "value": 50.0,
        "stop_loss": 3.0,
        "target": 8.0,
        "capital": 15000.0,
        "created_at": datetime.now() - timedelta(days=5),
        "updated_at": datetime.now() - timedelta(days=3),
        "generated_code": "# SMA Strategy Code\nimport pandas as pd\n\ndef sma_strategy():\n    print('SMA Strategy Implementation')\n    return 'Strategy executed'",
        "user_id": None  # Will be set to current user
    },
    {
        "id": 3,
        "name": "Bollinger Bands Squeeze",
        "description": "Volatility breakout strategy",
        "indicator": "Bollinger Bands",
        "operator": "greater_than",
        "value": 2.0,
        "stop_loss": 4.0,
        "target": 12.0,
        "capital": 20000.0,
        "created_at": datetime.now() - timedelta(days=7),
        "updated_at": datetime.now() - timedelta(days=5),
        "generated_code": "# Bollinger Bands Strategy Code\nimport pandas as pd\n\ndef bb_strategy():\n    print('Bollinger Bands Strategy Implementation')\n    return 'Strategy executed'",
        "user_id": None  # Will be set to current user
    }
]

def get_user_strategies(user_id: int, db: Session) -> List[dict]:
    """Get strategies for a user (database or sample data)"""
    try:
        if Strategy and strategy_crud:
            # Use database
            strategies = strategy_crud.get_user_strategies(db, user_id)
            return [
                {
                    "id": s.id,
                    "name": s.name,
                    "description": s.description,
                    "indicator": s.indicator,
                    "operator": s.operator,
                    "value": s.value,
                    "stop_loss": s.stop_loss,
                    "target": s.target,
                    "capital": s.capital,
                    "created_at": s.created_at,
                    "updated_at": s.updated_at,
                    "generated_code": s.generated_code
                }
                for s in strategies
            ]
        else:
            # Use sample data
            user_strategies = []
            for strategy in SAMPLE_STRATEGIES:
                strategy_copy = strategy.copy()
                strategy_copy["user_id"] = user_id
                user_strategies.append(strategy_copy)
            return user_strategies
    except Exception as e:
        logger.error(f"Error getting user strategies: {str(e)}")
        return []

def calculate_dashboard_stats(strategies: List[dict]) -> dict:
    """Calculate dashboard statistics"""
    total_strategies = len(strategies)
    total_capital = sum(s.get("capital", 0) for s in strategies)
    
    # Get latest strategy
    latest_strategy = None
    if strategies:
        latest_strategy = max(strategies, key=lambda s: s.get("created_at", datetime.min))
    
    # Calculate win rate (mock data for now)
    win_rate = 65.5 if total_strategies > 0 else 0
    
    # Calculate total profit (mock data for now)
    total_profit = total_capital * 0.15 if total_capital > 0 else 0
    
    return {
        "total_strategies": total_strategies,
        "total_capital": total_capital,
        "total_profit": total_profit,
        "win_rate": win_rate,
        "latest_strategy": latest_strategy,
        "last_created": latest_strategy.get("created_at").strftime("%B %d, %Y") if latest_strategy else "Never",
        "active_strategies": total_strategies  # All are considered active for now
    }

@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """User dashboard page - requires authentication"""
    try:
        # Get user's strategies
        strategies = get_user_strategies(current_user.id, db)
        
        # Calculate dashboard statistics
        stats = calculate_dashboard_stats(strategies)
        
        # Check for messages in query parameters
        message = request.query_params.get("message")
        message_type = request.query_params.get("type", "info")
        error = request.query_params.get("error")
        
        logger.info(f"Dashboard accessed by user {current_user.id} ({current_user.username})")
        
        return templates.TemplateResponse(
            "dashboard.html", 
            {
                "request": request,
                "user": current_user,
                "username": current_user.username,
                "email": current_user.email,
                "strategies": strategies,
                "total_strategies": stats["total_strategies"],
                "total_capital": stats["total_capital"],
                "total_profit": stats["total_profit"],
                "win_rate": stats["win_rate"],
                "last_created": stats["last_created"],
                "active_strategies": stats["active_strategies"],
                "message": message,
                "message_type": message_type,
                "error": error,
                "app_name": "Strategy Builder SaaS"
            }
        )
    except Exception as e:
        logger.error(f"Error in dashboard route: {str(e)}")
        raise HTTPException(status_code=500, detail="Dashboard error")

@router.get("/stats", response_class=JSONResponse)
async def dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """API endpoint for dashboard statistics"""
    try:
        strategies = get_user_strategies(current_user.id, db)
        stats = calculate_dashboard_stats(strategies)
        
        return JSONResponse(content={
            "status": "success",
            "data": {
                "total_strategies": stats["total_strategies"],
                "total_capital": stats["total_capital"],
                "total_profit": stats["total_profit"],
                "win_rate": stats["win_rate"],
                "active_strategies": stats["active_strategies"],
                "last_created": stats["last_created"]
            },
            "user": {
                "id": current_user.id,
                "username": current_user.username,
                "email": current_user.email
            }
        })
    except Exception as e:
        logger.error(f"Error in dashboard stats API: {str(e)}")
        return JSONResponse(
            content={"status": "error", "message": "Failed to fetch dashboard stats"},
            status_code=500
        )

@router.get("/recent-activity", response_class=JSONResponse)
async def recent_activity(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 10
):
    """Get recent activity for the dashboard"""
    try:
        strategies = get_user_strategies(current_user.id, db)
        
        # Sort by updated_at or created_at
        recent_strategies = sorted(
            strategies,
            key=lambda s: s.get("updated_at") or s.get("created_at", datetime.min),
            reverse=True
        )[:limit]
        
        activity = []
        for strategy in recent_strategies:
            activity.append({
                "type": "strategy_update" if strategy.get("updated_at") != strategy.get("created_at") else "strategy_created",
                "strategy_id": strategy["id"],
                "strategy_name": strategy["name"],
                "timestamp": strategy.get("updated_at") or strategy.get("created_at"),
                "description": f"Updated strategy '{strategy['name']}'" if strategy.get("updated_at") != strategy.get("created_at") else f"Created strategy '{strategy['name']}'"
            })
        
        return JSONResponse(content={
            "status": "success",
            "data": activity
        })
    except Exception as e:
        logger.error(f"Error in recent activity API: {str(e)}")
        return JSONResponse(
            content={"status": "error", "message": "Failed to fetch recent activity"},
            status_code=500
        )

@router.get("/performance", response_class=JSONResponse)
async def performance_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get performance metrics for charts"""
    try:
        strategies = get_user_strategies(current_user.id, db)
        
        # Mock performance data (replace with actual calculations)
        performance_data = {
            "monthly_returns": [
                {"month": "Jan", "return": 5.2},
                {"month": "Feb", "return": -2.1},
                {"month": "Mar", "return": 8.7},
                {"month": "Apr", "return": 3.4},
                {"month": "May", "return": 12.1},
                {"month": "Jun", "return": 7.8}
            ],
            "strategy_performance": [
                {
                    "strategy_name": strategy["name"],
                    "total_return": strategy.get("capital", 0) * 0.15,  # Mock 15% return
                    "win_rate": 65 + (strategy["id"] * 5),  # Mock win rate
                    "sharpe_ratio": 1.2 + (strategy["id"] * 0.1)  # Mock Sharpe ratio
                }
                for strategy in strategies[:5]  # Top 5 strategies
            ],
            "portfolio_allocation": [
                {
                    "strategy": strategy["name"],
                    "allocation": strategy.get("capital", 0)
                }
                for strategy in strategies
            ]
        }
        
        return JSONResponse(content={
            "status": "success",
            "data": performance_data
        })
    except Exception as e:
        logger.error(f"Error in performance metrics API: {str(e)}")
        return JSONResponse(
            content={"status": "error", "message": "Failed to fetch performance metrics"},
            status_code=500
        )

@router.post("/refresh")
async def refresh_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Refresh dashboard data"""
    try:
        # Force refresh of user data (useful for real-time updates)
        strategies = get_user_strategies(current_user.id, db)
        stats = calculate_dashboard_stats(strategies)
        
        return JSONResponse(content={
            "status": "success",
            "message": "Dashboard refreshed successfully",
            "data": {
                "total_strategies": stats["total_strategies"],
                "last_updated": datetime.now().isoformat()
            }
        })
    except Exception as e:
        logger.error(f"Error refreshing dashboard: {str(e)}")
        return JSONResponse(
            content={"status": "error", "message": "Failed to refresh dashboard"},
            status_code=500
        )

# Export endpoints for dashboard data
@router.get("/export/strategies")
async def export_strategies(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    format: str = "json"
):
    """Export user strategies"""
    try:
        strategies = get_user_strategies(current_user.id, db)
        
        if format.lower() == "json":
            return JSONResponse(content={
                "status": "success",
                "data": {
                    "user": current_user.username,
                    "export_date": datetime.now().isoformat(),
                    "strategies": strategies
                }
            })
        else:
            return JSONResponse(
                content={"status": "error", "message": "Unsupported export format"},
                status_code=400
            )
    except Exception as e:
        logger.error(f"Error exporting strategies: {str(e)}")
        return JSONResponse(
            content={"status": "error", "message": "Failed to export strategies"},
            status_code=500
        )