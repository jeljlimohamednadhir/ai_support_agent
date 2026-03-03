#!/usr/bin/env python3
"""
Afficher le hash du mot de passe admin depuis PostgreSQL
"""
import sys
sys.path.insert(0, '.')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.user import User
from app.models.refresh_token import RefreshToken

DB_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/ai_support_agent"

engine = create_engine(DB_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

try:
    admin = db.query(User).filter(User.username == "admin").first()
    
    if admin:
        print(f"Username: {admin.username}")
        print(f"Email: {admin.email}")
        print(f"Hash: {admin.hashed_password}")
        print(f"\nPour tester, mettez ce hash dans test_password_verify.py")
    else:
        print("Admin user not found")
finally:
    db.close()
