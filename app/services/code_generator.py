# services/code_generator.py
from typing import Dict, Any

def generate_strategy_code(strategy_data: Dict[str, Any]) -> str:
    """
    Generate Python trading strategy code based on user parameters
    """
    name = strategy_data.get('name', 'My Strategy')
    indicator = strategy_data.get('indicator')
    operator = strategy_data.get('operator')
    value = strategy_data.get('value')
    stop_loss = strategy_data.get('stop_loss')
    target = strategy_data.get('target')
    capital = strategy_data.get('capital')
    
    # Operator mapping for readable code
    operator_map = {
        'greater_than': '>',
        'less_than': '<',
        'crosses_above': 'crosses above',
        'crosses_below': 'crosses below',
        'equals': '=='
    }
    
    # Indicator-specific code generation
    indicator_code = generate_indicator_code(indicator, operator, value)
    
    code_template = f'''
# {name} - Auto-generated Trading Strategy
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

class {name.replace(' ', '').replace('-', '_')}Strategy:
    def __init__(self):
        self.capital = {capital}
        self.stop_loss_pct = {stop_loss}
        self.target_pct = {target}
        self.position = None
        self.entry_price = None
        
    def calculate_indicators(self, data):
        """Calculate technical indicators"""
        df = data.copy()
        
{indicator_code}
        
        return df
    
    def generate_signals(self, data):
        """Generate buy/sell signals based on strategy logic"""
        df = self.calculate_indicators(data)
        df['signal'] = 0
        
        # Strategy logic: {indicator} {operator_map.get(operator, operator)} {value}
{generate_signal_logic(indicator, operator, value)}
        
        return df
    
    def calculate_position_size(self, price):
        """Calculate position size based on available capital"""
        return int(self.capital / price)
    
    def execute_strategy(self, symbol, period='1y'):
        """Execute the complete trading strategy"""
        # Download historical data
        data = yf.download(symbol, period=period)
        
        # Generate signals
        df = self.generate_signals(data)
        
        # Backtest the strategy
        return self.backtest(df)
    
    def backtest(self, data):
        """Backtest the strategy and calculate returns"""
        portfolio_value = self.capital
        trades = []
        position = 0
        
        for i in range(1, len(data)):
            current_price = data['Close'].iloc[i]
            signal = data['signal'].iloc[i]
            
            # Buy signal
            if signal == 1 and position == 0:
                position = self.calculate_position_size(current_price)
                entry_price = current_price
                trades.append({{
                    'type': 'BUY',
                    'price': current_price,
                    'quantity': position,
                    'date': data.index[i]
                }})
            
            # Sell signal or stop loss/target
            elif signal == -1 and position > 0:
                exit_price = current_price
                profit_loss = (exit_price - entry_price) * position
                portfolio_value += profit_loss
                
                trades.append({{
                    'type': 'SELL',
                    'price': current_price,
                    'quantity': position,
                    'profit_loss': profit_loss,
                    'date': data.index[i]
                }})
                position = 0
            
            # Check stop loss and target
            elif position > 0:
                profit_pct = (current_price - entry_price) / entry_price * 100
                
                if profit_pct <= -self.stop_loss_pct or profit_pct >= self.target_pct:
                    exit_price = current_price
                    profit_loss = (exit_price - entry_price) * position
                    portfolio_value += profit_loss
                    
                    trades.append({{
                        'type': 'SELL (AUTO)',
                        'price': current_price,
                        'quantity': position,
                        'profit_loss': profit_loss,
                        'reason': 'Stop Loss' if profit_pct <= -self.stop_loss_pct else 'Target Hit',
                        'date': data.index[i]
                    }})
                    position = 0
        
        return {{
            'final_portfolio_value': portfolio_value,
            'total_return': portfolio_value - self.capital,
            'return_percentage': ((portfolio_value - self.capital) / self.capital) * 100,
            'total_trades': len(trades),
            'trades': trades
        }}

# Example usage:
if __name__ == "__main__":
    strategy = {name.replace(' ', '').replace('-', '_')}Strategy()
    
    # Test with a sample stock
    results = strategy.execute_strategy('AAPL', period='6mo')
    
    print(f"Strategy: {name}")
    print(f"Initial Capital: ${strategy.capital:,.2f}")
    print(f"Final Portfolio Value: ${results['final_portfolio_value']:,.2f}")
    print(f"Total Return: ${results['total_return']:,.2f}")
    print(f"Return Percentage: {results['return_percentage']:.2f}%")
    print(f"Total Trades: {{results['total_trades']}}")
'''
    
    return code_template.strip()

