"""
Gestionnaire des services de connaissance (singleton)
"""
from app.services.knowledge.vector_service import VectorService
from app.services.knowledge.graph_service import GraphService

# Instances singleton
_vector_service: VectorService = None
_graph_service: GraphService = None


def get_vector_service() -> VectorService:
    """Obtenir l'instance singleton du service vectoriel"""
    global _vector_service
    if _vector_service is None:
        _vector_service = VectorService()
    return _vector_service


def get_graph_service() -> GraphService:
    """Obtenir l'instance singleton du service de graphe"""
    global _graph_service
    if _graph_service is None:
        _graph_service = GraphService()
    return _graph_service
