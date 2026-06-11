# 🚀 Quick Start — BRASIL N3 Forensic AI Platform v2.0.0

Guide de démarrage rapide pour lancer la plateforme forensique BRASIL N3.

---

## ⚡ Démarrage (2 minutes)

### Prérequis
- Python 3.13+
- Qdrant accessible (local ou distant)
- PostgreSQL (ou SQLite en mode dev)
- Clé API Groq (`GROQ_API_KEY`)
- Sources Java BRASIL à `d:\ai-support-agent\brasil-default\brasil-default`

---

## 🖥️ Lancement du serveur backend

```powershell
# Variables d'environnement
$env:PYTHONPATH          = "d:\ai-support-agent\backend"
$env:BRASIL_SOURCE_ROOT  = "d:\ai-support-agent\brasil-default\brasil-default"
$env:PYTHONIOENCODING    = "utf-8"
$env:DEMO_MODE           = "true"    # Mode démo (optionnel)

# Lancement
Set-Location D:\ai-support-agent\backend
d:\ai-support-agent\.venv\Scripts\python.exe `
  -W ignore::DeprecationWarning `
  -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### ✅ Vérification
```powershell
Invoke-RestMethod http://localhost:8000/health
# → { "status": "ok" }

# Documentation interactive
Start-Process "http://localhost:8000/docs"
```

---

## 🧪 Lancer les tests

### Suite principale (110 tests)
```powershell
$env:PYTHONPATH = "D:\ai-support-agent\backend"
Set-Location D:\ai-support-agent

.venv\Scripts\python.exe -m pytest `
  backend/tests/test_truth_enforcement.py `
  backend/tests/test_provenance.py `
  backend/tests/test_semantic_router.py `
  backend/tests/test_workflow_intelligence.py `
  -v
# Attendu : 110 passed · 0 failed
```

### Tests intégration (serveur requis)
```powershell
.venv\Scripts\python.exe backend/tests/run_tests.py
.venv\Scripts\python.exe backend/tests/run_new_tests.py
```

---

## 💬 Appel API chatbot

```powershell
# Authentification
$auth = Invoke-RestMethod http://localhost:8000/api/v1/auth/login `
  -Method POST -ContentType "application/json" `
  -Body '{"username":"admin","password":"admin"}'
$token = $auth.access_token

# Question forensique
Invoke-RestMethod http://localhost:8000/api/v1/chatbot/chat `
  -Method POST -ContentType "application/json" `
  -Headers @{Authorization="Bearer $token"} `
  -Body '{"message":"Pourquoi la suppression DSLAM echoue ?","conversation_id":"test-1"}'
```

---

## 🏗️ Infrastructure (optionnel)

```powershell
# Démarrer Qdrant localement
wsl podman run -d --name qdrant -p 6333:6333 qdrant/qdrant

# Démarrer PostgreSQL
wsl podman run -d --name postgres -p 5432:5432 `
  -e POSTGRES_PASSWORD=password postgres:15
```

---

## 📁 Fichiers de configuration

| Fichier | Rôle |
|---|---|
| `backend/.env` | Variables d'environnement (DB, Groq, Qdrant) |
| `backend/.env.example` | Template à copier |
| `docker-compose.yml` | Orchestration complète |

---

## 🔍 Liens utiles

| Ressource | URL / Fichier |
|---|---|
| API docs (Swagger) | http://localhost:8000/docs |
| Qdrant dashboard | http://localhost:6333/dashboard |
| Structure du projet | [STRUCTURE.md](STRUCTURE.md) |
| Guide ML | [QUICKSTART_ML.md](QUICKSTART_ML.md) |
