"""
IncidentContextGuard
====================
Filters RAG context blocks so that only content relevant to the current
incident is injected into the LLM prompt.

Prevents:
  - Context mixing  (F2): unrelated incidents from other system domains
  - Hallucination   (F3): LLM mentioning systems not present in the ticket

Strategy:
  1. Extract systems mentioned in the first user message → locked_systems
  2. Build an exclusion list for every other known system
  3. Before each LLM call, filter context_blocks:
       - drop blocks that mention an excluded system
       - keep diagnostic_engine blocks unconditionally (they are pre-validated)
  4. Apply a per-phase cosine similarity threshold (similarity floor)
"""
from __future__ import annotations

import re
from typing import List, Dict, Optional

from app.services.nlp.diagnostic_behavior import KNOWN_SYSTEMS, ConversationPhase
from app.core.logging import get_logger

logger = get_logger(__name__)


# Per-phase minimum similarity score (0–100 scale matching orchestrator trust_score)
PHASE_SIMILARITY_THRESHOLDS: Dict[str, float] = {
    ConversationPhase.DIAGNOSTIC.value:    55.0,   # wide net – catch all candidates
    ConversationPhase.INVESTIGATION.value: 65.0,   # narrowing toward the root cause
    ConversationPhase.RESOLUTION.value:    70.0,   # only the matching procedure
    ConversationPhase.CLOSING.value:       None,   # no RAG at all in closing phase
}


class IncidentContextGuard:
    """
    Filters RAG context blocks to match the active incident scope.

    Usage::

        guard = IncidentContextGuard(
            locked_systems=["BRASIL", "ORRAHD"],
            excluded_systems=["SEBA", "42C", "VLAN"],
            phase=ConversationPhase.RESOLUTION,
        )
        filtered = guard.filter_context_blocks(raw_blocks)
    """

    def __init__(
        self,
        locked_systems: Optional[List[str]] = None,
        excluded_systems: Optional[List[str]] = None,
        phase: ConversationPhase = ConversationPhase.DIAGNOSTIC,
    ):
        self.locked_systems: List[str] = locked_systems or []
        self.excluded_systems: List[str] = [s.upper() for s in (excluded_systems or [])]
        self.phase = phase

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def filter_context_blocks(self, context_blocks: List[Dict]) -> List[Dict]:
        """
        Returns only the blocks that are relevant to the active incident.

        Rules (applied in order):
          1. diagnostic_engine blocks always pass — they are pre-validated by DiagnosticEngine.
          2. Blocks mentioning an excluded system are dropped.
          3. Blocks that do not mention any locked system are dropped (if locked_systems set).
          4. Blocks below the phase similarity threshold are dropped.
        """
        threshold = PHASE_SIMILARITY_THRESHOLDS.get(self.phase.value)
        if threshold is None:
            # CLOSING phase → no RAG blocks at all
            logger.debug("[ContextGuard] Phase CLOSING — all RAG blocks suppressed")
            return []

        filtered: List[Dict] = []
        for block in context_blocks:
            # Rule 1: always keep diagnostic engine blocks and DB schema blocks
            if block.get("source_type") == "diagnostic_engine":
                filtered.append(block)
                continue
            # DB schema blocks (database_table) are always relevant — never filtered by system
            # mode2 sets block["type"]="partial_canonical" but payload type="database_table"
            # We detect DB blocks via content heuristic ("Schéma BRASIL" or "Table BRASIL")
            content_check = (block.get("content", "") + " " + block.get("title", ""))
            if (block.get("block_type") == "database_table"
                    or block.get("source_type") == "database_table"
                    or "Table BRASIL:" in content_check
                    or "Schéma BRASIL" in content_check):
                filtered.append(block)
                continue

            content_upper = (block.get("content", "") + " " + block.get("title", "")).upper()

            # Rule 2: drop blocks that mention an excluded system
            # Only applies when locked_systems is set — if no system is locked we
            # cannot determine what's excluded, so we keep all blocks.
            if self.locked_systems and any(sys in content_upper for sys in self.excluded_systems):
                logger.debug(
                    f"[ContextGuard] Dropped block '{block.get('title', '')[:40]}' "
                    f"— mentions excluded system"
                )
                continue

            # Rule 3: if locked_systems is set, keep only blocks that mention one of them
            if self.locked_systems:
                mentions_relevant = any(
                    sys.upper() in content_upper for sys in self.locked_systems
                )
                if not mentions_relevant:
                    logger.debug(
                        f"[ContextGuard] Dropped block '{block.get('title', '')[:40]}' "
                        f"— no locked system mentioned"
                    )
                    continue

            # Rule 4: similarity threshold
            score = block.get("trust_score", block.get("score", 0))
            # Normalise: if score is 0–1 float, convert to 0–100
            if isinstance(score, float) and score <= 1.0:
                score = score * 100.0
            if score < threshold:
                logger.debug(
                    f"[ContextGuard] Dropped block '{block.get('title', '')[:40]}' "
                    f"— score {score:.1f} < threshold {threshold}"
                )
                continue

            filtered.append(block)

        logger.info(
            f"[ContextGuard] {len(context_blocks)} blocks → {len(filtered)} after filtering "
            f"(phase={self.phase.value}, locked={self.locked_systems})"
        )
        return filtered

    # ------------------------------------------------------------------
    # System extraction helpers
    # ------------------------------------------------------------------

    @staticmethod
    def extract_incident_systems(text: str) -> List[str]:
        """
        Returns the known systems explicitly mentioned in *text*.
        These become the allowed scope for RAG retrieval.
        """
        text_upper = text.upper()
        return [s for s in KNOWN_SYSTEMS if s.upper() in text_upper]

    @staticmethod
    def build_exclusion_list(mentioned: List[str]) -> List[str]:
        """
        Returns every known system that is NOT in *mentioned*.
        These systems will be excluded from the RAG context.
        """
        mentioned_upper = {s.upper() for s in mentioned}
        return [s for s in KNOWN_SYSTEMS if s.upper() not in mentioned_upper]

    # ------------------------------------------------------------------
    # Factory: build from first-turn ticket text
    # ------------------------------------------------------------------

    @classmethod
    def from_ticket_text(
        cls,
        ticket_text: str,
        phase: ConversationPhase = ConversationPhase.DIAGNOSTIC,
    ) -> "IncidentContextGuard":
        """
        Convenience factory: extract systems from the opening message and
        return a configured guard instance.
        """
        locked = cls.extract_incident_systems(ticket_text)
        excluded = cls.build_exclusion_list(locked)
        logger.info(
            f"[ContextGuard] Initialised — locked={locked}, excluded={excluded}"
        )
        return cls(
            locked_systems=locked,
            excluded_systems=excluded,
            phase=phase,
        )
