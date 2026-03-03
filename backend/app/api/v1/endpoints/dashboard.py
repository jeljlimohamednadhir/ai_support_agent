"""
Endpoint pour les statistiques du tableau de bord
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import get_db
from app.models.database import (
    Conversation, Message, ValidationTask, CollectionJob, KnowledgeNode
)
from datetime import datetime, timedelta
from typing import Dict, Any, List

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Récupérer les statistiques globales pour le tableau de bord
    """
    # Pour l'instant, on simule les données car les tables ne sont pas encore créées
    # TODO: Remplacer par de vraies requêtes quand les tables existent
    
    try:
        # Essayer de compter les conversations réelles
        total_conversations = db.query(Conversation).count() if hasattr(db, 'query') else 0
    except:
        # Si les tables n'existent pas, utiliser des données simulées
        total_conversations = 0
    
    # Données simulées réalistes pour la démo BRASIL
    return {
        "total_queries": max(total_conversations, 128),  # Nombre de tables + fiches injectées
        "queries_change": 15.3,
        "active_users": 5,  # Utilisateurs actifs simulés
        "users_change": 25.0,
        "issues_resolved": 42,  # Nombre de problèmes résolus
        "resolved_change": 8.5,
        "pending_validations": 7,  # Validations en attente
        "validations_change": -12.0,
        "total_messages": total_conversations * 4 if total_conversations > 0 else 256,
        "collection_jobs": 2,  # SQL + Docs
        "successful_jobs": 2,
        "knowledge_nodes": 179  # 128 tables + 51 fiches
    }


@router.get("/activity")
async def get_activity_chart(db: Session = Depends(get_db)) -> Dict[str, List]:
    """
    Récupérer les données d'activité pour le graphique (7 derniers jours)
    """
    now = datetime.utcnow()
    days_data = []
    
    # Générer des données simulées réalistes
    import random
    for i in range(6, -1, -1):
        day = now - timedelta(days=i)
        
        # Simuler une activité croissante
        base_conversations = 15 + random.randint(-3, 5)
        base_messages = base_conversations * random.randint(3, 6)
        
        days_data.append({
            "date": day.strftime("%Y-%m-%d"),
            "day": ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"][day.weekday()],
            "conversations": base_conversations,
            "messages": base_messages
        })
    
    return {
        "labels": [d["day"] for d in days_data],
        "datasets": [
            {
                "label": "Conversations",
                "data": [d["conversations"] for d in days_data]
            },
            {
                "label": "Messages",
                "data": [d["messages"] for d in days_data]
            }
        ]
    }


@router.get("/recent-issues")
async def get_recent_issues(
    limit: int = 10,
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Récupérer les problèmes/validations récents
    """
    # Données simulées réalistes pour BRASIL
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    
    issues_demo = [
        {
            "id": 1,
            "title": "Erreur BRASIL 1002 - Champ NIFolderID manquant",
            "status": "approved",
            "severity": "high",
            "created_at": (now - timedelta(hours=2)).isoformat(),
            "updated_at": (now - timedelta(hours=1)).isoformat()
        },
        {
            "id": 2,
            "title": "Compteurs DSLAM à 100% - FR 1583",
            "status": "pending",
            "severity": "critical",
            "created_at": (now - timedelta(hours=5)).isoformat(),
            "updated_at": (now - timedelta(hours=4)).isoformat()
        },
        {
            "id": 3,
            "title": "Recherche de broche en échec",
            "status": "approved",
            "severity": "medium",
            "created_at": (now - timedelta(days=1)).isoformat(),
            "updated_at": (now - timedelta(hours=12)).isoformat()
        },
        {
            "id": 4,
            "title": "Table t_ports - Incohérence données",
            "status": "rejected",
            "severity": "low",
            "created_at": (now - timedelta(days=2)).isoformat(),
            "updated_at": (now - timedelta(days=1)).isoformat()
        },
        {
            "id": 5,
            "title": "Migration PostgreSQL - Validation schéma",
            "status": "pending",
            "severity": "high",
            "created_at": (now - timedelta(days=3)).isoformat(),
            "updated_at": (now - timedelta(days=2)).isoformat()
        }
    ]
    
    return issues_demo[:limit]
