"""
Dashboard routes for authenticated users with unified interface
"""
from fastapi import APIRouter, Depends, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime, timedelta
import json

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
        "operator": ">",
        "value": 70.0,
        "stop_loss": 5.0,
        "target": 10.0,
        "capital": 10000.0,
        "created_at": datetime.now() - timedelta(days=2),
        "updated_at": datetime.now() - timedelta(days=1),
        "generated_code": "# RSI Strategy Code\nimport pandas as pd\nimport talib\n\nclass RSIStrategy:\n    def __init__(self):\n        self.rsi_period = 14\n        self.overbought = 70\n        self.oversold = 30\n\n    def calculate_rsi(self, data):\n        return talib.RSI(data['close'], timeperiod=self.rsi_period)\n\n    def check_entry(self, data):\n        rsi = self.calculate_rsi(data)\n        return rsi > self.overbought",
        "user_id": None,
        "is_active": True
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
        "generated_code": "# SMA Strategy Code\nimport pandas as pd\nimport talib\n\nclass SMAStrategy:\n    def __init__(self):\n        self.short_period = 20\n        self.long_period = 50\n\n    def calculate_sma(self, data, period):\n        return talib.SMA(data['close'], timeperiod=period)\n\n    def check_crossover(self, data):\n        short_sma = self.calculate_sma(data, self.short_period)\n        long_sma = self.calculate_sma(data, self.long_period)\n        return short_sma > long_sma",
        "user_id": None,
        "is_active": True
    },
    {
        "id": 3,
        "name": "Bollinger Bands Squeeze",
        "description": "Volatility breakout strategy",
        "indicator": "Bollinger_Bands",
        "operator": ">",
        "value": 2.0,
        "stop_loss": 4.0,
        "target": 12.0,
        "capital": 20000.0,
        "created_at": datetime.now() - timedelta(days=7),
        "updated_at": datetime.now() - timedelta(days=5),
        "generated_code": "# Bollinger Bands Strategy Code\nimport pandas as pd\nimport talib\n\nclass BollingerBandsStrategy:\n    def __init__(self):\n        self.period = 20\n        self.std_dev = 2\n\n    def calculate_bands(self, data):\n        upper, middle, lower = talib.BBANDS(data['close'], timeperiod=self.period, nbdevup=self.std_dev, nbdevdn=self.std_dev)\n        return upper, middle, lower\n\n    def check_breakout(self, data):\n        upper, middle, lower = self.calculate_bands(data)\n        return data['close'] > upper",
        "user_id": None,
        "is_active": True
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
                    "generated_code": s.generated_code,
                    "is_active": s.is_active
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
    total_capital = sum(s.get("capital", 0) for s in strategies if s.get("is_active", True))
    
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
        "active_strategies": sum(1 for s in strategies if s.get("is_active", True))
    }

