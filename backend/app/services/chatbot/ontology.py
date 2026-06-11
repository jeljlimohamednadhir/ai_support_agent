"""
ontology.py — Ontologie canonique BRASIL
========================================
Source unique de vérité pour tous les concepts métier:
  - Entités canoniques avec leurs aliases
  - Mappings table SQL ↔ concept métier
  - Mappings exception Java ↔ contexte
  - Liens workflows ↔ tables ↔ exceptions ↔ logs
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set

# ─── Chargement dynamique depuis brasil_schema_knowledge (généré par extract_schema_knowledge.py)
_SCHEMA_KB = None
try:
    from app.services.chatbot import brasil_schema_knowledge as _SCHEMA_KB  # type: ignore
except ImportError:
    pass


# ─── Types canoniques ───────────────────────────────────────────────────────


class EntityType(str, Enum):
    ND = "ND"                          # Numéro de Désignation (9 chiffres)
    EQUIPMENT = "EQUIPMENT"            # Équipement réseau (DSLAM, NIP, BRAS…)
    TABLE = "TABLE"                    # Table PostgreSQL réelle
    EXCEPTION = "EXCEPTION"            # Exception Java levée
    ERROR_CODE = "ERROR_CODE"          # Code d'erreur numérique
    FR = "FR"                          # Functional Requirement
    WORKFLOW = "WORKFLOW"              # Workflow métier BRASIL
    LOG_PATTERN = "LOG_PATTERN"        # Pattern de log reconnu
    SERVICE = "SERVICE"                # Service technique/accès MRT
    STATE = "STATE"                    # État d'un objet métier
    MAKING_FILE = "MAKING_FILE"        # Dossier de fabrication
    EPC = "EPC"                        # Entité de prestation client
    MRT = "MRT"                        # Media Resource Table entry
    VLAN = "VLAN"                      # VLAN interne


@dataclass
class BrasilEntity:
    canonical_id: str
    entity_type: EntityType
    label: str
    aliases: List[str] = field(default_factory=list)
    related_tables: List[str] = field(default_factory=list)
    related_exceptions: List[str] = field(default_factory=list)
    related_workflows: List[str] = field(default_factory=list)
    java_classes: List[str] = field(default_factory=list)
    description: str = ""


# ─── Entités canoniques ──────────────────────────────────────────────────────


CANONICAL_ENTITIES: Dict[str, BrasilEntity] = {

    # ── ND (Numéro de Désignation) ──
    "ND": BrasilEntity(
        canonical_id="ND",
        entity_type=EntityType.ND,
        label="Numéro de Désignation",
        aliases=["nd", "numéro de désignation", "num désignation", "désignation", "accès nd"],
        related_tables=["t_tpinitialstates", "t_makingfiles", "t_mrt_access_dslams"],
        related_workflows=["WORKFLOW_TP", "WORKFLOW_MAKING_FILE", "WORKFLOW_DSLAM_ACCESS"],
        description=(
            "Identifiant client à 9 chiffres. Stocké dans: "
            "t_tpinitialstates.tpis_nd (VARCHAR 15), "
            "t_makingfiles.mkfl_nd (VARCHAR 15), "
            "t_mrt_access_dslams.dsam_nd (VARCHAR 15)."
        ),
    ),

    # ── Equipment ──
    "EQUIPMENT": BrasilEntity(
        canonical_id="EQUIPMENT",
        entity_type=EntityType.EQUIPMENT,
        label="Équipement réseau",
        aliases=["équipement", "eqpt", "dslam", "nip", "bras", "équipements", "materiel"],
        related_tables=["t_equipments", "t_nodes", "t_shelfs", "t_cards", "t_ports", "t_d_dslammanelems"],
        related_exceptions=["SimpleLogicalEqptNotFoundException", "DslamTooManyFoundException"],
        related_workflows=["WORKFLOW_EQUIPMENT_STATE", "WORKFLOW_VLAN"],
        java_classes=["ManageVlanBusinessImpl", "ManageCreationVlanBusinessImpl"],
        description=(
            "Équipement réseau physique ou logique. "
            "Table principale: t_equipments (eqpt_id, eqpt_name, eqpt_state VARCHAR(1), eqpt_prodstate, node_id). "
            "État: eqpt_state ∈ {'E'=En service, 'D'=Désactivé, 'H'=Hors service}."
        ),
    ),

    # ── Making File ──
    "MAKING_FILE": BrasilEntity(
        canonical_id="MAKING_FILE",
        entity_type=EntityType.MAKING_FILE,
        label="Dossier de fabrication",
        aliases=["dossier", "dossier de fabrication", "making file", "makingfile", "dl", "dossier de livraison",
                 "folder", "dossier bloqué", "dl bloqué"],
        related_tables=["t_makingfiles", "t_epcversimpacts", "t_epcorderlines", "t_mrtversimpacts"],
        related_exceptions=["EpcVersNotFoundException"],
        related_workflows=["WORKFLOW_MAKING_FILE", "WORKFLOW_UMI_EPC"],
        java_classes=["ManageUMIepcBusinessImpl", "ManageDEMBusinessImpl"],
        description=(
            "Dossier de fabrication client. Table: t_makingfiles. "
            "États (mkfl_state SMALLINT): 0=CRÉÉ, 1=ALLOUÉ, 2=EN_COURS, "
            "3=PARTIELLEMENT_CONFIGURÉ, 4=CONFIGURÉ, 5=AVP."
        ),
    ),

    # ── EPC ──
    "EPC": BrasilEntity(
        canonical_id="EPC",
        entity_type=EntityType.EPC,
        label="Entité de prestation client",
        aliases=["epc", "entité prestation", "prestation client", "epcvers"],
        related_tables=["t_epcs", "t_epcvers", "t_epcversimpacts", "t_epcorderlines"],
        related_exceptions=["EpcVersNotFoundException"],
        related_workflows=["WORKFLOW_UMI_EPC"],
        java_classes=["ManageUMIepcBusinessImpl", "ManageEPCMouvementMakerBusinessImpl"],
        description=(
            "Entité de prestation client. "
            "t_epcs: epc_id, epc_epcid, epc_ndservice. "
            "t_epcvers: epcv_id, epcv_versno, epcv_currentstate VARCHAR(1) ∈ {'E'=En service, 'D'=Désactivé}."
        ),
    ),

    # ── DSLAM Access MRT ──
    "DSLAM_ACCESS_MRT": BrasilEntity(
        canonical_id="DSLAM_ACCESS_MRT",
        entity_type=EntityType.MRT,
        label="Accès DSLAM MRT",
        aliases=["mrt", "accès mrt", "dslam access", "dslamaccessmrt", "mrt dslam", "ligne dslam"],
        related_tables=["t_mrt_access_dslams", "t_mrt_access_dslam_vers", "t_mrtversimpacts"],
        related_exceptions=["DslamTooManyFoundException"],
        related_workflows=["WORKFLOW_DSLAM_ACCESS", "WORKFLOW_UMI_EPC"],
        java_classes=["ManageUMIepcBusinessImpl"],
        description=(
            "Accès DSLAM via Media Resource Table. "
            "t_mrt_access_dslams: dsam_id, dsam_nd VARCHAR(15), dsam_customerid, a_eqpt_id, b_eqpt_id. "
            "t_mrt_access_dslam_vers: dsmv_versno, dsmv_currentstate VARCHAR(1)."
        ),
    ),

    # ── VLAN ──
    "VLAN": BrasilEntity(
        canonical_id="VLAN",
        entity_type=EntityType.VLAN,
        label="VLAN interne",
        aliases=["vlan", "vlan interne", "vlan interface", "ccl vlan", "rpct_vlaninterne"],
        related_tables=["t_res_prod_controlables", "t_res_prod_roles", "t_d_rscvcis", "t_d_controlablerscs"],
        related_exceptions=[
            "VlanInterfaceDeleteConstraintException",
            "VlanInterfaceInvalidEqptTypeException",
            "VlanInterfaceInvalidSupportLinkException",
            "VlanInterfaceInvalidThresoldException",
            "VlanInterfaceMappingException",
            "VlanInterfaceNotFoundException",
            "VlanInterfaceUnicityConstraintException",
            "VlanRaccordementInvalidException",
            "VlanRaccordementMultipleOperatorException",
            "VlanRaccordementOperatorMissingException",
            "NoVcOnVpException",
        ],
        related_workflows=["WORKFLOW_VLAN"],
        java_classes=["ManageVlanBusinessImpl", "ManageCreationVlanBusinessImpl"],
        description=(
            "VLAN interne géré dans t_res_prod_controlables.rpct_vlaninterne VARCHAR(5). "
            "Contrôlé par t_d_controlablerscs (prodstate, stocksize, occupiedCount). "
            "Ressources VCI dans t_d_rscvcis (rscv_state VARCHAR(1), rpct_id)."
        ),
    ),

    # ── TP (Technical Process) ──
    "TP": BrasilEntity(
        canonical_id="TP",
        entity_type=EntityType.WORKFLOW,
        label="Technical Process",
        aliases=["tp", "technical process", "process technique", "processus"],
        related_tables=["t_tps", "t_tpinitialstates"],
        related_workflows=["WORKFLOW_TP"],
        description=(
            "Processus technique. t_tps: tp_id, tp_dslamn, tp_hubcode, tp_state SMALLINT, "
            "tp_creationdate INT. t_tpinitialstates: tpis_nd, tpis_vpinitial, tpis_vcinitial."
        ),
    ),

    # ── Execution Script ──
    "EXECUTION_SCRIPT": BrasilEntity(
        canonical_id="EXECUTION_SCRIPT",
        entity_type=EntityType.SERVICE,
        label="Script d'exécution",
        aliases=["es", "script", "exécution", "t_es", "dlm", "script dlm"],
        related_tables=["t_es", "t_eslogs", "t_estypes"],
        related_workflows=["WORKFLOW_SCRIPT"],
        description=(
            "Script d'exécution BRASIL. t_es: es_id, es_state SMALLINT, es_code SMALLINT, "
            "es_requestdate INT, est_id. "
            "Scripts DLM: t_estypes WHERE est_name LIKE '%DLM%'."
        ),
    ),

    # ── Media Link ──
    "MEDIA_LINK": BrasilEntity(
        canonical_id="MEDIA_LINK",
        entity_type=EntityType.SERVICE,
        label="Lien média",
        aliases=["media link", "medialink", "lien", "lien média", "t_medialinks"],
        related_tables=["t_medialinks"],
        related_exceptions=["VlanInterfaceInvalidSupportLinkException", "ConnectorLinkMigrationException"],
        related_workflows=["WORKFLOW_VLAN"],
        java_classes=["ManageVlanBusinessImpl"],
        description=(
            "Lien physique entre équipements. "
            "t_medialinks: mdlk_id, mdlk_state SMALLINT, a_eqpt_id, b_eqpt_id, a_node_id, b_node_id, fctc_id."
        ),
    ),
}


# ─── Tables SQL réelles (source de vérité) ───────────────────────────────────
# Priorité 1: tables extraites en live depuis brasil_prod (brasil_schema_knowledge.py)
# Priorité 2: liste statique issue du createSchemaPostgresql.sql


def _build_real_tables() -> Set[str]:
    if _SCHEMA_KB is not None:
        return set(getattr(_SCHEMA_KB, "REAL_SQL_TABLES", set()))
    return _STATIC_REAL_SQL_TABLES


_STATIC_REAL_SQL_TABLES: Set[str] = {
    "t_equipments", "t_nodes", "t_sites", "t_localareas", "t_bays", "t_rows", "t_rooms",
    "t_shelfs", "t_slots", "t_cards", "t_ports",
    "t_tps", "t_tpinitialstates",
    "t_makingfiles",
    "t_epcs", "t_epcvers", "t_epcversimpacts", "t_epcorderlines",
    "t_mrt_access_dslams", "t_mrt_access_dslam_vers",
    "t_service_access_mrts", "t_service_access_mrt_vers",
    "t_medialinks",
    "t_res_prod_controlables", "t_res_prod_roles", "t_res_prod_controlers", "t_resourceusages",
    "t_es", "t_eslogs", "t_estypes",
    "t_techservices", "t_techservtypes", "t_techservfunctions",
    "t_stcomponents", "t_functioncodes",
    "t_interfaces", "t_outputs", "t_technologytypes",
    "t_cardmodels", "t_cardsoftvers", "t_logicaleqptmodels", "t_manufacturers",
    "t_dslamsoftvers", "t_operators", "t_roles", "t_mrttypes",
    "t_mrtversimpacts", "t_lineprofils", "t_atmprofils",
    "t_ontprofiles", "t_ontprofilerels",
    "t_cardnationalprofils", "t_technooncardnationalprofils",
    "t_trassignments", "t_tpcclatms", "t_tpshelfs",
    "t_servers", "t_nipserverassocs", "t_netresrels", "t_netportmodels",
    "t_nobackontechnos", "t_distributors",
    "t_stripes", "t_stripemodels", "t_portgroups",
    "t_prestations", "t_resourceconstraints", "t_usageconstraints",
    "t_vclockranges", "t_serverconstraints",
    "t_sfpmodules", "t_sfpmoduleportassocs", "t_shelfmodels",
    "t_iccupdates", "t_dslamassignments", "t_dslamaccessconstraints",
    "t_ftthlockonts",
    "t_d_dslammanelems", "t_d_dslamlogicalshelfs", "t_d_dslamxdslcards",
    "t_d_controlablerscs", "t_d_rscvcis", "t_d_rscdslamtsfs",
    "t_d_mutationrequests", "t_d_neednewvcs", "t_d_bookedports", "t_d_xdslcardstripes",
    "t_demandesmutations",
    "t_applicationconfigs", "t_applicationparameters", "t_applicationparametervalues",
    "t_p_intsiamoffers", "t_p_intsiamconcatoffers",
    "t_p_talialogicalbays", "t_p_taliaserviceids",
    "t_p_techservicefilters", "t_p_tsttobg3compservs",
    "t_p_pcprepos", "t_p_slotrepos",
    "t_esconnexions",
}

REAL_SQL_TABLES: Set[str] = _build_real_tables()


def get_table_columns(table: str) -> List[Dict]:
    """Retourne les colonnes réelles d'une table depuis le schéma extrait."""
    if _SCHEMA_KB is not None:
        return getattr(_SCHEMA_KB, "TABLE_COLUMNS", {}).get(table, [])
    return []


