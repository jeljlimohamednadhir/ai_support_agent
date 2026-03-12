# ?? Structure du projet AI Support Agent

> Dernière mise à jour : Mars 2026

```
ai-support-agent/
¦
+-- ?? README.md                          # Documentation principale
+-- ?? LICENSE                            # Licence MIT
+-- ?? .gitignore                         # Fichiers à ignorer
+-- ?? docker-compose.yml                 # Orchestration Docker/Podman
¦
+-- ?? backend/                           # Backend API FastAPI (Python 3.13)
¦   +-- ?? requirements.txt              # Dépendances Python
¦   +-- ?? .env.example                  # Template variables d'environnement
¦   ¦
¦   +-- ?? app/                          # Application principale
¦   ¦   +-- ?? main.py                   # Point d'entrée FastAPI + lifespan
¦   ¦   ¦
¦   ¦   +-- ?? api/v1/endpoints/         # Endpoints REST
¦   ¦   ¦   +-- ?? chatbot.py            # POST /chatbot/chat
¦   ¦   ¦   +-- ?? chat.py               # Conversations & messages
¦   ¦   ¦   +-- ?? collector.py          # Collecte tickets Jira
¦   ¦   ¦   +-- ?? knowledge.py          # Knowledge graph
¦   ¦   ¦   +-- ?? validation.py         # Queue validation N3
¦   ¦   ¦   +-- ?? diagnostics.py        # Rapports diagnostics
¦   ¦   ¦   +-- ?? classification_ml.py  # Classification ML
¦   ¦   ¦   +-- ?? hierarchical_ml.py    # Classificateur hiérarchique
¦   ¦   ¦   +-- ?? users.py              # Gestion utilisateurs
¦   ¦   ¦
¦   ¦   +-- ?? core/                     # Config & utilitaires
¦   ¦   ¦   +-- ?? config.py             # Settings Pydantic
¦   ¦   ¦   +-- ?? security.py           # JWT auth
¦   ¦   ¦   +-- ?? llm_client.py         # Client Groq (qwen/qwen3-32b)
¦   ¦   ¦
¦   ¦   +-- ?? models/                   # SQLAlchemy ORM
¦   ¦   ¦   +-- ?? user.py               # Utilisateurs & rôles
¦   ¦   ¦   +-- ?? canonical.py          # Procédures canoniques
¦   ¦   ¦   +-- ?? classification_ml.py  # Corrections ML
¦   ¦   ¦
¦   ¦   +-- ?? services/
¦   ¦   ¦   ¦
¦   ¦   ¦   +-- ?? chatbot/              # Cœur du chatbot
¦   ¦   ¦   ¦   +-- ?? chatbot_service.py         # Orchestration principale
¦   ¦   ¦   ¦   ¦                                   # intent routing, _FOLLOWUP_PATTERNS
¦   ¦   ¦   ¦   ¦                                   # _PROC_CONTEXT_PATTERN (guard FR)
¦   ¦   ¦   ¦   ¦                                   # _extract_equipment_name (DSLAM/NRO)
¦   ¦   ¦   ¦   +-- ?? incident_context_guard.py   # ContextGuard (lock/exclude systems)
¦   ¦   ¦   ¦
¦   ¦   ¦   +-- ?? pipeline/             # Pipeline RAG
¦   ¦   ¦   ¦   +-- ?? mode1_fr_rich.py  # Mode riche (base de connaissances complète)
¦   ¦   ¦   ¦   +-- ?? mode2_fr_weak.py  # Mode faible (FR docs + Qdrant hybrid)
¦   ¦   ¦   ¦                             # _schema_priority, _search_brasil_procedures
¦   ¦   ¦   ¦                             # merge conditionnel incident/schema
¦   ¦   ¦   ¦
¦   ¦   ¦   +-- ?? knowledge/            # Base de connaissance
¦   ¦   ¦   ¦   +-- ?? vector_service.py          # Qdrant client
¦   ¦   ¦   ¦   ¦                                   # search_similar_code, _scroll_tables
¦   ¦   ¦   ¦   +-- ?? graph_service.py            # Neo4j graph (lazy)
¦   ¦   ¦   ¦   +-- ?? orchestrator.py             # Pipeline orchestrator
¦   ¦   ¦   ¦
¦   ¦   ¦   +-- ?? nlp/                  # Traitement du langage
¦   ¦   ¦   ¦   +-- ?? diagnostic_behavior.py      # Intent detection + trust gate
¦   ¦   ¦   ¦   ¦                                   # BRASIL_SCHEMA_TABLES (128 tables)
¦   ¦   ¦   ¦   +-- ?? smart_n3_parser.py          # Parser N3 tickets
¦   ¦   ¦   ¦
¦   ¦   ¦   +-- ?? collector/            # Collecte Jira
¦   ¦   ¦   ¦   +-- ?? jira_collector.py
¦   ¦   ¦   ¦
¦   ¦   ¦   +-- ?? diagnostic/
¦   ¦   ¦   ¦   +-- ?? diagnostic_engine.py
¦   ¦   ¦   ¦
¦   ¦   ¦   +-- ?? ml_classifier.py      # Classificateur ML (TF-IDF + ST)
¦   ¦   ¦   +-- ?? hierarchical_classifier.py  # KNN L1 + LR L2 + Groq fallback
¦   ¦   ¦
¦   ¦   +-- ?? db/                       # Database (PostgreSQL + SQLAlchemy)
¦   ¦       +-- ?? session.py
¦   ¦
¦   +-- ?? apps/brasil/                  # Config applicative BRASIL
¦   ¦   +-- ?? context.json              # Tables, glossaire, prompts
¦   ¦
¦   +-- ?? FR/                           # 51 Fiches de Resolution BRASIL (docx)
¦   ¦   +-- FR 001 CalculerToc.docx
¦   ¦   +-- FR 188 Suppression BAS ou ROUTEUR impossible.docx
¦   ¦   +-- FR 189 Suppression DSLAM impossible.docx
¦   ¦   +-- FR 190 Suppression VLAN IMPOSSIBLE.docx
¦   ¦   +-- FR 191 Suppression en masse de cartes.docx
¦   ¦   +-- ... (47 autres FRs)
¦   ¦
¦   +-- ?? scripts/                      # Scripts maintenance & injection
¦   ¦   +-- ?? knowledge/               # Injection base de connaissance
¦   ¦       +-- ?? inject_all_fr.py      # Indexe TOUTES les FRs (--force, --list)
¦   ¦       +-- ?? inject_fr_batch.py    # Injection par lot (FR 188/190/191)
¦   ¦       +-- ?? inject_fr189.py       # Injection initiale FR 189
¦   ¦
¦   +-- ?? data/                         # Donnees persistantes
¦       +-- ?? model_card.json           # Metriques ML classifier
¦       +-- ?? ml_corrections.jsonl      # Corrections RLHF
¦
+-- ?? frontend/                         # Frontend React + TypeScript + Vite
¦   +-- ?? package.json
¦   +-- ?? tsconfig.json
¦   +-- ?? vite.config.ts
¦   +-- ?? src/
¦       +-- ?? components/chatbot/
¦       ¦   +-- ?? ChatInterface.tsx     # Interface chat principale
¦       +-- ?? pages/
¦       ¦   +-- ?? DashboardPage.tsx
¦       ¦   +-- ?? KnowledgePage.tsx
¦       ¦   +-- ?? ValidationPage.tsx
¦       ¦   +-- ?? ClassificationMLPage.tsx
¦       +-- ?? services/
¦           +-- ?? classificationMLService.ts
¦
+-- ?? data_pipeline/                    # Pipeline donnees Jira -> training
¦   +-- ?? fr_parser.py                  # Parser FRs .docx
¦   +-- ?? build_labeled_dataset.py      # Construction dataset ML
¦
+-- ?? docs/                             # Documentation
¦   +-- ?? chatbot_reference.html        # Reference API chatbot
¦   +-- ?? documentation.html           # Documentation complete
¦
+-- ?? infrastructure/                   # Docker/Podman
    +-- ?? docker/
```

