"""
Knowledge Graph Endpoints
Manages the knowledge base
"""
from fastapi import APIRouter, HTTPException
from app.schemas.knowledge import KnowledgeQuery, KnowledgeNode, GraphStats
from app.services.knowledge_graph.graph_service import KnowledgeGraphService

router = APIRouter()


@router.post("/search")
async def search_knowledge(query: KnowledgeQuery):
    """
    Search the knowledge graph
    Supports semantic search, graph traversal, and filters
    """
    try:
        kg_service = KnowledgeGraphService()
        results = await kg_service.search(query)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/node/{node_id}")
async def get_node(node_id: str):
    """Get a specific knowledge node with relationships"""
    try:
        kg_service = KnowledgeGraphService()
        node = await kg_service.get_node(node_id)
        return node
    except Exception as e:
        raise HTTPException(status_code=404, detail="Node not found")


@router.get("/relationships/{entity}")
async def get_relationships(entity: str, depth: int = 2):
    """
    Get relationships for an entity
    Example: relationships for a function, table, or endpoint
    """
    try:
        kg_service = KnowledgeGraphService()
        relationships = await kg_service.get_relationships(entity, depth)
        return relationships
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=GraphStats)
async def get_graph_stats():
    """Get knowledge graph statistics"""
    try:
        kg_service = KnowledgeGraphService()
        stats = await kg_service.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rebuild")
async def rebuild_graph():
    """
    Rebuild the knowledge graph from scratch
    Should be used after major updates
    """
    try:
        kg_service = KnowledgeGraphService()
        result = await kg_service.rebuild()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph")
async def get_graph_visualization(limit: int = 100):
    """
    Récupérer le graphe complet pour visualisation
    Retourne nodes et links au format compatible avec react-force-graph
    """
    from app.services.knowledge.manager import get_graph_service
    
    graph_service = get_graph_service()
    
    if not graph_service.is_available():
        return {
            "nodes": [], 
            "links": [],
            "message": "Neo4j non disponible. Le graphe de connaissance n'est pas accessible."
        }
    
    try:
        # Requête Neo4j pour récupérer nodes et relations
        query = f"""
        MATCH (n:CodeNode)
        WITH n LIMIT {limit}
        OPTIONAL MATCH (n)-[r]->(m:CodeNode)
        RETURN n, r, m
        """
        
        with graph_service.driver.session() as session:
            result = session.run(query)
            
            nodes_dict = {}
            links = []
            
            for record in result:
                # Node source
                if record["n"]:
                    node_data = dict(record["n"])
                    node_id = node_data.get("id", str(record["n"].id))
                    if node_id not in nodes_dict:
                        nodes_dict[node_id] = {
                            "id": node_id,
                            "name": node_data.get("name", node_id),
                            "type": node_data.get("type", "unknown"),
                            "file_path": node_data.get("file_path", ""),
                            "language": node_data.get("language", "")
                        }
                
                # Relation et node target
                if record["r"] and record["m"]:
                    target_data = dict(record["m"])
                    target_id = target_data.get("id", str(record["m"].id))
                    
                    if target_id not in nodes_dict:
                        nodes_dict[target_id] = {
                            "id": target_id,
                            "name": target_data.get("name", target_id),
                            "type": target_data.get("type", "unknown"),
                            "file_path": target_data.get("file_path", ""),
                            "language": target_data.get("language", "")
                        }
                    
                    links.append({
                        "source": node_id,
                        "target": target_id,
                        "type": record["r"].type
                    })
            
            return {
                "nodes": list(nodes_dict.values()),
                "links": links
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération du graphe: {str(e)}")

