"""
pipeline_enforcer.py
━━━━━━━━━━━━━━━━━━━
Strict pipeline execution monitor and audit logger.

Enforces the invariant:
  retrieval → correlation → evidence → LLM → validation → learning

Does NOT replace chatbot_service logic.
Provides:
  - PipelineAudit: tracks gate completion per request
  - enforce_* helpers: called at each gate boundary
  - audit_pipeline: final summary log
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, List, Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline Audit — one instance per request
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PipelineAudit:
    session_id: str = ""
    message: str = ""
    t_start: float = field(default_factory=time.time)

    # Gate flags
    intent_ran: bool = False
    retrieval_ran: bool = False
    correlation_ran: bool = False
    evidence_built: bool = False
    llm_ran: bool = False
    validation_ran: bool = False
    validation_passed: Optional[bool] = None
    learning_ran: bool = False

    # Evidence counts
    fr_count: int = 0
    code_count: int = 0
    jira_count: int = 0
    log_count: int = 0
    db_count: int = 0

    # Correlation
    hypothesis_count: int = 0
    correlation_score: float = 0.0
    correlation_skipped_reason: Optional[str] = None

    # Validation
    validation_issues: List[str] = field(default_factory=list)
    validation_downgraded: bool = False

    # Blocked
    blocked: bool = False
    blocked_reason: Optional[str] = None

    # Outcome
    trust_score: int = 0
    response_length: int = 0
    pipeline_mode: Optional[str] = None

    def mark_retrieval(
        self,
        fr: int = 0,
        code: int = 0,
        jira: int = 0,
        logs: int = 0,
        db: int = 0,
    ) -> None:
        self.retrieval_ran = True
        self.fr_count = fr
        self.code_count = code
        self.jira_count = jira
        self.log_count = logs
        self.db_count = db

        empty = []
        if not fr:
            empty.append("FR/Qdrant")
        if not jira:
            empty.append("Jira")
        if not logs:
            empty.append("Logs")
        if not db:
            empty.append("DB")

        if empty:
            logger.warning(
                f"[Pipeline][Gate2-Retrieval] Empty sources: {empty} — "
                f"correlation will use partial data. "
                f"session={self.session_id}"
            )
        else:
            logger.info(
                f"[Pipeline][Gate2-Retrieval] All sources populated: "
                f"FR={fr} code={code} jira={jira} logs={logs} db={db}"
            )

        if fr == 0 and code == 0 and jira == 0 and logs == 0 and db == 0:
            self.blocked = True
            self.blocked_reason = "ALL_SOURCES_EMPTY"
            logger.error(
                f"[Pipeline][Gate2-Retrieval] ALL sources empty — "
                f"pipeline should return no-evidence response. "
                f"session={self.session_id}"
            )

    def mark_correlation(
        self,
        ran: bool,
        hypothesis_count: int = 0,
        score: float = 0.0,
        skipped_reason: Optional[str] = None,
    ) -> None:
        self.correlation_ran = ran
        self.hypothesis_count = hypothesis_count
        self.correlation_score = score
        self.correlation_skipped_reason = skipped_reason

        if not ran:
            logger.error(
                f"[Pipeline][Gate3-Correlation] SKIPPED — reason={skipped_reason}. "
                f"LLM MUST NOT be called without correlation. "
                f"session={self.session_id}"
            )
        else:
            logger.info(
                f"[Pipeline][Gate3-Correlation] hypotheses={hypothesis_count}, "
                f"score={score:.2f}, session={self.session_id}"
            )

    def mark_validation(
        self,
        ran: bool,
        passed: Optional[bool],
        issues: Optional[List[str]] = None,
        downgraded: bool = False,
    ) -> None:
        self.validation_ran = ran
        self.validation_passed = passed
        self.validation_issues = issues or []
        self.validation_downgraded = downgraded

        if not ran:
            logger.error(
                f"[Pipeline][Gate6-Validation] SKIPPED — "
                f"response went to user without validation. "
                f"session={self.session_id}"
            )
        elif not passed:
            logger.warning(
                f"[Pipeline][Gate6-Validation] FAILED — "
                f"issues={self.validation_issues[:3]}, downgraded={downgraded}. "
                f"session={self.session_id}"
            )
        else:
            logger.info(
                f"[Pipeline][Gate6-Validation] PASSED. session={self.session_id}"
            )

    def mark_learning(self, ran: bool) -> None:
        self.learning_ran = ran
        if not ran:
            logger.warning(
                f"[Pipeline][Gate8-Learning] NOT RECORDED. session={self.session_id}"
            )

    def audit(
        self,
        trust_score: int = 0,
        response_length: int = 0,
        pipeline_mode: Optional[str] = None,
    ) -> None:
        self.trust_score = trust_score
        self.response_length = response_length
        self.pipeline_mode = pipeline_mode

        elapsed_ms = int((time.time() - self.t_start) * 1000)

        gates = {
            "intent":       "✅" if self.intent_ran      else "❌",
            "retrieval":    "✅" if self.retrieval_ran    else "❌",
            "correlation":  "✅" if self.correlation_ran  else "🚨",
            "llm":          "✅" if self.llm_ran          else "⏭",
            "validation":   "✅" if self.validation_ran   else "🚨",
            "learning":     "✅" if self.learning_ran     else "⚠️",
        }

        missing_mandatory = []
        if not self.correlation_ran:
            missing_mandatory.append("CORRELATION")
        if not self.validation_ran:
            missing_mandatory.append("VALIDATION")

        status = "🔴 INCOMPLETE" if missing_mandatory else "✅ COMPLETE"

        logger.info(
            f"[Pipeline][Audit] {status} | "
            f"intent={gates['intent']} "
            f"retrieval={gates['retrieval']} "
            f"correlation={gates['correlation']} "
            f"llm={gates['llm']} "
            f"validation={gates['validation']} "
            f"learning={gates['learning']} | "
            f"hyp={self.hypothesis_count} "
            f"ev={self.fr_count+self.code_count+self.jira_count+self.log_count+self.db_count} "
            f"trust={trust_score} "
            f"mode={pipeline_mode} "
            f"{elapsed_ms}ms | "
            f"session={self.session_id}"
        )

        if missing_mandatory:
            logger.error(
                f"[Pipeline][Audit] MANDATORY GATES MISSED: {missing_mandatory} — "
                f"response quality not guaranteed. session={self.session_id}"
            )
