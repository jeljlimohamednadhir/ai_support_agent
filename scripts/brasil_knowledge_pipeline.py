#!/usr/bin/env python3
"""
BRASIL KNOWLEDGE EXTRACTION PIPELINE
======================================
Autonomous N3-level AI diagnostic knowledge builder.
Parses SQL, logs, FR DOCX, and existing pipeline outputs.
Produces 7 structured JSON knowledge files.
"""

import json
import re
import os
import sys
import hashlib
import datetime
from collections import defaultdict
from pathlib import Path

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
SQL_SCHEMA = BASE_DIR / "backend" / "brasil_db.sql"
FR_PARSED  = BASE_DIR / "data_pipeline" / "output" / "fr_parsed.json"
LOG_EVENTS = BASE_DIR / "data_pipeline" / "output" / "log_events.json"
LOG_KNOWLEDGE = BASE_DIR / "data_pipeline" / "output" / "log_knowledge.json"
PROCEDURES = BASE_DIR / "data_pipeline" / "output" / "procedures.json"
KNOWLEDGE_GRAPH = BASE_DIR / "data_pipeline" / "output" / "knowledge_graph.json"
CLUSTER_RESULTS = BASE_DIR / "data_pipeline" / "output" / "cluster_results.json"
LOG_DIR  = BASE_DIR / "data_pipeline" / "input"

OUTPUT_DIR = BASE_DIR / "backend" / "data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

NOW = datetime.datetime.utcnow().isoformat()

# ─────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────

def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_json(path, data):
    with open(path, "w", encoding="utf-8", errors="replace") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  [SAVED] {path}")

def clean_text(text):
    if not text:
        return ""
    # Remove encoding artifacts
    text = text.replace("Ã©", "é").replace("Ã¨", "è").replace("Ã ", "à")
    text = text.replace("Ã®", "î").replace("Ã´", "ô").replace("Ã¹", "ù")
    text = text.replace("â€™", "'").replace("â€œ", '"').replace("â€", '"')
    text = text.replace("Ã§", "ç").replace("Ã¢", "â").replace("Ã¯", "ï")
    text = text.replace("Ã»", "û").replace("Ã«", "ë").replace("Ã¼", "ü")
    text = text.replace("â†'", "→").replace("Â·", "·").replace("Â ", " ")
    return text


# ─────────────────────────────────────────────
# LAYER 1 + 2 — ENTITY DISCOVERY & STRUCTURAL MAPPING
# ─────────────────────────────────────────────

def extract_sql_entities(sql_path):
    """Parse brasil_db.sql for tables, columns, PKs, FKs."""
    entities = {}
    relationships = []

    if not sql_path.exists():
        return entities, relationships

    content = sql_path.read_text(encoding="utf-8", errors="replace")

    # Extract CREATE TABLE statements
    table_pattern = re.compile(
        r"CREATE TABLE (\w+)\s*\(([^;]+)\);",
        re.DOTALL | re.IGNORECASE
    )

    # Domain entity name mapping (SQL table → telecom entity type)
    ENTITY_TYPE_MAP = {
        "t_equipments":           "EQUIPMENT",
        "t_cards":                "CARD",
        "t_ports":                "PORT",
        "t_nodes":                "NODE",
        "t_bays":                 "BAY",
        "t_d_dslam_logical_shelfs": "SHELF",
        "t_d_dslam_manelems":     "DSLAM",
        "t_d_dslam_xdsl_cards":   "DSLAM_CARD",
        "t_mrt_access_dslams":    "MRT",
        "t_mrt_access_service_vers": "MRT_SERVICE_VERSION",
        "t_mrt_access_services":  "MRT_SERVICE",
        "t_res_prod_controlables": "CCL",
        "t_res_prod_roles":       "RESOURCE_ROLE",
        "t_res_prod_controlers":  "RESOURCE_CONTROLLER",
        "t_epcs":                 "EPC",
        "t_epc_vers":             "EPC_VERSION",
        "t_making_files":         "MAKING_FILE",
        "t_operators":            "OPERATOR",
        "t_logical_eqpt_models":  "EQUIPMENT_MODEL",
        "t_card_models":          "CARD_MODEL",
        "t_card_soft_vers":       "CARD_SOFT_VERSION",
        "t_card_national_profiles": "CARD_PROFILE",
        "t_technology_types":     "TECHNOLOGY",
        "t_port_groups":          "PORT_GROUP",
        "t_dslam_assignments":    "DSLAM_ASSIGNMENT",
        "t_dslam_access_constraints": "DSLAM_CONSTRAINT",
        "t_media_links":          "MEDIA_LINK",
        "t_distributions":        "DISTRIBUTOR",
        "t_distributors":         "DISTRIBUTOR",
        "t_local_areas":          "LOCAL_AREA",
        "t_dr":                   "DR_ZONE",
        "t_mutations_requests":   "MUTATION_REQUEST",
        "t_prestations":          "PRESTATION",
        "t_es":                   "ES_SCRIPT",
        "t_es_types":             "ES_TYPE",
        "t_es_logs":              "ES_LOG",
        "t_function_codes":       "FUNCTION_CODE",
        "t_atm_profiles":         "ATM_PROFILE",
        "t_line_profiles":        "LINE_PROFILE",
        "t_net_resource_rels":    "NETWORK_RESOURCE_REL",
        "t_resource_constraints": "RESOURCE_CONSTRAINT",
        "t_d_controlable_rscs":   "CONTROLLABLE_RSC",
        "t_d_rsc_vcis":           "VCI",
        "t_icc_updates":          "ICC_UPDATE",
        "t_interfaces":           "INTERFACE",
        "t_manufacturers":        "MANUFACTURER",
        "t_mrt_types":            "MRT_TYPE",
        "lst_vlan_usage":         "VLAN",
        "t_epc_order_lines":      "EPC_ORDER_LINE",
        "t_epc_vers_comps":       "EPC_VERSION_COMPONENT",
        "t_epc_vers_impacts":     "EPC_VERSION_IMPACT",
        "t_mrt_vers_impacts":     "MRT_VERSION_IMPACT",
        "t_no_back_on_technos":   "NO_BACK_TECHNO",
        "t_ftth_lock_onts":       "FTTH_ONT_LOCK",
        "t_ont_profiles":         "ONT_PROFILE",
        "t_mrt_access_msan_usage":"MSAN_USAGE",
        "t_application_configs":  "APP_CONFIG",
        "t_application_parameters": "APP_PARAMETER",
    }

    for match in table_pattern.finditer(content):
        table_name = match.group(1).lower()
        cols_block = match.group(2)

        cols = []
        pks = []
        fks_raw = []

        # Parse columns
        for col_line in cols_block.split("\n"):
            col_line = col_line.strip().rstrip(",")
            if not col_line or col_line.upper().startswith("CONSTRAINT"):
                continue
            col_match = re.match(r"^(\w+)\s+([\w\(\),\s]+)", col_line)
            if col_match:
                col_name = col_match.group(1).lower()
                col_type = col_match.group(2).strip()
                is_not_null = "NOT NULL" in col_line.upper()
                col_lines = [l.strip() for l in cols_block.split("\n") if l.strip()]
                first_col = col_lines[0].split()[0].lower() if col_lines else ""
                is_pk = (col_name == f"{table_name[:4]}_id" or
                         (col_name.endswith("_id") and "nextval" in col_line.lower() and col_name == first_col))
                cols.append({
                    "name": col_name,
                    "type": col_type,
                    "not_null": is_not_null
                })
                # Detect FK columns by naming convention (_id suffix referencing other tables)
                if col_name.endswith("_id") and "nextval" not in col_line.lower():
                    fks_raw.append(col_name)

        # Detect primary key (first column with nextval)
        for col_line in cols_block.split("\n"):
            col_line = col_line.strip()
            if "nextval" in col_line.lower():
                pk_match = re.match(r"^(\w+)", col_line)
                if pk_match:
                    pks.append(pk_match.group(1).lower())
                    break

        entity_type = ENTITY_TYPE_MAP.get(table_name, "TABLE")
        entity_id = f"SQL:{table_name.upper()}"

        entities[entity_id] = {
            "id": entity_id,
            "type": entity_type,
            "name": table_name.upper(),
            "display_name": table_name,
            "db_table": table_name,
            "columns": [c["name"] for c in cols[:20]],  # top 20
            "primary_key": pks[0] if pks else None,
            "foreign_keys": list(set(fks_raw)),
            "source_file": "brasil_db.sql",
            "confidence": "high"
        }

        # Generate FK relationships
        for fk_col in fks_raw:
            # Infer target table from FK column name
            # e.g. eqpt_id → t_equipments, card_id → t_cards, node_id → t_nodes
            fk_base = fk_col.replace("_id", "").replace("a_", "").replace("b_", "")
            COLUMN_TO_TABLE = {
                "eqpt": "t_equipments", "card": "t_cards", "port": "t_ports",
                "node": "t_nodes", "bay": "t_bays", "shlf": "t_d_dslam_logical_shelfs",
                "slot": "t_slots", "mkfl": "t_making_files", "oper": "t_operators",
                "rpct": "t_res_prod_controlables", "tsft": "t_tsf_types",
                "mrdv": "t_mrt_access_dslam_vers", "mrsv": "t_mrt_access_service_vers",
                "mrtd": "t_mrt_access_dslams", "mras": "t_mrt_access_services",
                "mrty": "t_mrt_types", "epcv": "t_epc_vers", "epc": "t_epcs",
                "cmod": "t_card_models", "csfv": "t_card_soft_vers",
                "cnpr": "t_card_national_profiles", "tcty": "t_technology_types",
                "pogr": "t_port_groups", "dsag": "t_dslam_assignments",
                "rpco": "t_res_prod_controlers", "lnpr": "t_line_profiles",
                "atpr": "t_atm_profiles", "lgem": "t_logical_eqpt_models",
                "manf": "t_manufacturers", "fctc": "t_function_codes",
                "role": "t_roles", "tst": "t_tst_types",
                "ontp": "t_ont_profiles", "mdlk": "t_media_links",
                "strp": "t_stripes", "row": "t_rows",
                "dist": "t_distributors", "site": "t_sites",
                "serv": "t_servers", "dssv": "t_dslam_soft_vers",
                "rcst": "t_resource_constraints",
                "dslam_eqpt": "t_equipments",
                "master_eqpt": "t_equipments",
                "source_eqpt": "t_equipments",
                "a_eqpt": "t_equipments",
                "b_eqpt": "t_equipments",
                "ce_eqpt": "t_equipments",
            }
            target_table = COLUMN_TO_TABLE.get(fk_base)
            if not target_table:
                # Try prefix match
                for prefix, tbl in COLUMN_TO_TABLE.items():
                    if fk_base.startswith(prefix):
                        target_table = tbl
                        break
            if target_table:
                target_id = f"SQL:{target_table.upper()}"
                relationships.append({
                    "source": entity_id,
                    "target": target_id,
                    "type": "DEPENDS_ON",
                    "via_column": fk_col,
                    "confidence": "high",
                    "source_file": "brasil_db.sql"
                })

    print(f"  [SQL] Extracted {len(entities)} tables, {len(relationships)} FK relationships")
    return entities, relationships


# ─────────────────────────────────────────────
# LAYER 1 — TELECOM DOMAIN ENTITIES (from FR docs + logs)
# ─────────────────────────────────────────────

