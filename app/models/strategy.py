# models/strategy.py
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from models.database import Base

class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    indicator = Column(String(100), nullable=False)
    operator = Column(String(100), nullable=False)
    value = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    target = Column(Float, nullable=False)
    capital = Column(Float, nullable=False)
    generated_code = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship with User
    user = relationship("User", back_populates="strategies")

    def __repr__(self):
        return f"<Strategy(id={self.id}, name='{self.name}', user_id={self.user_id})>"