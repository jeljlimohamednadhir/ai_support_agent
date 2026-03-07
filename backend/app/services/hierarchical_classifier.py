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
            "name": "INCIDENT_UTILISATEUR",
            "description": "Problèmes liés au comportement, droits, erreurs humaines ou demandes non justifiées.",
            "level_2_categories": ["MAUVAIS_USAGE", "ANNULATION_UTILISATEUR", "INCIDENT_DISPARU", "ASSISTANCE_UTILISATEUR"]
        },
        {
            "name": "INCIDENT_APPLICATIF",
            "description": "Dysfonctionnements dans la logique applicative, fonctionnalités, traitements ou composants.",
            "level_2_categories": ["BUG_FONCTIONNEL", "TRAITEMENT_INCOMPLET", "NON_CONFORMITE_APPLICATIVE", "INTERFACE_APPLICATIVE"]
        },
        {
            "name": "INCIDENT_DONNEES",
            "description": "Problèmes d'intégrité, corruption, incohérence ou qualité des données.",
            "level_2_categories": ["INCOHERENCE_DONNEES", "DONNEES_CORROMPUES", "CORRECTION_AUTOMATIQUE"]
        },
        {
            "name": "INCIDENT_INFRASTRUCTURE",
            "description": "Pannes ou dégradations matérielles, réseau, serveur ou middleware.",
            "level_2_categories": ["SERVEUR_RESEAU", "INTERFACE_SYSTEME"]
        },
        {
            "name": "DEMANDE_SERVICE",
            "description": "Demandes planifiées, travaux, évolutions ou causes non déterminées.",
            "level_2_categories": ["DEMANDE_TRAVAUX", "ANNULATION_PROCESS", "CAUSE_INDETERMINEE"]
        },
    ],
    "label_mapping": {
        "ANNULATION PROCESS":                              {"level_1": "DEMANDE_SERVICE",         "level_2": "ANNULATION_PROCESS"},
        "ANNULATION UTILISATEUR":                          {"level_1": "INCIDENT_UTILISATEUR",     "level_2": "ANNULATION_UTILISATEUR"},
        "APPLICATIF":                                      {"level_1": "INCIDENT_APPLICATIF",      "level_2": "BUG_FONCTIONNEL"},
        "APPLICATION COMPOSANT - FONCTIONNALITE":          {"level_1": "INCIDENT_APPLICATIF",      "level_2": "BUG_FONCTIONNEL"},
        "ASSISTANCE":                                      {"level_1": "INCIDENT_UTILISATEUR",     "level_2": "ASSISTANCE_UTILISATEUR"},
        "BON USAGE":                                       {"level_1": "INCIDENT_UTILISATEUR",     "level_2": "MAUVAIS_USAGE"},
        "CAUSE INDETERMINEE":                              {"level_1": "DEMANDE_SERVICE",          "level_2": "CAUSE_INDETERMINEE"},
        "DEMANDE DE TRAVAUX":                              {"level_1": "DEMANDE_SERVICE",          "level_2": "DEMANDE_TRAVAUX"},
        "DONNEES":                                         {"level_1": "INCIDENT_DONNEES",         "level_2": "INCOHERENCE_DONNEES"},
        "FONCTIONNALITE - DONNEE CORROMPUE":               {"level_1": "INCIDENT_DONNEES",         "level_2": "DONNEES_CORROMPUES"},
        "INCOHERENCE CORRIGEE PAR OUTIL OU SCRIPT":        {"level_1": "INCIDENT_DONNEES",         "level_2": "CORRECTION_AUTOMATIQUE"},
        "INCOHERENCE DE DONNEES":                          {"level_1": "INCIDENT_DONNEES",         "level_2": "INCOHERENCE_DONNEES"},
        "INFRASTRUCTURE TECHNIQUE - SERVEUR ET RESEAU":    {"level_1": "INCIDENT_INFRASTRUCTURE",  "level_2": "SERVEUR_RESEAU"},
        "INTERFACE AUTRE":                                 {"level_1": "INCIDENT_APPLICATIF",      "level_2": "INTERFACE_APPLICATIVE"},
        "INTERFACE ORACLE":                                {"level_1": "INCIDENT_INFRASTRUCTURE",  "level_2": "INTERFACE_SYSTEME"},
        "MECONNAISSANCE USAGE":                            {"level_1": "INCIDENT_UTILISATEUR",     "level_2": "MAUVAIS_USAGE"},
        "NON CONFORMITE":                                  {"level_1": "INCIDENT_APPLICATIF",      "level_2": "NON_CONFORMITE_APPLICATIVE"},
        "SERVEUR":                                         {"level_1": "INCIDENT_INFRASTRUCTURE",  "level_2": "SERVEUR_RESEAU"},
        "TRAITEMENT IMPOSSIBLE - DESCRIPTION INCOMPLETE":  {"level_1": "INCIDENT_APPLICATIF",      "level_2": "TRAITEMENT_INCOMPLET"},
        "UTILISATEUR":                                     {"level_1": "INCIDENT_UTILISATEUR",     "level_2": "ASSISTANCE_UTILISATEUR"},
        "UTILISATEUR - INCIDENT DISPARU":                  {"level_1": "INCIDENT_UTILISATEUR",     "level_2": "INCIDENT_DISPARU"},
    }
}

