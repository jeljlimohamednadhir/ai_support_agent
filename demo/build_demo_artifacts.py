import json
from pathlib import Path
from typing import Any, Dict, List

BASE = Path(__file__).resolve().parent
SCENARIOS_DIR = BASE / "scenarios"

MANDATORY_SECTIONS = [
    "Diagnostic",
    "Evidence",
    "Workflow",
    "Source Code",
    "Action",
    "Provenance",
]


def scenario(
    sid: str,
    category: str,
    question: str,
    expected_root_cause: str,
    expected_workflow: str,
    expected_evidence: List[str],
    expected_code_reference: str,
    expected_sources: List[str],
    required_mentions: List[str],
    forbidden_patterns: List[str],
) -> Dict[str, Any]:
    return {
        "id": sid,
        "tier": "GOLDEN",
        "category": category,
        "question": question,
        "expected_root_cause": expected_root_cause,
        "expected_workflow": expected_workflow,
        "expected_evidence": expected_evidence,
        "expected_code_reference": expected_code_reference,
        "expected_sources": expected_sources,
        "expected_response_contract": {
            "mandatory_sections": MANDATORY_SECTIONS,
            "required_mentions": required_mentions,
            "forbidden_patterns": forbidden_patterns,
        },
    }


SCENARIOS: List[Dict[str, Any]] = [
    scenario("TEST_01", "equipment_deletion", "Suppression équipement DSROB362 impossible", "Suppression bloquée par dépendances actives (MRT/services/données résiduelles)", "delete_dslam", ["dépendances MRT", "services actifs", "données résiduelles"], "ManageDslamBusinessImpl.deleteDslam()", ["LIVE_DB", "CODE", "FR"], ["dépendances MRT", "services actifs", "données résiduelles", "ManageDslamBusinessImpl.deleteDslam()"], ["DELETE ", "UPDATE ", "hypothèse", "je pense"]),
    scenario("TEST_02", "code_lookup", "Quelle est la méthode Java qui supprime un DSLAM ?", "Requête de localisation code (pas de diagnostic incident)", "code_lookup_only", ["classe", "méthode", "fichier", "ligne"], "ManageDslamBusinessImpl.deleteDslam()", ["CODE"], ["ManageDslamBusinessImpl", "deleteDslam()"], ["procédure métier", "workflow FR"]),
    scenario("TEST_03", "vlan_creation", "Comment créer un VLAN ?", "Demande de workflow de création VLAN", "create_vlan", ["validation d'entrée", "contrôle ressources", "création", "activation", "vérification"], "ManageCreationVlanBusinessImpl.creerVlan()", ["CODE", "FR"], ["ManageCreationVlanBusinessImpl.creerVlan()"], ["http://", "https://", "menu IHM", "UPDATE "]),
    scenario("TEST_04", "vlan_deletion", "Pourquoi un VLAN est occupé ?", "Ressources liées/non libérées et compteurs incohérents", "vlan_delete_diagnostic", ["ressources liées", "dépendances", "compteurs"], "ManageVlanBusinessImpl.deleteVlan()", ["LIVE_DB", "FR", "CODE"], ["workflow de diagnostic"], ["preuve inventée", "hallucination"]),
    scenario("TEST_05", "error_1300", "Erreur 1300", "Noeud IP / ORRAHD / IAR / désynchronisation", "error_1300_diagnostic_flow", ["Noeud IP", "ORRAHD", "IAR", "synchronisation"], "", ["LIVE_LOG", "LIVE_DB", "FR"], ["1300"], ["SQL inventé"]),
    scenario("TEST_06", "error_1201", "1201 : Il existe déjà un dossier avec cet IAR", "Dossier déjà existant pour IAR", "error_1201_diagnostic_flow", ["IAR", "dossier existant"], "", ["LIVE_DB", "FR"], ["1201", "IAR"], ["DELETE "]),
    scenario("TEST_07", "forensic_logs", "Montre les logs de DSTEL460 aujourd'hui", "Extraction de logs en fenêtre temporelle demandée", "forensic_logs", ["timestamps", "source log", "nb événements"], "", ["LIVE_LOG", "SSH"], ["AUCUNE PREUVE DISPONIBLE"], ["date inventée", "événement inventé", "client inventé"]),
    scenario("TEST_08", "forensic_logs", "Depuis quel fichier log proviennent ces informations ?", "Demande de provenance logs", "forensic_provenance", ["nom fichier", "serveur", "date", "source"], "", ["LIVE_LOG", "SSH", "Provenance"], ["fichier", "serveur"], ["réponse générique"]),
    scenario("TEST_09", "followup_reasoning", "Montre les exceptions détectées", "Lister uniquement exceptions réellement observées", "forensic_exceptions", ["exceptions réellement présentes"], "", ["LIVE_LOG", "CODE"], ["Aucune exception disponible"], ["exception inventée"]),
    scenario("TEST_10", "guide_me", "Guide moi", "Mode guidage N3 sans diagnostic prématuré", "guided_n3_questioning", ["symptôme", "code erreur", "équipement", "ND"], "", ["Conversation"], ["symptôme", "code erreur", "équipement", "ND"], ["diagnostic certain", "cause racine certaine"]),
    scenario("TEST_11", "code_lookup", "Quelle table est utilisée lors de la suppression d'un DSLAM ?", "Réponse uniquement basée sur code/SQL indexé", "code_table_lookup", ["table indexée"], "ManageDslamBusinessImpl.deleteDslam()", ["CODE", "LIVE_DB"], ["information indisponible"], ["table inventée"]),
    scenario("TEST_12", "workflow_analysis", "Quel workflow est exécuté lors de la création VLAN ?", "Reconstruction du workflow réel create_vlan", "create_vlan", ["services appelés", "validations", "ordre réel"], "ManageCreationVlanBusinessImpl.creerVlan()", ["CODE", "FR"], ["workflow métier"], ["étape inventée"]),
    scenario("TEST_13", "root_cause_analysis", "Pourquoi DSTEL460 n'a plus de VLAN disponible ?", "Capacité/compteurs/ressources occupées", "vlan_capacity_diagnostic", ["capacité", "compteurs", "ressources occupées", "FR associé"], "", ["LIVE_DB", "FR"], ["FR"], ["preuve inventée"]),
    scenario("TEST_14", "forensic_timeline", "Montre moi la chronologie complète de l'incident", "Timeline fusionnée logs/DB/SSH/FR", "forensic_timeline", ["logs", "DB", "SSH", "FR", "ordre chronologique"], "", ["LIVE_LOG", "LIVE_DB", "SSH", "FR"], ["chronologie"], ["ordre inventé"]),
    scenario("TEST_15", "incident_history", "Résume cet incident pour le dépositaire", "Résumé non technique et compréhensible", "ticket_summary_non_technical", ["message simple", "sans jargon"], "", ["Conversation"], ["non technique"], ["jargon BRASIL"]),
    scenario("TEST_16", "incident_history", "Résume cet incident pour les archives N3", "Résumé technique structuré N3", "n3_archive_summary", ["Cause", "Diagnostic", "Action", "Résultat", "Preuves"], "", ["LIVE_DB", "LIVE_LOG", "CODE", "FR"], ["Cause", "Diagnostic", "Action", "Résultat", "Preuves"], ["résumé vague"]),
    scenario("TEST_17", "jira_analysis", "Quels tickets Jira similaires existent ?", "Recherche similaire Jira dépendante du retour backend", "jira_similarity_search", ["tickets similaires"], "", ["INCIDENT", "JIRA"], ["Aucun ticket similaire trouvé"], ["ticket inventé"]),
    scenario("TEST_18", "root_cause_analysis", "Pourquoi cette suppression est bloquée ?", "Explication WHY/WHICH/WHERE/WHAT NEXT", "deletion_blocking_analysis", ["WHY", "WHICH", "WHERE", "WHAT NEXT"], "ManageDslamBusinessImpl.deleteDslam()", ["LIVE_DB", "CODE", "FR"], ["WHY", "WHICH", "WHERE", "WHAT NEXT"], ["réponse générique"]),
    scenario("TEST_19", "code_lookup", "Quelle fonction gère la création d'équipement ?", "Lookup code pur", "code_lookup_only", ["fonction", "classe", "fichier"], "", ["CODE"], ["Code intelligence"], ["procédure métier"]),
    scenario("TEST_20", "followup_reasoning", "Explique moi cette erreur comme à un collaborateur", "Vulgarisation alignée sur même cause racine", "followup_reasoning", ["vulgarisation", "même cause racine"], "", ["Conversation", "LIVE_LOG", "LIVE_DB"], ["version vulgarisée"], ["information inventée"]),
]