TELECOM_ENTITIES = {
    "DSLAM": {
        "id": "ENTITY:DSLAM",
        "type": "EQUIPMENT",
        "name": "DSLAM",
        "display_name": "Digital Subscriber Line Access Multiplexer",
        "db_table": "t_equipments + t_d_dslam_manelems",
        "description": "Network access equipment supporting xDSL lines. Has production status (open/closed). Contains shelves, cards, ports.",
        "attributes": ["eqpt_id", "eqpt_name", "eqpt_prod_status", "eqpt_status", "eqpt_toc_max_init", "eqpt_load"],
        "confidence": "high",
        "source_file": "brasil_db.sql + FR_docs + logs"
    },
    "MSAN": {
        "id": "ENTITY:MSAN",
        "type": "EQUIPMENT",
        "name": "MSAN",
        "display_name": "Multi-Service Access Node",
        "db_table": "t_equipments",
        "description": "Multi-service access node supporting VDSL2, GPON. Variant of DSLAM with extended service support.",
        "attributes": ["eqpt_id", "eqpt_name", "eqpt_prod_status", "eqpt_runtime_type"],
        "confidence": "high",
        "source_file": "brasil_db.sql + FR_docs"
    },
    "CARD": {
        "id": "ENTITY:CARD",
        "type": "CARD",
        "name": "CARD",
        "display_name": "Line Card",
        "db_table": "t_cards + t_d_dslam_xdsl_cards",
        "description": "Physical card installed in a DSLAM/MSAN chassis. Can be open or closed for production. Contains ports.",
        "attributes": ["card_id", "card_num", "card_prod_status", "card_nature", "cmod_id", "slot_id"],
        "confidence": "high",
        "source_file": "brasil_db.sql + logs"
    },
    "PORT": {
        "id": "ENTITY:PORT",
        "type": "PORT",
        "name": "PORT",
        "display_name": "Physical Port (Broche)",
        "db_table": "t_ports",
        "description": "Physical connection point on a card. Has occupation status, production status, attributable flag.",
        "attributes": ["port_id", "port_num", "port_type", "port_pin_num", "port_out_status", "port_occup_status", "port_attribuable", "port_prod_status"],
        "confidence": "high",
        "source_file": "brasil_db.sql + logs"
    },
    "SHELF": {
        "id": "ENTITY:SHELF",
        "type": "SHELF",
        "name": "SHELF",
        "display_name": "Logical Shelf (Chassis DSLAM)",
        "db_table": "t_d_dslam_logical_shelfs",
        "description": "Logical shelf grouping cards within a DSLAM chassis.",
        "attributes": ["dsls_id", "dsls_prod_status", "dsls_toc_max", "dsls_total_port_count", "dsls_total_used_port_count"],
        "confidence": "high",
        "source_file": "brasil_db.sql"
    },
    "NODE": {
        "id": "ENTITY:NODE",
        "type": "NODE",
        "name": "NODE",
        "display_name": "Network Node (NRA/NRO)",
        "db_table": "t_nodes",
        "description": "Geographic network concentration point. Can be NRA (copper) or NRO (fiber). Contains DSLAMs and distributors.",
        "attributes": ["node_id", "node_node_code", "node_base_code42c", "node_center_code42c", "node_dr_code", "node_nra_type"],
        "confidence": "high",
        "source_file": "brasil_db.sql + FR_docs"
    },
    "EPC": {
        "id": "ENTITY:EPC",
        "type": "SERVICE",
        "name": "EPC",
        "display_name": "Electronic Provisioning Contract",
        "db_table": "t_epcs + t_epc_vers",
        "description": "Customer service record. References the client ND and service versions. Entry point for provisioning commands.",
        "attributes": ["epc_id", "epc_epc_id", "epc_nd_service", "epc_reselled_offer", "epc_vers_num_0", "epc_vers_num_1"],
        "confidence": "high",
        "source_file": "brasil_db.sql + FR_docs + logs"
    },
    "MRT": {
        "id": "ENTITY:MRT",
        "type": "SERVICE",
        "name": "MRT",
        "display_name": "Macro Ressource Technique (MRT Access DSLAM)",
        "db_table": "t_mrt_access_dslams + t_mrt_access_service_vers",
        "description": "Technical resource link between customer (EPC) and physical DSLAM port. Key routing object.",
        "attributes": ["mrtd_id", "mrtd_customer_id", "mrtd_nd", "mrtd_crc_mrt_id", "mrtd_farid", "a_eqpt_id", "a_port_id"],
        "confidence": "high",
        "source_file": "brasil_db.sql + logs + FR_docs"
    },
    "CCL": {
        "id": "ENTITY:CCL",
        "type": "NETWORK_RESOURCE",
        "name": "CCL",
        "display_name": "Contrôle de Collecte Logique (CCL/VC)",
        "db_table": "t_res_prod_controlables",
        "description": "Logical resource (VLAN/VC) binding DSLAM to NIP/BAS. Has VC counters and production status. Critical for GE/CEV offers.",
        "attributes": ["rpct_id", "rpct_type", "rpct_ccl_name", "rpct_prod_status", "rpct_vc_max", "rpct_allocated_vc_count", "rpct_vlan_interne"],
        "confidence": "high",
        "source_file": "brasil_db.sql + FR_docs + logs"
    },
    "VLAN": {
        "id": "ENTITY:VLAN",
        "type": "NETWORK_RESOURCE",
        "name": "VLAN",
        "display_name": "Virtual LAN",
        "db_table": "lst_vlan_usage + t_res_prod_controlables",
        "description": "Virtual LAN identifier used for service routing. Managed via CCL resources.",
        "attributes": ["vlan", "usage"],
        "confidence": "high",
        "source_file": "brasil_db.sql + FR_docs"
    },
    "VP_VC": {
        "id": "ENTITY:VP_VC",
        "type": "NETWORK_RESOURCE",
        "name": "VP_VC",
        "display_name": "ATM Virtual Path/Virtual Circuit",
        "db_table": "t_d_rsc_vcis",
        "description": "ATM VP/VC resource assigned on DSLAM port for ADSL/VDSL services.",
        "attributes": ["rscv_id", "rscv_vci", "rscv_status", "rpct_id"],
        "confidence": "high",
        "source_file": "brasil_db.sql + FR_docs"
    },
    "MAKING_FILE": {
        "id": "ENTITY:MAKING_FILE",
        "type": "ORDER",
        "name": "MAKING_FILE",
        "display_name": "Dossier de Réalisation (Making File)",
        "db_table": "t_making_files",
        "description": "Provisioning order file. Contains business process type (CL/SAV/DLM/AVP/RES). Central orchestration object.",
        "attributes": ["mkfl_id", "mkfl_file_id", "mkfl_customer_name", "mkfl_nd", "mkfl_business_process", "mkfl_status", "mkfl_base_code_42c"],
        "confidence": "high",
        "source_file": "brasil_db.sql + FR_docs"
    },
    "NIP": {
        "id": "ENTITY:NIP",
        "type": "EQUIPMENT",
        "name": "NIP",
        "display_name": "Nœud IP (BAS/BRAS)",
        "db_table": "t_equipments",
        "description": "IP network node (BAS/BRAS/BNG) aggregating DSLAM traffic via CCL/VC resources.",
        "attributes": ["eqpt_id", "eqpt_name", "eqpt_runtime_type"],
        "confidence": "high",
        "source_file": "brasil_db.sql + FR_docs + logs"
    },
    "OPERATOR": {
        "id": "ENTITY:OPERATOR",
        "type": "ACTOR",
        "name": "OPERATOR",
        "display_name": "Opérateur",
        "db_table": "t_operators",
        "description": "Telecom operator (Orange, resellers). Controls service provisioning.",
        "attributes": ["oper_id", "oper_name", "oper_long_name"],
        "confidence": "high",
        "source_file": "brasil_db.sql"
    },
    "REGLETTE": {
        "id": "ENTITY:REGLETTE",
        "type": "PHYSICAL",
        "name": "REGLETTE",
        "display_name": "Réglette de répartiteur",
        "db_table": "implicit (referenced in FR docs and UMI-EPC messages)",
        "description": "Physical distribution frame strip. Referenced in MRT Access DSLAM for copper line termination.",
        "attributes": ["referenceReglette", "numeroBroche"],
        "confidence": "high",
        "source_file": "FR_docs"
    },
    "REPARTITEUR": {
        "id": "ENTITY:REPARTITEUR",
        "type": "PHYSICAL",
        "name": "REPARTITEUR",
        "display_name": "Répartiteur (MDF)",
        "db_table": "implicit",
        "description": "Main Distribution Frame. Physical junction between subscriber copper lines and DSLAM.",
        "attributes": ["grGs", "codeDr", "libelle42C", "code42C", "ciDico"],
        "confidence": "high",
        "source_file": "FR_docs"
    },
    "MUTATION": {
        "id": "ENTITY:MUTATION",
        "type": "OPERATION",
        "name": "MUTATION",
        "display_name": "Mutation (Link Mutation)",
        "db_table": "t_mutations_requests",
        "description": "Physical link mutation operation. Moves service between DSLAMs or nodes.",
        "attributes": ["murq_id", "murq_status", "murq_execution_type", "murq_equipment_n", "murq_equipment_n1"],
        "confidence": "high",
        "source_file": "brasil_db.sql + FR 100"
    },
    "DISTRIBUTOR": {
        "id": "ENTITY:DISTRIBUTOR",
        "type": "PHYSICAL",
        "name": "DISTRIBUTOR",
        "display_name": "Distributeur",
        "db_table": "t_distributors",
        "description": "Distribution element within a node. Connected to DSLAMs.",
        "attributes": ["dist_id", "node_id", "dist_prod_orientation"],
        "confidence": "high",
        "source_file": "brasil_db.sql"
    },
    "TSF": {
        "id": "ENTITY:TSF",
        "type": "PARAMETER",
        "name": "TSF",
        "display_name": "Tech Service Function (TSF)",
        "db_table": "t_d_rsc_dslam_tsfs",
        "description": "Technical service function binding. Defines which services can be provisioned on a DSLAM port.",
        "attributes": ["rscd_id", "tsft_id", "rpct_id", "dslam_eqpt_id", "rscd_priority"],
        "confidence": "high",
        "source_file": "brasil_db.sql + logs"
    },
    "DR_ZONE": {
        "id": "ENTITY:DR_ZONE",
        "type": "GEOGRAPHIC",
        "name": "DR_ZONE",
        "display_name": "Direction Régionale (DR)",
        "db_table": "t_dr",
        "description": "Regional zone grouping network nodes. Used for geographic routing and assignment.",
        "attributes": ["dr_code", "dr_name"],
        "confidence": "high",
        "source_file": "brasil_db.sql"
    }
}


def extract_fr_entities(fr_data):
    """Extract additional entities mentioned in FR documents."""
    entities = {}
    
    # Application/system entities from FR docs
    SYSTEM_ENTITIES = {
        "BRASIL": ("APPLICATION", "BRASIL application - telecom resource management system"),
        "ORCHESTRA": ("APPLICATION", "Orchestra - network element repository (référentiel NE)"),
        "SEBA": ("APPLICATION", "SEBA - service management application"),
        "E_BASILIQ": ("APPLICATION", "E-Basiliq - order processing system via MQ"),
        "IPON": ("APPLICATION", "IPON - IP/ON service management"),
        "SCA": ("APPLICATION", "SCA - service catalog application"),
        "ADELIA": ("APPLICATION", "ADELIA - provisioning automation"),
        "UMI_EPC": ("INTERFACE", "UMI-EPC connector - EPC movement processor"),
        "UMI_DICO": ("INTERFACE", "UMI-DICO connector - dictionary synchronization"),
        "CONNECTOR_CL": ("INTERFACE", "ConnectorCL - provisioning request processor"),
        "CONNECTOR_VLAN": ("INTERFACE", "ConnectorCreationVLAN - VLAN creation handler"),
        "SOLICITATION_DLM": ("INTERFACE", "SollicitationDLM - DLM provisioning trigger"),
        "SOLICITATION_FTTH": ("INTERFACE", "SollicitationFTTH - FTTH provisioning trigger"),
        "RABBITMQ": ("INFRASTRUCTURE", "RabbitMQ - message queue for async processing"),
        "POSTGRESQL": ("INFRASTRUCTURE", "PostgreSQL - BRASIL database backend"),
    }

    for name, (etype, desc) in SYSTEM_ENTITIES.items():
        entities[f"SYSTEM:{name}"] = {
            "id": f"SYSTEM:{name}",
            "type": etype,
            "name": name,
            "display_name": name,
            "description": desc,
            "confidence": "high",
            "source_file": "FR_docs + logs"
        }

    # Mine FR docs for error code entities
    if isinstance(fr_data, list):
        error_codes = set()
        for fr in fr_data:
            for code in fr.get("error_codes", []):
                error_codes.add(str(code))
        
        for code in error_codes:
            eid = f"ERROR:{code}"
            entities[eid] = {
                "id": eid,
                "type": "ERROR_CODE",
                "name": f"BRASIL_ERROR_{code}",
                "display_name": f"Error {code}",
                "confidence": "high",
                "source_file": "FR_docs"
            }

    return entities


# ─────────────────────────────────────────────
# LAYER 3 — RELATIONSHIPS
# ─────────────────────────────────────────────

