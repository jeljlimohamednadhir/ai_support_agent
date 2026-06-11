"""
api_v1.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Pydantic request/response schemas for the
external Operations API (v1).

All response models:
  - return structured JSON only
  - never expose internal prompts / CoT
  - always expose runtime_capabilities
  - always expose evidence / confidence / limitations
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# Shared types
# ─────────────────────────────────────────────────────────────────────────────

class RuntimeCapabilities(BaseModel):
    ssh_available: bool = Field(False, description="SSH connectivity to production servers")
    db_available: bool = Field(False, description="Direct DB query availability")
    logs_available: bool = Field(False, description="Live log access availability")
    mq_available: bool = Field(True, description="Message queue observability")


class EvidenceItem(BaseModel):
    source_type: str = Field(..., description="live_db | live_log | ssh | kb | rca")
    description: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    reference_id: Optional[str] = None


class ErrorDetail(BaseModel):
    code: str = Field(..., description="LOW_EVIDENCE | ENTITY_NOT_FOUND | WORKFLOW_UNKNOWN | "
                                       "RUNTIME_UNAVAILABLE | VALIDATION_FAILED | "
                                       "RCA_INCONCLUSIVE | ACCESS_DENIED")
    message: str
    details: List[str] = []


class ErrorResponse(BaseModel):
    error: ErrorDetail


class ValidationMode(str, Enum):
    deterministic = "deterministic"
    probabilistic = "probabilistic"
    investigation = "investigation"


class ResponseMode(str, Enum):
    diagnostic = "diagnostic"
    investigation = "investigation"
    clarification = "clarification"
    limited_visibility = "limited_visibility"


# ─────────────────────────────────────────────────────────────────────────────
# POST /diagnose
# ─────────────────────────────────────────────────────────────────────────────

class DiagnoseContext(BaseModel):
    equipment_id: Optional[str] = None
    nd: Optional[str] = None
    environment: Optional[str] = None
    intent: Optional[str] = None
    extra: Dict[str, Any] = {}


class DiagnoseRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    context: Optional[DiagnoseContext] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "question": "Suppression équipement erreur 1300",
                "context": {
                    "equipment_id": "OP49MAB11",
                    "environment": "BRASIL"
                }
            }
        }
    }


class DiagnoseResponse(BaseModel):
    mode: ResponseMode
    diagnostic: str
    root_cause: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence: List[EvidenceItem] = []
    workflow: Optional[str] = None
    limitations: List[str] = []
    next_steps: List[str] = []
    runtime_capabilities: RuntimeCapabilities


# ─────────────────────────────────────────────────────────────────────────────
# POST /investigate
# ─────────────────────────────────────────────────────────────────────────────

class InvestigateEntity(BaseModel):
    type: str = Field(..., description="ND | EQUIPMENT | VLAN | TP | BAS | EPC")
    id: str


class TimelineEvent(BaseModel):
    timestamp: Optional[str] = None
    event_type: str
    description: str
    severity: str = "info"
    source: str = "log"


class RCAHop(BaseModel):
    cause: str
    confidence: float
    evidence: List[str] = []
    description: Optional[str] = None


class InvestigateRequest(BaseModel):
    entity: InvestigateEntity
    question: str = Field(..., min_length=3, max_length=2000)

    model_config = {
        "json_schema_extra": {
            "example": {
                "entity": {"type": "ND", "id": "0142785811"},
                "question": "Pourquoi le dossier reste bloqué à l'état 2 ?"
            }
        }
    }


class InvestigateResponse(BaseModel):
    mode: ResponseMode
    timeline: List[TimelineEvent] = []
    rca_chain: List[RCAHop] = []
    anomalies: List[str] = []
    evidence: List[EvidenceItem] = []
    confidence: float = Field(..., ge=0.0, le=1.0)
    missing_information: List[str] = []
    limitations: List[str] = []
    next_steps: List[str] = []
    runtime_capabilities: RuntimeCapabilities


# ─────────────────────────────────────────────────────────────────────────────
# POST /workflow
# ─────────────────────────────────────────────────────────────────────────────

class WorkflowRequest(BaseModel):
    workflow_type: str = Field(..., description="equipment_delete | vlan_delete | tp_fix | bas_delete | operator_delete")
    entity_id: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "workflow_type": "equipment_delete",
                "entity_id": "OP49MAB11"
            }
        }
    }


class WorkflowResponse(BaseModel):
    workflow: str
    current_state: Optional[str] = None
    expected_next_state: Optional[str] = None
    invalid_transitions: List[str] = []
    blocking_conditions: List[str] = []
    business_rules_triggered: List[str] = []
    recommended_actions: List[str] = []
    runtime_capabilities: RuntimeCapabilities


# ─────────────────────────────────────────────────────────────────────────────
# POST /validate
# ─────────────────────────────────────────────────────────────────────────────

class ValidateContext(BaseModel):
    nd: Optional[str] = None
    equipment_id: Optional[str] = None
    extra: Dict[str, Any] = {}


class ValidateRequest(BaseModel):
    hypothesis: str = Field(..., min_length=5, max_length=1000)
    context: Optional[ValidateContext] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "hypothesis": "Le blocage provient d'un MQ ACK absent",
                "context": {"nd": "0142785811"}
            }
        }
    }


class ValidateResponse(BaseModel):
    valid: bool
    confidence: float = Field(..., ge=0.0, le=1.0)
    supporting_evidence: List[str] = []
    contradictions: List[str] = []
    missing_evidence: List[str] = []
    validation_mode: ValidationMode
    runtime_capabilities: RuntimeCapabilities


# ─────────────────────────────────────────────────────────────────────────────
# POST /search
# ─────────────────────────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=500)
    top_k: int = Field(5, ge=1, le=20)
    source_types: Optional[List[str]] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "Erreur 1300 suppression équipement"
            }
        }
    }


class SearchResult(BaseModel):
    source_type: str
    title: str
    relevance: float = Field(..., ge=0.0, le=1.0)
    summary: str
    reference_id: Optional[str] = None


class SearchResponse(BaseModel):
    results: List[SearchResult]
    total: int
    runtime_capabilities: RuntimeCapabilities
