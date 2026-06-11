# FORENSIC AUDIT — AI Support Agent N3 Platform
## Complete Integration Analysis

---

## PHASE 1 — EXECUTION FLOW (ACTUAL RUNTIME)

```
User Question (POST /api/v1/chatbot/chat)
    │
    ▼
ChatbotService.process_message()
    │
    ├─[1] NLP Enrichment: ticket_enricher.enrich() → structured_ticket
    ├─[2] Phase detection / Loop escalation
    ├─[3] Query reformulation (_resolve_query)
    │
    ▼
IntelligenceOrchestrator.process()
    │
    ├─ app_context_resolver → mode = FR_WEAK (for BRASIL)
    ├─ FrWeakPipeline.search() → Qdrant vector search
    │     └─ Returns: context_blocks[], trust_score, mode
    │
    ▼ (back in chatbot_service.py)
    │
    ├─[4] IncidentContextGuard.filter_context_blocks()
    ├─[5] Historical cases injection (keyword match, threshold ≥ 2.0)
    ├─[6] Intent short-circuits:
    │      ├─ off_topic → LLM (generic)
    │      ├─ ML analysis → dedicated handler
    │      ├─ ND log search → SSH grep
    │      ├─ Equipment log → SSH grep
    │      ├─ Jira intent → Jira handler
    │      ├─ Tech inference → code intelligence
    │      └─ Write ticket → summary handler
    │
    ├─[7] Trust gate (diagnostic_reasoner.check_trust_gate, threshold=40)
    ├─[8] Diagnostic Engine N3 (log patterns + procedures)
    │
    ├─[9] LIVE DIAGNOSTICS (SSH pipeline):
    │      ├─ intent_from_message() → _live_intent, _live_entity
    │      ├─ ForensicIntentResolver (regex + semantic_router)
    │      │
    │      ├── IF forensic_intent: forensic handler (logs/timeline/evidence)
    │      │
    │      ├── ELSE: _live_orch.run(intent, entity)
    │      │     ├─ DiagnosticPlanner.plan()
    │      │     ├─ SSH→psql DB queries (BDD server)
    │      │     ├─ SSH→grep log searches (WA server)
    │      │     ├─ SSH commands (if enabled)
    │      │     ├─ EvidenceNormalizer
    │      │     ├─ ResolutionEngine.resolve()
    │      │     └─ Returns: DiagnosticBundle
    │      │
    │      ├── N3 Reasoning Layer:
    │      │     ├─ BusinessRuleEngine.evaluate()
    │      │     ├─ StateMachine.analyze_equipment()
    │      │     ├─ SyncAnomalyDetector.analyze()
    │      │     └─ CausalRCA.analyze()
    │      │
    │      ├── IF confidence ≥ 0.90: DETERMINISTIC RESPONSE (LLM SKIPPED)
    │      └── ELSE: inject live evidence into system_prompt → LLM
    │
    ├─[10] MultiSourceCorrelator.correlate() → inject into system_prompt
    │
    ├─[11] LLM call (Groq) OR deterministic response
    │
    ├─[12] POST-PROCESSING:
    │      ├─ Strip thinking sections
    │      ├─ Strip invented IDs (BRASIL-XXX, FR-XXXX)
    │      ├─ Banned phrase removal
    │      ├─ Action sanitization
    │      ├─ response_quality.full_quality_check()
    │      ├─ _protect_unindexed_sql_identifiers()
    │      ├─ truth_enforcement.enforce()
    │      ├─ Provenance footer (only if live evidence exists)
    │      ├─ Entity name protection
    │      └─ _ensure_gold_sections() (via ChatResponse validator)
    │
    ▼
ChatResponse (message, sources, trust_score, trust_label)
```

---

## PHASE 2 — DEAD COMPONENT DETECTION

