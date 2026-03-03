#!/usr/bin/env python3
"""
Réinitialiser le mot de passe admin via PostgreSQL
"""
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.user import User
from app.models.refresh_token import RefreshToken, RevokedToken  # Import pour résoudre les relationships
from app.core.security import get_password_hash

# Direct PostgreSQL URL
DB_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/ai_support_agent"

def reset_admin_password(new_password: str):
    """Reset admin password"""
    engine = create_engine(DB_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Find admin user
        admin = db.query(User).filter(User.username == "admin").first()
        
        if not admin:
            print("❌ Utilisateur 'admin' introuvable")
            return False
        
        # Update password
        admin.hashed_password = get_password_hash(new_password)
        db.commit()
        
        print(f"✅ Mot de passe admin mis à jour avec succès!")
        print(f"   Username: {admin.username}")
        print(f"   Email: {admin.email}")
        print(f"   Nouveau mot de passe: {new_password}")
        return True
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    import getpass
    import os
    
    # Try to get password from environment variable
    password = os.getenv("ADMIN_PASSWORD")
    
    if not password:
        # Prompt for password
        password = getpass.getpass("Nouveau mot de passe admin: ")
        confirm = getpass.getpass("Confirmer le mot de passe: ")
        
        if password != confirm:
            print("❌ Les mots de passe ne correspondent pas")
            sys.exit(1)
    
    if len(password) < 8:
        print("❌ Le mot de passe doit contenir au moins 8 caractères")
        sys.exit(1)
    
    success = reset_admin_password(password)
    sys.exit(0 if success else 1)
