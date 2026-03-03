"""
Diagnostics Schemas
"""
from pydantic import BaseModel
from typing import List, Optional


class DiagnosticRequest(BaseModel):
    """Diagnostic request"""
    issue_description: str
    affected_component: Optional[str] = None
    error_logs: Optional[List[str]] = None
    context: Optional[dict] = None


class DiagnosticReport(BaseModel):
    """Diagnostic report"""
    diagnostic_id: str
    root_cause: str
    related_code: List[dict]
    related_logs: List[dict]
    suggested_fixes: List[str]
    confidence: float
