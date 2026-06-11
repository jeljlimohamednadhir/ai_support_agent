"""
ssh_pool.py
━━━━━━━━━━━
Singleton SSH connection pool — keeps sessions alive across HTTP requests.

Instead of opening a new TCP+SSH handshake per chat message, connections
are stored and reused.  A background keepalive ensures the transport stays
active.  If a connection drops, it is lazily recreated on next use.

Usage (in live_diagnostics or anywhere):
    from app.services.ssh_operations.client.ssh_pool import ssh_pool
    client = ssh_pool.get("wa", host=..., username=..., password=...)
    # client is a regular SshClient, already connected (or reconnected)
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, Optional

from app.services.ssh_operations.client.ssh_client import SshClient

logger = logging.getLogger(__name__)

# How often (seconds) we send a keepalive null packet to prevent idle timeout
_KEEPALIVE_INTERVAL = 30


class SshPool:
    """Thread-safe singleton pool of named SSH sessions."""

    def __init__(self) -> None:
        self._pool: Dict[str, SshClient] = {}
        self._lock = threading.Lock()
        self._keepalive_started = False

    # ── Public API ────────────────────────────────────────────────────────────

    def get(self, name: str, **kwargs: Any) -> SshClient:
        """
        Return a connected SshClient for *name*.

        If the pool already has a live session for that name, return it.
        Otherwise create one with the provided kwargs and connect it.

        Parameters
        ----------
        name : logical name (e.g. "bdd", "wa", "de")
        **kwargs : forwarded to SshClient() constructor on first creation
        """
        with self._lock:
            client = self._pool.get(name)

            # Existing client still alive?
            if client is not None and client.is_connected:
                return client

            # Dead or missing — (re)create
            if client is not None:
                logger.info(f"[SshPool] Session '{name}' dead, recreating...")
                try:
                    client.disconnect()
                except Exception:
                    pass

            client = SshClient(**kwargs)
            try:
                client.connect()
                logger.info(f"[SshPool] Session '{name}' connected to {client.host}")
            except Exception as e:
                logger.warning(f"[SshPool] Session '{name}' connect failed: {e}")
                raise

            self._pool[name] = client

            # Start background keepalive thread (once)
            if not self._keepalive_started:
                self._start_keepalive()

            return client

    def close_all(self) -> None:
        """Disconnect all pooled sessions (e.g. at app shutdown)."""
        with self._lock:
            for name, client in self._pool.items():
                try:
                    client.disconnect()
                except Exception:
                    pass
                logger.info(f"[SshPool] Closed session '{name}'")
            self._pool.clear()

    def remove(self, name: str) -> None:
        """Remove and disconnect a specific session."""
        with self._lock:
            client = self._pool.pop(name, None)
            if client:
                try:
                    client.disconnect()
                except Exception:
                    pass

    # ── Keepalive ─────────────────────────────────────────────────────────────

    def _start_keepalive(self) -> None:
        self._keepalive_started = True
        t = threading.Thread(target=self._keepalive_loop, daemon=True, name="ssh-keepalive")
        t.start()

    def _keepalive_loop(self) -> None:
        """Send periodic keepalive on all active transports."""
        while True:
            time.sleep(_KEEPALIVE_INTERVAL)
            with self._lock:
                for name, client in list(self._pool.items()):
                    try:
                        if client._client and client._client.get_transport():
                            transport = client._client.get_transport()
                            if transport and transport.is_active():
                                transport.send_ignore()
                    except Exception as e:
                        logger.debug(f"[SshPool] keepalive '{name}' failed: {e}")


# ── Module-level singleton ────────────────────────────────────────────────────
ssh_pool = SshPool()
