"""
Canonical Injector — Injecte les CanonicalProcedures dans PostgreSQL + Qdrant
Usage : python data_pipeline/canonical_injector.py [--dry-run]
Input : data_pipeline/output/canonical_candidates.json
Output: PostgreSQL table canonical_procedures + Qdrant collection brasil_canonical
"""
import json
import sys
import argparse
import os
from pathlib import Path
from typing import List, Dict, Optional

# Ajouter le backend au path Python
BACKEND_DIR = Path(__file__).parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

CANONICAL_FILE = Path(__file__).parent / "output" / "canonical_candidates.json"


def load_candidates() -> List[Dict]:
    """Charge les candidats générés par canonical_builder.py"""
    if not CANONICAL_FILE.exists():
        print(f"❌ canonical_candidates.json introuvable ({CANONICAL_FILE})")
        print("   Lancer d'abord: python data_pipeline/canonical_builder.py")
        return []
    with open(CANONICAL_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# ── INJECTION POSTGRESQL ────────────────────────────────────────────────────

def inject_to_postgres(candidates: List[Dict], dry_run: bool = False) -> Dict:
    """Injecte dans PostgreSQL via psycopg2 direct (sans dépendance au backend)"""
    stats = {"inserted": 0, "updated": 0, "skipped": 0, "errors": 0}

    try:
        import psycopg2
        import psycopg2.extras
    except ImportError:
        print("⚠️  psycopg2 non installé. Lancer: pip install psycopg2-binary")
        return stats

    if dry_run:
        print("  [DRY-RUN] PostgreSQL — simulation uniquement")
        stats["skipped"] = len(candidates)
        return stats

    DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
    DB_PORT = os.getenv("POSTGRES_PORT", "5432")
    DB_NAME = os.getenv("POSTGRES_DB", "ai_support_agent")
    DB_USER = os.getenv("POSTGRES_USER", "postgres")
    DB_PASS = os.getenv("POSTGRES_PASSWORD", "postgres")

    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
                                user=DB_USER, password=DB_PASS)
        cur = conn.cursor()
        trust_order = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}

        for candidate in candidates:
            try:
                cur.execute("SAVEPOINT sp1")
                # Vérifier si déjà existant
                cur.execute(
                    "SELECT id, trust_level FROM canonical_procedures WHERE app_id=%s AND title=%s",
                    (candidate["app_id"], candidate["title"])
                )
                existing = cur.fetchone()

                if existing:
                    existing_id, existing_trust = existing
                    if trust_order.get(candidate["trust_level"], 0) > trust_order.get(existing_trust, 0):
                        cur.execute("""
                            UPDATE canonical_procedures SET
                                trust_level=%s, error_codes=%s, symptoms=%s,
                                root_causes=%s, diagnostic_checks=%s,
                                resolution_steps=%s, source_fr_numbers=%s
                            WHERE id=%s
                        """, (
                            candidate["trust_level"],
                            json.dumps(candidate.get("error_codes", []), ensure_ascii=False),
                            json.dumps(candidate.get("symptoms", []), ensure_ascii=False),
                            json.dumps(candidate.get("root_causes", []), ensure_ascii=False),
                            json.dumps(candidate.get("diagnostic_checks", []), ensure_ascii=False),
                            json.dumps(candidate.get("resolution_steps", []), ensure_ascii=False),
                            json.dumps(candidate.get("source_fr_numbers", []), ensure_ascii=False),
                            existing_id
                        ))
                        stats["updated"] += 1
                    else:
                        stats["skipped"] += 1
                else:
                    cur.execute("""
                        INSERT INTO canonical_procedures
                            (app_id, title, category, error_codes, symptoms, root_causes,
                             diagnostic_checks, resolution_steps, risk_level, impact_scope,
                             trust_level, validated_by, source_fr_numbers, usage_count, success_count)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,0,0)
                    """, (
                        candidate["app_id"],
                        candidate["title"],
                        candidate.get("category", "Général"),
                        json.dumps(candidate.get("error_codes", []), ensure_ascii=False),
                        json.dumps(candidate.get("symptoms", []), ensure_ascii=False),
                        json.dumps(candidate.get("root_causes", []), ensure_ascii=False),
                        json.dumps(candidate.get("diagnostic_checks", []), ensure_ascii=False),
                        json.dumps(candidate.get("resolution_steps", []), ensure_ascii=False),
                        candidate.get("risk_level", "MEDIUM"),
                        candidate.get("impact_scope", "Brasil"),
                        candidate["trust_level"],
                        candidate.get("validated_by", "pipeline"),
                        json.dumps(candidate.get("source_fr_numbers", []), ensure_ascii=False),
                    ))
                    stats["inserted"] += 1

            except Exception as e:
                print(f"    ❌ Erreur pour '{candidate.get('title', '?')}': {e}")
                stats["errors"] += 1
                cur.execute("ROLLBACK TO SAVEPOINT sp1")

        conn.commit()
        cur.close()
        conn.close()
        print(f"  ✅ PostgreSQL: {stats['inserted']} insérés, {stats['updated']} mis à jour, {stats['skipped']} ignorés")

    except Exception as e:
        print(f"  ❌ Erreur PostgreSQL: {e}")

    return stats


