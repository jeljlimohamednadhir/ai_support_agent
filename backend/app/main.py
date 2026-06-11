"""
FastAPI Application Entry Point
"""
import os as _os
# Force offline mode for HuggingFace to use local cache (no internet access)
_os.environ.setdefault('HF_HUB_OFFLINE', '1')
_os.environ.setdefault('TRANSFORMERS_OFFLINE', '1')

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.api.v1.api import api_router
from app.core.logging import get_logger
import time

logger = get_logger(__name__)

# Variable globale pour l'état de préparation
app_ready = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager — remplace @app.on_event('startup'/'shutdown')"""
    global app_ready

    # --- STARTUP ---
    print(f"[START] Starting {settings.PROJECT_NAME}")
    print(f"   LLM Provider: {settings.LLM_PROVIDER}")
    print(f"   Model: {settings.GROQ_MODEL if settings.LLM_PROVIDER == 'groq' else 'N/A'}")

    # Initialize database
    try:
        import asyncio
        from app.db.session import init_db
        await asyncio.get_event_loop().run_in_executor(None, init_db)
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

    # Initialiser le GraphService (Neo4j) — probe TCP rapide au démarrage
    try:
        from app.services.knowledge.manager import get_graph_service
        _gs = get_graph_service()
        if _gs:
            import asyncio as _asyncio
            _neo4j_ok = await _asyncio.get_event_loop().run_in_executor(None, _gs.is_available)
            if _neo4j_ok:
                print("   [OK] GraphService connecté à Neo4j")
            else:
                print("   [WARN] GraphService: Neo4j non disponible (mode dégradé)")
        else:
            print("   [WARN] GraphService non initialisé")
    except Exception as e:
        print(f"   [WARN] GraphService init error: {e}")

    app_ready = True
    print("[READY] Application is ready to accept requests")

    yield  # <-- l'application tourne ici

    # --- SHUTDOWN ---
    print(f"[STOP] Shutting down {settings.PROJECT_NAME}")


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    version="0.1.0",
    lifespan=lifespan,
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
    """Readiness check endpoint — retourne le statut mis en cache de chaque service.
    N'effectue JAMAIS de nouvelle sonde bloquante : répond toujours en <50 ms."""
    from app.services.knowledge.vector_service import vector_service
    from app.services.collector.jira_collector import jira_collector
    from app.services.knowledge.manager import get_graph_service

    graph_service = get_graph_service()

    # Read cached availability flags — no blocking I/O
    qdrant_ok = getattr(vector_service, '_available', False)
    jira_ok   = (jira_collector.jira_client is not None) if jira_collector else False
    neo4j_ok  = getattr(graph_service, '_available', False) if graph_service else False

    services = {
        "app":    app_ready,
        "qdrant": qdrant_ok,
        "jira":   jira_ok,
        "neo4j":  neo4j_ok,
    }

    all_ready = all(services.values())

    return {
        "ready": all_ready,
        "services": services,
        "message": "All services ready" if all_ready else "Some services are unavailable (degraded mode)",
    }




