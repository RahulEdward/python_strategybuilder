import sqlite3

# Connect to the database
conn = sqlite3.connect('app.db')
cursor = conn.cursor()

# Get list of tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("Tables in the database:")
for table in tables:
    print(f"- {table[0]}")

# Check users table structure if it exists
if ('users',) in tables:
    print("\nUsers table structure:")
    cursor.execute("PRAGMA table_info(users)")
    columns = cursor.fetchall()
    for col in columns:
        print(f"- {col[1]} ({col[2]})")

# Close connection
conn.close()