# ── INJECTION QDRANT ────────────────────────────────────────────────────────

def inject_to_qdrant(candidates: List[Dict], dry_run: bool = False) -> Dict:
    """Injecte dans Qdrant avec embeddings"""
    stats = {"upserted": 0, "errors": 0}

    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import PointStruct, Distance, VectorParams
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        print(f"⚠️  Qdrant/SentenceTransformers non disponible: {e}")
        return stats

    QDRANT_URL        = os.getenv("QDRANT_URL", "http://localhost:6333")
    COLLECTION_NAME   = "brasil_canonical"
    # Utiliser le modèle disponible en cache local
    # mpnet (768 dim) si dispo, sinon MiniLM (384 dim) déjà en cache
    import os as _os
    _hf_cache = _os.path.expanduser("~/.cache/torch/sentence_transformers")
    _has_mpnet = _os.path.exists(_os.path.join(_hf_cache, "sentence-transformers_paraphrase-multilingual-mpnet-base-v2"))
    EMBEDDING_MODEL   = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2" if _has_mpnet else "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    VECTOR_SIZE       = 768 if _has_mpnet else 384
    print(f"  Modèle embedding: {EMBEDDING_MODEL.split('/')[-1]} (dim={VECTOR_SIZE})")

    if dry_run:
        print(f"  [DRY-RUN] Qdrant ({COLLECTION_NAME}) — simulation uniquement")
        stats["upserted"] = len(candidates)
        return stats

    try:
        print(f"  Connexion Qdrant: {QDRANT_URL}...")
        client = QdrantClient(url=QDRANT_URL, timeout=30)

        # Créer/recréer la collection avec la bonne dimension
        existing_collections = {c.name: c for c in client.get_collections().collections}
        if COLLECTION_NAME in existing_collections:
            # Vérifier la dimension actuelle
            coll_info = client.get_collection(COLLECTION_NAME)
            existing_dim = coll_info.config.params.vectors.size
            if existing_dim != VECTOR_SIZE:
                print(f"  ⚠️  Collection dim={existing_dim} incompatible avec modèle dim={VECTOR_SIZE} — recréation")
                client.delete_collection(COLLECTION_NAME)
                client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
                )
                print(f"  ✅ Collection '{COLLECTION_NAME}' recréée (dim={VECTOR_SIZE})")
            else:
                print(f"  ℹ️  Collection '{COLLECTION_NAME}' existante (dim={existing_dim})")
        else:
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )
            print(f"  ✅ Collection '{COLLECTION_NAME}' créée (dim={VECTOR_SIZE})")

        # Charger le modèle d'embedding
        print(f"  Chargement du modèle d'embedding...")
        model = SentenceTransformer(EMBEDDING_MODEL)

        # Encoder et upserter par batches
        batch_size = 10
        for i in range(0, len(candidates), batch_size):
            batch = candidates[i:i + batch_size]
            points = []

            for j, candidate in enumerate(batch):
                # Texte à encoder: titre + symptômes + codes d'erreur
                text_parts = [candidate["title"]]
                text_parts.extend(candidate.get("symptoms", [])[:3])
                if candidate.get("error_codes"):
                    text_parts.append("Codes: " + ", ".join(candidate["error_codes"]))
                text_parts.extend(candidate.get("root_causes", [])[:2])
                embed_text = " | ".join(text_parts)

                embedding = model.encode(embed_text).tolist()

                # ID déterministe basé sur app_id + title
                import hashlib
                point_id = int(hashlib.md5(
                    f"{candidate['app_id']}::{candidate['title']}".encode()
                ).hexdigest()[:8], 16)

                points.append(PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "app_id": candidate["app_id"],
                        "title": candidate["title"],
                        "category": candidate.get("category", ""),
                        "error_codes": candidate.get("error_codes", []),
                        "symptoms": candidate.get("symptoms", [])[:5],
                        "trust_level": candidate["trust_level"],
                        "resolution_steps": candidate.get("resolution_steps", [])[:5],
                        "source_fr_numbers": candidate.get("source_fr_numbers", []),
                        "ticket_count": candidate.get("ticket_count", 0),
                    }
                ))

            client.upsert(collection_name=COLLECTION_NAME, points=points)
            stats["upserted"] += len(points)
            print(f"  Batch {i // batch_size + 1}: {len(points)} points upsertés")

        print(f"  ✅ Qdrant: {stats['upserted']} procédures vectorisées dans '{COLLECTION_NAME}'")

    except Exception as e:
        print(f"  ❌ Erreur Qdrant: {e}")

    return stats


