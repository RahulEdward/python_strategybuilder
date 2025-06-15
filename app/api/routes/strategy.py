"""
Strategy management routes for CRUD operations
Enhanced with comprehensive error handling, logging, and API support
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Form, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional, List, Dict, Any
import logging
import json
from datetime import datetime

# Update imports to match your app structure
try:
    from app.db.session import get_db
    from app.models.user import User
    from app.crud.strategy import strategy_crud
    from app.services.auth_service import get_current_user, get_current_user_optional
    from app.services.code_generator import generate_strategy_code
    from app.schemas.strategy import StrategyUpdate, StrategyCreate, StrategyResponse
except ImportError:
    # Fallback imports for different project structures
    from models.database import get_db
    from models.user import User
    from crud.strategy import strategy_crud
    from services.auth import get_current_user, get_current_user_optional
    from services.code_generator import generate_strategy_code
    from schemas.strategy import StrategyUpdate, StrategyCreate, StrategyResponse

# Setup logging
logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Sample data for fallback when database is not ready
SAMPLE_STRATEGIES = {
    1: {
        "id": 1,
        "name": "RSI Momentum Strategy",
        "description": "Buy/Sell based on RSI levels",
        "indicator": "RSI",
        "operator": "greater_than",
        "value": 70.0,
        "stop_loss": 5.0,
        "target": 10.0,
        "capital": 10000.0,
        "generated_code": """# RSI Momentum Strategy
import pandas as pd
import numpy as np
import yfinance as yf

class RSIMomentumStrategy:
    def __init__(self):
        self.capital = 10000.0
        self.stop_loss_pct = 5.0
        self.target_pct = 10.0
    
    def calculate_rsi(self, prices, period=14):
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def generate_signals(self, data):
        data['RSI'] = self.calculate_rsi(data['Close'])
        data['signal'] = 0
        data.loc[data['RSI'] > 70, 'signal'] = 1  # Buy signal
        data.loc[data['RSI'] < 30, 'signal'] = -1  # Sell signal
        return data
    
    def backtest(self, symbol='AAPL', period='1y'):
        data = yf.download(symbol, period=period)
        return self.generate_signals(data)

# Usage example:
strategy = RSIMomentumStrategy()
results = strategy.backtest('AAPL')
print(f"Strategy executed successfully!")""",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "user_id": 1
    },
    2: {
        "id": 2,
        "name": "Moving Average Crossover",
        "description": "SMA 20/50 crossover signals",
        "indicator": "SMA",
        "operator": "crosses_above",
        "value": 50.0,
        "stop_loss": 3.0,
        "target": 8.0,
        "capital": 15000.0,
        "generated_code": """# Moving Average Crossover Strategy
import pandas as pd
import numpy as np
import yfinance as yf

class MovingAverageCrossoverStrategy:
    def __init__(self):
        self.capital = 15000.0
        self.stop_loss_pct = 3.0
        self.target_pct = 8.0
    
    def calculate_sma(self, prices, period):
        return prices.rolling(window=period).mean()
    
    def generate_signals(self, data):
        data['SMA_20'] = self.calculate_sma(data['Close'], 20)
        data['SMA_50'] = self.calculate_sma(data['Close'], 50)
        data['signal'] = 0
        
        # Buy when SMA 20 crosses above SMA 50
        buy_condition = (data['SMA_20'] > data['SMA_50']) & (data['SMA_20'].shift(1) <= data['SMA_50'].shift(1))
        data.loc[buy_condition, 'signal'] = 1
        
        # Sell when SMA 20 crosses below SMA 50
        sell_condition = (data['SMA_20'] < data['SMA_50']) & (data['SMA_20'].shift(1) >= data['SMA_50'].shift(1))
        data.loc[sell_condition, 'signal'] = -1
        
        return data
    
    def backtest(self, symbol='AAPL', period='1y'):
        data = yf.download(symbol, period=period)
        return self.generate_signals(data)

