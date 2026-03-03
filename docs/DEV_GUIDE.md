# Guide de Développement — Genergy IA

## Vue d'ensemble

Genergy IA est une plateforme d'assistance technique basée sur l'IA qui combine :
- **RAG (Retrieval-Augmented Generation)** : Vector store (Qdrant) + Knowledge Graph (Neo4j)
- **Backend FastAPI** : API REST pour chatbot, collecte, analyse et configuration
- **Frontend React/TypeScript** : Interface utilisateur moderne avec Vite et TailwindCSS
- **Workers Celery** : Tâches asynchrones pour indexation et analyse

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Frontend   │────▶│   Backend    │────▶│   Neo4j     │
│  (React)    │     │  (FastAPI)   │     │  (Graph)    │
└─────────────┘     └──────────────┘     └─────────────┘
                           │
                           ├────▶ Qdrant (Vectors)
                           │
                           ├────▶ PostgreSQL (Metadata)
                           │
                           └────▶ Workers (Celery)
```

## Stack Technique

### Backend
- **Python 3.11+**
- **FastAPI** : Framework web rapide et moderne
- **SQLAlchemy** : ORM pour PostgreSQL
- **Neo4j Python Driver** : Accès au knowledge graph
- **Qdrant Client** : Vector store pour embeddings
- **Sentence Transformers** : Génération d'embeddings
- **Groq/OpenAI/Anthropic** : LLM providers

### Frontend
- **React 18** avec TypeScript
- **Vite** : Build tool rapide
- **TailwindCSS** : Styling utility-first
- **React Query** : State management et cache
- **React Markdown** : Rendu markdown
- **React Force Graph** : Visualisation du graphe

### Infrastructure
- **Docker/Podman** : Conteneurisation
- **GitHub Actions** : CI/CD
- **Kubernetes** : Orchestration (optionnel)

## Structure du Projet

```
ai-support-agent/
├── backend/               # API FastAPI
│   ├── app/
│   │   ├── api/v1/       # Endpoints API
│   │   ├── core/         # Config, security, logging
│   │   ├── models/       # Modèles SQLAlchemy
│   │   ├── schemas/      # Schémas Pydantic
│   │   ├── services/     # Logique métier
│   │   └── utils/        # Utilitaires
│   ├── tests/            # Tests unitaires/intégration
│   └── requirements.txt
├── frontend/             # UI React
│   ├── src/
│   │   ├── components/   # Composants réutilisables
│   │   ├── pages/        # Pages principales
│   │   ├── services/     # API client
│   │   └── utils/        # Helpers
│   └── package.json
├── workers/              # Workers Celery
├── infrastructure/       # Docker, K8s, Terraform
└── docs/                 # Documentation
```

## Configuration Système

### Variables d'Environnement

Backend `.env`:
```bash
# LLM
GROQ_API_KEY=your_groq_key
OPENAI_API_KEY=your_openai_key

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333

# PostgreSQL (optionnel)
DATABASE_URL=postgresql://user:pass@localhost:5432/genergy

# Redis (pour Celery)
REDIS_URL=redis://localhost:6379/0
```

Frontend `.env`:
```bash
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

### Configuration via UI

Toutes les configurations peuvent être gérées via l'interface web :
- **Paramètres → LLM & IA** : Provider, modèle, température, tokens
- **Paramètres → Bases de données** : Neo4j, Qdrant, PostgreSQL
- **Paramètres → Interface** : Thème, langue, préférences

## Installation & Démarrage

### Prérequis

- Python 3.11+
- Node.js 18+
- Docker/Podman
- Neo4j
- Qdrant

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Services (Docker/Podman)

```bash
# Démarrer Neo4j et Qdrant
podman run -d --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest

podman run -d --name qdrant \
  -p 6333:6333 -p 6334:6334 \
  qdrant/qdrant:latest
```

## Endpoints API Principaux

### Configuration
- `GET /api/v1/config/` : Récupérer toute la configuration
- `PUT /api/v1/config/{key}` : Mettre à jour une clé
- `POST /api/v1/config/bulk` : Mise à jour en masse
- `POST /api/v1/config/reset` : Réinitialiser

### Chatbot
- `POST /api/v1/chatbot/chat` : Envoyer un message
- `GET /api/v1/chatbot/conversations/{id}` : Historique
- `POST /api/v1/chatbot/feedback` : Soumettre un feedback

### Knowledge Graph
- `GET /api/v1/knowledge/graph` : Données du graphe
- `POST /api/v1/knowledge/search` : Recherche sémantique
- `GET /api/v1/knowledge/stats` : Statistiques

### Dashboard
- `GET /api/v1/dashboard/stats` : Statistiques globales
- `GET /api/v1/dashboard/activity` : Activité récente

## Tests

### Backend

```bash
cd backend
pytest tests/ -v --cov=app
```

### Frontend

```bash
cd frontend
npm test
npm run test:e2e
```

### CI/CD

Le pipeline GitHub Actions exécute automatiquement :
- Tests backend (avec Neo4j et Qdrant)
- Tests frontend
- Linting et formatage
- Build Docker images

## Développement

### Ajouter un Endpoint

1. Créer le schéma dans `backend/app/schemas/`
2. Créer l'endpoint dans `backend/app/api/v1/endpoints/`
3. Enregistrer dans `backend/app/api/v1/api.py`
4. Ajouter des tests dans `backend/tests/`

### Ajouter une Page Frontend

1. Créer le composant dans `frontend/src/pages/`
2. Ajouter la route dans `App.tsx`
3. Créer les composants associés dans `components/`

### Ajouter un Service

1. Créer le service dans `backend/app/services/`
2. Implémenter la logique métier
3. Exposer via endpoints API
4. Ajouter tests unitaires

## Déploiement

### Docker Compose

```bash
docker-compose up -d
```

### Kubernetes

```bash
kubectl apply -f infrastructure/k8s/
```

## Monitoring & Observabilité

- **Logs** : Centralisés dans `backend/logs/`
- **Métriques** : Prometheus (à venir)
- **Traces** : OpenTelemetry (à venir)
- **Health checks** : `/health` endpoint

## Contribution

1. Fork le projet
2. Créer une branche feature (`git checkout -b feature/AmazingFeature`)
3. Commit les changements (`git commit -m 'Add AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

## Support

- **Documentation** : `docs/`
- **Issues** : GitHub Issues
- **Email** : support@genergy-ia.com (à configurer)

## Licence

Propriétaire - Orange © 2026
