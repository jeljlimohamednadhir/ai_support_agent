"""
Test de connexion SSH au serveur DB BRASIL.
Usage : python test_ssh_connection.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.core.config import settings
from app.services.ssh_operations.client.ssh_client import SshClient

def test():
    print("=" * 55)
    print("TEST CONNEXION SSH → BRASIL DB")
    print("=" * 55)
    print(f"  Host    : {settings.SSH_BRASIL_HOST}:{settings.SSH_BRASIL_PORT}")
    print(f"  User    : {settings.SSH_BRASIL_USER}")
    print(f"  Env     : {settings.SSH_BRASIL_ENV}")
    print(f"  DB name : {settings.BRASIL_PSQL_DB_NAME}")
    print(f"  DB user : {settings.BRASIL_PSQL_DB_USER}")
    print()

    if not settings.SSH_ENABLED:
        print("❌  SSH_ENABLED=false dans .env — activez-le d'abord.")
        return

    client = SshClient(
        host=settings.SSH_BRASIL_HOST,
        port=settings.SSH_BRASIL_PORT,
        username=settings.SSH_BRASIL_USER,
        password=settings.SSH_BRASIL_PASSWORD or None,
        private_key_path=settings.SSH_BRASIL_PRIVATE_KEY or None,
        connect_timeout_s=settings.SSH_CONNECT_TIMEOUT_S,
        auto_add_host_key=True,   # accepter la host key pour le test
    )

    # ── 1. Connexion SSH ──────────────────────────────────
    print("[1/4] Connexion SSH...")
    try:
        client.connect()
        print("      ✅ Connexion SSH OK")
    except Exception as e:
        print(f"      ❌ Échec connexion SSH : {e}")
        return

    # ── 2. whoami / hostname ──────────────────────────────
    print("[2/4] Identité sur le serveur...")
    try:
        r = client.exec_command("whoami && hostname")
        output = r.get("output", r.get("stdout", "")).strip()
        print(f"      ✅ {output}")
    except Exception as e:
        print(f"      ⚠️  {e}")

    # Trouver psql
    print("[2b] Recherche de psql...")
    for cmd in ["which psql", "find /usr -name psql 2>/dev/null | head -3",
                "find /opt -name psql 2>/dev/null | head -3",
                "ls /usr/bin/psql /usr/local/bin/psql /opt/postgresql*/bin/psql 2>/dev/null"]:
        r = client.exec_command(cmd)
        out = r.get("output", "").strip()
        if out:
            print(f"      ✅ {cmd} → {out}")
            break
    else:
        print("      ❌ psql introuvable via which/find")

    # ── 3. psql ping ──────────────────────────────────────
    print("[3/4] Test psql (SELECT 1) — recherche du bon port/socket...")
    PSQL     = "/opt/pgsql/na/9.4.4/bin/psql"
    PSQL_LIB = "/opt/pgsql/na/9.4.4/lib"
    PSQL_ENV = f"LD_LIBRARY_PATH={PSQL_LIB}:$LD_LIBRARY_PATH"
    for pg_opts in ["-h localhost -p 5432", "-h 127.0.0.1 -p 5432", "-p 5433", "-h localhost -p 5433", ""]:
        cmd = f"{PSQL_ENV} {PSQL} {pg_opts} -d {settings.BRASIL_PSQL_DB_NAME} -U {settings.BRASIL_PSQL_DB_USER} -t -c 'SELECT 1;'"
        r   = client.exec_command(cmd.strip(), timeout_s=10)
        out = r.get("output", "").strip()
        err = r.get("error", "").strip()
        if out and "1" in out:
            print(f"      ✅ psql OK  opts='{pg_opts}' → {out!r}")
            break
        else:
            print(f"      ⚠️  opts='{pg_opts}' → {err[:80]!r}")

    # ── 4. Vérifier tables brasil ─────────────────────────
    print("[4/4] Vérification tables BRASIL...")
    psql_tables = (
        f"{PSQL_LIB} {PSQL} -d {settings.BRASIL_PSQL_DB_NAME} -U {settings.BRASIL_PSQL_DB_USER} "
        f"-t -c \"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';\""
    )
    try:
        r = client.exec_command(psql_tables, timeout_s=15)
        output = r.get("output", r.get("stdout", "")).strip()
        print(f"      ✅ Tables dans public schema : {output.strip()}")
    except Exception as e:
        print(f"      ❌ {e}")

    client.disconnect()
    print()
    print("=" * 55)
    print("Test terminé.")

if __name__ == "__main__":
    test()
