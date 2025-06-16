"""
Code Generator Service for Trading Strategy Builder
Updated to work WITHOUT TA-Lib dependency - uses pure pandas/numpy
"""

from typing import Dict, Any
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def generate_python_strategy(params: Dict[str, Any]) -> str:
    """
    Generate Python trading strategy code based on user parameters.
    Uses pure pandas/numpy implementations instead of TA-Lib.
    
    Args:
        params (Dict[str, Any]): Strategy parameters containing:
            - indicator: str (e.g., 'RSI', 'EMA', 'SMA')
            - operator: str (e.g., '>', '<', '==')
            - value: float (threshold value)
            - stop_loss: float (stop loss percentage)
            - target: float (target percentage)
            - capital: float (trading capital in INR)
            - user_id: optional user identifier
    
    Returns:
        str: Generated Python strategy code
    """
    try:
        # Extract parameters
        indicator = params.get("indicator")
        operator = params.get("operator")
        value = params.get("value")
        stop_loss = params.get("stop_loss")
        target = params.get("target")
        capital = params.get("capital")
        
        # Generate strategy name
        strategy_name = f"{indicator}_{operator.replace('>', 'GT').replace('<', 'LT').replace('==', 'EQ').replace('>=', 'GTE').replace('<=', 'LTE').replace('crosses_above', 'XUP').replace('crosses_below', 'XDOWN')}_{value}"
        
        # Generate timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Build the strategy code
        strategy_code = f'''# Trading Strategy: {strategy_name}
# Generated on: {timestamp}
# Capital: ₹{capital:,.0f}
# No external dependencies required - uses pure pandas/numpy

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

class {strategy_name.replace('-', '_')}Strategy:
    """
    Trading strategy based on {indicator} indicator
    Entry: {indicator} {operator} {value}
    Risk Management: {stop_loss}% SL, {target}% Target
    
    This strategy uses pure pandas/numpy implementations for all indicators.
    No TA-Lib dependency required.
    """
    
    def __init__(self):
        self.name = "{strategy_name}"
        self.capital = {capital}
        self.stop_loss_pct = {stop_loss}
        self.target_pct = {target}
        self.position = None
        self.entry_price = 0.0
        self.stop_loss_price = 0.0
        self.target_price = 0.0
        
    def calculate_{indicator.lower()}(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate {indicator} indicator using pure pandas/numpy"""
        {_get_indicator_calculation_no_talib(indicator)}
        
    def get_entry_signal(self, data: pd.DataFrame) -> bool:
        """
        Check if entry conditions are met
        Entry Rule: {indicator} {operator} {value}
        """
        try:
            # Calculate indicator
            indicator_values = self.calculate_{indicator.lower()}(data)
            
            if len(indicator_values) < 2 or indicator_values.isna().iloc[-1]:
                return False
                
            current_value = indicator_values.iloc[-1]
            previous_value = indicator_values.iloc[-2] if len(indicator_values) > 1 else current_value
            
            # Apply entry condition
            {_get_entry_condition_logic(operator, value)}
            
        except Exception as e:
            print(f"Error in entry signal calculation: {{e}}")
            return False
    
    def calculate_position_size(self, current_price: float) -> int:
        """Calculate position size based on available capital"""
        try:
            # Use 95% of capital for trading (keep 5% as buffer)
            available_capital = self.capital * 0.95
            position_size = int(available_capital / current_price)
            return max(1, position_size)  # Minimum 1 share
        except:
            return 1
    
    def enter_position(self, current_price: float) -> Dict[str, Any]:
        """Enter a long position"""
        try:
            position_size = self.calculate_position_size(current_price)
            self.position = "LONG"
            self.entry_price = current_price
            
            # Calculate stop loss and target prices
            self.stop_loss_price = current_price * (1 - self.stop_loss_pct / 100)
            self.target_price = current_price * (1 + self.target_pct / 100)
            
            return {{
                "action": "BUY",
                "price": current_price,
                "quantity": position_size,
                "stop_loss": self.stop_loss_price,
                "target": self.target_price,
                "timestamp": pd.Timestamp.now()
            }}
        except Exception as e:
            print(f"Error entering position: {{e}}")
            return {{"action": "ERROR", "message": str(e)}}
    
    def check_exit_conditions(self, current_price: float) -> Optional[Dict[str, Any]]:
        """Check if position should be exited"""
        if self.position != "LONG":
            return None
            
        # Check stop loss
        if current_price <= self.stop_loss_price:
            return self.exit_position(current_price, "STOP_LOSS")
        
        # Check target
        if current_price >= self.target_price:
            return self.exit_position(current_price, "TARGET")
        
        return None
    
    def exit_position(self, current_price: float, reason: str) -> Dict[str, Any]:
        """Exit current position"""
        try:
            pnl = (current_price - self.entry_price) / self.entry_price * 100
            
            result = {{
                "action": "SELL",
                "price": current_price,
                "entry_price": self.entry_price,
                "pnl_percent": round(pnl, 2),
                "reason": reason,
                "timestamp": pd.Timestamp.now()
            }}
            
            # Reset position
            self.position = None
            self.entry_price = 0.0
            self.stop_loss_price = 0.0
            self.target_price = 0.0
            
            return result
        except Exception as e:
            print(f"Error exiting position: {{e}}")
            return {{"action": "ERROR", "message": str(e)}}
    
    def process_tick(self, data: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Process new market data tick
        Returns trading signal if any
        """
        try:
            current_price = data['close'].iloc[-1]
            
            # If no position, check for entry
            if self.position is None:
                if self.get_entry_signal(data):
                    return self.enter_position(current_price)
            
            # If in position, check for exit
            else:
                exit_signal = self.check_exit_conditions(current_price)
                if exit_signal:
                    return exit_signal
                    
            return None
            
        except Exception as e:
            print(f"Error processing tick: {{e}}")
            return {{"action": "ERROR", "message": str(e)}}

    def backtest(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Run a simple backtest on historical data
        """
        trades = []
        equity_curve = [self.capital]
        current_capital = self.capital
        
        # Ensure we have enough data
        min_periods = 50
        if len(data) < min_periods:
            return {{
                "error": f"Insufficient data for backtesting. Need at least {{min_periods}} periods, got {{len(data)}}",
                "initial_capital": self.capital,
                "final_capital": self.capital,
                "total_return": 0.0,
                "total_trades": 0,
                "winning_trades": 0,
                "win_rate": 0.0
            }}
        
        for i in range(min_periods, len(data)):
            window_data = data.iloc[:i+1]
            signal = self.process_tick(window_data)
            
            if signal and signal.get("action") == "SELL":
                # Calculate P&L
                pnl_amount = current_capital * (signal["pnl_percent"] / 100)
                current_capital += pnl_amount
                trades.append(signal)
                
            equity_curve.append(current_capital)
        
        # Calculate performance metrics
        total_return = (current_capital - self.capital) / self.capital * 100
        total_trades = len(trades)
        winning_trades = len([t for t in trades if t["pnl_percent"] > 0])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        return {{
            "initial_capital": self.capital,
            "final_capital": round(current_capital, 2),
            "total_return": round(total_return, 2),
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "win_rate": round(win_rate, 2),
            "trades": trades[-5:] if trades else [],  # Last 5 trades
            "equity_curve": equity_curve[-100:] if len(equity_curve) > 100 else equity_curve  # Last 100 points
        }}


# Utility functions for technical indicators (Pure pandas/numpy implementations)
class TechnicalIndicators:
    """Pure pandas/numpy implementations of common technical indicators"""
    
    @staticmethod
    def rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def sma(prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Simple Moving Average"""
        return prices.rolling(window=period).mean()
    
    @staticmethod
    def ema(prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Exponential Moving Average"""
        return prices.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
        """Calculate MACD"""
        ema_fast = TechnicalIndicators.ema(prices, fast)
        ema_slow = TechnicalIndicators.ema(prices, slow)
        macd_line = ema_fast - ema_slow
        signal_line = TechnicalIndicators.ema(macd_line, signal)
        histogram = macd_line - signal_line
        return {{"macd": macd_line, "signal": signal_line, "histogram": histogram}}
    
    @staticmethod
    def bollinger_bands(prices: pd.Series, period: int = 20, std_dev: int = 2) -> Dict[str, pd.Series]:
        """Calculate Bollinger Bands"""
        sma = TechnicalIndicators.sma(prices, period)
        std = prices.rolling(window=period).std()
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        return {{"upper": upper_band, "middle": sma, "lower": lower_band}}
    
    @staticmethod
    def stochastic(high: pd.Series, low: pd.Series, close: pd.Series, k_period: int = 14, d_period: int = 3) -> Dict[str, pd.Series]:
        """Calculate Stochastic Oscillator"""
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()
        k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
        d_percent = k_percent.rolling(window=d_period).mean()
        return {{"k": k_percent, "d": d_percent}}
    
    @staticmethod
    def williams_r(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Williams %R"""
        highest_high = high.rolling(window=period).max()
        lowest_low = low.rolling(window=period).min()
        wr = -100 * ((highest_high - close) / (highest_high - lowest_low))
        return wr
    
    @staticmethod
    def cci(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20) -> pd.Series:
        """Calculate Commodity Channel Index"""
        typical_price = (high + low + close) / 3
        sma_tp = typical_price.rolling(window=period).mean()
        mean_deviation = typical_price.rolling(window=period).apply(lambda x: np.mean(np.abs(x - x.mean())))
        cci = (typical_price - sma_tp) / (0.015 * mean_deviation)
        return cci


# Example usage and testing
def test_strategy_with_sample_data():
    """Test the strategy with sample data"""
    # Create sample data
    dates = pd.date_range(start='2023-01-01', end='2024-01-01', freq='D')
    np.random.seed(42)  # For reproducible results
    
    # Generate realistic price data
    price_changes = np.random.normal(0, 0.02, len(dates))
    prices = [100]  # Starting price
    for change in price_changes[1:]:
        new_price = prices[-1] * (1 + change)
        prices.append(max(new_price, 1))  # Ensure price doesn't go negative
    
    # Create OHLC data
    data = pd.DataFrame({{
        'date': dates,
        'open': prices,
        'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
        'close': prices,
        'volume': np.random.randint(1000, 10000, len(dates))
    }})
    
    data.set_index('date', inplace=True)
    
    return data

# Quick test function
if __name__ == "__main__":
    print("Testing Strategy Builder with Sample Data...")
    
    # Test parameters
    test_params = {{
        "indicator": "RSI",
        "operator": "<",
        "value": 30,
        "stop_loss": 2.0,
        "target": 5.0,
        "capital": 100000
    }}
    
    # Generate strategy
    strategy_code = generate_python_strategy(test_params)
    print("Strategy code generated successfully!")
    print(f"Code length: {{len(strategy_code)}} characters")
    
    # Test with sample data
    sample_data = test_strategy_with_sample_data()
    print(f"Sample data created: {{len(sample_data)}} days")
    print("Sample data columns:", list(sample_data.columns))
    print("Sample data head:")
    print(sample_data.head())
'''

        logger.info(f"Successfully generated strategy code for {indicator} strategy (no TA-Lib)")
        return strategy_code
        
    except Exception as e:
        logger.error(f"Error generating strategy code: {str(e)}")
        return f"# Error generating strategy code: {str(e)}\n# Please check your inputs and try again."


