"""
FastAPI Application Entry Point
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.api import api_router
from app.core.logging import get_logger
import time

logger = get_logger(__name__)

# Variable globale pour l'état de préparation
app_ready = False

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    version="0.1.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    logger.info(f"{request.method} {request.url.path}")
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"{request.method} {request.url.path} - {response.status_code} ({process_time:.2f}s)")
    return response

# Include API Router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "service": "ai-support-agent"
    }


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint - vérifie si tous les services sont prêts"""
    from app.services.knowledge.vector_service import vector_service
    from app.services.collector.jira_collector import jira_collector
    from app.services.knowledge.manager import get_graph_service
    
    graph_service = get_graph_service()
    
    services = {
        "app": app_ready,
        "qdrant": vector_service.is_available() if hasattr(vector_service, 'is_available') else False,
        "jira": jira_collector.jira_client is not None if jira_collector else False,
        "neo4j": graph_service.is_available() if graph_service else False
    }
    
    all_ready = all(services.values())
    
    return {
        "ready": all_ready,
        "services": services,
        "message": "All services ready" if all_ready else "Some services are still initializing..."
    }


@app.on_event("startup")
async def startup_event():
    """Actions on application startup"""
    global app_ready
    
    print(f"[START] Starting {settings.PROJECT_NAME}")
    print(f"   LLM Provider: {settings.LLM_PROVIDER}")
    print(f"   Model: {settings.GROQ_MODEL if settings.LLM_PROVIDER == 'groq' else 'N/A'}")
    
    # Initialize database (désactivé temporairement pour éviter les erreurs d'encodage)
    try:
        from app.db.session import init_db
        init_db()
        print("   [OK] Database initialized")
    except Exception as e:
        print(f"   [ERREUR] Database init failed: {e}")
        print("   [INFO] Application will continue without database")
    
    # Initialiser Jira si configuré
    try:
        from app.services.collector.jira_collector import jira_collector
        if jira_collector.jira_url and jira_collector.api_token:
            print("   [INFO] Initializing Jira connection...")
            if jira_collector._connect():
                print("   [OK] Jira connected")
            else:
                print("   [WARN] Jira connection failed")
    except Exception as e:
        print(f"   [WARN] Jira init error: {e}")
    
    # Initialiser le GraphService (Neo4j)
    try:
        from app.services.knowledge.manager import get_graph_service
        graph_service = get_graph_service()
        if graph_service.is_available():
            print("   [OK] Neo4j Graph Service connected")
        else:
            print("   [WARN] Neo4j not available - graph features disabled")
    except Exception as e:
        print(f"   [WARN] GraphService init error: {e}")
    
    # Marquer l'application comme prête
    app_ready = True
    print("[READY] Application is ready to accept requests")


@app.on_event("shutdown")
async def shutdown_event():
    """Actions on application shutdown"""
    print(f"[STOP] Shutting down {settings.PROJECT_NAME}")
    # Close database connections
    # Save state
