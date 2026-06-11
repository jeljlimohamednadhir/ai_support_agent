# 📁 Structure du projet — BRASIL N3 Forensic AI Platform

> Dernière mise à jour : Mai 2026 · Version 2.0.0

```
ai-support-agent/
│
├── 📄 README.md                          # Documentation principale (v2.0)
├── 📄 LICENSE                            # Licence MIT
├── 📄 .gitignore
├── 📄 docker-compose.yml                 # Orchestration Docker/Podman
├── 📄 QUICKSTART.md                      # Démarrage rapide
├── 📄 QUICKSTART_ML.md                   # Guide ML classifier
├── 📄 STRUCTURE.md                       # Ce fichier
│
├── 📁 backend/                           # Backend API FastAPI (Python 3.13)
│   ├── 📄 requirements.txt
│   ├── 📄 .env / .env.example
│   │
│   ├── 📁 app/                           # Application principale
│   │   ├── 📄 main.py                    # Point d'entrée FastAPI + lifespan
│   │   │
│   │   ├── 📁 api/v1/endpoints/          # Endpoints REST
│   │   │   ├── chatbot.py               # POST /chatbot/chat
│   │   │   ├── chat.py                  # Conversations & messages
│   │   │   ├── collector.py             # Collecte tickets Jira
│   │   │   ├── knowledge.py             # Knowledge graph
│   │   │   ├── validation.py            # Queue validation N3
│   │   │   ├── diagnostics.py           # Rapports diagnostics
│   │   │   ├── classification_ml.py     # Classification ML
│   │   │   └── users.py                 # Gestion utilisateurs
│   │   │
│   │   ├── 📁 core/
│   │   │   ├── config.py                # Settings Pydantic
│   │   │   ├── security.py              # JWT auth
│   │   │   └── llm_client.py            # Client Groq (qwen/qwen3-32b · 6000 TPM)
│   │   │
│   │   ├── 📁 models/                   # SQLAlchemy ORM
│   │   │
│   │   └── 📁 services/
│   │       │
│   │       ├── 📁 chatbot/              # ── CŒUR DU CHATBOT ──────────────────
│   │       │   ├── chatbot_service.py           # Orchestration principale (~3500 lignes)
│   │       │   │                                 # Intent routing · forensic pipeline
│   │       │   │                                 # Semantic Router · Truth Engine wired
│   │       │   │
│   │       │   ├── truth_enforcement.py         # Phase 1 — Moteur de vérité
│   │       │   │                                 # Bloque SQL mutations / shell / placeholders
│   │       │   │                                 # Valide tables/fonctions contre index réel
│   │       │   │
│   │       │   ├── semantic_intent_router.py    # Phase 2 — Routeur sémantique V2
│   │       │   │                                 # 25 catégories opérationnelles
│   │       │   │                                 # Français N3 · télécom · multi-label
│   │       │   │
│   │       │   ├── provenance_engine.py         # Phase 3 — Provenance
│   │       │   │                                 # ProvenanceRecord · ProvenanceEngine
│   │       │   │                                 # Footer "Sources" automatique
│   │       │   │
│   │       │   ├── workflow_intelligence.py     # Phase 4 — Workflow Intelligence
│   │       │   │                                 # DSLAM/VLAN/équipements depuis code+FR
│   │       │   │                                 # Jamais d'étapes inventées
│   │       │   │
│   │       │   ├── response_quality.py          # Phases 6+7 — Qualité réponse
│   │       │   │                                 # enforce_readonly_sql() · full_quality_check()
│   │       │   │                                 # 50+ patterns filler supprimés
│   │       │   │
│   │       │   ├── forensic_followup.py         # Handlers forensiques déterministes
│   │       │   │                                 # 17 intents · user_query parsing
│   │       │   │                                 # Provenance footer dans chaque handler
│   │       │   │
│   │       │   ├── forensic_memory.py           # Mémoire cross-tour (2h TTL · LRU 200)
│   │       │   │                                 # ForensicSnapshot · ForensicMemoryStore
│   │       │   │
│   │       │   ├── intent_resolver.py           # IntentResolver — regex patterns
│   │       │   │                                 # FORENSIC_INTENTS set · 25 intents
│   │       │   │
│   │       │   ├── conversation_state.py        # State machine conversation
│   │       │   │                                 # ConversationStateStore · TTL 2h · LRU
│   │       │   │
│   │       │   ├── incident_context_guard.py    # ContextGuard (lock/exclude systems)
│   │       │   ├── correlation_engine.py        # Corrélation multi-sources
│   │       │   ├── multi_source_correlator.py   # Corrélation Jira + logs + KB
│   │       │   ├── response_humanizer.py        # Humanisation (skippée en N3 mode)
│   │       │   ├── knowledge_layer.py           # Couche accès KB
│   │       │   ├── learning_loop.py             # Boucle apprentissage
│   │       │   ├── validation_layer.py          # Validation réponses
│   │       │   ├── forensic_formatter.py        # Formateur forensique
│   │       │   ├── maintenance.py               # Tâches maintenance
│   │       │   ├── n3_chatbot_orchestrator.py   # Orchestrateur N3
│   │       │   ├── response_generator.py        # Générateur réponses
│   │       │   ├── sfd_parser.py                # Parser SFD
│   │       │   ├── incident_graph.py            # Graphe incidents
│   │       │   └── sfd_reasoning.py             # Raisonnement SFD
│   │       │
│   │       ├── 📁 live_diagnostics/     # ── DIAGNOSTICS LIVE ──────────────────
│   │       │   ├── evidence_provenance.py       # EvidenceProvenance · SourceType
│   │       │   │                                 # provenance_from_log/db/code/fr/qdrant
│   │       │   ├── diagnostic_orchestrator.py   # Orchestrateur SSH+DB
│   │       │   ├── stability_guards.py          # sanitize_for_llm · TPM guard
│   │       │   │
│   │       │   ├── 📁 logs/
│   │       │   │   ├── log_reader.py            # SSH log reader
│   │       │   │   ├── log_parser.py            # Parser structured log events
│   │       │   │   └── log_correlation_engine.py # Hypothèses de corrélation
│   │       │   │
│   │       │   ├── 📁 timeline/
│   │       │   │   └── timeline_builder.py      # Reconstruction chronologie incidents
│   │       │   │
│   │       │   └── 📁 planners/
│   │       │       └── diagnostic_planner.py    # intent_from_message()
│   │       │
│   │       ├── 📁 code_intelligence/    # ── INTELLIGENCE CODE JAVA ────────────
│   │       │   ├── operation_graph.py           # 65 mappings intent → opération Java
│   │       │   │                                 # INTENT_TO_OPERATION · resolve()
│   │       │   ├── function_knowledge_index.py  # Index mot-clé → méthode Java
│   │       │   │                                 # _OP_SYNONYMS (16 entrées FR)
│   │       │   └── 📁 extractors/
│   │       │       └── brasil_extractor.py      # search_code_knowledge()
│   │       │
│   │       ├── 📁 pipeline/             # ── PIPELINE RAG ─────────────────────
│   │       │   ├── mode1_fr_rich.py             # Mode riche (KB complète)
│   │       │   └── mode2_fr_weak.py             # Mode faible (Qdrant hybrid)
│   │       │                                     # _schema_priority · merge conditionnel
│   │       │
│   │       ├── 📁 knowledge/            # ── BASE DE CONNAISSANCE ──────────────
│   │       │   ├── vector_service.py            # Client Qdrant
│   │       │   ├── graph_service.py             # Neo4j (lazy)
│   │       │   └── orchestrator.py              # Pipeline orchestrator
│   │       │
│   │       ├── 📁 nlp/                  # ── NLP ──────────────────────────────
│   │       │   ├── diagnostic_behavior.py       # Intent · trust gate
│   │       │   │                                 # BRASIL_SCHEMA_TABLES (128 tables)
│   │       │   ├── enricher.py                  # StructuredTicket enricher
│   │       │   └── smart_n3_parser.py           # Parser N3 tickets
│   │       │
│   │       ├── 📁 diagnostic/
│   │       │   └── diagnostic_engine.py         # Moteur diagnostic N3
│   │       │
│   │       └── 📁 collector/
│   │           └── jira_collector.py            # Sync Jira
│   │
│   ├── 📁 tests/                        # ── TESTS ───────────────────────────
│   │   ├── run_tests.py                 # Tests intégration E2E (serveur requis)
│   │   ├── run_new_tests.py             # Tests nouveaux moteurs (E2E)
│   │   ├── test_truth_enforcement.py    # 24 tests — SQL/shell/placeholder
│   │   ├── test_provenance.py           # 22 tests — ProvenanceRecord + Engine
│   │   ├── test_semantic_router.py      # 32 tests — 25 catégories · multi-label
│   │   ├── test_workflow_intelligence.py # 32 tests — workflows · safety
│   │   ├── test_chatbot_service.py
│   │   ├── test_diagnostics_engine.py
│   │   ├── test_graph_service.py
│   │   ├── test_validation_service.py
│   │   └── 📁 legacy/                  # Anciens tests (archivés — non exécutés)
│   │
│   ├── 📁 scripts/
│   │   ├── 📁 knowledge/               # Injection base de connaissance
│   │   │   ├── inject_all_fr.py        # Indexe toutes les FRs (--force · --list)
│   │   │   ├── inject_fr_batch.py      # Injection par lot
│   │   │   └── inject_fr189.py
│   │   └── 📁 maintenance/             # Scripts admin (archivés)
│   │       ├── create_or_update_admin.py
│   │       ├── init_db_simple.py
│   │       ├── migrate_sqlite_to_postgres.py
│   │       └── ... (30+ scripts)
│   │
│   ├── 📁 FR/                          # 51 Fiches de Résolution BRASIL (.docx)
│   │   ├── FR 189 Suppression DSLAM impossible.docx
│   │   ├── FR 190 Suppression VLAN IMPOSSIBLE.docx
│   │   └── ... (49 autres FRs)
│   │
│   ├── 📁 apps/brasil/
│   │   └── context.json                # Config applicative BRASIL
│   │
│   └── 📁 data/
│       ├── model_card.json             # Métriques ML classifier
│       ├── ml_corrections.jsonl        # Corrections RLHF
│       └── execution_graph_cache.json  # Cache graph Java (généré au 1er démarrage)
│
├── 📁 frontend/                        # Frontend React + TypeScript + Vite
│   └── src/
│       ├── 📁 components/
│       ├── 📁 pages/
│       └── 📁 services/
│
├── 📁 docs/
│   ├── 📁 history/                     # Rapports de phases archivés
│   │   ├── COMPLETION_REPORT.md
│   │   ├── FINAL_COMPLETION.md
│   │   ├── PODMAN_GUIDE.md
│   │   └── ... (12 fichiers)
│   └── ... (guides techniques)
│
├── 📁 scripts/                         # Scripts racine
│   ├── analyze_nd.py
│   ├── brasil_knowledge_pipeline.py
│   └── podman.ps1
│
├── 📁 infrastructure/                  # Docker · K8s · Terraform
├── 📁 workers/                         # Workers Celery
└── 📁 data_pipeline/                   # Pipeline de données
```

