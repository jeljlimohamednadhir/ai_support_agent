"""
Script de test du chatbot via l'API REST
Lance le serveur backend puis teste les endpoints
"""
import requests
import json
import time


def test_chat_api():
    base_url = "http://localhost:8000/api/v1/chatbot"
    
    tests = [
        {
            "name": "TEST 1: Erreur BRASIL 1002",
            "question": "Comment résoudre l'erreur BRASIL 1002 ?"
        },
        {
            "name": "TEST 2: Table t_ports",
            "question": "Qu'est-ce que la table t_ports ?"
        },
        {
            "name": "TEST 3: Compteurs DSLAM",
            "question": "Quelles tables sont concernées par les problèmes de compteurs DSLAM ?"
        },
        {
            "name": "TEST 4: FR 1583",
            "question": "Que dit la fiche FR 1583 ?"
        }
    ]
    
    print("🤖 Test du chatbot BRASIL via API REST\n")
    print("⚠️  IMPORTANT: Le serveur backend doit être lancé sur http://localhost:8000")
    print("   Commande: cd backend && uvicorn app.main:app --reload\n")
    
    # Vérifier que le serveur est accessible
    try:
        health_check = requests.get("http://localhost:8000/health", timeout=2)
        print(f"✅ Serveur accessible: {health_check.json()}\n")
    except Exception as e:
        print(f"❌ Serveur non accessible: {e}")
        print("   Lance d'abord le serveur backend!")
        return
    
    # Exécuter les tests
    for test in tests:
        print("=" * 80)
        print(f"📋 {test['name']}")
        print(f"❓ Question: {test['question']}")
        print("=" * 80)
        
        try:
            response = requests.post(
                f"{base_url}/chat",
                json={"content": test['question']},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                print(f"\n📝 RÉPONSE:")
                print(data['message'])
                
                print(f"\n📚 SOURCES ({len(data.get('sources', []))}):")
                for src in data.get('sources', []):
                    print(f"  • {src['name']} (pertinence: {src['relevance']:.2%})")
                
                print(f"\n🎯 Confiance: {data.get('confidence', 0):.2%}")
                print(f"🆔 Conversation ID: {data.get('conversation_id', 'N/A')}")
            else:
                print(f"❌ Erreur HTTP {response.status_code}: {response.text}")
        
        except Exception as e:
            print(f"❌ Erreur: {e}")
        
        print("\n")
        time.sleep(1)  # Pause entre les tests


if __name__ == "__main__":
    test_chat_api()
