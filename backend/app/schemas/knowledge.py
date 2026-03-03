"""
Knowledge Graph Schemas
"""
from pydantic import BaseModel
from typing import List, Optional, Dict


class KnowledgeQuery(BaseModel):
    """Knowledge graph query"""
    query: str
    filters: Optional[Dict] = None
    limit: int = 10


class KnowledgeNode(BaseModel):
    """Knowledge graph node"""
    id: str
    type: str
    properties: Dict
    relationships: List[dict] = []


class GraphStats(BaseModel):
    """Graph statistics"""
    total_nodes: int
    total_relationships: int
    node_types: Dict[str, int]
