"""
Core configuration settings for Strategy Builder SaaS
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # App settings
    app_name: str = "Strategy Builder SaaS"
    debug: bool = True
    app_env: str = "development"
    
    # Security settings
    secret_key: str = os.getenv("SECRET_KEY", "your-super-secret-key-change-this-in-production")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Database settings
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./strategy_builder.db")
    
    # CORS settings
    allowed_hosts: list = ["*"]
    
    class Config:
        env_file = ".env"

settings = Settings()