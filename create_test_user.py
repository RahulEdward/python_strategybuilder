"""
Create a test user for login testing
"""
import sqlite3
from passlib.context import CryptContext
import traceback

try:
    print("Starting test user creation script...")
    
    # Password hashing context
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def get_password_hash(password: str) -> str:
        """Generate password hash"""
        return pwd_context.hash(password)

    print("Connecting to database...")
    # Connect to the database
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()

    # Create a test user
    username = "testuser"
    email = "testuser@example.com"
    password = "test123456"
    print(f"Generating password hash for {username}...")
    password_hash = get_password_hash(password)

    # Check if user already exists
    print("Checking if user already exists...")
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    existing_user = cursor.fetchone()

    if existing_user:
        print(f"User {username} already exists. Updating password...")
        cursor.execute(
            "UPDATE users SET password_hash = ? WHERE username = ?", 
            (password_hash, username)
        )
    else:
        print(f"Creating new user {username}...")
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, is_active, is_superuser, created_at) VALUES (?, ?, ?, ?, ?, datetime('now'))",
            (username, email, password_hash, 1, 0)
        )

    # Commit changes and close connection
    print("Committing changes to database...")
    conn.commit()
    conn.close()

    print(f"Test user created/updated successfully!")
    print(f"Username: {username}")
    print(f"Password: {password}")
    print(f"Email: {email}")
    
except Exception as e:
    print(f"Error: {str(e)}")
    print("Traceback:")
    traceback.print_exc()
