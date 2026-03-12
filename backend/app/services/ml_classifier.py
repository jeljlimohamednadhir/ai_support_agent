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

        self.model = None
        self.vectorizer = None
        self.model_card = None
        self._use_hybrid = False  # set to True when ST embeddings were used at train time
        
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
        """Save model and vectorizer to disk"""
        try:
            with open(self.model_path, "wb") as f:
                pickle.dump(self.model, f)
            with open(self.vectorizer_path, "wb") as f:
                pickle.dump({"vec": self.vectorizer, "use_hybrid": self._use_hybrid}, f)
            logger.info(f"ML model saved (hybrid={self._use_hybrid})")
            return True
        except Exception as e:
            logger.error(f"Failed to save model: {e}")
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
        df: pd.DataFrame,
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
        texts = pd.Series(df[text_col].fillna("").astype(str).tolist())
        # Force plain numpy array — parquet files load with PyArrow-backed columns
        # which cause "only integer scalar arrays" error in train_test_split
        y_all = np.array(df[label_col].astype(str).fillna("Autre").tolist())
        
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
        else:
            recommended = 0.70
        
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
        }
        
        # Save model card
        self._save_model_card(result, text_col, label_col, len(df), max_features)
        
        return result
    
    def _compute_threshold(self, max_probs, y_true, y_pred) -> float:
        """Compute recommended threshold targeting 85% accuracy on accepted predictions"""
        import numpy as np
        thresholds = np.arange(0.50, 0.96, 0.01)
        best_thresh = 0.70
        best_coverage = 0.0
        
        for t in thresholds:
            accept = max_probs >= t
            if accept.sum() == 0:
                continue
            acc = (y_pred[accept] == y_true[accept]).mean()
            cov = accept.mean()
            
            if acc >= 0.85 and cov > best_coverage:
                best_thresh = t
                best_coverage = cov
        
        return float(best_thresh)
    
    def predict(
        self,
        texts: pd.Series,
        threshold: float = 0.7
    ) -> Tuple:
        """
        Predict labels with confidence scores
        
        Returns: (predictions, confidences, all_probabilities)
        """
        import numpy as np
        if self.model is None or self.vectorizer is None:
            raise RuntimeError("Model not loaded")

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
