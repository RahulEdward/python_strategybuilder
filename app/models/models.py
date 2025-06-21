"""
Pydantic Models for FastAPI Strategy Builder
Defines request/response models for API endpoints
"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from datetime import datetime

# Enums
class IndicatorType(str, Enum):
    """Supported technical indicators"""
    RSI = "RSI"
    EMA = "EMA"
    SMA = "SMA"
    MACD = "MACD"
    BB = "BB"
    STOCH = "STOCH"
    CCI = "CCI"
    WILLIAMS = "WILLIAMS"
    ATR = "ATR"
    ADX = "ADX"
    CUSTOM = "CUSTOM"

class OperatorType(str, Enum):
    """Supported comparison operators"""
    ABOVE = "above"
    BELOW = "below"
    EQUAL = "equal"
    NOT_EQUAL = "not_equal"
    GREATER_EQUAL = "greater_equal"
    LESS_EQUAL = "less_equal"
    CROSSES_ABOVE = "crosses_above"
    CROSSES_BELOW = "crosses_below"

class TimeframeType(str, Enum):
    """Supported timeframes"""
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"
    MN1 = "1M"

class ConditionLogic(str, Enum):
    """Logic for combining conditions"""
    AND = "AND"
    OR = "OR"

class ConditionType(str, Enum):
    """Type of trading condition"""
    BUY = "buy"
    SELL = "sell"

# Base Models
class IndicatorConfig(BaseModel):
    """Configuration for technical indicator"""
    indicator: IndicatorType = Field(..., description="Type of technical indicator")
    period: Optional[int] = Field(14, ge=1, le=200, description="Period for calculation")
    timeframe: Optional[TimeframeType] = Field(TimeframeType.D1, description="Timeframe for indicator")
    source: Optional[str] = Field("close", description="Price source (open, high, low, close)")
    custom_value: Optional[float] = Field(None, description="Custom value for CUSTOM indicator")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional parameters")

    @validator('custom_value')
    def validate_custom_value(cls, v, values):
        """Validate custom value is provided for CUSTOM indicator"""
        if values.get('indicator') == IndicatorType.CUSTOM and v is None:
            raise ValueError('custom_value is required for CUSTOM indicator')
        return v

class TradingCondition(BaseModel):
    """Single trading condition (left operator right)"""
    type: ConditionType = Field(..., description="Type of condition (buy/sell)")
    left: IndicatorConfig = Field(..., description="Left side of condition")
    operator: OperatorType = Field(..., description="Comparison operator")
    right: IndicatorConfig = Field(..., description="Right side of condition")
    logic: Optional[ConditionLogic] = Field(ConditionLogic.AND, description="Logic to combine with next condition")
    enabled: Optional[bool] = Field(True, description="Whether this condition is enabled")
    description: Optional[str] = Field(None, description="Human readable description")

    @validator('right')
    def validate_right_side(cls, v, values):
        """Validate right side configuration"""
        if v.indicator == IndicatorType.CUSTOM and v.custom_value is None:
            raise ValueError('Right side CUSTOM indicator must have custom_value')
        return v

class MoneyManagement(BaseModel):
    """Money management and risk settings"""
    position_size: Optional[float] = Field(10, ge=0.1, le=100, description="Position size as % of capital")
    max_risk: Optional[float] = Field(2, ge=0.1, le=50, description="Maximum risk per trade (%)")
    profit_target: Optional[float] = Field(5, ge=0.1, description="Profit target (%)")
    max_positions: Optional[int] = Field(1, ge=1, le=10, description="Maximum concurrent positions")
    initial_capital: Optional[float] = Field(100000, ge=1000, description="Initial trading capital")
    commission: Optional[float] = Field(0.001, ge=0, le=0.1, description="Commission rate (decimal)")
    stop_loss: Optional[float] = Field(None, ge=0.1, le=50, description="Stop loss percentage")
    trailing_stop: Optional[bool] = Field(False, description="Enable trailing stop")
    trailing_stop_distance: Optional[float] = Field(None, ge=0.1, description="Trailing stop distance (%)")

# Main Request Models
class StrategyRequest(BaseModel):
    """Complete strategy configuration request"""
    name: str = Field(..., min_length=3, max_length=100, description="Strategy name")
    description: Optional[str] = Field(None, max_length=500, description="Strategy description")
    timeframe: Optional[TimeframeType] = Field(TimeframeType.D1, description="Primary timeframe")
    buy_conditions: List[TradingCondition] = Field(..., min_items=1, max_items=10, description="Buy conditions")
    sell_conditions: Optional[List[TradingCondition]] = Field(default_factory=list, max_items=10, description="Sell conditions")
    money_management: Optional[MoneyManagement] = Field(default_factory=MoneyManagement, description="Money management settings")
    tags: Optional[List[str]] = Field(default_factory=list, description="Strategy tags")
    is_active: Optional[bool] = Field(True, description="Whether strategy is active")

    @validator('buy_conditions')
    def validate_buy_conditions(cls, v):
        """Ensure all buy conditions have correct type"""
        for condition in v:
            if condition.type != ConditionType.BUY:
                condition.type = ConditionType.BUY
        return v

    @validator('sell_conditions')
    def validate_sell_conditions(cls, v):
        """Ensure all sell conditions have correct type"""
        for condition in v:
            if condition.type != ConditionType.SELL:
                condition.type = ConditionType.SELL
        return v

class StrategyUpdateRequest(BaseModel):
    """Request to update existing strategy"""
    name: Optional[str] = Field(None, min_length=3, max_length=100, description="Strategy name")
    description: Optional[str] = Field(None, max_length=500, description="Strategy description")
    timeframe: Optional[TimeframeType] = Field(None, description="Primary timeframe")
    buy_conditions: Optional[List[TradingCondition]] = Field(None, min_items=1, max_items=10, description="Buy conditions")
    sell_conditions: Optional[List[TradingCondition]] = Field(None, max_items=10, description="Sell conditions")
    money_management: Optional[MoneyManagement] = Field(None, description="Money management settings")
    tags: Optional[List[str]] = Field(None, description="Strategy tags")
    is_active: Optional[bool] = Field(None, description="Whether strategy is active")

# Response Models
class GeneratedStrategy(BaseModel):
    """Generated strategy code and metadata"""
    strategy_name: str = Field(..., description="Name of the strategy")
    code: str = Field(..., description="Generated Python code")
    indicators_used: List[str] = Field(..., description="List of indicators used")
    conditions_count: Dict[str, int] = Field(..., description="Count of buy/sell conditions")
    code_size: Optional[int] = Field(None, description="Size of generated code in characters")
    estimated_complexity: Optional[str] = Field(None, description="Estimated complexity level")

class StrategyValidation(BaseModel):
    """Strategy validation results"""
    is_valid: bool = Field(..., description="Whether strategy is valid")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    indicators_count: Optional[int] = Field(None, description="Number of unique indicators")
    conditions_count: Optional[Dict[str, int]] = Field(None, description="Count of conditions by type")
    complexity_score: Optional[float] = Field(None, description="Strategy complexity score")

class StrategyResponse(BaseModel):
    """Main response for strategy operations"""
    success: bool = Field(..., description="Whether operation was successful")
    message: str = Field(..., description="Response message")
    strategy: Optional[GeneratedStrategy] = Field(None, description="Generated strategy (if applicable)")
    validation: Optional[StrategyValidation] = Field(None, description="Validation results (if applicable)")
    errors: List[str] = Field(default_factory=list, description="Error messages")
    warnings: List[str] = Field(default_factory=list, description="Warning messages")
    execution_time: Optional[float] = Field(None, description="Execution time in seconds")

class IndicatorInfo(BaseModel):
    """Information about available indicators"""
    name: str = Field(..., description="Indicator name")
    description: str = Field(..., description="Indicator description")
    parameters: List[str] = Field(..., description="Required parameters")
    default_values: Dict[str, Any] = Field(..., description="Default parameter values")
    category: Optional[str] = Field(None, description="Indicator category")
    min_periods: Optional[int] = Field(None, description="Minimum periods required")

class OperatorInfo(BaseModel):
    """Information about available operators"""
    name: str = Field(..., description="Operator name")
    symbol: str = Field(..., description="Operator symbol")
    description: str = Field(..., description="Operator description")
    type: str = Field(..., description="Operator type (comparison/cross)")

class StrategyTemplateInfo(BaseModel):
    """Information about strategy templates"""
    id: str = Field(..., description="Template ID")
    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    category: str = Field(..., description="Template category")
    indicators: List[str] = Field(..., description="Indicators used")
    complexity: str = Field(..., description="Complexity level")
    usage_count: Optional[int] = Field(0, description="Number of times used")

class IndicatorsListResponse(BaseModel):
    """Response for listing available indicators and operators"""
    indicators: List[IndicatorInfo] = Field(..., description="Available indicators")
    operators: List[OperatorInfo] = Field(..., description="Available operators")
    timeframes: List[str] = Field(..., description="Available timeframes")
    templates: List[StrategyTemplateInfo] = Field(..., description="Available templates")

# Backtest Models
class BacktestConfig(BaseModel):
    """Configuration for backtesting"""
    symbol: str = Field("SPY", description="Trading symbol")
    start_date: Optional[datetime] = Field(None, description="Backtest start date")
    end_date: Optional[datetime] = Field(None, description="Backtest end date")
    initial_capital: float = Field(100000, ge=1000, description="Initial capital")
    commission: float = Field(0.001, ge=0, le=0.1, description="Commission rate")
    slippage: float = Field(0.0001, ge=0, le=0.01, description="Slippage rate")
    benchmark: Optional[str] = Field("SPY", description="Benchmark symbol")

class BacktestRequest(BaseModel):
    """Request for backtesting a strategy"""
    strategy_id: Optional[int] = Field(None, description="Existing strategy ID")
    strategy_config: Optional[StrategyRequest] = Field(None, description="Strategy configuration")
    backtest_config: BacktestConfig = Field(..., description="Backtest configuration")
    save_results: Optional[bool] = Field(True, description="Whether to save results")

class TradeRecord(BaseModel):
    """Individual trade record"""
    timestamp: datetime = Field(..., description="Trade timestamp")
    action: str = Field(..., description="BUY or SELL")
    price: float = Field(..., description="Trade price")
    quantity: int = Field(..., description="Trade quantity")
    value: float = Field(..., description="Trade value")
    commission: float = Field(..., description="Commission paid")
    reason: Optional[str] = Field(None, description="Trade reason/signal")

class BacktestResults(BaseModel):
    """Backtest results and performance metrics"""
    # Configuration
    config: BacktestConfig = Field(..., description="Backtest configuration")
    
    # Basic Results
    initial_capital: float = Field(..., description="Initial capital")
    final_capital: float = Field(..., description="Final capital")
    total_return: float = Field(..., description="Total return percentage")
    
    # Trade Statistics
    total_trades: int = Field(..., description="Total number of trades")
    winning_trades: int = Field(..., description="Number of winning trades")
    losing_trades: int = Field(..., description="Number of losing trades")
    win_rate: float = Field(..., description="Win rate percentage")
    
    # Risk Metrics
    sharpe_ratio: Optional[float] = Field(None, description="Sharpe ratio")
    max_drawdown: Optional[float] = Field(None, description="Maximum drawdown percentage")
    volatility: Optional[float] = Field(None, description="Strategy volatility")
    calmar_ratio: Optional[float] = Field(None, description="Calmar ratio")
    
    # Benchmark Comparison
    benchmark_return: Optional[float] = Field(None, description="Benchmark return")
    alpha: Optional[float] = Field(None, description="Alpha vs benchmark")
    beta: Optional[float] = Field(None, description="Beta vs benchmark")
    
    # Detailed Data
    trades: List[TradeRecord] = Field(default_factory=list, description="Individual trades")
    equity_curve: List[float] = Field(default_factory=list, description="Daily equity values")
    monthly_returns: Dict[str, float] = Field(default_factory=dict, description="Monthly returns")
    
    # Execution Metadata
    execution_time: float = Field(..., description="Backtest execution time")
    data_points: int = Field(..., description="Number of data points processed")
    start_date: datetime = Field(..., description="Actual start date")
    end_date: datetime = Field(..., description="Actual end date")

class BacktestResponse(BaseModel):
    """Response for backtest request"""
    success: bool = Field(..., description="Whether backtest was successful")
    message: str = Field(..., description="Response message")
    results: Optional[BacktestResults] = Field(None, description="Backtest results")
    errors: List[str] = Field(default_factory=list, description="Error messages")

# Strategy Management Models
class StrategyListItem(BaseModel):
    """Strategy item for listing"""
    id: int = Field(..., description="Strategy ID")
    name: str = Field(..., description="Strategy name")
    description: Optional[str] = Field(None, description="Strategy description")
    timeframe: str = Field(..., description="Primary timeframe")
    indicators_used: List[str] = Field(..., description="Indicators used")
    is_active: bool = Field(..., description="Whether strategy is active")
    is_backtested: bool = Field(..., description="Whether strategy has been backtested")
    performance: Optional[Dict[str, Any]] = Field(None, description="Performance summary")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

class StrategyListResponse(BaseModel):
    """Response for listing strategies"""
    strategies: List[StrategyListItem] = Field(..., description="List of strategies")
    total_count: int = Field(..., description="Total number of strategies")
    page: int = Field(1, description="Current page")
    page_size: int = Field(10, description="Page size")
    total_pages: int = Field(..., description="Total number of pages")

class StrategyDetails(BaseModel):
    """Detailed strategy information"""
    id: int = Field(..., description="Strategy ID")
    name: str = Field(..., description="Strategy name")
    description: Optional[str] = Field(None, description="Strategy description")
    timeframe: str = Field(..., description="Primary timeframe")
    buy_conditions: List[Dict[str, Any]] = Field(..., description="Buy conditions")
    sell_conditions: List[Dict[str, Any]] = Field(..., description="Sell conditions")
    money_management: Dict[str, Any] = Field(..., description="Money management settings")
    indicators_used: List[str] = Field(..., description="Indicators used")
    generated_code: str = Field(..., description="Generated strategy code")
    is_active: bool = Field(..., description="Whether strategy is active")
    is_backtested: bool = Field(..., description="Whether strategy has been backtested")
    performance: Optional[Dict[str, Any]] = Field(None, description="Performance metrics")
    backtest_history: List[Dict[str, Any]] = Field(default_factory=list, description="Backtest history")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

class StrategyDetailsResponse(BaseModel):
    """Response for strategy details"""
    success: bool = Field(..., description="Whether request was successful")
    strategy: Optional[StrategyDetails] = Field(None, description="Strategy details")
    message: str = Field(..., description="Response message")

# Error Models
class ValidationError(BaseModel):
    """Validation error details"""
    field: str = Field(..., description="Field with error")
    message: str = Field(..., description="Error message")
    code: str = Field(..., description="Error code")

class APIError(BaseModel):
    """API error response"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[List[ValidationError]] = Field(None, description="Validation error details")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")

