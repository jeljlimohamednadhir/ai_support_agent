"""
TrustEngine — Calcul du score de confiance selon la source et le contexte
Logique centrale qui détermine la force d'un diagnostic
"""
from typing import List, Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass

from app.core.logging import get_logger

logger = get_logger(__name__)


class TrustLabel(str, Enum):
    STRONG = "strong"           # Score >= threshold_strong  → diagnostic ferme
    MODERATE = "moderate"       # Score >= threshold_medium  → diagnostic prudent
    WEAK = "weak"               # Score < threshold_medium   → hypothèse seulement
    INSUFFICIENT = "insufficient"  # Pas assez de données


@dataclass
class TrustScore:
    score: int                   # 0-100
    label: TrustLabel
    breakdown: Dict[str, int]    # Détail des points par facteur
    explanation: str
    can_diagnose: bool
    can_recommend: bool


class TrustEngine:
    """
    Moteur de calcul de confiance multi-sources.

    Règles de scoring :
    ─────────────────────────────────────────────
    SOURCE                          POINTS MAX
    ─────────────────────────────────────────────
    Canonical procedure (high)        +40
    Canonical procedure (medium)      +25
    Cluster validé                    +20
    Fréquence historique > 50         +20
    Fréquence historique > 10         +10
    Signature exacte (Mode 3)         +40
    Logs cohérents                    +20
    Stack trace stable                +20
    Ticket brut seul                  +10
    ─────────────────────────────────────────────
    """

    def __init__(
        self,
        threshold_strong: int = 70,
        threshold_medium: int = 40
    ):
        self.threshold_strong = threshold_strong
        self.threshold_medium = threshold_medium

    # ─────────────────────────────────────────────
    # API Publique
    # ─────────────────────────────────────────────

    def score_canonical_match(
        self,
        trust_level: str,          # "high" | "medium" | "low"
        match_score: float,        # 0.0–1.0 similarité sémantique
        usage_count: int = 0,
        success_count: int = 0,
    ) -> TrustScore:
        """Score pour un match sur une CanonicalProcedure (Mode 1 & 2)"""
        breakdown: Dict[str, int] = {}

        # Base selon trust_level de la procédure
        if trust_level == "high":
            breakdown["canonical_trust_high"] = 40
        elif trust_level == "medium":
            breakdown["canonical_trust_medium"] = 25
        else:
            breakdown["canonical_trust_low"] = 10

        # Bonus selon la similarité sémantique
        if match_score >= 0.9:
            breakdown["semantic_match_excellent"] = 20
        elif match_score >= 0.75:
            breakdown["semantic_match_good"] = 12
        elif match_score >= 0.6:
            breakdown["semantic_match_partial"] = 6

        # Bonus usage historique
        if usage_count > 50 and success_count > 0:
            success_rate = success_count / usage_count
            if success_rate > 0.7:
                breakdown["usage_proven"] = 10

        total = sum(breakdown.values())
        return self._build_result(total, breakdown, "canonical_procedure")

    def score_signature_match(
        self,
        exact_match: bool,
        frequency: int,
        logs_coherent: bool,
        stack_trace_stable: bool,
        cluster_confidence: Optional[float] = None,
    ) -> TrustScore:
        """Score pour un match sur ErrorSignature (Mode 3)"""
        breakdown: Dict[str, int] = {}

        # Signature exacte
        if exact_match:
            breakdown["signature_exact_match"] = 40
        else:
            breakdown["signature_partial_match"] = 15

        # Fréquence historique
        if frequency >= 50:
            breakdown["frequency_high"] = 20
        elif frequency >= 10:
            breakdown["frequency_medium"] = 10
        elif frequency >= 3:
            breakdown["frequency_low"] = 5

        # Cohérence des logs
        if logs_coherent:
            breakdown["logs_coherent"] = 20

        # Stack trace stable (reproductible)
        if stack_trace_stable:
            breakdown["stack_trace_stable"] = 20

        # Bonus cluster
        if cluster_confidence is not None and cluster_confidence >= 0.75:
            breakdown["cluster_confidence_bonus"] = 10

        total = sum(breakdown.values())
        return self._build_result(total, breakdown, "error_signature")

    def score_raw_ticket(
        self,
        ticket_count: int,
        has_resolution: bool,
        keyword_match_count: int,
    ) -> TrustScore:
        """Score minimal pour ticket brut non structuré (Mode 2 fallback)"""
        breakdown: Dict[str, int] = {}

        if ticket_count >= 20:
            breakdown["ticket_count_high"] = 15
        elif ticket_count >= 5:
            breakdown["ticket_count_medium"] = 8
        else:
            breakdown["ticket_count_low"] = 3

        if has_resolution:
            breakdown["has_resolution"] = 10

        breakdown["keyword_match"] = min(keyword_match_count * 2, 10)

        total = sum(breakdown.values())
        return self._build_result(total, breakdown, "raw_ticket")

    def score_combined(self, scores: List[TrustScore]) -> TrustScore:
        """
        Combine plusieurs scores (ex: canonical + signature).
        Prend le max + 20% des autres (pour éviter double-comptage).
        """
        if not scores:
            return TrustScore(
                score=0,
                label=TrustLabel.INSUFFICIENT,
                breakdown={},
                explanation="Aucune source disponible",
                can_diagnose=False,
                can_recommend=False,
            )

        sorted_scores = sorted(scores, key=lambda s: s.score, reverse=True)
        best = sorted_scores[0]
        bonus = sum(int(s.score * 0.2) for s in sorted_scores[1:])
        total = min(best.score + bonus, 100)

        combined_breakdown = {**best.breakdown}
        for i, s in enumerate(sorted_scores[1:], 1):
            for k, v in s.breakdown.items():
                combined_breakdown[f"source_{i}_{k}"] = int(v * 0.2)

        return self._build_result(total, combined_breakdown, "combined")

    # ─────────────────────────────────────────────
    # Privé
    # ─────────────────────────────────────────────

    def _build_result(
        self,
        total: int,
        breakdown: Dict[str, int],
        source_type: str,
    ) -> TrustScore:
        total = min(total, 100)

        if total >= self.threshold_strong:
            label = TrustLabel.STRONG
            explanation = f"Diagnostic fiable ({total}/100) — basé sur {source_type}"
            can_diagnose = True
            can_recommend = True
        elif total >= self.threshold_medium:
            label = TrustLabel.MODERATE
            explanation = f"Diagnostic probable ({total}/100) — basé sur {source_type}, à vérifier"
            can_diagnose = True
            can_recommend = True
        elif total > 0:
            label = TrustLabel.WEAK
            explanation = f"Hypothèse faible ({total}/100) — données insuffisantes pour {source_type}"
            can_diagnose = False
            can_recommend = True
        else:
            label = TrustLabel.INSUFFICIENT
            explanation = "Données insuffisantes pour établir un diagnostic"
            can_diagnose = False
            can_recommend = False

        return TrustScore(
            score=total,
            label=label,
            breakdown=breakdown,
            explanation=explanation,
            can_diagnose=can_diagnose,
            can_recommend=can_recommend,
        )


    def score_knowledge_document(
        self,
        source_type: str,
        quality_score: float = 0.0,
        is_human_validated: bool = False,
        has_symptoms: bool = False,
        has_root_cause: bool = False,
        has_steps: bool = False,
        cluster_size: int = 0,
        age_months: float = 0.0,
    ) -> TrustScore:
        """
        Full trust scoring formula for knowledge pipeline documents.

        Formula:
          T = w1*S_source + w2*S_completeness + w3*S_validation + w4*S_recency
          w1=0.40, w2=0.25, w3=0.25, w4=0.10

        Source types and their base scores:
          human_validated_fr  → 1.00
          fr_unvalidated      → 0.75
          jira_resolved       → 0.70
          jira_open           → 0.50
          cluster_large (≥20) → 0.65
          cluster_medium(5-19)→ 0.50
          single_ticket       → 0.30
          llm_generated       → 0.20
        """
        import math
        breakdown: Dict[str, int] = {}

        # S_source (0.0–1.0)
        source_scores = {
            "human_validated_fr": 1.00,
            "fr_unvalidated":     0.75,
            "jira_resolved":      0.70,
            "jira_open":          0.50,
            "cluster_large":      0.65,
            "cluster_medium":     0.50,
            "single_ticket":      0.30,
            "llm_generated":      0.20,
        }
        # Auto-map cluster size
        if source_type == "cluster":
            source_type = "cluster_large" if cluster_size >= 20 else "cluster_medium"
        s_source = source_scores.get(source_type, 0.30)

        # S_completeness (0.0–1.0)
        completeness = sum([has_symptoms, has_root_cause, has_steps]) / 3.0
        if quality_score > 0:
            completeness = max(completeness, quality_score / 100.0)

        # S_validation (0.0–1.0)
        s_validation = 1.0 if is_human_validated else 0.0

        # S_recency: exponential decay, lambda=0.05 per month
        lambda_decay = 0.05
        s_recency = math.exp(-lambda_decay * age_months)

        # Weighted sum → 0.0–1.0 → scale to 0–100
        trust_float = (
            0.40 * s_source
            + 0.25 * completeness
            + 0.25 * s_validation
            + 0.10 * s_recency
        )
        total = int(trust_float * 100)

        breakdown["source_score"] = int(0.40 * s_source * 100)
        breakdown["completeness"] = int(0.25 * completeness * 100)
        breakdown["validation"] = int(0.25 * s_validation * 100)
        breakdown["recency"] = int(0.10 * s_recency * 100)

        return self._build_result(total, breakdown, source_type)


# Singleton global
trust_engine = TrustEngine()
