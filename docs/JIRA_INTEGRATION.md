# Configuration Jira pour BRASIL AI Support Agent

## Variables d'environnement

Ajoutez ces variables dans votre fichier `.env` :

```bash
# Jira Configuration
JIRA_URL=https://votre-domaine.atlassian.net
JIRA_EMAIL=votre-email@example.com
JIRA_API_TOKEN=votre_token_api_jira
```

## Obtenir un API Token Jira

1. Connectez-vous à https://id.atlassian.com/manage-profile/security/api-tokens
2. Cliquez sur "Create API token"
3. Donnez un nom au token (ex: "BRASIL AI Assistant")
4. Copiez le token généré et ajoutez-le à votre `.env`

## Installation des dépendances

```bash
cd backend
pip install jira==3.6.0
```

## Endpoints API disponibles

### 1. Test de connexion
```bash
POST /api/v1/jira/test-connection
Content-Type: application/json

{
  "jira_url": "https://votre-domaine.atlassian.net",
  "email": "votre-email@example.com",
  "api_token": "votre_token"
}
```

### 2. Récupérer les projets
```bash
GET /api/v1/jira/projects
```

### 3. Statistiques Jira
```bash
GET /api/v1/jira/stats
```

### 4. Synchroniser les tickets
```bash
POST /api/v1/jira/sync
Content-Type: application/json

{
  "project_keys": ["BRASIL", "SUPPORT"],
  "max_results": 100,
  "include_resolved": true
}
```

### 5. Rechercher des tickets
```bash
POST /api/v1/jira/search
Content-Type: application/json

{
  "query": "erreur BRASIL",
  "project_keys": ["BRASIL"],
  "status": ["Open", "In Progress"],
  "max_results": 50
}
```

## Utilisation dans le chatbot

Une fois les tickets synchronisés, le chatbot pourra automatiquement les utiliser comme source de connaissance :

**Exemple de question :**
> "Y a-t-il des tickets Jira similaires à l'erreur BRASIL 1002 ?"

**Le chatbot va :**
1. Rechercher dans les tickets Jira indexés
2. Trouver les tickets similaires
3. Corréler avec les fiches FR et tables SQL
4. Proposer une réponse structurée avec les sources

## Format des tickets dans le RAG

Les tickets sont indexés avec les métadonnées suivantes :
- `type`: "jira_ticket"
- `ticket_key`: "BRASIL-123"
- `status`: "Open", "In Progress", "Resolved", etc.
- `priority`: "Highest", "High", "Medium", "Low"
- `issue_type`: "Bug", "Story", "Task", etc.
- `project_key`: "BRASIL"
- `assignee`: Nom de l'assigné
- `labels`: Tags du ticket
- `components`: Composants affectés

## Intégration frontend

La section Jira est intégrée dans la page "Collection" :
- Configuration de la connexion Jira
- Visualisation des stats (total, ouverts, en cours, résolus)
- Liste des projets avec nombre de tickets
- Bouton de synchronisation manuelle

## Sécurité

⚠️ **Important** :
- Ne commitez JAMAIS votre API token dans Git
- Ajoutez `.env` dans `.gitignore`
- Utilisez des tokens avec les permissions minimales
- Renouvelez les tokens régulièrement

## Permissions Jira requises

Le token API doit avoir les permissions suivantes :
- Read: View projects, issues, and comments
- Browse projects
- View issue details

## Troubleshooting

### Erreur "Unauthorized"
- Vérifiez que l'email correspond au compte Jira
- Vérifiez que le token API est valide
- Vérifiez les permissions du token

### Erreur "Connection timeout"
- Vérifiez l'URL Jira (doit contenir https://)
- Vérifiez votre connexion internet
- Vérifiez que Jira est accessible

### Tickets non trouvés dans le chatbot
- Lancez une synchronisation manuelle
- Vérifiez que les tickets sont bien dans Qdrant
- Attendez quelques secondes après la sync (embedding en cours)
