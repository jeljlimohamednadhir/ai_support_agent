#!/usr/bin/env python3
"""
inject_structured_frs.py
━━━━━━━━━━━━━━━━━━━━━━━━
Lit data/fr_structured/*.json (produits par fr_structurer.py) et injecte
chaque FR structurée dans la collection Qdrant `brasil_frs`.

- Embedding : sentence-transformers/all-MiniLM-L12-v2 (384 dims)
- UUID déterministe par FR id → idempotent (pas de doublons)
- Collection créée automatiquement si absente

Usage :
    python inject_structured_frs.py              # inject manquants seulement
    python inject_structured_frs.py --force      # ré-injecte tout
    python inject_structured_frs.py --list       # liste les FRs sans injecter
    python inject_structured_frs.py --from-master  # depuis brasil_fr_structured.json
"""
import sys
import os
import json
import uuid
import argparse
import logging
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
BACKEND_DIR   = Path(__file__).parent
DATA_DIR      = BACKEND_DIR / "data" / "fr_structured"
MASTER_JSON   = BACKEND_DIR / "data" / "brasil_fr_structured.json"
COLLECTION    = "brasil_frs"
EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
# Chemin local du cache (évite appels HuggingFace en mode offline)
import os as _os
_HF_CACHE = _os.path.expanduser(
    "~/.cache/huggingface/hub/models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2"
    "/snapshots/86741b4e3f5cb7765a600d3a3d55a0f6a6cb443d"
)
EMBED_MODEL_LOCAL = _HF_CACHE if _os.path.isdir(_HF_CACHE) else EMBED_MODEL
EMBED_DIM     = 384
QDRANT_HOST   = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT   = int(os.getenv("QDRANT_PORT", "6333"))

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

# ── Lazy singletons ───────────────────────────────────────────────────────────
_model  = None
_client = None


def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        log.info(f"Loading embedding model {EMBED_MODEL} …")
        _model = SentenceTransformer(EMBED_MODEL_LOCAL)
        log.info("Model ready.")
    return _model


def get_client():
    global _client
    if _client is None:
        from qdrant_client import QdrantClient
        _client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    return _client


# ── Helpers ───────────────────────────────────────────────────────────────────

def ensure_collection():
    from qdrant_client.models import Distance, VectorParams
    client = get_client()
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION not in existing:
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
        )
        log.info(f"Collection '{COLLECTION}' created.")
    else:
        info = client.get_collection(COLLECTION)
        log.info(f"Collection '{COLLECTION}' already exists — {info.points_count} points.")


def point_exists(point_id: str) -> bool:
    try:
        result = get_client().retrieve(
            collection_name=COLLECTION,
            ids=[point_id],
            with_payload=False,
        )
        return len(result) > 0
    except Exception:
        return False


def build_embed_text(rec: dict) -> str:
    symptom_texts  = " ".join(s.get("text", "") for s in rec.get("symptoms", []))
    diag_texts     = " ".join(s.get("step", "") for s in rec.get("diagnostic", []))
    trigger_texts  = " ".join(rec.get("trigger_signals", []))
    resolution_txt = " ".join(a.get("action", "") for a in rec.get("resolution", []))
    evidence_txt   = " ".join(rec.get("evidence_tags", []))
    return " ".join(filter(None, [
        rec.get("title", ""),
        symptom_texts,
        trigger_texts,
        diag_texts,
        resolution_txt,
        evidence_txt,
    ]))


def deterministic_id(rec: dict) -> str:
    """UUID5 déterministe basé sur l'identifiant logique de la FR."""
    key = rec.get("id") or rec.get("_source_file") or rec.get("title", "")
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"brasil_frs:{key}"))


def build_payload(rec: dict) -> dict:
    """Construit le payload Qdrant à partir d'un enregistrement structuré."""
    # Dériver le numéro FR depuis l'id ou le source_file
    import re
    fr_num = ""
    for field in (rec.get("id", ""), rec.get("_source_file", "")):
        m = re.search(r"FR[\s\-_]?(\d{1,4}[A-Za-z]?)", str(field), re.IGNORECASE)
        if m:
            fr_num = f"FR {m.group(1)}"
            break

    # Tables impliquées depuis les entités DATABASE_TABLE
    tables = []
    for ent in rec.get("entities", []):
        if str(ent.get("type", "")).upper() == "DATABASE_TABLE":
            tables.extend(ent.get("examples", []))

    # Symptômes texte seul
    symptom_texts = [s.get("text", "") for s in rec.get("symptoms", [])]

    # Étapes résolution texte seul
    resolution_steps = [a.get("action", "") for a in rec.get("resolution", [])]

    # SQL queries depuis diagnostic
    sql_queries = [
        s.get("step", "") for s in rec.get("diagnostic", [])
        if s.get("type") == "query" and s.get("step", "").upper().startswith("SELECT")
    ]

    rc = rec.get("root_cause", {})

    return {
        # Identifiants
        "id":                     rec.get("id", ""),
        "fr_number":              fr_num,
        "fr_aliases":             [fr_num, fr_num.replace(" ", ""), fr_num.replace(" ", "-")] if fr_num else [],

        # Contenu principal
        "title":                  rec.get("title", ""),
        "title_normalized":       rec.get("title", "").lower(),
        "application":            rec.get("application", "BRASIL"),
        "applications_involved":  ["BRASIL"],

        # Intelligence structurée
        "intents":                rec.get("intents", []),
        "symptoms":               symptom_texts,
        "root_cause_label":       rc.get("label", ""),
        "root_cause_class":       rc.get("class", ""),
        "root_cause_confidence":  rc.get("confidence", 0.0),
        "blocking_conditions":    rec.get("blocking_conditions", []),
        "non_blocking_conditions": rec.get("non_blocking_conditions", []),

        # Procédure
        "diagnostic_steps":       [s.get("step", "") for s in rec.get("diagnostic", [])],
        "resolution_steps":       resolution_steps,
        "sql_queries":            sql_queries,
        "tables_involved":        tables,
        "evidence_tags":          rec.get("evidence_tags", []),
        "sfd_rules":              [r.get("rule", "") for r in rec.get("sfd_rules", [])],

        # Enrichissement
        "pattern_signature":      rec.get("pattern_signature", ""),
        "trigger_signals":        rec.get("trigger_signals", []),
        "causal_graph":           rec.get("causal_graph", []),

        # Meta
        "confidence_score":       rec.get("confidence_score", 0.0),
        "trust_score":            rec.get("confidence_score", 0.0),
        "source_types":           ["fr_structured", "fr_document"],
        "source_fr_numbers":      [fr_num] if fr_num else [],
        "source_file":            rec.get("_source_file", ""),
        "type":                   "fr_structured",
    }


