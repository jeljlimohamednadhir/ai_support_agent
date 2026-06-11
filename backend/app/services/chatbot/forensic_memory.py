"""
forensic_memory.py
━━━━━━━━━━━━━━━━━━
Cross-turn forensic memory for the N3 chatbot.

Persists across conversation turns:
  - Last diagnostic bundle (evidence, DB state, logs)
  - Last resolved intent + entity
  - Evidence provenance chain
  - Operation context (intent → operation path)
  - Reasoning trace

This allows follow-up questions like:
  "montre les logs"
  "quelle contrainte bloque ?"
  "quelle FR appliquer ?"
WITHOUT restarting the entire diagnostic pipeline.

Thread-safe, TTL-aware, bounded memory.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Max conversations to keep in memory (LRU eviction)
_MAX_CONVERSATIONS = 200
# TTL for conversation memory (seconds) — 2 hours
_CONVERSATION_TTL = 7200


@dataclass
class ForensicSnapshot:
    """
    A snapshot of forensic state from a single diagnostic turn.
    Immutable after creation — new turns create new snapshots.
    """
    turn_idx: int
    intent: str = ""
    entity: str = ""
    operation: str = ""

    # Evidence pointers (not the full data — just references)
    has_db_evidence: bool = False
    has_log_evidence: bool = False
    has_code_evidence: bool = False
    has_fr_evidence: bool = False

    # Lightweight summaries
    db_tables_found: List[str] = field(default_factory=list)
    exceptions_detected: List[str] = field(default_factory=list)
    log_files_searched: List[str] = field(default_factory=list)
    fr_ids: List[str] = field(default_factory=list)
    blocking_conditions: List[str] = field(default_factory=list)

    # Full cached objects (for follow-up reuse)
    reasoning_trace: Dict[str, Any] = field(default_factory=dict)
    bundle_ref: Optional[Any] = None  # DiagnosticBundle reference

    created_at: float = field(default_factory=time.time)


class ForensicMemory:
    """
    Per-conversation forensic memory.

    Stores ordered snapshots of diagnostic evidence across turns.
    Supports:
      - get_last_snapshot() — most recent diagnostic evidence
      - get_entity() — persisted entity across turns
      - get_intent() — persisted intent across turns
      - get_all_exceptions() — accumulated exceptions
      - get_reasoning_trace() — last reasoning trace for follow-ups
    """

    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id
        self.snapshots: List[ForensicSnapshot] = []
        self.created_at = time.time()
        self.last_accessed = time.time()

    def record_diagnostic(
        self,
        turn_idx: int,
        intent: str = "",
        entity: str = "",
        operation: str = "",
        reasoning_trace: Optional[Dict] = None,
        bundle: Optional[Any] = None,
        db_tables: Optional[List[str]] = None,
        exceptions: Optional[List[str]] = None,
        log_files: Optional[List[str]] = None,
        fr_ids: Optional[List[str]] = None,
        blocking_conditions: Optional[List[str]] = None,
    ) -> ForensicSnapshot:
        """Record a new diagnostic snapshot for this turn."""
        snapshot = ForensicSnapshot(
            turn_idx=turn_idx,
            intent=intent,
            entity=entity,
            operation=operation,
            has_db_evidence=bundle is not None and hasattr(bundle, "db_evidence") and bool(bundle.db_evidence),
            has_log_evidence=bundle is not None and hasattr(bundle, "log_evidence") and bool(bundle.log_evidence),
            has_code_evidence=bool(blocking_conditions),
            has_fr_evidence=bool(fr_ids),
            db_tables_found=db_tables or [],
            exceptions_detected=exceptions or [],
            log_files_searched=log_files or [],
            fr_ids=fr_ids or [],
            blocking_conditions=blocking_conditions or [],
            reasoning_trace=reasoning_trace or {},
            bundle_ref=bundle,
        )
        self.snapshots.append(snapshot)
        self.last_accessed = time.time()

        # Keep max 10 snapshots per conversation
        if len(self.snapshots) > 10:
            # Drop oldest, but keep bundle_ref=None to free memory
            old = self.snapshots.pop(0)
            old.bundle_ref = None

        return snapshot

    def get_last_snapshot(self) -> Optional[ForensicSnapshot]:
        self.last_accessed = time.time()
        return self.snapshots[-1] if self.snapshots else None

    def get_entity(self) -> str:
        """Return the most recently known entity across all turns."""
        for snap in reversed(self.snapshots):
            if snap.entity:
                return snap.entity
        return ""

    def get_intent(self) -> str:
        """Return the most recently known intent."""
        for snap in reversed(self.snapshots):
            if snap.intent:
                return snap.intent
        return ""

    def get_all_exceptions(self) -> List[str]:
        """Accumulate all unique exceptions across turns."""
        seen = set()
        result = []
        for snap in self.snapshots:
            for exc in snap.exceptions_detected:
                if exc not in seen:
                    seen.add(exc)
                    result.append(exc)
        return result

    def get_reasoning_trace(self) -> Dict[str, Any]:
        """Return the last reasoning trace for follow-up handler reuse."""
        for snap in reversed(self.snapshots):
            if snap.reasoning_trace:
                return snap.reasoning_trace
        return {}

    def get_last_bundle(self) -> Optional[Any]:
        """Return the last DiagnosticBundle for follow-up reuse."""
        for snap in reversed(self.snapshots):
            if snap.bundle_ref is not None:
                return snap.bundle_ref
        return None

    def get_evidence_summary(self) -> str:
        """Compact summary of all evidence collected across turns."""
        if not self.snapshots:
            return "Aucune preuve collectée"
        last = self.snapshots[-1]
        parts = []
        if last.has_db_evidence:
            parts.append(f"DB: {', '.join(last.db_tables_found[:3])}" if last.db_tables_found else "DB: ✅")
        if last.has_log_evidence:
            parts.append(f"Logs: {', '.join(last.log_files_searched[:2])}" if last.log_files_searched else "Logs: ✅")
        if last.exceptions_detected:
            parts.append(f"Exceptions: {len(last.exceptions_detected)}")
        if last.fr_ids:
            parts.append(f"FR: {', '.join(last.fr_ids[:2])}")
        return " | ".join(parts) if parts else "Diagnostic lancé (sans preuve)"

    def is_expired(self) -> bool:
        return (time.time() - self.last_accessed) > _CONVERSATION_TTL


class ForensicMemoryStore:
    """
    Global thread-safe store for forensic memories.
    Implements TTL eviction and bounded size.
    """

    def __init__(self, max_size: int = _MAX_CONVERSATIONS):
        self._store: Dict[str, ForensicMemory] = {}
        self._lock = threading.Lock()
        self._max_size = max_size

    def get_or_create(self, conversation_id: str) -> ForensicMemory:
        with self._lock:
            self._evict_expired()
            if conversation_id not in self._store:
                if len(self._store) >= self._max_size:
                    self._evict_oldest()
                self._store[conversation_id] = ForensicMemory(conversation_id)
            mem = self._store[conversation_id]
            mem.last_accessed = time.time()
            return mem

    def get(self, conversation_id: str) -> Optional[ForensicMemory]:
        with self._lock:
            mem = self._store.get(conversation_id)
            if mem and not mem.is_expired():
                mem.last_accessed = time.time()
                return mem
            elif mem:
                del self._store[conversation_id]
            return None

    def delete(self, conversation_id: str) -> None:
        with self._lock:
            self._store.pop(conversation_id, None)

    def _evict_expired(self) -> None:
        expired = [cid for cid, mem in self._store.items() if mem.is_expired()]
        for cid in expired:
            del self._store[cid]

    def _evict_oldest(self) -> None:
        if not self._store:
            return
        oldest_id = min(self._store, key=lambda k: self._store[k].last_accessed)
        del self._store[oldest_id]

    @property
    def size(self) -> int:
        return len(self._store)


# ── Singleton ─────────────────────────────────────────────────────────────────
forensic_memory_store = ForensicMemoryStore()
