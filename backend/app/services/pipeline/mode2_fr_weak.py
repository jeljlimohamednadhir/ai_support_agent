"""
Pipeline Mode 2 — FR Weak
Utilisé quand les FR existent mais sont de mauvaise qualité.
Flux : Tickets historiques → Clustering → Pattern extraction → Réponse prudente
"""
from typing import List, Dict, Any, Optional
import hashlib
import re
from collections import Counter
from sqlalchemy.orm import Session

from app.models.app_context import ApplicationContext
from app.models.canonical import CanonicalProcedure, TrustLevel
from app.services.trust.trust_engine import trust_engine
from app.services.knowledge.vector_service import VectorService
from app.core.logging import get_logger

logger = get_logger(__name__)


class FrWeakPipeline:
    """
    Pipeline Mode 2 : Pattern Mining.
    Quand les FR sont de mauvaise qualité, on mine les patterns depuis les tickets.
    Produit des pseudo-procédures avec confiance medium.
    """

    def __init__(self, app_context: ApplicationContext, vector_service: VectorService):
        self.ctx = app_context
        self.vector_service = vector_service
        self.collection = f"{app_context.qdrant_collection_prefix or app_context.id.lower() + '_'}knowledge"

    async def search(
        self,
        query: str,
        db: Session,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """
        Recherche hybride : canonical medium/low + tickets bruts.
        """
        results = {
            "mode": "FR_WEAK",
            "app_id": self.ctx.id,
            "canonical_matches": [],
            "ticket_clusters": [],
            "trust_score": None,
            "context_blocks": [],
            "sources": [],
        }

        # 1. Chercher les procédures medium+low trust (partiellement validées)
        partial_procs = db.query(CanonicalProcedure).filter(
            CanonicalProcedure.app_id == self.ctx.id,
            CanonicalProcedure.is_active == True,
        ).all()

        # 2. Recherche vectorielle dans tickets + FR brutes
        vector_results = []
        try:
            vector_results = await self.vector_service.search_similar_code(
                query=query,
                top_k=top_k * 2,
                collection_name=self.collection,
            )
        except Exception as e:
            logger.warning(f"[Mode2] Erreur recherche vectorielle: {e}")

        # 3. Extraire les patterns récurrents depuis les résultats vectoriels
        ticket_clusters = self._extract_ticket_patterns(vector_results)

        # 4. Matcher les procédures partielles
        scored_matches = []
        for proc in partial_procs:
            match_score, matched_on = self._match_procedure(query, proc)
            if match_score > 0.2:
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

        scored_matches.sort(key=lambda x: x["trust"].score, reverse=True)

        # 5. Scorer les clusters de tickets
        scored_clusters = []
        for cluster in ticket_clusters:
            trust = trust_engine.score_raw_ticket(
                ticket_count=cluster["count"],
                has_resolution=cluster["has_resolution"],
                keyword_match_count=cluster["keyword_matches"],
            )
            scored_clusters.append({**cluster, "trust": trust})

        # 6. Construire les blocs de contexte
        context_blocks = []
        sources = []

        for item in scored_matches[:top_k]:
            proc = item["procedure"]
            trust = item["trust"]
            context_blocks.append({
                "type": "partial_canonical",
                "title": proc.title,
                "trust_badge": "⚠️ MEDIUM TRUST — Non validé N3",
                "trust_score": trust.score,
                "trust_label": trust.label.value,
                "content": self._format_partial_procedure(proc),
                "source_fr_numbers": proc.source_fr_numbers or [],
            })
            sources.append({
                "id": proc.id,
                "title": proc.title,
                "trust_level": proc.trust_level.value,
                "trust_score": trust.score,
                "trust_label": trust.label.value,
                "source_fr_numbers": proc.source_fr_numbers or [],
            })

        for cluster in scored_clusters[:3]:
            trust = cluster["trust"]
            if trust.score > 10:
                context_blocks.append({
                    "type": "ticket_cluster",
                    "title": cluster["pattern"],
                    "trust_badge": "🔶 CLUSTER TICKETS — Non validé",
                    "trust_score": trust.score,
                    "trust_label": trust.label.value,
                    "content": self._format_cluster(cluster),
                    "ticket_count": cluster["count"],
                })
                sources.append({
                    "id": f"cluster_{cluster['hash']}",
                    "title": cluster["pattern"],
                    "trust_level": "low",
                    "trust_score": trust.score,
                    "trust_label": trust.label.value,
                    "ticket_count": cluster["count"],
                })

        # Score global
        all_scores = [item["trust"] for item in scored_matches]
        all_scores += [c["trust"] for c in scored_clusters]
        global_trust = (
            trust_engine.score_combined(all_scores)
            if all_scores
            else trust_engine.score_raw_ticket(0, False, 0)
        )

        results["canonical_matches"] = scored_matches
        results["ticket_clusters"] = scored_clusters
        results["trust_score"] = global_trust
        results["context_blocks"] = context_blocks
        results["sources"] = sources

        logger.info(
            f"[Mode2][{self.ctx.id}] {len(scored_matches)} canonicals, "
            f"{len(scored_clusters)} clusters, trust={global_trust.score}/100"
        )
        return results

    # ─────────────────────────────────────────────
    # Clustering léger des tickets vectoriels
    # ─────────────────────────────────────────────

    def _extract_ticket_patterns(self, vector_results: List[Dict]) -> List[Dict]:
        """
        Regroupe les tickets vectoriels par pattern d'erreur.
        Extraction simple basée sur les codes d'erreur et mots-clés.
        """
        patterns: Dict[str, Dict] = {}

        for result in vector_results:
            meta = result.get("metadata", {})
            if meta.get("type") != "jira_ticket":
                continue

            content = result.get("code", "") + " " + meta.get("summary", "")
            error_codes = re.findall(r'\b(\d{4})\b', content)
            keywords = self._extract_keywords(content)

            pattern_key = error_codes[0] if error_codes else (keywords[0] if keywords else "unknown")
            h = hashlib.md5(pattern_key.encode()).hexdigest()[:8]

            if h not in patterns:
                patterns[h] = {
                    "hash": h,
                    "pattern": pattern_key,
                    "count": 0,
                    "has_resolution": False,
                    "keyword_matches": 0,
                    "sample_tickets": [],
                    "common_keywords": [],
                }

            patterns[h]["count"] += 1
            if meta.get("status") in ("Resolved", "Closed", "Done"):
                patterns[h]["has_resolution"] = True
            if meta.get("summary"):
                patterns[h]["sample_tickets"].append(meta["summary"][:80])
            for kw in keywords:
                patterns[h]["keyword_matches"] += 1

        # Trier par fréquence
        return sorted(patterns.values(), key=lambda x: x["count"], reverse=True)

    def _extract_keywords(self, text: str) -> List[str]:
        """Extrait les mots-clés techniques d'un texte ticket"""
        stop_words = {"le", "la", "les", "de", "du", "un", "une", "des", "est", "sur",
                      "dans", "par", "en", "pour", "avec", "que", "qui", "pas", "ne"}
        words = re.findall(r'\b[a-zA-Z_]{3,}\b', text.lower())
        return [w for w in words if w not in stop_words][:10]

    def _match_procedure(self, query: str, proc: CanonicalProcedure) -> tuple:
        """Match simple procédure vs query"""
        query_lower = query.lower()
        matched_on = []
        score = 0.0

        if proc.error_codes:
            matched = [c for c in proc.error_codes if c in query_lower]
            if matched:
                score += 0.5
                matched_on += [f"error_code:{c}" for c in matched]

        if proc.symptoms:
            matched = [s for s in proc.symptoms if s.lower() in query_lower]
            if matched:
                score += 0.3 * (len(matched) / len(proc.symptoms))
                matched_on += [f"symptom:{s}" for s in matched]

        if proc.title and proc.title.lower() in query_lower:
            score += 0.2
            matched_on.append(f"title:{proc.title}")

        return min(score, 1.0), matched_on

    def _format_partial_procedure(self, proc: CanonicalProcedure) -> str:
        lines = [f"**{proc.title}** ⚠️ (non validé N3)"]
        if proc.symptoms:
            lines.append("\n**Symptômes observés:**")
            lines.extend(f"  - {s}" for s in proc.symptoms)
        if proc.diagnostic_checks:
            lines.append("\n**Vérifications suggérées:**")
            lines.extend(f"  {i+1}. {c}" for i, c in enumerate(proc.diagnostic_checks))
        if proc.resolution_steps:
            lines.append("\n**Résolution probable (à confirmer):**")
            lines.extend(f"  {i+1}. {s}" for i, s in enumerate(proc.resolution_steps))
        return "\n".join(lines)

    def _format_cluster(self, cluster: Dict) -> str:
        lines = [
            f"**Pattern détecté: {cluster['pattern']}**",
            f"Occurrences dans l'historique: {cluster['count']} tickets",
        ]
        if cluster.get("sample_tickets"):
            lines.append("\nExemples de tickets:")
            for t in cluster["sample_tickets"][:3]:
                lines.append(f"  - {t}")
        if cluster.get("has_resolution"):
            lines.append("\n✅ Résolutions connues existent dans l'historique")
        return "\n".join(lines)