| Component | Purpose | Current State | Impact | Fix |
|-----------|---------|---------------|--------|-----|
| **`correlation_engine.py`** (Layer 5, 755 lines) | Multi-source hypothesis ranking with SFD/FR/incident/log evidence | **NEVER CALLED** from chatbot_service.py. Only imported by `n3_chatbot_orchestrator.py` which itself is dead code. | **CRITICAL** — The main correlation engine that ranks hypotheses by source weight is completely bypassed. Responses lack evidence-ranked root causes. | Wire into chatbot_service.py after live diagnostics, before LLM call. |
| **`validation_layer.py`** (Layer 6, 544 lines) | 3-stage anti-hallucination (entity validity, business validity, evidence grounding) | **NEVER CALLED** from chatbot_service.py. Only imported by dead `n3_chatbot_orchestrator.py`. | **CRITICAL** — Entity validity and business rule compliance are not enforced on final responses. | Call after LLM response, before sending to user. |
| **`n3_chatbot_orchestrator.py`** (570 lines) | Full 8-layer pipeline (SFD→Knowledge→State→Intent→Correlation→Validation→Response→Learning) | **DEAD CODE** — never imported by any runtime module. Exists as a parallel implementation. | **CRITICAL** — The proper N3 layered pipeline exists but is unreachable. chatbot_service.py reimplements ~40% of it ad-hoc. | Either: (a) Replace chatbot_service main flow with n3_chatbot_orchestrator, or (b) Wire missing layers into chatbot_service. |
| **`learning_loop.py`** (Layer 8, 940 lines) | Post-resolution pattern storage, bug detection | **NEVER CALLED** from chatbot_service.py | MEDIUM — No pattern learning occurs after successful resolutions. | Call `learning_loop.record_resolution()` when user confirms fix. |
| **`response_generator.py`** (Layer 7) | Structured N3 response builder with validated content | **NEVER CALLED** from chatbot_service.py | HIGH — Responses are built ad-hoc or by raw LLM output instead of structured builder. | Integrate as response formatter. |
| **`temporal_reasoning.py`** | Temporal event correlation | **NEVER CALLED** anywhere | MEDIUM — Timeline generation doesn't use temporal reasoning. | Integrate into forensic_timeline handler. |
| **`incident_graph.py`** | Causal graph-based incident reasoning | Only imported by `correlation_engine.py` (dead) and `n3_chatbot_orchestrator.py` (dead) | HIGH — Causal chains never reach the response. | Wire through correlation_engine activation. |
| **TrustEngine** (`trust/trust_engine.py`) | Score confidence per source type | Called by `FrWeakPipeline` for scoring KB results. **NOT called** for final response confidence. `trust_score` in response is from pipeline only. | MEDIUM — Live evidence, correlation, RCA results don't contribute to final trust score. | Compute composite trust from all evidence sources. |
| **`sfd_reasoning.py`** | SFD constraint evaluation | Only imported by `validation_layer.py` (dead) | HIGH — SFD constraints exist but never block invalid operations. | Activate via validation_layer. |
| **`multi_source_correlator.py`** | Lightweight correlation | **CALLED** (line 1973) — injects into system_prompt | OK — but receives empty `jira_tickets` and `log_entries` (always `[]` from orch_result). | Pass actual Jira/log data. |

---

## PHASE 3 — EVIDENCE FLOW AUDIT

| Source | Can Collect? | Normalized? | Correlated? | Reaches Truth Engine? | Reaches Response? | Discarded? |
|--------|:---:|:---:|:---:|:---:|:---:|:---:|
| **Live DB** (SSH→psql) | ✅ via DiagnosticBundle | ✅ EvidenceNormalizer | ⚠️ Only via ResolutionEngine | ❌ TrustEngine not called on live data | ✅ Injected in system_prompt or deterministic response | ❌ |
| **Live Logs** (SSH→grep) | ✅ via LogService | ✅ LogNormalizer + LogParser | ✅ log_correlation_engine | ❌ | ✅ (deterministic path) or ⚠️ (LLM path: truncated) | Sometimes truncated |
| **Code Intelligence** | ✅ brasil_extractor | N/A | ❌ Not correlated with other sources | ❌ | ✅ In deterministic response only | Lost in LLM path (not in prompt) |
| **FR Documents** | ✅ via Qdrant (FrWeakPipeline) | Partial (vector embeddings) | ❌ **correlation_engine is dead** | ❌ | ✅ As context_text to LLM | N/A |
| **Historical Incidents** | ✅ historical_cases_retriever | Partial (keyword match) | ❌ | ❌ | ✅ As context block | ❌ |
| **Jira** | ✅ (handler exists) | ❌ | ❌ | ❌ | ⚠️ Only when Jira intent detected | **YES** — `orch_result['jira_tickets']` is always `[]` |
| **SFD Constraints** | ✅ sfd_parser exists | N/A | ❌ (correlation_engine dead) | ❌ | ❌ NEVER REACHES RESPONSE | **YES** — completely disconnected |
| **Workflow Intelligence** | ✅ 603 lines implemented | N/A | ❌ | ❌ | ⚠️ Called only in forensic_followup handler | Mostly dead |

