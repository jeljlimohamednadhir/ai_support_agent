"""
brasil_knowledge_base.py — Base de connaissances unifiée BRASIL
================================================================
Source unique de vérité connectant:
  - Tables SQL → classes Java qui les lisent/écrivent
  - Exceptions → tables + fichiers Java qui les lèvent
  - Workflows → tables + exceptions + log patterns
  - Concept ND → tables concrètes
  - FR (Functional Requirements) → features
  - Patterns de logs → exceptions Java correspondantes

Importe ontology.py pour réutiliser les définitions canoniques.
"""

from typing import Any, Dict, List, Optional
from .ontology import (
    CANONICAL_ENTITIES,
    EXCEPTION_CATALOG,
    WORKFLOW_CATALOG,
    REAL_SQL_TABLES,
    BANNED_INVENTED_TABLES,
    get_entity_for_query,
    get_workflow_for_exception,
)


# ─── Mapping Table → classes Java ────────────────────────────────────────────


TABLE_TO_JAVA_CLASSES: Dict[str, List[str]] = {
    "t_equipments": [
        "ManageVlanBusinessImpl",
        "ManageCreationVlanBusinessImpl",
        "ManageUMIepcBusinessImpl",
    ],
    "t_tps": ["ManageTpBusinessImpl"],
    "t_tpinitialstates": ["ManageTpBusinessImpl", "ManageUMIepcBusinessImpl"],
    "t_makingfiles": [
        "ManageUMIepcBusinessImpl",
        "ManageDEMBusinessImpl",
        "ManageEPCMouvementMakerBusinessImpl",
    ],
    "t_epcs": ["ManageUMIepcBusinessImpl", "ManageEPCMouvementMakerBusinessImpl"],
    "t_epcvers": [
        "ManageUMIepcBusinessImpl",
        "ManageEPCMouvementMakerBusinessImpl",
        "EpcVersRepository",
    ],
    "t_epcversimpacts": ["ManageDEMBusinessImpl"],
    "t_epcorderlines": ["ManageDEMBusinessImpl"],
    "t_mrt_access_dslams": [
        "ManageUMIepcBusinessImpl",
        "DslamAccessMRTRepository",
        "ManageVlanBusinessImpl",
    ],
    "t_mrt_access_dslam_vers": ["ManageUMIepcBusinessImpl"],
    "t_service_access_mrts": ["ManageServiceAccessMRTBusinessImpl"],
    "t_service_access_mrt_vers": ["ManageServiceAccessMRTBusinessImpl"],
    "t_medialinks": ["ManageVlanBusinessImpl", "ManageCreationVlanBusinessImpl"],
    "t_res_prod_controlables": [
        "ManageVlanBusinessImpl",
        "ManageCreationVlanBusinessImpl",
    ],
    "t_res_prod_roles": ["ManageVlanBusinessImpl"],
    "t_d_rscvcis": ["ManageVlanBusinessImpl"],
    "t_d_controlablerscs": ["ManageVlanBusinessImpl"],
    "t_d_dslammanelems": ["ManageEquipmentBusinessImpl"],
    "t_es": ["ManageESBusinessImpl"],
    "t_eslogs": ["ManageESBusinessImpl"],
    "t_estypes": ["ManageESBusinessImpl"],
    "t_nodes": ["ManageNodeBusinessImpl"],
    "t_cards": ["ManageCardBusinessImpl"],
    "t_ports": ["ManagePortBusinessImpl", "ManageVlanBusinessImpl"],
    "t_portgroups": ["ManagePortGroupBusinessImpl"],
    "t_mrtversimpacts": ["ManageDEMBusinessImpl"],
}


# ─── Mapping Exception → tables + contexte complet ───────────────────────────


def get_exception_full_context(exception_name: str) -> Optional[Dict[str, Any]]:
    """Retourne le contexte complet d'une exception Java."""
    exc = EXCEPTION_CATALOG.get(exception_name)
    if not exc:
        return None
    return {
        **exc,
        "java_classes": [
            cls
            for tbl in exc.get("related_tables", [])
            for cls in TABLE_TO_JAVA_CLASSES.get(tbl, [])
        ],
        "workflow_details": WORKFLOW_CATALOG.get(exc.get("workflow", ""), {}),
    }


# ─── Patterns de logs → exceptions ───────────────────────────────────────────


