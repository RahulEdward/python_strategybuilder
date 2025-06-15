# update_user_table_simple.py - Simple SQLite fix
"""
Simple script to add missing columns to SQLite users table
"""
import sqlite3
import os
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def find_database_file():
    """Find the SQLite database file"""
    possible_files = [
        "app.db",
        "sqlite.db", 
        "database.db",
        "strategy_builder.db",
        "app/app.db",
        "app/database.db"
    ]
    
    for file_path in possible_files:
        if os.path.exists(file_path):
            logger.info(f"Found database file: {file_path}")
            return file_path
    
    logger.error("Could not find database file!")
    logger.info("Please specify your database file name:")
    logger.info("Available files in current directory:")
    for file in os.listdir("."):
        if file.endswith(".db"):
            logger.info(f"  - {file}")
    
    return None

def update_user_table_simple():
    """Simple update for SQLite users table"""
    
    # Find database file
    db_file = find_database_file()
    if not db_file:
        db_file = input("Enter your database file path: ").strip()
        if not os.path.exists(db_file):
            logger.error(f"File {db_file} not found!")
            return False
    
    try:
        # Connect to SQLite database
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        logger.info(f"Connected to database: {db_file}")
        
        # Check if users table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='users'
        """)
        
        if not cursor.fetchone():
            logger.error("Users table not found!")
            return False
        
        logger.info("✅ Users table found")
        
        # Get current table structure
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        logger.info("📋 Current columns:")
        for col in columns:
            logger.info(f"  - {col[1]} ({col[2]})")
        
        # Add missing columns one by one
        columns_to_add = [
            ("is_active", "BOOLEAN DEFAULT 1 NOT NULL"),
            ("is_superuser", "BOOLEAN DEFAULT 0 NOT NULL"), 
            ("last_login", "DATETIME NULL"),
            ("updated_at", "DATETIME NULL"),
            ("created_at", "DATETIME DEFAULT CURRENT_TIMESTAMP")
        ]
        
        for col_name, col_definition in columns_to_add:
            if col_name not in column_names:
                try:
                    query = f"ALTER TABLE users ADD COLUMN {col_name} {col_definition}"
                    logger.info(f"Adding column: {col_name}")
                    cursor.execute(query)
                    logger.info(f"✅ Added {col_name} column successfully")
                except Exception as e:
                    logger.warning(f"⚠️ Could not add {col_name}: {str(e)}")
            else:
                logger.info(f"✅ Column {col_name} already exists")
        
        # Update existing users
        logger.info("Updating existing user data...")
        
        # Set all users as active
        cursor.execute("UPDATE users SET is_active = 1 WHERE is_active IS NULL")
        updated_active = cursor.rowcount
        logger.info(f"✅ Set {updated_active} users as active")
        
        # Set all users as non-superuser
        cursor.execute("UPDATE users SET is_superuser = 0 WHERE is_superuser IS NULL")
        updated_super = cursor.rowcount
        logger.info(f"✅ Set {updated_super} users as non-superuser")
        
        # Set created_at for existing users if NULL
        cursor.execute("UPDATE users SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
        updated_created = cursor.rowcount
        logger.info(f"✅ Set created_at for {updated_created} users")
        
        # Commit changes
        conn.commit()
        
        # Verify changes
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        logger.info(f"📊 Total users in database: {total_users}")
        
        # Show sample data
        cursor.execute("SELECT id, username, email, is_active, is_superuser, created_at FROM users LIMIT 3")
        sample_users = cursor.fetchall()
        
        logger.info("📋 Sample user data:")
        for user in sample_users:
            logger.info(f"  User {user[0]}: {user[1]} | Active: {user[3]} | Super: {user[4]} | Created: {user[5]}")
        
        # Close connection
        conn.close()
        
        logger.info("🎉 Database update completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database update failed: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("🚀 Starting simple SQLite database update...")
    
    success = update_user_table_simple()
    
    if success:
        logger.info("✅ Update completed! You can now restart your FastAPI server.")
        logger.info("💡 Your login should now work without errors.")
    else:
        logger.error("❌ Update failed. Please check the error messages above.")
        logger.info("💡 Alternative: You can manually add the columns using SQLite browser.")
        
    input("Press Enter to exit...")