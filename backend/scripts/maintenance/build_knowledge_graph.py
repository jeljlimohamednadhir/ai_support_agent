"""
Construction complète du graphe de connaissances Neo4j
Crée tous les nœuds et relations à partir des 3 sources : DB + Fiches + Jira
"""
import asyncio
import logging
import re
from typing import Dict, List, Set, Tuple
from qdrant_client import QdrantClient
from app.services.knowledge.manager import get_graph_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KnowledgeGraphBuilder:
    def __init__(self):
        self.qdrant_client = QdrantClient(host="localhost", port=6333)
        self.graph_service = get_graph_service()
        
        # Patterns pour extraire les entités
        self.table_pattern = r'\b((?:qd|rip|ora|aml|ano|ref|file|lv|i)_\w+)\b'
        self.ticket_pattern = r'\b(BRASIL-\d+)\b'
        self.fr_pattern = r'\b(FR[_-]?\d+)\b'
        
    async def build_complete_graph(self):
        """Construire le graphe complet à partir de Qdrant"""
        print("🏗️  Construction du graphe de connaissances BRASIL...")
        
        if not self.graph_service.is_available():
            print("❌ Neo4j non disponible")
            return
        
        # 1. Nettoyer le graphe existant
        await self.clear_graph()
        
        # 2. Récupérer toutes les données de Qdrant
        all_points = await self.fetch_all_qdrant_data()
        
        # 3. Créer les nœuds
        nodes_created = await self.create_nodes(all_points)
        
        # 4. Analyser et créer les relations
        relations_created = await self.create_relations(all_points)
        
        print(f"✅ Graphe construit : {nodes_created} nœuds, {relations_created} relations")
        
    async def clear_graph(self):
        """Nettoyer tous les nœuds existants"""
        print("🗑️  Nettoyage du graphe...")
        
        with self.graph_service.driver.session() as session:
            result = session.run("MATCH (n) DELETE n")
            print("   Nœuds supprimés")
    
    async def fetch_all_qdrant_data(self) -> List[Dict]:
        """Récupérer toutes les données de Qdrant"""
        print("📊 Récupération des données Qdrant...")
        
        all_points = []
        offset = None
        
        while True:
            try:
                result = self.qdrant_client.scroll(
                    collection_name="code_knowledge",
                    limit=100,
                    offset=offset,
                    with_payload=True
                )
                
                points, next_offset = result
                
                for point in points:
                    all_points.append({
                        'id': str(point.id),
                        'payload': point.payload
                    })
                
                if not next_offset:
                    break
                offset = next_offset
                
            except Exception as e:
                print(f"   ❌ Erreur lecture Qdrant: {e}")
                break
        
        print(f"   📄 {len(all_points)} documents récupérés")
        return all_points
    
    async def create_nodes(self, all_points: List[Dict]) -> int:
        """Créer tous les nœuds dans Neo4j"""
        print("🔘 Création des nœuds...")
        
        nodes_created = 0
        
        for point in all_points:
            payload = point['payload']
            doc_type = payload.get('type', 'unknown')
            
            try:
                if doc_type == 'database_table':
                    await self.create_table_node(point)
                elif doc_type == 'resolution_fiche':
                    await self.create_fiche_node(point)
                elif doc_type == 'jira_ticket':
                    await self.create_ticket_node(point)
                else:
                    await self.create_generic_node(point)
                
                nodes_created += 1
                
            except Exception as e:
                logger.warning(f"Erreur création nœud {payload.get('name', 'unknown')}: {e}")
        
        print(f"   ✅ {nodes_created} nœuds créés")
        return nodes_created
    
    async def create_table_node(self, point: Dict):
        """Créer nœud table DB"""
        payload = point['payload']
        
        await self.graph_service.add_code_node(
            node_id=f"table_{payload.get('table_name')}",
            node_type="database_table",
            name=payload.get('table_name', 'unknown'),
            content=payload.get('code', ''),
            metadata={
                'schema': payload.get('schema_name', 'public'),
                'column_count': payload.get('column_count', 0),
                'description': payload.get('description', ''),
                'source': 'database'
            }
        )
    
    async def create_fiche_node(self, point: Dict):
        """Créer nœud fiche de résolution"""
        payload = point['payload']
        
        await self.graph_service.add_code_node(
            node_id=f"fiche_{payload.get('fr_number', 'unknown')}",
            node_type="resolution_fiche",
            name=payload.get('fr_number', 'unknown'),
            content=payload.get('code', ''),
            metadata={
                'title': payload.get('title', ''),
                'filename': payload.get('filename', ''),
                'category': payload.get('category', ''),
                'source': 'documentation'
            }
        )
    
    async def create_ticket_node(self, point: Dict):
        """Créer nœud ticket Jira"""
        payload = point['payload']
        
        await self.graph_service.add_code_node(
            node_id=f"ticket_{payload.get('ticket_key')}",
            node_type="jira_ticket", 
            name=payload.get('ticket_key', 'unknown'),
            content=payload.get('content', ''),
            metadata={
                'status': payload.get('status', ''),
                'priority': payload.get('priority', ''),
                'project': payload.get('project_key', ''),
                'assignee': payload.get('assignee', ''),
                'created': payload.get('created', ''),
                'source': 'jira'
            }
        )
    
    async def create_generic_node(self, point: Dict):
        """Créer nœud générique"""
        payload = point['payload']
        
        await self.graph_service.add_code_node(
            node_id=f"doc_{point['id']}",
            node_type="document",
            name=payload.get('name', f"doc_{point['id']}"),
            content=payload.get('code', payload.get('content', '')),
            metadata=payload
        )
    
    async def create_relations(self, all_points: List[Dict]) -> int:
        """Analyser le contenu et créer les relations"""
        print("🔗 Analyse des corrélations et création des relations...")
        
        relations_created = 0
        
        # Construire un index des entités
        entity_index = self.build_entity_index(all_points)
        
        # Pour chaque document, chercher les mentions d'autres entités
        for point in all_points:
            payload = point['payload']
            content = payload.get('content', payload.get('code', ''))
            doc_type = payload.get('type', 'unknown')
            
            # Identifier l'entité source
            source_id = self.get_node_id(payload, doc_type)
            if not source_id:
                continue
            
            # Chercher les entités mentionnées dans le contenu
            mentioned_entities = self.extract_mentioned_entities(content, entity_index)
            
            # Créer les relations
            for target_entity, target_type in mentioned_entities:
                target_id = f"{target_type}_{target_entity}"
                
                try:
                    await self.create_relationship(source_id, target_id, doc_type, target_type)
                    relations_created += 1
                except Exception as e:
                    logger.debug(f"Relation ignorée {source_id} -> {target_id}: {e}")
        
        print(f"   ✅ {relations_created} relations créées")
        return relations_created
    
    def build_entity_index(self, all_points: List[Dict]) -> Dict[str, str]:
        """Construire un index entité -> type"""
        entity_index = {}
        
        for point in all_points:
            payload = point['payload']
            doc_type = payload.get('type', 'unknown')
            
            if doc_type == 'database_table':
                entity_index[payload.get('table_name', '')] = 'table'
            elif doc_type == 'resolution_fiche':
                entity_index[payload.get('fr_number', '')] = 'fiche'
            elif doc_type == 'jira_ticket':
                entity_index[payload.get('ticket_key', '')] = 'ticket'
        
        return entity_index
    
    def get_node_id(self, payload: Dict, doc_type: str) -> str:
        """Obtenir l'ID du nœud"""
        if doc_type == 'database_table':
            return f"table_{payload.get('table_name')}"
        elif doc_type == 'resolution_fiche':
            return f"fiche_{payload.get('fr_number')}"
        elif doc_type == 'jira_ticket':
            return f"ticket_{payload.get('ticket_key')}"
        else:
            return f"doc_{payload.get('name', 'unknown')}"
    
    def extract_mentioned_entities(self, content: str, entity_index: Dict[str, str]) -> List[Tuple[str, str]]:
        """Extraire les entités mentionnées dans le contenu"""
        mentioned = []
        content_lower = content.lower()
        
        # Chercher chaque entité connue dans le contenu
        for entity_name, entity_type in entity_index.items():
            if entity_name and entity_name.lower() in content_lower:
                mentioned.append((entity_name, entity_type))
        
        return mentioned
    
    async def create_relationship(self, from_id: str, to_id: str, from_type: str, to_type: str):
        """Créer une relation dans Neo4j"""
        
        # Déterminer le type de relation
        rel_type = self.determine_relationship_type(from_type, to_type)
        
        cypher_query = f"""
        MATCH (a:CodeNode {{id: $from_id}})
        MATCH (b:CodeNode {{id: $to_id}})
        CREATE (a)-[:{rel_type}]->(b)
        """
        
        with self.graph_service.driver.session() as session:
            session.run(cypher_query, from_id=from_id, to_id=to_id)
    
    def determine_relationship_type(self, from_type: str, to_type: str) -> str:
        """Déterminer le type de relation approprié"""
        
        relation_map = {
            ('jira_ticket', 'database_table'): 'AFFECTS_TABLE',
            ('jira_ticket', 'resolution_fiche'): 'RESOLVED_BY',
            ('resolution_fiche', 'database_table'): 'DOCUMENTS_TABLE',
            ('database_table', 'jira_ticket'): 'HAS_INCIDENT', 
            ('resolution_fiche', 'jira_ticket'): 'RESOLVES',
            ('database_table', 'resolution_fiche'): 'DOCUMENTED_BY'
        }
        
        return relation_map.get((from_type, to_type), 'RELATES_TO')

async def main():
    """Point d'entrée principal"""
    builder = KnowledgeGraphBuilder()
    await builder.build_complete_graph()
    
    print("\n🎯 Le graphe de connaissances est maintenant prêt !")
    print("   - Utilisez le chatbot pour des questions complexes")
    print("   - Les corrélations seront automatiquement détectées")

if __name__ == "__main__":
    asyncio.run(main())