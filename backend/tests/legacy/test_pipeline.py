"""
Diagnostic complet : KB Qdrant + Live Diagnostics + API chat
"""
import asyncio
import httpx
import json
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

BASE = "http://localhost:8000/api/v1"

async def test_api():
    async with httpx.AsyncClient(timeout=60) as c:
        # Login
        r = await c.post(f"{BASE}/auth/login",
                         data={"username": "admin", "password": "admin123"})
        print(f"Login: {r.status_code}")
        if r.status_code != 200:
            print(r.text[:200])
            return
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Test chat queries
        queries = [
            ("brasil", "Suppression equipement DSROB362 impossible"),
            ("brasil", "Suppression VLAN impossible"),
            ("brasil", "MAJ CODE OPERATEUR UPD_ICC_OPE"),
        ]
        for app_id, msg in queries:
            print(f"\n{'='*60}")
            print(f"Query: {msg}")
            r2 = await c.post(f"{BASE}/chatbot/chat",
                              headers=headers,
                              json={"content": msg, "app_id": app_id, "conversation_id": None})
            print(f"Status: {r2.status_code}")
            if r2.status_code == 200:
                data = r2.json()
                resp = data.get("response") or data.get("message") or str(data)
                print(f"Response (200c): {resp[:300]}")
                print(f"Trust: {data.get('trust_score')}")
                sources = data.get("sources", [])
                if sources:
                    print(f"Sources: {[s.get('title','?') for s in sources[:3]]}")
            else:
                print(r2.text[:300])


def test_qdrant():
    """Test direct Qdrant retrieval"""
    from app.core.config import settings
    try:
        from qdrant_client import QdrantClient
        qc = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
        collections = [c.name for c in qc.get_collections().collections]
        print(f"\nQdrant collections: {collections}")
        for col in collections:
            info = qc.get_collection(col)
            print(f"  {col}: {info.points_count} points")
    except Exception as e:
        print(f"Qdrant error: {e}")


def test_live_diag():
    """Test live diagnostics pipeline"""
    from app.services.live_diagnostics import create_orchestrator_from_settings
    orch = create_orchestrator_from_settings()
    if not orch:
        print("\nLive diagnostics: DISABLED (SSH_ENABLED=false)")
        return
    print("\nLive diagnostics: ENABLED")
    bundle = orch.run(intent="delete_equipment", entity="DSROB362")
    blocks = bundle.to_context_blocks() if bundle else []
    print(f"  Bundle evidences: {len(bundle.evidences) if bundle else 0}")
    print(f"  Context blocks: {len(blocks)}")
    if blocks:
        for b in blocks[:2]:
            content = b.get('content', str(b)) if isinstance(b, dict) else str(b)
            print(f"  Block: {content[:200]}")
    elif bundle:
        print(f"  DB evidences: {[e.query_name for e in bundle.evidences if hasattr(e,'query_name')]}")
        print(f"  Errors: {[e.error for e in bundle.evidences if hasattr(e,'error') and e.error]}")


if __name__ == "__main__":
    test_qdrant()
    test_live_diag()
    print("\n" + "="*60)
    print("API CHAT TEST")
    asyncio.run(test_api())