# Statistics and Analytics Models
class StrategyStatistics(BaseModel):
    """Strategy usage and performance statistics"""
    total_strategies: int = Field(..., description="Total number of strategies")
    active_strategies: int = Field(..., description="Number of active strategies")
    backtested_strategies: int = Field(..., description="Number of backtested strategies")
    profitable_strategies: int = Field(..., description="Number of profitable strategies")
    avg_return: Optional[float] = Field(None, description="Average return across all strategies")
    success_rate: float = Field(..., description="Success rate percentage")
    popular_indicators: List[Dict[str, Any]] = Field(default_factory=list, description="Most used indicators")
    popular_timeframes: List[Dict[str, Any]] = Field(default_factory=list, description="Most used timeframes")

class UserStatistics(BaseModel):
    """User-specific statistics"""
    user_id: int = Field(..., description="User ID")
    total_strategies: int = Field(..., description="Total strategies created")
    active_strategies: int = Field(..., description="Active strategies")
    best_performing_strategy: Optional[Dict[str, Any]] = Field(None, description="Best performing strategy")
    total_backtests: int = Field(..., description="Total backtests run")
    avg_strategy_return: Optional[float] = Field(None, description="Average strategy return")
    favorite_indicators: List[str] = Field(default_factory=list, description="Most used indicators")
    account_created: datetime = Field(..., description="Account creation date")
    last_activity: Optional[datetime] = Field(None, description="Last activity timestamp")

