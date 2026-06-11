"""Test ultra-rapide"""
import asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

async def main():
    from app.core.llm_client import llm_client
    print("Test Groq...")
    r = await llm_client.generate("Dis juste 'OK'", temperature=0)
    print(f"✅ Groq fonctionne! Réponse: {r[:50]}")

asyncio.run(main())
