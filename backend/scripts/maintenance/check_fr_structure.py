from qdrant_client import QdrantClient
c = QdrantClient(host='localhost', port=6333)

res, _ = c.scroll('brasil_frs', limit=200, with_payload=True)

missing_structure = []
ok = []

for p in res:
    pay = p.payload
    has_resolution = bool(pay.get('resolution_steps'))
    has_diagnostic = bool(pay.get('diagnostic_steps'))
    has_triggers   = bool(pay.get('trigger_signals'))
    fr_type        = pay.get('type', '?')
    title          = pay.get('title', pay.get('id', '?'))[:55]

    if not has_resolution and not has_diagnostic:
        missing_structure.append((pay.get('id','?'), title, fr_type))
    else:
        ok.append((pay.get('id','?'), title))

print(f"=== FRs SANS resolution_steps ET diagnostic_steps ({len(missing_structure)}) ===")
for fr_id, title, t in missing_structure:
    print(f"  [{t}] {fr_id:<40} {title}")

print(f"\n=== FRs CORRECTEMENT STRUCTUREES ({len(ok)}) ===")
for fr_id, title in ok:
    print(f"  {fr_id:<40} {title}")
