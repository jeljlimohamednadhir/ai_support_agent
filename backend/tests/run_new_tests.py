import urllib.request, json, time

tests = [
    ("T-workflow", {"content": "comment supprimer un DSLAM dans BRASIL ?", "app_id": "brasil", "conversation_id": "audit-wf1"}),
    ("T-sql-mutation", {"content": "voici une requete DELETE FROM t_equipments WHERE id=1", "app_id": "brasil", "conversation_id": "audit-sql1"}),
    ("T-provenance", {"content": "depuis quels logs viennent ces informations ?", "app_id": "brasil", "conversation_id": "audit-prov1"}),
    ("T-create-vlan-workflow", {"content": "comment creer un VLAN etape par etape ?", "app_id": "brasil", "conversation_id": "audit-wf2"}),
]

for name, body in tests:
    req = urllib.request.Request(
        "http://localhost:8000/api/v1/chatbot/chat",
        json.dumps(body).encode(),
        {"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
            msg = data.get("message", "")
            pipe = data.get("pipeline_mode", "")
            trust = data.get("trust_score", 0)
            print(f"=== {name} ===")
            print(msg[:600])
            print(f"pipeline={pipe} trust={trust}")
            print()
    except Exception as e:
        print(f"{name} ERROR: {e}")
    time.sleep(2)
