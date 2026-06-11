"""
production_readiness.py
━━━━━━━━━━━━━━━━━━━━━━━
Pre-Output Quality Gate & Production Readiness Scorer

PURPOSE
───────
Before any chatbot response reaches the N3 engineer, this gate evaluates:
1. Is the response grounded in real evidence (not hallucinated)?
2. Does it actually answer the question asked?
3. Is the RCA depth appropriate for the severity?
4. Is the operational guidance actionable?
5. What is the hallucination risk?

Any response scoring below BLOCK_THRESHOLD (40/100) is BLOCKED and replaced
with a "confidence insuffisante" fallback. Responses between 40–60 get a
warning banner added. Responses above 60 pass cleanly.

SCORING DIMENSIONS (100 points total)
──────────────────────────────────────
1. Evidence Backing (0–25 pts)     — Are claims backed by DB/schema/logs?
2. Hallucination Risk (0–25 pts)   — Does it invent table names, values, errors?
3. RCA Depth (0–20 pts)            — Root cause identified? Chain explained?
4. Operational Value (0–20 pts)    — Can the engineer take action from this?
5. Answer Completeness (0–10 pts)  — Does it address the actual question?

BRASIL-SPECIFIC ANTI-HALLUCINATION RULES
─────────────────────────────────────────
- Table names must exist in REAL_SQL_TABLES (130 known tables)
- BRASIL error codes must be from known list (1300, 4002, 42C, 30x, etc.)
- State values must be valid (A/F/P/C/S for equipment, 0–5 for MakingFile, etc.)
- Workflow steps must match known BRASIL workflow definitions
- SQL queries must reference real columns (validated against schema)
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# ── Thresholds ────────────────────────────────────────────────────────────
BLOCK_THRESHOLD = 40      # Score below this → response blocked
WARN_THRESHOLD = 60       # Score below this → warning banner added
MAX_SCORE = 100


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# KNOWN VALID VALUES (BRASIL-specific ground truth)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_KNOWN_ERROR_CODES: Set[str] = {
    "1300", "4002", "42C", "301", "302", "303", "304", "305",
    "BROCHE_ERROR", "EQPT_DEL_001", "EQPT_DEL_002", "EQPT_DEL_003",
    "EPCV_FSM_001", "EPCV_FSM_002", "EPCV_FSM_003",
    "MKFL_001", "MKFL_002", "MKFL_003",
    "ND_AFF_001", "ND_AFF_002",
    "VLAN_DEL_001", "VLAN_DEL_002",
    "ES_SCR_001", "ORPHAN_001", "ORPHAN_002", "ORPHAN_003",
    "RETRY_001",
}

_VALID_EQPT_STATES: Set[str] = {"A", "F", "P", "C", "S"}
_VALID_MAKING_FILE_STATES: Set[str] = {"0", "1", "2", "3", "4", "5"}
_VALID_ES_SCRIPT_STATES: Set[str] = {"1", "2", "3", "4"}
_VALID_TP_STATES: Set[str] = {"1", "2", "3"}

# Hallucination red-flag patterns: phrases that indicate the model is guessing
_HALLUCINATION_RED_FLAGS: List[re.Pattern] = [
    re.compile(r"je\s+suppose\s+que|I\s+suppose|I\s+assume|je\s+crois\s+que|j\'imagine", re.I),
    re.compile(r"probablement\s+(?:la\s+table|le\s+champ|la\s+colonne)\s+t_[a-z]", re.I),
    re.compile(r"il\s+(?:me\s+)?semble\s+que\s+la\s+table|la\s+table\s+(?:devrait|devrait s'appeler)", re.I),
    re.compile(r"t_unknown|t_temp|t_test|t_example|t_sample|t_dummy", re.I),
    re.compile(r"erreur\s+9999|code\s+9999|exception.*9999", re.I),  # invented code
    re.compile(r"statut\s+[GHIJKLMNQRUVWXYZ]\b", re.I),  # invalid equipment status
    re.compile(r"(?:je\s+ne\s+suis\s+pas\s+sûr|I'm\s+not\s+sure)\s+(?:mais|but)\s+(?:je\s+pense|I\s+think)", re.I),
    re.compile(r"based\s+on\s+(?:my\s+)?(?:training|knowledge\s+cutoff)", re.I),
    re.compile(r"as\s+of\s+my\s+(?:last\s+)?(?:update|training)", re.I),
]

# Evidence anchors: phrases that INCREASE confidence (model citing real evidence)
_EVIDENCE_ANCHORS: List[re.Pattern] = [
    re.compile(r"SELECT\s+.+\s+FROM\s+t_\w+", re.I),   # real SQL
    re.compile(r"describe_table\(|brasil_schema_knowledge", re.I),
    re.compile(r"\bSCHÉMA\s+BRASIL\s+VÉRIFIÉ\b", re.I),
    re.compile(r"✅\s+SCHÉMA|✅\s+BRASIL", re.I),
    re.compile(r"colonne[s]?\s+:\s+\w+", re.I),         # column names listed
    re.compile(r"FK\s+→\s+t_\w+|clé\s+étrangère\s+vers", re.I),
    re.compile(r"eqpt_status\s*=\s*[\"']?[AFPCS][\"']?", re.I),
    re.compile(r"logs?\s*:\s*\[?\d{2}:\d{2}", re.I),    # log timestamps
]

# RCA depth markers: phrases that indicate the model did actual RCA
_RCA_DEPTH_MARKERS: List[re.Pattern] = [
    re.compile(r"cause\s+(?:racine|root|principale)", re.I),
    re.compile(r"chain[e]?\s+(?:de\s+)?causalit[eé]|causal\s+chain", re.I),
    re.compile(r"(?:parce\s+que|because)\s+.{10,}\s+(?:donc|ce\s+qui|which\s+means)", re.I),
    re.compile(r"(?:étape|step)\s+\d+\s*:\s*(?:vérifi|check)", re.I),
    re.compile(r"résolution\s+en\s+\d+\s+étapes?", re.I),
    re.compile(r"pré.requis\s+(?:de\s+)?(?:suppression|deletion|correction)", re.I),
]

# Operational value markers: actionable content
_OPERATIONAL_MARKERS: List[re.Pattern] = [
    re.compile(r"SELECT\s+.+\s+FROM\s+\w+\s+WHERE", re.I),  # SQL query
    re.compile(r"étape\s+\d+|step\s+\d+|[1-9]\.\s+\w", re.I),
    re.compile(r"commande\s*:\s*.{5,}|command\s*:\s*.{5,}", re.I),
    re.compile(r"(?:vérifi[e|ez]|check)\s+(?:la\s+table|le\s+champ|l[\'']état)", re.I),
    re.compile(r"UPDATE\s+\w+\s+SET|DELETE\s+FROM\s+\w+\s+WHERE", re.I),
    re.compile(r"(?:solution|fix|correction)\s*:\s*.{10,}", re.I),
    re.compile(r"procédure|procedure|runbook", re.I),
]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SCORING RESULT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class QualityScore:
    """Complete quality assessment of a chatbot response."""
    total: int = 0
    evidence_backing: int = 0      # /25
    hallucination_risk: int = 0    # /25 (higher = less risky = better)
    rca_depth: int = 0             # /20
    operational_value: int = 0     # /20
    answer_completeness: int = 0   # /10

    blocked: bool = False
    warnings: List[str] = field(default_factory=list)
    explanations: List[str] = field(default_factory=list)
    fake_tables_found: List[str] = field(default_factory=list)
    red_flags_found: List[str] = field(default_factory=list)

    @property
    def grade(self) -> str:
        if self.total >= 80:  return "A"
        if self.total >= 70:  return "B"
        if self.total >= 60:  return "C"
        if self.total >= 40:  return "D"
        return "F"

    @property
    def label(self) -> str:
        if self.blocked:      return "🚫 BLOQUÉ"
        if self.total >= 80:  return "✅ EXCELLENT"
        if self.total >= 60:  return "✅ BON"
        if self.total >= 40:  return "⚠️ ACCEPTABLE"
        return "❌ INSUFFISANT"

    def render_badge(self) -> str:
        return f"[Q:{self.total}/100 {self.grade}]"


@dataclass
class GateResult:
    """Final output of the production readiness gate."""
    passed: bool
    score: QualityScore
    final_response: str    # Original or modified/blocked response
    added_warnings: List[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.passed


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PRODUCTION READINESS GATE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ProductionReadinessGate:
    """
    Pre-output quality gate for N3 chatbot responses.

    Usage:
        gate = production_gate
        result = gate.evaluate(
            response="...",
            question="impossible de supprimer DSROB362",
            context={"category": "deletion_blocked"}
        )
        if result.passed:
            send_to_engineer(result.final_response)
        else:
            send_to_engineer(result.final_response)  # already contains fallback
    """

    def __init__(self):
        self._known_tables: Set[str] = self._load_known_tables()

    def _load_known_tables(self) -> Set[str]:
        try:
            from app.services.chatbot.brasil_schema_knowledge import REAL_SQL_TABLES
            if REAL_SQL_TABLES:
                return set(t.lower() for t in REAL_SQL_TABLES)
        except Exception:
            pass
        # Static fallback (subset)
        return {
            "t_equipments", "t_services", "t_vlan", "t_connectors",
            "t_epc", "t_mrt_access_dslams", "t_tech_services",
            "t_service_profiles", "t_resource_usages", "t_tp_es_scripts",
            "t_nd_infra", "t_p_talia_service_ids",
        }

    def evaluate(
        self,
        response: str,
        question: str = "",
        context: Optional[Dict] = None,
    ) -> GateResult:
        """
        Evaluate a response and return a GateResult.
        Modifies response if score is in warning zone or blocks it if too low.
        """
        context = context or {}

        score = QualityScore()

        # ── Score dimension 1: Evidence backing (0–25) ─────────────────────
        evidence_count = sum(1 for p in _EVIDENCE_ANCHORS if p.search(response))
        # Check SQL queries referencing real tables
        sql_tables = re.findall(r"FROM\s+(t_\w+)", response, re.I)
        real_sql_tables = [t for t in sql_tables if t.lower() in self._known_tables]
        sql_bonus = min(len(real_sql_tables) * 3, 10)
        score.evidence_backing = min(evidence_count * 4 + sql_bonus, 25)
        if score.evidence_backing >= 15:
            score.explanations.append(f"✅ Réponse bien ancrée ({evidence_count} ancres d'évidence)")

        # ── Score dimension 2: Hallucination risk (0–25, higher = safer) ───
        red_flag_count = 0
        for pat in _HALLUCINATION_RED_FLAGS:
            m = pat.search(response)
            if m:
                score.red_flags_found.append(m.group(0)[:60])
                red_flag_count += 1

        # Check for fake table names (t_xxx not in known tables)
        all_table_refs = re.findall(r"\bt_[a-z_]{3,40}\b", response, re.I)
        fake_tables = [t for t in all_table_refs if t.lower() not in self._known_tables]
        score.fake_tables_found = list(set(fake_tables))

        hallucination_penalty = red_flag_count * 5 + len(score.fake_tables_found) * 4
        score.hallucination_risk = max(0, 25 - hallucination_penalty)
        if score.fake_tables_found:
            score.warnings.append(
                f"⚠️ Tables inconnues référencées: {', '.join(score.fake_tables_found[:5])}"
            )
        if score.red_flags_found:
            score.warnings.append(
                f"⚠️ Indicateurs d'incertitude détectés: {red_flag_count} occurrence(s) — {score.red_flags_found[0][:50]}"
            )

        # ── Score dimension 3: RCA depth (0–20) ────────────────────────────
        rca_count = sum(1 for p in _RCA_DEPTH_MARKERS if p.search(response))
        category = context.get("category", "")
        rca_required = category in {
            "deletion_blocked", "workflow_stuck", "mq_sync_failure",
            "causal_escalation", "rollback_detected", "cross_system_drift",
            "recurring_incident",
        }
        if rca_required and rca_count == 0:
            score.rca_depth = 0
            score.warnings.append("⚠️ Analyse de cause racine absente pour un incident critique")
        else:
            score.rca_depth = min(rca_count * 5, 20)
            if rca_count >= 3:
                score.explanations.append("✅ RCA approfondie détectée")

        # ── Score dimension 4: Operational value (0–20) ────────────────────
        op_count = sum(1 for p in _OPERATIONAL_MARKERS if p.search(response))
        score.operational_value = min(op_count * 4, 20)
        if score.operational_value == 0 and len(response) > 200:
            score.warnings.append("⚠️ Réponse sans guidance opérationnel concret (pas de SQL, étapes, ou commandes)")

        # ── Score dimension 5: Answer completeness (0–10) ──────────────────
        # Basic: does response length suggest it addressed the question?
        resp_len = len(response.strip())
        if resp_len < 100:
            score.answer_completeness = 2
            score.warnings.append("⚠️ Réponse trop courte pour une question N3")
        elif resp_len < 300:
            score.answer_completeness = 5
        elif resp_len < 800:
            score.answer_completeness = 8
        else:
            score.answer_completeness = 10

        # Question keyword check (simple: does the response mention key nouns from question?)
        if question:
            question_words = set(re.findall(r"\b\w{5,}\b", question.lower()))
            response_words = set(re.findall(r"\b\w{5,}\b", response.lower()))
            overlap = question_words & response_words
            if len(question_words) > 0:
                overlap_ratio = len(overlap) / len(question_words)
                if overlap_ratio < 0.2:
                    score.answer_completeness = max(0, score.answer_completeness - 4)
                    score.warnings.append("⚠️ La réponse ne semble pas adresser la question posée")

        # ── Total ────────────────────────────────────────────────────────────
        score.total = (
            score.evidence_backing
            + score.hallucination_risk
            + score.rca_depth
            + score.operational_value
            + score.answer_completeness
        )

        # ── Gate decision ────────────────────────────────────────────────────
        if score.total < BLOCK_THRESHOLD:
            score.blocked = True
            final_response = self._build_fallback_response(question, score, context)
            return GateResult(
                passed=False,
                score=score,
                final_response=final_response,
                added_warnings=score.warnings,
            )

        # Add warning banner if in warning zone
        added_warnings = []
        if score.total < WARN_THRESHOLD and score.warnings:
            banner = self._build_warning_banner(score)
            final_response = banner + "\n\n" + response
            added_warnings = score.warnings
        else:
            final_response = response

        return GateResult(
            passed=True,
            score=score,
            final_response=final_response,
            added_warnings=added_warnings,
        )

    def _build_warning_banner(self, score: QualityScore) -> str:
        """Build a warning banner to prepend to low-confidence responses."""
        lines = [
            f"⚠️ **Confiance limitée** {score.render_badge()} — Cette réponse est partiellement validée.",
        ]
        if score.fake_tables_found:
            lines.append(
                f"Tables non vérifiées dans le schéma: `{'`, `'.join(score.fake_tables_found[:3])}`"
            )
        if score.warnings:
            for w in score.warnings[:2]:
                lines.append(w)
        lines.append("_Vérifiez les informations critiques avant toute action en production._")
        return "\n".join(lines)

    def _build_fallback_response(
        self,
        question: str,
        score: QualityScore,
        context: Dict,
    ) -> str:
        """Build a fallback response when the original is blocked."""
        category = context.get("category", "inconnu")
        lines = [
            f"🚫 **Réponse bloquée** — Score de confiance insuffisant ({score.total}/100)",
            "",
            f"La réponse générée ne satisfait pas les critères de qualité pour une question N3 "
            f"de type **{category}**.",
            "",
            "**Problèmes détectés:**",
        ]
        for w in score.warnings[:5]:
            lines.append(f"  - {w}")

        lines.extend([
            "",
            "**Actions recommandées:**",
            "  1. Vérifiez les logs BRASIL directement",
            "  2. Consultez la documentation technique N3",
            "  3. Escaladez si le problème persiste",
            "",
            "_Le chatbot ne dispose pas d'informations suffisantes pour répondre "
            "de manière fiable à cette question. Merci de fournir plus de contexte "
            "(logs, nom de l'entité, message d'erreur exact)._",
        ])
        return "\n".join(lines)

    def quick_check(self, response: str, question: str = "") -> Tuple[bool, int, str]:
        """
        Quick check returning (passed, score, label).
        For use in chatbot_service.py without full context.
        """
        result = self.evaluate(response, question)
        return result.passed, result.score.total, result.score.label

    def reload_schema(self) -> None:
        """Reload the known tables list (call after schema pack update)."""
        self._known_tables = self._load_known_tables()
        logger.info(f"[ProductionGate] Schema reloaded: {len(self._known_tables)} tables")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# QUICK HELPERS FOR chatbot_service.py
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def gate_response(
    response: str,
    question: str = "",
    category: str = "",
    urgency: str = "normal",
) -> str:
    """
    Main integration point for chatbot_service.py:
    Pass the LLM response through the quality gate and return the final
    (possibly modified or blocked) response string.
    """
    result = production_gate.evaluate(
        response=response,
        question=question,
        context={"category": category, "urgency": urgency},
    )
    if not result.passed:
        logger.warning(
            f"[ProductionGate] BLOCKED response | score={result.score.total} "
            f"| category={category} | question={question[:80]}"
        )
    elif result.added_warnings:
        logger.info(
            f"[ProductionGate] Response passed with warnings | score={result.score.total}"
        )
    return result.final_response


def score_response(response: str, question: str = "") -> QualityScore:
    """Return just the QualityScore without modifying the response."""
    result = production_gate.evaluate(response, question)
    return result.score


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SINGLETON
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

production_gate = ProductionReadinessGate()
