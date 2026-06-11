"""
api_facade.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Service facade wrapping existing N3 engines for
the external Operations API layer.

Design principles:
  - Never redesigns or modifies core engines.
  - Wraps existing engines: causal_rca, temporal_reasoning,
    sync_anomaly_detector, business_rule_engine,
    workflow_intelligence, live_diagnostics, KB retrieval.
  - Always returns structured dicts (no raw chain-of-thought).
  - Always appends runtime_capabilities to every result.
  - Never exposes internal prompts, reasoning traces, or LLM output.
  - Degrades gracefully when runtime unavailable.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Runtime capability snapshot
# ──────────────────────────────────────────────────────────────────────────────

def _get_runtime_capabilities() -> Dict[str, bool]:
    """Return current availability flags from live orchestrator (non-blocking)."""
    caps = {
        "ssh_available": False,
        "db_available": False,
        "logs_available": False,
        "mq_available": True,
    }
    try:
        from app.services.live_diagnostics import create_orchestrator_from_settings
        orch = create_orchestrator_from_settings()
        if orch:
            caps["db_available"] = getattr(orch, "_enable_db", False)
            caps["logs_available"] = getattr(orch, "_enable_log", False)
            caps["ssh_available"] = getattr(orch, "_enable_ssh", False)
    except Exception as _e:
        logger.debug(f"[ApiFacade] runtime caps unavailable: {_e}")
    return caps


# ──────────────────────────────────────────────────────────────────────────────
# Confidence threshold
# ──────────────────────────────────────────────────────────────────────────────

_MIN_ACTIONABLE_CONFIDENCE = 0.55


def _mode_from_confidence(confidence: float) -> str:
    if confidence >= _MIN_ACTIONABLE_CONFIDENCE:
        return "diagnostic"
    return "investigation"


def _safe_next_steps(steps: List[str], caps: Dict[str, bool]) -> List[str]:
    """Strip runtime-unsupported steps before returning to API caller."""
    ssh_tokens = ("ssh", "kill -9", "who -t", "ps -ft", "serveur dsm")
    log_tokens = ("log", "grep", "tomcat", "trace")
    db_tokens = ("select ", "update ", "delete ", "insert ", "t_", "sql")
    mq_tokens = ("mq", "broker", "dlq", "ack")
    out = []
    for s in steps:
        lower = s.lower()
        if not caps.get("ssh_available") and any(t in lower for t in ssh_tokens):
            continue
        if not caps.get("logs_available") and any(t in lower for t in log_tokens):
            continue
        if not caps.get("db_available") and any(t in lower for t in db_tokens):
            continue
        if not caps.get("mq_available") and any(t in lower for t in mq_tokens):
            continue
        out.append(s)
    return out


# ──────────────────────────────────────────────────────────────────────────────
# /diagnose
# ──────────────────────────────────────────────────────────────────────────────

def run_diagnose(
    question: str,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Run a quick operational diagnosis.
    Returns structured result with evidence, confidence, and runtime caps.
    """
    caps = _get_runtime_capabilities()
    context = context or {}
    entity = context.get("equipment_id") or context.get("nd")
    environment = context.get("environment", "BRASIL")
    intent = context.get("intent")

    evidence: List[Dict] = []
    next_steps: List[str] = []
    root_cause: Optional[str] = None
    confidence = 0.0
    diagnostic_text = "Données insuffisantes pour un diagnostic déterministe."
    workflow: Optional[str] = None
    limitations: List[str] = []

    # ── KB retrieval ─────────────────────────────────────────────────────────
    try:
        from app.services.orchestrator import intelligence_orchestrator
        import asyncio
        orch_res = asyncio.get_event_loop().run_until_complete(
            intelligence_orchestrator.process(
                app_id="brasil",
                query=question,
                top_k=3,
            )
        ) if not asyncio.get_event_loop().is_running() else {}

        kb_blocks = orch_res.get("context_blocks", []) or []
        if kb_blocks:
            top = kb_blocks[0]
            confidence = max(confidence, (top.get("trust_score") or 0) / 100)
            diagnostic_text = top.get("summary") or top.get("content", diagnostic_text)[:300]
            evidence.append({
                "source_type": "kb",
                "description": top.get("title", "KB result"),
                "confidence": confidence,
                "reference_id": top.get("fr_id") or top.get("id"),
            })
    except Exception as _e:
        logger.debug(f"[ApiFacade/diagnose] KB lookup failed: {_e}")
        limitations.append("Knowledge base indisponible — résultats partiels.")

    # ── Live diagnostics ─────────────────────────────────────────────────────
    if entity and (caps["db_available"] or caps["logs_available"]):
        try:
            from app.services.live_diagnostics import create_orchestrator_from_settings
            live_orch = create_orchestrator_from_settings()
            if live_orch:
                _resolved_intent = intent or "diagnose_equipment"
                bundle = live_orch.run(intent=_resolved_intent, entity=entity)
                conf = bundle.highest_confidence()
                if conf > confidence:
                    confidence = conf
                res_blocks = bundle.reasoning_trace.get("resolution_blocks", []) or []
                for rb in res_blocks:
                    if isinstance(rb, dict):
                        if not root_cause and rb.get("title"):
                            root_cause = rb["title"].replace("Résolution: ", "")
                        for step in rb.get("content", "").splitlines():
                            step = step.strip()
                            if step.startswith(("1.", "2.", "3.", "4.", "5.", "-")):
                                next_steps.append(step.lstrip("12345.- "))
                        workflow = rb.get("fr_id")
                        evidence.append({
                            "source_type": "live_db",
                            "description": rb.get("title", "Resolution block"),
                            "confidence": round(conf, 3),
                            "reference_id": rb.get("fr_id"),
                        })
        except Exception as _e:
            logger.debug(f"[ApiFacade/diagnose] live diag failed: {_e}")
            limitations.append("Diagnostic live indisponible — résultats partiels.")

    if not caps["ssh_available"]:
        limitations.append("Connexion SSH indisponible — procédures SSH non proposées.")
    if not caps["logs_available"]:
        limitations.append("Logs serveur indisponibles — analyse de logs ignorée.")

    next_steps = _safe_next_steps(next_steps[:6], caps)
    mode = _mode_from_confidence(confidence)
    if mode == "investigation":
        limitations.append("Confiance insuffisante — mode investigation activé.")

    return {
        "mode": mode,
        "diagnostic": diagnostic_text,
        "root_cause": root_cause,
        "confidence": round(confidence, 3),
        "evidence": evidence,
        "workflow": workflow,
        "limitations": limitations,
        "next_steps": next_steps,
        "runtime_capabilities": caps,
    }


