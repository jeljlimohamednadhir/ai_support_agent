"""
test_operations_api.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Integration tests for the Operations API layer.
Covers:
  - Happy paths (all 5 endpoints)
  - LOW_EVIDENCE / investigation mode
  - RUNTIME_UNAVAILABLE degradation
  - VALIDATION_FAILED / invalid inputs
  - Unknown workflow type → 422
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# ──────────────────────────────────────────────────────────────────────────────
# App bootstrap
# ──────────────────────────────────────────────────────────────────────────────
from app.main import app

client = TestClient(app, raise_server_exceptions=False)

# ──────────────────────────────────────────────────────────────────────────────
# Auth helper (uses existing test user or bypasses via override)
# ──────────────────────────────────────────────────────────────────────────────

_FAKE_USER = MagicMock()
_FAKE_USER.is_active = True
_FAKE_USER.id = 1


def override_auth():
    return _FAKE_USER


app.dependency_overrides = {}


def _auth_headers() -> dict:
    """Override auth dep and return empty headers (dep override handles it)."""
    from app.api.deps import get_current_active_user
    app.dependency_overrides[get_current_active_user] = override_auth
    return {}


@pytest.fixture(autouse=True)
def patch_auth():
    from app.api.deps import get_current_active_user
    app.dependency_overrides[get_current_active_user] = override_auth
    yield
    app.dependency_overrides.clear()


# ──────────────────────────────────────────────────────────────────────────────
# Facade stub factories
# ──────────────────────────────────────────────────────────────────────────────

_CAPS_OK = {
    "ssh_available": False,
    "db_available": True,
    "logs_available": True,
    "mq_available": True,
}

_CAPS_NONE = {
    "ssh_available": False,
    "db_available": False,
    "logs_available": False,
    "mq_available": False,
}


def _diagnose_ok(**kwargs):
    return {
        "mode": "diagnostic",
        "diagnostic": "Liens actifs bloquent la suppression.",
        "root_cause": "equipment_has_active_links",
        "confidence": 0.82,
        "evidence": [
            {
                "source_type": "live_db",
                "description": "Résolution bloc",
                "confidence": 0.82,
                "reference_id": "FR-4521",
            }
        ],
        "workflow": "FR-4521",
        "limitations": [],
        "next_steps": ["Supprimer liens actifs"],
        "runtime_capabilities": _CAPS_OK,
    }


def _diagnose_low(**kwargs):
    return {
        "mode": "investigation",
        "diagnostic": "Données insuffisantes.",
        "root_cause": None,
        "confidence": 0.30,
        "evidence": [],
        "workflow": None,
        "limitations": ["Confiance insuffisante — mode investigation activé."],
        "next_steps": [],
        "runtime_capabilities": _CAPS_OK,
    }


def _investigate_ok(**kwargs):
    return {
        "mode": "diagnostic",
        "timeline": [
            {
                "timestamp": "2024-01-15T14:30:00+00:00",
                "event_type": "DELETE_ATTEMPT",
                "description": "Tentative bloquée",
                "severity": "ERROR",
                "source": "temporal_engine",
            }
        ],
        "rca_chain": [
            {
                "cause": "equipment_has_residual_data",
                "confidence": 0.78,
                "evidence": ["FK_VIOLATION"],
                "description": "Données résiduelles",
            }
        ],
        "anomalies": ["Boucle retry: DELETE_ATTEMPT x5"],
        "evidence": [
            {
                "source_type": "rca",
                "description": "equipment_has_residual_data",
                "confidence": 0.78,
                "reference_id": None,
            }
        ],
        "confidence": 0.78,
        "missing_information": [],
        "limitations": [],
        "next_steps": [],
        "runtime_capabilities": _CAPS_OK,
    }


def _workflow_ok(**kwargs):
    return {
        "workflow": "delete_equipment",
        "current_state": None,
        "expected_next_state": None,
        "invalid_transitions": [],
        "blocking_conditions": [],
        "business_rules_triggered": ["RULE_NO_ACTIVE_LINKS"],
        "recommended_actions": ["Supprimer les liens avant suppression"],
        "runtime_capabilities": _CAPS_OK,
    }


def _workflow_unknown(**kwargs):
    return {
        "error": {
            "code": "WORKFLOW_UNKNOWN",
            "message": "Workflow type 'unknown_type' non reconnu.",
            "details": [],
        }
    }


def _validate_ok(**kwargs):
    return {
        "valid": True,
        "confidence": 0.71,
        "supporting_evidence": ["RCA: equipment_has_residual_data (conf=0.71)"],
        "contradictions": [],
        "missing_evidence": [],
        "validation_mode": "deterministic",
        "runtime_capabilities": _CAPS_OK,
    }


def _validate_no_evidence(**kwargs):
    return {
        "valid": False,
        "confidence": 0.0,
        "supporting_evidence": [],
        "contradictions": [],
        "missing_evidence": ["Aucune preuve disponible pour confirmer l'hypothèse."],
        "validation_mode": "deterministic",
        "runtime_capabilities": _CAPS_OK,
    }


def _search_ok(**kwargs):
    return {
        "results": [
            {
                "source_type": "kb",
                "title": "FR-4521",
                "relevance": 0.91,
                "summary": "Suppression équipement N3...",
                "reference_id": "FR-4521",
            }
        ],
        "total": 1,
        "runtime_capabilities": _CAPS_OK,
    }


def _search_empty(**kwargs):
    return {
        "results": [],
        "total": 0,
        "runtime_capabilities": _CAPS_NONE,
    }


# ──────────────────────────────────────────────────────────────────────────────
# /diagnose
# ──────────────────────────────────────────────────────────────────────────────

class TestDiagnose:
    def test_happy_path(self):
        with patch("app.services.api_facade.run_diagnose", side_effect=_diagnose_ok):
            r = client.post(
                "/api/v1/operations/diagnose",
                json={"question": "Le ND N3-EQUIP-001 ne peut pas être supprimé"},
            )
        assert r.status_code == 200
        body = r.json()
        assert body["mode"] == "diagnostic"
        assert body["confidence"] == 0.82
        assert body["root_cause"] == "equipment_has_active_links"
        assert body["runtime_capabilities"]["db_available"] is True
        assert "Supprimer liens actifs" in body["next_steps"]

    def test_low_evidence_investigation_mode(self):
        with patch("app.services.api_facade.run_diagnose", side_effect=_diagnose_low):
            r = client.post(
                "/api/v1/operations/diagnose",
                json={"question": "Problème inconnu"},
            )
        assert r.status_code == 200
        body = r.json()
        assert body["mode"] == "investigation"
        assert body["confidence"] < 0.55
        assert body["root_cause"] is None
        assert any("investigation" in lim for lim in body["limitations"])

    def test_missing_question_returns_422(self):
        r = client.post("/api/v1/operations/diagnose", json={})
        assert r.status_code == 422

    def test_runtime_unavailable_surfaces_in_caps(self):
        def _no_caps(**kwargs):
            return {**_diagnose_ok(), "runtime_capabilities": _CAPS_NONE}

        with patch("app.services.api_facade.run_diagnose", side_effect=_no_caps):
            r = client.post(
                "/api/v1/operations/diagnose",
                json={"question": "test"},
            )
        assert r.status_code == 200
        caps = r.json()["runtime_capabilities"]
        assert caps["db_available"] is False
        assert caps["logs_available"] is False


# ──────────────────────────────────────────────────────────────────────────────
# /investigate
# ──────────────────────────────────────────────────────────────────────────────

class TestInvestigate:
    def test_happy_path(self):
        with patch("app.services.api_facade.run_investigate", side_effect=_investigate_ok):
            r = client.post(
                "/api/v1/operations/investigate",
                json={
                    "entity_type": "equipment",
                    "entity_id": "N3-EQUIP-001",
                    "question": "Pourquoi la suppression échoue?",
                },
            )
        assert r.status_code == 200
        body = r.json()
        assert body["mode"] == "diagnostic"
        assert len(body["timeline"]) == 1
        assert body["timeline"][0]["event_type"] == "DELETE_ATTEMPT"
        assert len(body["rca_chain"]) == 1
        assert body["rca_chain"][0]["cause"] == "equipment_has_residual_data"
        assert len(body["anomalies"]) == 1

    def test_missing_fields_returns_422(self):
        r = client.post(
            "/api/v1/operations/investigate",
            json={"entity_id": "X"},
        )
        assert r.status_code == 422

    def test_low_confidence_mode(self):
        def _low(**kwargs):
            return {**_investigate_ok(), "confidence": 0.3, "mode": "investigation"}

        with patch("app.services.api_facade.run_investigate", side_effect=_low):
            r = client.post(
                "/api/v1/operations/investigate",
                json={
                    "entity_type": "equipment",
                    "entity_id": "N3-EQUIP-001",
                    "question": "?",
                },
            )
        assert r.status_code == 200
        assert r.json()["mode"] == "investigation"


# ──────────────────────────────────────────────────────────────────────────────
# /workflow
# ──────────────────────────────────────────────────────────────────────────────

class TestWorkflow:
    def test_happy_path(self):
        with patch("app.services.api_facade.run_workflow", side_effect=_workflow_ok):
            r = client.post(
                "/api/v1/operations/workflow",
                json={"workflow_type": "equipment_delete", "entity_id": "N3-EQUIP-001"},
            )
        assert r.status_code == 200
        body = r.json()
        assert body["workflow"] == "delete_equipment"
        assert "RULE_NO_ACTIVE_LINKS" in body["business_rules_triggered"]

    def test_unknown_workflow_returns_422(self):
        with patch(
            "app.services.api_facade.run_workflow", side_effect=_workflow_unknown
        ):
            r = client.post(
                "/api/v1/operations/workflow",
                json={"workflow_type": "unknown_type", "entity_id": "X"},
            )
        assert r.status_code == 422
        detail = r.json()["detail"]
        assert detail["code"] == "WORKFLOW_UNKNOWN"

    def test_missing_entity_id_returns_422(self):
        r = client.post(
            "/api/v1/operations/workflow",
            json={"workflow_type": "equipment_delete"},
        )
        assert r.status_code == 422


# ──────────────────────────────────────────────────────────────────────────────
# /validate
# ──────────────────────────────────────────────────────────────────────────────

class TestValidate:
    def test_happy_path_valid(self):
        with patch("app.services.api_facade.run_validate", side_effect=_validate_ok):
            r = client.post(
                "/api/v1/operations/validate",
                json={
                    "hypothesis": "L'équipement a des données résiduelles MQ",
                    "context": {"nd": "N3-EQUIP-001"},
                },
            )
        assert r.status_code == 200
        body = r.json()
        assert body["valid"] is True
        assert body["confidence"] == 0.71
        assert len(body["supporting_evidence"]) >= 1

    def test_no_evidence_valid_false(self):
        with patch(
            "app.services.api_facade.run_validate", side_effect=_validate_no_evidence
        ):
            r = client.post(
                "/api/v1/operations/validate",
                json={"hypothesis": "Hypothèse sans preuves"},
            )
        assert r.status_code == 200
        body = r.json()
        assert body["valid"] is False
        assert body["confidence"] == 0.0
        assert len(body["missing_evidence"]) > 0

    def test_missing_hypothesis_returns_422(self):
        r = client.post("/api/v1/operations/validate", json={})
        assert r.status_code == 422


# ──────────────────────────────────────────────────────────────────────────────
# /search
# ──────────────────────────────────────────────────────────────────────────────

class TestSearch:
    def test_happy_path(self):
        with patch("app.services.api_facade.run_search", side_effect=_search_ok):
            r = client.post(
                "/api/v1/operations/search",
                json={"query": "suppression équipement liens actifs"},
            )
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert body["results"][0]["source_type"] == "kb"
        assert body["results"][0]["relevance"] == 0.91
        assert body["results"][0]["reference_id"] == "FR-4521"

    def test_empty_results_runtime_none(self):
        with patch("app.services.api_facade.run_search", side_effect=_search_empty):
            r = client.post(
                "/api/v1/operations/search",
                json={"query": "xyz inconnu"},
            )
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 0
        assert body["results"] == []
        assert body["runtime_capabilities"]["db_available"] is False

    def test_top_k_clamp(self):
        """top_k outside 1-20 should be rejected."""
        r = client.post(
            "/api/v1/operations/search",
            json={"query": "test", "top_k": 999},
        )
        assert r.status_code == 422

    def test_missing_query_returns_422(self):
        r = client.post("/api/v1/operations/search", json={})
        assert r.status_code == 422
