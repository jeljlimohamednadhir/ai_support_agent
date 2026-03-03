# ✅ PRIORITÉ 1: Persistance Upload + Session (IMPLÉMENTÉ)

## 🎯 Objectifs
1. ✅ Upload CSV ne doit pas être perdu lors du changement d'onglet
2. ✅ Simplifier UI d'entraînement (auto-sélection colonne texte)
3. ⏳ Afficher classes prédites sur tickets (TODO)
4. ⏳ Dropdown classes pour corrections (TODO)

## 📝 Modifications Appliquées

### Backend

#### 1. `backend/app/api/v1/endpoints/classification_ml.py`
**Changements:**
- ✅ Ajout `import uuid` et `Dict` dans imports
- ✅ Ajout variable globale `_uploaded_sessions: Dict[str, pd.DataFrame] = {}`
- ✅ Génération `session_id = str(uuid.uuid4())` dans `/upload`
- ✅ Stockage session: `_uploaded_sessions[session_id] = df`
- ✅ Retour `session_id` dans `UploadResponse`
- ✅ Endpoint `/train`: restauration session avec `request.session_id`
- ✅ Auto-sélection colonne texte si `text_col` non fourni:
  ```python
  if not text_col:
      if 'text_ml_postmortem' in df.columns:
          text_col = 'text_ml_postmortem'
      elif 'texte_complet' in df.columns:
          text_col = 'texte_complet'
      elif 'resume' in df.columns:
          text_col = 'resume'
      else:
          raise HTTPException(...)
  ```

#### 2. `backend/app/models/classification_ml.py`
**Changements:**
- ✅ `UploadResponse`: ajout `session_id: Optional[str]`
- ✅ `TrainRequest`: 
  - `text_col: Optional[str]` (plus requis)
  - Ajout `session_id: Optional[str]`

### Frontend

#### 3. `frontend/src/services/classificationMLService.ts`
**Changements:**
- ✅ `UploadResponse`: ajout `session_id?: string`
- ✅ `TrainRequest`: 
  - `text_col?: string` (optionnel)
  - Ajout `session_id?: string`

#### 4. `frontend/src/pages/ClassificationMLPage.tsx`
**Changements:**
- ✅ Ajout state: `const [sessionId, setSessionId] = useState<string | null>(null)`
- ✅ `useEffect` restaure session: `localStorage.getItem('ml_session_id')`
- ✅ `handleFileUpload`: sauvegarde session_id dans localStorage
- ✅ `handleTrainModel`: signature simplifiée (plus de `textCol` param)
- ✅ `handleTrainModel`: envoi `session_id` dans requête
- ✅ **TrainingTab**: simplifié
  - ❌ Supprimé dropdown "Colonne de texte"
  - ✅ Message info: "La colonne de texte sera automatiquement détectée"
  - ✅ Seulement dropdown "Colonne à prédire (label)"
  - ✅ Valeurs par défaut: `labelCol: 'cause'` (au lieu de cause_canonique)

## 🧪 Tests Manuels

### Test 1: Persistance Upload Entre Onglets
```powershell
# 1. Démarrer backend
cd backend; python -m uvicorn app.main:app --reload

# 2. Démarrer frontend
cd frontend; npm run dev

# 3. Naviguer vers Classification ML
# 4. Uploader test_tickets.csv
# 5. Vérifier session_id dans localStorage (DevTools > Application > Local Storage)
# 6. Changer vers onglet "Synthèse"
# 7. Retourner vers "Entraînement"
# 8. ✅ SUCCÈS: les données sont toujours présentes (dropdown label contient colonnes)
```

### Test 2: Auto-Sélection Colonne Texte
```powershell
# 1. Uploader test_tickets.csv
# 2. Aller dans onglet "Entraînement"
# 3. Observer: dropdown "Colonne de texte" n'existe plus
# 4. Observer: message info bleu "La colonne sera automatiquement détectée"
# 5. Sélectionner colonne label: "cause"
# 6. Cliquer "Entraîner le modèle"
# 7. ✅ SUCCÈS: backend détecte "texte_complet" ou "text_ml_postmortem" automatiquement
```

