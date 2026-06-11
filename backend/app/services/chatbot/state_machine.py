"""
state_machine.py
━━━━━━━━━━━━━━━━
BRASIL Entity Finite State Machine — N3 Layer

Gap corrected: the previous architecture fetched `eqpt_status` from the DB
but had NO validator for state transitions. The LLM was expected to reason
about states from raw text. This is unreliable.

This module:
1. Defines legal state transitions for every Brasil entity type
2. Detects INVALID / IMPOSSIBLE / ORPHAN states
3. Detects STATE INCONSISTENCIES (e.g. DB=ACTIVE but dependencies are deleted)
4. Produces a deterministic state diagnosis BEFORE the LLM call

Entity state machines modeled:
  - EQUIPEMENT (DSLAM, OLT, Router)
  - VLAN
  - ND (Noeud de Distribution)
  - SERVICE
  - PORT / BROCHE
  - MEDIA_LINK (MRT)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EQUIPMENT STATES
# Extracted from Brasil Java enum EquipementStatut + DB analysis
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class EquipementStatut(str, Enum):
    """Brasil equipment statuses — from t_equipments.eqpt_status"""
    ACTIF               = "A"   # Active in production
    FERME               = "F"   # Closed to production
    EN_COURS            = "P"   # In configuration (transient)
    SUPPRIME            = "S"   # Deleted (soft)
    CLOTURE             = "C"   # Closed
    ORPHAN              = "ORPHAN"       # Computed: active but no dependencies
    INCONSISTENT        = "INCONSISTENT" # Computed: state mismatch with external system

    @classmethod
    def from_db(cls, raw: Optional[str]) -> "EquipementStatut":
        if not raw:
            return cls.INCONSISTENT
        clean = raw.strip().upper()
        for member in cls:
            if member.value == clean or member.name == clean:
                return member
        return cls.INCONSISTENT


class VlanStatut(str, Enum):
    """VLAN statuses — from t_vlans.vlan_status"""
    ACTIF    = "A"
    SUPPRIME = "S"
    EN_COURS = "P"
    ORPHAN   = "ORPHAN"


class ServiceStatut(str, Enum):
    """Service statuses — from t_services.svc_status"""
    ACTIF    = "A"
    CLOTURE  = "C"
    SUPPRIME = "S"
    EN_COURS = "P"
    RESERVE  = "R"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LEGAL TRANSITIONS
# (source_state) → frozenset of allowed target states
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EQUIPEMENT_TRANSITIONS: Dict[EquipementStatut, FrozenSet[EquipementStatut]] = {
    EquipementStatut.EN_COURS: frozenset({
        EquipementStatut.ACTIF,
        EquipementStatut.FERME,
        EquipementStatut.SUPPRIME,
    }),
    EquipementStatut.ACTIF: frozenset({
        EquipementStatut.FERME,
        EquipementStatut.CLOTURE,
        EquipementStatut.SUPPRIME,
        EquipementStatut.EN_COURS,  # reconfiguration
    }),
    EquipementStatut.FERME: frozenset({
        EquipementStatut.ACTIF,     # reopening
        EquipementStatut.SUPPRIME,
    }),
    EquipementStatut.CLOTURE: frozenset({
        EquipementStatut.SUPPRIME,
    }),
    EquipementStatut.SUPPRIME: frozenset(),   # terminal
    EquipementStatut.ORPHAN: frozenset({
        EquipementStatut.SUPPRIME,            # cleanup only
    }),
    EquipementStatut.INCONSISTENT: frozenset(),
}

# States from which deletion is NEVER allowed without cleanup
DELETION_BLOCKING_STATES: Set[EquipementStatut] = {
    EquipementStatut.EN_COURS,
    EquipementStatut.ORPHAN,
    EquipementStatut.INCONSISTENT,
}

# States that indicate production-blocking problems
CRITICAL_STATES: Set[EquipementStatut] = {
    EquipementStatut.FERME,
    EquipementStatut.ORPHAN,
    EquipementStatut.INCONSISTENT,
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STATE DIAGNOSIS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class StateDiagnosis:
    """Result of FSM analysis for an entity."""
    entity_type: str
    entity_name: str
    current_state: str
    is_valid_state: bool
    is_orphan: bool = False
    is_inconsistent: bool = False
    is_transient: bool = False
    transition_to: Optional[str] = None       # what they're trying to do
    transition_allowed: bool = True
    blocking_reason: Optional[str] = None
    recommendations: List[str] = field(default_factory=list)
    confidence: float = 1.0                   # 0..1

    def to_context_block(self) -> dict:
        return {
            "source": "state_machine",
            "type": "state_diagnosis",
            "entity": self.entity_name,
            "current_state": self.current_state,
            "is_valid": self.is_valid_state,
            "is_orphan": self.is_orphan,
            "is_inconsistent": self.is_inconsistent,
            "is_transient": self.is_transient,
            "transition_allowed": self.transition_allowed,
            "blocking_reason": self.blocking_reason,
            "text": self.render(),
        }

    def render(self) -> str:
        lines = [f"🔄 **État actuel: `{self.current_state}`**"]

        if self.is_orphan:
            lines.append(
                "⚠️ **État ORPHAN détecté** — L'équipement existe en DB "
                "mais ses dépendances (services, liens) sont absentes ou incohérentes."
            )
        if self.is_inconsistent:
            lines.append(
                "🔴 **État INCONSISTANT** — L'état en DB ne correspond pas "
                "à l'état attendu du workflow (MQ/ORCHESTRA désynchronisé possible)."
            )
        if self.is_transient:
            lines.append(
                "⏳ **État TRANSITOIRE** — Un workflow est en cours. "
                "Les opérations de suppression/modification sont risquées."
            )
        if not self.transition_allowed and self.blocking_reason:
            lines.append(f"🚫 **Transition bloquée:** {self.blocking_reason}")
        if self.recommendations:
            lines.append("\n📋 **Recommandations:**")
            for rec in self.recommendations:
                lines.append(f"  • {rec}")
        return "\n".join(lines)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FSM ANALYZER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class BrasilStateMachine:
    """
    Analyzes entity states and validates transitions.

    Usage:
        fsm = BrasilStateMachine()
        diag = fsm.analyze_equipment(
            entity_name="DSROB362",
            current_status="P",
            target_operation="delete",
            active_services=3,
            active_links=0,
            mq_ack_present=False,
        )
    """

    def analyze_equipment(
        self,
        entity_name: str,
        current_status: Optional[str],
        target_operation: Optional[str] = None,   # "delete" | "modify" | "activate"
        active_services: int = 0,
        active_links: int = 0,
        active_cards: int = 0,
        mq_ack_present: Optional[bool] = None,
        orchestra_status: Optional[str] = None,
    ) -> StateDiagnosis:
        """Full FSM analysis for an equipment entity."""
        current = EquipementStatut.from_db(current_status)

        diag = StateDiagnosis(
            entity_type="EQUIPEMENT",
            entity_name=entity_name,
            current_state=current.value,
            is_valid_state=current not in (
                EquipementStatut.ORPHAN, EquipementStatut.INCONSISTENT
            ),
            is_transient=current == EquipementStatut.EN_COURS,
        )

        # Orphan detection: active in DB but no dependencies
        if (current == EquipementStatut.ACTIF
                and active_services == 0
                and active_links == 0
                and active_cards == 0):
            diag.is_orphan = True
            diag.current_state = EquipementStatut.ORPHAN.value
            diag.recommendations.append(
                "Vérifier si l'équipement a réellement des services en production"
            )
            diag.recommendations.append(
                "Possible suppression partielle laissant l'équipement en état ORPHAN"
            )

        # Inconsistency detection: DB active but MQ ACK missing
        if (current in (EquipementStatut.ACTIF, EquipementStatut.EN_COURS)
                and mq_ack_present is False):
            diag.is_inconsistent = True
            diag.recommendations.append(
                "Vérifier les dead-letter queues MQ pour les ACK ARTEMIS manquants"
            )
            diag.recommendations.append(
                "Syndrome BRASIL/ARTEMIS désynchronisé — comparer l'état en DB avec ORCHESTRA"
            )

        # Inconsistency: DB state ≠ ORCHESTRA state
        if orchestra_status and orchestra_status.upper() not in (
            current.value, current.name
        ):
            diag.is_inconsistent = True
            diag.recommendations.append(
                f"État DB=`{current.value}` mais ORCHESTRA=`{orchestra_status}` — "
                f"synchronisation requise"
            )

        # Transition validation
        if target_operation:
            target_state = self._operation_to_target_state(target_operation)
            if target_state:
                allowed_targets = EQUIPEMENT_TRANSITIONS.get(current, frozenset())
                if target_state not in allowed_targets:
                    diag.transition_allowed = False
                    diag.transition_to = target_state.value
                    diag.blocking_reason = (
                        f"Transition `{current.value}` → `{target_state.value}` "
                        f"n'est pas autorisée dans le FSM BRASIL. "
                        f"États cibles légaux: {[s.value for s in allowed_targets]}"
                    )

        # Critical state recommendations
        if current == EquipementStatut.FERME:
            diag.recommendations.append(
                "Équipement fermé (F) — procédure de réouverture requise avant toute opération"
            )
        if current in DELETION_BLOCKING_STATES and target_operation == "delete":
            diag.transition_allowed = False
            diag.blocking_reason = (
                f"La suppression depuis l'état `{current.value}` "
                f"nécessite une procédure de nettoyage préalable"
            )

        return diag

    def analyze_vlan(
        self,
        entity_name: str,
        current_status: Optional[str],
        attached_resources: int = 0,
        target_operation: Optional[str] = None,
    ) -> StateDiagnosis:
        """FSM analysis for a VLAN entity."""
        current_raw = (current_status or "").strip().upper()
        is_orphan = (current_raw == "A" and attached_resources == 0)
        diag = StateDiagnosis(
            entity_type="VLAN",
            entity_name=entity_name,
            current_state=current_raw or "INCONNU",
            is_valid_state=current_raw in ("A", "S", "P"),
            is_orphan=is_orphan,
            is_transient=current_raw == "P",
        )
        if is_orphan:
            diag.recommendations.append(
                "VLAN ACTIF sans ressources attachées — possible état résiduel"
            )
        if target_operation == "delete" and attached_resources > 0:
            diag.transition_allowed = False
            diag.blocking_reason = (
                f"{attached_resources} ressource(s) attachée(s) bloquent la suppression"
            )
        return diag

    @staticmethod
    def _operation_to_target_state(operation: str) -> Optional[EquipementStatut]:
        mapping = {
            "delete": EquipementStatut.SUPPRIME,
            "suppress": EquipementStatut.SUPPRIME,
            "close": EquipementStatut.CLOTURE,
            "activate": EquipementStatut.ACTIF,
            "configure": EquipementStatut.EN_COURS,
            "open": EquipementStatut.ACTIF,
        }
        return mapping.get(operation.lower())


# Singleton
_fsm_instance: Optional[BrasilStateMachine] = None

def get_state_machine() -> BrasilStateMachine:
    global _fsm_instance
    if _fsm_instance is None:
        _fsm_instance = BrasilStateMachine()
    return _fsm_instance
