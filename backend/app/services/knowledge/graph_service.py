"""
Service de gestion du graphe de connaissances avec Neo4j
"""
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)


@dataclass
class CodeNode:
    """Nœud représentant un élément de code"""
    id: str
    type: str  # 'file', 'class', 'function', 'import'
    name: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    

@dataclass
class Relationship:
    """Relation entre deux nœuds"""
    from_id: str
    to_id: str
    rel_type: str  # 'imports', 'calls', 'inherits', 'contains'
    metadata: Dict[str, Any] = field(default_factory=dict)


class GraphService:
    """Service pour gérer le graphe de connaissances avec Neo4j (singleton)"""
    
    # Instance singleton au niveau de la classe
    _instance = None
    _driver = None
    _initialized = False
    _connect_attempted = False        # True after first connect attempt (success or fail)
    _last_connect_attempt: float = 0  # epoch seconds of last attempt
    _RETRY_INTERVAL: float = 60.0    # retry after 60 s of cooldown
    
    def __new__(cls, uri: str = "bolt://localhost:7687", auth: tuple = ("neo4j", "password")):
        """Implémenter le singleton"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, uri: str = "bolt://localhost:7687", auth: tuple = ("neo4j", "password")):
        """Initialiser le service de graphe avec Neo4j — connexion LAZY (pas de blocage au démarrage)"""
        if GraphService._initialized:
            return
        self.uri = uri
        self.auth = auth
        self._available = False
        GraphService._initialized = True
        logger.info(f"[INFO] GraphService configuré — connexion Neo4j lazy sur {uri}")

    def _connect(self) -> bool:
        """
        Tente la connexion Neo4j avec un pré-test TCP (<2s) pour éviter
        que le handshake Bolt ne bloque plusieurs minutes.
        Appelé à la demande par is_available() et driver.
        Ne tente qu'une seule fois, puis attend _RETRY_INTERVAL secondes avant
        de réessayer — évite les blocages répétés sur /ready.
        """
        if GraphService._driver is not None:
            return self._available
        import time as _time
        import socket as _sock
        # Honour cooldown: don't retry within _RETRY_INTERVAL seconds
        now = _time.monotonic()
        if GraphService._connect_attempted and (now - GraphService._last_connect_attempt) < GraphService._RETRY_INTERVAL:
            return False
        GraphService._connect_attempted = True
        GraphService._last_connect_attempt = now
        try:
            host = self.uri.replace("bolt://", "").replace("bolt+s://", "").split(":")[0]
            raw = self.uri.split("//")[-1]
            port = int(raw.split(":")[-1]) if ":" in raw else 7687
            _sock.create_connection((host, port), timeout=2).close()
        except OSError:
            logger.warning(f"[WARN] Neo4j TCP injoignable ({self.uri}) — mode dégradé")
            return False
        try:
            GraphService._driver = GraphDatabase.driver(
                self.uri, auth=self.auth, connection_timeout=3
            )
            with GraphService._driver.session() as s:
                s.run("RETURN 1").consume()
            with GraphService._driver.session() as session:
                session.run("CREATE INDEX node_id_index IF NOT EXISTS FOR (n:CodeNode) ON (n.id)")
                session.run("CREATE INDEX node_type_index IF NOT EXISTS FOR (n:CodeNode) ON (n.type)")
                session.run("CREATE INDEX node_name_index IF NOT EXISTS FOR (n:CodeNode) ON (n.name)")
            self._available = True
            logger.info(f"[OK] GraphService connecté à Neo4j ({self.uri})")
        except Exception as e:
            logger.warning(f"[WARN] Neo4j non disponible ({self.uri}): {e}")
            GraphService._driver = None
            self._available = False
        return self._available

    def is_available(self) -> bool:
        """Vérifier si Neo4j est disponible — retourne le statut mis en cache.
        Tente la connexion une seule fois, puis attend _RETRY_INTERVAL secondes
        avant de réessayer (évite les blocages répétés sur /ready)."""
        if self._available:
            return True
        if GraphService._driver is not None:
            return self._available
        # If we haven't tried yet, or the cooldown has expired, probe once
        import time as _time
        now = _time.monotonic()
        if not GraphService._connect_attempted or (now - GraphService._last_connect_attempt) >= GraphService._RETRY_INTERVAL:
            self._connect()
        return getattr(self, '_available', False)

    @property
    def driver(self):
        """Accès au driver Neo4j — déclenche la connexion lazy si pas encore faite."""
        if GraphService._driver is None:
            self._connect()
        return GraphService._driver
    
    
    async def add_code_node(
        self,
        node_id: str,
        node_type: str,
        name: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Ajouter un nœud de code au graphe
        
        Args:
            node_id: ID unique du nœud
            node_type: Type (file, class, function, import)
            name: Nom de l'élément
            content: Contenu/code
            metadata: Métadonnées additionnelles
            
        Returns:
            True si succès
        """
        if not self.is_available():
            logger.warning("[WARN] Neo4j non disponible pour add_code_node")
            return False
            
        try:
            # Convertir les métadonnées en types primitifs pour Neo4j
            safe_metadata = {}
            if metadata:
                for key, value in metadata.items():
                    if isinstance(value, (str, int, float, bool)):
                        safe_metadata[key] = value
                    elif isinstance(value, (list, dict)):
                        safe_metadata[key] = str(value)
                    else:
                        safe_metadata[key] = str(value)
            
            with self.driver.session() as session:
                session.run(
                    """
                    MERGE (n:CodeNode {id: $node_id})
                    SET n.type = $node_type,
                        n.name = $name,
                        n.content = $content,
                        n.created_at = datetime(),
                        n += $metadata
                    """,
                    node_id=node_id,
                    node_type=node_type,
                    name=name,
                    content=content,
                    metadata=safe_metadata
                )
            
            logger.info(f"[OK] Nœud {node_id} ajouté à Neo4j (type: {node_type})")
            return True
            
        except Exception as e:
            logger.error(f"[ERREUR] add_code_node: {e}")
            return False
    
    
    async def create_relationship(
        self,
        from_id: str,
        to_id: str,
        rel_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Créer une relation entre deux nœuds
        
        Args:
            from_id: ID du nœud source
            to_id: ID du nœud cible
            rel_type: Type de relation (imports, calls, inherits, contains)
            metadata: Métadonnées additionnelles
            
        Returns:
            True si succès
        """
        try:
            with self.driver.session() as session:
                # Utiliser MERGE pour éviter les doublons
                session.run(
                    f"""
                    MATCH (from:CodeNode {{id: $from_id}})
                    MATCH (to:CodeNode {{id: $to_id}})
                    MERGE (from)-[r:{rel_type}]->(to)
                    SET r.metadata = $metadata
                    """,
                    from_id=from_id,
                    to_id=to_id,
                    metadata=metadata or {}
                )
            
            logger.info(f"[OK] Relation {from_id} --[{rel_type}]--> {to_id} dans Neo4j")
            return True
            
        except Exception as e:
            logger.error(f"[ERREUR] create_relationship: {e}")
            return False
    
    
    async def get_node(self, node_id: str) -> Optional[CodeNode]:
        """Récupérer un nœud par son ID"""
        try:
            with self.driver.session() as session:
                result = session.run(
                    """
                    MATCH (n:CodeNode {id: $node_id})
                    RETURN n.id AS id, n.type AS type, n.name AS name, 
                           n.content AS content, n.metadata AS metadata
                    """,
                    node_id=node_id
                )
                record = result.single()
                if record:
                    return CodeNode(
                        id=record['id'],
                        type=record['type'],
                        name=record['name'],
                        content=record['content'],
                        metadata=record['metadata'] or {}
                    )
            return None
        except Exception as e:
            logger.error(f"[ERREUR] get_node: {e}")
            return None
    
    
    async def find_nodes_by_type(self, node_type: str) -> List[CodeNode]:
        """Trouver tous les nœuds d'un type donné"""
        try:
            with self.driver.session() as session:
                result = session.run(
                    """
                    MATCH (n:CodeNode {type: $node_type})
                    RETURN n.id AS id, n.type AS type, n.name AS name,
                           n.content AS content, n.metadata AS metadata
                    """,
                    node_type=node_type
                )
                return [
                    CodeNode(
                        id=record['id'],
                        type=record['type'],
                        name=record['name'],
                        content=record['content'],
                        metadata=record['metadata'] or {}
                    )
                    for record in result
                ]
        except Exception as e:
            logger.error(f"[ERREUR] find_nodes_by_type: {e}")
            return []
    
    
    async def find_nodes_by_name(self, name: str) -> List[CodeNode]:
        """Trouver les nœuds par nom (recherche exacte)"""
        try:
            with self.driver.session() as session:
                result = session.run(
                    """
                    MATCH (n:CodeNode {name: $name})
                    RETURN n.id AS id, n.type AS type, n.name AS name,
                           n.content AS content, n.metadata AS metadata
                    """,
                    name=name
                )
                return [
                    CodeNode(
                        id=record['id'],
                        type=record['type'],
                        name=record['name'],
                        content=record['content'],
                        metadata=record['metadata'] or {}
                    )
                    for record in result
                ]
        except Exception as e:
            logger.error(f"[ERREUR] find_nodes_by_name: {e}")
            return []
    
    
    async def get_related_nodes(
        self,
        node_id: str,
        rel_type: Optional[str] = None,
        direction: str = "outgoing"
    ) -> List[CodeNode]:
        """
        Trouver les nœuds reliés à un nœud donné
        
        Args:
            node_id: ID du nœud source
            rel_type: Filtrer par type de relation (optionnel)
            direction: 'outgoing', 'incoming' ou 'both'
            
        Returns:
            Liste des nœuds reliés
        """
        try:
            with self.driver.session() as session:
                # Construire la requête selon la direction
                if direction == "outgoing":
                    query = """
                    MATCH (from:CodeNode {id: $node_id})-[r]->(to:CodeNode)
                    WHERE $rel_type IS NULL OR type(r) = $rel_type
                    RETURN to.id AS id, to.type AS type, to.name AS name,
                           to.content AS content, to.metadata AS metadata
                    """
                elif direction == "incoming":
                    query = """
                    MATCH (from:CodeNode)-[r]->(to:CodeNode {id: $node_id})
                    WHERE $rel_type IS NULL OR type(r) = $rel_type
                    RETURN from.id AS id, from.type AS type, from.name AS name,
                           from.content AS content, from.metadata AS metadata
                    """
                else:  # both
                    query = """
                    MATCH (n:CodeNode {id: $node_id})-[r]-(other:CodeNode)
                    WHERE $rel_type IS NULL OR type(r) = $rel_type
                    RETURN other.id AS id, other.type AS type, other.name AS name,
                           other.content AS content, other.metadata AS metadata
                    """
                
                result = session.run(query, node_id=node_id, rel_type=rel_type)
                return [
                    CodeNode(
                        id=record['id'],
                        type=record['type'],
                        name=record['name'],
                        content=record['content'],
                        metadata=record['metadata'] or {}
                    )
                    for record in result
                ]
        except Exception as e:
            logger.error(f"[ERREUR] get_related_nodes: {e}")
            return []
    
    
    async def get_dependencies(self, file_id: str) -> List[str]:
        """
        Obtenir les dépendances (imports) d'un fichier
        
        Args:
            file_id: ID du fichier
            
        Returns:
            Liste des IDs de fichiers dépendants
        """
        try:
            with self.driver.session() as session:
                result = session.run(
                    """
                    MATCH (file:CodeNode {id: $file_id})-[:IMPORTS]->(dep:CodeNode)
                    RETURN dep.id AS id
                    """,
                    file_id=file_id
                )
                return [record['id'] for record in result]
        except Exception as e:
            logger.error(f"[ERREUR] get_dependencies: {e}")
            return []
    
    
    async def add_relationship(
        self,
        from_node_id: str,
        to_node_id: str,
        relationship_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Ajouter une relation entre deux nœuds existants
        
        Args:
            from_node_id: ID du nœud source
            to_node_id: ID du nœud cible  
            relationship_type: Type de relation (AFFECTS, RESOLVES, DOCUMENTS, etc.)
            metadata: Métadonnées de la relation
            
        Returns:
            True si succès
        """
        if not self.is_available():
            logger.warning("[WARN] Neo4j non disponible pour add_relationship")
            return False
            
        try:
            with self.driver.session() as session:
                query = f"""
                MATCH (a:CodeNode {{id: $from_id}})
                MATCH (b:CodeNode {{id: $to_id}})
                MERGE (a)-[r:{relationship_type}]->(b)
                SET r += $metadata
                RETURN r
                """
                
                result = session.run(
                    query,
                    from_id=from_node_id,
                    to_id=to_node_id,
                    metadata=metadata or {}
                )
                
                logger.info(f"[OK] Relation créée: {from_node_id} -[{relationship_type}]-> {to_node_id}")
                return True
                
        except Exception as e:
            logger.error(f"[ERREUR] add_relationship: {e}")
            return False

    async def find_correlations(self, entity_name: str, max_depth: int = 2) -> List[Dict[str, Any]]:
        """
        Trouver toutes les corrélations pour une entité donnée
        
        Args:
            entity_name: Nom de l'entité (table, ticket, fiche)
            max_depth: Profondeur maximale de recherche dans le graphe
            
        Returns:
            Liste des corrélations avec métadonnées
        """
        if not self.is_available():
            return []
            
        try:
            with self.driver.session() as session:
                query = f"""
                MATCH path = (start:CodeNode)-[*1..{max_depth}]-(related:CodeNode)
                WHERE start.name =~ '(?i).*{entity_name}.*' 
                   OR start.id =~ '(?i).*{entity_name}.*'
                   OR $entity_name IN split(start.content, ' ')
                WITH start, related, relationships(path) as rels, length(path) as distance
                WHERE start.id <> related.id
                RETURN DISTINCT start, related, rels, distance
                ORDER BY distance, start.type, related.type
                LIMIT 20
                """
                
                result = session.run(query, entity_name=entity_name)
                correlations = []
                
                for record in result:
                    start_node = dict(record["start"])
                    related_node = dict(record["related"])
                    relationships = [dict(rel) for rel in record["rels"]]
                    
                    correlations.append({
                        'start': {
                            'id': start_node.get('id'),
                            'name': start_node.get('name'),
                            'type': start_node.get('type'),
                            'content_preview': start_node.get('content', '')[:100] + '...' if start_node.get('content') else ''
                        },
                        'related': {
                            'id': related_node.get('id'),
                            'name': related_node.get('name'),
                            'type': related_node.get('type'),
                            'content_preview': related_node.get('content', '')[:100] + '...' if related_node.get('content') else ''
                        },
                        'path_length': record["distance"],
                        'relationship_types': [rel.type for rel in record["rels"]] if record["rels"] else []
                    })
                
                logger.info(f"[OK] Trouvé {len(correlations)} corrélations pour '{entity_name}'")
                return correlations
                
        except Exception as e:
            logger.error(f"[ERREUR] find_correlations pour '{entity_name}': {e}")
            return []

    async def find_related_by_type(
        self,
        source_type: str,
        target_type: str,
        relationship_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Trouver les relations entre types spécifiques (ex: jira_ticket -> database_table)
        
        Args:
            source_type: Type de nœud source (jira_ticket, resolution_fiche, etc.)
            target_type: Type de nœud cible  
            relationship_types: Types de relations à filtrer (optionnel)
            
        Returns:
            Liste des relations trouvées
        """
        if not self.is_available():
            return []
            
        try:
            with self.driver.session() as session:
                rel_filter = ""
                if relationship_types:
                    rel_types_str = "|".join(relationship_types)
                    rel_filter = f"AND type(r) IN {relationship_types}"
                
                query = f"""
                MATCH (source:CodeNode {{type: $source_type}})-[r]->(target:CodeNode {{type: $target_type}})
                {rel_filter}
                RETURN source, target, type(r) as rel_type, r as relationship
                ORDER BY source.name, target.name
                LIMIT 50
                """
                
                result = session.run(
                    query,
                    source_type=source_type,
                    target_type=target_type
                )
                
                relations = []
                for record in result:
                    source_node = dict(record["source"])
                    target_node = dict(record["target"])
                    
                    relations.append({
                        'source': {
                            'id': source_node.get('id'),
                            'name': source_node.get('name'),
                            'type': source_node.get('type')
                        },
                        'target': {
                            'id': target_node.get('id'),
                            'name': target_node.get('name'),
                            'type': target_node.get('type')
                        },
                        'relationship_type': record["rel_type"],
                        'metadata': dict(record["relationship"]) if record["relationship"] else {}
                    })
                
                logger.info(f"[OK] Trouvé {len(relations)} relations {source_type} -> {target_type}")
                return relations
                
        except Exception as e:
            logger.error(f"[ERREUR] find_related_by_type: {e}")
            return []

    async def clear_graph(self) -> bool:
        """Vider complètement le graphe Neo4j (ATTENTION: destructif!)"""
        if not self.is_available():
            return False
            
        try:
            with self.driver.session() as session:
                # Supprimer toutes les relations
                session.run("MATCH ()-[r]->() DELETE r")
                # Supprimer tous les nœuds  
                session.run("MATCH (n:CodeNode) DELETE n")
                
                logger.warning("[WARN] Graphe Neo4j vidé complètement!")
                return True
                
        except Exception as e:
            logger.error(f"[ERREUR] clear_graph: {e}")
            return False
        """
        Obtenir les statistiques du graphe
        
        Returns:
            Statistiques (nombre de nœuds, relations, etc.)
        """
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Obtenir les statistiques complètes du graphe de connaissances
        
        Returns:
            Statistiques détaillées (nœuds, relations, types, etc.)
        """
        if not self.is_available():
            return {
                "total_nodes": 0,
                "total_relationships": 0,
                "nodes_by_type": {},
                "relationships_by_type": {},
                "neo4j_available": False,
                "error": "Neo4j service not available"
            }
            
        try:
            with self.driver.session() as session:
                # Compter les nœuds par type
                node_result = session.run(
                    """
                    MATCH (n:CodeNode)
                    RETURN n.type AS type, count(n) AS count
                    ORDER BY type
                    """
                )
                nodes_by_type = {record['type']: record['count'] for record in node_result}
                
                # Compter les relations par type
                rel_result = session.run(
                    """
                    MATCH ()-[r]->()
                    RETURN type(r) AS type, count(r) AS count
                    ORDER BY type
                    """
                )
                relationships_by_type = {record['type']: record['count'] for record in rel_result}
                
                # Totaux
                total_nodes = sum(nodes_by_type.values()) if nodes_by_type else 0
                total_rels = sum(relationships_by_type.values()) if relationships_by_type else 0
                
                # Statistiques additionnelles
                density_result = session.run(
                    """
                    MATCH (n:CodeNode)
                    OPTIONAL MATCH (n)-[r]->()
                    RETURN count(DISTINCT n) as nodes, count(r) as edges
                    """
                )
                density_record = density_result.single()
                
                return {
                    'total_nodes': total_nodes,
                    'total_relationships': total_rels,
                    'nodes_by_type': nodes_by_type,
                    'relationships_by_type': relationships_by_type,
                    'neo4j_available': True,
                    'neo4j_uri': self.uri,
                    'graph_density': {
                        'nodes': density_record['nodes'] if density_record else 0,
                        'edges': density_record['edges'] if density_record else 0,
                        'max_possible_edges': (density_record['nodes'] * (density_record['nodes'] - 1)) if density_record and density_record['nodes'] > 1 else 0
                    }
                }
                
        except Exception as e:
            logger.error(f"[ERREUR] get_statistics: {e}")
            return {
                "total_nodes": 0,
                "total_relationships": 0,
                "nodes_by_type": {},
                "relationships_by_type": {},
                "neo4j_available": False,
                "error": str(e)
            }
    
    
    async def traverse_from_file(
        self,
        file_id: str,
        max_depth: int = 3
    ) -> Dict[str, Any]:
        """
        Parcourir le graphe à partir d'un fichier
        
        Args:
            file_id: ID du fichier de départ
            max_depth: Profondeur maximale de traversée
            
        Returns:
            Arbre de dépendances
        """
        try:
            with self.driver.session() as session:
                result = session.run(
                    """
                    MATCH path = (start:CodeNode {id: $file_id})-[*0..%d]->(end:CodeNode)
                    RETURN path
                    LIMIT 100
                    """ % max_depth,
                    file_id=file_id
                )
                
                # Construire l'arbre à partir des chemins
                nodes_dict = {}
                
                for record in result:
                    path = record['path']
                    nodes = path.nodes
                    relationships = path.relationships
                    
                    for i, node in enumerate(nodes):
                        node_id = node['id']
                        if node_id not in nodes_dict:
                            nodes_dict[node_id] = {
                                'id': node_id,
                                'type': node.get('type'),
                                'name': node.get('name'),
                                'metadata': node.get('metadata', {}),
                                'children': []
                            }
                        
                        # Ajouter les relations
                        if i < len(relationships):
                            rel = relationships[i]
                            target_id = nodes[i + 1]['id']
                            nodes_dict[node_id]['children'].append({
                                'relationship': rel.type,
                                'node_id': target_id
                            })
                
                return nodes_dict.get(file_id, {})
                
        except Exception as e:
            logger.error(f"[ERREUR] traverse_from_file: {e}")
            return {}
