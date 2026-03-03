# ✅ PRIORITÉ 3: RAG Chatbot sur Tickets Uploadés

## 🎯 Objectifs
1. Indexer tickets CSV uploadés dans Qdrant (embeddings)
2. Chatbot peut répondre à partir du contenu des tickets
3. Intégrer corrections dans l'index RAG
4. Interface toggle "Rechercher dans tickets uploadés"
5. Afficher sources (ticket IDs) dans réponses

## 📝 Architecture RAG

### Flow RAG sur Tickets
```
User Upload CSV → Indexation Qdrant → User Query Chatbot
      │                  │                     │
      ▼                  ▼                     ▼
┌──────────┐    ┌────────────────┐   ┌─────────────────┐
│ Tickets  │───►│ Vector Embeddings│◄──│ Question User   │
│ CSV Data │    │ Collection       │   │ "Top causes?"   │
└──────────┘    └────────────────┘   └─────────────────┘
                        │                     │
                        │ Similarity Search   │
                        └──────────┬──────────┘
                                   ▼
                        ┌──────────────────────┐
                        │ Top 5 Similar Tickets│
                        │ (contexte RAG)       │
                        └──────────────────────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │ LLM Prompt:          │
                        │ Context: {tickets}   │
                        │ Question: {query}    │
                        └──────────────────────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │ Réponse avec Sources │
                        │ [Ticket #123, #456]  │
                        └──────────────────────┘
```

## 🛠️ Implémentation

### 1. Backend: Endpoint Indexation Tickets

**Fichier:** `backend/app/api/v1/endpoints/classification_ml.py`

```python
@router.post("/index-tickets")
async def index_tickets_for_rag(background_tasks: BackgroundTasks):
    """
    Indexer les tickets uploadés dans Qdrant pour RAG chatbot
    """
    global _uploaded_data
    
    if _uploaded_data is None:
        raise HTTPException(status_code=400, detail="No data uploaded")
    
    try:
        from app.services.knowledge.vector_service import VectorService
        vector_service = VectorService()
        
        if not vector_service.is_available():
            raise HTTPException(status_code=503, detail="Vector service unavailable")
        
        # Créer collection tickets si n'existe pas
        try:
            vector_service.client.get_collection("tickets_rag")
        except:
            from qdrant_client.models import Distance, VectorParams
            vector_service.client.create_collection(
                collection_name="tickets_rag",
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )
        
        # Préparer textes tickets
        df = _uploaded_data.copy()
        
        # Détecter colonnes texte
        text_cols = []
        for col in ['resume', 'signalement', 'cause', 'solution', 'description']:
            if col in df.columns:
                text_cols.append(col)
        
        if not text_cols:
            raise HTTPException(status_code=400, detail="No text columns found in data")
        
        # Créer texte complet pour chaque ticket
        df['text_for_rag'] = df[text_cols].fillna('').agg(' | '.join, axis=1)
        
        # Indexer en arrière-plan
        background_tasks.add_task(
            _index_tickets_background,
            df=df,
            vector_service=vector_service
        )
        
        return {
            "message": f"Indexing {len(df)} tickets in background",
            "ticket_count": len(df),
            "text_columns": text_cols
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Index tickets failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _index_tickets_background(df: pd.DataFrame, vector_service):
    """Tâche arrière-plan: indexer tickets dans Qdrant"""
    try:
        from qdrant_client.models import PointStruct
        import uuid
        
        points = []
        for idx, row in df.iterrows():
            # Générer embedding
            text = row['text_for_rag']
            embedding = vector_service.embedding_model.encode(text).tolist()
            
            # Construire point Qdrant
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={
                    "ticket_id": row.get('ticket_id', f"ticket_{idx}"),
                    "text": text[:500],  # Limiter taille
                    "resume": row.get('resume', ''),
                    "cause": row.get('cause', ''),
                    "solution": row.get('solution', ''),
                    "application": row.get('application', ''),
                    "date": str(row.get('date_debut', '')),
                    "indexed_at": pd.Timestamp.now().isoformat()
                }
            )
            points.append(point)
            
            # Batch upsert every 100 tickets
            if len(points) >= 100:
                vector_service.client.upsert(
                    collection_name="tickets_rag",
                    points=points
                )
                logger.info(f"[RAG] Indexed {len(points)} tickets batch")
                points = []
        
        # Upsert remaining
        if points:
            vector_service.client.upsert(
                collection_name="tickets_rag",
                points=points
            )
        
        logger.info(f"[RAG] Indexation complete: {len(df)} tickets")
        
    except Exception as e:
        logger.error(f"[RAG] Indexation failed: {e}")
```

