# models/strategy.py
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from models.database import Base
from typing import Dict, Any, List, Optional
from datetime import datetime

class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Legacy fields (for backward compatibility)
    indicator = Column(String(100), nullable=True)  # Made nullable for new strategies
    operator = Column(String(100), nullable=True)   # Made nullable for new strategies
    value = Column(Float, nullable=True)             # Made nullable for new strategies
    stop_loss = Column(Float, nullable=True)         # Made nullable for new strategies
    target = Column(Float, nullable=True)            # Made nullable for new strategies
    capital = Column(Float, nullable=False)
    generated_code = Column(Text, nullable=False)
    
    # New fields for advanced strategy builder
    timeframe = Column(String(10), default="1d")
    buy_conditions = Column(JSON, default=list)     # Store array of buy conditions
    sell_conditions = Column(JSON, default=list)    # Store array of sell conditions
    money_management = Column(JSON, default=dict)   # Store money management settings
    indicators_used = Column(JSON, default=list)    # Store list of indicators used
    
    # Strategy metadata
    strategy_type = Column(String(50), default="custom")  # "simple", "advanced", "custom"
    is_active = Column(Boolean, default=True)
    is_backtested = Column(Boolean, default=False)
    
    # Performance metrics (populated after backtesting)
    total_return = Column(Float, nullable=True)
    total_trades = Column(Integer, nullable=True)
    winning_trades = Column(Integer, nullable=True)
    win_rate = Column(Float, nullable=True)
    sharpe_ratio = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="strategies")
    backtest_results = relationship("BacktestResult", back_populates="strategy", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Strategy(id={self.id}, name='{self.name}', user_id={self.user_id}, type='{self.strategy_type}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert strategy to dictionary"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "timeframe": self.timeframe,
            "strategy_type": self.strategy_type,
            "is_active": self.is_active,
            "is_backtested": self.is_backtested,
            
            # Legacy fields
            "legacy_config": {
                "indicator": self.indicator,
                "operator": self.operator,
                "value": self.value,
                "stop_loss": self.stop_loss,
                "target": self.target,
                "capital": self.capital
            },
            
            # New advanced fields
            "buy_conditions": self.buy_conditions or [],
            "sell_conditions": self.sell_conditions or [],
            "money_management": self.money_management or {},
            "indicators_used": self.indicators_used or [],
            
            # Performance metrics
            "performance": {
                "total_return": self.total_return,
                "total_trades": self.total_trades,
                "winning_trades": self.winning_trades,
                "win_rate": self.win_rate,
                "sharpe_ratio": self.sharpe_ratio,
                "max_drawdown": self.max_drawdown
            },
            
            # Metadata
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "generated_code": self.generated_code
        }
    
    @classmethod
    def create_simple_strategy(cls, user_id: int, name: str, description: str, 
                              indicator: str, operator: str, value: float,
                              stop_loss: float, target: float, capital: float,
                              generated_code: str) -> "Strategy":
        """Create a simple strategy (legacy format)"""
        return cls(
            user_id=user_id,
            name=name,
            description=description,
            indicator=indicator,
            operator=operator,
            value=value,
            stop_loss=stop_loss,
            target=target,
            capital=capital,
            generated_code=generated_code,
            strategy_type="simple",
            timeframe="1d",
            buy_conditions=[],
            sell_conditions=[],
            money_management={"position_size": 10, "max_risk": 2, "max_positions": 1},
            indicators_used=[indicator] if indicator else []
        )
    
    @classmethod
    def create_advanced_strategy(cls, user_id: int, name: str, description: str,
                               timeframe: str, buy_conditions: List[Dict],
                               sell_conditions: List[Dict], money_management: Dict,
                               indicators_used: List[str], generated_code: str,
                               capital: float = 100000) -> "Strategy":
        """Create an advanced strategy (new format)"""
        return cls(
            user_id=user_id,
            name=name,
            description=description,
            timeframe=timeframe,
            buy_conditions=buy_conditions,
            sell_conditions=sell_conditions,
            money_management=money_management,
            indicators_used=indicators_used,
            generated_code=generated_code,
            strategy_type="advanced",
            capital=capital,
            # Legacy fields set to None for advanced strategies
            indicator=None,
            operator=None,
            value=None,
            stop_loss=money_management.get("max_risk", 2.0),
            target=money_management.get("profit_target", 5.0)
        )
    
    def update_performance(self, backtest_results: Dict[str, Any]):
        """Update strategy performance metrics from backtest results"""
        self.total_return = backtest_results.get("total_return")
        self.total_trades = backtest_results.get("total_trades")
        self.winning_trades = backtest_results.get("winning_trades")
        self.win_rate = backtest_results.get("win_rate")
        self.sharpe_ratio = backtest_results.get("sharpe_ratio")
        self.max_drawdown = backtest_results.get("max_drawdown")
        self.is_backtested = True
    
    def is_legacy_strategy(self) -> bool:
        """Check if this is a legacy simple strategy"""
        return self.strategy_type == "simple" or (
            self.indicator is not None and 
            self.operator is not None and 
            self.value is not None
        )
    
    def get_conditions_summary(self) -> Dict[str, Any]:
        """Get a summary of strategy conditions"""
        if self.is_legacy_strategy():
            return {
                "type": "simple",
                "condition": f"{self.indicator} {self.operator} {self.value}",
                "stop_loss": self.stop_loss,
                "target": self.target
            }
        else:
            return {
                "type": "advanced",
                "buy_conditions_count": len(self.buy_conditions or []),
                "sell_conditions_count": len(self.sell_conditions or []),
                "indicators_used": self.indicators_used or [],
                "timeframe": self.timeframe
            }


class BacktestResult(Base):
    """Database model for storing detailed backtest results"""
    __tablename__ = "backtest_results"
    
    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=False)
    
    # Backtest Configuration
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    initial_capital = Column(Float, default=100000)
    symbol = Column(String(20), default="SPY")  # Asset symbol used for backtesting
    
    # Results Summary
    final_capital = Column(Float, nullable=False)
    total_return = Column(Float, nullable=False)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0)
    
    # Risk Metrics
    sharpe_ratio = Column(Float, default=0)
    max_drawdown = Column(Float, default=0)
    volatility = Column(Float, nullable=True)
    
    # Detailed Data (stored as JSON)
    trades = Column(JSON, default=list)           # Individual trade records
    equity_curve = Column(JSON, default=list)     # Daily equity values
    monthly_returns = Column(JSON, default=dict)  # Monthly return breakdown
    
    # Benchmark Comparison
    benchmark_return = Column(Float, nullable=True)  # Buy and hold return
    alpha = Column(Float, nullable=True)             # Excess return vs benchmark
    beta = Column(Float, nullable=True)              # Beta vs benchmark
    
    # Metadata
    backtest_duration_seconds = Column(Float, nullable=True)
    data_points_used = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    strategy = relationship("Strategy", back_populates="backtest_results")
    
    def __repr__(self):
        return f"<BacktestResult(id={self.id}, strategy_id={self.strategy_id}, return={self.total_return:.2%})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert backtest result to dictionary"""
        return {
            "id": self.id,
            "strategy_id": self.strategy_id,
            "configuration": {
                "start_date": self.start_date.isoformat() if self.start_date else None,
                "end_date": self.end_date.isoformat() if self.end_date else None,
                "initial_capital": self.initial_capital,
                "symbol": self.symbol
            },
            "summary": {
                "final_capital": self.final_capital,
                "total_return": self.total_return,
                "total_trades": self.total_trades,
                "winning_trades": self.winning_trades,
                "losing_trades": self.losing_trades,
                "win_rate": self.win_rate
            },
            "risk_metrics": {
                "sharpe_ratio": self.sharpe_ratio,
                "max_drawdown": self.max_drawdown,
                "volatility": self.volatility
            },
            "benchmark": {
                "benchmark_return": self.benchmark_return,
                "alpha": self.alpha,
                "beta": self.beta
            },
            "detailed_data": {
                "trades": self.trades,
                "equity_curve": self.equity_curve,
                "monthly_returns": self.monthly_returns
            },
            "metadata": {
                "backtest_duration_seconds": self.backtest_duration_seconds,
                "data_points_used": self.data_points_used,
                "created_at": self.created_at.isoformat() if self.created_at else None
            }
        }


