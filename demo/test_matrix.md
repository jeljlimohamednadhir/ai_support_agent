# Forensix AI DEMO Test Matrix

## Scope
- Total scenarios: **20**
- Tier: **GOLDEN v1**
- Mandatory response contract sections: Diagnostic, Evidence, Workflow, Source Code, Action, Provenance

## Audit Inventory
- DEMO_MODE: `available` in `backend/app/services/chatbot/forensic_formatter.py`
- Forensic follow-up handler: `backend/app/services/chatbot/forensic_followup.py`
- Workflow handler: `backend/app/services/chatbot/workflow_intelligence.py`
- Provenance engines: `provenance_engine.py` + `evidence_provenance.py`

## Scenario Matrix

| ID | Category | Question | Key expected code ref |
|---|---|---|---|
| TEST_01 | equipment_deletion | Suppression équipement DSROB362 impossible | ManageDslamBusinessImpl.deleteDslam() |
| TEST_02 | code_lookup | Quelle est la méthode Java qui supprime un DSLAM ? | ManageDslamBusinessImpl.deleteDslam() |
| TEST_03 | vlan_creation | Comment créer un VLAN ? | ManageCreationVlanBusinessImpl.creerVlan() |
| TEST_04 | vlan_deletion | Pourquoi un VLAN est occupé ? | ManageVlanBusinessImpl.deleteVlan() |
| TEST_05 | error_1300 | Erreur 1300 | - |
| TEST_06 | error_1201 | 1201 : Il existe déjà un dossier avec cet IAR | - |
| TEST_07 | forensic_logs | Montre les logs de DSTEL460 aujourd'hui | - |
| TEST_08 | forensic_logs | Depuis quel fichier log proviennent ces informations ? | - |
| TEST_09 | followup_reasoning | Montre les exceptions détectées | - |
| TEST_10 | guide_me | Guide moi | - |
| TEST_11 | code_lookup | Quelle table est utilisée lors de la suppression d'un DSLAM ? | ManageDslamBusinessImpl.deleteDslam() |
| TEST_12 | workflow_analysis | Quel workflow est exécuté lors de la création VLAN ? | ManageCreationVlanBusinessImpl.creerVlan() |
| TEST_13 | root_cause_analysis | Pourquoi DSTEL460 n'a plus de VLAN disponible ? | - |
| TEST_14 | forensic_timeline | Montre moi la chronologie complète de l'incident | - |
| TEST_15 | incident_history | Résume cet incident pour le dépositaire | - |
| TEST_16 | incident_history | Résume cet incident pour les archives N3 | - |
| TEST_17 | jira_analysis | Quels tickets Jira similaires existent ? | - |
| TEST_18 | root_cause_analysis | Pourquoi cette suppression est bloquée ? | ManageDslamBusinessImpl.deleteDslam() |
| TEST_19 | code_lookup | Quelle fonction gère la création d'équipement ? | - |
| TEST_20 | followup_reasoning | Explique moi cette erreur comme à un collaborateur | - |

## Failure Taxonomy (Phase 2)
- ROUTING_ERROR
- INTENT_ERROR
- WORKFLOW_ERROR
- FORENSIC_ERROR
- PROVENANCE_ERROR
- MISSING_EVIDENCE
- MISSING_CODE_REFERENCE
- GENERIC_RESPONSE
- HALLUCINATION
- SQL_MUTATION
- UNKNOWN_TABLE
- UNKNOWN_FUNCTION
