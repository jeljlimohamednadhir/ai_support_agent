#!/usr/bin/env python3
"""
Script pour configurer la clé API Groq dans le fichier .env
"""
import os
import sys
from pathlib import Path

def configure_groq_api():
    """Configure Groq API key in .env file"""
    
    # Path to .env file
    env_path = Path(__file__).parent / ".env"
    
    print("=" * 60)
    print("Configuration de la clé API Groq")
    print("=" * 60)
    print()
    print("Pour obtenir une clé API Groq gratuite:")
    print("1. Visitez https://console.groq.com/")
    print("2. Créez un compte ou connectez-vous")
    print("3. Allez dans 'API Keys'")
    print("4. Créez une nouvelle clé API")
    print()
    
    api_key = input("Entrez votre clé API Groq (ou 'skip' pour passer): ").strip()
    
    if api_key.lower() == 'skip':
        print("⏭️  Configuration ignorée")
        return
    
    if not api_key:
        print("❌ Clé API vide, annulation")
        return
    
    # Read existing .env
    env_content = ""
    groq_key_exists = False
    
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        # Update or preserve existing lines
        for line in lines:
            if line.startswith('GROQ_API_KEY='):
                env_content += f'GROQ_API_KEY={api_key}\n'
                groq_key_exists = True
            else:
                env_content += line
    
    # Add GROQ_API_KEY if it doesn't exist
    if not groq_key_exists:
        if env_content and not env_content.endswith('\n'):
            env_content += '\n'
        env_content += f'GROQ_API_KEY={api_key}\n'
    
    # Write back to .env
    try:
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        print()
        print("✅ Clé API Groq configurée avec succès!")
        print(f"📁 Fichier: {env_path}")
        print()
        print("🔄 Redémarrez le backend pour appliquer les changements:")
        print("   cd backend")
        print("   python -m uvicorn app.main:app --reload")
        print()
        
    except Exception as e:
        print(f"❌ Erreur lors de l'écriture du fichier .env: {e}")
        return
    
    # Test the API key
    print("🧪 Test de la clé API...")
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        
        # Simple test call
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": "test"}],
            model="llama-3.1-8b-instant",
            max_tokens=5
        )
        
        print("✅ La clé API fonctionne correctement!")
        
    except ImportError:
        print("⚠️  Module 'groq' non installé, impossible de tester la clé")
        print("   Installation: pip install groq")
    except Exception as e:
        print(f"❌ Erreur lors du test de la clé API: {e}")
        print("   Vérifiez que la clé est valide sur https://console.groq.com/")

if __name__ == "__main__":
    try:
        configure_groq_api()
    except KeyboardInterrupt:
        print("\n⏹️  Configuration annulée")
        sys.exit(0)
