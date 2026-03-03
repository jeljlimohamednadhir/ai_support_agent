# 🤖 Genergy IA — Assistant Technique Intelligent

**Version 1.0.0** | ✅ Production Ready

Une plateforme complète d'assistance technique basée sur l'IA qui combine RAG (Retrieval-Augmented Generation), Knowledge Graph et Vector Store pour fournir des réponses expertes et traçables, avec **automatisation complète via Workers Celery**.

## 📋 Table des Matières

- [Vue d'ensemble](#-vue-densemble)
- [Fonctionnalités](#-fonctionnalités)
- [Architecture](#-architecture)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Utilisation](#-utilisation)
- [Documentation](#-documentation)
- [Technologies](#-technologies)
- [Développement](#-développement)
- [CI/CD](#-cicd)
- [Support](#-support)

## 🎯 Vue d'ensemble

**Genergy IA** est une solution complète qui :

- 🔍 **Recherche intelligente** : Vector store (Qdrant) + Knowledge Graph (Neo4j)
- 💬 **Chatbot RAG** : Réponses contextuelles avec sources citées
- 📊 **Visualisation** : Graphe de connaissances interactif
- ⚙️ **Configuration centralisée** : Tout gérable depuis l'UI
- 🤖 **Workers automatisés** : Sync Jira + Build Graph (Celery + Beat)
- 📈 **Monitoring temps réel** : Dashboard Flower pour les workers
- ✅ **Validation humaine** : Amélioration continue de l'IA
- 🚀 **Prêt pour la production** : Tests, CI/CD, documentation complète

### Cas d'usage

**Question** : "Qu'est-ce que la table t_ports et comment l'interroger ?"

**L'IA répond** :
- Description de la table et ses colonnes
- Relations avec d'autres tables (via le graphe)
- Exemples de requêtes SQL
- Fiches de résolution associées
- Sources traçables (liens vers la documentation)

## ✨ Fonctionnalités

### 🤖 Assistant Conversationnel
- Chatbot intelligent avec RAG
- Détection de requêtes déterministes (ex: "les 5 derniers Jira")
- Affichage des sources avec badges interactifs
- Historique des conversations
- Feedback utilisateur

### 🔄 Automatisation (Workers Celery)
- **Sync Jira** : Synchronisation automatique horaire des tickets
- **Build Graph** : Reconstruction du knowledge graph toutes les 6h
- **Monitoring Flower** : Dashboard temps réel sur port 5555
- **Celery Beat** : Planification flexible des tâches
- **Scalable** : Architecture multi-workers

### 📊 Base de Connaissances
- Visualisation du graphe (nodes + relations)
- Recherche sémantique
- Statistiques en temps réel
- Export des données

### ⚙️ Configuration Centralisée
- **LLM & IA** : Provider, modèle, température, tokens
- **Bases de données** : Neo4j, Qdrant, PostgreSQL
- **Interface** : Thème, langue, préférences
- **Jira** : URL, authentification, projet par défaut
- Chiffrement des valeurs sensibles

### 📈 Dashboard
- Statistiques globales
- Activité récente
- Métriques de performance
- Graphiques d'évolution

### ✅ Validation
- Validation des réponses de l'IA
- Corrections et feedback
- Amélioration continue

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React + TypeScript)             │
│  Chat │ Knowledge Graph │ Dashboard │ Validation │ Settings │
└─────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
                    ▼                   ▼
┌────────────────────────────────────────────────────────────┐
│                   Backend API (FastAPI)                     │
│  Chatbot │ Config │ Knowledge │ Validation │ Dashboard     │
└────────────────────────────────────────────────────────────┘
                    │
        ┌───────────┼───────────┬───────────┐
        ▼           ▼           ▼           ▼
   ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐
   │ Neo4j  │  │ Qdrant │  │Postgres│  │ Groq   │
   │(Graph) │  │(Vector)│  │  (DB)  │  │ (LLM)  │
   └────────┘  └────────┘  └────────┘  └────────┘
```

### Composants Principaux

- **Frontend** : React 18, TypeScript, Vite, TailwindCSS
- **Backend** : FastAPI, SQLAlchemy, Pydantic
- **Workers** : Celery + Redis (Jira Sync, Graph Builder, Analyzers)
- **Scheduler** : Celery Beat (tâches périodiques)
- **Monitoring** : Flower Dashboard (port 5555)
- **Knowledge Graph** : Neo4j (relations et corrélations)
- **Vector Store** : Qdrant (embeddings sémantiques)
- **LLM** : Groq (Llama), OpenAI, Anthropic
- **Database** : PostgreSQL (métadonnées, config)

## 🚀 Installation

### Prérequis

- **Python** 3.11+
- **Node.js** 18+
- **Docker** ou **Podman**
- **Neo4j** 5.x
- **Qdrant** 1.x

### 1. Cloner le Projet

```bash
git clone <repository-url>
cd ai-support-agent
```

### 2. Backend
           │              │              │              │
           ▼              ▼              ▼              ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  PostgreSQL  │  │    Redis     │  │    Neo4j     │  │   Qdrant     │
│  (Metadata)  │  │   (Cache)    │  │   (Graph)    │  │  (Vectors)   │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
                         │
                         ▼
           ┌───────────────────────────────┐
           │     Celery Workers (AI)        │
           │  Code│Logs│DB│Doc Analyzers   │
           └───────────────────────────────┘
```

## 🧭 Workflow

Le workflow décrit le parcours principal des données : collecte → analyse → indexation dans le graphe & vector store → réponses via le chatbot → validation humaine. Ci‑dessous deux représentations visuelles : une carte mentale et un schéma de workflow.

![Carte mentale](docs/mindmap.svg)

![Workflow](docs/workflow.svg)

**Démo interactive :** ouvrez `docs/workflow.html` dans votre navigateur pour une version animée et narrative du workflow (GSAP).

**Démo cinématique :** ouvrez `docs/workflow_cinematic.html` pour une expérience visuelle plus avancée (caméra, particules, timeline GSAP).


### Composants principaux

1. **Collecteur** : Git, Logs, Base de données, Documentation
2. **Analyseur IA** : Extraction règles métier, patterns, anomalies
3. **Knowledge Graph** : Neo4j + Qdrant pour relations et recherche sémantique
4. **Validation Humaine** : Interface pour corrections et amélioration
5. **Chatbot Expert** : LLM + RAG sur le graphe de connaissance
6. **Workers** : Analyse asynchrone en arrière-plan

## ✨ Fonctionnalités

### 🔍 Collecte Automatique
- ✅ Clone et analyse de dépôts Git
- ✅ Parsing de code (fonctions, classes, dépendances)
- ✅ Collecte de logs (fichiers, syslog, cloud)
- ✅ Introspection de schémas DB
- ✅ Indexation de documentation (Markdown, PDF, API specs)

### 🧠 Analyse IA
- ✅ Extraction de règles métier
- ✅ Analyse de flux applicatifs
- ✅ Détection d'anomalies dans les logs
- ✅ Identification de patterns d'erreurs
- ✅ Analyse de comportements

### 💬 Chatbot Expert
- ✅ Réponses contextuelles
- ✅ Diagnostic de problèmes
- ✅ Suggestions de solutions
- ✅ Références vers code/logs pertinents

### ✅ Validation & Amélioration
- ✅ Interface de validation humaine
- ✅ Corrections et feedback
- ✅ Métriques de qualité
- ✅ Amélioration continue

## 🚀 Installation

### ⚠️ Important : Podman au lieu de Docker

Ce projet utilise **Podman** comme moteur de conteneurisation (pas Docker).

**Pourquoi Podman ?**
- 🔒 **Rootless** : Plus sécurisé, pas besoin de droits admin
- 🐳 **Compatible Docker** : Même syntaxe, mêmes images
- 🏢 **Enterprise-ready** : Approuvé par Orange/RedHat
- 💰 **Gratuit** : Pas de licence commerciale requise

### Prérequis

- **Podman Desktop** + podman-compose
- Python 3.11+
- Node.js 20+ (pour le frontend)
- Git

### Installation rapide avec Podman (Recommandé)

#### 🪟 Windows

```powershell
# 1. Installer Podman Desktop
# Télécharger: https://podman-desktop.io/downloads

# 2. Installer podman-compose
pip install podman-compose

# 3. Cloner le projet
git clone <repo-url>
cd ai-support-agent

# 4. Configurer l'environnement
# Le fichier .env est déjà créé avec la clé Groq

# 5. Lancer avec le script PowerShell
.\podman.ps1 up -Detached

# Ou avec podman-compose
podman-compose up -d
```

#### 🐧 Linux (WSL/Ubuntu)

```bash
# 1. Installer Podman automatiquement
chmod +x install-podman.sh
./install-podman.sh

# 2. Recharger le terminal
source ~/.bashrc

# 3. Lancer l'application
podman-compose up -d
```

📖 **Guide complet Podman** : Voir [PODMAN_GUIDE.md](PODMAN_GUIDE.md)

#### ⚙️ Alternative avec Docker (non recommandé)

```bash
# Seulement si Docker est déjà installé et que vous ne pouvez pas utiliser Podman
docker-compose up -d
```

Les services seront disponibles sur :
- Frontend : http://localhost:3000 (ou 5173 en dev)
- Backend API : http://localhost:8000
- API Docs : http://localhost:8000/docs
- **Flower Dashboard** : http://localhost:5555 (Workers)
- Neo4j Browser : http://localhost:7474
- Qdrant : http://localhost:6333

### Démarrage des Workers ⚡

#### Windows (PowerShell)
```powershell
cd workers
.\start_workers.ps1

# Menu :
# 1 - Celery Worker (traitement tâches)
# 2 - Celery Beat (planification)
# 3 - Flower (monitoring)
# 4 - Tout démarrer
```

#### Linux/Mac (Bash)
```bash
cd workers
./start_workers.sh

# Même menu interactif
```

**Workers automatiques :**
- 🔄 Sync Jira toutes les heures
- 📊 Build Graph toutes les 6 heures
- 📈 Monitoring sur http://localhost:5555

### Installation manuelle

#### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Configurer .env
uvicorn app.main:app --reload
```

#### Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

#### Workers

```bash
cd workers
pip install -r requirements.txt
celery -A celery_app worker --loglevel=info
```

## ⚙️ Configuration

### Variables d'environnement essentielles

**Backend (.env)**
```env
# Base de données
POSTGRES_SERVER=localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DB=ai_support_agent

# IA/LLM
OPENAI_API_KEY=sk-...
LLM_PROVIDER=openai
LLM_MODEL=gpt-4-turbo-preview

# Neo4j (Knowledge Graph)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Jira (Workers)
JIRA_URL=https://your-company.atlassian.net
JIRA_USER=user@company.com
JIRA_TOKEN=your_jira_api_token
JIRA_PROJECT_KEY=PROJ

# Redis (Celery)
REDIS_URL=redis://localhost:6379/0

# Sécurité
SECRET_KEY=your-secret-key-min-32-characters
```

**Frontend (.env)**
```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

## 📖 Utilisation

### 1. Collecter les données

```bash
# Via API
curl -X POST http://localhost:8000/api/v1/collector/collect/code \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/user/repo", "branch": "main"}'
```

### 2. Analyser avec l'IA

```bash
curl -X POST http://localhost:8000/api/v1/analyzer/analyze/behavior \
  -H "Content-Type: application/json" \
  -d '{"scenario": "Que se passe-t-il quand un user non vérifié accède à admin?"}'
```

### 3. Utiliser le chatbot

Ouvrir http://localhost:3000/chat et poser vos questions !

### 4. Valider les insights

Aller sur http://localhost:3000/validation pour approuver/corriger les insights générés par l'IA.

## 🛠️ Développement

### Structure du projet

```
ai-support-agent/
├── backend/              # API FastAPI
│   ├── app/
│   │   ├── api/         # Endpoints REST
│   │   ├── core/        # Configuration, sécurité
│   │   ├── models/      # Modèles DB
│   │   ├── schemas/     # Schémas Pydantic
│   │   └── services/    # Logique métier
│   └── tests/
├── frontend/            # Interface React
│   ├── src/
│   │   ├── components/  # Composants UI
│   │   ├── pages/       # Pages
│   │   └── services/    # API client
├── workers/             # Workers Celery
│   ├── code_analyzer/
│   ├── log_analyzer/
│   ├── db_analyzer/
│   └── doc_analyzer/
├── infrastructure/      # Docker, K8s, Terraform
│   ├── docker/
│   └── k8s/
└── docs/               # Documentation
```

### Lancer les tests

```bash
# Backend
cd backend
pytest tests/ --cov=app

# Frontend
cd frontend
npm test
```

### Ajouter un nouveau endpoint

1. Créer le endpoint dans `backend/app/api/v1/endpoints/`
2. Ajouter le schéma dans `backend/app/schemas/`
3. Implémenter la logique dans `backend/app/services/`
4. Ajouter les tests dans `backend/tests/`

## 🚢 Déploiement

### Podman Compose (Développement/Staging)

```bash
# Windows (avec script PowerShell)
.\podman.ps1 up -Detached

# Ou avec podman-compose
podman-compose up -d
```

### Kubernetes (Production)

```bash
# Appliquer les manifests
kubectl apply -f infrastructure/k8s/

# Vérifier le déploiement
kubectl get pods
kubectl get services
```

### CI/CD

Le pipeline GitHub Actions :
1. Teste backend et frontend
2. Build les images Docker
3. Push vers le registry
4. Déploie sur Kubernetes

## 🔧 Technologies

### Backend
- **FastAPI** : Framework web Python asynchrone
- **SQLAlchemy** : ORM pour PostgreSQL
- **Celery + Beat** : Queue de tâches + planification
- **Redis** : Broker Celery et cache
- **Neo4j** : Base de données graphe
- **Qdrant** : Vector store pour recherche sémantique
- **Jira API** : Intégration tickets (workers)

### Frontend
- **React 18** : Library UI
- **TypeScript** : Typage statique
- **TailwindCSS** : Framework CSS
- **React Query** : Gestion état serveur
- **Vite** : Build tool

### Workers & Automation
- **Celery** : Tâches asynchrones distribuées
- **Celery Beat** : Planification (cron-like)
- **Flower** : Monitoring workers (dashboard web)
- **Redis** : Broker et backend Celery
- **Jira Library** : Client Python pour Jira API

### IA/ML
- **OpenAI GPT-4** : Génération et analyse
- **Anthropic Claude** : Alternative LLM
- **LangChain** : Orchestration LLM
- **Sentence Transformers** : Embeddings

### Infrastructure
- **Podman** : Conteneurisation (alternative rootless à Docker)
- **Kubernetes** : Orchestration
- **GitHub Actions** : CI/CD
- **Prometheus** : Monitoring
- **Grafana** : Visualisation

## 📚 Documentation complémentaire

### Guides Principaux
- [**FINAL_COMPLETION.md**](FINAL_COMPLETION.md) - ✅ Guide complet du projet finalisé
- [**WORKERS_GUIDE.md**](docs/WORKERS_GUIDE.md) - 🤖 Guide détaillé des workers Celery
- [**DEV_GUIDE.md**](docs/DEV_GUIDE.md) - Architecture et développement
- [**USER_GUIDE.md**](docs/USER_GUIDE.md) - Guide utilisateur de l'interface

### Documentation Technique
- [Architecture détaillée](docs/ARCHITECTURE.md)
- [Guide API](docs/API.md)
- [Modèle de données](docs/DATA_MODEL.md)
- [Workflow IA](docs/AI_WORKFLOW.md)
- [Sécurité](docs/SECURITY.md)

### Planification Scrum
- [Plan Projet](docs/PROJECT_PLAN.md)
- [Roadmap](docs/ROADMAP.md)
- [Timeline](docs/TIMELINE.md)
- [User Stories](docs/USER_STORIES.md)
- [Sprint Backlog](docs/SPRINT_BACKLOG.md)

### Podman
- [Guide Podman](PODMAN_GUIDE.md)
- [Migration Docker → Podman](PODMAN_MIGRATION.md)
- [Setup Podman](PODMAN_SETUP.md)

## 🤝 Contribution

Les contributions sont les bienvenues ! Voir [CONTRIBUTING.md](docs/CONTRIBUTING.md)

## 📄 Licence

MIT License - voir [LICENSE](LICENSE)

## 👥 Support

- Issues GitHub : [github.com/user/ai-support-agent/issues](https://github.com)
- Email : support@example.com
- Documentation : [docs.example.com](https://docs.example.com)

---

**Fait avec ❤️ pour améliorer le support technique**
