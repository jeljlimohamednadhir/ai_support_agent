"""
Jira Collector Service
Collects and processes Jira tickets for knowledge base
"""
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from jira import JIRA, JIRAError
from jira.resources import Issue

from app.core.config import settings
from app.schemas.jira import (
    JiraIssue, JiraProject, JiraStats, JiraSyncRequest, 
    JiraSyncResponse, JiraTestConnectionResponse
)

logger = logging.getLogger(__name__)


class JiraCollector:
    """Service for collecting Jira tickets"""
    
    # Cache pour stats et projets (5 minutes)
    _stats_cache: Optional[JiraStats] = None
    _stats_cache_time: Optional[datetime] = None
    _projects_cache: Optional[List[JiraProject]] = None
    _projects_cache_time: Optional[datetime] = None
    _cache_duration = timedelta(minutes=5)
    
    def __init__(self, jira_url: str = None, email: str = None, api_token: str = None, auto_connect: bool = False):
        """Initialize Jira collector"""
        raw_url = jira_url or settings.JIRA_URL or ""
        # Strip /projects/... suffix — we need the server root only
        import re as _re
        self.jira_url = _re.sub(r'/projects/.*$', '', raw_url.rstrip('/'))
        # Traiter les chaînes vides comme None
        self.email = email if email and email.strip() else (settings.JIRA_EMAIL if settings.JIRA_EMAIL and settings.JIRA_EMAIL.strip() else None)
        # Always strip whitespace from token
        raw_token = api_token or settings.JIRA_API_TOKEN or ""
        self.api_token = raw_token.strip() or None
        self.jira_client: Optional[JIRA] = None
        
        # Connexion automatique seulement si demandée explicitement
        if auto_connect and self.jira_url and self.api_token:
            self._connect()
    
    def _connect(self) -> bool:
        """Establish connection to Jira"""
        try:
            # Support pour 2 types d'authentification:
            # 1. Personal Access Token (PAT) - Jira Cloud/Server moderne
            # 2. API Token avec email - Jira Cloud classique
            
            if self.api_token and not self.email:
                # Authentification avec PAT uniquement (Bearer token)
                self.jira_client = JIRA(
                    server=self.jira_url,
                    token_auth=self.api_token,
                    timeout=10,  # Timeout réduit à 10s
                    max_retries=1
                )
                logger.info(f"Connecté à Jira avec PAT: {self.jira_url}")
            else:
                # Authentification avec email + API token (Basic Auth)
                self.jira_client = JIRA(
                    server=self.jira_url,
                    basic_auth=(self.email, self.api_token),
                    timeout=10,  # Timeout réduit à 10s
                    max_retries=1
                )
                logger.info(f"Connecté à Jira avec Basic Auth: {self.jira_url}")
            
            return True
        except JIRAError as e:
            logger.error(f"Erreur connexion Jira: {e}")
            self.jira_client = None
            return False
        except Exception as e:
            logger.error(f"Erreur inattendue Jira: {e}")
            self.jira_client = None
            return False
    
    def test_connection(self) -> JiraTestConnectionResponse:
        """Test Jira connection"""
        try:
            if not self.jira_client:
                if not self._connect():
                    return JiraTestConnectionResponse(
                        success=False,
                        message="Impossible de se connecter à Jira. Vérifiez les credentials."
                    )
            
            # Get server info
            server_info = self.jira_client.server_info()
            projects = self.jira_client.projects()
            
            return JiraTestConnectionResponse(
                success=True,
                message=f"Connecté à Jira {server_info.get('version', 'unknown')}",
                server_info={
                    "version": server_info.get("version"),
                    "build": server_info.get("buildNumber"),
                    "url": self.jira_url
                },
                projects_count=len(projects)
            )
        except JIRAError as e:
            return JiraTestConnectionResponse(
                success=False,
                message=f"Erreur Jira: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Erreur test connexion: {e}")
            return JiraTestConnectionResponse(
                success=False,
                message=f"Erreur: {str(e)}"
            )
    
    def get_projects(self) -> List[JiraProject]:
        """Get only BRASIL project"""
        # Vérifier le cache
        if self._projects_cache and self._projects_cache_time:
            if datetime.now() - self._projects_cache_time < self._cache_duration:
                logger.debug("Retour projets depuis cache")
                return self._projects_cache
        
        if not self.jira_client:
            logger.warning("Client Jira non initialisé, tentative de connexion...")
            if not self._connect():
                logger.error("Impossible de se connecter à Jira")
                return []
        
        try:
            # Récupérer uniquement le projet BRASIL
            result = []
            
            try:
                project = self.jira_client.project('BRASIL')
                
                # Récupérer quelques tickets pour obtenir le total (plus rapide que maxResults=0)
                search_result = self.jira_client.search_issues(
                    "project = BRASIL ORDER BY updated DESC",
                    maxResults=1  # On récupère juste 1 ticket pour avoir le .total
                )
                issue_count = search_result.total if hasattr(search_result, 'total') else 0
                
                # Récupérer le lead (c'est un objet User, pas un dict)
                lead_name = None
                if hasattr(project, 'lead') and project.lead:
                    lead_name = getattr(project.lead, 'displayName', None)
                
                result.append(JiraProject(
                    id=project.id,
                    key=project.key,
                    name=project.name,
                    description=getattr(project, 'description', None),
                    lead=lead_name,
                    project_type=getattr(project, 'projectTypeKey', None),
                    issue_count=issue_count
                ))
                
                logger.info(f"[OK] Projet BRASIL trouvé avec {issue_count} tickets")
            except Exception as e:
                logger.error(f"[ERROR] Impossible de récupérer le projet BRASIL: {e}")
            
            # Mettre en cache
            self._projects_cache = result
            self._projects_cache_time = datetime.now()
            
            return result
        except Exception as e:
            logger.error(f"Erreur récupération projets: {e}")
            return []
    
    def _parse_issue(self, issue: Issue) -> JiraIssue:
        """Parse Jira issue to schema"""
        fields = issue.fields
        
        return JiraIssue(
            id=issue.id,
            key=issue.key,
            summary=fields.summary,
            description=fields.description or "",
            status=fields.status.name if hasattr(fields.status, 'name') else str(fields.status),
            priority=fields.priority.name if fields.priority and hasattr(fields.priority, 'name') else None,
            issue_type=fields.issuetype.name if hasattr(fields.issuetype, 'name') else str(fields.issuetype),
            assignee=fields.assignee.displayName if fields.assignee else None,
            reporter=fields.reporter.displayName if fields.reporter else None,
            created=datetime.fromisoformat(fields.created.replace('Z', '+00:00')) if fields.created else None,
            updated=datetime.fromisoformat(fields.updated.replace('Z', '+00:00')) if fields.updated else None,
            resolved=datetime.fromisoformat(fields.resolutiondate.replace('Z', '+00:00')) if fields.resolutiondate else None,
            project_key=fields.project.key if hasattr(fields.project, 'key') else "",
            project_name=fields.project.name if hasattr(fields.project, 'name') else "",
            labels=list(fields.labels) if fields.labels else [],
            components=[c.name for c in fields.components] if fields.components else []
        )
    
    def fetch_issues(self, request: JiraSyncRequest) -> List[JiraIssue]:
        """Fetch Jira issues from BRASIL project only"""
        if not self.jira_client:
            logger.warning("Client Jira non initialisé, tentative de connexion...")
            if not self._connect():
                logger.error("Impossible de se connecter à Jira")
                return []
        
        try:
            # Forcer le projet BRASIL uniquement
            jql_parts = ["project = BRASIL"]
            
            if not request.include_resolved:
                jql_parts.append("resolution = Unresolved")
            
            jql = " AND ".join(jql_parts) + " ORDER BY updated DESC"
            
            logger.info(f"[SEARCH] Recherche Jira BRASIL avec JQL: {jql}")
            logger.info(f"Max results: {request.max_results}")
            
            # Search issues
            issues = self.jira_client.search_issues(
                jql,
                maxResults=request.max_results,
                fields="summary,description,status,priority,issuetype,assignee,reporter,created,updated,resolutiondate,project,labels,components"
            )
            
            logger.info(f"[OK] Trouvé {len(issues)} tickets Jira BRASIL")
            
            # Parse issues
            parsed_issues = []
            for issue in issues:
                try:
                    parsed = self._parse_issue(issue)
                    parsed_issues.append(parsed)
                except Exception as e:
                    logger.warning(f"Erreur parsing ticket {issue.key}: {e}")
                    continue
            
            return parsed_issues
            
        except JIRAError as e:
            logger.error(f"[ERROR] Erreur recherche Jira: {e}")
            return []
        except Exception as e:
            logger.error(f"[ERROR] Erreur inattendue fetch issues: {e}")
            return []
    
    def get_stats(self) -> JiraStats:
        """Get Jira statistics for BRASIL project only"""
        # Vérifier le cache
        if self._stats_cache and self._stats_cache_time:
            if datetime.now() - self._stats_cache_time < self._cache_duration:
                logger.debug("Retour stats depuis cache")
                return self._stats_cache
        
        if not self.jira_client:
            logger.warning("Client Jira non initialisé, tentative de connexion...")
            if not self._connect():
                logger.error("Impossible de se connecter à Jira")
                return JiraStats()
        
        try:
            stats = JiraStats()
            
            # Stats uniquement pour le projet BRASIL
            logger.info("Récupération stats pour projet BRASIL...")
            
            # Toujours 1 projet (BRASIL uniquement)
            stats.total_projects = 1
            
            # Compter les tickets BRASIL avec la méthode rapide
            try:
                search_result = self.jira_client.search_issues(
                    "project = BRASIL ORDER BY updated DESC",
                    maxResults=1  # On récupère juste 1 ticket pour avoir le .total
                )
                stats.total_issues = search_result.total if hasattr(search_result, 'total') else 0
                logger.info(f"[OK] {stats.total_issues} tickets trouvés dans BRASIL")
            except Exception as e:
                logger.error(f"Erreur comptage tickets BRASIL: {e}")
                stats.total_issues = 0
            
            # Compter par statut
            try:
                # Tickets ouverts (To Do, Open, etc.)
                open_result = self.jira_client.search_issues(
                    'project = BRASIL AND status in ("Open", "To Do", "Backlog", "New") ORDER BY created DESC',
                    maxResults=1
                )
                stats.open_issues = open_result.total if hasattr(open_result, 'total') else 0
                logger.info(f"[SEARCH] {stats.open_issues} tickets ouverts")
                
                # Tickets en cours
                progress_result = self.jira_client.search_issues(
                    'project = BRASIL AND status in ("In Progress", "In Development", "In Review") ORDER BY created DESC',
                    maxResults=1
                )
                stats.in_progress_issues = progress_result.total if hasattr(progress_result, 'total') else 0
                logger.info(f"[SEARCH] {stats.in_progress_issues} tickets en cours")
                
                # Tickets résolus
                resolved_result = self.jira_client.search_issues(
                    'project = BRASIL AND status = "Resolved" ORDER BY created DESC',
                    maxResults=1
                )
                stats.resolved_issues = resolved_result.total if hasattr(resolved_result, 'total') else 0
                logger.info(f"[SEARCH] {stats.resolved_issues} tickets résolus")
                
                # Tickets fermés
                closed_result = self.jira_client.search_issues(
                    'project = BRASIL AND status in ("Closed", "Done", "Completed") ORDER BY created DESC',
                    maxResults=1
                )
                stats.closed_issues = closed_result.total if hasattr(closed_result, 'total') else 0
                logger.info(f"[SEARCH] {stats.closed_issues} tickets fermés")
                
            except Exception as e:
                logger.error(f"[ERROR] Erreur comptage par statut: {e}")
            
            stats.last_sync = datetime.now()
            
            # Mettre en cache
            self._stats_cache = stats
            self._stats_cache_time = datetime.now()
            
            logger.info(f"Stats Jira BRASIL: {stats.total_issues} tickets")
            return stats
            
        except Exception as e:
            logger.error(f"Erreur récupération stats: {e}")
            return JiraStats()
    
    def format_issue_for_rag(self, issue: JiraIssue) -> Dict[str, Any]:
        """Format issue for RAG injection"""
        # Build content string
        content_parts = [
            f"Ticket: {issue.key}",
            f"Résumé: {issue.summary}",
            f"Type: {issue.issue_type}",
            f"Statut: {issue.status}",
            f"Projet: {issue.project_name} ({issue.project_key})",
        ]
        
        if issue.priority:
            content_parts.append(f"Priorité: {issue.priority}")
        
        if issue.assignee:
            content_parts.append(f"Assigné à: {issue.assignee}")
        
        if issue.description:
            content_parts.append(f"\nDescription:\n{issue.description[:2000]}")
        
        if issue.labels:
            content_parts.append(f"\nLabels: {', '.join(issue.labels)}")
        
        if issue.components:
            content_parts.append(f"Composants: {', '.join(issue.components)}")
        
        content = "\n".join(content_parts)
        
        # Build metadata
        metadata = {
            "type": "jira_ticket",
            "source": "jira",
            "ticket_key": issue.key,
            "ticket_id": issue.id,
            "status": issue.status,
            "priority": issue.priority or "None",
            "issue_type": issue.issue_type,
            "project_key": issue.project_key,
            "project_name": issue.project_name,
            "created": issue.created.isoformat() if issue.created else None,
            "updated": issue.updated.isoformat() if issue.updated else None,
            "assignee": issue.assignee,
            "labels": issue.labels,
            "components": issue.components
        }
        
        return {
            "content": content,
            "metadata": metadata
        }


# Global instance
jira_collector = JiraCollector()