LOG_PATTERN_TO_EXCEPTION: Dict[str, str] = {
    "VlanInterfaceDeleteConstraintException": "VlanInterfaceDeleteConstraintException",
    "VlanInterfaceInvalidEqptTypeException":  "VlanInterfaceInvalidEqptTypeException",
    "VlanInterfaceInvalidSupportLinkException": "VlanInterfaceInvalidSupportLinkException",
    "VlanInterfaceInvalidThresoldException":  "VlanInterfaceInvalidThresoldException",
    "VlanInterfaceMappingException":          "VlanInterfaceMappingException",
    "VlanInterfaceNotFoundException":         "VlanInterfaceNotFoundException",
    "VlanInterfaceUnicityConstraintException":"VlanInterfaceUnicityConstraintException",
    "VlanRaccordementInvalidException":       "VlanRaccordementInvalidException",
    "VlanRaccordementMultipleOperatorException": "VlanRaccordementMultipleOperatorException",
    "VlanRaccordementOperatorMissingException":  "VlanRaccordementOperatorMissingException",
    "NoVcOnVpException":                      "NoVcOnVpException",
    "EpcVersNotFoundException":               "EpcVersNotFoundException",
    "ConnectorLinkMigrationException":        "ConnectorLinkMigrationException",
    "DslamTooManyFoundException":             "DslamTooManyFoundException",
    "SimpleLogicalEqptNotFoundException":     "SimpleLogicalEqptNotFoundException",
    "PortGroupEmptyException":                "PortGroupEmptyException",
    "PortFreeException":                      "PortFreeException",
    "BusinessRuleException":                  "BusinessRuleException",
    # Code patterns
    "erreur 1300":                            "BusinessRuleException",
    "code=1300":                              "BusinessRuleException",
    "IRID(102, 4663":                         "DslamTooManyFoundException",
    "makeMouvement":                          None,  # UMI-EPC normal flow
    "completeMovement":                       None,
}


# ─── Intents → ressources ────────────────────────────────────────────────────


INTENT_TO_RESOURCES: Dict[str, Dict[str, Any]] = {
    # ND / accès
    "check_nd": {
        "tables": ["t_tpinitialstates", "t_makingfiles", "t_mrt_access_dslams"],
        "queries": ["get_tp_by_nd", "get_making_file_by_nd", "get_mrt_by_nd"],
        "workflow": "WORKFLOW_TP",
    },
    "check_making_file": {
        "tables": ["t_makingfiles", "t_epcversimpacts"],
        "queries": ["get_making_file_by_nd", "get_making_file_by_fileid"],
        "workflow": "WORKFLOW_MAKING_FILE",
    },
    "making_file_blocked": {
        "tables": ["t_makingfiles", "t_epcversimpacts", "t_epcorderlines"],
        "queries": ["get_making_file_by_nd", "get_epcvers_by_making_file"],
        "workflow": "WORKFLOW_MAKING_FILE",
        "exceptions": ["EpcVersNotFoundException"],
    },
    # Équipement
    "check_equipment": {
        "tables": ["t_equipments", "t_nodes"],
        "queries": ["get_equipment_by_name", "get_equipment_state"],
        "workflow": "WORKFLOW_EQUIPMENT_STATE",
    },
    "equipment_not_found": {
        "tables": ["t_equipments"],
        "exceptions": ["SimpleLogicalEqptNotFoundException", "DslamTooManyFoundException"],
        "workflow": "WORKFLOW_EQUIPMENT_STATE",
    },
    # VLAN
    "vlan_issue": {
        "tables": ["t_res_prod_controlables", "t_d_rscvcis", "t_d_controlablerscs", "t_medialinks"],
        "queries": ["get_vlan_by_equipment"],
        "workflow": "WORKFLOW_VLAN",
        "exceptions": [
            "VlanInterfaceNotFoundException",
            "VlanInterfaceMappingException",
            "NoVcOnVpException",
        ],
    },
    "vp_creation_failed": {
        "tables": ["t_d_rscvcis", "t_d_controlablerscs", "t_res_prod_controlables"],
        "workflow": "WORKFLOW_VLAN",
        "exceptions": ["NoVcOnVpException", "VlanInterfaceUnicityConstraintException"],
    },
    # EPC / UMI
    "check_epc": {
        "tables": ["t_epcs", "t_epcvers"],
        "queries": ["get_epc_by_nd"],
        "workflow": "WORKFLOW_UMI_EPC",
    },
    "epc_not_found": {
        "tables": ["t_epcvers", "t_epcs"],
        "exceptions": ["EpcVersNotFoundException"],
        "workflow": "WORKFLOW_UMI_EPC",
    },
    # TP
    "tp_blocked": {
        "tables": ["t_tps", "t_tpinitialstates"],
        "queries": ["get_tp_by_nd"],
        "workflow": "WORKFLOW_TP",
    },
    # Accès DSLAM
    "dslam_access_issue": {
        "tables": ["t_mrt_access_dslams", "t_mrt_access_dslam_vers"],
        "queries": ["get_mrt_by_nd"],
        "workflow": "WORKFLOW_DSLAM_ACCESS",
        "exceptions": ["DslamTooManyFoundException"],
    },
    # Scripts
    "script_failed": {
        "tables": ["t_es", "t_eslogs", "t_estypes"],
        "queries": ["get_es_logs_by_equipment"],
        "workflow": "WORKFLOW_SCRIPT",
    },
    "dl_folder_open": {
        "tables": ["t_es", "t_estypes"],
        "queries": ["get_es_logs_by_equipment"],
        "workflow": "WORKFLOW_SCRIPT",
    },
    "dl_folder_close": {
        "tables": ["t_es", "t_estypes"],
        "workflow": "WORKFLOW_SCRIPT",
    },
    # FTTH
    "ftth_scenario": {
        "tables": ["t_mrt_access_dslams", "t_epcs", "t_epcvers", "t_makingfiles"],
        "workflow": "WORKFLOW_UMI_EPC",
    },
    # SL / service logique
    "sl_not_found": {
        "tables": ["t_service_access_mrts", "t_service_access_mrt_vers"],
        "workflow": "WORKFLOW_DSLAM_ACCESS",
    },
    # Erreur 1300
    "error_1300_nd": {
        "tables": ["t_tpinitialstates", "t_tps"],
        "queries": ["get_tp_by_nd", "error_1300_nd"],
        "workflow": "WORKFLOW_TP",
        "exceptions": ["BusinessRuleException"],
    },
}


