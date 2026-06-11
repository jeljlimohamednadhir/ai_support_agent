"""Test SSH connections to Brasil hosts (banner probe + SshClient connect).

Usage: set environment variables for credentials and run the script.

Notes:
- Pass secrets via environment variables. Do NOT commit secrets.
- This script runs locally; it will not be executed from the assistant environment.
"""
from __future__ import annotations

import os
import socket
import sys
import time
from typing import Optional

from app.services.ssh_operations.client.ssh_client import SshClient


def banner_probe(host: str, port: int = 22, timeout: float = 5.0) -> tuple[bool, Optional[str]]:
    """Open a raw TCP socket and try to read an SSH banner line.
    Returns (ok, banner_or_error).
    """
    try:
        with socket.create_connection((host, port), timeout=timeout) as s:
            s.settimeout(timeout)
            try:
                data = s.recv(256)
                if not data:
                    return False, "(no data)"
                text = data.decode("utf-8", errors="replace").strip()
                return (text.startswith("SSH-"), text)
            except socket.timeout:
                return False, "(read timeout)"
            except Exception as e:
                return False, f"(read error: {e})"
    except Exception as e:
        return False, f"(connect error: {e})"


def try_ssh_connect(host: str, user: str, password: Optional[str] = None, key_path: Optional[str] = None, port: int = 22):
    print(f"\n--- Trying SSH -> {host}:{port} as {user} ---")
    ok, banner = banner_probe(host, port=port, timeout=5.0)
    print(f"Banner probe: ok={ok}, banner={banner}")

    # Use SshClient with a few retries
    try:
        client = SshClient(host=host, port=port, username=user, password=password, private_key_path=key_path, connect_retries=5, auto_add_host_key=False)
        try:
            client.connect()
        except Exception as e:
            print(f"Connect failed: {e}")
            return False

        print("Connected. Running basic checks...")
        try:
            res = client.exec_command("hostname && whoami && pwd", timeout_s=30)
            if res.get('success'):
                print("Command output:\n", res.get('output'))
            else:
                print("Command failed:\n", res.get('error'))
        except Exception as e:
            print("Command execution error:", e)
        finally:
            client.disconnect()
        return True
    except Exception as e:
        print("Unexpected error creating SshClient:", e)
        return False


def main():
    # Read credentials from environment variables
    bds_host = os.getenv('BDS_HOST', '10.103.246.194')
    bds_user = os.getenv('BDS_USER', 'op49mbdd')
    bds_pass = os.getenv('BDS_PASSWORD')
    wa_host = os.getenv('WA_HOST', '10.103.246.78')
    wa_user = os.getenv('WA_USER', 'op49mapp')
    wa_pass = os.getenv('WA_PASSWORD')

    print('Starting Brasil SSH connectivity checks')

    ok1 = try_ssh_connect(bds_host, bds_user, password=bds_pass)
    ok2 = try_ssh_connect(wa_host, wa_user, password=wa_pass)

    print('\nSummary:')
    print(f' BDD {bds_host} -> {"OK" if ok1 else "FAILED"}')
    print(f' WA  {wa_host} -> {"OK" if ok2 else "FAILED"}')

    sys.exit(0 if (ok1 and ok2) else 2)


if __name__ == '__main__':
    main()
