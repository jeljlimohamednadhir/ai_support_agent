"""
Tests pour le service de Validation
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.orm import Session

from app.services.validation.validation_service import ValidationService
from app.models.database import ValidationTask, Correction
from app.schemas.validation import ValidationResult, CorrectionSubmission


@pytest.fixture
def mock_db():
    """Mock de la session database"""
    return Mock(spec=Session)


@pytest.fixture
def validation_service(mock_db):
    """Instance de ValidationService avec DB mockée"""
    return ValidationService(mock_db)


class TestGetPendingTasks:
    """Tests pour get_pending_tasks"""
    
    @pytest.mark.asyncio
    async def test_get_pending_tasks_returns_list(self, validation_service, mock_db):
        """Doit retourner liste de tâches pending"""
        # Arrange
        mock_tasks = [
            Mock(
                id=1,
                task_type="response_validation",
                priority=5,
                status="pending",
                original_data={"question": "Test?"},
                ai_suggestion={"answer": "Test answer"},
                created_at=datetime.utcnow()
            )
        ]
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_tasks
        
        mock_db.query.return_value = mock_query
        
        # Act
        result = await validation_service.get_pending_tasks(limit=10)
        
        # Assert
        assert len(result) == 1
        assert result[0]["task_id"] == "1"
        assert result[0]["task_type"] == "response_validation"
        assert result[0]["status"] == "pending"
    
    @pytest.mark.asyncio
    async def test_get_pending_tasks_with_filter(self, validation_service, mock_db):
        """Doit filtrer par task_type"""
        # Arrange
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        
        mock_db.query.return_value = mock_query
        
        # Act
        await validation_service.get_pending_tasks(limit=5, task_type="rule_extraction")
        
        # Assert
        assert mock_query.filter.call_count == 2  # status + task_type


class TestSubmitValidation:
    """Tests pour submit_validation"""
    
    @pytest.mark.asyncio
    async def test_submit_approved_validation(self, validation_service, mock_db):
        """Doit approuver et appliquer suggestion"""
        # Arrange
        mock_task = Mock(
            id=1,
            task_type="response_validation",
            ai_suggestion={"answer": "Correct answer"},
            validated_at=None
        )
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_task
        
        mock_db.query.return_value = mock_query
        
        validation = ValidationResult(
            task_id="1",
            approved=True,
            validator_id="user123"
        )
        
        with patch.object(validation_service, '_apply_to_knowledge_base', new_callable=AsyncMock):
            # Act
            result = await validation_service.submit_validation(validation)
        
        # Assert
        assert result["task_id"] == "1"
        assert result["status"] == "validated"
        assert result["applied"] is True
        assert mock_task.status == "validated"
        assert mock_task.validator_id == "user123"
    
    @pytest.mark.asyncio
    async def test_submit_rejected_validation(self, validation_service, mock_db):
        """Doit rejeter sans appliquer"""
        # Arrange
        mock_task = Mock(id=1, validated_at=None)
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_task
        
        mock_db.query.return_value = mock_query
        
        validation = ValidationResult(
            task_id="1",
            approved=False,
            validator_id="user123",
            comments="Incorrect answer"
        )
        
        # Act
        result = await validation_service.submit_validation(validation)
        
        # Assert
        assert result["status"] == "rejected"
        assert mock_task.status == "rejected"
        assert mock_task.validation_comment == "Incorrect answer"
    
    @pytest.mark.asyncio
    async def test_submit_validation_not_found(self, validation_service, mock_db):
        """Doit lever ValueError si tâche inexistante"""
        # Arrange
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        
        mock_db.query.return_value = mock_query
        
        validation = ValidationResult(
            task_id="999",
            approved=True,
            validator_id="user123"
        )
        
        # Act & Assert
        with pytest.raises(ValueError, match="Validation task 999 not found"):
            await validation_service.submit_validation(validation)


class TestApplyCorrection:
    """Tests pour apply_correction"""
    
    @pytest.mark.asyncio
    async def test_apply_correction_to_knowledge_node(self, validation_service, mock_db):
        """Doit appliquer correction à un nœud"""
        # Arrange
        correction = CorrectionSubmission(
            entity_id="node123",
            entity_type="knowledge_node",
            corrections={"description": "Updated description"},
            reason="Outdated info",
            submitter_id="user123"
        )
        
        mock_correction = Mock(id=1)
        mock_db.add = Mock()
        mock_db.flush = Mock()
        
        with patch.object(
            validation_service,
            '_update_knowledge_node',
            new_callable=AsyncMock,
            return_value=True
        ):
            # Act
            result = await validation_service.apply_correction(correction)
        
        # Assert
        assert result["applied"] is True
        assert result["entity_type"] == "knowledge_node"
        assert result["entity_id"] == "node123"


class TestGetMetrics:
    """Tests pour get_metrics"""
    
    @pytest.mark.asyncio
    async def test_get_metrics_returns_stats(self, validation_service, mock_db):
        """Doit retourner statistiques complètes"""
        # Arrange
        from sqlalchemy import func
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.scalar.side_effect = [100, 80, 15, 10]  # total, approved, pending, weekly
        mock_query.group_by.return_value = mock_query
        mock_query.all.return_value = [
            Mock(task_type="response_validation", count=50),
            Mock(task_type="rule_extraction", count=30)
        ]
        
        mock_db.query.return_value = mock_query
        
        # Act
        metrics = await validation_service.get_metrics()
        
        # Assert
        assert metrics["total_validations"] == 100
        assert metrics["approved"] == 80
        assert metrics["rejected"] == 20
        assert metrics["accuracy_rate"] == 80.0
        assert metrics["pending_count"] == 15
        assert metrics["weekly_validations"] == 10
        assert "by_type" in metrics


class TestBrasilTerrainConsistency:
    """Tests pour verify_brasil_terrain_consistency"""
    
    @pytest.mark.asyncio
    async def test_detects_inconsistencies(self, validation_service, mock_db):
        """Doit détecter incohérences"""
        # Arrange
        brasil_data = {
            "id": "123",
            "status": "active",
            "description": "BRASIL description"
        }
        
        terrain_data = {
            "id": "123",
            "status": "inactive",  # Incohérence
            "description": "BRASIL description"
        }
        
        with patch.object(
            validation_service,
            'create_validation_task',
            new_callable=AsyncMock
        ) as mock_create:
            # Act
            result = await validation_service.verify_brasil_terrain_consistency(
                brasil_data,
                terrain_data
            )
        
        # Assert
        assert result["consistent"] is False
        assert result["inconsistencies_count"] > 0
        assert any(i["field"] == "status" for i in result["inconsistencies"])
    
    @pytest.mark.asyncio
    async def test_creates_validation_task_for_critical(self, validation_service, mock_db):
        """Doit créer tâche si incohérence critique"""
        # Arrange
        brasil_data = {"affectation": "Team A"}
        terrain_data = {"affectation": "Team B"}  # Champ critique
        
        with patch.object(
            validation_service,
            'create_validation_task',
            new_callable=AsyncMock
        ) as mock_create:
            # Act
            result = await validation_service.verify_brasil_terrain_consistency(
                brasil_data,
                terrain_data
            )
        
        # Assert
        assert mock_create.called
        assert result["validation_task_created"] is True


@pytest.mark.asyncio
async def test_create_validation_task(validation_service, mock_db):
    """Test création de tâche de validation"""
    # Arrange
    task_type = "pattern_confirmation"
    original_data = {"pattern": "Error pattern XYZ"}
    ai_suggestion = {"confidence": 0.8}
    
    mock_db.add = Mock()
    mock_db.commit = Mock()
    
    # Act
    task_id = await validation_service.create_validation_task(
        task_type,
        original_data,
        ai_suggestion,
        priority=7
    )
    
    # Assert
    assert task_id is not None
    assert mock_db.add.called
    assert mock_db.commit.called