```
EVIDENCE FLOW DIAGRAM:

User Question
    │
    ▼
┌─────────────────────────┐
│   Qdrant/RAG Retrieval  │──► context_blocks ──► LLM prompt (or _ensure_gold_sections)
│   (FrWeakPipeline)      │
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│   Live Diagnostics      │──► DiagnosticBundle
│   (SSH→DB, SSH→Logs)    │         │
└─────────────────────────┘         ├──► N3 Reasoning (BRE/FSM/Sync/RCA)
                                    │         └──► Prepended to live_blocks
                                    │
                                    ├──► ResolutionEngine
                                    │         └──► resolution_blocks
                                    │
                                    ├──► LogParser + LogCorrelation
                                    │         └──► reasoning_trace (internal only)
                                    │
                                    └──► IF conf≥0.90: DETERMINISTIC
                                         ELSE: injected into system_prompt

┌─────────────────────────┐
│   Correlation Engine    │   ◄── DEAD — NEVER CALLED
│   (Layer 5, 755 lines)  │
└─────────────────────────┘

┌─────────────────────────┐
│   Validation Layer      │   ◄── DEAD — NEVER CALLED
│   (Layer 6, 544 lines)  │
└─────────────────────────┘

┌─────────────────────────┐
│   SFD Reasoning         │   ◄── Only reachable through dead validation_layer
└─────────────────────────┘

┌─────────────────────────┐
│   Incident Graph        │   ◄── Only reachable through dead correlation_engine
└─────────────────────────┘

┌─────────────────────────┐
│   Learning Loop         │   ◄── DEAD — Never records resolutions
└─────────────────────────┘
```

---

## PHASE 4 — CORRELATION ENGINE AUDIT

**File**: `backend/app/services/chatbot/correlation_engine.py` (755 lines)

- **Is it executed?** ❌ NO — never imported by `chatbot_service.py`
- **How often?** Never
- **What inputs could reach it?** ConversationState, knowledge blocks, log patterns, SFD constraints, diagnostic rules
- **What outputs would it produce?** `CorrelationResult` with ranked hypotheses, SFD violations, causal graph reasoning
- **Are outputs consumed?** N/A (dead)
- **Where information is lost:** The system uses `multi_source_correlator.py` (a lightweight substitute, line 1973) but passes it **empty** Jira/log data because `orch_result` never populates those fields.

**The actual correlation engine (Layer 5) is the most critical dead component.**

It would provide:
- Source-weighted hypothesis ranking (SFD > FR > Incident > Learned > Log)
- SFD constraint violation detection
- Causal graph traversal via `incident_graph`
- Evidence chain building

Instead, the LLM receives raw context blocks without ranking or cross-validation.

---

## PHASE 5 — TRUTH ENGINE AUDIT

### `trust/trust_engine.py` (scoring)
- **Called by:** `FrWeakPipeline` to score KB results
- **Does it influence final response?** Only `trust_score` field on ChatResponse
- **Does it block hallucinations?** ❌ NO — it's a scorer, not a blocker

### `truth_enforcement.py` (blocking)
- **Called:** ✅ YES (line ~2135 in chatbot_service.py)
- **What it does:** Validates SQL tables, Java methods, log files, FR refs against indexes
- **Does it block hallucinations?** ✅ Replaces unvalidated claims with safe text
- **Bypasses found:**
  1. **Deterministic responses** use `truth_engine` (strict) — ✅ good
  2. **LLM responses** use `truth_engine_lenient` — ⚠️ only blocks mutations/shells
  3. **`_ensure_gold_sections()` appends text AFTER truth enforcement** — BYPASS: appended sections are NOT validated
  4. **Early return paths** (off_topic, escalation_loop, jira_intent, nd_log, equipment_log, write_ticket, classify_ticket, ml_analysis, summarize) — ALL bypass truth enforcement entirely

### Bypasses (responses generated without Truth Engine):
- Line 478: `off_topic` → direct LLM, no truth check
- Line 490: `escalation_loop` → static text, no check needed
- Line 516: `summarize` → history-based, bypasses
- Lines 690-715: `jira_intent`, `tech_inference`, `write_ticket` → dedicated handlers bypass
- Line 635: `nd_log`, `equipment_log` → SSH-direct results bypass

