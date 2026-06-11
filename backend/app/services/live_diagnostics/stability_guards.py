"""
stability_guards.py
━━━━━━━━━━━━━━━━━━━
Production stability guards for the BRASIL forensic diagnostic platform.

Implements:
  - Timeout protections for SSH/DB/LLM calls
  - Anti-hallucination validation on LLM output
  - Graceful fallback responses
  - Response schema validation
  - Safe log parsing (never crashes)
  - Deterministic fallback explanations

Design: every guard is a standalone function/decorator that can wrap
existing pipeline steps without modifying them.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import re
import time
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TIMEOUT PROTECTION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Default timeouts (seconds)
TIMEOUT_SSH = 15
TIMEOUT_DB = 10
TIMEOUT_LLM = 30
TIMEOUT_QDRANT = 8


def with_timeout(timeout_seconds: float, fallback_value: Any = None):
    """
    Decorator: wraps an async function with a timeout.
    Returns fallback_value if timeout expires.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout_seconds,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    f"[TIMEOUT] {func.__name__} exceeded {timeout_seconds}s — returning fallback"
                )
                return fallback_value
            except Exception as e:
                logger.warning(f"[GUARD] {func.__name__} error: {e}")
                return fallback_value
        return wrapper
    return decorator


def sync_timeout(func: Callable, timeout_seconds: float, fallback: Any = None, *args, **kwargs) -> Any:
    """Run a sync function with a time budget. Uses threading for actual enforcement."""
    import concurrent.futures
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(func, *args, **kwargs)
            result = future.result(timeout=timeout_seconds)
            return result
    except concurrent.futures.TimeoutError:
        logger.warning(f"[TIMEOUT] {func.__name__} exceeded {timeout_seconds}s — returning fallback")
        return fallback
    except Exception as e:
        logger.warning(f"[GUARD] {func.__name__} error: {e}")
        return fallback


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ANTI-HALLUCINATION GUARDS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Patterns that indicate the LLM is hallucinating
_HALLUCINATION_PATTERNS = [
    # Inventing file paths that don't exist in BRASIL
    re.compile(r"(?:fichier|file)\s+['\"]?/(?:home|tmp|opt)/\w+", re.IGNORECASE),
    # Inventing specific IP addresses not in our known servers
    re.compile(r"\b(?:192\.168\.\d+\.\d+|10\.(?!103\.246)\d+\.\d+\.\d+)\b"),
    # Claiming to have "run" or "executed" something
    re.compile(r"j'ai (?:exécuté|lancé|run|vérifié en temps réel)", re.IGNORECASE),
    # Inventing timestamps that look too specific
    re.compile(r"à\s+\d{2}:\d{2}:\d{2}\.\d{3}\s+(?:le|du)\s+\d{2}/\d{2}/\d{4}"),
    # Claiming database results without evidence
    re.compile(r"(?:j'ai trouvé|résultat)\s+\d+\s+(?:lignes?|rows?|enregistrements?)\s+dans", re.IGNORECASE),
]

# Values that MUST be preserved exactly (never altered by LLM)
_PROTECTED_VALUE_RX = re.compile(
    r"(?:eqpt_id|eqpt_name|rpct_id|code_erreur|error_code)\s*[=:]\s*(\S+)"
)


