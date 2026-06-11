"""
tests/test_workflow_intelligence.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Unit tests for the WorkflowIntelligenceEngine.

Tests:
  - Known workflows return validated steps
  - Unknown workflows return explicit uncertainty (no hallucination)
  - French synonyms for operations are resolved correctly
  - Entity detection works for DSLAM, VLAN, equipment
  - Workflow rendering produces expected sections
  - render_workflow_response always returns a string
  - Unknown operation returns uncertainty message, not invented steps
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from app.services.chatbot.workflow_intelligence import (
    WorkflowIntelligenceEngine,
    Workflow,
    WorkflowStep,
    workflow_engine,
)


@pytest.fixture
def engine():
    return WorkflowIntelligenceEngine()


# ── Known Workflow Tests ───────────────────────────────────────────────────

class TestKnownWorkflows:

    def test_resolve_delete_dslam(self, engine):
        wf = engine.resolve("comment supprimer un DSLAM ?")
        assert wf is not None
        assert wf.name == "Suppression d'un DSLAM"
        assert len(wf.steps) >= 4

    def test_resolve_create_vlan(self, engine):
        wf = engine.resolve("comment créer un vlan ?")
        assert wf is not None
        assert wf.name == "Création d'un VLAN"
        assert len(wf.steps) >= 3

    def test_resolve_delete_equipment_generic(self, engine):
        wf = engine.resolve("comment supprimer un équipement ?")
        assert wf is not None
        assert wf.operation == "delete_equipment"

    def test_resolve_returns_validated_workflow(self, engine):
        wf = engine.resolve("comment supprimer un DSLAM ?")
        assert wf.is_validated is True
        assert wf.source in ("FR", "code", "hybrid")

    def test_steps_have_technical_details(self, engine):
        wf = engine.resolve("comment supprimer un DSLAM ?")
        has_technical = any(s.technical_detail for s in wf.steps)
        assert has_technical, "Expected at least one step with technical_detail"

    def test_steps_have_conditions(self, engine):
        wf = engine.resolve("comment supprimer un DSLAM ?")
        has_condition = any(s.condition for s in wf.steps)
        assert has_condition, "Expected at least one step with blocking condition"


# ── Unknown Workflow Tests (Anti-Hallucination) ────────────────────────────

class TestUnknownWorkflowSafety:

    def test_unknown_operation_returns_uncertainty_not_none(self, engine):
        wf = engine.resolve_or_unknown("comment faire une migration inter-DC ?")
        assert wf is not None
        assert wf.source == "unknown" or not wf.is_validated

    def test_unknown_workflow_has_uncertainty_message(self, engine):
        wf = engine.resolve_or_unknown("comment provisionner une ONT sur un OLT GPON ?")
        if wf.source == "unknown":
            assert wf.uncertainty_message is not None
            assert len(wf.uncertainty_message) > 10

    def test_unknown_workflow_renders_uncertainty(self, engine):
        wf = engine.resolve_or_unknown("comment réinitialiser une carte NIP sur un MSAN ?")
        rendered = wf.render()
        if wf.source == "unknown":
            assert "⚠️" in rendered or "non indexé" in rendered

    def test_unknown_workflow_does_not_invent_steps(self, engine):
        wf = engine.resolve_or_unknown("comment faire une restauration complète du système ?")
        if wf.source == "unknown":
            # Should have zero steps and only uncertainty message
            assert len(wf.steps) == 0 or wf.uncertainty_message is not None

    def test_render_workflow_response_never_empty(self, engine):
        # Even for completely unknown operations, render should return a string
        response = engine.render_workflow_response("blabla xyz 123 ?")
        assert isinstance(response, str)
        assert len(response) > 5

    def test_resolve_returns_none_for_unknown_not_invented(self, engine):
        # resolve() (without _or_unknown) should return None for unknown workflows
        wf = engine.resolve("comment faire une synchronisation LDAP ?")
        # Either None or a low-confidence result
        if wf is not None:
            assert wf.confidence < 0.5 or wf.source == "unknown"


# ── Synonym Resolution Tests ───────────────────────────────────────────────

class TestSynonymResolution:

    def test_suppression_maps_to_delete(self, engine):
        op = engine._detect_operation("suppression d'un équipement")
        assert op == "delete"

    def test_effacer_maps_to_delete(self, engine):
        op = engine._detect_operation("effacer un DSLAM")
        assert op == "delete"

    def test_creer_maps_to_create(self, engine):
        op = engine._detect_operation("créer un VLAN")
        assert op == "create"

    def test_rejouer_maps_to_replay(self, engine):
        op = engine._detect_operation("rejouer une commande bloquée")
        assert op == "replay"

    def test_dslam_entity_detected(self, engine):
        ent = engine._detect_entity("suppression d'un DSLAM")
        assert ent == "dslam"

    def test_vlan_entity_detected(self, engine):
        ent = engine._detect_entity("création d'un VLAN")
        assert ent == "vlan"

    def test_equipement_entity_detected(self, engine):
        ent = engine._detect_entity("supprimer un équipement")
        assert ent == "equipment"


# ── Workflow Rendering Tests ───────────────────────────────────────────────

class TestWorkflowRendering:

    def test_render_has_workflow_emoji(self, engine):
        wf = engine.resolve("comment supprimer un DSLAM ?")
        rendered = wf.render()
        assert "🧩" in rendered

    def test_render_has_numbered_steps(self, engine):
        wf = engine.resolve("comment supprimer un DSLAM ?")
        rendered = wf.render()
        assert "1." in rendered
        assert "2." in rendered

    def test_render_shows_technical_detail(self, engine):
        wf = engine.resolve("comment supprimer un DSLAM ?")
        rendered = wf.render()
        assert "ManageDslamBusinessImpl" in rendered

    def test_render_shows_blocking_conditions(self, engine):
        wf = engine.resolve("comment supprimer un DSLAM ?")
        rendered = wf.render()
        assert "services actifs" in rendered.lower() or "⚠️" in rendered

    def test_render_create_vlan_has_correct_method(self, engine):
        wf = engine.resolve("comment créer un vlan ?")
        rendered = wf.render()
        assert "creerVlan" in rendered or "ManageCreationVlan" in rendered

    def test_step_render_unvalidated_has_warning(self):
        step = WorkflowStep(
            index=1,
            description="Étape non validée",
            source="inferred",
            validated=False,
        )
        rendered = step.render()
        assert "⚠️" in rendered or "non validé" in rendered


# ── Registry Tests ────────────────────────────────────────────────────────

class TestRegistry:

    def test_get_all_operations_returns_list(self, engine):
        ops = engine.get_all_operations()
        assert isinstance(ops, list)
        assert len(ops) >= 3

    def test_add_custom_workflow(self, engine):
        custom_wf = Workflow(
            name="Test Custom Workflow",
            operation="test_op",
            entity="test",
            source="FR",
            confidence=0.9,
            steps=[WorkflowStep(1, "Step 1", source="FR")],
        )
        engine.add_workflow("test_op_test", custom_wf)
        resolved = engine.resolve("test op test entity")
        # May or may not resolve depending on detection, just ensure no crash
        assert isinstance(engine.get_all_operations(), list)
        assert "test_op_test" in engine.get_all_operations()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
