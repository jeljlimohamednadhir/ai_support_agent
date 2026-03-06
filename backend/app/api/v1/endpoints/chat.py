"""
Chat Conversation Endpoints
Manages user chat conversations and messages with authentication
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from app.db.session import get_db
from app.models.user import User, ChatConversation, ChatMessage
from app.core.auth import get_current_active_user
from app.core.llm_client import llm_client
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic schemas
class MessageCreate(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    timestamp: datetime
    
    class Config:
        from_attributes = True


class ConversationCreate(BaseModel):
    title: Optional[str] = "New Conversation"


class ConversationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    message_count: Optional[int] = 0
    
    class Config:
        from_attributes = True


class ConversationDetailResponse(ConversationResponse):
    messages: List[MessageResponse] = []


@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List all conversations for current user
    Ordered by most recently updated first
    """
    conversations = (
        db.query(ChatConversation)
        .filter(ChatConversation.user_id == current_user.id)
        .order_by(ChatConversation.updated_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    # Add message count to each conversation
    for conv in conversations:
        conv.message_count = db.query(ChatMessage).filter(
            ChatMessage.conversation_id == conv.id
        ).count()
    
    logger.info(f"User {current_user.username} listed {len(conversations)} conversations")
    return conversations


@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation_data: ConversationCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new conversation for current user
    """
    now = datetime.utcnow()
    conversation = ChatConversation(
        user_id=current_user.id,
        title=conversation_data.title or "New Conversation",
        created_at=now,
        updated_at=now
    )
    
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    
    conversation.message_count = 0
    
    logger.info(f"User {current_user.username} created conversation {conversation.id}: {conversation.title}")
    return conversation


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific conversation with all its messages
    User can only access their own conversations
    """
    conversation = db.query(ChatConversation).filter(
        ChatConversation.id == conversation_id,
        ChatConversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied"
        )
    
    # Load messages
    messages = db.query(ChatMessage).filter(
        ChatMessage.conversation_id == conversation_id
    ).order_by(ChatMessage.timestamp.asc()).all()
    
    conversation.messages = messages
    conversation.message_count = len(messages)
    
    return conversation


@router.put("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: int,
    conversation_data: ConversationCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update conversation title
    User can only update their own conversations
    """
    conversation = db.query(ChatConversation).filter(
        ChatConversation.id == conversation_id,
        ChatConversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied"
        )
    
    conversation.title = conversation_data.title or conversation.title
    conversation.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(conversation)
    
    conversation.message_count = db.query(ChatMessage).filter(
        ChatMessage.conversation_id == conversation.id
    ).count()
    
    logger.info(f"User {current_user.username} updated conversation {conversation_id}")
    return conversation


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a conversation and all its messages
    User can only delete their own conversations
    """
    conversation = db.query(ChatConversation).filter(
        ChatConversation.id == conversation_id,
        ChatConversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied"
        )
    
    # Delete all messages first (cascade should handle this, but being explicit)
    db.query(ChatMessage).filter(ChatMessage.conversation_id == conversation_id).delete()
    
    # Delete conversation
    db.delete(conversation)
    db.commit()
    
    logger.info(f"User {current_user.username} deleted conversation {conversation_id}")
    return None


@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def add_message(
    conversation_id: int,
    message_data: MessageCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Add a message to a conversation
    User can only add messages to their own conversations
    """
    # Verify conversation ownership
    conversation = db.query(ChatConversation).filter(
        ChatConversation.id == conversation_id,
        ChatConversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied"
        )
    
    # Validate role
    if message_data.role not in ["user", "assistant"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be 'user' or 'assistant'"
        )
    
    # Create message
    message = ChatMessage(
        conversation_id=conversation_id,
        role=message_data.role,
        content=message_data.content
    )
    
    db.add(message)
    
    # Update conversation timestamp
    conversation.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(message)
    
    logger.info(f"User {current_user.username} added {message_data.role} message to conversation {conversation_id}")
    return message


@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def list_messages(
    conversation_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List all messages in a conversation
    User can only access messages from their own conversations
    """
    # Verify conversation ownership
    conversation = db.query(ChatConversation).filter(
        ChatConversation.id == conversation_id,
        ChatConversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied"
        )
    
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.timestamp.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    return messages


@router.post("/conversations/{conversation_id}/generate-title", response_model=ConversationResponse)
async def generate_conversation_title(
    conversation_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Generate an AI title for a conversation based on its first user message.
    Updates the conversation title in DB and returns the updated conversation.
    """
    conversation = db.query(ChatConversation).filter(
        ChatConversation.id == conversation_id,
        ChatConversation.user_id == current_user.id
    ).first()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied"
        )

    # Get first user message
    first_message = (
        db.query(ChatMessage)
        .filter(ChatMessage.conversation_id == conversation_id, ChatMessage.role == "user")
        .order_by(ChatMessage.timestamp.asc())
        .first()
    )

    if not first_message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No user message found in this conversation"
        )

    # Ask LLM for a short title
    try:
        prompt = (
            f"Génère un titre court (5 à 8 mots maximum, en français) pour une conversation "
            f"dont la première question est : \"{first_message.content[:300]}\"\n"
            f"Réponds uniquement avec le titre, sans guillemets ni ponctuation finale."
        )
        title = await llm_client.generate(prompt, max_tokens=30)
        title = title.strip().strip('"').strip("'")
        if len(title) > 80:
            title = title[:77] + "..."
    except Exception as e:
        logger.warning(f"LLM title generation failed: {e} — using truncated message")
        title = first_message.content[:60].strip()
        if len(first_message.content) > 60:
            title += "..."

    conversation.title = title
    conversation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(conversation)

    conversation.message_count = db.query(ChatMessage).filter(
        ChatMessage.conversation_id == conversation.id
    ).count()

    logger.info(f"Generated title for conversation {conversation_id}: '{title}'")
    return conversation
