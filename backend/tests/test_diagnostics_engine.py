"""
Tests pour DiagnosticsEngine
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.orm import Session

from app.services.analyzer.diagnostics_engine import DiagnosticsEngine
from app.models.database import DiagnosticReport, SimilarIssue
from app.schemas.diagnostics import DiagnosticRequest


@pytest.fixture
def mock_db():
    """Mock de la session database"""
    return Mock(spec=Session)


@pytest.fixture
def diagnostics_engine(mock_db):
    """Instance de DiagnosticsEngine avec dépendances mockées"""
    engine = DiagnosticsEngine(mock_db)
    engine.llm_client = AsyncMock()
    engine.graph_service = AsyncMock()
    engine.vector_service = AsyncMock()
    return engine


class TestDiagnose:
    """Tests pour la fonction diagnose"""
    
    @pytest.mark.asyncio
    async def test_diagnose_creates_report(self, diagnostics_engine, mock_db):
        """Doit créer rapport de diagnostic complet"""
        # Arrange
        request = DiagnosticRequest(
            issue_description="Application crashes on startup",
            affected_component="backend-api",
            error_logs=["Error: Connection refused"],
            context={"requester_id": "user123"}
        )
        
        diagnostics_engine.vector_service.search_similar = AsyncMock(return_value=[
            {
                "payload": {"file_path": "app/main.py", "content": "def start()..."},
                "score": 0.9
            }
        ])
        
        diagnostics_engine.llm_client.chat = AsyncMock(
            return_value='{"root_cause": "Database connection timeout", "severity": "high", "confidence": 0.85, "explanation": "Connection pool exhausted"}'
        )
        
        mock_db.add = Mock()
        mock_db.commit = Mock()
        
        with patch.object(diagnostics_engine, 'find_similar_issues', new_callable=AsyncMock, return_value=[]):
            # Act
            result = await diagnostics_engine.diagnose(request)
        
        # Assert
        assert "diagnostic_id" in result
        assert result["root_cause"] == "Database connection timeout"
        assert result["severity"] == "high"
        assert result["confidence"] == 0.85
        assert len(result["related_code"]) > 0
        assert mock_db.add.called
        assert mock_db.commit.called
    
    @pytest.mark.asyncio
    async def test_diagnose_with_similar_issues(self, diagnostics_engine, mock_db):
        """Doit inclure issues similaires dans l'analyse"""
        # Arrange
        request = DiagnosticRequest(
            issue_description="Memory leak detected",
            affected_component="worker"
        )
        
        similar_issues = [
            {
                "id": "issue-1",
                "description": "Memory leak in worker",
                "resolution": "Fixed by clearing cache",
                "score": 0.92,
                "source": "history"
            }
        ]
        
        diagnostics_engine.vector_service.search_similar = AsyncMock(return_value=[])
        diagnostics_engine.llm_client.chat = AsyncMock(
            return_value='{"root_cause": "Cache not cleared", "severity": "medium", "confidence": 0.75, "explanation": "Similar to previous issue"}'
        )
        
        mock_db.add = Mock()
        mock_db.commit = Mock()
        
        with patch.object(
            diagnostics_engine,
            'find_similar_issues',
            new_callable=AsyncMock,
            return_value=similar_issues
        ):
            # Act
            result = await diagnostics_engine.diagnose(request)
        
        # Assert
        assert len(result["similar_issues"]) > 0
        assert result["similar_issues"][0]["id"] == "issue-1"


class TestFindSimilarIssues:
    """Tests pour find_similar_issues"""
    
    @pytest.mark.asyncio
    async def test_finds_similar_from_vector_store(self, diagnostics_engine, mock_db):
        """Doit rechercher dans Qdrant"""
        # Arrange
        diagnostics_engine.vector_service.search_similar = AsyncMock(return_value=[
            {
                "id": "vec-1",
                "payload": {
                    "description": "Similar issue",
                    "resolution": "Fixed"
                },
                "score": 0.88
            }
        ])
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        
        mock_db.query.return_value = mock_query
        
        with patch.object(
            diagnostics_engine,
            '_search_jira_issues',
            new_callable=AsyncMock,
            return_value=[]
        ):
            # Act
            result = await diagnostics_engine.find_similar_issues("Test issue", limit=5)
        
        # Assert
        assert len(result) > 0
        assert result[0]["source"] == "history"
        assert result[0]["score"] == 0.88
    
    @pytest.mark.asyncio
    async def test_finds_similar_from_postgres(self, diagnostics_engine, mock_db):
        """Doit rechercher dans PostgreSQL"""
        # Arrange
        mock_reports = [
            Mock(
                id="diag-1",
                issue_description="Application timeout",
                root_cause="Database slow",
                resolution_notes="Optimized queries",
                resolved_at=datetime.utcnow()
            )
        ]
        
        diagnostics_engine.vector_service.search_similar = AsyncMock(return_value=[])
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_reports
        
        mock_db.query.return_value = mock_query
        
        with patch.object(
            diagnostics_engine,
            '_search_jira_issues',
            new_callable=AsyncMock,
            return_value=[]
        ):
            # Act
            result = await diagnostics_engine.find_similar_issues("Application timeout", limit=5)
        
        # Assert
        # Note: Similarité dépend de _calculate_text_similarity
        # Avec "Application timeout" vs "Application timeout", devrait être > 0.6
        matching = [r for r in result if r["source"] == "diagnostics"]
        assert len(matching) > 0