class StrategyTemplate(Base):
    """Database model for storing reusable strategy templates"""
    __tablename__ = "strategy_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)  # e.g., "trend_following", "mean_reversion", "momentum"
    
    # Template Configuration
    template_config = Column(JSON, nullable=False)  # Store the condition template
    default_parameters = Column(JSON, default=dict)  # Default parameter values
    
    # Usage Statistics
    usage_count = Column(Integer, default=0)
    avg_performance = Column(Float, nullable=True)  # Average performance of strategies using this template
    
    # Metadata
    is_public = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<StrategyTemplate(id={self.id}, name='{self.name}', category='{self.category}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "template_config": self.template_config,
            "default_parameters": self.default_parameters,
            "statistics": {
                "usage_count": self.usage_count,
                "avg_performance": self.avg_performance
            },
            "metadata": {
                "is_public": self.is_public,
                "created_by": self.created_by,
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None
            }
        }
    
    def increment_usage(self):
        """Increment the usage count when this template is used"""
        self.usage_count += 1


# Migration helper functions for upgrading existing strategies
def migrate_legacy_strategy_to_advanced(strategy: Strategy) -> Dict[str, Any]:
    """Convert legacy strategy format to new advanced format"""
    if not strategy.is_legacy_strategy():
        return strategy.to_dict()
    
    # Convert legacy single condition to new format
    buy_condition = {
        "type": "buy",
        "left": {
            "indicator": strategy.indicator,
            "period": 14,  # Default period
            "timeframe": strategy.timeframe or "1d",
            "source": "close"
        },
        "operator": strategy.operator.lower(),
        "right": {
            "indicator": "CUSTOM",
            "custom_value": strategy.value
        }
    }
    
    # Create sell conditions based on stop loss and target
    sell_conditions = []
    if strategy.stop_loss:
        sell_conditions.append({
            "type": "sell",
            "condition": "stop_loss",
            "value": strategy.stop_loss
        })
    
    if strategy.target:
        sell_conditions.append({
            "type": "sell", 
            "condition": "profit_target",
            "value": strategy.target
        })
    
    return {
        "buy_conditions": [buy_condition],
        "sell_conditions": sell_conditions,
        "money_management": {
            "position_size": 10,
            "max_risk": strategy.stop_loss or 2,
            "profit_target": strategy.target or 5,
            "max_positions": 1
        },
        "indicators_used": [strategy.indicator] if strategy.indicator else []
    }


def get_strategy_statistics(user_id: int = None) -> Dict[str, Any]:
    """Get statistics about strategies (for dashboard)"""
    from sqlalchemy.orm import sessionmaker
    from models.database import engine
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        query = session.query(Strategy)
        if user_id:
            query = query.filter(Strategy.user_id == user_id)
        
        strategies = query.all()
        
        total_strategies = len(strategies)
        active_strategies = len([s for s in strategies if s.is_active])
        backtested_strategies = len([s for s in strategies if s.is_backtested])
        
        # Performance statistics
        profitable_strategies = len([
            s for s in strategies 
            if s.total_return is not None and s.total_return > 0
        ])
        
        avg_return = None
        if backtested_strategies > 0:
            returns = [s.total_return for s in strategies if s.total_return is not None]
            avg_return = sum(returns) / len(returns) if returns else 0
        
        return {
            "total_strategies": total_strategies,
            "active_strategies": active_strategies,
            "backtested_strategies": backtested_strategies,
            "profitable_strategies": profitable_strategies,
            "avg_return": avg_return,
            "success_rate": profitable_strategies / backtested_strategies if backtested_strategies > 0 else 0
        }
    
    finally:
        session.close()