---

## PHASE 6 — LIVE DIAGNOSTICS AUDIT

### What is actually queried:
- **DB (BDD server):** SQL via SSH→psql using `ALLOWED_QUERIES` registry (whitelisted queries by intent)
- **Logs (WA server):** `grep` via SSH for entity name in log files
- **SSH commands:** Process checks (`ps`, `java_process`)

### What entities are searched:
- Entity extracted from user message via regex (DSLAM names, ND numbers)
- Equipment ID resolved from DB query `get_equipment_id`

### What results are returned:
- `DiagnosticBundle` containing: db_evidence (dict), log_evidence (list), ssh_evidence (list)
- Plus reasoning_trace with resolution_blocks, correlation_hypotheses, forensic_summary

### Why results sometimes don't appear in answers:
1. **SSH connection fails** (WinError 10054) → bundle has zero evidence → R7 fallback (structured "no data" message)
2. **Confidence < 0.90** → evidence goes into system_prompt but LLM may ignore it
3. **Truncation**: `sanitize_for_llm(context_text, max_chars=3000)` cuts evidence
4. **ForensicMemory not populated on first turn** → follow-up questions have no bundle to reuse

### Exact execution chain (happy path):
```
_live_orch.run(intent, entity)
  → DiagnosticPlanner.plan() → list of DB queries
  → SshPsqlDbService.execute(query) → DbEvidence rows
  → LogService.grep_equipment(entity) → LogEvidence lines
  → EvidenceNormalizer.normalize_all()
  → ResolutionEngine.resolve() → resolution candidates
  → to_context_blocks() → resolution_blocks
```

---

## PHASE 7 — ROOT CAUSE ANALYSIS AUDIT

### `causal_rca.py` (CausalRCA Engine)
- **Called:** ✅ YES (line 1254) — but ONLY when `_live_orch.run()` produces live_blocks
- **Does RCA consume evidence?** ✅ active_rule_ids from BRE, sync_anomaly_types, detected_exceptions, log_signals, db_status
- **Does RCA consume incidents?** ❌ NO — no incident history passed
- **Does RCA consume workflow data?** ❌ NO
- **Does RCA consume code analysis?** ❌ NO
- **Does RCA consume live diagnostics?** ✅ Partial (db_status, log_signals)

### Verdict:
RCA runs on partial data. It receives BRE results and sync anomalies but NOT:
- Historical similar incidents
- FR procedure matches
- Code execution graph constraints
- Workflow state violations

It produces hypotheses that are prepended to `_live_blocks` → injected into LLM prompt or deterministic response. **However, when SSH fails (common case), RCA never runs.**

---

## PHASE 8 — TIMELINE ENGINE AUDIT

### `live_diagnostics/timeline/timeline_builder.py`
- **Called:** ✅ In deterministic path (line ~1445) and forensic_timeline handler (line ~1110)

### Can timeline events be extracted from:
- **Logs:** ✅ If SSH connection works and entity is found in logs
- **Incidents:** ❌ No historical incident data passed to timeline builder
- **Workflow states:** ❌ Not integrated
- **Jira history:** ❌ Not integrated

### Why timelines are empty:
1. **SSH connection fails** → no log_evidence → no events to build timeline from
2. **Entity not found in logs** → grep returns empty
3. **Only live data used** — no historical incidents or Jira events contribute to timeline
4. **Forensic memory empty on first request** — user must first run a diagnostic, THEN ask for timeline

---

## PHASE 9 — INCIDENT MEMORY AUDIT

### `historical_cases_retriever.py`
- **Called:** ✅ (line ~580) — keyword-based retrieval from `historical_cases.json`
- **Similarity search:** Simple keyword matching with weighted scoring (not vector/semantic)
- **Ranking:** By score (frequency × keyword match), threshold ≥ 2.0
- **Are results discarded?** Sometimes — if score < 2.0

### `forensic_memory.py`
- **Called:** ✅ For storing/retrieving evidence across conversation turns
- **Works correctly** for multi-turn forensic sessions

### Missing:
- No **vector similarity search** on historical incidents
- No **Qdrant-based incident retrieval** (only keyword)
- `incident_graph.py` (causal patterns) is dead code

---

## PHASE 10 — CODE TO DATABASE TRACEABILITY

