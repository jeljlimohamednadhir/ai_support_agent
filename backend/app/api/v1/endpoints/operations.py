"""
operations.py — External Operations API
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
5 endpoints exposing N3 intelligence to web UIs, dashboards,
NOC tools, and messaging integrations (Teams / Slack).

POST /operations/diagnose
POST /operations/investigate
POST /operations/workflow
POST /operations/validate
POST /operations/search
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from app.core.auth import get_current_active_user
from app.schemas.api_v1 import (
    DiagnoseRequest,
    DiagnoseResponse,
    EvidenceItem,
    ErrorResponse,
    InvestigateRequest,
    InvestigateResponse,
    RCAHop,
    RuntimeCapabilities,
    SearchRequest,
    SearchResponse,
    SearchResult,
    TimelineEvent,
    ValidateRequest,
    ValidateResponse,
    WorkflowRequest,
    WorkflowResponse,
)
from app.services import api_facade

logger = logging.getLogger(__name__)

router = APIRouter()


# ─────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────

def _build_runtime_caps(raw: Dict[str, bool]) -> RuntimeCapabilities:
    return RuntimeCapabilities(
        ssh_available=raw.get("ssh_available", False),
        db_available=raw.get("db_available", False),
        logs_available=raw.get("logs_available", False),
        mq_available=raw.get("mq_available", True),
    )


def _build_evidence(raw: List[Dict]) -> List[EvidenceItem]:
    out = []
    for r in raw or []:
        try:
            out.append(EvidenceItem(**r))
        except Exception:
            pass
    return out


def _handle_facade_error(endpoint: str, exc: Exception) -> None:
    logger.error(f"[{endpoint}] unexpected error: {exc}", exc_info=True)
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=ErrorResponse(
            code="ENGINE_ERROR",
            message="Erreur moteur interne — réessayez ultérieurement.",
            details=[str(exc)],
        ).model_dump(),
    )


# ─────────────────────────────────────────────────────────────
# POST /diagnose
# ─────────────────────────────────────────────────────────────

@router.post(
    "/diagnose",
    response_model=DiagnoseResponse,
    summary="Diagnostic opérationnel rapide",
    description=(
        "Exécute un diagnostic deterministe basé sur la KB et les moteurs live. "
        "Retourne cause racine, preuves, étapes suivantes et capacités runtime."
    ),
    responses={
        200: {"model": DiagnoseResponse},
        422: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def diagnose(
    body: DiagnoseRequest,
    _current_user: Any = Depends(get_current_active_user),
) -> DiagnoseResponse:
    try:
        res = api_facade.run_diagnose(
            question=body.question,
            context=body.context,
        )
    except Exception as exc:
        _handle_facade_error("diagnose", exc)

    if "error" in res:
        err = res["error"]
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=ErrorResponse(
                code=err.get("code", "DIAGNOSE_ERROR"),
                message=err.get("message", "Erreur diagnostic."),
                details=err.get("details", []),
            ).model_dump(),
        )

    return DiagnoseResponse(
        mode=res["mode"],
        diagnostic=res["diagnostic"],
        root_cause=res.get("root_cause"),
        confidence=res["confidence"],
        evidence=_build_evidence(res.get("evidence", [])),
        workflow=res.get("workflow"),
        limitations=res.get("limitations", []),
        next_steps=res.get("next_steps", []),
        runtime_capabilities=_build_runtime_caps(res["runtime_capabilities"]),
    )


# ─────────────────────────────────────────────────────────────
# POST /investigate
# ─────────────────────────────────────────────────────────────

@router.post(
    "/investigate",
    response_model=InvestigateResponse,
    summary="Investigation RCA profonde",
    description=(
        "RCA détaillée avec reconstruction de timeline. "
        "Utilise le moteur temporel et le graphe causal."
    ),
    responses={
        200: {"model": InvestigateResponse},
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def investigate(
    body: InvestigateRequest,
    _current_user: Any = Depends(get_current_active_user),
) -> InvestigateResponse:
    try:
        res = api_facade.run_investigate(
            entity_type=body.entity_type,
            entity_id=body.entity_id,
            question=body.question,
        )
    except Exception as exc:
        _handle_facade_error("investigate", exc)

    if "error" in res:
        err = res["error"]
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                code=err.get("code", "ENTITY_NOT_FOUND"),
                message=err.get("message", "Entité non trouvée."),
                details=err.get("details", []),
            ).model_dump(),
        )

    timeline = [
        TimelineEvent(**ev)
        for ev in (res.get("timeline") or [])
        if ev.get("timestamp")
    ]
    rca_chain = [
        RCAHop(
            cause=hop["cause"],
            confidence=hop["confidence"],
            evidence=hop.get("evidence", []),
            description=hop.get("description"),
        )
        for hop in (res.get("rca_chain") or [])
    ]

    return InvestigateResponse(
        mode=res["mode"],
        timeline=timeline,
        rca_chain=rca_chain,
        anomalies=res.get("anomalies", []),
        evidence=_build_evidence(res.get("evidence", [])),
        confidence=res["confidence"],
        missing_information=res.get("missing_information", []),
        limitations=res.get("limitations", []),
        next_steps=res.get("next_steps", []),
        runtime_capabilities=_build_runtime_caps(res["runtime_capabilities"]),
    )


# ─────────────────────────────────────────────────────────────
# POST /workflow
# ─────────────────────────────────────────────────────────────

@router.post(
    "/workflow",
    response_model=WorkflowResponse,
    summary="Analyse de workflow et FSM",
    description=(
        "Analyse un workflow opérationnel: transitions FSM, règles métier, "
        "conditions bloquantes et actions recommandées."
    ),
    responses={
        200: {"model": WorkflowResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def workflow(
    body: WorkflowRequest,
    _current_user: Any = Depends(get_current_active_user),
) -> WorkflowResponse:
    try:
        res = api_facade.run_workflow(
            workflow_type=body.workflow_type,
            entity_id=body.entity_id,
        )
    except Exception as exc:
        _handle_facade_error("workflow", exc)

    if "error" in res:
        err = res["error"]
        code = err.get("code", "WORKFLOW_ERROR")
        http_code = (
            status.HTTP_422_UNPROCESSABLE_ENTITY
            if code == "WORKFLOW_UNKNOWN"
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(
            status_code=http_code,
            detail=ErrorResponse(
                code=code,
                message=err.get("message", "Erreur workflow."),
                details=err.get("details", []),
            ).model_dump(),
        )

    return WorkflowResponse(
        workflow=res["workflow"],
        current_state=res.get("current_state"),
        expected_next_state=res.get("expected_next_state"),
        invalid_transitions=res.get("invalid_transitions", []),
        blocking_conditions=res.get("blocking_conditions", []),
        business_rules_triggered=res.get("business_rules_triggered", []),
        recommended_actions=res.get("recommended_actions", []),
        runtime_capabilities=_build_runtime_caps(res["runtime_capabilities"]),
    )


# ─────────────────────────────────────────────────────────────
# POST /validate
# ─────────────────────────────────────────────────────────────

@router.post(
    "/validate",
    response_model=ValidateResponse,
    summary="Validation d'hypothèse opérationnelle",
    description=(
        "Valide une hypothèse via KB + graphe causal. "
        "Ne retourne valid=true que si des preuves concrètes sont trouvées."
    ),
    responses={
        200: {"model": ValidateResponse},
        503: {"model": ErrorResponse},
    },
)
async def validate(
    body: ValidateRequest,
    _current_user: Any = Depends(get_current_active_user),
) -> ValidateResponse:
    try:
        res = api_facade.run_validate(
            hypothesis=body.hypothesis,
            context=body.context,
        )
    except Exception as exc:
        _handle_facade_error("validate", exc)

    return ValidateResponse(
        valid=res["valid"],
        confidence=res["confidence"],
        supporting_evidence=res.get("supporting_evidence", []),
        contradictions=res.get("contradictions", []),
        missing_evidence=res.get("missing_evidence", []),
        validation_mode=res.get("validation_mode", "deterministic"),
        runtime_capabilities=_build_runtime_caps(res["runtime_capabilities"]),
    )


# ─────────────────────────────────────────────────────────────
# POST /search
# ─────────────────────────────────────────────────────────────

@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Recherche dans la KB opérationnelle",
    description=(
        "Recherche sémantique dans la base de connaissances FR/N3. "
        "Retourne les résultats classés par pertinence."
    ),
    responses={
        200: {"model": SearchResponse},
        503: {"model": ErrorResponse},
    },
)
async def search(
    body: SearchRequest,
    _current_user: Any = Depends(get_current_active_user),
) -> SearchResponse:
    try:
        res = api_facade.run_search(
            query=body.query,
            top_k=body.top_k,
            source_types=body.source_types,
        )
    except Exception as exc:
        _handle_facade_error("search", exc)

    results = [
        SearchResult(**r)
        for r in (res.get("results") or [])
    ]

    return SearchResponse(
        results=results,
        total=res["total"],
        runtime_capabilities=_build_runtime_caps(res["runtime_capabilities"]),
    )
