Genergy IA — Roadmap
=====================

Vision
------
Fournir une plateforme interne d'assistance technique capable de répondre précisément aux questions des équipes opérationnelles et d'ingénierie en s'appuyant sur une base de connaissances hybride (graph + vecteurs), actualisée automatiquement depuis sources (JIRA, code, docs, logs).

Epics (priorisés)
------------------

1. Core Indexing & Retrieval
   - Ingestion connectors (JIRA, Git, DB, logs)
   - Vector store (Qdrant) integration
   - Knowledge graph (Neo4j) modeling and relationships

2. RAG Chatbot and Deterministic Handlers
   - Chatbot service with RAG orchestration
   - Deterministic handlers for list/filters (reduce LLM use)

3. Authentication & Security
   - Jira hybrid auth (service account + per-user)
   - Secure credential storage & rotation

4. Sync & Automation
   - Webhooks and scheduled ingestion
   - Incremental updates and backfills

5. Observability & Ops
   - Healthchecks, metrics, alerting
   - CI/CD pipelines and containerization

6. UX and Visualization
   - Frontend pages: Chat, Knowledge Graph, Admin
   - Graph visualization and source links

Milestones
----------

- M1 (MVP): Core indexing + RAG chatbot + deterministic list handler — Done (local tests passed).
- M2: Hybrid Jira auth + secure storage + simple UI for connections — Next priority.
- M3: Sync automation + CI tests + deployable containers — After M2.
- M4: Observability + scaling + production deployment — Long term.
