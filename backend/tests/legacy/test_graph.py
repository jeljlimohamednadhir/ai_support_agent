#!/usr/bin/env python3
"""
Test script pour vérifier le graphe Neo4j
"""
import asyncio
from neo4j import GraphDatabase
from app.services.knowledge.graph_service import GraphService

def test_direct_neo4j():
    """Test direct de Neo4j"""
    print("=== TEST DIRECT NEO4J ===")
    
    driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'password'))
    
    try:
        with driver.session() as session:
            # Compter tous les nœuds
            result = session.run('MATCH (n) RETURN count(n) as total')
            total = result.single()['total'] if result.single() else 0
            print(f'Total nœuds dans Neo4j: {total}')
            
            # Compter par label
            result = session.run('MATCH (n) RETURN DISTINCT labels(n) as labels, count(n) as count')
            for record in result:
                labels = record['labels']
                count = record['count']
                print(f'Labels {labels}: {count}')
                
            # Échantillon de nœuds
            if total > 0:
                result = session.run('MATCH (n) RETURN n LIMIT 5')
                print('\nÉchantillon de nœuds:')
                for i, record in enumerate(result):
                    node = record['n']
                    node_id = node.get('id', 'N/A')
                    node_type = node.get('type', 'N/A')
                    node_name = node.get('name', 'N/A')[:50] + '...' if node.get('name') else 'N/A'
                    labels = list(node.labels)
                    print(f'{i+1}. ID: {node_id}')
                    print(f'   Type: {node_type}')
                    print(f'   Name: {node_name}')
                    print(f'   Labels: {labels}')
                    print()
                    
    except Exception as e:
        print(f'Erreur Neo4j direct: {e}')
    finally:
        driver.close()

async def test_graph_service():
    """Test via GraphService"""
    print("=== TEST GRAPH SERVICE ===")
    
    try:
        graph = GraphService()
        
        if not graph.is_available():
            print("GraphService non disponible")
            return
            
        stats = await graph.get_statistics()
        print("Statistiques GraphService:")
        for key, value in stats.items():
            print(f'  {key}: {value}')
        
        # Test recherche de corrélations
        print("\n=== TEST CORRÉLATIONS ===")
        test_terms = ['BRASIL', 'database', 'FR', 'table']
        
        for term in test_terms:
            correlations = await graph.find_correlations(term, max_depth=2)
            print(f'Corrélations pour "{term}": {len(correlations)}')
            
            if correlations:
                for i, corr in enumerate(correlations[:2]):
                    start_type = corr['start']['type']
                    related_type = corr['related']['type']
                    relations = corr.get('relationship_types', [])
                    print(f'  {i+1}. {start_type} -> {related_type}')
                    print(f'     Relations: {relations}')
            print()
                    
    except Exception as e:
        print(f'Erreur GraphService: {e}')

if __name__ == "__main__":
    test_direct_neo4j()
    print("\n" + "="*50 + "\n")
    asyncio.run(test_graph_service())