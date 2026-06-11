"""
ML Classification Service
Handles ML model training, prediction, and management
Idea F: Hybrid TF-IDF + Sentence Transformers (paraphrase-multilingual-MiniLM-L12-v2)
"""
from __future__ import annotations  # rend toutes les annotations lazily évaluées (PEP 563)
import os
import json
import pickle
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path

# NOTE: numpy, pandas, sklearn importés lazily dans les méthodes pour ne pas
# bloquer le démarrage (~40s sur OneDrive à cause du scan de fichiers).
# Ils sont chargés une seule fois au premier appel à train() ou predict().
_np = None
_pd = None
SKLEARN_AVAILABLE: Optional[bool] = None  # None = non encore testé


def _get_np():
    global _np
    if _np is None:
        import numpy as np
        _np = np
    return _np


def _get_pd():
    global _pd
    if _pd is None:
        import pandas as pd
        _pd = pd
    return _pd


def _ensure_sklearn():
    global SKLEARN_AVAILABLE
    if SKLEARN_AVAILABLE is None:
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer  # noqa
            SKLEARN_AVAILABLE = True
        except ImportError:
            SKLEARN_AVAILABLE = False
    return SKLEARN_AVAILABLE

# Idea F: Sentence Transformers for semantic embeddings — import LAZY pour ne pas bloquer le démarrage
# (~567s sur OneDrive à cause du scan de fichiers torch/transformers)
_ST_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
_sentence_transformer = None
SENTENCE_TRANSFORMERS_AVAILABLE: Optional[bool] = None  # None = non encore testé

from app.core.logging import get_logger

logger = get_logger(__name__)

# ── Lazy-load TelecomPreprocessor (évite import circulaire potentiel) ─────────
_telecom_preprocessor = None

def _get_preprocessor():
    global _telecom_preprocessor
    if _telecom_preprocessor is None:
        try:
            from app.services.ml_preprocessing import TelecomPreprocessor
            _telecom_preprocessor = TelecomPreprocessor()
            logger.info("[MLClassifier] TelecomPreprocessor chargé")
        except Exception as e:
            logger.warning(f"[MLClassifier] TelecomPreprocessor non disponible: {e}")
    return _telecom_preprocessor

# Versioning : combien de versions on conserve
_MAX_MODEL_VERSIONS = 5


def _get_sentence_transformer():
    """Lazy-load the sentence transformer (singleton) — importe sentence_transformers la première fois."""
    global _sentence_transformer, SENTENCE_TRANSFORMERS_AVAILABLE
    # Tester la disponibilité une seule fois
    if SENTENCE_TRANSFORMERS_AVAILABLE is None:
        try:
            from sentence_transformers import SentenceTransformer as _ST  # noqa: F401
            SENTENCE_TRANSFORMERS_AVAILABLE = True
        except ImportError:
            SENTENCE_TRANSFORMERS_AVAILABLE = False
    if not SENTENCE_TRANSFORMERS_AVAILABLE:
        return None
    if _sentence_transformer is None:
        try:
            from sentence_transformers import SentenceTransformer
            _sentence_transformer = SentenceTransformer(_ST_MODEL_NAME)
            logger.info(f"[MLClassifier] Sentence Transformer loaded: {_ST_MODEL_NAME}")
        except Exception as e:
            logger.warning(f"[MLClassifier] Failed to load Sentence Transformer: {e}")
            return None
    return _sentence_transformer