def generate_indicator_code(indicator: str, operator: str, value: float) -> str:
    """Generate indicator-specific calculation code"""
    if indicator == "RSI":
        return f'''        # RSI Calculation
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))'''
        
    elif indicator == "SMA":
        period = int(value) if operator in ['crosses_above', 'crosses_below'] else 20
        return f'''        # Simple Moving Average
        df['SMA_{period}'] = df['Close'].rolling(window={period}).mean()'''
        
    elif indicator == "EMA":
        period = int(value) if operator in ['crosses_above', 'crosses_below'] else 20
        return f'''        # Exponential Moving Average
        df['EMA_{period}'] = df['Close'].ewm(span={period}).mean()'''
        
    elif indicator == "MACD":
        return f'''        # MACD Calculation
        exp1 = df['Close'].ewm(span=12).mean()
        exp2 = df['Close'].ewm(span=26).mean()
        df['MACD'] = exp1 - exp2
        df['MACD_signal'] = df['MACD'].ewm(span=9).mean()
        df['MACD_histogram'] = df['MACD'] - df['MACD_signal']'''
        
    elif indicator == "Bollinger Bands":
        return f'''        # Bollinger Bands
        df['BB_middle'] = df['Close'].rolling(window=20).mean()
        df['BB_std'] = df['Close'].rolling(window=20).std()
        df['BB_upper'] = df['BB_middle'] + (df['BB_std'] * 2)
        df['BB_lower'] = df['BB_middle'] - (df['BB_std'] * 2)'''
        
    else:
        return f"        # {indicator} calculation code here"

def generate_signal_logic(indicator: str, operator: str, value: float) -> str:
    """Generate signal logic based on indicator and operator"""
    if indicator == "RSI":
        if operator == "greater_than":
            return f'''        # Buy when RSI > {value}
        df.loc[df['RSI'] > {value}, 'signal'] = 1
        # Sell when RSI < {value}
        df.loc[df['RSI'] < {value}, 'signal'] = -1'''
        elif operator == "less_than":
            return f'''        # Buy when RSI < {value}
        df.loc[df['RSI'] < {value}, 'signal'] = 1
        # Sell when RSI > {value}
        df.loc[df['RSI'] > {value}, 'signal'] = -1'''
            
    elif indicator in ["SMA", "EMA"]:
        period = int(value) if operator in ['crosses_above', 'crosses_below'] else 20
        col_name = f"{indicator}_{period}"
        
        if operator == "crosses_above":
            return f'''        # Buy when price crosses above {indicator}
        df.loc[(df['Close'] > df['{col_name}']) & (df['Close'].shift(1) <= df['{col_name}'].shift(1)), 'signal'] = 1'''
        elif operator == "crosses_below":
            return f'''        # Sell when price crosses below {indicator}
        df.loc[(df['Close'] < df['{col_name}']) & (df['Close'].shift(1) >= df['{col_name}'].shift(1)), 'signal'] = -1'''
    
    elif indicator == "MACD":
        if operator == "crosses_above":
            return f'''        # Buy when MACD crosses above signal line
        df.loc[(df['MACD'] > df['MACD_signal']) & (df['MACD'].shift(1) <= df['MACD_signal'].shift(1)), 'signal'] = 1'''
        elif operator == "crosses_below":
            return f'''        # Sell when MACD crosses below signal line
        df.loc[(df['MACD'] < df['MACD_signal']) & (df['MACD'].shift(1) >= df['MACD_signal'].shift(1)), 'signal'] = -1'''
    
    return f"        # Signal logic for {indicator} {operator} {value}"