# 🔍 Services de Validation et Diagnostics

Guide complet des services de validation humaine et de diagnostic IA.

---

## 📋 Vue d'Ensemble

### Service de Validation
**Human-in-the-loop** pour validation et correction des insights générés par l'IA.

**Fonctionnalités:**
- ✅ File d'attente de tâches de validation
- ✅ Approbation/rejet des suggestions IA
- ✅ Corrections manuelles avec feedback
- ✅ Vérification cohérence BRASIL ↔ Terrain
- ✅ Métriques et historique complet

### Service de Diagnostics
**Analyse intelligente** de problèmes techniques avec IA.

**Fonctionnalités:**
- ✅ Diagnostic automatique via LLM
- ✅ Recherche d'issues similaires
- ✅ Identification cause racine
- ✅ Suggestions de solutions
- ✅ Patterns d'erreurs récurrents

---

## 🔄 Service de Validation

### Architecture

```
┌─────────────────────────────────────────┐
│   ValidationService                     │
├─────────────────────────────────────────┤
│ • get_pending_tasks()                   │
│ • submit_validation()                   │
│ • apply_correction()                    │
│ • verify_brasil_terrain_consistency()  │
│ • get_metrics()                         │
└─────────────────────────────────────────┘
           │
           ├──► PostgreSQL (ValidationTask, Correction)
           ├──► Neo4j (Knowledge Graph updates)
           └──► GraphService (apply to KB)
```

### Endpoints API

#### GET /api/v1/validation/pending
Récupère les tâches en attente de validation.

**Paramètres:**
- `limit` (int): Nombre max de tâches (défaut: 50)
- `task_type` (str): Filtrer par type (optionnel)

**Types de tâches:**
- `response_validation`: Validation de réponse chatbot
- `rule_extraction`: Extraction de règle métier
- `pattern_confirmation`: Confirmation de pattern détecté
- `consistency_check`: Vérification cohérence BRASIL/Terrain

**Réponse:**
```json
{
  "count": 5,
  "tasks": [
    {
      "task_id": "42",
      "task_type": "response_validation",
      "priority": 7,
      "content": {
        "original_data": {"question": "..."},
        "ai_suggestion": {"answer": "..."}
      },
      "created_at": "2026-01-12T10:00:00Z",
      "status": "pending"
    }
  ]
}
```

#### POST /api/v1/validation/submit
Soumet un résultat de validation.

**Body:**
```json
{
  "task_id": "42",
  "approved": true,
  "corrections": {
    "answer": "Corrected answer"
  },
  "comments": "Minor correction needed",
  "validator_id": "user123"
}
```

**Réponse:**
```json
{
  "task_id": "42",
  "status": "validated",
  "validated_at": "2026-01-12T10:05:00Z",
  "applied": true
}
```

#### POST /api/v1/validation/correction
Applique une correction manuelle à la base de connaissances.

**Body:**
```json
{
  "entity_id": "node_abc",
  "entity_type": "knowledge_node",
  "corrections": {
    "description": "Updated description"
  },
  "reason": "Outdated information",
  "submitter_id": "user123"
}
```

#### POST /api/v1/validation/verify-consistency
Vérifie cohérence entre données BRASIL et terrain.

**Body:**
```json
{
  "brasil_data": {
    "id": "123",
    "status": "active",
    "affectation": "Team A"
  },
  "terrain_data": {
    "id": "123",
    "status": "inactive",
    "affectation": "Team A"
  }
}
```

**Réponse:**
```json
{
  "consistent": false,
  "inconsistencies_count": 1,
  "critical_count": 1,
  "inconsistencies": [
    {
      "field": "status",
      "brasil_value": "active",
      "terrain_value": "inactive",
      "severity": "critical"
    }
  ],
  "validation_task_created": true
}
```

#### GET /api/v1/validation/metrics
Récupère métriques de validation.

**Réponse:**
```json
{
  "total_validations": 250,
  "approved": 200,
  "rejected": 50,
  "accuracy_rate": 80.0,
  "pending_count": 15,
  "weekly_validations": 42,
  "by_type": {
    "response_validation": 150,
    "rule_extraction": 70,
    "pattern_confirmation": 30
  }
}
```

