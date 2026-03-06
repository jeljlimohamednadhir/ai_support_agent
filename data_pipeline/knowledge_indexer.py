"""
Knowledge Indexer — Indexes log knowledge and N3 procedures into Qdrant.

Reads:
  - data_pipeline/output/log_knowledge.json   (log-derived knowledge records)
  - data_pipeline/output/procedures.json      (generated N3 procedures)

Creates / updates Qdrant collections:
  brasil_log_patterns  — one point per log knowledge record
  brasil_procedures    — one point per N3 procedure

Each point payload follows the full metadata schema required for RAG filtering:
  application, incident_type, source_type, trust_score, related_systems,
  exception_names, error_codes, procedure_id, catalog_validated

Usage:
  python data_pipeline/knowledge_indexer.py
  python data_pipeline/knowledge_indexer.py --dry-run
  python data_pipeline/knowledge_indexer.py --collection procedures
"""
import json
import sys
import uuid
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

BACKEND_DIR = Path(__file__).parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

LOG_KNOWLEDGE_FILE = Path(__file__).parent / "output" / "log_knowledge.json"
PROCEDURES_FILE    = Path(__file__).parent / "output" / "procedures.json"

# Qdrant collection names
COLLECTION_LOG_PATTERNS = "brasil_log_patterns"
COLLECTION_PROCEDURES   = "brasil_procedures"

# Trust gate: skip points below this score
MIN_TRUST_SCORE = 0.35

# Embedding dimension (matches the deployed model)
VECTOR_SIZE = 384

# Batch size for upsert
BATCH_SIZE = 32


# ─────────────────────────────────────────────────────────────────────────────
# Embedding helper
# ─────────────────────────────────────────────────────────────────────────────

_embedding_model = None

def get_embedding_model():
    """Load the sentence transformer model (singleton)."""
    global _embedding_model
    if _embedding_model is not None:
        return _embedding_model

    import os
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

    try:
        from sentence_transformers import SentenceTransformer
        cache_dir = Path(BACKEND_DIR).parent / "data" / "models"
        _embedding_model = SentenceTransformer(
            "paraphrase-multilingual-MiniLM-L12-v2",
            cache_folder=str(cache_dir),
        )
        print(f"  ✅ Modèle d'embedding chargé (dim={_embedding_model.get_sentence_embedding_dimension()})")
        return _embedding_model
    except Exception as e:
        print(f"  ⚠️  SentenceTransformer non disponible: {e}")
        return None


def embed_text(text: str, model) -> List[float]:
    """Embed a text string. Returns zero vector on failure."""
    if model is None:
        return [0.0] * VECTOR_SIZE
    try:
        vec = model.encode(text, show_progress_bar=False)
        return vec.tolist()
    except Exception:
        return [0.0] * VECTOR_SIZE


def build_log_pattern_text(record: Dict) -> str:
    """Build the text to embed for a log knowledge record."""
    parts = []
    if record.get("exception"):
        parts.append(f"Exception: {record['exception']}")
    if record.get("error_pattern") and "<CATALOG>" not in record.get("error_pattern", ""):
        parts.append(f"Pattern: {record['error_pattern'][:200]}")
    if record.get("probable_root_cause"):
        parts.append(f"Cause: {record['probable_root_cause'][:200]}")
    if record.get("component"):
        parts.append(f"Composant: {record['component']}")
    parts.append(f"Application: {record.get('application', 'BRASIL')}")
    parts.append(f"Type: {record.get('incident_type', '')}")
    return " | ".join(parts)


def build_procedure_text(proc: Dict) -> str:
    """Build the text to embed for a procedure (maximizes retrieval surface)."""
    parts = []
    parts.append(f"Titre: {proc.get('title', '')}")
    parts.append(f"Type incident: {proc.get('incident_type', '')}")
    parts.append(f"Applications: {', '.join(proc.get('applications_involved', []))}")

    symptoms = proc.get("symptoms", [])
    if symptoms:
        parts.append(f"Symptômes: {'; '.join(symptoms[:4])}")

    causes = proc.get("root_causes", [])
    if causes:
        parts.append(f"Causes: {'; '.join(causes[:2])}")

    excs = proc.get("exceptions_referenced", [])
    if excs:
        parts.append(f"Exceptions: {', '.join(excs)}")

    codes = proc.get("error_codes_referenced", [])
    if codes:
        parts.append(f"Codes erreur: {', '.join(codes)}")

    steps = proc.get("diagnostic_steps", [])
    if steps:
        step_texts = [
            s.get("action", "") if isinstance(s, dict) else str(s)
            for s in steps[:3]
        ]
        parts.append(f"Étapes: {'; '.join(step_texts[:3])}")

    return " | ".join(p for p in parts if p.strip())


