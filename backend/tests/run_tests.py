import urllib.request, json, time

tests = [
    ("T1-delete-equip", {"content": "quelle est la fonction qui permet de supprimer un equipement ?", "app_id": "brasil", "conversation_id": "audit-t1"}),
    ("T2-create-vlan", {"content": "quel service effectue la creation de VLAN ?", "app_id": "brasil", "conversation_id": "audit-t2"}),
    ("T3-java-delete-dslam", {"content": "quelle methode Java supprime un DSLAM ?", "app_id": "brasil", "conversation_id": "audit-t3"}),
    ("T4-exceptions-montre", {"content": "montre les exceptions detectees pour DSFEN104", "app_id": "brasil", "conversation_id": "audit-t4"}),
    ("T5-table-hallucination", {"content": "quelles tables contiennent les donnees DSLAM ?", "app_id": "brasil", "conversation_id": "audit-t5"}),
]

for name, body in tests:
    req = urllib.request.Request(
        "http://localhost:8000/api/v1/chatbot/chat",
        json.dumps(body).encode(),
        {"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read())
            msg = data.get("message", "")
            print(f"=== {name} ===")
            print(msg[:600])
            print(f"pipeline={data.get('pipeline_mode')} trust={data.get('trust_score')}")
            print()
    except Exception as e:
        print(f"{name} ERROR: {e}")
    time.sleep(2)