### Utilisation en Code

```python
from app.services.validation.validation_service import ValidationService
from app.db.session import get_db

# Initialiser service
db = next(get_db())
validation_service = ValidationService(db)

# Récupérer tâches en attente
tasks = await validation_service.get_pending_tasks(limit=10)

# Soumettre validation
result = await validation_service.submit_validation(
    ValidationResult(
        task_id="42",
        approved=True,
        validator_id="user123"
    )
)

# Vérifier cohérence BRASIL/Terrain
report = await validation_service.verify_brasil_terrain_consistency(
    brasil_data={"id": "123", "status": "active"},
    terrain_data={"id": "123", "status": "inactive"}
)

# Métriques
metrics = await validation_service.get_metrics()
```

---

## 🩺 Service de Diagnostics

### Architecture

```
┌─────────────────────────────────────────┐
│   DiagnosticsEngine                     │
├─────────────────────────────────────────┤
│ • diagnose()          ──► LLM           │
│ • find_similar_issues() ──► Qdrant     │
│ • suggest_fixes()     ──► Neo4j        │
│ • get_patterns()      ──► PostgreSQL   │
└─────────────────────────────────────────┘
```

### Endpoints API

#### POST /api/v1/diagnostics/diagnose
Lance un diagnostic complet d'un problème.

**Body:**
```json
{
  "issue_description": "Application crashes on startup",
  "affected_component": "backend-api",
  "error_logs": [
    "Error: Connection refused to database",
    "Stacktrace: ..."
  ],
  "context": {
    "requester_id": "user123",
    "environment": "production"
  }
}
```

**Réponse:**
```json
{
  "diagnostic_id": "diag-uuid-123",
  "root_cause": "Database connection pool exhausted",
  "severity": "high",
  "confidence": 0.85,
  "related_code": [
    {
      "file": "app/db/session.py",
      "content": "...",
      "score": 0.92
    }
  ],
  "related_logs": [
    {
      "message": "Connection timeout",
      "timestamp": "2026-01-12T09:45:00Z",
      "level": "ERROR"
    }
  ],
  "suggested_fixes": [
    {
      "type": "quick_fix",
      "description": "Increase connection pool size",
      "steps": [
        "Edit config.py",
        "Set POOL_SIZE = 20",
        "Restart service"
      ],
      "estimated_time": "5 minutes"
    },
    {
      "type": "proper_fix",
      "description": "Implement connection pooling strategy",
      "steps": ["..."],
      "estimated_time": "2 hours"
    }
  ],
  "similar_issues": [
    {
      "id": "issue-456",
      "description": "Similar database issue",
      "resolution": "Increased pool size",
      "score": 0.89,
      "source": "history"
    }
  ]
}
```

#### GET /api/v1/diagnostics/similar-issues
Recherche d'issues similaires.

**Paramètres:**
- `issue_description` (str): Description du problème
- `limit` (int): Nombre max de résultats (défaut: 10)

**Sources:**
- Historique diagnostics (PostgreSQL)
- Tickets Jira résolus (Neo4j)
- Base vectorielle (Qdrant)

#### POST /api/v1/diagnostics/suggest-fixes/{diagnostic_id}
Génère ou récupère suggestions de solutions.

**Réponse:**
```json
{
  "diagnostic_id": "diag-123",
  "fixes": [
    {
      "type": "quick_fix",
      "description": "...",
      "steps": ["..."],
      "estimated_time": "..."
    }
  ]
}
```

#### GET /api/v1/diagnostics/patterns
Analyse patterns d'erreurs récurrents.

**Réponse:**
```json
{
  "total_diagnostics": 500,
  "resolved": 350,
  "resolution_rate": 70.0,
  "avg_resolution_time_hours": 4.5,
  "top_affected_components": [
    {"component": "backend-api", "count": 120},
    {"component": "worker", "count": 80}
  ],
  "severity_distribution": {
    "low": 100,
    "medium": 250,
    "high": 120,
    "critical": 30
  }
}
```

