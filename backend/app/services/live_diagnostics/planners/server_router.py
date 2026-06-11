"""
server_router.py
━━━━━━━━━━━━━━━━
Deterministic routing: intent -> server(s) -> log paths / commands.

Based on auto-discovery results from op49mwa11, op49mdb11, op49mde11.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ServerRole(str, Enum):
    BDD = "bdd"       # op49mdb11 - PostgreSQL, donnees metier
    WA  = "wa"        # op49mwa11 - Tomcat, IHM Brasil, webservices
    DE  = "de"        # op49mde11 - Data Extractor, batch


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Discovered paths (from discover_servers.py / discover_wa_deep.py)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TOMCAT_BASE = "/opt/application/49mapp/current/tomcat/00"
TOMCAT_LOGS = f"{TOMCAT_BASE}/logs"
BRASIL_CONFIG = "/opt/application/49mapp/G09R17C00/tomcat/00/brasil-ear-configuration"
UMIDICO_BASE = "/opt/application/49mapp/current/umidico"

# ── Log files per server ──────────────────────────────────────────────────────

SERVER_LOG_PATHS: Dict[ServerRole, Dict[str, str]] = {
    ServerRole.WA: {
        # Main application log (catalina)
        "catalina":         f"{TOMCAT_LOGS}/catalina.out",
        "catalina_daily":   f"{TOMCAT_LOGS}/catalina.{{date}}.log",
        # Transaction log (operations BRASIL)
        "transaction":      f"{TOMCAT_LOGS}/49mapp_transaction.log",
        # ConnectorCL - liens clients, services, equipements
        "connector_cl":     f"{TOMCAT_LOGS}/connectorCL_{{date8}}.log",
        "connector_cl_act": f"{TOMCAT_LOGS}/connectorCL_activity_{{date8}}.log",
        # VLAN creation/deletion
        "connector_vlan":   f"{TOMCAT_LOGS}/connectorCreationVlan_{{date8}}.log",
        # DLM operations
        "dlm":              f"{TOMCAT_LOGS}/AccesBrasil_DLM_{{date8}}.log",
        # FTTH operations
        "ftth_access":      f"{TOMCAT_LOGS}/AccesFTTHBrasil_accessManagement_{{date8}}.log",
        "ftth_techconf":    f"{TOMCAT_LOGS}/AccesFTTHBrasil_manageTechnicalConfiguration_{{date8}}.log",
        "ftth_customer":    f"{TOMCAT_LOGS}/AccesFTTHBrasil_customerConsultation_{{date8}}.log",
        # IPON
        "ipon":             f"{TOMCAT_LOGS}/IponBrasil_{{date8}}.log",
        # Retrofit
        "retrofit":         f"{TOMCAT_LOGS}/AccesBrasil_retrofit_{{date8}}.log",
        # UmiDico (batch dictionnaire)
        "umidico":          f"{UMIDICO_BASE}/logs/brasilUmidico.log",
        "umidico_msg":      f"{UMIDICO_BASE}/logs/brasilUmidico_messages_{{date8}}.log",
        # GC log
        "gc":               f"{TOMCAT_LOGS}/GC.log",
        # Sollicitations (webservices entrants)
        "sollicitation_dlm":     f"{TOMCAT_LOGS}/sollicitationDLM_{{datemonth}}.log",
        "sollicitation_retrofit": f"{TOMCAT_LOGS}/sollicitationRETROFIT_{{datemonth}}.log",
        "sollicitation_sebar":   f"{TOMCAT_LOGS}/sollicitationSEBAR_{{datemonth}}.log",
        "sollicitation_sebau":   f"{TOMCAT_LOGS}/sollicitationSEBAU_{{datemonth}}.log",
    },
    ServerRole.BDD: {
        "pg_metrics":       "/opt/pgsql/log/pg_collectmetrics_pgserver01_{date_log}.log",
        "pg_purge":         "/opt/pgsql/log/pg_purge_pgserver01_*.log",
    },
    ServerRole.DE: {
        # DE batch logs - path TBD (no active process found during discovery)
        # Will be populated when DE batch is running
    },
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Intent -> Which logs to search, on which server
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

INTENT_LOG_TARGETS: Dict[str, List[Dict]] = {
    "delete_equipment": [
        # Patterns prefixed with '+' are secondary filters (ANDed with entity via pipe)
        # Bare patterns are standalone greps.  Only entity-anchored searches here.
        {"server": ServerRole.WA, "log_key": "catalina",     "patterns": ["{entity}", "+ConstraintViolationException", "+deleteEquipment", "+BrasilDeleteException"]},
        {"server": ServerRole.WA, "log_key": "connector_cl", "patterns": ["{entity}"]},
        {"server": ServerRole.WA, "log_key": "transaction",  "patterns": ["{entity}"]},
    ],
    "delete_vlan": [
        {"server": ServerRole.WA, "log_key": "connector_vlan", "patterns": ["{entity}", "+VLAN_PREFERRED", "+ConstraintViolation"]},
        {"server": ServerRole.WA, "log_key": "catalina",       "patterns": ["{entity}", "+ConstraintViolation"]},
    ],
    "fix_ihm_blocked": [
        {"server": ServerRole.WA, "log_key": "catalina",     "patterns": ["OutOfMemoryError", "StackOverflow", "SEVERE", "blocked"]},
        {"server": ServerRole.WA, "log_key": "gc",           "patterns": ["Full GC", "pause"]},
        {"server": ServerRole.WA, "log_key": "transaction",  "patterns": ["timeout", "blocked", "DSM"]},
    ],
    "fix_blocked_tp": [
        {"server": ServerRole.WA, "log_key": "catalina",       "patterns": ["{entity}", "+tp_status", "+blocked"]},
        {"server": ServerRole.WA, "log_key": "connector_cl",   "patterns": ["{entity}", "+TP"]},
    ],
    "fix_blocked_dlm": [
        {"server": ServerRole.WA, "log_key": "dlm",           "patterns": ["{entity}", "+blocked"]},
        {"server": ServerRole.WA, "log_key": "catalina",       "patterns": ["{entity}", "+DLM", "+synchronisation"]},
    ],
    "error_1300": [
        {"server": ServerRole.WA, "log_key": "catalina",       "patterns": ["1300", "AVP", "noeud"]},
        {"server": ServerRole.WA, "log_key": "connector_cl",   "patterns": ["1300", "ERROR"]},
    ],
    "error_1002": [
        {"server": ServerRole.WA, "log_key": "catalina",       "patterns": ["1002", "ERROR"]},
    ],
    "fix_vc_counters": [
        {"server": ServerRole.WA, "log_key": "connector_vlan", "patterns": ["VC", "counter", "occupation"]},
    ],
    "fix_port_assignment": [
        {"server": ServerRole.WA, "log_key": "connector_cl",   "patterns": ["port", "affectation", "{entity}"]},
    ],
    # ── Expanded N3 intents ──────────────────────────────────────────────
    "equipment_stuck_state": [
        {"server": ServerRole.WA, "log_key": "catalina",       "patterns": ["{entity}", "+status", "+state"]},
        {"server": ServerRole.WA, "log_key": "connector_cl",   "patterns": ["{entity}"]},
    ],
    "equipment_not_found": [
        {"server": ServerRole.WA, "log_key": "catalina",       "patterns": ["{entity}", "+NotFoundException", "+not found"]},
    ],
    "equipment_inconsistent_state": [
        {"server": ServerRole.WA, "log_key": "catalina",       "patterns": ["{entity}", "+IncoherentState", "+status"]},
    ],
    "workflow_blocked": [
        {"server": ServerRole.WA, "log_key": "catalina",       "patterns": ["{entity}", "+workflow", "+blocked", "+timeout"]},
        {"server": ServerRole.WA, "log_key": "transaction",    "patterns": ["{entity}", "+timeout"]},
    ],
    "rollback_detected": [
        {"server": ServerRole.WA, "log_key": "catalina",       "patterns": ["{entity}", "+rollback", "+RollbackException"]},
    ],
    "create_vlan": [
        {"server": ServerRole.WA, "log_key": "connector_vlan", "patterns": ["{entity}", "+creation", "+VLAN"]},
        {"server": ServerRole.WA, "log_key": "catalina",       "patterns": ["{entity}", "+VLAN", "+create"]},
    ],
    "vlan_sync_issue": [
        {"server": ServerRole.WA, "log_key": "connector_vlan", "patterns": ["{entity}", "+sync", "+propagat"]},
    ],
    "check_residual_data": [
        {"server": ServerRole.WA, "log_key": "catalina",       "patterns": ["{entity}", "+residual", "+orphan", "+constraint"]},
    ],
    "diagnose_equipment": [
        {"server": ServerRole.WA, "log_key": "catalina",       "patterns": ["{entity}", "+ERROR", "+Exception"]},
        {"server": ServerRole.WA, "log_key": "connector_cl",   "patterns": ["{entity}"]},
        {"server": ServerRole.WA, "log_key": "transaction",    "patterns": ["{entity}"]},
    ],
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Intent -> SSH commands per server
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

INTENT_SSH_TARGETS: Dict[str, List[Dict]] = {
    "fix_ihm_blocked": [
        {"server": ServerRole.WA, "commands": ["check_java_process", "check_disk_space"]},
        {"server": ServerRole.BDD, "commands": ["check_active_sessions_db"]},
    ],
    "delete_equipment": [
        {"server": ServerRole.WA, "commands": ["check_java_process"]},
    ],
    "check_system": [
        {"server": ServerRole.WA, "commands": ["check_java_process", "check_disk_space", "check_memory"]},
        {"server": ServerRole.BDD, "commands": ["check_disk_space", "check_memory"]},
    ],
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Helper functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_log_path(server: ServerRole, log_key: str, date: Optional[str] = None) -> str:
    """Resolve a log path with optional date substitution."""
    from datetime import datetime as _dt
    now = _dt.now()
    path_template = SERVER_LOG_PATHS.get(server, {}).get(log_key, "")
    if not path_template:
        return ""
    return (
        path_template
        .replace("{date}", now.strftime("%Y-%m-%d"))
        .replace("{date8}", now.strftime("%Y%m%d"))
        .replace("{datemonth}", now.strftime("%Y%m"))
        .replace("{date_log}", date or now.strftime("%Y%m%d_%HH%M"))
    )


def get_servers_for_intent(intent: str) -> List[ServerRole]:
    """Return which servers are needed for a given intent."""
    servers = set()
    for target in INTENT_LOG_TARGETS.get(intent, []):
        servers.add(target["server"])
    for target in INTENT_SSH_TARGETS.get(intent, []):
        servers.add(target["server"])
    # BDD always needed for psql queries
    servers.add(ServerRole.BDD)
    return list(servers)


def get_log_searches_for_intent(intent: str, entity: Optional[str] = None) -> List[Dict]:
    """
    Return structured log search plan for an intent.
    Each entry: {server, log_path, patterns}
    """
    searches = []
    for target in INTENT_LOG_TARGETS.get(intent, []):
        log_path = get_log_path(target["server"], target["log_key"])
        if not log_path:
            continue
        patterns = [
            p.replace("{entity}", entity or "") for p in target["patterns"]
        ]
        patterns = [p for p in patterns if p]  # remove empty
        searches.append({
            "server": target["server"],
            "log_path": log_path,
            "log_key": target["log_key"],
            "patterns": patterns,
        })
    return searches


def get_ssh_commands_for_intent(intent: str) -> List[Dict]:
    """Return SSH command plan per server."""
    return INTENT_SSH_TARGETS.get(intent, [])
