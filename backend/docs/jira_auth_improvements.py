"""
Amélioration du JiraCollector pour supporter l'authentification multi-utilisateurs
"""

# Option 1: Authentification globale (compte de service)
# Dans .env:
# JIRA_SERVICE_ACCOUNT_TOKEN=xxx  # Token du compte de service
# JIRA_USE_SERVICE_ACCOUNT=true

# Option 2: Authentification par session utilisateur
# Via l'API, l'utilisateur fournit ses credentials:
# POST /api/v1/jira/connect
# {
#   "email": "user@orange.com",
#   "api_token": "user_token"
# }

# Modification du JiraCollector pour supporter les deux:

class JiraCollector:
    def __init__(
        self, 
        jira_url: str = None,
        email: str = None, 
        api_token: str = None,
        use_service_account: bool = True  # Nouveau paramètre
    ):
        self.jira_url = jira_url or settings.JIRA_URL
        
        if use_service_account and settings.JIRA_SERVICE_ACCOUNT_TOKEN:
            # Utiliser le compte de service (partagé)
            self.api_token = settings.JIRA_SERVICE_ACCOUNT_TOKEN
            self.email = settings.JIRA_SERVICE_EMAIL
        else:
            # Utiliser les credentials personnels
            self.email = email or settings.JIRA_EMAIL
            self.api_token = api_token or settings.JIRA_API_TOKEN
        
        self.jira_client = None

# Endpoint API pour connexion personnelle:
@router.post("/connect")
async def connect_personal_jira(
    credentials: JiraCredentials,
    current_user: User = Depends(get_current_user)
):
    """Connecter Jira avec credentials personnels"""
    collector = JiraCollector(
        email=credentials.email,
        api_token=credentials.api_token,
        use_service_account=False
    )
    
    # Tester la connexion
    result = collector.test_connection()
    
    if result.success:
        # Stocker les credentials en session (sécurisé)
        # ou en base chiffrée pour cet utilisateur
        return {"message": "Connecté à Jira avec succès"}
    else:
        raise HTTPException(status_code=401, detail="Échec authentification Jira")