def build_structural_relationships(sql_entities, sql_fk_rels, telecom_entities):
    """Build all relationships from SQL, telecom domain knowledge, and FR docs."""
    relationships = []

    # 1. SQL-derived FK relationships (already computed)
    relationships.extend(sql_fk_rels)

    # 2. Telecom domain structural relationships
    DOMAIN_RELS = [
        # Physical hierarchy
        ("ENTITY:NODE",     "ENTITY:DSLAM",    "HAS",        "NODE contains DSLAM equipments", "high", "domain_model"),
        ("ENTITY:NODE",     "ENTITY:MSAN",     "HAS",        "NODE contains MSAN equipments",  "high", "domain_model"),
        ("ENTITY:NODE",     "ENTITY:DISTRIBUTOR","HAS",      "NODE has physical distributor",   "high", "brasil_db.sql"),
        ("ENTITY:DSLAM",    "ENTITY:SHELF",    "HAS",        "DSLAM has logical shelves",       "high", "brasil_db.sql"),
        ("ENTITY:DSLAM",    "ENTITY:CARD",     "HAS",        "DSLAM contains cards",            "high", "brasil_db.sql + logs"),
        ("ENTITY:CARD",     "ENTITY:PORT",     "HAS",        "CARD contains physical ports",    "high", "brasil_db.sql + logs"),
        ("ENTITY:SHELF",    "ENTITY:CARD",     "HAS",        "SHELF groups cards",              "high", "brasil_db.sql"),
        ("ENTITY:PORT",     "ENTITY:REGLETTE", "LINKED_TO",  "PORT linked to MDF reglette",     "high", "FR_docs"),
        ("ENTITY:REGLETTE", "ENTITY:REPARTITEUR","BELONGS_TO","Reglette belongs to repartiteur","high","FR_docs"),

        # Service hierarchy
        ("ENTITY:EPC",      "ENTITY:MRT",      "HAS",        "EPC has associated MRT (access)", "high", "brasil_db.sql"),
        ("ENTITY:MRT",      "ENTITY:PORT",     "LINKED_TO",  "MRT linked to physical port",     "high", "brasil_db.sql"),
        ("ENTITY:MRT",      "ENTITY:DSLAM",    "LINKED_TO",  "MRT linked to DSLAM equipment",   "high", "brasil_db.sql"),
        ("ENTITY:MRT",      "ENTITY:CCL",      "DEPENDS_ON", "MRT service depends on CCL resource","high","brasil_db.sql + logs"),
        ("ENTITY:CCL",      "ENTITY:VP_VC",    "HAS",        "CCL manages VP/VC resources",     "high", "brasil_db.sql"),
        ("ENTITY:CCL",      "ENTITY:VLAN",     "HAS",        "CCL has associated VLAN",         "high", "brasil_db.sql + FR_docs"),
        ("ENTITY:CCL",      "ENTITY:DSLAM",    "LINKED_TO",  "CCL connects DSLAM side",         "high", "brasil_db.sql"),
        ("ENTITY:CCL",      "ENTITY:NIP",      "LINKED_TO",  "CCL connects NIP/BAS side",       "high", "brasil_db.sql"),

        # Order/provisioning
        ("ENTITY:MAKING_FILE","ENTITY:EPC",    "HAS",        "Making file triggers EPC update", "high", "brasil_db.sql"),
        ("ENTITY:MAKING_FILE","ENTITY:MRT",    "HAS",        "Making file has MRT impacts",     "high", "brasil_db.sql"),
        ("ENTITY:MAKING_FILE","ENTITY:OPERATOR","BELONGS_TO","Making file belongs to operator", "high", "brasil_db.sql"),

        # Physical-logical
        ("ENTITY:DSLAM",    "ENTITY:TSF",      "HAS",        "DSLAM has technical service functions","high","brasil_db.sql + logs"),
        ("ENTITY:TSF",      "ENTITY:CCL",      "LINKED_TO",  "TSF linked to CCL resource",      "high", "brasil_db.sql"),
        ("ENTITY:NODE",     "ENTITY:DR_ZONE",  "BELONGS_TO", "NODE belongs to DR geographic zone","high","brasil_db.sql"),

        # Mutation
        ("ENTITY:MUTATION", "ENTITY:DSLAM",    "LINKED_TO",  "Mutation involves source/target DSLAM","high","brasil_db.sql + FR 100"),
        ("ENTITY:MUTATION", "ENTITY:MRT",      "DEPENDS_ON", "Mutation requires MRT reassignment","high","brasil_db.sql"),

        # System interfaces
        ("SYSTEM:CONNECTOR_CL", "ENTITY:MAKING_FILE","PROCESSES","ConnectorCL processes making files","high","logs"),
        ("SYSTEM:CONNECTOR_CL", "ENTITY:EPC",   "PROCESSES",  "ConnectorCL processes EPC updates","high","logs"),
        ("SYSTEM:UMI_EPC",   "ENTITY:EPC",      "SYNCHRONIZES","UMI-EPC syncs EPC movements",   "high","FR_docs + logs"),
        ("SYSTEM:E_BASILIQ", "SYSTEM:BRASIL",   "INTERFACES_WITH","E-Basiliq exchanges data with BRASIL","high","FR_docs"),
        ("SYSTEM:ORCHESTRA", "ENTITY:DSLAM",    "MANAGES",    "Orchestra manages DSLAM NE repository","high","FR_docs"),
        ("SYSTEM:ORCHESTRA", "ENTITY:NODE",     "MANAGES",    "Orchestra manages node repository","high","FR_docs"),
        ("SYSTEM:RABBITMQ",  "SYSTEM:CONNECTOR_CL","DELIVERS","RabbitMQ delivers messages to ConnectorCL","high","logs"),
        ("SYSTEM:BRASIL",    "ENTITY:DSLAM",    "MANAGES",    "BRASIL manages DSLAM resources",  "high","domain_model"),
        ("SYSTEM:BRASIL",    "ENTITY:EPC",      "MANAGES",    "BRASIL manages EPC service records","high","domain_model"),
    ]

    for src, tgt, rtype, desc, conf, source in DOMAIN_RELS:
        relationships.append({
            "source": src,
            "target": tgt,
            "type": rtype,
            "description": desc,
            "confidence": conf,
            "source_file": source
        })

    print(f"  [REL] Total relationships: {len(relationships)}")
    return relationships


# ─────────────────────────────────────────────
# LAYER 4 — CONSTRAINTS
# ─────────────────────────────────────────────

def extract_constraints(fr_data, sql_content=""):
    """Extract blocking constraints from FR docs, SQL and logs."""
    constraints = []

    # ── SQL-derived constraints ──
    sql_constraints = [
        {
            "id": "CSTR-SQL-001",
            "description": "EQUIPMENT cannot be deleted if CARDS reference it (eqpt_id FK in t_cards)",
            "rule": "DELETE t_equipments WHERE eqpt_id IS REFERENCED BY t_cards.eqpt_id → BLOCKED",
            "affected_entities": ["EQUIPMENT", "CARD"],
            "severity": "blocking",
            "constraint_type": "deletion",
            "confidence": "high",
            "source_file": "brasil_db.sql",
            "multi_source": False
        },
        {
            "id": "CSTR-SQL-002",
            "description": "CARD cannot be deleted if PORTS reference it (card_id FK in t_ports)",
            "rule": "DELETE t_cards WHERE card_id IS REFERENCED BY t_ports.card_id → BLOCKED",
            "affected_entities": ["CARD", "PORT"],
            "severity": "blocking",
            "constraint_type": "deletion",
            "confidence": "high",
            "source_file": "brasil_db.sql",
            "multi_source": False
        },
        {
            "id": "CSTR-SQL-003",
            "description": "NODE cannot be deleted if EQUIPMENTS or DISTRIBUTORS reference it",
            "rule": "DELETE t_nodes WHERE node_id IS REFERENCED BY t_equipments.node_id OR t_distributors.node_id → BLOCKED",
            "affected_entities": ["NODE", "EQUIPMENT", "DISTRIBUTOR"],
            "severity": "blocking",
            "constraint_type": "deletion",
            "confidence": "high",
            "source_file": "brasil_db.sql",
            "multi_source": False
        },
        {
            "id": "CSTR-SQL-004",
            "description": "MAKING_FILE cannot be processed if status is blocking (mkfl_status)",
            "rule": "PROCESS t_making_files WHERE mkfl_status IN (BLOCKED, CANCELLED) → REJECTED",
            "affected_entities": ["MAKING_FILE"],
            "severity": "blocking",
            "constraint_type": "lifecycle",
            "confidence": "high",
            "source_file": "brasil_db.sql",
            "multi_source": False
        },
        {
            "id": "CSTR-SQL-005",
            "description": "PORT cannot be assigned if port_attribuable = 0",
            "rule": "ASSIGN t_ports WHERE port_attribuable = 0 → BLOCKED",
            "affected_entities": ["PORT"],
            "severity": "blocking",
            "constraint_type": "validation",
            "confidence": "high",
            "source_file": "brasil_db.sql + FR 1583B",
            "multi_source": True
        },
        {
            "id": "CSTR-SQL-006",
            "description": "CCL cannot accept new VCs if rpct_allocated_vc_count >= rpct_vc_max",
            "rule": "ASSIGN VC ON t_res_prod_controlables WHERE allocated_vc_count >= vc_max → REJECTED",
            "affected_entities": ["CCL", "VP_VC"],
            "severity": "blocking",
            "constraint_type": "capacity",
            "confidence": "high",
            "source_file": "brasil_db.sql + FR_docs",
            "multi_source": True
        },
        {
            "id": "CSTR-SQL-007",
            "description": "EPC cannot have duplicate epc_epc_id",
            "rule": "INSERT t_epcs WHERE epc_epc_id ALREADY EXISTS → UNIQUE VIOLATION",
            "affected_entities": ["EPC"],
            "severity": "blocking",
            "constraint_type": "uniqueness",
            "confidence": "high",
            "source_file": "brasil_db.sql + logs",
            "multi_source": True
        },
        {
            "id": "CSTR-SQL-008",
            "description": "FTTH ONT lock requires unique (ont_num, port_id) pair",
            "rule": "INSERT t_ftth_lock_onts WHERE (flko_ont_num, port_id) ALREADY EXISTS → UNIQUE CONSTRAINT",
            "affected_entities": ["PORT", "FTTH_ONT_LOCK"],
            "severity": "blocking",
            "constraint_type": "uniqueness",
            "confidence": "high",
            "source_file": "brasil_db.sql",
            "multi_source": False
        }
    ]
    constraints.extend(sql_constraints)

    # ── FR-derived constraints ──
    FR_DERIVED_CONSTRAINTS = [
        {
            "id": "CSTR-FR-001",
            "description": "DSLAM closed for production blocks all port assignment (recherche broche)",
            "rule": "IF dslam_prod_status = CLOSED THEN AffecterRessourcesXdslService → FAIL with 'fermé à la production'",
            "affected_entities": ["DSLAM", "PORT", "MAKING_FILE"],
            "severity": "blocking",
            "constraint_type": "production_state",
            "fr_references": ["FR 1583", "FR 1583B"],
            "confidence": "high",
            "source_file": "FR_docs + logs",
            "multi_source": True
        },
        {
            "id": "CSTR-FR-002",
            "description": "CARD closed for production blocks port assignment on that card",
            "rule": "IF card_prod_status = CLOSED THEN AffecterRessourcesXdslService → FAIL with 'carte fermée à la production'",
            "affected_entities": ["CARD", "PORT"],
            "severity": "blocking",
            "constraint_type": "production_state",
            "fr_references": ["FR 1583", "logs"],
            "confidence": "high",
            "source_file": "logs",
            "multi_source": True
        },
        {
            "id": "CSTR-FR-003",
            "description": "CCL (VC) NumeroCCL is mandatory for CEV offers",
            "rule": "IF offer_type = CEV AND rpct_ccl_name IS NULL THEN AffecterRessourcesXdslService → ERROR 'Le NumeroCCL est obligatoire dans le cas d\\'une offre CEV'",
            "affected_entities": ["CCL", "MAKING_FILE", "EPC"],
            "severity": "blocking",
            "constraint_type": "validation",
            "fr_references": ["FR 135"],
            "confidence": "high",
            "source_file": "FR_docs + logs",
            "multi_source": True
        },
        {
            "id": "CSTR-FR-004",
            "description": "EPC identifier already used by another EPC (duplicate detection)",
            "rule": "IF epc_epc_id ALREADY IN USE → AffecterRessourcesXdslService → ERROR 'L\\'identifiant d\\'EPC est déjà utilisé'",
            "affected_entities": ["EPC"],
            "severity": "blocking",
            "constraint_type": "uniqueness",
            "fr_references": ["logs"],
            "confidence": "high",
            "source_file": "logs",
            "multi_source": False
        },
        {
            "id": "CSTR-FR-005",
            "description": "MRT Access DSLAM identifier unknown blocks liberation (LibérerRessources)",
            "rule": "IF mrtd_id NOT FOUND → LibererRessourcesXdslService → ERROR 'Identifiant de Macro Ressource Technique inconnu'",
            "affected_entities": ["MRT", "MAKING_FILE"],
            "severity": "blocking",
            "constraint_type": "referential_integrity",
            "fr_references": ["FR_docs", "logs"],
            "confidence": "high",
            "source_file": "logs",
            "multi_source": False
        },
        {
            "id": "CSTR-FR-006",
            "description": "EPC dossier de réalisation ID unknown blocks modification",
            "rule": "IF mkfl_id NOT FOUND → ModifierDonneesCommerciales → ERROR 'Identifiant de dossier de réalisation inconnu'",
            "affected_entities": ["MAKING_FILE", "EPC"],
            "severity": "blocking",
            "constraint_type": "referential_integrity",
            "fr_references": ["FR 012", "logs"],
            "confidence": "high",
            "source_file": "FR_docs + logs",
            "multi_source": True
        },
        {
            "id": "CSTR-FR-007",
            "description": "Port counter (TOC) at 100% prevents new port assignment on DSLAM",
            "rule": "IF DSLAM_TOC = 100% THEN RechercherBrochesService → FAIL 'No port found with such constraints'",
            "affected_entities": ["DSLAM", "PORT", "CARD"],
            "severity": "blocking",
            "constraint_type": "capacity",
            "fr_references": ["FR 001 (CalculerToc)", "FR 1583"],
            "confidence": "high",
            "source_file": "FR_docs + logs",
            "multi_source": True
        },
        {
            "id": "CSTR-FR-008",
            "description": "Access already being modified (dossier en cours) blocks concurrent modification",
            "rule": "IF mkfl_status = IN_PROGRESS → AffecterRessourcesXdslService → ERROR 'L\\'accès est déjà en cours de modification'",
            "affected_entities": ["MAKING_FILE", "EPC", "MRT"],
            "severity": "blocking",
            "constraint_type": "concurrency",
            "fr_references": ["logs"],
            "confidence": "high",
            "source_file": "logs",
            "multi_source": False
        },
        {
            "id": "CSTR-FR-009",
            "description": "MRTChemin already carried by another MRTAccesDslam blocks new assignment",
            "rule": "IF mrtd_crc_mrt_id ALREADY ASSIGNED TO ANOTHER MRTD → ERROR 'Un accès client existe déjà avec le même identifiant'",
            "affected_entities": ["MRT", "EPC"],
            "severity": "blocking",
            "constraint_type": "uniqueness",
            "fr_references": ["logs"],
            "confidence": "high",
            "source_file": "logs",
            "multi_source": False
        },
        {
            "id": "CSTR-FR-010",
            "description": "Deadlock in PostgreSQL causes provisioning rollback and retry with 55s delay",
            "rule": "IF PSQLException deadlock_detected → ROLLBACK → RETRY after 55000ms (max 3 attempts)",
            "affected_entities": ["MAKING_FILE", "PORT", "CCL"],
            "severity": "warning",
            "constraint_type": "transactional",
            "fr_references": ["logs - ConnectorCLMDBBean(236)"],
            "confidence": "high",
            "source_file": "logs",
            "multi_source": False
        },
        {
            "id": "CSTR-FR-011",
            "description": "SCA blocking caused by missing FARID or RemoteID",
            "rule": "IF farid IS NULL OR remote_id IS NULL → SCA_BLOCKED",
            "affected_entities": ["EPC", "MRT", "MAKING_FILE"],
            "severity": "blocking",
            "constraint_type": "validation",
            "fr_references": ["FR 010"],
            "confidence": "high",
            "source_file": "FR 010",
            "multi_source": False
        },
        {
            "id": "CSTR-FR-012",
            "description": "DSLAM constraint on repartiteur must exist before DSLAM assignment",
            "rule": "IF t_dslam_access_constraints FOR node DOES NOT EXIST → assignment blocked",
            "affected_entities": ["DSLAM", "NODE", "DISTRIBUTOR"],
            "severity": "blocking",
            "constraint_type": "prerequisite",
            "fr_references": ["FR 150"],
            "confidence": "high",
            "source_file": "FR 150",
            "multi_source": False
        },
        {
            "id": "CSTR-FR-013",
            "description": "VP/VLAN/VC counter incorrect (occupied wrongly) blocks new resource assignment",
            "rule": "IF ctrs_occupied_count MISMATCH ACTUAL USAGE → new VC assignment may fail",
            "affected_entities": ["CCL", "VP_VC", "VLAN", "DSLAM"],
            "severity": "blocking",
            "constraint_type": "data_inconsistency",
            "fr_references": ["FR 136b", "FR 136c"],
            "confidence": "high",
            "source_file": "FR 136b + FR 136c",
            "multi_source": True
        },
        {
            "id": "CSTR-FR-014",
            "description": "NIFolderID field missing (Error 1002) - mandatory field validation",
            "rule": "IF nifolderid IS NULL IN INCOMING MESSAGE → BRASIL ERROR 1002 'Champ obligatoire NIFolderID non présent'",
            "affected_entities": ["MAKING_FILE", "EPC"],
            "severity": "blocking",
            "constraint_type": "validation",
            "fr_references": ["FR 012"],
            "confidence": "high",
            "source_file": "FR 012",
            "multi_source": False
        },
        {
            "id": "CSTR-FR-015",
            "description": "UPDATEDMRTLIST field absent or format error (Error 1002)",
            "rule": "IF updatedmrtlist IS NULL OR FORMAT_INVALID → BRASIL ERROR 1002",
            "affected_entities": ["MRT", "EPC"],
            "severity": "blocking",
            "constraint_type": "validation",
            "fr_references": ["FR 013"],
            "confidence": "high",
            "source_file": "FR 013",
            "multi_source": False
        },
        {
            "id": "CSTR-FR-016",
            "description": "DLM blocked orders require manual reprocessing via Brasil N3 procedure",
            "rule": "IF mkfl_business_process = DLM AND mkfl_status = BLOCKED → manual intervention required",
            "affected_entities": ["MAKING_FILE"],
            "severity": "blocking",
            "constraint_type": "lifecycle",
            "fr_references": ["FR 101"],
            "confidence": "high",
            "source_file": "FR 101",
            "multi_source": False
        },
        {
            "id": "CSTR-FR-017",
            "description": "Port réseau without service or endpoint is invalid resource",
            "rule": "IF port_occup_status = OCCUPIED AND NO_SERVICE AND NO_ENDPOINT → data inconsistency requires correction",
            "affected_entities": ["PORT", "CCL", "MRT"],
            "severity": "warning",
            "constraint_type": "data_inconsistency",
            "fr_references": ["FR 114"],
            "confidence": "high",
            "source_file": "FR 114",
            "multi_source": False
        },
        {
            "id": "CSTR-FR-018",
            "description": "BBC movement without Brasil action requires investigation",
            "rule": "IF bbc_movement_received AND NO_BRASIL_ACTION → data_sync_failure",
            "affected_entities": ["MAKING_FILE", "EPC"],
            "severity": "warning",
            "constraint_type": "synchronization",
            "fr_references": ["FR 156"],
            "confidence": "medium",
            "source_file": "FR 156",
            "multi_source": False
        },
        {
            "id": "CSTR-FR-019",
            "description": "TSF resources not found for DSLAM causes internal error on service assignment",
            "rule": "IF TSF resources not available ON DSLAM → BrasilInternalErrorException on resource reservation",
            "affected_entities": ["TSF", "CCL", "DSLAM", "MRT"],
            "severity": "blocking",
            "constraint_type": "resource_availability",
            "fr_references": ["logs - ManageNetworkTRProductionBusinessImpl(968)"],
            "confidence": "high",
            "source_file": "logs",
            "multi_source": True
        }
    ]
    constraints.extend(FR_DERIVED_CONSTRAINTS)

    print(f"  [CSTR] Total constraints: {len(constraints)}")
    return constraints


