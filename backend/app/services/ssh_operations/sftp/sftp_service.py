"""
sftp_service.py
━━━━━━━━━━━━━━━
SFTP file transfer service built on top of SshClient.

Capabilities:
  - Upload local file -> remote path
  - Download remote file -> local path
  - Validate remote paths (whitelist)
  - Log all transfers
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.ssh_operations.client.ssh_client import SshClient

logger = logging.getLogger(__name__)

# Only allowed remote base paths for uploads/downloads
ALLOWED_REMOTE_PATHS = [
    "/tmp/",
    "/logs/brasil/",
    "/app/brasil/scripts/",
    "/data/brasil/",
]

MAX_UPLOAD_SIZE_MB = 50


class SftpService:
    """
    Secure SFTP operations via paramiko.
    Only allowed paths can be accessed.
    """

    def __init__(self, client: SshClient):
        self._client    = client
        self._audit_log: List[Dict[str, Any]] = []

    def upload(
        self,
        local_path:  str,
        remote_path: str,
    ) -> Dict[str, Any]:
        """
        Upload a local file to a whitelisted remote path.

        Returns {success, remote_path, size_bytes, error}
        """
        local = Path(local_path)
        if not local.exists():
            return {"success": False, "error": f"Local file not found: {local_path}"}

        # Validate remote path
        try:
            self._validate_remote_path(remote_path)
        except ValueError as e:
            return {"success": False, "error": str(e)}

        # Check file size
        size_bytes = local.stat().st_size
        if size_bytes > MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            return {
                "success": False,
                "error":   f"File too large: {size_bytes / 1024 / 1024:.1f} MB > {MAX_UPLOAD_SIZE_MB} MB limit",
            }

        t0 = time.perf_counter()
        audit = {
            "operation":   "upload",
            "local_path":  str(local),
            "remote_path": remote_path,
            "host":        self._client.host,
            "timestamp":   time.time(),
            "success":     False,
        }

        try:
            sftp = self._client.get_sftp()
            sftp.put(str(local), remote_path)
            sftp.close()

            duration = round((time.perf_counter() - t0) * 1000, 1)
            audit.update({"success": True, "duration_ms": duration, "size_bytes": size_bytes})
            logger.info(
                f"[SftpService] Uploaded {local.name} -> {remote_path} "
                f"({size_bytes} bytes, {duration} ms)"
            )
            return {
                "success":     True,
                "remote_path": remote_path,
                "size_bytes":  size_bytes,
                "duration_ms": duration,
                "error":       None,
            }

        except Exception as e:
            audit["error"] = str(e)
            logger.error(f"[SftpService] Upload failed: {e}")
            return {"success": False, "error": str(e)}

        finally:
            self._audit_log.append(audit)

    def download(
        self,
        remote_path: str,
        local_path:  str,
    ) -> Dict[str, Any]:
        """Download a remote file to a local path."""
        try:
            self._validate_remote_path(remote_path)
        except ValueError as e:
            return {"success": False, "error": str(e)}

        t0    = time.perf_counter()
        audit = {
            "operation":   "download",
            "remote_path": remote_path,
            "local_path":  local_path,
            "host":        self._client.host,
            "timestamp":   time.time(),
            "success":     False,
        }

        try:
            sftp = self._client.get_sftp()
            sftp.get(remote_path, local_path)
            sftp.close()

            size_bytes = Path(local_path).stat().st_size
            duration   = round((time.perf_counter() - t0) * 1000, 1)
            audit.update({"success": True, "size_bytes": size_bytes, "duration_ms": duration})
            logger.info(f"[SftpService] Downloaded {remote_path} -> {local_path}")
            return {
                "success":    True,
                "local_path": local_path,
                "size_bytes": size_bytes,
                "error":      None,
            }

        except Exception as e:
            audit["error"] = str(e)
            return {"success": False, "error": str(e)}

        finally:
            self._audit_log.append(audit)

    def list_remote(self, remote_dir: str) -> Dict[str, Any]:
        """List files in a whitelisted remote directory."""
        try:
            self._validate_remote_path(remote_dir + "/")
        except ValueError as e:
            return {"success": False, "error": str(e), "files": []}

        try:
            sftp  = self._client.get_sftp()
            files = sftp.listdir_attr(remote_dir)
            sftp.close()
            return {
                "success": True,
                "files": [
                    {"name": f.filename, "size": f.st_size, "mtime": f.st_mtime}
                    for f in files
                ],
            }
        except Exception as e:
            return {"success": False, "error": str(e), "files": []}

    @staticmethod
    def _validate_remote_path(path: str) -> None:
        """Ensure the remote path is under an allowed base."""
        for allowed in ALLOWED_REMOTE_PATHS:
            if path.startswith(allowed):
                return
        raise ValueError(
            f"Remote path '{path}' is not in the allowed list: {ALLOWED_REMOTE_PATHS}"
        )

    def get_audit_log(self) -> List[Dict[str, Any]]:
        return list(self._audit_log)