# ──────────────────────────────────────────────────────────────────────────────
# /investigate
# ──────────────────────────────────────────────────────────────────────────────

def run_investigate(
    entity_type: str,
    entity_id: str,
    question: str,
) -> Dict[str, Any]:
    """
    Deep RCA investigation with timeline reconstruction.
    Wraps temporal_reasoning + causal_rca engines.
    """
    caps = _get_runtime_capabilities()
    timeline: List[Dict] = []
    rca_chain: List[Dict] = []
    anomalies: List[str] = []
    evidence: List[Dict] = []
    confidence = 0.0
    missing_info: List[str] = []
    limitations: List[str] = []
    next_steps: List[str] = []

    # ── Temporal reasoning ────────────────────────────────────────────────────
    try:
        from app.services.chatbot.temporal_reasoning import TemporalReasoningEngine
        tr = TemporalReasoningEngine()
        result = tr.analyze(raw_logs="", entity=entity_id, context={"intent": entity_type.lower()})
        confidence = max(confidence, result.confidence)
        for ev in result.timeline[:15]:
            timeline.append({
                "timestamp": ev.timestamp.isoformat() if ev.timestamp else None,
                "event_type": ev.event_type,
                "description": ev.description,
                "severity": ev.severity,
                "source": ev.source,
            })
        for loop in result.retry_loops:
            anomalies.append(
                f"Boucle retry: {loop.event_type} x{loop.occurrences}"
            )
        for gap in result.gaps:
            missing_info.append(gap.reason)
    except Exception as _e:
        logger.debug(f"[ApiFacade/investigate] temporal engine: {_e}")
        limitations.append("Moteur temporel indisponible.")

    # ── Causal RCA ────────────────────────────────────────────────────────────
    try:
        from app.services.chatbot.causal_rca import get_rca_engine
        rca = get_rca_engine()
        rca_res = rca.analyze(
            entity_name=entity_id,
            intent=entity_type.lower(),
            active_rule_ids=[],
            sync_anomaly_types=[],
            detected_exceptions=[],
            log_signals=[],
            db_status=None,
            active_services=0,
            active_links=0,
        )
        if rca_res.hypotheses:
            confidence = max(confidence, rca_res.top_hypothesis.confidence
                             if rca_res.top_hypothesis else confidence)
        for h in (rca_res.hypotheses or [])[:5]:
            rca_chain.append({
                "cause": h.root_cause_id,
                "confidence": round(h.confidence, 3),
                "evidence": getattr(h, "evidence", []),
                "description": getattr(h, "description", ""),
            })
            evidence.append({
                "source_type": "rca",
                "description": h.root_cause_id,
                "confidence": round(h.confidence, 3),
                "reference_id": None,
            })
    except Exception as _e:
        logger.debug(f"[ApiFacade/investigate] RCA engine: {_e}")
        limitations.append("Moteur RCA indisponible.")

    if confidence < _MIN_ACTIONABLE_CONFIDENCE:
        limitations.append("Confiance insuffisante — investigation en cours.")
        next_steps.append("Fournir les logs serveur pour affiner le diagnostic.")
        next_steps.append("Préciser le dernier état connu de l'entité.")

    mode = "investigation" if confidence < _MIN_ACTIONABLE_CONFIDENCE else "diagnostic"

    return {
        "mode": mode,
        "timeline": timeline,
        "rca_chain": rca_chain,
        "anomalies": anomalies,
        "evidence": evidence,
        "confidence": round(confidence, 3),
        "missing_information": missing_info,
        "limitations": limitations,
        "next_steps": next_steps,
        "runtime_capabilities": caps,
    }


