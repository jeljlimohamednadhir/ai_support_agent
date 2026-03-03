"""
ML Classification Service
Handles ML model training, prediction, and management
"""
import os
import json
import pickle
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, confusion_matrix, f1_score
    from sklearn.calibration import CalibratedClassifierCV
    from scipy import sparse as sp
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from app.core.logging import get_logger

logger = get_logger(__name__)


class MLClassifier:
    """Wrapper for ML classification model with calibration"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.model_path = self.data_dir / "model_classifier.pkl"
        self.vectorizer_path = self.data_dir / "vectorizer.pkl"
        self.model_card_path = self.data_dir / "model_card.json"
        
        self.model = None
        self.vectorizer = None
        self.model_card = None
        
    def load(self) -> bool:
        """Load model and vectorizer from disk"""
        try:
            if self.model_path.exists() and self.vectorizer_path.exists():
                with open(self.model_path, "rb") as f:
                    self.model = pickle.load(f)
                with open(self.vectorizer_path, "rb") as f:
                    self.vectorizer = pickle.load(f)
                if self.model_card_path.exists():
                    with open(self.model_card_path, "r", encoding="utf-8") as f:
                        self.model_card = json.load(f)
                logger.info("ML model loaded successfully")
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
                pickle.dump(self.vectorizer, f)
            logger.info("ML model saved successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to save model: {e}")
            return False
    
    def _build_vectorizers(self, max_features: int = 5000) -> Dict:
        """Build word + char TF-IDF vectorizers"""
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
    
    def _vectorize_fit(self, vec_dict: Dict, texts: pd.Series):
        """Fit vectorizers and return combined features"""
        Xw = vec_dict["word"].fit_transform(texts)
        Xc = vec_dict["char"].fit_transform(texts)
        X = sp.hstack([Xw, Xc], format="csr")
        return X
    
    def _vectorize_transform(self, vec_dict: Dict, texts: pd.Series):
        """Transform texts using fitted vectorizers"""
        Xw = vec_dict["word"].transform(texts)
        Xc = vec_dict["char"].transform(texts)
        X = sp.hstack([Xw, Xc], format="csr")
        return X
    
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
        if not SKLEARN_AVAILABLE:
            raise RuntimeError("scikit-learn not available")
        
        texts = df[text_col].fillna("").astype(str)
        y_all = df[label_col].astype(str).fillna("Autre").values
        
        # Build vectorizers
        vec_dict = self._build_vectorizers(max_features=max_features)
        X_all = self._vectorize_fit(vec_dict, texts)
        
        # Filter rare classes (< 2 samples)
        y_series = pd.Series(y_all)
        vc_all = y_series.value_counts()
        rare_labels = vc_all[vc_all < 2].index.tolist()
        
        if rare_labels:
            mask_keep = ~y_series.isin(rare_labels)
            X_use = X_all[mask_keep.values]
            y_use = y_series[mask_keep].values
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
            "rare_labels": rare_labels
        }
        
        # Save model card
        self._save_model_card(result, text_col, label_col, len(df), max_features)
        
        return result
    
    def _compute_threshold(self, max_probs: np.ndarray, y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """Compute recommended threshold targeting 85% accuracy on accepted predictions"""
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
    ) -> Tuple[np.ndarray, np.ndarray, Optional[np.ndarray]]:
        """
        Predict labels with confidence scores
        
        Returns: (predictions, confidences, all_probabilities)
        """
        if self.model is None or self.vectorizer is None:
            raise RuntimeError("Model not loaded")
        
        X = self._vectorize_transform(self.vectorizer, texts)
        
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
            "rare_labels": metrics.get("rare_labels", [])
        }
        
        try:
            with open(self.model_card_path, "w", encoding="utf-8") as f:
                json.dump(card, f, ensure_ascii=False, indent=2)
            self.model_card = card
        except Exception as e:
            logger.error(f"Failed to save model card: {e}")
    
    def get_info(self) -> Dict[str, Any]:
        """Get model information"""
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
                    "recommended_threshold": card.get("recommended_threshold", 0.7)
                }
            except:
                pass
        return {"exists": False}
