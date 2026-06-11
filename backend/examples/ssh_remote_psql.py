"""Example: execute a remote psql command via SshClient

Notes:
- This requires `psql` to be installed on the remote host. If not present,
  consider using an SSH tunnel and connecting with a local psql client.

Run:
    python backend\examples\ssh_remote_psql.py
"""
from app.services.ssh_operations.client.ssh_client import SshClient

import os

HOST = os.getenv("SSH_HOST", "brasil-db-host")
USER = os.getenv("SSH_USER", "dbuser")
KEY = os.getenv("SSH_KEY")
PASSWORD = os.getenv("SSH_PASSWORD")
DB = os.getenv("REMOTE_DB", "brasil_db")

if __name__ == "__main__":
    if KEY and not os.path.exists(KEY):
        print(f"Private key not found at {KEY}. Set SSH_KEY env or leave unset to use agent/keys.")
        raise SystemExit(2)

    # Query for ND '0142785811'
    cmd = f"psql -d {DB} -t -A -c \"SELECT nd, status FROM t_nd WHERE nd = '0142785811';\""
    # Prefer key auth if KEY provided, otherwise use SSH_PASSWORD if set, otherwise rely on agent
    with SshClient(host=HOST, username=USER, private_key_path=KEY, password=PASSWORD, auto_add_host_key=False) as client:
        res = client.exec_command(cmd, timeout_s=30)
        if res.get('success'):
            print("PSQL output:\n", res.get('output'))
        else:
            print("PSQL error:\n", res.get('error'))
