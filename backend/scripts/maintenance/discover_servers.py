"""
discover_servers.py
━━━━━━━━━━━━━━━━━━━
Auto-discovery des serveurs BRASIL (WA, DE, BDD).
Detecte : chemins de logs, processus Java, versions, disques.

Usage:
    python discover_servers.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from app.services.ssh_operations.client.ssh_client import SshClient

# ── Config depuis .env ──────────────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

SERVERS = {
    "BDD": {
        "host": os.getenv("SSH_BRASIL_HOST"),
        "port": int(os.getenv("SSH_BRASIL_PORT", 22)),
        "user": os.getenv("SSH_BRASIL_USER"),
        "password": os.getenv("SSH_BRASIL_PASSWORD"),
    },
    "WA": {
        "host": os.getenv("SSH_WA_HOST"),
        "port": int(os.getenv("SSH_WA_PORT", 22)),
        "user": os.getenv("SSH_WA_USER"),
        "password": os.getenv("SSH_WA_PASSWORD"),
    },
    "DE": {
        "host": os.getenv("SSH_DE_HOST"),
        "port": int(os.getenv("SSH_DE_PORT", 22)),
        "user": os.getenv("SSH_DE_USER"),
        "password": os.getenv("SSH_DE_PASSWORD"),
    },
}

# ── Discovery commands ──────────────────────────────────────────────────────
DISCOVERY_CMDS = {
    "hostname":       "hostname 2>/dev/null",
    "os_version":     "cat /etc/redhat-release 2>/dev/null || uname -a",
    "java_processes": "ps -ef | grep java | grep -v grep | head -10",
    "tomcat_home":    "find /opt -maxdepth 3 -name 'catalina.sh' 2>/dev/null | head -5",
    "log_dirs": (
        "find /opt /var/log /logs /app -maxdepth 3 "
        "\\( -name '*.log' -o -name 'catalina.out' \\) "
        "-type f 2>/dev/null | head -30"
    ),
    "disk_usage":     "df -h | head -10",
    "brasil_paths": (
        "find / -maxdepth 4 -type d -name 'brasil' 2>/dev/null | head -10"
    ),
    "psql_version":   "/opt/pgsql/na/9.4.4/bin/psql --version 2>/dev/null || psql --version 2>/dev/null || echo 'no psql'",
    "listening_ports": "netstat -tlnp 2>/dev/null | grep -E '(java|postgres|tomcat)' | head -10",
}


def discover(role: str, cfg: dict):
    """Connect and run discovery commands."""
    if not cfg.get("host"):
        print(f"  [SKIP] {role}: host not configured")
        return

    print(f"\n{'='*70}")
    print(f"  SERVER: {role} ({cfg['host']}:{cfg['port']} as {cfg['user']})")
    print(f"{'='*70}")

    client = SshClient(
        host=cfg["host"],
        port=cfg["port"],
        username=cfg["user"],
        password=cfg["password"],
        connect_timeout_s=15,
        auto_add_host_key=True,
    )

    try:
        client.connect()
        print(f"  [OK] Connected")
    except Exception as e:
        print(f"  [FAIL] Connection failed: {e}")
        return

    for label, cmd in DISCOVERY_CMDS.items():
        try:
            result = client.exec_command(cmd, timeout_s=15)
            output = result.get("output", "").strip()
            exit_code = result.get("exit_code", -1)
            if output:
                print(f"\n  [{label}] (exit={exit_code})")
                for line in output.splitlines()[:15]:
                    print(f"    {line}")
            else:
                print(f"\n  [{label}] (empty / exit={exit_code})")
        except Exception as e:
            print(f"\n  [{label}] ERROR: {e}")

    client.disconnect()


if __name__ == "__main__":
    print("=" * 70)
    print("  BRASIL Server Auto-Discovery")
    print("=" * 70)

    for role, cfg in SERVERS.items():
        discover(role, cfg)

    print("\n" + "=" * 70)
    print("  Discovery complete.")
    print("=" * 70)
