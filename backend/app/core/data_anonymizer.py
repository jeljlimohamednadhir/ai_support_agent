"""
Data Anonymizer — LLM Call Protection
======================================
Intercepts sensitive data before any outbound LLM API call (Groq, OpenAI, etc.)
and restores original values in the LLM response.

Activated by default (ANONYMIZE_LLM_CALLS=true in settings).
Can be disabled per-environment via .env: ANONYMIZE_LLM_CALLS=false

Entities anonymized:
  - ND numbers          (ND-123456)            → [ND_01]
  - DSLAM / equipment   (LNTL01, LNTL01A)      → [DSLAM_01]
  - IPv4 addresses      (192.168.1.5)           → [IP_01]
  - IPv6 addresses                              → [IPV6_01]
  - MAC addresses       (aa:bb:cc:dd:ee:ff)     → [MAC_01]
  - Agent/user logins   (n.jeljli, p.dupont)   → [AGENT_01]
  - Order numbers       (CMD-78901, ORD-12345)  → [CMD_01]
  - Client identifiers  (CL-4521, CLI4521)      → [CLIENT_01]
  - NRO/NRA codes       (NRO-PARIS01)           → [NRO_01]
  - Phone numbers       (0612345678, +33...)    → [PHONE_01]

Design:
  - Stateless per-call: each anonymize() returns a fresh mapping dict
  - The mapping is passed back to restore() — no global state, thread-safe
  - Patterns ordered from most specific to least specific to avoid partial matches
  - Logging: counts of entities masked per call (never the values themselves)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Sensitivity patterns — (compiled_regex, token_prefix, description)
# Order matters: more specific patterns first.
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class _Pattern:
    regex: re.Pattern
    prefix: str       # e.g. "ND", "IP", "DSLAM"
    description: str  # for audit logs


_PATTERNS: list[_Pattern] = [
    # ── ND numbers (ND-123456 or ND123456) ──────────────────────────────────
    _Pattern(
        regex=re.compile(r"\bND[-_]?\d{4,10}\b", re.IGNORECASE),
        prefix="ND",
        description="Numéro ND",
    ),
    # ── Order / command numbers ──────────────────────────────────────────────
    _Pattern(
        regex=re.compile(r"\b(?:CMD|ORD|ORDER|COMMANDE)[-_]?\d{4,12}\b", re.IGNORECASE),
        prefix="CMD",
        description="Numéro de commande",
    ),
    # ── Client identifiers ───────────────────────────────────────────────────
    _Pattern(
        regex=re.compile(r"\bCLI?[-_]?\d{4,10}\b", re.IGNORECASE),
        prefix="CLIENT",
        description="Identifiant client",
    ),
    # ── IPv4 addresses ───────────────────────────────────────────────────────
    _Pattern(
        regex=re.compile(
            r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"
        ),
        prefix="IP",
        description="Adresse IPv4",
    ),
    # ── IPv6 addresses ───────────────────────────────────────────────────────
    _Pattern(
        regex=re.compile(
            r"\b(?:[0-9a-fA-F]{1,4}:){2,7}[0-9a-fA-F]{1,4}\b"
        ),
        prefix="IPV6",
        description="Adresse IPv6",
    ),
    # ── MAC addresses ────────────────────────────────────────────────────────
    _Pattern(
        regex=re.compile(
            r"\b(?:[0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2}\b"
        ),
        prefix="MAC",
        description="Adresse MAC",
    ),
    # ── NRO / NRA codes  (NRO-PARIS01, NRA_LYON02) ───────────────────────────
    _Pattern(
        regex=re.compile(r"\bNR[OA][-_]?[A-Z0-9]{2,12}\b", re.IGNORECASE),
        prefix="NRO",
        description="Code NRO/NRA",
    ),
    # ── DSLAM / equipment IDs  (4 uppercase letters + 2 digits + optional letter)
    # e.g. LNTL01, LNTL01A, MARS12, PARS01B
    _Pattern(
        regex=re.compile(r"\b[A-Z]{3,5}\d{2,4}[A-Z]?\b"),
        prefix="DSLAM",
        description="Identifiant équipement/DSLAM",
    ),
    # ── Agent/user login  (firstname.lastname, n.jeljli, p.dupont) ───────────
    _Pattern(
        regex=re.compile(r"\b[a-z]{1,3}\.[a-z]{2,20}\b"),
        prefix="AGENT",
        description="Login agent",
    ),
    # ── French phone numbers ─────────────────────────────────────────────────
    _Pattern(
        regex=re.compile(
            r"\b(?:\+33|0033|0)[1-9](?:[ .\-]?\d{2}){4}\b"
        ),
        prefix="PHONE",
        description="Numéro de téléphone",
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
# Mapping container
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class AnonymizationMapping:
    """
    Holds the token→original mapping for one LLM call.
    Thread-safe: created fresh per request, never shared.
    """
    _token_to_original: dict[str, str] = field(default_factory=dict)
    _original_to_token: dict[str, str] = field(default_factory=dict)
    _counters: dict[str, int] = field(default_factory=dict)

    def get_or_create(self, original: str, prefix: str) -> str:
        """Return existing token for `original` or create a new one."""
        if original in self._original_to_token:
            return self._original_to_token[original]
        idx = self._counters.get(prefix, 0) + 1
        self._counters[prefix] = idx
        token = f"[{prefix}_{idx:02d}]"
        self._original_to_token[original] = token
        self._token_to_original[token] = original
        return token

    def restore(self, text: str) -> str:
        """Replace all tokens in text with their original values."""
        for token, original in self._token_to_original.items():
            text = text.replace(token, original)
        return text

    @property
    def stats(self) -> dict[str, int]:
        return dict(self._counters)

    @property
    def is_empty(self) -> bool:
        return len(self._original_to_token) == 0


# ─────────────────────────────────────────────────────────────────────────────
# Main anonymizer
# ─────────────────────────────────────────────────────────────────────────────

class DataAnonymizer:
    """
    Anonymizes sensitive data in text before sending to the LLM API.

    Usage::

        mapping = AnonymizationMapping()
        clean_prompt = anonymizer.anonymize(raw_prompt, mapping)
        clean_system = anonymizer.anonymize(raw_system, mapping)

        response = llm_api.call(clean_prompt, clean_system)

        restored_response = anonymizer.restore(response, mapping)
    """

    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    # ── Public API ───────────────────────────────────────────────────────────

    def anonymize(self, text: str | None, mapping: AnonymizationMapping) -> str:
        """
        Replace sensitive entities in `text` with opaque tokens.
        Modifies `mapping` in place; returns the sanitized text.
        """
        if not self.enabled or not text:
            return text or ""

        result = text
        for pat in _PATTERNS:
            result = pat.regex.sub(
                lambda m, p=pat, mp=mapping: mp.get_or_create(m.group(0), p.prefix),
                result,
            )
        return result

    def anonymize_messages(
        self,
        messages: list[dict[str, Any]],
        mapping: AnonymizationMapping,
    ) -> list[dict[str, Any]]:
        """
        Anonymize the `content` field of each message dict in place (copy).
        Used for conversation_history before sending to the LLM.
        """
        if not self.enabled:
            return messages
        result = []
        for msg in messages:
            content = msg.get("content", "")
            clean = self.anonymize(content, mapping) if isinstance(content, str) else content
            result.append({**msg, "content": clean})
        return result

    def restore(self, text: str | None, mapping: AnonymizationMapping) -> str:
        """
        Replace tokens in the LLM response with original values.
        No-op if mapping is empty or anonymization is disabled.
        """
        if not self.enabled or not text or mapping.is_empty:
            return text or ""
        return mapping.restore(text)

    def log_stats(self, mapping: AnonymizationMapping, call_site: str = "") -> None:
        """Log a summary of what was masked (counts only, never values)."""
        if mapping.is_empty:
            return
        parts = [f"{k}×{v}" for k, v in mapping.stats.items()]
        site = f"[{call_site}] " if call_site else ""
        logger.info(f"[Anonymizer] {site}Entités masquées avant appel LLM: {', '.join(parts)}")


# ── Singleton ────────────────────────────────────────────────────────────────
# Reads ANONYMIZE_LLM_CALLS from settings (default=True).
# To disable: add ANONYMIZE_LLM_CALLS=false in backend/.env

def _make_anonymizer() -> DataAnonymizer:
    try:
        from app.core.config import settings
        return DataAnonymizer(enabled=settings.ANONYMIZE_LLM_CALLS)
    except Exception:
        return DataAnonymizer(enabled=True)


data_anonymizer = _make_anonymizer()
