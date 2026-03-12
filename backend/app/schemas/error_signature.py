"""
Schemas Pydantic pour ErrorSignature (Mode 3)
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class SignatureStatus(str, Enum):
    RAW = "raw"
    CLUSTERED = "clustered"
    VALIDATED = "validated"


class ProbableCause(BaseModel):
    cause: str
    probability: float = Field(..., ge=0.0, le=1.0)
    evidence: Optional[List[str]] = None


class ErrorSignatureCreate(BaseModel):
    id: str
    app_id: str
    signature_hash: str
    error_type: Optional[str] = None
    module: Optional[str] = None
    method: Optional[str] = None
    error_message_pattern: Optional[str] = None
    log_keywords: Optional[List[str]] = None
    stack_trace_pattern: Optional[str] = None
    affected_classes: Optional[List[str]] = None
    frequency: int = 1
    first_seen_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    cluster_id: Optional[str] = None
    cluster_confidence: Optional[float] = None
    confidence_score: float = 0.0
    status: SignatureStatus = SignatureStatus.RAW
    known_resolution: Optional[str] = None
    resolution_confidence: Optional[float] = None
    probable_causes: Optional[List[ProbableCause]] = None
    extra_metadata: Optional[Dict[str, Any]] = None


class ErrorSignatureRead(BaseModel):
    id: str
    app_id: str
    signature_hash: str
    error_type: Optional[str]
    module: Optional[str]
    method: Optional[str]
    error_message_pattern: Optional[str]
    log_keywords: Optional[List[str]]
    stack_trace_pattern: Optional[str]
    affected_classes: Optional[List[str]]
    frequency: int
    first_seen_at: Optional[datetime]
    last_seen_at: Optional[datetime]
    cluster_id: Optional[str]
    cluster_confidence: Optional[float]
    confidence_score: float
    status: SignatureStatus
    known_resolution: Optional[str]
    resolution_confidence: Optional[float]
    probable_causes: Optional[List[ProbableCause]]
    validated_by: Optional[str]
    validated_at: Optional[datetime]
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ParsedErrorEvent(BaseModel):
    """Résultat du parsing d'un log/stack trace brut"""
    app_id: str
    raw_input: str
    error_type: Optional[str] = None
    module: Optional[str] = None
    method: Optional[str] = None
    error_message: Optional[str] = None
    log_keywords: List[str] = []
    stack_trace_lines: List[str] = []
    affected_classes: List[str] = []
    signature_hash: str = ""
    parser_strategy: str = "custom"


class DiagnosticResult(BaseModel):
    """Résultat du diagnostic Mode 3"""
    app_id: str
    parsed_event: ParsedErrorEvent
    matched_signatures: List[ErrorSignatureRead] = []
    probable_causes: List[ProbableCause] = []
    recommended_checks: List[str] = []
    diagnostic_strength: int = Field(..., ge=0, le=100)
    trust_label: str  # "strong", "moderate", "weak", "insufficient"
    summary: str
    sources: List[str] = []
