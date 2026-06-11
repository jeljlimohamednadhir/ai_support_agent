"""
diagnostic_planner.py
━━━━━━━━━━━━━━━━━━━━━
Deterministic diagnostic planner.

Decides WHICH queries/logs/SSH commands to execute based on:
  - intent
  - detected entities
  - symptoms (from FR matching)
  - optional active SFD rules

NO LLM DECISION IS ALLOWED HERE.
All routing is pure deterministic rule-based logic.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.services.live_diagnostics.db.db_query_registry import (
    INTENT_QUERY_PLAN,
    get_plan_for_intent,
)

logger = logging.getLogger(__name__)


@dataclass
class DiagnosticPlan:
    """What the planner decided to execute."""
    intent:            str
    entity:            Optional[str]
    db_queries:        List[str]              # ordered query names
    db_params_map:     Dict[str, list]        # query_name -> params
    log_searches:      List[Dict[str, Any]]   # {pattern, log_file, max_lines}
    ssh_commands:      List[str]              # command registry keys
    reasoning:         List[str]             # human-readable trace
    confidence:        float
    skip_live_db:      bool = False
    skip_logs:         bool = False
    skip_ssh:          bool = False


# ─────────────────────────────────────────────────────────────────────────────
class DiagnosticPlanner:
    """
    Given an intent + extracted entities, produce a DiagnosticPlan.

    Rules are fully deterministic — no LLM call, no external call.
    """

    # ── Symptom -> additional queries ─────────────────────────────────────────
    _SYMPTOM_EXTRA_QUERIES: Dict[str, List[str]] = {
        "ghost_data":        ["check_residual_references", "check_active_services"],
        "residual_services": ["check_active_services"],
        "counter_error":     ["check_vc_counters", "check_resource_counters"],
        "port_shared":       ["check_shared_port_links", "check_port_attribution"],
        "port_blocked":      ["check_port_attribution"],
        "charset_anomaly":   ["check_port_remarks_anomaly"],
        "dlm_blocked":       ["check_blocked_dlm"],
        "tp_blocked":        ["get_blocked_tps"],
    }

    # ── Intent -> log search patterns ─────────────────────────────────────────
    _INTENT_LOG_SEARCHES: Dict[str, List[Dict[str, Any]]] = {
        "order_blocked": [
            {"pattern": "{entity}", "log_file": "brasil_app", "max_lines": 100},
            {"pattern": "ConstraintViolationException", "log_file": "brasil_app", "max_lines": 50},
            {"pattern": "impossible", "log_file": "brasil_app", "max_lines": 50},
        ],
        "delete_equipment": [
            {"pattern": "{entity}", "log_file": "brasil_app", "max_lines": 100},
            {"pattern": "ConstraintViolationException", "log_file": "brasil_app", "max_lines": 50},
        ],
        "delete_vlan": [
            {"pattern": "VLAN", "log_file": "brasil_app", "max_lines": 50},
            {"pattern": "{entity}", "log_file": "brasil_app", "max_lines": 50},
        ],
        "fix_blocked_tp": [
            {"pattern": "tp_status", "log_file": "brasil_app", "max_lines": 100},
            {"pattern": "{entity}", "log_file": "brasil_app", "max_lines": 50},
        ],
        "fix_ihm_blocked": [
            {"pattern": "DSM PARAM", "log_file": "brasil_ihm", "max_lines": 100},
            {"pattern": "process", "log_file": "brasil_ihm", "max_lines": 50},
        ],
    }

    # ── Intent -> SSH commands ─────────────────────────────────────────────────
    _INTENT_SSH_COMMANDS: Dict[str, List[str]] = {
        "order_blocked":    ["check_java_process", "check_disk_space"],
        "delete_equipment": ["check_java_process", "check_disk_space"],
        "fix_ihm_blocked":  ["check_java_process", "tail_brasil_logs"],
        "fix_blocked_tp":   ["tail_brasil_logs"],
    }

    def plan(
        self,
        intent: str,
        entity: Optional[str] = None,
        symptoms: Optional[List[str]] = None,
        enable_live_db:  bool = True,
        enable_logs:     bool = True,
        enable_ssh:      bool = False,   # SSH disabled by default for safety
    ) -> DiagnosticPlan:
        """
        Produce a DiagnosticPlan for the given intent + entity.

        Parameters
        ----------
        intent          : resolved intent string (e.g. "delete_equipment")
        entity          : extracted entity name (e.g. "DSROB362")
        symptoms        : list of detected symptom tags
        enable_live_db  : whether to include DB queries
        enable_logs     : whether to include log searches
        enable_ssh      : whether to include SSH commands (default OFF)
        """
        symptoms = symptoms or []
        reasoning: List[str] = []

        # ── DB queries ────────────────────────────────────────────────────────
        db_queries: List[str] = []
        db_params_map: Dict[str, list] = {}

        if enable_live_db:
            # ── Route ND (9-digit numeric) to ND-specific query plan ──────────
            _is_nd_entity = entity and bool(__import__('re').match(r'^\d{9}$', str(entity).strip()))
            if _is_nd_entity and intent in ("error_1300", "check_status", "diagnose_equipment",
                                             "forensic_db_state", "order_blocked"):
                _nd_intent = "error_1300_nd" if intent == "error_1300" else "check_nd"
                base_plan = get_plan_for_intent(_nd_intent)
                reasoning.append(
                    f"Entity '{entity}' is a ND (9-digit) — routing to '{_nd_intent}' "
                    f"instead of '{intent}'"
                )
            else:
                base_plan = get_plan_for_intent(intent)
            reasoning.append(f"Intent '{intent}' -> base plan: {base_plan}")

            # Add symptom-derived extras
            extra: List[str] = []
            for symptom in symptoms:
                extras = self._SYMPTOM_EXTRA_QUERIES.get(symptom, [])
                for q in extras:
                    if q not in base_plan and q not in extra:
                        extra.append(q)
                        reasoning.append(f"Symptom '{symptom}' adds query: {q}")

            db_queries = base_plan + extra

            # Build params
            db_params_map = self._build_params(db_queries, entity, intent)
        else:
            reasoning.append("Live DB disabled.")

        # ── Log searches ──────────────────────────────────────────────────────
        log_searches: List[Dict[str, Any]] = []
        if enable_logs:
            templates = self._INTENT_LOG_SEARCHES.get(intent, [])
            for tmpl in templates:
                pattern = tmpl["pattern"].replace("{entity}", entity or "")
                if pattern:
                    log_searches.append({
                        "pattern":   pattern,
                        "log_file":  tmpl["log_file"],
                        "max_lines": tmpl.get("max_lines", 50),
                    })
            if log_searches:
                reasoning.append(f"Log searches planned: {[s['pattern'] for s in log_searches]}")

        # ── SSH commands ──────────────────────────────────────────────────────
        ssh_commands: List[str] = []
        if enable_ssh:
            ssh_commands = self._INTENT_SSH_COMMANDS.get(intent, [])
            if ssh_commands:
                reasoning.append(f"SSH commands planned: {ssh_commands}")
        else:
            reasoning.append("SSH disabled (enable_ssh=False).")

        confidence = 0.95 if (db_queries or log_searches) else 0.3

        plan = DiagnosticPlan(
            intent=intent,
            entity=entity,
            db_queries=db_queries,
            db_params_map=db_params_map,
            log_searches=log_searches,
            ssh_commands=ssh_commands,
            reasoning=reasoning,
            confidence=confidence,
            skip_live_db=not enable_live_db,
            skip_logs=not enable_logs,
            skip_ssh=not enable_ssh,
        )

        logger.info(
            f"[DiagPlanner] intent={intent} entity={entity} "
            f"-> {len(db_queries)} queries, {len(log_searches)} log searches, "
            f"{len(ssh_commands)} SSH cmds"
        )
        return plan

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _build_params(
        self,
        query_names: List[str],
        entity: Optional[str],
        intent: str,
    ) -> Dict[str, list]:
        """
        Build the params_map for a list of query names.
        Uses entity name as the first param, then resolves eqpt_id from
        the get_equipment_id result (handled at runtime by the executor).
        """
        params_map: Dict[str, list] = {}

        for qname in query_names:
            if qname == "get_equipment_id" or qname == "check_equipment_status":
                params_map[qname] = [entity or ""]
            elif qname in (
                "check_residual_references",
                "check_active_services",
                "check_mrt_dslam_links",
                "check_cards_on_equipment",
                "check_vc_counters",
                "check_resource_counters",
                "check_shared_port_links",
                "check_bas_residual_data",
                "check_operator_mrt_links",
            ):
                # eqpt_id to be resolved at runtime after get_equipment_id
                params_map[qname] = ["__EQPT_ID__"]
            elif qname in (
                "get_nd_by_number",
                "check_nd_tp_status",
                "check_tps_by_nd_1300",
                "check_nd_services",
            ):
                # ND queries — use nd_number param = entity (9-digit ND)
                params_map[qname] = [entity or ""]
            elif qname == "get_blocked_tps":
                params_map[qname] = [entity or ""]
            elif qname == "get_tp_initial_states":
                params_map[qname] = ["__TP_ID__"]
            elif qname in ("check_port_remarks_anomaly", "check_blocked_dlm"):
                params_map[qname] = []   # no params
            else:
                params_map[qname] = [entity or ""]

        return params_map


# ─────────────────────────────────────────────────────────────────────────────
# Intent detection from raw user message (no LLM — pure keyword matching)
# ─────────────────────────────────────────────────────────────────────────────

# Ordered list : (intent, keywords_any_of)
# First match wins — order from most specific to most generic
_INTENT_RULES: List[tuple] = [
    # ── Specific deletes FIRST (before generic delete_equipment) ──────────────
    ("delete_vlan",       ["suppression vlan", "supprimer vlan", "vlan impossible",
                           "vlan bloqué", "vlan bloquee"]),
    ("delete_operator",   ["suppression opérateur", "supprimer opérateur",
                           "suppression operateur", "opérateur bloqué"]),
    ("delete_bas",        ["suppression bas", "supprimer bas", "bas impossible",
                           "bas bloqué"]),
    # ── Generic equipment delete ───────────────────────────────────────────────
    ("delete_equipment",  ["suppression", "supprimer", "effacer", "impossible à supprimer",
                           "cannot delete", "suppression impossible", "équipement bloqué"]),
    ("fix_ihm_blocked",   ["ihm bloquée", "ihm bloqué", "ihm ne répond", "dsm param",
                           "script bloqué", "process bloqué", "ihm plantée"]),
    ("fix_vc_counters",   ["compteurs vc", "vc counter", "vc incohérent", "remise à zéro compteur"]),
    ("fix_port_assignment", ["affectation port", "port sans service", "port sans extrémité",
                              "port non affecté"]),
    ("fix_blocked_tp",    ["tp bloqué", "tp bloque", "tp atm", "modification état tp",
                           "modification etat tp", "tp en état", "tp en etat"]),
    ("fix_port_remarks",  ["remarque port", "anomalie remarque", "port remarks"]),
    ("fix_blocked_dlm",   ["dlm bloqué", "dlm", "synchronisation dlm"]),
    ("error_1300",        ["erreur 1300", "error 1300", "1300"]),
    ("error_1002",        ["erreur 1002", "error 1002", "1002"]),
    ("check_system",      ["état système", "mémoire", "disque", "processus java", "java process"]),
    ("check_db",          ["connexion base", "locks", "base bloquée", "db lock"]),
    ("check_node",        ["nœud", "node", "équipement", "equipment", "dsrob", "dsla",
                           "vérifier", "état de"]),
]

import re as _re

def intent_from_message(message: str, entity: Optional[str] = None) -> tuple[str, Optional[str]]:
    """
    Detect intent and optionally extract entity from a raw user message.

    Returns: (intent, entity)
    entity is extracted from message if not provided.

    Pure keyword matching — deterministic, no LLM.
    """
    msg_lower = message.lower()

    # Entity extraction: equipment name OR ND/IAR number (7-10 digits)
    detected_entity = entity
    if not detected_entity:
        m = _re.search(r'\b(DS[A-Z]{2,4}\d{2,6}|BAS[-_]?\d{2,6}|VL[A-Z]{0,3}\d{2,6})\b',
                       message, _re.IGNORECASE)
        if m:
            detected_entity = m.group().upper()
    if not detected_entity:
        # ND / IAR / dossier number (7-10 digits)
        nd_m = _re.search(
            r'\b(?:ND|IAR|dossier|order)\s*[:\s#]?\s*(\d{7,10})\b',
            message, _re.IGNORECASE
        )
        if not nd_m:
            nd_m = _re.search(r'\b(\d{7,10})\b', message)
        if nd_m:
            detected_entity = nd_m.group(1)

    # Intent matching
    for intent, keywords in _INTENT_RULES:
        for kw in keywords:
            if kw.lower() in msg_lower:
                return intent, detected_entity

    # Fallback
    return "check_node", detected_entity