---

## 🔑 Fichiers clés

| Fichier | Rôle | Lignes |
|---|---|---|
| `services/chatbot/chatbot_service.py` | Orchestration principale | ~3 500 |
| `services/chatbot/truth_enforcement.py` | Moteur de vérité — bloque hallucinations | ~310 |
| `services/chatbot/semantic_intent_router.py` | Routeur 25 catégories | ~350 |
| `services/chatbot/provenance_engine.py` | Sources automatiques | ~260 |
| `services/chatbot/workflow_intelligence.py` | Workflows opérationnels | ~280 |
| `services/chatbot/forensic_followup.py` | 17 handlers forensiques | ~666 |
| `services/chatbot/forensic_memory.py` | Mémoire cross-tour TTL 2h | ~200 |
| `services/chatbot/intent_resolver.py` | Résolution intents regex | ~438 |
| `services/chatbot/response_quality.py` | Anti-hallucination · SQL readonly | ~320 |
| `services/code_intelligence/operation_graph.py` | 65 mappings intent→Java | ~250 |
| `services/nlp/diagnostic_behavior.py` | 128 tables · trust gate | ~1 513 |
| `services/live_diagnostics/evidence_provenance.py` | Provenance bas niveau | ~224 |

---

## 🧪 Suite de tests

```
tests/test_truth_enforcement.py     → 24 tests  ✅
tests/test_provenance.py            → 22 tests  ✅
tests/test_semantic_router.py       → 32 tests  ✅
tests/test_workflow_intelligence.py → 32 tests  ✅
                                       ─────────
                                Total: 110 tests · 0 échec · 0 régression
```
