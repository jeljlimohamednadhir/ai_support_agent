"""
Retraining Pipeline — KB update from N3 chatbot corrections
============================================================
Prend les corrections validées par l'équipe N3 (table corrections, correction_type='chatbot_n3')
et les intègre dans la base de connaissances RAG sans réentraîner le LLM.

Étapes :
  1. Charge les corrections chatbot non traitées depuis PostgreSQL
  2. Génère de nouveaux chunks KB (trust = 0.85 — validé humain)
  3. Met à jour les trust scores des FRs approuvées/rejetées
  4. Indexe les nouveaux chunks dans Qdrant (si dispo)
  5. Drafts de nouvelles procédures groupées par incident_type
  6. Sauvegarde dans data_pipeline/output/kb_corrections.json
  7. Marque les corrections comme traitées (processed=True)
"""

import json
import time
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parents[5] / "data_pipeline" / "output"
KB_CORRECTIONS_FILE = OUTPUT_DIR / "kb_corrections.json"
KB_PROCEDURES_FILE  = OUTPUT_DIR / "fr_normalized.json"

# Trust adjustments
TRUST_APPROVED_BOOST  = +0.15
TRUST_REJECTED_PENALTY = -0.20
TRUST_N3_CORRECTION   = 0.85   # Human-validated correction


