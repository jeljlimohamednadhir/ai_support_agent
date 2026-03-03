import sqlite3
from passlib.context import CryptContext

# Configuration
import os
DB_PATH = os.getenv("ADMIN_DB_PATH", "backend/ai_support.db")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")
# ADMIN_PASSWORD should come from environment or be prompted at runtime
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
if not ADMIN_PASSWORD:
    try:
        # ask interactively to avoid storing secrets in scripts
        import getpass
        ADMIN_PASSWORD = getpass.getpass("Admin password (will not be echoed): ")
    except Exception:
        raise RuntimeError("ADMIN_PASSWORD not set in environment and interactive prompt failed")

# Générer le hash du mot de passe
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
hashed_password = pwd_context.hash(ADMIN_PASSWORD)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Vérifier si un admin existe déjà
cur.execute("SELECT id FROM users WHERE username=? OR email=?", (ADMIN_USERNAME, ADMIN_EMAIL))
row = cur.fetchone()

if row:
    # Mettre à jour le mot de passe et le rôle
    cur.execute("""
        UPDATE users SET hashed_password=?, role='admin' WHERE id=?
    """, (hashed_password, row[0]))
    print(f"Utilisateur admin existant mis à jour (id={row[0]})")
else:
    # Créer un nouvel utilisateur admin
    cur.execute("""
        INSERT INTO users (username, email, hashed_password, role, is_active) VALUES (?, ?, ?, 'admin', 1)
    """, (ADMIN_USERNAME, ADMIN_EMAIL, hashed_password))
    print("Nouvel utilisateur admin créé.")

conn.commit()
conn.close()
print("Opération terminée.")
