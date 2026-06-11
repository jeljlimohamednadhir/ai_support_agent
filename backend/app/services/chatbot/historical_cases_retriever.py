"""
historical_cases_retriever.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Retrieves relevant historical N3 cases from the analyzed CSV knowledge base.
Provides correlation scoring with FR, Code, Jira, and historical frequency.

Design:
  - Deterministic keyword matching (no LLM)
  - Weighted scoring: FR=1.0, Code=1.0, Historical=0.9, Jira=0.7
  - Returns structured results for fusion with other knowledge sources
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Load historical cases at module level
_CASES_PATH = Path(__file__).resolve().parent.parent.parent.parent.parent / "data" / "historical_analysis" / "historical_cases.json"
_TRAINING_PATH = Path(__file__).resolve().parent.parent.parent.parent.parent / "data" / "historical_analysis" / "intent_training_set.json"

_HISTORICAL_CASES: List[Dict[str, Any]] = []
_INTENT_VARIANTS: Dict[str, Any] = {}

try:
    if _CASES_PATH.exists():
        _HISTORICAL_CASES = json.loads(_CASES_PATH.read_text(encoding="utf-8"))
        logger.info(f"[HistoricalCases] Loaded {len(_HISTORICAL_CASES)} cases from {_CASES_PATH}")
    if _TRAINING_PATH.exists():
        _INTENT_VARIANTS = json.loads(_TRAINING_PATH.read_text(encoding="utf-8"))
        logger.info(f"[HistoricalCases] Loaded {len(_INTENT_VARIANTS)} intent variant sets")
except Exception as e:
    logger.warning(f"[HistoricalCases] Failed to load: {e}")


# Scoring weights
WEIGHT_FR = 1.0
WEIGHT_CODE = 1.0
WEIGHT_HISTORICAL = 0.9
WEIGHT_JIRA = 0.7


def historical_cases_retriever(
    query: str,
    intent: Optional[str] = None,
    entity: Optional[str] = None,
    max_results: int = 3,
) -> List[Dict[str, Any]]:
    """
    Retrieve relevant historical N3 cases for a given query.
    
    Returns list of matching cases with scores and correlations.
    """
    if not _HISTORICAL_CASES:
        return []

    query_lower = query.lower()
    results: List[Tuple[float, Dict[str, Any]]] = []

    for case in _HISTORICAL_CASES:
        score = 0.0
        match_reasons = []

        # 1. Intent match (highest weight)
        if intent and case["intent"] == intent:
            score += 2.0
            match_reasons.append(f"intent_match:{intent}")

        # 2. Keyword overlap with examples
        example_text = " ".join(case.get("examples", [])).lower()
        query_words = set(re.findall(r"\b\w{4,}\b", query_lower))
        example_words = set(re.findall(r"\b\w{4,}\b", example_text))
        overlap = query_words & example_words
        if overlap:
            score += len(overlap) * 0.3
            match_reasons.append(f"keyword_overlap:{len(overlap)}")

        # 3. Entity match
        if entity:
            entity_low = entity.lower()
            if entity_low in example_text or entity_low in case["intent"]:
                score += 1.0
                match_reasons.append(f"entity_match:{entity}")

        # 4. Frequency bonus (more frequent = more reliable)
        freq = case.get("frequency", 1)
        score += min(freq * 0.05, 1.0)

        # 5. Direct keyword match in intent name
        intent_words = case["intent"].replace("_", " ").split()
        for iw in intent_words:
            if iw in query_lower:
                score += 0.5
                match_reasons.append(f"intent_keyword:{iw}")

        if score > 0.5:
            result = {
                "intent": case["intent"],
                "score": round(score, 2),
                "match_reasons": match_reasons,
                "frequency": freq,
                "confidence": case.get("confidence", 0.5),
                "root_causes": case.get("root_causes", [])[:3],
                "n3_actions": case.get("n3_actions", [])[:3],
                "related_fr": case.get("related_fr", []),
                "related_code": case.get("related_code", []),
                "related_tables": case.get("related_tables", []),
                "workflows": case.get("workflows", []),
            }
            results.append((score, result))

    # Sort by score descending
    results.sort(key=lambda x: -x[0])
    return [r[1] for r in results[:max_results]]


def compute_historical_case_score(
    query: str,
    intent: Optional[str] = None,
    entity: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Compute a weighted correlation score combining:
    - FR match (1.0)
    - Code match (1.0)
    - Historical case match (0.9)
    - Jira match (0.7)
    
    Returns dict with total_score, breakdown, and matched case.
    """
    cases = historical_cases_retriever(query, intent=intent, entity=entity, max_results=1)
    if not cases:
        return {"total_score": 0.0, "breakdown": {}, "matched_case": None}

    best = cases[0]
    breakdown = {
        "historical_score": round(best["score"] * WEIGHT_HISTORICAL, 2),
        "fr_score": round(len(best["related_fr"]) * WEIGHT_FR * 0.5, 2),
        "code_score": round(len(best["related_code"]) * WEIGHT_CODE * 0.5, 2),
        "jira_score": 0.0,  # Populated by Jira retriever externally
    }
    total = sum(breakdown.values())

    return {
        "total_score": round(total, 2),
        "breakdown": breakdown,
        "matched_case": best,
    }


def get_intent_variants(intent: str) -> List[str]:
    """Get all training variants for a given intent."""
    data = _INTENT_VARIANTS.get(intent, {})
    return data.get("variants", [])


def match_intent_from_query(query: str) -> Optional[str]:
    """Try to match query to a known intent using training variants."""
    query_lower = query.lower()
    best_intent = None
    best_score = 0

    for intent_name, data in _INTENT_VARIANTS.items():
        score = 0
        # Check canonical
        if data.get("canonical", "").lower() in query_lower:
            score += 3
        # Check variants
        for variant in data.get("variants", []):
            variant_words = set(re.findall(r"\b\w{4,}\b", variant.lower()))
            query_words = set(re.findall(r"\b\w{4,}\b", query_lower))
            overlap = variant_words & query_words
            if len(overlap) >= 2:
                score += len(overlap) * 0.2
        if score > best_score:
            best_score = score
            best_intent = intent_name

    return best_intent if best_score >= 1.0 else None