# ─────────────────────────────────────────────
# LAYER 5 — WORKFLOWS
# ─────────────────────────────────────────────

def extract_workflows(fr_data):
    """Extract ordered workflow sequences from FR documents and domain knowledge."""
    
    workflows = [
        {
            "id": "WF-001",
            "name": "Service Provisioning (CL - Création de Ligne)",
            "type": "provisioning",
            "trigger": "New service order received from E-Basiliq via RabbitMQ",
            "business_process": "CL",
            "entities_involved": ["MAKING_FILE", "EPC", "MRT", "DSLAM", "PORT", "CCL"],
            "steps": [
                {"step": 1, "action": "Receive UMI-EPC message from Orchestra via RabbitMQ", "component": "ConnectorCL", "validation": "Message format check (NIFolderID, UPDATEDMRTLIST)"},
                {"step": 2, "action": "Create or update Making File (Dossier de Réalisation)", "component": "ManageTRProductionBusinessImpl", "validation": "mkfl_status = OPEN"},
                {"step": 3, "action": "Validate EPC record (IdEpc)", "component": "ObtenirEptXdslService", "validation": "EPC exists and not duplicate"},
                {"step": 4, "action": "Verify DSLAM production status (open/closed)", "component": "PortBooker", "validation": "eqpt_prod_status = OPEN"},
                {"step": 5, "action": "Search available port (Rechercher Broche)", "component": "RechercherBrochesService", "validation": "port_attribuable=1, TOC < 100%"},
                {"step": 6, "action": "Reserve logical resources (VP/VC on CCL)", "component": "LogicalResBooker", "validation": "CCL vc_count < vc_max, TSF available"},
                {"step": 7, "action": "Assign resources (Affecter Ressources XDSL)", "component": "AffecterRessourcesXdslService", "validation": "No concurrent modification, no duplicate MRTChemin"},
                {"step": 8, "action": "Commit transaction and update counters", "component": "ManageTRProductionBusinessImpl", "validation": "No deadlock, transaction complete"},
                {"step": 9, "action": "Send UMI-EPC movement to E-Basiliq", "component": "ConnectorUMIepc", "validation": "Movement sent, E-Basiliq queue not congested"},
                {"step": 10, "action": "Update MRT and EPC version state", "component": "BRASIL", "validation": "mrsv_current_state = C (connected)"}
            ],
            "error_paths": [
                {"at_step": 4, "error": "DSLAM closed for production", "constraint": "CSTR-FR-001", "action": "Reject with 'fermé à la production'"},
                {"at_step": 5, "error": "No port found (TOC=100%)", "constraint": "CSTR-FR-007", "action": "Reject, run CalculerToc to verify"},
                {"at_step": 6, "error": "TSF not found for DSLAM", "constraint": "CSTR-FR-019", "action": "Reject with BrasilInternalErrorException"},
                {"at_step": 7, "error": "CCL NumeroCCL missing for CEV", "constraint": "CSTR-FR-003", "action": "Reject with validation error"},
                {"at_step": 8, "error": "Deadlock detected", "constraint": "CSTR-FR-010", "action": "Rollback + retry after 55s"}
            ],
            "confidence": "high",
            "source_file": "FR_docs + logs + brasil_db.sql"
        },
        {
            "id": "WF-002",
            "name": "Service Liberation (Libérer Ressources XDSL)",
            "type": "deprovisioning",
            "trigger": "Service termination order (SAV process)",
            "business_process": "SAV",
            "entities_involved": ["MAKING_FILE", "EPC", "MRT", "PORT", "CCL"],
            "steps": [
                {"step": 1, "action": "Receive liberation request via RabbitMQ", "component": "ConnectorCL", "validation": "Message valid"},
                {"step": 2, "action": "Locate Making File by ID", "component": "ManageTRProductionBusinessImpl", "validation": "mkfl_id exists"},
                {"step": 3, "action": "Validate MRT identifier", "component": "LibererRessourcesXdslService", "validation": "mrtd_id exists in t_mrt_access_dslams"},
                {"step": 4, "action": "Release logical resources (VP/VC/CCL)", "component": "LogicalResBooker", "validation": "Resources actually assigned"},
                {"step": 5, "action": "Free physical port (port_occup_status = FREE)", "component": "PortBooker", "validation": "Port state consistent"},
                {"step": 6, "action": "Delete or archive MRT version", "component": "BRASIL", "validation": "No active services remain"},
                {"step": 7, "action": "Notify E-Basiliq via UMI-EPC", "component": "ConnectorUMIepc", "validation": "Movement confirmed"}
            ],
            "error_paths": [
                {"at_step": 3, "error": "MRT identifier unknown", "constraint": "CSTR-FR-005", "action": "Reject with 'Identifiant MRT inconnu'"},
                {"at_step": 2, "error": "Making file unknown", "constraint": "CSTR-FR-006", "action": "Reject with 'dossier de réalisation inconnu'"}
            ],
            "confidence": "high",
            "source_file": "FR_docs + logs"
        },
        {
            "id": "WF-003",
            "name": "TOC Calculation (CalculerToc)",
            "type": "diagnostic",
            "trigger": "N3 manual action or scheduled check for DSLAM saturation",
            "business_process": "N3_MAINTENANCE",
            "entities_involved": ["DSLAM", "CARD", "PORT"],
            "steps": [
                {"step": 1, "action": "Connect to 49mbdd database on ad49mbdd server", "component": "BrasilTools/CalculerTOC.ksh", "validation": "DB accessible"},
                {"step": 2, "action": "Run SQL query for ADSL TOC on t_d_dslam_xdsl_cards", "component": "SQL", "validation": "Query returns result"},
                {"step": 3, "action": "Run SQL query for SDSL TOC", "component": "SQL", "validation": ""},
                {"step": 4, "action": "Run SQL query for VDSL2 TOC", "component": "SQL", "validation": ""},
                {"step": 5, "action": "Verify results in IHM BRASIL (TOC ADSL panel)", "component": "BRASIL_IHM", "validation": "TOC < 100% for normal operation"},
                {"step": 6, "action": "Check logs in BrasilTools/logs/", "component": "filesystem", "validation": "No errors in log"}
            ],
            "error_paths": [
                {"at_step": 5, "error": "TOC = 100%", "constraint": "CSTR-FR-007", "action": "Investigate port_attribuable field, run FR 1583 procedure"}
            ],
            "confidence": "high",
            "source_file": "FR 001"
        },
        {
            "id": "WF-004",
            "name": "Mass UMI-EPC Resend (Envoi en Masse)",
            "type": "recovery",
            "trigger": "Data desynchronization between Orchestra and Brasil for GP NDs",
            "business_process": "N3_RECOVERY",
            "entities_involved": ["EPC", "MRT", "MAKING_FILE"],
            "steps": [
                {"step": 1, "action": "Verify E-Basiliq MQ queue capacity (PUC monitoring)", "component": "E_BASILIQ_PUC", "validation": "Queue not congested"},
                {"step": 2, "action": "Avoid peak hours (08h30-09h30)", "component": "OPERATIONAL", "validation": "Time window check"},
                {"step": 3, "action": "Prepare CSV file with ND list (9-char format)", "component": "filesystem", "validation": "File format correct"},
                {"step": 4, "action": "Launch N3-Envoi mouvements UMI-EPC from IHM Brasil", "component": "BRASIL_IHM", "validation": "Script accepted"},
                {"step": 5, "action": "Monitor execution via IHM request history", "component": "BRASIL_IHM", "validation": "Status changes from IN_PROGRESS to DONE"},
                {"step": 6, "action": "Verify report and log file", "component": "BRASIL_IHM", "validation": "No errors in report"},
                {"step": 7, "action": "Verify UMI-EPC movement file on op49mwa11", "component": "connectorUMIepc log", "validation": "ND present in movement file"},
                {"step": 8, "action": "Verify E-Basiliq PUC confirms NDs processed", "component": "E_BASILIQ_PUC", "validation": "NDs acknowledged"}
            ],
            "error_paths": [
                {"at_step": 1, "error": "E-Basiliq queue congested", "constraint": "CSTR-INFRA-001", "action": "Wait, retry later or off-peak hours"}
            ],
            "confidence": "high",
            "source_file": "FR 002"
        },
        {
            "id": "WF-005",
            "name": "DLM Blocked Orders Recovery",
            "type": "recovery",
            "trigger": "DLM orders blocked in Brasil requiring N3 intervention",
            "business_process": "DLM",
            "entities_involved": ["MAKING_FILE", "EPC", "MRT"],
            "steps": [
                {"step": 1, "action": "Identify blocked DLM orders in t_making_files", "component": "SQL", "validation": "mkfl_business_process=4 AND mkfl_status=BLOCKED"},
                {"step": 2, "action": "Analyze blocking reason from logs", "component": "Brasil logs", "validation": "Root cause identified"},
                {"step": 3, "action": "Apply corrective action (manual data fix or replay)", "component": "N3_ACTION", "validation": "Depends on root cause"},
                {"step": 4, "action": "Re-trigger processing via IHM Brasil", "component": "BRASIL_IHM", "validation": "Order status changes"},
                {"step": 5, "action": "Verify order completed successfully", "component": "BRASIL_IHM", "validation": "mkfl_status = COMPLETED"}
            ],
            "error_paths": [],
            "confidence": "high",
            "source_file": "FR 101"
        },
        {
            "id": "WF-006",
            "name": "Node Comparison Brasil vs Référentiel Sites",
            "type": "diagnostic",
            "trigger": "Node present in Référentiel Sites but absent in Brasil (or mismatch)",
            "business_process": "N3_DIAGNOSTIC",
            "entities_involved": ["NODE", "DSLAM"],
            "steps": [
                {"step": 1, "action": "Query Brasil for node by code42C or node_code", "component": "BRASIL_IHM", "validation": "Node found or not found"},
                {"step": 2, "action": "Query Référentiel Sites for same node", "component": "ORCHESTRA", "validation": "Node data in referential"},
                {"step": 3, "action": "Compare node attributes (code, DR, name, type)", "component": "N3_COMPARISON", "validation": "Differences identified"},
                {"step": 4, "action": "If discrepancy: create ticket or apply correction", "component": "JIRA/BRASIL_IHM", "validation": "Sync restored"}
            ],
            "error_paths": [
                {"at_step": 1, "error": "Node absent in Brasil", "constraint": "CSTR-FR-012", "action": "Create node via admin procedure"}
            ],
            "confidence": "high",
            "source_file": "FR 148 + FR 151"
        },
        {
            "id": "WF-007",
            "name": "DSLAM Node Modification",
            "type": "configuration",
            "trigger": "Need to move DSLAM to different node",
            "business_process": "NETWORK_REORGANIZATION",
            "entities_involved": ["DSLAM", "NODE", "CARD", "PORT"],
            "steps": [
                {"step": 1, "action": "Verify no active services on DSLAM before move", "component": "SQL/BRASIL_IHM", "validation": "No MRT in state C"},
                {"step": 2, "action": "Close DSLAM for production", "component": "BRASIL_IHM", "validation": "eqpt_prod_status = CLOSED"},
                {"step": 3, "action": "Modify node_id on t_equipments", "component": "N3_DB_ACTION", "validation": "FK constraint check on t_nodes"},
                {"step": 4, "action": "Update node constraints (t_dslam_access_constraints)", "component": "N3_DB_ACTION", "validation": "Constraints consistent"},
                {"step": 5, "action": "Reopen DSLAM for production", "component": "BRASIL_IHM", "validation": "eqpt_prod_status = OPEN"},
                {"step": 6, "action": "Verify DSLAM visible in correct node context", "component": "BRASIL_IHM", "validation": "Node association confirmed"}
            ],
            "error_paths": [
                {"at_step": 1, "error": "Active services present", "constraint": "CSTR-SQL-001", "action": "Cannot move; must decommission services first"},
                {"at_step": 4, "error": "Missing constraint on repartiteur", "constraint": "CSTR-FR-012", "action": "Create constraint via FR 150 procedure"}
            ],
            "confidence": "high",
            "source_file": "FR 152 + FR 150"
        },
        {
            "id": "WF-008",
            "name": "MQ Backout Message Recovery (UMI-DICO)",
            "type": "recovery",
            "trigger": "UMI-DICO messages stuck in MQ Backout queue",
            "business_process": "N3_RECOVERY",
            "entities_involved": ["SYSTEM:UMI_DICO", "SYSTEM:RABBITMQ"],
            "steps": [
                {"step": 1, "action": "Identify messages in MQ Backout via PUC monitoring", "component": "PUC", "validation": "Backout queue not empty"},
                {"step": 2, "action": "Analyze message content and failure reason", "component": "MQ_ADMIN", "validation": "Root cause identified"},
                {"step": 3, "action": "Apply data fix if required", "component": "N3_DB_ACTION", "validation": "Data corrected"},
                {"step": 4, "action": "Move messages back to active queue", "component": "MQ_ADMIN", "validation": "Messages reprocessed"},
                {"step": 5, "action": "Monitor processing completion", "component": "BRASIL_IHM", "validation": "No new backout messages"}
            ],
            "error_paths": [],
            "confidence": "high",
            "source_file": "FR 003"
        }
    ]

    print(f"  [WF] Total workflows: {len(workflows)}")
    return workflows


