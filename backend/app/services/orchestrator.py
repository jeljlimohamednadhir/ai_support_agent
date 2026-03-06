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
from app.services.nlp.diagnostic_behavior import is_contextual_intent

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
        structured_ticket: Optional[Any] = None,
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

        # 4. Générer les instructions pour le LLM selon le trust / l'intention
        result["llm_instructions"] = self._build_llm_instructions(
            result, ctx, structured_ticket=structured_ticket
        )

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
        structured_ticket: Optional[Any] = None,
    ) -> str:
        trust_score = result.get("trust_score")
        mode = result.get("mode", "")
        score = trust_score.score if trust_score else 0
        label = trust_score.label.value if trust_score else "insufficient"

        base = f"""
Instructions pour ta réponse (Trust: {score}/100 — {label.upper()}) :
IMPORTANT : Synthétise le contexte ci-dessus en UNE SEULE réponse. Ne répète pas deux fois la même information. Ne duplique pas les sections.
"""
        # Branch 4 : contextual intent — answer from conversation history, no KB needed
        intent_type = structured_ticket.incident_type if structured_ticket else ""
        if is_contextual_intent(structured_ticket):
            if intent_type in ("ticket_summary", "summarize"):
                return base + """
- Utilise UNIQUEMENT l'historique de la conversation.
- Structure : **Problème signalé** → **Diagnostic effectué** → **Actions recommandées**
- Sois concis (5-10 lignes maximum). Ne recherche pas de nouvelle procédure.
"""
            elif intent_type in ("ticket_closing", "write_ticket_message"):
                return base + """
- Utilise UNIQUEMENT l'historique de la conversation.
- Produis DEUX sections :
  SECTION 1 — Résumé technique N3 : Incident | Cause | Action effectuée | Résultat.
  SECTION 2 — Message pour le dépositaire : message professionnel confirmant la résolution.
- Ton professionnel et neutre.
"""
            elif intent_type in ("log_investigation", "investigate_logs"):
                return base + """
- Fournis des informations opérationnelles concrètes (chemins de logs, commandes de consultation).
- Si des logs ont été fournis dans la conversation, analyse-les.
- Ne refuse pas cette question : c'est une demande opérationnelle légitime.
"""
            elif intent_type == "find_similar_tickets":
                return base + """
- Présente les tickets ou clusters similaires fournis dans le contexte.
- Format : ID | Date | Symptôme | Résolution appliquée.
- Identifie le pattern commun si plusieurs tickets correspondent.
- Si aucun ticket similaire : indique-le clairement et suggère des mots-clés de recherche.
"""
            elif intent_type == "find_jira":
                return base + """
- Présente les issues Jira trouvées dans le contexte : clé Jira | titre | statut | lien.
- Indique si l'issue est ouverte, en cours ou résolue.
- Si aucune issue Jira : propose d'en créer une et fournis les éléments clés à renseigner.
"""
            elif intent_type == "explain_jira":
                return base + """
- Lis le contenu de la carte Jira fournie dans le contexte.
- Reformule-le en langage clair et structuré :
  (1) Contexte / Système impacté
  (2) Problème décrit
  (3) Actions déjà effectuées
  (4) Ce qui reste à faire selon toi
- Sois factuel. Ne complète que ce qui est présent dans le ticket.
"""
            else:
                return base + """
- Utilise le contexte de la conversation pour répondre. Réponds en français.
"""

        if intent_type == "explain_data_model":
            return base + """
- INTERDICTIONS ABSOLUES :
  * NE GÉNÈRE AUCUNE REQUÊTE SQL (SELECT, FROM, WHERE, JOIN, etc.).
  * NE GÉNÈRE AUCUNE expression régulière (regex), séquence hexadécimale ou commande shell.
  * N'INVENTE AUCUN nom de colonne, de table ou de relation.
  * NE RÉPÈTE PAS deux fois la même section.

- Utilise UNIQUEMENT les noms de colonnes et tables tels qu'ils apparaissent EXACTEMENT dans le contexte KB (snippet_id: db-table-*).
- Si un élément n'est pas dans les sources, écris explicitement 'non disponible dans les sources'.

- FORMAT OBLIGATOIRE (respecte strictement cet ordre) :
  **Titre** : Explication Table `<nom_table>` — Synthèse N3
  **Vue d'ensemble** : [rôle en une phrase]
  **Clé primaire** : [nom exact depuis le KB]
  **Colonnes** (noms exacts du KB, liste EXHAUSTIVE) :
    - colonne (type) — description / FK vers table.colonne si applicable
  **Relations (FK)** :
    FK sortantes : colonne_locale → table_cible.colonne_cible
    FK entrantes : table_source.colonne_source → cette_table.colonne
  **Observations** : [anomalies/tickets Jira connus sur cette table]
  **Vérifications N3 recommandées** (TEXTE UNIQUEMENT — sans SQL, sans commande) :
    1. [description textuelle]
  **Sources** : [snippet_id / procedure_id / liens Jira — une seule fois]
  **Confiance** : MOYEN — à valider par l'ingénieur N3
"""

        if score >= ctx.trust_threshold_strong:
            return base + """
- Formule un diagnostic FERME basé sur les procédures canoniques validées N3
- Cite les sources (numéros FR) UNE SEULE FOIS à la fin
- Structure en UNE SEULE FOIS : **Diagnostic** → **Cause** → **Procédure de résolution** → **Risques**
- Termine par : "Niveau de confiance : ÉLEVÉ ✅ (Sources : ...)"
"""
        elif score >= ctx.trust_threshold_medium:
            return base + """
- Propose une hypothèse de diagnostic à confirmer
- Cite les sources disponibles UNE SEULE FOIS
- Structure en UNE SEULE FOIS : **Hypothèse** → **Vérifications** → **Procédure suggérée**
- Termine par : "Niveau de confiance : MOYEN ⚠️ — À valider N3"
"""
        else:
            return base + """
- Ne pas formuler de diagnostic ferme
- Structure en UNE SEULE FOIS : **Observations** → **Pistes** → **Actions recommandées**
- Termine par : "⚠️ Information non validée — investigation requise"
"""


# Singleton global
intelligence_orchestrator = IntelligenceOrchestrator()
