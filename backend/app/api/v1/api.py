"""
API v1 Router
Aggregates all API endpoints
"""
from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    chat,
    chatbot,
    collector,
    analyzer,
    knowledge,
    validation,
    diagnostics,
    users,
    dashboard,
    jira,
    config,
    classification_ml,
    apps,
    intelligence,
    hierarchical_ml,
)

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(chatbot.router, prefix="/chatbot", tags=["chatbot"])
api_router.include_router(collector.router, prefix="/collector", tags=["collector"])
api_router.include_router(analyzer.router, prefix="/analyzer", tags=["analyzer"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(validation.router, prefix="/validation", tags=["validation"])
api_router.include_router(diagnostics.router, prefix="/diagnostics", tags=["diagnostics"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(jira.router, prefix="/jira", tags=["jira"])
api_router.include_router(config.router, prefix="/config", tags=["config"])
api_router.include_router(classification_ml.router, prefix="/classification-ml", tags=["classification-ml"])
api_router.include_router(apps.router, prefix="/apps", tags=["apps"])
api_router.include_router(intelligence.router, prefix="/intelligence", tags=["intelligence"])
api_router.include_router(hierarchical_ml.router, prefix="/hierarchical-ml", tags=["hierarchical-ml"])