# Export/Import Models
class StrategyExport(BaseModel):
    """Strategy export data"""
    metadata: Dict[str, Any] = Field(..., description="Export metadata")
    strategy: StrategyRequest = Field(..., description="Strategy configuration")
    performance: Optional[Dict[str, Any]] = Field(None, description="Performance data")
    backtest_results: Optional[List[BacktestResults]] = Field(None, description="Backtest results")
    export_timestamp: datetime = Field(default_factory=datetime.now, description="Export timestamp")
    version: str = Field("1.0", description="Export format version")

class StrategyImport(BaseModel):
    """Strategy import request"""
    strategy_data: StrategyExport = Field(..., description="Strategy export data")
    overwrite_existing: bool = Field(False, description="Whether to overwrite existing strategy")
    import_performance: bool = Field(True, description="Whether to import performance data")

# Configuration Models
class SystemConfiguration(BaseModel):
    """System configuration for strategy builder"""
    max_strategies_per_user: int = Field(50, description="Maximum strategies per user")
    max_conditions_per_strategy: int = Field(10, description="Maximum conditions per strategy")
    supported_symbols: List[str] = Field(default_factory=list, description="Supported trading symbols")
    default_commission: float = Field(0.001, description="Default commission rate")
    max_backtest_days: int = Field(365, description="Maximum backtest period in days")
    rate_limit: Dict[str, int] = Field(default_factory=dict, description="API rate limits")