---

## Collections Qdrant

| Collection | Points | Contenu |
|---|---|---|
| `brasil_procedures` | **82** | 51 FRs indexees + procedures canoniques |
| `code_knowledge` | **197** | 128 tables BRASIL + procedures schema |
| `brasil_log_patterns` | **12** | Patterns erreurs logs |

---

## Fichiers cles

| Fichier | Role | Statut |
|---|---|---|
| `backend/app/services/chatbot/chatbot_service.py` | Orchestration chatbot, intent routing | ? actif |
| `backend/app/services/chatbot/incident_context_guard.py` | Lock/exclude systemes incidents | ? actif |
| `backend/app/services/pipeline/mode2_fr_weak.py` | Pipeline RAG hybride (merge conditionnel) | ? actif |
| `backend/app/services/knowledge/vector_service.py` | Qdrant + fuzzy keyword search | ? actif |
| `backend/app/services/nlp/diagnostic_behavior.py` | Intent detection + trust gate + 128 tables | ? actif |
| `backend/scripts/knowledge/inject_all_fr.py` | Indexation batch des 51 FRs | ? actif |

---

## Demarrage rapide

```powershell
# Backend
cd backend
.venv/Scripts/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend
cd frontend
npm run dev

# Re-indexer toutes les FRs
cd backend
.venv/Scripts/python.exe scripts/knowledge/inject_all_fr.py          # incremental
.venv/Scripts/python.exe scripts/knowledge/inject_all_fr.py --force  # tout re-indexer
.venv/Scripts/python.exe scripts/knowledge/inject_all_fr.py --list   # lister sans indexer
```

---

## Statistiques

- **FRs indexees** : 51 (FR 001 a FR 999)
- **Tables BRASIL indexees** : 128
- **Endpoints API** : 25+
- **Pipeline modes** : 2 (FR_RICH / FR_WEAK)
- **LLM** : Groq `qwen/qwen3-32b`
- **Embedding** : `paraphrase-multilingual-MiniLM-L12-v2` (dim=384)