# ─────────────────────────────────────────────────────────────────────────────
# Qdrant client
# ─────────────────────────────────────────────────────────────────────────────

def get_qdrant_client():
    """Connect to Qdrant and return client."""
    import os
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams

        host = os.getenv("QDRANT_HOST", "localhost")
        port = int(os.getenv("QDRANT_PORT", "6333"))

        client = QdrantClient(host=host, port=port, timeout=10)

        # Ensure collections exist
        for coll_name in [COLLECTION_LOG_PATTERNS, COLLECTION_PROCEDURES]:
            try:
                client.get_collection(coll_name)
                print(f"  ✅ Collection '{coll_name}' existante")
            except Exception:
                client.create_collection(
                    collection_name=coll_name,
                    vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
                )
                print(f"  ✅ Collection '{coll_name}' créée")

        return client
    except Exception as e:
        print(f"  ❌ Qdrant non disponible: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Indexing functions
# ─────────────────────────────────────────────────────────────────────────────

def index_log_patterns(
    records: List[Dict],
    client,
    model,
    dry_run: bool = False,
) -> int:
    """Index log knowledge records into brasil_log_patterns collection."""
    from qdrant_client.models import PointStruct

    indexed = 0
    skipped = 0
    batch: List[PointStruct] = []

    for record in records:
        trust = record.get("trust_score", 0.0)
        if trust < MIN_TRUST_SCORE:
            skipped += 1
            continue

        text = build_log_pattern_text(record)
        vector = embed_text(text, model)

        point = PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_DNS, record.get("record_id", text))),
            vector=vector,
            payload={
                "record_id":        record.get("record_id", ""),
                "exception":        record.get("exception", ""),
                "error_pattern":    record.get("error_pattern", "")[:300],
                "application":      record.get("application", "BRASIL"),
                "component":        record.get("component", ""),
                "incident_type":    record.get("incident_type", ""),
                "severity":         record.get("severity", "medium"),
                "related_systems":  record.get("related_systems", []),
                "trust_score":      trust,
                "frequency":        record.get("frequency", 0),
                "source_type":      record.get("source_type", "log_derived"),
                "catalog_validated": record.get("catalog_validated", False),
                "probable_root_cause": record.get("probable_root_cause", "")[:500],
                "diagnostic_actions": record.get("diagnostic_actions", [])[:5],
                "resolution_actions": record.get("resolution_actions", [])[:5],
                "first_seen":       record.get("first_seen", ""),
                "last_seen":        record.get("last_seen", ""),
                "indexed_at":       datetime.utcnow().isoformat(),
            },
        )
        batch.append(point)

        if len(batch) >= BATCH_SIZE:
            if not dry_run and client:
                client.upsert(collection_name=COLLECTION_LOG_PATTERNS, points=batch)
            indexed += len(batch)
            batch = []

    # Flush remaining
    if batch:
        if not dry_run and client:
            client.upsert(collection_name=COLLECTION_LOG_PATTERNS, points=batch)
        indexed += len(batch)

    print(f"  ✅ {indexed} log patterns indexés (ignorés: {skipped} trust<{MIN_TRUST_SCORE})")
    return indexed