# WebSocket Models (for real-time updates)
class WebSocketMessage(BaseModel):
    """WebSocket message format"""
    type: str = Field(..., description="Message type")
    data: Dict[str, Any] = Field(..., description="Message data")
    timestamp: datetime = Field(default_factory=datetime.now, description="Message timestamp")
    user_id: Optional[int] = Field(None, description="Target user ID")

class StrategyUpdate(BaseModel):
    """Real-time strategy update"""
    strategy_id: int = Field(..., description="Strategy ID")
    update_type: str = Field(..., description="Type of update")
    data: Dict[str, Any] = Field(..., description="Update data")
    timestamp: datetime = Field(default_factory=datetime.now, description="Update timestamp")

# Helper functions for model validation
def validate_timeframe(timeframe: str) -> bool:
    """Validate timeframe format"""
    valid_timeframes = [tf.value for tf in TimeframeType]
    return timeframe in valid_timeframes

def validate_indicator_config(config: Dict[str, Any]) -> bool:
    """Validate indicator configuration"""
    try:
        IndicatorConfig(**config)
        return True
    except Exception:
        return False

def validate_money_management(config: Dict[str, Any]) -> bool:
    """Validate money management configuration"""
    try:
        MoneyManagement(**config)
        return True
    except Exception:
        return False

