"""
Validation Endpoints
Human-in-the-loop validation and corrections
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Optional

from app.schemas.validation import ValidationTask, ValidationResult, CorrectionSubmission
from app.services.validation.validation_service import ValidationService
from app.db.session import get_db

router = APIRouter()


def get_validation_service(db: Session = Depends(get_db)) -> ValidationService:
    """Dependency injection pour ValidationService"""
    return ValidationService(db)


@router.get("/pending")
async def get_pending_validations(
    limit: int = 50,
    task_type: Optional[str] = None,
    service: ValidationService = Depends(get_validation_service)
):
    """
    Récupère les tâches de validation en attente
    
    **Paramètres:**
    - limit: Nombre max de tâches (défaut: 50)
    - task_type: Filtrer par type (response_validation, rule_extraction, pattern_confirmation)
    
    **Retourne:**
    Liste des tâches ordonnées par priorité
    """
    try:
        tasks = await service.get_pending_tasks(limit, task_type)
        return {"count": len(tasks), "tasks": tasks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/submit")
async def submit_validation(
    validation: ValidationResult,
    service: ValidationService = Depends(get_validation_service)
):
    """
    Soumet un résultat de validation
    
    **Actions:**
    - Approuver/rejeter la suggestion de l'IA
    - Appliquer corrections si nécessaire
    - Mettre à jour la base de connaissances
    
    **Body:**
    - task_id: ID de la tâche
    - approved: true/false
    - corrections: Données corrigées (optionnel)
    - comments: Commentaires (optionnel)
    - validator_id: ID du validateur
    """
    try:
        result = await service.submit_validation(validation)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/correction")
async def submit_correction(
    correction: CorrectionSubmission,
    service: ValidationService = Depends(get_validation_service)
):
    """
    Soumet une correction manuelle à la base de connaissances
    
    **Utilisé pour:**
    - Corriger des données inexactes
    - Améliorer la précision de l'IA
    - Mettre à jour des relations dans le graphe
    
    **Body:**
    - entity_id: ID de l'entité à corriger
    - entity_type: Type (knowledge_node, relationship)
    - corrections: Nouvelles valeurs
    - reason: Raison de la correction
    - submitter_id: ID du soumetteur
    """
    try:
        result = await service.apply_correction(correction)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_validation_history(
    user_id: Optional[str] = None,
    limit: int = 100,
    task_type: Optional[str] = None,
    service: ValidationService = Depends(get_validation_service)
):
    """
    Récupère l'historique des validations
    
    **Paramètres:**
    - user_id: Filtrer par validateur (optionnel)
    - limit: Nombre max de résultats (défaut: 100)
    - task_type: Filtrer par type (optionnel)
    
    **Retourne:**
    Historique des validations avec statuts
    """
    try:
        history = await service.get_history(user_id, limit, task_type)
        return {"count": len(history), "history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics")
async def get_validation_metrics(
    service: ValidationService = Depends(get_validation_service)
):
    """
    Récupère les métriques de validation
    
    **Métriques:**
    - Total de validations
    - Taux d'approbation
    - Nombre en attente
    - Validations par semaine
    - Répartition par type
    
    **Retourne:**
    Dashboard metrics pour monitoring
    """
    try:
        metrics = await service.get_metrics()
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify-consistency")
async def verify_consistency(
    brasil_data: dict,
    terrain_data: dict,
    service: ValidationService = Depends(get_validation_service)
):
    """
    Vérifie la cohérence entre données BRASIL et terrain
    
    **Utilisé pour:**
    - Détecter incohérences entre systèmes
    - Identifier données obsolètes
    - Créer tâches de validation automatiques
    
    **Body:**
    - brasil_data: Données du système BRASIL
    - terrain_data: Données relevées sur le terrain
    
    **Retourne:**
    Rapport avec liste des incohérences et leur sévérité
    """
    try:
        result = await service.verify_brasil_terrain_consistency(brasil_data, terrain_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create-task")
async def create_validation_task(
    task_type: str,
    original_data: dict,
    ai_suggestion: Optional[dict] = None,
    priority: int = 5,
    service: ValidationService = Depends(get_validation_service)
):
    """
    Crée une nouvelle tâche de validation
    
    **Paramètres:**
    - task_type: Type (response_validation, rule_extraction, etc.)
    - original_data: Données originales à valider
    - ai_suggestion: Suggestion de l'IA (optionnel)
    - priority: Priorité 1-10 (défaut: 5)
    
    **Retourne:**
    task_id de la tâche créée
    """
    try:
        task_id = await service.create_validation_task(
            task_type, original_data, ai_suggestion, priority
        )
        return {"task_id": task_id, "status": "created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Chatbot N3 Validation endpoints ────────────────────────────────────────

from pydantic import BaseModel  # noqa: E402


class ApproveRequest(BaseModel):
    validator_id: str
    comment: str = ""


class CorrectRequest(BaseModel):
    validator_id: str
    corrected_response: str
    correction_reason: str


class RejectRequest(BaseModel):
    validator_id: str
    reason: str


class EscalateRequest(BaseModel):
    escalated_by: str
    escalation_note: str


class RetrainRequest(BaseModel):
    triggered_by: str = "n3_dashboard"


@router.get("/chatbot-tasks")
def get_chatbot_tasks(
    priority_min: Optional[int] = None,
    application:  Optional[str] = None,
    limit:  int = 50,
    offset: int = 0,
    service: ValidationService = Depends(get_validation_service),
):
    """
    Dashboard N3 — Réponses chatbot en attente de validation.
    Triées par priorité décroissante.
    """
    return service.get_chatbot_tasks(
        priority_min=priority_min,
        application=application,
        limit=limit,
        offset=offset,
    )


@router.get("/chatbot-stats")
def get_chatbot_stats(
    service: ValidationService = Depends(get_validation_service),
):
    """Stats chatbot N3 pour le dashboard (pending, validées, corrections…)."""
    return service.get_chatbot_stats()


@router.post("/chatbot-tasks/{task_id}/approve")
def approve_chatbot_task(
    task_id: int,
    body: ApproveRequest,
    service: ValidationService = Depends(get_validation_service),
):
    """N3 approuve la réponse → trust +0.15."""
    result = service.approve_chatbot_response(task_id, body.validator_id, body.comment)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/chatbot-tasks/{task_id}/correct")
def correct_chatbot_task(
    task_id: int,
    body: CorrectRequest,
    service: ValidationService = Depends(get_validation_service),
):
    """N3 corrige la réponse → sauvegardée pour réapprentissage KB."""
    result = service.correct_chatbot_response(
        task_id,
        body.validator_id,
        body.corrected_response,
        body.correction_reason,
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/chatbot-tasks/{task_id}/reject")
def reject_chatbot_task(
    task_id: int,
    body: RejectRequest,
    service: ValidationService = Depends(get_validation_service),
):
    """N3 rejette la réponse → trust -0.20."""
    result = service.reject_chatbot_response(task_id, body.validator_id, body.reason)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/chatbot-tasks/{task_id}/escalate")
def escalate_chatbot_task(
    task_id: int,
    body: EscalateRequest,
    service: ValidationService = Depends(get_validation_service),
):
    """Escalade vers expert N3 senior — priorité max."""
    result = service.escalate_chatbot_response(
        task_id, body.escalated_by, body.escalation_note
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/retrain")
def trigger_retraining(
    body: RetrainRequest,
    service: ValidationService = Depends(get_validation_service),
):
    """
    Lance le pipeline de réapprentissage KB depuis les corrections N3.

    Ce que ça fait :
      1. Charge les corrections chatbot N3 non traitées
      2. Génère des chunks RAG (trust=0.85, validé humain)
      3. Recalcule les trust scores des FRs
      4. Indexe dans Qdrant (si dispo)
      5. Génère des procédures draft si ≥2 corrections même type
      6. Sauvegarde data_pipeline/output/kb_corrections.json

    Ce que ça NE fait PAS :
      - Fine-tuning LLM (Groq est une API externe)
    """
    try:
        stats = service.trigger_retraining()
        return {
            "status":       "success",
            "message":      "Réapprentissage KB terminé",
            "triggered_by": body.triggered_by,
            **stats,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur pipeline: {str(e)}")
