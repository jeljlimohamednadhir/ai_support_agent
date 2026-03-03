# Guide Utilisateur — Genergy IA

## Bienvenue dans Genergy IA

Genergy IA est votre assistant technique intelligent pour :
- 🔍 Rechercher des informations techniques
- 💬 Poser des questions sur la base de données BRASIL
- 📊 Visualiser le graphe de connaissances
- ✅ Valider des réponses de l'IA
- ⚙️ Configurer le système

## Accès à l'Application

1. Ouvrez votre navigateur
2. Accédez à `http://localhost:3000` (ou l'URL fournie)
3. L'application se lance automatiquement

## Interface Principale

### 1. Chat Assistant

**Comment l'utiliser :**

1. Cliquez sur **"Chat"** dans le menu
2. Tapez votre question dans la zone de texte
3. Appuyez sur **Entrée** ou cliquez sur **Envoyer**

**Exemples de questions :**
- "Qu'est-ce que la table t_ports ?"
- "Comment résoudre l'erreur BRASIL 1002 ?"
- "Cite-moi les 5 derniers tickets Jira"
- "Quelles fiches concernent les compteurs DSLAM ?"

**Fonctionnalités :**
- ✨ Réponses avec sources citées
- 📎 Liens vers les documents originaux
- 💾 Historique des conversations
- 👍 Feedback sur les réponses

**Astuces :**
- Utilisez **Shift + Entrée** pour ajouter une ligne
- Cliquez sur les badges de source pour voir les détails
- L'historique est sauvegardé automatiquement

### 2. Base de Connaissances

**Visualiser le Graphe :**

1. Cliquez sur **"Connaissances"**
2. Le graphe se charge automatiquement
3. Utilisez les contrôles pour :
   - 🔍 Zoomer/dézoomer
   - 🔄 Rafraîchir
   - 🖱️ Cliquer sur un nœud pour voir les détails

**Types de nœuds :**
- 🔵 **Bleu** : Fonctions
- 🟣 **Violet** : Classes
- 🟢 **Vert** : Modules
- 🟠 **Orange** : Fichiers
- 🔴 **Rouge** : API

**Recherche :**
- Utilisez la barre de recherche en haut
- Tapez un nom de table, fonction ou fichier
- Les résultats s'affichent instantanément

### 3. Dashboard

**Statistiques en temps réel :**

- 📊 Nombre de tickets traités
- 📈 Taux de résolution
- ⏱️ Temps de réponse moyen
- 🔥 Erreurs les plus fréquentes

**Graphiques :**
- **Activité** : Évolution dans le temps
- **Top erreurs** : Les plus signalées
- **Performance** : Métriques de qualité

### 4. Validation

**Améliorer l'IA :**

1. Cliquez sur **"Validation"**
2. Consultez les réponses en attente
3. Pour chaque réponse :
   - ✅ **Valider** si correcte
   - ❌ **Rejeter** si incorrecte
   - ✏️ **Corriger** si besoin d'ajustement

**Votre feedback aide à :**
- Améliorer la précision de l'IA
- Enrichir la base de connaissances
- Affiner les réponses futures

### 5. Paramètres

**Configuration du système :**

#### Onglet "LLM & IA"

- **Fournisseur** : Groq, OpenAI ou Anthropic
- **Modèle** : Choisissez le modèle LLM
- **Température** : Contrôle la créativité (0 = précis, 2 = créatif)
- **Tokens max** : Longueur maximale des réponses
- **Clé API** : (Optionnel) Votre propre clé

#### Onglet "Bases de données"

**Neo4j (Graphe de connaissances) :**
- URI : Adresse du serveur Neo4j
- Utilisateur et mot de passe

**Qdrant (Stockage vectoriel) :**
- Hôte et port du serveur Qdrant

**PostgreSQL :**
- URI de connexion (optionnel)

#### Onglet "Interface"

- **Thème** : Clair, Sombre ou Automatique
- **Langue** : Français ou Anglais
- **Éléments par page** : Nombre d'items affichés
- **Notifications** : Activer/désactiver

**Actions :**
- 💾 **Enregistrer** : Sauvegarder vos modifications
- 🔄 **Réinitialiser** : Revenir aux valeurs par défaut

## Cas d'Usage Fréquents

### Rechercher une Table

1. Posez la question : *"Qu'est-ce que la table t_ports ?"*
2. L'IA vous donne :
   - Description de la table
   - Colonnes principales
   - Relations avec d'autres tables
   - Exemples d'utilisation

### Résoudre une Erreur

1. Demandez : *"Comment résoudre l'erreur BRASIL 1002 ?"*
2. L'IA fournit :
   - Description de l'erreur
   - Causes possibles
   - Étapes de résolution
   - Fiches de résolution associées

### Lister les Tickets

1. Tapez : *"Cite-moi les 5 derniers tickets Jira"*
2. Vous obtenez :
   - Liste des tickets récents
   - Clé, résumé, statut
   - Date de création
   - Priorité

### Explorer le Graphe

1. Allez dans **Connaissances**
2. Cherchez un élément (ex: "dslam")
3. Cliquez sur un nœud
4. Explorez les relations

## Bonnes Pratiques

### Pour de Meilleures Réponses

✅ **À faire :**
- Poser des questions précises
- Utiliser des mots-clés techniques
- Citer des noms de tables ou erreurs

❌ **À éviter :**
- Questions trop vagues
- Plusieurs questions en une
- Contexte insuffisant

### Exemples

**Bonne question :**
> "Quelle est la structure de la table t_dslam_counters et comment l'interroger ?"

**Mauvaise question :**
> "Comment ça marche ?"

## Dépannage

### Problème : Aucune réponse

**Solutions :**
1. Vérifiez la connexion réseau
2. Assurez-vous que les services sont démarrés
3. Consultez les paramètres de connexion
4. Contactez l'administrateur

### Problème : Réponses hors sujet

**Solutions :**
1. Reformulez votre question
2. Ajoutez plus de contexte
3. Utilisez des termes plus précis
4. Soumettez un feedback négatif

### Problème : Graphe ne charge pas

**Solutions :**
1. Rafraîchissez la page
2. Vérifiez que Neo4j est accessible
3. Consultez l'onglet Paramètres → Bases de données
4. Cliquez sur "Actualiser" dans le graphe

## Raccourcis Clavier

- **Ctrl/Cmd + K** : Focus sur la recherche
- **Shift + Entrée** : Nouvelle ligne dans le chat
- **Entrée** : Envoyer le message
- **Échap** : Fermer les modals

## Support

**Besoin d'aide ?**

- 📖 Consultez la documentation complète : `docs/`
- 💬 Contactez l'équipe support
- 🐛 Signalez un bug via GitHub Issues
- 💡 Proposez des améliorations

## Mises à Jour

L'application est régulièrement mise à jour avec :
- Nouvelles fonctionnalités
- Améliorations de performance
- Corrections de bugs
- Enrichissement de la base de connaissances

Les mises à jour sont automatiques et transparentes.

## Confidentialité & Sécurité

- 🔒 Vos conversations sont privées
- 🛡️ Les données sont chiffrées
- 🔐 Authentification sécurisée
- 📊 Pas de partage de données externes

---

**Version :** 1.0.0  
**Dernière mise à jour :** Janvier 2026  
**Support :** support@genergy-ia.com