# ──────────────────────────────────────────────────────────────────────────────
# /workflow
# ──────────────────────────────────────────────────────────────────────────────

_WORKFLOW_INTENT_MAP: Dict[str, str] = {
    "equipment_delete": "delete_equipment",
    "vlan_delete":      "delete_vlan",
    "tp_fix":           "fix_blocked_tp",
    "bas_delete":       "delete_bas",
    "operator_delete":  "delete_operator",
    "card_delete":      "delete_card",
}


def run_workflow(workflow_type: str, entity_id: str) -> Dict[str, Any]:
    """
    Workflow analysis and FSM state validation.
    Wraps workflow_intelligence + business_rule_engine.
    """
    caps = _get_runtime_capabilities()
    intent = _WORKFLOW_INTENT_MAP.get(workflow_type)
    blocking: List[str] = []
    business_rules: List[str] = []
    recommended: List[str] = []
    invalid_transitions: List[str] = []
    current_state: Optional[str] = None
    next_state: Optional[str] = None

    if not intent:
        return {
            "error": {
                "code": "WORKFLOW_UNKNOWN",
                "message": f"Workflow type '{workflow_type}' non reconnu.",
                "details": [f"Types valides: {', '.join(_WORKFLOW_INTENT_MAP)}"],
            }
        }

    # ── Business rule engine ─────────────────────────────────────────────────
    try:
        from app.services.chatbot.business_rule_engine import (
            get_business_rule_engine, EvidenceContext
        )
        bre = get_business_rule_engine()
        ev_ctx = EvidenceContext()
        bre_res = bre.evaluate(intent=intent, evidence=ev_ctx)
        for rule in bre_res.fired_rules:
            business_rules.append(rule.rule_id)
        if bre_res.blocked:
            blocking.append("Opération bloquée par règle métier.")
    except Exception as _e:
        logger.debug(f"[ApiFacade/workflow] BRE: {_e}")

    # ── Workflow intelligence ─────────────────────────────────────────────────
    try:
        from app.services.chatbot.workflow_intelligence import workflow_engine
        wf_text = workflow_engine.render_workflow_response(
            query=f"{workflow_type} {entity_id}",
            entity=entity_id,
        )
        if wf_text:
            for line in wf_text.splitlines():
                s = line.strip().lstrip("1234567890.-• ")
                if s and len(s) > 6:
                    recommended.append(s)
    except Exception as _e:
        logger.debug(f"[ApiFacade/workflow] workflow engine: {_e}")

    recommended = _safe_next_steps(recommended[:8], caps)

    return {
        "workflow": intent,
        "current_state": current_state,
        "expected_next_state": next_state,
        "invalid_transitions": invalid_transitions,
        "blocking_conditions": blocking,
        "business_rules_triggered": business_rules,
        "recommended_actions": recommended,
        "runtime_capabilities": caps,
    }


