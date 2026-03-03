Genergy IA — Project Plan
==========================

Objectif
--------
Construire un agent d'assistance IA (Genergy IA) capable de :

- Indexer et corréler des sources techniques (JIRA, dépôts de code, logs, bases de données) dans une base de connaissances hybride (graph + vecteurs).
- Répondre aux questions techniques avec RAG (vector store + knowledge graph) et fournir des sources traçables.
- Offrir des intégrations opérationnelles (synchronisation JIRA, accès multi-utilisateurs, UI de consultation et validation).

Portée actuelle (aujourd'hui — 2026-01-12)
----------------------------------------

- Backend Python avec services principaux : `GraphService` (Neo4j), `VectorService` (Qdrant), `ChatbotService`.
- `GraphService` : ajout de gestion des relations, corrélations et statistiques; sérialisation des métadonnées.
- `ChatbotService` : détection des requêtes de type "liste" et handler direct renvoyant les N derniers tickets Jira (bypass LLM pour déterminisme).
- `VectorService` : ingestion de tickets Jira de test dans Qdrant; signature `add_code_snippet(code, metadata, snippet_id)`.
- Environnement local : Qdrant et Neo4j démarrés via Podman sur WSL; tests manuels démontrant la fonctionnalité "les 5 derniers Jira".

Hypothèses et contraintes
-------------------------

- Neo4j exige des propriétés primitives pour les nœuds et relations.
- Qdrant stocke des payloads top-level (ex: `type`, `key`, `summary`).
- L'accès JIRA peut être par compte personnel (PAT) ou via un compte de service recommandé pour partage.
- Déploiement initial prévu en conteneurs (Podman/Docker). LLM externe (Groq/Llama) utilisé pour génération.

Objectifs à moyen terme (3 mois)
-------------------------------

- Implémenter authentification hybride JIRA : service account + connexion per-user.
- Ajouter une synchronisation automatique (scheduler + webhooks) pour JIRA.
- Mettre en place tests automatisés (unit + integration) et pipeline CI minimal.
- Ajouter UI : pages de consultation, visualisation du knowledge graph, et page d'admin pour connexions JIRA.

Objectifs long terme (6-12 mois)
-------------------------------

- Scalabilité : multi-tenant, file d'ingestion, monitoring et alerting (Prometheus + Grafana).
- Améliorer pertinence RAG : ranking multi-signaux (embedding score + graph proximity + recency).
- Gouvernance : gestion des accès, chiffrement des credentials, historique d'audit.
- Déploiement cloud (k8s) et setup CI/CD pour backend et frontend.

Risques
-------

- Gestion des identifiants JIRA (sécurité) — mitigé par chiffrement et service account.
- Coût et latence des appels LLM — mitigé par caching et bypasss déterministes pour requêtes listes/filtrées.
- Modèle de données hétérogène entre Qdrant et Neo4j — mitigé par contrats et adaptateurs.

Mesures de succès
-----------------

- Indexation initiale complète des tickets JIRA d'un projet pilote.
- Réponse correcte à requêtes communes (ex: "les 5 derniers jira") sans LLM.
- Pipeline de synchronisation fonctionnel et tests automatisés passant en CI.
