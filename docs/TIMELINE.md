Genergy IA — Timeline & Sprints
================================

Résumé des travaux effectués
---------------------------

- Jan 2026 Week 1: Implemented GraphService improvements, fixed Neo4j metadata issues.
- Jan 2026 Week 2: Implemented Chatbot list handler; created test Jira tickets; started Qdrant & Neo4j on WSL; validated end-to-end local flow.

Proposed timeline (next 12 weeks)
---------------------------------

- Sprint 1 (Weeks 1-2): Jira Hybrid Auth
  - Tasks: Design auth model, implement endpoints to connect per-user, implement encrypted storage, add service-account fallback.
  - Deliverable: `auth` endpoints + docs.

- Sprint 2 (Weeks 3-4): Sync & Scheduler
  - Tasks: Implement Jira sync worker (initial + incremental), webhook receiver, reconciliation scripts.
  - Deliverable: Automated sync job and docs.

- Sprint 3 (Weeks 5-6): UI & Visualization
  - Tasks: Add admin page for connectors, add Knowledge Graph viewer, Chat page improvements.
  - Deliverable: Frontend pages + basic e2e flows.

- Sprint 4 (Weeks 7-8): Tests & CI/CD
  - Tasks: Add unit/integration tests, GitHub Actions pipeline, containerization improvements.
  - Deliverable: Passing CI and deployable images.

- Sprint 5 (Weeks 9-12): Production Hardening
  - Tasks: Monitoring, secrets management, scaling, performance tuning.
  - Deliverable: Production-ready deployment guide.

Notes
-----

- Each sprint is 2 weeks with a sprint planning + demo + retrospective.
- Buffer included for unknown blockers.