# ─────────────────────────────────────────────
# LAYER 6 — LOG INTELLIGENCE
# ─────────────────────────────────────────────

def extract_log_patterns(log_dir, existing_log_events=None):
    """Extract error patterns from log files and existing log knowledge."""
    patterns = []

    # ── From log file analysis ──
    LOG_PATTERNS_RAW = [
        {
            "pattern": r"DSLAM .* closed for production",
            "error_type": "DSLAM_CLOSED_FOR_PRODUCTION",
            "component": "PortBooker / ManageTRProductionBusinessImpl",
            "impacted_entities": ["DSLAM", "CARD", "PORT"],
            "probable_causes": [
                "DSLAM manually closed for maintenance",
                "DSLAM status set to CLOSED in Orchestra NE repository",
                "DSLAM decommissioned but services not migrated"
            ],
            "recommended_checks": [
                "Check eqpt_prod_status in t_equipments for target DSLAM",
                "Verify Orchestra NE status for same DSLAM",
                "Check if maintenance ticket exists for this DSLAM",
                "Run: SELECT eqpt_name, eqpt_prod_status FROM t_equipments WHERE eqpt_name = '<DSLAM_NAME>'"
            ]
        },
        {
            "pattern": r"Card .* closed for production",
            "error_type": "CARD_CLOSED_FOR_PRODUCTION",
            "component": "PortBooker / ManageTRProductionBusinessImpl",
            "impacted_entities": ["CARD", "PORT", "DSLAM"],
            "probable_causes": [
                "Card hardware failure flagged",
                "Card manually closed for maintenance",
                "Card prod_status set to CLOSED in t_cards"
            ],
            "recommended_checks": [
                "Check card_prod_status in t_cards for target card",
                "Verify card number and chassis in t_d_dslam_xdsl_cards",
                "Check if other cards on same DSLAM are available",
                "Run: SELECT card_num, card_prod_status FROM t_cards WHERE eqpt_id = (SELECT eqpt_id FROM t_equipments WHERE eqpt_name='<DSLAM_NAME>')"
            ]
        },
        {
            "pattern": r"No port found with such constraints",
            "error_type": "PORT_NOT_FOUND",
            "component": "PortBooker / RechercherBrochesService",
            "impacted_entities": ["PORT", "DSLAM", "CARD"],
            "probable_causes": [
                "DSLAM TOC at 100% (saturated)",
                "port_attribuable field incorrectly set to 0",
                "All available ports already occupied",
                "Port counters desynchronized (port_logical_occup_cpt mismatch)"
            ],
            "recommended_checks": [
                "Run CalculerToc.ksh script (FR 001)",
                "Check dsme_mnl_available_port_count in t_d_dslam_manelems",
                "Verify port_attribuable = 1 for available ports",
                "Check t_d_dslam_xdsl_cards.dxcd_auto_available_port_count",
                "Run FR 1583B procedure if port counters suspect"
            ]
        },
        {
            "pattern": r"Aucune MRT Access DSLAM ne correspond aux critères",
            "error_type": "MRT_NOT_FOUND",
            "component": "ManageGetEptXdslTranslatorBusinessImpl / ObtenirEptXdslService",
            "impacted_entities": ["MRT", "DSLAM"],
            "probable_causes": [
                "MRT identifier expired or deleted",
                "Data migration incomplete",
                "DSLAM node changed without MRT update",
                "Incorrect search criteria"
            ],
            "recommended_checks": [
                "Search mrtd_id in t_mrt_access_dslams",
                "Check if recent data migration occurred",
                "Verify mrtd_nd and mrtd_customer_id match",
                "Check BRASIL-SEBA synchronization status"
            ]
        },
        {
            "pattern": r"Identifiant de Macro Ressource Technique .* inconnu",
            "error_type": "MRT_ID_UNKNOWN",
            "component": "LibererRessourcesXdslService",
            "impacted_entities": ["MRT", "MAKING_FILE"],
            "probable_causes": [
                "MRT already deleted before liberation",
                "Wrong MRT ID in making file",
                "Data synchronization issue between systems"
            ],
            "recommended_checks": [
                "SELECT * FROM t_mrt_access_dslams WHERE mrtd_id = <ID>",
                "Check t_making_files.mkfl_current_crc_id for the order",
                "Verify Orchestra referential for MRT status"
            ]
        },
        {
            "pattern": r"Le NumeroCCL est obligatoire dans le cas d'une offre CEV",
            "error_type": "CCL_MISSING_FOR_CEV",
            "component": "AffecterRessourcesXdslService",
            "impacted_entities": ["CCL", "MAKING_FILE", "EPC"],
            "probable_causes": [
                "CEV offer but no CCL number provided in order",
                "Incorrect business process type for CEV",
                "CCL not provisioned on target DSLAM"
            ],
            "recommended_checks": [
                "Check rpct_ccl_name in t_res_prod_controlables for target DSLAM",
                "Verify offer type is correctly set as CEV",
                "Check t_making_files.mkfl_business_process value",
                "Verify CCL provisioned in Francia for this DSLAM/NIP pair"
            ]
        },
        {
            "pattern": r"L'identifiant d'EPC .* est déjà utilisé par un autre EPC",
            "error_type": "EPC_DUPLICATE_ID",
            "component": "AffecterRessourcesXdslService",
            "impacted_entities": ["EPC"],
            "probable_causes": [
                "Duplicate EPC creation attempt",
                "Message replayed from backout queue",
                "Order system sent duplicate request"
            ],
            "recommended_checks": [
                "SELECT * FROM t_epcs WHERE epc_epc_id = '<EPC_ID>'",
                "Check MQ backout queue for duplicate messages",
                "Verify E-Basiliq order deduplication"
            ]
        },
        {
            "pattern": r"Identifiant de dossier de réalisation .* inconnu",
            "error_type": "MAKING_FILE_UNKNOWN",
            "component": "ModifierDonneesCommercialesEptXdslService / AffecterRessourcesXdslService",
            "impacted_entities": ["MAKING_FILE", "EPC"],
            "probable_causes": [
                "Making file already closed or archived",
                "Wrong file ID in message",
                "Concurrent modification deleted the file",
                "NIFolderID field incorrect"
            ],
            "recommended_checks": [
                "SELECT * FROM t_making_files WHERE mkfl_file_id = '<FILE_ID>'",
                "Check mkfl_status is not CLOSED/CANCELLED",
                "Verify IdEpc format in FR 012 procedure"
            ]
        },
        {
            "pattern": r"L'accès est déjà en cours de modification",
            "error_type": "CONCURRENT_MODIFICATION",
            "component": "AffecterRessourcesXdslService",
            "impacted_entities": ["MAKING_FILE", "EPC", "MRT"],
            "probable_causes": [
                "Another making file in progress for same ND",
                "Previous order not fully completed",
                "Deadlock left a file in intermediate state"
            ],
            "recommended_checks": [
                "SELECT * FROM t_making_files WHERE mkfl_nd = '<ND>' AND mkfl_status = 'IN_PROGRESS'",
                "Check if a deadlock recovery is pending",
                "Wait for active order to complete before retrying"
            ]
        },
        {
            "pattern": r"Un accès client existe déjà avec le même identifiant",
            "error_type": "MRT_CHEMIN_DUPLICATE",
            "component": "AffecterRessourcesXdslService",
            "impacted_entities": ["MRT", "EPC"],
            "probable_causes": [
                "MRTChemin ID already assigned to another MRTAccesDslam",
                "Previous order partially executed",
                "Data inconsistency between Brasil and Orchestra"
            ],
            "recommended_checks": [
                "SELECT * FROM t_mrt_access_dslams WHERE mrtd_crc_mrt_id = '<MRT_CHEMIN_ID>'",
                "Identify all MRTs using same crc_mrt_id",
                "Apply FR procedure to clean duplicate assignment"
            ]
        },
        {
            "pattern": r"deadlock detected",
            "error_type": "DB_DEADLOCK",
            "component": "AbstractBrasilMDBBean / ConnectorCLMDBBean / PostgreSQL",
            "impacted_entities": ["MAKING_FILE", "PORT", "CCL"],
            "probable_causes": [
                "Concurrent provisioning transactions on same DSLAM",
                "High load causing transaction conflicts",
                "Long-running transactions blocking others"
            ],
            "recommended_checks": [
                "Check PostgreSQL pg_locks for blocking queries",
                "Monitor ConnectorCL thread count",
                "Check retry counter - max 3 retries with 55s delay",
                "Review t_making_files for stuck orders after deadlock"
            ]
        },
        {
            "pattern": r"Resources not found for following TechServiceFunction",
            "error_type": "TSF_RESOURCES_NOT_FOUND",
            "component": "LogicalResBooker / ManageNetworkTRProductionBusinessImpl",
            "impacted_entities": ["TSF", "CCL", "DSLAM"],
            "probable_causes": [
                "TSF not provisioned on target DSLAM",
                "CCL for this TSF saturated or inactive",
                "Routing misconfiguration in t_d_rsc_dslam_tsfs"
            ],
            "recommended_checks": [
                "Check t_d_rsc_dslam_tsfs for target DSLAM",
                "Verify t_res_prod_controlables status for related CCL",
                "Check t_res_prod_roles for DSLAM/NIP binding",
                "Run FR 137 routing check procedure"
            ]
        },
        {
            "pattern": r"current transaction is aborted, commands ignored",
            "error_type": "TX_ABORTED",
            "component": "SqlExceptionHelper / PostgreSQL",
            "impacted_entities": ["MAKING_FILE"],
            "probable_causes": [
                "Previous statement in same transaction failed (usually after deadlock)",
                "Transaction not rolled back before continuing"
            ],
            "recommended_checks": [
                "Check if preceded by deadlock error",
                "Verify ConnectorCL retry logic executed rollback",
                "Check t_making_files for orphaned in-progress orders"
            ]
        }
    ]

    for i, raw in enumerate(LOG_PATTERNS_RAW):
        patterns.append({
            "id": f"LOG-PATTERN-{i+1:03d}",
            "pattern_regex": raw["pattern"],
            "error_type": raw["error_type"],
            "component": raw["component"],
            "impacted_entities": raw["impacted_entities"],
            "probable_causes": raw["probable_causes"],
            "recommended_checks": raw["recommended_checks"],
            "confidence": "high",
            "source_file": "data_pipeline/input/*.log"
        })

    # ── Absorb existing log_knowledge records ──
    if existing_log_events and isinstance(existing_log_events, dict):
        records = existing_log_events.get("records", [])
        for rec in records:
            exc = rec.get("exception", "")
            if exc:
                patterns.append({
                    "id": f"LOG-{rec.get('record_id', hashlib.md5(exc.encode()).hexdigest()[:8])}",
                    "pattern_regex": exc,
                    "error_type": exc,
                    "component": f"{rec.get('application','BRASIL')}/{rec.get('component','unknown')}",
                    "impacted_entities": rec.get("related_systems", []),
                    "probable_causes": [clean_text(rec.get("probable_root_cause", ""))],
                    "recommended_checks": [clean_text(a) for a in rec.get("diagnostic_actions", [])],
                    "confidence": "medium" if rec.get("frequency", 0) == 0 else "high",
                    "source_file": "data_pipeline/output/log_knowledge.json"
                })

    print(f"  [LOG] Total log patterns: {len(patterns)}")
    return patterns