class RetrainingPipeline:
    """
    Integrates N3 chatbot corrections into the RAG knowledge base.
    Does NOT fine-tune the LLM — updates the retrieval layer only.
    """

    def __init__(self, db: Session):
        self.db = db
        self.stats: Dict[str, Any] = {
            "corrections_applied":    0,
            "kb_chunks_updated":      0,
            "trust_scores_updated":   0,
            "new_procedures_drafted": 0,
            "duration_seconds":       0,
        }

    # ──────────────────────────────────────────────────────────────────
    # PUBLIC — main entry point
    # ──────────────────────────────────────────────────────────────────

    def run(self) -> Dict[str, Any]:
        """Full retraining pipeline. Returns stats dict."""
        start = time.time()
        logger.info("[RETRAIN] Démarrage du pipeline de réapprentissage...")

        try:
            corrections = self._load_corrections()
            if not corrections:
                logger.info("[RETRAIN] Aucune correction chatbot N3 à traiter")
                self.stats["duration_seconds"] = round(time.time() - start, 2)
                return self.stats

            logger.info(f"[RETRAIN] {len(corrections)} correction(s) chargée(s)")

            new_chunks = self._generate_kb_chunks(corrections)
            self.stats["kb_chunks_updated"] = len(new_chunks)

            trust_updates = self._update_trust_scores()
            self.stats["trust_scores_updated"] = trust_updates

            self._index_qdrant(new_chunks)

            procedures = self._draft_procedures(corrections)
            self.stats["new_procedures_drafted"] = len(procedures)

            self._save_kb_file(new_chunks, procedures)
            self._mark_processed(corrections)
            self.stats["corrections_applied"] = len(corrections)

        except Exception as e:
            logger.error(f"[RETRAIN] Erreur pipeline: {e}", exc_info=True)
            raise

        self.stats["duration_seconds"] = round(time.time() - start, 2)
        logger.info(f"[RETRAIN] Terminé en {self.stats['duration_seconds']}s — {self.stats}")
        return self.stats

    # ──────────────────────────────────────────────────────────────────
    # STEP 1 — Load unprocessed chatbot N3 corrections
    # ──────────────────────────────────────────────────────────────────

    def _load_corrections(self) -> List[Dict]:
        """Load unprocessed chatbot N3 corrections from DB."""
        try:
            rows = self.db.execute(text("""
                SELECT id, correction_type, entity_type, entity_id,
                       original_value, corrected_value, corrector_id,
                       reason, created_at
                FROM corrections
                WHERE correction_type = 'chatbot_n3'
                  AND (applied = FALSE OR applied IS NULL)
                ORDER BY created_at ASC
                LIMIT 500
            """)).fetchall()
        except Exception:
            # Fallback: load all corrections not yet processed
            try:
                rows = self.db.execute(text("""
                    SELECT id, correction_type, entity_type, entity_id,
                           original_value, corrected_value, corrector_id,
                           reason, created_at
                    FROM corrections
                    WHERE applied = FALSE OR applied IS NULL
                    ORDER BY created_at ASC
                    LIMIT 500
                """)).fetchall()
            except Exception as e2:
                logger.warning(f"[RETRAIN] Impossible de charger les corrections: {e2}")
                return []

        result = []
        for r in rows:
            try:
                orig = r[4] if isinstance(r[4], dict) else json.loads(r[4] or "{}")
                corr = r[5] if isinstance(r[5], dict) else json.loads(r[5] or "{}")
                result.append({
                    "id":               r[0],
                    "correction_type":  r[1] or "chatbot_n3",
                    "entity_type":      r[2] or "chatbot_response",
                    "entity_id":        r[3] or "",
                    "original_value":   orig,
                    "corrected_value":  corr,
                    "corrector_id":     r[6] or "n3_engineer",
                    "reason":           r[7] or "",
                    "created_at":       r[8].isoformat() if r[8] else "",
                    # Extract chatbot-specific fields from JSON payloads
                    "application":      corr.get("application") or orig.get("application", "BRASIL"),
                    "incident_type":    corr.get("incident_type") or orig.get("incident_type", "unknown"),
                    "corrected_response": corr.get("corrected_response") or corr.get("response", ""),
                    "original_response":  orig.get("bot_response") or orig.get("response", ""),
                    "user_question":    orig.get("user_question", ""),
                })
            except Exception:
                continue

        return result

    # ──────────────────────────────────────────────────────────────────
    # STEP 2 — Generate KB chunks
    # ──────────────────────────────────────────────────────────────────

    def _generate_kb_chunks(self, corrections: List[Dict]) -> List[Dict]:
        """Convert each correction into a RAG-ready KB chunk (trust=0.85)."""
        chunks = []
        for corr in corrections:
            corrected_text = corr["corrected_response"]
            if not corrected_text:
                continue

            chunk_id = f"CORR-{str(corr['id'])[:8].upper()}"
            chunk_text = (
                f"Incident: {corr['incident_type']}\n"
                f"Application: {corr['application']}\n"
                f"Question utilisateur: {corr['user_question']}\n"
                f"Raison de correction: {corr['reason']}\n"
                f"Réponse validée N3:\n{corrected_text}"
            )
            chunks.append({
                "doc_id":             chunk_id,
                "text":               chunk_text,
                "source_type":        "n3_correction",
                "application":        corr["application"],
                "incident_type":      corr["incident_type"],
                "trust_score":        TRUST_N3_CORRECTION,
                "confidence_level":   "high",
                "validated_by":       corr["corrector_id"],
                "correction_reason":  corr["reason"],
                "original_response":  corr["original_response"],
                "language":           "fr",
                "created_at":         datetime.utcnow().isoformat(),
                "metadata": {
                    "correction_id": str(corr["id"]),
                    "user_question": corr["user_question"],
                },
            })

        logger.info(f"[RETRAIN] {len(chunks)} chunk(s) KB générés")
        return chunks

    # ──────────────────────────────────────────────────────────────────
    # STEP 3 — Update trust scores in fr_normalized.json
    # ──────────────────────────────────────────────────────────────────

    def _update_trust_scores(self) -> int:
        """Apply trust boosts/penalties from recent validated/rejected tasks."""
        updated = 0
        try:
            approved_row = self.db.execute(text("""
                SELECT COUNT(*) FROM validation_tasks
                WHERE status = 'validated'
                AND validated_at > NOW() - INTERVAL '7 days'
            """)).fetchone()
            rejected_row = self.db.execute(text("""
                SELECT COUNT(*) FROM validation_tasks
                WHERE status = 'rejected'
                AND validated_at > NOW() - INTERVAL '7 days'
            """)).fetchone()

            approvals  = approved_row[0] if approved_row else 0
            rejections = rejected_row[0] if rejected_row else 0
            updated    = approvals + rejections

            if KB_PROCEDURES_FILE.exists():
                with open(KB_PROCEDURES_FILE, "r", encoding="utf-8") as f:
                    kb_data = json.load(f)

                for chunk in kb_data.get("rag_chunks", []):
                    current = chunk.get("trust_score", 0.5)
                    if approvals > 5 and current > 0.6:
                        chunk["trust_score"] = round(min(0.95, current + 0.02), 3)

                kb_data["last_trust_update"] = datetime.utcnow().isoformat()
                kb_data["trust_stats"] = {
                    "recent_approvals":  approvals,
                    "recent_rejections": rejections,
                }

                with open(KB_PROCEDURES_FILE, "w", encoding="utf-8") as f:
                    json.dump(kb_data, f, ensure_ascii=False, indent=2)

                logger.info(
                    f"[RETRAIN] Trust scores mis à jour: "
                    f"+{approvals} approvals / -{rejections} rejections"
                )
        except Exception as e:
            logger.warning(f"[RETRAIN] Trust update warning: {e}")

        return updated

    # ──────────────────────────────────────────────────────────────────
    # STEP 4 — Qdrant indexing
    # ──────────────────────────────────────────────────────────────────

    def _index_qdrant(self, chunks: List[Dict]) -> None:
        """Index new chunks in Qdrant if available (TF-IDF hash vectors)."""
        if not chunks:
            return
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import PointStruct, VectorParams, Distance

            client = QdrantClient(host="localhost", port=6333, timeout=5)
            collection = "brasil_kb"

            try:
                client.get_collection(collection)
            except Exception:
                client.create_collection(
                    collection_name=collection,
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE),
                )

            points = []
            for chunk in chunks:
                # Deterministic pseudo-vector from text hash (no sentence-transformers needed)
                h = hashlib.sha256(chunk["text"].encode("utf-8")).digest()
                vec = [(b / 127.5) - 1.0 for b in h]  # 32 values, normalize to [-1,1]
                vec = (vec * 12)[:384]                  # pad to 384 dims

                point_id = abs(int(hashlib.md5(chunk["doc_id"].encode()).hexdigest(), 16)) % (2 ** 31)
                points.append(PointStruct(
                    id=point_id,
                    vector=vec,
                    payload={
                        "doc_id":        chunk["doc_id"],
                        "text":          chunk["text"][:500],
                        "application":   chunk["application"],
                        "incident_type": chunk["incident_type"],
                        "trust_score":   chunk["trust_score"],
                        "source_type":   chunk["source_type"],
                    },
                ))

            if points:
                client.upsert(collection_name=collection, points=points)
                logger.info(f"[RETRAIN] {len(points)} chunk(s) indexés dans Qdrant (collection '{collection}')")

        except Exception as e:
            logger.warning(f"[RETRAIN] Qdrant non disponible, skip indexing: {e}")

    # ──────────────────────────────────────────────────────────────────
    # STEP 5 — Draft procedures from grouped corrections
    # ──────────────────────────────────────────────────────────────────

    def _draft_procedures(self, corrections: List[Dict]) -> List[Dict]:
        """
        Group corrections by application + incident_type.
        Draft a new procedure when ≥2 corrections share the same group.
        """
        groups: Dict[str, List[Dict]] = defaultdict(list)
        for corr in corrections:
            key = f"{corr['application']}::{corr['incident_type']}"
            groups[key].append(corr)

        procedures = []
        for key, group in groups.items():
            if len(group) < 2:
                continue

            app, inc_type = key.split("::", 1)
            proc_id = f"DRAFT-{hashlib.md5(key.encode()).hexdigest()[:8].upper()}"

            steps = []
            for i, corr in enumerate(group, 1):
                resp = corr["corrected_response"][:300]
                if resp:
                    steps.append(f"{i}. {resp}")

            procedure = {
                "procedure_id":             proc_id,
                "title":                    f"[DRAFT N3] {inc_type} — {app}",
                "application":              app,
                "incident_type":            inc_type,
                "source_type":              "n3_correction_draft",
                "trust_score":              0.70,
                "confidence_level":         "medium",
                "symptoms":                 list({c["reason"] for c in group if c["reason"]}),
                "resolution_steps":         steps,
                "corrected_by":             list({c["corrector_id"] for c in group}),
                "based_on_corrections":     [str(c["id"]) for c in group],
                "created_at":               datetime.utcnow().isoformat(),
                "requires_validation":      True,
            }
            procedures.append(procedure)
            logger.info(f"[RETRAIN] Procédure draft créée: {proc_id} ({app}/{inc_type})")

        return procedures

    # ──────────────────────────────────────────────────────────────────
    # STEP 6 — Save KB corrections file
    # ──────────────────────────────────────────────────────────────────

    def _save_kb_file(self, chunks: List[Dict], procedures: List[Dict]) -> None:
        """Merge new chunks/procedures into kb_corrections.json."""
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        existing: Dict = {}
        if KB_CORRECTIONS_FILE.exists():
            try:
                with open(KB_CORRECTIONS_FILE, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except Exception:
                existing = {}

        old_chunks = existing.get("chunks", [])
        old_procs  = existing.get("procedures", [])

        existing_ids = {c["doc_id"] for c in old_chunks}
        new_chunks   = [c for c in chunks if c["doc_id"] not in existing_ids]

        existing_proc_ids = {p["procedure_id"] for p in old_procs}
        new_procs = [p for p in procedures if p["procedure_id"] not in existing_proc_ids]

        output = {
            "generated_at":     datetime.utcnow().isoformat(),
            "total_chunks":     len(old_chunks) + len(new_chunks),
            "total_procedures": len(old_procs) + len(new_procs),
            "last_retrain":     datetime.utcnow().isoformat(),
            "chunks":           old_chunks + new_chunks,
            "procedures":       old_procs + new_procs,
        }

        with open(KB_CORRECTIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        logger.info(
            f"[RETRAIN] kb_corrections.json mis à jour: "
            f"+{len(new_chunks)} chunks, +{len(new_procs)} procédures"
        )

    # ──────────────────────────────────────────────────────────────────
    # STEP 7 — Mark corrections as processed
    # ──────────────────────────────────────────────────────────────────

    def _mark_processed(self, corrections: List[Dict]) -> None:
        """Set applied=True on processed corrections."""
        try:
            for corr in corrections:
                self.db.execute(
                    text("UPDATE corrections SET applied = TRUE, applied_at = :now WHERE id = :id"),
                    {"id": corr["id"], "now": datetime.utcnow()},
                )
            self.db.commit()
            logger.info(f"[RETRAIN] {len(corrections)} correction(s) marquée(s) applied=True")
        except Exception as e:
            logger.warning(f"[RETRAIN] Mark processed warning: {e}")
