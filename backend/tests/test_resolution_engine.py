import pytest
from unittest.mock import MagicMock
from app.services.live_diagnostics.resolution_engine import ResolutionEngine, ResolutionCandidate
from datetime import datetime, timedelta

@pytest.fixture
def resolution_engine():
    engine = ResolutionEngine()
    return engine

def test_fallback_added_with_valid_relevance(resolution_engine):
    """Test that fallback root cause is added when it passes relevance validation."""
    bundle = MagicMock()  # Mock the incident bundle
    bundle.intent = "delete_equipment"
    bundle.db_evidence = {}
    bundle.log_evidence = []
    bundle.ssh_evidence = []
    resolution_engine._validate_causal_relevance = MagicMock(return_value=True)

    # Call resolve
    candidates = resolution_engine.resolve(bundle)

    # Verify fallback was added
    assert len(candidates) == 1
    assert candidates[0].root_cause == "equipment_has_residual_data"
    assert candidates[0].confidence >= 0.5

def test_fallback_not_added_with_low_confidence(resolution_engine):
    """Test that fallback root cause is not added when confidence is too low."""
    bundle = MagicMock()
    bundle.intent = "delete_equipment"
    bundle.db_evidence = {}
    bundle.log_evidence = []
    bundle.ssh_evidence = []

    # Mock validate_causal_relevance to return False
    resolution_engine._validate_causal_relevance = MagicMock(return_value=False)

    # Call resolve
    candidates = resolution_engine.resolve(bundle)

    # Verify fallback was not added
    assert len(candidates) == 0

def test_deduplication_logic(resolution_engine):
    """Test that deduplication keeps only the highest-confidence candidate."""
    candidates = [
        ResolutionCandidate(root_cause="cause1", confidence=0.8, sources=["source1"], fr_id=None, steps=[], sql_hints=[], tags=[]),
        ResolutionCandidate(root_cause="cause1", confidence=0.9, sources=["source2"], fr_id=None, steps=[], sql_hints=[], tags=[]),
        ResolutionCandidate(root_cause="cause2", confidence=0.7, sources=["source3"], fr_id=None, steps=[], sql_hints=[], tags=[]),
    ]

    deduplicated = resolution_engine._deduplicate(candidates)

    # Verify deduplication results
    assert len(deduplicated) == 2
    assert any(c.root_cause == "cause1" and c.confidence == 0.9 for c in deduplicated)
    assert any(c.root_cause == "cause2" and c.confidence == 0.7 for c in deduplicated)

def test_ranking_logic(resolution_engine):
    """Test that candidates are ranked deterministically by confidence and source."""
    candidates = [
        ResolutionCandidate(root_cause="cause1", confidence=0.8, sources=["sourceB"], fr_id=None, steps=[], sql_hints=[], tags=[]),
        ResolutionCandidate(root_cause="cause2", confidence=0.8, sources=["sourceA"], fr_id=None, steps=[], sql_hints=[], tags=[]),
        ResolutionCandidate(root_cause="cause3", confidence=0.9, sources=["sourceC"], fr_id=None, steps=[], sql_hints=[], tags=[]),
    ]

    candidates = resolution_engine._deduplicate(candidates)
    candidates.sort(key=lambda x: (x.confidence, x.sources[0] if x.sources else ""), reverse=True)

    # Verify ranking
    assert candidates[0].root_cause == "cause3"
    assert candidates[1].root_cause == "cause1"
    assert candidates[2].root_cause == "cause2"

def test_validate_causal_relevance_with_valid_evidence(resolution_engine):
    """Test that causal relevance validation passes with valid evidence."""
    bundle = MagicMock()
    bundle.db_evidence = {
        "mock_root_cause": {"timestamp": datetime.now()}
    }
    bundle.log_evidence = {}

    result = resolution_engine._validate_causal_relevance(bundle, "mock_root_cause")
    assert result is True

