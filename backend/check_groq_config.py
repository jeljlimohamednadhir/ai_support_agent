#!/usr/bin/env python3
"""
Vérifier la configuration de la clé API Groq
"""
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

def check_groq_config():
    """Vérifier la configuration Groq"""
    print("\n" + "="*60)
    print("🔍 VÉRIFICATION CONFIGURATION GROQ API")
    print("="*60 + "\n")
    
    # Vérifier si la clé est définie
    if not settings.GROQ_API_KEY:
        print("❌ GROQ_API_KEY n'est pas définie")
        print("\n📝 Pour corriger ce problème :")
        print("   1. Obtenir une clé API gratuite sur https://console.groq.com/keys")
        print("   2. Ouvrir le fichier backend/.env")
        print("   3. Ajouter ou modifier la ligne :")
        print("      GROQ_API_KEY=gsk_votre_cle_api_ici")
        print("   4. Redémarrer le backend")
        print("\n⚠️  Sans clé API Groq valide, le chatbot ne fonctionnera pas.")
        return False
    
    # Vérifier la validité de la clé
    groq_key = settings.GROQ_API_KEY
    
    if groq_key == "your_groq_api_key":
        print("❌ GROQ_API_KEY utilise la valeur par défaut")
        print("   Valeur actuelle : 'your_groq_api_key' (placeholder)")
        print("\n📝 Pour corriger :")
        print("   1. Obtenir une vraie clé API sur https://console.groq.com/keys")
        print("   2. Remplacer dans backend/.env :")
        print("      GROQ_API_KEY=gsk_votre_vraie_cle_ici")
        return False
    
    # Vérifier le format
    if not groq_key.startswith("gsk_"):
        print(f"⚠️  GROQ_API_KEY semble invalide")
        print(f"   Valeur actuelle : {groq_key[:20]}...")
        print("   Format attendu : gsk_xxxxxxxxxxxxxxxxxxxxxxxx")
        print("\n📝 Vérifiez que vous avez copié la clé complète depuis")
        print("   https://console.groq.com/keys")
        return False
    
    # Configuration OK
    print("✅ GROQ_API_KEY est définie")
    print(f"   Préfixe : {groq_key[:8]}...")
    print(f"   Longueur : {len(groq_key)} caractères")
    print(f"\n✅ Provider : {settings.LLM_PROVIDER}")
    print(f"✅ Modèle : {settings.GROQ_MODEL}")
    print(f"✅ Température : {settings.GROQ_TEMPERATURE}")
    print(f"✅ Max tokens : {settings.GROQ_MAX_TOKENS}")
    
    # Test simple
    print("\n🧪 Test de connexion à l'API Groq...")
    try:
        from groq import Groq
        client = Groq(api_key=groq_key)
        
        # Test simple
        response = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[{"role": "user", "content": "Bonjour"}],
            max_tokens=10
        )
        
        print("✅ Connexion réussie à l'API Groq!")
        print(f"   Réponse du modèle : {response.choices[0].message.content}")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test : {e}")
        print("\n📝 Si l'erreur est '401 Invalid API Key' :")
        print("   - Vérifiez que la clé est correcte")
        print("   - Vérifiez qu'elle n'a pas expiré sur console.groq.com")
        print("   - Générez une nouvelle clé si nécessaire")
        return False

if __name__ == "__main__":
    success = check_groq_config()
    sys.exit(0 if success else 1)
