"""
command_executor.py
━━━━━━━━━━━━━━━━━━━
Execute ONLY whitelisted SSH commands via the SshClient.

Security:
  - Command name must exist in ALLOWED_COMMANDS
  - Parameters are sanitized via build_command_string()
  - Raw command strings from user input are REJECTED
  - Every execution is audit-logged
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Generator, List, Optional

from app.services.ssh_operations.client.ssh_client import SshClient, SshConnectionError
from app.services.ssh_operations.commands.ssh_command_registry import (
    ALLOWED_COMMANDS,
    build_command_string,
    get_command,
)
from app.services.live_diagnostics.models.evidence import EvidenceType, SshEvidence

logger = logging.getLogger(__name__)


class CommandExecutor:
    """
    Execute whitelisted SSH commands and return SshEvidence objects.
    """

    def __init__(self, client: SshClient):
        self._client    = client
        self._audit_log: List[Dict[str, Any]] = []

    def execute(
        self,
        command_name: str,
        params:       Dict[str, str] | None = None,
        timeout_s:    int | None = None,
    ) -> SshEvidence:
        """
        Execute a whitelisted command by name.

        Parameters
        ----------
        command_name : key in ALLOWED_COMMANDS
        params       : template substitution dict (sanitized by registry)
        timeout_s    : per-command timeout (overrides registry default)
        """
        cmd_def = get_command(command_name)
        if not cmd_def:
            raise ValueError(
                f"[CommandExecutor] Command '{command_name}' not in whitelist."
            )

        try:
            cmd_str = build_command_string(command_name, params or {})
        except ValueError as e:
            return self._error_evidence(command_name, str(e))

        eff_timeout = timeout_s or cmd_def.get("timeout_s", 30)
        t0 = time.perf_counter()

        audit = {
            "command_name": command_name,
            "params":       list((params or {}).keys()),   # keys only, not values
            "timestamp":    time.time(),
            "host":         self._client.host,
            "success":      False,
        }

        try:
            result = self._client.exec_command(cmd_str, timeout_s=eff_timeout)
            success = result.get("success", False)
            output  = result.get("output", "")
            error   = result.get("error", "")

            audit["success"]     = success
            audit["duration_ms"] = result.get("duration_ms", 0)

            confidence = 0.90 if success and output else 0.40

            return SshEvidence(
                evidence_type=EvidenceType.SSH,
                command_name=command_name,
                host=self._client.host,
                success=success,
                output=output[:4000],   # Hard cap — never expose huge outputs
                error=error[:500],
                duration_ms=result.get("duration_ms", 0),
                confidence=confidence,
                tags=cmd_def.get("tags", []),
            )

        except SshConnectionError as e:
            audit["error"] = str(e)
            return self._error_evidence(command_name, str(e))

        except Exception as e:
            logger.error(f"[CommandExecutor] Unexpected error: {e}")
            audit["error"] = str(e)
            return self._error_evidence(command_name, str(e))

        finally:
            self._audit_log.append(audit)
            logger.info(
                f"[CommandExecutor] {command_name} on {self._client.host} "
                f"-> {'OK' if audit['success'] else 'FAIL'}"
            )

    def execute_plan(
        self,
        command_names: List[str],
        params_map:    Dict[str, Dict[str, str]] | None = None,
    ) -> List[SshEvidence]:
        """Execute a list of whitelisted commands."""
        params_map = params_map or {}
        results = []
        for name in command_names:
            ev = self.execute(name, params_map.get(name, {}))
            results.append(ev)
        return results

    def stream(
        self,
        command_name: str,
        params:       Dict[str, str] | None = None,
        timeout_s:    int | None = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Stream command output line-by-line.

        Yields:
            {"type": "stream", "line": str}
        or
            {"type": "error", "error": str}
        """
        cmd_def = get_command(command_name)
        if not cmd_def:
            yield {"type": "error", "error": f"Command '{command_name}' not in whitelist."}
            return

        try:
            cmd_str = build_command_string(command_name, params or {})
        except ValueError as e:
            yield {"type": "error", "error": str(e)}
            return

        eff_timeout = timeout_s or cmd_def.get("timeout_s", 30)
        logger.info(f"[CommandExecutor] Streaming '{command_name}' on {self._client.host}")

        try:
            for line in self._client.stream_command(cmd_str, timeout_s=eff_timeout):
                yield {"type": "stream", "line": line}
        except Exception as e:
            yield {"type": "error", "error": str(e)}

    def get_audit_log(self) -> List[Dict[str, Any]]:
        return list(self._audit_log)

    @staticmethod
    def _error_evidence(command_name: str, error: str) -> SshEvidence:
        return SshEvidence(
            evidence_type=EvidenceType.SSH,
            command_name=command_name,
            host="unknown",
            success=False,
            output="",
            error=error,
            duration_ms=0.0,
            confidence=0.0,
        )
