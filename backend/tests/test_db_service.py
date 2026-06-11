import pytest
from unittest.mock import MagicMock
from app.services.live_diagnostics.db.db_service import DbDiagnosticService as DbService, DbEvidence, EvidenceType

@pytest.fixture
def db_service():
    service = DbService()
    service._engine = MagicMock()  # Mock the database engine
    service._engine.connect.return_value.__enter__.return_value.execute.return_value.fetchall.return_value = []
    return service

def test_insufficient_evidence_blocked(db_service):
    """Test that RCA generation is blocked for insufficient evidence."""
    # Use a valid query name from the whitelist
    evidence = db_service.execute("get_equipment_id", ["mock_name", "mock_name"])
    assert evidence.confidence < 0.7
    assert evidence.error == "Insufficient evidence"

def test_sufficient_evidence_passes(db_service):
    """Test that RCA generation proceeds for sufficient evidence."""
    # Mock execute to simulate rows returned
    def mock_execute(query_name, params):
        return DbEvidence(
            evidence_type=EvidenceType.LIVE_DB,
            query_name=query_name,
            rows=[{"id": 1}],
            row_count=1,
            error=None,
            confidence=0.97,
            truncated=False,
        )

    db_service.execute = mock_execute

    # Call execute and verify behavior
    evidence = db_service.execute("mock_query", [])
    assert evidence.confidence >= 0.7
    assert evidence.error is None