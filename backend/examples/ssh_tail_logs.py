"""Example: stream remote catalina.out using SshClient

Run from the backend venv (where paramiko is installed):

    python -m backend.examples.ssh_tail_logs

Or run directly:
    python backend\examples\ssh_tail_logs.py
"""
from app.services.ssh_operations.client.ssh_client import SshClient

import os

HOST = os.getenv("SSH_HOST", "brasil.example.local")
USER = os.getenv("SSH_USER", "deployuser")
KEY = os.getenv("SSH_KEY")  # path to private key, optional if agent keys are available

if __name__ == "__main__":
    if KEY and not os.path.exists(KEY):
        print(f"Private key not found at {KEY}. Set SSH_KEY env or leave unset to use agent/keys.")
        raise SystemExit(2)

    with SshClient(host=HOST, username=USER, private_key_path=KEY, auto_add_host_key=False) as client:
        try:
            for line in client.stream_command("tail -n 200 -F /opt/tomcat/logs/catalina.out", timeout_s=600):
                # stream_command yields decoded lines (strings)
                print(line, end="")
        except Exception as e:
            print("Streaming failed:", e)