# ── RAPPORT FINAL ───────────────────────────────────────────────────────────

def print_final_report(candidates: List[Dict], pg_stats: Dict, qdrant_stats: Dict):
    """Affiche le rapport d'injection final"""
    print("\n" + "=" * 70)
    print("📋 RAPPORT D'INJECTION")
    print("=" * 70)

    high   = sum(1 for c in candidates if c["trust_level"] == "HIGH")
    medium = sum(1 for c in candidates if c["trust_level"] == "MEDIUM")
    low    = sum(1 for c in candidates if c["trust_level"] == "LOW")

    print(f"\n  Procédures traitées: {len(candidates)}")
    print(f"    HIGH:   {high}")
    print(f"    MEDIUM: {medium}")
    print(f"    LOW:    {low}")

    print(f"\n  PostgreSQL:")
    print(f"    Insérés:       {pg_stats.get('inserted', 0)}")
    print(f"    Mis à jour:    {pg_stats.get('updated', 0)}")
    print(f"    Ignorés:       {pg_stats.get('skipped', 0)}")
    print(f"    Erreurs:       {pg_stats.get('errors', 0)}")

    print(f"\n  Qdrant (brasil_canonical):")
    print(f"    Vectorisés:    {qdrant_stats.get('upserted', 0)}")
    print(f"    Erreurs:       {qdrant_stats.get('errors', 0)}")

    total_ok = pg_stats.get("inserted", 0) + pg_stats.get("updated", 0) + qdrant_stats.get("upserted", 0)
    if total_ok > 0:
        print(f"\n  ✅ Injection terminée avec succès!")
        print(f"  🚀 L'orchestrateur Brasil peut maintenant utiliser ces {len(candidates)} procédures.")
    else:
        print(f"\n  ⚠️  Aucune donnée injectée (dry-run ou erreurs).")

    print(f"\n  Prochaine étape: Démarrer l'API et tester via /api/v1/chat")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inject canonical procedures to DB + Qdrant")
    parser.add_argument("--dry-run", action="store_true", help="Simuler sans écrire")
    parser.add_argument("--postgres-only", action="store_true", help="Injecter seulement PostgreSQL")
    parser.add_argument("--qdrant-only", action="store_true", help="Injecter seulement Qdrant")
    args = parser.parse_args()

    print("💉 Canonical Injector — Brasil")
    if args.dry_run:
        print("  ⚠️  MODE DRY-RUN: aucune écriture réelle")
    print("-" * 70)

    # Charger les candidats
    candidates = load_candidates()
    if not candidates:
        print("❌ Aucun candidat trouvé. Lancer d'abord canonical_builder.py")
        sys.exit(1)

    print(f"✅ {len(candidates)} procédures candidates chargées")

    # Filtrer: n'injecter que ceux avec trust_level HIGH ou MEDIUM par défaut
    high_medium = [c for c in candidates if c["trust_level"] in ("HIGH", "MEDIUM")]
    low_only    = [c for c in candidates if c["trust_level"] == "LOW"]
    print(f"  Filtrage: {len(high_medium)} HIGH/MEDIUM + {len(low_only)} LOW")
    print(f"  → Injection des {len(high_medium)} HIGH/MEDIUM + {len(low_only)} LOW")

    # Injection PostgreSQL
    pg_stats = {"inserted": 0, "updated": 0, "skipped": 0, "errors": 0}
    if not args.qdrant_only:
        print("\n📦 Injection PostgreSQL...")
        pg_stats = inject_to_postgres(candidates, dry_run=args.dry_run)

    # Injection Qdrant
    qdrant_stats = {"upserted": 0, "errors": 0}
    if not args.postgres_only:
        print("\n🔍 Injection Qdrant (vectorisation)...")
        qdrant_stats = inject_to_qdrant(candidates, dry_run=args.dry_run)

    # Rapport final
    print_final_report(candidates, pg_stats, qdrant_stats)
