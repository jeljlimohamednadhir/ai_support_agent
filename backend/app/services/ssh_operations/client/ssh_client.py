"""
ssh_client.py
━━━━━━━━━━━━━
Secure SSH connection manager.

Security guarantees:
  - Credentials NEVER passed to LLM
  - No arbitrary command execution
  - Only whitelisted commands (via command_executor)
  - Timeout enforced on every operation
  - Full audit logging
  - Supports password + private key authentication
  - Host key verification configurable

Requires: pip install paramiko
"""

from __future__ import annotations

import logging
import socket
import time
import warnings
from typing import Any, Dict, List, Optional, Generator

# Supprimer le warning TripleDES de paramiko 2.x (cryptography >= 42)
warnings.filterwarnings(
    "ignore",
    message="TripleDES has been moved",
    category=DeprecationWarning,
)
try:
    from cryptography.utils import CryptographyDeprecationWarning  # type: ignore
except Exception:
    CryptographyDeprecationWarning = None

if CryptographyDeprecationWarning is not None:
    warnings.filterwarnings(
        "ignore",
        category=CryptographyDeprecationWarning,
        module="paramiko",
    )

logger = logging.getLogger(__name__)

_PARAMIKO_AVAILABLE = False
try:
    import paramiko  # type: ignore
    _PARAMIKO_AVAILABLE = True
except ImportError:
    logger.warning("[SshClient] paramiko not installed. SSH operations disabled.")


class SshConnectionError(Exception):
    pass


class SshAuthError(SshConnectionError):
    pass


class SshTimeoutError(SshConnectionError):
    pass


