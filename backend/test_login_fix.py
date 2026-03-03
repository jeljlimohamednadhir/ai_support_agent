"""Test rapide du login après correction bcrypt"""
import sys
import os

# Ajouter le répertoire backend au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.user import User
from app.models.refresh_token import RefreshToken, RevokedToken  # Import pour résoudre les relationships
from app.core.security import verify_password

# Direct PostgreSQL URL (comme dans reset_admin_password.py)
DB_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/ai_support_agent"

# Créer session DB
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

try:
    # Récupérer l'utilisateur admin
    admin = db.query(User).filter(User.username == "admin").first()
    
    if not admin:
        print("❌ Utilisateur admin introuvable")
        sys.exit(1)
    
    print(f"✅ Utilisateur trouvé: {admin.username} ({admin.email})")
    print(f"   Role: {admin.role}")
    print(f"   Hash commence par: {admin.hashed_password[:20]}")
    
    # Tester la vérification du mot de passe
    test_password = "Admin@2024"
    is_valid = verify_password(test_password, admin.hashed_password)
    
    if is_valid:
        print(f"✅ Mot de passe '{test_password}' VALIDE!")
        print("\n🎉 Le login devrait fonctionner maintenant!")
    else:
        print(f"❌ Mot de passe '{test_password}' INVALIDE")
        print("   Réexécuter reset_admin_password.py")
    
finally:
    db.close()
