"""
Test de connexion Jira avec différentes configurations
"""

import os
from jira import JIRA, JIRAError
from dotenv import load_dotenv

from pathlib import Path
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

# Correction : utiliser les bonnes variables d'environnement
JIRA_URL = os.getenv('JIRA_URL')
JIRA_EMAIL = os.getenv('JIRA_EMAIL', '')
JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN')

print(f"🔍 Test de connexion Jira")
print(f"URL: {JIRA_URL}")
print(f"Email: {JIRA_EMAIL if JIRA_EMAIL else '(vide - mode PAT)'}")
print(f"Token: {'***' + JIRA_API_TOKEN[-4:] if JIRA_API_TOKEN and len(JIRA_API_TOKEN) > 4 else '(non défini)'}")
print("-" * 60)

# Test 1: PAT (Personal Access Token)
if JIRA_API_TOKEN and not JIRA_EMAIL.strip():
    print("\n✅ Mode PAT détecté")
    try:
        print(f"Tentative de connexion avec PAT à {JIRA_URL}...")
        jira = JIRA(server=JIRA_URL, token_auth=JIRA_API_TOKEN, timeout=30)
        
        # Test: récupérer les infos du serveur
        server_info = jira.server_info()
        print(f"✅ Connexion réussie!")
        print(f"   Version: {server_info.get('version')}")
        print(f"   Type: {server_info.get('deploymentType', 'Unknown')}")
        
        # Test: récupérer l'utilisateur actuel
        try:
            current_user = jira.myself()
            print(f"   Utilisateur: {current_user.get('displayName')} ({current_user.get('emailAddress')})")
        except:
            print("   (Impossible de récupérer les infos utilisateur)")
        
        # Test: lister les projets
        projects = jira.projects()
        print(f"   Projets accessibles: {len(projects)}")
        if projects:
            print(f"   Premiers projets:")
            for p in projects[:5]:
                print(f"     - {p.key}: {p.name}")
        
    except JIRAError as e:
        print(f"❌ Erreur JIRA: {e.status_code} - {e.text}")
        if e.status_code == 401:
            print("   → Token invalide ou expiré")
        elif e.status_code == 403:
            print("   → Accès refusé (permissions insuffisantes)")
        elif e.status_code == 404:
            print("   → URL incorrecte")
    except Exception as e:
        print(f"❌ Erreur: {type(e).__name__}: {e}")

# Test 2: Basic Auth (Email + API Token)
elif JIRA_EMAIL and JIRA_API_TOKEN:
    print("\n✅ Mode Basic Auth détecté")
    try:
        print(f"Tentative de connexion avec email/token à {JIRA_URL}...")
        jira = JIRA(server=JIRA_URL, basic_auth=(JIRA_EMAIL, JIRA_API_TOKEN), timeout=30)
        
        server_info = jira.server_info()
        print(f"✅ Connexion réussie!")
        print(f"   Version: {server_info.get('version')}")
        print(f"   Type: {server_info.get('deploymentType', 'Unknown')}")
        
        projects = jira.projects()
        print(f"   Projets accessibles: {len(projects)}")
        if projects:
            print(f"   Premiers projets:")
            for p in projects[:5]:
                print(f"     - {p.key}: {p.name}")
        
    except JIRAError as e:
        print(f"❌ Erreur JIRA: {e.status_code} - {e.text}")
        if e.status_code == 401:
            print("   → Credentials invalides")
        elif e.status_code == 403:
            print("   → Accès refusé")
        elif e.status_code == 404:
            print("   → URL incorrecte")
    except Exception as e:
        print(f"❌ Erreur: {type(e).__name__}: {e}")

else:
    print("❌ Configuration incomplète")
    print("   Assurez-vous que JIRA_URL et JIRA_API_TOKEN sont définis dans .env")
    print("   Pour PAT: laissez JIRA_EMAIL vide")
    print("   Pour Basic Auth: renseignez JIRA_EMAIL")

print("\n" + "=" * 60)
print("💡 Conseils:")
print("   - Pour PAT: JIRA_EMAIL doit être vide ou commenté")
print("   - URL doit être l'URL de base sans /browse ou /projects")
print("   - Exemple: https://portail.agir.orange.com")
print("   - Pour vérifier le token, allez dans votre profil Jira")
