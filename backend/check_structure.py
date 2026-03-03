#!/usr/bin/env python3
from qdrant_client import QdrantClient

client = QdrantClient(host='localhost', port=6333)
result = client.scroll(
    collection_name='code_knowledge',
    limit=5,
    with_payload=True
)

print('=== STRUCTURE DES POINTS ===')
for i, point in enumerate(result[0][:5], 1):
    print(f'\n{i}. Point ID: {point.id}')
    print(f'   Payload keys: {list(point.payload.keys())}')
    
    # Chercher type
    if 'type' in point.payload:
        print(f'   ✅ Type direct: {point.payload["type"]}')
    
    if 'metadata' in point.payload:
        print(f'   Metadata keys: {list(point.payload["metadata"].keys())[:5]}...')
        if 'type' in point.payload['metadata']:
            print(f'   ✅ Type dans metadata: {point.payload["metadata"]["type"]}')