def index_procedures(
    procedures: List[Dict],
    client,
    model,
    dry_run: bool = False,
) -> int:
    """Index N3 procedures into brasil_procedures collection."""
    from qdrant_client.models import PointStruct

    indexed = 0
    skipped = 0
    batch: List[PointStruct] = []

    for proc in procedures:
        trust = proc.get("trust_score", 0.0)
        if trust < MIN_TRUST_SCORE:
            skipped += 1
            continue

        text = build_procedure_text(proc)
        vector = embed_text(text, model)

        # Flatten diagnostic steps to strings for payload
        raw_steps = proc.get("diagnostic_steps", [])
        steps_flat = []
        for s in raw_steps[:8]:
            if isinstance(s, dict):
                action = s.get("action", "")
                tool   = s.get("tool", "")
                steps_flat.append(f"{action} [{tool}]" if tool else action)
            else:
                steps_flat.append(str(s))

        point = PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_DNS, proc.get("procedure_id", text))),
            vector=vector,
            payload={
                "procedure_id":          proc.get("procedure_id", ""),
                "title":                 proc.get("title", ""),
                "incident_type":         proc.get("incident_type", ""),
                "application":           (proc.get("applications_involved") or ["BRASIL"])[0],
                "applications_involved": proc.get("applications_involved", []),
                "symptoms":              proc.get("symptoms", [])[:5],
                "diagnostic_steps":      steps_flat,
                "root_causes":           proc.get("root_causes", [])[:3],
                "resolution_steps":      proc.get("resolution_steps", [])[:5],
                "escalation_path":       proc.get("escalation_path", ""),
                "exceptions_referenced": proc.get("exceptions_referenced", []),
                "error_codes_referenced": proc.get("error_codes_referenced", []),
                "trust_score":           trust,
                "ticket_count":          proc.get("ticket_count", 0),
                "cluster_id":            proc.get("cluster_id", ""),
                "source_types":          proc.get("source_types", []),
                "version":               proc.get("version", "1.0"),
                "last_updated":          proc.get("last_updated", ""),
                "indexed_at":            datetime.utcnow().isoformat(),
            },
        )
        batch.append(point)

        if len(batch) >= BATCH_SIZE:
            if not dry_run and client:
                client.upsert(collection_name=COLLECTION_PROCEDURES, points=batch)
            indexed += len(batch)
            batch = []

    if batch:
        if not dry_run and client:
            client.upsert(collection_name=COLLECTION_PROCEDURES, points=batch)
        indexed += len(batch)

    print(f"  ✅ {indexed} procédures indexées (ignorées: {skipped} trust<{MIN_TRUST_SCORE})")
    return indexed


# ─────────────────────────────────────────────────────────────────────────────
# Main pipeline
# ─────────────────────────────────────────────────────────────────────────────

def run(
    collection: Optional[str] = None,
    dry_run: bool = False,
) -> bool:
    """
    Main indexing pipeline.

    Args:
        collection: "logs", "procedures", or None (both)
        dry_run: If True, compute embeddings but don't upsert into Qdrant
    """
    # Load data
    log_records = []
    procedures  = []

    if collection in (None, "logs"):
        if LOG_KNOWLEDGE_FILE.exists():
            with open(LOG_KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            log_records = data.get("records", [])
            print(f"  📂 {len(log_records)} log knowledge records chargés")
        else:
            print(f"  ⚠️  log_knowledge.json introuvable — skip log patterns")

    if collection in (None, "procedures"):
        if PROCEDURES_FILE.exists():
            with open(PROCEDURES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            procedures = data.get("procedures", [])
            print(f"  📂 {len(procedures)} procédures chargées")
        else:
            print(f"  ⚠️  procedures.json introuvable — skip procedures")

    if not log_records and not procedures:
        print("  ❌ Aucune donnée à indexer")
        return False

    # Load model
    print("  🧠 Chargement du modèle d'embedding...")
    model = get_embedding_model()

    # Connect to Qdrant
    client = None
    if not dry_run:
        print("  🔌 Connexion à Qdrant...")
        client = get_qdrant_client()
        if client is None and not dry_run:
            print("  ⚠️  Qdrant inaccessible — basculement en mode DRY-RUN")
            dry_run = True

    if dry_run:
        print("  🔍 Mode DRY-RUN activé — pas d'écriture dans Qdrant")

    # Index
    total_indexed = 0

    if log_records:
        print(f"\n  📋 Indexation des log patterns ({len(log_records)} records)...")
        total_indexed += index_log_patterns(log_records, client, model, dry_run)

    if procedures:
        print(f"\n  📋 Indexation des procédures N3 ({len(procedures)} procédures)...")
        total_indexed += index_procedures(procedures, client, model, dry_run)

    print(f"\n  📊 Total indexé: {total_indexed} points")
    if not dry_run:
        print(f"     Collections: {COLLECTION_LOG_PATTERNS}, {COLLECTION_PROCEDURES}")

    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Knowledge Indexer — Index log patterns and procedures into Qdrant"
    )
    parser.add_argument(
        "--collection",
        choices=["logs", "procedures"],
        default=None,
        help="Collection to index (default: both)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute embeddings but don't write to Qdrant",
    )
    args = parser.parse_args()

    success = run(collection=args.collection, dry_run=args.dry_run)
    sys.exit(0 if success else 1)