# Model factory functions
def create_default_strategy_request() -> StrategyRequest:
    """Create a default strategy request for testing"""
    return StrategyRequest(
        name="Default Strategy",
        description="Default strategy for testing",
        timeframe=TimeframeType.D1,
        buy_conditions=[
            TradingCondition(
                type=ConditionType.BUY,
                left=IndicatorConfig(indicator=IndicatorType.RSI, period=14),
                operator=OperatorType.BELOW,
                right=IndicatorConfig(indicator=IndicatorType.CUSTOM, custom_value=30)
            )
        ],
        sell_conditions=[
            TradingCondition(
                type=ConditionType.SELL,
                left=IndicatorConfig(indicator=IndicatorType.RSI, period=14),
                operator=OperatorType.ABOVE,
                right=IndicatorConfig(indicator=IndicatorType.CUSTOM, custom_value=70)
            )
        ],
        money_management=MoneyManagement()
    )

def create_error_response(message: str, errors: List[str] = None) -> StrategyResponse:
    """Create an error response"""
    return StrategyResponse(
        success=False,
        message=message,
        errors=errors or []
    )

def create_success_response(message: str, strategy: GeneratedStrategy = None) -> StrategyResponse:
    """Create a success response"""
    return StrategyResponse(
        success=True,
        message=message,
        strategy=strategy
    )

# Model export for easy importing
__all__ = [
    # Enums
    "IndicatorType", "OperatorType", "TimeframeType", "ConditionLogic", "ConditionType",
    
    # Base Models
    "IndicatorConfig", "TradingCondition", "MoneyManagement",
    
    # Request Models
    "StrategyRequest", "StrategyUpdateRequest", "BacktestRequest",
    
    # Response Models
    "GeneratedStrategy", "StrategyValidation", "StrategyResponse",
    "IndicatorInfo", "OperatorInfo", "StrategyTemplateInfo", "IndicatorsListResponse",
    "BacktestResults", "BacktestResponse",
    "StrategyListItem", "StrategyListResponse", "StrategyDetails", "StrategyDetailsResponse",
    
    # Error Models
    "ValidationError", "APIError",
    
    # Statistics Models
    "StrategyStatistics", "UserStatistics",
    
    # Export/Import Models
    "StrategyExport", "StrategyImport",
    
    # Configuration Models
    "SystemConfiguration", "WebSocketMessage", "StrategyUpdate",
    
    # Helper Functions
    "validate_timeframe", "validate_indicator_config", "validate_money_management",
    "create_default_strategy_request", "create_error_response", "create_success_response"
]