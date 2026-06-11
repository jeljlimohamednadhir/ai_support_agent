import asyncio
import traceback
from app.services.collector.orchestrator import CollectorOrchestrator

repo_path = r'c:\Users\n.jeljli\OneDrive - orange.com\Bureau\Genergy_IA\test-repo-example'
try:
    result = asyncio.run(CollectorOrchestrator().start_code_collection(repo_path, 'master'))
    print("[OK] Collection reussie!")
    print(f"Fichiers: {result.get('artifacts_count', 0)}")
    print(f"Langages: {result.get('statistics', {}).get('languages', {})}")
except Exception as e:
    print(f"[ERREUR] {e}")
    traceback.print_exc()
