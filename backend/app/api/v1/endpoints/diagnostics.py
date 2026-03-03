"""
Diagnostics Endpoints
Intelligent problem diagnosis and troubleshooting
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Optional

from app.schemas.diagnostics import DiagnosticRequest, DiagnosticReport
from app.services.analyzer.diagnostics_engine import DiagnosticsEngine
from app.db.session import get_db

router = APIRouter()


def get_diagnostics_engine(db: Session = Depends(get_db)) -> DiagnosticsEngine:
    """Dependency injection pour DiagnosticsEngine"""
    return DiagnosticsEngine(db)


@router.post("/diagnose")
async def diagnose_issue(
    request: DiagnosticRequest,
    engine: DiagnosticsEngine = Depends(get_diagnostics_engine)
):
    """
    Diagnostic IA d'un problème technique
    
    **Processus:**
    1. Analyse sémantique du problème
    2. Recherche contexte pertinent (code, logs, docs)
    3. Identification d'issues similaires
    4. Détermination de la cause racine via LLM
    5. Génération de solutions suggérées
    
    **Body:**
    - issue_description: Description du problème
    - affected_component: Composant impacté (optionnel)
    - error_logs: Logs d'erreur (optionnel)
    - context: Contexte additionnel (optionnel)
    
    **Retourne:**
    - diagnostic_id: ID du rapport
    - root_cause: Cause racine identifiée
    - severity: Sévérité (low, medium, high, critical)
    - confidence: Confiance de l'analyse (0.0-1.0)
    - related_code: Sections de code pertinentes
    - related_logs: Entrées de logs liées
    - suggested_fixes: Solutions proposées
    - similar_issues: Issues similaires résolues
    """
    try:
        report = await engine.diagnose(request)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Diagnostic failed: {str(e)}")


@router.get("/similar-issues")
async def find_similar_issues(
    issue_description: str,
    limit: int = 10,
    engine: DiagnosticsEngine = Depends(get_diagnostics_engine)
):
    """
    Recherche d'issues similaires dans l'historique
    
    **Sources:**
    - Historique des diagnostics (PostgreSQL)
    - Tickets Jira résolus (Neo4j)
    - Base vectorielle (Qdrant)
    
    **Paramètres:**
    - issue_description: Description du problème à comparer
    - limit: Nombre max de résultats (défaut: 10)
    
    **Retourne:**
    Liste d'issues avec scores de similarité, résolutions, sources
    """
    try:
        similar = await engine.find_similar_issues(issue_description, limit)
        return {"count": len(similar), "issues": similar}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/suggest-fixes/{diagnostic_id}")
async def suggest_fixes(
    diagnostic_id: str,
    engine: DiagnosticsEngine = Depends(get_diagnostics_engine)
):
    """
    Génère ou récupère les suggestions de solutions
    
    **Paramètres:**
    - diagnostic_id: ID du rapport de diagnostic
    
    **Retourne:**
    Liste de solutions avec types (quick_fix, proper_fix, preventive), 
    descriptions, étapes détaillées, temps estimé
    """
    try:
        fixes = await engine.suggest_fixes(diagnostic_id)
        return {"diagnostic_id": diagnostic_id, "fixes": fixes}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patterns")
async def get_diagnostic_patterns(
    engine: DiagnosticsEngine = Depends(get_diagnostics_engine)
):
    """
    Analyse des patterns d'erreurs récurrents
    
    **Métriques:**
    - Total de diagnostics
    - Taux de résolution
    - Temps moyen de résolution
    - Top composants affectés
    - Distribution par sévérité
    
    **Utilisé pour:**
    - Identifier zones problématiques
    - Prioriser amélioration qualité
    - Anticiper problèmes futurs
    
    **Retourne:**
    Dashboard statistics sur les patterns de problèmes
    """
    try:
        patterns = await engine.get_diagnostic_patterns()
        return patterns
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{diagnostic_id}")
async def get_diagnostic_report(
    diagnostic_id: str,
    engine: DiagnosticsEngine = Depends(get_diagnostics_engine)
):
    """
    Récupère un rapport de diagnostic complet
    
    **Paramètres:**
    - diagnostic_id: ID du diagnostic
    
    **Retourne:**
    Rapport complet avec historique, analyse, solutions, statut
    """
    try:
        report = engine.db.query(engine.db.query(DiagnosticReport).filter(
            DiagnosticReport.id == diagnostic_id
        ).first())
        
        if not report:
            raise HTTPException(status_code=404, detail=f"Diagnostic {diagnostic_id} not found")
        
        return {
            "diagnostic_id": report.id,
            "issue_description": report.issue_description,
            "affected_component": report.affected_component,
            "severity": report.severity,
            "status": report.status,
            "root_cause": report.root_cause,
            "analysis": report.analysis,
            "confidence": report.confidence,
            "error_logs": report.error_logs,
            "related_code": report.related_code,
            "suggested_fixes": report.suggested_fixes,
            "applied_fix": report.applied_fix,
            "resolution_notes": report.resolution_notes,
            "created_at": report.created_at.isoformat(),
            "updated_at": report.updated_at.isoformat(),
            "resolved_at": report.resolved_at.isoformat() if report.resolved_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{diagnostic_id}/status")
async def update_diagnostic_status(
    diagnostic_id: str,
    status: str,
    resolution_notes: Optional[str] = None,
    applied_fix: Optional[dict] = None,
    engine: DiagnosticsEngine = Depends(get_diagnostics_engine)
):
    """
    Met à jour le statut d'un diagnostic
    
    **Statuts possibles:**
    - open: Nouveau diagnostic
    - in_progress: En cours d'investigation
    - resolved: Problème résolu
    - closed: Fermé (sans résolution ou duplicata)
    
    **Paramètres:**
    - diagnostic_id: ID du diagnostic
    - status: Nouveau statut
    - resolution_notes: Notes de résolution (optionnel)
    - applied_fix: Solution appliquée (optionnel)
    
    **Retourne:**
    Confirmation de mise à jour
    """
    try:
        from app.models.database import DiagnosticReport
        from datetime import datetime
        
        report = engine.db.query(DiagnosticReport).filter(
            DiagnosticReport.id == diagnostic_id
        ).first()
        
        if not report:
            raise HTTPException(status_code=404, detail=f"Diagnostic {diagnostic_id} not found")
        
        report.status = status
        
        if resolution_notes:
            report.resolution_notes = resolution_notes
        
        if applied_fix:
            report.applied_fix = applied_fix
        
        if status == "resolved":
            report.resolved_at = datetime.utcnow()
        
        engine.db.commit()
        
        return {
            "diagnostic_id": diagnostic_id,
            "status": status,
            "updated_at": report.updated_at.isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_diagnostics(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    component: Optional[str] = None,
    limit: int = 50,
    engine: DiagnosticsEngine = Depends(get_diagnostics_engine)
):
    """
    Liste les rapports de diagnostics avec filtres
    
    **Filtres:**
    - status: Filtrer par statut (open, in_progress, resolved, closed)
    - severity: Filtrer par sévérité (low, medium, high, critical)
    - component: Filtrer par composant affecté
    - limit: Nombre max de résultats (défaut: 50)
    
    **Retourne:**
    Liste paginée de diagnostics
    """
    try:
        from app.models.database import DiagnosticReport
        from sqlalchemy import desc
        
        query = engine.db.query(DiagnosticReport)
        
        if status:
            query = query.filter(DiagnosticReport.status == status)
        
        if severity:
            query = query.filter(DiagnosticReport.severity == severity)
        
        if component:
            query = query.filter(DiagnosticReport.affected_component == component)
        
        reports = query.order_by(desc(DiagnosticReport.created_at)).limit(limit).all()
        
        return {
            "count": len(reports),
            "diagnostics": [
                {
                    "diagnostic_id": r.id,
                    "issue_description": r.issue_description,
                    "affected_component": r.affected_component,
                    "severity": r.severity,
                    "status": r.status,
                    "root_cause": r.root_cause,
                    "confidence": r.confidence,
                    "created_at": r.created_at.isoformat(),
                    "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None
                }
                for r in reports
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
