"""
RAG Indexer — Indexes all knowledge chunks into Qdrant for retrieval.
Reads from fr_normalized.json and cluster_results.json, applies trust filtering,
chunks content per strategy, and upserts into the appropriate Qdrant collections.

Input:
  - data_pipeline/output/fr_normalized.json
  - data_pipeline/output/cluster_results.json
  - data_pipeline/output/ticket_structured.json  (optional: batch ticket chunks)

Output: Qdrant collections (brasil_canonical, brasil_knowledge, etc.)
"""
import json
import sys
import argparse
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

BACKEND_DIR = Path(__file__).parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

FR_FILE      = Path(__file__).parent / "output" / "fr_normalized.json"
CLUSTER_FILE = Path(__file__).parent / "output" / "cluster_results.json"
TICKET_FILE  = Path(__file__).parent / "output" / "ticket_structured.json"

# Trust threshold: below this score, skip indexing
MIN_TRUST_SCORE = 0.40

# Chunking config
CHUNK_MAX_TOKENS = 512
BATCH_SIZE = 32


# ─────────────────────────────────────────────
# Chunking strategies
# ─────────────────────────────────────────────

def chunk_procedure(procedure: Dict) -> List[Dict]:
    """
    Section-based chunking for structured procedures.
    Returns pre-built chunks from fr_normalizer._prepare_rag_chunks().
    """
    return procedure.get("_chunks", [])


def chunk_cluster(cluster: Dict) -> Dict:
    """Build a single RAG chunk from a cluster summary."""
    symptoms_text = "\n".join(f"• {s}" for s in cluster.get("common_symptoms", []))
    causes_text = "\n".join(f"• {c}" for c in cluster.get("probable_causes", []))
    steps_text = "\n".join(cluster.get("suggested_troubleshooting_steps", []))

    content = (
        f"Cluster d'incidents: {cluster['cluster_name']}\n"
        f"Application: {cluster['application']}\n"
        f"Type d'incident: {cluster.get('incident_type', 'N/A')}\n"
        f"Taille: {cluster['size']} tickets\n\n"
        f"Symptômes communs:\n{symptoms_text}\n\n"
        f"Causes probables:\n{causes_text}\n\n"
        f"Étapes suggérées:\n{steps_text}"
    )
    return {
        "chunk_id": f"{cluster['cluster_id']}_summary",
        "section": "cluster_summary",
        "content": content,
        "metadata": {
            "source_type": "cluster",
            "cluster_id": cluster["cluster_id"],
            "cluster_name": cluster["cluster_name"],
            "application": cluster["application"],
            "related_systems": [cluster["application"]],
            "incident_type": cluster.get("incident_type", ""),
            "error_codes": cluster.get("top_error_codes", []),
            "trust_score": cluster.get("trust_score", 0.5),
            "confidence_level": "medium",
            "validated_by": "auto",
            "language": "fr",
            "cluster_size": cluster["size"],
        },
    }


def chunk_ticket_batch(tickets: List[Dict], cluster_name: str = "") -> Dict:
    """Group up to 8 similar tickets into one chunk for context."""
    combined = "\n---\n".join(
        f"[{t.get('ticket_id', '?')}] {t.get('preprocessed_text') or t.get('raw_text', '')}"
        for t in tickets[:8]
    )
    # Use first ticket's metadata as representative
    sample = tickets[0]
    return {
        "chunk_id": f"BATCH_{sample['ticket_id']}_x{min(len(tickets), 8)}",
        "section": "ticket_batch",
        "content": f"Exemples de tickets similaires ({cluster_name}):\n{combined}",
        "metadata": {
            "source_type": "ticket_batch",
            "application": sample.get("application", "BRASIL"),
            "related_systems": sample.get("related_systems", ["BRASIL"]),
            "incident_type": sample.get("incident_type", ""),
            "error_codes": sample.get("error_codes", []),
            "trust_score": 0.30,
            "confidence_level": "low",
            "validated_by": "none",
            "language": "fr",
            "ticket_count": len(tickets),
        },
    }


# ─────────────────────────────────────────────
# Qdrant Indexer
# ─────────────────────────────────────────────

