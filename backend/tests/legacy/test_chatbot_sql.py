#!/usr/bin/env python3
"""Test du chatbot avec questions SQL."""

from app.services.chatbot.chatbot_service import ChatbotService
import asyncio


async def test_sql_questions():
    """Test le chatbot avec des questions sur le schéma SQL."""
    from app.schemas.chatbot import ChatMessage
    
    service = ChatbotService()
    
    questions = [
        "Qu'est-ce que la table aml_agregat?",
        "Quelles sont les tables ipon?",
        "Qu'est-ce que la table qd_anomalie?"
    ]
    
    for question in questions:
        print(f"\n{'='*70}")
        print(f"❓ QUESTION: {question}")
        print('='*70)
        
        msg = ChatMessage(
            role="user",
            content=question,
            user_id="test-user",
            conversation_id="test-conv"
        )
        
        response = await service.process_message(msg)
        
        print(f"\n💬 RÉPONSE:\n{response.message}")
        
        if response.sources:
            print(f"\n📚 SOURCES ({len(response.sources)}):")
            for src in response.sources:
                print(f"  - {src.get('name', 'unknown')} ({src.get('type', 'unknown')})")
                print(f"    Path: {src.get('file_path', 'N/A')}")


if __name__ == "__main__":
    asyncio.run(test_sql_questions())
