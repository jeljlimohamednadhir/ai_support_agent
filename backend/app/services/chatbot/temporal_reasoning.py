"""
temporal_reasoning.py
━━━━━━━━━━━━━━━━━━━━━
Temporal Event Chain Reasoning Engine — N3 Layer

WHAT THIS SOLVES
────────────────
The causal_rca.py engine is good at STRUCTURAL causality (A blocks B).
But many N3 incidents are TEMPORAL: events happen in a sequence and the
causality is only visible when you reconstruct the timeline.

Example (MQ ACK incident):
  10:00 MQ broker restart (log signal)
  10:02 BRASIL sends EPC provisioning message
  10:05 DB shows EPC in state CONFIGURED
  10:07 ORCHESTRA never received ACK (missing event)
  10:10 BRASIL triggers rollback → EPC state reverts to IN_PROGRESS
  10:12 Retry loop begins

Without temporal reasoning: the engineer sees EPC stuck in IN_PROGRESS and
doesn't know why. The chatbot correctly identifies "MQ ACK missing" but
cannot explain HOW it got there.

With temporal reasoning: the engine reconstructs the chain, identifies the
10:00 broker restart as the root event, explains the propagation delay, and
flags the retry loop starting at 10:12.

CAPABILITIES
────────────
1. Event normalization: parse log events into structured TemporalEvent objects
2. Timeline construction: order events by timestamp
3. Gap detection: detect missing expected events (ACK, callback, state change)
4. Retry loop detection: recurring identical events within a time window
5. Causal window analysis: find events preceding a symptom within N minutes
6. State drift detection: DB state ≠ expected state given event history
7. Orphan state detection: started event with no completion event

BRASIL-SPECIFIC PATTERNS
────────────────────────
- MQ provisioning: SEND → ACK (expected within 30s) → PROCESS → CONFIRM
- EPC workflow: CREATED → IN_PROGRESS → CONFIGURED → ACTIVE
- MakingFile: 0=CREATED → 1=ALLOCATED → 2=IN_PROGRESS → 3=PARTLY → 4=CONFIGURED → 5=AVP
- ES Script: RUNNING → DONE (or RUNNING → ERROR)
- TP: 1=EnCours → 2=Exécuté (or 1=EnCours → 3=Erreur)
- Order lifecycle: order_received → provisioning → db_update → ack → close
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DATA STRUCTURES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class TemporalEvent:
    """A single parsed event on the timeline."""
    timestamp: Optional[datetime]
    event_type: str           # "mq_send", "mq_ack", "state_change", "exception", "log_error", etc.
    entity: Optional[str]     # DSLAM name, ND, EPC ID, ...
    description: str
    source: str               # "log", "db", "exception", "mq_trace"
    severity: str = "info"    # "info", "warning", "error", "critical"
    raw_line: str = ""
    tags: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        ts = self.timestamp.strftime("%H:%M:%S") if self.timestamp else "??:??:??"
        return f"[{ts}] {self.severity.upper():8s} {self.event_type:25s} | {self.description}"


@dataclass
class TimelineGap:
    """A missing expected event on the timeline."""
    expected_event: str
    after_event: str
    max_delay_seconds: int
    reason: str
    severity: str = "warning"

    def render(self) -> str:
        return (
            f"⚠️ **Événement manquant**: `{self.expected_event}` "
            f"attendu après `{self.after_event}` (délai max: {self.max_delay_seconds}s)\n"
            f"   → {self.reason}"
        )


@dataclass
class RetryLoop:
    """A detected retry loop (recurring event pattern)."""
    event_type: str
    occurrences: int
    first_seen: Optional[datetime]
    last_seen: Optional[datetime]
    interval_seconds: Optional[float]
    entity: Optional[str]

    def render(self) -> str:
        dur = ""
        if self.first_seen and self.last_seen:
            dur = f"sur {(self.last_seen - self.first_seen).seconds}s"
        return (
            f"🔄 **Boucle de retry détectée**: `{self.event_type}` × {self.occurrences} {dur}\n"
            f"   → Entité: {self.entity or 'inconnue'} | "
            f"Intervalle: {self.interval_seconds:.1f}s"
            if self.interval_seconds else
            f"🔄 **Boucle de retry**: `{self.event_type}` × {self.occurrences}"
        )


@dataclass
class TemporalAnalysisResult:
    """Complete temporal analysis of an incident."""
    entity: Optional[str]
    timeline: List[TemporalEvent] = field(default_factory=list)
    gaps: List[TimelineGap] = field(default_factory=list)
    retry_loops: List[RetryLoop] = field(default_factory=list)
    root_event: Optional[TemporalEvent] = None       # earliest causal event
    triggering_event: Optional[TemporalEvent] = None  # event that started the failure
    resolution_hypothesis: str = ""
    confidence: float = 0.0

    def render(self) -> str:
        if not self.timeline:
            return ""
        lines = [f"\n⏱️ **Chronologie de l'incident** — {self.entity or 'entité inconnue'}\n"]

        # Timeline
        lines.append("**Séquence d'événements:**")
        for ev in self.timeline[:15]:
            icon = {"error": "🔴", "critical": "🚨", "warning": "🟡", "info": "🔵"}.get(ev.severity, "⚪")
            lines.append(f"  {icon} {ev}")

        # Gaps
        if self.gaps:
            lines.append("\n**Événements manquants (gaps):**")
            for gap in self.gaps:
                lines.append(f"  {gap.render()}")

        # Retry loops
        if self.retry_loops:
            lines.append("\n**Boucles détectées:**")
            for loop in self.retry_loops:
                lines.append(f"  {loop.render()}")

        # Root event
        if self.root_event:
            lines.append(f"\n🎯 **Événement déclencheur probable:** `{self.root_event.event_type}` — {self.root_event.description}")

        # Hypothesis
        if self.resolution_hypothesis:
            lines.append(f"\n💡 **Hypothèse de résolution:** {self.resolution_hypothesis}")

        return "\n".join(lines)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LOG PATTERN → EVENT TYPE MAPPING (BRASIL-SPECIFIC)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_LOG_EVENT_PATTERNS: List[Tuple[re.Pattern, str, str, str]] = [
    # (pattern, event_type, severity, description_template)

    # MQ / JMS events
    (re.compile(r"JMSException|MessageNotDeliveredException|javax\.jms", re.I),
     "mq_error", "error", "Erreur JMS/MQ"),
    (re.compile(r"dead\.letter|DLQ|dead.letter.queue", re.I),
     "dlq_event", "critical", "Message en Dead Letter Queue"),
    (re.compile(r"ACK|acknowledgement|acknowledged", re.I),
     "mq_ack", "info", "Accusé de réception MQ"),
    (re.compile(r"send.*message|message.*sent|publish.*topic", re.I),
     "mq_send", "info", "Envoi message MQ"),
    (re.compile(r"consume|received.*message|message.*received", re.I),
     "mq_receive", "info", "Réception message MQ"),
    (re.compile(r"ConnectionFactory|broker.*unreachable|cannot connect.*broker", re.I),
     "mq_broker_down", "critical", "Broker MQ inaccessible"),

    # BRASIL workflow state changes
    (re.compile(r"createMovement|makeMouvement", re.I),
     "epc_movement_start", "info", "Début mouvement EPC/UMI"),
    (re.compile(r"completeMovement|completeDeletion", re.I),
     "epc_movement_complete", "info", "Fin mouvement EPC"),
    (re.compile(r"makingfile.*state|state.*makingfile|mkfl_state", re.I),
     "makingfile_state_change", "info", "Changement d'état MakingFile"),

    # BRASIL exceptions
    (re.compile(r"ConstraintViolationException|BrasilConstraintException", re.I),
     "constraint_violation", "error", "Violation de contrainte BRASIL"),
    (re.compile(r"BrasilInternalException|INTERNAL_ERROR", re.I),
     "brasil_internal_error", "error", "Erreur interne BRASIL"),
    (re.compile(r"AffectationException|DSLAM.AFFECTATION", re.I),
     "affectation_error", "error", "Erreur affectation 42C"),
    (re.compile(r"BrocheSearchException|erreur.30[0-9]|port.*attribuable.*false", re.I),
     "broche_error", "error", "Erreur attribution port/broche"),
    (re.compile(r"ConnectorCreationVlanException", re.I),
     "vlan_creation_error", "error", "Erreur création VLAN"),
    (re.compile(r"erreur.1300|noeud.ip.absent|eqpt_status.*F", re.I),
     "error_1300", "error", "Erreur 1300 — Noeud IP absent"),

    # Retry and timeout
    (re.compile(r"retry|retrying|tentative.*\d+|attempt.*\d+", re.I),
     "retry_attempt", "warning", "Tentative de rejeu"),
    (re.compile(r"timeout|TimeoutException|Timed out|délai.*expiré", re.I),
     "timeout", "error", "Timeout"),
    (re.compile(r"rollback|ROLLBACK|transaction.*rolled.back", re.I),
     "rollback", "warning", "Rollback transaction"),

    # ES Script states
    (re.compile(r"script.*running|es_state.*1|état.*running|lancement.*script", re.I),
     "script_running", "info", "Script ES en cours"),
    (re.compile(r"script.*done|es_state.*4|script.*terminé", re.I),
     "script_done", "info", "Script ES terminé"),
    (re.compile(r"script.*error|es_state.*2|script.*erreur", re.I),
     "script_error", "error", "Script ES en erreur"),
    (re.compile(r"script.*warning|es_state.*3", re.I),
     "script_warning", "warning", "Script ES avec warning"),

    # DB state signals
    (re.compile(r"eqpt_status.*=.*[AFPCS]|UPDATE.*t_equipments.*status", re.I),
     "db_eqpt_state", "info", "Changement statut équipement"),
    (re.compile(r"epcv_currentstate|epc.*state|EPC.*état", re.I),
     "db_epc_state", "info", "Changement état EPC"),

    # ORCHESTRA/sync
    (re.compile(r"ORCHESTRA|orchestra.*sync|sync.*orchestra", re.I),
     "orchestra_sync", "info", "Synchronisation ORCHESTRA"),
    (re.compile(r"42C|AffectationManager|ManageAffectation", re.I),
     "42c_interaction", "info", "Interaction 42C"),

    # Orphan / residual
    (re.compile(r"orphan|residual|résiduel|données.*résiduelles|stale", re.I),
     "orphan_detected", "warning", "Données résiduelles détectées"),
]

# Timestamp patterns in log files
_TIMESTAMP_PATTERNS: List[re.Pattern] = [
    re.compile(r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)"),
    re.compile(r"(\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2})"),
    re.compile(r"(\d{2}:\d{2}:\d{2}(?:\.\d+)?)"),   # HH:MM:SS only
]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EXPECTED EVENT SEQUENCES (what SHOULD happen in a healthy workflow)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_EXPECTED_SEQUENCES: Dict[str, List[Tuple[str, str, int]]] = {
    # (trigger_event, expected_followup, max_seconds)
    "mq_send": [
        ("mq_ack", "ACK MQ attendu dans les 30s", 30),
        ("mq_receive", "Le consommateur doit traiter le message", 60),
    ],
    "epc_movement_start": [
        ("epc_movement_complete", "Le mouvement EPC doit se compléter", 120),
    ],
    "script_running": [
        ("script_done", "Le script doit se terminer (done ou error)", 3600),
    ],
}

# State machine transitions for BRASIL entities
_BRASIL_FSM: Dict[str, Dict[str, List[str]]] = {
    "makingfile": {
        "0_CREATED":      ["1_ALLOCATED"],
        "1_ALLOCATED":    ["2_IN_PROGRESS"],
        "2_IN_PROGRESS":  ["3_PARTLY_CONFIGURED"],
        "3_PARTLY_CONFIGURED": ["4_CONFIGURED"],
        "4_CONFIGURED":   ["5_AVP"],
        "5_AVP":          [],  # terminal
    },
    "epc": {
        "C": ["M"],    # Created → Modified (or deletion)
        "M": ["C", "X"],
        "X": [],       # terminal (deleted)
    },
    "equipment": {
        "C": ["A", "F"],   # Created → Active or Closed
        "A": ["P", "F", "S"],  # Active → In_progress, Closed, Suppression
        "P": ["A", "F"],   # In_progress → Active or Closed
        "F": ["A", "S"],   # Closed → Active or Suppression
        "S": [],           # Suppression → terminal
    },
    "es_script": {
        "1_RUNNING": ["2_ERROR", "3_WARNING", "4_DONE"],
        "2_ERROR":   ["1_RUNNING"],  # re-run possible
        "3_WARNING": ["4_DONE"],
        "4_DONE":    [],
    },
    "tp": {
        "1_EN_COURS": ["2_EXECUTE", "3_ERREUR"],
        "2_EXECUTE":  [],
        "3_ERREUR":   ["1_EN_COURS"],  # retry
    },
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEMPORAL REASONING ENGINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TemporalReasoningEngine:
    """
    Reconstructs and analyzes event timelines for N3 incident investigation.

    Usage:
        engine = temporal_engine
        result = engine.analyze(
            raw_logs="[10:02] JMSException... [10:07] retry... [10:10] rollback",
            entity="DSROB362",
            context={"intent": "workflow_blocked"}
        )
    """

    # Maximum age of events to consider for RCA (stale suppression window)
    _STALE_WINDOW_HOURS: int = 48

    def analyze(
        self,
        raw_logs: str = "",
        events: Optional[List[TemporalEvent]] = None,
        entity: Optional[str] = None,
        context: Optional[Dict] = None,
        suppress_stale: bool = True,
    ) -> TemporalAnalysisResult:
        """
        Main entry point.
        Accepts either raw log text or pre-parsed TemporalEvent list.
        suppress_stale: if True, events older than _STALE_WINDOW_HOURS are
          kept in the timeline but down-weighted and not used for root cause.
        """
        context = context or {}
        result = TemporalAnalysisResult(entity=entity)

        # 1. Parse events from raw logs
        if raw_logs:
            parsed = self._parse_log_text(raw_logs, entity)
            if events:
                events = parsed + events
            else:
                events = parsed

        if not events:
            return result

        # 2. Sort by timestamp (unknowns at the end)
        events = sorted(events, key=lambda e: (e.timestamp is None, e.timestamp or datetime.min))

        # 3. Stale event suppression — tag events older than window as stale
        if suppress_stale:
            events = self._suppress_stale_events(events)

        result.timeline = events

        # 3. Detect retry loops
        result.retry_loops = self._detect_retry_loops(events)

        # 4. Detect missing events (gaps)
        result.gaps = self._detect_gaps(events)

        # 5. Identify root / triggering events
        result.root_event = self._find_root_event(events)
        result.triggering_event = self._find_triggering_event(events, context)

        # 6. Generate resolution hypothesis
        result.resolution_hypothesis = self._generate_hypothesis(result, context)
        result.confidence = self._score_confidence(result)

        return result

    def validate_fsm_transition(
        self,
        entity_type: str,
        from_state: str,
        to_state: str,
    ) -> Tuple[bool, str]:
        """
        Validate a state machine transition against BRASIL FSM rules.
        Returns (is_valid, explanation).
        """
        fsm = _BRASIL_FSM.get(entity_type.lower(), {})
        if not fsm:
            return True, f"FSM inconnu pour '{entity_type}' — validation ignorée"

        # Normalize state
        from_norm = from_state.upper().split("_")[0] if "_" in from_state else from_state.upper()
        allowed = fsm.get(from_state, fsm.get(from_norm, []))

        if to_state in allowed or to_state.upper() in [a.upper() for a in allowed]:
            return True, f"Transition {from_state} → {to_state} valide pour {entity_type}"

        return False, (
            f"🚫 Transition INVALIDE pour {entity_type}: `{from_state}` → `{to_state}`\n"
            f"Transitions autorisées depuis `{from_state}`: {allowed or ['aucune (état terminal)']}"
        )

    def detect_orphan_state(
        self,
        entity_type: str,
        current_state: str,
        expected_completion_event: Optional[str] = None,
    ) -> Optional[str]:
        """
        Detect if an entity is stuck in an intermediate state with no completion path.
        """
        fsm = _BRASIL_FSM.get(entity_type.lower(), {})
        if not fsm:
            return None

        state_upper = current_state.upper()
        # Check if this is a non-terminal state
        if state_upper in fsm:
            if not fsm[state_upper]:
                return None  # terminal state, not orphaned
            # It's in a transitional state — flag it
            allowed_next = fsm[state_upper]
            return (
                f"⚠️ **État orphelin potentiel**: {entity_type} en état `{current_state}`\n"
                f"Prochains états possibles: {allowed_next}\n"
                f"Si aucun événement attendu n'est en cours, cette entité est potentiellement bloquée."
            )
        return None

    # ── Private methods ────────────────────────────────────────────────────

    def _suppress_stale_events(self, events: List[TemporalEvent]) -> List[TemporalEvent]:
        """
        Tag events older than _STALE_WINDOW_HOURS as stale.
        Stale events stay in the timeline (for context) but get severity
        downgraded to 'info' and tagged so RCA can ignore them.
        """
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=self._STALE_WINDOW_HOURS)
        for ev in events:
            if not ev.timestamp:
                continue

            event_ts = ev.timestamp
            if event_ts.tzinfo is None:
                event_ts = event_ts.replace(tzinfo=timezone.utc)
            else:
                event_ts = event_ts.astimezone(timezone.utc)

            if event_ts > now:
                if "future_timestamp" not in ev.tags:
                    ev.tags.append("future_timestamp")
                continue

            if event_ts < cutoff:
                if ev.severity in ("error", "critical"):
                    ev.severity = "info"  # downgrade
                if "stale" not in ev.tags:
                    ev.tags.append("stale")
                    ev.description = f"[STALE] {ev.description}"
        return events

    def _parse_log_text(self, text: str, entity: Optional[str]) -> List[TemporalEvent]:
        """Parse raw log text into TemporalEvent objects."""
        events: List[TemporalEvent] = []
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue

            # Extract timestamp
            ts = self._extract_timestamp(line)

            # Match event type
            for pattern, event_type, severity, desc in _LOG_EVENT_PATTERNS:
                if pattern.search(line):
                    events.append(TemporalEvent(
                        timestamp=ts,
                        event_type=event_type,
                        entity=entity,
                        description=desc,
                        source="log",
                        severity=severity,
                        raw_line=line[:200],
                    ))
                    break  # first match wins
            else:
                # Check if this line contains an error/exception even with no pattern match
                if any(kw in line.lower() for kw in ["exception", "error", "erreur", "failed", "failure"]):
                    events.append(TemporalEvent(
                        timestamp=ts,
                        event_type="unclassified_error",
                        entity=entity,
                        description=line[:120],
                        source="log",
                        severity="error",
                        raw_line=line[:200],
                    ))

        return events

    def _extract_timestamp(self, line: str) -> Optional[datetime]:
        """Extract timestamp from a log line."""
        for pattern in _TIMESTAMP_PATTERNS:
            m = pattern.search(line)
            if m:
                ts_str = m.group(1)
                for fmt in (
                    "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d %H:%M:%S.%f",
                    "%d/%m/%Y %H:%M:%S",
                    "%H:%M:%S", "%H:%M:%S.%f",
                ):
                    try:
                        dt = datetime.strptime(ts_str.split("+")[0].split("Z")[0], fmt)
                        # For time-only, use today's date
                        if dt.year == 1900:
                            today = datetime.now()
                            dt = dt.replace(year=today.year, month=today.month, day=today.day)
                        return dt
                    except ValueError:
                        continue
        return None

    # Event types that legitimately recur often and should NOT be flagged as retry loops
    _BENIGN_RECURRING: frozenset = frozenset({
        "orchestra_sync", "42c_interaction", "mq_receive", "db_eqpt_state",
        "db_epc_state", "mq_send",  # high-frequency operational events
    })

    def _detect_retry_loops(self, events: List[TemporalEvent]) -> List[RetryLoop]:
        """Detect recurring event patterns (retry loops)."""
        loops: List[RetryLoop] = []
        event_counts: Dict[str, List[TemporalEvent]] = {}
        for ev in events:
            event_counts.setdefault(ev.event_type, []).append(ev)

        for event_type, occurrences in event_counts.items():
            # Skip benign operational events that legitimately recur
            if event_type in self._BENIGN_RECURRING:
                continue
            # Threshold: 5 for error/retry events, 8 for non-error events
            threshold = 5 if event_type in {
                "retry_attempt", "timeout", "mq_error", "script_running",
                "rollback", "constraint_violation", "dlq_event"
            } else 8
            if len(occurrences) >= threshold:
                timed = [e for e in occurrences if e.timestamp]
                interval = None
                if len(timed) >= 2:
                    deltas = [
                        (timed[i+1].timestamp - timed[i].timestamp).total_seconds()
                        for i in range(len(timed) - 1)
                    ]
                    interval = sum(deltas) / len(deltas) if deltas else None

                loops.append(RetryLoop(
                    event_type=event_type,
                    occurrences=len(occurrences),
                    first_seen=timed[0].timestamp if timed else None,
                    last_seen=timed[-1].timestamp if timed else None,
                    interval_seconds=interval,
                    entity=occurrences[0].entity,
                ))

        return loops

    def _detect_gaps(self, events: List[TemporalEvent]) -> List[TimelineGap]:
        """Detect missing expected follow-up events."""
        gaps: List[TimelineGap] = []
        seen_types = {ev.event_type for ev in events}

        for trigger_type, expectations in _EXPECTED_SEQUENCES.items():
            if trigger_type not in seen_types:
                continue
            # This trigger event exists — check if expected follow-ups exist
            for expected_type, reason, max_secs in expectations:
                if expected_type not in seen_types:
                    gaps.append(TimelineGap(
                        expected_event=expected_type,
                        after_event=trigger_type,
                        max_delay_seconds=max_secs,
                        reason=reason,
                        severity="error" if max_secs <= 30 else "warning",
                    ))

        return gaps

    def _find_root_event(self, events: List[TemporalEvent]) -> Optional[TemporalEvent]:
        """Find the earliest critical event that likely started the failure chain.
        Stale events are excluded from root cause consideration."""
        critical_types = {"mq_broker_down", "constraint_violation", "error_1300",
                          "dlq_event", "affectation_error"}
        non_stale = [e for e in events if "stale" not in e.tags]
        search_set = non_stale if non_stale else events  # fallback to all if all stale
        for ev in search_set:  # already sorted by time
            if ev.event_type in critical_types or ev.severity == "critical":
                return ev
        # Fall back to first error
        for ev in search_set:
            if ev.severity in ("error", "critical"):
                return ev
        return None

    def _find_triggering_event(
        self,
        events: List[TemporalEvent],
        context: Dict,
    ) -> Optional[TemporalEvent]:
        """Find the specific event that directly triggered the user's observed symptom."""
        intent = context.get("intent", "")

        intent_triggers = {
            "delete_equipment": {"constraint_violation", "brasil_internal_error"},
            "workflow_blocked": {"timeout", "rollback", "mq_error"},
            "mq_sync_issue": {"mq_error", "dlq_event", "mq_broker_down"},
            "script_stuck": {"script_running"},
            "vlan_inconsistency": {"vlan_creation_error", "orchestra_sync"},
        }

        relevant_types = intent_triggers.get(intent, set())
        # Search in reverse (most recent first) for triggering event
        for ev in reversed(events):
            if ev.event_type in relevant_types:
                return ev
        return None

    def _generate_hypothesis(
        self,
        result: TemporalAnalysisResult,
        context: Dict,
    ) -> str:
        """Generate a natural language resolution hypothesis from temporal evidence."""
        parts = []

        # Root event
        if result.root_event:
            parts.append(
                f"L'événement initiateur est `{result.root_event.event_type}` "
                f"({'à ' + result.root_event.timestamp.strftime('%H:%M:%S') if result.root_event.timestamp else 'heure inconnue'})."
            )

        # MQ gap
        mq_gaps = [g for g in result.gaps if "mq" in g.expected_event.lower()]
        if mq_gaps:
            parts.append(
                "Un ACK MQ est absent — le message a été envoyé mais le consommateur "
                "ne l'a pas traité dans les délais. Vérifier la DLQ et le broker."
            )

        # Retry loops
        if result.retry_loops:
            worst = max(result.retry_loops, key=lambda l: l.occurrences)
            parts.append(
                f"Une boucle de retry est active (`{worst.event_type}` × {worst.occurrences}). "
                "Corriger la cause racine avant de relancer."
            )

        # Rollback detected
        if any(ev.event_type == "rollback" for ev in result.timeline):
            parts.append(
                "Un rollback a été détecté — l'état DB peut être incohérent. "
                "Vérifier l'état actuel en base avant toute action."
            )

        return " ".join(parts) if parts else ""

    def _score_confidence(self, result: TemporalAnalysisResult) -> float:
        """Score the confidence of the temporal analysis."""
        score = 0.0
        timed_events = [e for e in result.timeline if e.timestamp is not None]
        if timed_events:
            score += 0.3  # temporal ordering available
        if result.root_event:
            score += 0.2
        if result.gaps:
            score += 0.2
        if result.retry_loops:
            score += 0.15
        if result.resolution_hypothesis:
            score += 0.15
        return min(score, 0.95)

    def summarize_for_prompt(self, result: TemporalAnalysisResult) -> str:
        """Compact summary suitable for injection into LLM system prompt."""
        if not result.timeline:
            return ""
        critical = [e for e in result.timeline if e.severity in ("error", "critical")]
        parts = [
            f"[TEMPORAL] Entité: {result.entity or 'N/A'}",
            f"Événements: {len(result.timeline)} total, {len(critical)} erreur(s)/critique(s)",
        ]
        if result.root_event:
            parts.append(f"Événement racine: {result.root_event.event_type} — {result.root_event.description}")
        if result.gaps:
            parts.append(f"Gaps: {'; '.join(g.expected_event for g in result.gaps)}")
        if result.retry_loops:
            parts.append(f"Loops: {'; '.join(f'{l.event_type}×{l.occurrences}' for l in result.retry_loops)}")
        if result.resolution_hypothesis:
            parts.append(f"Hypothèse: {result.resolution_hypothesis}")
        return "\n".join(parts)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# QUICK ANALYSIS HELPERS (for chatbot_service.py injection)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def analyze_logs_temporal(
    raw_logs: str,
    entity: Optional[str] = None,
    intent: Optional[str] = None,
) -> TemporalAnalysisResult:
    """Convenience function: analyze raw log text and return temporal result."""
    return temporal_engine.analyze(
        raw_logs=raw_logs,
        entity=entity,
        context={"intent": intent or ""},
    )


def inject_temporal_context(
    raw_logs: str,
    entity: Optional[str] = None,
    intent: Optional[str] = None,
) -> str:
    """
    Quick utility for chatbot_service.py:
    Returns a formatted temporal analysis string ready to inject into the LLM prompt.
    Returns empty string if no meaningful analysis.
    """
    if not raw_logs or len(raw_logs) < 50:
        return ""
    result = analyze_logs_temporal(raw_logs, entity, intent)
    if not result.timeline:
        return ""
    return result.render()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SINGLETON
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

temporal_engine = TemporalReasoningEngine()
