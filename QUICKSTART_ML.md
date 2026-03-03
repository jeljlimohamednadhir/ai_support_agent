# 🚀 Guide de Démarrage Rapide - Classification ML

## Installation et Lancement

### 1️⃣ Backend Setup

```powershell
# Naviguer vers le backend
cd backend

# Installer les dépendances ML
pip install scikit-learn==1.3.2 pandas==2.1.4 numpy==1.26.3 scipy==1.11.4 unidecode==1.3.7 reportlab==4.0.9 python-multipart

# Ou installer tout depuis requirements.txt
pip install -r requirements.txt

# Lancer le serveur
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

✅ Backend disponible sur: http://localhost:8000

### 2️⃣ Frontend Setup

```powershell
# Nouvelle fenêtre PowerShell
cd frontend

# Installer les dépendances (si pas déjà fait)
npm install

# Lancer le serveur dev
npm run dev
```

✅ Frontend disponible sur: http://localhost:5173

### 3️⃣ Test Rapide API (Optionnel)

```powershell
# Depuis backend/
python test_classification_ml.py
```

## 🎯 Premier Workflow

### Étape 1: Accéder à l'interface
1. Ouvrir http://localhost:5173
2. Cliquer sur **"GenIQ ML"** dans la sidebar (icône ✨)

### Étape 2: Upload CSV
1. Cliquer sur **"Upload CSV"** en haut à droite
2. Sélectionner un fichier CSV avec des tickets
   - Colonnes minimales: `resume`, `cause`, `solution`, `ticket_id`
   - Exemple fourni: `backend/test_tickets.csv`
3. Attendre l'analyse automatique

### Étape 3: Entraîner le modèle
1. Aller dans l'onglet **"Entraînement ML"**
2. Sélectionner:
   - Colonne de texte: `texte_complet` (auto-créée)
   - Colonne de label: `cause_canonique` (détectée)
   - Max features: 5000 (par défaut)
3. Cocher "Utiliser hint cause" si besoin
4. Cliquer **"Entraîner le modèle"**
5. Attendre ~10-30 secondes
6. Visualiser les métriques (F1-score, matrice confusion)

### Étape 4: Prédire
1. Aller dans l'onglet **"Correction Tickets"**
2. Ajuster le seuil de confiance (curseur)
3. Cliquer **"Lancer la prédiction"**
4. Visualiser:
   - Total acceptés/rejetés
   - Coverage (% tickets > seuil)
   - Table tickets faible confiance

### Étape 5: Corriger (optionnel)
1. Dans la table, saisir le label corrigé
2. Cliquer **"Sauver"** pour chaque correction
3. Les corrections sont sauvegardées dans `data/ml_corrections.jsonl`
4. Possibilité de réentraîner avec les corrections

### Étape 6: Analyser
1. **Résumé Exécutif**: KPIs, highlights, recommandations
2. **Synthèse**: Pareto causes/catégories, aperçu données
3. **Analyse Interactive**: Timeseries, top valeurs

### Étape 7: Exporter
1. Onglet **"Export PDF"**
2. Cliquer **"Télécharger le rapport PDF"**
3. PDF généré avec analyse complète

## 📊 Structure Données CSV

### Colonnes Recommandées
```csv
ticket_id,resume,cause,solution,signalement,application,date_debut,groupe,statut
```

### Colonnes Détectées Automatiquement
- `resume`: Description ticket
- `cause`: Cause identifiée
- `solution`: Solution appliquée
- `signalement`: Détails technique
- `application`: Application concernée
- `ticket_id`: Identifiant unique
- `date_debut`: Date ouverture
- `groupe`: Groupe support
- `statut`: État ticket

### Colonnes Créées par Préparation
- `texte_complet`: Concaténation resume+cause+solution+signalement
- `text_ml_postmortem`: Comme texte_complet mais sans cause (pour éviter data leakage)
- `cause_canonique`: Version normalisée de la cause
- `categorie_intelligente`: Catégorie basée mots-clés
- `mttr_days`: Durée résolution en jours
- `date`, `mois`, `semaine`: Périodes temporelles
- `codes_erreurs`: Codes extraits (B4002, ORA-xxx, HTTP xxx)

## 🔧 Configuration Mots-Clés

### Accès Configuration
Onglet **"Configuration"** → Éditer catégories et mots-clés

### Catégories Par Défaut (10)
1. **Intégration/Interfaces SI**: API, REST, SOAP, webservice, flux, ESB, MOM, Kafka
2. **Blocage commande**: commande, order, bloqué, workflow, statut, validation
3. **Erreurs techniques/Réseau**: timeout, connexion, réseau, firewall, HTTP, SSL, certificat, ORA-, SQLSTATE
4. **Qualité données/Référentiels**: données, référentiel, doublon, inconsistance, qualité, corruption, import
5. **Paramétrage/Equipement**: paramétrage, configuration, routeur, switch, équipement, device
6. **Opérations/TP**: batch, traitement, job, cron, scheduler, sauvegarde, backup
7. **Changements/MEP/Reprises**: MEP, déploiement, rollback, migration, upgrade, reprise
8. **Habilitations/Procédures**: habilitation, accès, rôle, permission, procédure, documentation
9. **Demandes/Evolution**: demande, évolution, feature, développement
10. **Performance**: performance, lent, latence, mémoire, CPU, slow query

### Actions
- ✏️ Modifier mots-clés existants
- ➕ Ajouter nouvelle catégorie
- 🗑️ Supprimer catégorie
- 🔄 Réinitialiser configuration

## 🎓 Métriques ML Expliquées

### F1-Score
- Score de 0 à 1
- **> 0.8**: Excellent
- **0.6-0.8**: Bon
- **< 0.6**: À améliorer

### Seuil de Confiance
- **Recommandé**: Auto-calculé (cible 85% précision)
- **Ajustable**: 0.0 (tout accepter) à 1.0 (très sélectif)
- **Trade-off**: Coverage vs Précision

### Matrice de Confusion
- **Diagonale**: Prédictions correctes
- **Hors diagonale**: Erreurs de classification
- **Couleur**: Intensité = fréquence

### Coverage
- % tickets acceptés (confiance > seuil)
- **> 70%**: Bon coverage
- **< 50%**: Modèle peu confiant

## 🐛 Troubleshooting

### Erreur "Model not trained"
→ Entraîner le modèle dans l'onglet "Entraînement ML"

### Erreur "No uploaded data"
→ Upload CSV d'abord

### Erreur "Not enough labeled data"
→ CSV doit contenir ≥ 10 lignes avec labels

### Prédictions toutes rejetées
→ Baisser le seuil de confiance
→ Vérifier qualité données (textes vides?)

### Backend timeout
→ Augmenter timeout Axios (30s par défaut)
→ Vérifier logs backend

### CSV non détecté
→ Vérifier encoding (UTF-8, cp1252, latin1 supportés)
→ Vérifier séparateur (;, , TAB, | supportés)

## 📁 Fichiers Générés

```
backend/data/
├── model_classifier.pkl      # Modèle ML entraîné
├── vectorizer.pkl            # Vectoriseur TF-IDF
├── model_card.json           # Métadonnées modèle
├── keywords_config.json      # Configuration mots-clés
└── ml_corrections.jsonl      # Log corrections manuelles
```

## 🚨 Limitations Actuelles

- ⚠️ État global in-memory (perdu au redémarrage backend)
- ⚠️ 1 seul modèle actif à la fois
- ⚠️ Pas d'authentification
- ⚠️ Upload limité à 1 fichier

### Roadmap Production
- [ ] Persistence PostgreSQL/Redis
- [ ] Multi-tenancy
- [ ] Authentification JWT
- [ ] Versioning modèles
- [ ] Batch predictions async
- [ ] Real-time monitoring

## 📚 Ressources

- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **Code Source**: `backend/app/api/v1/endpoints/classification_ml.py`
- **Documentation**: `INTEGRATION_COMPLETE.md`
- **Test CSV**: `backend/test_tickets.csv`

## ✅ Checklist Démarrage

- [ ] Backend lancé (port 8000)
- [ ] Frontend lancé (port 5173)
- [ ] Dépendances ML installées
- [ ] Répertoire `data/` créé
- [ ] CSV de test préparé
- [ ] Navigation "GenIQ ML" visible
- [ ] Upload CSV fonctionnel
- [ ] Entraînement réussi
- [ ] Prédictions lancées
- [ ] Visualisations affichées

---

**Besoin d'aide ?** Consulter `INTEGRATION_COMPLETE.md` pour documentation complète.

**Feedback/Issues ?** Ouvrir un ticket dans le projet.

🎉 **Bonne utilisation de Classification ML !**