class MLClassifier:
    """Wrapper for ML classification model with calibration.
    Idea F: Uses hybrid TF-IDF + Sentence Transformer features when available.
    """

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        self.model_path = self.data_dir / "model_classifier.pkl"
        self.vectorizer_path = self.data_dir / "vectorizer.pkl"
        self.model_card_path = self.data_dir / "model_card.json"
        self.versions_dir = self.data_dir / "model_versions"
        self.versions_dir.mkdir(exist_ok=True)

        self.model = None
        self.vectorizer = None
        self.model_card = None
        self._use_hybrid = False  # set to True when ST embeddings were used at train time
        self._use_preprocessing = True  # TelecomPreprocessor enabled by default
        
    def load(self) -> bool:
        """Load model and vectorizer from disk"""
        try:
            if self.model_path.exists() and self.vectorizer_path.exists():
                with open(self.model_path, "rb") as f:
                    self.model = pickle.load(f)
                with open(self.vectorizer_path, "rb") as f:
                    vec_data = pickle.load(f)
                    # Support both old format (plain dict) and new format (with use_hybrid)
                    if isinstance(vec_data, dict) and "vec" in vec_data:
                        self.vectorizer = vec_data["vec"]
                        self._use_hybrid = vec_data.get("use_hybrid", False)
                    else:
                        self.vectorizer = vec_data
                        self._use_hybrid = False
                if self.model_card_path.exists():
                    with open(self.model_card_path, "r", encoding="utf-8") as f:
                        self.model_card = json.load(f)
                logger.info(f"ML model loaded (hybrid={self._use_hybrid})")
                return True
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
        return False
    
    def save(self) -> bool:
        """Save model and vectorizer to disk + create versioned snapshot."""
        try:
            with open(self.model_path, "wb") as f:
                pickle.dump(self.model, f)
            with open(self.vectorizer_path, "wb") as f:
                pickle.dump({"vec": self.vectorizer, "use_hybrid": self._use_hybrid}, f)
            logger.info(f"ML model saved (hybrid={self._use_hybrid})")
            # ── Versioning ────────────────────────────────────────────────
            self._save_version_snapshot()
            return True
        except Exception as e:
            logger.error(f"Failed to save model: {e}")
            return False

    def _save_version_snapshot(self):
        """Crée un snapshot versionné du modèle courant (conservation _MAX_MODEL_VERSIONS)."""
        try:
            # Numéro de version = training_count dans model_card
            version = 1
            if self.model_card and "training_count" in self.model_card:
                version = self.model_card["training_count"]
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            snap_dir = self.versions_dir / f"v{version:03d}_{ts}"
            snap_dir.mkdir(exist_ok=True)
            with open(snap_dir / "model.pkl", "wb") as f:
                pickle.dump(self.model, f)
            with open(snap_dir / "vectorizer.pkl", "wb") as f:
                pickle.dump({"vec": self.vectorizer, "use_hybrid": self._use_hybrid}, f)
            if self.model_card:
                with open(snap_dir / "model_card.json", "w", encoding="utf-8") as f:
                    import json
                    json.dump(self.model_card, f, ensure_ascii=False, indent=2)
            logger.info(f"[MLClassifier] Version snapshot saved: {snap_dir.name}")
            # Garder seulement les N dernières versions
            self._prune_versions()
        except Exception as e:
            logger.warning(f"[MLClassifier] Failed to save version snapshot: {e}")

    def _prune_versions(self):
        """Supprime les versions excédant _MAX_MODEL_VERSIONS."""
        try:
            versions = sorted(self.versions_dir.iterdir(), key=lambda p: p.stat().st_mtime)
            while len(versions) > _MAX_MODEL_VERSIONS:
                oldest = versions.pop(0)
                import shutil
                shutil.rmtree(oldest, ignore_errors=True)
                logger.info(f"[MLClassifier] Pruned old version: {oldest.name}")
        except Exception as e:
            logger.warning(f"[MLClassifier] Version pruning failed: {e}")

    def list_versions(self) -> list:
        """Retourne la liste des versions disponibles avec leurs métadonnées."""
        versions = []
        try:
            for snap in sorted(self.versions_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
                card_path = snap / "model_card.json"
                meta = {"version_dir": snap.name, "created_at": datetime.fromtimestamp(snap.stat().st_mtime).isoformat()}
                if card_path.exists():
                    try:
                        import json
                        card = json.loads(card_path.read_text(encoding="utf-8"))
                        meta.update({
                            "training_count": card.get("training_count"),
                            "macro_f1": card.get("macro_f1_val"),
                            "n_samples": card.get("n_samples"),
                            "trained_at": card.get("trained_at"),
                            "label_col": card.get("label_col"),
                            "classes_count": len(card.get("classes", [])),
                            "hybrid": card.get("hybrid_embeddings", False),
                            "preprocessing": card.get("preprocessing_enabled", False),
                        })
                    except Exception:
                        pass
                versions.append(meta)
        except Exception as e:
            logger.warning(f"[MLClassifier] list_versions failed: {e}")
        return versions

    def rollback_to_version(self, version_dir: str) -> bool:
        """Recharge le modèle depuis un snapshot versionné."""
        try:
            snap = self.versions_dir / version_dir
            if not snap.exists():
                logger.error(f"[MLClassifier] Version not found: {version_dir}")
                return False
            with open(snap / "model.pkl", "rb") as f:
                self.model = pickle.load(f)
            with open(snap / "vectorizer.pkl", "rb") as f:
                vec_data = pickle.load(f)
                self.vectorizer = vec_data["vec"]
                self._use_hybrid = vec_data.get("use_hybrid", False)
            card_path = snap / "model_card.json"
            if card_path.exists():
                import json
                self.model_card = json.loads(card_path.read_text(encoding="utf-8"))
            # Écraser le modèle courant
            self.save()
            logger.info(f"[MLClassifier] Rolled back to version: {version_dir}")
            return True
        except Exception as e:
            logger.error(f"[MLClassifier] Rollback failed: {e}")
            return False
    
    def _build_vectorizers(self, max_features: int = 5000) -> Dict:
        """Build word + char TF-IDF vectorizers"""
        from sklearn.feature_extraction.text import TfidfVectorizer
        word_vec = TfidfVectorizer(
            lowercase=True,
            strip_accents="unicode",
            min_df=2,
            ngram_range=(1, 2),
            max_features=max_features,
            sublinear_tf=True,
            token_pattern=r"(?u)\b[\w\-]{2,}\b"
        )
        char_vec = TfidfVectorizer(
            analyzer='char_wb',
            ngram_range=(3, 5),
            min_df=2,
            max_features=max_features,
            lowercase=True
        )
        return {"word": word_vec, "char": char_vec}
    
    def _vectorize_fit(self, vec_dict: Dict, texts):
        """Fit vectorizers and return combined features"""
        from scipy import sparse as sp
        Xw = vec_dict["word"].fit_transform(texts)
        Xc = vec_dict["char"].fit_transform(texts)
        X = sp.hstack([Xw, Xc], format="csr")
        return X
    
    def _vectorize_transform(self, vec_dict: Dict, texts):
        """Transform texts using fitted vectorizers"""
        from scipy import sparse as sp
        Xw = vec_dict["word"].transform(texts)
        Xc = vec_dict["char"].transform(texts)
        X = sp.hstack([Xw, Xc], format="csr")
        return X

    # ── Idea F: Hybrid features (TF-IDF + Sentence Transformers) ──────────────

    def _build_hybrid_features_fit(self, vec_dict: Dict, texts):
        """
        Fit TF-IDF and concatenate with Sentence Transformer dense embeddings.
        Falls back to TF-IDF only if ST not available.
        """
        import numpy as np
        from scipy import sparse as sp
        X_tfidf = self._vectorize_fit(vec_dict, texts)
        st = _get_sentence_transformer()
        if st is None:
            self._use_hybrid = False
            return X_tfidf
        try:
            logger.info(f"[MLClassifier] Computing ST embeddings for {len(texts)} texts...")
            st_emb = st.encode(texts.tolist(), batch_size=64, show_progress_bar=False)
            X_dense = sp.csr_matrix(st_emb.astype(np.float32))
            X_hybrid = sp.hstack([X_tfidf, X_dense], format="csr")
            self._use_hybrid = True
            logger.info(f"[MLClassifier] Hybrid features: TF-IDF ({X_tfidf.shape[1]}) + ST ({st_emb.shape[1]}) = {X_hybrid.shape[1]}")
            return X_hybrid
        except Exception as e:
            logger.warning(f"[MLClassifier] ST embedding failed, falling back to TF-IDF: {e}")
            self._use_hybrid = False
            return X_tfidf

    def _build_hybrid_features_transform(self, vec_dict: Dict, texts):
        """Transform using fitted TF-IDF + fresh ST embeddings."""
        import numpy as np
        from scipy import sparse as sp
        X_tfidf = self._vectorize_transform(vec_dict, texts)
        if not self._use_hybrid:
            return X_tfidf
        st = _get_sentence_transformer()
        if st is None:
            return X_tfidf
        try:
            st_emb = st.encode(texts.tolist(), batch_size=64, show_progress_bar=False)
            X_dense = sp.csr_matrix(st_emb.astype(np.float32))
            return sp.hstack([X_tfidf, X_dense], format="csr")
        except Exception as e:
            logger.warning(f"[MLClassifier] ST transform failed: {e}")
            return X_tfidf
    
    def train(
        self,
        df: "pd.DataFrame",
        text_col: str,
        label_col: str,
        max_features: int = 5000,
        test_size: float = 0.2
    ) -> Dict[str, Any]:
        """
        Train classification model with validation
        
        Returns dict with metrics, classes, recommended_threshold, etc.
        """
        import numpy as np
        import pandas as pd
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import classification_report, confusion_matrix, f1_score
        from sklearn.calibration import CalibratedClassifierCV
        if not _ensure_sklearn():
            raise RuntimeError("scikit-learn not available")
        
        # Force plain numpy/pandas objects — parquet loads PyArrow-backed columns
        # which cause "only integer scalar arrays" in train_test_split/_safe_indexing
        raw_texts = pd.Series(df[text_col].fillna("").astype(str).tolist())
        # Force plain numpy array — parquet files load with PyArrow-backed columns
        # which cause "only integer scalar arrays" error in train_test_split
        y_all = np.array(df[label_col].astype(str).fillna("Autre").tolist())

        # ── Preprocessing télécom métier ──────────────────────────────────
        preprocessor = _get_preprocessor()
        if preprocessor is not None and self._use_preprocessing:
            texts = pd.Series(preprocessor.preprocess_batch(raw_texts))
            logger.info(f"[MLClassifier] Preprocessing applied: {len(texts)} textes")
        else:
            texts = raw_texts

        # Build vectorizers
        vec_dict = self._build_vectorizers(max_features=max_features)
        X_all = self._build_hybrid_features_fit(vec_dict, texts)
        
        # Filter rare classes (< 2 samples)
        # Use object dtype explicitly to prevent ArrowExtensionArray backing
        y_series = pd.Series(y_all, dtype=object)
        vc_all = y_series.value_counts()
        rare_labels = vc_all[vc_all < 2].index.tolist()
        
        if rare_labels:
            mask_keep = ~y_series.isin(rare_labels)
            keep_idx = np.where(mask_keep.to_numpy(dtype=bool))[0]
            from scipy import sparse as _sp
            X_use = X_all[keep_idx]
            # Force plain numpy str array — .values on ArrowExtensionArray
            # returns ArrowExtensionArray which breaks sklearn _safe_indexing
            y_use = np.array(y_series.iloc[keep_idx].tolist(), dtype=str)
            logger.warning(f"Filtered {len(rare_labels)} rare classes for validation")
        else:
            X_use = X_all
            y_use = y_all
        
        # Check if enough data for validation
        unique_kept = np.unique(y_use)
        if len(unique_kept) < 2 or X_use.shape[0] < 5:
            # Train on all data without validation
            base = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=42)
            base.fit(X_all, y_all)
            self.model = base
            self.vectorizer = vec_dict
            self.save()
            
            return {
                "classification_report": "Validation unavailable (too few samples)",
                "macro_f1": None,
                "classes": list(getattr(base, "classes_", unique_kept)),
                "confusion_matrix": [],
                "recommended_threshold": 0.70,
                "training_count": self._get_training_count() + 1,
                "rare_labels": rare_labels
            }
        
        # Train/test split
        try:
            X_tr, X_val, y_tr, y_val = train_test_split(
                X_use, y_use, test_size=test_size, stratify=y_use, random_state=42
            )
        except ValueError:
            # Fallback to non-stratified
            X_tr, X_val, y_tr, y_val = train_test_split(
                X_use, y_use, test_size=test_size, random_state=42
            )
        
        # Train with calibration
        base = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=42)
        try:
            clf = CalibratedClassifierCV(base_estimator=base, method="isotonic", cv=3)
        except:
            clf = base
        
        clf.fit(X_tr, y_tr)
        
        # Evaluate
        y_pred_val = clf.predict(X_val)
        report = classification_report(y_val, y_pred_val, digits=3)
        cm = confusion_matrix(y_val, y_pred_val)
        macro_f1 = f1_score(y_val, y_pred_val, average="macro")
        
        # Compute recommended threshold
        probs_val = clf.predict_proba(X_val) if hasattr(clf, "predict_proba") else None
        if probs_val is not None:
            max_probs = probs_val.max(axis=1)
            recommended = self._compute_threshold(max_probs, y_val, y_pred_val)
            # ── ECE + per-class adaptive thresholds ────────────────────────────
            ece = self._compute_ece(probs_val, y_val, clf.classes_)
            per_class_thresholds = self._compute_per_class_thresholds(
                probs_val, y_val, clf.classes_
            )
        else:
            recommended = 0.70
            ece = None
            per_class_thresholds = {}

        # Save
        self.model = clf
        self.vectorizer = vec_dict
        self.save()

        result = {
            "classification_report": report,
            "macro_f1": float(round(macro_f1, 3)),
            "classes": list(getattr(clf, "classes_", unique_kept)),
            "confusion_matrix": cm.tolist(),
            "recommended_threshold": float(round(recommended, 2)),
            "training_count": self._get_training_count() + 1,
            "rare_labels": rare_labels,
            "label_distribution": {k: int(v) for k, v in pd.Series(y_all).value_counts().items()},
            "ece": float(round(ece, 4)) if ece is not None else None,
            "per_class_thresholds": per_class_thresholds,
        }

        # Save model card
        self._save_model_card(result, text_col, label_col, len(df), max_features)

        return result
    
    def _compute_threshold(self, max_probs, y_true, y_pred) -> float:
        """Compute recommended threshold targeting 85% accuracy on accepted predictions"""
        import numpy as np
        thresholds = np.arange(0.30, 0.96, 0.01)
        best_thresh = 0.50
        best_score = 0.0

        for t in thresholds:
            accept = max_probs >= t
            if accept.sum() < 3:
                continue
            acc = (y_pred[accept] == y_true[accept]).mean()
            cov = accept.mean()
            # Score = harmonic mean of accuracy and coverage (F1-like)
            score = 2 * acc * cov / (acc + cov + 1e-9)
            if acc >= 0.80 and score > best_score:
                best_thresh = t
                best_score = score

        return float(best_thresh)

    def _compute_ece(self, probs: "np.ndarray", y_true, classes, n_bins: int = 10) -> float:
        """
        Expected Calibration Error (ECE) — mesure l'écart entre confiance prédite et précision réelle.
        ECE ≈ 0 → calibration parfaite.
        ECE > 0.1 → sur/sous-confiance significative.
        """
        import numpy as np
        max_probs = probs.max(axis=1)
        class_idx = probs.argmax(axis=1)
        # Map class index back to label
        if hasattr(classes, 'tolist'):
            classes = list(classes)
        preds = [str(classes[i]) for i in class_idx]
        y_str = [str(y) for y in y_true]
        correct = np.array([p == t for p, t in zip(preds, y_str)], dtype=float)

        bins = np.linspace(0, 1, n_bins + 1)
        ece = 0.0
        n = len(max_probs)
        for i in range(n_bins):
            mask = (max_probs >= bins[i]) & (max_probs < bins[i + 1])
            if mask.sum() == 0:
                continue
            bin_conf = max_probs[mask].mean()
            bin_acc  = correct[mask].mean()
            ece += (mask.sum() / n) * abs(bin_acc - bin_conf)
        return float(ece)

    def _compute_per_class_thresholds(
        self, probs: "np.ndarray", y_true, classes, target_precision: float = 0.80
    ) -> dict:
        """
        Calcule un seuil adaptatif par classe visant target_precision% de précision.
        Les classes rares reçoivent un seuil plus bas (favorise le recall).

        Returns: {class_name: threshold}
        """
        import numpy as np
        if hasattr(classes, 'tolist'):
            classes_list = list(classes)
        else:
            classes_list = [str(c) for c in classes]

        y_str = np.array([str(y) for y in y_true])
        thresholds = {}

        for i, cls in enumerate(classes_list):
            cls_probs = probs[:, i]
            cls_true  = (y_str == str(cls)).astype(float)
            n_cls = cls_true.sum()

            if n_cls < 3:
                # Classe rare → seuil bas pour favoriser le recall
                thresholds[str(cls)] = 0.30
                continue

            # Chercher seuil minimal garantissant target_precision
            best_t = 0.30
            for t in np.arange(0.25, 0.95, 0.05):
                mask = cls_probs >= t
                if mask.sum() < 2:
                    break
                prec = cls_true[mask].mean()
                if prec >= target_precision:
                    best_t = float(round(t, 2))
                    break
            thresholds[str(cls)] = best_t

        return thresholds

    def predict_adaptive(self, texts, per_class_thresholds: dict = None) -> dict:
        """
        Prédiction avec seuils adaptatifs par classe.
        Retourne des résultats enrichis avec confidence_tier, unknown_reason, top_k.

        Returns: list of dicts with keys:
          predicted_label, confidence, confidence_tier, accepted,
          threshold_applied, unknown_reason, top_k
        """
        import numpy as np
        import pandas as pd_

        if self.model is None or self.vectorizer is None:
            raise RuntimeError("Model not loaded")

        preprocessor = _get_preprocessor()
        if preprocessor is not None and self._use_preprocessing:
            texts = pd_.Series(preprocessor.preprocess_batch(texts))

        X = self._build_hybrid_features_transform(self.vectorizer, texts)

        if not hasattr(self.model, "predict_proba"):
            preds = self.model.predict(X)
            return [{"predicted_label": str(p), "confidence": 0.5,
                     "confidence_tier": "LOW", "accepted": True,
                     "threshold_applied": 0.5, "unknown_reason": None, "top_k": []} for p in preds]

        probs = self.model.predict_proba(X)
        classes = list(self.model.classes_)

        # Fallback to global threshold from model_card
        if per_class_thresholds is None:
            per_class_thresholds = {}
            if self.model_card:
                per_class_thresholds = self.model_card.get("per_class_thresholds", {})
        global_thresh = self.model_card.get("recommended_threshold", 0.50) if self.model_card else 0.50

        results = []
        for row_probs in probs:
            top_idx  = int(np.argmax(row_probs))
            top_cls  = str(classes[top_idx])
            top_conf = float(row_probs[top_idx])

            thresh = per_class_thresholds.get(top_cls, global_thresh)
            accepted = top_conf >= thresh

            # Top-k alternatives
            sorted_idx = np.argsort(row_probs)[::-1][:3]
            top_k = [
                {"label": str(classes[j]), "confidence": round(float(row_probs[j]), 3)}
                for j in sorted_idx
            ]

            # Confidence tier
            if top_conf >= 0.75:
                tier = "HIGH"
            elif top_conf >= 0.50:
                tier = "MEDIUM"
            else:
                tier = "LOW"

            unknown_reason = None
            if not accepted:
                if top_conf < 0.35:
                    unknown_reason = f"Confiance très faible ({top_conf:.0%}) — ticket ambigu ou vocabulaire inconnu"
                else:
                    unknown_reason = f"Sous le seuil adaptatif pour '{top_cls}' ({thresh:.0%} requis, {top_conf:.0%} obtenu)"

            results.append({
                "predicted_label":    top_cls if accepted else "UNKNOWN",
                "raw_label":          top_cls,
                "confidence":         round(top_conf, 3),
                "confidence_tier":    tier,
                "accepted":           accepted,
                "threshold_applied":  round(thresh, 3),
                "unknown_reason":     unknown_reason,
                "top_k":              top_k,
            })

        return results
    
    def predict(
        self,
        texts: "pd.Series",
        threshold: float = 0.7
    ) -> Tuple:
        """
        Predict labels with confidence scores
        
        Returns: (predictions, confidences, all_probabilities)
        """
        import numpy as np
        pd = _get_pd()
        if self.model is None or self.vectorizer is None:
            raise RuntimeError("Model not loaded")

        # Appliquer le même preprocessing qu'à l'entraînement
        preprocessor = _get_preprocessor()
        if preprocessor is not None and self._use_preprocessing:
            texts = pd.Series(preprocessor.preprocess_batch(texts))

        X = self._build_hybrid_features_transform(self.vectorizer, texts)
        
        if hasattr(self.model, "predict_proba"):
            probs = self.model.predict_proba(X)
            preds = self.model.predict(X)
            max_probs = probs.max(axis=1)
            return preds, max_probs, probs
        else:
            preds = self.model.predict(X)
            conf = np.array([0.5] * len(preds))
            return preds, conf, None
    
    def _get_training_count(self) -> int:
        """Get current training count from model card"""
        if self.model_card and "training_count" in self.model_card:
            return self.model_card["training_count"]
        return 0
    
    def _save_model_card(
        self,
        metrics: Dict,
        text_col: str,
        label_col: str,
        n_samples: int,
        max_features: int
    ):
        """Save model metadata"""
        card = {
            "trained_at": datetime.now().isoformat(),
            "training_count": metrics.get("training_count", 1),
            "label_col": label_col,
            "text_col": text_col,
            "n_samples": n_samples,
            "classes": metrics.get("classes", []),
            "macro_f1_val": metrics.get("macro_f1"),
            "recommended_threshold": metrics.get("recommended_threshold", 0.70),
            "vectorizer": {
                "max_features": max_features,
                "ngram_range": [[1, 2], [3, 5]]
            },
            "rare_labels": metrics.get("rare_labels", []),
            "label_distribution": metrics.get("label_distribution", {}),
            "hybrid_embeddings": self._use_hybrid,
            "sentence_transformer_model": _ST_MODEL_NAME if self._use_hybrid else None,
            "preprocessing_enabled": self._use_preprocessing,
            "preprocessor": "TelecomPreprocessor" if self._use_preprocessing else None,
            "ece": metrics.get("ece"),
            "per_class_thresholds": metrics.get("per_class_thresholds", {}),
        }
        
        try:
            with open(self.model_card_path, "w", encoding="utf-8") as f:
                json.dump(card, f, ensure_ascii=False, indent=2)
            self.model_card = card
        except Exception as e:
            logger.error(f"Failed to save model card: {e}")
    
    def get_info(self) -> Dict[str, Any]:
        """Get model information"""
        # Auto-load from disk if not in memory (e.g. after server restart)
        if self.model is None and self.model_path.exists():
            self.load()
        if self.model_card_path.exists():
            try:
                with open(self.model_card_path, "r", encoding="utf-8") as f:
                    card = json.load(f)
                return {
                    "exists": True,
                    "trained_at": card.get("trained_at"),
                    "training_count": card.get("training_count", 0),
                    "label_col": card.get("label_col"),
                    "n_samples": card.get("n_samples"),
                    "classes": card.get("classes", []),
                    "macro_f1": card.get("macro_f1_val"),
                    "recommended_threshold": card.get("recommended_threshold", 0.7),
                    "use_sentence_transformers": card.get("use_sentence_transformers", False),
                    "label_distribution": card.get("label_distribution", {}),
                }
            except:
                pass
        # Model pkl loaded but no card yet — return minimal exists:True
        if self.model is not None:
            classes = list(getattr(self.model, "classes_", []))
            return {
                "exists": True,
                "trained_at": None,
                "training_count": 0,
                "label_col": None,
                "n_samples": None,
                "classes": [str(c) for c in classes],
                "macro_f1": None,
                "recommended_threshold": 0.7,
                "weak_points": [],
            }
        return {"exists": False}
