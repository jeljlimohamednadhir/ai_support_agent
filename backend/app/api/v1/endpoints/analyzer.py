"""
Analyzer Endpoints
AI-powered code, log, and system analysis
"""
from fastapi import APIRouter, HTTPException
from app.schemas.analyzer import AnalysisRequest, AnalysisResult
from app.services.analyzer.analyzer_service import AnalyzerService

router = APIRouter()


@router.post("/analyze/code", response_model=AnalysisResult)
async def analyze_code(request: AnalysisRequest):
    """
    Analyze code for:
    - Business rules extraction
    - Flow analysis
    - Dependencies
    - Potential issues
    """
    try:
        analyzer = AnalyzerService()
        result = await analyzer.analyze_code(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/logs")
async def analyze_logs(log_query: dict):
    """
    Analyze logs for:
    - Error patterns
    - Anomalies
    - Performance issues
    - Security concerns
    """
    try:
        analyzer = AnalyzerService()
        result = await analyzer.analyze_logs(log_query)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/behavior")
async def analyze_behavior(scenario: dict):
    """
    Analyze application behavior for specific scenarios
    
    Example: "What happens when a non-verified user accesses admin?"
    """
    try:
        analyzer = AnalyzerService()
        result = await analyzer.analyze_behavior(scenario)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights")
async def get_insights(category: str = None):
    """
    Get AI-generated insights about the application
    Categories: security, performance, architecture, bugs
    """
    try:
        analyzer = AnalyzerService()
        insights = await analyzer.get_insights(category)
        return insights
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
