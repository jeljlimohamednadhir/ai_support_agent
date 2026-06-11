import psycopg2
from dotenv import load_dotenv
from pathlib import Path
import os

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

# Supprimer tous les utilisateurs
pg_cur.execute("DELETE FROM users")
pg_conn.commit()

print("Tous les utilisateurs ont été supprimés de PostgreSQL.")

pg_cur.close()
pg_conn.close()
