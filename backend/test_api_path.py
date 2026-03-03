import asyncio
from app.services.collector.orchestrator import CollectorOrchestrator

repo_url = "c:/Users/n.jeljli/OneDrive - orange.com/Bureau/Genergy_IA/test-repo-example"

try:
    orchestrator = CollectorOrchestrator()
    result = asyncio.run(orchestrator.start_code_collection(repo_url, 'master'))
    print(f"[OK] Fichiers: {result.get('artifacts_count')}")
    print(f"Langages: {result.get('statistics', {}).get('languages', {})}")
except Exception as e:
    import traceback
    print(f"[ERREUR] {e}")
    traceback.print_exc()
