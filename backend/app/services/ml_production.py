"""
ml_production.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Services MLOps production pour le module Classification ML :

  1. ActiveLearningQueue  — file review intelligente
  2. StagingRetrainer     — réentraînement sécurisé avec validation gate
  3. ErrorAnalyzer        — analyse FP/FN, confusion hotspots
  4. PredictionDriftMonitor — surveillance distribution prédictions
"""
from __future__ import annotations

import json
import logging
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

DATA_DIR  = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# 1. ACTIVE LEARNING QUEUE
# ─────────────────────────────────────────────────────────────────────────────

_ACTIVE_LEARNING_FILE = DATA_DIR / "active_learning_queue.jsonl"

# Priorité : LOW = doit être reviewé en premier
PRIORITY_SCORES = {
    "LOW_CONFIDENCE":      1,   # confiance < 0.40
    "MEDIUM_CONFIDENCE":   2,   # confiance 0.40-0.60
    "UNKNOWN":             1,   # UNKNOWN retourné
    "RARE_CLASS":          2,   # classe rare (< 15 samples dans train)
    "DRIFTED":             1,   # échantillon proche d'un centroid de drift
    "NEW_PATTERN":         1,   # termes non vus à l'entraînement
}


class ActiveLearningQueue:
    """
    File review intelligente pour active learning.

    Un ticket est envoyé en review quand :
      - confiance < seuil (LOW / UNKNOWN)
      - classe rare détectée
      - nouveau pattern vocabulaire
      - drift détecté

    La file est persistée dans active_learning_queue.jsonl.
    Elle est consommée par les opérateurs N3 dans le dashboard Monitoring.
    """

    def __init__(self, queue_file: Path = _ACTIVE_LEARNING_FILE):
        self.queue_file = queue_file

    def add_item(
        self,
        text: str,
        predicted_label: str,
        confidence: float,
        confidence_tier: str,
        ticket_id: Optional[str] = None,
        reason: str = "LOW_CONFIDENCE",
        top_k: Optional[List[Dict]] = None,
        unknown_reason: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Ajoute un ticket à la file review."""
        item = {
            "id":              ticket_id or f"al_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            "text":            text[:500],
            "predicted_label": predicted_label,
            "confidence":      round(confidence, 3),
            "confidence_tier": confidence_tier,
            "reason":          reason,
            "priority":        PRIORITY_SCORES.get(reason, 3),
            "top_k":           top_k or [],
            "unknown_reason":  unknown_reason,
            "session_id":      session_id,
            "status":          "pending",    # pending / reviewed / corrected / dismissed
            "corrected_label": None,
            "added_at":        datetime.now().isoformat(),
            "reviewed_at":     None,
            "reviewer":        None,
        }
        try:
            with open(self.queue_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error("[ActiveLearning] Failed to write queue item: %s", e)
        return item

    def get_queue(
        self,
        status: str = "pending",
        max_items: int = 50,
        sort_by_priority: bool = True,
    ) -> List[Dict[str, Any]]:
        """Retourne la file (ou un sous-ensemble filtré)."""
        items = self._read_all()
        if status != "all":
            items = [i for i in items if i.get("status") == status]
        if sort_by_priority:
            items.sort(key=lambda x: (x.get("priority", 9), x.get("confidence", 1.0)))
        return items[:max_items]

    def update_item(
        self,
        item_id: str,
        status: str,
        corrected_label: Optional[str] = None,
        reviewer: Optional[str] = None,
    ) -> bool:
        """Met à jour le statut d'un item (reviewed / corrected / dismissed)."""
        items = self._read_all()
        updated = False
        for item in items:
            if item.get("id") == item_id:
                item["status"] = status
                item["reviewed_at"] = datetime.now().isoformat()
                if corrected_label:
                    item["corrected_label"] = corrected_label
                if reviewer:
                    item["reviewer"] = reviewer
                updated = True
                break
        if updated:
            self._write_all(items)
        return updated

    def get_stats(self) -> Dict[str, Any]:
        items = self._read_all()
        total = len(items)
        pending = sum(1 for i in items if i.get("status") == "pending")
        reviewed = sum(1 for i in items if i.get("status") in ("reviewed", "corrected"))
        corrected = sum(1 for i in items if i.get("status") == "corrected")
        by_reason = {}
        for i in items:
            r = i.get("reason", "?")
            by_reason[r] = by_reason.get(r, 0) + 1
        return {
            "total": total, "pending": pending,
            "reviewed": reviewed, "corrected": corrected,
            "by_reason": by_reason,
            "review_rate": round(reviewed / max(total, 1) * 100, 1),
        }

    def _read_all(self) -> List[Dict]:
        if not self.queue_file.exists():
            return []
        items = []
        try:
            with open(self.queue_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        items.append(json.loads(line))
                    except Exception:
                        pass
        except Exception as e:
            logger.error("[ActiveLearning] Read failed: %s", e)
        return items

    def _write_all(self, items: List[Dict]):
        try:
            with open(self.queue_file, "w", encoding="utf-8") as f:
                for item in items:
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error("[ActiveLearning] Write failed: %s", e)


active_learning_queue = ActiveLearningQueue()


# ─────────────────────────────────────────────────────────────────────────────
# 2. STAGING RETRAINER
# ─────────────────────────────────────────────────────────────────────────────

_STAGING_DIR  = DATA_DIR / "staging_models"
_STAGING_DIR.mkdir(exist_ok=True)
_STAGING_LOG  = DATA_DIR / "staging_history.jsonl"

# Seuils pour la promotion automatique
PROMOTION_THRESHOLDS = {
    "macro_f1_min_delta": -0.02,    # tolérance de dégradation F1 (-2%)
    "coverage_min_delta": -0.05,    # tolérance de dégradation coverage (-5%)
    "ece_max_delta":       0.05,    # tolérance de dégradation ECE (+5%)
}


class StagingRetrainer:
    """
    Réentraînement sécurisé avec gate de validation.

    Workflow :
      1. train_candidate()  → entraîne un modèle candidat dans staging/
      2. compare()          → compare candidat vs production sur métriques
      3. promote()          → remplace production SI metrics_ok
      4. rollback_staging() → annule la promotion

    Anti-poisoning :
      - Valide les corrections avant fusion (seuil divergence)
      - Détecte les corrections contradictoires entre opérateurs
    """

    def __init__(self, staging_dir: Path = _STAGING_DIR):
        self.staging_dir = staging_dir
        self.staging_dir.mkdir(exist_ok=True)
        self._candidate_metrics: Optional[Dict] = None
        self._production_metrics: Optional[Dict] = None

    def train_candidate(
        self,
        df,
        text_col: str,
        label_col: str,
        corrections_log: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Entraîne un modèle candidat dans staging (ne touche pas la production).
        Fusionne les corrections validées si fourni.
        """
        import pandas as pd
        import pickle

        from app.services.ml_classifier import MLClassifier

        # ── Validation anti-poisoning des corrections ──────────────────
        if corrections_log and corrections_log.exists():
            df = self._merge_validated_corrections(df, text_col, label_col, corrections_log)

        # Entraîner dans staging
        candidate = MLClassifier(data_dir=str(self.staging_dir))
        result = candidate.train(df=df, text_col=text_col, label_col=label_col)
        self._candidate_metrics = {
            "macro_f1": result.get("macro_f1"),
            "ece":      result.get("ece"),
            "coverage": self._estimate_coverage(result),
            "trained_at": datetime.now().isoformat(),
            "n_samples": len(df),
            "classes_count": len(result.get("classes", [])),
        }

        # Log
        self._log_staging_event("CANDIDATE_TRAINED", self._candidate_metrics)
        logger.info("[StagingRetrainer] Candidat entraîné — F1=%.3f, ECE=%s",
                    result.get("macro_f1", 0), result.get("ece"))
        return {"status": "candidate_ready", "metrics": self._candidate_metrics}

    def compare(self) -> Dict[str, Any]:
        """
        Compare le modèle candidat vs production.
        Retourne une décision : PROMOTE / REJECT + raisons.
        """
        if self._candidate_metrics is None:
            return {"decision": "NO_CANDIDATE", "reason": "Entraîner un candidat d'abord"}

        # Récupérer métriques production
        from app.services.ml_classifier import MLClassifier
        prod = MLClassifier(data_dir="data")
        prod_info = prod.get_info()
        self._production_metrics = {
            "macro_f1": prod_info.get("macro_f1"),
            "ece":      prod_info.get("ece") if prod_info.get("exists") else None,
            "coverage": None,  # pas de coverage dans model_card
        }

        cand  = self._candidate_metrics
        prod_ = self._production_metrics

        # Décision
        reasons = []
        promote = True

        # F1
        if prod_["macro_f1"] is not None and cand["macro_f1"] is not None:
            delta_f1 = cand["macro_f1"] - prod_["macro_f1"]
            if delta_f1 < PROMOTION_THRESHOLDS["macro_f1_min_delta"]:
                promote = False
                reasons.append(f"F1 dégradé : {prod_['macro_f1']:.3f} → {cand['macro_f1']:.3f} (Δ{delta_f1:+.3f})")
            else:
                reasons.append(f"F1 OK : {prod_['macro_f1']:.3f} → {cand['macro_f1']:.3f} (Δ{delta_f1:+.3f})")

        # ECE
        if prod_["ece"] is not None and cand["ece"] is not None:
            delta_ece = cand["ece"] - prod_["ece"]
            if delta_ece > PROMOTION_THRESHOLDS["ece_max_delta"]:
                promote = False
                reasons.append(f"ECE dégradée : {prod_['ece']:.4f} → {cand['ece']:.4f} (Δ{delta_ece:+.4f})")
            else:
                reasons.append(f"ECE OK : {prod_['ece']:.4f} → {cand['ece']:.4f}")

        decision = "PROMOTE" if promote else "REJECT"
        comparison = {
            "decision": decision,
            "promote": promote,
            "reasons": reasons,
            "candidate": cand,
            "production": prod_,
        }
        self._log_staging_event(f"COMPARISON_{decision}", comparison)
        return comparison

    def promote(self) -> Dict[str, Any]:
        """
        Promeut le candidat en production si la comparaison est favorable.
        UNSAFE : appeler compare() d'abord.
        """
        comparison = self.compare()
        if not comparison.get("promote"):
            return {"status": "REJECTED", "reasons": comparison.get("reasons", [])}

        import shutil
        # Copier les fichiers staging → production
        production_dir = Path("data")
        for fname in ["model_classifier.pkl", "vectorizer.pkl", "model_card.json"]:
            src = self.staging_dir / fname
            if src.exists():
                shutil.copy2(src, production_dir / fname)

        # Recharger le moteur
        try:
            from app.services.classification_engine import classification_engine
            classification_engine.reload()
        except Exception:
            pass

        self._log_staging_event("PROMOTED", self._candidate_metrics)
        logger.info("[StagingRetrainer] Candidat promu en production")
        return {"status": "PROMOTED", "metrics": self._candidate_metrics}

    def _merge_validated_corrections(self, df, text_col, label_col, corrections_log: Path):
        """Fusionne les corrections en filtrant les anomalies (anti-poisoning)."""
        import pandas as pd

        corrections = []
        with open(corrections_log, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    corrections.append(json.loads(line))
                except Exception:
                    pass

        if not corrections:
            return df

        corr_df = pd.DataFrame(corrections)
        corr_df = corr_df[corr_df["corrected_label"].notna() & (corr_df["corrected_label"] != "")]

        # Anti-poisoning : détecter corrections contradictoires sur même texte
        if "text" in corr_df.columns:
            dup_texts = corr_df.groupby("text")["corrected_label"].nunique()
            contradictory = dup_texts[dup_texts > 1].index.tolist()
            if contradictory:
                logger.warning("[StagingRetrainer] Anti-poisoning: %d textes avec labels contradictoires — ignorés",
                               len(contradictory))
                corr_df = corr_df[~corr_df["text"].isin(contradictory)]

        # Fusionner
        if "text" in corr_df.columns and "corrected_label" in corr_df.columns:
            corr_subset = corr_df[["text", "corrected_label"]].rename(
                columns={"text": text_col, "corrected_label": label_col}
            ).dropna()
            df = pd.concat([df, corr_subset], ignore_index=True)
            logger.info("[StagingRetrainer] %d corrections fusionnées après validation", len(corr_subset))

        return df

    @staticmethod
    def _estimate_coverage(result: Dict) -> Optional[float]:
        """Estime la coverage depuis le threshold recommandé (approximatif)."""
        # Sans données de validation dans result, on ne peut pas calculer exactement
        # On utilise le threshold comme proxy inverse
        t = result.get("recommended_threshold", 0.5)
        # Coverage estimée : plus le seuil est bas, plus la coverage est haute
        return round(max(0.0, min(1.0, 1.0 - t + 0.3)), 2)

    def _log_staging_event(self, event_type: str, data: Dict):
        try:
            record = {"event": event_type, "at": datetime.now().isoformat(), **data}
            with open(_STAGING_LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def get_history(self, max_events: int = 20) -> List[Dict]:
        if not _STAGING_LOG.exists():
            return []
        events = []
        with open(_STAGING_LOG, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    events.append(json.loads(line))
                except Exception:
                    pass
        return events[-max_events:]


staging_retrainer = StagingRetrainer()


# ─────────────────────────────────────────────────────────────────────────────
# 3. ERROR ANALYZER
# ─────────────────────────────────────────────────────────────────────────────

class ErrorAnalyzer:
    """
    Analyse les erreurs de classification :
      - Top faux positifs (FP) par classe
      - Top faux négatifs (FN) par classe
      - Confusion hotspots (paires de classes les plus confondues)
      - Classes les plus dégradées depuis le dernier entraînement
    """

    def analyze(
        self,
        y_true: List[str],
        y_pred: List[str],
        texts: Optional[List[str]] = None,
        confidences: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """
        Analyse complète des erreurs.

        Args:
            y_true:      Labels réels
            y_pred:      Labels prédits
            texts:       Textes correspondants (optionnel, pour exemples)
            confidences: Confidences associées (optionnel)

        Returns: dict avec fp, fn, confusion_hotspots, per_class_metrics
        """
        classes = sorted(set(y_true) | set(y_pred))

        fp_by_class: Dict[str, List[Dict]] = {c: [] for c in classes}
        fn_by_class: Dict[str, List[Dict]] = {c: [] for c in classes}
        confusion_pairs: Dict[str, int] = {}
        per_class: Dict[str, Dict] = {c: {"tp": 0, "fp": 0, "fn": 0} for c in classes}

        for i, (true, pred) in enumerate(zip(y_true, y_pred)):
            text_excerpt = (texts[i][:100] if texts else "")
            conf = confidences[i] if confidences else None

            if true == pred:
                per_class[true]["tp"] += 1
            else:
                # FP : pred a dit C mais c'était D
                per_class[pred]["fp"] += 1
                fp_by_class[pred].append({"true": true, "pred": pred, "text": text_excerpt, "conf": conf})
                # FN : true était C mais pred a dit D
                per_class[true]["fn"] += 1
                fn_by_class[true].append({"true": true, "pred": pred, "text": text_excerpt, "conf": conf})
                # Confusion pair
                pair = f"{true} → {pred}"
                confusion_pairs[pair] = confusion_pairs.get(pair, 0) + 1

        # Métriques par classe
        per_class_metrics = []
        for cls in classes:
            tp = per_class[cls]["tp"]
            fp = per_class[cls]["fp"]
            fn = per_class[cls]["fn"]
            precision = tp / max(tp + fp, 1)
            recall    = tp / max(tp + fn, 1)
            f1        = 2 * precision * recall / max(precision + recall, 1e-9)
            per_class_metrics.append({
                "class": cls, "tp": tp, "fp": fp, "fn": fn,
                "precision": round(precision, 3), "recall": round(recall, 3),
                "f1": round(f1, 3), "support": tp + fn,
            })
        per_class_metrics.sort(key=lambda x: x["f1"])  # worst first

        # Confusion hotspots (top 10 paires)
        hotspots = sorted(confusion_pairs.items(), key=lambda x: -x[1])[:10]

        # Top FP/FN par classe (max 5 exemples)
        top_fp = {c: sorted(v, key=lambda x: x.get("conf") or 0, reverse=True)[:5]
                  for c, v in fp_by_class.items() if v}
        top_fn = {c: sorted(v, key=lambda x: x.get("conf") or 0, reverse=True)[:5]
                  for c, v in fn_by_class.items() if v}

        # Classes critiques (recall < 0.5 avec support ≥ 5)
        critical_classes = [
            m for m in per_class_metrics
            if m["recall"] < 0.5 and m["support"] >= 5
        ]

        total = len(y_true)
        correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
        accuracy = correct / max(total, 1)

        return {
            "accuracy": round(accuracy, 3),
            "total_samples": total,
            "error_count": total - correct,
            "error_rate": round(1 - accuracy, 3),
            "per_class_metrics": per_class_metrics,
            "confusion_hotspots": [{"pair": p, "count": c} for p, c in hotspots],
            "critical_classes": critical_classes,
            "top_fp_examples": top_fp,
            "top_fn_examples": top_fn,
        }

    def analyze_from_session(
        self,
        df,
        true_col: str,
        pred_col: str,
        text_col: Optional[str] = None,
        conf_col: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Helper : analyse depuis un DataFrame avec colonnes nommées."""
        try:
            valid = df.dropna(subset=[true_col, pred_col])
            if len(valid) < 5:
                return None
            y_true = valid[true_col].astype(str).tolist()
            y_pred = valid[pred_col].astype(str).tolist()
            texts  = valid[text_col].fillna("").astype(str).tolist() if text_col and text_col in valid.columns else None
            confs  = valid[conf_col].tolist() if conf_col and conf_col in valid.columns else None
            return self.analyze(y_true, y_pred, texts, confs)
        except Exception as e:
            logger.error("[ErrorAnalyzer] analyze_from_session failed: %s", e)
            return None


error_analyzer = ErrorAnalyzer()


# ─────────────────────────────────────────────────────────────────────────────
# 4. PREDICTION DRIFT MONITOR
# ─────────────────────────────────────────────────────────────────────────────

class PredictionDriftMonitor:
    """
    Surveille la dérive des prédictions en production :
      - Explosion UNKNOWN rate
      - Chute recall estimée
      - Classes soudainement dominantes
      - Nouveaux termes/équipements non vus à l'entraînement
    """

    def analyze(
        self,
        predictions: List[str],
        confidences: List[float],
        training_distribution: Optional[Dict[str, int]] = None,
        training_vocab: Optional[set] = None,
        texts: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Analyse les prédictions récentes pour détecter des dérives.

        Returns: dict avec alertes et métriques
        """
        total = max(len(predictions), 1)
        unknown_count = sum(1 for p in predictions if p == "UNKNOWN")
        unknown_rate  = unknown_count / total

        low_conf_count = sum(1 for c in confidences if c < 0.40)
        low_conf_rate  = low_conf_count / total
        avg_confidence = sum(confidences) / total if confidences else 0.0

        # Distribution actuelle
        current_dist: Dict[str, int] = {}
        for p in predictions:
            current_dist[p] = current_dist.get(p, 0) + 1

        # KL divergence si référence dispo
        kl_score = None
        if training_distribution:
            kl_score = self._kl_divergence(training_distribution, current_dist)

        # Nouveaux tokens si vocab dispo
        new_terms: List[str] = []
        if training_vocab and texts:
            import re
            for text in texts[:100]:  # limiter pour perf
                tokens = re.findall(r'\b[A-Z]{2,4}\d{2}[A-Z]{2,5}\d+\b', text)  # equipment IDs
                tokens += re.findall(r'\bERROR_CODE_\w+\b', text)
                for t in tokens:
                    if t not in training_vocab:
                        new_terms.append(t)
            new_terms = list(set(new_terms))[:20]

        # Alertes
        alerts: List[Dict[str, str]] = []
        if unknown_rate > 0.30:
            alerts.append({"level": "CRITICAL", "type": "UNKNOWN_EXPLOSION",
                           "message": f"Taux UNKNOWN critique : {unknown_rate:.0%} (seuil > 30%)"})
        elif unknown_rate > 0.15:
            alerts.append({"level": "WARNING", "type": "UNKNOWN_HIGH",
                           "message": f"Taux UNKNOWN élevé : {unknown_rate:.0%} (seuil > 15%)"})

        if low_conf_rate > 0.40:
            alerts.append({"level": "WARNING", "type": "LOW_CONFIDENCE_HIGH",
                           "message": f"Confiance faible sur {low_conf_rate:.0%} des prédictions"})

        if kl_score is not None and kl_score > 0.40:
            alerts.append({"level": "CRITICAL", "type": "DISTRIBUTION_DRIFT",
                           "message": f"Dérive distribution critique (KL={kl_score:.3f})"})
        elif kl_score is not None and kl_score > 0.15:
            alerts.append({"level": "WARNING", "type": "DISTRIBUTION_DRIFT",
                           "message": f"Dérive distribution modérée (KL={kl_score:.3f})"})

        if new_terms:
            alerts.append({"level": "INFO", "type": "NEW_PATTERNS",
                           "message": f"{len(new_terms)} nouveaux patterns détectés : {', '.join(new_terms[:5])}"})

        return {
            "total_predictions": total,
            "unknown_rate":      round(unknown_rate, 3),
            "low_confidence_rate": round(low_conf_rate, 3),
            "avg_confidence":    round(avg_confidence, 3),
            "kl_divergence":     round(kl_score, 4) if kl_score is not None else None,
            "current_distribution": {k: v for k, v in sorted(current_dist.items(), key=lambda x: -x[1])[:15]},
            "new_terms_detected": new_terms,
            "alerts": alerts,
            "health": "CRITICAL" if any(a["level"] == "CRITICAL" for a in alerts)
                      else "WARNING" if any(a["level"] == "WARNING" for a in alerts)
                      else "OK",
        }

    @staticmethod
    def _kl_divergence(ref: Dict[str, int], current: Dict[str, int]) -> float:
        all_labels = set(ref) | set(current)
        n_ref = max(sum(ref.values()), 1)
        n_cur = max(sum(current.values()), 1)
        kl = 0.0
        for label in all_labels:
            p = max(ref.get(label, 0) / n_ref, 1e-10)
            q = max(current.get(label, 0) / n_cur, 1e-10)
            if p > 0:
                kl += p * math.log(p / q)
        return float(kl)


prediction_drift_monitor = PredictionDriftMonitor()
