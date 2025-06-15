# crud/strategy.py
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from models.strategy import Strategy
from schemas.strategy import StrategyCreate, StrategyUpdate

class StrategyCRUD:
    def get_strategy_by_id(self, db: Session, strategy_id: int) -> Optional[Strategy]:
        """Get a strategy by its ID"""
        return db.query(Strategy).filter(Strategy.id == strategy_id).first()
    
    def get_user_strategies(self, db: Session, user_id: int) -> List[Strategy]:
        """Get all strategies belonging to a user"""
        return db.query(Strategy).filter(Strategy.user_id == user_id).order_by(Strategy.created_at.desc()).all()
    
    def get_strategy_by_user(self, db: Session, strategy_id: int, user_id: int) -> Optional[Strategy]:
        """Get a strategy by ID that belongs to a specific user"""
        return db.query(Strategy).filter(
            Strategy.id == strategy_id,
            Strategy.user_id == user_id
        ).first()
    
    def create_strategy(self, db: Session, strategy: StrategyCreate, user_id: int) -> Strategy:
        """Create a new strategy"""
        db_strategy = Strategy(
            user_id=user_id,
            name=strategy.name,
            description=strategy.description,
            indicator=strategy.indicator,
            operator=strategy.operator,
            value=strategy.value,
            stop_loss=strategy.stop_loss,
            target=strategy.target,
            capital=strategy.capital,
            generated_code=strategy.generated_code
        )
        db.add(db_strategy)
        db.commit()
        db.refresh(db_strategy)
        return db_strategy
    
    def update_strategy(self, db: Session, strategy_id: int, strategy_data: Dict[str, Any]) -> Optional[Strategy]:
        """Update an existing strategy"""
        db_strategy = self.get_strategy_by_id(db, strategy_id)
        if not db_strategy:
            return None
        
        # Update fields
        for field, value in strategy_data.items():
            if hasattr(db_strategy, field):
                setattr(db_strategy, field, value)
        
        db.commit()
        db.refresh(db_strategy)
        return db_strategy
    
    def delete_strategy(self, db: Session, strategy_id: int) -> bool:
        """Delete a strategy"""
        db_strategy = self.get_strategy_by_id(db, strategy_id)
        if not db_strategy:
            return False
        
        db.delete(db_strategy)
        db.commit()
        return True
    
    def get_strategies_count(self, db: Session, user_id: int) -> int:
        """Get total count of strategies for a user"""
        return db.query(Strategy).filter(Strategy.user_id == user_id).count()
    
    def search_strategies(self, db: Session, user_id: int, search_term: str) -> List[Strategy]:
        """Search strategies by name or description"""
        return db.query(Strategy).filter(
            Strategy.user_id == user_id,
            (Strategy.name.ilike(f"%{search_term}%") | 
             Strategy.description.ilike(f"%{search_term}%"))
        ).order_by(Strategy.created_at.desc()).all()

# Create instance to be imported
strategy_crud = StrategyCRUD()