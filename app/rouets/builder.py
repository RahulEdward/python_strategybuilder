from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Annotated
import logging

# Import your dependencies
from services.code_generator import generate_python_strategy
from dependencies.auth import get_current_user  # Adjust import path as needed
from models.user import User  # Adjust import path as needed

# Configure logging
logger = logging.getLogger(__name__)

# Initialize router and templates
router = APIRouter(prefix="/builder", tags=["strategy-builder"])
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def get_builder_page(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Render the strategy builder form page.
    Only accessible to authenticated users.
    """
    try:
        context = {
            "request": request,
            "user": current_user,
            "page_title": "Strategy Builder",
            "generated_code": None,  # No code on initial load
        }
        return templates.TemplateResponse("builder.html", context)
    
    except Exception as e:
        logger.error(f"Error rendering builder page: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/", response_class=HTMLResponse)
async def process_strategy_builder(
    request: Request,
    indicator: Annotated[str, Form()],
    operator: Annotated[str, Form()],
    value: Annotated[float, Form()],
    stop_loss: Annotated[float, Form()],
    target: Annotated[float, Form()],
    capital: Annotated[float, Form()],
    current_user: User = Depends(get_current_user)
):
    """
    Process the strategy builder form submission.
    Generate Python strategy code and return it in the same template.
    """
    try:
        # Validate form inputs
        validation_errors = []
        
        if not indicator or indicator == "":
            validation_errors.append("Please select a technical indicator")
        
        if not operator or operator == "":
            validation_errors.append("Please select an operator")
        
        if value is None:
            validation_errors.append("Please enter a threshold value")
        
        if stop_loss is None or stop_loss <= 0 or stop_loss >= 100:
            validation_errors.append("Stop loss must be between 0 and 100%")
        
        if target is None or target <= 0:
            validation_errors.append("Target must be greater than 0%")
        
        if capital is None or capital < 1000:
            validation_errors.append("Capital must be at least ₹1,000")
        
        # If validation fails, return form with errors
        if validation_errors:
            context = {
                "request": request,
                "user": current_user,
                "page_title": "Strategy Builder",
                "generated_code": None,
                "errors": validation_errors,
                "form_data": {
                    "indicator": indicator,
                    "operator": operator,
                    "value": value,
                    "stop_loss": stop_loss,
                    "target": target,
                    "capital": capital,
                }
            }
            return templates.TemplateResponse("builder.html", context)
        
        # Create strategy parameters
        strategy_params = {
            "indicator": indicator,
            "operator": operator,
            "value": value,
            "stop_loss": stop_loss,
            "target": target,
            "capital": capital,
            "user_id": current_user.id  # Optional: for user-specific customization
        }
        
        # Generate the Python strategy code
        logger.info(f"Generating strategy for user {current_user.id} with params: {strategy_params}")
        generated_code = generate_python_strategy(strategy_params)
        
        # Log successful generation
        logger.info(f"Successfully generated strategy code for user {current_user.id}")
        
        # Prepare template context with generated code
        context = {
            "request": request,
            "user": current_user,
            "page_title": "Strategy Builder",
            "generated_code": generated_code,
            "form_data": strategy_params,
            "success_message": "Strategy code generated successfully!"
        }
        
        return templates.TemplateResponse("builder.html", context)
    
    except ValueError as e:
        logger.error(f"Validation error in strategy builder: {str(e)}")
        context = {
            "request": request,
            "user": current_user,
            "page_title": "Strategy Builder",
            "generated_code": None,
            "errors": [f"Input validation error: {str(e)}"],
            "form_data": {
                "indicator": indicator,
                "operator": operator,
                "value": value,
                "stop_loss": stop_loss,
                "target": target,
                "capital": capital,
            }
        }
        return templates.TemplateResponse("builder.html", context)
    
    except Exception as e:
        logger.error(f"Unexpected error in strategy builder: {str(e)}")
        context = {
            "request": request,
            "user": current_user,
            "page_title": "Strategy Builder",
            "generated_code": None,
            "errors": ["An unexpected error occurred. Please try again."],
            "form_data": {
                "indicator": indicator,
                "operator": operator,
                "value": value,
                "stop_loss": stop_loss,
                "target": target,
                "capital": capital,
            }
        }
        return templates.TemplateResponse("builder.html", context)


# Optional: Additional utility endpoints
@router.get("/indicators", response_class=HTMLResponse)
async def get_available_indicators(current_user: User = Depends(get_current_user)):
    """
    API endpoint to get list of available indicators.
    Useful for dynamic form population or AJAX requests.
    """
    indicators = [
        {"value": "RSI", "label": "RSI (Relative Strength Index)"},
        {"value": "EMA", "label": "EMA (Exponential Moving Average)"},
        {"value": "SMA", "label": "SMA (Simple Moving Average)"},
        {"value": "MACD", "label": "MACD (Moving Average Convergence Divergence)"},
        {"value": "Bollinger_Bands", "label": "Bollinger Bands"},
        {"value": "Stochastic", "label": "Stochastic Oscillator"},
        {"value": "Williams_R", "label": "Williams %R"},
        {"value": "CCI", "label": "CCI (Commodity Channel Index)"},
    ]
    return {"indicators": indicators}


@router.get("/operators", response_class=HTMLResponse)
async def get_available_operators(current_user: User = Depends(get_current_user)):
    """
    API endpoint to get list of available operators.
    """
    operators = [
        {"value": ">", "label": "Greater than (>)"},
        {"value": "<", "label": "Less than (<)"},
        {"value": "==", "label": "Equal to (==)"},
        {"value": ">=", "label": "Greater than or equal (>=)"},
        {"value": "<=", "label": "Less than or equal (<=)"},
        {"value": "crosses_above", "label": "Crosses Above"},
        {"value": "crosses_below", "label": "Crosses Below"},
    ]
    return {"operators": operators}