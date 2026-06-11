from datetime import datetime, timedelta, timezone

from app.services.chatbot.temporal_reasoning import TemporalEvent, TemporalReasoningEngine
from app.services.live_diagnostics.logs.log_correlation_engine import CorrelationHypothesis, LogCorrelationEngine


def test_log_correlation_deterministic_tie_breaker_by_cause(monkeypatch):
    monkeypatch.setattr(
        "app.services.code_intelligence.CODE_INTELLIGENCE_ENABLED",
        False,
        raising=False,
    )
    engine = LogCorrelationEngine()

    hypotheses = engine.correlate(exceptions=["DslamIncoherentStateException"])

    assert len(hypotheses) >= 2
    assert hypotheses[0].confidence == hypotheses[1].confidence
    assert hypotheses[0].cause == "delete_blocked"
    assert hypotheses[1].cause == "state_incoherent"


def test_temporal_suppress_stale_handles_timezone_aware_timestamp():
    engine = TemporalReasoningEngine()
    stale_ts = datetime.now(timezone.utc) - timedelta(hours=72)
    ev = TemporalEvent(
        timestamp=stale_ts,
        event_type="constraint_violation",
        entity="EQPT1",
        description="Old error",
        source="log",
        severity="error",
    )

    out = engine._suppress_stale_events([ev])

    assert len(out) == 1
    assert "stale" in out[0].tags
    assert out[0].severity == "info"


def test_temporal_future_timestamp_not_marked_stale():
    engine = TemporalReasoningEngine()
    future_ts = datetime.now(timezone.utc) + timedelta(minutes=10)
    ev = TemporalEvent(
        timestamp=future_ts,
        event_type="mq_error",
        entity="EQPT2",
        description="Future clock skew event",
        source="log",
        severity="error",
    )

    out = engine._suppress_stale_events([ev])

    assert len(out) == 1
    assert "stale" not in out[0].tags
    assert "future_timestamp" in out[0].tags
    assert out[0].severity == "error"


def test_correlation_to_dict_removes_generic_non_evidence_actions():
    hypothesis = CorrelationHypothesis(
        cause="generic_issue",
        confidence=0.7,
        evidence=["token=unknown"],
        actions=[
            "Vérifier les logs complets pour le contexte de l'erreur",
            "Identifier la cause du blocage dans le message complet",
        ],
        fr_ids=[],
        description="",
    )

    serialized = hypothesis.to_dict()

    assert serialized["actions"] == []


def test_correlation_to_dict_keeps_concrete_evidence_backed_actions():
    hypothesis = CorrelationHypothesis(
        cause="foreign_key_violation",
        confidence=0.88,
        evidence=["ConstraintViolationException", "code=6969"],
        actions=[
            "Identifier la contrainte FK via DETAIL dans les logs psql",
            "Nettoyer les références orphelines dans t_services",
        ],
        fr_ids=["FR-CONSTRAINT-001"],
        description="",
    )

    serialized = hypothesis.to_dict()

    assert len(serialized["actions"]) == 2
    assert "contrainte fk" in serialized["actions"][0].lower()
    assert "t_services" in serialized["actions"][1]
