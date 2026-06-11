"""
Script de test pour vérifier l'accès au projet BRASIL sur Jira
"""
from jira import JIRA, JIRAError

# ===== CONFIGURATION =====
# Remplacez ces valeurs par vos identifiants
JIRA_URL = "https://portail.agir.orange.com"  # Votre URL Jira
EMAIL = ""  # Laisser vide si vous utilisez un Personal Access Token
API_TOKEN = "BITBUCKET_TOKEN_REDACTED"  # Votre Personal Access Token ou API Token

# =========================

def test_jira_brasil():
    """Test de connexion et recherche du projet BRASIL"""
    
    print("=" * 60)
    print("TEST DE CONNEXION JIRA - PROJET BRASIL")
    print("=" * 60)
    
    # Validation
    if not JIRA_URL or not API_TOKEN:
        print("❌ ERREUR: Veuillez renseigner JIRA_URL et API_TOKEN dans le script")
        return
    
    try:
        print(f"\n📡 Connexion à Jira...")
        print(f"   URL: {JIRA_URL}")
        print(f"   Mode: {'Personal Access Token' if not EMAIL else 'Email + API Token'}")
        
        # Connexion Jira
        if EMAIL and EMAIL.strip():
            # Mode Email + API Token
            jira = JIRA(
                server=JIRA_URL,
                basic_auth=(EMAIL, API_TOKEN),
                timeout=10,
                max_retries=1
            )
            print(f"   Email: {EMAIL}")
        else:
            # Mode Personal Access Token
            jira = JIRA(
                server=JIRA_URL,
                token_auth=API_TOKEN,
                timeout=10,
                max_retries=1
            )
            print("   Email: (non requis pour PAT)")
        
        print("✅ Connexion réussie!\n")
        
        # Test 1: Lister tous les projets accessibles
        print("📋 Liste de tous les projets accessibles:")
        print("-" * 60)
        try:
            projects = jira.projects()
            print(f"   Nombre total de projets: {len(projects)}")
            
            for project in projects[:10]:  # Afficher max 10 projets
                print(f"   • {project.key:15s} - {project.name}")
            
            if len(projects) > 10:
                print(f"   ... et {len(projects) - 10} autres projets")
            
            print()
        except Exception as e:
            print(f"❌ Erreur lors de la récupération des projets: {e}\n")
        
        # Test 2: Rechercher spécifiquement le projet BRASIL
        print("🔍 Recherche du projet BRASIL:")
        print("-" * 60)
        try:
            brasil_project = jira.project('BRASIL')
            
            print("✅ PROJET BRASIL TROUVÉ!")
            print(f"   ID: {brasil_project.id}")
            print(f"   Clé: {brasil_project.key}")
            print(f"   Nom: {brasil_project.name}")
            
            if hasattr(brasil_project, 'description') and brasil_project.description:
                print(f"   Description: {brasil_project.description[:100]}...")
            
            if hasattr(brasil_project, 'lead') and brasil_project.lead:
                print(f"   Responsable: {brasil_project.lead.displayName}")
            
            print()
            
            # Test 3: Récupérer quelques tickets directement (plus rapide)
            print("🎫 Récupération de tickets BRASIL (les 10 plus récents):")
            print("-" * 60)
            try:
                print("   ⏳ Recherche en cours (timeout 15s)...")
                
                # Récupérer directement 10 tickets avec timeout court
                recent = jira.search_issues(
                    "project = BRASIL ORDER BY updated DESC",
                    maxResults=10
                )
                
                total_found = recent.total if hasattr(recent, 'total') else len(recent)
                
                print(f"   ✅ {len(recent)} tickets récupérés (total estimé: {total_found})")
                print()
                
                if len(recent) > 0:
                    print("📝 Tickets récents:")
                    print("-" * 60)
                    for i, issue in enumerate(recent, 1):
                        status = issue.fields.status.name if hasattr(issue.fields, 'status') else 'N/A'
                        priority = issue.fields.priority.name if hasattr(issue.fields, 'priority') and issue.fields.priority else 'N/A'
                        print(f"   {i}. {issue.key}: {issue.fields.summary[:45]}...")
                        print(f"      📊 Statut: {status} | Priorité: {priority}")
                    print()
                else:
                    print("   ℹ️ Aucun ticket trouvé dans BRASIL")
                    print()
                
            except Exception as e:
                print(f"⚠️ Erreur lors du comptage des tickets: {e}\n")
            
        except JIRAError as e:
            if e.status_code == 404:
                print("❌ PROJET BRASIL NON TROUVÉ")
                print("   Le projet BRASIL n'existe pas ou vous n'y avez pas accès")
            else:
                print(f"❌ Erreur Jira: {e}")
            print()
        except Exception as e:
            print(f"❌ Erreur: {e}\n")
        
        print("=" * 60)
        print("✅ TEST TERMINÉ")
        print("=" * 60)
        
    except JIRAError as e:
        print(f"\n❌ ERREUR DE CONNEXION JIRA:")
        print(f"   Code: {e.status_code}")
        print(f"   Message: {e.text}")
        
        if "CAPTCHA_CHALLENGE" in str(e):
            print("\n💡 SUGGESTION:")
            print("   Il semble que vous devez utiliser un Personal Access Token")
            print("   au lieu de l'authentification Email + API Token")
        
        print()
        
    except Exception as e:
        print(f"\n❌ ERREUR INATTENDUE: {e}\n")


if __name__ == "__main__":
    test_jira_brasil()