# ─────────────────────────────────────────────
# GRAPH CONSTRUCTION
# ─────────────────────────────────────────────

def build_graph(telecom_entities, sql_entities, system_entities, fr_entities, relationships):
    """Merge all entities and relationships into a unified graph."""
    
    nodes = {}
    edges = []
    
    # Add all entity collections
    for eid, entity in telecom_entities.items():
        nodes[eid] = entity
    
    for eid, entity in sql_entities.items():
        if eid not in nodes:
            nodes[eid] = entity
    
    for eid, entity in system_entities.items():
        nodes[eid] = entity

    for eid, entity in fr_entities.items():
        if eid not in nodes:
            nodes[eid] = entity

    # Add edges
    edge_set = set()
    for rel in relationships:
        src = rel.get("source", "")
        tgt = rel.get("target", "")
        rtype = rel.get("type", "RELATED_TO")
        
        if not src or not tgt:
            continue
        
        edge_key = f"{src}|{rtype}|{tgt}"
        if edge_key in edge_set:
            continue
        edge_set.add(edge_key)
        
        edges.append({
            "source": src,
            "target": tgt,
            "type": rtype,
            "description": rel.get("description", ""),
            "confidence": rel.get("confidence", "medium"),
            "source_file": rel.get("source_file", "unknown"),
            "via_column": rel.get("via_column", None)
        })

    # Graph density
    n = len(nodes)
    e = len(edges)
    density = round(e / (n * (n - 1)) if n > 1 else 0, 4)

    print(f"  [GRAPH] Nodes: {n}, Edges: {e}, Density: {density}")
    return {
        "nodes": list(nodes.values()),
        "edges": edges,
        "_meta": {
            "nodes_count": n,
            "edges_count": e,
            "density": density
        }
    }


# ─────────────────────────────────────────────
# SELF-VALIDATION
# ─────────────────────────────────────────────

def self_validate(entities_all, relationships, constraints):
    """Detect issues: duplicates, missing links, orphan nodes, conflicting rels."""
    issues = []
    
    # Check for duplicate entity names
    name_seen = {}
    for eid, entity in entities_all.items():
        name = entity.get("name", "").upper()
        if name in name_seen:
            issues.append({
                "type": "duplicate_name",
                "severity": "warning",
                "entities": [eid, name_seen[name]],
                "message": f"Duplicate entity name: {name}"
            })
        else:
            name_seen[name] = eid

    # Check for relationships pointing to non-existent entities
    entity_ids = set(entities_all.keys())
    for rel in relationships:
        src = rel.get("source", "")
        tgt = rel.get("target", "")
        if src not in entity_ids:
            issues.append({
                "type": "missing_source",
                "severity": "warning",
                "rel": f"{src} → {tgt}",
                "message": f"Relationship source not in entity set: {src}"
            })
        if tgt not in entity_ids:
            issues.append({
                "type": "missing_target",
                "severity": "info",
                "rel": f"{src} → {tgt}",
                "message": f"Relationship target not in entity set: {tgt}"
            })

    # Detect constraint-entity mismatches
    for cstr in constraints:
        for entity_name in cstr.get("affected_entities", []):
            found = any(
                e.get("name", "").upper() == entity_name.upper() or
                e.get("type", "").upper() == entity_name.upper()
                for e in entities_all.values()
            )
            if not found:
                issues.append({
                    "type": "constraint_entity_missing",
                    "severity": "info",
                    "constraint": cstr.get("id"),
                    "missing_entity": entity_name,
                    "message": f"Constraint {cstr['id']} references unknown entity: {entity_name}"
                })

    return issues


# ─────────────────────────────────────────────
# SELF-IMPROVEMENT LOOP
# ─────────────────────────────────────────────

def self_improve(entities_all, relationships, constraints, issues):
    """Second pass: fix detectable issues, upgrade confidence, add missing links."""
    
    # Upgrade confidence for multi-source confirmed constraints
    upgraded = 0
    for cstr in constraints:
        if cstr.get("multi_source") and cstr.get("confidence") != "high":
            cstr["confidence"] = "high"
            upgraded += 1
    
    # Merge relationships with same source/target/type but different sources
    rel_map = {}
    for rel in relationships:
        key = (rel.get("source"), rel.get("target"), rel.get("type"))
        if key in rel_map:
            existing = rel_map[key]
            # Merge sources
            existing_src = existing.get("source_file", "")
            new_src = rel.get("source_file", "")
            if new_src not in existing_src:
                existing["source_file"] = f"{existing_src} + {new_src}"
                existing["confidence"] = "high"  # multi-source = high
        else:
            rel_map[key] = rel

    merged_relationships = list(rel_map.values())

    # Remove info-level issues that are just missing FK targets (SQL tables not in domain model)
    filtered_issues = [i for i in issues if i.get("severity") in ("warning", "error")]

    print(f"  [IMPROVE] Upgraded {upgraded} constraints. Merged to {len(merged_relationships)} relationships.")
    return entities_all, merged_relationships, constraints, filtered_issues


# ─────────────────────────────────────────────
# DIAGNOSTIC RULES
# ─────────────────────────────────────────────

