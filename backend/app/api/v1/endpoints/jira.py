"""
Jira API Endpoints
"""
import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
# NOTE: qdrant_client importé lazily dans les fonctions pour ne pas bloquer le démarrage

from app.schemas.jira import (
    JiraConnection, JiraStats, JiraSyncRequest, JiraSyncResponse,
    JiraTestConnectionResponse, JiraSearchRequest, JiraSearchResponse,
    JiraProject, JiraIssue
)
from app.services.collector.jira_collector import JiraCollector
from app.services.knowledge.vector_service import vector_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/test-connection", response_model=JiraTestConnectionResponse)
async def test_jira_connection(connection: JiraConnection):
    """Test Jira connection"""
    try:
        collector = JiraCollector(
            jira_url=connection.jira_url,
            email=connection.email,
            api_token=connection.api_token,
            auto_connect=True  # Forcer la connexion pour le test
        )
        return collector.test_connection()
    except Exception as e:
        logger.error(f"Erreur test connexion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects", response_model=List[JiraProject])
async def get_jira_projects():
    """Get all Jira projects"""
    try:
        from app.services.collector.jira_collector import jira_collector
        projects = jira_collector.get_projects()
        return projects
    except Exception as e:
        logger.error(f"Erreur récupération projets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=JiraStats)
async def get_jira_stats():
    """Get Jira statistics"""
    try:
        from app.services.collector.jira_collector import jira_collector
        stats = jira_collector.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Erreur récupération stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync", response_model=JiraSyncResponse)
async def sync_jira_issues(request: JiraSyncRequest):
    """Sync Jira issues to knowledge base"""
    start_time = datetime.now()
    errors = []
    
    try:
        from app.services.collector.jira_collector import jira_collector
        
        # Fetch issues
        issues = jira_collector.fetch_issues(request)
        
        if not issues:
            return JiraSyncResponse(
                success=False,
                issues_fetched=0,
                issues_indexed=0,
                projects=[],
                duration_seconds=0,
                errors=["Aucun ticket trouvé"]
            )
        
        # Get unique projects
        projects = list(set(issue.project_key for issue in issues))
        
        # Prepare points for Qdrant
        points = []
        for i, issue in enumerate(issues):
            try:
                formatted = jira_collector.format_issue_for_rag(issue)
                
                # Create embedding using the embedding_model
                embedding = vector_service.embedding_model.encode(formatted["content"]).tolist()
                
                # Create point
                from qdrant_client.models import PointStruct
                point = PointStruct(
                    id=hash(f"jira_{issue.key}_{issue.id}") % (2**63),
                    vector=embedding,
                    payload={
                        **formatted["metadata"],
                        "content": formatted["content"]
                    }
                )
                points.append(point)
                
            except Exception as e:
                logger.warning(f"Erreur traitement ticket {issue.key}: {e}")
                errors.append(f"Ticket {issue.key}: {str(e)}")
                continue
        
        # Upload to Qdrant
        if points:
            try:
                vector_service.client.upsert(
                    collection_name=vector_service.collection_name,
                    points=points
                )
                logger.info(f"Injecté {len(points)} tickets Jira dans Qdrant")
                
                # Ajouter les tickets au graphe Neo4j pour les corrélations
                try:
                    from app.services.knowledge.manager import get_graph_service
                    graph_service = get_graph_service()
                    
                    if graph_service.is_available():
                        for issue in issues:
                            # Créer nœud ticket
                            await graph_service.add_code_node(
                                node_id=f"jira_{issue.key}",
                                node_type="jira_ticket",
                                name=issue.key,
                                content=f"{issue.summary}\n{issue.description or ''}",
                                metadata={
                                    "status": issue.status,
                                    "priority": issue.priority,
                                    "project": issue.project_key,
                                    "created": issue.created.isoformat() if issue.created else None
                                }
                            )
                        
                        logger.info(f"Ajouté {len(issues)} tickets Jira dans Neo4j")
                except Exception as e:
                    logger.warning(f"Erreur ajout Neo4j: {e}")
                    
            except Exception as e:
                logger.error(f"Erreur injection Qdrant: {e}")
                errors.append(f"Erreur injection Qdrant: {str(e)}")
                raise
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return JiraSyncResponse(
            success=len(points) > 0,
            issues_fetched=len(issues),
            issues_indexed=len(points),
            projects=projects,
            duration_seconds=duration,
            errors=errors
        )
        
    except Exception as e:
        logger.error(f"Erreur sync Jira: {e}")
        duration = (datetime.now() - start_time).total_seconds()
        return JiraSyncResponse(
            success=False,
            issues_fetched=0,
            issues_indexed=0,
            projects=[],
            duration_seconds=duration,
            errors=[str(e)]
        )


@router.post("/search", response_model=JiraSearchResponse)
async def search_jira_issues(request: JiraSearchRequest):
    """Search Jira issues with pagination"""
    try:
        from app.services.collector.jira_collector import jira_collector
        
        # Build JQL
        jql_parts = []
        
        if request.query:
            jql_parts.append(f'text ~ "{request.query}"')
        
        if request.project_keys:
            projects = ", ".join(request.project_keys)
            jql_parts.append(f"project in ({projects})")
        
        if request.status:
            statuses = ", ".join([f'"{s}"' for s in request.status])
            jql_parts.append(f"status in ({statuses})")
        
        jql = " AND ".join(jql_parts) if jql_parts else "order by updated DESC"
        
        # Recherche avec pagination
        if not jira_collector.jira_client:
            raise HTTPException(status_code=503, detail="Jira non connecté")
        
        search_result = jira_collector.jira_client.search_issues(
            jql,
            startAt=request.start_at,
            maxResults=request.max_results,
            fields="summary,description,status,priority,issuetype,assignee,reporter,created,updated,resolutiondate,project,labels,components"
        )
        
        # Parser les issues
        issues = []
        for issue in search_result:
            try:
                parsed = jira_collector._parse_issue(issue)
                issues.append(parsed)
            except Exception as e:
                logger.warning(f"Erreur parsing {issue.key}: {e}")
                continue
        
        return JiraSearchResponse(
            issues=issues,
            total=search_result.total if hasattr(search_result, 'total') else len(issues),
            start_at=request.start_at,
            max_results=request.max_results
        )
        
    except Exception as e:
        logger.error(f"Erreur recherche Jira: {e}")
        raise HTTPException(status_code=500, detail=str(e))
