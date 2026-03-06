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
        # Collection canonique (brasil_canonical, etc.)
        prefix = app_context.qdrant_collection_prefix or (app_context.id.lower() + '_')
        self.canonical_collection = f"{prefix}canonical"
        # Fallback : ancienne convention _knowledge
        self.collection = f"{prefix}knowledge"

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

        # 2. Détection requête hors-contexte (salutations, questions génériques)
        OFF_TOPIC_PATTERNS = [
            r'^(bonjour|bonsoir|salut|hello|hi|coucou|hey)\b',
            r'^(merci|au revoir|bye|bonne journée|bonne soirée)\b',
            r'^(comment ça va|ça va|comment allez|comment vas)',
            r'^(oui|non|ok|d\'accord|vu|compris)\s*$',
        ]
        import re as _re
        query_stripped = query.strip().lower()
        is_off_topic = any(_re.match(p, query_stripped) for p in OFF_TOPIC_PATTERNS)

        if is_off_topic:
            logger.info(f"[Mode2] Requête hors-contexte détectée: '{query[:40]}'")
            results["trust_score"] = trust_engine.score_raw_ticket(0, False, 0)
            results["off_topic"] = True
            return results

        # 3. Recherche hybride : vectorielle Qdrant + textuelle PostgreSQL
        VECTOR_SCORE_THRESHOLD = 0.55  # Seuil réduit car vecteurs courts

        vector_results = []
        try:
            # 3a. Recherche vectorielle dans brasil_canonical
            raw_results = await self._search_canonical_collection(query, top_k * 2)
            vector_results = [r for r in raw_results if r.get("score", 0) >= VECTOR_SCORE_THRESHOLD]
            if not vector_results and raw_results:
                best = max(r.get('score', 0) for r in raw_results)
                logger.info(f"[Mode2] Scores vectoriels trop faibles (max={best:.3f}) — activation recherche textuelle")
            if not raw_results:
                # Fallback : ancienne collection _knowledge
                vector_results = await self.vector_service.search_similar_code(
                    query=query, top_k=top_k * 2, collection_name=self.collection,
                )
        except Exception as e:
            logger.warning(f"[Mode2] Erreur recherche vectorielle: {e}")

        # 3b. Recherche textuelle PostgreSQL — complément si vecteurs insuffisants
        text_results = self._search_by_keywords(query, partial_procs, top_k)
        # Fusionner : les résultats textuels viennent EN PREMIER si bon score,
        # les vecteurs complètent ensuite
        seen_titles = set()
        merged_results = []

        # D'abord les matches textuels forts (score >= 0.30)
        strong_text = [tr for tr in text_results if tr.get('score', 0) >= 0.30]
        for tr in strong_text:
            t = tr.get('metadata', {}).get('title', '').lower()
            if t not in seen_titles:
                merged_results.append(tr)
                seen_titles.add(t)

        # Ensuite les résultats vectoriels
        for vr in vector_results:
            t = vr.get('metadata', {}).get('title', '').lower()
            if t not in seen_titles:
                merged_results.append(vr)
                seen_titles.add(t)

        # Enfin les matches textuels plus faibles non encore inclus
        for tr in text_results:
            t = tr.get('metadata', {}).get('title', '').lower()
            if t not in seen_titles:
                merged_results.append(tr)
                seen_titles.add(t)

        vector_results = merged_results
        if text_results:
            logger.info(f"[Mode2] Hybride: {len(strong_text)} textuels forts + {len(vector_results)} total")

        # 4. Extraire les patterns récurrents depuis les résultats vectoriels
        ticket_clusters = self._extract_ticket_patterns(vector_results)

        # 4. Construire les matches depuis les résultats vectoriels (payload direct)
        scored_matches = []

        if vector_results:
            for vr in vector_results[:top_k]:
                meta = vr.get("metadata", {})
                match_score = vr.get("score", 0.5)
                tl_raw = meta.get("trust_level", "MEDIUM")
                # Normaliser trust_level : HIGH→high, MEDIUM→medium, LOW→low
                tl_norm = tl_raw.lower() if tl_raw else "medium"
                trust = trust_engine.score_canonical_match(
                    trust_level=tl_norm,
                    match_score=match_score,
                    usage_count=0,
                    success_count=0,
                )
                scored_matches.append({
                    "procedure": None,   # pas besoin de l'objet DB
                    "payload": meta,
                    "match_score": match_score,
                    "matched_on": ["vector_search"],
                    "trust": trust,
                })
        else:
            # Fallback keyword si Qdrant vide
            proc_by_title = {p.title.lower(): p for p in partial_procs}
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
                        "payload": None,
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
            proc = item.get("procedure")
            payload = item.get("payload") or {}
            trust = item["trust"]

            # Titre et contenu depuis payload Qdrant ou objet DB
            title = payload.get("title") or (proc.title if proc else "Procédure inconnue")
            fr_numbers = payload.get("source_fr_numbers") or (proc.source_fr_numbers if proc else []) or []
            trust_lv = payload.get("trust_level") or (proc.trust_level.value if proc else "medium")

            # Formater le contenu
            if proc:
                content = self._format_partial_procedure(proc)
            else:
                content = self._format_payload_procedure(payload)

            context_blocks.append({
                "type": "partial_canonical",
                "title": title,
                "trust_badge": "⚠️ MEDIUM TRUST — Non validé N3",
                "trust_score": trust.score,
                "trust_label": trust.label.value,
                "content": content,
                "source_fr_numbers": fr_numbers,
            })
            sources.append({
                "id": payload.get("id") or (str(proc.id) if proc else "unknown"),
                "title": title,
                "trust_level": trust_lv,
                "trust_score": trust.score,
                "trust_label": trust.label.value,
                "source_fr_numbers": fr_numbers,
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
    # Recherche vectorielle dans la collection canonical
    # ─────────────────────────────────────────────

    async def _search_canonical_collection(self, query: str, top_k: int) -> List[Dict]:
        """Recherche dans la collection brasil_canonical via Qdrant directement."""
        try:
            from qdrant_client import QdrantClient
            client = QdrantClient(
                host=self.vector_service.client.host if hasattr(self.vector_service.client, 'host') else 'localhost',
                port=self.vector_service.client.port if hasattr(self.vector_service.client, 'port') else 6333,
            )
            vec = self.vector_service.embedding_model.encode(query).tolist()
            results = client.query_points(
                collection_name=self.canonical_collection,
                query=vec,
                limit=top_k,
                with_payload=True,
            )
            formatted = []
            for r in results.points:
                p = r.payload or {}
                formatted.append({
                    "id": str(r.id),
                    "score": r.score,
                    "metadata": {
                        "type": "canonical_procedure",
                        "title": p.get("title", ""),
                        "symptoms": p.get("symptoms") or [],
                        "error_codes": p.get("error_codes") or [],
                        "resolution_steps": p.get("resolution_steps") or [],
                        "risk_level": p.get("risk_level", ""),
                        "trust_level": p.get("trust_level", "MEDIUM"),
                        "source_fr_numbers": p.get("source_fr_numbers") or [],
                        "category": p.get("category", ""),
                    },
                })
            logger.info(f"[Mode2] {len(formatted)} résultats depuis {self.canonical_collection}")
            return formatted
        except Exception as e:
            logger.warning(f"[Mode2] Échec recherche {self.canonical_collection}: {e}")
            return []

    def _search_by_keywords(self, query: str, procs: list, top_k: int) -> List[Dict]:
        """
        Recherche textuelle sur les procédures en mémoire.
        Calcule un score de correspondance mot-clé entre la requête et
        le titre + error_codes + category de chaque procédure.
        """
        import re as _re
        import unicodedata

        def normalize(s: str) -> str:
            s = s.lower()
            s = unicodedata.normalize('NFD', s)
            s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
            return s

        q_words = set(_re.findall(r'\w{3,}', normalize(query)))
        # Stopwords techniques à ignorer
        stopwords = {'les', 'des', 'une', 'que', 'qui', 'sur', 'dans', 'avec', 'pour',
                     'mais', 'est', 'pas', 'veux', 'faut', 'peut', 'faire'}
        q_words -= stopwords
        if not q_words:
            return []

        scored = []
        for proc in procs:
            # Texte indexé : titre + codes erreur + catégorie
            idx_parts = [proc.title or '']
            if proc.error_codes and isinstance(proc.error_codes, list):
                idx_parts.extend([str(c) for c in proc.error_codes])
            if proc.category:
                idx_parts.append(proc.category)
            if proc.symptoms and isinstance(proc.symptoms, list):
                idx_parts.extend([s for s in proc.symptoms[:3] if isinstance(s, str)])
            idx_text = normalize(' '.join(idx_parts))
            idx_words = set(_re.findall(r'\w{3,}', idx_text))

            # Score = intersection / union (Jaccard) pondérée par fréquence
            common = q_words & idx_words
            if not common:
                continue
            score = len(common) / max(len(q_words), 1)
            # Bonus si le titre contient un mot-clé de la requête
            title_words = set(_re.findall(r'\w{3,}', normalize(proc.title or '')))
            title_hits = len(q_words & title_words)
            score += title_hits * 0.15

            if score >= 0.15:
                trust_lv = proc.trust_level.value if proc.trust_level else 'MEDIUM'
                scored.append((score, {
                    'id': str(proc.id),
                    'score': min(score, 0.95),
                    'metadata': {
                        'type': 'canonical_procedure',
                        'title': proc.title,
                        'symptoms': proc.symptoms or [],
                        'error_codes': proc.error_codes or [],
                        'resolution_steps': proc.resolution_steps or [],
                        'risk_level': proc.risk_level or '',
                        'trust_level': trust_lv,
                        'source_fr_numbers': proc.source_fr_numbers or [],
                        'category': proc.category or '',
                    },
                }))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = [item for _, item in scored[:top_k]]
        if results:
            logger.info(f"[Mode2] Recherche textuelle: {len(results)} correspondances " +
                       f"({', '.join(r['metadata']['title'][:30] for r in results[:3])})")
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

    def _format_payload_procedure(self, payload: Dict) -> str:
        """Formate une procédure depuis le payload Qdrant directement"""
        title = payload.get("title", "Procédure inconnue")
        lines = [f"**{title}** ⚠️ (non validé N3)"]

        symptoms = payload.get("symptoms") or []
        if symptoms:
            lines.append("\n**Symptômes observés:**")
            lines.extend(f"  - {s}" for s in symptoms if s)

        error_codes = payload.get("error_codes") or []
        if error_codes:
            lines.append(f"\n**Codes d'erreur associés:** {', '.join(str(c) for c in error_codes)}")

        resolution_steps = payload.get("resolution_steps") or []
        if resolution_steps:
            lines.append("\n**Résolution probable (à confirmer):**")
            for i, s in enumerate(resolution_steps):
                lines.append(f"  {i+1}. {s}")

        fr_numbers = payload.get("source_fr_numbers") or []
        if fr_numbers:
            lines.append(f"\n**Sources FR:** {', '.join(str(f) for f in fr_numbers)}")

        return "\n".join(lines)

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