def get_fk_children(table: str) -> List[str]:
    """Tables qui référencent cette table (FK entrantes)."""
    if _SCHEMA_KB is not None:
        return getattr(_SCHEMA_KB, "REVERSE_FK", {}).get(table, [])
    return []


def get_fk_parents(table: str) -> List[Dict]:
    """Tables parentes (FK sortantes) d'une table."""
    if _SCHEMA_KB is not None:
        return getattr(_SCHEMA_KB, "FK_GRAPH", {}).get(table, [])
    return []


def get_state_values(table: str, column: str) -> List[str]:
    """Valeurs d'état connues pour une colonne métier VARCHAR(1)/SMALLINT."""
    if _SCHEMA_KB is not None:
        return getattr(_SCHEMA_KB, "STATE_COLUMNS", {}).get(table, {}).get(column, {}).get("values", [])
    return []


def describe_table(table: str) -> str:
    """Description lisible d'une table pour injection LLM."""
    if _SCHEMA_KB is not None and hasattr(_SCHEMA_KB, "describe_table"):
        return _SCHEMA_KB.describe_table(table)
    return f"Table: {table}"


# ─── Tables inventées (bannies) ───────────────────────────────────────────────


BANNED_INVENTED_TABLES: Dict[str, str] = {
    "t_nd":             "Utiliser t_tpinitialstates.tpis_nd, t_makingfiles.mkfl_nd, t_mrt_access_dslams.dsam_nd",
    "t_services":       "Utiliser t_service_access_mrts + t_service_access_mrt_vers",
    "t_vlans":          "Utiliser t_res_prod_controlables.rpct_vlaninterne",
    "t_virtual_channels": "Utiliser t_d_rscvcis + t_res_prod_controlables",
    "t_scripts":        "Utiliser t_es + t_estypes",
    "t_dlm":            "Utiliser t_es + t_estypes WHERE est_name LIKE '%DLM%'",
    "t_mrtdslam":       "Utiliser t_mrt_access_dslams",
    "t_media_links":    "Le nom correct est t_medialinks (sans underscore entre media et links)",
    "t_tp_initial_states": "Le nom correct est t_tpinitialstates (sans underscores internes)",
    "t_service_access_mrts": "Correct — c'est bien t_service_access_mrts",
    "t_dslam_access_mrts":   "Le nom correct est t_mrt_access_dslams",
    "t_epc_vers":       "Le nom correct est t_epcvers",
    "t_epc_versimpacts": "Le nom correct est t_epcversimpacts",
    "t_making_files":   "Le nom correct est t_makingfiles",
    "t_resp_prod_controlables": "Le nom correct est t_res_prod_controlables",
    "t_resprodcontrolables":    "Le nom correct est t_res_prod_controlables",
    "t_dslamaccessmrts":        "Le nom correct est t_mrt_access_dslams",
    # Legacy / variant spellings used by older chatbot responses
    "t_p_talia_service_ids":   "Le nom correct est t_p_taliaserviceids",
    "t_tech_services":         "Le nom correct est t_techservices",
    "t_service_profiles":      "Le nom correct est t_serviceaccessmrtvers",
    "t_resource_usages":       "Le nom correct est t_resourceusages",
    "t_media_links":           "Le nom correct est t_medialinks",
}


