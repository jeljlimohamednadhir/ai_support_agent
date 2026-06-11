"""
Test rapide de Groq
"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

async def main():
    print("🧪 Test Groq simple\n")
    
    # Test 1: Config
    from app.core.config import settings
    print(f"✅ Config OK - Provider: {settings.LLM_PROVIDER}")
    
    # Test 2: Client
    from app.core.llm_client import llm_client
    print(f"✅ Client LLM initialisé")
    
    # Test 3: Appel simple
    print("\n📤 Test d'appel Groq...")
    response = await llm_client.generate(
        prompt="Réponds en un mot: quelle est la capitale de la France ?",
        temperature=0.1
    )
    print(f"✅ Réponse: {response}\n")
    
    # Test 4: Chatbot
    from app.services.chatbot.chatbot_service import ChatbotService
    from app.schemas.chatbot import ChatMessage
    
    chatbot = ChatbotService()
    message = ChatMessage(message="Bonjour, c'est un test", user_id="test")
    result = await chatbot.process_message(message)
    print(f"✅ Chatbot OK - Conv ID: {result.conversation_id}")
    print(f"   Réponse: {result.message[:80]}...")
    
    print("\n🎉 TOUS LES TESTS PASSENT!")

if __name__ == "__main__":
    asyncio.run(main())
