"""
Pipeline Mode 1 — FR Rich
Utilisé quand l'application a des FR de bonne qualité + procédures canoniques validées.
Flux : Query → CanonicalProcedure match → TrustEngine → Réponse structurée
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.app_context import ApplicationContext
from app.models.canonical import CanonicalProcedure, TrustLevel
from app.services.trust.trust_engine import trust_engine, TrustScore
from app.services.knowledge.vector_service import VectorService
from app.core.logging import get_logger

logger = get_logger(__name__)


class FrRichPipeline:
    """
    Pipeline Mode 1 : Knowledge Driven.
    S'appuie sur les CanonicalProcedures validées N3.
    Priorité : high_trust > medium_trust > vector search FR brutes
    """

    def __init__(self, app_context: ApplicationContext, vector_service: VectorService):
        self.ctx = app_context
        self.vector_service = vector_service
        _override = (app_context.extra_config or {}).get("knowledge_collection")
        self.collection = _override or f"{app_context.qdrant_collection_prefix or app_context.id.lower() + '_'}knowledge"

    async def search(
        self,
        query: str,
        db: Session,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """
        Recherche les procédures canoniques les plus pertinentes pour la query.
        Retourne un résultat structuré avec score de confiance.
        """
        results = {
            "mode": "FR_RICH",
            "app_id": self.ctx.id,
            "canonical_matches": [],
            "trust_score": None,
            "context_blocks": [],
            "sources": [],
        }

        # 1. Chercher les procédures high_trust en priorité
        high_trust_procs = db.query(CanonicalProcedure).filter(
            CanonicalProcedure.app_id == self.ctx.id,
            CanonicalProcedure.trust_level == TrustLevel.HIGH,
            CanonicalProcedure.is_active == True,
        ).all()

        # 2. Recherche vectorielle dans la collection de l'app
        vector_results = []
        try:
            vector_results = await self.vector_service.search_similar_code(
                query=query,
                top_k=top_k,
                collection_name=self.collection,
            )
        except Exception as e:
            logger.warning(f"[Mode1] Erreur recherche vectorielle: {e}")

        # 3. Matcher les procédures canoniques sur les codes d'erreur détectés
        matched_procedures = self._match_by_error_codes(query, high_trust_procs)
        if not matched_procedures:
            matched_procedures = self._match_by_symptoms(query, high_trust_procs)

        # 4. Scorer chaque match
        scored_matches = []
        for proc, match_score, matched_on in matched_procedures[:top_k]:
            trust = trust_engine.score_canonical_match(
                trust_level=proc.trust_level.value,
                match_score=match_score,
                usage_count=proc.usage_count,
                success_count=proc.success_count,
            )
            scored_matches.append({
                "procedure": proc,
                "match_score": match_score,
                "matched_on": matched_on,
                "trust": trust,
            })

        # 5. Trier par score de confiance
        scored_matches.sort(key=lambda x: x["trust"].score, reverse=True)

        # 6. Construire les blocs de contexte pour le LLM
        context_blocks = []
        sources = []

        for item in scored_matches:
            proc = item["procedure"]
            trust: TrustScore = item["trust"]

            block = self._build_context_block(proc, trust)
            context_blocks.append(block)
            sources.append({
                "id": proc.id,
                "title": proc.title,
                "trust_level": proc.trust_level.value,
                "trust_score": trust.score,
                "trust_label": trust.label.value,
                "source_fr_numbers": proc.source_fr_numbers or [],
            })

        # Ajouter les résultats vectoriels non couverts par canonical
        for vr in vector_results:
            meta = vr.get("metadata", {})
            if meta.get("type") == "resolution_fiche":
                fr_id = meta.get("fr_number", "")
                # Éviter les doublons avec les canonicals déjà présents
                already_covered = any(
                    fr_id in (s.get("source_fr_numbers") or [])
                    for s in sources
                )
                if not already_covered:
                    context_blocks.append({
                        "type": "fr_raw",
                        "title": meta.get("title", "FR sans titre"),
                        "content": vr.get("code", ""),
                        "trust_label": "low",
                        "trust_score": 20,
                    })
                    sources.append({
                        "id": fr_id,
                        "title": meta.get("title", ""),
                        "trust_level": "low",
                        "trust_score": 20,
                        "trust_label": "weak",
                        "source_fr_numbers": [fr_id],
                    })

        # Score global combiné
        all_trust_scores = [item["trust"] for item in scored_matches]
        global_trust = (
            trust_engine.score_combined(all_trust_scores)
            if all_trust_scores
            else trust_engine.score_canonical_match("low", 0.0)
        )

        results["canonical_matches"] = scored_matches
        results["trust_score"] = global_trust
        results["context_blocks"] = context_blocks
        results["sources"] = sources

        logger.info(
            f"[Mode1][{self.ctx.id}] {len(scored_matches)} canonical matches, "
            f"trust={global_trust.score}/100 ({global_trust.label.value})"
        )
        return results

    # ─────────────────────────────────────────────
    # Privé
    # ─────────────────────────────────────────────

    def _match_by_error_codes(
        self,
        query: str,
        procedures: List[CanonicalProcedure],
    ) -> List[tuple]:
        matches = []
        for proc in procedures:
            if not proc.error_codes:
                continue
            matched_codes = [
                code for code in proc.error_codes
                if code.lower() in query.lower()
            ]
            if matched_codes:
                score = min(len(matched_codes) / max(len(proc.error_codes), 1), 1.0)
                matches.append((proc, score, [f"error_code:{c}" for c in matched_codes]))
        return matches

    def _match_by_symptoms(
        self,
        query: str,
        procedures: List[CanonicalProcedure],
    ) -> List[tuple]:
        matches = []
        query_lower = query.lower()
        for proc in procedures:
            if not proc.symptoms:
                continue
            matched = [s for s in proc.symptoms if s.lower() in query_lower]
            if matched:
                score = len(matched) / max(len(proc.symptoms), 1)
                matches.append((proc, score, [f"symptom:{s}" for s in matched]))
        return sorted(matches, key=lambda x: x[1], reverse=True)

    def _build_context_block(
        self,
        proc: CanonicalProcedure,
        trust: TrustScore,
    ) -> Dict[str, Any]:
        trust_badge = {
            "strong": "✅ HIGH TRUST",
            "moderate": "⚠️ MEDIUM TRUST",
            "weak": "🔶 LOW TRUST",
            "insufficient": "❌ INSUFFICIENT",
        }.get(trust.label.value, "")

        return {
            "type": "canonical_procedure",
            "id": proc.id,
            "title": proc.title,
            "trust_badge": trust_badge,
            "trust_score": trust.score,
            "trust_label": trust.label.value,
            "content": self._format_procedure(proc),
            "risk_level": proc.risk_level.value,
            "source_fr_numbers": proc.source_fr_numbers or [],
        }

    def _format_procedure(self, proc: CanonicalProcedure) -> str:
        lines = [f"**{proc.title}**"]
        if proc.category:
            lines.append(f"Catégorie: {proc.category}")
        if proc.error_codes:
            lines.append(f"Codes d'erreur: {', '.join(proc.error_codes)}")
        if proc.symptoms:
            lines.append("\n**Symptômes:**")
            lines.extend(f"  - {s}" for s in proc.symptoms)
        if proc.root_causes:
            lines.append("\n**Causes probables:**")
            lines.extend(f"  - {c}" for c in proc.root_causes)
        if proc.diagnostic_checks:
            lines.append("\n**Vérifications à effectuer:**")
            lines.extend(f"  {i+1}. {c}" for i, c in enumerate(proc.diagnostic_checks))
        if proc.resolution_steps:
            lines.append("\n**Étapes de résolution:**")
            lines.extend(f"  {i+1}. {s}" for i, s in enumerate(proc.resolution_steps))
        return "\n".join(lines)
