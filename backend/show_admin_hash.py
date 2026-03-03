import sqlite3

# Chemin vers la base SQLite
DB_PATH = "backend/ai_support.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("SELECT username, email, hashed_password FROM users WHERE role='admin'")
rows = cur.fetchall()
if not rows:
    print("Aucun utilisateur admin trouvé.")
else:
    for row in rows:
        print("Username:", row[0])
        print("Email:", row[1])
        print("Hashed password:", row[2])
        print("-")
conn.close()
