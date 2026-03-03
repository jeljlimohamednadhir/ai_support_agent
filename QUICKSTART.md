# 🚀 Quick Start — Genergy IA v1.0.0

Guide de démarrage rapide pour lancer l'application complète avec tous les composants.

---

## ⚡ Démarrage Ultra-Rapide (5 minutes)

### Prérequis
- Python 3.11+
- Node.js 18+
- Podman Desktop ou Docker

### Étape 1 : Services Infrastructure
```powershell
# Windows (PowerShell) avec Podman
wsl podman run -d --name redis -p 6379:6379 redis:7-alpine
wsl podman run -d --name neo4j -p 7474:7474 -p 7687:7687 `
  -e NEO4J_AUTH=neo4j/password neo4j:5
wsl podman run -d --name qdrant -p 6333:6333 qdrant/qdrant
wsl podman run -d --name postgres -p 5432:5432 `
  -e POSTGRES_PASSWORD=genergy postgres:15
```

### Étape 2 : Backend
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Étape 3 : Frontend
```powershell
cd frontend
npm install
npm run dev
```

### Étape 4 : Workers
```powershell
cd workers
pip install -r requirements.txt
.\start_workers.ps1  # Choisir option 4 (Tout)
```

### ✅ Vérification
- Frontend : http://localhost:5173
- Backend : http://localhost:8000/docs
- Flower : http://localhost:5555
- Neo4j : http://localhost:7474

---

## 🎯 Utilisation Rapide

### 1. Configurer l'Application
1. Ouvrir http://localhost:5173/settings
2. Onglet **LLM** : 
   - Provider : `groq`
   - Model : `llama-3.3-70b-versatile`
   - API Key : `gsk_...` (votre clé Groq)
3. Onglet **Jira** :
   - URL : `https://your-company.atlassian.net`
   - User : `user@company.com`
   - Token : Votre token Jira
4. Cliquer **Sauvegarder**

### 2. Synchroniser Jira
```powershell
# Option 1 : Attendre le sync automatique (1h)

# Option 2 : Déclencher manuellement
celery -A celery_app call workers.jira_sync.tasks.sync_jira_tickets `
  --args='["PROJ", true]'
```

### 3. Construire le Graph
```powershell
# Option 1 : Attendre la reconstruction auto (6h)

# Option 2 : Déclencher manuellement
celery -A celery_app call workers.graph_builder.tasks.build_knowledge_graph
```

### 4. Utiliser le Chatbot
1. Ouvrir http://localhost:5173/chat
2. Poser une question : "Quels sont les 5 derniers tickets Jira ?"
3. L'IA répond avec sources citées

---

## 🔧 Configuration Avancée

### Variables d'Environnement
Créer `backend/.env` :
```env
# LLM
GROQ_API_KEY=gsk_your_key_here
LLM_PROVIDER=groq
LLM_MODEL=llama-3.3-70b-versatile
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=4096

# Databases
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

QDRANT_HOST=localhost
QDRANT_PORT=6333

POSTGRES_URI=postgresql://postgres:genergy@localhost:5432/genergy

# Redis
REDIS_URL=redis://localhost:6379/0

# Jira
JIRA_URL=https://your-company.atlassian.net
JIRA_USER=user@company.com
JIRA_TOKEN=your_jira_token
JIRA_PROJECT_KEY=PROJ

# Security
SECRET_KEY=your-super-secret-key-min-32-chars
```

### Personnaliser les Workers

**Modifier les schedules (backend/workers/celery_app.py)** :
```python
beat_schedule = {
    'sync-jira-hourly': {
        'task': 'workers.jira_sync.tasks.scheduled_sync',
        'schedule': crontab(minute=0),  # Toutes les heures
    },
    'rebuild-graph': {
        'task': 'workers.graph_builder.tasks.scheduled_graph_build',
        'schedule': crontab(minute=0, hour='*/6'),  # Toutes les 6h
    },
}
```

**Exemples de personnalisation** :
```python
# Sync toutes les 30 minutes
'schedule': crontab(minute='*/30'),

# Rebuild tous les jours à 2h du matin
'schedule': crontab(minute=0, hour=2),

# Sync en semaine seulement
'schedule': crontab(minute=0, hour='*/2', day_of_week='mon-fri'),
```

---

## 🐛 Troubleshooting

### Problème : Workers ne démarrent pas
```powershell
# Vérifier Redis
wsl podman ps | Select-String redis
wsl podman exec redis redis-cli ping  # Doit retourner PONG

# Redémarrer Redis si nécessaire
wsl podman restart redis
```

### Problème : Neo4j connexion échoue
```powershell
# Vérifier Neo4j
wsl podman ps | Select-String neo4j
wsl podman logs neo4j

