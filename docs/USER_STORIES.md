Genergy IA — User Stories
==========================

How to read these stories
-------------------------

- Format: As a [role], I want [goal] so that [benefit].
- Acceptance criteria: list of conditions that must be true.
- Story points: rough complexity estimate (1-13 Fibonacci).

Epic: Core Indexing & Retrieval
--------------------------------

US-001 — Ingest JIRA issues
- Role: Developer
- Story: As a content indexer, I want the system to fetch and index JIRA issues so that the knowledge base contains the latest tickets.
- Acceptance criteria:
  - The system can fetch issues for a given project key.
  - Each issue is stored in Qdrant with payload fields: `type`, `key`, `summary`, `status`, `priority`, `created`, `updated`.
  - Neo4j nodes are created for issues with metadata serialized.
- Story points: 5

US-002 — Add relationships in Neo4j
- Role: Data Engineer
- Story: As a data engineer, I want to create relationships between issues and code files so that correlations can be found.
- Acceptance criteria:
  - A `LINKS_TO` relationship can be created between a `JiraTicket` node and `CodeFile` node.
  - Queries can retrieve correlated nodes within 2 hops.
- Story points: 3

Epic: RAG Chatbot
------------------

US-010 — Deterministic list handler (JIRA)
- Role: End user
- Story: As a user, I want to ask "les N derniers JIRA" and get a deterministic, fast list without using the LLM.
- Acceptance criteria:
  - When the query matches the list pattern, the chatbot returns top-N issues sorted by `created`.
  - Response includes `key`, `summary`, `created`, `status`, `priority`.
- Story points: 2

US-011 — RAG answer with sources
- Role: End user
- Story: As a user, I want to ask technical questions and receive an answer with cited sources from Qdrant and Neo4j correlations.
- Acceptance criteria:
  - The chatbot runs a vector search and expands context with graph nodes.
  - The reply contains an answer and a list of sources (links or IDs).
- Story points: 8

Epic: Authentication & Security
------------------------------

US-020 — Connect JIRA (per-user)
- Role: User
- Story: As a user, I want to connect my JIRA account so that the system can access my project tickets when permitted.
- Acceptance criteria:
  - OAuth or token-based connect endpoint exists.
  - Secrets are stored encrypted and per-user.
  - Admins can revoke tokens.
- Story points: 5

More stories can be broken down from epics above.