#### GET /api/v1/diagnostics/
Liste les diagnostics avec filtres.

**Paramètres:**
- `status`: Filtrer par statut (open, in_progress, resolved, closed)
- `severity`: Filtrer par sévérité (low, medium, high, critical)
- `component`: Filtrer par composant
- `limit`: Nombre max de résultats (défaut: 50)

#### GET /api/v1/diagnostics/{diagnostic_id}
Récupère un rapport complet.

#### PUT /api/v1/diagnostics/{diagnostic_id}/status
Met à jour le statut d'un diagnostic.

**Body:**
```json
{
  "status": "resolved",
  "resolution_notes": "Fixed by increasing connection pool",
  "applied_fix": {
    "type": "quick_fix",
    "description": "..."
  }
}
```

### Utilisation en Code

```python
from app.services.analyzer.diagnostics_engine import DiagnosticsEngine
from app.schemas.diagnostics import DiagnosticRequest
from app.db.session import get_db

# Initialiser engine
db = next(get_db())
engine = DiagnosticsEngine(db)

# Lancer diagnostic
request = DiagnosticRequest(
    issue_description="App crashes",
    affected_component="api",
    error_logs=["Error: ..."]
)

report = await engine.diagnose(request)

# Rechercher issues similaires
similar = await engine.find_similar_issues("Memory leak detected")

# Suggestions de solutions
fixes = await engine.suggest_fixes("diag-uuid-123")

# Patterns
patterns = await engine.get_diagnostic_patterns()
```

---

## 🔗 Intégrations

### Validation → Knowledge Graph
Quand une validation est approuvée:
1. `submit_validation()` appelle `_apply_to_knowledge_base()`
2. Selon le type, met à jour Neo4j:
   - `rule_extraction` → `add_business_rule()`
   - `pattern_confirmation` → `add_pattern()`
   - `response_validation` → `add_validated_response()`

### Diagnostics → LLM + Vector Store
Workflow de diagnostic:
1. Recherche contexte pertinent (Qdrant)
2. Trouve issues similaires (PostgreSQL + Neo4j)
3. Analyse avec LLM (Groq/OpenAI)
4. Génère solutions (LLM)
5. Sauvegarde rapport (PostgreSQL)

---

## 📊 Modèles de Données

### ValidationTask
```python
{
  "id": int,
  "task_type": str,  # response_validation, rule_extraction, etc.
  "status": str,     # pending, validated, rejected, skipped
  "priority": int,   # 1-10
  "original_data": dict,
  "ai_suggestion": dict,
  "validated_data": dict,
  "validator_id": str,
  "validation_comment": str,
  "created_at": datetime,
  "validated_at": datetime
}
```

### DiagnosticReport
```python
{
  "id": str (UUID),
  "issue_description": str,
  "affected_component": str,
  "severity": str,  # low, medium, high, critical
  "status": str,    # open, in_progress, resolved, closed
  "root_cause": str,
  "analysis": dict,
  "confidence": float,  # 0.0-1.0
  "error_logs": list,
  "related_code": list,
  "suggested_fixes": list,
  "applied_fix": dict,
  "resolution_notes": str,
  "created_at": datetime,
  "resolved_at": datetime
}
```

---

## 🧪 Tests

### Tests Validation
```bash
cd backend
pytest tests/test_validation_service.py -v

# Tests couverts:
# - get_pending_tasks
# - submit_validation (approved/rejected)
# - apply_correction
# - get_metrics
# - verify_brasil_terrain_consistency
# - create_validation_task
```

### Tests Diagnostics
```bash
pytest tests/test_diagnostics_engine.py -v

# Tests couverts:
# - diagnose (avec/sans similar issues)
# - find_similar_issues (multiple sources)
# - suggest_fixes
# - get_diagnostic_patterns
# - Méthodes privées
```

---

## 🚀 Déploiement

