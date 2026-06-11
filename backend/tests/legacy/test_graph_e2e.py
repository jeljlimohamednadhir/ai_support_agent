import requests, json

BASE = "http://localhost:8000/api/v1"

r = requests.post(f"{BASE}/auth/login", data={"username": "admin", "password": "admin123"})
print(f"Auth: {r.status_code}")
token = r.json().get("access_token", "")
H = {"Authorization": f"Bearer {token}"}

def chat(msg, conv_id):
    r = requests.post(f"{BASE}/chatbot/chat",
        json={"content": msg, "conversation_id": conv_id},
        headers=H, timeout=360)
    data = r.json()
    print(f"\n{'='*60}")
    print(f"Q: {msg}")
    print(f"Status: {r.status_code} | trust={data.get('trust_score','?')} | exc={data.get('exceptions_detected','?')}")
    print(data.get("message","")[:600])
    fup = data.get("follow_up_message","")
    if fup:
        print("--- follow_up ---")
        print(fup[:500])

chat("impossible de supprimer le dslam op49mdb11, operation bloquee", "e2e-1")
chat("montre moi la methode bloquante dans le code source", "e2e-1")
chat("d ou vient cette exception dans le code java", "e2e-1")