def validate_llm_response(
    llm_output: str,
    context_values: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Validate LLM output against anti-hallucination rules.

    Returns:
        {
            "valid": True/False,
            "warnings": [...],
            "cleaned": <cleaned output or original>,
        }
    """
    warnings = []

    # Check hallucination patterns
    for pattern in _HALLUCINATION_PATTERNS:
        match = pattern.search(llm_output)
        if match:
            warnings.append(f"Potential hallucination: '{match.group()}'")

    # Check that protected values are preserved
    if context_values:
        for key, expected in context_values.items():
            if expected and expected in llm_output:
                continue
            # If the value should be there but was altered
            if expected and key in llm_output.lower():
                actual_match = re.search(
                    rf"{re.escape(key)}\s*[=:]\s*(\S+)", llm_output, re.IGNORECASE
                )
                if actual_match and actual_match.group(1) != expected:
                    warnings.append(
                        f"Value altered: {key}={actual_match.group(1)} (expected {expected})"
                    )

    return {
        "valid": len(warnings) == 0,
        "warnings": warnings,
        "cleaned": llm_output,
    }


def sanitize_for_llm(text: str, max_chars: int = 3000) -> str:
    """
    Sanitize text before sending to LLM.
    - Truncates safely
    - Removes binary/garbage
    - Normalizes whitespace
    """
    if not text:
        return ""
    # Remove null bytes and control chars (except newline/tab)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Truncate
    if len(text) > max_chars:
        text = text[:max_chars] + "\n[...tronqué pour limites TPM...]"
    return text


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GRACEFUL FALLBACK RESPONSES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_FALLBACK_RESPONSES = {
    "delete_equipment": (
        "🧠 **Diagnostic**\n"
        "La suppression de l'équipement est bloquée par des dépendances résiduelles.\n\n"
        "**Procédure recommandée:**\n"
        "1. Identifier l'eqpt_id: `SELECT eqpt_id FROM t_equipments WHERE eqpt_name = '<EQPT>';`\n"
        "2. Vérifier les dépendances: `SELECT * FROM t_res_prod_controlables WHERE a_eqpt_id = <ID>;`\n"
        "3. Nettoyer les références orphelines\n"
        "4. Relancer la suppression\n\n"
        "📋 Consulter FR-189 / FR-190 pour la procédure complète."
    ),
    "delete_vlan": (
        "🧠 **Diagnostic**\n"
        "Le VLAN ne peut être supprimé car des interfaces ou ressources sont encore actives.\n\n"
        "**Procédure recommandée:**\n"
        "1. Vérifier les VP/VC actifs sur le VLAN\n"
        "2. Libérer les ressources associées\n"
        "3. Relancer la suppression\n\n"
        "📋 Consulter FR-190."
    ),
    "generic": (
        "🧠 **Diagnostic**\n"
        "L'opération a échoué. Le système déterministe n'a pas pu identifier "
        "la cause racine avec certitude.\n\n"
        "**Actions recommandées:**\n"
        "1. Vérifier les logs sur le serveur BRASIL\n"
        "2. Consulter l'état de l'équipement dans la base\n"
        "3. Contacter l'équipe N3 si le problème persiste"
    ),
}


def get_fallback_response(intent: str, entity: Optional[str] = None) -> str:
    """Get a safe deterministic fallback response for a given intent."""
    template = _FALLBACK_RESPONSES.get(intent, _FALLBACK_RESPONSES["generic"])
    if entity:
        template = template.replace("<EQPT>", entity)
    return template


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RESPONSE SCHEMA VALIDATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

REQUIRED_RESPONSE_FIELDS = {"message", "sources", "confidence", "conversation_id"}


def validate_response_schema(response_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate the chat response has all required fields.
    Fills missing fields with safe defaults.
    """
    # Ensure message is never empty
    if not response_dict.get("message"):
        response_dict["message"] = get_fallback_response("generic")
        response_dict["_fallback_used"] = True

    # Ensure sources is a list
    if not isinstance(response_dict.get("sources"), list):
        response_dict["sources"] = []

    # Ensure confidence is valid
    conf = response_dict.get("confidence", 0)
    if not isinstance(conf, (int, float)) or conf < 0 or conf > 1:
        response_dict["confidence"] = 0.5

    # Ensure conversation_id exists
    if not response_dict.get("conversation_id"):
        import uuid
        response_dict["conversation_id"] = str(uuid.uuid4())

    return response_dict


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SAFE LOG PARSING WRAPPER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def safe_parse_logs(raw_output: str, max_lines: int = 200) -> List[str]:
    """
    Safely parse SSH log output into clean lines.
    - Removes binary garbage
    - Limits line count
    - Strips ANSI codes
    - Never raises
    """
    try:
        if not raw_output:
            return []
        # Remove ANSI escape codes
        clean = re.sub(r"\x1b\[[0-9;]*m", "", raw_output)
        # Remove null bytes
        clean = clean.replace("\x00", "")
        # Split lines
        lines = clean.split("\n")
        # Filter empty and too-short lines
        lines = [l.strip() for l in lines if l.strip() and len(l.strip()) > 5]
        return lines[:max_lines]
    except Exception:
        return []


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DB READ-ONLY ENFORCEMENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_DANGEROUS_SQL_PATTERNS = [
    re.compile(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE)\b", re.IGNORECASE),
    re.compile(r"\b(GRANT|REVOKE|EXECUTE)\b", re.IGNORECASE),
    re.compile(r";\s*\w", re.IGNORECASE),  # Multiple statements
]


def validate_sql_readonly(sql: str) -> bool:
    """
    Validates that a SQL query is read-only.
    Returns True if safe, False if dangerous.
    """
    if not sql:
        return True
    for pattern in _DANGEROUS_SQL_PATTERNS:
        if pattern.search(sql):
            logger.warning(f"[SQL-GUARD] Blocked dangerous SQL: {sql[:100]}")
            return False
    return True


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SSH RECONNECT SAFETY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class SSHHealthTracker:
    """
    Tracks SSH connection health per host.
    Implements circuit-breaker pattern: after N failures, skip the host.
    """

    def __init__(self, max_failures: int = 3, cooldown_seconds: float = 120):
        self._failures: Dict[str, int] = {}
        self._last_failure_time: Dict[str, float] = {}
        self._max_failures = max_failures
        self._cooldown = cooldown_seconds

    def record_success(self, host: str) -> None:
        self._failures[host] = 0

    def record_failure(self, host: str) -> None:
        self._failures[host] = self._failures.get(host, 0) + 1
        self._last_failure_time[host] = time.time()
        if self._failures[host] >= self._max_failures:
            logger.warning(f"[SSH-CIRCUIT-BREAKER] Host {host} marked unhealthy after {self._failures[host]} failures")

    def is_healthy(self, host: str) -> bool:
        """Check if host should be attempted."""
        failures = self._failures.get(host, 0)
        if failures < self._max_failures:
            return True
        # Check cooldown
        last = self._last_failure_time.get(host, 0)
        if time.time() - last > self._cooldown:
            # Reset after cooldown
            self._failures[host] = 0
            return True
        return False

    def get_status(self) -> Dict[str, str]:
        """Get health status for all known hosts."""
        status = {}
        for host in set(list(self._failures.keys()) + list(self._last_failure_time.keys())):
            if self.is_healthy(host):
                status[host] = "✅ healthy"
            else:
                status[host] = f"❌ unhealthy ({self._failures.get(host, 0)} failures)"
        return status


# Global SSH health tracker
ssh_health_tracker = SSHHealthTracker()
