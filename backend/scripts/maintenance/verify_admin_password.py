import psycopg2
from dotenv import load_dotenv
from pathlib import Path
import os
from passlib.context import CryptContext

# Charger la config depuis backend/.env
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

# Config PostgreSQL depuis .env
PG_HOST = os.getenv('POSTGRES_SERVER', 'localhost')
PG_PORT = int(os.getenv('POSTGRES_PORT', 5432))
PG_USER = os.getenv('POSTGRES_USER', 'postgres')
PG_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'postgres')
PG_DBNAME = os.getenv('POSTGRES_DB', 'ai_support_agent')

# Connexion PostgreSQL
pg_conn = psycopg2.connect(host=PG_HOST, port=PG_PORT, dbname=PG_DBNAME, user=PG_USER, password=PG_PASSWORD)
pg_cur = pg_conn.cursor()

# Récupérer l'utilisateur admin
pg_cur.execute("SELECT username, email, hashed_password, role FROM users WHERE username='admin'")
user = pg_cur.fetchone()

if user:
    username, email, hashed_password, role = user
    print(f"Username: {username}")
    print(f"Email: {email}")
    print(f"Role: {role}")
    print(f"Hashed password: {hashed_password[:60]}...")
    
    # Tester la vérification du mot de passe
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    test_password = "Admin@123"
    
    try:
        is_valid = pwd_context.verify(test_password, hashed_password)
        print(f"\nVérification du mot de passe '{test_password}': {'✓ VALIDE' if is_valid else '✗ INVALIDE'}")
    except Exception as e:
        print(f"\nErreur lors de la vérification: {e}")
else:
    print("Aucun utilisateur admin trouvé")

pg_cur.close()
pg_conn.close()
