#!/usr/bin/env python3
import asyncio
from app.services.chatbot.chatbot_service import ChatbotService
from app.schemas.chatbot import ChatMessage

async def test():
    print("Initialisation du chatbot...")
    chatbot = ChatbotService()
    
    # Test des questions de type liste
    questions = [
        "Cite-moi les 5 derniers tickets Jira",
        "Liste les 3 dernières fiches de résolution",
        "Montre-moi les 10 derniers tickets Jira par date",
        "Affiche toutes les tables de la base de données"
    ]
    
    for question in questions:
        print("\n" + "="*80)
        print(f"QUESTION: {question}")
        print("="*80)
        
        message = ChatMessage(content=question, role='user')
        response = await chatbot.process_message(message)
        
        print(response.message if hasattr(response, 'message') else str(response))

asyncio.run(test())