### Current state of `code_intelligence/`:
```
deleteDslam()
  → ManageDslamBusinessImpl.deleteDslam()
    → checkProductionInfoIsPresent()
    → [Missing: DAO layer mapping]
    → [Missing: SQL table mapping]

createVlan()
  → ManageCreationVlanBusinessImpl.creerVlan()
    → checkInputs()
    → [Missing: DAO layer mapping]

deleteVlan()
  → ManageVlanBusinessImpl.deleteVlan()
    → [Missing: DAO layer mapping]
```

### What exists:
- `brasil_extractor.py`: 3350 entries from cache (methods, conditions, exceptions)
- `execution_graph_extractor.py`: 3913 nodes, 19 operations

### What's missing:
- **Method → Table mapping** is NOT in the code intelligence index
- `_protect_unindexed_sql_identifiers()` marks ALL `t_*` table names as "❌ Table non trouvée" because `brasil_knowledge_base.is_real_table()` has no data
- The `brasil_schema_knowledge.py` has `REAL_SQL_TABLES` but it's not linked to method calls

---

## PHASE 11 — ANTI-HALLUCINATION AUDIT

| Location | What can be invented | Severity | Current Guard |
|----------|---------------------|----------|---------------|
| LLM response (general) | Procedures, RCA, table names | HIGH | `truth_enforcement` (lenient mode — only blocks mutations/shells) |
| LLM response (SQL) | Table names | HIGH | `_protect_unindexed_sql_identifiers()` — marks as ❌ |
| LLM response (IDs) | FR references, ticket IDs | MEDIUM | Regex strip of non-source IDs |
| Deterministic response | N/A (code-generated) | LOW | `truth_enforcement` (strict) |
| `_ensure_gold_sections()` / ChatResponse validator | Section text | MEDIUM | **NO GUARD** — appended after truth enforcement |
| Early return paths (off_topic, Jira, ND log, etc.) | Generic advice, procedures | HIGH | **NO GUARD** — bypass all post-processing |
| `_lookup_code_ref()` in ChatResponse | Code references | LOW | Keyword-matched from known index |
| FR content from Qdrant | Stale/wrong procedure | MEDIUM | Trust score threshold (40), but still passed to LLM |
| historical_cases_retriever | Wrong case match | LOW | Score threshold ≥ 2.0, SQL sanitization |

---

## PHASE 12 — FINAL REPORT

### 1. Architecture Map
```
┌───────────────────────────────────────────────────────────────┐
│                    chatbot_service.py (4300 lines)             │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ ACTIVE PIPELINE                                          │ │
│  │  NLP → Orchestrator → FrWeakPipeline → Trust Gate       │ │
│  │  → Live Diagnostics → N3 Reasoning → LLM/Deterministic  │ │
│  │  → Truth Enforcement → Quality Check → Response          │ │
│  └──────────────────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ DEAD PIPELINE (n3_chatbot_orchestrator.py)               │ │
│  │  SFD → Knowledge → State → Intent → Correlation         │ │
│  │  → Validation → Response Generator → Learning Loop       │ │
│  └──────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────┘
```

### 2. Evidence Flow Map
See Phase 3 diagram above.

### 3. Dead Components
- `correlation_engine.py` (Layer 5) — CRITICAL
- `validation_layer.py` (Layer 6) — CRITICAL  
- `n3_chatbot_orchestrator.py` — CRITICAL (entire proper pipeline)
- `response_generator.py` (Layer 7) — HIGH
- `learning_loop.py` (Layer 8) — MEDIUM
- `incident_graph.py` — HIGH
- `temporal_reasoning.py` — MEDIUM

### 4. Disconnected Components
- `sfd_reasoning.py` → only reachable via dead validation_layer
- `TrustEngine` → scores KB but not live evidence or final response
- `multi_source_correlator` → called but receives empty Jira/log data

### 5. Missing Integrations
- CorrelationEngine(L5) → chatbot_service main flow
- ValidationLayer(L6) → post-LLM validation
- LearningLoop(L8) → resolution confirmation
- incident_graph → correlation evidence
- Code Intelligence → Method-to-Table traceability
- Historical incidents → Timeline builder
- Jira data → Correlation engine input

### 6. Hallucination Risks
- **CRITICAL**: Early return paths bypass truth enforcement
- **HIGH**: LLM in lenient mode can invent procedures
- **HIGH**: `_ensure_gold_sections()` appends unvalidated text
- **MEDIUM**: FK/table references in LLM output not linked to real schema

### 7. Highest ROI Fixes (ordered)

