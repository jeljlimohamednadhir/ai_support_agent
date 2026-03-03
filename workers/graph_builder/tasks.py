"""
Knowledge Graph Builder Worker
Build and update the knowledge graph from collected data
"""
from celery import Task
from workers.celery_app import celery_app
import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.services.knowledge.graph_service import GraphService
from app.services.knowledge.vector_service import VectorService

logger = logging.getLogger(__name__)


class GraphBuilderTask(Task):
    """Base task for graph building"""
    _graph_service = None
    _vector_service = None
    
    @property
    def graph_service(self):
        if self._graph_service is None:
            self._graph_service = GraphService()
        return self._graph_service
    
    @property
    def vector_service(self):
        if self._vector_service is None:
            self._vector_service = VectorService()
        return self._vector_service


@celery_app.task(base=GraphBuilderTask, bind=True, name='workers.graph_builder.build_graph')
def build_knowledge_graph(self, source_types: list = None):
    """
    Build knowledge graph from vector store data
    
    Args:
        source_types: List of source types to process (e.g., ['code', 'database_table', 'jira_ticket'])
    """
    try:
        logger.info("Starting knowledge graph build")
        
        if not self.graph_service.is_available():
            logger.error("Neo4j not available")
            return {
                'status': 'error',
                'message': 'Neo4j not available',
                'nodes_created': 0
            }
        
        # Get all points from Qdrant
        points = []
        offset = None
        batch_size = 100
        
        logger.info("Fetching data from Qdrant...")
        
        while True:
            result = self.vector_service.client.scroll(
                collection_name=self.vector_service.collection_name,
                limit=batch_size,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )
            
            batch_points = result[0]
            if not batch_points:
                break
            
            points.extend(batch_points)
            offset = result[1]
            
            if offset is None:
                break
        
        logger.info(f"Found {len(points)} points in Qdrant")
        
        nodes_created = 0
        relationships_created = 0
        
        # Process each point
        for idx, point in enumerate(points):
            try:
                payload = point.payload
                
                # Skip if source_types specified and not in list
                if source_types and payload.get('type') not in source_types:
                    continue
                
                # Extract node data
                node_type = payload.get('type', 'unknown')
                name = payload.get('name') or payload.get('key') or payload.get('table_name') or str(point.id)
                file_path = payload.get('file_path', '')
                
                # Create metadata dict (primitives only)
                metadata = {
                    'language': payload.get('language', ''),
                    'source': payload.get('source', 'qdrant'),
                }
                
                # Add type-specific metadata
                if node_type == 'jira_ticket':
                    metadata['status'] = payload.get('status', '')
                    metadata['priority'] = payload.get('priority', '')
                elif node_type == 'database_table':
                    metadata['schema'] = payload.get('schema', '')
                
                # Add node to graph
                node_id = self.graph_service.add_code_node(
                    name=name,
                    node_type=node_type,
                    file_path=file_path,
                    metadata=metadata
                )
                
                nodes_created += 1
                
                # Create relationships based on references
                # TODO: Extract references from content and create relationships
                
                if (idx + 1) % 50 == 0:
                    logger.info(f"Processed {idx + 1}/{len(points)} points...")
                    self.update_state(
                        state='PROGRESS',
                        meta={
                            'current': idx + 1,
                            'total': len(points),
                            'nodes_created': nodes_created
                        }
                    )
                
            except Exception as e:
                logger.error(f"Failed to process point {point.id}: {e}")
                continue
        
        # Get final stats
        stats = self.graph_service.get_statistics()
        
        logger.info(f"Graph build completed: {nodes_created} nodes, {relationships_created} relationships")
        
        return {
            'status': 'success',
            'message': f'Built knowledge graph with {nodes_created} nodes',
            'nodes_created': nodes_created,
            'relationships_created': relationships_created,
            'graph_stats': stats
        }
        
    except Exception as e:
        logger.error(f"Graph build failed: {e}")
        return {
            'status': 'error',
            'message': str(e),
            'nodes_created': 0
        }


@celery_app.task(base=GraphBuilderTask, bind=True, name='workers.graph_builder.update_relationships')
def update_relationships(self):
    """
    Analyze existing nodes and create/update relationships
    """
    try:
        logger.info("Starting relationship analysis")
        
        if not self.graph_service.is_available():
            return {
                'status': 'error',
                'message': 'Neo4j not available'
            }
        
        relationships_created = 0
        
        # Query all nodes
        with self.graph_service.driver.session() as session:
            result = session.run("MATCH (n) RETURN n LIMIT 1000")
            nodes = [record["n"] for record in result]
            
            logger.info(f"Analyzing {len(nodes)} nodes for relationships...")
            
            # TODO: Implement relationship detection logic
            # Examples:
            # - Code files that import other files
            # - Tables referenced in code
            # - Jira tickets linked to code files
            
        return {
            'status': 'success',
            'message': f'Updated {relationships_created} relationships',
            'relationships_created': relationships_created
        }
        
    except Exception as e:
        logger.error(f"Relationship update failed: {e}")
        return {
            'status': 'error',
            'message': str(e)
        }


@celery_app.task(name='workers.graph_builder.scheduled_build')
def scheduled_graph_build():
    """
    Scheduled task to rebuild graph periodically
    Run with Celery Beat
    """
    logger.info("Starting scheduled graph build")
    
    result = build_knowledge_graph.delay()
    
    return {
        'status': 'scheduled',
        'task_id': result.id
    }
