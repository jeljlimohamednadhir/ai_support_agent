# Support Pilot AI — FAQ Présentation
## Réponses préparées aux questions anticipées

---

### 1. « Et si l'IA se trompe ? »

Trois garde-fous :
- **Mode lecture seule** — aucune modification possible en production.
- **Couche de validation** — chaque réponse est vérifiée avant envoi : entités inventées ou tables inexistantes → bloquées automatiquement.
- **Traçabilité** — chaque affirmation est liée à sa source (n° FR, fichier log, résultat SQL). L'expert vérifie en un clic.

→ L'IA propose, l'humain dispose.

---

### 2. « Ça va remplacer nos experts N3 ? »

Non, ça les **libère**. Aujourd'hui l'expert passe 80% du temps à chercher dans 5 sources. L'IA fait ce travail de recherche. L'expert reste celui qui **décide** et **agit**.

→ C'est un GPS : ça ne remplace pas le conducteur, ça lui évite de chercher la route.

---

### 3. « Quelles données l'IA utilise ? C'est sécurisé ? »

L'IA utilise uniquement :
- Fiches FR internes (déjà documentées)
- Code source BRASIL (indexé localement)
- Logs et BDD via SSH en **lecture seule**

Aucune donnée ne sort du périmètre Orange. Le LLM (OpenRama) est hébergé en interne. Pas d'envoi vers le cloud externe.

---

### 4. « C'est quoi le coût d'infrastructure ? »

Infra légère :
- Un serveur applicatif (FastAPI + React)
- Qdrant (base vectorielle, ~2 Go RAM)
- Neo4j (graphe de connaissances)
- Accès SSH existants (pas de nouveau réseau)

Pas de GPU dédié — LLM via API interne. Coût marginal vs **209 heures/an** économisées (279 incidents × 45 min).

---

### 5. « Pourquoi pas simplement un moteur de recherche sur les FR ? »

Un moteur de recherche retourne des **documents**. Support Pilot AI retourne une **réponse structurée** :
- Cause racine identifiée
- Preuves corrélées depuis plusieurs sources
- Procédure exacte à suivre
- Code source concerné

L'expert n'a plus besoin de lire 3 fiches et croiser mentalement — c'est déjà fait.

---

### 6. « C'est prêt pour la prod ? »

Le MVP est fonctionnel. Pour la prod :
- Validation sécurité (déjà lecture seule) ✓
- Shadow mode (l'IA répond, l'expert compare)
- Accès réseau SSH stabilisé

→ Pilote possible avec 2-3 experts en **quelques jours**.

---

### 7. « Comment l'outil s'améliore avec le temps ? »