### Test 3: Restauration Session Après Refresh
```powershell
# 1. Uploader CSV et noter session_id
# 2. Refresh page (F5)
# 3. useEffect restaure session_id depuis localStorage
# 4. ⚠️ LIMITATION ACTUELLE: DataFrame n'est pas restauré (stocké en RAM backend)
# 5. 📋 SOLUTION PRODUCTION: utiliser Redis ou PostgreSQL pour stocker session
```

## 🚀 Commandes Validation Complète

```powershell
# Backend: Vérifier endpoint retourne session_id
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/classification-ml/model-info" -Method GET

# Frontend: Build sans erreurs
cd frontend
npm run build

# Tester upload avec curl (Windows)
$boundary = [System.Guid]::NewGuid().ToString()
$filePath = "backend\test_tickets.csv"
$fileBytes = [System.IO.File]::ReadAllBytes($filePath)
$fileEnc = [System.Text.Encoding]::GetEncoding("iso-8859-1").GetString($fileBytes)

$body = @"
--$boundary
Content-Disposition: form-data; name="file"; filename="test_tickets.csv"
Content-Type: text/csv

$fileEnc
--$boundary--
"@

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/classification-ml/upload" -Method POST -ContentType "multipart/form-data; boundary=$boundary" -Body $body
```

## 📋 TODO Restants (Priorité 1)

### 3. Afficher Classes Prédites sur Tickets
**Fichiers à modifier:**
- `frontend/src/components/ml/DataTable.tsx`
- `frontend/src/components/ml/LowConfidenceTable.tsx`

**Changements requis:**
```typescript
// Dans DataTable: ajouter colonne "Classe Prédite"
<td className="px-4 py-2">
  {row.predicted_label || 'Non classé'}
  {row.confidence && (
    <span className={`ml-2 text-xs px-2 py-1 rounded ${
      row.confidence >= 0.7 ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
    }`}>
      {(row.confidence * 100).toFixed(0)}%
    </span>
  )}
</td>
```

### 4. Dropdown Classes pour Corrections
**Fichiers à modifier:**
- `frontend/src/components/ml/LowConfidenceTable.tsx`

**Changements requis:**
```typescript
// Récupérer classes depuis modelInfo
const [classes, setClasses] = useState<string[]>([]);

useEffect(() => {
  classificationMLService.getModelInfo().then(info => {
    setClasses(info.classes);
  });
}, []);

// Remplacer input texte par dropdown
<select 
  value={correction[ticket.ticket_id] || ''}
  onChange={(e) => setCorrection({...correction, [ticket.ticket_id]: e.target.value})}
  className="w-full px-3 py-2 border rounded-lg"
>
  <option value="">-- Sélectionner --</option>
  {classes.map(cls => (
    <option key={cls} value={cls}>{cls}</option>
  ))}
</select>
```

## 🔐 Limitations Actuelles et Solutions Production

### Limitation 1: Session RAM Seulement
**Problème:** `_uploaded_sessions` est en mémoire RAM, perdu au restart backend

**Solution Production:**
```python
# Utiliser Redis
import redis
redis_client = redis.Redis(host='localhost', port=6379, db=0)

@router.post("/upload")
async def upload_csv(file: UploadFile):
    session_id = str(uuid.uuid4())
    df = _data_processor.load_csv_robust(str(temp_path))
    
    # Sauvegarder dans Redis (pickle + compression)
    import pickle, gzip
    df_bytes = gzip.compress(pickle.dumps(df))
    redis_client.setex(f"ml_session:{session_id}", 3600, df_bytes)  # 1h TTL
    
    return UploadResponse(..., session_id=session_id)

@router.post("/train")
async def train_model(request: TrainRequest):
    if request.session_id:
        df_bytes = redis_client.get(f"ml_session:{request.session_id}")
        if df_bytes:
            df = pickle.loads(gzip.decompress(df_bytes))
            _uploaded_data = df
```

### Limitation 2: Aucun Nettoyage Sessions
**Problème:** Sessions s'accumulent en mémoire

