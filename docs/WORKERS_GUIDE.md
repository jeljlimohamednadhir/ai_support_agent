# Guide des Workers — Genergy IA

## Vue d'ensemble

Les workers Celery gèrent les tâches asynchrones :
- **Jira Sync** : Synchronisation des tickets Jira
- **Graph Builder** : Construction du knowledge graph
- **Code Analyzer** : Analyse de code source
- **Log Analyzer** : Analyse des logs
- **DB Analyzer** : Analyse de bases de données
- **Doc Analyzer** : Analyse de documentation

## Prérequis

- **Redis** : Queue broker pour Celery
- **Backend** : Services Neo4j, Qdrant, PostgreSQL

## Installation

### 1. Installer Redis

**Windows (Podman/WSL) :**
```bash
wsl podman run -d --name redis -p 6379:6379 redis:latest
```

**Linux/Mac (Docker) :**
```bash
docker run -d --name redis -p 6379:6379 redis:latest
```

### 2. Installer les Dépendances

```bash
cd workers
pip install -r requirements.txt
```

## Démarrage

### Worker Principal

```bash
cd workers
celery -A celery_app worker --loglevel=info
```

### Celery Beat (Tâches planifiées)

```bash
celery -A celery_app beat --loglevel=info
```

### Flower (Monitoring Web)

```bash
pip install flower
celery -A celery_app flower --port=5555
```

Ouvrir `http://localhost:5555` pour le dashboard.

## Workers Disponibles

### 1. Jira Sync Worker

**Tâches :**
- `workers.jira_sync.sync_jira_tickets` : Synchronisation manuelle
- `workers.jira_sync.scheduled_sync` : Sync horaire (auto)
- `workers.jira_sync.full_resync` : Resync complet

**Utilisation manuelle :**
```python
from workers.jira_sync.tasks import sync_jira_tickets

# Sync incremental
result = sync_jira_tickets.delay(project_key='BRASIL', incremental=True)

# Sync complet
result = sync_jira_tickets.delay(project_key='BRASIL', incremental=False)
```

**Configuration requise :**
```python
# backend/app/core/config.py
JIRA_URL = "https://jira.yourcompany.com"
JIRA_USER = "your.email@company.com"
JIRA_TOKEN = "your_api_token"
```

**Planification :**
- Sync horaire : Toutes les heures (crontab `minute=0`)
- Incremental : Tickets modifiés dans les dernières 24h

### 2. Graph Builder Worker

**Tâches :**
- `workers.graph_builder.build_graph` : Construire le graphe
- `workers.graph_builder.update_relationships` : Mettre à jour les relations
- `workers.graph_builder.scheduled_build` : Build périodique (auto)

**Utilisation manuelle :**
```python
from workers.graph_builder.tasks import build_knowledge_graph

# Construire graphe complet
result = build_knowledge_graph.delay()

# Construire pour types spécifiques
result = build_knowledge_graph.delay(source_types=['jira_ticket', 'database_table'])
```

**Planification :**
- Rebuild : Toutes les 6 heures (crontab `minute=0, hour='*/6'`)

### 3. Code Analyzer Worker

**Tâches :**
- Analyse de dépôts Git
- Extraction de fonctions, classes, imports
- Détection de patterns

### 4. Log Analyzer Worker

**Tâches :**
- Ingestion de logs
- Détection d'anomalies
- Extraction de patterns d'erreurs

### 5. DB Analyzer Worker

**Tâches :**
- Analyse de schémas de bases de données
- Extraction de métadonnées de tables
- Relations entre tables

### 6. Doc Analyzer Worker

**Tâches :**
- Indexation de documentation
- Extraction de sections
- Analyse de markdown/rst

## Configuration Celery

**Broker & Backend :**
```python
# workers/celery_app.py
broker = "redis://localhost:6379/0"
backend = "redis://localhost:6379/0"
```

**Paramètres :**
- `task_time_limit` : 3600s (1h max par tâche)
- `worker_prefetch_multiplier` : 1 (exécution séquentielle)
- `timezone` : UTC

## Monitoring

### Flower Dashboard

**Installation :**
```bash
pip install flower
```