def generate_python_strategy(data: dict) -> str:
    """Generate Python strategy code based on form data"""
    indicator_code = get_indicator_code(data.get("indicator", "RSI"))
    
    return f'''# Trading Strategy: {data.get("indicator", "Custom")} Strategy
# Generated by Strategy Builder on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

import pandas as pd
import numpy as np
import talib
from datetime import datetime

class TradingStrategy:
    def __init__(self, capital={data.get("capital", 100000)}, stop_loss={data.get("stop_loss", 2.5)}, target={data.get("target", 5.0)}):
        self.capital = capital
        self.stop_loss = stop_loss / 100  # Convert to decimal
        self.target = target / 100  # Convert to decimal
        self.position = 0
        self.entry_price = 0
        self.trades = []
        
    def calculate_{data.get("indicator", "rsi").lower().replace(" ", "_")}(self, data):
        """Calculate {data.get("indicator", "RSI")} indicator"""
        {indicator_code}
        
    def check_entry_condition(self, data):
        """Check if entry condition is met"""
        indicator_value = self.calculate_{data.get("indicator", "rsi").lower().replace(" ", "_")}(data)
        condition = "{data.get("operator", ">")}"
        threshold = {data.get("value", 70)}
        
        if condition == ">":
            return indicator_value > threshold
        elif condition == "<":
            return indicator_value < threshold
        elif condition == ">=":
            return indicator_value >= threshold
        elif condition == "<=":
            return indicator_value <= threshold
        elif condition == "==":
            return abs(indicator_value - threshold) < 0.01
        elif condition == "crosses_above":
            # Simplified crossover logic
            return indicator_value > threshold
        elif condition == "crosses_below":
            # Simplified crossover logic
            return indicator_value < threshold
        else:
            return False
        
    def execute_trade(self, current_price, timestamp=None):
        """Execute trade based on strategy"""
        if timestamp is None:
            timestamp = datetime.now()
            
        if self.position == 0:  # No position
            if self.check_entry_condition(data):  # data should be passed as parameter
                self.position = self.capital / current_price
                self.entry_price = current_price
                trade_info = {{
                    "type": "BUY",
                    "shares": self.position,
                    "price": current_price,
                    "timestamp": timestamp,
                    "capital_used": self.capital
                }}
                self.trades.append(trade_info)
                print(f"BUY: {{self.position:.4f}} shares at ₹{{current_price:.2f}}")
                return trade_info
                
        elif self.position > 0:  # Long position
            # Check stop loss
            if current_price <= self.entry_price * (1 - self.stop_loss):
                profit_loss = (current_price - self.entry_price) * self.position
                trade_info = {{
                    "type": "SELL_STOP_LOSS",
                    "shares": self.position,
                    "price": current_price,
                    "timestamp": timestamp,
                    "pnl": profit_loss
                }}
                self.trades.append(trade_info)
                print(f"STOP LOSS: Sold at ₹{{current_price:.2f}}, P&L: ₹{{profit_loss:.2f}}")
                self.position = 0
                return trade_info
                
            # Check target
            elif current_price >= self.entry_price * (1 + self.target):
                profit_loss = (current_price - self.entry_price) * self.position
                trade_info = {{
                    "type": "SELL_TARGET",
                    "shares": self.position,
                    "price": current_price,
                    "timestamp": timestamp,
                    "pnl": profit_loss
                }}
                self.trades.append(trade_info)
                print(f"TARGET: Sold at ₹{{current_price:.2f}}, P&L: ₹{{profit_loss:.2f}}")
                self.position = 0
                return trade_info
        
        return None
    
    def get_performance_summary(self):
        """Get strategy performance summary"""
        if not self.trades:
            return {{"total_trades": 0, "total_pnl": 0, "win_rate": 0}}
        
        buy_trades = [t for t in self.trades if t["type"] == "BUY"]
        sell_trades = [t for t in self.trades if "SELL" in t["type"]]
        
        total_pnl = sum(t.get("pnl", 0) for t in sell_trades)
        winning_trades = len([t for t in sell_trades if t.get("pnl", 0) > 0])
        
        return {{
            "total_trades": len(sell_trades),
            "total_pnl": total_pnl,
            "win_rate": (winning_trades / len(sell_trades) * 100) if sell_trades else 0,
            "current_position": self.position,
            "entry_price": self.entry_price
        }}

# Usage Example:
# strategy = TradingStrategy(capital={data.get("capital", 100000)}, stop_loss={data.get("stop_loss", 2.5)}, target={data.get("target", 5.0)})
# result = strategy.execute_trade(current_market_price, market_data)
# performance = strategy.get_performance_summary()
'''

def get_indicator_code(indicator: str) -> str:
    """Get the appropriate indicator calculation code"""
    indicators = {
        'RSI': 'return talib.RSI(data["close"], timeperiod=14)',
        'EMA': 'return talib.EMA(data["close"], timeperiod=20)',
        'SMA': 'return talib.SMA(data["close"], timeperiod=20)',
        'MACD': '''macd, signal, hist = talib.MACD(data["close"])
        return macd''',
        'Bollinger_Bands': '''upper, middle, lower = talib.BBANDS(data["close"])
        return middle''',
        'Stochastic': '''slowk, slowd = talib.STOCH(data["high"], data["low"], data["close"])
        return slowk''',
        'Williams_R': 'return talib.WILLR(data["high"], data["low"], data["close"])',
        'CCI': 'return talib.CCI(data["high"], data["low"], data["close"])'
    }
    return indicators.get(indicator, 'return 0  # Indicator not implemented')