# ─────────────────────────────────────────────────────────────────────────────
# Confidence thresholds
# ─────────────────────────────────────────────────────────────────────────────
THRESHOLD_L1_HIGH   = 0.75   # HIGH confidence — direct label
THRESHOLD_L1_MEDIUM = 0.65   # MEDIUM — label + flag review
THRESHOLD_L2_HIGH   = 0.70
THRESHOLD_L2_MEDIUM = 0.60
MIN_SAMPLES_L2      = 5      # below this, skip L2 model → LLM fallback


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
        self.embeddings: Optional[Any]   = None   # np.ndarray shape (N, 384)
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
        return {"level_1": "DEMANDE_SERVICE", "level_2": "CAUSE_INDETERMINEE"}

    # ──────────────────────────────────────────────
    # Embedding
    # ──────────────────────────────────────────────

    def _get_embedder(self):
        """Lazy-load sentence transformer."""
        try:
            from sentence_transformers import SentenceTransformer
            cache_dir = str(self.data_dir / "models")
            model = SentenceTransformer(
                "paraphrase-multilingual-MiniLM-L12-v2",
                cache_folder=cache_dir
            )
            return model
        except Exception as e:
            logger.warning(f"[HierarchicalClassifier] SentenceTransformer unavailable: {e}")
            return None

    def _embed(self, texts: List[str]) -> Any:
        """Encode texts → numpy array (N, 384). Falls back to TF-IDF vectors."""
        import numpy as np
        model = self._get_embedder()
        if model is not None:
            try:
                return model.encode(texts, batch_size=32, show_progress_bar=False, normalize_embeddings=True)
            except Exception as e:
                logger.warning(f"[HierarchicalClassifier] Encoding failed: {e}")
        # TF-IDF fallback (dim=384 padded)
        logger.warning("[HierarchicalClassifier] Using TF-IDF fallback for embeddings")
        from sklearn.feature_extraction.text import TfidfVectorizer
        vec = TfidfVectorizer(max_features=384, ngram_range=(1, 2))
        X = vec.fit_transform(texts).toarray()
        # Normalize
        norms = np.linalg.norm(X, axis=1, keepdims=True)
        norms[norms == 0] = 1
        return (X / norms).astype(np.float32)

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

        # ── Step 2: Validate L1 distribution ─────────────────────────────────
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
        Returns a rich dict with confidence, tier, nearest neighbors.
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

        # ── Step 2: KNN cosine similarity for L1 ─────────────────────────────
        sims = self.embeddings @ q_emb  # cosine (embeddings are normalized)
        top_k_idx = np.argsort(sims)[::-1][:k]
        top_k_sims = sims[top_k_idx]
        top_k_l1   = [self.labels_l1[i] for i in top_k_idx]
        top_k_l2   = [self.labels_l2[i] for i in top_k_idx]
        top_k_texts= [self.texts_train[i] for i in top_k_idx]

        # Weighted vote for L1
        l1_scores: Dict[str, float] = {}
        for sim, l1 in zip(top_k_sims, top_k_l1):
            l1_scores[l1] = l1_scores.get(l1, 0.0) + float(sim)
        pred_l1     = max(l1_scores, key=l1_scores.get)
        l1_sim      = float(top_k_sims[0])  # nearest neighbor similarity
        l1_confidence = l1_sim

        nearest_neighbors = [
            {"text": top_k_texts[i][:150], "l1": top_k_l1[i], "l2": top_k_l2[i], "similarity": round(float(top_k_sims[i]), 4)}
            for i in range(min(3, len(top_k_idx)))
        ]

        # ── Step 3: L2 prediction ─────────────────────────────────────────────
        pred_l2       = "CAUSE_INDETERMINEE"
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
                logger.warning(f"[HierarchicalClassifier] L2 prediction failed: {e}")
        else:
            # No L2 model for this L1 — derive from nearest neighbor
            l2_from_nn  = [l2 for l1, l2 in zip(top_k_l1, top_k_l2) if l1 == pred_l1]
            if l2_from_nn:
                pred_l2       = l2_from_nn[0]
                l2_confidence = l1_sim * 0.8  # reduced confidence
                l2_source     = "nearest_neighbor"

        # ── Step 4: Confidence tier ───────────────────────────────────────────
        tier = self._compute_tier(l1_confidence, l2_confidence)

        # ── Step 5: LLM fallback ──────────────────────────────────────────────
        llm_used = False
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
            "level_1":           pred_l1,
            "level_2":           pred_l2,
            "level_1_confidence": round(l1_confidence, 4),
            "level_2_confidence": round(l2_confidence, 4),
            "confidence_tier":    tier,
            "l2_source":          l2_source,
            "llm_used":           llm_used,
            "llm_rationale":      llm_rationale,
            "nearest_neighbors":  nearest_neighbors,
            "needs_review":       tier in ("LOW", "MEDIUM"),
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

    def _compute_tier(self, l1_sim: float, l2_prob: float) -> str:
        if l1_sim >= THRESHOLD_L1_HIGH and l2_prob >= THRESHOLD_L2_HIGH:
            return "HIGH"
        if l1_sim >= THRESHOLD_L1_MEDIUM and l2_prob >= THRESHOLD_L2_MEDIUM:
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

            card = {
                "trained_at":    datetime.now().isoformat(),
                "n_samples":     n_samples,
                "l1_distribution": dict(l1_dist),
                "l2_stats":      l2_stats,
                "thresholds": {
                    "l1_high":   THRESHOLD_L1_HIGH,
                    "l1_medium": THRESHOLD_L1_MEDIUM,
                    "l2_high":   THRESHOLD_L2_HIGH,
                    "l2_medium": THRESHOLD_L2_MEDIUM,
                    "min_l2_samples": MIN_SAMPLES_L2,
                }
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
