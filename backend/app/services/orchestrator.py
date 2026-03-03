"""
Orchestrator Central — Context-Aware
Route chaque requête vers le bon pipeline selon le profil de l'application.
Remplace la logique monolithique de chatbot_service.py
"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.app_context import AppMode
from app.core.app_context_resolver import app_context_resolver
from app.services.pipeline.mode1_fr_rich import FrRichPipeline
from app.services.pipeline.mode2_fr_weak import FrWeakPipeline
from app.services.pipeline.mode3_log_based import LogBasedPipeline
from app.services.knowledge.manager import get_vector_service
from app.services.trust.trust_engine import TrustLabel
from app.core.logging import get_logger

logger = get_logger(__name__)


class IntelligenceOrchestrator:
    """
    Orchestrateur central multi-tenant.

    Pour chaque requête :
      1. Résoudre le contexte de l'application (app_id → profil)
      2. Router vers le pipeline correspondant au mode
      3. Retourner un résultat unifié avec score de confiance

    Modes :
      FR_RICH   → FrRichPipeline  (canonical procedures, high trust)
      FR_WEAK   → FrWeakPipeline  (clustering + partial canonical)
      LOG_BASED → LogBasedPipeline (logs + stack traces, probabilistic)
    """

    def __init__(self):
        self.vector_service = get_vector_service()

    async def process(
        self,
        app_id: str,
        query: str,
        db: Session,
        logs: Optional[str] = None,
        stack_trace: Optional[str] = None,
        ticket_description: Optional[str] = None,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """
        Point d'entrée unique pour toutes les requêtes d'intelligence.

        Args:
            app_id: Identifiant de l'application (ex: "BRASIL")
            query: Question ou description du problème
            db: Session DB
            logs: Logs bruts (optionnel, Mode 3)
            stack_trace: Stack trace brute (optionnel, Mode 3)
            ticket_description: Description du ticket (optionnel)
            top_k: Nombre de résultats à retourner

        Returns:
            Résultat structuré unifié avec context_blocks, trust_score, sources
        """
        # 1. Résoudre le profil applicatif
        ctx = app_context_resolver.resolve(app_id, db)
        mode = ctx.mode

        logger.info(f"[Orchestrator] app={app_id}, mode={mode.value}, query='{query[:60]}...'")

        # 2. Router vers le bon pipeline
        if mode == AppMode.FR_RICH:
            pipeline = FrRichPipeline(ctx, self.vector_service)
            result = await pipeline.search(query, db, top_k=top_k)

        elif mode == AppMode.FR_WEAK:
            pipeline = FrWeakPipeline(ctx, self.vector_service)
            result = await pipeline.search(query, db, top_k=top_k)

        elif mode == AppMode.LOG_BASED:
            pipeline = LogBasedPipeline(ctx)
            result = await pipeline.analyze(
                query=query,
                db=db,
                logs=logs,
                stack_trace=stack_trace,
                ticket_description=ticket_description,
            )

        else:
            # Fallback sécurisé
            logger.warning(f"[Orchestrator] Mode inconnu '{mode}' pour '{app_id}' → FR_WEAK fallback")
            pipeline = FrWeakPipeline(ctx, self.vector_service)
            result = await pipeline.search(query, db, top_k=top_k)

        # 3. Enrichir le résultat avec les métadonnées de routing
        result["app_context"] = {
            "id": ctx.id,
            "display_name": ctx.display_name,
            "mode": mode.value,
            "trust_thresholds": {
                "strong": ctx.trust_threshold_strong,
                "medium": ctx.trust_threshold_medium,
            },
        }

        # 4. Générer les instructions pour le LLM selon le trust
        result["llm_instructions"] = self._build_llm_instructions(result, ctx)

        return result

    def build_prompt_context(self, orchestrator_result: Dict[str, Any]) -> str:
        """
        Transforme le résultat de l'orchestrateur en contexte texte pour le LLM.
        Appelé par chatbot_service.py.
        """
        blocks = orchestrator_result.get("context_blocks", [])
        if not blocks:
            return ""

        mode = orchestrator_result.get("mode", "")
        app_name = orchestrator_result.get("app_context", {}).get("display_name", "")
        trust_score = orchestrator_result.get("trust_score")
        trust_val = trust_score.score if trust_score else 0

        lines = [f"\n\n=== BASE DE CONNAISSANCE — {app_name} (Mode: {mode}) ===\n"]
        lines.append(f"Score de confiance global : {trust_val}/100\n")

        for block in blocks:
            trust_badge = block.get("trust_badge", "")
            title = block.get("title", "")
            content = block.get("content", "")

            lines.append(f"\n{'─' * 50}")
            lines.append(f"📌 {title} {trust_badge}")
            lines.append(f"{'─' * 50}")
            lines.append(content)

        lines.append("\n=== FIN DU CONTEXTE ===\n")
        return "\n".join(lines)

    def get_response_guard(self, orchestrator_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retourne les contraintes de réponse selon le score de trust.
        Le LLM doit respecter ces contraintes dans sa réponse.
        """
        trust_score = orchestrator_result.get("trust_score")
        if not trust_score:
            return {"can_diagnose": False, "can_recommend": True, "warning_required": True}

        label = trust_score.label
        return {
            "can_diagnose": trust_score.can_diagnose,
            "can_recommend": trust_score.can_recommend,
            "warning_required": label in (TrustLabel.WEAK, TrustLabel.INSUFFICIENT),
            "trust_label": label.value,
            "trust_score": trust_score.score,
        }

    # ─────────────────────────────────────────────
    # Privé
    # ─────────────────────────────────────────────

    def _build_llm_instructions(
        self,
        result: Dict[str, Any],
        ctx: Any,
    ) -> str:
        trust_score = result.get("trust_score")
        mode = result.get("mode", "")
        score = trust_score.score if trust_score else 0
        label = trust_score.label.value if trust_score else "insufficient"

        base = f"""
Instructions pour la réponse (Trust: {score}/100 — {label.upper()}) :
"""
        if score >= ctx.trust_threshold_strong:
            return base + """
- Tu peux formuler un diagnostic FERME basé sur les procédures canoniques validées N3
- Cite systématiquement les sources (numéros FR, IDs procédure)
- Structure : Diagnostic → Cause → Procédure de résolution → Risques
- Niveau de confiance : ÉLEVÉ ✅
"""
        elif score >= ctx.trust_threshold_medium:
            return base + """
- Tu peux proposer une hypothèse de diagnostic en indiquant qu'elle est à confirmer
- Cite les sources disponibles (clusters, FR partielles)
- Recommande des vérifications supplémentaires
- Structure : Hypothèse probable → Vérifications → Procédure suggérée
- Niveau de confiance : MOYEN ⚠️
- Ajoute : "Cette analyse est basée sur des patterns historiques non validés N3"
"""
        else:
            return base + """
- NE PAS formuler de diagnostic ferme — données insuffisantes
- Tu peux lister les observations techniques et proposer des pistes d'investigation
- Structure : Observations → Pistes → Actions immédiates recommandées
- Niveau de confiance : FAIBLE 🔶
- Ajoute systématiquement : "⚠️ Information non validée — investigation requise"
"""


# Singleton global
intelligence_orchestrator = IntelligenceOrchestrator()
