"""
Jira Sync Worker
Synchronize Jira tickets to Qdrant and Neo4j
"""
from celery import Task
from workers.celery_app import celery_app
from datetime import datetime, timedelta
import logging
from typing import Dict, Any, List
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.services.knowledge.vector_service import VectorService
from app.services.knowledge.graph_service import GraphService

logger = logging.getLogger(__name__)


class JiraSyncTask(Task):
    """Base task for Jira synchronization"""
    _vector_service = None
    _graph_service = None
    
    @property
    def vector_service(self):
        if self._vector_service is None:
            self._vector_service = VectorService()
        return self._vector_service
    
    @property
    def graph_service(self):
        if self._graph_service is None:
            self._graph_service = GraphService()
        return self._graph_service


@celery_app.task(base=JiraSyncTask, bind=True, name='workers.jira_sync.sync_jira_tickets')
def sync_jira_tickets(self, project_key: str = None, incremental: bool = True):
    """
    Synchronize Jira tickets to vector store and knowledge graph
    
    Args:
        project_key: Jira project key (e.g., 'BRASIL'). If None, sync all configured projects
        incremental: If True, only sync tickets updated since last sync
    """
    try:
        logger.info(f"Starting Jira sync for project: {project_key or 'ALL'}")
        
        # Import Jira client (assume configured)
        try:
            from jira import JIRA
            from app.core.config import settings
            
            # Get Jira credentials from config
            jira_url = getattr(settings, 'JIRA_URL', None)
            jira_user = getattr(settings, 'JIRA_USER', None)
            jira_token = getattr(settings, 'JIRA_TOKEN', None)
            
            if not all([jira_url, jira_user, jira_token]):
                logger.warning("Jira credentials not configured, skipping sync")
                return {
                    'status': 'skipped',
                    'message': 'Jira credentials not configured',
                    'synced': 0
                }
            
            jira = JIRA(server=jira_url, basic_auth=(jira_user, jira_token))
            
        except ImportError:
            logger.error("Jira library not installed. Install with: pip install jira")
            return {
                'status': 'error',
                'message': 'Jira library not installed',
                'synced': 0
            }
        except Exception as e:
            logger.error(f"Failed to connect to Jira: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'synced': 0
            }
        
        # Build JQL query
        jql_parts = []
        if project_key:
            jql_parts.append(f"project = {project_key}")
        
        if incremental:
            # Get issues updated in last 24 hours
            since = (datetime.utcnow() - timedelta(hours=24)).strftime('%Y-%m-%d')
            jql_parts.append(f"updated >= {since}")
        
        jql = " AND ".join(jql_parts) if jql_parts else "order by updated DESC"
        
        logger.info(f"JQL Query: {jql}")
        
        # Fetch issues
        issues = jira.search_issues(jql, maxResults=1000)
        logger.info(f"Found {len(issues)} issues to sync")
        
        synced_count = 0
        
        for issue in issues:
            try:
                # Extract issue data
                issue_data = {
                    'key': issue.key,
                    'summary': issue.fields.summary,
                    'description': issue.fields.description or '',
                    'status': issue.fields.status.name,
                    'priority': issue.fields.priority.name if issue.fields.priority else 'None',
                    'issue_type': issue.fields.issuetype.name,
                    'created': issue.fields.created,
                    'updated': issue.fields.updated,
                    'reporter': issue.fields.reporter.displayName if issue.fields.reporter else 'Unknown',
                    'assignee': issue.fields.assignee.displayName if issue.fields.assignee else 'Unassigned',
                }
                
                # Prepare content for embedding
                content = f"{issue.key}: {issue.fields.summary}\n\n{issue.fields.description or ''}"
                
                # Prepare metadata
                metadata = {
                    'type': 'jira_ticket',
                    'key': issue.key,
                    'summary': issue.fields.summary,
                    'status': issue.fields.status.name,
                    'priority': issue.fields.priority.name if issue.fields.priority else 'None',
                    'created': issue.fields.created,
                    'updated': issue.fields.updated,
                    'reporter': issue.fields.reporter.displayName if issue.fields.reporter else 'Unknown',
                    'assignee': issue.fields.assignee.displayName if issue.fields.assignee else 'Unassigned',
                    'source': 'jira',
                    'file_path': f'jira://{issue.key}',
                    'language': 'jira'
                }
                
                # Add to vector store
                self.vector_service.add_code_snippet(
                    code=content,
                    metadata=metadata,
                    snippet_id=f"jira_{issue.key}"
                )
                
                # Add to knowledge graph (if available)
                if self.graph_service.is_available():
                    node_id = self.graph_service.add_code_node(
                        name=issue.key,
                        node_type='jira_ticket',
                        file_path=f'jira://{issue.key}',
                        metadata={
                            'summary': issue.fields.summary[:200],
                            'status': issue.fields.status.name,
                            'priority': issue.fields.priority.name if issue.fields.priority else 'None',
                            'created': issue.fields.created,
                            'language': 'jira'
                        }
                    )
                
                synced_count += 1
                
                if synced_count % 10 == 0:
                    logger.info(f"Synced {synced_count}/{len(issues)} issues...")
                    self.update_state(
                        state='PROGRESS',
                        meta={'current': synced_count, 'total': len(issues)}
                    )
                
            except Exception as e:
                logger.error(f"Failed to sync issue {issue.key}: {e}")
                continue
        
        logger.info(f"Jira sync completed: {synced_count} issues synced")
        
        return {
            'status': 'success',
            'message': f'Synced {synced_count} Jira tickets',
            'synced': synced_count,
            'total': len(issues),
            'project': project_key or 'ALL'
        }
        
    except Exception as e:
        logger.error(f"Jira sync failed: {e}")
        return {
            'status': 'error',
            'message': str(e),
            'synced': 0
        }


@celery_app.task(name='workers.jira_sync.scheduled_sync')
def scheduled_sync():
    """
    Scheduled task to sync Jira tickets periodically
    Run this with Celery Beat
    """
    logger.info("Starting scheduled Jira sync")
    
    # Sync all configured projects incrementally
    result = sync_jira_tickets.delay(project_key=None, incremental=True)
    
    return {
        'status': 'scheduled',
        'task_id': result.id
    }


@celery_app.task(name='workers.jira_sync.full_resync')
def full_resync(project_key: str = None):
    """
    Full resync of all Jira tickets (not incremental)
    Use this for initial setup or after major changes
    """
    logger.info(f"Starting full Jira resync for project: {project_key or 'ALL'}")
    
    result = sync_jira_tickets.delay(project_key=project_key, incremental=False)
    
    return {
        'status': 'scheduled',
        'task_id': result.id,
        'type': 'full_resync'
    }
