"""
Validation Service
Human-in-the-loop validation avec intégration BRASIL ↔ Terrain
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
import uuid

from app.models.database import ValidationTask, Correction, KnowledgeNode
from app.schemas.validation import ValidationResult, CorrectionSubmission
from app.services.knowledge.graph_service import GraphService


class ValidationService:
    """Service de validation et feedback humain"""
    
    def __init__(self, db: Session):
        self.db = db
        self.graph_service = GraphService()
    
    async def get_pending_tasks(self, limit: int = 10, task_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Récupère les tâches de validation en attente
        
        Args:
            limit: Nombre max de tâches à retourner
            task_type: Filtrer par type (response_validation, rule_extraction, pattern_confirmation)
        
        Returns:
            Liste des tâches ordonnées par priorité puis date
        """
        query = self.db.query(ValidationTask).filter(ValidationTask.status == "pending")
        
        if task_type:
            query = query.filter(ValidationTask.task_type == task_type)
        
        tasks = query.order_by(
            desc(ValidationTask.priority),
            ValidationTask.created_at
        ).limit(limit).all()
        
        return [
            {
                "task_id": str(task.id),
                "task_type": task.task_type,
                "priority": task.priority,
                "content": {
                    "original_data": task.original_data,
                    "ai_suggestion": task.ai_suggestion
                },
                "created_at": task.created_at.isoformat(),
                "status": task.status
            }
            for task in tasks
        ]
    
    async def submit_validation(self, validation: ValidationResult) -> Dict[str, Any]:
        """
        Soumet un résultat de validation
        
        Args:
            validation: Résultat de validation avec task_id, approved, corrections
        
        Returns:
            Confirmation avec métadonnées
        """
        task = self.db.query(ValidationTask).filter(
            ValidationTask.id == int(validation.task_id)
        ).first()
        
        if not task:
            raise ValueError(f"Validation task {validation.task_id} not found")
        
        # Mise à jour de la tâche
        task.status = "validated" if validation.approved else "rejected"
        task.validator_id = validation.validator_id
        task.validated_at = datetime.utcnow()
        task.validation_comment = validation.comments
        
        if validation.corrections:
            task.validated_data = validation.corrections
        elif validation.approved and task.ai_suggestion:
            task.validated_data = task.ai_suggestion
        
        # Si approuvé, appliquer à la base de connaissances
        if validation.approved:
            await self._apply_to_knowledge_base(task)
        
        self.db.commit()
        
        return {
            "task_id": validation.task_id,
            "status": task.status,
            "validated_at": task.validated_at.isoformat(),
            "applied": validation.approved
        }
    
    async def apply_correction(self, correction: CorrectionSubmission) -> Dict[str, Any]:
        """
        Applique une correction à la base de connaissances
        Utilisé pour améliorer l'IA avec des corrections utilisateur
        
        Args:
            correction: Données de correction
        
        Returns:
            Confirmation avec détails
        """
        # Enregistrer la correction
        new_correction = Correction(
            correction_type="manual",
            entity_type=correction.entity_type,
            entity_id=correction.entity_id,
            original_value={},  # TODO: Fetch original from KB
            corrected_value=correction.corrections,
            corrector_id=correction.submitter_id,
            reason=correction.reason,
            applied=False
        )
        
        self.db.add(new_correction)
        self.db.flush()
        
        # Appliquer selon le type d'entité
        if correction.entity_type == "knowledge_node":
            success = await self._update_knowledge_node(
                correction.entity_id,
                correction.corrections
            )
        elif correction.entity_type == "relationship":
            success = await self._update_relationship(
                correction.entity_id,
                correction.corrections
            )
        else:
            success = False
        
        if success:
            new_correction.applied = True
            new_correction.applied_at = datetime.utcnow()
        
        self.db.commit()
        
        return {
            "correction_id": new_correction.id,
            "applied": success,
            "entity_type": correction.entity_type,
            "entity_id": correction.entity_id
        }
    
    async def get_history(
        self, 
        user_id: Optional[str] = None, 
        limit: int = 100,
        task_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Récupère l'historique des validations
        
        Args:
            user_id: Filtrer par validateur
            limit: Nombre max de résultats
            task_type: Filtrer par type
        
        Returns:
            Historique des validations
        """
        query = self.db.query(ValidationTask).filter(
            ValidationTask.status.in_(["validated", "rejected"])
        )
        
        if user_id:
            query = query.filter(ValidationTask.validator_id == user_id)
        
        if task_type:
            query = query.filter(ValidationTask.task_type == task_type)
        
        tasks = query.order_by(desc(ValidationTask.validated_at)).limit(limit).all()
        
        return [
            {
                "task_id": str(task.id),
                "task_type": task.task_type,
                "status": task.status,
                "validator_id": task.validator_id,
                "validated_at": task.validated_at.isoformat() if task.validated_at else None,
                "comment": task.validation_comment,
                "original_data": task.original_data,
                "validated_data": task.validated_data
            }
            for task in tasks
        ]
    
    async def get_metrics(self) -> Dict[str, Any]:
        """
        Calcule les métriques de validation
        
        Returns:
            Métriques: total, taux d'approbation, en attente, etc.
        """
        # Total validations
        total_validated = self.db.query(func.count(ValidationTask.id)).filter(
            ValidationTask.status.in_(["validated", "rejected"])
        ).scalar()
        
        # Approved
        approved = self.db.query(func.count(ValidationTask.id)).filter(
            ValidationTask.status == "validated"
        ).scalar()
        
        # Pending
        pending = self.db.query(func.count(ValidationTask.id)).filter(
            ValidationTask.status == "pending"
        ).scalar()
        
        # Accuracy rate
        accuracy_rate = (approved / total_validated * 100) if total_validated > 0 else 0.0
        
        # Validations par jour (dernière semaine)
        week_ago = datetime.utcnow() - timedelta(days=7)
        weekly_count = self.db.query(func.count(ValidationTask.id)).filter(
            ValidationTask.validated_at >= week_ago,
            ValidationTask.status.in_(["validated", "rejected"])
        ).scalar()
        
        # Par type
        type_stats = self.db.query(
            ValidationTask.task_type,
            func.count(ValidationTask.id).label("count")
        ).filter(
            ValidationTask.status.in_(["validated", "rejected"])
        ).group_by(ValidationTask.task_type).all()
        
        return {
            "total_validations": total_validated or 0,
            "approved": approved or 0,
            "rejected": (total_validated - approved) if total_validated else 0,
            "accuracy_rate": round(accuracy_rate, 2),
            "pending_count": pending or 0,
            "weekly_validations": weekly_count or 0,
            "by_type": {stat.task_type: stat.count for stat in type_stats}
        }
    
    async def create_validation_task(
        self,
        task_type: str,
        original_data: Dict[str, Any],
        ai_suggestion: Optional[Dict[str, Any]] = None,
        priority: int = 5
    ) -> str:
        """
        Crée une nouvelle tâche de validation
        
        Args:
            task_type: Type de tâche
            original_data: Données originales
            ai_suggestion: Suggestion de l'IA (optionnel)
            priority: Priorité 1-10
        
        Returns:
            task_id créé
        """
        task = ValidationTask(
            task_type=task_type,
            status="pending",
            priority=priority,
            original_data=original_data,
            ai_suggestion=ai_suggestion
        )
        
        self.db.add(task)
        self.db.commit()
        
        return str(task.id)
    
    async def verify_brasil_terrain_consistency(
        self,
        brasil_data: Dict[str, Any],
        terrain_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Vérifie la cohérence entre données BRASIL et terrain
        
        Args:
            brasil_data: Données système BRASIL
            terrain_data: Données terrain
        
        Returns:
            Rapport de cohérence avec incohérences détectées
        """
        inconsistencies = []
        
        # Vérifier les champs communs
        common_fields = set(brasil_data.keys()) & set(terrain_data.keys())
        
        for field in common_fields:
            brasil_value = brasil_data.get(field)
            terrain_value = terrain_data.get(field)
            
            if brasil_value != terrain_value:
                inconsistencies.append({
                    "field": field,
                    "brasil_value": brasil_value,
                    "terrain_value": terrain_value,
                    "severity": self._assess_inconsistency_severity(field, brasil_value, terrain_value)
                })
        
        # Créer une tâche de validation si incohérences critiques
        critical_inconsistencies = [i for i in inconsistencies if i["severity"] == "critical"]
        
        if critical_inconsistencies:
            await self.create_validation_task(
                task_type="consistency_check",
                original_data={
                    "brasil_data": brasil_data,
                    "terrain_data": terrain_data,
                    "inconsistencies": critical_inconsistencies
                },
                priority=9  # Haute priorité
            )
        
        return {
            "consistent": len(inconsistencies) == 0,
            "inconsistencies_count": len(inconsistencies),
            "critical_count": len(critical_inconsistencies),
            "inconsistencies": inconsistencies,
            "validation_task_created": len(critical_inconsistencies) > 0
        }
    
    # Méthodes privées
    
    async def _apply_to_knowledge_base(self, task: ValidationTask) -> bool:
        """Applique les données validées à la base de connaissances"""
        try:
            validated_data = task.validated_data or task.ai_suggestion
            
            if task.task_type == "rule_extraction":
                # Ajouter règle au graphe
                await self.graph_service.add_business_rule(validated_data)
            
            elif task.task_type == "pattern_confirmation":
                # Confirmer pattern détecté
                await self.graph_service.add_pattern(validated_data)
            
            elif task.task_type == "response_validation":
                # Enregistrer comme exemple validé
                await self.graph_service.add_validated_response(validated_data)
            
            return True
        except Exception as e:
            print(f"Error applying to KB: {e}")
            return False
    
    async def _update_knowledge_node(self, node_id: str, corrections: Dict[str, Any]) -> bool:
        """Met à jour un nœud de la base de connaissances"""
        try:
            # Mettre à jour dans Neo4j
            await self.graph_service.update_node(node_id, corrections)
            
            # Mettre à jour le cache PostgreSQL
            node = self.db.query(KnowledgeNode).filter(KnowledgeNode.id == node_id).first()
            if node:
                node.properties = {**(node.properties or {}), **corrections}
                node.last_updated = datetime.utcnow()
                self.db.commit()
            
            return True
        except Exception as e:
            print(f"Error updating node: {e}")
            return False
    
    async def _update_relationship(self, relationship_id: str, corrections: Dict[str, Any]) -> bool:
        """Met à jour une relation dans le graphe"""
        try:
            await self.graph_service.update_relationship(relationship_id, corrections)
            return True
        except Exception as e:
            print(f"Error updating relationship: {e}")
            return False
    
    def _assess_inconsistency_severity(self, field: str, value1: Any, value2: Any) -> str:
        """Évalue la sévérité d'une incohérence"""
        # Champs critiques
        critical_fields = ["id", "status", "type", "affectation"]
        
        if field in critical_fields:
            return "critical"
        
        # Champs importants
        important_fields = ["description", "priority", "assignee"]
        
        if field in important_fields:
            return "high"
        
        return "low"

    # ──────────────────────────────────────────────────────────────────
    # CHATBOT N3 VALIDATION — auto-create tasks + N3 actions
    # ──────────────────────────────────────────────────────────────────

    # Trust thresholds for auto-task creation
    AUTO_THRESHOLD  = 0.80   # above → no validation needed
    MEDIUM_THRESHOLD = 0.60  # 0.60–0.79 → priority 4
    LOW_THRESHOLD   = 0.40   # 0.40–0.59 → priority 7
                              # < 0.40    → priority 9

    CRITICAL_INCIDENT_TYPES = {
        "backend_error.api_error",
        "system_integration_problem.interface_failure",
        "network_equipment_issue.dslam_error",
    }

    def create_chatbot_task(
        self,
        user_question: str,
        bot_response: str,
        trust_score: float,
        incident_type: str = "unknown",
        application: str   = "BRASIL",
        conversation_id: str = "",
    ) -> Optional[int]:
        """
        Appelé automatiquement après chaque réponse chatbot.
        Crée une ValidationTask si trust_score < seuil.
        Retourne l'id de la tâche créée, ou None si pas nécessaire.
        """
        if trust_score >= self.AUTO_THRESHOLD:
            return None

        # Compute numeric priority (1-10 scale existing model)
        if incident_type in self.CRITICAL_INCIDENT_TYPES and trust_score < 0.70:
            priority = 9
        elif trust_score < self.LOW_THRESHOLD:
            priority = 9
        elif trust_score < self.MEDIUM_THRESHOLD:
            priority = 7
        else:
            priority = 4

        task = ValidationTask(
            task_type="chatbot_response_validation",
            status="pending",
            priority=priority,
            original_data={
                "user_question":   user_question,
                "bot_response":    bot_response,
                "trust_score":     trust_score,
                "incident_type":   incident_type,
                "application":     application,
                "conversation_id": conversation_id,
            },
            ai_suggestion={
                "trust_score":   trust_score,
                "incident_type": incident_type,
                "application":   application,
            },
        )
        try:
            self.db.add(task)
            self.db.commit()
            self.db.refresh(task)
            return task.id
        except Exception as e:
            self.db.rollback()
            import logging
            logging.getLogger(__name__).warning(f"[VALIDATION] create_chatbot_task error: {e}")
            return None

    def approve_chatbot_response(
        self, task_id: int, validator_id: str, comment: str = ""
    ) -> Dict[str, Any]:
        """N3 approuve la réponse → trust +0.15, tâche validée."""
        task = self.db.query(ValidationTask).filter(ValidationTask.id == task_id).first()
        if not task:
            return {"error": f"Tâche {task_id} introuvable"}

        task.status        = "validated"
        task.validator_id  = validator_id
        task.validated_at  = datetime.utcnow()
        task.validation_comment = comment
        task.validated_data = {
            **(task.original_data or {}),
            "action":       "approved",
            "trust_boost":  +0.15,
            "validated_by": validator_id,
            "validated_at": datetime.utcnow().isoformat(),
        }
        try:
            self.db.commit()
            return {"status": "approved", "task_id": task_id, "trust_boost": +0.15}
        except Exception as e:
            self.db.rollback()
            return {"error": str(e)}

    def correct_chatbot_response(
        self,
        task_id: int,
        validator_id: str,
        corrected_response: str,
        correction_reason: str,
    ) -> Dict[str, Any]:
        """N3 corrige la réponse → sauvegardée dans corrections pour réapprentissage."""
        task = self.db.query(ValidationTask).filter(ValidationTask.id == task_id).first()
        if not task:
            return {"error": f"Tâche {task_id} introuvable"}

        original = task.original_data or {}

        # Save in corrections table for retraining pipeline
        corr = Correction(
            correction_type="chatbot_n3",
            entity_type="chatbot_response",
            entity_id=str(task_id),
            original_value={
                "user_question": original.get("user_question", ""),
                "bot_response":  original.get("bot_response", ""),
                "trust_score":   original.get("trust_score", 0),
                "incident_type": original.get("incident_type", ""),
                "application":   original.get("application", "BRASIL"),
            },
            corrected_value={
                "corrected_response": corrected_response,
                "correction_reason":  correction_reason,
                "incident_type":      original.get("incident_type", ""),
                "application":        original.get("application", "BRASIL"),
                "user_question":      original.get("user_question", ""),
            },
            corrector_id=validator_id,
            reason=correction_reason,
            applied=False,
        )
        task.status        = "validated"
        task.validator_id  = validator_id
        task.validated_at  = datetime.utcnow()
        task.validated_data = {
            "action":             "corrected",
            "corrected_response": corrected_response,
            "correction_reason":  correction_reason,
            "corrected_by":       validator_id,
        }
        try:
            self.db.add(corr)
            self.db.commit()
            return {
                "status":      "corrected",
                "task_id":     task_id,
                "message":     "Correction sauvegardée pour le réapprentissage KB.",
            }
        except Exception as e:
            self.db.rollback()
            return {"error": str(e)}

    def reject_chatbot_response(
        self, task_id: int, validator_id: str, reason: str
    ) -> Dict[str, Any]:
        """N3 rejette la réponse → trust -0.20."""
        task = self.db.query(ValidationTask).filter(ValidationTask.id == task_id).first()
        if not task:
            return {"error": f"Tâche {task_id} introuvable"}

        task.status        = "rejected"
        task.validator_id  = validator_id
        task.validated_at  = datetime.utcnow()
        task.validation_comment = reason
        task.validated_data = {
            **(task.original_data or {}),
            "action":        "rejected",
            "trust_penalty": -0.20,
            "rejected_by":   validator_id,
            "reject_reason": reason,
        }
        try:
            self.db.commit()
            return {"status": "rejected", "task_id": task_id, "trust_penalty": -0.20}
        except Exception as e:
            self.db.rollback()
            return {"error": str(e)}

    def escalate_chatbot_response(
        self, task_id: int, escalated_by: str, escalation_note: str
    ) -> Dict[str, Any]:
        """Escalade vers expert N3 senior — priorité max."""
        task = self.db.query(ValidationTask).filter(ValidationTask.id == task_id).first()
        if not task:
            return {"error": f"Tâche {task_id} introuvable"}

        task.priority      = 10
        task.validator_id  = escalated_by
        task.validation_comment = f"[ESCALADE] {escalation_note}"
        task.validated_data = {
            **(task.original_data or {}),
            "action":          "escalated",
            "escalated_by":    escalated_by,
            "escalation_note": escalation_note,
            "escalated_at":    datetime.utcnow().isoformat(),
        }
        try:
            self.db.commit()
            return {"status": "escalated", "task_id": task_id, "priority": 10}
        except Exception as e:
            self.db.rollback()
            return {"error": str(e)}

    def get_chatbot_tasks(
        self,
        priority_min: int = None,
        application: str  = None,
        limit: int        = 50,
        offset: int       = 0,
    ) -> Dict[str, Any]:
        """Dashboard N3 — tâches chatbot en attente, triées par priorité."""
        query = self.db.query(ValidationTask).filter(
            ValidationTask.task_type == "chatbot_response_validation",
            ValidationTask.status    == "pending",
        )
        if priority_min is not None:
            query = query.filter(ValidationTask.priority >= priority_min)

        total = query.count()
        tasks = (
            query
            .order_by(desc(ValidationTask.priority), ValidationTask.created_at)
            .offset(offset)
            .limit(limit)
            .all()
        )

        def _priority_label(p: int) -> str:
            if p >= 9: return "high"
            if p >= 6: return "medium"
            return "low"

        result = []
        for t in tasks:
            od = t.original_data or {}
            result.append({
                "task_id":       t.id,
                "status":        t.status,
                "priority":      t.priority,
                "priority_label": _priority_label(t.priority),
                "created_at":    t.created_at.isoformat() if t.created_at else None,
                "user_question": od.get("user_question", ""),
                "bot_response":  od.get("bot_response", "")[:300],
                "trust_score":   od.get("trust_score", 0.0),
                "incident_type": od.get("incident_type", ""),
                "application":   od.get("application", ""),
            })

        return {"total": total, "offset": offset, "limit": limit, "tasks": result}

    def get_chatbot_stats(self) -> Dict[str, Any]:
        """Stats chatbot N3 pour le dashboard."""
        base = self.db.query(ValidationTask).filter(
            ValidationTask.task_type == "chatbot_response_validation"
        )
        total     = base.count()
        pending   = base.filter(ValidationTask.status == "pending").count()
        validated = base.filter(ValidationTask.status == "validated").count()
        rejected  = base.filter(ValidationTask.status == "rejected").count()
        high_prio = base.filter(
            ValidationTask.status   == "pending",
            ValidationTask.priority >= 9,
        ).count()

        corrections_pending = self.db.query(Correction).filter(
            Correction.correction_type == "chatbot_n3",
            Correction.applied == False,  # noqa: E712
        ).count()

        return {
            "total":                  total,
            "pending":                pending,
            "validated":              validated,
            "rejected":               rejected,
            "high_priority_pending":  high_prio,
            "corrections_pending":    corrections_pending,
            "validation_rate":        round((validated + rejected) / max(total, 1) * 100, 1),
        }

    def trigger_retraining(self) -> Dict[str, Any]:
        """Lance le pipeline de réapprentissage KB depuis les corrections N3."""
        from app.services.validation.retraining_pipeline import RetrainingPipeline
        pipeline = RetrainingPipeline(self.db)
        return pipeline.run()
