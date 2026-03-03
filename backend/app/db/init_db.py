"""
Database initialization script
Creates tables and default admin user
"""
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base_class import Base
from app.models.user import User, UserRole, ChatConversation, ChatMessage
from app.core.auth import get_password_hash
from app.core.config import settings

# Import all models to ensure they're registered
from app.models.user import User


def init_db():
    """Initialize database with tables and default admin"""
    # Create engine
    engine = create_engine(settings.db_url)
    
    # Create all tables
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ Tables created successfully")
    
    # Create session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Check if admin exists
        admin = db.query(User).filter(User.username == "admin").first()
        
        if not admin:
            print("\nCreating default admin user...")
            admin = User(
                username="admin",
                email="admin@support-ai.local",
                full_name="System Administrator",
                hashed_password=get_password_hash("Admin@123"),
                role=UserRole.ADMIN,
                is_active=True
            )
            db.add(admin)
            db.commit()
            print("✓ Default admin user created")
            print("\n" + "="*60)
            print("DEFAULT ADMIN CREDENTIALS")
            print("="*60)
            print("Username: admin")
            print("Password: Admin@123")
            print("\n⚠️  IMPORTANT: Change this password after first login!")
            print("="*60 + "\n")
        else:
            print("\n✓ Admin user already exists")
        
        # Create a test expert user
        expert = db.query(User).filter(User.username == "expert").first()
        if not expert:
            print("Creating test expert user...")
            expert = User(
                username="expert",
                email="expert@support-ai.local",
                full_name="Test Expert",
                hashed_password=get_password_hash("Expert@123"),
                role=UserRole.EXPERT,
                is_active=True
            )
            db.add(expert)
            db.commit()
            print("✓ Test expert user created (username: expert, password: Expert@123)")
        
        # Create a test user
        user = db.query(User).filter(User.username == "user").first()
        if not user:
            print("Creating test user...")
            user = User(
                username="user",
                email="user@support-ai.local",
                full_name="Test User",
                hashed_password=get_password_hash("User@123"),
                role=UserRole.USER,
                is_active=True
            )
            db.add(user)
            db.commit()
            print("✓ Test user created (username: user, password: User@123)")
        
        print("\n✅ Database initialization complete!")
        
    except Exception as e:
        print(f"\n❌ Error during initialization: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("🚀 Initializing AI Support Agent Database...\n")
    init_db()