**Solution:**
```python
# Ajouter TTL cleanup task
from datetime import datetime, timedelta

_session_timestamps: Dict[str, datetime] = {}

async def cleanup_old_sessions():
    """Background task: nettoyer sessions > 1h"""
    while True:
        await asyncio.sleep(300)  # Check every 5min
        now = datetime.now()
        to_delete = [
            sid for sid, ts in _session_timestamps.items()
            if now - ts > timedelta(hours=1)
        ]
        for sid in to_delete:
            _uploaded_sessions.pop(sid, None)
            _session_timestamps.pop(sid, None)
```

## ✅ Critères d'Acceptance

- [x] Upload retourne `session_id` valide (UUID4)
- [x] Session_id sauvegardé dans `localStorage`
- [x] Changement d'onglet ne perd pas l'upload (données disponibles dans state)
- [x] Formulaire d'entraînement ne contient plus dropdown "Colonne de texte"
- [x] Message info explique l'auto-détection
- [x] Backend détecte colonne texte dans ordre: text_ml_postmortem > texte_complet > resume
- [x] Training endpoint accepte `text_col: null` et auto-sélectionne
- [ ] Classes prédites affichées dans tableau tickets (TODO)
- [ ] Dropdown classes pour corrections (TODO)
- [ ] Colonne Genergy utilisée pour ticket_id corrections (TODO)

## 📊 Impact Utilisateur

### Avant ✗
- ❌ Upload perdu en changeant d'onglet → frustration
- ❌ Utilisateur doit re-uploader pour chaque onglet
- ❌ Formulaire complexe avec 2 dropdowns (texte + label)
- ❌ Confusion sur quelle colonne texte choisir

### Après ✓
- ✅ Upload persisté pendant session → fluidité
- ✅ Navigation libre entre onglets sans perte
- ✅ Formulaire simplifié (1 seul dropdown label)
- ✅ Auto-détection intelligente colonne texte
- ✅ Workflow identique à GenIQ Streamlit

## 🏗️ Architecture Session Management

```
Frontend (React)                Backend (FastAPI)
┌──────────────────┐           ┌────────────────────┐
│ localStorage     │           │ _uploaded_sessions │
│ ml_session_id    │◄──────────┤ {                  │
│                  │  upload   │   uuid1: df1,      │
└──────────────────┘  response │   uuid2: df2       │
        │                       │ }                  │
        │ sessionId state       └────────────────────┘
        ▼                                 ▲
┌──────────────────┐                     │
│ ClassificationML │  POST /train        │
│ Page Component   │  {session_id: uuid} │
│                  ├─────────────────────┘
└──────────────────┘  restore df from session
```

## 🔄 Flow Diagram: Upload + Train

```
User                 Frontend                Backend
 │                      │                       │
 │──Upload CSV──────►   │                       │
 │                      │──POST /upload────────►│
 │                      │                       │ Generate UUID
 │                      │                       │ Store df in _uploaded_sessions
 │                      │◄─{session_id, ...}────│
 │                      │ Save to localStorage  │
 │                      │                       │
 │─Change Tab Synthese─►│                       │
 │                      │ (data preserved)      │
 │                      │                       │
 │─Change Tab Training─►│                       │
 │                      │ Read localStorage     │
 │                      │ sessionId exists ✓    │
 │                      │                       │
 │──Click "Entraîner"──►│                       │
 │                      │──POST /train─────────►│
 │                      │  {label_col, session_id}
 │                      │                       │ Restore df from session
 │                      │                       │ Auto-detect text_col
 │                      │                       │ Train model
 │                      │◄─{metrics, ...}───────│
 │◄──Results Displayed──│                       │
```

## 🎉 Résultat Final

**Comportement GenIQ reproduit:**
1. ✅ Upload une seule fois
2. ✅ Navigation fluide entre onglets
3. ✅ Entraînement simplifié (juste choisir label)
4. ✅ Auto-sélection intelligente des colonnes

**Prêt pour les priorités 2 et 3:**
- Priorité 2: HuggingFace SSL + Fallback Embeddings
- Priorité 3: RAG Chatbot sur Tickets