AUDIT_INVENTORY = {
    "demo_mode": {
        "status": "available",
        "module": "backend/app/services/chatbot/forensic_formatter.py",
        "behavior": "prioritizes strongest evidence display without faking data",
    },
    "intents": {
        "source": "backend/app/services/chatbot/intent_resolver.py",
        "forensic": [
            "forensic_logs", "forensic_timeline", "forensic_evidence", "forensic_exceptions",
            "forensic_db_state", "forensic_workflow", "forensic_root_cause", "forensic_rollback",
            "forensic_constraint_chain", "find_code_function"
        ]
    },
    "handlers": {
        "forensic_followup": "backend/app/services/chatbot/forensic_followup.py",
        "workflow_engine": "backend/app/services/chatbot/workflow_intelligence.py",
        "code_intelligence": [
            "backend/app/services/code_intelligence/operation_graph.py",
            "backend/app/services/code_intelligence/function_knowledge_index.py",
            "backend/app/services/code_intelligence/extractors/execution_graph_extractor.py",
        ],
        "provenance": [
            "backend/app/services/chatbot/provenance_engine.py",
            "backend/app/services/live_diagnostics/evidence_provenance.py",
        ],
    },
}


def build_expected_answers(scenarios: List[Dict[str, Any]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for sc in scenarios:
        out[sc["id"]] = {
            "question": sc["question"],
            "contract": sc["expected_response_contract"],
            "expected": {
                "root_cause": sc["expected_root_cause"],
                "workflow": sc["expected_workflow"],
                "evidence": sc["expected_evidence"],
                "code_reference": sc["expected_code_reference"],
                "sources": sc["expected_sources"],
            },
        }
    return out


def build_test_matrix_md(scenarios: List[Dict[str, Any]]) -> str:
    lines: List[str] = [
        "# Forensix AI DEMO Test Matrix",
        "",
        "## Scope",
        "- Total scenarios: **20**",
        "- Tier: **GOLDEN v1**",
        "- Mandatory response contract sections: Diagnostic, Evidence, Workflow, Source Code, Action, Provenance",
        "",
        "## Audit Inventory",
        f"- DEMO_MODE: `{AUDIT_INVENTORY['demo_mode']['status']}` in `{AUDIT_INVENTORY['demo_mode']['module']}`",
        "- Forensic follow-up handler: `backend/app/services/chatbot/forensic_followup.py`",
        "- Workflow handler: `backend/app/services/chatbot/workflow_intelligence.py`",
        "- Provenance engines: `provenance_engine.py` + `evidence_provenance.py`",
        "",
        "## Scenario Matrix",
        "",
        "| ID | Category | Question | Key expected code ref |",
        "|---|---|---|---|",
    ]
    for sc in scenarios:
        code_ref = sc["expected_code_reference"] or "-"
        q = sc["question"].replace("|", "\\|")
        lines.append(f"| {sc['id']} | {sc['category']} | {q} | {code_ref} |")

    lines.extend([
        "",
        "## Failure Taxonomy (Phase 2)",
        "- ROUTING_ERROR",
        "- INTENT_ERROR",
        "- WORKFLOW_ERROR",
        "- FORENSIC_ERROR",
        "- PROVENANCE_ERROR",
        "- MISSING_EVIDENCE",
        "- MISSING_CODE_REFERENCE",
        "- GENERIC_RESPONSE",
        "- HALLUCINATION",
        "- SQL_MUTATION",
        "- UNKNOWN_TABLE",
        "- UNKNOWN_FUNCTION",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    BASE.mkdir(parents=True, exist_ok=True)
    SCENARIOS_DIR.mkdir(parents=True, exist_ok=True)

    scenarios_path = BASE / "scenarios.json"
    expected_path = BASE / "expected_answers.json"
    matrix_path = BASE / "test_matrix.md"

    scenarios_path.write_text(json.dumps(SCENARIOS, ensure_ascii=False, indent=2), encoding="utf-8")
    expected_path.write_text(json.dumps(build_expected_answers(SCENARIOS), ensure_ascii=False, indent=2), encoding="utf-8")
    matrix_path.write_text(build_test_matrix_md(SCENARIOS), encoding="utf-8")

    for sc in SCENARIOS:
        (SCENARIOS_DIR / f"{sc['id'].lower()}.json").write_text(json.dumps(sc, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Generated: {scenarios_path}")
    print(f"Generated: {expected_path}")
    print(f"Generated: {matrix_path}")
    print(f"Generated scenario files: {len(SCENARIOS)} in {SCENARIOS_DIR}")


if __name__ == "__main__":
    main()
