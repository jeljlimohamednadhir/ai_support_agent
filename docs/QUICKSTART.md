# Quick Start Guide - Podman Edition

## Démarrage rapide en 5 minutes

### 1. Prérequis

#### Windows
```powershell
# Vérifier Podman
podman --version  # >= 4.0
podman-compose --version  # >= 1.0

# Si pas installé:
# Télécharger Podman Desktop: https://podman-desktop.io/downloads
# Installer podman-compose: pip install podman-compose
```

#### Linux/WSL
```bash
# Utiliser le script d'installation
chmod +x install-podman.sh
./install-podman.sh
source ~/.bashrc
```

### 2. Configuration

```powershell
cd ai-support-agent

# Le fichier .env est déjà configuré avec Groq
# Vérifier backend/.env pour la clé API Groq
```

### 3. Lancer tous les services

#### Windows (Méthode simple)
```powershell
# Avec le script PowerShell
.\podman.ps1 up -Detached

# Voir l'état
.\podman.ps1 ps
```

#### Linux/Windows (Méthode standard)
```bash
# Avec podman-compose
podman-compose up -d

# Vérifier les logs
podman-compose logs -f
```

### 4. Accéder à l'application

| Service | URL | Identifiants |
|---------|-----|--------------|
| **Backend API** | http://localhost:8000/docs | - |
| **Neo4j Browser** | http://localhost:7474 | neo4j / neo4j_secure_2024 |
| **Qdrant Dashboard** | http://localhost:6333/dashboard | - |
| **PostgreSQL** | localhost:5432 | postgres / postgres_secure_2024 |

### 5. Tester le chatbot

#### Avec PowerShell
```powershell
# Test rapide
cd backend
python quick_test.py

# Lancer le backend
python -m uvicorn app.main:app --reload
```

#### Avec curl
```powershell
# Tester l'endpoint chat
curl -X POST http://localhost:8000/api/v1/chatbot/chat `
  -H "Content-Type: application/json" `
  -d '{"message": "Bonjour, explique-moi ce qu''est un API REST", "user_id": "test"}'
```

## Résolution de problèmes

### Conteneurs ne démarrent pas
```powershell
# Vérifier les logs
.\podman.ps1 logs postgres

# Ou avec podman directement
podman logs ai-support-postgres

# Redémarrer un service
.\podman.ps1 restart postgres
```

### Port déjà utilisé
```powershell
# Trouver le processus
netstat -ano | findstr :5432

# Arrêter tous les conteneurs
.\podman.ps1 down

# Relancer
.\podman.ps1 up -Detached
```

### Connexion LLM échoue
- Vérifier que `GROQ_API_KEY` est dans `backend/.env`
- Tester: `cd backend; python quick_test.py`
- Vérifier les logs: `Get-Content backend/logs/app.log -Tail 20`

### Base de données vide
```powershell
# Se connecter au conteneur PostgreSQL
podman exec -it ai-support-postgres psql -U postgres -d ai_support_agent

# Vérifier les tables
\dt
```

## Commandes utiles

```powershell
# Voir tous les conteneurs
.\podman.ps1 ps

# Arrêter tout
.\podman.ps1 down

# Nettoyer complètement (⚠️ supprime les données)
.\podman.ps1 clean

# Logs d'un service
.\podman.ps1 logs neo4j

# Redémarrer tout
.\podman.ps1 restart
```

## Prochaines étapes

1. ✅ Services démarrés → Tester le chatbot (http://localhost:8000/docs)
2. 📚 Lire le [Guide Podman complet](../PODMAN_GUIDE.md)
3. 🔧 Voir l'[architecture](ARCHITECTURE.md)
4. 🚀 [Implémenter les collecteurs](../README.md#développement)

**Vous êtes prêt ! 🎉**

