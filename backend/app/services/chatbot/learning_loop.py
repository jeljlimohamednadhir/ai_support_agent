"""
Layer 8 — Learning Loop
========================
Post-conversation learning: pattern extraction from confirmed resolutions.

Rules:
  1. JIRA data is NEVER exposed in any user-facing response.
  2. JIRA is used ONLY as an internal signal to detect known bugs.
  3. Learning happens AFTER user confirms resolution OR after repeated failures.
  4. Learned patterns are stored in: data/learning/learned_patterns.json

Triggers:
  - confirm_resolution → store successful resolution pattern
  - deny_resolution (after 2+ attempts) → generate internal JIRA bug suggestion
  - session_end → compact conversation to a new incident pattern

Output files:
  data/learning/learned_patterns.json   — successful resolution patterns
  data/learning/bug_suggestions.json    — internal JIRA suggestions (NEVER user-facing)
  data/learning/unresolved_cases.json   — unresolved sessions for review
"""
from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

from app.services.chatbot.conversation_state import ConversationState

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────────────────────

_BASE = Path(__file__).parents[3]  # backend/
_LEARNING_DIR = _BASE / "data" / "learning"
_PATTERNS_FILE = _LEARNING_DIR / "learned_patterns.json"
_BUGS_FILE = _LEARNING_DIR / "bug_suggestions.json"
_UNRESOLVED_FILE = _LEARNING_DIR / "unresolved_cases.json"
_CORRECTIONS_FILE = _LEARNING_DIR / "corrections.json"
_HYP_STATS_FILE = _LEARNING_DIR / "hypothesis_stats.json"
_ENTITY_MEMORY_FILE = _LEARNING_DIR / "entity_memory.json"
_WEAK_PATTERNS_FILE = _LEARNING_DIR / "weak_patterns.json"


# ─────────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class LearnedPattern:
    """A successful resolution that becomes a reusable incident pattern."""
    id: str
    created_at: str
    entity_type: str
    entity_name: str
    problem_summary: str
    root_cause: str
    actions_taken: List[str]
    hypothesis_id: str
    turn_count: int
    confidence: float
    source_conversation_id: str


@dataclass
class BugSuggestion:
    """
    Internal suggestion for JIRA-level bug.
    NEVER shown to user. Used by N3 team internally.
    """
    id: str
    created_at: str
    entity_type: str
    problem_summary: str
    repeated_failures: int
    probable_module: str
    probable_bug: str
    fix_recommendation: str
    related_patterns: List[str]
    internal_only: bool = True   # hard guarantee: never in user response


@dataclass
class UnresolvedCase:
    """Session that ended without resolution — for review."""
    id: str
    created_at: str
    entity_name: str
    problem_summary: str
    attempts: int
    last_hypothesis: str
    conversation_summary: str


@dataclass
class HumanCorrection:
    """
    A correction submitted by an N3 operator via the /corrections API.
    Drives reinforcement or suppression of graph nodes + hypotheses.
    """
    id: str
    created_at: str
    query: str                   # original user query
    original_response: str       # chatbot's response that was wrong
    corrected_response: str      # operator's correct response
    entity_name: str
    entity_type: str
    hypothesis_id: str           # which hypothesis was active
    correction_type: str         # "reinforce" | "suppress"
    corrected_root_cause: str = ""
    corrected_actions: List[str] = field(default_factory=list)
    operator_id: str = "n3_operator"
    applied: bool = False        # True after reinforce/suppress was called


@dataclass
class HypothesisStats:
    """
    Per-hypothesis performance counters.
    Persisted in data/learning/hypothesis_stats.json.
    """
    hypothesis_id: str
    visit_count: int = 0
    success_count: int = 0       # confirmed resolutions
    failure_count: int = 0       # denied resolutions
    last_seen: str = ""
    suppression_factor: float = 1.0  # multiplied into correlation score

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.5  # neutral prior
        return self.success_count / total

    @property
    def confidence_score(self) -> float:
        """
        Composite confidence:
          f(success_rate, log(1 + visit_count), suppression_factor)
        """
        sr = self.success_rate
        visit_boost = math.log(1 + self.visit_count) * 0.08
        base = sr * 0.7 + visit_boost
        return round(min(1.0, max(0.0, base * self.suppression_factor)), 4)