def generate_diagnostic_rules(constraints, log_patterns, workflows):
    """Generate N3-level diagnostic rules from multi-source correlation."""
    
    rules = [
        {
            "id": "DIAG-001",
            "incident_type": "port_assignment_failure",
            "title": "Recherche de broche en échec (Port Assignment Failure)",
            "detected_on": ["AffecterRessourcesXdslService", "RechercherBrochesService", "PortBooker"],
            "log_indicators": [
                "No port found with such constraints",
                "Echec de la recherche de broche",
                "DSLAM closed for production",
                "Card closed for production"
            ],
            "probable_causes": [
                "DSLAM production status CLOSED (eqpt_prod_status='F')",
                "Card production status CLOSED (card_prod_status='F')",
                "DSLAM TOC at 100% - no available ports",
                "port_attribuable = 0 incorrectly set",
                "Port counters desynchronized in t_d_dslam_xdsl_cards"
            ],
            "related_entities": ["DSLAM", "CARD", "PORT", "MAKING_FILE"],
            "related_constraints": ["CSTR-FR-001", "CSTR-FR-002", "CSTR-FR-007", "CSTR-SQL-005"],
            "recommended_checks": [
                "SELECT eqpt_name, eqpt_prod_status FROM t_equipments WHERE eqpt_name='<DSLAM_NAME>'",
                "Run CalculerToc.ksh (FR 001) to verify TOC percentage",
                "SELECT card_num, card_prod_status FROM t_cards WHERE eqpt_id=<DSLAM_EQPT_ID>",
                "Check dsme_auto_available_port_count in t_d_dslam_manelems",
                "Check port_attribuable in t_ports for target DSLAM ports",
                "If TOC=100% and ports appear free: run FR 1583B procedure"
            ],
            "resolution_steps": [
                "If DSLAM closed: open DSLAM in BRASIL IHM → verify in Orchestra",
                "If card closed: open card or identify alternative card",
                "If TOC=100% but ports available: run counter recalculation (FR 001)",
                "If port_attribuable=0: investigate why and correct per FR 1583"
            ],
            "confidence": "high",
            "sources_correlated": ["brasil_db.sql", "FR 001", "FR 1583", "FR 1583B", "logs/connectorCL"]
        },
        {
            "id": "DIAG-002",
            "incident_type": "ccl_resource_failure",
            "title": "CCL/VC Resource Unavailable (Logical Resource Booking Failure)",
            "detected_on": ["LogicalResBooker", "ManageNetworkTRProductionBusinessImpl"],
            "log_indicators": [
                "Resources not found for following TechServiceFunction",
                "TechnicalException (BrasilInternalErrorException) sur la réservation de ressources",
                "Le NumeroCCL est obligatoire dans le cas d'une offre CEV"
            ],
            "probable_causes": [
                "TSF not provisioned on target DSLAM (t_d_rsc_dslam_tsfs empty)",
                "CCL saturated: allocated_vc_count >= vc_max",
                "CCL production status inactive",
                "CEV offer without CCL number in order",
                "Routing misconfiguration (VP/VLAN counter mismatch)"
            ],
            "related_entities": ["TSF", "CCL", "VLAN", "VP_VC", "DSLAM", "NIP"],
            "related_constraints": ["CSTR-FR-003", "CSTR-FR-013", "CSTR-FR-019", "CSTR-SQL-006"],
            "recommended_checks": [
                "SELECT * FROM t_d_rsc_dslam_tsfs WHERE dslam_eqpt_id=<ID>",
                "SELECT rpct_ccl_name, rpct_vc_max, rpct_allocated_vc_count FROM t_res_prod_controlables WHERE a_eqpt_id=<DSLAM_ID>",
                "Check rpct_prod_status in t_res_prod_controlables",
                "Verify offer type requires CCL (CEV/GE offers)",
                "Run FR 136b/FR 136c counter verification"
            ],
            "resolution_steps": [
                "If TSF missing: provision TSF via network team",
                "If CCL saturated: request CCL capacity extension",
                "If CEV with missing CCL: verify order includes CCL number",
                "If counter mismatch: apply FR 136b/136c correction procedure"
            ],
            "confidence": "high",
            "sources_correlated": ["brasil_db.sql", "FR 135", "FR 136b", "FR 136c", "FR 137", "logs/connectorCL"]
        },
        {
            "id": "DIAG-003",
            "incident_type": "mrt_not_found",
            "title": "MRT/EPC Not Found (Référentiel Inconsistency)",
            "detected_on": ["ObtenirEptXdslService", "LibererRessourcesXdslService", "ManageGetEptXdslTranslatorBusinessImpl"],
            "log_indicators": [
                "Aucune MRT Access DSLAM ne correspond aux critères de recherche",
                "Identifiant de Macro Ressource Technique inconnu",
                "Erreur interne Brasil - Aucune MRT Access DSLAM"
            ],
            "probable_causes": [
                "MRT deleted before service liberation",
                "Data migration incomplete (MRT not propagated)",
                "DSLAM node changed without MRT update",
                "MRT ID expired or wrong ID in order",
                "BRASIL-SEBA synchronization gap"
            ],
            "related_entities": ["MRT", "EPC", "DSLAM", "MAKING_FILE"],
            "related_constraints": ["CSTR-FR-005", "CSTR-FR-006"],
            "recommended_checks": [
                "SELECT * FROM t_mrt_access_dslams WHERE mrtd_id=<MRT_ID>",
                "SELECT * FROM t_mrt_access_dslams WHERE mrtd_nd='<ND>' AND mrtd_customer_id='<CLIENT_ID>'",
                "Check if recent data migration affected this ND",
                "Verify making file contains correct MRT reference",
                "Compare BRASIL data with SEBA/Orchestra referential"
            ],
            "resolution_steps": [
                "If MRT missing: recreate via admin procedure",
                "If wrong ID: identify correct MRT and update order",
                "If migration issue: force BRASIL-SEBA resync for this ND",
                "If node changed: verify MRT points to correct DSLAM/node"
            ],
            "confidence": "high",
            "sources_correlated": ["brasil_db.sql", "FR_docs", "logs/connectorCL"]
        },
        {
            "id": "DIAG-004",
            "incident_type": "data_synchronization_failure",
            "title": "Data Synchronization Failure (Orchestra-Brasil-SEBA)",
            "detected_on": ["ConnectorCL", "ConnectorUMIepc", "E_BASILIQ"],
            "log_indicators": [
                "Un accès client existe déjà avec le même identifiant",
                "Identifiant de dossier de réalisation inconnu",
                "BRASIL ERROR 1002"
            ],
            "probable_causes": [
                "Duplicate EPC/MRT from replayed MQ message",
                "Making file ID mismatch between systems",
                "NIFolderID or UPDATEDMRTLIST field missing/malformed",
                "Orchestra-Brasil desynchronization after weekend resynchro"
            ],
            "related_entities": ["EPC", "MRT", "MAKING_FILE", "SYSTEM:E_BASILIQ", "SYSTEM:ORCHESTRA"],
            "related_constraints": ["CSTR-FR-004", "CSTR-FR-006", "CSTR-FR-014", "CSTR-FR-015"],
            "recommended_checks": [
                "Check MQ backout queue for duplicate messages",
                "SELECT * FROM t_epcs WHERE epc_epc_id='<EPC_ID>'",
                "Verify message format: NIFolderID and UPDATEDMRTLIST present",
                "Check E-Basiliq PUC for MQ queue congestion",
                "Compare Orchestra referential with Brasil data for affected ND"
            ],
            "resolution_steps": [
                "If duplicate: purge backout queue duplicate",
                "If field missing: fix sender system (Orchestra/E-Basiliq)",
                "If desync post-weekend: use FR 002 mass UMI-EPC resend",
                "If making file mismatch: reset order and recreate"
            ],
            "confidence": "high",
            "sources_correlated": ["FR 002", "FR 003", "FR 012", "FR 013", "logs"]
        },
        {
            "id": "DIAG-005",
            "incident_type": "db_concurrency_issue",
            "title": "Database Deadlock / Transaction Failure",
            "detected_on": ["AbstractBrasilMDBBean", "ConnectorCLMDBBean", "SqlExceptionHelper"],
            "log_indicators": [
                "deadlock detected",
                "PSQLException: ERROR: deadlock detected",
                "current transaction is aborted, commands ignored until end of transaction block",
                "LockAcquisitionException"
            ],
            "probable_causes": [
                "Concurrent provisioning orders on same DSLAM",
                "High load on ConnectorCL (multiple RabbitMQ consumers)",
                "Long-running transactions holding locks",
                "CASCADE update/delete conflicts"
            ],
            "related_entities": ["MAKING_FILE", "PORT", "CCL", "DSLAM"],
            "related_constraints": ["CSTR-FR-010"],
            "recommended_checks": [
                "Check pg_locks in PostgreSQL for blocking sessions",
                "Monitor ConnectorCL thread pool utilization",
                "Check t_making_files for orders stuck in IN_PROGRESS state",
                "Review retry counter: 3 retries × 55s delay",
                "Check if deadlock involves t_ports or t_res_prod_controlables"
            ],
            "resolution_steps": [
                "System auto-retries 3 times with 55s delay",
                "If persistent: check PostgreSQL connection pool settings",
                "If orders stuck: manually close and replay from IHM Brasil",
                "Long-term: review concurrent access patterns on high-load DSLAMs"
            ],
            "confidence": "high",
            "sources_correlated": ["logs/connectorCL", "brasil_db.sql"]
        },
        {
            "id": "DIAG-006",
            "incident_type": "node_dslam_mismatch",
            "title": "Node/DSLAM Mismatch between Brasil and Référentiel Sites",
            "detected_on": ["BRASIL_IHM", "Orchestra"],
            "log_indicators": [
                "Node present in Référentiel Sites absent in BRASIL",
                "DSLAM node association incorrect"
            ],
            "probable_causes": [
                "Node created in Référentiel Sites but not synced to Brasil",
                "DSLAM moved to different node without Brasil update",
                "Node code42C mismatch between systems"
            ],
            "related_entities": ["NODE", "DSLAM", "DR_ZONE"],
            "related_constraints": ["CSTR-FR-012"],
            "recommended_checks": [
                "SELECT * FROM t_nodes WHERE node_base_code42c='<CODE42C>'",
                "Compare with Orchestra Référentiel Sites record",
                "Check t_equipments.node_id for affected DSLAMs",
                "Verify t_dslam_access_constraints for node"
            ],
            "resolution_steps": [
                "If node missing in Brasil: create via admin procedure",
                "If DSLAM on wrong node: apply FR 152 (Modifier nœud DSLAM)",
                "If constraint missing: apply FR 150 procedure",
                "Resync Brasil with Orchestra Référentiel Sites"
            ],
            "confidence": "high",
            "sources_correlated": ["FR 148", "FR 150", "FR 151", "FR 152", "brasil_db.sql"]
        },
        {
            "id": "DIAG-007",
            "incident_type": "mutation_failure",
            "title": "Link Mutation Failure",
            "detected_on": ["ManageTRProductionBusinessImpl", "MutationService"],
            "log_indicators": [
                "mutation blocked",
                "DSLAM closed for production",
                "No port found"
            ],
            "probable_causes": [
                "Target DSLAM closed for production",
                "No available ports on target DSLAM",
                "MRT already in mutation state",
                "Missing constraint on target repartiteur/node"
            ],
            "related_entities": ["MUTATION", "DSLAM", "NODE", "MRT", "PORT"],
            "related_constraints": ["CSTR-FR-001", "CSTR-FR-007", "CSTR-FR-012"],
            "recommended_checks": [
                "Verify target DSLAM production status",
                "Run CalculerToc on target DSLAM",
                "Check t_mutations_requests.murq_status",
                "Verify t_dslam_access_constraints for target node"
            ],
            "resolution_steps": [
                "Open target DSLAM if closed",
                "Apply FR 100 (Mutation de Liens) procedure",
                "If constraint missing: apply FR 150",
                "Verify new port assignment after mutation"
            ],
            "confidence": "high",
            "sources_correlated": ["FR 100", "brasil_db.sql"]
        },
        {
            "id": "DIAG-008",
            "incident_type": "vc_vlan_counter_mismatch",
            "title": "VP/VLAN/VC Counter Mismatch (Logical Resource Counter Error)",
            "detected_on": ["BRASIL_IHM", "SQL"],
            "log_indicators": [
                "AFFECTATION SUR CCL VC DEJA OCCUPE",
                "compteurs VC VP VLAN OCCUPE A TORT"
            ],
            "probable_causes": [
                "Counter not updated after failed transaction",
                "Manual intervention modified data without counter update",
                "Software bug in counter management (BRASIL-439)"
            ],
            "related_entities": ["CCL", "VP_VC", "VLAN", "DSLAM"],
            "related_constraints": ["CSTR-FR-013"],
            "recommended_checks": [
                "SELECT rpct_allocated_vc_count, rpct_vc_max FROM t_res_prod_controlables WHERE rpct_ccl_name='<CCL_NAME>'",
                "COUNT actual VCs on CCL vs stored counter",
                "Check t_d_controlable_rscs.ctrs_occupied_count vs actual",
                "Run FR 136c counter verification procedure"
            ],
            "resolution_steps": [
                "Apply FR 136b (Libérer ports occupés à tort)",
                "Apply FR 136c (VP VLAN VC counter correction)",
                "Run counter recalculation via N3 script",
                "Verify after correction: counters match reality"
            ],
            "confidence": "high",
            "sources_correlated": ["FR 135", "FR 136", "FR 136b", "FR 136c", "brasil_db.sql"]
        },
        {
            "id": "DIAG-009",
            "incident_type": "encoding_corruption",
            "title": "Character Encoding Corruption in Database",
            "detected_on": ["t_ports.t_remarks", "Database"],
            "log_indicators": [
                "CARACTERES ERRONES EN BASE BRASIL",
                "encoding_correct table"
            ],
            "probable_causes": [
                "UTF-8/Latin-1 encoding mismatch on data import",
                "Connector encoding misconfiguration",
                "Database migration encoding error"
            ],
            "related_entities": ["PORT", "EQUIPMENT"],
            "related_constraints": [],
            "recommended_checks": [
                "Check encoding_correct table for affected records",
                "Query t_ports.port_remarks for garbled characters",
                "Verify database connection encoding settings"
            ],
            "resolution_steps": [
                "Apply FR 077 encoding correction procedure",
                "Use encoding_correct table to identify and fix affected records",
                "Correct database connection charset to UTF-8"
            ],
            "confidence": "high",
            "sources_correlated": ["FR 077", "brasil_db.sql (encoding_correct table)"]
        },
        {
            "id": "DIAG-010",
            "incident_type": "sca_blocking",
            "title": "SCA Blocking Due to Missing FARID or RemoteID",
            "detected_on": ["SCA", "AffecterRessourcesXdslService"],
            "log_indicators": [
                "SCA blocked",
                "FARID missing",
                "RemoteID absent"
            ],
            "probable_causes": [
                "EPC order missing FARID field",
                "RemoteID not generated for FTTH/GPON service",
                "SCA-Brasil interface configuration error"
            ],
            "related_entities": ["EPC", "MRT", "MAKING_FILE", "SYSTEM:SCA"],
            "related_constraints": ["CSTR-FR-011"],
            "recommended_checks": [
                "Check mrtd_farid in t_mrt_access_dslams",
                "Check mras_remote_id in t_mrt_access_services",
                "Verify SCA interface configuration",
                "Check if offer type requires FARID/RemoteID"
            ],
            "resolution_steps": [
                "Apply FR 010 (Blocage SCA) procedure",
                "Fill missing FARID/RemoteID fields",
                "Contact SCA team if interface issue"
            ],
            "confidence": "high",
            "sources_correlated": ["FR 010", "brasil_db.sql"]
        },
        {
            "id": "DIAG-011",
            "incident_type": "error_type_1300",
            "title": "Error Type 1300 (Brasil Internal Classification Error)",
            "detected_on": ["BRASIL", "ConnectorCL"],
            "log_indicators": [
                "BRASIL erreur 1300",
                "type d'erreur 1300"
            ],
            "probable_causes": [
                "Internal Brasil classification error",
                "Service type not matching equipment capability",
                "Configuration data missing for requested service"
            ],
            "related_entities": ["EPC", "MAKING_FILE", "DSLAM"],
            "related_constraints": [],
            "recommended_checks": [
                "Check Brasil logs for exact 1300 error context",
                "Verify offer type vs DSLAM/card capabilities",
                "Apply FR 130 analysis procedure"
            ],
            "resolution_steps": [
                "Apply FR 130 (Les types d'erreur 1300) procedure",
                "Analyze logs for specific sub-type of 1300",
                "Contact Brasil N3 team for configuration fix"
            ],
            "confidence": "medium",
            "sources_correlated": ["FR 130"]
        },
        {
            "id": "DIAG-012",
            "incident_type": "port_search_failure_300_327",
            "title": "Port Search Failure with Error 300 or 327",
            "detected_on": ["RechercherBrochesService", "BRASIL"],
            "log_indicators": [
                "RECHERCHE DE BROCHE EN ECHEC",
                "300", "327"
            ],
            "probable_causes": [
                "DSLAM port counter at 100% (TOC)",
                "port_attribuable field incorrectly set",
                "Wrong port group assignment",
                "DSLAM shelf/card configuration error"
            ],
            "related_entities": ["PORT", "DSLAM", "CARD", "SHELF"],
            "related_constraints": ["CSTR-FR-007", "CSTR-SQL-005"],
            "recommended_checks": [
                "Apply FR 1583B specific diagnosis",
                "Check port_attribuable for all ports on DSLAM",
                "Verify t_d_dslam_xdsl_cards counters",
                "Compare available vs occupied port counts"
            ],
            "resolution_steps": [
                "Apply FR 1583B procedure (Recherche de broche en échec 300 ou 327)",
                "Fix port_attribuable if incorrectly 0",
                "Recalculate TOC with FR 001",
                "Escalate to BRASIL development team if persistent"
            ],
            "confidence": "high",
            "sources_correlated": ["FR 1583", "FR 1583B", "brasil_db.sql"]
        }
    ]

    print(f"  [DIAG] Total diagnostic rules: {len(rules)}")
    return rules


