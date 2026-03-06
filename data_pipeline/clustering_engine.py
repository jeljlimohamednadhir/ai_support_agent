"""
Incident Clustering Engine — Groups similar tickets into knowledge clusters.

Algorithm:
  1. Load structured tickets from ticket_structured.json
  2. Embed each ticket with multilingual sentence-transformers
  3. Reduce dimensions with UMAP (if available)
  4. Cluster with HDBSCAN (falls back to KMeans if unavailable)
  5. Enrich each cluster with: name, symptoms, causes, troubleshooting steps
  6. Output cluster_results.json

Input : data_pipeline/output/ticket_structured.json
Output: data_pipeline/output/cluster_results.json
"""
import json
import re
import sys
import hashlib
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from collections import Counter

# Add backend to path
BACKEND_DIR = Path(__file__).parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

TICKET_STRUCTURED_FILE = Path(__file__).parent / "output" / "ticket_structured.json"
OUTPUT_FILE            = Path(__file__).parent / "output" / "cluster_results.json"

# Minimum cluster size
MIN_CLUSTER_SIZE = 3


# ─────────────────────────────────────────────
# Embedding
# ─────────────────────────────────────────────

def load_embedding_model():
    """Load a multilingual sentence transformer model (offline-capable).
    Falls back to TF-IDF if sentence_transformers / torch are not available.
    """
    # Skip heavy torch/transformers stack — use lightweight TF-IDF directly
    print("  ↪️  Utilisation de TF-IDF (fallback léger sans PyTorch)")
    return None


def embed_texts(texts: List[str], model) -> Any:
    """Embed a list of texts. Falls back to TF-IDF if model is None."""
    if model is not None:
        try:
            return model.encode(texts, show_progress_bar=False, batch_size=32)
        except Exception as e:
            print(f"  ⚠️  Erreur embedding: {e} → TF-IDF fallback")

    # TF-IDF fallback
    from sklearn.feature_extraction.text import TfidfVectorizer
    vectorizer = TfidfVectorizer(
        max_features=500,
        ngram_range=(1, 2),
        sublinear_tf=True,
        min_df=1,
    )
    matrix = vectorizer.fit_transform(texts)
    return matrix.toarray()


# ─────────────────────────────────────────────
# Dimensionality Reduction
# ─────────────────────────────────────────────

def reduce_dimensions(embeddings, n_components: int = 10):
    """Reduce dimensions with UMAP. Falls back to PCA if UMAP unavailable."""
    try:
        import umap
        reducer = umap.UMAP(
            n_components=n_components,
            metric="cosine",
            random_state=42,
            min_dist=0.0,
        )
        return reducer.fit_transform(embeddings)
    except ImportError:
        pass
    # PCA fallback
    try:
        from sklearn.decomposition import PCA
        import numpy as np
        n = min(n_components, embeddings.shape[0] - 1, embeddings.shape[1])
        pca = PCA(n_components=n, random_state=42)
        return pca.fit_transform(embeddings)
    except Exception as e:
        print(f"  ⚠️  Réduction dimensions échouée: {e} → utilisation directe")
        return embeddings


# ─────────────────────────────────────────────
# Clustering
# ─────────────────────────────────────────────

