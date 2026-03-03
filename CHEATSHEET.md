# 🎯 Aide-Mémoire — Genergy IA v1.0.0

Commandes et références rapides pour l'utilisation quotidienne.

---

## 🚀 Démarrage

### Services Infrastructure
```powershell
# Redis
wsl podman run -d --name redis -p 6379:6379 redis:7-alpine

# Neo4j
wsl podman run -d --name neo4j -p 7474:7474 -p 7687:7687 `
  -e NEO4J_AUTH=neo4j/password neo4j:5

# Qdrant
wsl podman run -d --name qdrant -p 6333:6333 qdrant/qdrant

# PostgreSQL
wsl podman run -d --name postgres -p 5432:5432 `
  -e POSTGRES_PASSWORD=genergy postgres:15
```

### Backend
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```powershell
cd frontend
npm run dev
```

### Workers
```powershell
cd workers
.\start_workers.ps1  # Option 4 (Tout)
```

---

## 📊 URLs Importantes

| Service | URL | Credentials |
|---------|-----|-------------|
| Frontend | http://localhost:5173 | - |
| Backend API | http://localhost:8000 | - |
| API Docs | http://localhost:8000/docs | - |
| Flower | http://localhost:5555 | - |
| Neo4j | http://localhost:7474 | neo4j/password |
| Qdrant | http://localhost:6333/dashboard | - |

---

## 🔧 Commandes Celery

### Worker
```powershell
# Démarrer worker
celery -A celery_app worker --loglevel=INFO

# Avec concurrency
celery -A celery_app worker --loglevel=INFO --concurrency=4

# Pool specifique
celery -A celery_app worker --pool=solo  # Windows
```

### Beat (Scheduler)
```powershell
# Démarrer Beat
celery -A celery_app beat --loglevel=INFO

# Voir les tâches planifiées
celery -A celery_app inspect scheduled
```

### Flower (Monitoring)
```powershell
# Démarrer Flower
celery -A celery_app flower --port=5555

# Avec auth basique
celery -A celery_app flower --basic_auth=user:password
```

### Inspection
```powershell
# Workers actifs
celery -A celery_app inspect active

# Tâches enregistrées
celery -A celery_app inspect registered

# Statistiques
celery -A celery_app inspect stats

# État du cluster
celery -A celery_app status
```

### Contrôle
```powershell
# Purger la queue
celery -A celery_app purge

# Arrêter un worker
celery -A celery_app control shutdown

# Reload configuration
celery -A celery_app control reload
```

---

## 🎯 Tâches Manuelles

### Jira Sync
```powershell
# Sync incrémental (dernières 24h)
celery -A celery_app call workers.jira_sync.tasks.sync_jira_tickets `
  --args='["PROJ", true]'

# Sync complet
celery -A celery_app call workers.jira_sync.tasks.sync_jira_tickets `
  --args='["PROJ", false]'

# Full resync (effacer + recréer)
celery -A celery_app call workers.jira_sync.tasks.full_resync `
  --args='["PROJ"]'
```

### Graph Builder
```powershell
# Construire le graphe
celery -A celery_app call workers.graph_builder.tasks.build_knowledge_graph

# Mettre à jour les relations
celery -A celery_app call workers.graph_builder.tasks.update_relationships
```

---

## 🗄️ Commandes Neo4j (Cypher)

### Exploration
```cypher
// Compter les nœuds par type
MATCH (n) RETURN labels(n) as Type, count(n) as Count

// Voir tous les types de relations
MATCH ()-[r]->() RETURN DISTINCT type(r)

// Statistiques globales
CALL apoc.meta.stats()

// Schéma du graphe
CALL db.schema.visualization()
```

### Jira Tickets
```cypher
// Tous les tickets
MATCH (n:JiraTicket) RETURN n LIMIT 10

// Tickets récents
MATCH (n:JiraTicket) 
RETURN n.key, n.summary, n.status, n.updated 
ORDER BY n.updated DESC LIMIT 10

// Tickets par statut
MATCH (n:JiraTicket) 
RETURN n.status as Status, count(n) as Count
ORDER BY Count DESC

// Recherche par mot-clé
MATCH (n:JiraTicket)
WHERE n.summary CONTAINS "bug"
RETURN n.key, n.summary

// Relations d'un ticket
MATCH (j:JiraTicket {key: "PROJ-123"})-[r]-(n)
RETURN j, r, n
```

### Maintenance
```cypher
// Supprimer tous les nœuds
MATCH (n) DETACH DELETE n

// Supprimer les Jira seulement
MATCH (n:JiraTicket) DETACH DELETE n

// Créer un index
CREATE INDEX jira_key FOR (n:JiraTicket) ON (n.key)

// Créer contrainte d'unicité
CREATE CONSTRAINT jira_unique IF NOT EXISTS
FOR (n:JiraTicket) REQUIRE n.key IS UNIQUE
```

---

## 📦 Commandes Podman/Docker

### Gestion Containers
```powershell
# Lister containers actifs
wsl podman ps

# Tous les containers
wsl podman ps -a

# Arrêter un container
wsl podman stop redis

# Démarrer un container
wsl podman start redis

# Redémarrer
wsl podman restart redis

# Supprimer
wsl podman rm redis

# Supprimer avec force
wsl podman rm -f redis
```

### Logs
```powershell
# Voir les logs
wsl podman logs redis

# Suivre en temps réel
wsl podman logs -f redis

# 100 dernières lignes
wsl podman logs --tail 100 redis
```

### Exec
```powershell
# Redis CLI
wsl podman exec -it redis redis-cli

# Shell dans container
wsl podman exec -it neo4j bash

