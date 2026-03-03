# 📁 Structure complète du projet AI Support Agent

```
ai-support-agent/
│
├── 📄 README.md                          # Documentation principale
├── 📄 LICENSE                            # Licence MIT
├── 📄 .gitignore                         # Fichiers à ignorer
├── 📄 docker-compose.yml                 # Orchestration Docker
│
├── 📂 backend/                           # Backend API FastAPI
│   ├── 📄 requirements.txt              # Dépendances Python
│   ├── 📄 .env.example                  # Template variables d'environnement
│   ├── 📄 .gitignore                    # Ignores spécifiques backend
│   │
│   ├── 📂 app/                          # Application principale
│   │   ├── 📄 __init__.py
│   │   ├── 📄 main.py                   # Point d'entrée FastAPI
│   │   │
│   │   ├── 📂 api/                      # Endpoints API
│   │   │   ├── 📄 __init__.py
│   │   │   └── 📂 v1/
│   │   │       ├── 📄 __init__.py
│   │   │       ├── 📄 api.py            # Routeur principal
│   │   │       └── 📂 endpoints/
│   │   │           ├── 📄 __init__.py
│   │   │           ├── 📄 chatbot.py    # Endpoints chatbot
│   │   │           ├── 📄 collector.py  # Endpoints collecte
│   │   │           ├── 📄 analyzer.py   # Endpoints analyse
│   │   │           ├── 📄 knowledge.py  # Endpoints knowledge graph
│   │   │           ├── 📄 validation.py # Endpoints validation
│   │   │           ├── 📄 diagnostics.py # Endpoints diagnostics
│   │   │           └── 📄 users.py      # Endpoints utilisateurs
│   │   │
│   │   ├── 📂 core/                     # Configuration et utilitaires
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 config.py             # Configuration app
│   │   │   ├── 📄 security.py           # Sécurité JWT
│   │   │   └── 📄 logging.py            # Configuration logs
│   │   │
│   │   ├── 📂 models/                   # Modèles SQLAlchemy
│   │   │   └── 📄 __init__.py
│   │   │
│   │   ├── 📂 schemas/                  # Schémas Pydantic
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 chatbot.py
│   │   │   ├── 📄 collector.py
│   │   │   ├── 📄 analyzer.py
│   │   │   ├── 📄 knowledge.py
│   │   │   ├── 📄 validation.py
│   │   │   ├── 📄 diagnostics.py
│   │   │   └── 📄 users.py
│   │   │
│   │   ├── 📂 services/                 # Logique métier
│   │   │   ├── 📄 __init__.py
│   │   │   │
│   │   │   ├── 📂 chatbot/
│   │   │   │   └── 📄 chatbot_service.py
│   │   │   │
│   │   │   ├── 📂 collector/
│   │   │   │   ├── 📄 orchestrator.py
│   │   │   │   ├── 📄 code_collector.py
│   │   │   │   ├── 📄 log_collector.py
│   │   │   │   └── 📄 db_collector.py
│   │   │   │
│   │   │   ├── 📂 analyzer/
│   │   │   │   ├── 📄 analyzer_service.py
│   │   │   │   └── 📄 diagnostics_engine.py
│   │   │   │
│   │   │   ├── 📂 knowledge_graph/
│   │   │   │   ├── 📄 graph_service.py
│   │   │   │   └── 📄 vector_store.py
│   │   │   │
│   │   │   └── 📂 validation/
│   │   │       ├── 📄 validation_service.py
│   │   │       └── 📄 user_service.py
│   │   │
│   │   ├── 📂 db/                       # Database setup
│   │   │   └── 📄 __init__.py
│   │   │
│   │   └── 📂 utils/                    # Utilitaires
│   │       └── 📄 __init__.py
│   │
│   └── 📂 tests/                        # Tests unitaires
│       └── 📄 __init__.py
│
├── 📂 frontend/                         # Frontend React
│   ├── 📄 package.json                  # Dépendances npm
│   ├── 📄 tsconfig.json                 # Config TypeScript
│   ├── 📄 vite.config.ts                # Config Vite
│   ├── 📄 tailwind.config.js            # Config TailwindCSS
│   ├── 📄 .env.example                  # Template env variables
│   ├── 📄 index.html                    # HTML principal
│   │
│   ├── 📂 src/
│   │   ├── 📄 main.tsx                  # Point d'entrée
│   │   ├── 📄 App.tsx                   # Composant racine
│   │   ├── 📄 index.css                 # Styles globaux
│   │   │
│   │   ├── 📂 components/               # Composants React
│   │   │   ├── 📄 Layout.tsx            # Layout principal
│   │   │   │
│   │   │   ├── 📂 chatbot/
│   │   │   │   ├── 📄 ChatInterface.tsx
│   │   │   │   └── 📄 ChatHistory.tsx
│   │   │   │
│   │   │   ├── 📂 dashboard/
│   │   │   │   ├── 📄 StatsCards.tsx
│   │   │   │   ├── 📄 ActivityChart.tsx
│   │   │   │   ├── 📄 RecentIssues.tsx
│   │   │   │   ├── 📄 KnowledgeSearch.tsx
│   │   │   │   └── 📄 KnowledgeGraph.tsx
│   │   │   │
│   │   │   └── 📂 validation/
│   │   │       ├── 📄 ValidationQueue.tsx
│   │   │       └── 📄 ValidationMetrics.tsx
│   │   │
│   │   ├── 📂 pages/                    # Pages
│   │   │   ├── 📄 ChatPage.tsx
│   │   │   ├── 📄 DashboardPage.tsx
│   │   │   ├── 📄 ValidationPage.tsx
│   │   │   ├── 📄 KnowledgePage.tsx
│   │   │   └── 📄 SettingsPage.tsx
│   │   │
│   │   ├── 📂 services/                 # Services API
│   │   │   └── 📄 api.ts                # Client API
│   │   │
│   │   └── 📂 utils/                    # Utilitaires
│   │       └── 📄 __init__.py
│   │
│   └── 📂 public/                       # Assets statiques
│
├── 📂 workers/                          # Workers Celery
│   ├── 📄 requirements.txt              # Dépendances workers
│   ├── 📄 celery_app.py                 # Config Celery
│   │
│   ├── 📂 code_analyzer/
│   │   └── 📄 tasks.py                  # Tâches analyse code
│   │
│   ├── 📂 log_analyzer/
│   │   └── 📄 tasks.py                  # Tâches analyse logs
│   │
│   ├── 📂 db_analyzer/
│   │   └── 📄 tasks.py                  # Tâches analyse DB
│   │
│   └── 📂 doc_analyzer/
│       └── 📄 tasks.py                  # Tâches analyse docs
│
├── 📂 infrastructure/                   # Infrastructure
│   │
│   ├── 📂 docker/                       # Dockerfiles
│   │   ├── 📄 backend.Dockerfile
│   │   ├── 📄 frontend.Dockerfile
│   │   └── 📄 worker.Dockerfile
│   │
│   ├── 📂 k8s/                          # Kubernetes manifests
│   │   ├── 📄 backend-deployment.yaml
│   │   ├── 📄 frontend-deployment.yaml
│   │   └── 📄 worker-deployment.yaml
│   │
│   └── 📂 terraform/                    # Infrastructure as Code
│
├── 📂 .github/                          # GitHub Actions
│   └── 📂 workflows/
│       └── 📄 ci-cd.yml                 # Pipeline CI/CD
│
├── 📂 docs/                             # Documentation
│   ├── 📄 ARCHITECTURE.md               # Architecture détaillée
│   ├── 📄 QUICKSTART.md                 # Guide démarrage rapide
│   ├── 📄 API.md                        # Documentation API
│   ├── 📄 DATA_MODEL.md                 # Modèle de données
│   ├── 📄 AI_WORKFLOW.md                # Workflow IA
│   ├── 📄 SECURITY.md                   # Sécurité
│   └── 📄 CONTRIBUTING.md               # Guide contribution
│
└── 📂 scripts/                          # Scripts utilitaires
    ├── 📄 setup.sh                      # Setup initial
    ├── 📄 deploy.sh                     # Déploiement
    └── 📄 backup.sh                     # Backup databases
```

