"""
Chatbot Schemas
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional


class ChatMessage(BaseModel):
    """Chat message from user"""
    content: str = Field(..., description="Message content")
    role: str = Field(default="user", description="Message role (user/assistant)")
    conversation_id: Optional[str] = None
    user_id: str = "anonymous"
    context: Optional[dict] = None
    
    # Accepter aussi 'message' comme alias de 'content'
    @field_validator('content', mode='before')
    @classmethod
    def accept_message_field(cls, v, info):
        # Si 'message' est fourni au lieu de 'content', l'utiliser
        if v is None and hasattr(info, 'data') and 'message' in info.data:
            return info.data.get('message')
        return v


class ChatResponse(BaseModel):
    """AI response"""
    message: str
    sources: List[dict] = []
    suggestions: List[str] = []
    confidence: float
    conversation_id: str
    timestamp: Optional[str] = None


class ConversationHistory(BaseModel):
    """Conversation history"""
    conversation_id: str
    messages: List[dict]
    created_at: str
    updated_at: str