# ─────────────────────────────────────────────────────────────────────────────
# Module classification for BRASIL
# ─────────────────────────────────────────────────────────────────────────────

_MODULE_MAP: Dict[str, str] = {
    "HYP-001": "IHM BRASIL / t_equipments",
    "HYP-002": "CalculerToc / t_ports",
    "HYP-003": "t_cards / card_prod_status",
    "HYP-004": "t_mrt_access_dslams / MRT provisioning",
    "HYP-005": "UMI-EPC / making file handler",
    "HYP-006": "CEV order validation",
    "HYP-007": "PostgreSQL transaction manager",
    "HYP-008": "Counter recalculation (FR 136b/136c)",
    "HYP-009": "Concurrent access manager",
    "HYP-010": "Equipment deletion orchestrator",
    "HYP-011": "Node synchronization (FR 148/151)",
    "HYP-012": "TSF provisioning engine",
}

_BUG_MAP: Dict[str, str] = {
    "HYP-001": "eqpt_prod_status not updated after maintenance window close",
    "HYP-002": "port_attribuable counter not decremented on service deactivation",
    "HYP-003": "card_prod_status stuck in 'F' after card swap",
    "HYP-004": "MRT cross-reference not synchronized after DSLAM migration",
    "HYP-005": "NIFolderID missing from UMI-EPC message payload",
    "HYP-006": "NumeroCCL validation bypassed for CEV offers",
    "HYP-007": "Deadlock on concurrent making_file INSERT — retry not triggered",
    "HYP-008": "VP/VC/VLAN counters diverge after partial rollback",
    "HYP-009": "IN_PROGRESS state not released after connector timeout",
    "HYP-010": "FK constraint violation on t_cards not surfaced in error message",
    "HYP-011": "Node not imported from Référentiel Sites on new DSLAM creation",
    "HYP-012": "TSF resources not provisioned during DSLAM onboarding",
}

_FIX_MAP: Dict[str, str] = {
    "HYP-001": "Add automated eqpt_prod_status reset job after maintenance window expiry",
    "HYP-002": "Fix counter decrement trigger on t_ports on service deactivation event",
    "HYP-003": "Add health check job to detect cards stuck in 'F' beyond SLA",
    "HYP-004": "Add MRT sync validation step in DSLAM migration procedure",
    "HYP-005": "Add NIFolderID mandatory field validation in UMI-EPC schema",
    "HYP-006": "Add NumeroCCL presence check in CEV order creation handler",
    "HYP-007": "Implement exponential backoff + alerting after 3 deadlock retries",
    "HYP-008": "Add counter consistency check job (FR 136b) to nightly batch",
    "HYP-009": "Add IN_PROGRESS auto-release after configurable timeout",
    "HYP-010": "Surface full FK constraint tree in BRASIL error response",
    "HYP-011": "Add Référentiel Sites import step to DSLAM onboarding wizard",
    "HYP-012": "Add TSF provisioning verification to DSLAM activation checklist",
}


# ─────────────────────────────────────────────────────────────────────────────
# Learning Loop
# ─────────────────────────────────────────────────────────────────────────────