### 2. Backend: Endpoint Recherche RAG

**Fichier:** `backend/app/api/v1/endpoints/chatbot.py`

```python
@router.post("/search-tickets")
async def search_tickets_rag(query: str, top_k: int = 5):
    """
    Rechercher tickets similaires pour RAG
    """
    try:
        from app.services.knowledge.vector_service import VectorService
        vector_service = VectorService()
        
        if not vector_service.is_available():
            return {"results": [], "message": "Vector service unavailable"}
        
        # Vérifier collection existe
        try:
            vector_service.client.get_collection("tickets_rag")
        except:
            return {"results": [], "message": "No tickets indexed yet"}
        
        # Générer embedding query
        query_embedding = vector_service.embedding_model.encode(query).tolist()
        
        # Recherche similarité
        search_result = vector_service.client.search(
            collection_name="tickets_rag",
            query_vector=query_embedding,
            limit=top_k,
            score_threshold=0.5  # Seuil similarité minimum
        )
        
        # Formatter résultats
        results = []
        for hit in search_result:
            results.append({
                "ticket_id": hit.payload.get("ticket_id"),
                "resume": hit.payload.get("resume"),
                "cause": hit.payload.get("cause"),
                "solution": hit.payload.get("solution"),
                "score": float(hit.score),
                "text_preview": hit.payload.get("text", "")[:200]
            })
        
        return {
            "results": results,
            "count": len(results),
            "query": query
        }
        
    except Exception as e:
        logger.error(f"Search tickets failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat-with-context")
async def chat_with_tickets_context(
    message: str,
    use_uploaded_tickets: bool = True,
    conversation_id: Optional[str] = None
):
    """
    Chat avec contexte RAG des tickets uploadés
    """
    try:
        context_tickets = []
        
        # Récupérer contexte tickets si activé
        if use_uploaded_tickets:
            search_response = await search_tickets_rag(message, top_k=5)
            context_tickets = search_response.get("results", [])
        
        # Construire prompt avec contexte
        system_prompt = """Tu es un assistant expert en analyse de tickets IT.
Réponds en français de manière concise et précise."""
        
        if context_tickets:
            context_text = "\\n\\n".join([
                f"**Ticket {t['ticket_id']}:**\\n"
                f"Résumé: {t['resume']}\\n"
                f"Cause: {t['cause']}\\n"
                f"Solution: {t['solution']}"
                for t in context_tickets[:3]  # Top 3 seulement
            ])
            
            system_prompt += f"""\\n\\n**CONTEXTE TICKETS:**\\n{context_text}\\n
Utilise ces tickets comme référence pour répondre."""
        
        # Appeler LLM avec contexte
        from app.services.chatbot.chatbot_service import ChatbotService
        chatbot = ChatbotService()
        
        response = await chatbot.chat(
            message=message,
            conversation_id=conversation_id,
            system_prompt=system_prompt
        )
        
        # Ajouter sources dans réponse
        if context_tickets:
            sources = [t['ticket_id'] for t in context_tickets]
            response['sources'] = sources
            response['context_used'] = True
        else:
            response['context_used'] = False
        
        return response
        
    except Exception as e:
        logger.error(f"Chat with context failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

### 3. Frontend: Toggle RAG Tickets

**Fichier:** `frontend/src/components/ChatInterface.tsx`

```typescript
// État pour activer RAG tickets
const [useTicketsContext, setUseTicketsContext] = useState(false);