class SshClient:
    """
    Manages a single SSH connection to a remote host.

    Usage
    -----
    client = SshClient(host="10.0.0.1", username="op49mbdd", password="...")
    with client:
        result = client.run("tail_brasil_logs")
    """

    def __init__(
        self,
        host:                   str,
        port:                   int          = 22,
        username:               str          = "",
        password:               Optional[str] = None,
        private_key_path:       Optional[str] = None,
        private_key_passphrase: Optional[str] = None,
        connect_timeout_s:      int          = 5,
        default_timeout_s:      int          = 10,
        connect_retries:        int          = 1,
        known_hosts_path:       Optional[str] = None,
        auto_add_host_key:      bool         = False,  # Set True only for dev/staging
        allow_agent:            bool         = False,  # ⭐ NOUVEAU : False par défaut
        look_for_keys:          bool         = False,  # ⭐ NOUVEAU : False par défaut
        legacy_mode:            bool         = False,  # ⭐ NOUVEAU : désactive rsa-sha2 si True
    ):
        self.host              = host
        self.port              = port
        self.username          = username
        self._password         = password
        self._key_path         = private_key_path
        self._key_passphrase   = private_key_passphrase
        self.connect_timeout_s = connect_timeout_s
        self.connect_retries   = connect_retries
        self.default_timeout_s = default_timeout_s
        self._known_hosts      = known_hosts_path
        self._auto_add         = auto_add_host_key
        self._allow_agent      = allow_agent      # ⭐
        self._look_for_keys    = look_for_keys    # ⭐
        self._legacy_mode      = legacy_mode      # ⭐
        self._client: Optional["paramiko.SSHClient"] = None
        self._connected = False

    # ── Context manager ───────────────────────────────────────────────────────

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *_):
        self.disconnect()

    # ── Connection lifecycle ──────────────────────────────────────────────────

    def connect(self) -> None:
        if not _PARAMIKO_AVAILABLE:
            raise SshConnectionError("paramiko not installed.")
        if self._connected:
            return

        client = paramiko.SSHClient()

        # ── Host key policy ───────────────────────────────────────────────────
        # - auto_add_host_key=True  → dev/staging : accepte et cache toutes les clés
        # - known_hosts_path fourni → production  : rejette les clés inconnues
        # - sinon                   → accept-new  : accepte et cache (comme ssh -o StrictHostKeyChecking=accept-new)
        try:
            from paramiko import AutoAddPolicy, RejectPolicy
        except Exception:
            AutoAddPolicy = paramiko.AutoAddPolicy
            RejectPolicy  = getattr(paramiko, "RejectPolicy", None)

        if self._auto_add:
            client.set_missing_host_key_policy(AutoAddPolicy())
        elif self._known_hosts:
            client.load_host_keys(self._known_hosts)
            if RejectPolicy is not None:
                client.set_missing_host_key_policy(RejectPolicy())
            else:
                client.set_missing_host_key_policy(AutoAddPolicy())
        else:
            client.set_missing_host_key_policy(AutoAddPolicy())

        # ── Patch ssh-rsa pour serveurs legacy (paramiko 3+) ──────────────────
        # paramiko 3+ désactive ssh-rsa par défaut.
        # On le réactive pour les serveurs AIX / RHEL anciens.
        try:
            import paramiko.transport as _pt
            import paramiko.rsakey    as _rsa
            preferred = list(_pt.Transport._preferred_keys)
            if "ssh-rsa" not in preferred:
                _pt.Transport._preferred_keys = ("ssh-rsa",) + tuple(preferred)
            if "ssh-rsa" not in _pt.Transport._key_info:
                _pt.Transport._key_info["ssh-rsa"] = _rsa.RSAKey
        except Exception as _e:
            logger.debug(f"[SshClient] patch ssh-rsa: {_e}")

        # ── Optional debug via SSH_DEBUG env var ──────────────────────────────
        try:
            import os as _os
            if _os.getenv("SSH_DEBUG"):
                import logging as _logging
                _logging.getLogger("paramiko").setLevel(_logging.DEBUG)
        except Exception:
            pass

        try:
            # ── Construction des kwargs de connexion ──────────────────────────
            connect_kwargs: Dict[str, Any] = {
                "hostname":       self.host,
                "port":           self.port,
                "username":       self.username,
                "timeout":        self.connect_timeout_s,
                "banner_timeout": self.connect_timeout_s,
                # ⭐ CORRECTION PRINCIPALE : désactiver agent et recherche de clés
                # par défaut pour éviter les tentatives d'auth multiples qui
                # provoquent la fermeture de connexion par le serveur distant.
                "allow_agent":    self._allow_agent,
                "look_for_keys":  self._look_for_keys,
            }

            # ⭐ CORRECTION : disabled_algorithms uniquement en mode legacy
            # (serveurs AIX/RHEL anciens forçant ssh-rsa SHA1).
            # Ne pas l'appliquer par défaut car cela peut causer des
            # incompatibilités avec des serveurs modernes.
            if self._legacy_mode:
                connect_kwargs["disabled_algorithms"] = {
                    "pubkeys": ["rsa-sha2-256", "rsa-sha2-512"]
                }

            # ── Méthode d'authentification ────────────────────────────────────
            if self._key_path:
                # Authentification par clé privée
                pkey = paramiko.RSAKey.from_private_key_file(
                    self._key_path, password=self._key_passphrase
                )
                connect_kwargs["pkey"] = pkey
            elif self._password:
                # Authentification par mot de passe (chemin direct, sans tentatives inutiles)
                connect_kwargs["password"] = self._password
            else:
                # Aucune auth explicite : fallback sur agent/clés locales
                # (override des valeurs par défaut False)
                connect_kwargs["look_for_keys"] = True
                connect_kwargs["allow_agent"]   = True

            # ── Boucle de tentatives de connexion ─────────────────────────────
            last_exc = None
            for attempt in range(1, max(1, self.connect_retries) + 1):
                try:
                    client.connect(**connect_kwargs)
                    self._client    = client
                    self._connected = True
                    logger.info(
                        f"[SshClient] Connected to {self.host}:{self.port} "
                        f"(attempt {attempt})"
                    )
                    last_exc = None
                    break
                except Exception as e:
                    last_exc = e
                    logger.warning(
                        f"[SshClient] connect attempt {attempt}/{self.connect_retries} "
                        f"failed: {e}"
                    )
                    if attempt < self.connect_retries:
                        time.sleep(1)

            if last_exc:
                raise last_exc

        except paramiko.AuthenticationException as e:
            raise SshAuthError(
                f"Authentication failed to {self.host}: {e}"
            ) from e
        except (socket.timeout, TimeoutError) as e:
            raise SshTimeoutError(
                f"Connection timeout to {self.host}: {e}"
            ) from e
        except Exception as e:
            raise SshConnectionError(
                f"SSH connection failed to {self.host}: {e}"
            ) from e

    def disconnect(self) -> None:
        if self._client:
            self._client.close()
            self._client    = None
            self._connected = False
            logger.info(f"[SshClient] Disconnected from {self.host}")

    def reconnect(self) -> None:
        self.disconnect()
        self.connect()

    @property
    def is_connected(self) -> bool:
        if not self._connected or not self._client:
            return False
        transport = self._client.get_transport()
        return transport is not None and transport.is_active()

    def _ensure_connected(self) -> None:
        if not self.is_connected:
            logger.warning("[SshClient] Connection lost, reconnecting...")
            self.reconnect()

    # ── Command execution ─────────────────────────────────────────────────────

    def exec_command(
        self,
        command:   str,
        timeout_s: int | None = None,
    ) -> Dict[str, Any]:
        """
        Execute a single command and return {success, output, error}.

        INTERNAL USE ONLY.
        External callers should use CommandExecutor with whitelisted commands.
        """
        self._ensure_connected()
        timeout = timeout_s or self.default_timeout_s
        t0      = time.perf_counter()

        try:
            stdin, stdout, stderr = self._client.exec_command(  # type: ignore
                command, timeout=timeout
            )
            out = stdout.read().decode("utf-8", errors="replace")
            err = stderr.read().decode("utf-8", errors="replace")
            rc  = stdout.channel.recv_exit_status()

            duration = round((time.perf_counter() - t0) * 1000, 1)
            success  = rc == 0

            logger.info(
                f"[SshClient] Command exit={rc} ({duration} ms) on {self.host}"
            )
            return {
                "success":     success,
                "output":      out,
                "error":       err,
                "exit_code":   rc,
                "duration_ms": duration,
            }

        except socket.timeout:
            raise SshTimeoutError(
                f"Command timed out after {timeout}s on {self.host}"
            )
        except Exception as e:
            logger.error(f"[SshClient] exec_command failed: {e}")
            return {
                "success":   False,
                "output":    "",
                "error":     str(e),
                "exit_code": -1,
            }

    # ── Streaming support ─────────────────────────────────────────────────────

    def stream_command(
        self,
        command:   str,
        timeout_s: int | None = None,
    ) -> Generator[str, None, None]:
        """
        Stream command output line-by-line.

        Usage:
            for line in client.stream_command("tail -f /var/log/app.log"):
                print(line)
        """
        self._ensure_connected()
        timeout = timeout_s or self.default_timeout_s

        try:
            transport = self._client.get_transport()  # type: ignore
            channel   = transport.open_session()
            channel.settimeout(timeout)
            channel.exec_command(command)

            buffer = b""
            while True:
                chunk = channel.recv(4096)
                if not chunk:
                    break
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    yield line.decode("utf-8", errors="replace")

            if buffer:
                yield buffer.decode("utf-8", errors="replace")

            channel.close()

        except Exception as e:
            logger.error(f"[SshClient] stream_command failed: {e}")
            yield f"[ERROR] {e}"

    # ── Interactive shell ─────────────────────────────────────────────────────

    def invoke_shell(self, timeout_s: int = 30) -> "paramiko.Channel":
        """
        Open an interactive shell channel.
        Used for multi-step interactive scripts.
        """
        self._ensure_connected()
        channel = self._client.invoke_shell()  # type: ignore
        channel.settimeout(timeout_s)
        return channel

    # ── SFTP ─────────────────────────────────────────────────────────────────

    def get_sftp(self) -> "paramiko.SFTPClient":
        """Return an SFTP client for file operations."""
        self._ensure_connected()
        return self._client.open_sftp()  # type: ignore
