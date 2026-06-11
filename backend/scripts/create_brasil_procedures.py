#!/usr/bin/env python3
"""
create_brasil_procedures.py — R3
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Crée la collection Qdrant `brasil_procedures` depuis les JSONs structurés
de data/fr_structured/.

Chaque point = une étape de résolution ou un bloc procédure d'une FR,
ce qui permet une recherche ciblée sur les PROCÉDURES de résolution
(distinct de brasil_frs qui indexe la FR complète).

Usage :
    python scripts/create_brasil_procedures.py
    python scripts/create_brasil_procedures.py --force   # recrée tout
    python scripts/create_brasil_procedures.py --dry-run # affiche sans injecter
"""
import sys
import os
import json
import uuid
import argparse
import logging
from pathlib import Path

# ── Chemins ───────────────────────────────────────────────────────────────────
BACKEND_DIR  = Path(__file__).parent.parent
DATA_DIR     = BACKEND_DIR / "data" / "fr_structured"
MASTER_JSON  = BACKEND_DIR / "data" / "brasil_fr_structured.json"
COLLECTION   = "brasil_procedures"
EMBED_DIM    = 384
QDRANT_HOST  = os.getenv("QDRANT_HOST", "172.28.31.168")
QDRANT_PORT  = int(os.getenv("QDRANT_PORT", "6333"))

# Modèle embedding (même que brasil_frs)
_HF_CACHE = os.path.expanduser(
    "~/.cache/huggingface/hub/models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2"
    "/snapshots/86741b4e3f5cb7765a600d3a3d55a0f6a6cb443d"
)
EMBED_MODEL = _HF_CACHE if os.path.isdir(_HF_CACHE) else \
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

_model  = None
_client = None


def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        log.info(f"Chargement modèle embedding...")
        _model = SentenceTransformer(EMBED_MODEL)
        log.info("Modèle prêt.")
    return _model


def get_client():
    global _client
    if _client is None:
        from qdrant_client import QdrantClient
        _client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    return _client


def ensure_collection(force: bool = False):
    from qdrant_client.models import Distance, VectorParams
    client = get_client()
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION in existing:
        if force:
            client.delete_collection(COLLECTION)
            log.info(f"Collection '{COLLECTION}' supprimée (--force).")
        else:
            info = client.get_collection(COLLECTION)
            log.info(f"Collection '{COLLECTION}' existante — {info.points_count} points.")
            return
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
    )
    log.info(f"Collection '{COLLECTION}' créée (dim={EMBED_DIM}, COSINE).")


def load_records() -> list:
    """Charge depuis data/fr_structured/*.json puis data/brasil_fr_structured.json en fallback."""
    records = []
    if DATA_DIR.exists():
        for path in sorted(DATA_DIR.glob("*.json")):
            try:
                with open(path, encoding="utf-8") as f:
                    rec = json.load(f)
                if "_source_file" not in rec:
                    rec["_source_file"] = path.stem
                records.append(rec)
            except Exception as e:
                log.warning(f"Lecture échouée {path.name}: {e}")
    if not records and MASTER_JSON.exists():
        log.info("Fallback sur brasil_fr_structured.json")
        with open(MASTER_JSON, encoding="utf-8") as f:
            records = json.load(f)
    return records