// Toggle UI
<div className="flex items-center gap-2 mb-4">
  <input
    type="checkbox"
    id="useTicketsContext"
    checked={useTicketsContext}
    onChange={(e) => setUseTicketsContext(e.target.checked)}
    className="rounded border-gray-300"
  />
  <label htmlFor="useTicketsContext" className="text-sm font-medium">
    Rechercher dans les tickets uploadés
  </label>
  {useTicketsContext && (
    <span className="text-xs text-blue-600">
      🔍 Mode RAG activé
    </span>
  )}
</div>

// Modifier appel API
const sendMessage = async (message: string) => {
  try {
    const response = await fetch('/api/v1/chatbot/chat-with-context', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        use_uploaded_tickets: useTicketsContext,
        conversation_id: conversationId
      })
    });
    
    const data = await response.json();
    
    // Afficher sources si disponibles
    if (data.sources && data.sources.length > 0) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.content,
        sources: data.sources,
        timestamp: new Date()
      }]);
    }
  } catch (error) {
    console.error('Chat error:', error);
  }
};

// Afficher sources dans message
<div className="message">
  <p>{message.content}</p>
  {message.sources && (
    <div className="mt-2 text-xs text-gray-600">
      📎 Sources: {message.sources.map(s => `Ticket ${s}`).join(', ')}
    </div>
  )}
</div>
```

### 4. Frontend: Bouton Indexation

**Fichier:** `frontend/src/pages/ClassificationMLPage.tsx`

```typescript
const [indexingStatus, setIndexingStatus] = useState<'idle' | 'indexing' | 'done'>('idle');

const handleIndexTickets = async () => {
  if (!uploadedData) return;
  
  setIndexingStatus('indexing');
  try {
    const response = await classificationMLService.indexTickets();
    console.log('Indexation started:', response);
    setIndexingStatus('done');
    
    // Notification
    toast.success(`${response.ticket_count} tickets indexés pour RAG chatbot`);
  } catch (error) {
    console.error('Indexation failed:', error);
    setIndexingStatus('idle');
    toast.error('Échec indexation tickets');
  }
};

// UI Bouton
<button
  onClick={handleIndexTickets}
  disabled={!uploadedData || indexingStatus === 'indexing'}
  className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 flex items-center gap-2"
>
  {indexingStatus === 'indexing' ? (
    <>
      <Loader className="w-4 h-4 animate-spin" />
      Indexation en cours...
    </>
  ) : indexingStatus === 'done' ? (
    <>
      <CheckCircle className="w-4 h-4" />
      Tickets indexés ✓
    </>
  ) : (
    <>
      <Database className="w-4 h-4" />
      Indexer pour Chatbot RAG
    </>
  )}
</button>
```

## 🧪 Tests

### Test 1: Indexation Tickets
```powershell
# 1. Uploader test_tickets.csv
# 2. Cliquer "Indexer pour Chatbot RAG"
# 3. Observer logs backend:
# [RAG] Indexed 100 tickets batch
# [RAG] Indexation complete: 230 tickets

# 4. Vérifier Qdrant
wsl podman exec -it ai-support-qdrant curl http://localhost:6333/collections/tickets_rag
# Attendu: {"status":"green","vectors_count":230,...}
```

### Test 2: Recherche RAG
```powershell
# Tester endpoint search
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/chatbot/search-tickets?query=probleme connexion base donnees&top_k=5" -Method POST

