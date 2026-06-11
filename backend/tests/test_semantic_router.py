"""
tests/test_semantic_router.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Unit tests for the SemanticIntentRouter.

Tests:
  - French telecom queries route to correct categories
  - Source code queries → source_code_lookup
  - Log queries → forensic_logs
  - Exception queries → exception_lookup
  - Workflow queries → workflow_navigation
  - Provenance queries → evidence_provenance
  - Multi-label detection
  - Unknown queries gracefully return runtime_diagnostic
  - forensic_intent mappings are correct
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from app.services.chatbot.semantic_intent_router import (
    SemanticIntentRouter,
    semantic_router,
    CAT_SOURCE_CODE_LOOKUP,
    CAT_FORENSIC_LOGS,
    CAT_FORENSIC_TIMELINE,
    CAT_EXCEPTION_LOOKUP,
    CAT_WORKFLOW_NAVIGATION,
    CAT_EVIDENCE_PROVENANCE,
    CAT_FUNCTION_TRACE,
    CAT_SCHEMA_LOOKUP,
    CAT_ROLLBACK_ANALYSIS,
    CAT_VALIDATION_CONSTRAINT,
    CAT_RUNTIME_DIAGNOSTIC,
)


@pytest.fixture
def router():
    return SemanticIntentRouter()


class TestSourceCodeLookup:

    def test_delete_function_query(self, router):
        result = router.route("quelle est la fonction qui permet de supprimer un equipement ?")
        assert result.primary == CAT_SOURCE_CODE_LOOKUP
        assert result.confidence >= 0.8

    def test_create_vlan_service_query(self, router):
        result = router.route("quel service effectue la creation de VLAN ?")
        assert result.primary == CAT_SOURCE_CODE_LOOKUP
        assert result.confidence >= 0.8

    def test_java_method_query(self, router):
        result = router.route("quelle methode Java supprime un DSLAM ?")
        assert result.primary == CAT_SOURCE_CODE_LOOKUP

    def test_java_class_query(self, router):
        result = router.route("quelle classe gere la suppression des cartes ?")
        assert result.primary == CAT_SOURCE_CODE_LOOKUP

    def test_code_source_direct(self, router):
        result = router.route("montre le code source de la suppression DSLAM")
        assert result.has_category(CAT_SOURCE_CODE_LOOKUP)

    def test_forensic_intent_is_find_code_function(self, router):
        result = router.route("quelle fonction supprime un dslam ?")
        assert result.forensic_intent == "find_code_function"


class TestFunctionTrace:

    def test_call_chain_query(self, router):
        result = router.route("quelle est la chaîne d'appel pour la suppression ?")
        assert result.has_category(CAT_FUNCTION_TRACE)

    def test_who_calls_query(self, router):
        result = router.route("qui appelle la methode deleteDslam ?")
        assert result.has_category(CAT_FUNCTION_TRACE)


class TestForensicLogs:

    def test_show_logs_query(self, router):
        result = router.route("montrer les logs pour DSFEN104")
        assert result.primary == CAT_FORENSIC_LOGS

    def test_catalina_log_query(self, router):
        result = router.route("que dit catalina.out ?")
        assert result.has_category(CAT_FORENSIC_LOGS)

    def test_forensic_intent_is_forensic_logs(self, router):
        result = router.route("affiche les logs forensiques")
        assert result.forensic_intent == "forensic_logs"


class TestForensicTimeline:

    def test_timeline_query(self, router):
        result = router.route("montre la timeline de l'incident")
        assert result.primary == CAT_FORENSIC_TIMELINE

    def test_chronology_query(self, router):
        result = router.route("quelle est la chronologie des événements ?")
        assert result.has_category(CAT_FORENSIC_TIMELINE)


class TestExceptionLookup:

    def test_show_exceptions_french(self, router):
        result = router.route("montre les exceptions detectees pour DSFEN104")
        assert result.primary == CAT_EXCEPTION_LOOKUP

    def test_what_exceptions_raised(self, router):
        result = router.route("quelles exceptions sont levées lors de la suppression ?")
        assert result.primary == CAT_EXCEPTION_LOOKUP

    def test_named_exception(self, router):
        result = router.route("BrasilTechnicalException est levée pourquoi ?")
        assert result.has_category(CAT_EXCEPTION_LOOKUP)

    def test_forensic_intent_is_exceptions(self, router):
        result = router.route("liste les exceptions java")
        assert result.forensic_intent == "forensic_exceptions"


class TestWorkflowNavigation:

    def test_how_to_create_vlan(self, router):
        result = router.route("comment créer un vlan ?")
        assert result.has_category(CAT_WORKFLOW_NAVIGATION)

    def test_how_to_delete_equipment(self, router):
        result = router.route("comment supprimer un équipement dans BRASIL ?")
        assert result.has_category(CAT_WORKFLOW_NAVIGATION)

    def test_what_steps(self, router):
        result = router.route("quelles sont les étapes pour déployer un DSLAM ?")
        assert result.has_category(CAT_WORKFLOW_NAVIGATION)


class TestEvidenceProvenance:

    def test_where_do_infos_come_from(self, router):
        result = router.route("depuis quels logs viennent ces informations ?")
        assert result.primary == CAT_EVIDENCE_PROVENANCE

    def test_what_is_source(self, router):
        result = router.route("quelle est la source de ces données ?")
        assert result.has_category(CAT_EVIDENCE_PROVENANCE)


class TestSchemaLookup:

    def test_which_tables_dslam(self, router):
        result = router.route("quelles tables contiennent les données DSLAM ?")
        assert result.has_category(CAT_SCHEMA_LOOKUP)

    def test_schema_structure(self, router):
        result = router.route("quelle est la structure de la table t_equipments ?")
        assert result.has_category(CAT_SCHEMA_LOOKUP)


class TestRollbackAnalysis:

    def test_rollback_query(self, router):
        result = router.route("pourquoi y a-t-il eu un rollback ?")
        assert result.has_category(CAT_ROLLBACK_ANALYSIS)

    def test_annulation_query(self, router):
        result = router.route("la transaction a été annulée, pourquoi ?")
        assert result.has_category(CAT_ROLLBACK_ANALYSIS)


class TestValidationConstraint:

    def test_blocking_constraint(self, router):
        result = router.route("qu'est-ce qui bloque la suppression ?")
        assert result.has_category(CAT_VALIDATION_CONSTRAINT)

    def test_prerequisite_query(self, router):
        result = router.route("quelles sont les conditions de blocage pour ce workflow ?")
        assert result.has_category(CAT_VALIDATION_CONSTRAINT)


class TestEdgeCases:

    def test_empty_returns_runtime_diagnostic(self, router):
        result = router.route("")
        assert result.primary == "runtime_diagnostic"

    def test_unknown_returns_gracefully(self, router):
        result = router.route("abc def 123 xyz")
        assert isinstance(result.primary, str)
        assert result.confidence >= 0.0

    def test_multi_label_for_complex_query(self, router):
        # Should hit both source_code_lookup and function_trace
        result = router.route("quelle méthode Java effectue la suppression et quelle est sa chaîne d'appel ?")
        assert result.is_multi_label

    def test_explain_returns_string(self, router):
        explanation = router.explain("quelle fonction supprime un DSLAM ?")
        assert isinstance(explanation, str)
        assert "Semantic Route" in explanation

    def test_get_forensic_intent_helper(self, router):
        intent = router.get_forensic_intent("quelle methode supprime un equipement ?")
        assert intent == "find_code_function"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
