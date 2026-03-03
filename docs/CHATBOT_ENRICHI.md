# 🤖 Chatbot BRASIL - Réponses Enrichies avec Corrélation

## ✅ Modifications Appliquées

Le LLM a été configuré pour structurer ses réponses en corrélant automatiquement :
- **📋 Fiches de résolution (FR)** : Procédures documentées, étapes de correction
- **📊 Tables de la base de données** : Structure PostgreSQL, colonnes, relations

## 🎯 Format de Réponse Structuré

Le chatbot répond maintenant selon ce modèle :

```
1️⃣ **Contexte** : Explique le problème/la question

2️⃣ **Tables concernées** : Liste des tables impliquées avec leur rôle
   📊 Table t_ports : Gestion des ports réseau
   📊 Table t_cards : Configuration des cartes
   
3️⃣ **Étapes de résolution** : Procédure détaillée numérotée
   Étape 1: Vérifier la colonne X dans la table Y
   Étape 2: Exécuter la requête SQL suivante...
   Étape 3: Valider dans l'interface BRASIL...

4️⃣ **Points d'attention** : Warnings et best practices
   ⚠️ Attention aux contraintes sur la table...
   ⚠️ Toujours sauvegarder avant modification...

5️⃣ **Sources** : Références précises
   📋 FR 012 - Erreur BRASIL 1002
   📊 Table t_application_configs
```

## 📋 Exemples de Questions Supportées

### ❓ Questions sur les Erreurs
- "Comment résoudre l'erreur BRASIL 1002 ?"
- "Que faire en cas de compteurs DSLAM à 100% ?"
- "Explication de l'erreur B4002 INTERNE BRASIL"

### ❓ Questions sur les Tables
- "Qu'est-ce que la table t_ports ?"
- "Combien de colonnes a la table t_equipments ?"
- "Quel est le rôle de la table t_dslam_assignments ?"

### ❓ Questions avec Corrélation (NOUVEAU ✨)
- "Quelles tables sont mentionnées dans la FR 012 ?"
- "Quelles fiches FR concernent la table t_ports ?"
- "Comment les compteurs DSLAM sont-ils stockés en base ?"

## 🛠️ Test du Chatbot

### Option 1 : Via l'interface Web

1. Lance le backend :
   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```

2. Lance le frontend :
   ```bash
   cd frontend
   npm run dev
   ```

3. Ouvre http://localhost:5173 et pose tes questions dans le chat

### Option 2 : Via le script de test API

1. Lance le backend (même commande que ci-dessus)

2. Exécute le script de test :
   ```bash
   cd backend
   python test_api_chat.py
   ```

## 🔍 Architecture de la Solution

### Composants Modifiés

**`chatbot_service.py`** :
- ✅ `_search_knowledge()` : Distingue tables vs fiches dans les résultats
- ✅ `_build_context_prompt()` : Sépare contexte DB vs procédures
- ✅ `process_message()` : Prompt système enrichi avec instructions de corrélation
- ✅ Sources retournées : Emoji 📊 pour tables, 📋 pour fiches FR

### Prompt Système (System Prompt)

```
Tu es un assistant expert de l'application BRASIL chez Orange. 
Tu aides les techniciens et développeurs à résoudre les problèmes 
en combinant la connaissance de la base de données PostgreSQL 
et les procédures documentées dans les fiches de résolution. 
Tu corrèles toujours les informations techniques (tables, colonnes) 
avec les étapes opérationnelles (fiches FR).
```

### Instructions du Prompt Utilisateur

```
- Structure ta réponse en ÉTAPES NUMÉROTÉES si c'est une procédure
- Fais la CORRÉLATION entre les fiches de résolution et les tables DB
- Si une fiche mentionne des tables, indique QUELLES TABLES
- Si la question concerne une table, indique QUELLES FICHES y font référence
- Cite systématiquement tes sources (numéros de FR et noms de tables)
- Utilise des emojis : 📋 fiches, 📊 tables, ⚠️ erreurs
```

## 📊 Base de Connaissances Actuelle

- **128 tables** PostgreSQL (brasil_db.sql)
- **51 fiches** de résolution (.docx, FR 001 à FR 999)
- **Qdrant** collection : `code_knowledge` (vecteurs 384-dim)
- **Neo4j** : Vide pour l'instant (future extension pour graphe relationnel)

## 🚀 Prochaines Améliorations Possibles

1. **Graphe Neo4j** : Créer des relations explicites
   - `(Fiche)-[:MENTIONS]->(Table)`
   - `(Erreur)-[:CORRIGEE_PAR]->(Fiche)`
   - `(Table)-[:LIEE_A]->(Table)`

2. **Extraction automatique** des mentions de tables dans les fiches
   - Parser le contenu des FR pour identifier les noms de tables
   - Créer les liens automatiquement

3. **Historique de conversations**
   - Stocker les conversations en base
   - Apprendre des feedbacks utilisateurs

4. **Injection du code source**
   - Parser les fichiers Python de l'application BRASIL
   - Lier code → tables → fiches FR