Chaque résolution confirmée par un expert est enregistrée automatiquement (boucle d'apprentissage). Plus on l'utilise, plus il est précis.

→ Capitalisation automatique, contrairement aux wikis qu'on oublie de mettre à jour.

---

### 8. « Et pour les autres applications, pas que BRASIL ? »

L'architecture est **multi-tenant**. Le pipeline est générique, seule la base de connaissances change. Brancher une nouvelle app = indexer ses FR + son schéma.

→ Roadmap moyen terme.

---

### 9. « Quel est le taux de bonnes réponses ? »

Sur les scénarios représentatifs des incidents les plus fréquents : **95%+ de réponses exploitables**. Les 5% restants = cas sans documentation → l'IA le dit clairement au lieu d'inventer.

---

### 10. « Combien de temps a pris le développement ? »

Prototype fonctionnel en **quelques semaines**, équipe réduite. C'est la puissance des briques IA modernes (LLM, vector search, RAG) — on assemble plus qu'on ne code from scratch.

---

### 11. « Quelle est la différence avec ChatGPT / Copilot ? »

ChatGPT est **généraliste** et ne connaît pas BRASIL. Support Pilot AI :
- Connaît le schéma exact de la BDD (130+ tables)
- A accès aux logs en temps réel
- Respecte les procédures FR validées
- Ne peut pas halluciner un nom de table (validation intégrée)

→ C'est un outil **spécialisé métier**, pas un chatbot générique.

---

### 12. « Et la confidentialité des données clients ? »

- Aucune donnée client nominative n'est stockée dans l'index vectoriel
- Les requêtes SQL retournent des données techniques (états, compteurs) — pas de données personnelles
- Les logs sont filtrés côté serveur avant indexation
- Conforme RGPD par design

---

### 13. « Qui maintient l'outil au quotidien ? »

Maintenance minimale :
- Les FR sont réindexées quand elles changent (script automatique)
- Le modèle LLM est mis à jour par l'équipe plateforme (OpenRama)
- Les feature flags permettent d'activer/désactiver chaque couche sans redéploiement

→ Pas besoin d'une équipe IA dédiée pour l'exploitation.

---

### 14. « Comment on mesure le ROI ? »

KPIs à suivre dès le pilote :
- Temps moyen de résolution (avant/après)
- Nombre d'escalades N2→N3 évitées
- Taux de satisfaction expert (feedback intégré)
- Nombre de résolutions capitalisées automatiquement

→ Dashboard de suivi prévu dans la roadmap court terme.

---

### 15. « Et si le serveur SSH est down ? »

Le système fonctionne en **mode dégradé** :
- Les fiches FR et le code source restent consultables (indexés localement)
- L'IA indique clairement « serveurs inaccessibles » et propose les vérifications manuelles à faire
- Aucun plantage — graceful fallback intégré

---

### 16. « Peut-on l'utiliser en astreinte / hors heures ? »

Oui, c'est un des avantages clés :
- Disponible **24/7** (pas de dépendance humaine pour la recherche)
- L'astreinte N2 peut obtenir une première analyse sans réveiller le N3
- Réduction du stress en HNO (Heures Non Ouvrées)

---

### 17. « Comment gérer les mises à jour de BRASIL ? »

Quand BRASIL évolue :
- Nouveau schéma → script de réindexation automatique
- Nouvelles FR → ajout dans Qdrant en quelques minutes
- Nouveau code Java → réindexation du graphe Neo4j

→ Processus intégré dans la CI/CD, pas de rewrite nécessaire.

---

### 18. « Quel est le risque si on ne fait rien ? »

- Les experts seniors partent → la connaissance part avec eux
- La charge augmente → plus d'incidents, même équipe
- Les SLA se dégradent → impact client
- Les nouveaux mettent 3 mois à être autonomes → coût de rotation

→ Le risque de ne rien faire est supérieur au risque d'essayer.

---

## 🔧 Questions techniques — Ingestion, traitement, raisonnement

---

### 19. « Comment les fiches FR sont ingérées ? »

Pipeline d'ingestion :
1. Les PDF/Word des FR sont parsés et découpés en **chunks sémantiques** (~500 tokens)
2. Chaque chunk est transformé en vecteur via **sentence-transformers** (modèle multilingual)
3. Les vecteurs sont stockés dans **Qdrant** avec métadonnées (n° FR, titre, catégorie)
4. Le schéma BDD BRASIL (400+ tables) est extrait et indexé séparément

→ Réindexation complète en ~5 minutes. Ajout incrémental d'une FR en quelques secondes.

---

### 20. « Comment le code source Java est indexé ? »

- Le code est parsé statiquement : classes, méthodes, signatures, lignes
- Un **graphe Neo4j** stocke les relations (classe → méthode → exceptions → tables utilisées)
- Les validateurs (conditions `if/throw`) sont extraits avec leur condition exacte
- Recherche par nom de méthode, nom de classe, ou exception levée

→ Quand l'utilisateur demande "quelle méthode supprime un DSLAM", on traverse le graphe, pas du full-text search.

---

### 21. « Comment le chatbot comprend la question ? »

Deux niveaux d'analyse :
1. **Intent detection** — classifie la question (diagnostic, code lookup, workflow, forensic logs…)
2. **Entity extraction** — détecte les identifiants réseau (DSLAM, ND, VLAN, OLT) via regex + NER

Exemples :
- "Suppression DSROB362 impossible" → intent=`delete_equipment`, entity=`DSROB362`
- "Montre les logs de DSTEL460" → intent=`forensic_logs`, entity=`DSTEL460`

→ C'est du NLP déterministe (pas de LLM pour cette étape) = rapide et prédictible.

---

### 22. « Comment fonctionne la recherche vectorielle ? »

1. La question est encodée en vecteur (même modèle que l'indexation)
2. Qdrant retourne les **top-K chunks** les plus proches sémantiquement
3. Les résultats sont filtrés par pertinence (score > seuil) et dédupliqués

→ Avantage vs keyword search : "VLAN occupé" trouve la FR 136c "compteurs VC VP VLAN" même sans les mêmes mots exacts.

---

### 23. « Qu'est-ce que la corrélation multi-sources ? »

C'est le **cœur du raisonnement** (Layer 5). Le moteur :
1. Reçoit les preuves de toutes les sources (FR, logs live, BDD, code, incidents)
2. Génère des **hypothèses** avec un score pondéré par type de source :
   - Règles SFD : poids 1.5 (source de vérité)
   - Fiches FR : poids 1.3
   - Incidents historiques : poids 1.0
   - Logs : poids 0.85
3. Classe les hypothèses et injecte le **top-3** dans le prompt LLM

→ Le LLM ne raisonne pas à partir de rien : il reçoit des hypothèses déjà classées et les reformule.

---

### 24. « Comment le LLM génère la réponse finale ? »

Le LLM (OpenRama) n'est **pas** un raisonneur — c'est un **formateur** :
- Il reçoit un contexte structuré pré-calculé (cause racine, preuves, procédure)
- Son rôle : reformuler en français clair, structurer le diagnostic
- Il n'a **pas accès** à la base de connaissances brute — seulement au résultat du pipeline

→ Architecture "Deterministic Core + LLM Formatter" = pas d'hallucination par re-raisonnement.

---

### 25. « Comment la validation anti-hallucination fonctionne ? »

Trois étapes après la génération LLM :
1. **Validité des entités** — tout nom de table mentionné doit exister dans le schéma BRASIL (400+ tables indexées). Sinon → remplacé par un marqueur d'erreur.
2. **Validité métier** — les procédures citées doivent correspondre à une FR existante.
3. **Ancrage dans les preuves** — les affirmations doivent être traçables à une source.

Si la validation échoue → la réponse est **bloquée** et remplacée par un message safe.

---

### 26. « Comment les requêtes SQL live fonctionnent ? »

Quand une entité réseau est détectée :
1. Connexion SSH au serveur BDD (`op49mdb11`) via pool de connexions persistantes
2. Exécution de requêtes `SELECT` paramétrées (pas de SQL dynamique, pas de mutation)
3. Les résultats sont injectés comme preuves dans le pipeline de corrélation

Sécurité :
- Uniquement des `SELECT` — toute commande `UPDATE/DELETE/INSERT` est interdite au niveau code
- Timeout de 10s par requête
- Connexion avec compte en lecture seule

---

### 27. « Quelle est la latence typique d'une réponse ? »

- Question simple (code lookup, FR) : **3-5 secondes**
- Question avec diagnostic live (SSH + BDD) : **8-15 secondes**
- Premier appel (cold start sentence-transformers) : **30-60 secondes** (une seule fois)

Le goulot d'étranglement est le LLM (1-3s) et le SSH quand les serveurs sont lents.

---

### 28. « Comment le système gère le contexte conversationnel ? »

Un **ConversationState** est maintenu par session :
- Historique des échanges (derniers 10 messages)
- Entités détectées (DSLAM, ND, VLAN…)
- Hypothèses en cours d'investigation
- Intent courant

→ Si l'utilisateur dit "montre les logs" après avoir parlé de DSROB362, le système sait que c'est les logs de DSROB362.

---

### 29. « Quelle est la différence entre RAG classique et votre approche ? »

| RAG classique | Support Pilot AI |
|---------------|-----------------|
| Retrieval → LLM raisonne | Retrieval → Corrélation → Validation → LLM formate |
| Le LLM fait le raisonnement | Le raisonnement est déterministe (pré-calculé) |
| Pas de vérification post-LLM | Validation anti-hallucination active |
| Sources plates | Sources pondérées par autorité (SFD > FR > Logs) |
| Pas de données live | Accès SSH temps réel (BDD + logs) |

→ On va au-delà du RAG : c'est du **RAG + corrélation + validation + live evidence**.

---

### 30. « Comment on ajoute une nouvelle source de données ? »

Architecture modulaire :
- Nouvelle base de connaissances → indexer dans Qdrant (script d'ingestion)
- Nouveau serveur SSH → ajouter dans le pool de connexions (config)
- Nouveau type de requête SQL → ajouter un template paramétré
- Nouveau type de log → ajouter un pattern de parsing

→ Extensible sans réécriture du pipeline principal.

