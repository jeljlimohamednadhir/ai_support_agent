"""
code_indexer.py
━━━━━━━━━━━━━━━
Indexes code intelligence entries into Qdrant collection `code_runtime_knowledge`.

Each chunk = one business rule / exception flow / constraint.
"""

from __future__ import annotations

import hashlib
import logging
import os
from typing import List, Optional

logger = logging.getLogger(__name__)

QDRANT_HOST = os.getenv("QDRANT_HOST", "172.28.31.168")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION_NAME = "code_runtime_knowledge"
VECTOR_SIZE = 384  # MiniLM-L6-v2 dimension


def index_code_knowledge(entries: Optional[List] = None, batch_size: int = 100):
    """
    Index code knowledge entries to Qdrant.
    
    Requires: sentence-transformers, qdrant-client
    """
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import (
            Distance, VectorParams, PointStruct
        )
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        logger.error(f"[CodeIndexer] Missing dependency: {e}")
        return 0

    if entries is None:
        from app.services.code_intelligence.extractors.brasil_extractor import get_code_knowledge
        entries = get_code_knowledge()

    if not entries:
        logger.warning("[CodeIndexer] No entries to index.")
        return 0

    logger.info(f"[CodeIndexer] Indexing {len(entries)} entries to {COLLECTION_NAME}...")

    # Init encoder
    model = SentenceTransformer("all-MiniLM-L6-v2")

    # Init Qdrant
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=30)

    # Create collection if needed
    collections = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME not in collections:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        logger.info(f"[CodeIndexer] Created collection: {COLLECTION_NAME}")

    # Build points
    points = []
    for i, entry in enumerate(entries):
        text = entry.embedding_text
        if not text.strip():
            continue

        # Deterministic ID from content hash
        entry_hash = hashlib.md5(text.encode()).hexdigest()
        point_id = int(entry_hash[:12], 16)  # 48-bit int

        vector = model.encode(text).tolist()

        payload = {
            "source_type": "code",
            "application": entry.application,
            "module": entry.module,
            "entity": entry.entity,
            "exception_class": entry.exception_class,
            "exception_parent": entry.exception_parent,
            "root_cause": entry.root_cause,
            "blocking_condition": entry.blocking_condition,
            "trigger": entry.trigger,
            "sql_tables": entry.sql_tables,
            "business_rule": entry.business_rule,
            "tags": entry.tags,
            "workflow_states": entry.workflow_states,
            "confidence": entry.confidence,
            "code_location": entry.code_location,
            "text": text[:500],
        }

        points.append(PointStruct(id=point_id, vector=vector, payload=payload))

    # Upsert in batches
    indexed = 0
    for i in range(0, len(points), batch_size):
        batch = points[i:i + batch_size]
        client.upsert(collection_name=COLLECTION_NAME, points=batch)
        indexed += len(batch)
        logger.info(f"[CodeIndexer] Indexed {indexed}/{len(points)} points")

    logger.info(f"[CodeIndexer] Done — {indexed} points in {COLLECTION_NAME}")
    return indexed


def search_code_qdrant(
    query: str,
    limit: int = 5,
    entity_filter: Optional[str] = None,
    tag_filter: Optional[str] = None,
) -> List[dict]:
    """Semantic search in code_runtime_knowledge."""
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        from sentence_transformers import SentenceTransformer
    except ImportError:
        return []

    model = SentenceTransformer("all-MiniLM-L6-v2")
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=10)

    vector = model.encode(query).tolist()

    # Build optional filters
    must_conditions = []
    if entity_filter:
        must_conditions.append(
            FieldCondition(key="entity", match=MatchValue(value=entity_filter))
        )
    if tag_filter:
        must_conditions.append(
            FieldCondition(key="tags", match=MatchValue(value=tag_filter))
        )

    search_filter = Filter(must=must_conditions) if must_conditions else None

    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=vector,
        query_filter=search_filter,
        limit=limit,
    )

    return [
        {
            "score": hit.score,
            **hit.payload,
        }
        for hit in results
    ]