# ─── FR (Functional Requirements) ─────────────────────────────────────────────


FR_CATALOG: Dict[str, Dict[str, Any]] = {
    "FR_UMI_EPC_CREATE": {
        "label": "Création mouvement UMI-EPC",
        "workflow": "WORKFLOW_UMI_EPC",
        "java_class": "ManageUMIepcBusinessImpl",
        "method": "createMovement",
    },
    "FR_MAKING_FILE_STATES": {
        "label": "Gestion états dossier de fabrication",
        "workflow": "WORKFLOW_MAKING_FILE",
        "states": {0: "CRÉÉ", 1: "ALLOUÉ", 2: "EN_COURS",
                   3: "PARTIELLEMENT_CONFIGURÉ", 4: "CONFIGURÉ", 5: "AVP"},
    },
    "FR_VLAN_CREATION": {
        "label": "Création interface VLAN",
        "workflow": "WORKFLOW_VLAN",
        "java_class": "ManageCreationVlanBusinessImpl",
        "method": "createVlanInterface",
    },
    "FR_EQUIPMENT_STATE": {
        "label": "Gestion état équipement",
        "workflow": "WORKFLOW_EQUIPMENT_STATE",
        "states": {"E": "En service", "D": "Désactivé", "H": "Hors service"},
    },
    "FR_TP_BLOCKING": {
        "label": "Blocage Technical Process",
        "workflow": "WORKFLOW_TP",
        "description": "TP bloqué quand tp_state=1 (BLOQUÉ) ou tp_state=3 (ERREUR)",
    },
}


# ─── Interface principale ────────────────────────────────────────────────────


class BrasilKnowledgeBase:
    """Interface de consultation de la base de connaissances BRASIL."""

    def get_resources_for_intent(self, intent: str) -> Dict[str, Any]:
        return INTENT_TO_RESOURCES.get(intent, {})

    def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        return WORKFLOW_CATALOG.get(workflow_id, {})

    def get_exception_context(self, exception_name: str) -> Optional[Dict[str, Any]]:
        return get_exception_full_context(exception_name)

    def get_java_classes_for_table(self, table_name: str) -> List[str]:
        return TABLE_TO_JAVA_CLASSES.get(table_name, [])

    def is_real_table(self, table_name: str) -> bool:
        return table_name.lower() in REAL_SQL_TABLES

    def get_table_correction(self, invented_table: str) -> Optional[str]:
        return BANNED_INVENTED_TABLES.get(invented_table.lower())

    def find_entities_in_query(self, query: str) -> list:
        return get_entity_for_query(query)

    def get_intent_from_exception(self, exception_name: str) -> Optional[str]:
        workflow = get_workflow_for_exception(exception_name)
        if not workflow:
            return None
        # Map workflow → primary intent
        workflow_to_intent = {
            "WORKFLOW_VLAN": "vlan_issue",
            "WORKFLOW_UMI_EPC": "check_epc",
            "WORKFLOW_MAKING_FILE": "check_making_file",
            "WORKFLOW_TP": "tp_blocked",
            "WORKFLOW_DSLAM_ACCESS": "dslam_access_issue",
            "WORKFLOW_EQUIPMENT_STATE": "check_equipment",
            "WORKFLOW_SCRIPT": "script_failed",
        }
        return workflow_to_intent.get(workflow)

    def get_log_exception(self, log_fragment: str) -> Optional[str]:
        for pattern, exception in LOG_PATTERN_TO_EXCEPTION.items():
            if pattern.lower() in log_fragment.lower():
                return exception
        return None

    def get_full_context_for_intent(self, intent: str) -> Dict[str, Any]:
        """Contexte complet: tables + exceptions + workflow + classes Java."""
        resources = self.get_resources_for_intent(intent)
        if not resources:
            return {}

        tables = resources.get("tables", [])
        exceptions = resources.get("exceptions", [])
        workflow_id = resources.get("workflow", "")

        java_classes = set()
        for tbl in tables:
            java_classes.update(TABLE_TO_JAVA_CLASSES.get(tbl, []))

        exc_details = []
        for exc in exceptions:
            ctx = get_exception_full_context(exc)
            if ctx:
                exc_details.append(ctx)

        return {
            "intent": intent,
            "tables": tables,
            "exceptions": exceptions,
            "exception_details": exc_details,
            "java_classes": list(java_classes),
            "workflow": WORKFLOW_CATALOG.get(workflow_id, {}),
            "queries": resources.get("queries", []),
        }


# Singleton exporté
brasil_kb = BrasilKnowledgeBase()