**Démarrage :**
```bash
celery -A celery_app flower --port=5555
```

**URL :** `http://localhost:5555`

**Fonctionnalités :**
- Voir les workers actifs
- Tâches en cours/terminées
- Statistiques de performance
- Logs en temps réel

### Logs

Les logs sont écrits dans :
- **Console** : Niveau INFO
- **Fichiers** : `workers/logs/` (à configurer)

## Dépannage

### Problème : Worker ne démarre pas

**Solution :**
```bash
# Vérifier Redis
redis-cli ping  # Doit retourner "PONG"

# Vérifier les dépendances
pip install -r requirements.txt

# Vérifier le path Python
export PYTHONPATH="${PYTHONPATH}:$(pwd)/../backend"
```

### Problème : Tâches bloquées

**Solution :**
```bash
# Purger la queue
celery -A celery_app purge

# Redémarrer workers
celery -A celery_app worker --loglevel=info --purge
```

### Problème : Jira sync échoue

**Solution :**
1. Vérifier les credentials Jira
2. Tester la connexion manuellement :
```python
from jira import JIRA
jira = JIRA(server='https://jira.company.com', basic_auth=('user', 'token'))
issues = jira.search_issues('project = BRASIL', maxResults=1)
```

### Problème : Neo4j non disponible

**Solution :**
```bash
# Démarrer Neo4j
wsl podman start neo4j

# Vérifier connexion
curl http://localhost:7474
```

## Commandes Utiles

```bash
# Voir les tâches actives
celery -A celery_app inspect active

# Voir les tâches planifiées
celery -A celery_app inspect scheduled

# Voir les workers enregistrés
celery -A celery_app inspect registered

# Révoquer une tâche
celery -A celery_app revoke <task_id>

# Statistiques
celery -A celery_app inspect stats
```

## Déploiement Production

### Systemd Service (Linux)

**Fichier :** `/etc/systemd/system/celery-worker.service`
```ini
[Unit]
Description=Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=genergy
Group=genergy
WorkingDirectory=/opt/genergy-ia/workers
ExecStart=/opt/genergy-ia/.venv/bin/celery -A celery_app worker --loglevel=info --detach
ExecStop=/opt/genergy-ia/.venv/bin/celery -A celery_app control shutdown

[Install]
WantedBy=multi-user.target
```

**Démarrage :**
```bash
sudo systemctl enable celery-worker
sudo systemctl start celery-worker
sudo systemctl status celery-worker
```

### Docker Compose

```yaml
services:
  redis:
    image: redis:latest
    ports:
      - "6379:6379"
  
  celery-worker:
    build:
      context: .
      dockerfile: infrastructure/docker/worker.Dockerfile
    depends_on:
      - redis
      - neo4j
      - qdrant
    environment:
      - REDIS_URL=redis://redis:6379/0
      - NEO4J_URI=bolt://neo4j:7687
      - QDRANT_HOST=qdrant
  
  celery-beat:
    build:
      context: .
      dockerfile: infrastructure/docker/worker.Dockerfile
    command: celery -A celery_app beat --loglevel=info
    depends_on:
      - redis
```

## Performance

### Scaling

**Plusieurs workers :**
```bash
# Worker 1 (général)
celery -A celery_app worker -Q default --loglevel=info --hostname=worker1@%h

# Worker 2 (Jira sync)
celery -A celery_app worker -Q jira_sync --loglevel=info --hostname=worker2@%h

# Worker 3 (Graph builder)
celery -A celery_app worker -Q graph_builder --loglevel=info --hostname=worker3@%h
```

### Concurrency

```bash
# Mode prefork (multiprocessing)
celery -A celery_app worker --concurrency=4

# Mode gevent (async I/O)
celery -A celery_app worker --pool=gevent --concurrency=100
```

## Sécurité

1. **Variables d'environnement** : Ne jamais hardcoder les secrets
2. **Redis** : Configurer password en production
3. **Logs** : Ne pas logger les tokens/passwords
4. **Réseau** : Isoler Redis dans un réseau privé

---

**Support :** Consultez `docs/DEV_GUIDE.md` pour plus d'informations.
