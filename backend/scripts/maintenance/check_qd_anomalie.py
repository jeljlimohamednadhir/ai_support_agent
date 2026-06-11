#!/usr/bin/env python3
"""Vérifier le contenu de qd_anomalie dans Qdrant."""

from qdrant_client import QdrantClient

client = QdrantClient(host='localhost', port=6333)
results = client.retrieve(
    collection_name='code_knowledge',
    ids=['08c09929-c8eb-4753-ada7-4d31f36dfb0e']
)

if results:
    point = results[0]
    print('📄 Contenu de la table qd_anomalie dans Qdrant:')
    print(f'ID: {point.id}')
    print(f'Name: {point.payload.get("name")}')
    print(f'Table Name: {point.payload.get("table_name")}')
    print(f'Type: {point.payload.get("type")}')
    print(f'File Path: {point.payload.get("file_path")}')
    print(f'\nCode (full):')
    print(point.payload.get('code', 'N/A'))
    print(f'\n\n=== TEST DE RECHERCHE VECTORIELLE ===')
    
# Test de recherche avec le nom exact
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

queries = [
    "table qd_anomalie",
    "qd_anomalie",
    "Qu'est-ce que la table qd_anomalie?",
    "anomalie"
]

for query in queries:
    print(f'\n🔍 Query: "{query}"')
    embedding = model.encode(query).tolist()
    
    results = client.query_points(
        collection_name='code_knowledge',
        query=embedding,
        limit=5
    )
    
    print(f'   Top 5 résultats:')
    for i, point in enumerate(results.points, 1):
        name = point.payload.get('name', 'N/A')
        distance = point.score
        print(f'   {i}. {name} (score: {distance:.4f})')