### Variables d'Environnement
```env
# LLM pour diagnostics
GROQ_API_KEY=gsk_...
LLM_MODEL=llama-3.3-70b-versatile

# Bases de données
NEO4J_URI=bolt://localhost:7687
QDRANT_HOST=localhost
POSTGRES_URI=postgresql://...

# Config validation
VALIDATION_AUTO_APPLY=false  # Auto-appliquer si confidence > seuil
VALIDATION_CONFIDENCE_THRESHOLD=0.9
```

### Migrations Base de Données
```bash
# Créer les nouvelles tables
alembic revision --autogenerate -m "Add validation and diagnostics models"
alembic upgrade head
```

---

## 📈 Métriques et Monitoring

### Validation
- **Taux d'approbation**: % de validations approuvées
- **Temps moyen**: Délai entre création et validation
- **Par type**: Distribution des types de tâches
- **File d'attente**: Nombre de tâches pending

### Diagnostics
- **Taux de résolution**: % de diagnostics résolus
- **Temps de résolution**: Délai moyen de résolution
- **Composants critiques**: Top zones problématiques
- **Confiance IA**: Distribution des scores de confiance

### Dashboards Flower
```bash
# Lancer Flower pour monitoring workers
celery -A celery_app flower --port=5555

# URL: http://localhost:5555
# Voir tâches de validation/diagnostic en temps réel
```

---

## 🎯 Cas d'Usage

### 1. Validation de Réponse Chatbot
**Scénario:** L'IA génère une réponse, l'expert valide.

```python
# Créer tâche
task_id = await validation_service.create_validation_task(
    task_type="response_validation",
    original_data={
        "question": "Comment interroger la table t_ports?",
        "context": "SQL Database"
    },
    ai_suggestion={
        "answer": "SELECT * FROM t_ports WHERE ...",
        "confidence": 0.75
    },
    priority=5
)

# Valider
await validation_service.submit_validation(
    ValidationResult(
        task_id=task_id,
        approved=True,
        validator_id="expert123"
    )
)
```

### 2. Diagnostic de Problème Production
**Scénario:** Application plante, besoin de diagnostic rapide.

```python
# Lancer diagnostic
report = await engine.diagnose(
    DiagnosticRequest(
        issue_description="API returns 500 errors",
        affected_component="backend-api",
        error_logs=["Traceback: ...", "Error: Database connection failed"],
        context={"environment": "production", "time": "2026-01-12 10:00"}
    )
)

# Appliquer solution suggérée
await engine.db.query(DiagnosticReport).filter(
    DiagnosticReport.id == report["diagnostic_id"]
).update({
    "status": "resolved",
    "applied_fix": report["suggested_fixes"][0],
    "resolution_notes": "Applied quick fix - increased pool size"
})
```

### 3. Vérification Cohérence BRASIL/Terrain
**Scénario:** Synchronisation données BRASIL ↔ Relevés terrain.

```python
# Vérifier cohérence
report = await validation_service.verify_brasil_terrain_consistency(
    brasil_data={
        "port_id": "P123",
        "status": "active",
        "affectation": "Zone A",
        "last_maintenance": "2025-12-01"
    },
    terrain_data={
        "port_id": "P123",
        "status": "inactive",  # Incohérence
        "affectation": "Zone A",
        "observed_date": "2026-01-12"
    }
)

# Si incohérence critique → tâche de validation créée automatiquement
if report["critical_count"] > 0:
    # Technicien reçoit notification pour vérifier
    pass
```

---

## 🔒 Sécurité

### Permissions
- **Validation**: Requiert rôle `validator` ou `admin`
- **Diagnostics**: Accessible à tous les utilisateurs authentifiés
- **Correction KB**: Requiert rôle `admin` ou `knowledge_manager`

### Audit Trail
Toutes les validations et corrections sont enregistrées avec:
- Timestamp
- User ID
- Action (approved/rejected/corrected)
- Raison/commentaire

---

## 📚 Documentation Complète

- **API Reference**: http://localhost:8000/docs
- **Tests**: `backend/tests/`
- **Exemples**: Voir cas d'usage ci-dessus

---

**Version**: 1.0.0  
**Dernière mise à jour**: 12 janvier 2026  
**Status**: ✅ Production Ready
