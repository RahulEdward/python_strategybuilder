#!/usr/bin/env python3
"""
Database initialization script for PyStrategy Builder
Creates all database tables based on SQLAlchemy models
"""

from app.db.session import engine
from app.models import Base

def create_tables():
    """Create all database tables"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")

if __name__ == "__main__":
    create_tables()