def _get_indicator_calculation_no_talib(indicator: str) -> str:
    """Generate indicator calculation code using pure pandas/numpy"""
    calculations = {
        "RSI": '''try:
            close = data['close']
            return TechnicalIndicators.rsi(close, period)
        except Exception as e:
            print(f"Error calculating RSI: {e}")
            return pd.Series([50] * len(data), index=data.index)''',
        
        "EMA": '''try:
            close = data['close']
            return TechnicalIndicators.ema(close, period)
        except Exception as e:
            print(f"Error calculating EMA: {e}")
            return pd.Series([0] * len(data), index=data.index)''',
        
        "SMA": '''try:
            close = data['close']
            return TechnicalIndicators.sma(close, period)
        except Exception as e:
            print(f"Error calculating SMA: {e}")
            return pd.Series([0] * len(data), index=data.index)''',
        
        "MACD": '''try:
            close = data['close']
            macd_data = TechnicalIndicators.macd(close)
            return macd_data["macd"]
        except Exception as e:
            print(f"Error calculating MACD: {e}")
            return pd.Series([0] * len(data), index=data.index)''',
        
        "Bollinger_Bands": '''try:
            close = data['close']
            bb_data = TechnicalIndicators.bollinger_bands(close, period)
            return bb_data["middle"]  # Return middle band (SMA)
        except Exception as e:
            print(f"Error calculating Bollinger Bands: {e}")
            return pd.Series([0] * len(data), index=data.index)''',
        
        "Stochastic": '''try:
            high = data['high']
            low = data['low']
            close = data['close']
            stoch_data = TechnicalIndicators.stochastic(high, low, close, period)
            return stoch_data["k"]
        except Exception as e:
            print(f"Error calculating Stochastic: {e}")
            return pd.Series([50] * len(data), index=data.index)''',
        
        "Williams_R": '''try:
            high = data['high']
            low = data['low']
            close = data['close']
            return TechnicalIndicators.williams_r(high, low, close, period)
        except Exception as e:
            print(f"Error calculating Williams %R: {e}")
            return pd.Series([-50] * len(data), index=data.index)''',
        
        "CCI": '''try:
            high = data['high']
            low = data['low']
            close = data['close']
            return TechnicalIndicators.cci(high, low, close, period)
        except Exception as e:
            print(f"Error calculating CCI: {e}")
            return pd.Series([0] * len(data), index=data.index)'''
    }
    
    return calculations.get(indicator, '''try:
            close = data['close']
            return TechnicalIndicators.sma(close, period)
        except Exception as e:
            print(f"Error calculating indicator: {e}")
            return pd.Series([0] * len(data), index=data.index)''')


def _get_entry_condition_logic(operator: str, value: float) -> str:
    """Generate entry condition logic based on operator"""
    conditions = {
        ">": f"return current_value > {value}",
        "<": f"return current_value < {value}",
        "==": f"return abs(current_value - {value}) < 0.01",  # Use small tolerance for float comparison
        ">=": f"return current_value >= {value}",
        "<=": f"return current_value <= {value}",
        "crosses_above": f"return previous_value <= {value} and current_value > {value}",
        "crosses_below": f"return previous_value >= {value} and current_value < {value}"
    }
    
    return conditions.get(operator, f"return current_value > {value}")