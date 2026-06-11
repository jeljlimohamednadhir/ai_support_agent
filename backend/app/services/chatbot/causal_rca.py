"""
causal_rca.py
━━━━━━━━━━━━━
Causal Root Cause Analysis Engine — N3 Layer

Gap corrected: The multi_source_correlator.py fuses hypotheses from multiple
sources using keyword matching + confidence averaging. This is FUSION, not
CAUSAL REASONING. It cannot:
  - traverse dependency chains
  - infer upstream causes from downstream symptoms
  - score hypotheses by causal plausibility
  - produce ordered causal chains: Symptom → Failure Point → Root Cause → Action

This module implements a proper causal RCA engine:
  1. CausalNode: entity in the causal graph (equipment, service, workflow step)
  2. CausalEdge: directed dependency with failure propagation weight
  3. CausalGraph: Brasil operational dependency graph (static + dynamic)
  4. RCAEngine: traverses graph from symptom evidence to root cause

Architecture:
  Evidence (DB + Logs + Sync anomalies + Rule violations)
  → Symptom nodes activated
  → Backward traversal: which upstream nodes CAUSED this symptom?
  → Hypothesis scoring: P(cause | evidence) ∝ edge_weight × evidence_strength
  → Ordered RCA chain output

The static graph encodes KNOWN Brasil operational dependencies:
  - Equipment → Services → Ports (cardinality constraints)
  - Equipment → MRT Links (deletion dependency)
  - Equipment → VLAN attachments
  - Workflow step N → Step N+1 (sequential dependency)
  - DB state → MQ event → ORCHESTRA state (sync chain)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CAUSAL GRAPH NODES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class CausalNode:
    """A node in the operational dependency graph."""
    node_id: str
    label: str
    node_type: str               # "entity" | "workflow_step" | "state" | "external_system"
    description: str = ""
    # Evidence signals that activate this node
    activation_signals: List[str] = field(default_factory=list)


@dataclass
class CausalEdge:
    """A directed causal dependency edge."""
    source: str          # node_id of the cause
    target: str          # node_id of the effect (symptom)
    relation: str        # "blocks" | "requires" | "propagates_to" | "sync_dependency"
    weight: float = 0.8  # failure propagation probability
    description: str = ""


@dataclass
class CausalHypothesis:
    """A scored root cause hypothesis."""
    root_cause_id: str
    root_cause_label: str
    confidence: float
    evidence_chain: List[str]    # ordered chain: root_cause → ... → symptom
    supporting_evidence: List[str]
    corrective_action: str
    fr_id: Optional[str] = None

    def render(self) -> str:
        chain_str = " → ".join(self.evidence_chain)
        lines = [
            f"🔍 **Hypothèse RCA** (confiance: {self.confidence:.0%})",
            f"**Cause racine:** {self.root_cause_label}",
            f"**Chaîne causale:** `{chain_str}`",
        ]
        if self.supporting_evidence:
            lines.append("**Preuves:**")
            for ev in self.supporting_evidence:
                lines.append(f"  • {ev}")
        lines.append(f"\n🔧 **Action corrective:** {self.corrective_action}")
        if self.fr_id:
            lines.append(f"📋 Référence: `{self.fr_id}`")
        return "\n".join(lines)


@dataclass
class RCAResult:
    """Result of full RCA traversal."""
    entity_name: Optional[str]
    symptom_description: str
    hypotheses: List[CausalHypothesis] = field(default_factory=list)
    top_hypothesis: Optional[CausalHypothesis] = None

    def to_context_block(self) -> dict:
        return {
            "source": "causal_rca",
            "type": "rca_result",
            "entity": self.entity_name,
            "hypothesis_count": len(self.hypotheses),
            "top_confidence": self.top_hypothesis.confidence if self.top_hypothesis else 0,
            "text": self.render(),
        }

    def render(self) -> str:
        if not self.hypotheses:
            return ""
        lines = [f"🧠 **Analyse Cause Racine — {self.entity_name or 'Entité'}**\n"]
        for i, h in enumerate(self.hypotheses[:3], 1):
            lines.append(f"**#{i}** {h.render()}\n")
        return "\n".join(lines)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STATIC CAUSAL GRAPH — BRASIL OPERATIONAL DEPENDENCIES
# Extracted from Java service call chains + incident analysis
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_STATIC_NODES: List[CausalNode] = [
    # Equipment lifecycle nodes
    CausalNode("eqpt_has_active_services", "Services actifs sur équipement",
               "state", "t_services.svc_status NOT IN ('C','S')",
               ["active_services_count > 0", "svc_status=A"]),
    CausalNode("eqpt_has_mrt_links", "Liens MRT actifs sur équipement",
               "state", "t_media_links.mdlk_status != 'S'",
               ["active_links_count > 0", "mdlk_status!=S"]),
    CausalNode("eqpt_has_cards", "Cartes actives sur équipement",
               "state", "t_cards.eqpt_id_delocalized = eqpt_id",
               ["active_cards_count > 0"]),
    CausalNode("eqpt_closed", "Équipement fermé (statut F)",
               "state", "t_equipments.eqpt_status = 'F'",
               ["eqpt_status=F", "FERME", "erreur 1300"]),
    CausalNode("eqpt_transient", "Équipement en cours de configuration",
               "state", "t_equipments.eqpt_status = 'P'",
               ["eqpt_status=P", "EN_COURS"]),

    # Deletion blocking causes
    CausalNode("deletion_blocked_services", "Suppression bloquée: services non clôturés",
               "workflow_step", "EquipementService.validateDeletion() throws if services active",
               ["suppression impossible", "service actif", "EQPT_DEL_001"]),
    CausalNode("deletion_blocked_links", "Suppression bloquée: liens MRT",
               "workflow_step", "EquipementService.validateDeletion() checks t_media_links",
               ["lien MRT", "media link", "EQPT_DEL_002"]),

    # Sync/MQ nodes
    CausalNode("mq_ack_missing", "ACK MQ absent",
               "state", "MQ broker did not receive ACK from ARTEMIS",
               ["MQ ACK absent", "ACK timeout", "JMSException", "ARTEMIS timeout"]),
    CausalNode("orchestra_desync", "Désynchronisation ORCHESTRA",
               "state", "ORCHESTRA state ≠ BRASIL DB state",
               ["ORCHESTRA", "désynchronisé", "SYNC_DB_ORCH"]),
    CausalNode("42c_desync", "Désynchronisation 42C",
               "state", "42C state ≠ BRASIL DB state",
               ["42C", "AffectationException", "incohérence 42C"]),
    CausalNode("dlq_accumulation", "Dead-letter queue accumulée",
               "state", "Messages non consommés dans la DLQ",
               ["dead.letter", "DLQ", "message non consommé"]),
    CausalNode("mq_broker_down", "Broker MQ indisponible",
               "external_system", "ActiveMQ / AMQP broker unreachable",
               ["JMSException", "broker unreachable", "ConnectionFactory failed"]),

    # Exception-level nodes
    CausalNode("exception_1300", "Erreur 1300 — Noeud IP absent",
               "state", "ConstraintViolationException + eqpt_status=F",
               ["erreur 1300", "1300", "ConstraintViolationException", "eqpt_status=F"]),
    CausalNode("exception_4002", "Erreur interne 4002",
               "state", "BrasilInternalException during service activation",
               ["B4002", "4002", "BrasilInternalException"]),
    CausalNode("exception_42c", "Erreur affectation 42C",
               "state", "AffectationException — incohérence BRASIL/42C",
               ["42C", "AffectationException", "DSLAM-AFFECTATION"]),
    CausalNode("exception_broche", "Erreur broche 300/327",
               "state", "BrocheSearchException — port non attribuable",
               ["erreur 300", "erreur 327", "BrocheSearchException", "port_attribuable=false"]),

    # Final symptom nodes (what the user observes)
    CausalNode("symptom_delete_fails", "Échec de suppression équipement",
               "entity", "User cannot delete equipment",
               ["suppression impossible", "impossible de supprimer", "delete fails"]),
    CausalNode("symptom_workflow_stuck", "Workflow bloqué",
               "entity", "Workflow stuck in intermediate state",
               ["bloqué", "en attente", "workflow stuck", "workflow bloqué"]),
    CausalNode("symptom_sync_failure", "Échec de synchronisation",
               "entity", "Sync failed between systems",
               ["désynchronisé", "sync failure", "état incohérent"]),
]

_NODES: Dict[str, CausalNode] = {n.node_id: n for n in _STATIC_NODES}

_STATIC_EDGES: List[CausalEdge] = [
    # Equipment deletion failure causes
    CausalEdge("eqpt_has_active_services", "deletion_blocked_services",
               "blocks", 0.97, "Services actifs → validateDeletion() throws"),
    CausalEdge("eqpt_has_mrt_links", "deletion_blocked_links",
               "blocks", 0.95, "Liens MRT actifs → validateDeletion() throws"),
    CausalEdge("deletion_blocked_services", "symptom_delete_fails",
               "propagates_to", 0.99),
    CausalEdge("deletion_blocked_links", "symptom_delete_fails",
               "propagates_to", 0.99),
    CausalEdge("eqpt_closed", "symptom_delete_fails",
               "blocks", 0.90, "Statut F → cannot delete without reopening"),
    CausalEdge("eqpt_transient", "symptom_delete_fails",
               "blocks", 0.75, "Statut P → workflow in progress"),
    CausalEdge("exception_1300", "symptom_delete_fails",
               "propagates_to", 0.95),

    # Sync failure causes
    CausalEdge("mq_broker_down", "mq_ack_missing",
               "propagates_to", 0.95, "Broker KO → aucun ACK possible"),
    CausalEdge("mq_ack_missing", "orchestra_desync",
               "sync_dependency", 0.88, "Pas d'ACK → ORCHESTRA pas notifié"),
    CausalEdge("mq_ack_missing", "symptom_sync_failure",
               "propagates_to", 0.92),
    CausalEdge("orchestra_desync", "symptom_sync_failure",
               "propagates_to", 0.90),
    CausalEdge("42c_desync", "symptom_sync_failure",
               "propagates_to", 0.88),
    CausalEdge("dlq_accumulation", "mq_ack_missing",
               "propagates_to", 0.85, "DLQ pleine → messages bloqués"),

    # Workflow stuck causes
    CausalEdge("mq_ack_missing", "symptom_workflow_stuck",
               "propagates_to", 0.90),
    CausalEdge("eqpt_transient", "symptom_workflow_stuck",
               "propagates_to", 0.80),
    CausalEdge("42c_desync", "exception_42c",
               "propagates_to", 0.92),
    CausalEdge("exception_42c", "symptom_workflow_stuck",
               "propagates_to", 0.85),
]

# ── Extended nodes (EPC FSM, MakingFile, ES Script, retry, orphan) ──────────
_EXTENDED_NODES: List[CausalNode] = [
    CausalNode("epc_fsm_invalid_transition", "Transition FSM EPC invalide",
               "state", "EPC moved to illegal state (e.g. C → X directly)",
               ["epcv_currentstate", "FSM invalid", "EPC state machine", "mouvement EPC"]),
    CausalNode("making_file_blocked", "MakingFile bloqué en IN_PROGRESS",
               "state", "t_making_file.mkfl_state stuck at 2 (IN_PROGRESS)",
               ["PARTLY_CONFIGURED", "makingfile 2", "IN_PROGRESS making", "mkfl_state=2"]),
    CausalNode("making_file_partly", "MakingFile partiellement configuré",
               "state", "t_making_file.mkfl_state = 3 (PARTLY_CONFIGURED)",
               ["PARTLY_CONFIGURED", "mkfl_state=3", "configuration partielle"]),
    CausalNode("es_script_timeout", "Script ES bloqué (état RUNNING)",
               "state", "t_tp_es_scripts.es_state = 1 (RUNNING) for too long",
               ["script RUNNING", "es_state=1", "script bloqué", "script ES en attente"]),
    CausalNode("es_script_error", "Script ES en erreur",
               "state", "t_tp_es_scripts.es_state = 2 (ERROR)",
               ["script ERROR", "es_state=2", "script ES erreur"]),
    CausalNode("nd_orphan", "ND sans équipement associé",
               "state", "ND present in t_nd_infra with no linked DSLAM in t_mrt_access_dslams",
               ["ND orphelin", "ND sans DSLAM", "noeud désaffecté"]),
    CausalNode("vlan_orphan", "VLAN orphelin (référencé mais absent)",
               "state", "VLAN in t_connectors but not in t_vlan",
               ["VLAN 0", "VLAN orphelin", "connecteur VLAN absent", "ConnectorCreationVlanException"]),
    CausalNode("retry_loop_detected", "Boucle de retry active",
               "state", "Same operation retried 3+ times without success",
               ["retry loop", "boucle retry", "tentatives répétées", "retry count"]),
    CausalNode("partial_rollback", "Rollback partiel détecté",
               "state", "Transaction rolled back but some side effects persisted",
               ["rollback partiel", "partial rollback", "état incohérent après rollback"]),
    CausalNode("ghost_service_node", "Service fantôme (DB≠réseau)",
               "state", "Service exists in t_services but not provisioned on network",
               ["service fantôme", "ghost service", "ressource fantôme"]),
]

_EXTENDED_EDGES: List[CausalEdge] = [
    # EPC FSM failures
    CausalEdge("mq_ack_missing", "epc_fsm_invalid_transition",
               "propagates_to", 0.85, "ACK manquant → EPC FSM ne passe pas à l'état suivant"),
    CausalEdge("epc_fsm_invalid_transition", "symptom_workflow_stuck",
               "propagates_to", 0.93),
    CausalEdge("42c_desync", "epc_fsm_invalid_transition",
               "propagates_to", 0.80, "42C désynchronisé → EPC state invalide"),

    # MakingFile blocking
    CausalEdge("es_script_error", "making_file_blocked",
               "blocks", 0.88, "Script ES en erreur → MakingFile ne progresse pas"),
    CausalEdge("es_script_timeout", "making_file_blocked",
               "blocks", 0.85, "Script ES bloqué → MakingFile suspendu"),
    CausalEdge("making_file_blocked", "symptom_workflow_stuck",
               "propagates_to", 0.95),
    CausalEdge("making_file_partly", "symptom_workflow_stuck",
               "propagates_to", 0.75),
    CausalEdge("mq_ack_missing", "making_file_blocked",
               "propagates_to", 0.70, "ACK absent → étape MakingFile non confirmée"),

    # ES Script failures
    CausalEdge("es_script_timeout", "symptom_workflow_stuck",
               "propagates_to", 0.88),
    CausalEdge("es_script_error", "symptom_workflow_stuck",
               "propagates_to", 0.90),

    # Orphan / ghost data
    CausalEdge("partial_rollback", "nd_orphan",
               "propagates_to", 0.72, "Rollback partiel → ND sans équipement"),
    CausalEdge("partial_rollback", "vlan_orphan",
               "propagates_to", 0.75, "Rollback partiel → VLAN résiduel"),
    CausalEdge("partial_rollback", "ghost_service_node",
               "propagates_to", 0.78),
    CausalEdge("nd_orphan", "symptom_sync_failure",
               "propagates_to", 0.82),
    CausalEdge("vlan_orphan", "symptom_workflow_stuck",
               "propagates_to", 0.80),
    CausalEdge("ghost_service_node", "symptom_sync_failure",
               "propagates_to", 0.76),

    # Retry loop
    CausalEdge("retry_loop_detected", "dlq_accumulation",
               "propagates_to", 0.88, "Retry loop → messages s'accumulent dans DLQ"),
    CausalEdge("retry_loop_detected", "symptom_workflow_stuck",
               "propagates_to", 0.85),
    CausalEdge("mq_ack_missing", "retry_loop_detected",
               "propagates_to", 0.80, "ACK manquant → retry automatique déclenché"),

    # Partial rollback
    CausalEdge("exception_1300", "partial_rollback",
               "propagates_to", 0.82, "Erreur 1300 → rollback de la transaction"),
    CausalEdge("exception_4002", "partial_rollback",
               "propagates_to", 0.80),
    CausalEdge("partial_rollback", "symptom_workflow_stuck",
               "propagates_to", 0.85),
    CausalEdge("partial_rollback", "symptom_delete_fails",
               "propagates_to", 0.70),
]

# Merge into master collections
_STATIC_NODES.extend(_EXTENDED_NODES)
_NODES.update({n.node_id: n for n in _EXTENDED_NODES})
_STATIC_EDGES.extend(_EXTENDED_EDGES)

# Build adjacency: effect → list of (cause, edge)
_REVERSE_EDGES: Dict[str, List[Tuple[str, CausalEdge]]] = {}
for _e in _STATIC_EDGES:
    _REVERSE_EDGES.setdefault(_e.target, []).append((_e.source, _e))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RCA ENGINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class RCAEngine:
    """
    Traverses the causal graph backward from observed symptoms to root causes.

    Usage:
        engine = RCAEngine()
        result = engine.analyze(
            entity_name="DSROB362",
            intent="delete_equipment",
            active_rule_ids=["EQPT_DEL_001"],
            sync_anomaly_types=["SYNC_DB_MQ"],
            detected_exceptions=["ConstraintViolationException"],
            log_signals=["dead.letter", "ACK timeout"],
        )
    """

    def analyze(
        self,
        entity_name: Optional[str] = None,
        intent: Optional[str] = None,
        active_rule_ids: Optional[List[str]] = None,
        sync_anomaly_types: Optional[List[str]] = None,
        detected_exceptions: Optional[List[str]] = None,
        log_signals: Optional[List[str]] = None,
        db_status: Optional[str] = None,
        active_services: int = 0,
        active_links: int = 0,
    ) -> RCAResult:
        """Full backward causal traversal from symptoms to root causes."""
        active_rule_ids = active_rule_ids or []
        sync_anomaly_types = sync_anomaly_types or []
        detected_exceptions = detected_exceptions or []
        log_signals = log_signals or []

        # Identify the symptom node from intent
        symptom_id = self._intent_to_symptom(intent)
        symptom_desc = self._describe_symptom(symptom_id, entity_name)

        result = RCAResult(
            entity_name=entity_name,
            symptom_description=symptom_desc,
        )

        # Activate evidence nodes from all available evidence
        activated = self._activate_nodes(
            active_rule_ids, sync_anomaly_types,
            detected_exceptions, log_signals,
            db_status, active_services, active_links,
        )

        if not symptom_id or not activated:
            return result

        # Backward traversal: find all causal paths to symptom
        hypotheses = self._backward_traverse(symptom_id, activated, max_depth=4)

        # Sort by confidence DESC, then by root_cause_id ASC for deterministic tie-breaking
        hypotheses.sort(key=lambda h: (-h.confidence, h.root_cause_id))
        result.hypotheses = hypotheses[:5]
        result.top_hypothesis = result.hypotheses[0] if result.hypotheses else None
        return result

    def _activate_nodes(
        self,
        rule_ids: List[str],
        sync_types: List[str],
        exceptions: List[str],
        log_signals: List[str],
        db_status: Optional[str],
        active_services: int,
        active_links: int,
    ) -> Set[str]:
        """Activate causal nodes from all available evidence."""
        activated: Set[str] = set()

        # From business rule violations
        rule_to_node = {
            "EQPT_DEL_001": "eqpt_has_active_services",
            "EQPT_DEL_002": "eqpt_has_mrt_links",
            "EQPT_DEL_003": "eqpt_closed",
            "EQPT_DEL_004": "eqpt_transient",
            "SYNC_MQ_001":  "mq_ack_missing",
            "VLAN_SYNC_001": "orchestra_desync",
            "ND_AFF_001":   "42c_desync",
            # Extended rules
            "EPCV_FSM_001": "epc_fsm_invalid_transition",
            "EPCV_FSM_002": "epc_fsm_invalid_transition",
            "EPCV_FSM_003": "epc_fsm_invalid_transition",
            "MKFL_001":     "making_file_blocked",
            "MKFL_002":     "making_file_partly",
            "MKFL_003":     "making_file_blocked",
            "ES_SCR_001":   "es_script_timeout",
            "ORPHAN_001":   "nd_orphan",
            "ORPHAN_002":   "vlan_orphan",
            "ORPHAN_003":   "ghost_service_node",
            "RETRY_001":    "retry_loop_detected",
            "VLAN_DEL_002": "vlan_orphan",
        }
        for rid in rule_ids:
            if rid in rule_to_node:
                activated.add(rule_to_node[rid])

        # From sync anomaly types
        sync_to_node = {
            "SYNC_DB_MQ":     "mq_ack_missing",
            "SYNC_DB_ORCH":   "orchestra_desync",
            "SYNC_DB_42C":    "42c_desync",
            "SYNC_DLQ":       "dlq_accumulation",
            "SYNC_TIMEOUT":   "mq_ack_missing",
            "SYNC_ROLLBACK":  "partial_rollback",
            "SYNC_EPC_FSM":   "epc_fsm_invalid_transition",
            "SYNC_MAKINGFILE": "making_file_blocked",
        }
        for st in sync_types:
            if st in sync_to_node:
                activated.add(sync_to_node[st])

        # From detected exceptions
        exc_to_node = {
            "ConstraintViolationException": "exception_1300",
            "BrasilInternalException": "exception_4002",
            "AffectationException": "exception_42c",
            "BrocheSearchException": "exception_broche",
            "JMSException": "mq_broker_down",
            "ConnectorCreationVlanException": "vlan_orphan",
            "epc_fsm_invalid_transition": "epc_fsm_invalid_transition",
        }
        for exc in exceptions:
            if exc in exc_to_node:
                activated.add(exc_to_node[exc])

        # From direct DB evidence
        if db_status == "F":
            activated.add("eqpt_closed")
        if db_status == "P":
            activated.add("eqpt_transient")
        if active_services > 0:
            activated.add("eqpt_has_active_services")
        if active_links > 0:
            activated.add("eqpt_has_mrt_links")

        # From log signals (semantic matching)
        all_signals = " ".join(log_signals).lower()
        if any(s in all_signals for s in ["dead.letter", "dlq", "dead letter"]):
            activated.add("dlq_accumulation")
        if any(s in all_signals for s in ["jmsexception", "broker", "amqp"]):
            activated.add("mq_broker_down")
        if "42c" in all_signals or "affectation" in all_signals:
            activated.add("42c_desync")
        if any(s in all_signals for s in ["script running", "es_state", "script bloqué", "script_timeout"]):
            activated.add("es_script_timeout")
        if any(s in all_signals for s in ["making_file", "makingfile", "partly_configured", "mkfl"]):
            activated.add("making_file_blocked")
        if any(s in all_signals for s in ["rollback", "rolled back"]):
            activated.add("partial_rollback")
        if any(s in all_signals for s in ["retry", "tentative", "retry count"]):
            activated.add("retry_loop_detected")
        if any(s in all_signals for s in ["epc", "epcv", "mouvement epc"]):
            activated.add("epc_fsm_invalid_transition")

        return activated

    def _backward_traverse(
        self,
        symptom_id: str,
        activated_nodes: Set[str],
        max_depth: int = 4,
    ) -> List[CausalHypothesis]:
        """
        Backward BFS/DFS from symptom node.
        Returns hypotheses for all activated causal ancestors.
        """
        hypotheses = []
        visited: Set[str] = set()

        def dfs(
            node_id: str,
            chain: List[str],
            cumulative_weight: float,
            depth: int,
        ) -> None:
            if depth > max_depth or node_id in visited:
                return
            visited.add(node_id)

            parents = _REVERSE_EDGES.get(node_id, [])
            for parent_id, edge in parents:
                if parent_id not in _NODES:
                    continue
                new_chain = [parent_id] + chain
                new_weight = cumulative_weight * edge.weight

                if parent_id in activated_nodes:
                    # This activated node is a confirmed causal ancestor
                    parent_node = _NODES[parent_id]
                    symptom_node = _NODES.get(symptom_id)
                    hyp = self._build_hypothesis(
                        parent_node, symptom_node, new_chain, new_weight
                    )
                    hypotheses.append(hyp)
                else:
                    # Continue traversal upstream
                    dfs(parent_id, new_chain, new_weight, depth + 1)

        dfs(symptom_id, [symptom_id], 1.0, 0)
        return hypotheses

    def _build_hypothesis(
        self,
        cause_node: CausalNode,
        symptom_node: Optional[CausalNode],
        chain: List[str],
        weight: float,
    ) -> CausalHypothesis:
        """Build a CausalHypothesis from a confirmed causal path."""
        chain_labels = [
            _NODES[n].label if n in _NODES else n
            for n in chain
        ]
        corrective, fr_id = self._get_corrective_action(cause_node.node_id)
        return CausalHypothesis(
            root_cause_id=cause_node.node_id,
            root_cause_label=cause_node.label,
            confidence=min(weight, 0.99),
            evidence_chain=chain_labels,
            supporting_evidence=[cause_node.description],
            corrective_action=corrective,
            fr_id=fr_id,
        )

    @staticmethod
    def _get_corrective_action(node_id: str) -> Tuple[str, Optional[str]]:
        """Return corrective action + FR for a root cause node."""
        actions: Dict[str, Tuple[str, Optional[str]]] = {
            "eqpt_has_active_services": (
                "Clôturer tous les services actifs (`t_services`) "
                "puis relancer la suppression",
                "FR-DSLAM-DELETION-189"
            ),
            "eqpt_has_mrt_links": (
                "Supprimer les liens MRT résiduels (`t_mrtdslam`, `t_media_links`) "
                "depuis l'IHM BRASIL",
                "FR-DSLAM-DELETION-189"
            ),
            "eqpt_closed": (
                "Appliquer la procédure de réouverture de l'équipement fermé (statut F)",
                "FR-NOEUD-IP-ABSENT-1300"
            ),
            "mq_ack_missing": (
                "Vérifier la DLQ du broker MQ; vérifier les logs ARTEMIS; "
                "forcer un re-send si nécessaire",
                None
            ),
            "dlq_accumulation": (
                "Inspecter la DLQ: identifier les messages bloqués, "
                "décider de rejouer ou purger, vérifier le consommateur ARTEMIS",
                None
            ),
            "mq_broker_down": (
                "Vérifier la disponibilité du broker MQ (ActiveMQ/AMQP); "
                "redémarrer si KO (procédure N3)",
                None
            ),
            "orchestra_desync": (
                "Forcer une synchronisation BRASIL→ORCHESTRA depuis l'IHM",
                None
            ),
            "42c_desync": (
                "Appliquer la procédure de réconciliation BRASIL/42C",
                "FR-DSLAM-AFFECTATION-147B"
            ),
            "exception_1300": (
                "Vérifier le statut de l'équipement (`eqpt_status=F`); "
                "appliquer FR-NOEUD-IP-ABSENT-1300",
                "FR-NOEUD-IP-ABSENT-1300"
            ),
            "exception_42c": (
                "Vérifier cohérence BRASIL/42C; appliquer procédure d'affectation",
                "FR-DSLAM-AFFECTATION-147B"
            ),
        }
        return actions.get(node_id, ("Consulter la documentation N3 pour ce cas.", None))

    @staticmethod
    def _intent_to_symptom(intent: Optional[str]) -> Optional[str]:
        mapping = {
            "delete_equipment": "symptom_delete_fails",
            "force_delete_equipment": "symptom_delete_fails",
            "equipment_stuck_state": "symptom_delete_fails",
            "workflow_blocked": "symptom_workflow_stuck",
            "workflow_stuck": "symptom_workflow_stuck",
            "orchestration_timeout": "symptom_sync_failure",
            "vlan_sync_issue": "symptom_sync_failure",
            "rollback_detected": "symptom_workflow_stuck",
            "transaction_failed": "symptom_workflow_stuck",
        }
        return mapping.get(intent or "", None)

    @staticmethod
    def _describe_symptom(symptom_id: Optional[str], entity: Optional[str]) -> str:
        node = _NODES.get(symptom_id or "")
        if node:
            return f"{node.label} ({entity or 'entité inconnue'})"
        return f"Symptôme: {symptom_id or 'inconnu'}"


# Singleton
_rca_instance: Optional[RCAEngine] = None

def get_rca_engine() -> RCAEngine:
    global _rca_instance
    if _rca_instance is None:
        _rca_instance = RCAEngine()
    return _rca_instance
