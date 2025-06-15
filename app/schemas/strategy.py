# schemas/strategy.py
from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime

class StrategyBase(BaseModel):
    name: str
    description: Optional[str] = None
    indicator: str
    operator: str
    value: float
    stop_loss: float
    target: float
    capital: float

    @validator('stop_loss')
    def validate_stop_loss(cls, v):
        if v < 0 or v > 100:
            raise ValueError('Stop loss must be between 0 and 100')
        return v
    
    @validator('target')
    def validate_target(cls, v):
        if v <= 0:
            raise ValueError('Target must be greater than 0')
        return v
    
    @validator('capital')
    def validate_capital(cls, v):
        if v <= 0:
            raise ValueError('Capital must be greater than 0')
        return v

class StrategyCreate(StrategyBase):
    generated_code: str

class StrategyUpdate(StrategyBase):
    pass

class StrategyResponse(StrategyBase):
    id: int
    user_id: int
    generated_code: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True