# Ouvrir http://localhost:7474
# User: neo4j, Password: password
```

### Problème : Jira sync échoue
```powershell
# Vérifier les credentials
# Ouvrir Flower : http://localhost:5555
# Onglet "Tasks" → Voir les erreurs

# Tester manuellement
python -c "from jira import JIRA; j = JIRA('https://your-company.atlassian.net', basic_auth=('user@company.com', 'token')); print(j.myself())"
```

### Problème : Frontend ne charge pas
```powershell
# Vérifier le backend
curl http://localhost:8000/api/v1/config/

# Vérifier les logs frontend
# Console navigateur (F12)
```

### Logs Utiles
```powershell
# Backend
backend\logs\app.log

# Workers
workers\logs\celery_worker.log
workers\logs\celery_beat.log
workers\logs\flower.log

# Containers
wsl podman logs redis
wsl podman logs neo4j
wsl podman logs qdrant
```

---

## 📊 Monitoring

### Flower Dashboard
- URL : http://localhost:5555
- **Workers** : État des workers (actif, inactif, occupé)
- **Tasks** : Tâches en cours et historique
- **Broker** : État de la queue Redis
- **Monitor** : Graphiques de performance

### Neo4j Browser
- URL : http://localhost:7474
- User : `neo4j`
- Password : `password`

**Requêtes utiles** :
```cypher
// Compter les nœuds par type
MATCH (n) RETURN labels(n) as Type, count(n) as Count

// Voir les tickets Jira récents
MATCH (n:JiraTicket) 
RETURN n.key, n.summary, n.status 
ORDER BY n.updated DESC LIMIT 10

// Voir le graphe complet (attention si gros)
MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 100
```

### Backend Health
```powershell
# Health check
curl http://localhost:8000/health

# Metrics (si implémenté)
curl http://localhost:8000/metrics
```

---

## 🚀 Déploiement Production

### Checklist Pré-Déploiement
- [ ] Variables d'environnement configurées (pas de .env committé)
- [ ] Secret keys générés (min 32 caractères)
- [ ] Credentials Jira valides
- [ ] Bases de données externalisées (pas en containers)
- [ ] HTTPS configuré (nginx, Traefik, ou cloud load balancer)
- [ ] Monitoring activé (Prometheus + Grafana)
- [ ] Backups automatiques configurés
- [ ] CI/CD pipeline testé

### Docker Compose Production
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  backend:
    image: genergy-backend:latest
    environment:
      - ENV=production
      - LOG_LEVEL=INFO
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped

  worker:
    image: genergy-worker:latest
    environment:
      - ENV=production
    restart: unless-stopped

  beat:
    image: genergy-worker:latest
    command: celery -A celery_app beat --loglevel=INFO
    restart: unless-stopped

  flower:
    image: genergy-worker:latest
    command: celery -A celery_app flower --port=5555
    ports:
      - "5555:5555"
    restart: unless-stopped
```

### Systemd Services (Linux)
```ini
# /etc/systemd/system/genergy-worker.service
[Unit]
Description=Genergy IA Celery Worker
After=network.target redis.service

[Service]
Type=simple
User=genergy
WorkingDirectory=/opt/genergy/workers
Environment="PATH=/opt/genergy/workers/.venv/bin"
ExecStart=/opt/genergy/workers/.venv/bin/celery -A celery_app worker --loglevel=INFO
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

### Kubernetes Deployment
```yaml
# k8s/worker-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: genergy-worker
spec:
  replicas: 3
  selector:
    matchLabels:
      app: genergy-worker
  template:
    metadata:
      labels:
        app: genergy-worker
    spec:
      containers:
      - name: worker
        image: genergy-worker:latest
        env:
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: genergy-secrets
              key: redis-url
        - name: JIRA_TOKEN
          valueFrom:
            secretKeyRef:
              name: genergy-secrets
              key: jira-token
```

---

## 📚 Ressources

### Documentation
- [Guide Complet](FINAL_COMPLETION.md)
- [Guide Workers](docs/WORKERS_GUIDE.md)
- [Guide Développeur](docs/DEV_GUIDE.md)
- [Guide Utilisateur](docs/USER_GUIDE.md)

### Support
- GitHub Issues : Pour bugs et feature requests
- Documentation : `docs/` directory
- Logs : `backend/logs/` et `workers/logs/`

### APIs Externes
- [Jira API Docs](https://developer.atlassian.com/cloud/jira/platform/rest/v3/)
- [Groq API Docs](https://console.groq.com/docs)
- [Neo4j Cypher](https://neo4j.com/docs/cypher-manual/)
- [Celery Docs](https://docs.celeryq.dev/)

---

**🎉 Votre application est prête à l'emploi !**

Pour toute question : Consultez `FINAL_COMPLETION.md` ou `docs/WORKERS_GUIDE.md`
