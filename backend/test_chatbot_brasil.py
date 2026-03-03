"""
Script de test du chatbot BRASIL avec corrélation FR + Tables
"""
import asyncio
from app.services.chatbot.chatbot_service import ChatbotService
from app.schemas.chatbot import ChatMessage


async def test_chatbot():
    print("🤖 Initialisation du chatbot BRASIL...")
    service = ChatbotService()
    
    # Test 1: Erreur BRASIL avec corrélation attendue
    print("\n" + "=" * 80)
    print("TEST 1: Comment résoudre l'erreur BRASIL 1002 ?")
    print("=" * 80)
    
    msg = ChatMessage(content="Comment résoudre l'erreur BRASIL 1002 ?")
    response = await service.process_message(msg)
    
    print("\n📝 RÉPONSE:")
    print(response.message)
    
    print("\n📚 SOURCES:")
    for src in response.sources:
        print(f"  • {src['name']} (pertinence: {src['relevance']:.2%})")
    
    # Test 2: Question sur une table
    print("\n\n" + "=" * 80)
    print("TEST 2: Qu'est-ce que la table t_ports ?")
    print("=" * 80)
    
    msg2 = ChatMessage(content="Qu'est-ce que la table t_ports ?")
    response2 = await service.process_message(msg2)
    
    print("\n📝 RÉPONSE:")
    print(response2.message)
    
    print("\n📚 SOURCES:")
    for src in response2.sources:
        print(f"  • {src['name']} (pertinence: {src['relevance']:.2%})")
    
    # Test 3: Question mixte avec corrélation attendue
    print("\n\n" + "=" * 80)
    print("TEST 3: Quelles tables sont concernées par les problèmes de compteurs DSLAM ?")
    print("=" * 80)
    
    msg3 = ChatMessage(content="Quelles tables sont concernées par les problèmes de compteurs DSLAM ?")
    response3 = await service.process_message(msg3)
    
    print("\n📝 RÉPONSE:")
    print(response3.message)
    
    print("\n📚 SOURCES:")
    for src in response3.sources:
        print(f"  • {src['name']} (pertinence: {src['relevance']:.2%})")


if __name__ == "__main__":
    asyncio.run(test_chatbot())
