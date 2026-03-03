"""
Collector Endpoints
Manages data collection from various sources
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from app.schemas.collector import CollectionJob, CollectionStatus
from app.services.collector.orchestrator import CollectorOrchestrator

router = APIRouter()


class CodeCollectionRequest(BaseModel):
    """Requête de collection de code"""
    repo_url: str
    branch: str = "main"


@router.post("/collect/code", response_model=CollectionJob)
async def collect_code(
    request: CodeCollectionRequest,
    background_tasks: BackgroundTasks = None
):
    """
    Trigger code collection from Git repository
    Accepts local paths (Windows/Linux) or Git URLs
    """
    try:
        # Normaliser le chemin pour Windows
        repo_url = request.repo_url.replace('/', '\\') if ':\\' in request.repo_url or request.repo_url.startswith('c:') else request.repo_url
        
        orchestrator = CollectorOrchestrator()
        job = await orchestrator.start_code_collection(repo_url, request.branch)
        return job
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/collect/logs")
async def collect_logs(log_source: dict):
    """
    Trigger log collection
    Supports: file paths, syslog, cloud logging services
    """
    try:
        orchestrator = CollectorOrchestrator()
        job = await orchestrator.start_log_collection(log_source)
        return job
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/collect/database")
async def collect_database_schema(db_config: dict):
    """
    Collect database schema and metadata
    """
    try:
        orchestrator = CollectorOrchestrator()
        job = await orchestrator.start_db_collection(db_config)
        return job
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/collect/documentation")
async def collect_documentation(doc_sources: list):
    """
    Collect and index documentation
    Supports: Markdown, HTML, PDF, API specs
    """
    try:
        orchestrator = CollectorOrchestrator()
        job = await orchestrator.start_doc_collection(doc_sources)
        return job
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}", response_model=CollectionStatus)
async def get_job_status(job_id: str):
    """Get collection job status"""
    try:
        orchestrator = CollectorOrchestrator()
        status = await orchestrator.get_job_status(job_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=404, detail="Job not found")


@router.get("/jobs")
async def list_jobs(limit: int = 50):
    """List all collection jobs"""
    try:
        orchestrator = CollectorOrchestrator()
        jobs = await orchestrator.list_jobs(limit)
        return jobs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/stats")
async def get_knowledge_stats():
    """
    Obtenir les statistiques du knowledge store (graphe + vecteurs)
    """
    try:
        from app.services.knowledge.manager import get_vector_service, get_graph_service
        
        vector_service = get_vector_service()
        graph_service = get_graph_service()
        
        vector_stats = await vector_service.get_statistics()
        graph_stats = await graph_service.get_statistics()
        
        return {
            "vector_store": vector_stats,
            "knowledge_graph": graph_stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
