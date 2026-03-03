Genergy IA — Sprint Backlog (Initial)
=====================================

Sprint 0 (Current) — Stabilize MVP (1 week)
------------------------------------------

- Goal: Fix metadata issues, enable list-handler, create test data, and verify Qdrant/Neo4j availability.
- Tasks:
  - Fix Neo4j metadata serialization (done).
  - Implement list handler in ChatbotService (done).
  - Create `create_test_jira.py` to seed Qdrant (done).
  - Start Qdrant & Neo4j on WSL/Podman and validate (done).

Sprint 1 (Weeks 1-2)
--------------------

- Goal: Implement Jira hybrid auth and secure token storage.
- Tasks:
  - Design auth model & API endpoints.
  - Implement encrypted storage for tokens.
  - Add admin endpoints for service account.
  - Add unit tests for auth flows.

Sprint 2 (Weeks 3-4)
--------------------

- Goal: Jira sync automation (initial + incremental)
- Tasks:
  - Implement sync worker and scheduler.
  - Implement webhook receiver for JIRA events.
  - Add reconciliation script.

Sprint 3 (Weeks 5-6)
--------------------

- Goal: Frontend integration and graph visualization
- Tasks:
  - Add admin UI for connectors.
  - Add Knowledge Graph viewer page.
  - Improve Chat UI to show sources and links.

Sprint 4 (Weeks 7-8)
--------------------

- Goal: Tests & CI/CD
- Tasks:
  - Add unit and integration tests.
  - Add GitHub Actions workflow to run tests and build images.

Notes
-----

- Prioritize security and auth before automating sync to avoid accidental data exposure.
- Each sprint includes planning, development, demo and retro.
