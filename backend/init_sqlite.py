"""
Initialize SQLite database with test users
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base_class import Base
from app.models.user import User, UserRole
from app.core.auth import get_password_hash
import os

# Get database path
db_path = os.path.join(os.path.dirname(__file__), "ai_support.db")
DATABASE_URL = f"sqlite:///{db_path}"

print(f"Creating SQLite database at: {db_path}")

# Create engine
engine = create_engine(DATABASE_URL, echo=True)

# Create all tables
print("Creating tables...")
Base.metadata.create_all(bind=engine)

# Create session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

try:
    # Check if users already exist
    existing = db.query(User).first()
    if existing:
        print("Users already exist, skipping creation")
    else:
        # Create test users
        users = [
            User(
                username="admin",
                email="admin@example.com",
                hashed_password=get_password_hash("Admin@123"),
                full_name="Admin User",
                role=UserRole.ADMIN,
                is_active=True
            ),
            User(
                username="expert",
                email="expert@example.com",
                hashed_password=get_password_hash("Expert@123"),
                full_name="Expert User",
                role=UserRole.EXPERT,
                is_active=True
            ),
            User(
                username="user",
                email="user@example.com",
                hashed_password=get_password_hash("User@123"),
                full_name="Regular User",
                role=UserRole.USER,
                is_active=True
            ),
        ]
        
        for user in users:
            db.add(user)
        
        db.commit()
        print("✅ Created 3 test users:")
        print("  - admin / Admin@123 (ADMIN)")
        print("  - expert / Expert@123 (EXPERT)")
        print("  - user / User@123 (USER)")
        
finally:
    db.close()

print(f"\n✅ SQLite database initialized at: {db_path}")