TABLE_ALIAS_TO_CANONICAL: Dict[str, str] = {
    # Normalized aliases → canonical injected table names
    "t_ptaliaserviceids": "t_p_taliaserviceids",
    "t_ptalia_service_ids": "t_p_taliaserviceids",
    "t_taliaserviceids": "t_p_taliaserviceids",
    "t_taliaservice_ids": "t_p_taliaserviceids",
    "t_techservices": "t_techservices",
    "t_tech_services": "t_techservices",
    "t_serviceprofiles": "t_serviceaccessmrtvers",
    "t_service_profiles": "t_serviceaccessmrtvers",
    "t_resourceusages": "t_resourceusages",
    "t_resource_usages": "t_resourceusages",
    "t_medialinks": "t_medialinks",
    "t_media_links": "t_medialinks",
}


# ─── Exceptions Java ─────────────────────────────────────────────────────────


EXCEPTION_CATALOG: Dict[str, Dict] = {
    # VLAN exceptions
    "VlanInterfaceDeleteConstraintException": {
        "package": "com.orange.vpcreator.exception",
        "context": "Suppression VLAN interface avec contrainte active",
        "related_tables": ["t_res_prod_controlables", "t_d_rscvcis"],
        "workflow": "WORKFLOW_VLAN",
    },
    "VlanInterfaceInvalidEqptTypeException": {
        "package": "com.orange.vpcreator.exception",
        "context": "Type d'équipement invalide pour VLAN interface",
        "related_tables": ["t_equipments", "t_res_prod_controlables"],
        "workflow": "WORKFLOW_VLAN",
    },
    "VlanInterfaceInvalidSupportLinkException": {
        "package": "com.orange.vpcreator.exception",
        "context": "Lien support invalide pour interface VLAN",
        "related_tables": ["t_medialinks", "t_res_prod_controlables"],
        "workflow": "WORKFLOW_VLAN",
    },
    "VlanInterfaceInvalidThresoldException": {
        "package": "com.orange.vpcreator.exception",
        "context": "Seuil invalide pour interface VLAN",
        "related_tables": ["t_d_controlablerscs"],
        "workflow": "WORKFLOW_VLAN",
    },
    "VlanInterfaceMappingException": {
        "package": "com.orange.vpcreator.exception",
        "context": "Erreur de mapping interface VLAN",
        "related_tables": ["t_res_prod_controlables", "t_d_rscvcis"],
        "workflow": "WORKFLOW_VLAN",
    },
    "VlanInterfaceNotFoundException": {
        "package": "com.orange.vpcreator.exception",
        "context": "Interface VLAN non trouvée en base",
        "related_tables": ["t_res_prod_controlables"],
        "workflow": "WORKFLOW_VLAN",
    },
    "VlanInterfaceUnicityConstraintException": {
        "package": "com.orange.vpcreator.exception",
        "context": "Contrainte d'unicité VLAN interface violée",
        "related_tables": ["t_res_prod_controlables"],
        "workflow": "WORKFLOW_VLAN",
    },
    "VlanRaccordementInvalidException": {
        "package": "com.orange.vpcreator.exception",
        "context": "Raccordement VLAN invalide",
        "related_tables": ["t_res_prod_controlables", "t_medialinks"],
        "workflow": "WORKFLOW_VLAN",
    },
    "VlanRaccordementMultipleOperatorException": {
        "package": "com.orange.vpcreator.exception",
        "context": "Plusieurs opérateurs pour un raccordement VLAN",
        "related_tables": ["t_operators", "t_res_prod_controlables"],
        "workflow": "WORKFLOW_VLAN",
    },
    "VlanRaccordementOperatorMissingException": {
        "package": "com.orange.vpcreator.exception",
        "context": "Opérateur manquant pour raccordement VLAN",
        "related_tables": ["t_operators"],
        "workflow": "WORKFLOW_VLAN",
    },
    "NoVcOnVpException": {
        "package": "com.orange.vpcreator.exception",
        "context": "Pas de canal virtuel (VC) sur le VP",
        "related_tables": ["t_d_rscvcis", "t_d_controlablerscs"],
        "workflow": "WORKFLOW_VLAN",
    },
    # EPC/UMI exceptions
    "EpcVersNotFoundException": {
        "package": "com.orange.vpcreator.exception",
        "context": "Version EPC non trouvée",
        "related_tables": ["t_epcvers", "t_epcs"],
        "workflow": "WORKFLOW_UMI_EPC",
    },
    # Link/connector exceptions
    "ConnectorLinkMigrationException": {
        "package": "com.orange.vpcreator.exception",
        "context": "Erreur de migration de lien connecteur",
        "related_tables": ["t_medialinks"],
        "workflow": "WORKFLOW_VLAN",
    },
    "DslamTooManyFoundException": {
        "package": "com.orange.vpcreator.exception",
        "context": "Trop de DSLAMs trouvés pour le critère",
        "related_tables": ["t_equipments", "t_mrt_access_dslams"],
        "workflow": "WORKFLOW_DSLAM_ACCESS",
    },
    "SimpleLogicalEqptNotFoundException": {
        "package": "com.orange.vpcreator.exception",
        "context": "Équipement logique simple non trouvé",
        "related_tables": ["t_equipments"],
        "workflow": "WORKFLOW_EQUIPMENT_STATE",
    },
    "PortGroupEmptyException": {
        "package": "com.orange.vpcreator.exception",
        "context": "Groupe de ports vide",
        "related_tables": ["t_portgroups", "t_ports"],
        "workflow": "WORKFLOW_VLAN",
    },
    "PortFreeException": {
        "package": "com.orange.vpcreator.exception",
        "context": "Port déjà libre / non occupé",
        "related_tables": ["t_ports"],
        "workflow": "WORKFLOW_VLAN",
    },
    "BusinessRuleException": {
        "package": "com.orange.vpcreator.exception",
        "context": "Règle métier BRASIL violée",
        "related_tables": [],
        "workflow": "WORKFLOW_GENERIC",
    },
}