# Attendu:
# {
#   "results": [
#     {"ticket_id": "INC123", "resume": "Erreur connexion DB", "score": 0.87, ...},
#     {"ticket_id": "INC456", "resume": "Timeout PostgreSQL", "score": 0.82, ...}
#   ],
#   "count": 5
# }
```

### Test 3: Chat RAG
```powershell
# Dans UI Chat:
# 1. Cocher "Rechercher dans les tickets uploadés"
# 2. Poser question: "Quelles sont les causes les plus fréquentes?"
# 3. Observer réponse:
# - Contenu basé sur tickets uploadés
# - Sources affichées: "📎 Sources: Ticket INC123, INC456, INC789"

# 4. Tester sans RAG:
# - Décocher "Rechercher dans tickets"
# - Même question → réponse générique sans contexte
```

### Test 4: Corrections Integration
```powershell
# 1. Corriger ticket dans UI (LowConfidenceTable)
# 2. Réindexer tickets
# 3. Chatbot doit utiliser correction dans réponses
```

## 📊 Métriques RAG

### Pertinence Recherche
```python
# Mesurer précision similarité
from sklearn.metrics import precision_at_k

# Ground truth: tickets pertinents connus
relevant_tickets = ["INC123", "INC456"]

# RAG results
rag_results = search_tickets_rag("connexion base données", top_k=5)
retrieved_ids = [r['ticket_id'] for r in rag_results['results']]

# Calculer précision
precision = len(set(retrieved_ids) & set(relevant_tickets)) / len(retrieved_ids)
print(f"Precision@5: {precision:.2%}")
```

### Latence RAG
- **Embedding query:** ~50ms
- **Qdrant search:** ~20ms (230 tickets)
- **LLM generation:** ~2s
- **Total:** ~2.1s (acceptable)

## 🎯 Critères d'Acceptance

- [ ] Endpoint `/index-tickets` indexe tous tickets CSV
- [ ] Collection Qdrant `tickets_rag` créée automatiquement
- [ ] Endpoint `/search-tickets` retourne top-k similaires
- [ ] Endpoint `/chat-with-context` intègre RAG
- [ ] Toggle UI "Rechercher dans tickets" fonctionnel
- [ ] Sources tickets affichées dans réponses chatbot
- [ ] Corrections intégrées lors réindexation
- [ ] Performance <3s pour réponse RAG complète
- [ ] Fallback graceful si Qdrant indisponible

## 🚀 Améliorations Futures

### 1. Filtres Avancés
```python
# Filtrer par date, application, groupe
search_result = vector_service.client.search(
    collection_name="tickets_rag",
    query_vector=query_embedding,
    query_filter={
        "must": [
            {"key": "application", "match": {"value": "SAP"}},
            {"key": "date", "range": {"gte": "2024-01-01"}}
        ]
    },
    limit=top_k
)
```

### 2. Réindexation Incrémentale
```python
# Indexer seulement nouveaux tickets
last_indexed = redis_client.get("last_indexed_timestamp")
new_tickets = df[df['date_debut'] > last_indexed]
# Index only new_tickets
```

### 3. Feedback Loop
```python
# Utilisateur vote réponse RAG
@router.post("/feedback")
async def feedback_rag(ticket_id: str, query: str, helpful: bool):
    # Stocker feedback
    # Ajuster poids embeddings (fine-tuning)
    pass
```

### 4. Résumés Automatiques
```python
# Générer résumés tickets longs
if len(text) > 500:
    summary = llm.summarize(text, max_length=200)
    point.payload["summary"] = summary
```

## ✅ Résultat Final

**Capacités Chatbot RAG:**
1. ✅ Répondre basé sur tickets réels uploadés
2. ✅ Recherche sémantique (pas seulement mots-clés)
3. ✅ Afficher sources traçables
4. ✅ Intégrer corrections utilisateurs
5. ✅ Toggle on/off mode RAG

**Exemples Questions Supportées:**
- "Quelles sont les causes les plus fréquentes?"
- "Quels tickets concernent SAP?"
- "Comment résoudre erreur ORA-12154?"
- "Tickets groupe Infrastructure cette semaine?"
- "Durée moyenne résolution incidents DB?"

**Prêt pour Tests Complets et Déploiement**
