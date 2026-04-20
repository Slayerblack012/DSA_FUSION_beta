"""
Initialize Database
Run: python app/utils/init_db.py
"""
import sys
import os
import sqlite3
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.models.models import Base
from app.core.config import DB_FILE
from app.utils.auth import hash_password
from sqlalchemy import create_engine, inspect

print("=" * 60)
print("DATABASE INITIALIZATION")
print("=" * 60)

print(f"\nDatabase path: {DB_FILE}")

# Create engine
engine = create_engine(f"sqlite:///{DB_FILE}")

# Check if tables exist
inspector = inspect(engine)
tables = inspector.get_table_names()
print(f"Existing tables: {tables}")

# Create tables if not exist
print("\nCreating tables...")
Base.metadata.create_all(bind=engine)
print("[OK] Tables created/verified")

# Check if users table is empty
# Check if users table is empty
conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM users")
user_count = cursor.fetchone()[0]
print(f"\nCurrent users: {user_count}")

if user_count == 0:
    print("\nCreating demo users...")

    # Student user
    student_hash = hash_password("sv123")
    cursor.execute("""
        INSERT INTO users (username, password_hash, full_name, role)
        VALUES (?, ?, ?, ?)
    """, ("122000001", student_hash, "Student Nguyen Van A", "STUDENT"))
    
    conn.commit()
    print("[OK] Demo users created:")
    print("    - 122000001 / sv123 (STUDENT)")
else:
    print("\n[OK] Users already exist")
    cursor.execute("SELECT username, role FROM users")
    users = cursor.fetchall()
    for user in users:
        print(f"    - {user[0]} ({user[1]})")

conn.close()

print("\n" + "=" * 60)
print("DATABASE READY")
print("=" * 60)
print("\nYou can now start the server: python main.py")
