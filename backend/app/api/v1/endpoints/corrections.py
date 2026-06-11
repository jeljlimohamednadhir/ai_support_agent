"""
POST /corrections — Human Correction Endpoint
===============================================
Allows N3 operators to submit corrections for LOW/MEDIUM-tier chatbot responses.

Each submitted correction:
  1. Stores the corrected response in data/learning/corrections.json
  2. Calls incident_graph.reinforce() or suppress() to shift future rankings
  3. If corrected_root_cause / corrected_actions are provided,
     stores a new LearnedPattern as high-confidence evidence for future retrieval

Correction types:
  "reinforce" — the hypothesis was CORRECT; operator adds better phrasing / actions
  "suppress"  — the hypothesis was WRONG;  operator provides the real root cause

GET /corrections/stats  — returns aggregated correction statistics (internal only)
GET /corrections/suppressed — returns currently suppressed hypotheses
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.chatbot.learning_loop import learning_loop, HumanCorrection

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response models
# ─────────────────────────────────────────────────────────────────────────────

class CorrectionRequest(BaseModel):
    query: str = Field(..., description="Original user query that triggered the response")
    original_response: str = Field(..., description="Chatbot's response that was wrong or incomplete")
    corrected_response: str = Field(..., description="Operator's corrected response")
    entity_name: str = Field(..., description="Equipment/entity name (e.g. DSLAM222)")
    entity_type: str = Field(default="UNKNOWN", description="Entity type (DSLAM, CARD, PORT, …)")
    hypothesis_id: str = Field(..., description="Hypothesis ID that was active (HYP-001 … HYP-012)")
    correction_type: str = Field(
        ...,
        description="'reinforce' — hypothesis was correct | 'suppress' — hypothesis was wrong",
    )
    corrected_root_cause: str = Field(default="", description="Optional: operator's identified root cause")
    corrected_actions: List[str] = Field(
        default_factory=list,
        description="Optional: list of correct SQL/procedure actions",
    )
    operator_id: str = Field(default="n3_operator", description="Operator identifier")


class CorrectionResponse(BaseModel):
    id: str
    created_at: str
    hypothesis_id: str
    correction_type: str
    entity_name: str
    applied: bool
    message: str


class CorrectionStats(BaseModel):
    total: int
    reinforce: int
    suppress: int


class SuppressedHypothesis(BaseModel):
    hypothesis_id: str
    suppression_delta: float
    description: str


class PatternInsight(BaseModel):
    hypothesis_id: str
    description: str
    appeared_count: int
    confirmed_count: int
    rejected_count: int
    success_rate: float
    confidence_score: float
    trend: str   # "up" | "down" | "stable" | "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# Hypothesis catalog for description lookup
# ─────────────────────────────────────────────────────────────────────────────

_HYP_LABELS = {
    "HYP-001": "DSLAM fermé à la production",
    "HYP-002": "Aucun port disponible (TOC 100%)",
    "HYP-003": "Carte fermée à la production",
    "HYP-004": "MRT introuvable ou inconnu",
    "HYP-005": "Problème de making file / NIFolderID manquant",
    "HYP-006": "Validation CEV échouée",
    "HYP-007": "Deadlock transactionnel PostgreSQL",
    "HYP-008": "Compteurs VP/VC/VLAN incohérents",
    "HYP-009": "Équipement bloqué en état IN_PROGRESS",
    "HYP-010": "Suppression d'équipement bloquée (dépendances)",
    "HYP-011": "Nœud non importé du Référentiel Sites",
    "HYP-012": "TSF non provisionné",
}


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=CorrectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a human correction for a chatbot response",
)
async def submit_correction(req: CorrectionRequest) -> CorrectionResponse:
    """
    Submit a human correction.

    - **correction_type = "reinforce"**: hypothesis was correct; boost its graph weight
    - **correction_type = "suppress"**: hypothesis was wrong; reduce its graph weight + store correct pattern
    """
    if req.correction_type not in ("reinforce", "suppress"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="correction_type must be 'reinforce' or 'suppress'",
        )

    correction: HumanCorrection = learning_loop.apply_correction(
        query=req.query,
        original_response=req.original_response,
        corrected_response=req.corrected_response,
        entity_name=req.entity_name,
        entity_type=req.entity_type,
        hypothesis_id=req.hypothesis_id,
        correction_type=req.correction_type,
        corrected_root_cause=req.corrected_root_cause,
        corrected_actions=req.corrected_actions,
        operator_id=req.operator_id,
    )

    action_verb = "Reinforced" if req.correction_type == "reinforce" else "Suppressed"
    hyp_label = _HYP_LABELS.get(req.hypothesis_id, req.hypothesis_id)

    return CorrectionResponse(
        id=correction.id,
        created_at=correction.created_at,
        hypothesis_id=req.hypothesis_id,
        correction_type=req.correction_type,
        entity_name=req.entity_name,
        applied=correction.applied,
        message=f"{action_verb} hypothesis [{req.hypothesis_id}] '{hyp_label}' for entity {req.entity_name}",
    )


@router.get(
    "/stats",
    response_model=CorrectionStats,
    summary="Get correction statistics (internal)",
)
async def get_correction_stats() -> CorrectionStats:
    """Return aggregated counts of reinforce vs suppress corrections + tier distribution."""
    from app.services.chatbot.maintenance import _compute_tier_distribution
    import json
    from pathlib import Path

    stats = learning_loop.get_correction_stats()

    # Augment with tier distribution (from hypothesis stats)
    tier_dist = _compute_tier_distribution()
    stats["tier_distribution"] = {
        "HIGH":   tier_dist.get("HIGH", 0),
        "MEDIUM": tier_dist.get("MEDIUM", 0),
        "LOW":    tier_dist.get("LOW", 0),
    }

    # Count corrections created today
    today_str = datetime.now(tz=timezone.utc).date().isoformat()
    corr_file = Path(__file__).parents[4] / "data" / "learning" / "corrections.json"
    today_count = 0
    if corr_file.exists():
        try:
            data = json.loads(corr_file.read_text(encoding="utf-8"))
            today_count = sum(
                1 for c in data.get("corrections", [])
                if c.get("created_at", "")[:10] == today_str
            )
        except Exception:
            pass
    stats["today_count"] = today_count

    return CorrectionStats(**stats)


@router.get(
    "/pattern-insight/{hypothesis_id}",
    response_model=PatternInsight,
    summary="Get pattern usage insight for a hypothesis",
)
async def get_pattern_insight(hypothesis_id: str) -> PatternInsight:
    """
    Return Pattern Insight for a specific hypothesis:
    - How many times it appeared
    - How many confirmations vs rejections
    - Confidence trend (up/down/stable)
    """
    all_stats = learning_loop.get_all_hypothesis_stats()
    h = all_stats.get(hypothesis_id)

    appeared = h.visit_count if h else 0
    confirmed = h.success_count if h else 0
    rejected = h.failure_count if h else 0
    success_rate = h.success_rate if h else 0.5
    confidence_score = h.confidence_score if h else 0.5

    # Determine trend from drift_log or simply from ratio
    trend = "unknown"
    if h and (confirmed + rejected) >= 4:
        # Simple heuristic: last 2 outcomes via success_rate vs prior
        prior = (confirmed - 1) / max(1, confirmed + rejected - 1)  # laplace-like
        if success_rate > prior + 0.05:
            trend = "up"
        elif success_rate < prior - 0.05:
            trend = "down"
        else:
            trend = "stable"
    elif h and (confirmed + rejected) >= 1:
        trend = "up" if success_rate >= 0.6 else "down"

    return PatternInsight(
        hypothesis_id=hypothesis_id,
        description=_HYP_LABELS.get(hypothesis_id, "Hypothèse inconnue"),
        appeared_count=appeared,
        confirmed_count=confirmed,
        rejected_count=rejected,
        success_rate=round(success_rate, 3),
        confidence_score=round(confidence_score, 3),
        trend=trend,
    )


@router.post(
    "/maintenance",
    summary="Run daily maintenance (admin only)",
    response_model=Dict[str, Any],
)
async def run_maintenance(dry_run: bool = False) -> Dict[str, Any]:
    """
    Trigger the auto-calibration maintenance loop manually.
    Performs: pattern decay, confidence recompute, bug-pattern suppression,
    graph weight rebalancing, storage compaction, weak pattern promotion, drift detection.
    """
    from app.services.chatbot.maintenance import run_daily_maintenance
    return run_daily_maintenance(dry_run=dry_run)


@router.get(
    "/suppressed",
    response_model=List[SuppressedHypothesis],
    summary="List currently suppressed hypotheses",
)
async def get_suppressed_hypotheses(threshold: int = 3) -> List[SuppressedHypothesis]:
    """
    Return hypotheses suppressed due to repeated failures or corrections.
    threshold: minimum number of bug reports + suppress corrections to trigger suppression.
    """
    suppressed = learning_loop.get_suppressed_hypotheses(threshold=threshold)
    return [
        SuppressedHypothesis(
            hypothesis_id=hyp_id,
            suppression_delta=delta,
            description=_HYP_LABELS.get(hyp_id, "Unknown hypothesis"),
        )
        for hyp_id, delta in sorted(suppressed.items(), key=lambda x: x[1])
    ]
