# create_db.py - Run this script to initialize database
from sqlalchemy import create_engine, text
from app.core.config import settings
from app.models import Base
from app.db.session import engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database():
    """Initialize database and create tables"""
    try:
        # Test connection first
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            logger.info("Database connection successful")
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
        # Verify tables exist
        with engine.connect() as connection:
            # Check if users table exists
            try:
                result = connection.execute(text("SELECT COUNT(*) FROM users"))
                count = result.fetchone()[0]
                logger.info(f"Users table exists with {count} records")
            except Exception as e:
                logger.error(f"Users table might not exist: {str(e)}")
        
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = init_database()
    if success:
        print("✅ Database initialized successfully!")
    else:
        print("❌ Database initialization failed!")
        
    # Also create a test user
    try:
        from app.db.session import get_db
        from app.crud.user import create_user, get_user_by_username
        from app.schemas.user import UserCreate
        
        db = next(get_db())
        
        # Check if test user exists
        existing_user = get_user_by_username(db, "test")
        if not existing_user:
            user_data = UserCreate(
                username="test",
                email="test@example.com", 
                password="test123"
            )
            user = create_user(db, user_data)
            print(f"✅ Test user created: {user.username}")
        else:
            print(f"✅ Test user already exists: {existing_user.username}")
            
    except Exception as e:
        print(f"❌ Test user creation failed: {str(e)}")