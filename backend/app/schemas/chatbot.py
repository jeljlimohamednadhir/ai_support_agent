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

    # Multi-tenant : identifiant de l'application cible
    app_id: str = Field(default="BRASIL", description="Identifiant de l'application (ex: BRASIL)")

    # Mémoire conversationnelle : historique passé par le frontend ou rechargé depuis la DB
    # Format : [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
    conversation_history: Optional[List[dict]] = Field(
        default=None,
        description="Historique des échanges précédents pour la mémoire conversationnelle"
    )

    # Mode 3 enrichi : logs et stack traces optionnels
    logs: Optional[str] = Field(default=None, description="Logs bruts (Mode 3)")
    stack_trace: Optional[str] = Field(default=None, description="Stack trace brute (Mode 3)")

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

    # Métadonnées multi-tenant
    app_id: Optional[str] = None
    pipeline_mode: Optional[str] = None      # FR_RICH | FR_WEAK | LOG_BASED
    trust_score: Optional[int] = None        # 0-100
    trust_label: Optional[str] = None        # strong | moderate | weak | insufficient
    diagnostic_available: Optional[bool] = None

    # Diagnostic Engine N3 enrichment
    procedure_id: Optional[str] = None           # matched N3 procedure ID (e.g. PROC-BRASIL-PROV-0001)
    exceptions_detected: Optional[List[str]] = None  # list of detected exception class names
    thinking_content: Optional[str] = None       # <think>...</think> extrait du LLM (Qwen3, DeepSeek-R1...)


class ConversationHistory(BaseModel):
    """Conversation history"""
    conversation_id: str
    messages: List[dict]
    created_at: str
    updated_at: str
