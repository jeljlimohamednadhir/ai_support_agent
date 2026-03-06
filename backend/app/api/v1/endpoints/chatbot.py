"""
Chatbot Endpoints
Handles conversational AI interactions
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel
from app.schemas.chatbot import ChatMessage, ChatResponse, ConversationHistory
from app.services.chatbot.chatbot_service import ChatbotService
from app.db.session import get_db
from app.models.database import Correction
from app.core.auth import get_current_active_user
from app.models.user import User

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
async def chat(message: ChatMessage, db: Session = Depends(get_db)):
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
        response = await chatbot_service.process_message(message, db=db)
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


class SourceFeedbackRequest(BaseModel):
    source_name: str          # e.g. "FR 202"
    source_type: str          # e.g. "resolution_fiche"
    question: str             # the user question that triggered the retrieval
    conversation_id: Optional[str] = None
    reason: Optional[str] = "Source non pertinente pour ce contexte"


@router.post("/source-feedback", status_code=201)
async def report_irrelevant_source(
    body: SourceFeedbackRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Report a RAG source as irrelevant for a given question.
    Stored in the corrections table for future retraining.
    """
    correction = Correction(
        correction_type="chatbot_n3",
        entity_type="rag_source",
        entity_id=body.source_name,
        original_value={
            "source_name": body.source_name,
            "source_type": body.source_type,
            "question": body.question,
            "conversation_id": body.conversation_id,
        },
        corrected_value={
            "relevant": False,
            "action": "exclude_source",
        },
        corrector_id=str(current_user.id),
        reason=body.reason,
        applied=False,
        created_at=datetime.utcnow(),
    )
    db.add(correction)
    db.commit()
    return {"status": "saved", "source": body.source_name}
