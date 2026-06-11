#!/usr/bin/env python3
"""
Test du chatbot avec le système de corrélations amélioré
"""
import asyncio
from app.services.chatbot.chatbot_service import ChatbotService
from app.schemas.chatbot import ChatMessage

async def test_chatbot_correlations():
    """Test du chatbot avec questions sur les corrélations"""
    
    print("=" * 80)
    print("TEST DU CHATBOT AVEC SYSTÈME DE CORRÉLATIONS")
    print("=" * 80)
    
    chatbot = ChatbotService()
    
    # Liste de questions de test
    test_questions = [
        "Quels sont les problèmes liés à BRASIL dans les fiches de résolution?",
        "Quelles tables de base de données sont concernées par les erreurs de port?",
        "Y a-t-il des corrélations entre les tables t_ports et les fiches FR?",
        "Comment résoudre un problème d'affectation sur CCL VC déjà occupé?"
    ]
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n{'='*80}")
        print(f"QUESTION {i}: {question}")
        print(f"{'='*80}\n")
        
        try:
            # Créer le message
            message = ChatMessage(content=question, role="user")
            
            # Obtenir la réponse
            response = await chatbot.process_message(message)
            
            # Extraire le texte de la réponse
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Afficher la réponse (premiers 1000 caractères)
            print("RÉPONSE:")
            print("-" * 80)
            if len(response_text) > 1000:
                print(response_text[:1000] + f"\n\n[...Réponse tronquée - {len(response_text)} caractères au total...]")
            else:
                print(response_text)
            print("-" * 80)
            
        except Exception as e:
            print(f"❌ ERREUR lors du traitement de la question: {e}")
            import traceback
            traceback.print_exc()
        
        # Petit délai entre les questions
        await asyncio.sleep(1)
    
    print(f"\n{'='*80}")
    print("TEST TERMINÉ")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_chatbot_correlations())