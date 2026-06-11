"""
classifier_bridge.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Bridge chatbot → ClassificationEngine.

IMPORTANT : ce fichier NE contient plus de logique de décision ML.
Toute la logique est dans ClassificationEngine (classification_engine.py).

Ce bridge fournit uniquement :
  1. format_for_chatbot(text) → markdown prêt pour le chatbot
  2. drift_report(distribution) → rapport PSI markdown
  3. get_status() / is_trained() → délègue à ClassificationEngine

Le chatbot DOIT utiliser classifier_bridge (pas ClassificationEngine directement)
car le bridge gère le formatage et le contexte conversationnel.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ClassifierBridge:
    """
    Interface chatbot → ClassificationEngine.
    Délègue la classification à classification_engine (moteur unique).
    """

    def is_trained(self) -> bool:
        from app.services.classification_engine import classification_engine
        return classification_engine.is_ready()

    def get_status(self) -> Dict[str, Any]:
        from app.services.classification_engine import classification_engine
        return classification_engine.get_status()

    def classify(self, text: str, groq_client=None) -> Optional[Dict[str, Any]]:
        """Classifie via ClassificationEngine et retourne un dict."""
        from app.services.classification_engine import classification_engine
        result = classification_engine.predict(text, groq_client=groq_client)
        if result.classifier_used == "none":
            return None
        return result.to_dict()

    def format_for_chatbot(self, text: str, groq_client=None) -> str:
        """Classifie et retourne le markdown formaté pour le chatbot."""
        from app.services.classification_engine import classification_engine
        result = classification_engine.predict(text, groq_client=groq_client)

        if result.classifier_used == "none":
            status = classification_engine.get_status()
            return (
                "🤖 **Classification ML — Modèle non disponible**\n\n"
                "Aucun modèle entraîné. Pour classifier ce ticket :\n"
                "1. Allez dans **Classification ML**\n"
                "2. Uploadez votre CSV de tickets BRASIL\n"
                "3. Entraînez le modèle\n\n"
                f"_Pipeline actif : `{status.get('active_pipeline', 'none')}`_"
            )

        return result.format_markdown()

    # ──────────────────────────────────────────────────────────────────────
    # Drift detection (PSI) — inchangé
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def compute_psi(
        reference: Dict[str, int],
        current: Dict[str, int],
    ) -> Tuple[float, List[Dict[str, Any]]]:
        import math
        all_labels = set(reference) | set(current)
        n_ref = max(sum(reference.values()), 1)
        n_cur = max(sum(current.values()), 1)
        psi_total = 0.0
        details: List[Dict[str, Any]] = []
        for label in sorted(all_labels):
            p_ref = max(reference.get(label, 0) / n_ref, 1e-4)
            p_cur = max(current.get(label, 0) / n_cur, 1e-4)
            psi_i = (p_cur - p_ref) * math.log(p_cur / p_ref)
            psi_total += psi_i
            if abs(psi_i) > 0.005:
                details.append({
                    "label": label, "ref_pct": round(p_ref * 100, 1),
                    "cur_pct": round(p_cur * 100, 1),
                    "psi": round(psi_i, 4), "drift_flag": psi_i > 0.025,
                })
        details.sort(key=lambda x: abs(x["psi"]), reverse=True)
        return round(psi_total, 4), details

    def drift_report(self, current_distribution: Dict[str, int]) -> str:
        from app.services.classification_engine import classification_engine
        status = classification_engine.get_status()
        ref_dist: Dict[str, int] = {}
        # Essayer de récupérer la distribution de référence depuis le modèle flat
        try:
            from app.services.ml_classifier import MLClassifier
            ml = MLClassifier(data_dir="data")
            info = ml.get_info()
            ref_dist = {k: int(v) for k, v in info.get("label_distribution", {}).items()}
        except Exception:
            pass
        if not ref_dist:
            return "📊 **Drift Detection** — Données de référence manquantes. Entraînez un modèle d'abord."
        psi, details = self.compute_psi(ref_dist, current_distribution)
        if psi < 0.10:
            status_line = f"🟢 **Distribution stable** — PSI = {psi:.3f}"
        elif psi < 0.25:
            status_line = f"🟡 **Dérive modérée** — PSI = {psi:.3f} — Surveillez"
        else:
            status_line = f"🔴 **Dérive significative** — PSI = {psi:.3f} — Réentraînement recommandé"
        lines = ["📊 **Rapport Drift ML (PSI)**\n", status_line, "",
                 "| Catégorie | Entraînement | Actuel | PSI | Alerte |",
                 "|---|---|---|---|---|"]
        for d in details[:10]:
            flag = "⚠️" if d["drift_flag"] else ""
            lines.append(f"| `{d['label']}` | {d['ref_pct']}% | {d['cur_pct']}% | {d['psi']:.4f} | {flag} |")
        if psi > 0.25:
            lines.append("\n> 🔴 **Action :** Réentraînez via Classification ML → Entraîner.")
        return "\n".join(lines)


# Singleton
classifier_bridge = ClassifierBridge()


from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Confidence tier labels
# ─────────────────────────────────────────────────────────────────────────────

_TIER_LABEL: Dict[str, str] = {
    "HIGH":   "🟢 Élevée",
    "MEDIUM": "🟡 Moyenne",
    "LOW":    "🔴 Faible",
}

_TIER_EMOJI: Dict[str, str] = {
    "HIGH":   "✅",
    "MEDIUM": "⚠️",
    "LOW":    "🔴",
}


# ─────────────────────────────────────────────────────────────────────────────
# ClassifierBridge
# ─────────────────────────────────────────────────────────────────────────────

class ClassifierBridge:
    """
    Interface unifiée chatbot → ML classifiers.

    Usage:
        result = classifier_bridge.classify("DSLAM OP49MAB11 bloqué erreur 1300")
        text   = classifier_bridge.format_for_chatbot("DSLAM OP49MAB11 bloqué")
    """

    def __init__(self) -> None:
        self._hclassifier = None   # HierarchicalClassifier (lazy)
        self._ml_classifier = None  # MLClassifier flat (lazy, fallback)

    # ──────────────────────────────────────────────────────────────────────
    # Lazy loaders
    # ──────────────────────────────────────────────────────────────────────

    def _get_hierarchical(self):
        """Lazy-load HierarchicalClassifier singleton."""
        if self._hclassifier is None:
            try:
                from app.services.hierarchical_classifier import HierarchicalClassifier
                h = HierarchicalClassifier(data_dir="data")
                h.load()
                self._hclassifier = h
                logger.info("[ClassifierBridge] HierarchicalClassifier chargé (trained=%s)", h.is_trained)
            except Exception as e:
                logger.warning("[ClassifierBridge] HierarchicalClassifier non disponible: %s", e)
        return self._hclassifier

    def _get_flat(self):
        """Lazy-load MLClassifier (flat, fallback) singleton."""
        if self._ml_classifier is None:
            try:
                from app.services.ml_classifier import MLClassifier
                m = MLClassifier(data_dir="data")
                m.load()
                self._ml_classifier = m
                logger.info("[ClassifierBridge] MLClassifier (flat) chargé (model=%s)", m.model is not None)
            except Exception as e:
                logger.warning("[ClassifierBridge] MLClassifier non disponible: %s", e)
        return self._ml_classifier

    # ──────────────────────────────────────────────────────────────────────
    # Status
    # ──────────────────────────────────────────────────────────────────────

    def is_trained(self) -> bool:
        """Return True if at least one classifier is ready."""
        h = self._get_hierarchical()
        if h and h.is_trained:
            return True
        m = self._get_flat()
        return m is not None and m.model is not None

    def get_status(self) -> Dict[str, Any]:
        """Return a status dict for diagnostics / dashboard."""
        h = self._get_hierarchical()
        m = self._get_flat()
        h_info = h.get_info() if h else {"exists": False}
        m_info = m.get_info() if m else {"exists": False}
        return {
            "hierarchical": {
                "available": bool(h and h.is_trained),
                "trained_at": h_info.get("trained_at"),
                "n_samples": h_info.get("n_samples"),
                "l1_categories": list(h_info.get("l1_distribution", {}).keys()) if h_info.get("l1_distribution") else [],
            },
            "flat": {
                "available": bool(m and m.model is not None),
                "trained_at": m_info.get("trained_at"),
                "n_samples": m_info.get("n_samples"),
                "macro_f1": m_info.get("macro_f1"),
                "classes": m_info.get("classes", []),
            },
            "active_model": "hierarchical" if (h and h.is_trained) else ("flat" if (m and m.model) else "none"),
        }

    # ──────────────────────────────────────────────────────────────────────
    # Classification
    # ──────────────────────────────────────────────────────────────────────

    def classify(self, text: str, groq_client=None) -> Optional[Dict[str, Any]]:
        """
        Classify a text using the best available model.

        Priority:
          1. HierarchicalClassifier (L1 KNN + L2 LR + Groq fallback)
          2. MLClassifier flat (TF-IDF + MiniLM hybrid)

        Returns:
          Dict with keys: level_1, level_2, level_1_confidence, level_2_confidence,
          confidence_tier, needs_review, nearest_neighbors, classifier_used
          OR None if no model is trained.
        """
        # ── Hierarchical (preferred) ────────────────────────────────────
        h = self._get_hierarchical()
        if h and h.is_trained:
            try:
                result = h.predict_single(text, groq_client=groq_client)
                result["classifier_used"] = "hierarchical"
                return result
            except Exception as e:
                logger.warning("[ClassifierBridge] Hierarchical predict failed: %s", e)

        # ── Flat fallback ────────────────────────────────────────────────
        m = self._get_flat()
        if m and m.model is not None:
            try:
                import pandas as pd
                preds, confs, _ = m.predict(pd.Series([text]))
                conf = float(confs[0])
                tier = "HIGH" if conf >= 0.75 else "MEDIUM" if conf >= 0.50 else "LOW"
                return {
                    "level_1":            str(preds[0]),
                    "level_2":            "N/A",
                    "level_1_confidence": conf,
                    "level_2_confidence": 0.0,
                    "confidence_tier":    tier,
                    "needs_review":       conf < 0.75,
                    "nearest_neighbors":  [],
                    "llm_used":           False,
                    "llm_rationale":      None,
                    "classifier_used":    "flat",
                }
            except Exception as e:
                logger.warning("[ClassifierBridge] Flat predict failed: %s", e)

        return None

    # ──────────────────────────────────────────────────────────────────────
    # Chatbot formatting
    # ──────────────────────────────────────────────────────────────────────

    def format_for_chatbot(self, text: str, groq_client=None) -> str:
        """
        Classify text and return a formatted markdown response ready
        to be returned by the chatbot.
        """
        result = self.classify(text, groq_client=groq_client)

        if result is None:
            status = self.get_status()
            return (
                "🤖 **Classification ML — Modèle non disponible**\n\n"
                "Aucun modèle entraîné. Pour classifier ce ticket :\n"
                "1. Allez dans le module **Classification ML**\n"
                "2. Uploadez votre CSV de tickets BRASIL\n"
                "3. Entraînez le modèle (mode **Hiérarchique L1/L2** recommandé)\n\n"
                f"_Modèle actif : `{status['active_model']}`_"
            )

        l1          = result.get("level_1", "N/A")
        l2          = result.get("level_2", "N/A")
        l1_conf     = result.get("level_1_confidence", 0.0)
        l2_conf     = result.get("level_2_confidence", 0.0)
        tier        = result.get("confidence_tier", "LOW")
        needs_review = result.get("needs_review", True)
        classifier  = result.get("classifier_used", "?")
        nn          = result.get("nearest_neighbors", [])
        rationale   = result.get("llm_rationale")
        llm_used    = result.get("llm_used", False)

        tier_label  = _TIER_LABEL.get(tier, tier)
        tier_emoji  = _TIER_EMOJI.get(tier, "")
        review_flag = "⚠️ Revue recommandée" if needs_review else "✅ Auto-accepté"
        model_label = {"hierarchical": "Hiérarchique (L1/L2)", "flat": "Plat (TF-IDF+MiniLM)"}.get(classifier, classifier)

        lines = [
            "🤖 **Classification ML — Résultat**\n",
            "| Champ | Valeur |",
            "|---|---|",
            f"| **Domaine (L1)** | `{l1}` — {l1_conf:.0%} |",
        ]

        if l2 and l2 not in ("N/A", "UNDETERMINED", "INCOMPLETE_DESCRIPTION"):
            lines.append(f"| **Cause (L2)** | `{l2}` — {l2_conf:.0%} |")

        lines += [
            f"| **Confiance** | {tier_emoji} {tier_label} |",
            f"| **Statut** | {review_flag} |",
            f"| **Modèle** | {model_label} |",
        ]

        if llm_used:
            lines.append(f"| **LLM** | ✅ Groq utilisé (confiance faible) |")

        # ── Nearest neighbors ────────────────────────────────────────────
        if nn:
            lines.append("\n**📎 Tickets proches dans la base d'entraînement :**")
            for n in nn[:3]:
                sim   = n.get("similarity", 0.0)
                l1n   = n.get("l1", "?")
                l2n   = n.get("l2", "?")
                excerpt = (n.get("text") or "")[:100].strip()
                if excerpt:
                    lines.append(f"  - `{l1n}/{l2n}` ({sim:.0%}) — *{excerpt}…*")
                else:
                    lines.append(f"  - `{l1n}/{l2n}` ({sim:.0%})")

        # ── LLM rationale ────────────────────────────────────────────────
        if rationale:
            lines.append(f"\n💡 **Justification Groq :** {rationale}")

        # ── Action tip ───────────────────────────────────────────────────
        if needs_review:
            lines.append(
                "\n> ⚠️ Confiance insuffisante — vérifiez la classification dans le module ML "
                "et corrigez si nécessaire. Chaque correction améliore le modèle."
            )

        return "\n".join(lines)

    # ──────────────────────────────────────────────────────────────────────
    # Drift detection (Population Stability Index — PSI)
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def compute_psi(
        reference: Dict[str, int],
        current: Dict[str, int],
    ) -> Tuple[float, List[Dict[str, Any]]]:
        """
        Compute Population Stability Index between two label distributions.

        PSI < 0.10 → stable
        PSI 0.10–0.25 → moderate drift (monitor)
        PSI > 0.25 → significant drift (retrain recommended)

        Args:
            reference: {label: count} — baseline distribution (training set)
            current:   {label: count} — current distribution (recent tickets)

        Returns:
            (psi_total, per_label_details)
        """
        import math

        all_labels = set(reference) | set(current)
        n_ref = max(sum(reference.values()), 1)
        n_cur = max(sum(current.values()), 1)

        psi_total = 0.0
        details: List[Dict[str, Any]] = []

        for label in sorted(all_labels):
            p_ref = max(reference.get(label, 0) / n_ref, 1e-4)  # avoid log(0)
            p_cur = max(current.get(label, 0) / n_cur, 1e-4)
            psi_i = (p_cur - p_ref) * math.log(p_cur / p_ref)
            psi_total += psi_i

            if abs(psi_i) > 0.005:  # only report meaningful contributions
                details.append({
                    "label":       label,
                    "ref_pct":     round(p_ref * 100, 1),
                    "cur_pct":     round(p_cur * 100, 1),
                    "psi":         round(psi_i, 4),
                    "drift_flag":  psi_i > 0.025,
                })

        details.sort(key=lambda x: abs(x["psi"]), reverse=True)
        return round(psi_total, 4), details

    def drift_report(
        self,
        current_distribution: Dict[str, int],
    ) -> str:
        """
        Compare current_distribution to the training distribution stored in the model card.
        Returns a formatted markdown drift report.

        Args:
            current_distribution: {label: count} — distribution of recent tickets
        """
        h = self._get_hierarchical()
        info = h.get_info() if h else {}
        ref_dist: Dict[str, int] = info.get("l1_distribution", {})

        if not ref_dist:
            m = self._get_flat()
            m_info = m.get_info() if m else {}
            ref_dist = m_info.get("label_distribution", {})

        if not ref_dist:
            return (
                "📊 **Drift Detection — Données de référence manquantes**\n\n"
                "Entraînez d'abord un modèle pour établir la distribution de référence."
            )

        psi, details = self.compute_psi(ref_dist, current_distribution)

        if psi < 0.10:
            status_line = f"🟢 **Distribution stable** — PSI = {psi:.3f} (< 0.10)"
        elif psi < 0.25:
            status_line = f"🟡 **Dérive modérée** — PSI = {psi:.3f} (0.10–0.25) — Surveillez"
        else:
            status_line = f"🔴 **Dérive significative** — PSI = {psi:.3f} (> 0.25) — Réentraînement recommandé"

        lines = [
            "📊 **Rapport de Drift ML (PSI)**\n",
            status_line,
            "",
            "| Catégorie | Entraînement | Actuel | PSI | Alerte |",
            "|---|---|---|---|---|",
        ]

        for d in details[:10]:
            flag = "⚠️" if d["drift_flag"] else ""
            lines.append(
                f"| `{d['label']}` | {d['ref_pct']}% | {d['cur_pct']}% | {d['psi']:.4f} | {flag} |"
            )

        if psi > 0.25:
            lines.append(
                "\n> 🔴 **Action recommandée :** Réentraînez le modèle avec les tickets récents "
                "via le module Classification ML → Entraîner."
            )

        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Singleton
# ─────────────────────────────────────────────────────────────────────────────

classifier_bridge = ClassifierBridge()