# ─────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────

def run_pipeline():
    print("\n" + "="*60)
    print("BRASIL KNOWLEDGE EXTRACTION PIPELINE")
    print("="*60)
    
    # ── Load existing data ──
    print("\n[1/7] Loading existing pipeline outputs...")
    fr_data = load_json(FR_PARSED)
    if isinstance(fr_data, list):
        print(f"  [FR] Loaded {len(fr_data)} FR parsed documents")
    log_events = load_json(LOG_EVENTS)
    log_knowledge = load_json(LOG_KNOWLEDGE)
    existing_procedures = load_json(PROCEDURES)
    existing_kg = load_json(KNOWLEDGE_GRAPH)

    # ── LAYER 1+2: Entity Discovery & Structural Mapping ──
    print("\n[2/7] Layer 1+2: Entity Discovery & Structural Mapping...")
    sql_entities, sql_fk_rels = extract_sql_entities(SQL_SCHEMA)
    fr_entities = extract_fr_entities(fr_data)

    # Separate system entities
    system_entities = {k: v for k, v in fr_entities.items() if k.startswith("SYSTEM:")}
    error_code_entities = {k: v for k, v in fr_entities.items() if k.startswith("ERROR:")}

    # Combine all entity dicts
    all_entities = {}
    all_entities.update(TELECOM_ENTITIES)
    all_entities.update(sql_entities)
    all_entities.update(system_entities)
    all_entities.update(error_code_entities)

    print(f"  [TOTAL] {len(TELECOM_ENTITIES)} telecom + {len(sql_entities)} SQL + {len(system_entities)} systems + {len(error_code_entities)} error codes = {len(all_entities)} entities")

    # ── LAYER 3: Relationships ──
    print("\n[3/7] Layer 3: Relationship Extraction...")
    relationships = build_structural_relationships(sql_entities, sql_fk_rels, TELECOM_ENTITIES)

    # ── LAYER 4: Constraints ──
    print("\n[4/7] Layer 4: Constraints Extraction...")
    sql_content = SQL_SCHEMA.read_text(encoding="utf-8", errors="replace") if SQL_SCHEMA.exists() else ""
    constraints = extract_constraints(fr_data, sql_content)

    # ── LAYER 5: Workflows ──
    print("\n[5/7] Layer 5: Workflow Extraction...")
    workflows = extract_workflows(fr_data)

    # ── LAYER 6: Log Intelligence ──
    print("\n[6/7] Layer 6: Log Intelligence...")
    log_patterns = extract_log_patterns(LOG_DIR, log_knowledge)

    # ── GRAPH CONSTRUCTION ──
    print("\n[7/7] Building Unified Knowledge Graph...")
    graph_data = build_graph(TELECOM_ENTITIES, sql_entities, system_entities, error_code_entities, relationships)

    # ── SELF-VALIDATION ──
    print("\n[VALIDATE] Running self-validation...")
    issues = self_validate(all_entities, relationships, constraints)
    print(f"  [VALIDATE] {len(issues)} issues detected")

    # ── SELF-IMPROVEMENT ──
    print("\n[IMPROVE] Running self-improvement loop...")
    all_entities, relationships, constraints, filtered_issues = self_improve(
        all_entities, relationships, constraints, issues
    )

    # Rebuild graph after improvement
    graph_data = build_graph(TELECOM_ENTITIES, sql_entities, system_entities, error_code_entities, relationships)

    # ── DIAGNOSTIC RULES ──
    print("\n[DIAG] Generating diagnostic rules...")
    diagnostic_rules = generate_diagnostic_rules(constraints, log_patterns, workflows)

    # ─────────────────────────────────────────────
    # OUTPUT PHASE
    # ─────────────────────────────────────────────
    print("\n" + "="*60)
    print("GENERATING OUTPUT FILES")
    print("="*60)

    # 1. brasil_entities.json
    entities_output = {
        "generated_at": NOW,
        "pipeline_version": "2.0",
        "total_entities": len(all_entities),
        "by_type": {},
        "entities": list(all_entities.values())
    }
    by_type = {}
    for e in all_entities.values():
        t = e.get("type", "UNKNOWN")
        by_type[t] = by_type.get(t, 0) + 1
    entities_output["by_type"] = by_type
    save_json(OUTPUT_DIR / "brasil_entities.json", entities_output)

    # 2. brasil_relationships.json
    relationships_output = {
        "generated_at": NOW,
        "pipeline_version": "2.0",
        "total_relationships": len(relationships),
        "by_type": {},
        "relationships": relationships
    }
    by_rel_type = {}
    for r in relationships:
        rt = r.get("type", "UNKNOWN")
        by_rel_type[rt] = by_rel_type.get(rt, 0) + 1
    relationships_output["by_type"] = by_rel_type
    save_json(OUTPUT_DIR / "brasil_relationships.json", relationships_output)

    # 3. brasil_constraints.json
    constraints_output = {
        "generated_at": NOW,
        "pipeline_version": "2.0",
        "total_constraints": len(constraints),
        "blocking_count": sum(1 for c in constraints if c.get("severity") == "blocking"),
        "warning_count": sum(1 for c in constraints if c.get("severity") == "warning"),
        "constraints": constraints
    }
    save_json(OUTPUT_DIR / "brasil_constraints.json", constraints_output)

    # 4. brasil_workflows.json
    workflows_output = {
        "generated_at": NOW,
        "pipeline_version": "2.0",
        "total_workflows": len(workflows),
        "workflows": workflows
    }
    save_json(OUTPUT_DIR / "brasil_workflows.json", workflows_output)

    # 5. brasil_logs_patterns.json
    logs_output = {
        "generated_at": NOW,
        "pipeline_version": "2.0",
        "total_patterns": len(log_patterns),
        "log_files_scanned": [str(p) for p in LOG_DIR.glob("*.log")] if LOG_DIR.exists() else [],
        "patterns": log_patterns
    }
    save_json(OUTPUT_DIR / "brasil_logs_patterns.json", logs_output)

    # 6. brasil_graph.json
    graph_output = {
        "generated_at": NOW,
        "pipeline_version": "2.0",
        "nodes": graph_data["nodes"],
        "edges": graph_data["edges"],
        "stats": {
            "nodes_count": graph_data["_meta"]["nodes_count"],
            "edges_count": graph_data["_meta"]["edges_count"],
            "graph_density": graph_data["_meta"]["density"],
            "nodes_by_type": {},
            "edges_by_type": {}
        }
    }
    for node in graph_data["nodes"]:
        t = node.get("type", "UNKNOWN")
        graph_output["stats"]["nodes_by_type"][t] = graph_output["stats"]["nodes_by_type"].get(t, 0) + 1
    for edge in graph_data["edges"]:
        t = edge.get("type", "UNKNOWN")
        graph_output["stats"]["edges_by_type"][t] = graph_output["stats"]["edges_by_type"].get(t, 0) + 1
    save_json(OUTPUT_DIR / "brasil_graph.json", graph_output)

    # 7. brasil_diagnostic_rules.json
    diagnostic_output = {
        "generated_at": NOW,
        "pipeline_version": "2.0",
        "total_rules": len(diagnostic_rules),
        "validation_report": {
            "entities_count": len(all_entities),
            "relationships_count": len(relationships),
            "constraints_count": len(constraints),
            "workflows_count": len(workflows),
            "log_patterns_count": len(log_patterns),
            "graph_density": graph_data["_meta"]["density"],
            "issues_detected": filtered_issues,
            "issues_count": len(filtered_issues),
            "confidence_distribution": {
                "high": sum(1 for r in diagnostic_rules if r.get("confidence") == "high"),
                "medium": sum(1 for r in diagnostic_rules if r.get("confidence") == "medium"),
                "low": sum(1 for r in diagnostic_rules if r.get("confidence") == "low")
            }
        },
        "rules": diagnostic_rules
    }
    save_json(OUTPUT_DIR / "brasil_diagnostic_rules.json", diagnostic_output)

    # ── FINAL SUMMARY ──
    print("\n" + "="*60)
    print("PIPELINE COMPLETE — SUMMARY")
    print("="*60)
    print(f"  Entities       : {len(all_entities)}")
    print(f"  Relationships  : {len(relationships)}")
    print(f"  Constraints    : {len(constraints)} ({constraints_output['blocking_count']} blocking, {constraints_output['warning_count']} warning)")
    print(f"  Workflows      : {len(workflows)}")
    print(f"  Log Patterns   : {len(log_patterns)}")
    print(f"  Graph Nodes    : {graph_data['_meta']['nodes_count']}")
    print(f"  Graph Edges    : {graph_data['_meta']['edges_count']}")
    print(f"  Graph Density  : {graph_data['_meta']['density']}")
    print(f"  Diagnostic Rules: {len(diagnostic_rules)}")
    print(f"  Issues detected: {len(filtered_issues)}")
    print(f"\n  Output directory: {OUTPUT_DIR}")
    print("="*60)

    return {
        "status": "success",
        "output_dir": str(OUTPUT_DIR),
        "files": [
            "brasil_entities.json",
            "brasil_relationships.json",
            "brasil_constraints.json",
            "brasil_workflows.json",
            "brasil_logs_patterns.json",
            "brasil_graph.json",
            "brasil_diagnostic_rules.json"
        ],
        "stats": {
            "entities": len(all_entities),
            "relationships": len(relationships),
            "constraints": len(constraints),
            "workflows": len(workflows),
            "log_patterns": len(log_patterns),
            "diagnostic_rules": len(diagnostic_rules)
        }
    }


if __name__ == "__main__":
    result = run_pipeline()
    sys.exit(0 if result["status"] == "success" else 1)