# Commande directe
wsl podman exec redis redis-cli PING
```

---

## 🧪 Tests

### Backend
```powershell
cd backend

# Tous les tests
pytest

# Avec couverture
pytest --cov=app --cov-report=html

# Test spécifique
pytest tests/test_config_endpoints.py

# Verbose
pytest -v

# Arrêter au premier échec
pytest -x
```

### Frontend
```powershell
cd frontend

# Tests unitaires
npm test

# Tests E2E
npm run test:e2e

# Lint
npm run lint

# Format
npm run format
```

---

## 🔍 Debugging

### Backend Logs
```powershell
# Logs en temps réel
Get-Content backend\logs\app.log -Wait -Tail 50
```

### Worker Logs
```powershell
# Worker
Get-Content workers\logs\celery_worker.log -Wait -Tail 50

# Beat
Get-Content workers\logs\celery_beat.log -Wait -Tail 50

# Flower
Get-Content workers\logs\flower.log -Wait -Tail 50
```

### Redis Debug
```powershell
# Connexion
wsl podman exec -it redis redis-cli

# Dans Redis CLI :
PING                      # Tester connexion
INFO                      # Infos serveur
DBSIZE                    # Nombre de clés
KEYS celery*              # Lister clés Celery
LLEN celery               # Taille de la queue
FLUSHALL                  # DANGER : Supprimer tout
```

### PostgreSQL Debug
```powershell
# Connexion
wsl podman exec -it postgres psql -U postgres

# Dans psql :
\l                        # Lister bases
\c genergy                # Connecter à base
\dt                       # Lister tables
\d system_config          # Décrire table
SELECT * FROM system_config;
```

---

## 📊 Monitoring

### Flower Dashboard
http://localhost:5555

**Vues importantes :**
- **Workers** : État des workers (actif, charge, tâches terminées)
- **Tasks** : Liste des tâches (actives, réussies, échouées)
- **Monitor** : Graphiques temps réel
- **Broker** : État de Redis (queue size, etc.)

### Vérifications Santé
```powershell
# Backend
curl http://localhost:8000/health

# Redis
wsl podman exec redis redis-cli PING

# Neo4j
curl http://localhost:7474

# Qdrant
curl http://localhost:6333
```

---

## 🛠️ Maintenance

### Nettoyage
```powershell
# Purger queue Celery
celery -A celery_app purge

# Supprimer tous les containers
wsl podman rm -f (wsl podman ps -aq)

# Supprimer toutes les images
wsl podman rmi -f (wsl podman images -q)

# Nettoyer volumes
wsl podman volume prune
```

### Backup
```powershell
# Export Neo4j
wsl podman exec neo4j neo4j-admin dump --database=neo4j --to=/backups/neo4j.dump

# Export PostgreSQL
wsl podman exec postgres pg_dump -U postgres genergy > genergy_backup.sql

# Export Qdrant (copier volume)
wsl podman cp qdrant:/qdrant/storage ./qdrant_backup
```

### Restore
```powershell
# Restore Neo4j
wsl podman exec neo4j neo4j-admin load --database=neo4j --from=/backups/neo4j.dump

# Restore PostgreSQL
cat genergy_backup.sql | wsl podman exec -i postgres psql -U postgres genergy
```

---

## 📚 Références Rapides

### Endpoints API Backend
```
GET    /api/v1/config/                    # Toute la config
GET    /api/v1/config/category/{cat}      # Config par catégorie
GET    /api/v1/config/{key}                # Config spécifique
PUT    /api/v1/config/{key}                # Mettre à jour
POST   /api/v1/config/bulk                 # Bulk update
POST   /api/v1/config/reset                # Reset defaults

POST   /api/v1/chatbot/chat                # Envoyer message
GET    /api/v1/chatbot/conversations       # Liste conversations
GET    /api/v1/chatbot/conversations/{id}  # Conversation spécifique
DELETE /api/v1/chatbot/conversations/{id}  # Supprimer

GET    /api/v1/knowledge/stats             # Stats graphe
GET    /api/v1/knowledge/graph             # Export graphe
POST   /api/v1/knowledge/search            # Recherche sémantique
```

### Catégories Config
- `llm` : Provider, model, temperature, max_tokens, api_key
- `database` : neo4j_uri, qdrant_host, postgres_uri
- `ui_preferences` : theme, language, items_per_page, notifications_enabled
- `jira` : jira_url, jira_user, jira_token, jira_project_key

### Schedules Workers
- Jira Sync : Toutes les heures (`crontab(minute=0)`)
- Graph Build : Toutes les 6 heures (`crontab(minute=0, hour='*/6')`)

---

## 🚨 Troubleshooting Express

| Problème | Solution |
|----------|----------|
| Workers ne démarrent pas | Vérifier Redis : `wsl podman exec redis redis-cli PING` |
| Neo4j connexion échouée | Ouvrir http://localhost:7474, credentials neo4j/password |
| Jira sync échoue | Vérifier token dans Flower → Tasks → Erreur |
| Frontend 404 | Vérifier backend actif : `curl http://localhost:8000/docs` |
| Queue pleine | `celery -A celery_app purge` |
| Worker bloqué | `celery -A celery_app control shutdown` puis redémarrer |

---

## 📖 Documentation Complète

- **FINAL_COMPLETION.md** : Vue d'ensemble complète
- **QUICKSTART.md** : Guide de démarrage détaillé
- **docs/WORKERS_GUIDE.md** : Guide workers Celery
- **docs/DEV_GUIDE.md** : Architecture et développement
- **docs/USER_GUIDE.md** : Guide utilisateur

---

**Version :** 1.0.0  
**Dernière mise à jour :** 12 janvier 2026  
**Support :** Voir documentation dans `docs/`
