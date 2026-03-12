"""
Hierarchical ML Classifier — 2-level taxonomy for IT ticket classification.

Architecture:
  STEP 1  — Sentence Transformer embeddings (lazy, ONNX-safe)
  STEP 2  — KNN (cosine, k=5) for Level 1 classification
  STEP 3  — Specialized LogisticRegression per L1 category for Level 2
  STEP 4  — Confidence check (L1 cosine sim + L2 probability)
  STEP 5  — Groq LLM fallback for low-confidence predictions
"""
from __future__ import annotations

import json
import pickle
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from app.core.logging import get_logger

logger = get_logger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Taxonomy — built-in default (can be overridden by taxonomy.json)
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_TAXONOMY: Dict[str, Any] = {
    "level_1_categories": [
        {
            "name": "DATA",
            "description": "Problèmes liés à l'intégrité, la cohérence, la correction ou la configuration des données réseau BRASIL.",
            "level_2_categories": [
                "DATA_INCONSISTENCY",
                "DATA_CORRUPTION",
                "DATA_CORRECTION_SCRIPT",
                "NETWORK_CONFIGURATION",
                "DATA_UPDATE_OR_DELETE",
            ],
        },
        {
            "name": "APPLICATION",
            "description": "Dysfonctionnements applicatifs, bugs fonctionnels ou problèmes de configuration de l'application BRASIL.",
            "level_2_categories": [
                "APPLICATION_BUG",
                "APPLICATION_FUNCTIONALITY",
                "APPLICATION_CONFIGURATION",
            ],
        },
        {
            "name": "ACCESS",
            "description": "Problèmes de droits d'accès, de connexion ou de profils utilisateurs BRASIL.",
            "level_2_categories": [
                "ACCESS_RIGHTS",
                "LOGIN_ISSUE",
                "PERMISSION_CONFIGURATION",
            ],
        },
        {
            "name": "OPERATIONS",
            "description": "Demandes de service planifiées, travaux sur le réseau, ordonnancement ou annulations.",
            "level_2_categories": [
                "SERVICE_REQUEST",
                "SCHEDULING",
                "PROCESS_OPERATION",
                "ANNULATION",
            ],
        },
        {
            "name": "PROCESS_ERROR",
            "description": "Erreurs de workflow, dysfonctionnements système ou pannes de processus BRASIL/infrastructure.",
            "level_2_categories": [
                "WORKFLOW_ERROR",
                "SYSTEM_PROCESS_ERROR",
                "PROCESS_FAILURE",
            ],
        },
        {
            "name": "UNKNOWN",
            "description": "Tickets sans cause déterminée ou avec description insuffisante.",
            "level_2_categories": [
                "UNDETERMINED",
                "INCOMPLETE_DESCRIPTION",
            ],
        },
    ],
    "label_mapping": {
        # ── Data domain ──────────────────────────────────────────────────────
        "INCOHERENCE DE DONNEES":                          {"level_1": "DATA",         "level_2": "DATA_INCONSISTENCY"},
        "INCOHERENCE DONNEES":                             {"level_1": "DATA",         "level_2": "DATA_INCONSISTENCY"},
        "DONNEES":                                         {"level_1": "DATA",         "level_2": "DATA_INCONSISTENCY"},
        "CORRECTION DE DONNEES":                           {"level_1": "DATA",         "level_2": "DATA_UPDATE_OR_DELETE"},
        "FONCTIONNALITE - DONNEE CORROMPUE":               {"level_1": "DATA",         "level_2": "DATA_CORRUPTION"},
        "INCOHERENCE CORRIGEE PAR OUTIL OU SCRIPT":        {"level_1": "DATA",         "level_2": "DATA_CORRECTION_SCRIPT"},
        "ADMINISTRATION DONNEES - QUALITE DONNEES":        {"level_1": "DATA",         "level_2": "DATA_UPDATE_OR_DELETE"},
        "QUALITE DONNEES":                                 {"level_1": "DATA",         "level_2": "DATA_UPDATE_OR_DELETE"},
        "CONFIGURATION RESEAU":                            {"level_1": "DATA",         "level_2": "NETWORK_CONFIGURATION"},
        "CONFIGURATION":                                   {"level_1": "DATA",         "level_2": "NETWORK_CONFIGURATION"},
        # ── Application domain ───────────────────────────────────────────────
        "BUG APPLICATIF":                                  {"level_1": "APPLICATION",  "level_2": "APPLICATION_BUG"},
        "APPLICATIF":                                      {"level_1": "APPLICATION",  "level_2": "APPLICATION_BUG"},
        "APPLICATION COMPOSANT - FONCTIONNALITE":          {"level_1": "APPLICATION",  "level_2": "APPLICATION_FUNCTIONALITY"},
        "FONCTIONNALITE":                                  {"level_1": "APPLICATION",  "level_2": "APPLICATION_FUNCTIONALITY"},
        "NON CONFORMITE":                                  {"level_1": "APPLICATION",  "level_2": "APPLICATION_CONFIGURATION"},
        "NON CONFORMITE APPLICATIVE":                      {"level_1": "APPLICATION",  "level_2": "APPLICATION_CONFIGURATION"},
        "INTERFACE AUTRE":                                 {"level_1": "APPLICATION",  "level_2": "APPLICATION_BUG"},
        "TRAITEMENT IMPOSSIBLE - DESCRIPTION INCOMPLETE":  {"level_1": "APPLICATION",  "level_2": "APPLICATION_BUG"},
        # ── Access domain ────────────────────────────────────────────────────
        "NON CONFORMITE PROFIL OU DROITS":                 {"level_1": "ACCESS",       "level_2": "ACCESS_RIGHTS"},
        "ACCES":                                           {"level_1": "ACCESS",       "level_2": "ACCESS_RIGHTS"},
        "DROITS":                                          {"level_1": "ACCESS",       "level_2": "ACCESS_RIGHTS"},
        "PROFIL":                                          {"level_1": "ACCESS",       "level_2": "PERMISSION_CONFIGURATION"},
        "CONNEXION":                                       {"level_1": "ACCESS",       "level_2": "LOGIN_ISSUE"},
        # ── Operations domain ────────────────────────────────────────────────
        "DEMANDE DE TRAVAUX":                              {"level_1": "OPERATIONS",   "level_2": "SERVICE_REQUEST"},
        "DEMANDE TRAVAUX":                                 {"level_1": "OPERATIONS",   "level_2": "SERVICE_REQUEST"},
        "ASSISTANCE":                                      {"level_1": "OPERATIONS",   "level_2": "SERVICE_REQUEST"},
        "ANNULATION PROCESS":                              {"level_1": "OPERATIONS",   "level_2": "ANNULATION"},
        "ANNULATION UTILISATEUR":                          {"level_1": "OPERATIONS",   "level_2": "ANNULATION"},
        "ORDONNANCEMENT":                                  {"level_1": "OPERATIONS",   "level_2": "SCHEDULING"},
        "PLANIFICATION":                                   {"level_1": "OPERATIONS",   "level_2": "SCHEDULING"},
        "BON USAGE":                                       {"level_1": "OPERATIONS",   "level_2": "PROCESS_OPERATION"},
        "UTILISATEUR":                                     {"level_1": "OPERATIONS",   "level_2": "PROCESS_OPERATION"},
        # ── Process Error domain ─────────────────────────────────────────────
        "INFRASTRUCTURE TECHNIQUE - SERVEUR ET RESEAU":    {"level_1": "PROCESS_ERROR","level_2": "SYSTEM_PROCESS_ERROR"},
        "SERVEUR":                                         {"level_1": "PROCESS_ERROR","level_2": "SYSTEM_PROCESS_ERROR"},
        "INTERFACE ORACLE":                                {"level_1": "PROCESS_ERROR","level_2": "SYSTEM_PROCESS_ERROR"},
        "PROCESS":                                         {"level_1": "PROCESS_ERROR","level_2": "WORKFLOW_ERROR"},
        "ERREUR PROCESS":                                  {"level_1": "PROCESS_ERROR","level_2": "WORKFLOW_ERROR"},
        # ── Unknown domain ───────────────────────────────────────────────────
        "MECONNAISSANCE USAGE":                            {"level_1": "UNKNOWN",      "level_2": "UNDETERMINED"},
        "CAUSE INDETERMINEE":                              {"level_1": "UNKNOWN",      "level_2": "UNDETERMINED"},
        "CAUSE INCONNUE":                                  {"level_1": "UNKNOWN",      "level_2": "UNDETERMINED"},
        "DESCRIPTION INCOMPLETE":                          {"level_1": "UNKNOWN",      "level_2": "INCOMPLETE_DESCRIPTION"},
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Confidence thresholds (designed for 222-ticket BRASIL dataset)
# ─────────────────────────────────────────────────────────────────────────────
THRESHOLD_L1_HIGH   = 0.75   # ≥ 0.75 → auto-accept, no review needed
THRESHOLD_L1_MEDIUM = 0.50   # 0.50–0.74 → accept with human review flag
# Below 0.50 → LLM fallback
THRESHOLD_L2_HIGH   = 0.70
THRESHOLD_L2_MEDIUM = 0.55
MIN_SAMPLES_L2      = 5      # below this, skip L2 model → LLM fallback

# Hybrid voting weights (alpha + beta = 1.0)
ALPHA_SIMILARITY = 0.60      # weight for embedding cosine similarity vote
BETA_KEYWORD     = 0.40      # weight for keyword boost vote

# Confidence scoring weights (must sum to 1.0)
W_SIM       = 0.40   # nearest-neighbor similarity score
W_AGREEMENT = 0.35   # neighbor label agreement ratio
W_KEYWORD   = 0.25   # keyword boost sum

# ─────────────────────────────────────────────────────────────────────────────
# BRASIL-specific keyword signals → (L1, L2, weight)
# ─────────────────────────────────────────────────────────────────────────────
KEYWORD_SIGNALS: Dict[str, Tuple[str, str, float]] = {
    # ── DATA / DATA_CORRECTION_SCRIPT ──────────────────────────────────────
    "script":               ("DATA", "DATA_CORRECTION_SCRIPT", 0.50),
    "outil de correction":  ("DATA", "DATA_CORRECTION_SCRIPT", 0.55),
    "correction script":    ("DATA", "DATA_CORRECTION_SCRIPT", 0.60),
    "corrigé par script":   ("DATA", "DATA_CORRECTION_SCRIPT", 0.65),
    # ── DATA / DATA_INCONSISTENCY ───────────────────────────────────────────
    "incohérence":          ("DATA", "DATA_INCONSISTENCY", 0.55),
    "doublon":              ("DATA", "DATA_INCONSISTENCY", 0.55),
    "incoherence":          ("DATA", "DATA_INCONSISTENCY", 0.55),
    "doublons":             ("DATA", "DATA_INCONSISTENCY", 0.50),
    "avp":                  ("DATA", "DATA_INCONSISTENCY", 0.45),
    "vlan":                 ("DATA", "DATA_INCONSISTENCY", 0.40),
    "blocage vlan":         ("DATA", "DATA_INCONSISTENCY", 0.55),
    "vlan bloqué":          ("DATA", "DATA_INCONSISTENCY", 0.55),
    # ── DATA / DATA_UPDATE_OR_DELETE ───────────────────────────────────────
    "suppression":          ("DATA", "DATA_UPDATE_OR_DELETE", 0.40),
    "supprimer":            ("DATA", "DATA_UPDATE_OR_DELETE", 0.40),
    "suppression impossible": ("DATA", "DATA_UPDATE_OR_DELETE", 0.55),
    "mise à jour":          ("DATA", "DATA_UPDATE_OR_DELETE", 0.40),
    "dossier stormshield":  ("DATA", "DATA_UPDATE_OR_DELETE", 0.50),
    # ── DATA / DATA_CORRUPTION ─────────────────────────────────────────────
    "données corrompues":   ("DATA", "DATA_CORRUPTION", 0.65),
    "corruption":           ("DATA", "DATA_CORRUPTION", 0.65),
    # ── DATA / NETWORK_CONFIGURATION ───────────────────────────────────────
    "configuration réseau": ("DATA", "NETWORK_CONFIGURATION", 0.55),
    "routeur":              ("DATA", "NETWORK_CONFIGURATION", 0.40),
    "dslam":                ("DATA", "NETWORK_CONFIGURATION", 0.40),
    "olt":                  ("DATA", "NETWORK_CONFIGURATION", 0.40),
    "nœud":                 ("DATA", "NETWORK_CONFIGURATION", 0.35),
    "ne/nb":                ("DATA", "NETWORK_CONFIGURATION", 0.45),
    # ── APPLICATION / APPLICATION_BUG ──────────────────────────────────────
    "bug":                  ("APPLICATION", "APPLICATION_BUG", 0.55),
    "erreur applicatif":    ("APPLICATION", "APPLICATION_BUG", 0.60),
    "erreur 1300":          ("APPLICATION", "APPLICATION_BUG", 0.65),
    "1300":                 ("APPLICATION", "APPLICATION_BUG", 0.60),
    "b4002":                ("APPLICATION", "APPLICATION_BUG", 0.60),
    "ora-":                 ("APPLICATION", "APPLICATION_BUG", 0.55),
    "exception":            ("APPLICATION", "APPLICATION_BUG", 0.45),
    # ── APPLICATION / APPLICATION_FUNCTIONALITY ─────────────────────────────
    "fonctionnalité":       ("APPLICATION", "APPLICATION_FUNCTIONALITY", 0.50),
    "fonctionnement":       ("APPLICATION", "APPLICATION_FUNCTIONALITY", 0.45),
    # ── ACCESS / ACCESS_RIGHTS ─────────────────────────────────────────────
    "droits":               ("ACCESS", "ACCESS_RIGHTS", 0.55),
    "accès":                ("ACCESS", "ACCESS_RIGHTS", 0.50),
    "habilitation":         ("ACCESS", "ACCESS_RIGHTS", 0.60),
    "profil utilisateur":   ("ACCESS", "PERMISSION_CONFIGURATION", 0.55),
    "non conformité profil":("ACCESS", "PERMISSION_CONFIGURATION", 0.65),
    # ── ACCESS / LOGIN_ISSUE ───────────────────────────────────────────────
    "connexion":            ("ACCESS", "LOGIN_ISSUE", 0.50),
    "login":                ("ACCESS", "LOGIN_ISSUE", 0.50),
    "mot de passe":         ("ACCESS", "LOGIN_ISSUE", 0.55),
    # ── OPERATIONS / ANNULATION ─────────────────────────────────────────────
    "annulation":           ("OPERATIONS", "ANNULATION", 0.60),
    "annulé":               ("OPERATIONS", "ANNULATION", 0.55),
    # ── OPERATIONS / SERVICE_REQUEST ───────────────────────────────────────
    "demande de travaux":   ("OPERATIONS", "SERVICE_REQUEST", 0.65),
    "travaux":              ("OPERATIONS", "SERVICE_REQUEST", 0.45),
    "prestation":           ("OPERATIONS", "SERVICE_REQUEST", 0.45),
    # ── OPERATIONS / SCHEDULING ────────────────────────────────────────────
    "ordonnancement":       ("OPERATIONS", "SCHEDULING", 0.65),
    "planification":        ("OPERATIONS", "SCHEDULING", 0.60),
    "batch":                ("OPERATIONS", "SCHEDULING", 0.50),
    # ── PROCESS_ERROR / SYSTEM_PROCESS_ERROR ────────────────────────────────
    "brasil hs":            ("PROCESS_ERROR", "SYSTEM_PROCESS_ERROR", 0.80),
    "brasil hors service":  ("PROCESS_ERROR", "SYSTEM_PROCESS_ERROR", 0.80),
    "serveur indisponible": ("PROCESS_ERROR", "SYSTEM_PROCESS_ERROR", 0.70),
    "infrastructure":       ("PROCESS_ERROR", "SYSTEM_PROCESS_ERROR", 0.50),
    "interface oracle":     ("PROCESS_ERROR", "SYSTEM_PROCESS_ERROR", 0.65),
    # ── PROCESS_ERROR / WORKFLOW_ERROR ─────────────────────────────────────
    "workflow":             ("PROCESS_ERROR", "WORKFLOW_ERROR", 0.60),
    "processus bloqué":     ("PROCESS_ERROR", "WORKFLOW_ERROR", 0.65),
    "traitement bloqué":    ("PROCESS_ERROR", "WORKFLOW_ERROR", 0.65),
    # ── UNKNOWN ────────────────────────────────────────────────────────────
    "méconnaissance":       ("UNKNOWN", "UNDETERMINED", 0.50),
    "cause inconnue":       ("UNKNOWN", "UNDETERMINED", 0.55),
}


# ─────────────────────────────────────────────────────────────────────────────
# Text preparation helpers
# ─────────────────────────────────────────────────────────────────────────────

import re as _re


def prepare_text(user_sig: str, inc_solution: str) -> str:
    """
    Combine user_sig + inc_solution into a single ML-ready string.

    inc_solution carries 2× weight (duplicated) because engineers' resolution
    text is a far stronger classification signal than the user description.
    Technical tokens (VLAN names, error codes, equipment IDs) are preserved.

    Args:
        user_sig:     Raw user description field.
        inc_solution: Engineer resolution / solution field.

    Returns:
        Normalised text string ready for SentenceTransformer encoding.
    """
    sig = _re.sub(r'\s+', ' ', str(user_sig or "").lower()).strip()
    sol = _re.sub(r'\s+', ' ', str(inc_solution or "").lower()).strip()
    # inc_solution duplicated to give it 2× weight in the embedding space
    parts = [p for p in [sig, sol, sol] if p]
    return " [SEP] ".join(parts)


def compute_keyword_boost(
    text: str,
) -> Tuple[Dict[str, float], float]:
    """
    Scan text for BRASIL-specific keyword signals and aggregate per-L1 scores.

    Returns:
        l1_scores  — dict {l1_name: aggregated_weight}
        total_boost — capped at 1.0 (used in confidence formula)
    """
    text_lower = str(text or "").lower()
    l1_scores: Dict[str, float] = {}
    total_boost = 0.0

    for keyword, (l1, _l2, weight) in KEYWORD_SIGNALS.items():
        if keyword in text_lower:
            l1_scores[l1] = l1_scores.get(l1, 0.0) + weight
            total_boost += weight

    # Normalize so scores sum to 1 (avoids scale issues when combining with sim)
    if total_boost > 0:
        l1_scores = {k: v / total_boost for k, v in l1_scores.items()}

    return l1_scores, min(total_boost, 1.0)


def compute_keyword_boost_l2(
    text: str,
    l1_filter: str,
) -> Dict[str, float]:
    """
    Same as compute_keyword_boost but restricted to a specific L1 domain,
    returning per-L2 scores for the constrained L2 prediction step.
    """
    text_lower = str(text or "").lower()
    l2_scores: Dict[str, float] = {}
    total = 0.0

    for keyword, (l1, l2, weight) in KEYWORD_SIGNALS.items():
        if l1 == l1_filter and keyword in text_lower:
            l2_scores[l2] = l2_scores.get(l2, 0.0) + weight
            total += weight

    if total > 0:
        l2_scores = {k: v / total for k, v in l2_scores.items()}
    return l2_scores


class HierarchicalClassifier:
    """
    Two-level hierarchical classifier for IT support tickets.

    Level 1: KNN (cosine similarity) on sentence embeddings
    Level 2: Specialized LogisticRegression per L1 category
    Fallback: Groq LLM with dynamic few-shot (3 nearest neighbors)
    """

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        # Paths
        self.model_path     = self.data_dir / "hierarchical_model.pkl"
        self.taxonomy_path  = self.data_dir / "taxonomy.json"
        self.card_path      = self.data_dir / "hierarchical_card.json"

        # State
        self.taxonomy: Dict[str, Any] = {}
        self.embeddings: Optional[Any]   = None   # np.ndarray shape (N, 768)
        self.faiss_index: Optional[Any]  = None   # faiss.IndexFlatIP (or None → numpy fallback)
        self.labels_l1: Optional[List]   = None   # list of L1 strings (length N)
        self.labels_l2: Optional[List]   = None   # list of L2 strings (length N)
        self.texts_train: Optional[List] = None   # original texts (for few-shot)
        self.l2_models: Dict[str, Any]   = {}     # {l1_name: LogisticRegression}
        self.l2_vectorizers: Dict[str, Any] = {}  # {l1_name: TfidfVectorizer}
        self.is_trained: bool = False
        self.card: Dict[str, Any] = {}

        self._load_taxonomy()

    # ──────────────────────────────────────────────
    # Taxonomy
    # ──────────────────────────────────────────────

    def _load_taxonomy(self):
        """Load taxonomy from file or use default."""
        if self.taxonomy_path.exists():
            try:
                with open(self.taxonomy_path, "r", encoding="utf-8") as f:
                    self.taxonomy = json.load(f)
                logger.info("[HierarchicalClassifier] Taxonomy loaded from file")
                return
            except Exception as e:
                logger.warning(f"[HierarchicalClassifier] Failed to load taxonomy file: {e}")
        self.taxonomy = DEFAULT_TAXONOMY
        logger.info("[HierarchicalClassifier] Using default taxonomy")

    def save_taxonomy(self, taxonomy: Dict[str, Any]):
        """Persist a custom taxonomy to disk."""
        with open(self.taxonomy_path, "w", encoding="utf-8") as f:
            json.dump(taxonomy, f, ensure_ascii=False, indent=2)
        self.taxonomy = taxonomy
        logger.info("[HierarchicalClassifier] Custom taxonomy saved")

    def get_taxonomy(self) -> Dict[str, Any]:
        return self.taxonomy

    def map_old_label(self, old_label: str) -> Dict[str, str]:
        """Return {level_1, level_2} for a legacy label string."""
        mapping = self.taxonomy.get("label_mapping", {})
        key = old_label.upper().strip()
        if key in mapping:
            return mapping[key]
        # Fuzzy fallback: partial match
        for k, v in mapping.items():
            if key in k or k in key:
                return v
        return {"level_1": "UNKNOWN", "level_2": "UNDETERMINED"}

    # ──────────────────────────────────────────────
    # Embedding
    # ──────────────────────────────────────────────

    def _get_embedder(self):
        """Lazy-load sentence transformer.
        Tries mpnet-base-v2 first (768-dim, better quality).
        Falls back to MiniLM-L12-v2 (384-dim) if mpnet is not cached locally.
        """
        models_to_try = [
            "paraphrase-multilingual-mpnet-base-v2",
            "paraphrase-multilingual-MiniLM-L12-v2",
        ]
        cache_dir = str(self.data_dir / "models")
        for model_name in models_to_try:
            try:
                from sentence_transformers import SentenceTransformer
                model = SentenceTransformer(model_name, cache_folder=cache_dir)
                logger.info(f"[HierarchicalClassifier] Loaded embedder: {model_name}")
                return model
            except Exception as e:
                logger.warning(f"[HierarchicalClassifier] {model_name} unavailable: {e}")
        logger.warning("[HierarchicalClassifier] No SentenceTransformer model available — will use TF-IDF fallback")
        return None

    def _embed(self, texts: List[str]) -> Any:
        """Encode texts → numpy array (N, D). Falls back to TF-IDF vectors."""
        import numpy as np
        model = self._get_embedder()
        if model is not None:
            try:
                return model.encode(texts, batch_size=32, show_progress_bar=False, normalize_embeddings=True)
            except Exception as e:
                logger.warning(f"[HierarchicalClassifier] Encoding failed: {e}")
        # TF-IDF fallback
        logger.warning("[HierarchicalClassifier] Using TF-IDF fallback for embeddings")
        from sklearn.feature_extraction.text import TfidfVectorizer
        vec = TfidfVectorizer(max_features=512, ngram_range=(1, 2))
        X = vec.fit_transform(texts).toarray()
        norms = np.linalg.norm(X, axis=1, keepdims=True)
        norms[norms == 0] = 1
        return (X / norms).astype(np.float32)

    def _build_faiss_index(self, embeddings: Any) -> Any:
        """Build a FAISS IndexFlatIP for fast cosine similarity search.
        Falls back to None (numpy dot product used instead) if faiss unavailable."""
        try:
            import faiss  # type: ignore
            import numpy as np
            dim = embeddings.shape[1]
            index = faiss.IndexFlatIP(dim)
            vecs = embeddings.astype(np.float32)
            index.add(vecs)
            logger.info(f"[HierarchicalClassifier] FAISS IndexFlatIP built ({index.ntotal} vectors, dim={dim})")
            return index
        except ImportError:
            logger.info("[HierarchicalClassifier] faiss not installed — using numpy dot product for KNN")
            return None
        except Exception as e:
            logger.warning(f"[HierarchicalClassifier] FAISS build failed: {e}")
            return None

    # ──────────────────────────────────────────────
    # Training
    # ──────────────────────────────────────────────

    def train(
        self,
        texts: List[str],
        labels_original: List[str],
        label_col_is_hierarchical: bool = False,
        l1_col: Optional[List[str]] = None,
        l2_col: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Train the hierarchical classifier.

        Args:
            texts:                   Raw ticket texts.
            labels_original:         Original labels (will be mapped via taxonomy).
            label_col_is_hierarchical: If True, l1_col/l2_col are provided directly.
            l1_col:                  Pre-mapped L1 labels (optional).
            l2_col:                  Pre-mapped L2 labels (optional).
        """
        import numpy as np
        from sklearn.linear_model import LogisticRegression
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics import f1_score

        logger.info(f"[HierarchicalClassifier] Training on {len(texts)} samples…")

        # ── Map labels ──────────────────────────────────────────────────────
        if label_col_is_hierarchical and l1_col and l2_col:
            mapped_l1 = list(l1_col)
            mapped_l2 = list(l2_col)
        else:
            mapped = [self.map_old_label(lbl) for lbl in labels_original]
            mapped_l1 = [m["level_1"] for m in mapped]
            mapped_l2 = [m["level_2"] for m in mapped]

        # ── Step 1: Compute embeddings ───────────────────────────────────────
        logger.info("[HierarchicalClassifier] Computing embeddings…")
        emb = self._embed(texts)

        self.embeddings   = emb
        self.labels_l1    = mapped_l1
        self.labels_l2    = mapped_l2
        self.texts_train  = texts

        # ── Step 1b: Build FAISS index ───────────────────────────────────────
        self.faiss_index = self._build_faiss_index(emb)
        logger.info("[HierarchicalClassifier] FAISS index ready" if self.faiss_index else "[HierarchicalClassifier] Using numpy KNN fallback")
        from collections import Counter
        l1_dist = Counter(mapped_l1)
        logger.info(f"[HierarchicalClassifier] L1 distribution: {dict(l1_dist)}")

        # ── Step 3: Train L2 specialized classifiers ──────────────────────────
        self.l2_models      = {}
        self.l2_vectorizers = {}
        l2_stats            = {}

        l1_categories = list(l1_dist.keys())

        for l1_name in l1_categories:
            idx = [i for i, l in enumerate(mapped_l1) if l == l1_name]
            sub_texts  = [texts[i] for i in idx]
            sub_labels = [mapped_l2[i] for i in idx]

            l2_sub_dist = Counter(sub_labels)
            n_classes = len(l2_sub_dist)
            n_samples = len(sub_texts)

            l2_stats[l1_name] = {
                "n_samples": n_samples,
                "n_classes": n_classes,
                "distribution": dict(l2_sub_dist),
                "model": "none"
            }

            if n_samples < MIN_SAMPLES_L2 or n_classes < 2:
                logger.warning(f"[HierarchicalClassifier] L1={l1_name}: too few samples ({n_samples}) or classes ({n_classes}) for L2 model — LLM fallback will be used")
                continue

            try:
                tfidf = TfidfVectorizer(
                    max_features=500,
                    ngram_range=(1, 2),
                    min_df=1,
                    sublinear_tf=True
                )
                X_l2 = tfidf.fit_transform(sub_texts)
                clf  = LogisticRegression(
                    max_iter=500,
                    class_weight="balanced",
                    random_state=42,
                    C=1.0
                )
                clf.fit(X_l2, sub_labels)

                # Quick F1 on training data (indicative only given small size)
                y_pred = clf.predict(X_l2)
                macro_f1 = f1_score(sub_labels, y_pred, average="macro", zero_division=0)

                self.l2_models[l1_name]      = clf
                self.l2_vectorizers[l1_name] = tfidf
                l2_stats[l1_name]["model"]   = "LogisticRegression"
                l2_stats[l1_name]["train_f1"] = round(float(macro_f1), 3)
                logger.info(f"[HierarchicalClassifier] L1={l1_name}: L2 model trained (f1={macro_f1:.3f})")
            except Exception as e:
                logger.warning(f"[HierarchicalClassifier] L2 training failed for {l1_name}: {e}")

        self.is_trained = True

        # ── Save ─────────────────────────────────────────────────────────────
        self._save(l1_dist, l2_stats, len(texts))

        return {
            "status": "trained",
            "n_samples": len(texts),
            "l1_categories": l1_categories,
            "l1_distribution": dict(l1_dist),
            "l2_stats": l2_stats,
            "trained_at": datetime.now().isoformat(),
        }

    # ──────────────────────────────────────────────
    # Prediction
    # ──────────────────────────────────────────────

    def predict_single(
        self,
        text: str,
        groq_client=None,
        k: int = 5,
    ) -> Dict[str, Any]:
        """
        Predict L1 + L2 for a single ticket text.

        Hybrid strategy:
          - Embedding similarity (FAISS/numpy KNN, k=5) weighted by ALPHA_SIMILARITY
          - BRASIL keyword boost weighted by BETA_KEYWORD
          - Confidence = W_SIM * top_sim + W_AGREEMENT * neighbor_agreement + W_KEYWORD * keyword_boost
        """
        import numpy as np

        if not self.is_trained or self.embeddings is None:
            raise RuntimeError("Model not trained. Call train() first.")

        # ── Step 1: Embed query ───────────────────────────────────────────────
        model = self._get_embedder()
        if model is not None:
            try:
                q_emb = model.encode([text], normalize_embeddings=True)[0]
            except Exception:
                q_emb = self._embed([text])[0]
        else:
            q_emb = self._embed([text])[0]

        # ── Step 2: KNN retrieval (FAISS or numpy fallback) ──────────────────
        if self.faiss_index is not None:
            try:
                import faiss  # type: ignore
                q_vec = np.array([q_emb], dtype=np.float32)
                scores, indices = self.faiss_index.search(q_vec, k)
                top_k_idx  = indices[0].tolist()
                top_k_sims = scores[0].tolist()
            except Exception:
                sims = self.embeddings @ q_emb
                top_k_idx  = np.argsort(sims)[::-1][:k].tolist()
                top_k_sims = sims[np.array(top_k_idx)].tolist()
        else:
            sims = self.embeddings @ q_emb
            top_k_idx  = np.argsort(sims)[::-1][:k].tolist()
            top_k_sims = sims[np.array(top_k_idx)].tolist()

        top_k_l1    = [self.labels_l1[i] for i in top_k_idx]
        top_k_l2    = [self.labels_l2[i] for i in top_k_idx]
        top_k_texts = [self.texts_train[i] for i in top_k_idx]

        # ── Step 3: Embedding similarity vote (per-L1 weighted sum) ──────────
        sim_l1_scores: Dict[str, float] = {}
        for sim, l1 in zip(top_k_sims, top_k_l1):
            sim_l1_scores[l1] = sim_l1_scores.get(l1, 0.0) + float(sim)
        # Normalize so sum = 1
        total_sim = sum(sim_l1_scores.values()) or 1.0
        sim_l1_norm = {l1: v / total_sim for l1, v in sim_l1_scores.items()}

        # ── Step 4: Keyword boost vote ────────────────────────────────────────
        kw_l1_scores, kw_total_boost = compute_keyword_boost(text)

        # ── Step 5: Hybrid L1 vote (alpha * sim + beta * keyword) ────────────
        all_l1 = set(sim_l1_norm) | set(kw_l1_scores)
        hybrid_l1: Dict[str, float] = {}
        for l1 in all_l1:
            hybrid_l1[l1] = (
                ALPHA_SIMILARITY * sim_l1_norm.get(l1, 0.0)
                + BETA_KEYWORD   * kw_l1_scores.get(l1, 0.0)
            )
        pred_l1   = max(hybrid_l1, key=hybrid_l1.get)
        l1_top_sim = float(top_k_sims[0])

        # Neighbor agreement ratio (fraction of k neighbours agreeing on pred_l1)
        neighbor_agreement = top_k_l1.count(pred_l1) / max(len(top_k_l1), 1)

        # ── Step 6: Confidence score ──────────────────────────────────────────
        l1_confidence = (
            W_SIM       * l1_top_sim
            + W_AGREEMENT * neighbor_agreement
            + W_KEYWORD   * kw_total_boost
        )

        nearest_neighbors = [
            {
                "text":       top_k_texts[i][:150],
                "l1":         top_k_l1[i],
                "l2":         top_k_l2[i],
                "similarity": round(float(top_k_sims[i]), 4),
            }
            for i in range(min(3, len(top_k_idx)))
        ]

        # ── Step 7: L2 prediction ─────────────────────────────────────────────
        pred_l2       = "UNDETERMINED"
        l2_confidence = 0.0
        l2_source     = "none"

        if pred_l1 in self.l2_models:
            try:
                vec   = self.l2_vectorizers[pred_l1]
                clf   = self.l2_models[pred_l1]
                X_q   = vec.transform([text])
                proba = clf.predict_proba(X_q)[0]
                pred_l2       = clf.classes_[int(np.argmax(proba))]
                l2_confidence = float(np.max(proba))
                l2_source     = "LogisticRegression"
            except Exception as e:
                logger.warning(f"[HierarchicalClassifier] L2 LR prediction failed: {e}")

        # If LR gave nothing useful, try keyword-based L2 within the predicted domain
        if l2_source == "none" or l2_confidence < THRESHOLD_L2_MEDIUM:
            kw_l2_scores = compute_keyword_boost_l2(text, pred_l1)
            if kw_l2_scores:
                kw_best_l2 = max(kw_l2_scores, key=kw_l2_scores.get)
                if l2_confidence < THRESHOLD_L2_MEDIUM:
                    pred_l2       = kw_best_l2
                    l2_confidence = max(l2_confidence, kw_l2_scores[kw_best_l2] * 0.85)
                    l2_source     = "keyword_boost" if l2_source == "none" else "lr+keyword_boost"
            elif l2_source == "none":
                # Fallback: nearest neighbor with same L1
                l2_from_nn = [l2 for l1, l2 in zip(top_k_l1, top_k_l2) if l1 == pred_l1]
                if l2_from_nn:
                    pred_l2       = l2_from_nn[0]
                    l2_confidence = l1_top_sim * 0.8
                    l2_source     = "nearest_neighbor"

        # ── Step 8: Confidence tier ───────────────────────────────────────────
        tier = self._compute_tier(l1_confidence, l2_confidence)

        # ── Step 9: LLM fallback for low confidence ───────────────────────────
        llm_used      = False
        llm_rationale = None

        if tier == "LOW" and groq_client is not None:
            try:
                llm_result = self._llm_fallback(
                    text=text,
                    nearest_neighbors=nearest_neighbors,
                    pred_l1=pred_l1,
                    groq_client=groq_client,
                )
                if llm_result:
                    pred_l1       = llm_result.get("level_1", pred_l1)
                    pred_l2       = llm_result.get("level_2", pred_l2)
                    l1_confidence = llm_result.get("confidence", l1_confidence)
                    l2_confidence = llm_result.get("confidence", l2_confidence)
                    llm_rationale = llm_result.get("rationale")
                    llm_used      = True
                    tier          = "MEDIUM"
            except Exception as e:
                logger.warning(f"[HierarchicalClassifier] LLM fallback failed: {e}")

        return {
            "level_1":             pred_l1,
            "level_2":             pred_l2,
            "level_1_confidence":  round(l1_confidence, 4),
            "level_2_confidence":  round(l2_confidence, 4),
            "confidence_tier":     tier,
            "l2_source":           l2_source,
            "llm_used":            llm_used,
            "llm_rationale":       llm_rationale,
            "nearest_neighbors":   nearest_neighbors,
            "needs_review":        tier in ("LOW", "MEDIUM"),
            # Extra debug info
            "keyword_boost":       round(kw_total_boost, 4),
            "neighbor_agreement":  round(neighbor_agreement, 4),
        }



    def predict_batch(
        self,
        texts: List[str],
        groq_client=None,
    ) -> List[Dict[str, Any]]:
        """Predict for a list of texts."""
        return [self.predict_single(t, groq_client=groq_client) for t in texts]

    # ──────────────────────────────────────────────
    # Confidence helpers
    # ──────────────────────────────────────────────

    def _compute_tier(self, l1_confidence: float, l2_prob: float) -> str:
        """Classify prediction quality into HIGH / MEDIUM / LOW."""
        if l1_confidence >= THRESHOLD_L1_HIGH and l2_prob >= THRESHOLD_L2_HIGH:
            return "HIGH"
        if l1_confidence >= THRESHOLD_L1_MEDIUM and l2_prob >= THRESHOLD_L2_MEDIUM:
            return "MEDIUM"
        return "LOW"

    # ──────────────────────────────────────────────
    # LLM Fallback
    # ──────────────────────────────────────────────

    def _llm_fallback(
        self,
        text: str,
        nearest_neighbors: List[Dict],
        pred_l1: str,
        groq_client,
    ) -> Optional[Dict[str, Any]]:
        """Call Groq with dynamic few-shot from nearest neighbors."""
        import asyncio, json as _json

        l1_cats = [c["name"] for c in self.taxonomy.get("level_1_categories", [])]
        l2_cats: List[str] = []
        for cat in self.taxonomy.get("level_1_categories", []):
            if cat["name"] == pred_l1:
                l2_cats = cat.get("level_2_categories", [])
                break
        if not l2_cats:
            l2_cats = ["CAUSE_INDETERMINEE"]

        # Build few-shot examples from nearest neighbors
        examples = "\n".join(
            f"  Ticket: \"{nn['text']}\"\n  → L1: {nn['l1']} | L2: {nn['l2']}"
            for nn in nearest_neighbors
        )

        prompt = (
            f"Tu es un expert ITSM (classification tickets IT BRASIL).\n\n"
            f"Exemples similaires:\n{examples}\n\n"
            f"Catégories L1 disponibles: {', '.join(l1_cats)}\n"
            f"Catégories L2 pour '{pred_l1}': {', '.join(l2_cats)}\n\n"
            f"Ticket à classifier:\n\"\"\"\n{text[:500]}\n\"\"\"\n\n"
            f"Réponds UNIQUEMENT en JSON strict:\n"
            f"{{\"level_1\": \"...\", \"level_2\": \"...\", \"confidence\": 0.0-1.0, \"rationale\": \"...\"}}"
        )

        try:
            if asyncio.iscoroutinefunction(groq_client.generate):
                loop = asyncio.new_event_loop()
                raw = loop.run_until_complete(
                    groq_client.generate(
                        prompt=prompt,
                        system_prompt="Réponds uniquement en JSON strict. Pas d'explication hors JSON.",
                        max_tokens=200,
                    )
                )
                loop.close()
            else:
                raw = groq_client.generate(prompt=prompt, max_tokens=200)

            # Extract JSON from response
            start = raw.find("{")
            end   = raw.rfind("}") + 1
            if start >= 0 and end > start:
                return _json.loads(raw[start:end])
        except Exception as e:
            logger.warning(f"[HierarchicalClassifier] LLM parse error: {e}")
        return None

    # ──────────────────────────────────────────────
    # Persistence
    # ──────────────────────────────────────────────

    def _save(self, l1_dist, l2_stats, n_samples: int):
        """Persist model state to disk."""
        try:
            state = {
                "embeddings":    self.embeddings,
                "labels_l1":     self.labels_l1,
                "labels_l2":     self.labels_l2,
                "texts_train":   self.texts_train,
                "l2_models":     self.l2_models,
                "l2_vectorizers":self.l2_vectorizers,
            }
            with open(self.model_path, "wb") as f:
                pickle.dump(state, f)

            # Persist FAISS index separately (faiss has its own serialisation)
            faiss_path = self.data_dir / "hierarchical_faiss.index"
            if self.faiss_index is not None:
                try:
                    import faiss  # type: ignore
                    faiss.write_index(self.faiss_index, str(faiss_path))
                except Exception as fe:
                    logger.warning(f"[HierarchicalClassifier] FAISS save failed: {fe}")

            card = {
                "trained_at":    datetime.now().isoformat(),
                "n_samples":     n_samples,
                "l1_distribution": dict(l1_dist),
                "l2_stats":      l2_stats,
                "model_name":    "paraphrase-multilingual-mpnet-base-v2",
                "thresholds": {
                    "l1_high":      THRESHOLD_L1_HIGH,
                    "l1_medium":    THRESHOLD_L1_MEDIUM,
                    "l2_high":      THRESHOLD_L2_HIGH,
                    "l2_medium":    THRESHOLD_L2_MEDIUM,
                    "min_l2_samples": MIN_SAMPLES_L2,
                },
                "hybrid_weights": {
                    "alpha_similarity": ALPHA_SIMILARITY,
                    "beta_keyword":     BETA_KEYWORD,
                    "w_sim":            W_SIM,
                    "w_agreement":      W_AGREEMENT,
                    "w_keyword":        W_KEYWORD,
                },
            }
            with open(self.card_path, "w", encoding="utf-8") as f:
                json.dump(card, f, ensure_ascii=False, indent=2)
            self.card = card
            logger.info(f"[HierarchicalClassifier] Model saved ({n_samples} samples)")
        except Exception as e:
            logger.error(f"[HierarchicalClassifier] Save failed: {e}")

    def load(self) -> bool:
        """Load model from disk."""
        if not self.model_path.exists():
            return False
        try:
            with open(self.model_path, "rb") as f:
                state = pickle.load(f)
            self.embeddings     = state["embeddings"]
            self.labels_l1      = state["labels_l1"]
            self.labels_l2      = state["labels_l2"]
            self.texts_train    = state["texts_train"]
            self.l2_models      = state["l2_models"]
            self.l2_vectorizers = state["l2_vectorizers"]
            self.is_trained     = True

            # Try to reload FAISS index; rebuild from embeddings if unavailable
            faiss_path = self.data_dir / "hierarchical_faiss.index"
            if faiss_path.exists():
                try:
                    import faiss  # type: ignore
                    self.faiss_index = faiss.read_index(str(faiss_path))
                    logger.info(f"[HierarchicalClassifier] FAISS index loaded ({self.faiss_index.ntotal} vectors)")
                except Exception as fe:
                    logger.warning(f"[HierarchicalClassifier] FAISS load failed, rebuilding: {fe}")
                    self.faiss_index = self._build_faiss_index(self.embeddings)
            elif self.embeddings is not None:
                self.faiss_index = self._build_faiss_index(self.embeddings)

            if self.card_path.exists():
                with open(self.card_path, "r", encoding="utf-8") as f:
                    self.card = json.load(f)
            logger.info("[HierarchicalClassifier] Model loaded from disk")
            return True
        except Exception as e:
            logger.error(f"[HierarchicalClassifier] Load failed: {e}")
            return False

    def get_info(self) -> Dict[str, Any]:
        """Return model card info."""
        if self.card:
            return {"exists": True, **self.card}
        if self.card_path.exists():
            try:
                with open(self.card_path, "r", encoding="utf-8") as f:
                    self.card = json.load(f)
                return {"exists": True, **self.card}
            except Exception:
                pass
        return {"exists": False}