def cluster_embeddings(embeddings, min_cluster_size: int = MIN_CLUSTER_SIZE) -> List[int]:
    """
    Cluster embeddings with HDBSCAN (preferred) or KMeans fallback.
    Returns a list of cluster labels (-1 = noise).
    """
    try:
        import hdbscan
        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=min_cluster_size,
            min_samples=2,
            metric="euclidean",
            cluster_selection_method="eom",
        )
        labels = clusterer.fit_predict(embeddings)
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        print(f"  🔬 HDBSCAN: {n_clusters} clusters, {sum(1 for l in labels if l == -1)} outliers")
        return labels.tolist()
    except ImportError:
        pass

    # KMeans fallback
    try:
        from sklearn.cluster import KMeans
        import numpy as np
        n_clusters = max(3, min(len(embeddings) // max(min_cluster_size, 1), 20))
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(embeddings)
        print(f"  🔬 KMeans: {n_clusters} clusters (fallback, HDBSCAN non disponible)")
        return labels.tolist()
    except Exception as e:
        print(f"  ⚠️  Clustering échoué: {e}")
        return [0] * len(embeddings)


# ─────────────────────────────────────────────
# Cluster Enrichment
# ─────────────────────────────────────────────

def extract_top_terms(texts: List[str], top_n: int = 10) -> List[str]:
    """Extract top TF-IDF terms from a list of texts."""
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        import numpy as np
        if len(texts) < 2:
            return texts[0].split()[:top_n] if texts else []
        vectorizer = TfidfVectorizer(
            max_features=200,
            stop_words=None,  # Keep French words; custom stop below
            ngram_range=(1, 2),
        )
        matrix = vectorizer.fit_transform(texts)
        mean_scores = matrix.mean(axis=0).A1
        feature_names = vectorizer.get_feature_names_out()
        # Filter French stop words
        fr_stop = {"le", "la", "les", "de", "du", "des", "un", "une", "et", "en",
                   "dans", "sur", "pour", "avec", "par", "ne", "pas", "est", "a",
                   "à", "au", "ou", "que", "qui", "ce", "se", "si", "il", "elle",
                   "on", "nous", "vous", "ils", "elles", "je", "tu"}
        top_indices = mean_scores.argsort()[::-1]
        terms = []
        for idx in top_indices:
            term = feature_names[idx]
            words = term.split()
            if not all(w in fr_stop for w in words):
                terms.append(term)
            if len(terms) >= top_n:
                break
        return terms
    except Exception:
        # Fallback: simple token frequency
        all_tokens = []
        for text in texts:
            all_tokens.extend(re.findall(r"\b\w{3,}\b", text.lower()))
        counter = Counter(all_tokens)
        return [t for t, _ in counter.most_common(top_n)]


def name_cluster(top_terms: List[str], incident_types: List[str], error_codes: List[str]) -> str:
    """
    Generate a cluster name from its top terms, incident types, and error codes.
    Pattern: [primary_term]_[secondary_term] or [error_code]_[app]
    """
    # Error code-based naming takes priority
    if error_codes:
        code = error_codes[0].lower().replace(" ", "_")
        # Find most frequent incident type
        if incident_types:
            top_type = Counter(incident_types).most_common(1)[0][0]
            category = top_type.split(".")[0] if "." in top_type else top_type
            return f"{code}_{category}"
        return f"erreur_{code}"

    # Term-based naming
    if top_terms:
        # Clean terms
        clean = [re.sub(r"[^\w]", "_", t.lower()) for t in top_terms[:3]]
        return "_".join(t for t in clean if len(t) > 2)[:50]

    return f"cluster_{hashlib.md5(''.join(incident_types)).hexdigest()[:8]}"


def enrich_cluster(
    cluster_id: int,
    tickets: List[Dict],
) -> Dict[str, Any]:
    """
    Build a full cluster summary from its member tickets.
    """
    texts = [t.get("preprocessed_text") or t.get("raw_text", "") for t in tickets]
    intents = [t.get("intent", "unknown") for t in tickets]
    incident_types = [t.get("incident_type", "unknown") for t in tickets]
    applications = [t.get("application", "BRASIL") for t in tickets]
    error_codes_all = []
    for t in tickets:
        error_codes_all.extend(t.get("error_codes", []))

    top_terms = extract_top_terms(texts, top_n=8)
    top_error_codes = [c for c, _ in Counter(error_codes_all).most_common(3)]
    top_incident_type = Counter(incident_types).most_common(1)[0][0] if incident_types else "unknown"
    top_application = Counter(applications).most_common(1)[0][0] if applications else "BRASIL"

    # Generate cluster name
    cluster_name = name_cluster(top_terms, incident_types, top_error_codes)

    # Common symptoms: top terms phrased as symptoms
    common_symptoms = _build_symptom_phrases(top_terms, top_error_codes)

    # Probable causes from taxonomy
    probable_causes = _infer_probable_causes(top_incident_type, top_error_codes)

    # Suggested troubleshooting steps
    troubleshooting_steps = _build_troubleshooting_steps(top_incident_type, top_error_codes, top_application)

    # Trust score for cluster: based on size
    trust_score = _cluster_trust_score(len(tickets))

    return {
        "cluster_id": f"CLU-{cluster_id:03d}",
        "cluster_name": cluster_name,
        "size": len(tickets),
        "application": top_application,
        "incident_type": top_incident_type,
        "top_error_codes": top_error_codes,
        "top_terms": top_terms,
        "top_intents": dict(Counter(intents).most_common(3)),
        "common_symptoms": common_symptoms,
        "probable_causes": probable_causes,
        "suggested_troubleshooting_steps": troubleshooting_steps,
        "representative_ticket_ids": [t["ticket_id"] for t in tickets[:3]],
        "all_ticket_ids": [t["ticket_id"] for t in tickets],
        "trust_score": trust_score,
        "linked_procedures": [],     # Filled by canonical injection step
        "created_at": datetime.utcnow().isoformat(),
    }


def _build_symptom_phrases(top_terms: List[str], error_codes: List[str]) -> List[str]:
    """Build human-readable symptom phrases from top terms."""
    symptoms = []
    if error_codes:
        symptoms.append(f"Retour de code erreur {', '.join(error_codes[:2])}")
    for term in top_terms[:4]:
        symptoms.append(f"Présence de '{term}' dans les tickets")
    return symptoms[:5]


def _infer_probable_causes(incident_type: str, error_codes: List[str]) -> List[str]:
    """Infer probable causes from taxonomy data."""
    try:
        from app.services.nlp.taxonomy import INCIDENT_TAXONOMY
        if incident_type in INCIDENT_TAXONOMY:
            causes = INCIDENT_TAXONOMY[incident_type].possible_root_causes
            return causes[:4]
    except Exception:
        pass
    # Generic fallback
    return [
        "Données incohérentes dans la base",
        "Paramètre manquant ou incorrect",
        "Service tiers indisponible",
        "Erreur de configuration",
    ]


def _build_troubleshooting_steps(
    incident_type: str,
    error_codes: List[str],
    application: str,
) -> List[str]:
    """Build generic troubleshooting steps based on incident type."""
    steps = [
        f"1. Reproduire le problème sur l'environnement {application}",
        "2. Vérifier les logs de l'application sur la période concernée",
    ]
    if error_codes:
        steps.append(f"3. Rechercher le code erreur {error_codes[0]} dans la base de connaissances")
    else:
        steps.append("3. Identifier le code erreur exact dans les logs")
    steps.append(f"4. Consulter la procédure canonique liée à '{incident_type}'")
    steps.append("5. Si problème persiste, escalader à l'équipe N3 avec les logs")
    return steps


def _cluster_trust_score(cluster_size: int) -> float:
    """Compute trust score for a cluster based on its size."""
    if cluster_size >= 20:
        return 0.65
    elif cluster_size >= 10:
        return 0.55
    elif cluster_size >= 5:
        return 0.48
    else:
        return 0.35


# ─────────────────────────────────────────────
# Main pipeline
# ─────────────────────────────────────────────

def run(min_size: int = MIN_CLUSTER_SIZE, dry_run: bool = False) -> bool:
    if not TICKET_STRUCTURED_FILE.exists():
        print(f"  ❌ ticket_structured.json introuvable ({TICKET_STRUCTURED_FILE})")
        print("     Lancer d'abord: python data_pipeline/ticket_structurer.py")
        return False

    with open(TICKET_STRUCTURED_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    tickets = data.get("tickets", [])
    if not tickets:
        print("  ❌ Aucun ticket dans le fichier")
        return False

    print(f"  📂 {len(tickets)} tickets chargés")

    # Build text corpus for embedding
    texts = []
    for t in tickets:
        text = t.get("preprocessed_text") or t.get("raw_text", "")
        # Enrich text with entities and error codes for better clustering
        codes = " ".join(t.get("error_codes", []))
        systems = " ".join(t.get("related_systems", []))
        texts.append(f"{text} {codes} {systems}".strip())

    # Embed
    print("  🧠 Embedding des tickets...")
    model = load_embedding_model()
    embeddings = embed_texts(texts, model)

    # Reduce dimensions
    print("  📉 Réduction dimensionnelle...")
    import numpy as np
    embeddings_arr = np.array(embeddings)
    if embeddings_arr.shape[0] > 10:
        reduced = reduce_dimensions(embeddings_arr, n_components=min(10, embeddings_arr.shape[0] - 1))
    else:
        reduced = embeddings_arr

    # Cluster
    print("  🔬 Clustering...")
    labels = cluster_embeddings(reduced, min_cluster_size=min_size)

    # Group tickets by cluster
    cluster_map: Dict[int, List[Dict]] = {}
    for ticket, label in zip(tickets, labels):
        if label not in cluster_map:
            cluster_map[label] = []
        cluster_map[label].append(ticket)

    # Assign cluster IDs to tickets
    ticket_id_to_cluster = {}
    for label, cluster_tickets in cluster_map.items():
        cluster_id = f"CLU-{label:03d}" if label != -1 else "CLU-NOISE"
        for t in cluster_tickets:
            ticket_id_to_cluster[t["ticket_id"]] = cluster_id

    # Enrich non-noise clusters
    clusters = []
    for label, cluster_tickets in sorted(cluster_map.items()):
        if label == -1:
            # Noise cluster — still capture as individual outliers
            print(f"  📌 {len(cluster_tickets)} tickets non-clustérisés (bruit)")
            continue
        cluster = enrich_cluster(label, cluster_tickets)
        clusters.append(cluster)
        print(f"  ✅ {cluster['cluster_id']}: '{cluster['cluster_name']}' ({cluster['size']} tickets, "
              f"trust={cluster['trust_score']:.2f})")

    print(f"\n  📊 Total: {len(clusters)} clusters générés")

    if dry_run:
        print("  🔍 Mode DRY-RUN — pas d'écriture")
        return True

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "generated_at": datetime.utcnow().isoformat(),
        "total_tickets": len(tickets),
        "total_clusters": len(clusters),
        "noise_tickets": len(cluster_map.get(-1, [])),
        "min_cluster_size": min_size,
        "clusters": clusters,
        "ticket_cluster_map": ticket_id_to_cluster,
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n  💾 Sauvegardé: {OUTPUT_FILE}")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Incident Clustering Engine")
    parser.add_argument("--min-size", type=int, default=MIN_CLUSTER_SIZE,
                        help="Taille minimale d'un cluster")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    success = run(min_size=args.min_size, dry_run=args.dry_run)
    sys.exit(0 if success else 1)
