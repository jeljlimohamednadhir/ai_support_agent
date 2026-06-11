"""
sync_anomaly_detector.py
━━━━━━━━━━━━━━━━━━━━━━━━
MQ / Orchestration Synchronisation Anomaly Detector — N3 Layer

Gap corrected: The previous architecture had NO mechanism to detect the
classic BRASIL synchronisation failure patterns:
  - DB = ACTIVE  but  MQ ACK = absent
  - DB = SUPPRIME but  ORCHESTRA still shows entity
  - DB state ≠ external system state (ARTEMIS, ORCHESTRA, 42C)
  - Partial workflow completion (step N done, step N+1 never executed)
  - Dead-letter queue accumulation (retries exhausted, no alert)

These are the most common N3 production incident patterns at Orange Telecom.
Without this detector, the chatbot cannot reason about them — it can only
retrieve documentation about them.

This module evaluates synchronisation anomalies DETERMINISTICALLY from
structured evidence before any LLM call.

Anomaly taxonomy:
  SYNC_DB_MQ      — DB state updated, MQ propagation failed
  SYNC_DB_ORCH    — DB state diverges from ORCHESTRA
  SYNC_DB_42C     — DB state diverges from 42C
  SYNC_PARTIAL    — workflow partially completed
  SYNC_DLQ        — dead-letter queue accumulation detected
  SYNC_TIMEOUT    — async operation timed out without ACK
  SYNC_ROLLBACK   — partial rollback detected (inconsistent mid-state)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ANOMALY TYPES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class SyncAnomalyType(str, Enum):
    DB_MQ_DIVERGENCE    = "SYNC_DB_MQ"       # DB updated, MQ event lost
    DB_ORCH_DIVERGENCE  = "SYNC_DB_ORCH"     # DB ≠ ORCHESTRA
    DB_42C_DIVERGENCE   = "SYNC_DB_42C"      # DB ≠ 42C
    PARTIAL_WORKFLOW    = "SYNC_PARTIAL"     # workflow partially completed
    DEAD_LETTER_QUEUE   = "SYNC_DLQ"         # DLQ accumulation
    ASYNC_TIMEOUT       = "SYNC_TIMEOUT"     # operation timed out
    PARTIAL_ROLLBACK    = "SYNC_ROLLBACK"    # mid-state after failed transaction
    ORPHAN_RESOURCE     = "SYNC_ORPHAN"      # resource in DB without parent context
    COUNTER_MISMATCH    = "SYNC_COUNTER"     # counter out of sync (TOC)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ANOMALY RESULT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class SyncAnomaly:
    """A detected synchronisation anomaly."""
    anomaly_type: SyncAnomalyType
    severity: str                          # "CRITICAL" | "HIGH" | "MEDIUM"
    entity_name: Optional[str]
    description: str
    evidence_points: List[str] = field(default_factory=list)
    corrective_steps: List[str] = field(default_factory=list)
    fr_id: Optional[str] = None
    confidence: float = 0.9

    def render(self) -> str:
        icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡"}.get(self.severity, "⚠️")
        lines = [
            f"{icon} **Anomalie de synchronisation — {self.anomaly_type.value}**",
            f"*{self.description}*",
        ]
        if self.evidence_points:
            lines.append("\n📊 **Preuves détectées:**")
            for e in self.evidence_points:
                lines.append(f"  • {e}")
        if self.corrective_steps:
            lines.append("\n🔧 **Actions correctives:**")
            for i, step in enumerate(self.corrective_steps, 1):
                lines.append(f"  {i}. {step}")
        if self.fr_id:
            lines.append(f"\n📋 Référence: `{self.fr_id}`")
        return "\n".join(lines)


@dataclass
class SyncAnalysisResult:
    """Result of full synchronisation anomaly analysis."""
    entity_name: Optional[str]
    anomalies: List[SyncAnomaly] = field(default_factory=list)
    has_critical: bool = False
    has_high: bool = False

    def to_context_block(self) -> dict:
        return {
            "source": "sync_anomaly_detector",
            "type": "sync_analysis",
            "entity": self.entity_name,
            "anomaly_count": len(self.anomalies),
            "has_critical": self.has_critical,
            "text": self.render(),
        }

    def render(self) -> str:
        if not self.anomalies:
            return ""
        return "\n\n".join(a.render() for a in self.anomalies)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LOG PATTERNS THAT INDICATE SYNC ANOMALIES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_DLQ_LOG_SIGNALS = [
    "dead.letter", "deadletter", "DLQ", "DEAD_LETTER",
    "message non consomm", "undelivered", "requeue failed",
]
_TIMEOUT_LOG_SIGNALS = [
    "TimeoutException", "SocketTimeoutException", "Connection timed out",
    "timeout after", "ACK timeout", "ARTEMIS timeout",
]
_ROLLBACK_LOG_SIGNALS = [
    "RollbackException", "TransactionRolledbackException",
    "rolling back", "ROLLBACK", "transaction rolled back",
]
_MQ_FAILURE_SIGNALS = [
    "JMSException", "MQException", "ConnectionFactory failed",
    "queue.full", "broker unreachable", "ActiveMQ", "AMQP error",
]


def _detect_in_logs(log_lines: List[str], signals: List[str]) -> List[str]:
    """Return matching lines from log evidence."""
    hits = []
    for line in log_lines:
        for sig in signals:
            if sig.lower() in line.lower():
                hits.append(line[:120])
                break
    return hits[:5]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SYNC ANOMALY DETECTOR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class SyncAnomalyDetector:
    """
    Detects BRASIL synchronisation anomalies from structured evidence.

    Usage:
        detector = SyncAnomalyDetector()
        result = detector.analyze(
            entity_name="DSROB362",
            db_status="A",
            mq_ack_present=False,
            orchestra_status=None,
            log_lines=[...],
            intent="workflow_stuck",
        )
        if result.has_critical:
            # inject result.to_context_block() into LLM prompt
    """

    def analyze(
        self,
        entity_name: Optional[str] = None,
        db_status: Optional[str] = None,
        mq_ack_present: Optional[bool] = None,
        orchestra_status: Optional[str] = None,
        status_42c: Optional[str] = None,
        log_lines: Optional[List[str]] = None,
        detected_exceptions: Optional[List[str]] = None,
        intent: Optional[str] = None,
        active_services: int = 0,
        active_links: int = 0,
    ) -> SyncAnalysisResult:
        """Detect all synchronisation anomalies from available evidence."""
        result = SyncAnalysisResult(entity_name=entity_name)
        log_lines = log_lines or []
        detected_exceptions = detected_exceptions or []

        # ── 1. DB / MQ divergence ─────────────────────────────────────────────
        if (db_status in ("A", "ACTIF", "ACTIVE")
                and mq_ack_present is False):
            anomaly = SyncAnomaly(
                anomaly_type=SyncAnomalyType.DB_MQ_DIVERGENCE,
                severity="CRITICAL",
                entity_name=entity_name,
                description=(
                    f"L'entité `{entity_name}` est ACTIVE en DB "
                    f"mais aucun ACK MQ n'a été reçu par ARTEMIS."
                ),
                evidence_points=[
                    f"DB eqpt_status = `{db_status}`",
                    "MQ ACK: ABSENT",
                    "ARTEMIS n'a pas confirmé la mise en service",
                ],
                corrective_steps=[
                    "Vérifier les dead-letter queues du broker MQ (ActiveMQ/AMQP)",
                    "Vérifier les logs ARTEMIS pour les messages non consommés",
                    "Forcer un re-send du message de mise en service si applicable",
                    "Vérifier la connectivité broker → ARTEMIS",
                ],
                fr_id="FR-BRASIL-SYNC-MQ-001",
                confidence=0.92,
            )
            result.anomalies.append(anomaly)
            result.has_critical = True

        # ── 2. DB / ORCHESTRA divergence ──────────────────────────────────────
        if (db_status and orchestra_status
                and db_status.upper() != orchestra_status.upper()):
            anomaly = SyncAnomaly(
                anomaly_type=SyncAnomalyType.DB_ORCH_DIVERGENCE,
                severity="HIGH",
                entity_name=entity_name,
                description=(
                    f"État BRASIL DB=`{db_status}` ≠ ORCHESTRA=`{orchestra_status}`. "
                    f"Désynchronisation entre les deux systèmes."
                ),
                evidence_points=[
                    f"BRASIL DB: `{db_status}`",
                    f"ORCHESTRA: `{orchestra_status}`",
                ],
                corrective_steps=[
                    "Identifier l'état de référence (DB ou ORCHESTRA)",
                    "Forcer une synchronisation depuis l'IHM BRASIL",
                    "Vérifier l'historique des événements dans les deux systèmes",
                ],
            )
            result.anomalies.append(anomaly)
            result.has_high = True

        # ── 3. DB / 42C divergence ────────────────────────────────────────────
        if (db_status and status_42c
                and db_status.upper() != status_42c.upper()):
            anomaly = SyncAnomaly(
                anomaly_type=SyncAnomalyType.DB_42C_DIVERGENCE,
                severity="HIGH",
                entity_name=entity_name,
                description=(
                    f"Incohérence BRASIL/42C détectée: DB=`{db_status}`, "
                    f"42C=`{status_42c}`."
                ),
                evidence_points=[
                    f"BRASIL DB: `{db_status}`",
                    f"42C: `{status_42c}`",
                ],
                corrective_steps=[
                    "Appliquer la procédure de réconciliation BRASIL/42C",
                    "Vérifier les logs pour l'exception AffectationException",
                ],
                fr_id="FR-DSLAM-AFFECTATION-147B",
            )
            result.anomalies.append(anomaly)
            result.has_high = True

        # ── 4. Dead-letter queue signals in logs ─────────────────────────────
        dlq_hits = _detect_in_logs(log_lines, _DLQ_LOG_SIGNALS)
        if dlq_hits:
            anomaly = SyncAnomaly(
                anomaly_type=SyncAnomalyType.DEAD_LETTER_QUEUE,
                severity="CRITICAL",
                entity_name=entity_name,
                description="Messages en dead-letter queue détectés dans les logs.",
                evidence_points=dlq_hits,
                corrective_steps=[
                    "Inspecter la DLQ du broker MQ",
                    "Identifier les messages bloqués et leur cause",
                    "Décider: re-jouer les messages ou les purger",
                    "Vérifier les consommateurs MQ (ARTEMIS, ORCHESTRA)",
                ],
            )
            result.anomalies.append(anomaly)
            result.has_critical = True

        # ── 5. Timeout signals ───────────────────────────────────────────────
        timeout_hits = _detect_in_logs(log_lines, _TIMEOUT_LOG_SIGNALS)
        if timeout_hits or "TimeoutException" in detected_exceptions:
            anomaly = SyncAnomaly(
                anomaly_type=SyncAnomalyType.ASYNC_TIMEOUT,
                severity="HIGH",
                entity_name=entity_name,
                description="Timeout d'opération asynchrone détecté.",
                evidence_points=timeout_hits or ["TimeoutException dans les logs"],
                corrective_steps=[
                    "Vérifier la disponibilité des systèmes cibles (ARTEMIS, ORCHESTRA)",
                    "Vérifier les timeouts configurés dans standalone.xml / application.properties",
                    "Identifier les opérations en attente depuis > 30 min",
                ],
            )
            result.anomalies.append(anomaly)
            result.has_high = True

        # ── 6. Rollback / partial transaction signals ────────────────────────
        rollback_hits = _detect_in_logs(log_lines, _ROLLBACK_LOG_SIGNALS)
        if rollback_hits or any(e in detected_exceptions for e in [
            "RollbackException", "TransactionRolledbackException"
        ]):
            anomaly = SyncAnomaly(
                anomaly_type=SyncAnomalyType.PARTIAL_ROLLBACK,
                severity="HIGH",
                entity_name=entity_name,
                description=(
                    "Rollback de transaction détecté — l'entité peut être dans "
                    "un état mi-chemin (données partielles en DB)."
                ),
                evidence_points=rollback_hits or ["RollbackException dans les logs"],
                corrective_steps=[
                    "Vérifier la cohérence des données en DB après rollback",
                    "Identifier si des enregistrements partiels existent (t_equipments, t_services)",
                    "Appliquer la procédure de nettoyage des données résiduelles",
                ],
                fr_id="FR-DSLAM-DELETION-189",
            )
            result.anomalies.append(anomaly)
            result.has_high = True

        # ── 7. Orphan resource ────────────────────────────────────────────────
        if (db_status in ("A", "ACTIF")
                and active_services == 0
                and active_links == 0):
            anomaly = SyncAnomaly(
                anomaly_type=SyncAnomalyType.ORPHAN_RESOURCE,
                severity="MEDIUM",
                entity_name=entity_name,
                description=(
                    f"Ressource `{entity_name}` ACTIVE en DB sans services ni liens attachés. "
                    f"Possible état résiduel après suppression partielle."
                ),
                evidence_points=[
                    f"DB status: `{db_status}`",
                    "active_services = 0",
                    "active_links = 0",
                ],
                corrective_steps=[
                    "Vérifier si l'équipement est réellement en production",
                    "Si résiduel: appliquer la procédure de suppression forcée",
                ],
            )
            result.anomalies.append(anomaly)

        return result


# Singleton
_detector_instance: Optional[SyncAnomalyDetector] = None

def get_sync_anomaly_detector() -> SyncAnomalyDetector:
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = SyncAnomalyDetector()
    return _detector_instance