def inject_record(rec: dict, force: bool = False) -> str:
    """Injecte un enregistrement dans Qdrant. Retourne 'injected'|'skipped'|'error'."""
    from qdrant_client.models import PointStruct

    point_id = rec.get("_qdrant_id") or deterministic_id(rec)

    if not force and point_exists(point_id):
        return "skipped"

    try:
        embed_text = build_embed_text(rec)
        vector = get_model().encode(embed_text).tolist()
        payload = build_payload(rec)

        get_client().upsert(
            collection_name=COLLECTION,
            points=[PointStruct(id=point_id, vector=vector, payload=payload)],
        )
        return "injected"
    except Exception as e:
        log.error(f"  ✗ Injection échouée ({rec.get('id', '?')}): {e}")
        return "error"


# ── Sources ───────────────────────────────────────────────────────────────────

def load_from_per_file() -> list[dict]:
    """Charge tous les JSON individuels depuis data/fr_structured/."""
    records = []
    if not DATA_DIR.exists():
        log.warning(f"Dossier introuvable: {DATA_DIR}")
        return records
    for path in sorted(DATA_DIR.glob("*.json")):
        try:
            with open(path, encoding="utf-8") as f:
                rec = json.load(f)
            # Injecter le nom de fichier source si absent
            if "_source_file" not in rec:
                rec["_source_file"] = path.stem
            records.append(rec)
        except Exception as e:
            log.warning(f"  Lecture échouée {path.name}: {e}")
    return records


def load_from_master() -> list[dict]:
    """Charge depuis le master brasil_fr_structured.json."""
    if not MASTER_JSON.exists():
        log.warning(f"Master JSON introuvable: {MASTER_JSON}")
        return []
    with open(MASTER_JSON, encoding="utf-8") as f:
        return json.load(f)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Inject structured FRs into Qdrant brasil_frs")
    parser.add_argument("--force",       action="store_true", help="Ré-injecter même les points existants")
    parser.add_argument("--list",        action="store_true", help="Lister les FRs sans injecter")
    parser.add_argument("--from-master", action="store_true", help="Lire depuis brasil_fr_structured.json au lieu des fichiers individuels")
    args = parser.parse_args()

    # ── Charger les enregistrements ───────────────────────────────────────
    if args.from_master:
        records = load_from_master()
        log.info(f"Master JSON: {len(records)} enregistrements")
    else:
        records = load_from_per_file()
        log.info(f"Dossier fr_structured: {len(records)} fichiers JSON")

    if not records:
        log.error("Aucun enregistrement trouvé. Vérifier data/fr_structured/ ou data/brasil_fr_structured.json")
        sys.exit(1)

    # ── Mode --list ───────────────────────────────────────────────────────
    if args.list:
        print(f"\n{'─'*60}")
        print(f"  {'ID FR':<30} {'Titre':<50} {'Classe'}")
        print(f"{'─'*60}")
        for rec in records:
            rc = rec.get("root_cause", {})
            print(f"  {rec.get('id', '?'):<30} {rec.get('title', '')[:48]:<50} [{rc.get('class','?')}]")
        print(f"{'─'*60}")
        print(f"  Total: {len(records)} FRs structurées")
        return

    # ── Injection ─────────────────────────────────────────────────────────
    print(f"\n{'━'*60}")
    print(f"  🚀 Injection FRs structurées → Qdrant `{COLLECTION}`")
    print(f"     Source : {'master JSON' if args.from_master else 'data/fr_structured/'}")
    print(f"     Mode   : {'FORCE (ré-injection)' if args.force else 'incrémental (skip existants)'}")
    print(f"     FRs    : {len(records)}")
    print(f"{'━'*60}\n")

    ensure_collection()
    get_model()  # warm up

    injected = skipped = errors = 0
    for rec in records:
        title = rec.get("title", rec.get("id", "?"))[:55]
        status = inject_record(rec, force=args.force)
        if status == "injected":
            rc = rec.get("root_cause", {})
            print(f"  ✅ {title} [class={rc.get('class','?')}]")
            injected += 1
        elif status == "skipped":
            print(f"  ⏭  {title} (déjà présent)")
            skipped += 1
        else:
            print(f"  ❌ {title}")
            errors += 1

    # ── Résumé ─────────────────────────────────────────────────────────
    col_info = get_client().get_collection(COLLECTION)
    print(f"\n{'━'*60}")
    print(f"  ✅ Injectées : {injected}")
    print(f"  ⏭  Ignorées  : {skipped}")
    print(f"  ❌ Erreurs   : {errors}")
    print(f"  📦 Total dans Qdrant `{COLLECTION}` : {col_info.points_count}")
    print(f"{'━'*60}")


if __name__ == "__main__":
    main()
