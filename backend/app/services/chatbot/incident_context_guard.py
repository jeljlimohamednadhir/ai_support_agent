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
# R2-FIX: seuils abaissés — la phase DIAGNOSTIC doit accepter le maximum de blocs KB
# pour éviter que le LLM réponde sans contexte FR. Le filtrage fin se fait en RESOLUTION.
PHASE_SIMILARITY_THRESHOLDS: Dict[str, float] = {
    ConversationPhase.DIAGNOSTIC.value:    25.0,   # filet très large — attrape tous les candidats
    ConversationPhase.INVESTIGATION.value: 40.0,   # réduction progressive vers la cause racine
    ConversationPhase.RESOLUTION.value:    60.0,   # uniquement la procédure correspondante
    ConversationPhase.CLOSING.value:       None,   # pas de RAG en phase closing
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
          2. Blocks mentioning an excluded system are dropped (only when locked_systems set).
          3. Blocks that do not mention any locked system are dropped
             (SKIPPED in DIAGNOSTIC phase when locked_systems is empty — R2-FIX).
          4. Blocks below the phase similarity threshold are dropped
             (score=0 blocks always pass in DIAGNOSTIC phase — R2-FIX).
        """
        phase_value = self.phase.value if hasattr(self.phase, 'value') else str(self.phase)
        threshold = PHASE_SIMILARITY_THRESHOLDS.get(phase_value)
        is_diagnostic = (phase_value == ConversationPhase.DIAGNOSTIC.value)

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
            content_check = (block.get("content", "") + " " + block.get("title", ""))
            if (block.get("block_type") == "database_table"
                    or block.get("source_type") == "database_table"
                    or "Table BRASIL:" in content_check
                    or "Schéma BRASIL" in content_check):
                filtered.append(block)
                continue

            content_upper = content_check.upper()

            # Rule 2: drop blocks that mention an excluded system
            # Only when locked_systems is set.
            if self.locked_systems and any(sys in content_upper for sys in self.excluded_systems):
                logger.debug(
                    f"[ContextGuard] Dropped '{block.get('title', '')[:40]}' — excluded system"
                )
                continue

            # Rule 3: if locked_systems is set AND we are NOT in diagnostic phase,
            # keep only blocks mentioning a locked system.
            # R2-FIX: in DIAGNOSTIC phase we skip this rule entirely so the LLM
            # always gets KB context even when the system list is not yet locked.
            if self.locked_systems and not is_diagnostic:
                mentions_relevant = any(
                    sys.upper() in content_upper for sys in self.locked_systems
                )
                if not mentions_relevant:
                    logger.debug(
                        f"[ContextGuard] Dropped '{block.get('title', '')[:40]}' — no locked system"
                    )
                    continue

            # Rule 4: similarity threshold
            # R2-FIX: score=0 blocks are kept in DIAGNOSTIC phase (Qdrant may not set score).
            score = block.get("trust_score", block.get("score", 0))
            if isinstance(score, float) and score <= 1.0:
                score = score * 100.0
            # In diagnostic phase, only drop if score is explicitly non-zero and below threshold
            if not is_diagnostic and score < threshold:
                logger.debug(
                    f"[ContextGuard] Dropped '{block.get('title', '')[:40]}' — "
                    f"score {score:.1f} < {threshold}"
                )
                continue
            if is_diagnostic and score > 0 and score < threshold:
                logger.debug(
                    f"[ContextGuard] Kept '{block.get('title', '')[:40]}' despite "
                    f"score {score:.1f} < {threshold} (diagnostic phase)"
                )
                # Keep it anyway — diagnostic phase is permissive

            filtered.append(block)

        logger.info(
            f"[ContextGuard] {len(context_blocks)} blocks → {len(filtered)} after filtering "
            f"(phase={phase_value}, locked={self.locked_systems})"
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