def extract_procedure_blocks(rec: dict) -> list:
    """
    Extrait les blocs procédure d'une FR structurée.
    Chaque bloc = un point Qdrant indexé séparément.

    Types de blocs générés :
      - 'resolution'  : étapes de résolution (resolution[].action)
      - 'diagnostic'  : étapes de diagnostic (diagnostic[].step)
      - 'full_proc'   : procédure complète résumée (fallback si vide)
    """
    import re

    fr_id = rec.get("id", "")
    title = rec.get("title", "")
    intents = rec.get("intents", [])
    app = rec.get("application", "BRASIL")
    root_cause = rec.get("root_cause", {})
    symptoms = [s.get("text", "") for s in rec.get("symptoms", [])]
    evidence_tags = rec.get("evidence_tags", [])
    trigger_signals = rec.get("trigger_signals", [])
    blocking_conditions = rec.get("blocking_conditions", [])

    # Dériver numéro FR
    fr_num = ""
    for field in (fr_id, rec.get("_source_file", "")):
        m = re.search(r"FR[\s\-_]?(\d{1,4}[A-Za-z]?)", str(field), re.IGNORECASE)
        if m:
            fr_num = f"FR {m.group(1)}"
            break

    blocks = []

    # ── Bloc résolution complet ───────────────────────────────────────────
    resolution_steps = rec.get("resolution", [])
    if resolution_steps:
        steps_text = "\n".join(
            f"{i+1}. {s.get('action', s.get('step', str(s)))}"
            for i, s in enumerate(resolution_steps)
        )
        sql_queries = [
            s.get("action", "") for s in resolution_steps
            if s.get("type") == "sql" or "SELECT" in str(s.get("action", "")).upper()
        ]
        embed_text = " ".join(filter(None, [
            title, root_cause.get("label", ""),
            " ".join(symptoms[:3]),
            " ".join(trigger_signals[:5]),
            steps_text,
        ]))
        blocks.append({
            "type": "resolution",
            "embed_text": embed_text,
            "payload": {
                "fr_id": fr_id,
                "fr_number": fr_num,
                "title": title,
                "application": app,
                "intents": intents,
                "block_type": "resolution",
                "steps_text": steps_text,
                "steps_count": len(resolution_steps),
                "sql_queries": sql_queries,
                "symptoms": symptoms,
                "trigger_signals": trigger_signals,
                "blocking_conditions": blocking_conditions,
                "root_cause_label": root_cause.get("label", ""),
                "root_cause_class": root_cause.get("class", ""),
                "evidence_tags": evidence_tags,
                "confidence_score": rec.get("confidence_score", 0.0),
                "trust_score": rec.get("confidence_score", 0.0),
                "source_fr_numbers": [fr_num] if fr_num else [],
                "source_file": rec.get("_source_file", ""),
                "type": "procedure",
            },
        })

    # ── Bloc diagnostic ───────────────────────────────────────────────────
    diag_steps = rec.get("diagnostic", [])
    if diag_steps:
        diag_text = "\n".join(
            f"{i+1}. {s.get('step', str(s))}"
            for i, s in enumerate(diag_steps)
        )
        sql_diag = [
            s.get("step", "") for s in diag_steps
            if s.get("type") == "query" or "SELECT" in str(s.get("step", "")).upper()
        ]
        embed_text = " ".join(filter(None, [
            f"diagnostic {title}",
            root_cause.get("label", ""),
            " ".join(symptoms[:3]),
            diag_text,
        ]))
        blocks.append({
            "type": "diagnostic",
            "embed_text": embed_text,
            "payload": {
                "fr_id": fr_id,
                "fr_number": fr_num,
                "title": f"Diagnostic — {title}",
                "application": app,
                "intents": intents,
                "block_type": "diagnostic",
                "steps_text": diag_text,
                "steps_count": len(diag_steps),
                "sql_queries": sql_diag,
                "symptoms": symptoms,
                "trigger_signals": trigger_signals,
                "root_cause_label": root_cause.get("label", ""),
                "root_cause_class": root_cause.get("class", ""),
                "evidence_tags": evidence_tags,
                "confidence_score": rec.get("confidence_score", 0.0),
                "trust_score": rec.get("confidence_score", 0.0),
                "source_fr_numbers": [fr_num] if fr_num else [],
                "source_file": rec.get("_source_file", ""),
                "type": "procedure",
            },
        })

    # ── Fallback : bloc procédure complet (titre + symptômes) ────────────
    if not blocks:
        symptom_text = " ".join(symptoms)
        embed_text = " ".join(filter(None, [title, symptom_text, root_cause.get("label", "")]))
        if embed_text.strip():
            blocks.append({
                "type": "full_proc",
                "embed_text": embed_text,
                "payload": {
                    "fr_id": fr_id,
                    "fr_number": fr_num,
                    "title": title,
                    "application": app,
                    "intents": intents,
                    "block_type": "full_proc",
                    "steps_text": f"{title}\n{symptom_text}",
                    "steps_count": 0,
                    "symptoms": symptoms,
                    "root_cause_label": root_cause.get("label", ""),
                    "evidence_tags": evidence_tags,
                    "confidence_score": rec.get("confidence_score", 0.0),
                    "trust_score": rec.get("confidence_score", 0.0),
                    "source_fr_numbers": [fr_num] if fr_num else [],
                    "source_file": rec.get("_source_file", ""),
                    "type": "procedure",
                },
            })

    return blocks