## 📊 Statistiques du projet

- **Total fichiers** : ~100+
- **Langages** : Python, TypeScript, YAML, SQL
- **Services** : 8 (Backend, Frontend, 4 Workers, Flower, Databases)
- **Endpoints API** : 30+
- **Composants React** : 20+
- **Workers Celery** : 4 types d'analyseurs

## 🔑 Fichiers clés

| Fichier | Rôle | Importance |
|---------|------|------------|
| `backend/app/main.py` | Point d'entrée API | ⭐⭐⭐ |
| `backend/app/core/config.py` | Configuration | ⭐⭐⭐ |
| `frontend/src/App.tsx` | Application React | ⭐⭐⭐ |
| `docker-compose.yml` | Orchestration services | ⭐⭐⭐ |
| `workers/celery_app.py` | Configuration workers | ⭐⭐⭐ |
| `.github/workflows/ci-cd.yml` | Pipeline CI/CD | ⭐⭐ |

## 🎯 Points d'entrée

1. **Développement local** : `podman-compose up -d` ou `.\podman.ps1 up -Detached`
2. **Backend seul** : `cd backend && uvicorn app.main:app --reload`
3. **Frontend seul** : `cd frontend && npm run dev`
4. **Worker seul** : `cd workers && celery -A celery_app worker`

## 📦 Dépendances principales

### Backend
- FastAPI 0.109
- SQLAlchemy 2.0
- Celery 5.3
- OpenAI 1.10
- Neo4j 5.16

### Frontend
- React 18
- TypeScript 5
- TailwindCSS 3
- React Query 5
- Axios 1.6

## 🚀 Prochaines étapes

Après avoir créé l'arborescence :

1. ✅ Installer les dépendances : `cd backend && pip install -r requirements.txt`
2. ✅ Configurer les env : Copier `.env.example` vers `.env`
3. ✅ Lancer les services : `podman-compose up -d` (ou `.\podman.ps1 up -Detached`)
4. ✅ Accéder à l'app : http://localhost:3000
5. ✅ Tester l'API : http://localhost:8000/docs
