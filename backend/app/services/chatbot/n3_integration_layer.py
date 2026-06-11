"""
n3_integration_layer.py
━━━━━━━━━━━━━━━━━━━━━━━
Surgical integration of dead N3 pipeline layers into the active chatbot_service.

This module activates:
  - Layer 5: correlation_engine (evidence ranking + hypothesis scoring)
  - Layer 6: validation_layer (anti-hallucination: entity/business/evidence)
  - Layer 7: response_generator (structured N3 response)
  - Layer 8: learning_loop (post-resolution pattern recording)

Feature flags control activation (all default ON):
  ENABLE_CORRELATION_ENGINE = True
  ENABLE_VALIDATION_LAYER = True
  ENABLE_RESPONSE_GENERATOR = True
  ENABLE_LEARNING_LOOP = True

Called from chatbot_service.py at specific integration points.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FEATURE FLAGS (env-based, default ON)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ENABLE_CORRELATION_ENGINE = os.getenv("ENABLE_CORRELATION_ENGINE", "1") == "1"
ENABLE_VALIDATION_LAYER = os.getenv("ENABLE_VALIDATION_LAYER", "1") == "1"
ENABLE_RESPONSE_GENERATOR = os.getenv("ENABLE_RESPONSE_GENERATOR", "1") == "1"
ENABLE_LEARNING_LOOP = os.getenv("ENABLE_LEARNING_LOOP", "1") == "1"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LAZY IMPORTS (avoid blocking startup)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_correlation_engine = None
_validation_layer = None
_response_generator = None
_learning_loop = None


def _get_correlation_engine():
    global _correlation_engine
    if _correlation_engine is None:
        try:
            from app.services.chatbot.correlation_engine import correlation_engine
            _correlation_engine = correlation_engine
            logger.info("[N3Integration] CorrelationEngine loaded")
        except Exception as e:
            logger.warning(f"[N3Integration] CorrelationEngine unavailable: {e}")
    return _correlation_engine


def _get_validation_layer():
    global _validation_layer
    if _validation_layer is None:
        try:
            from app.services.chatbot.validation_layer import validation_layer
            _validation_layer = validation_layer
            logger.info("[N3Integration] ValidationLayer loaded")
        except Exception as e:
            logger.warning(f"[N3Integration] ValidationLayer unavailable: {e}")
    return _validation_layer


def _get_response_generator():
    global _response_generator
    if _response_generator is None:
        try:
            from app.services.chatbot.response_generator import response_generator
            _response_generator = response_generator
            logger.info("[N3Integration] ResponseGenerator loaded")
        except Exception as e:
            logger.warning(f"[N3Integration] ResponseGenerator unavailable: {e}")
    return _response_generator


def _get_learning_loop():
    global _learning_loop
    if _learning_loop is None:
        try:
            from app.services.chatbot.learning_loop import learning_loop
            _learning_loop = learning_loop
            logger.info("[N3Integration] LearningLoop loaded")
        except Exception as e:
            logger.warning(f"[N3Integration] LearningLoop unavailable: {e}")
    return _learning_loop


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RESULT TYPES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class CorrelationResult:
    """Simplified result from the correlation engine for integration."""
    hypotheses_block: str = ""          # Formatted text for LLM prompt injection
    top_hypothesis: Optional[str] = ""  # Label of best hypothesis
    confidence: float = 0.0
    evidence_count: int = 0
    sfd_violations: List[str] = field(default_factory=list)
    raw_result: Any = None              # Original CorrelationResult object


@dataclass
class ValidationResult:
    """Simplified result from validation layer."""
    passed: bool = True
    tier: str = "HIGH"                  # HIGH / MEDIUM / LOW
    violations: List[str] = field(default_factory=list)
    safe_response: Optional[str] = None  # Replacement if blocked
    evidence_count: int = 0
    raw_result: Any = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# INTEGRATION POINT 1: PRE-LLM CORRELATION
# Called after retrieval + live diagnostics, before LLM call
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def correlate_evidence(
    query: str,
    context_blocks: List[Dict[str, Any]],
    live_db_evidence: List[Dict[str, Any]] = None,
    live_log_evidence: List[Dict[str, Any]] = None,
    jira_tickets: List[Dict[str, Any]] = None,
    intent: str = "",
    conv_state: Any = None,
) -> CorrelationResult:
    """
    Run the full Layer 5 correlation engine on all available evidence.

    Returns a CorrelationResult with:
      - hypotheses_block: formatted text to inject into LLM system prompt
      - confidence, evidence_count: for downstream decision-making
      - sfd_violations: any SFD constraint issues detected
    """
    if not ENABLE_CORRELATION_ENGINE:
        return CorrelationResult()

    engine = _get_correlation_engine()
    if engine is None:
        return CorrelationResult()

    try:
        # Partition context_blocks into source categories
        fr_blocks = []
        incident_blocks = []
        log_patterns = []
        for block in (context_blocks or []):
            if not isinstance(block, dict):
                continue
            src_type = str(block.get("source_type", "") or "").lower()
            if src_type in ("fr", "resolution_fiche", "canonical", "procedure"):
                fr_blocks.append(block)
            elif src_type in ("incident", "historical_cases", "jira"):
                incident_blocks.append(block)
            elif src_type in ("log", "live_log", "log_pattern"):
                log_patterns.append(block)
            else:
                # Default: treat as FR/KB content
                fr_blocks.append(block)

        # Add live evidence as log patterns
        for ev in (live_log_evidence or []):
            if isinstance(ev, dict):
                log_patterns.append(ev)

        # Build a minimal state object if conv_state is a real ConversationState
        state = conv_state

        result = engine.correlate(
            query=query,
            state=state,
            kb_blocks=fr_blocks,
            incident_blocks=incident_blocks,
            log_patterns=log_patterns,
            intent=intent,
        )

        # Build the injectable context block
        hypotheses_block = result.to_context_block() if result else ""
        top_hyp = result.top_hypothesis if result else None

        return CorrelationResult(
            hypotheses_block=hypotheses_block,
            top_hypothesis=top_hyp.label if top_hyp else None,
            confidence=result.confidence if result else 0.0,
            evidence_count=sum(len(h.evidence) for h in (result.hypotheses or [])),
            sfd_violations=result.sfd_violations if result else [],
            raw_result=result,
        )

    except Exception as e:
        logger.warning(f"[N3Integration][Correlation] Error (non-blocking): {e}")
        return CorrelationResult()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# INTEGRATION POINT 2: POST-LLM VALIDATION
# Called after LLM response, before sending to user
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def validate_response(
    response_text: str,
    query: str,
    intent: str = "",
    context_blocks: List[Dict[str, Any]] = None,
    correlation_confidence: float = 0.0,
    conv_state: Any = None,
) -> ValidationResult:
    """
    Run the full Layer 6 validation on the response before returning to user.

    Checks:
      - Entity validity (only known entities appear in response)
      - Business validity (SFD constraint compliance)
      - Evidence grounding (factual claims backed by sources)

    Returns ValidationResult with pass/fail and optional safe replacement.
    """
    if not ENABLE_VALIDATION_LAYER:
        return ValidationResult(passed=True)

    vl = _get_validation_layer()
    if vl is None:
        return ValidationResult(passed=True)

    try:
        # Build a minimal retrieved dict from context_blocks
        retrieved = {"fr": [], "canonical": [], "incidents": [], "logs": []}
        for block in (context_blocks or []):
            if not isinstance(block, dict):
                continue
            src = str(block.get("source_type", "") or "").lower()
            if src in ("fr", "resolution_fiche", "canonical"):
                retrieved["fr"].append(block)
            elif src in ("incident", "historical_cases"):
                retrieved["incidents"].append(block)

        result = vl.validate(
            response=response_text,
            state=conv_state,
            intent=intent,
            retrieved=retrieved,
            correlation_confidence=correlation_confidence,
        )

        violations = []
        safe_resp = None
        if hasattr(result, 'violations'):
            violations = [v.message for v in result.violations if hasattr(v, 'message')]
        if hasattr(result, 'safe_response') and not result.passed:
            safe_resp = result.safe_response

        return ValidationResult(
            passed=result.passed if hasattr(result, 'passed') else True,
            tier=result.tier if hasattr(result, 'tier') else "HIGH",
            violations=violations,
            safe_response=safe_resp,
            evidence_count=result.evidence_count if hasattr(result, 'evidence_count') else 0,
            raw_result=result,
        )

    except Exception as e:
        logger.warning(f"[N3Integration][Validation] Error (non-blocking): {e}")
        return ValidationResult(passed=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# INTEGRATION POINT 2b: RESPONSE GENERATOR (L7)
# Called after correlation, builds structured LLM context
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def build_structured_llm_context(
    query: str,
    intent: str,
    correlation_raw_result: Any = None,
    conv_state: Any = None,
) -> Optional[str]:
    """
    Use the ResponseGenerator to build a structured LLM context.
    This replaces raw KB dump with pre-computed diagnostic result.
    Returns the formatted context string for the LLM system prompt,
    or None if L7 is disabled/unavailable.
    """
    if not ENABLE_RESPONSE_GENERATOR:
        return None

    rg = _get_response_generator()
    if rg is None or correlation_raw_result is None:
        return None

    # L7 requires a valid ConversationState — skip if unavailable
    if conv_state is None:
        return None

    try:
        # Generate the structured response (deterministic, no LLM)
        structured = rg.generate(
            intent=intent,
            state=conv_state,
            correlation=correlation_raw_result,
            validation=None,
            mode="expert",
        )

        # Build the LLM formatter context (compact, <700 tokens)
        llm_context = rg.build_llm_context(
            intent=intent,
            state=conv_state,
            correlation=correlation_raw_result,
            user_text=query,
            structured_result=structured,
        )
        return llm_context
    except Exception as e:
        logger.debug(f"[N3Integration][L7] ResponseGenerator error: {e}")
        return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# INTEGRATION POINT 3: LEARNING LOOP RECORDING
# Called after response is finalized and sent to user
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def record_interaction(
    session_id: str,
    query: str,
    response: str,
    intent: str = "",
    entity: str = "",
    confidence: float = 0.0,
    evidence_count: int = 0,
    hypothesis: str = "",
    resolution_confirmed: bool = False,
    conv_state: Any = None,
) -> None:
    """
    Record the interaction into the learning loop for future pattern extraction.

    Called:
      - After every response (stores weak pattern candidates)
      - On resolution confirmation (stores successful patterns)
    """
    if not ENABLE_LEARNING_LOOP:
        return

    ll = _get_learning_loop()
    if ll is None:
        return

    try:
        if resolution_confirmed and conv_state is not None:
            ll.on_resolution_confirmed(
                state=conv_state,
                hypothesis_id=hypothesis,
                hypothesis_label=hypothesis,
                actions_taken=[],
                confidence=confidence,
            )
            logger.info(f"[N3Integration][Learning] Resolution confirmed: {hypothesis}")
        elif evidence_count > 0:
            # Store ALL interactions with evidence (weak + strong) for pattern extraction
            ll.store_weak_pattern_candidate(
                session_id=session_id,
                query=query,
                response=response,
                hypothesis_id=hypothesis or "unknown",
                entity_name=entity or "unknown",
                validation_score=confidence,
                evidence_count=evidence_count,
            )
    except Exception as e:
        logger.debug(f"[N3Integration][Learning] Record error: {e}")