# Main Dashboard Route
@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Unified dashboard with sidebar navigation"""
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
            "dashboard/main.html", 
            {
                "request": request,
                "user": current_user,
                "username": current_user.username,
                "email": current_user.email,
                "strategies": strategies,
                "stats": stats,
                "message": message,
                "message_type": message_type,
                "error": error,
                "app_name": "Strategy Builder SaaS"
            }
        )
    except Exception as e:
        logger.error(f"Error in dashboard route: {str(e)}")
        raise HTTPException(status_code=500, detail="Dashboard error")

# Strategy Builder Routes
@router.post("/api/generate-strategy")
async def generate_strategy_api(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    indicator: str = Form(...),
    operator: str = Form(...),
    value: float = Form(...),
    stop_loss: float = Form(...),
    target: float = Form(...),
    capital: float = Form(...)
):
    """API endpoint to generate strategy code"""
    try:
        strategy_data = {
            "indicator": indicator,
            "operator": operator,
            "value": value,
            "stop_loss": stop_loss,
            "target": target,
            "capital": capital
        }
        
        # Generate Python strategy code
        generated_code = generate_python_strategy(strategy_data)
        
        # Optionally save to database (implement this when Strategy model is ready)
        # if Strategy and strategy_crud:
        #     saved_strategy = strategy_crud.create_strategy(db, strategy_data, current_user.id, generated_code)
        
        return JSONResponse(content={
            "success": True,
            "code": generated_code,
            "summary": {
                "indicator": indicator,
                "operator": operator,
                "value": value,
                "stop_loss": stop_loss,
                "target": target,
                "capital": capital
            }
        })
    except Exception as e:
        logger.error(f"Error generating strategy: {str(e)}")
        return JSONResponse(
            content={"success": False, "error": str(e)},
            status_code=400
        )

@router.post("/api/save-strategy")
async def save_strategy_api(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save a generated strategy"""
    try:
        data = await request.json()
        
        # Here you would save to database when Strategy model is ready
        # For now, just return success
        return JSONResponse(content={
            "success": True,
            "message": "Strategy saved successfully",
            "strategy_id": len(SAMPLE_STRATEGIES) + 1  # Mock ID
        })
    except Exception as e:
        logger.error(f"Error saving strategy: {str(e)}")
        return JSONResponse(
            content={"success": False, "error": str(e)},
            status_code=400
        )

# API Routes for Dashboard Data
@router.get("/api/stats", response_class=JSONResponse)
async def dashboard_stats_api(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """API endpoint for dashboard statistics"""
    try:
        strategies = get_user_strategies(current_user.id, db)
        stats = calculate_dashboard_stats(strategies)
        
        return JSONResponse(content={
            "status": "success",
            "data": stats,
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

@router.get("/api/strategies", response_class=JSONResponse)
async def get_strategies_api(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user strategies as JSON"""
    try:
        strategies = get_user_strategies(current_user.id, db)
        return JSONResponse(content={
            "status": "success",
            "data": strategies
        })
    except Exception as e:
        logger.error(f"Error fetching strategies: {str(e)}")
        return JSONResponse(
            content={"status": "error", "message": "Failed to fetch strategies"},
            status_code=500
        )

@router.get("/api/strategy/{strategy_id}")
async def get_strategy_api(
    strategy_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific strategy"""
    try:
        strategies = get_user_strategies(current_user.id, db)
        strategy = next((s for s in strategies if s["id"] == strategy_id), None)
        
        if not strategy:
            return JSONResponse(
                content={"status": "error", "message": "Strategy not found"},
                status_code=404
            )
        
        return JSONResponse(content={
            "status": "success",
            "data": strategy
        })
    except Exception as e:
        logger.error(f"Error fetching strategy {strategy_id}: {str(e)}")
        return JSONResponse(
            content={"status": "error", "message": "Failed to fetch strategy"},
            status_code=500
        )

@router.delete("/api/strategy/{strategy_id}")
async def delete_strategy_api(
    strategy_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a strategy"""
    try:
        # Here you would delete from database when Strategy model is ready
        # For now, just return success
        return JSONResponse(content={
            "status": "success",
            "message": "Strategy deleted successfully"
        })
    except Exception as e:
        logger.error(f"Error deleting strategy {strategy_id}: {str(e)}")
        return JSONResponse(
            content={"status": "error", "message": "Failed to delete strategy"},
            status_code=500
        )

@router.get("/api/recent-activity", response_class=JSONResponse)
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

@router.get("/api/performance", response_class=JSONResponse)
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

@router.post("/api/refresh")
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
@router.get("/api/export/strategies")
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

# Legacy route for backward compatibility
@router.get("/stats", response_class=JSONResponse)
async def dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Legacy API endpoint for dashboard statistics"""
    return await dashboard_stats_api(current_user, db)

@router.get("/recent-activity", response_class=JSONResponse)
async def legacy_recent_activity(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 10
):
    """Legacy recent activity endpoint"""
    return await recent_activity(current_user, db, limit)

@router.get("/performance", response_class=JSONResponse)
async def legacy_performance_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Legacy performance metrics endpoint"""
    return await performance_metrics(current_user, db)

@router.post("/refresh")
async def legacy_refresh_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Legacy refresh dashboard endpoint"""
    return await refresh_dashboard(current_user, db)

@router.get("/export/strategies")
async def legacy_export_strategies(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    format: str = "json"
):
    """Legacy export strategies endpoint"""
    return await export_strategies(current_user, db, format)