def test_validate_causal_relevance_with_stale_evidence(resolution_engine):
    """Test that causal relevance validation fails with stale evidence."""
    bundle = MagicMock()
    bundle.db_evidence = {
        "mock_root_cause": {"timestamp": datetime.now() - timedelta(hours=2)}
    }
    bundle.log_evidence = {}

    result = resolution_engine._validate_causal_relevance(bundle, "mock_root_cause")
    assert result is False

def test_validate_causal_relevance_with_missing_timestamp(resolution_engine):
    """Test that causal relevance validation fails when timestamp is missing."""
    bundle = MagicMock()
    bundle.db_evidence = {
        "mock_root_cause": {}
    }
    bundle.log_evidence = {}

    result = resolution_engine._validate_causal_relevance(bundle, "mock_root_cause")
    assert result is False

def test_validate_causal_relevance_with_no_evidence(resolution_engine):
    """Test that causal relevance validation fails when no evidence is found."""
    bundle = MagicMock()
    bundle.db_evidence = {}
    bundle.log_evidence = {}

    result = resolution_engine._validate_causal_relevance(bundle, "mock_root_cause")
    assert result is False


def test_to_context_blocks_filters_unsupported_runtime_actions(resolution_engine):
    candidate = ResolutionCandidate(
        root_cause="ihm_blocked_dsm_param",
        confidence=0.95,
        sources=["ssh"],
        fr_id="FR-IHM-BLOQUEE-DSM-PARAM-182",
        steps=[
            "Se connecter sur le serveur DSM PARAM via SSH",
            "Consulter les logs Tomcat pour confirmer le blocage",
            "Exécuter une requête SQL de contrôle",
        ],
        sql_hints=["SELECT * FROM t_services WHERE eqpt_id = <eqpt_id>;"],
        tags=["fix_ihm_blocked"],
    )

    blocks = resolution_engine.to_context_blocks(
        [candidate],
        eqpt_id="1234",
        runtime_capabilities={
            "ssh_available": False,
            "logs_available": False,
            "db_available": False,
            "mq_available": True,
        },
    )

    assert len(blocks) == 1
    content = blocks[0]["content"]
    assert "serveur dsm param" not in content.lower()
    assert "logs tomcat" not in content.lower()
    assert "requête sql" not in content.lower()
    assert blocks[0]["sql_hints_raw"] == []
    assert blocks[0]["sql_resolved"] is False


def test_to_context_blocks_keeps_sql_hints_when_db_available(resolution_engine):
    candidate = ResolutionCandidate(
        root_cause="equipment_has_residual_data",
        confidence=0.97,
        sources=["live_db"],
        fr_id="FR-DSLAM-DELETION-189",
        steps=["Identifier les tables avec des données résiduelles via SQL"],
        sql_hints=["SELECT * FROM t_services WHERE eqpt_id = <eqpt_id>;"],
        tags=["delete_equipment"],
    )

    blocks = resolution_engine.to_context_blocks(
        [candidate],
        eqpt_id="5050111",
        runtime_capabilities={"db_available": True},
    )

    assert len(blocks) == 1
    assert "SELECT * FROM t_services WHERE eqpt_id = 5050111;" in blocks[0]["content"]
    assert blocks[0]["sql_hints_raw"] == ["SELECT * FROM t_services WHERE eqpt_id = 5050111;"]
    assert blocks[0]["sql_resolved"] is True


def test_to_context_blocks_removes_generic_non_evidence_steps(resolution_engine):
    candidate = ResolutionCandidate(
        root_cause="delete_blocked",
        confidence=0.9,
        sources=["intent_fallback"],
        fr_id="FR-TEST-001",
        steps=[
            "Vérifier les logs",
            "Identifier la cause du problème",
        ],
        sql_hints=[],
        tags=[],
    )

    blocks = resolution_engine.to_context_blocks(
        [candidate],
        runtime_capabilities={
            "ssh_available": True,
            "logs_available": True,
            "db_available": True,
            "mq_available": True,
        },
    )

    assert len(blocks) == 1
    content = blocks[0]["content"].lower()
    assert "vérifier les logs" not in content
    assert "identifier la cause" not in content
    assert "actions opérationnelles limitées" in content