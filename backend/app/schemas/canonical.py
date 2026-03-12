"""
Schemas Pydantic pour CanonicalProcedure
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ImpactScope(str, Enum):
    SINGLE_CUSTOMER = "single_customer"
    MULTIPLE_CUSTOMERS = "multiple_customers"
    INFRASTRUCTURE = "infrastructure"
    PLATFORM = "platform"


class TrustLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CanonicalProcedureCreate(BaseModel):
    id: str = Field(..., description="Ex: brasil_err1300_nd_delete")
    app_id: str
    title: str
    category: Optional[str] = None
    error_codes: Optional[List[str]] = None
    symptoms: Optional[List[str]] = None
    root_causes: Optional[List[str]] = None
    diagnostic_checks: Optional[List[str]] = None
    resolution_steps: Optional[List[str]] = None
    risk_level: RiskLevel = RiskLevel.MEDIUM
    impact_scope: ImpactScope = ImpactScope.SINGLE_CUSTOMER
    trust_level: TrustLevel = TrustLevel.MEDIUM
    validated_by: Optional[str] = None
    source_fr_numbers: Optional[List[str]] = None
    source_cluster_id: Optional[str] = None
    source_ticket_count: int = 0
    extra_metadata: Optional[Dict[str, Any]] = None


class CanonicalProcedureUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    error_codes: Optional[List[str]] = None
    symptoms: Optional[List[str]] = None
    root_causes: Optional[List[str]] = None
    diagnostic_checks: Optional[List[str]] = None
    resolution_steps: Optional[List[str]] = None
    risk_level: Optional[RiskLevel] = None
    impact_scope: Optional[ImpactScope] = None
    trust_level: Optional[TrustLevel] = None
    validated_by: Optional[str] = None
    is_active: Optional[bool] = None
    extra_metadata: Optional[Dict[str, Any]] = None


class CanonicalProcedureRead(BaseModel):
    id: str
    app_id: str
    title: str
    category: Optional[str]
    error_codes: Optional[List[str]]
    symptoms: Optional[List[str]]
    root_causes: Optional[List[str]]
    diagnostic_checks: Optional[List[str]]
    resolution_steps: Optional[List[str]]
    risk_level: RiskLevel
    impact_scope: ImpactScope
    trust_level: TrustLevel
    validated_by: Optional[str]
    validated_at: Optional[datetime]
    source_fr_numbers: Optional[List[str]]
    source_cluster_id: Optional[str]
    source_ticket_count: int
    usage_count: int
    success_count: int
    is_active: bool
    extra_metadata: Optional[Dict[str, Any]]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_validated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class CanonicalProcedureMatch(BaseModel):
    """Résultat d'un match de procédure canonique (retourné par TrustEngine)"""
    procedure: CanonicalProcedureRead
    match_score: float = Field(..., ge=0.0, le=1.0)
    matched_on: List[str]  # Ex: ["error_code:1300", "symptom:suppression ND impossible"]
    trust_level: TrustLevel
    diagnostic_strength: int  # Score 0-100 calculé par TrustEngine
