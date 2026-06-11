#!/usr/bin/env python3
import asyncio
from app.services.chatbot.chatbot_service import ChatbotService
from app.schemas.chatbot import ChatMessage

async def test():
    print("Initialisation du chatbot...")
    chatbot = ChatbotService()
    
    message = ChatMessage(
        content='cite-moi les 5 derniers jira par date',
        role='user'
    )
    
    print("\nEnvoi de la question...")
    response = await chatbot.process_message(message)
    
    print("\n" + "="*80)
    print("RÉPONSE DU CHATBOT")
    print("="*80)
    print(response.content if hasattr(response, 'content') else str(response))
    
    print("\n" + "="*80)
    print("SOURCES UTILISÉES")
    print("="*80)
    if hasattr(response, 'sources') and response.sources:
        for i, source in enumerate(response.sources, 1):
            source_type = source.get('type', 'N/A')
            source_title = source.get('title', 'N/A')
            print(f"{i}. [{source_type}] {source_title[:60]}")
    else:
        print("Aucune source disponible")

asyncio.run(test())