# ─── Workflows BRASIL ────────────────────────────────────────────────────────


WORKFLOW_CATALOG: Dict[str, Dict] = {
    "WORKFLOW_UMI_EPC": {
        "label": "Workflow UMI-EPC (Mouvement)",
        "entry_point": "ManageUMIepcBusinessImpl.createMovement(DEM, serviceName)",
        "steps": [
            "1. createMovement(DEM, serviceName)",
            "2. Si DEM.getMouvement() != null → suppression, mouvement pré-construit",
            "3. Sinon → création/modification: makeMouvement(epcVersKey, typeMvt, processusDLM, operateurName)",
            "4. completeMovement: enrichit typeMouvement, etatEpt, ancienIdEpc, vciNtu/vpiNtu/refPsc",
            "5. completeMovementNumber: concat(platformId, serverStartTime, sequenceNumber)",
            "6. completeDeletionMovement: IRID(102, 4663, idMrt, '49m') via dslamAccessMRTRepository",
            "7. addFarIdAndRemoteId: pour état CONFIGURED (annulation)",
        ],
        "tables": ["t_epcs", "t_epcvers", "t_mrt_access_dslams", "t_makingfiles"],
        "exceptions": ["EpcVersNotFoundException", "DslamTooManyFoundException"],
        "states": {
            "making_file": {0: "CRÉÉ", 1: "ALLOUÉ", 2: "EN_COURS",
                            3: "PARTIELLEMENT_CONFIGURÉ", 4: "CONFIGURÉ", 5: "AVP"},
            "epcvers": {"E": "En service", "D": "Désactivé/Supprimé"},
        },
    },
    "WORKFLOW_MAKING_FILE": {
        "label": "Workflow Dossier de Fabrication",
        "tables": ["t_makingfiles", "t_epcversimpacts", "t_epcorderlines", "t_mrtversimpacts"],
        "states": {0: "CRÉÉ", 1: "ALLOUÉ", 2: "EN_COURS",
                   3: "PARTIELLEMENT_CONFIGURÉ", 4: "CONFIGURÉ", 5: "AVP"},
        "column": "mkfl_state SMALLINT",
    },
    "WORKFLOW_VLAN": {
        "label": "Workflow VLAN Interface",
        "tables": [
            "t_res_prod_controlables", "t_res_prod_roles",
            "t_d_rscvcis", "t_d_controlablerscs",
            "t_medialinks", "t_equipments",
        ],
        "exceptions": [
            "VlanInterfaceNotFoundException", "VlanInterfaceUnicityConstraintException",
            "VlanInterfaceMappingException", "VlanRaccordementInvalidException",
            "NoVcOnVpException",
        ],
        "java_classes": ["ManageVlanBusinessImpl", "ManageCreationVlanBusinessImpl"],
    },
    "WORKFLOW_DSLAM_ACCESS": {
        "label": "Workflow Accès DSLAM",
        "tables": ["t_mrt_access_dslams", "t_mrt_access_dslam_vers", "t_tpinitialstates"],
        "exceptions": ["DslamTooManyFoundException"],
    },
    "WORKFLOW_TP": {
        "label": "Workflow Technical Process",
        "tables": ["t_tps", "t_tpinitialstates"],
        "states": {1: "BLOQUÉ", 3: "ERREUR"},
        "column": "tp_state SMALLINT",
    },
    "WORKFLOW_EQUIPMENT_STATE": {
        "label": "Workflow État Équipement",
        "tables": ["t_equipments", "t_d_dslammanelems"],
        "states": {"E": "En service", "D": "Désactivé", "H": "Hors service"},
        "column": "eqpt_state VARCHAR(1)",
    },
    "WORKFLOW_SCRIPT": {
        "label": "Workflow Script d'Exécution",
        "tables": ["t_es", "t_eslogs", "t_estypes"],
        "column": "es_state SMALLINT",
    },
}


