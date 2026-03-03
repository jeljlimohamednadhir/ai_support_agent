"""
API Endpoints — Applications (Multi-Tenant)
CRUD sur les ApplicationContext + trigger invalidation cache
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth import get_current_user
from app.models.app_context import ApplicationContext
from app.schemas.app_context import (
    ApplicationContextCreate,
    ApplicationContextUpdate,
    ApplicationContextRead,
    ApplicationContextSummary,
)
from app.core.app_context_resolver import app_context_resolver
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/", response_model=List[ApplicationContextSummary])
async def list_applications(
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Liste toutes les applications enregistrées"""
    query = db.query(ApplicationContext)
    if active_only:
        query = query.filter(ApplicationContext.is_active == True)
    return query.order_by(ApplicationContext.id).all()


@router.get("/{app_id}", response_model=ApplicationContextRead)
async def get_application(
    app_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Récupère le profil d'une application"""
    ctx = db.query(ApplicationContext).filter(ApplicationContext.id == app_id.upper()).first()
    if not ctx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{app_id}' non trouvée"
        )
    return ctx


@router.post("/", response_model=ApplicationContextRead, status_code=status.HTTP_201_CREATED)
async def create_application(
    payload: ApplicationContextCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Crée un nouveau profil d'application"""
    app_id = payload.id.upper()

    existing = db.query(ApplicationContext).filter(ApplicationContext.id == app_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Application '{app_id}' existe déjà"
        )

    ctx = ApplicationContext(
        id=app_id,
        display_name=payload.display_name,
        description=payload.description,
        mode=payload.mode,
        has_canonical_procedures=payload.has_canonical_procedures,
        has_ticket_history=payload.has_ticket_history,
        has_logs=payload.has_logs,
        has_stack_traces=payload.has_stack_traces,
        has_codebase=payload.has_codebase,
        log_parser_strategy=payload.log_parser_strategy,
        trust_threshold_strong=payload.trust_threshold_strong,
        trust_threshold_medium=payload.trust_threshold_medium,
        min_cluster_frequency=payload.min_cluster_frequency,
        max_canonical_procedures=payload.max_canonical_procedures,
        qdrant_collection_prefix=payload.qdrant_collection_prefix or f"{app_id.lower()}_",
        extra_config=payload.extra_config,
        is_active=True,
    )
    db.add(ctx)
    db.commit()
    db.refresh(ctx)

    logger.info(f"[Apps] Application créée: {app_id} (mode={payload.mode})")
    return ctx


@router.patch("/{app_id}", response_model=ApplicationContextRead)
async def update_application(
    app_id: str,
    payload: ApplicationContextUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Met à jour le profil d'une application + invalide le cache"""
    ctx = db.query(ApplicationContext).filter(ApplicationContext.id == app_id.upper()).first()
    if not ctx:
        raise HTTPException(status_code=404, detail=f"Application '{app_id}' non trouvée")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(ctx, field, value)

    db.commit()
    db.refresh(ctx)

    # Invalider le cache du resolver
    app_context_resolver.invalidate_cache(app_id)

    logger.info(f"[Apps] Application mise à jour: {app_id}")
    return ctx


@router.delete("/{app_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_application(
    app_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Désactive une application (soft delete)"""
    ctx = db.query(ApplicationContext).filter(ApplicationContext.id == app_id.upper()).first()
    if not ctx:
        raise HTTPException(status_code=404, detail=f"Application '{app_id}' non trouvée")

    ctx.is_active = False
    db.commit()
    app_context_resolver.invalidate_cache(app_id)

    logger.info(f"[Apps] Application désactivée: {app_id}")


@router.post("/{app_id}/cache/invalidate", status_code=status.HTTP_200_OK)
async def invalidate_app_cache(
    app_id: str,
    current_user=Depends(get_current_user),
):
    """Force l'invalidation du cache du resolver pour une application"""
    app_context_resolver.invalidate_cache(app_id)
    return {"message": f"Cache invalidé pour '{app_id}'"}


@router.get("/{app_id}/pipeline-mode")
async def get_pipeline_mode(
    app_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Retourne le mode de pipeline actif pour une application"""
    mode = app_context_resolver.get_pipeline_mode(app_id.upper(), db)
    return {
        "app_id": app_id.upper(),
        "mode": mode.value,
        "description": {
            "FR_RICH": "Procédures canoniques validées N3 — diagnostic ferme",
            "FR_WEAK": "Clustering tickets + procédures partielles — diagnostic prudent",
            "LOG_BASED": "Analyse logs/stack traces — diagnostic probabiliste",
        }.get(mode.value, ""),
    }
