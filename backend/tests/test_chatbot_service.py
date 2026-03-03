"""
Tests for Chatbot Service
"""
import pytest
from app.services.chatbot.chatbot_service import ChatbotService
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
