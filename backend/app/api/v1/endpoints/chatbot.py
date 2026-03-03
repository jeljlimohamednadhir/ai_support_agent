"""
Chatbot Endpoints
Handles conversational AI interactions
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from app.schemas.chatbot import ChatMessage, ChatResponse, ConversationHistory
from app.services.chatbot.chatbot_service import ChatbotService

router = APIRouter()

# Instance globale du chatbot service (singleton)
_chatbot_service = None

def get_chatbot_service() -> ChatbotService:
    """Obtenir l'instance singleton du chatbot service"""
    global _chatbot_service
    if _chatbot_service is None:
        _chatbot_service = ChatbotService()
    return _chatbot_service


@router.post("/chat", response_model=ChatResponse)
async def chat(message: ChatMessage):
    """
    Send a message to the AI assistant
    
    The AI will:
    - Analyze the question
    - Search the knowledge graph
    - Provide expert answers
    - Suggest diagnostics steps
    """
    try:
        chatbot_service = get_chatbot_service()
        response = await chatbot_service.process_message(message)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conversation_id}", response_model=ConversationHistory)
async def get_conversation(conversation_id: str):
    """Get conversation history"""
    try:
        chatbot_service = get_chatbot_service()
        history = await chatbot_service.get_conversation_history(conversation_id)
        return history
    except Exception as e:
        raise HTTPException(status_code=404, detail="Conversation not found")


@router.post("/feedback")
async def submit_feedback(conversation_id: str, message_id: str, feedback: dict):
    """
    Submit feedback on AI response
    Used for continuous improvement
    """
    try:
        chatbot_service = get_chatbot_service()
        await chatbot_service.save_feedback(conversation_id, message_id, feedback)
        return {"status": "success", "message": "Feedback saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