# ──────────────────────────────────────────────────────────────────────────────
# /validate
# ──────────────────────────────────────────────────────────────────────────────

def run_validate(
    hypothesis: str,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Validate an operational hypothesis using KB + causal graph.
    Never returns True unless supporting evidence is found.
    """
    caps = _get_runtime_capabilities()
    context = context or {}
    supporting: List[str] = []
    contradictions: List[str] = []
    missing: List[str] = []
    confidence = 0.0
    valid = False
    validation_mode = "deterministic"

    try:
        from app.services.chatbot.causal_rca import get_rca_engine
        rca = get_rca_engine()
        hypothesis_lower = hypothesis.lower()
        signals: List[str] = []
        for kw in ("mq", "ack", "constraint", "residual", "lock", "timeout", "blocked"):
            if kw in hypothesis_lower:
                signals.append(kw)

        rca_res = rca.analyze(
            entity_name=context.get("nd") or context.get("equipment_id") or "unknown",
            intent="validate_hypothesis",
            active_rule_ids=[],
            sync_anomaly_types=[],
            detected_exceptions=signals,
            log_signals=[hypothesis[:200]],
            db_status=None,
            active_services=0,
            active_links=0,
        )
        if rca_res.hypotheses:
            top = rca_res.top_hypothesis
            if top:
                confidence = round(top.confidence, 3)
                valid = confidence >= _MIN_ACTIONABLE_CONFIDENCE
                supporting.append(f"RCA: {top.root_cause_id} (conf={confidence})")
    except Exception as _e:
        logger.debug(f"[ApiFacade/validate] RCA: {_e}")
        validation_mode = "probabilistic"

    # ── KB cross-check ────────────────────────────────────────────────────────
    try:
        from app.services.knowledge.vector_service import vector_service
        import asyncio
        _loop = asyncio.new_event_loop()
        kb_res = _loop.run_until_complete(
            vector_service.search(hypothesis, top_k=3)
        ) if vector_service else []
        _loop.close()
        for r in (kb_res or [])[:2]:
            score = r.get("score", 0) if isinstance(r, dict) else getattr(r, "score", 0)
            title = r.get("title", "") if isinstance(r, dict) else getattr(r, "title", "")
            if score > 0.6:
                supporting.append(f"KB: {title} (score={score:.2f})")
                confidence = max(confidence, score)
    except Exception as _e:
        logger.debug(f"[ApiFacade/validate] KB: {_e}")
        missing.append("Base de connaissance non consultée.")

    if not supporting:
        missing.append("Aucune preuve disponible pour confirmer l'hypothèse.")
        valid = False

    return {
        "valid": valid,
        "confidence": round(confidence, 3),
        "supporting_evidence": supporting,
        "contradictions": contradictions,
        "missing_evidence": missing,
        "validation_mode": validation_mode,
        "runtime_capabilities": caps,
    }


# ──────────────────────────────────────────────────────────────────────────────
# /search
# ──────────────────────────────────────────────────────────────────────────────

def run_search(
    query: str,
    top_k: int = 5,
    source_types: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Search the FR/KB operational knowledge base.
    Returns relevance-ranked structured results only.
    """
    caps = _get_runtime_capabilities()
    results: List[Dict] = []

    try:
        from app.services.orchestrator import intelligence_orchestrator
        import asyncio
        _loop = asyncio.new_event_loop()
        orch_res = _loop.run_until_complete(
            intelligence_orchestrator.process(
                app_id="brasil",
                query=query,
                top_k=top_k,
            )
        )
        _loop.close()
        for blk in (orch_res.get("context_blocks") or [])[:top_k]:
            src_type = blk.get("source_type", "kb")
            if source_types and src_type not in source_types:
                continue
            results.append({
                "source_type": src_type,
                "title": blk.get("title", ""),
                "relevance": (blk.get("trust_score") or 0) / 100,
                "summary": (blk.get("content") or blk.get("summary") or "")[:300],
                "reference_id": blk.get("fr_id") or blk.get("id"),
            })
    except Exception as _e:
        logger.debug(f"[ApiFacade/search] orchestrator: {_e}")

    return {
        "results": results,
        "total": len(results),
        "runtime_capabilities": caps,
    }
