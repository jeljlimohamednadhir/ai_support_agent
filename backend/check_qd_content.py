#!/usr/bin/env python3
"""Vérifier le contenu de qd_anomalie après réinjection."""

from qdrant_client import QdrantClient

client = QdrantClient(host='localhost', port=6333)

# Rechercher qd_anomalie par metadata
results = client.scroll(
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

if results[0]:
    point = results[0][0]
    print('📄 Contenu de qd_anomalie dans Qdrant:')
    print(f'ID: {point.id}')
    print(f'Name: {point.payload.get("name")}')
    print(f'Table Name: {point.payload.get("table_name")}')
    print(f'Colonnes: {point.payload.get("column_count")}')
    print(f'\n=== CODE ===')
    print(point.payload.get('code'))
else:
    print('❌ Table qd_anomalie non trouvée')