class LearningLoop:
    """
    Post-resolution learning engine.
    Writes to data/learning/ — never exposes data to users.
    """

    def __init__(self):
        self._ensure_dirs()

    # ── public API ────────────────────────────────────────────────────────────

    def on_resolution_confirmed(
        self,
        state: ConversationState,
        hypothesis_id: str = "",
        hypothesis_label: str = "",
        actions_taken: Optional[List[str]] = None,
        confidence: float = 0.0,
    ) -> Optional[LearnedPattern]:
        """
        Called when user confirms the problem is resolved.
        Stores a new learned pattern.
        """
        primary = state.get_primary_equipment()
        entity_name = primary.name if primary else "unknown"
        entity_type = primary.type.value if primary else "UNKNOWN"

        summary_data = state.summary()
        problem_summary = summary_data.get("last_intent", "") or f"{len(state.history)} turns"

        pattern = LearnedPattern(
            id=f"LP-{datetime.now(tz=timezone.utc).strftime('%Y%m%d%H%M%S')}-{state.conversation_id[:8]}",
            created_at=datetime.now(tz=timezone.utc).isoformat(),
            entity_type=entity_type,
            entity_name=entity_name,
            problem_summary=problem_summary,
            root_cause=hypothesis_label,
            actions_taken=actions_taken or [],
            hypothesis_id=hypothesis_id,
            turn_count=len(state.history),
            confidence=confidence,
            source_conversation_id=state.conversation_id,
        )

        self._append_to_file(_PATTERNS_FILE, "patterns", asdict(pattern))
        logger.info(f"Learning Loop: saved pattern {pattern.id} for {entity_name}")

        # Update hypothesis performance stats
        if hypothesis_id:
            self.update_hypothesis_stats(hypothesis_id, outcome="success")

        # Update entity memory
        self.update_entity_memory(
            entity_name=entity_name,
            entity_type=entity_type,
            cause=hypothesis_label or "unknown",
            pattern_id=pattern.id,
            outcome="success",
        )
        return pattern

    def on_resolution_denied(
        self,
        state: ConversationState,
        hypothesis_id: str = "",
        hypothesis_label: str = "",
        denial_count: int = 1,
    ) -> Optional[BugSuggestion]:
        """
        Called when user says the problem is NOT resolved.
        After 2+ denials → generate internal bug suggestion.
        """
        primary = state.get_primary_equipment()
        entity_type = primary.type.value if primary else "UNKNOWN"

        # Store unresolved case
        summary_data = state.summary()
        problem_summary = summary_data.get("last_intent", "") or f"{len(state.history)} turns"
        unresolved = UnresolvedCase(
            id=f"UC-{datetime.now(tz=timezone.utc).strftime('%Y%m%d%H%M%S')}",
            created_at=datetime.now(tz=timezone.utc).isoformat(),
            entity_name=primary.name if primary else "unknown",
            problem_summary=problem_summary,
            attempts=len(state.history),
            last_hypothesis=hypothesis_label,
            conversation_summary=problem_summary,
        )
        self._append_to_file(_UNRESOLVED_FILE, "unresolved_cases", asdict(unresolved))

        # Update hypothesis failure stats
        if hypothesis_id:
            self.update_hypothesis_stats(hypothesis_id, outcome="failure")

        # Update entity memory
        if primary:
            self.update_entity_memory(
                entity_name=primary.name if primary else "unknown",
                entity_type=entity_type,
                cause=hypothesis_label or "unknown",
                pattern_id=f"UC-{denial_count}",
                outcome="failure",
            )

        # Only generate bug suggestion after repeated failures
        if denial_count < 2:
            return None

        bug = BugSuggestion(
            id=f"BUG-SUGGESTION-{datetime.now(tz=timezone.utc).strftime('%Y%m%d%H%M%S')}",
            created_at=datetime.now(tz=timezone.utc).isoformat(),
            entity_type=entity_type,
            problem_summary=state.summary() or "N/A",
            repeated_failures=denial_count,
            probable_module=_MODULE_MAP.get(hypothesis_id, "Module inconnu"),
            probable_bug=_BUG_MAP.get(hypothesis_id, "Bug non catalogué"),
            fix_recommendation=_FIX_MAP.get(hypothesis_id, "Investigation N3 requise"),
            related_patterns=[hypothesis_id] if hypothesis_id else [],
            internal_only=True,
        )

        self._append_to_file(_BUGS_FILE, "bug_suggestions", asdict(bug))
        logger.info(
            f"Learning Loop: generated BUG SUGGESTION {bug.id} "
            f"(INTERNAL ONLY — never shown to user)"
        )
        return bug  # returned to orchestrator for INTERNAL logging only

    def on_session_end(self, state: ConversationState):
        """
        Called at end of session regardless of resolution.
        Compacts the conversation if unresolved.
        """
        if state.resolution_status is None:
            summary_data = state.summary()
            problem_summary = summary_data.get("last_intent", "") or "Session ended without resolution"
            unresolved = UnresolvedCase(
                id=f"UC-END-{datetime.now(tz=timezone.utc).strftime('%Y%m%d%H%M%S')}",
                created_at=datetime.now(tz=timezone.utc).isoformat(),
                entity_name=(state.get_primary_equipment().name
                             if state.get_primary_equipment() else "unknown"),
                problem_summary=problem_summary,
                attempts=len(state.history),
                last_hypothesis="",
                conversation_summary=problem_summary,
            )
            self._append_to_file(_UNRESOLVED_FILE, "unresolved_cases", asdict(unresolved))

    def get_pattern_for_entity(self, entity_name: str) -> Optional[Dict]:
        """
        Retrieve the best-scored pattern for a given entity.
        Returns the highest computed_score pattern (anti-bias scored).
        Backward-compatible — still returns a single dict or None.
        """
        results = self.get_patterns_for_entity(entity_name, limit=1)
        return results[0] if results else None

    def apply_correction(
        self,
        query: str,
        original_response: str,
        corrected_response: str,
        entity_name: str,
        entity_type: str,
        hypothesis_id: str,
        correction_type: str,
        corrected_root_cause: str = "",
        corrected_actions: Optional[List[str]] = None,
        operator_id: str = "n3_operator",
    ) -> HumanCorrection:
        """
        Store a human correction and immediately apply reinforcement or
        suppression to the incident graph.

        correction_type:
          "reinforce" — hypothesis was correct, boost its graph weight
          "suppress"  — hypothesis was wrong, reduce its graph weight
        """
        from app.services.chatbot.incident_graph import incident_graph  # deferred

        correction = HumanCorrection(
            id=f"CORR-{datetime.now(tz=timezone.utc).strftime('%Y%m%d%H%M%S')}-{hypothesis_id}",
            created_at=datetime.now(tz=timezone.utc).isoformat(),
            query=query,
            original_response=original_response,
            corrected_response=corrected_response,
            entity_name=entity_name,
            entity_type=entity_type,
            hypothesis_id=hypothesis_id,
            correction_type=correction_type,
            corrected_root_cause=corrected_root_cause,
            corrected_actions=corrected_actions or [],
            operator_id=operator_id,
            applied=False,
        )

        # Apply graph reinforcement / suppression
        if correction_type == "reinforce":
            incident_graph.reinforce(hypothesis_id, delta=0.20)
        elif correction_type == "suppress":
            incident_graph.suppress(hypothesis_id, delta=0.20)

        correction.applied = True

        # If a corrected resolution is provided, also store it as a learned pattern
        if corrected_root_cause or corrected_actions:
            from app.services.chatbot.conversation_state import ConversationState
            pattern = LearnedPattern(
                id=f"LP-CORR-{datetime.now(tz=timezone.utc).strftime('%Y%m%d%H%M%S')}",
                created_at=datetime.now(tz=timezone.utc).isoformat(),
                entity_type=entity_type,
                entity_name=entity_name,
                problem_summary=query[:200],
                root_cause=corrected_root_cause or "(operator correction)",
                actions_taken=corrected_actions or [],
                hypothesis_id=hypothesis_id,
                turn_count=0,
                confidence=0.95,
                source_conversation_id=correction.id,
            )
            self._append_to_file(_PATTERNS_FILE, "patterns", asdict(pattern))

        self._append_to_file(_CORRECTIONS_FILE, "corrections", asdict(correction))
        logger.info(
            f"Learning Loop: applied {correction_type} correction {correction.id} "
            f"for hypothesis {hypothesis_id} on entity {entity_name}"
        )
        return correction

    def get_suppressed_hypotheses(self, threshold: int = 3) -> Dict[str, float]:
        """
        Return hypotheses that appear >= threshold times in bug_suggestions.json.
        Maps hypothesis_id -> suppression_delta (negative value to apply in correlation).
        Called by correlation_engine to reduce base score of faulty hypotheses.
        """
        if not _BUGS_FILE.exists():
            return {}
        try:
            data = json.loads(_BUGS_FILE.read_text(encoding="utf-8"))
            bugs = data.get("bug_suggestions", [])
        except Exception:
            return {}

        count: Dict[str, int] = {}
        for bug in bugs:
            hyp_id = bug.get("related_patterns", [None])[0]
            if hyp_id:
                count[hyp_id] = count.get(hyp_id, 0) + 1

        # Also count suppress corrections
        if _CORRECTIONS_FILE.exists():
            try:
                cdata = json.loads(_CORRECTIONS_FILE.read_text(encoding="utf-8"))
                for c in cdata.get("corrections", []):
                    if c.get("correction_type") == "suppress":
                        hyp_id = c.get("hypothesis_id", "")
                        if hyp_id:
                            count[hyp_id] = count.get(hyp_id, 0) + 1
            except Exception:
                pass

        suppressed = {}
        for hyp_id, n in count.items():
            if n >= threshold:
                # Each count beyond threshold adds 10% suppression, max 50%
                suppressed[hyp_id] = -min(0.50, (n - threshold + 1) * 0.10)
        return suppressed

    def get_correction_stats(self) -> Dict[str, Any]:
        """Return correction statistics for the internal dashboard."""
        stats: Dict[str, Any] = {"total": 0, "reinforce": 0, "suppress": 0}
        if not _CORRECTIONS_FILE.exists():
            return stats
        try:
            data = json.loads(_CORRECTIONS_FILE.read_text(encoding="utf-8"))
            corrections = data.get("corrections", [])
            stats["total"] = len(corrections)
            stats["reinforce"] = sum(1 for c in corrections if c.get("correction_type") == "reinforce")
            stats["suppress"] = sum(1 for c in corrections if c.get("correction_type") == "suppress")
        except Exception:
            pass
        return stats

    def get_statistics(self) -> Dict[str, Any]:
        """Return learning loop statistics (for internal dashboard use only)."""
        stats: Dict[str, Any] = {
            "patterns": 0,
            "bug_suggestions": 0,
            "unresolved_cases": 0,
        }
        for key, fpath in [
            ("patterns", _PATTERNS_FILE),
            ("bug_suggestions", _BUGS_FILE),
            ("unresolved_cases", _UNRESOLVED_FILE),
        ]:
            if fpath.exists():
                try:
                    data = json.loads(fpath.read_text(encoding="utf-8"))
                    stats[key] = len(data.get(key, []))
                except Exception:
                    pass
        return stats

    # ── Hypothesis stats ──────────────────────────────────────────────────

    def update_hypothesis_stats(
        self,
        hypothesis_id: str,
        outcome: str,             # "success" | "failure"
        suppression_delta: float = 0.0,
    ) -> HypothesisStats:
        """
        Increment visit/success/failure counters for a hypothesis.
        Called on resolution confirm (success) and denial (failure).
        """
        stats = self._load_hyp_stats()
        if hypothesis_id not in stats:
            stats[hypothesis_id] = HypothesisStats(hypothesis_id=hypothesis_id)
        h = stats[hypothesis_id]
        h.visit_count += 1
        h.last_seen = datetime.now(tz=timezone.utc).isoformat()
        if outcome == "success":
            h.success_count += 1
        elif outcome == "failure":
            h.failure_count += 1
        # Apply suppression_factor multiplicatively (only decreases)
        if suppression_delta < 0:
            h.suppression_factor = max(0.1, h.suppression_factor * (1 + suppression_delta))
        self._save_hyp_stats(stats)
        return h

    def get_hypothesis_confidence(self, hypothesis_id: str) -> float:
        """
        Return the composite confidence score for a hypothesis.
        Used by correlation_engine to adjust ranking.
        """
        stats = self._load_hyp_stats()
        if hypothesis_id not in stats:
            return 0.5  # neutral prior
        return stats[hypothesis_id].confidence_score

    def get_all_hypothesis_stats(self) -> Dict[str, HypothesisStats]:
        return self._load_hyp_stats()

    # ── Pattern scoring ──────────────────────────────────────────────────

    @staticmethod
    def compute_pattern_score(pattern: Dict) -> float:
        """
        Anti-bias scoring formula for learned patterns.

        score = min(0.85 + 0.02 * visit_count, 0.95)
              * age_factor        (decay for patterns > 30 days old)
              * success_factor    (penalty for low success rate < 0.6)
        """
        visit_count = pattern.get("visit_count", 0)
        base_score = min(0.85 + 0.02 * visit_count, 0.95)

        # Age factor
        age_days = 0.0
        try:
            created = datetime.fromisoformat(pattern.get("created_at", ""))
            age_days = (datetime.now(tz=timezone.utc) - created).days
        except Exception:
            pass
        if age_days > 60:
            age_factor = 0.80
        elif age_days > 30:
            age_factor = 0.85
        elif age_days > 14:
            age_factor = 0.92
        else:
            age_factor = 1.0

        # Success rate factor
        s_total = pattern.get("success_count", 0) + pattern.get("failure_count", 0)
        if s_total > 0:
            sr = pattern.get("success_count", 0) / s_total
            success_factor = 0.70 if sr < 0.6 else 1.0
        else:
            success_factor = 0.90  # neutral: new pattern, no outcome data yet

        return round(base_score * age_factor * success_factor, 4)

    # ── Pattern decay ────────────────────────────────────────────────────────

    def decay_patterns(
        self,
        inactive_days: int = 14,
        prune_threshold: float = 0.20,
    ) -> Dict[str, int]:
        """
        Apply time-based decay to learned patterns.

        - Patterns not used recently: score *= 0.98
        - Patterns older than 60 days: score *= 0.90
        - Patterns below prune_threshold are REMOVED

        Returns stats dict with 'decayed', 'pruned', 'kept' counts.
        """
        if not _PATTERNS_FILE.exists():
            return {"decayed": 0, "pruned": 0, "kept": 0}

        try:
            data = json.loads(_PATTERNS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {"decayed": 0, "pruned": 0, "kept": 0}

        patterns = data.get("patterns", [])
        now = datetime.now(tz=timezone.utc)
        stats = {"decayed": 0, "pruned": 0, "kept": 0}
        surviving: List[Dict] = []

        for p in patterns:
            # Compute age
            try:
                created = datetime.fromisoformat(p.get("created_at", ""))
                age_days = (now - created).days
            except Exception:
                age_days = 0

            # Check last use
            try:
                last_used_str = p.get("last_used_at", p.get("created_at", ""))
                last_used = datetime.fromisoformat(last_used_str)
                days_since_use = (now - last_used).days
            except Exception:
                days_since_use = age_days

            current_score = p.get("confidence", 0.85)

            # Apply decay
            if days_since_use > inactive_days:
                current_score *= 0.98
                stats["decayed"] += 1
            if age_days > 60:
                current_score *= 0.90

            p["confidence"] = round(current_score, 4)
            p["visit_count"] = p.get("visit_count", 0)  # ensure field exists

            if current_score < prune_threshold:
                stats["pruned"] += 1
                logger.info(f"Learning Loop: pruned pattern {p.get('id')} (score={current_score:.3f})")
            else:
                surviving.append(p)
                stats["kept"] += 1

        data["patterns"] = surviving
        data["last_decay"] = now.isoformat()
        _PATTERNS_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info(f"Learning Loop: decay complete — {stats}")
        return stats

    # ── Entity memory ─────────────────────────────────────────────────────────

    def update_entity_memory(
        self,
        entity_name: str,
        entity_type: str,
        cause: str,
        pattern_id: str,
        outcome: str,   # "success" | "failure"
    ) -> None:
        """
        Maintain per-entity memory of frequent causes and outcome history.
        Stored in data/learning/entity_memory.json.
        """
        memory = self._load_entity_memory()
        key = entity_name.upper()
        if key not in memory:
            memory[key] = {
                "entity_type": entity_type,
                "frequent_causes": {},
                "success_patterns": [],
                "failure_patterns": [],
                "last_updated": "",
            }
        em = memory[key]
        # Update cause frequency
        em["frequent_causes"][cause] = em["frequent_causes"].get(cause, 0) + 1
        # Track pattern outcome
        if outcome == "success" and pattern_id not in em["success_patterns"]:
            em["success_patterns"] = ([pattern_id] + em["success_patterns"])[:20]
        elif outcome == "failure" and pattern_id not in em["failure_patterns"]:
            em["failure_patterns"] = ([pattern_id] + em["failure_patterns"])[:20]
        em["last_updated"] = datetime.now(tz=timezone.utc).isoformat()
        self._save_entity_memory(memory)

    def get_entity_memory(self, entity_name: str) -> Optional[Dict]:
        """Return entity memory for use in retrieval scoring."""
        memory = self._load_entity_memory()
        return memory.get(entity_name.upper())

    def store_weak_pattern_candidate(
        self,
        session_id: str,
        query: str,
        response: str,
        hypothesis_id: str,
        entity_name: str,
        validation_score: float,
        evidence_count: int,
    ) -> None:
        """
        Store a MEDIUM-tier response as a weak pattern candidate.
        Human review can promote it to a full learned pattern.
        """
        entry = {
            "id": f"WP-{datetime.now(tz=timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "session_id": session_id,
            "created_at": datetime.now(tz=timezone.utc).isoformat(),
            "query": query[:300],
            "response": response[:500],
            "hypothesis_id": hypothesis_id,
            "entity_name": entity_name,
            "validation_score": round(validation_score, 3),
            "evidence_count": evidence_count,
            "priority": "HIGH" if validation_score < 0.65 else "NORMAL",
            "status": "pending_review",
        }
        self._append_to_file(_WEAK_PATTERNS_FILE, "weak_patterns", entry)
        logger.info(
            f"Learning Loop: stored weak pattern candidate {entry['id']} "
            f"for {entity_name} (score={validation_score:.2f}, priority={entry['priority']})"
        )

    # ── Weak Pattern Promotion ────────────────────────────────────────────────

    def promote_weak_patterns(
        self,
        min_count: int = 3,
        min_success_rate: float = 0.7,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Weak Pattern Promotion System.

        A weak pattern is automatically promoted to a full LearnedPattern when:
          - It has been seen >= min_count times (across sessions)
          - Its human-confirmed success rate >= min_success_rate (70%)

        This converts MEDIUM-tier responses into high-confidence learned knowledge.
        Promoted patterns get confidence = 0.80 (conservative — not max).

        Returns: dict with 'promoted', 'skipped', 'details' keys.
        """
        if not _WEAK_PATTERNS_FILE.exists():
            return {"promoted": 0, "skipped": 0, "details": []}

        try:
            data = json.loads(_WEAK_PATTERNS_FILE.read_text(encoding="utf-8"))
            weak_patterns = data.get("weak_patterns", [])
        except Exception:
            return {"promoted": 0, "skipped": 0, "error": "Cannot read weak_patterns.json"}

        # Group by (hypothesis_id, entity_name) to count occurrences
        groups: Dict[str, List[Dict]] = {}
        for wp in weak_patterns:
            group_key = f"{wp.get('hypothesis_id', 'X')}__{wp.get('entity_name', 'X').upper()}"
            groups.setdefault(group_key, []).append(wp)

        promoted: List[str] = []
        skipped: List[str] = []
        newly_learned: List[Dict] = []

        for group_key, entries in groups.items():
            # Only groups with enough occurrences
            if len(entries) < min_count:
                skipped.append(group_key)
                continue

            # Compute success rate from correction feedback in hyp_stats
            hyp_id = entries[0].get("hypothesis_id", "")
            stats = self._load_hyp_stats()
            h_stats = stats.get(hyp_id)
            if h_stats:
                success_rate = h_stats.success_rate
            else:
                # No correction data yet — use validation_score as proxy
                avg_score = sum(e.get("validation_score", 0.5) for e in entries) / len(entries)
                success_rate = avg_score

            if success_rate < min_success_rate:
                skipped.append(f"{group_key} (sr={success_rate:.2f})")
                logger.debug(
                    f"WeakPromotion: skip {group_key} — success_rate={success_rate:.2f} < {min_success_rate}"
                )
                continue

            # Pick representative entry (highest validation_score)
            best = max(entries, key=lambda e: e.get("validation_score", 0.0))
            entity_name = best.get("entity_name", "unknown")

            # Build a full LearnedPattern
            pattern_id = f"LP-PROMO-{datetime.now(tz=timezone.utc).strftime('%Y%m%d%H%M%S')}"
            lp = LearnedPattern(
                id=pattern_id,
                created_at=datetime.now(tz=timezone.utc).isoformat(),
                entity_type="AUTO_PROMOTED",
                entity_name=entity_name,
                problem_summary=best.get("query", "")[:200],
                root_cause=best.get("response", "")[:300],
                actions_taken=[],
                hypothesis_id=hyp_id,
                turn_count=len(entries),
                confidence=0.80,  # conservative: promoted, not manually confirmed
                source_conversation_id=best.get("session_id", ""),
            )

            if not dry_run:
                self._append_to_file(_PATTERNS_FILE, "patterns", asdict(lp))
                # Mark all entries as promoted in weak_patterns
                for e in entries:
                    e["status"] = "promoted"

            newly_learned.append({"id": pattern_id, "hyp_id": hyp_id, "entity": entity_name})
            promoted.append(group_key)
            logger.info(
                f"WeakPromotion: promoted {group_key} → {pattern_id} "
                f"(count={len(entries)}, sr={success_rate:.2f})"
            )

        # Persist updated weak_patterns (mark promoted entries)
        if not dry_run and promoted:
            try:
                data["weak_patterns"] = weak_patterns
                _WEAK_PATTERNS_FILE.write_text(
                    json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
                )
            except Exception as e:
                logger.warning(f"WeakPromotion: could not save weak_patterns: {e}")

        return {
            "promoted": len(promoted),
            "skipped": len(skipped),
            "dry_run": dry_run,
            "details": newly_learned,
        }

    # ── Enriched get_pattern_for_entity ──────────────────────────────────────────

    def get_patterns_for_entity(self, entity_name: str, limit: int = 3) -> List[Dict]:
        """
        Return the top N patterns for an entity, sorted by computed_score descending.
        Each returned dict includes a '_computed_score' field for injection ranking.
        """
        if not _PATTERNS_FILE.exists():
            return []
        try:
            data = json.loads(_PATTERNS_FILE.read_text(encoding="utf-8"))
            patterns = data.get("patterns", [])
            matching = [
                p for p in patterns
                if p.get("entity_name", "").upper() == entity_name.upper()
            ]
        except Exception:
            return []

        # Score + sort
        scored = []
        for p in matching:
            score = self.compute_pattern_score(p)
            p["_computed_score"] = score
            scored.append((score, p))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored[:limit]]

    # ── internal helpers ──────────────────────────────────────────────────────────

    def _load_hyp_stats(self) -> Dict[str, HypothesisStats]:
        if not _HYP_STATS_FILE.exists():
            return {}
        try:
            raw = json.loads(_HYP_STATS_FILE.read_text(encoding="utf-8"))
            return {
                hyp_id: HypothesisStats(**v)
                for hyp_id, v in raw.items()
            }
        except Exception:
            return {}

    def _save_hyp_stats(self, stats: Dict[str, HypothesisStats]) -> None:
        _HYP_STATS_FILE.write_text(
            json.dumps(
                {k: asdict(v) for k, v in stats.items()},
                ensure_ascii=False, indent=2,
            ),
            encoding="utf-8",
        )

    def _load_entity_memory(self) -> Dict[str, Any]:
        if not _ENTITY_MEMORY_FILE.exists():
            return {}
        try:
            return json.loads(_ENTITY_MEMORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_entity_memory(self, memory: Dict[str, Any]) -> None:
        _ENTITY_MEMORY_FILE.write_text(
            json.dumps(memory, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ── existing internal ──────────────────────────────────────────────────────────

    def _ensure_dirs(self):
        _LEARNING_DIR.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _append_to_file(path: Path, list_key: str, item: Dict):
        """Append an item to a JSON list file."""
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        else:
            data = {}

        if list_key not in data:
            data[list_key] = []
        data[list_key].append(item)

        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# Singleton
learning_loop = LearningLoop()
