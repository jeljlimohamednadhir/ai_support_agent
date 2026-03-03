import sqlite3
import psycopg2
from dotenv import load_dotenv
from pathlib import Path
import os

# Charger la config depuis backend/.env
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

# Config SQLite
SQLITE_DB = os.getenv('SQLITE_DB_PATH', 'backend/ai_support.db')

# Config PostgreSQL depuis .env
PG_HOST = os.getenv('POSTGRES_SERVER', 'localhost')
PG_PORT = int(os.getenv('POSTGRES_PORT', 5432))
PG_USER = os.getenv('POSTGRES_USER', 'postgres')
PG_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'postgres')
PG_DBNAME = os.getenv('POSTGRES_DB', 'ai_support_agent')

PG_CONN_DSN = f"host={PG_HOST} port={PG_PORT} dbname={PG_DBNAME} user={PG_USER} password={PG_PASSWORD}"


def ensure_users_table(pg_cur, pg_conn):
    # Create users table if it doesn't exist (simple schema matching models/user.py)
    pg_cur.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(100) UNIQUE NOT NULL,
        email VARCHAR(255) UNIQUE NOT NULL,
        hashed_password VARCHAR(255) NOT NULL,
        full_name VARCHAR(255),
        role VARCHAR(20) NOT NULL DEFAULT 'user',
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMP,
        updated_at TIMESTAMP,
        last_login TIMESTAMP
    );
    ''')
    pg_conn.commit()


def main():
    # Connexion SQLite
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_cur = sqlite_conn.cursor()

    # Connexion PostgreSQL - affichage debug (mot de passe masqué)
    print("Postgres connect params:")
    print("  host=", PG_HOST)
    print("  port=", PG_PORT)
    print("  dbname=", PG_DBNAME)
    print("  user=", PG_USER)
    print("  password=", '***masked***')
    try:
        pg_conn = psycopg2.connect(host=PG_HOST, port=PG_PORT, dbname=PG_DBNAME, user=PG_USER, password=PG_PASSWORD)
    except Exception as e:
        print("Erreur connexion PostgreSQL:", repr(e))
        raise
    pg_cur = pg_conn.cursor()

    ensure_users_table(pg_cur, pg_conn)

    # Lire tous les utilisateurs de SQLite
    sqlite_cur.execute("SELECT username, email, hashed_password, full_name, role, is_active, created_at, updated_at, last_login FROM users")
    users = sqlite_cur.fetchall()

    # Insérer dans PostgreSQL (convertir is_active int -> bool, role en majuscules)
    migrated = 0
    skipped = 0
    for user in users:
        username, email, hashed_password, full_name, role, is_active, created_at, updated_at, last_login = user
        is_active_bool = bool(is_active)  # Convertir 0/1 -> False/True
        role_upper = role.upper() if role else 'USER'  # Convertir role en majuscules pour correspondre à l'enum PostgreSQL
        try:
            pg_cur.execute('''
                INSERT INTO users (username, email, hashed_password, full_name, role, is_active, created_at, updated_at, last_login)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (email) DO UPDATE SET
                  username = EXCLUDED.username,
                  hashed_password = EXCLUDED.hashed_password,
                  full_name = EXCLUDED.full_name,
                  role = EXCLUDED.role,
                  is_active = EXCLUDED.is_active,
                  updated_at = EXCLUDED.updated_at,
                  last_login = EXCLUDED.last_login;
            ''', (username, email, hashed_password, full_name, role_upper, is_active_bool, created_at, updated_at, last_login))
            migrated += 1
        except psycopg2.errors.UniqueViolation as e:
            # Si conflit sur username (autre que email), on skip
            print(f"Conflit ignoré pour {username}/{email}: {e}")
            pg_conn.rollback()
            skipped += 1
            continue

    pg_conn.commit()
    print(f"{migrated} utilisateurs migrés de SQLite vers PostgreSQL.")
    if skipped > 0:
        print(f"{skipped} utilisateurs ignorés (conflits de username/email déjà existants).")

    sqlite_conn.close()
    pg_cur.close()
    pg_conn.close()


if __name__ == '__main__':
    main()
