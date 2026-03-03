# 🎯 Intégration Classification ML dans AI Support Agent

## ✅ Intégration Complétée

L'interface **GenIQ** (Classification ML, SharePoint, Entraînement) a été intégrée comme un nouvel onglet dans **AI Support Agent**.

### 📁 Fichiers Modifiés

1. **Nouvelle Page** : `frontend/src/pages/ClassificationPage.tsx`
   - Intègre l'interface Streamlit via iframe
   - Détection automatique de disponibilité
   - Fallback si Streamlit non démarré

2. **Routes** : `frontend/src/App.tsx`
   - Import de `ClassificationPage`
   - Route `/classification` ajoutée

3. **Navigation** : `frontend/src/components/Layout.tsx`
   - Nouvel item "Classification ML" avec icône Brain 🧠
   - Ajout dans le menu latéral

---

## 🚀 Utilisation

### 1. Démarrer le Backend API (Backend FastAPI)

```powershell
cd ai-support-agent/backend
python -m uvicorn app.main:app --reload --port 8000
```

**Ou avec le projet fusionné (try1/) :**

```powershell
cd try1
.\scripts\start_api.ps1
```

### 2. Démarrer l'Interface Streamlit (GenIQ)

```powershell
cd try1
.\scripts\start_ui.ps1
```

**Ou manuellement :**

```powershell
cd try1
python -m streamlit run genergy/ui/streamlit_app.py --server.port 8501
```

### 3. Démarrer le Frontend React

```powershell
cd ai-support-agent/frontend
npm run dev
```

### 4. Accès

Ouvrez http://localhost:5173 (ou le port affiché par Vite)

Dans le menu latéral, cliquez sur **"Classification ML" 🧠**

---

## 🎨 Fonctionnalités de la Page Classification

### Interface Intégrée (via iframe Streamlit)
- ✅ **Classification automatique** de tickets/fichiers
- ✅ **Entraînement du modèle ML** (TF-IDF + Logistic Regression)
- ✅ **Évaluation du modèle** (accuracy, F1-score, matrice de confusion)
- ✅ **Correction humaine** et réapprentissage
- ✅ **Synchronisation SharePoint** (upload/download avec résolution de conflits)
- ✅ **Gestion des mots-clés** et configuration
- ✅ **Export PDF** des rapports

### Détection Intelligente
- Vérification automatique si Streamlit est lancé (`/healthz`)
- Message d'erreur clair avec instructions si non disponible
- Bouton "Réessayer" pour recheck
- Lien "Ouvrir en plein écran" pour nouvelle fenêtre

---

## 🏗️ Architecture

```
ai-support-agent (Interface principale React)
├── Frontend React (port 5173)
│   └── /classification → Iframe vers Streamlit
│
├── Backend FastAPI (port 8000)
│   └── API endpoints (chatbot, collector, etc.)
│
└── Interface Streamlit (port 8501)
    └── GenIQ UI (classification ML, SharePoint, etc.)
```

### Flux de Communication

1. **Frontend React** (http://localhost:5173)
   - Menu latéral avec "Classification ML"
   - Page avec iframe Streamlit

2. **Streamlit** (http://localhost:8501)
   - Interface GenIQ complète
   - Communique directement avec le backend API

3. **Backend API** (http://localhost:8000)
   - Endpoints FastAPI
   - Services (ML, SharePoint, Neo4j, Qdrant, etc.)

---

## 🔧 Configuration Streamlit

Pour un meilleur rendu dans l'iframe, Streamlit utilise le paramètre `?embed=true` qui :
- Masque le menu hamburger
- Réduit les marges
- Optimise pour l'intégration

**URL complète de l'iframe :**
```
http://localhost:8501?embed=true
```

---

## 🎯 Avantages de cette Approche

### ✅ Pros
- **Séparation des préoccupations** : React pour navigation, Streamlit pour ML
- **Réutilisation complète** du code GenIQ (3037 lignes)
- **Pas de réécriture** en React/TypeScript
- **Indépendance** : Streamlit peut être lancé séparément si besoin
- **Maintenabilité** : modifications Streamlit ne touchent pas React

### ⚠️ Considérations
- Nécessite 2 serveurs (Vite + Streamlit)
- Communication iframe (peut nécessiter postMessage pour événements complexes)
- Authentification à gérer si ajoutée

---

## 🚀 Commandes Rapides

### Tout démarrer (avec try1/)

```powershell
# Terminal 1 - API
cd try1
.\scripts\start_api.ps1

# Terminal 2 - Streamlit
cd try1
.\scripts\start_ui.ps1

# Terminal 3 - Frontend React
cd ai-support-agent/frontend
npm run dev
```

### Ou tout en un (si script créé)

```powershell
# À la racine
.\scripts\start_all_with_frontend.ps1  # À créer si besoin
```

---

## 📖 Documentation

- **Streamlit** : http://localhost:8501
- **API Docs** : http://localhost:8000/docs
- **Frontend** : http://localhost:5173

---

## 🔮 Améliorations Futures

### Possible V2
- [ ] Authentification partagée entre React et Streamlit
- [ ] Communication bidirectionnelle via postMessage
- [ ] Notification React quand un modèle est entraîné
- [ ] Thème unifié (dark mode synchronisé)
- [ ] SSO centralisé

### Alternative (si besoin)
- Réécrire l'interface ML en React/TypeScript
  - Avantage : expérience utilisateur unifiée
  - Inconvénient : ~2-3 jours de développement, maintenance doublée

---

**✨ L'intégration est maintenant complète ! L'interface GenIQ est accessible via l'onglet "Classification ML" 🧠 dans AI Support Agent.**
