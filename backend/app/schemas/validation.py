"""
Validation Schemas
"""
from pydantic import BaseModel
from typing import Optional


class ValidationTask(BaseModel):
    """Validation task"""
    task_id: str
    content: dict
    task_type: str
    status: str


class ValidationResult(BaseModel):
    """Validation result"""
    task_id: str
    approved: bool
    corrections: Optional[dict] = None
    comments: Optional[str] = None
    validator_id: str


class CorrectionSubmission(BaseModel):
    """Correction submission"""
    entity_id: str
    entity_type: str
    corrections: dict
    reason: str
    submitter_id: str
