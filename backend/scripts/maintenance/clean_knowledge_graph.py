#!/usr/bin/env python3
"""
Script pour nettoyer toutes les données du Knowledge Graph
Supprime les collections Qdrant et les données Neo4j
"""
from qdrant_client import QdrantClient
from neo4j import GraphDatabase

print("=" * 70)
print("🗑️  NETTOYAGE DU KNOWLEDGE GRAPH")
print("=" * 70)

# 1. Nettoyer Qdrant
print("\n📦 Connexion à Qdrant...")
try:
    qdrant_client = QdrantClient(host='localhost', port=6333)
    
    # Lister toutes les collections
    collections = qdrant_client.get_collections()
    
    if collections.collections:
        print(f"✅ Trouvé {len(collections.collections)} collection(s)")
        
        for collection in collections.collections:
            collection_name = collection.name
            print(f"\n   🗑️  Suppression de '{collection_name}'...")
            qdrant_client.delete_collection(collection_name)
            print(f"   ✅ Collection '{collection_name}' supprimée")
    else:
        print("ℹ️  Aucune collection trouvée dans Qdrant")
        
except Exception as e:
    print(f"❌ Erreur Qdrant: {e}")

# 2. Nettoyer Neo4j
print("\n\n📊 Connexion à Neo4j...")
try:
    neo4j_driver = GraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("neo4j", "password123")
    )
    
    with neo4j_driver.session() as session:
        # Compter les nœuds avant suppression
        result = session.run("MATCH (n) RETURN count(n) as count")
        count_before = result.single()["count"]
        print(f"✅ Trouvé {count_before} nœud(s)")
        
        if count_before > 0:
            print(f"\n   🗑️  Suppression de tous les nœuds et relations...")
            session.run("MATCH (n) DETACH DELETE n")
            
            # Vérifier après suppression
            result = session.run("MATCH (n) RETURN count(n) as count")
            count_after = result.single()["count"]
            print(f"   ✅ {count_before} nœud(s) supprimé(s)")
            print(f"   ℹ️  {count_after} nœud(s) restant(s)")
        else:
            print("ℹ️  Aucun nœud trouvé dans Neo4j")
    
    neo4j_driver.close()
    
except Exception as e:
    print(f"❌ Erreur Neo4j: {e}")

print("\n" + "=" * 70)
print("✅ NETTOYAGE TERMINÉ")
print("=" * 70)
print("\nLe Knowledge Graph est maintenant vide et prêt pour un nouvel exemple.")