| # | Fix | Effort | Impact |
|---|-----|--------|--------|
| 1 | **Wire correlation_engine.py into chatbot_service** — call `correlation_engine.correlate()` with KB blocks + live evidence → produces ranked hypotheses → inject into LLM prompt | 2h | Responses become evidence-ranked instead of flat KB dump |
| 2 | **Wire validation_layer.py post-LLM** — call `validation_layer.validate()` on response text before sending to user | 1h | Blocks entity hallucinations, enforces SFD compliance |
| 3 | **Pass real Jira/log data to MultiSourceCorrelator** — populate `orch_result['jira_tickets']` and `orch_result['log_entries']` | 1h | Cross-source correlation becomes effective |
| 4 | **Apply truth enforcement to ALL response paths** — wrap early returns through truth_enforcement | 2h | Eliminates bypass vectors |
| 5 | **Feed RCA with incident history + code analysis** — pass historical_cases and code_intelligence results to CausalRCA | 2h | RCA becomes truly evidence-driven |
| 6 | **Build Method→Table mapping** in code intelligence | 3h | Eliminates "❌ Table non trouvée" hallucination |
| 7 | **Activate learning_loop on resolution confirmation** | 1h | System improves over time |

### 8. Prioritized Implementation Plan

**Week 1 — Critical Integration (transforms behavior)**
1. Wire correlation_engine into chatbot_service (replaces flat KB dump with ranked hypotheses)
2. Wire validation_layer post-LLM (blocks hallucinated entities/procedures)
3. Truth enforcement on all code paths

**Week 2 — Evidence Enrichment**
4. Real data to MultiSourceCorrelator
5. Feed historical incidents + code analysis into RCA
6. Timeline builder receives incident + Jira events

**Week 3 — Learning & Traceability**
7. Learning loop activation
8. Method→Table code traceability
9. SFD constraint enforcement in responses

### 9. Target Architecture

```
User Question
    │
    ▼
[Intent Resolution] ← IntentResolver + SemanticRouter
    │
    ├──► [Knowledge Retrieval] ← FrWeakPipeline + HistoricalCases
    ├──► [Live Diagnostics] ← SSH→DB + SSH→Logs
    ├──► [Code Intelligence] ← brasil_extractor + execution_graph
    │
    ▼
[CORRELATION ENGINE] ← Fuses ALL evidence sources with source weights
    │                    SFD(1.5) > FR(1.3) > Incident(1.0) > Log(0.85)
    │
    ▼
[CAUSAL RCA] ← Receives correlated evidence, builds hypothesis chain
    │
    ▼
[VALIDATION LAYER] ← Entity + Business + Evidence grounding checks
    │
    ▼
[RESPONSE GENERATION] ← Structured N3 format with validated content
    │
    ▼
[TRUTH ENFORCEMENT] ← Final sweep: block any remaining fabrication
    │
    ▼
[LEARNING LOOP] ← Record resolution if confirmed
    │
    ▼
ChatResponse
```

### 10. Estimated Score Before/After

| Metric | Current | After Fixes |
|--------|---------|-------------|
| Evidence-grounded responses | ~40% (only when SSH works) | ~85% |
| Hallucination-free responses | ~70% (truth_enforcement helps) | ~95% |
| Cross-source correlation | ~5% (MSC has empty inputs) | ~70% |
| SFD constraint enforcement | 0% | ~80% |
| Historical incident reuse | ~20% (keyword only) | ~60% |
| Timeline generation (with SSH) | ~30% | ~70% |
| Learning from resolutions | 0% | ~50% (after activation) |

---

## ROOT CAUSE OF "DOCUMENTATION CHATBOT" BEHAVIOR

**The system has TWO complete architectures built in parallel:**

1. **`n3_chatbot_orchestrator.py`** — The correct 8-layer N3 pipeline (SFD→Knowledge→Correlation→Validation→Response→Learning). **NEVER CALLED.**

2. **`chatbot_service.py`** — A 4300-line monolith that reimplements ~40% of the pipeline ad-hoc but skips the critical layers (Correlation, Validation, Learning).

The result: evidence is collected (Live Diagnostics works) but is never **correlated**, **ranked**, or **validated** before reaching the user. The LLM receives flat context blocks without priority ordering, and its output is only lightly checked (lenient truth enforcement).

**The fix is NOT to build new components. It is to WIRE the existing dead components into the active pipeline.**
