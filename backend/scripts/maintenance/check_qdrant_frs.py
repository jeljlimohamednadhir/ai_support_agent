from qdrant_client import QdrantClient
c = QdrantClient(host='localhost', port=6333)
info = c.get_collection('brasil_frs')
print(f'Points dans brasil_frs: {info.points_count}')
res, _ = c.scroll('brasil_frs', limit=200, with_payload=['id','title','type'])
qdrant_ids = set()
for p in res:
    fr_id = p.payload.get('id','')
    qdrant_ids.add(fr_id)
    print(f"  {fr_id:<40} {p.payload.get('title','')[:50]}")

print(f'\nTotal Qdrant: {len(qdrant_ids)}')
