"""
Script de test du RAG - vérifier si la recherche vectorielle fonctionne
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.services.knowledge.vector_service import VectorService

async def test_rag():
    print("=" * 70)
    print("🔍 TEST DU RAG (Recherche Vectorielle)")
    print("=" * 70)
    
    # Initialiser le service
    print("\n📦 Initialisation du VectorService...")
    vector_service = VectorService()
    
    if not vector_service.is_available():
        print("❌ Qdrant non disponible!")
        return
    
    print("✅ Qdrant connecté")
    
    # Test 1: Vérifier le nombre de documents
    print("\n📊 Vérification du contenu de Qdrant...")
    try:
        collection_info = vector_service.client.get_collection("code_knowledge")
        print(f"✅ Collection 'code_knowledge' contient {collection_info.points_count} documents")
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return
    
    # Test 2: Recherche vectorielle
    test_queries = [
        "Comment fonctionne l'authentification ?",
        "Quelles sont les règles pour créer une commande ?",
        "Que se passe-t-il lors d'un paiement ?",
        "admin non vérifié",
        "User model"
    ]
    
    print("\n🔎 Test de recherches vectorielles...")
    for query in test_queries:
        print(f"\n📝 Query: '{query}'")
        results = await vector_service.search_similar_code(query, top_k=3)
        
        if results:
            print(f"   ✅ Trouvé {len(results)} résultats:")
            for i, result in enumerate(results, 1):
                print(f"      {i}. {result['metadata'].get('name', 'Sans nom')}")
                print(f"         Distance: {result['distance']:.4f}")
                print(f"         File: {result['metadata'].get('file_path', 'N/A')}")
        else:
            print("   ❌ Aucun résultat trouvé")
    
    print("\n" + "=" * 70)
    print("✅ Test terminé")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_rag())
