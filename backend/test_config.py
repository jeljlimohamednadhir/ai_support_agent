"""
Script de test pour vérifier la configuration
"""
import asyncio
import os
from pathlib import Path

# Ajouter le répertoire parent au path
import sys
sys.path.insert(0, str(Path(__file__).parent))

async def test_groq_connection():
    """Test de connexion Groq"""
    print("\n🧪 Test 1: Connexion Groq API")
    print("=" * 50)
    
    try:
        from app.core.config import settings
        print(f"✅ Configuration chargée")
        print(f"   Provider: {settings.LLM_PROVIDER}")
        print(f"   Model: {settings.GROQ_MODEL}")
        print(f"   API Key: {'✅ Configurée' if settings.GROQ_API_KEY else '❌ Manquante'}")
        
        if not settings.GROQ_API_KEY:
            print("❌ GROQ_API_KEY non trouvée dans .env")
            return False
        
        from app.core.llm_client import llm_client
        
        # Test simple
        print("\n📤 Envoi d'un message test...")
        response = await llm_client.generate(
            prompt="Dis simplement 'Bonjour' en français",
            temperature=0.1
        )
        
        print(f"✅ Réponse reçue: {response[:100]}...")
        return True
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_database_models():
    """Test des modèles SQLAlchemy"""
    print("\n🧪 Test 2: Modèles de base de données")
    print("=" * 50)
    
    try:
        from app.models import (
            Conversation, Message, MessageFeedback,
            CollectionJob, ValidationTask, Correction
        )
        print("✅ Tous les modèles importés avec succès")
        print(f"   - Conversation")
        print(f"   - Message")
        print(f"   - MessageFeedback")
        print(f"   - CollectionJob")
        print(f"   - ValidationTask")
        print(f"   - Correction")
        return True
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_chatbot_service():
    """Test du service chatbot"""
    print("\n🧪 Test 3: Service Chatbot")
    print("=" * 50)
    
    try:
        from app.services.chatbot.chatbot_service import ChatbotService
        from app.schemas.chatbot import ChatMessage
        
        chatbot = ChatbotService()
        print("✅ ChatbotService initialisé")
        
        # Test d'un message
        print("\n📤 Envoi d'une question test...")
        message = ChatMessage(
            message="Explique-moi en une phrase ce qu'est un API REST",
            user_id="test_user"
        )
        
        response = await chatbot.process_message(message)
        
        print(f"✅ Réponse reçue:")
        print(f"   Message: {response.message[:150]}...")
        print(f"   Conversation ID: {response.conversation_id}")
        print(f"   Confidence: {response.confidence}")
        print(f"   Suggestions: {len(response.suggestions)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Exécute tous les tests"""
    print("\n" + "=" * 50)
    print("🚀 TESTS DE CONFIGURATION AI SUPPORT AGENT")
    print("=" * 50)
    
    results = []
    
    # Test 1: Groq
    results.append(await test_groq_connection())
    
    # Test 2: Models
    results.append(await test_database_models())
    
    # Test 3: Chatbot (nécessite Groq)
    if results[0]:
        results.append(await test_chatbot_service())
    else:
        print("\n⏭️  Test 3 sauté (Groq non disponible)")
        results.append(False)
    
    # Résumé
    print("\n" + "=" * 50)
    print("📊 RÉSUMÉ DES TESTS")
    print("=" * 50)
    print(f"✅ Tests réussis: {sum(results)}/{len(results)}")
    print(f"❌ Tests échoués: {len(results) - sum(results)}/{len(results)}")
    
    if all(results):
        print("\n🎉 TOUS LES TESTS SONT PASSÉS!")
        print("   Vous pouvez maintenant lancer: podman-compose up -d")
        print("   Ou avec le script: .\\podman.ps1 up -Detached")
    else:
        print("\n⚠️  Certains tests ont échoué")
        print("   Vérifiez les erreurs ci-dessus")
    
    return all(results)


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
