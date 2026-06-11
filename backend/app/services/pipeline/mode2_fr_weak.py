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

_SCHEMA_TABLE_TYPES = {"database_table", "schema_table", "schema_table_alias"}


def _build_direct_schema_hits(query: str, top_k: int) -> List[Dict[str, Any]]:
    """Resolve explicit table names directly from the generated schema pack."""
    try:
        from app.services.chatbot.brasil_schema_knowledge import (
            REAL_SQL_TABLES,
            TABLE_ALIAS_TO_CANONICAL,
            table_to_document,
        )
    except Exception:
        return []

    query_lower = query.lower()
    tokens = set(re.findall(r"\bt_[a-z0-9_]+\b", query_lower))
    hits: List[Dict[str, Any]] = []

    for token in tokens:
        canonical = TABLE_ALIAS_TO_CANONICAL.get(token, token)
        if canonical not in REAL_SQL_TABLES:
            continue

        doc = table_to_document(canonical)
        doc["table_name"] = canonical
        doc["title"] = canonical
        doc["_text"] = doc.get("text", "")
        hits.append({
            "id": canonical,
            "code": doc.get("text", ""),
            "metadata": doc,
            "distance": 0.0,
            "original_score": 1.0,
            "boost_applied": 0.0,
            "match_type": "exact_direct",
        })

    return hits[:top_k]


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
        # Utilise knowledge_collection de extra_config si défini (ex: code_knowledge)
        _override = (app_context.extra_config or {}).get("knowledge_collection")
        self.collection = _override or f"{prefix}knowledge"

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
        VECTOR_SCORE_THRESHOLD = 0.35  # Seuil adapté aux embeddings français (cosine ~0.3–0.6)

        # Détecter si la requête est une question de SCHÉMA DB (t_xxx, table, colonnes)
        # ou une question de PROCÉDURE/INCIDENT (suppression impossible, comment faire...)
        import re as _re_intent
        _is_schema_query = bool(_re_intent.search(
            r'\bt_[a-z_]+\b|c.est quoi la table|qu.est.ce que la table|'
            r'colonnes?|structure|champs?|schéma|schema|définition de la table',
            query, _re_intent.IGNORECASE
        ))
        _is_procedure_query = bool(_re_intent.search(
            r'impossible|comment|proc.dure|FR\s*\d+|\u00e9tape|débloquer|supprimer|'
            r'faire quoi|je fais quoi|comment faire|résoudre|escalad',
            query, _re_intent.IGNORECASE
        ))
        # Si les deux sont vrais ou aucun, on est dans le cas générique
        _schema_priority = _is_schema_query and not _is_procedure_query

        # 3-pre. Détection requête de schéma (intent tech_inference_schema)
        # Si la requête parle d'une table BRASIL, chercher directement dans code_knowledge
        # par nom/mot-clé AVANT la recherche vectorielle générale, pour éviter que des
        # procédures génériques ne supplantent les vraies docs de table.
        _schema_table_results = []
        try:
            _schema_table_results = await self.vector_service.search_similar_code(
                query=query, top_k=top_k,
            )
            # Garder uniquement les résultats de type database_table
            _db_table_hits = [
                r for r in _schema_table_results
                if r.get("metadata", {}).get("type") in _SCHEMA_TABLE_TYPES
            ]
            if _db_table_hits:
                logger.info(f"[Mode2] {len(_db_table_hits)} table(s) schema trouvée(s) via search_similar_code (schema_priority={_schema_priority})")
        except Exception as e:
            logger.warning(f"[Mode2] Erreur recherche schema: {e}")
            _db_table_hits = []

        _direct_schema_hits = _build_direct_schema_hits(query, top_k)
        if _direct_schema_hits:
            seen_ids = {r.get("id") for r in _db_table_hits}
            for hit in _direct_schema_hits:
                if hit.get("id") not in seen_ids:
                    _db_table_hits.insert(0, hit)
                    seen_ids.add(hit.get("id"))
            logger.info(f"[Mode2] {len(_direct_schema_hits)} table(s) résolue(s) directement depuis le schéma généré")

        vector_results = []
        try:
            # 3a. Recherche vectorielle dans brasil_canonical
            raw_results = await self._search_canonical_collection(query, top_k * 2)
            vector_results = [r for r in raw_results if r.get("score", 0) >= VECTOR_SCORE_THRESHOLD]
            if not vector_results and raw_results:
                # Score seuil non atteint mais des résultats existent — prendre le top-3 quand même
                best = max(r.get('score', 0) for r in raw_results)
                logger.info(f"[Mode2] Scores vectoriels sous seuil (max={best:.3f}) — utilisation du top-3 brasil_canonical")
                # Utiliser les top-3 résultats même sous le seuil (evite la réponse générique)
                vector_results = sorted(raw_results, key=lambda r: r.get("score", 0), reverse=True)[:3]
            if not raw_results:
                # Fallback priorité 1a : FRs structurées (brasil_frs) — enrichissement sémantique
                frs_results = await self._search_brasil_frs(query, top_k * 2)
                if frs_results:
                    vector_results = frs_results
                # Fallback priorité 1b : recherche dans brasil_procedures (FRs indexées)
                proc_results = await self._search_brasil_procedures(query, top_k * 2)
                if proc_results:
                    seen_ids = {r.get("id") for r in vector_results}
                    for pr in proc_results:
                        if pr.get("id") not in seen_ids:
                            vector_results.append(pr)
                            seen_ids.add(pr.get("id"))
                # Fallback priorité 2 : code_knowledge (tables de schéma)
                if _db_table_hits:
                    seen_ids = {r.get("id") for r in vector_results}
                    for hit in _db_table_hits:
                        if hit.get("id") not in seen_ids:
                            vector_results.append(hit)
                            seen_ids.add(hit.get("id"))
                if not vector_results:
                    vector_results = await self.vector_service.search_similar_code(
                        query=query, top_k=top_k * 2,
                    )
            else:
                # brasil_canonical a retourné des résultats — compléter avec brasil_frs + brasil_procedures
                frs_results = await self._search_brasil_frs(query, top_k)
                proc_results = await self._search_brasil_procedures(query, top_k)
                seen_ids = {r.get("id") for r in vector_results}
                for pr in (frs_results + proc_results):
                    if pr.get("id") not in seen_ids:
                        vector_results.append(pr)
                        seen_ids.add(pr.get("id"))
                # Tables de schéma ajoutées seulement si vraie requête schema
                # (pas d'insertion en tête pour les requêtes d'incident/procédure)
                if _db_table_hits and _schema_priority:
                    for hit in _db_table_hits:
                        if hit.get("id") not in seen_ids:
                            vector_results.insert(0, hit)
                            seen_ids.add(hit.get("id"))
        except Exception as e:
            logger.warning(f"[Mode2] Erreur recherche vectorielle: {e}")

        # 3b. Recherche textuelle PostgreSQL — complément si vecteurs insuffisants
        text_results = self._search_by_keywords(query, partial_procs, top_k)
        # Fusionner selon la priorité détectée :
        # - _schema_priority=True  : tables DB en tête (question de schéma)
        # - _schema_priority=False : procédures FR en tête (question d'incident/procédure)
        seen_titles = set()
        merged_results = []

        if _schema_priority:
            # Question de schéma : tables DB en tête absolue
            for hit in _db_table_hits:
                meta = hit.get('metadata', {})
                t = (meta.get('table_name') or meta.get('title') or str(hit.get('id', ''))).lower()
                if t not in seen_titles:
                    merged_results.append(hit)
                    seen_titles.add(t)
        else:
            # Question d'incident/procédure : procédures FR en tête
            # 1. Procédures vectorielles (brasil_procedures)
            for vr in vector_results:
                meta = vr.get('metadata', {})
                if meta.get('type') == 'canonical_procedure':
                    t = (meta.get('title') or meta.get('fr_number') or str(vr.get('id', ''))).lower()
                    if t not in seen_titles:
                        merged_results.append(vr)
                        seen_titles.add(t)
            # 2. Matches textuels forts (score >= 0.30)
            strong_text = [tr for tr in text_results if tr.get('score', 0) >= 0.30]
            for tr in strong_text:
                meta = tr.get('metadata', {})
                t = (meta.get('title') or meta.get('table_name') or meta.get('name') or '').lower()
                if t not in seen_titles:
                    merged_results.append(tr)
                    seen_titles.add(t)
            # 3. Tables de schéma en complément (pas en tête)
            for hit in _db_table_hits:
                meta = hit.get('metadata', {})
                t = (meta.get('table_name') or meta.get('title') or str(hit.get('id', ''))).lower()
                if t not in seen_titles:
                    merged_results.append(hit)
                    seen_titles.add(t)

        # Compléter avec le reste des résultats vectoriels non encore inclus
        for vr in vector_results:
            meta = vr.get('metadata', {})
            t = (meta.get('title') or meta.get('table_name') or meta.get('name') or str(vr.get('id', ''))).lower()
            if t not in seen_titles:
                merged_results.append(vr)
                seen_titles.add(t)

        # Enfin les matches textuels faibles non encore inclus
        strong_text = [tr for tr in text_results if tr.get('score', 0) >= 0.30]
        for tr in text_results:
            meta = tr.get('metadata', {})
            t = (meta.get('title') or meta.get('table_name') or meta.get('name') or '').lower()
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
                # search_similar_code retourne 'original_score', les autres retournent 'score'
                match_score = vr.get("original_score") or vr.get("score", 0.5)
                tl_raw = meta.get("trust_level", "MEDIUM")
                # Normaliser trust_level : HIGH→high, MEDIUM→medium, LOW→low
                tl_norm = tl_raw.lower() if tl_raw else "medium"
                # Pour les tables DB, booster le score si c'est une correspondance exacte
                if meta.get("type") in _SCHEMA_TABLE_TYPES and vr.get("match_type") == "exact":
                    match_score = max(match_score, 0.9)
                trust = trust_engine.score_canonical_match(
                    trust_level=tl_norm,
                    match_score=match_score,
                    usage_count=0,
                    success_count=0,
                )
                scored_matches.append({
                    "procedure": None,
                    "payload": meta,
                    "raw_code": vr.get("code", ""),  # contenu brut (table SQL, ticket, etc.)
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
            raw_code = item.get("raw_code", "")
            trust = item["trust"]

            # Titre et contenu depuis payload Qdrant ou objet DB
            title = (
                payload.get("title")
                or payload.get("table_name")
                or payload.get("name")
                or (proc.title if proc else "Procédure inconnue")
            )
            fr_numbers = payload.get("source_fr_numbers") or (proc.source_fr_numbers if proc else []) or []
            trust_lv = payload.get("trust_level") or (proc.trust_level.value if proc else "medium")

            # Formater le contenu
            if proc:
                content = self._format_partial_procedure(proc)
            elif raw_code and payload.get("type") in _SCHEMA_TABLE_TYPES:
                # Résultat schema BRASIL : utiliser le code brut (describe_table / inject_brasil_knowledge)
                content = f"**Schéma BRASIL — Table `{title}`**\n\n{raw_code}"
            elif payload.get("type") in _SCHEMA_TABLE_TYPES:
                # type schéma mais sans raw_code → tenter une résolution directe
                _tbl = payload.get("table_name") or payload.get("name") or title
                try:
                    from app.services.chatbot.brasil_schema_knowledge import describe_table as _dt
                    _desc = _dt(_tbl)
                    content = f"**Schéma BRASIL — Table `{_tbl}`**\n\n{_desc}"
                except Exception:
                    content = self._format_payload_procedure(payload)
            else:
                content = self._format_payload_procedure(payload)
                if raw_code and content.strip() in (
                    "**Procédure inconnue** ⚠️ (non validé N3)",
                    f"**{title}**",
                ):
                    content = raw_code  # fallback sur le code brut si la proc est vide

            _is_schema_hit = payload.get("type") in _SCHEMA_TABLE_TYPES
            context_blocks.append({
                "type": "partial_canonical",
                "title": title,
                "trust_badge": (
                    "✅ SCHÉMA BRASIL VÉRIFIÉ — Extrait de brasil_prod"
                    if _is_schema_hit else
                    "⚠️ MEDIUM TRUST — Non validé N3"
                ),
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
    # Recherche dans brasil_procedures (FRs indexées)
    # ─────────────────────────────────────────────

    async def _search_brasil_procedures(self, query: str, top_k: int) -> List[Dict]:
        """
        Recherche dans brasil_procedures :
        1. Lookup direct par numéro FR (ex: 'FR 189', 'FR189')
        2. Recherche vectorielle sémantique
        Retourne des résultats formatés compatibles avec le pipeline.
        """
        import re as _re
        results = []
        # FIX #8: Check collection existence before querying
        if hasattr(self, '_brasil_procedures_disabled') and self._brasil_procedures_disabled:
            return []
        try:
            from qdrant_client import QdrantClient
            client = QdrantClient(url=self.vector_service.qdrant_url)
            try:
                client.get_collection("brasil_procedures")
            except Exception:
                logger.info("[Mode2] Collection brasil_procedures inexistante - désactivée pour cette session")
                self._brasil_procedures_disabled = True
                return []
            from qdrant_client import QdrantClient
            from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchAny

            client = QdrantClient(host='localhost', port=6333)

            # ── 1. Lookup FR number ────────────────────────────────────────
            fr_match = _re.search(r'\bFR[\s\-]?(\d{1,4})\b', query, _re.IGNORECASE)
            if fr_match:
                fr_num = fr_match.group(1)
                fr_variants = [f"FR {fr_num}", f"FR{fr_num}", f"FR-{fr_num}"]
                try:
                    # Scroll tous les points brasil_procedures et filtrer par fr_number
                    all_pts, _ = client.scroll(
                        collection_name="brasil_procedures",
                        limit=200,
                        with_payload=True,
                    )
                    for pt in all_pts:
                        p = pt.payload or {}
                        pt_fr = p.get("fr_number", "")
                        pt_aliases = p.get("fr_aliases") or []
                        if pt_fr in fr_variants or any(a in fr_variants for a in pt_aliases):
                            results.append({
                                "id": str(pt.id),
                                "score": 0.99,
                                "metadata": self._format_procedure_payload(p),
                            })
                    if results:
                        logger.info(f"[Mode2] Lookup FR {fr_num}: {len(results)} résultat(s) dans brasil_procedures")
                        return results[:top_k]
                except Exception as e_fr:
                    logger.warning(f"[Mode2] Lookup FR number échoué: {e_fr}")

            # ── 2. Recherche vectorielle dans brasil_procedures ────────────
            try:
                vec = self.vector_service.embedding_model.encode(query).tolist()
                vr = client.query_points(
                    collection_name="brasil_procedures",
                    query=vec,
                    limit=top_k,
                    with_payload=True,
                )
                for r in vr.points:
                    if r.score >= 0.40:
                        p = r.payload or {}
                        results.append({
                            "id": str(r.id),
                            "score": r.score,
                            "metadata": self._format_procedure_payload(p),
                        })
                if results:
                    logger.info(f"[Mode2] Vector brasil_procedures: {len(results)} résultat(s) (seuil 0.40)")
            except Exception as e_vec:
                logger.warning(f"[Mode2] Recherche vectorielle brasil_procedures échouée: {e_vec}")

        except Exception as e:
            logger.warning(f"[Mode2] _search_brasil_procedures error: {e}")
        return results[:top_k]

    async def _search_brasil_frs(self, query: str, top_k: int) -> List[Dict]:
        """
        Recherche dans brasil_frs (FRs structurées par fr_structurer.py).
        1. Lookup direct par numéro FR si présent dans la requête
        2. Recherche vectorielle sémantique
        3. Filtre supplémentaire par pattern_signature / trigger_signals
        """
        import re as _re
        results = []
        try:
            from qdrant_client import QdrantClient
            client = QdrantClient(host='localhost', port=6333)

            # Vérifier que la collection existe
            existing = [c.name for c in client.get_collections().collections]
            if "brasil_frs" not in existing:
                return []

            # ── 1. Lookup FR number ──────────────────────────────────────
            fr_match = _re.search(r'\bFR[\s\-]?(\d{1,4}[A-Za-z]?)\b', query, _re.IGNORECASE)
            if fr_match:
                fr_num = fr_match.group(1)
                fr_variants = [f"FR {fr_num}", f"FR{fr_num}", f"FR-{fr_num}"]
                try:
                    all_pts, _ = client.scroll(
                        collection_name="brasil_frs",
                        limit=300,
                        with_payload=True,
                    )
                    for pt in all_pts:
                        p = pt.payload or {}
                        pt_fr = p.get("fr_number", "")
                        pt_aliases = p.get("fr_aliases") or []
                        if pt_fr in fr_variants or any(a in fr_variants for a in pt_aliases):
                            results.append({
                                "id": str(pt.id),
                                "score": 0.99,
                                "metadata": self._format_fr_structured_payload(p),
                            })
                    if results:
                        logger.info(f"[Mode2] brasil_frs lookup FR {fr_num}: {len(results)} résultat(s)")
                        return results[:top_k]
                except Exception as e_fr:
                    logger.warning(f"[Mode2] brasil_frs lookup FR échoué: {e_fr}")

            # ── 2. Recherche vectorielle ──────────────────────────────────
            try:
                vec = self.vector_service.embedding_model.encode(query).tolist()
                vr = client.query_points(
                    collection_name="brasil_frs",
                    query=vec,
                    limit=top_k,
                    with_payload=True,
                )
                for r in vr.points:
                    if r.score >= 0.38:
                        p = r.payload or {}
                        results.append({
                            "id": str(r.id),
                            "score": r.score,
                            "metadata": self._format_fr_structured_payload(p),
                        })
                if results:
                    logger.info(f"[Mode2] brasil_frs vector: {len(results)} résultat(s) (seuil 0.38)")
            except Exception as e_vec:
                logger.warning(f"[Mode2] brasil_frs recherche vectorielle échouée: {e_vec}")

            # ── 3. Keyword fallback — trigger_signals + intents + pattern_signature ────
            # Used when vector score < 0.38 (equipment name noise degrades embedding similarity).
            # Loads brasil_fr_structured.json directly to avoid Qdrant round-trip.
            if not results:
                from pathlib import Path as _Path
                import json as _json
                _INTENT_KWS = {
                    "delete_equipment": ["supprim", "effac", "retir", "enlev"],
                    "update_service":   ["modif", "chang", "mis \u00e0 jour"],
                    "diagnose":         ["diagn", "analys", "v\u00e9rif", "probl", "erreur", "panne"],
                    "check_status":     ["\u00e9tat", "status", "v\u00e9rif"],
                    "install":          ["install", "d\u00e9ploy", "configur"],
                    "transfer":         ["transfer", "migr", "d\u00e9plac"],
                    "reset":            ["reset", "r\u00e9init", "red\u00e9marr"],
                }
                _master = _Path(__file__).parents[3] / "data" / "brasil_fr_structured.json"
                _kw_matches: list = []
                try:
                    if _master.exists():
                        _frs = _json.loads(_master.read_text(encoding="utf-8"))
                        _q = query.lower()
                        for _fr in _frs:
                            _score = 0.0
                            # trigger_signals
                            for _sig in _fr.get("trigger_signals", []):
                                if _sig.lower() in _q:
                                    _score += 0.40
                                elif any(w in _q for w in _sig.lower().split() if len(w) > 4):
                                    _score += 0.15
                            # intents
                            for _intent in _fr.get("intents", []):
                                for _kw in _INTENT_KWS.get(_intent, [_intent.replace("_", " ")]):
                                    if _kw in _q:
                                        _score += 0.20
                                        break
                            # evidence_tags
                            for _tag in _fr.get("evidence_tags", []):
                                if str(_tag).lower() in _q:
                                    _score += 0.10
                            # entities EQUIPMENT
                            for _ent in _fr.get("entities", []):
                                _boost = 0.25 if _ent.get("type") == "EQUIPMENT" else 0.08
                                for _ex in _ent.get("examples", []):
                                    if str(_ex).lower() in _q:
                                        _score += _boost
                            # title words
                            _tw = [w for w in _fr.get("title", "").lower().split() if len(w) > 4]
                            _score += sum(1 for w in _tw if w in _q) * 0.06
                            if _score >= 0.20:
                                _kw_matches.append((_score, _fr))
                        _kw_matches.sort(key=lambda x: x[0], reverse=True)
                        for _sc, _fr in _kw_matches[:top_k]:
                            # Build resolution_steps from 'resolution' list
                            _res = _fr.get("resolution_steps") or [
                                a.get("action", str(a)) if isinstance(a, dict) else str(a)
                                for a in _fr.get("resolution", [])
                            ]
                            _diag = _fr.get("diagnostic_steps") or [
                                s.get("step", str(s)) if isinstance(s, dict) else str(s)
                                for s in _fr.get("diagnostic", [])
                            ]
                            _syms = _fr.get("symptoms") or [
                                {"text": s.get("text", str(s)) if isinstance(s, dict) else str(s)}
                                for s in _fr.get("symptoms", [])
                            ]
                            _payload = {
                                "title": _fr.get("title", _fr.get("id", "")),
                                "fr_number": _fr.get("id", ""),
                                "type": "fr_structured",
                                "symptoms": [s.get("text", str(s)) if isinstance(s, dict) else str(s) for s in _syms],
                                "diagnostic_steps": _diag,
                                "resolution_steps": _res,
                                "root_causes": [_fr.get("root_cause", {}).get("label", "")] if _fr.get("root_cause") else [],
                                "root_cause_class": _fr.get("root_cause", {}).get("class", ""),
                                "sql_queries": [
                                    s.get("step", str(s)) if isinstance(s, dict) else str(s)
                                    for s in _fr.get("diagnostic", [])
                                    if (s.get("type", "") if isinstance(s, dict) else "") == "query"
                                ],
                                "tables_involved": _fr.get("evidence_tags", []),
                                "blocking_conditions": _fr.get("blocking_conditions", []),
                                "non_blocking_conditions": _fr.get("non_blocking_conditions", []),
                                "evidence_tags": _fr.get("evidence_tags", []),
                                "trigger_signals": _fr.get("trigger_signals", []),
                                "pattern_signature": _fr.get("pattern_signature", ""),
                                "trust_level": "HIGH" if _fr.get("confidence_score", 0) >= 0.90 else "MEDIUM",
                                "source_fr_numbers": [_fr.get("id", "")],
                                "applications_involved": ["BRASIL"],
                                "sfd_rules": [
                                    r.get("rule", str(r)) if isinstance(r, dict) else str(r)
                                    for r in _fr.get("sfd_rules", [])
                                ],
                            }
                            results.append({"id": _fr.get("id", ""), "score": _sc, "metadata": _payload})
                        if results:
                            logger.info(f"[Mode2] brasil_frs keyword fallback: {len(results)} FR(s) (scores: {[round(s,2) for s,_ in _kw_matches[:top_k]]})")
                except Exception as _kw_err:
                    logger.warning(f"[Mode2] brasil_frs keyword fallback error: {_kw_err}")

        except Exception as e:
            logger.warning(f"[Mode2] _search_brasil_frs error: {e}")
        return results[:top_k]

    def _format_fr_structured_payload(self, p: dict) -> dict:
        """Formate un payload brasil_frs (FR structurée) en métadonnées standard."""
        return {
            "type":                 "fr_structured",
            "title":               p.get("title", p.get("fr_number", "")),
            "fr_number":           p.get("fr_number", ""),
            "symptoms":            p.get("symptoms") or [],
            "diagnostic_steps":    p.get("diagnostic_steps") or [],
            "resolution_steps":    p.get("resolution_steps") or [],
            "root_causes":         [p.get("root_cause_label", "")] if p.get("root_cause_label") else [],
            "root_cause_class":    p.get("root_cause_class", ""),
            "sql_queries":         p.get("sql_queries") or [],
            "tables_involved":     p.get("tables_involved") or [],
            "evidence_tags":       p.get("evidence_tags") or [],
            "error_codes":         [],
            "blocking_conditions": p.get("blocking_conditions") or [],
            "non_blocking_conditions": p.get("non_blocking_conditions") or [],
            "pattern_signature":   p.get("pattern_signature", ""),
            "trigger_signals":     p.get("trigger_signals") or [],
            "intents":             p.get("intents") or [],
            "risk_level":          "HIGH" if p.get("root_cause_class") == "C" else "MEDIUM",
            "trust_level":         "HIGH" if p.get("confidence_score", 0) >= 0.90 else "MEDIUM",
            "source_fr_numbers":   p.get("source_fr_numbers") or ([p["fr_number"]] if p.get("fr_number") else []),
            "category":            (p.get("intents") or [""])[0],
            "applications_involved": p.get("applications_involved") or ["BRASIL"],
            "sfd_rules":           p.get("sfd_rules") or [],
        }

    def _format_procedure_payload(self, p: dict) -> dict:
        """Formate un payload brasil_procedures en métadonnées standard."""
        return {
            "type": "canonical_procedure",
            "title": p.get("title", p.get("fr_number", "")),
            "fr_number": p.get("fr_number", ""),
            "symptoms": p.get("symptoms") or [],
            "diagnostic_steps": p.get("diagnostic_steps") or [],
            "resolution_steps": p.get("resolution_steps") or [],
            "root_causes": p.get("root_causes") or [],
            "sql_queries": p.get("sql_queries") or [],
            "tables_involved": p.get("tables_involved") or [],
            "error_codes": p.get("error_codes_referenced") or p.get("exceptions_referenced") or [],
            "risk_level": p.get("sensitivity", ""),
            "trust_level": "HIGH" if p.get("trust_score", 0) >= 0.80 else "MEDIUM",
            "source_fr_numbers": [p.get("fr_number")] if p.get("fr_number") else [],
            "category": p.get("incident_type", ""),
            "escalation_path": p.get("escalation_path", ""),
            "applications_involved": p.get("applications_involved") or [],
        }

    # ─────────────────────────────────────────────
    # Recherche vectorielle dans la collection canonical
    # ─────────────────────────────────────────────

    async def _search_canonical_collection(self, query: str, top_k: int) -> List[Dict]:
        """Recherche dans la collection brasil_canonical via Qdrant — réutilise le client existant."""
        try:
            # Réutiliser le client singleton VectorService au lieu d'en créer un nouveau
            client = self.vector_service.client
            if client is None:
                logger.warning(f"[Mode2] VectorService client non disponible — skip {self.canonical_collection}")
                return []
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
        fr_number = payload.get("fr_number", "")
        header = f"**{title}**" if not fr_number else f"**{title}** ({fr_number})"
        lines = [header]

        symptoms = payload.get("symptoms") or []
        if symptoms:
            lines.append("\n**Symptômes observés:**")
            lines.extend(f"  - {s}" for s in symptoms if s)

        error_codes = payload.get("error_codes") or []
        if error_codes:
            lines.append(f"\n**Codes/Exceptions associés:** {', '.join(str(c) for c in error_codes)}")

        diagnostic_steps = payload.get("diagnostic_steps") or []
        if diagnostic_steps:
            lines.append("\n**Étapes de diagnostic:**")
            for i, s in enumerate(diagnostic_steps[:5], 1):
                lines.append(f"  {i}. {s}")

        root_causes = payload.get("root_causes") or []
        if root_causes:
            lines.append("\n**Causes racines identifiées:**")
            lines.extend(f"  - {c}" for c in root_causes if c)

        resolution_steps = payload.get("resolution_steps") or []
        if resolution_steps:
            lines.append("\n**Résolution:**")
            for i, s in enumerate(resolution_steps, 1):
                lines.append(f"  {i}. {s}")

        sql_queries = payload.get("sql_queries") or []
        if sql_queries:
            lines.append("\n**Requêtes SQL clés:**")
            for q in sql_queries[:4]:
                lines.append(f"  ```sql\n  {q}\n  ```")

        tables = payload.get("tables_involved") or []
        if tables:
            lines.append(f"\n**Tables impliquées:** {', '.join(f'`{t}`' for t in tables)}")

        fr_sources = payload.get("source_fr_numbers") or ([fr_number] if fr_number else [])
        if fr_sources:
            lines.append(f"\n**Source:** {', '.join(str(f) for f in fr_sources)}")

        escalation = payload.get("escalation_path", "")
        if escalation:
            lines.append(f"\n**Escalade:** {escalation}")

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
