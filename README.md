# 🧠 BRASIL N3 — Forensic AI Support Platform

**Version 2.0.0** | ✅ Production Ready — Stabilization Pass Complete

Plateforme d'assistance forensique N3 pour le système **BRASIL** (Orange Telecom).  
Combine RAG, intelligence du code source Java, diagnostics live SSH/PostgreSQL, et un moteur de vérité déterministe pour assister les ingénieurs N3 sans hallucination.

> **Branche active** : `feature/multi-tenant-intelligence-platform`  
> **LLM** : Groq `qwen/qwen3-32b` (formateur uniquement — jamais source de vérité)  
> **Embedding** : `paraphrase-multilingual-MiniLM-L12-v2` (dim=384)  
> **Base de connaissance** : 51 FRs indexées · 128 tables BRASIL · ~3 200 fichiers Java analysés

## 📋 Table des Matières

- [Vue d'ensemble](#-vue-densemble)
- [Architecture](#-architecture)
- [Démarrage rapide](#-démarrage-rapide)
- [Fonctionnalités](#-fonctionnalités)
- [Moteurs de stabilisation](#-moteurs-de-stabilisation)
- [Intelligence du code source](#-intelligence-du-code-source)
- [Pipeline anti-hallucination](#-pipeline-anti-hallucination)
- [Tests](#-tests)
- [Configuration](#-configuration)
- [Technologies](#-technologies)

---

## 🎯 Vue d'ensemble

La plateforme assiste les ingénieurs N3 BRASIL avec :

| Capacité | Description |
|---|---|
| 🔍 **Diagnostics live** | SSH → logs Tomcat · PostgreSQL readonly · Corrélation runtime |
| 📖 **Base de connaissance** | 51 FRs BRASIL · 128 tables DB · ~3 200 fichiers Java indexés |
| 🧠 **Intelligence code** | Résolution de méthodes Java, chaînes d'appel, validateurs, exceptions |
| 🛡️ **Truth Enforcement** | Bloque SQL mutations · Invalide tables inexistantes · Refuse scripts shell |
| 🧭 **Semantic Routing** | 25 catégories opérationnelles · Langue française N3 · Multi-label |
| 📂 **Provenance** | Chaque réponse cite : fichier log · table DB · classe Java · FR · serveur |
| 🔄 **Workflow Intelligence** | Étapes opérationnelles DSLAM/VLAN/équipements depuis code + FRs |
| 💾 **Mémoire forensique** | Persistance cross-tour (2h TTL) — contexte conservé entre les questions |

### Principe fondamental

```
LLM = formateur / naturaliseur uniquement
Moteur déterministe = source de vérité principale
```

Le LLM ne raisonne jamais sur des logs bruts, des données DB, ou du code source directement.
Toutes les preuves viennent de pipelines déterministes vérifiés.

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    Frontend  React + TypeScript                   │
│          Chat │ Knowledge Graph │ Dashboard │ Validation          │
└──────────────────────────────────────────────────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
        ┌─────────────────────┐    ┌─────────────────────────┐
        │  FastAPI  :8000     │    │  Semantic Intent Router  │
        │  chatbot_service.py │◄───│  25 catégories          │
        └─────────────────────┘    └─────────────────────────┘
                    │
     ┌──────────────┼──────────────┬──────────────────┐
     ▼              ▼              ▼                  ▼
┌─────────┐  ┌──────────┐  ┌──────────────┐  ┌──────────────┐
│Qdrant   │  │Execution │  │  Live Diag   │  │  Truth       │
│51 FRs   │  │Graph     │  │  SSH+Psql    │  │  Enforcement │
│128 tbls │  │~3200 .java│  │  Forensic   │  │  Engine      │
└─────────┘  └──────────┘  └──────────────┘  └──────────────┘
                    │
     ┌──────────────┼──────────────┬──────────────────┐
     ▼              ▼              ▼                  ▼
┌─────────┐  ┌──────────┐  ┌──────────────┐  ┌──────────────┐
│Provenance│  │Workflow  │  │  Forensic    │  │  Response    │
│Engine   │  │Intellig. │  │  Memory      │  │  Quality     │
│📂 Sources│  │🧩 Steps  │  │  (2h TTL)   │  │  (Phase 7)   │
└─────────┘  └──────────┘  └──────────────┘  └──────────────┘
```

---

## 🚀 Démarrage rapide

### Prérequis

- Python 3.11+ · Node.js 18+ · PostgreSQL · Qdrant · Groq API key
- Code source BRASIL Java disponible localement

### Lancer le serveur

```powershell
$env:PYTHONPATH="d:\ai-support-agent\backend"
$env:BRASIL_SOURCE_ROOT="d:\ai-support-agent\brasil-default\brasil-default"
$env:PYTHONIOENCODING="utf-8"
$env:DEMO_MODE="true"
Set-Location D:\ai-support-agent\backend
.venv\Scripts\python.exe -W ignore::DeprecationWarning -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

> ⚠️ Le premier démarrage déclenche un scan du code source (~20s). Les appels suivants sont instantanés.

### Vérification

```bash
curl http://localhost:8000/health
# → {"status": "healthy", "version": "2.0.0", "service": "ai-support-agent"}
```

### Exemples d'utilisation

```bash
# Trouver une fonction Java
curl -X POST http://localhost:8000/api/v1/chatbot/chat \
  -H "Content-Type: application/json" \
  -d '{"content":"quelle fonction supprime un DSLAM ?","app_id":"brasil"}'

# Workflow opérationnel
curl -X POST http://localhost:8000/api/v1/chatbot/chat \
  -d '{"content":"comment créer un VLAN étape par étape ?","app_id":"brasil"}'

# Exceptions Java
curl -X POST http://localhost:8000/api/v1/chatbot/chat \
  -d '{"content":"quelles exceptions sont levées lors de la suppression ?","app_id":"brasil"}'
```

---

## ✨ Fonctionnalités

### 🔎 Résolution de fonctions Java

```
Question: "quelle méthode Java supprime un DSLAM ?"

→ 🔎 Fonction dans le code source — DSLAM
  Opération: delete_equipment
  🟦 ManageDslamBusinessImpl.deleteDslam()       ligne 1787
  🟦 ManageDslamManagerImpl.deleteDslamManager() ligne 128
  ⚠ Validateur: checkProductionInfoIsPresent()
     Condition: si services actifs → suppression bloquée
```

### 🧩 Workflow Intelligence

```
Question: "comment supprimer un DSLAM ?"

→ 🧩 Workflow — Suppression d'un DSLAM (Source: code)
  1. Vérifier l'absence de services actifs
     → ManageDslamBusinessImpl.checkProductionInfoIsPresent()
     ⚠️ Si services actifs → suppression bloquée
  2. Contrôler les dépendances MRT
     → ManageDslamBusinessImpl.checkMrtDependencies()
  3. Vérifier les données résiduelles (t_mrt_access_dslams)
  4. Lancer ManageDslamBusinessImpl.deleteDslam()
  5. Confirmer en base (t_equipments)
  6. Vérifier le retrait des ressources associées
```

### 📂 Provenance automatique

```
📂 Sources des informations
📋 runtime_log:
  - connectorCL_20260515.log | server: op49mwa11 | conf: 85%
🗄️ database:
  - t_equipments | server: op49mdb11 | conf: 95%
⚙️ source_code:
  - ManageDslamBusinessImpl.deleteDslam() | ligne: 1787 | conf: 100%
📄 FR:
  - FR-DSLAM-189 | conf: 90%
```

### 🛡️ Vérité garantie

- `DELETE FROM t_equipments` → `🚫 Commande SQL de mutation bloquée`
- Table `t_fake_table` → `⚠️\`t_fake_table\`` (non présente dans le schéma indexé)
- Script `bash deploy.sh` → `🚫 Commande shell bloquée`
- Placeholder `[NOM_EQPT]` → requête retirée automatiquement

---

## 🔬 Moteurs de stabilisation

### Phase 1 — Truth Enforcement (`truth_enforcement.py`)

| Check | Action |
|---|---|
| SQL `UPDATE/DELETE/INSERT/ALTER/DROP/TRUNCATE` | Bloqué · remplacé par message sécurisé |
| Script `bash/sh/shell` | Bloqué · fenced block remplacé |
| Placeholder SQL `[NOM]` | Requête entière retirée |
| Table inconnue `t_xyz` | Flaggée `⚠️` en strict mode |
| Méthode Java introuvable | Journalisée (non remplacée) |

### Phase 2 — Semantic Intent Router (`semantic_intent_router.py`)

25 catégories opérationnelles — classification pure regex, sans LLM :

```
"quelle fonction supprime un dslam"  → source_code_lookup → find_code_function
"comment créer un VLAN"              → workflow_navigation → forensic_workflow
"depuis quels logs viennent ces infos" → evidence_provenance → forensic_evidence
"quelles exceptions sont levées"     → exception_lookup → forensic_exceptions
"pourquoi le VLAN est occupé"        → runtime_diagnostic + dependency_analysis
```

### Phase 3 — Provenance Engine (`provenance_engine.py`)

Chaque evidence block inclut automatiquement :
`source_type · source_name · file · table · class · method · timestamp · server · confidence`

### Phase 4 — Workflow Intelligence (`workflow_intelligence.py`)

Workflows opérationnels indexés depuis code + FRs. Si inconnu → message d'incertitude explicite, **jamais** d'étapes inventées.

### Phase 6 — SQL Readonly (`response_quality.py`)

`enforce_readonly_sql()` — premier filtre dans `full_quality_check()`. Bloque toute mutation avant toute autre transformation.

### Phase 7 — Response Quality (`response_quality.py`)

50+ patterns de filler supprimés : "N'hésitez pas à", "Cordialement", "Il semble que", "Probablement", "Veuillez vérifier", etc.

---

## 🧠 Intelligence du code source

### Execution Graph Cache

Scan de ~3 200 fichiers Java BRASIL au démarrage → `execution_graph_cache.json`

```
delete_equipment → ManageDslamBusinessImpl.deleteDslam():1787
create_vlan      → ManageCreationVlanBusinessImpl.creerVlan():1221
                   ManageVlanBusinessImpl.createVlan():1612
```

### 65 mappings d'opérations (`operation_graph.py`)

Couvre : `delete_equipment`, `create_vlan`, `create_equipment`, `replay_order`, `mass_replay`, `mutation_request`, `fix_counter`, `check_toc`, `forensic_exceptions`, `forensic_db_state`, `rollback`, `check_residual_data`, `check_active_services`, `check_foreign_keys`, etc.

### Mémoire forensique cross-tour (`forensic_memory.py`)

```python
ForensicMemoryStore: 200 conversations max · TTL 2h · LRU eviction
ForensicSnapshot:    intent · entity · operation · bundle_ref · exceptions
```

---

## 🧪 Tests

```powershell
cd D:\ai-support-agent\backend

# Suite complète (110 tests)
$env:PYTHONPATH="D:\ai-support-agent\backend"
.venv\Scripts\python.exe -m pytest tests/ -v --tb=short

# Par module
pytest tests/test_truth_enforcement.py    # 24 tests — SQL/shell/placeholder blocking
pytest tests/test_provenance.py           # 22 tests — ProvenanceRecord + Engine
pytest tests/test_semantic_router.py      # 32 tests — 25 catégories · multi-label
pytest tests/test_workflow_intelligence.py # 32 tests — workflows · anti-hallucination

# Intégration end-to-end (serveur requis)
.venv\Scripts\python.exe tests/run_tests.py
```

**Résultats** : 110/110 ✅ — 0 régression

---

## ⚙️ Configuration

### Variables d'environnement essentielles (`backend/.env`)

```env
# LLM
GROQ_API_KEY=gsk_...
LLM_MODEL=qwen/qwen3-32b

# Base de données
POSTGRES_SERVER=localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DB=ai_support_agent

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333

# SSH (diagnostics live)
SSH_ENABLED=true
SSH_HOST=op49mwa11
SSH_USER=brasil
SSH_PASSWORD=...

# Code source BRASIL
BRASIL_SOURCE_ROOT=d:\ai-support-agent\brasil-default\brasil-default

# Mode démo (pas de SSH requis)
DEMO_MODE=true
```

### Injection de la base de connaissance

```powershell
cd backend

# Indexer toutes les FRs (51 fiches de résolution)
.venv\Scripts\python.exe scripts\knowledge\inject_all_fr.py

# Réindexer tout
.venv\Scripts\python.exe scripts\knowledge\inject_all_fr.py --force

# Vérifier le contenu Qdrant
.venv\Scripts\python.exe scripts\maintenance\check_qdrant_frs.py
```

---

## 🔧 Technologies

| Couche | Technologie |
|---|---|
| **Backend** | FastAPI · SQLAlchemy · Python 3.13 |
| **LLM** | Groq `qwen/qwen3-32b` (6000 TPM) |
| **Vector DB** | Qdrant (embeddings paraphrase-multilingual) |
| **Live Diag** | SSH Paramiko · PostgreSQL readonly |
| **Code Intel** | Scan Java ~3200 fichiers · AST-like extraction |
| **Frontend** | React 18 · TypeScript · Vite · TailwindCSS |
| **Auth** | JWT · bcrypt |
| **Tests** | pytest · 110 tests unitaires |

---

## 📁 Structure du projet

Voir [STRUCTURE.md](STRUCTURE.md) pour l'arborescence complète.

## 📚 Documentation historique

Les rapports de phases précédentes sont archivés dans [`docs/history/`](docs/history/).

## 📄 Licence

MIT License — voir [LICENSE](LICENSE)