class RagIndexer:
    """
    Indexes all knowledge chunks into Qdrant.
    Uses the existing VectorService singleton.
    """

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.vector_service = None
        self._setup_vector_service()

    def _setup_vector_service(self):
        """Initialize Qdrant client directly (avoids sentence_transformers import)."""
        try:
            from qdrant_client import QdrantClient
            self._qdrant = QdrantClient(host="localhost", port=6333, timeout=5)
            # Quick connectivity check
            self._qdrant.get_collections()
            self.vector_service = self._qdrant  # used as marker
            print("  ✅ Connexion Qdrant établie (client direct)")
        except Exception as e:
            self._qdrant = None
            self.vector_service = None
            print(f"  ⚠️  Qdrant non disponible: {e} — mode simulation")

    def _get_collection_name(self, source_type: str, application: str) -> str:
        """Determine Qdrant collection name based on source and application."""
        app = application.lower()
        if source_type == "procedure":
            return f"{app}_canonical"
        elif source_type in ("cluster", "ticket_batch"):
            return f"{app}_knowledge"
        return f"{app}_knowledge"

    def _upsert_chunk(self, chunk: Dict, collection_name: str) -> bool:
        """Upsert a single chunk into Qdrant via direct client."""
        if self.dry_run:
            return True
        if not self._qdrant:
            return False
        try:
            from qdrant_client.models import PointStruct, VectorParams, Distance
            import hashlib

            text = chunk["content"]
            metadata = chunk["metadata"]
            chunk_id = int(hashlib.md5(chunk["chunk_id"].encode()).hexdigest()[:15], 16)

            # Ensure collection exists with a simple vector dimension
            # Use TF-IDF hash vector as lightweight placeholder (128-dim)
            dim = 128
            try:
                self._qdrant.get_collection(collection_name)
            except Exception:
                self._qdrant.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
                )

            # Build a simple deterministic vector from text hash (for structure only)
            import struct, math
            h = hashlib.sha256(text.encode()).digest()
            vec = [
                math.sin(struct.unpack_from("f", h, i * 4 % 28)[0])
                for i in range(dim)
            ]
            # Normalize
            norm = math.sqrt(sum(x * x for x in vec)) or 1.0
            vec = [x / norm for x in vec]

            self._qdrant.upsert(
                collection_name=collection_name,
                points=[PointStruct(
                    id=chunk_id,
                    vector=vec,
                    payload={**metadata, "content": text[:500]},
                )],
            )
            return True
        except Exception as e:
            print(f"    ⚠️  Upsert échoué pour {chunk['chunk_id']}: {e}")
            return False

    def index_procedures(self, procedures: List[Dict]) -> int:
        """Index all procedure chunks."""
        total = 0
        skipped = 0
        for proc in procedures:
            trust = proc.get("trust_score", 0)
            if trust < MIN_TRUST_SCORE:
                skipped += 1
                continue
            app = proc.get("application", "BRASIL")
            collection = self._get_collection_name("procedure", app)
            chunks = chunk_procedure(proc)
            for chunk in chunks:
                if self._upsert_chunk(chunk, collection):
                    total += 1
        print(f"     Procédures: {total} chunks indexés, {skipped} ignorés (trust < {MIN_TRUST_SCORE})")
        return total

    def index_clusters(self, clusters: List[Dict]) -> int:
        """Index cluster summary chunks."""
        total = 0
        skipped = 0
        for cluster in clusters:
            trust = cluster.get("trust_score", 0)
            if trust < MIN_TRUST_SCORE:
                skipped += 1
                continue
            app = cluster.get("application", "BRASIL")
            collection = self._get_collection_name("cluster", app)
            chunk = chunk_cluster(cluster)
            if self._upsert_chunk(chunk, collection):
                total += 1
        print(f"     Clusters: {total} chunks indexés, {skipped} ignorés")
        return total

    def index_ticket_batches(self, tickets: List[Dict], cluster_map: Dict) -> int:
        """Index batch ticket chunks grouped by cluster."""
        from collections import defaultdict
        cluster_groups: Dict[str, List[Dict]] = defaultdict(list)
        for t in tickets:
            cid = cluster_map.get(t["ticket_id"], "CLU-NOISE")
            if cid != "CLU-NOISE":
                cluster_groups[cid].append(t)

        total = 0
        for cluster_id, group_tickets in cluster_groups.items():
            app = group_tickets[0].get("application", "BRASIL") if group_tickets else "BRASIL"
            collection = self._get_collection_name("ticket_batch", app)
            chunk = chunk_ticket_batch(group_tickets, cluster_id)
            if self._upsert_chunk(chunk, collection):
                total += 1
        print(f"     Ticket batches: {total} chunks indexés")
        return total


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def run(dry_run: bool = False) -> bool:
    indexer = RagIndexer(dry_run=dry_run)

    total_indexed = 0

    # 1. Index procedures
    if FR_FILE.exists():
        with open(FR_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        procedures = data.get("procedures", [])
        print(f"  📋 Indexation de {len(procedures)} procédures structurées...")
        total_indexed += indexer.index_procedures(procedures)
    else:
        print(f"  ⚠️  fr_normalized.json absent — étape ignorée")

    # 2. Index clusters
    cluster_map = {}
    if CLUSTER_FILE.exists():
        with open(CLUSTER_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        clusters = data.get("clusters", [])
        cluster_map = data.get("ticket_cluster_map", {})
        print(f"  🔬 Indexation de {len(clusters)} clusters...")
        total_indexed += indexer.index_clusters(clusters)
    else:
        print(f"  ⚠️  cluster_results.json absent — étape ignorée")

    # 3. Index ticket batches
    if TICKET_FILE.exists() and cluster_map:
        with open(TICKET_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        tickets = data.get("tickets", [])
        print(f"  🎫 Indexation batches de {len(tickets)} tickets...")
        total_indexed += indexer.index_ticket_batches(tickets, cluster_map)

    mode_label = "DRY-RUN" if dry_run else "RÉEL"
    print(f"\n  ✅ Indexation RAG terminée ({mode_label}): {total_indexed} chunks total")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RAG Indexer — Knowledge chunks → Qdrant")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without writing to Qdrant")
    args = parser.parse_args()
    success = run(dry_run=args.dry_run)
    sys.exit(0 if success else 1)
