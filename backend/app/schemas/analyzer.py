"""
Analyzer Schemas
"""
from pydantic import BaseModel
from typing import List, Optional


class AnalysisRequest(BaseModel):
    """Analysis request"""
    target: str
    analysis_type: str
    options: Optional[dict] = None


class AnalysisResult(BaseModel):
    """Analysis result"""
    analysis_id: str
    findings: List[dict]
    insights: List[str]
    recommendations: List[str]
    confidence: float