# ─── Helpers ─────────────────────────────────────────────────────────────────


def is_real_table(table_name: str) -> bool:
    """Vérifie si une table existe dans le schéma réel."""
    return table_name.lower() in REAL_SQL_TABLES


def get_table_correction(invented_table: str) -> Optional[str]:
    """Retourne la correction pour une table inventée."""
    normalized = invented_table.lower().replace("-", "_")
    return BANNED_INVENTED_TABLES.get(normalized)


def normalize_table_alias(table_name: str) -> str:
    """Normalise les variantes legacy d'un nom de table vers son nom canonique."""
    normalized = table_name.lower().replace("-", "_")
    return TABLE_ALIAS_TO_CANONICAL.get(normalized, table_name)


def get_entity_for_query(query: str) -> List[BrasilEntity]:
    """Trouve les entités canoniques mentionnées dans une requête utilisateur."""
    query_lower = query.lower().replace("-", "_")
    matched = []
    for entity in CANONICAL_ENTITIES.values():
        aliases = [alias.lower().replace("-", "_") for alias in entity.aliases]
        if any(alias in query_lower for alias in aliases):
            matched.append(entity)
    return matched


def get_workflow_for_exception(exception_name: str) -> Optional[str]:
    """Retourne le workflow associé à une exception."""
    info = EXCEPTION_CATALOG.get(exception_name)
    return info["workflow"] if info else None


def get_exceptions_for_table(table_name: str) -> List[str]:
    """Retourne les exceptions associées à une table."""
    result = []
    for exc_name, exc_info in EXCEPTION_CATALOG.items():
        if table_name in exc_info.get("related_tables", []):
            result.append(exc_name)
    return result
