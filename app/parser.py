"""
Strategy Parser Module for FastAPI Strategy Builder
Handles parsing and validation of trading strategies
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

# Setup logging
logger = logging.getLogger(__name__)

class StrategyParser:
    """Main parser class for strategy configurations"""
    
    def __init__(self):
        """Initialize the strategy parser"""
        self.supported_indicators = {
            "RSI": {"name": "Relative Strength Index", "params": ["period"], "defaults": {"period": 14}},
            "EMA": {"name": "Exponential Moving Average", "params": ["period"], "defaults": {"period": 20}},
            "SMA": {"name": "Simple Moving Average", "params": ["period"], "defaults": {"period": 50}},
            "MACD": {"name": "MACD", "params": ["fast", "slow", "signal"], "defaults": {"fast": 12, "slow": 26, "signal": 9}},
            "BB": {"name": "Bollinger Bands", "params": ["period", "std"], "defaults": {"period": 20, "std": 2}},
            "STOCH": {"name": "Stochastic", "params": ["k", "d", "smooth"], "defaults": {"k": 14, "d": 3, "smooth": 3}},
            "CCI": {"name": "Commodity Channel Index", "params": ["period"], "defaults": {"period": 20}},
            "WILLIAMS": {"name": "Williams %R", "params": ["period"], "defaults": {"period": 14}},
            "ATR": {"name": "Average True Range", "params": ["period"], "defaults": {"period": 14}},
            "ADX": {"name": "Average Directional Index", "params": ["period"], "defaults": {"period": 14}},
            "CUSTOM": {"name": "Custom Value", "params": [], "defaults": {}}
        }
        
        self.supported_operators = {
            "above": ">",
            "below": "<", 
            "equal": "==",
            "not_equal": "!=",
            "crosses_above": "crossover",
            "crosses_below": "crossunder",
            "greater_equal": ">=",
            "less_equal": "<="
        }
        
        self.supported_timeframes = ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M"]
        
        logger.info("Strategy Parser initialized successfully")
    
    def validate_strategy(self, strategy_request) -> Dict[str, Any]:
        """
        Validate a strategy configuration
        
        Args:
            strategy_request: Strategy request object or dict
            
        Returns:
            Dict with validation results
        """
        try:
            errors = []
            warnings = []
            
            # Convert to dict if it's an object
            if hasattr(strategy_request, '__dict__'):
                strategy_data = strategy_request.__dict__
            elif hasattr(strategy_request, 'dict'):
                strategy_data = strategy_request.dict()
            else:
                strategy_data = strategy_request
            
            # Validate basic structure
            if not isinstance(strategy_data, dict):
                errors.append("Strategy must be a valid dictionary or object")
                return {"is_valid": False, "errors": errors, "warnings": warnings}
            
            # Validate strategy name
            strategy_name = strategy_data.get('name', '').strip()
            if not strategy_name:
                errors.append("Strategy name is required")
            elif len(strategy_name) < 3:
                errors.append("Strategy name must be at least 3 characters long")
            elif len(strategy_name) > 100:
                errors.append("Strategy name must be less than 100 characters")
            
            # Validate buy conditions
            buy_conditions = strategy_data.get('buy_conditions', [])
            if not isinstance(buy_conditions, list):
                errors.append("Buy conditions must be a list")
            elif len(buy_conditions) == 0:
                errors.append("At least one buy condition is required")
            elif len(buy_conditions) > 10:
                warnings.append("More than 10 buy conditions may impact performance")
            
            # Validate sell conditions  
            sell_conditions = strategy_data.get('sell_conditions', [])
            if not isinstance(sell_conditions, list):
                errors.append("Sell conditions must be a list")
            elif len(sell_conditions) == 0:
                warnings.append("No sell conditions defined - using default stop loss/take profit")
            elif len(sell_conditions) > 10:
                warnings.append("More than 10 sell conditions may impact performance")
            
            # Validate individual conditions
            condition_errors = []
            
            # Validate buy conditions
            for i, condition in enumerate(buy_conditions):
                cond_errors = self._validate_condition(condition, f"Buy condition {i+1}")
                condition_errors.extend(cond_errors)
            
            # Validate sell conditions
            for i, condition in enumerate(sell_conditions):
                cond_errors = self._validate_condition(condition, f"Sell condition {i+1}")
                condition_errors.extend(cond_errors)
            
            errors.extend(condition_errors)
            
            # Validate timeframe
            timeframe = strategy_data.get('timeframe', '1d')
            if timeframe not in self.supported_timeframes:
                errors.append(f"Unsupported timeframe: {timeframe}")
            
            # Validate money management
            money_mgmt = strategy_data.get('money_management', {})
            if money_mgmt:
                mgmt_errors = self._validate_money_management(money_mgmt)
                errors.extend(mgmt_errors)
            
            # Final validation
            is_valid = len(errors) == 0
            
            result = {
                "is_valid": is_valid,
                "errors": errors,
                "warnings": warnings,
                "summary": {
                    "buy_conditions_count": len(buy_conditions),
                    "sell_conditions_count": len(sell_conditions),
                    "total_errors": len(errors),
                    "total_warnings": len(warnings)
                }
            }
            
            logger.info(f"Strategy validation completed: {'PASSED' if is_valid else 'FAILED'}")
            return result
            
        except Exception as e:
            logger.error(f"Strategy validation error: {str(e)}")
            return {
                "is_valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": []
            }
    
    def _validate_condition(self, condition: Dict, condition_name: str) -> List[str]:
        """Validate individual condition"""
        errors = []
        
        try:
            # Check if condition has required fields
            if not isinstance(condition, dict):
                errors.append(f"{condition_name}: Must be a dictionary")
                return errors
            
            # Validate left side (indicator)
            left = condition.get('left', {})
            if not isinstance(left, dict):
                errors.append(f"{condition_name}: Left side must be a dictionary")
            else:
                # Validate indicator
                indicator = left.get('indicator', '')
                if not indicator:
                    errors.append(f"{condition_name}: Left indicator is required")
                elif indicator not in self.supported_indicators:
                    errors.append(f"{condition_name}: Unsupported left indicator '{indicator}'")
                
                # Validate period if required
                period = left.get('period')
                if indicator != 'CUSTOM' and period is not None:
                    if not isinstance(period, (int, float)) or period <= 0:
                        errors.append(f"{condition_name}: Period must be a positive number")
            
            # Validate operator
            operator = condition.get('operator', '')
            if not operator:
                errors.append(f"{condition_name}: Operator is required")
            elif operator not in self.supported_operators:
                errors.append(f"{condition_name}: Unsupported operator '{operator}'")
            
            # Validate right side
            right = condition.get('right', {})
            if not isinstance(right, dict):
                errors.append(f"{condition_name}: Right side must be a dictionary")
            else:
                # Validate right indicator
                right_indicator = right.get('indicator', '')
                if not right_indicator:
                    errors.append(f"{condition_name}: Right indicator is required")
                elif right_indicator not in self.supported_indicators:
                    errors.append(f"{condition_name}: Unsupported right indicator '{right_indicator}'")
                
                # Validate custom value for CUSTOM indicator
                if right_indicator == 'CUSTOM':
                    custom_value = right.get('custom_value')
                    if custom_value is None:
                        errors.append(f"{condition_name}: Custom value is required for CUSTOM indicator")
                    elif not isinstance(custom_value, (int, float)):
                        errors.append(f"{condition_name}: Custom value must be a number")
        
        except Exception as e:
            errors.append(f"{condition_name}: Validation error - {str(e)}")
        
        return errors
    
    def _validate_money_management(self, money_mgmt: Dict) -> List[str]:
        """Validate money management settings"""
        errors = []
        
        try:
            # Validate position size
            position_size = money_mgmt.get('position_size')
            if position_size is not None:
                if not isinstance(position_size, (int, float)) or position_size <= 0 or position_size > 100:
                    errors.append("Position size must be between 0 and 100")
            
            # Validate max risk
            max_risk = money_mgmt.get('max_risk')
            if max_risk is not None:
                if not isinstance(max_risk, (int, float)) or max_risk <= 0 or max_risk > 50:
                    errors.append("Max risk must be between 0 and 50")
            
            # Validate profit target
            profit_target = money_mgmt.get('profit_target')
            if profit_target is not None:
                if not isinstance(profit_target, (int, float)) or profit_target <= 0:
                    errors.append("Profit target must be a positive number")
            
            # Validate max positions
            max_positions = money_mgmt.get('max_positions')
            if max_positions is not None:
                if not isinstance(max_positions, int) or max_positions <= 0 or max_positions > 10:
                    errors.append("Max positions must be between 1 and 10")
            
            # Validate initial capital
            initial_capital = money_mgmt.get('initial_capital')
            if initial_capital is not None:
                if not isinstance(initial_capital, (int, float)) or initial_capital <= 0:
                    errors.append("Initial capital must be a positive number")
        
        except Exception as e:
            errors.append(f"Money management validation error: {str(e)}")
        
        return errors
    
    def parse_strategy(self, strategy_request) -> Dict[str, Any]:
        """
        Parse strategy request into standardized format
        
        Args:
            strategy_request: Strategy request object or dict
            
        Returns:
            Parsed strategy data
        """
        try:
            # Convert to dict if it's an object
            if hasattr(strategy_request, '__dict__'):
                strategy_data = strategy_request.__dict__
            elif hasattr(strategy_request, 'dict'):
                strategy_data = strategy_request.dict()
            else:
                strategy_data = strategy_request
            
            # Extract basic information
            parsed_data = {
                "strategy_name": strategy_data.get('name', f"Strategy_{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
                "description": strategy_data.get('description', ''),
                "timeframe": strategy_data.get('timeframe', '1d'),
                "buy_conditions": [],
                "sell_conditions": [],
                "money_management": {},
                "indicators_used": set(),
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "parser_version": "1.0.0",
                    "total_conditions": 0
                }
            }
            
            # Parse buy conditions
            buy_conditions = strategy_data.get('buy_conditions', [])
            for i, condition in enumerate(buy_conditions):
                parsed_condition = self._parse_condition(condition, f"buy_{i}")
                parsed_data["buy_conditions"].append(parsed_condition)
                
                # Collect indicators
                if parsed_condition.get('left', {}).get('indicator'):
                    parsed_data["indicators_used"].add(parsed_condition['left']['indicator'])
                if parsed_condition.get('right', {}).get('indicator'):
                    parsed_data["indicators_used"].add(parsed_condition['right']['indicator'])
            
            # Parse sell conditions
            sell_conditions = strategy_data.get('sell_conditions', [])
            for i, condition in enumerate(sell_conditions):
                parsed_condition = self._parse_condition(condition, f"sell_{i}")
                parsed_data["sell_conditions"].append(parsed_condition)
                
                # Collect indicators
                if parsed_condition.get('left', {}).get('indicator'):
                    parsed_data["indicators_used"].add(parsed_condition['left']['indicator'])
                if parsed_condition.get('right', {}).get('indicator'):
                    parsed_data["indicators_used"].add(parsed_condition['right']['indicator'])
            
            # Remove CUSTOM from indicators list and convert to list
            parsed_data["indicators_used"].discard('CUSTOM')
            parsed_data["indicators_used"] = list(parsed_data["indicators_used"])
            
            # Parse money management
            money_mgmt = strategy_data.get('money_management', {})
            parsed_data["money_management"] = {
                "position_size": money_mgmt.get('position_size', 10),
                "max_risk": money_mgmt.get('max_risk', 2),
                "profit_target": money_mgmt.get('profit_target', 5),
                "max_positions": money_mgmt.get('max_positions', 1),
                "initial_capital": money_mgmt.get('initial_capital', 100000),
                "commission": money_mgmt.get('commission', 0.001)
            }
            
            # Update metadata
            parsed_data["metadata"]["total_conditions"] = len(parsed_data["buy_conditions"]) + len(parsed_data["sell_conditions"])
            parsed_data["metadata"]["indicators_count"] = len(parsed_data["indicators_used"])
            
            logger.info(f"Strategy parsed successfully: {parsed_data['strategy_name']}")
            return parsed_data
            
        except Exception as e:
            logger.error(f"Strategy parsing error: {str(e)}")
            raise ValueError(f"Failed to parse strategy: {str(e)}")
    
    def _parse_condition(self, condition: Dict, condition_id: str) -> Dict[str, Any]:
        """Parse individual condition"""
        try:
            parsed_condition = {
                "id": condition_id,
                "type": condition.get('type', 'unknown'),
                "left": {},
                "operator": condition.get('operator', ''),
                "right": {},
                "logic": condition.get('logic', 'AND'),
                "enabled": condition.get('enabled', True)
            }
            
            # Parse left side
            left = condition.get('left', {})
            parsed_condition["left"] = {
                "indicator": left.get('indicator', ''),
                "period": left.get('period', self.supported_indicators.get(left.get('indicator', ''), {}).get('defaults', {}).get('period')),
                "timeframe": left.get('timeframe', ''),
                "source": left.get('source', 'close'),
                "parameters": left.get('parameters', {})
            }
            
            # Parse right side
            right = condition.get('right', {})
            parsed_condition["right"] = {
                "indicator": right.get('indicator', ''),
                "period": right.get('period', self.supported_indicators.get(right.get('indicator', ''), {}).get('defaults', {}).get('period')),
                "timeframe": right.get('timeframe', ''),
                "source": right.get('source', 'close'),
                "custom_value": right.get('custom_value'),
                "parameters": right.get('parameters', {})
            }
            
            # Convert operator to symbol
            parsed_condition["operator_symbol"] = self.supported_operators.get(
                parsed_condition["operator"], 
                parsed_condition["operator"]
            )
            
            return parsed_condition
            
        except Exception as e:
            logger.error(f"Condition parsing error: {str(e)}")
            raise ValueError(f"Failed to parse condition {condition_id}: {str(e)}")
    
    def get_supported_indicators(self) -> Dict[str, Any]:
        """Get list of supported indicators"""
        return self.supported_indicators.copy()
    
    def get_supported_operators(self) -> Dict[str, str]:
        """Get list of supported operators"""
        return self.supported_operators.copy()
    
    def get_supported_timeframes(self) -> List[str]:
        """Get list of supported timeframes"""
        return self.supported_timeframes.copy()
    
    def export_strategy_config(self, parsed_strategy: Dict) -> str:
        """Export strategy configuration to JSON"""
        try:
            return json.dumps(parsed_strategy, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Export error: {str(e)}")
            raise ValueError(f"Failed to export strategy: {str(e)}")
    
    def import_strategy_config(self, json_string: str) -> Dict[str, Any]:
        """Import strategy configuration from JSON"""
        try:
            strategy_data = json.loads(json_string)
            return self.parse_strategy(strategy_data)
        except Exception as e:
            logger.error(f"Import error: {str(e)}")
            raise ValueError(f"Failed to import strategy: {str(e)}")


# Helper functions
def create_default_strategy() -> Dict[str, Any]:
    """Create a default strategy configuration for testing"""
    return {
        "name": "Default RSI Strategy",
        "description": "Simple RSI-based trading strategy",
        "timeframe": "1d",
        "buy_conditions": [
            {
                "type": "buy",
                "left": {
                    "indicator": "RSI",
                    "period": 14,
                    "timeframe": "1d",
                    "source": "close"
                },
                "operator": "below",
                "right": {
                    "indicator": "CUSTOM",
                    "custom_value": 30
                },
                "logic": "AND",
                "enabled": True
            }
        ],
        "sell_conditions": [
            {
                "type": "sell",
                "left": {
                    "indicator": "RSI",
                    "period": 14,
                    "timeframe": "1d", 
                    "source": "close"
                },
                "operator": "above",
                "right": {
                    "indicator": "CUSTOM",
                    "custom_value": 70
                },
                "logic": "AND",
                "enabled": True
            }
        ],
        "money_management": {
            "position_size": 10,
            "max_risk": 2,
            "profit_target": 5,
            "max_positions": 1,
            "initial_capital": 100000,
            "commission": 0.001
        }
    }


def validate_and_parse_strategy(strategy_data: Any) -> Dict[str, Any]:
    """Convenience function to validate and parse strategy in one call"""
    parser = StrategyParser()
    
    # Validate first
    validation_result = parser.validate_strategy(strategy_data)
    if not validation_result["is_valid"]:
        raise ValueError(f"Strategy validation failed: {validation_result['errors']}")
    
    # Parse if valid
    return parser.parse_strategy(strategy_data)


# Initialize parser instance for module-level use
strategy_parser = StrategyParser()

if __name__ == "__main__":
    # Test the parser
    print("Testing Strategy Parser...")
    
    # Create and test default strategy
    default_strategy = create_default_strategy()
    
    parser = StrategyParser()
    
    # Test validation
    validation_result = parser.validate_strategy(default_strategy)
    print(f"Validation result: {validation_result}")
    
    # Test parsing
    if validation_result["is_valid"]:
        parsed_strategy = parser.parse_strategy(default_strategy)
        print(f"Parsed strategy: {parsed_strategy['strategy_name']}")
        print(f"Indicators used: {parsed_strategy['indicators_used']}")
    
    print("Strategy Parser test completed!")