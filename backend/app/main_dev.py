"""
Version de développement simplifiée du backend
Fonctionne sans Docker et sans bases de données
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import os
from groq import Groq

# Configuration Groq
GROQ_API_KEY = "GROQ_API_KEY_REDACTED"
groq_client = Groq(api_key=GROQ_API_KEY)

app = FastAPI(title="AI Support Agent - Dev Mode")

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modèles
class Message(BaseModel):
    content: str
    role: str = "user"

class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    timestamp: str

class Conversation(BaseModel):
    id: str
    title: str
    created_at: str
    message_count: int

# Stockage temporaire en mémoire
conversations_db = {}
messages_db = {}

@app.get("/")
async def root():
    return {
        "message": "AI Support Agent API - Mode Développement",
        "status": "running",
        "version": "0.1.0-dev"
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "mode": "development"}

# API Chatbot
@app.post("/api/v1/chatbot/chat", response_model=ChatResponse)
async def chat(message: Message):
    """Endpoint de chat avec Groq AI"""
    conversation_id = "conv_001"
    
    try:
        # Appel à l'API Groq
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": """Tu es un assistant IA expert pour les équipes de support technique.
Tu aides à analyser les applications, diagnostiquer les problèmes et proposer des solutions.
Réponds en français de manière claire et professionnelle."""
                },
                {
                    "role": "user",
                    "content": message.content
                }
            ],
            model="llama-3.1-8b-instant",
            temperature=0.7,
            max_tokens=1024,
        )
        
        response_text = chat_completion.choices[0].message.content
        
    except Exception as e:
        response_text = f"""Erreur lors de l'appel à l'API Groq : {str(e)}

**Note** : Je fonctionne en mode développement simplifié.

Votre message : "{message.content}"

Pour une assistance complète, assurez-vous que la clé API Groq est valide."""
    
    return ChatResponse(
        response=response_text,
        conversation_id=conversation_id,
        timestamp=datetime.now().isoformat()
    )

@app.get("/api/v1/chatbot/conversations", response_model=List[Conversation])
async def list_conversations():
    """Liste des conversations"""
    return [
        Conversation(
            id="conv_001",
            title="Conversation de test",
            created_at=datetime.now().isoformat(),
            message_count=0
        )
    ]

@app.get("/api/v1/chatbot/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Récupérer une conversation"""
    return {
        "id": conversation_id,
        "title": "Conversation de test",
        "messages": [],
        "created_at": datetime.now().isoformat()
    }

# API Collector
@app.post("/api/v1/collector/code")
async def collect_code(repo_url: str):
    return {"status": "queued", "task_id": "task_001", "message": "Collecte de code en attente (mode dev)"}

@app.post("/api/v1/collector/logs")
async def collect_logs(log_path: str):
    return {"status": "queued", "task_id": "task_002", "message": "Collecte de logs en attente (mode dev)"}

# API Dashboard
@app.get("/api/v1/dashboard/stats")
async def get_stats():
    return {
        "total_conversations": 1,
        "total_analyses": 0,
        "knowledge_items": 0,
        "pending_validations": 0,
        "mode": "development"
    }

# API Validation
@app.get("/api/v1/validation/pending")
async def get_pending_validations():
    return []

# API Knowledge
@app.get("/api/v1/knowledge/search")
async def search_knowledge(query: str):
    return {
        "results": [],
        "total": 0,
        "query": query,
        "message": "Base de connaissances non disponible en mode dev"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