# Usage example:
strategy = MovingAverageCrossoverStrategy()
results = strategy.backtest('AAPL')
print(f"Strategy executed successfully!")""",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "user_id": 1
    }
}

# Helper functions
def is_api_request(request: Request) -> bool:
    """Detect if request is from API client"""
    content_type = request.headers.get("content-type", "")
    accept_header = request.headers.get("accept", "")
    return (
        "application/json" in content_type or 
        "application/json" in accept_header or
        request.headers.get("x-requested-with") == "XMLHttpRequest"
    )

def validate_strategy_data(data: dict) -> tuple[bool, str]:
    """Validate strategy data"""
    required_fields = ["name", "indicator", "operator", "value", "stop_loss", "target", "capital"]
    
    for field in required_fields:
        if field not in data or data[field] is None:
            return False, f"{field.replace('_', ' ').title()} is required"
    
    # Validate numeric fields
    if data["value"] <= 0:
        return False, "Value must be greater than 0"
    
    if data["stop_loss"] <= 0 or data["stop_loss"] > 100:
        return False, "Stop loss must be between 0 and 100%"
    
    if data["target"] <= 0:
        return False, "Target must be greater than 0%"
    
    if data["capital"] <= 0:
        return False, "Capital must be greater than 0"
    
    # Validate name length
    if len(data["name"].strip()) < 3:
        return False, "Strategy name must be at least 3 characters"
    
    return True, ""

def get_strategy_safely(db: Session, strategy_id: int, user_id: int):
    """Safely get strategy with error handling"""
    try:
        if strategy_crud:
            return strategy_crud.get_strategy_by_user(db, strategy_id, user_id)
        else:
            # Fallback to sample data
            strategy = SAMPLE_STRATEGIES.get(strategy_id)
            if strategy and strategy.get("user_id") == user_id:
                return strategy
            return None
    except Exception as e:
        logger.error(f"Error getting strategy {strategy_id}: {str(e)}")
        return None

def handle_error_response(request: Request, template: str, error: str, status_code: int = 400):
    """Handle error responses for both API and web requests"""
    if is_api_request(request):
        return JSONResponse(
            content={"error": error, "status": "error"},
            status_code=status_code
        )
    else:
        if status_code == 404:
            return templates.TemplateResponse("404.html", {"request": request, "error": error}, status_code=404)
        elif status_code == 403:
            return templates.TemplateResponse("403.html", {"request": request, "error": error}, status_code=403)
        else:
            return RedirectResponse(url=f"/dashboard?error={error}", status_code=303)

# ========== STRATEGY VIEW ROUTES ==========

@router.get("/strategy/{strategy_id}", response_class=HTMLResponse)
async def view_strategy(
    strategy_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """View strategy details and generated code with enhanced error handling"""
    try:
        logger.info(f"User {current_user.username} viewing strategy {strategy_id}")
        
        # Get strategy with ownership check
        strategy = get_strategy_safely(db, strategy_id, current_user.id)
        
        if not strategy:
            logger.warning(f"Strategy {strategy_id} not found or access denied for user {current_user.id}")
            return handle_error_response(request, "404.html", "Strategy not found", 404)
        
        # For API requests, return JSON
        if is_api_request(request):
            return JSONResponse(content={
                "status": "success",
                "strategy": {
                    "id": strategy["id"] if isinstance(strategy, dict) else strategy.id,
                    "name": strategy["name"] if isinstance(strategy, dict) else strategy.name,
                    "description": strategy["description"] if isinstance(strategy, dict) else strategy.description,
                    "indicator": strategy["indicator"] if isinstance(strategy, dict) else strategy.indicator,
                    "operator": strategy["operator"] if isinstance(strategy, dict) else strategy.operator,
                    "value": strategy["value"] if isinstance(strategy, dict) else strategy.value,
                    "stop_loss": strategy["stop_loss"] if isinstance(strategy, dict) else strategy.stop_loss,
                    "target": strategy["target"] if isinstance(strategy, dict) else strategy.target,
                    "capital": strategy["capital"] if isinstance(strategy, dict) else strategy.capital,
                    "generated_code": strategy["generated_code"] if isinstance(strategy, dict) else strategy.generated_code,
                    "created_at": strategy["created_at"].isoformat() if isinstance(strategy, dict) else strategy.created_at.isoformat(),
                }
            })
        
        # For web requests, return HTML template
        return templates.TemplateResponse("strategy_view.html", {
            "request": request,
            "strategy": strategy,
            "user": current_user,
            "app_name": "Strategy Builder SaaS"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in view_strategy: {str(e)}")
        return handle_error_response(request, "500.html", "Internal server error", 500)

@router.get("/strategy/{strategy_id}/edit", response_class=HTMLResponse)
async def edit_strategy_form(
    strategy_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Show edit form for strategy with pre-filled values"""
    try:
        logger.info(f"User {current_user.username} editing strategy {strategy_id}")
        
        # Get strategy with ownership check
        strategy = get_strategy_safely(db, strategy_id, current_user.id)
        
        if not strategy:
            logger.warning(f"Strategy {strategy_id} not found or access denied for user {current_user.id}")
            return handle_error_response(request, "404.html", "Strategy not found", 404)
        
        # Define options for dropdowns
        indicators = ["RSI", "MACD", "SMA", "EMA", "Bollinger Bands", "Stochastic", "Williams %R"]
        operators = ["greater_than", "less_than", "crosses_above", "crosses_below", "equals", "between"]
        
        # For API requests, return JSON with form data
        if is_api_request(request):
            return JSONResponse(content={
                "status": "success",
                "strategy": {
                    "id": strategy["id"] if isinstance(strategy, dict) else strategy.id,
                    "name": strategy["name"] if isinstance(strategy, dict) else strategy.name,
                    "description": strategy["description"] if isinstance(strategy, dict) else strategy.description,
                    "indicator": strategy["indicator"] if isinstance(strategy, dict) else strategy.indicator,
                    "operator": strategy["operator"] if isinstance(strategy, dict) else strategy.operator,
                    "value": strategy["value"] if isinstance(strategy, dict) else strategy.value,
                    "stop_loss": strategy["stop_loss"] if isinstance(strategy, dict) else strategy.stop_loss,
                    "target": strategy["target"] if isinstance(strategy, dict) else strategy.target,
                    "capital": strategy["capital"] if isinstance(strategy, dict) else strategy.capital,
                },
                "form_options": {
                    "indicators": indicators,
                    "operators": operators
                }
            })
        
        # For web requests, return HTML template
        return templates.TemplateResponse("strategy_edit.html", {
            "request": request,
            "strategy": strategy,
            "user": current_user,
            "indicators": indicators,
            "operators": operators,
            "app_name": "Strategy Builder SaaS"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in edit_strategy_form: {str(e)}")
        return handle_error_response(request, "500.html", "Internal server error", 500)

# ========== STRATEGY UPDATE ROUTES ==========

@router.post("/strategy/{strategy_id}/edit")
async def update_strategy(
    strategy_id: int,
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    indicator: str = Form(...),
    operator: str = Form(...),
    value: float = Form(...),
    stop_loss: float = Form(...),
    target: float = Form(...),
    capital: float = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update strategy with new parameters and regenerate code"""
    try:
        logger.info(f"User {current_user.username} updating strategy {strategy_id}")
        
        # Handle JSON requests
        strategy_data = {}
        if is_api_request(request):
            try:
                body = await request.body()
                if body:
                    json_data = json.loads(body.decode())
                    strategy_data = {
                        "name": json_data.get("name", name),
                        "description": json_data.get("description", description),
                        "indicator": json_data.get("indicator", indicator),
                        "operator": json_data.get("operator", operator),
                        "value": json_data.get("value", value),
                        "stop_loss": json_data.get("stop_loss", stop_loss),
                        "target": json_data.get("target", target),
                        "capital": json_data.get("capital", capital)
                    }
            except json.JSONDecodeError:
                return handle_error_response(request, "", "Invalid JSON data", 400)
        else:
            strategy_data = {
                "name": name,
                "description": description,
                "indicator": indicator,
                "operator": operator,
                "value": value,
                "stop_loss": stop_loss,
                "target": target,
                "capital": capital
            }
        
        # Validate strategy data
        is_valid, error_msg = validate_strategy_data(strategy_data)
        if not is_valid:
            return handle_error_response(request, "", error_msg, 400)
        
        # Get strategy with ownership check
        strategy = get_strategy_safely(db, strategy_id, current_user.id)
        if not strategy:
            return handle_error_response(request, "404.html", "Strategy not found", 404)
        
        # Generate new code with updated parameters
        try:
            generated_code = generate_strategy_code(strategy_data)
            strategy_data["generated_code"] = generated_code
        except Exception as e:
            logger.error(f"Code generation failed: {str(e)}")
            return handle_error_response(request, "", f"Code generation failed: {str(e)}", 400)
        
        # Update strategy in database or sample data
        try:
            if strategy_crud:
                updated_strategy = strategy_crud.update_strategy(db, strategy_id, strategy_data)
                if not updated_strategy:
                    return handle_error_response(request, "", "Failed to update strategy", 500)
            else:
                # Update sample data
                if strategy_id in SAMPLE_STRATEGIES:
                    SAMPLE_STRATEGIES[strategy_id].update(strategy_data)
                    SAMPLE_STRATEGIES[strategy_id]["updated_at"] = datetime.now()
        except SQLAlchemyError as e:
            logger.error(f"Database error updating strategy: {str(e)}")
            return handle_error_response(request, "", "Database error occurred", 500)
        
        logger.info(f"Strategy {strategy_id} updated successfully by user {current_user.username}")
        
        # Return appropriate response
        if is_api_request(request):
            return JSONResponse(content={
                "status": "success",
                "message": "Strategy updated successfully",
                "strategy_id": strategy_id,
                "redirect": f"/strategy/{strategy_id}"
            })
        else:
            return RedirectResponse(
                url="/dashboard?message=Strategy updated successfully&type=success",
                status_code=status.HTTP_303_SEE_OTHER
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in update_strategy: {str(e)}")
        return handle_error_response(request, "", "Internal server error", 500)

# ========== STRATEGY DELETE ROUTES ==========

@router.post("/strategy/{strategy_id}/delete")
async def delete_strategy(
    strategy_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a strategy with comprehensive error handling"""
    try:
        logger.info(f"User {current_user.username} deleting strategy {strategy_id}")
        
        # Get strategy with ownership check
        strategy = get_strategy_safely(db, strategy_id, current_user.id)
        if not strategy:
            return handle_error_response(request, "404.html", "Strategy not found", 404)
        
        # Delete strategy from database or sample data
        try:
            if strategy_crud:
                success = strategy_crud.delete_strategy(db, strategy_id)
                if not success:
                    return handle_error_response(request, "", "Failed to delete strategy", 500)
            else:
                # Delete from sample data
                if strategy_id in SAMPLE_STRATEGIES:
                    del SAMPLE_STRATEGIES[strategy_id]
        except SQLAlchemyError as e:
            logger.error(f"Database error deleting strategy: {str(e)}")
            return handle_error_response(request, "", "Database error occurred", 500)
        
        logger.info(f"Strategy {strategy_id} deleted successfully by user {current_user.username}")
        
        # Return appropriate response
        if is_api_request(request):
            return JSONResponse(content={
                "status": "success",
                "message": "Strategy deleted successfully",
                "redirect": "/dashboard"
            })
        else:
            return RedirectResponse(
                url="/dashboard?message=Strategy deleted successfully&type=success",
                status_code=status.HTTP_303_SEE_OTHER
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in delete_strategy: {str(e)}")
        return handle_error_response(request, "", "Internal server error", 500)

# ========== STRATEGY API ROUTES ==========

@router.get("/api/strategy/{strategy_id}/code")
async def get_strategy_code(
    strategy_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get strategy code for copying (API endpoint)"""
    try:
        strategy = get_strategy_safely(db, strategy_id, current_user.id)
        
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        code = strategy["generated_code"] if isinstance(strategy, dict) else strategy.generated_code
        
        return JSONResponse(content={
            "status": "success",
            "strategy_id": strategy_id,
            "code": code,
            "language": "python"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting strategy code: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get strategy code")

@router.get("/api/strategies")
async def list_user_strategies(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """List user strategies with pagination (API endpoint)"""
    try:
        if strategy_crud:
            strategies = strategy_crud.get_user_strategies(db, current_user.id)
        else:
            # Use sample data
            strategies = [s for s in SAMPLE_STRATEGIES.values() if s.get("user_id") == current_user.id]
        
        # Apply pagination
        total = len(strategies)
        strategies_page = strategies[offset:offset + limit]
        
        # Format response
        strategy_list = []
        for strategy in strategies_page:
            if isinstance(strategy, dict):
                strategy_list.append({
                    "id": strategy["id"],
                    "name": strategy["name"],
                    "description": strategy["description"],
                    "indicator": strategy["indicator"],
                    "created_at": strategy["created_at"].isoformat(),
                    "updated_at": strategy["updated_at"].isoformat()
                })
            else:
                strategy_list.append({
                    "id": strategy.id,
                    "name": strategy.name,
                    "description": strategy.description,
                    "indicator": strategy.indicator,
                    "created_at": strategy.created_at.isoformat(),
                    "updated_at": strategy.updated_at.isoformat() if strategy.updated_at else None
                })
        
        return JSONResponse(content={
            "status": "success",
            "strategies": strategy_list,
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_next": offset + limit < total
            }
        })
        
    except Exception as e:
        logger.error(f"Error listing strategies: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list strategies")

@router.post("/api/strategy/{strategy_id}/duplicate")
async def duplicate_strategy(
    strategy_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Duplicate an existing strategy"""
    try:
        # Get original strategy
        original_strategy = get_strategy_safely(db, strategy_id, current_user.id)
        if not original_strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        # Create duplicate data
        if isinstance(original_strategy, dict):
            duplicate_data = {
                "name": f"{original_strategy['name']} (Copy)",
                "description": original_strategy["description"],
                "indicator": original_strategy["indicator"],
                "operator": original_strategy["operator"],
                "value": original_strategy["value"],
                "stop_loss": original_strategy["stop_loss"],
                "target": original_strategy["target"],
                "capital": original_strategy["capital"],
                "generated_code": original_strategy["generated_code"]
            }
        else:
            duplicate_data = {
                "name": f"{original_strategy.name} (Copy)",
                "description": original_strategy.description,
                "indicator": original_strategy.indicator,
                "operator": original_strategy.operator,
                "value": original_strategy.value,
                "stop_loss": original_strategy.stop_loss,
                "target": original_strategy.target,
                "capital": original_strategy.capital,
                "generated_code": original_strategy.generated_code
            }
        
        # Create new strategy
        if strategy_crud:
            new_strategy = strategy_crud.create_strategy(db, duplicate_data, current_user.id)
            new_id = new_strategy.id
        else:
            # Create in sample data
            new_id = max(SAMPLE_STRATEGIES.keys()) + 1 if SAMPLE_STRATEGIES else 1
            duplicate_data.update({
                "id": new_id,
                "user_id": current_user.id,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            })
            SAMPLE_STRATEGIES[new_id] = duplicate_data
        
        logger.info(f"Strategy {strategy_id} duplicated as {new_id} by user {current_user.username}")
        
        return JSONResponse(content={
            "status": "success",
            "message": "Strategy duplicated successfully",
            "original_id": strategy_id,
            "new_id": new_id,
            "redirect": f"/strategy/{new_id}"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error duplicating strategy: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to duplicate strategy")

# ========== UTILITY ROUTES ==========

@router.get("/api/strategy/indicators")
async def get_available_indicators():
    """Get list of available indicators"""
    return JSONResponse(content={
        "status": "success",
        "indicators": [
            {"value": "RSI", "label": "Relative Strength Index (RSI)", "description": "Momentum oscillator"},
            {"value": "MACD", "label": "MACD", "description": "Moving Average Convergence Divergence"},
            {"value": "SMA", "label": "Simple Moving Average", "description": "Average price over time"},
            {"value": "EMA", "label": "Exponential Moving Average", "description": "Weighted average giving more importance to recent prices"},
            {"value": "Bollinger Bands", "label": "Bollinger Bands", "description": "Volatility bands around moving average"},
            {"value": "Stochastic", "label": "Stochastic Oscillator", "description": "Momentum indicator"},
            {"value": "Williams %R", "label": "Williams %R", "description": "Momentum indicator similar to Stochastic"}
        ]
    })

@router.get("/api/strategy/operators")
async def get_available_operators():
    """Get list of available operators"""
    return JSONResponse(content={
        "status": "success",
        "operators": [
            {"value": "greater_than", "label": "Greater Than", "description": "Value is greater than threshold"},
            {"value": "less_than", "label": "Less Than", "description": "Value is less than threshold"},
            {"value": "crosses_above", "label": "Crosses Above", "description": "Value crosses above threshold"},
            {"value": "crosses_below", "label": "Crosses Below", "description": "Value crosses below threshold"},
            {"value": "equals", "label": "Equals", "description": "Value equals threshold"},
            {"value": "between", "label": "Between", "description": "Value is between two thresholds"}
        ]
    })

@router.get("/health")
async def strategy_health_check():
    """Health check for strategy service"""
    return {
        "status": "healthy",
        "service": "strategy",
        "version": "2.0.0",
        "endpoints": {
            "view": "GET /strategy/{id}",
            "edit": "GET,POST /strategy/{id}/edit",
            "delete": "POST /strategy/{id}/delete",
            "list": "GET /api/strategies",
            "duplicate": "POST /api/strategy/{id}/duplicate"
        },
        "features": [
            "CRUD operations",
            "Code generation",
            "Ownership verification",
            "API and web support",
            "Error handling"
        ]
    }