class TestSuggestFixes:
    """Tests pour suggest_fixes"""
    
    @pytest.mark.asyncio
    async def test_returns_existing_fixes(self, diagnostics_engine, mock_db):
        """Doit retourner fixes existants si disponibles"""
        # Arrange
        mock_report = Mock(
            id="diag-123",
            suggested_fixes=[
                {"type": "quick_fix", "description": "Restart service"}
            ],
            analysis={}
        )
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_report
        
        mock_db.query.return_value = mock_query
        
        # Act
        fixes = await diagnostics_engine.suggest_fixes("diag-123")
        
        # Assert
        assert len(fixes) == 1
        assert fixes[0]["type"] == "quick_fix"
    
    @pytest.mark.asyncio
    async def test_generates_new_fixes(self, diagnostics_engine, mock_db):
        """Doit générer nouveaux fixes si absents"""
        # Arrange
        mock_report = Mock(
            id="diag-123",
            suggested_fixes=None,
            analysis={"root_cause": "Memory leak"},
            issue_description="Memory issue",
            affected_component="worker",
            error_logs=[],
            root_cause="Memory leak"
        )
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_report
        
        mock_db.query.return_value = mock_query
        mock_db.commit = Mock()
        
        diagnostics_engine.llm_client.chat = AsyncMock(
            return_value='[{"type": "proper_fix", "description": "Implement cleanup", "steps": ["Add cleanup"], "estimated_time": "2 hours"}]'
        )
        
        # Act
        fixes = await diagnostics_engine.suggest_fixes("diag-123")
        
        # Assert
        assert len(fixes) > 0
        assert mock_report.suggested_fixes is not None
        assert mock_db.commit.called
    
    @pytest.mark.asyncio
    async def test_raises_error_for_missing_diagnostic(self, diagnostics_engine, mock_db):
        """Doit lever erreur si diagnostic inexistant"""
        # Arrange
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        
        mock_db.query.return_value = mock_query
        
        # Act & Assert
        with pytest.raises(ValueError, match="Diagnostic .* not found"):
            await diagnostics_engine.suggest_fixes("nonexistent")


class TestGetDiagnosticPatterns:
    """Tests pour get_diagnostic_patterns"""
    
    @pytest.mark.asyncio
    async def test_returns_pattern_statistics(self, diagnostics_engine, mock_db):
        """Doit retourner statistiques des patterns"""
        # Arrange
        from sqlalchemy import func
        
        mock_query = Mock()
        mock_query.group_by.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.side_effect = [
            # top_components
            [Mock(affected_component="api", count=15)],
            # severity_dist
            [Mock(severity="high", count=5), Mock(severity="medium", count=10)]
        ]
        mock_query.scalar.side_effect = [50, 30]  # total, resolved
        mock_query.filter.return_value = mock_query
        
        mock_db.query.return_value = mock_query
        
        with patch.object(
            diagnostics_engine,
            '_calculate_avg_resolution_time',
            new_callable=AsyncMock,
            return_value=4.5
        ):
            # Act
            patterns = await diagnostics_engine.get_diagnostic_patterns()
        
        # Assert
        assert patterns["total_diagnostics"] == 50
        assert patterns["resolved"] == 30
        assert patterns["resolution_rate"] == 60.0
        assert patterns["avg_resolution_time_hours"] == 4.5
        assert len(patterns["top_affected_components"]) > 0
        assert "severity_distribution" in patterns


class TestPrivateMethods:
    """Tests pour méthodes privées"""
    
    @pytest.mark.asyncio
    async def test_search_relevant_context(self, diagnostics_engine):
        """Doit rechercher contexte dans multiples sources"""
        # Arrange
        diagnostics_engine.vector_service.search_similar = AsyncMock(side_effect=[
            # Code results
            [{"payload": {"file_path": "test.py", "content": "code"}, "score": 0.9}],
            # Log results
            [{"payload": {"message": "Error", "timestamp": "2024-01-01"}, "score": 0.8}],
            # Doc results
            [{"payload": {"title": "Guide", "content": "documentation"}, "score": 0.7}]
        ])
        
        # Act
        context = await diagnostics_engine._search_relevant_context(
            "Test issue",
            "api"
        )
        
        # Assert
        assert "code_sections" in context
        assert "log_entries" in context
        assert "documentation" in context
        assert len(context["code_sections"]) > 0
    
    def test_calculate_text_similarity(self, diagnostics_engine):
        """Test calcul de similarité textuelle"""
        # Act
        similarity = diagnostics_engine._calculate_text_similarity(
            "application crashes on startup",
            "app crashes at start"
        )
        
        # Assert
        assert 0.0 <= similarity <= 1.0
        assert similarity > 0.4  # Devrait avoir quelques mots en commun
    
    @pytest.mark.asyncio
    async def test_calculate_avg_resolution_time(self, diagnostics_engine, mock_db):
        """Test calcul temps moyen de résolution"""
        # Arrange
        from datetime import timedelta
        
        now = datetime.utcnow()
        mock_reports = [
            Mock(
                created_at=now - timedelta(hours=5),
                resolved_at=now
            ),
            Mock(
                created_at=now - timedelta(hours=3),
                resolved_at=now
            )
        ]
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = mock_reports
        
        mock_db.query.return_value = mock_query
        
        # Act
        avg_time = await diagnostics_engine._calculate_avg_resolution_time()
        
        # Assert
        assert avg_time == 4.0  # (5 + 3) / 2
