"""
operation_graph.py
━━━━━━━━━━━━━━━━━━
Maps user/chatbot intents to OperationPaths from the execution graph.

Usage:
    from app.services.code_intelligence.operation_graph import OperationGraph
    graph = OperationGraph()
    path = graph.resolve("delete_equipment", "Dslam")
    context = graph.to_forensic_context("delete_equipment", "Dslam")
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

from .extractors.execution_graph_extractor import (
    ExecutionNode,
    OperationPath,
    get_execution_graph,
    search_execution_graph,
)

logger = logging.getLogger(__name__)


# ── Intent → (operation_key, entity) mapping ────────────────────────────────

INTENT_TO_OPERATION: Dict[str, Tuple[str, str]] = {
    # Equipment lifecycle
    "delete_equipment":          ("delete_equipment", "Dslam"),
    "force_delete_equipment":    ("delete_equipment", "Dslam"),
    "equipment_stuck_state":     ("delete_equipment", "Dslam"),
    "equipment_not_found":       ("get", "Dslam"),
    "equipment_inconsistent_state": ("modify_equipment", "Dslam"),
    "equipment_locked":          ("validate_deletion", "Dslam"),
    "equipment_orphan_data":     ("delete_equipment", "Dslam"),
    "equipment_creation_blocked": ("create_equipment", "Dslam"),
    "diagnose_equipment":        ("validate_deletion", "Dslam"),
    "check_delete_blocked":      ("validate_deletion", "Dslam"),
    "check_status":              ("get", "Dslam"),

    # VLAN lifecycle
    "create_vlan":               ("create_vlan", "Vlan"),
    "delete_vlan":               ("delete_vlan", "Vlan"),
    "vlan_sync_issue":           ("sync_orchestra", "Vlan"),
    "vlan_orphan_data":          ("delete_vlan", "Vlan"),

    # MRT / WAN
    "check_mrt_links":           ("check_mrt", "MRT"),
    "check_mrt":                 ("check_mrt", "MRT"),

    # Workflow / Orchestration
    "workflow_blocked":          ("validate_deletion", ""),
    "workflow_stuck":            ("validate_deletion", ""),
    "orchestration_timeout":     ("sync_orchestra", ""),
    "rollback_detected":         ("rollback", ""),
    "transaction_failed":        ("rollback", ""),

    # Replay / Orders
    "replay_order":              ("replay_order", ""),
    "mass_replay":               ("replay_order", ""),

    # Mutation / Migration
    "mutation_request":          ("mutate_dslam", "Dslam"),

    # Counter / TOC
    "fix_counter":               ("fix_counter", ""),
    "check_toc":                 ("fix_counter", ""),

    # Port / Search
    "search_port":               ("search_port", ""),

    # Forensic follow-up intents (use entity from context)
    "forensic_root_cause":       ("validate_deletion", ""),
    "forensic_constraint_chain": ("validate_deletion", ""),
    "forensic_exceptions":       ("delete_equipment", ""),
    "forensic_db_state":         ("get", ""),
    "forensic_workflow":         ("validate_deletion", ""),
    "forensic_rollback":         ("rollback", ""),
    "show_blocking_method":      ("validate_deletion", ""),
    "show_constraint_source":    ("validate_deletion", ""),
    "explain_code_constraint":   ("validate_deletion", ""),
    "explain_exception_source":  ("delete_equipment", ""),
    "check_residual_data":       ("delete_equipment", ""),
    "check_active_services":     ("get", ""),
    "check_foreign_keys":        ("validate_deletion", ""),
    "check_orphan_rows":         ("delete_equipment", ""),

    # Code intelligence
    "find_code_function":        ("delete_equipment", ""),

    # Incident analysis
    "similar_incidents":         ("get", ""),
    "known_problem":             ("get", ""),

    # Summary / RCA
    "generate_n3_summary":       ("get", ""),
    "generate_rca":              ("validate_deletion", ""),
}

# Operation display names (for forensic summaries)
OPERATION_DISPLAY: Dict[str, str] = {
    "delete_equipment":   "Suppression équipement",
    "create_equipment":   "Création équipement",
    "create_vlan":        "Création VLAN",
    "delete_vlan":        "Suppression VLAN",
    "modify_equipment":   "Modification équipement",
    "get":                "Lecture équipement",
    "validate_deletion":  "Validation contraintes suppression",
    "check_mrt":          "Vérification liens MRT",
    "rollback":           "Rollback opération",
    "sync_orchestra":     "Synchronisation Orchestra",
    "replay_order":       "Rejeu commande",
    "mutate_dslam":       "Mutation DSLAM",
    "fix_counter":        "Correction compteur TOC",
    "search_port":        "Recherche port disponible",
}


class OperationGraph:
    """
    High-level interface for mapping N3 intents to execution paths.

    The execution graph is loaded lazily from cache on first call.
    All output is safe for LLM context (deterministic, length-bounded).
    """

    def resolve(
        self,
        intent: str,
        entity: Optional[str] = None,
    ) -> Optional[OperationPath]:
        """
        Returns the best OperationPath for a given intent.

        Args:
            intent:  Intent key (e.g. "delete_equipment")
            entity:  Entity override (e.g. "Dslam", "Vlan")
        """
        op_key, default_entity = INTENT_TO_OPERATION.get(intent, ("", ""))
        if not op_key:
            return None
        graph = get_execution_graph()
        # Try entity-specific operation path first (e.g. delete_vlan vs delete_equipment)
        if entity and entity.lower() != default_entity.lower():
            entity_op = f"{op_key}_{entity.lower()}"
            path = graph.get_operation_path(entity_op)
            if path:
                return path
        return graph.get_operation_path(op_key)

    def find_methods_for_intent(
        self,
        intent: str,
        entity: Optional[str] = None,
    ) -> List[ExecutionNode]:
        """
        Find all execution nodes relevant to this intent.
        Returns service + validator nodes first.
        """
        op_key, default_entity = INTENT_TO_OPERATION.get(intent, ("", ""))
        resolved_entity = entity or default_entity

        # Direct operation path first
        op_path = self.resolve(intent, resolved_entity)
        if op_path:
            graph = get_execution_graph()
            node_ids = (
                op_path.services[:3]
                + op_path.validators[:2]
                + op_path.repositories[:2]
            )
            return [graph.nodes[nid] for nid in node_ids if nid in graph.nodes]

        # Fallback: keyword search
        op_parts = op_key.split("_") if op_key else intent.split("_")
        operation_word = op_parts[0] if op_parts else intent
        return search_execution_graph(
            operation=operation_word,
            entity=resolved_entity,
        )

    def to_forensic_context(
        self,
        intent: str,
        entity: Optional[str] = None,
        max_chars: int = 1500,
    ) -> str:
        """
        Builds a deterministic, bounded LLM context block for an intent.

        Returns a string like:
          [CODE CHAIN] delete_equipment
          Service: DslamServiceImpl.deleteDslam | throws=[DslamDeletionException]
          Validator: DslamDeletionValidator.canDelete | blocks=[if (hasActivePorts) → throws...]
          Table: t_dslam, t_port
        """
        op_key, default_entity = INTENT_TO_OPERATION.get(intent, ("", ""))
        resolved_entity = entity or default_entity
        display = OPERATION_DISPLAY.get(op_key, op_key or intent)

        op_path = self.resolve(intent, resolved_entity)
        if op_path:
            lines = [f"[CHAÎNE CODE] {display}"]
            graph = get_execution_graph()

            for section, ids, label in [
                (op_path.services[:3], op_path.services, "Service"),
                (op_path.validators[:2], op_path.validators, "Validateur"),
                (op_path.repositories[:2], op_path.repositories, "Repository"),
            ]:
                for nid in ids[:3]:
                    node = graph.nodes.get(nid)
                    if node:
                        lines.append(f"  {label}: {node.to_summary()}")

            if op_path.exceptions:
                lines.append(f"  Exceptions possibles: {', '.join(op_path.exceptions[:5])}")
            if op_path.blocking_conditions:
                lines.append(f"  Conditions bloquantes: {op_path.blocking_conditions[0][:100]}")
            if op_path.sql_tables:
                lines.append(f"  Tables SQL: {', '.join(op_path.sql_tables[:5])}")

            result = "\n".join(lines)
            return result[:max_chars]

        # Fallback: just return service nodes
        nodes = self.find_methods_for_intent(intent, entity)
        if nodes:
            lines = [f"[MÉTHODES CODE] {display or intent}"]
            for n in nodes[:5]:
                lines.append(f"  {n.to_summary()}")
            return "\n".join(lines)[:max_chars]

        return ""

    def get_blocking_conditions(self, intent: str, entity: Optional[str] = None) -> List[str]:
        """Extract all known blocking conditions for a deletion/validation intent."""
        op_path = self.resolve(intent, entity)
        if op_path:
            return op_path.blocking_conditions

        nodes = self.find_methods_for_intent(intent, entity)
        conditions = []
        for n in nodes:
            conditions.extend(n.blocking_conditions)
        return list(set(conditions))[:8]

    def get_exceptions_for_intent(self, intent: str, entity: Optional[str] = None) -> List[str]:
        """Return all exceptions that can be thrown during this operation."""
        op_path = self.resolve(intent, entity)
        if op_path:
            return op_path.exceptions

        nodes = self.find_methods_for_intent(intent, entity)
        excs = []
        for n in nodes:
            excs.extend(n.exceptions_thrown)
        return list(set(excs))[:8]


# Singleton
operation_graph = OperationGraph()
