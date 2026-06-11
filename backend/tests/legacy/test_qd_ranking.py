#!/usr/bin/env python3
"""Test direct de recherche qd_anomalie."""

from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

client = QdrantClient(host='localhost', port=6333)
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

query = "Qu'est-ce que la table qd_anomalie?"
print(f'🔍 Query: "{query}"\n')

# Générer l'embedding
embedding = model.encode(query).tolist()

# Rechercher les 10 premiers résultats
results = client.query_points(
    collection_name='code_knowledge',
    query=embedding,
    limit=10
)

print(f'Top 10 résultats:')
for i, point in enumerate(results.points, 1):
    name = point.payload.get('name', 'N/A')
    table_name = point.payload.get('table_name', 'N/A')
    score = point.score
    
    # Vérifier si c'est qd_anomalie
    is_target = '✅' if table_name == 'qd_anomalie' else '  '
    
    print(f'{is_target} {i}. {name} (table_name={table_name}, score={score:.4f})')

print('\n' + '='*70)
print('Recherche par filtre exact:')

# Recherche directe par table_name
direct_results = client.scroll(
    collection_name='code_knowledge',
    scroll_filter={
        'must': [
            {
                'key': 'table_name',
                'match': {
                    'value': 'qd_anomalie'
                }
            }
        ]
    },
    limit=1
)

if direct_results[0]:
    point = direct_results[0][0]
    print(f'\n✅ Table qd_anomalie trouvée directement:')
    print(f'   ID: {point.id}')
    print(f'   Name: {point.payload.get("name")}')
    print(f'   Colonnes: {point.payload.get("column_count")}')
    print(f'\n   Code:\n{point.payload.get("code")[:300]}...')