def deterministic_id(fr_id: str, block_type: str, idx: int) -> str:
    key = f"brasil_procedures:{fr_id}:{block_type}:{idx}"
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, key))


def main():
    parser = argparse.ArgumentParser(description="Crée brasil_procedures dans Qdrant")
    parser.add_argument("--force",   action="store_true", help="Supprimer et recréer la collection")
    parser.add_argument("--dry-run", action="store_true", help="Afficher sans injecter")
    args = parser.parse_args()

    # ── Charger les FRs ───────────────────────────────────────────────────
    records = load_records()
    if not records:
        log.error("Aucune FR trouvée dans data/fr_structured/ ou brasil_fr_structured.json")
        sys.exit(1)
    log.info(f"{len(records)} FRs chargées")

    # ── Extraire tous les blocs ───────────────────────────────────────────
    all_blocks = []
    for rec in records:
        blocks = extract_procedure_blocks(rec)
        for i, b in enumerate(blocks):
            fr_id = rec.get("id", rec.get("_source_file", "?"))
            b["_point_id"] = deterministic_id(fr_id, b["type"], i)
        all_blocks.extend(blocks)

    log.info(f"{len(all_blocks)} blocs procédure extraits ({len(records)} FRs)")

    if args.dry_run:
        print(f"\n{'─'*70}")
        print(f"  DRY-RUN — {len(all_blocks)} points à injecter dans '{COLLECTION}'")
        print(f"{'─'*70}")
        for b in all_blocks[:15]:
            p = b["payload"]
            print(f"  [{b['type']:10s}] {p.get('fr_number','?'):8s}  {p.get('title','')[:55]}")
        if len(all_blocks) > 15:
            print(f"  ... et {len(all_blocks)-15} autres")
        return

    # ── Qdrant ────────────────────────────────────────────────────────────
    ensure_collection(force=args.force)
    model = get_model()
    client = get_client()

    from qdrant_client.models import PointStruct

    print(f"\n{'━'*70}")
    print(f"  🚀 Injection → Qdrant '{COLLECTION}'")
    print(f"     {len(all_blocks)} blocs depuis {len(records)} FRs")
    print(f"{'━'*70}\n")

    injected = errors = 0
    batch_size = 32

    for i in range(0, len(all_blocks), batch_size):
        batch = all_blocks[i:i + batch_size]
        try:
            texts = [b["embed_text"] for b in batch]
            vectors = model.encode(texts, batch_size=batch_size, show_progress_bar=False)
            points = [
                PointStruct(
                    id=b["_point_id"],
                    vector=vectors[j].tolist(),
                    payload=b["payload"],
                )
                for j, b in enumerate(batch)
            ]
            client.upsert(collection_name=COLLECTION, points=points)
            for b in batch:
                p = b["payload"]
                print(f"  ✅ [{b['type']:10s}] {p.get('fr_number','?'):8s}  {p.get('title','')[:55]}")
            injected += len(batch)
        except Exception as e:
            log.error(f"Batch {i//batch_size + 1} échoué: {e}")
            errors += len(batch)

    col_info = client.get_collection(COLLECTION)
    print(f"\n{'━'*70}")
    print(f"  ✅ Injectés : {injected}")
    print(f"  ❌ Erreurs  : {errors}")
    print(f"  📦 Total dans '{COLLECTION}' : {col_info.points_count} points")
    print(f"{'━'*70}")


if __name__ == "__main__":
    main()
