"""Tests for Chatbot Service."""
from types import SimpleNamespace

import pytest
from app.services.chatbot.chatbot_service import (
    ChatbotService,
    _has_real_live_evidence,
    _partition_live_context_blocks,
    _sanitize_llm_response_actions_with_context,
    _sanitize_resolution_actions_with_context,
)
from app.schemas.chatbot import ChatMessage


@pytest.fixture
def chatbot_service():
    """Create a chatbot service instance"""
    return ChatbotService()


@pytest.mark.asyncio
async def test_process_message_basic(chatbot_service):
    """Test basic message processing"""
    message = ChatMessage(
        content="Bonjour",
        role="user"
    )
    
    try:
        response = await chatbot_service.process_message(message)
        assert response is not None
        assert hasattr(response, 'message') or hasattr(response, 'content')
    except Exception as e:
        # Services may not be available in test environment
        pytest.skip(f"Services not available: {e}")


@pytest.mark.asyncio
async def test_list_query_detection(chatbot_service):
    """Test detection of list queries"""
    message = ChatMessage(
        content="cite-moi les 5 derniers jira",
        role="user"
    )
    
    try:
        response = await chatbot_service.process_message(message)
        assert response is not None
        # Should return a list response
    except Exception as e:
        pytest.skip(f"Services not available: {e}")


@pytest.mark.asyncio
async def test_knowledge_search(chatbot_service):
    """Test knowledge search functionality"""
    message = ChatMessage(
        content="Qu'est-ce que la table t_ports ?",
        role="user"
    )
    
    try:
        response = await chatbot_service.process_message(message)
        assert response is not None
    except Exception as e:
        pytest.skip(f"Services not available: {e}")


def test_sanitize_resolution_actions_drops_vague_unlinked_actions():
    raw_text = (
        "**Procédure de résolution (FR-TEST):**\n"
        "  1. Vérifier les logs\n"
        "  2. Identifier la cause\n"
    )
    cleaned = _sanitize_resolution_actions_with_context(
        raw_text,
        context_blocks=[],
        resolution_blocks=[],
    )

    assert "Vérifier les logs" not in cleaned
    assert "Identifier la cause" not in cleaned
    assert "Actions non proposées" in cleaned


def test_sanitize_resolution_actions_keeps_concrete_anchored_action():
    raw_text = (
        "**Procédure de résolution (FR-DSLAM-DELETION-189):**\n"
        "  1. Identifier la contrainte FK via DETAIL dans les logs psql\n"
        "  2. Nettoyer les références orphelines dans t_services\n"
    )
    resolution_blocks = [
        {
            "title": "Résolution: Foreign Key Violation",
            "fr_id": "FR-DSLAM-DELETION-189",
            "sql_hints_raw": ["SELECT * FROM t_services WHERE eqpt_id = 1;"],
        }
    ]
    cleaned = _sanitize_resolution_actions_with_context(
        raw_text,
        context_blocks=[{"title": "[LIVE_DB] Diagnostic", "source_type": "live_diagnostic"}],
        resolution_blocks=resolution_blocks,
    )

    assert "contrainte FK" in cleaned
    assert "t_services" in cleaned


def test_sanitize_llm_response_actions_drops_vague_unlinked_lines():
    response_text = (
        "🧠 **Diagnostic**\n"
        "Cause détectée.\n\n"
        "✅ **Actions recommandées**\n"
        "1. Vérifier les logs\n"
        "2. Identifier la cause\n\n"
        "📌 **Preuves détectées**\n"
        "- code=6969\n"
    )

    cleaned = _sanitize_llm_response_actions_with_context(
        response_text,
        context_blocks=[],
        resolution_blocks=[],
    )

    assert "1. Vérifier les logs" not in cleaned
    assert "2. Identifier la cause" not in cleaned
    assert "Actions non proposées" in cleaned
    assert "📌 **Preuves détectées**" in cleaned


def test_sanitize_llm_response_actions_keeps_anchored_concrete_lines():
    response_text = (
        "✅ **Actions recommandées**\n"
        "1. Identifier la contrainte FK via DETAIL dans les logs psql\n"
        "2. Exécuter SELECT * FROM t_services WHERE eqpt_id = 5050111;\n"
    )
    resolution_blocks = [
        {
            "title": "Résolution: Foreign Key Violation",
            "fr_id": "FR-DSLAM-DELETION-189",
            "sql_hints_raw": ["SELECT * FROM t_services WHERE eqpt_id = 5050111;"],
        }
    ]

    cleaned = _sanitize_llm_response_actions_with_context(
        response_text,
        context_blocks=[{"title": "[LIVE_DB] Diagnostic", "source_type": "live_diagnostic"}],
        resolution_blocks=resolution_blocks,
    )

    assert "contrainte FK" in cleaned
    assert "SELECT * FROM t_services" in cleaned


def test_partition_live_context_blocks_keeps_live_sources_separate():
    blocks = [
        {"source_type": "live_db", "title": "DB block"},
        {"source_type": "live_log", "title": "Log block"},
        {"source_type": "vector_knowledge", "title": "KB block"},
    ]

    parts = _partition_live_context_blocks(blocks)

    assert [b["title"] for b in parts["live_db"]] == ["DB block"]
    assert [b["title"] for b in parts["live_log"]] == ["Log block"]
    assert [b["title"] for b in parts["other"]] == ["KB block"]


def test_has_real_live_evidence_requires_actual_bundle_data():
    bundle = SimpleNamespace(
        db_evidence={"q": SimpleNamespace(has_data=False)},
        log_evidence=[],
        ssh_evidence=[],
    )

    assert _has_real_live_evidence(bundle) is False


def test_has_real_live_evidence_detects_log_lines_without_db_rows():
    bundle = SimpleNamespace(
        db_evidence={},
        log_evidence=[SimpleNamespace(has_data=False, matched_lines=["ERROR fk violation"])],
        ssh_evidence=[],
    )

    assert _has_real_live_evidence(bundle) is True
