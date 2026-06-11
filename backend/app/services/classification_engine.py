"""
classification_engine.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MOTEUR DE CLASSIFICATION UNIQUE — remplace la logique multi-pipeline
de classifier_bridge.py et toute logique "try A else try B".

Architecture décisionnelle UNIQUE :

  TEXT
    → TelecomPreprocessor (normalisation métier)
    → MLClassifier (TF-IDF + MiniLM, CalibratedClassifierCV, class_weight)
        → predict_adaptive() → seuils par classe → confidence tier
        → si LOW/UNKNOWN + HierarchicalClassifier dispo → fusion probabiliste
    → ClassificationResult normalisé

Principe :
  - UNE seule entrée   : ClassificationEngine.predict(text)
  - UNE seule logique  : flat ML premier, hiérarchique comme enrichissement L2
  - UNE seule sortie   : ClassificationResult dataclass
  - Pas de fallback silencieux
  - Scores calibrés (isotonic regression en train)
  - UNKNOWN intelligent avec raison

Le HierarchicalClassifier n'est PAS un pipeline concurrent.
Il fournit uniquement :
  - enrichissement L2 quand le modèle flat a classifié L1
  - rationale LLM quand confiance faible

Le chatbot DOIT utiliser ClassificationEngine, pas classifier_bridge.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Output normalisé — UNE SEULE structure possible
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ClassificationResult:
    """
    Résultat unifié de ClassificationEngine.predict().
    Tous les champs sont toujours présents (jamais None sauf cas explicites).
    """
    # Prédiction principale
    label:            str             # label prédit (ou "UNKNOWN")
    raw_label:        str             # label avant seuil (même si UNKNOWN retourné)
    confidence:       float           # confiance calibrée [0, 1]
    confidence_tier:  str             # HIGH / MEDIUM / LOW
    accepted:         bool            # confidence >= seuil adaptatif

    # Enrichissement L2 (si HierarchicalClassifier disponible)
    level_2:          Optional[str]   = None
    level_2_confidence: float         = 0.0

    # Diagnostic UNKNOWN
    unknown_reason:   Optional[str]   = None
    threshold_applied: float          = 0.50

    # Top alternatives (top-3 labels avec probabilités)
    top_k:            List[Dict]      = field(default_factory=list)

    # Traçabilité
    classifier_used:  str             = "flat"   # "flat" | "hierarchical_l2" | "llm_fallback"
    llm_used:         bool            = False
    llm_rationale:    Optional[str]   = None
    nearest_neighbors: List[Dict]     = field(default_factory=list)

    # Calibration
    ece_at_training:  Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label":             self.label,
            "raw_label":         self.raw_label,
            "confidence":        self.confidence,
            "confidence_tier":   self.confidence_tier,
            "accepted":          self.accepted,
            "level_2":           self.level_2,
            "level_2_confidence": self.level_2_confidence,
            "unknown_reason":    self.unknown_reason,
            "threshold_applied": self.threshold_applied,
            "top_k":             self.top_k,
            "classifier_used":   self.classifier_used,
            "llm_used":          self.llm_used,
            "llm_rationale":     self.llm_rationale,
            "nearest_neighbors": self.nearest_neighbors,
            "ece_at_training":   self.ece_at_training,
        }

    def format_markdown(self) -> str:
        """Retourne le résultat formaté pour le chatbot."""
        tier_emoji = {"HIGH": "✅", "MEDIUM": "⚠️", "LOW": "🔴"}.get(self.confidence_tier, "")
        tier_label = {"HIGH": "🟢 Élevée", "MEDIUM": "🟡 Moyenne", "LOW": "🔴 Faible"}.get(self.confidence_tier, self.confidence_tier)
        review_flag = "⚠️ Revue recommandée" if not self.accepted else "✅ Auto-accepté"
        model_label = {"flat": "ML Plat (TF-IDF+MiniLM)", "hierarchical_l2": "Hiérarchique L1/L2", "llm_fallback": "Groq LLM"}.get(self.classifier_used, self.classifier_used)

        lines = [
            "🤖 **Classification ML — Résultat**\n",
            "| Champ | Valeur |",
            "|---|---|",
            f"| **Domaine (L1)** | `{self.label}` — {self.confidence:.0%} |",
        ]
        if self.level_2 and self.level_2 not in ("N/A", "UNDETERMINED"):
            lines.append(f"| **Cause (L2)** | `{self.level_2}` — {self.level_2_confidence:.0%} |")
        lines += [
            f"| **Confiance** | {tier_emoji} {tier_label} |",
            f"| **Statut** | {review_flag} |",
            f"| **Seuil appliqué** | {self.threshold_applied:.0%} |",
            f"| **Moteur** | {model_label} |",
        ]
        if self.llm_used:
            lines.append("| **LLM** | ✅ Groq (confiance faible) |")

        # Top alternatives
        if self.top_k and len(self.top_k) > 1:
            lines.append("\n**🔀 Alternatives :**")
            for alt in self.top_k[1:3]:
                lines.append(f"  - `{alt['label']}` — {alt['confidence']:.0%}")

        # Nearest neighbors
        if self.nearest_neighbors:
            lines.append("\n**📎 Tickets proches :**")
            for n in self.nearest_neighbors[:3]:
                sim = n.get("similarity", 0.0)
                l1n = n.get("l1", "?")
                l2n = n.get("l2", "?")
                excerpt = (n.get("text") or "")[:100].strip()
                if excerpt:
                    lines.append(f"  - `{l1n}/{l2n}` ({sim:.0%}) — *{excerpt}…*")
                else:
                    lines.append(f"  - `{l1n}/{l2n}` ({sim:.0%})")

        if self.llm_rationale:
            lines.append(f"\n💡 **Justification Groq :** {self.llm_rationale}")

        if not self.accepted:
            reason = self.unknown_reason or "Confiance insuffisante"
            lines.append(f"\n> ⚠️ **UNKNOWN** — {reason}")
            lines.append("> Corrigez dans le module ML pour améliorer le modèle.")
        elif self.confidence_tier in ("LOW", "MEDIUM"):
            lines.append("\n> ⚠️ Confiance moyenne — vérification recommandée.")

        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# ClassificationEngine — moteur unique
# ─────────────────────────────────────────────────────────────────────────────

class ClassificationEngine:
    """
    Moteur de classification unifié.

    Usage :
        result = engine.predict("DSLAM OP49MAB11 bloqué erreur 1300")
        print(result.label, result.confidence_tier)

    Seule classe à instancier pour obtenir une classification ML.
    Ne jamais appeler MLClassifier ou HierarchicalClassifier directement
    depuis le chatbot ou l'API.
    """

    def __init__(self) -> None:
        self._ml: Optional[Any]   = None   # MLClassifier (principal)
        self._hc: Optional[Any]   = None   # HierarchicalClassifier (enrichissement L2)
        self._ready: bool         = False

    # ──────────────────────────────────────────────────────────────────────
    # Lazy initialization
    # ──────────────────────────────────────────────────────────────────────

    def _load(self):
        if self._ready:
            return
        try:
            from app.services.ml_classifier import MLClassifier
            ml = MLClassifier(data_dir="data")
            ml.load()
            self._ml = ml
            logger.info("[ClassificationEngine] MLClassifier chargé (model=%s)", ml.model is not None)
        except Exception as e:
            logger.warning("[ClassificationEngine] MLClassifier non disponible: %s", e)

        try:
            from app.services.hierarchical_classifier import HierarchicalClassifier
            hc = HierarchicalClassifier(data_dir="data")
            hc.load()
            self._hc = hc
            logger.info("[ClassificationEngine] HierarchicalClassifier chargé (trained=%s)", hc.is_trained)
        except Exception as e:
            logger.warning("[ClassificationEngine] HierarchicalClassifier non disponible: %s", e)

        self._ready = True

    def is_ready(self) -> bool:
        self._load()
        return (self._ml is not None and self._ml.model is not None) or (
            self._hc is not None and self._hc.is_trained
        )

    def reload(self):
        """Force reload (après entraînement)."""
        self._ready = False
        self._ml = None
        self._hc = None
        self._load()

    # ──────────────────────────────────────────────────────────────────────
    # PREDICT — point d'entrée unique
    # ──────────────────────────────────────────────────────────────────────

    def predict(self, text: str, groq_client=None) -> ClassificationResult:
        """
        Classifie un texte. UNIQUE point d'entrée.

        Logique décisionnelle :
          1. MLClassifier.predict_adaptive()  →  L1 + confiance calibrée
          2. Si MEDIUM/LOW + HierarchicalClassifier disponible
               → enrichissement L2 + nearest neighbors
          3. Si LOW + groq_client disponible
               → rationale LLM (pas de nouvelle classification)

        Args:
            text:        Texte du ticket à classifier.
            groq_client: Client Groq optionnel (pour rationale LLM en LOW).

        Returns:
            ClassificationResult (jamais None).
        """
        self._load()

        if not self.is_ready():
            return ClassificationResult(
                label="UNKNOWN",
                raw_label="UNKNOWN",
                confidence=0.0,
                confidence_tier="LOW",
                accepted=False,
                unknown_reason="Aucun modèle entraîné. Uploadez un CSV et entraînez le modèle dans le module ML.",
                classifier_used="none",
            )

        # ── Étape 1 : classification principale (MLClassifier) ──────────
        ml_result = self._predict_flat(text)

        if ml_result is None:
            # Fallback sur hiérarchique seul (si flat non entraîné)
            return self._predict_hierarchical_only(text, groq_client)

        # ── Étape 2 : enrichissement L2 si pertinent ────────────────────
        if self._hc and self._hc.is_trained and ml_result.accepted:
            ml_result = self._enrich_l2(text, ml_result)

        # ── Étape 3 : rationale LLM si confiance faible ─────────────────
        if ml_result.confidence_tier == "LOW" and groq_client is not None:
            ml_result = self._add_llm_rationale(text, ml_result, groq_client)

        return ml_result

    def predict_batch(self, texts: list, groq_client=None) -> List[ClassificationResult]:
        """Classifie une liste de textes (LLM désactivé pour le batch)."""
        return [self.predict(t) for t in texts]

    # ──────────────────────────────────────────────────────────────────────
    # Internals
    # ──────────────────────────────────────────────────────────────────────

    def _predict_flat(self, text: str) -> Optional[ClassificationResult]:
        """Prédiction via MLClassifier.predict_adaptive() avec seuils par classe."""
        if self._ml is None or self._ml.model is None:
            return None
        try:
            import pandas as pd
            results = self._ml.predict_adaptive(pd.Series([text]))
            r = results[0]
            ece = None
            if self._ml.model_card:
                ece = self._ml.model_card.get("ece")
            return ClassificationResult(
                label=r["predicted_label"],
                raw_label=r["raw_label"],
                confidence=r["confidence"],
                confidence_tier=r["confidence_tier"],
                accepted=r["accepted"],
                unknown_reason=r.get("unknown_reason"),
                threshold_applied=r["threshold_applied"],
                top_k=r.get("top_k", []),
                classifier_used="flat",
                ece_at_training=ece,
            )
        except Exception as e:
            logger.error("[ClassificationEngine] MLClassifier predict_adaptive failed: %s", e)
            return None

    def _predict_hierarchical_only(self, text: str, groq_client=None) -> ClassificationResult:
        """Prédit uniquement via HierarchicalClassifier (si flat non dispo)."""
        if self._hc is None or not self._hc.is_trained:
            return ClassificationResult(
                label="UNKNOWN", raw_label="UNKNOWN", confidence=0.0,
                confidence_tier="LOW", accepted=False,
                unknown_reason="Aucun modèle disponible.",
                classifier_used="none",
            )
        try:
            r = self._hc.predict_single(text, groq_client=groq_client)
            return ClassificationResult(
                label=r.get("level_1", "UNKNOWN"),
                raw_label=r.get("level_1", "UNKNOWN"),
                confidence=r.get("level_1_confidence", 0.0),
                confidence_tier=r.get("confidence_tier", "LOW"),
                accepted=not r.get("needs_review", True),
                level_2=r.get("level_2"),
                level_2_confidence=r.get("level_2_confidence", 0.0),
                nearest_neighbors=r.get("nearest_neighbors", []),
                llm_used=r.get("llm_used", False),
                llm_rationale=r.get("llm_rationale"),
                classifier_used="hierarchical_l2",
            )
        except Exception as e:
            logger.error("[ClassificationEngine] HierarchicalClassifier failed: %s", e)
            return ClassificationResult(
                label="UNKNOWN", raw_label="UNKNOWN", confidence=0.0,
                confidence_tier="LOW", accepted=False,
                unknown_reason=f"Erreur classification : {e}",
                classifier_used="error",
            )

    def _enrich_l2(self, text: str, result: ClassificationResult) -> ClassificationResult:
        """Enrichit le résultat plat avec L2 et nearest neighbors du HierarchicalClassifier."""
        try:
            # Utiliser le HierarchicalClassifier pour L2 uniquement
            hc_result = self._hc.predict_single(text, groq_client=None)
            hc_l1 = hc_result.get("level_1", "")
            # N'utiliser L2 que si L1 est cohérent avec le résultat flat
            if hc_l1.upper() == result.label.upper() or (
                result.label.upper() in hc_l1.upper() or hc_l1.upper() in result.label.upper()
            ):
                result.level_2 = hc_result.get("level_2")
                result.level_2_confidence = hc_result.get("level_2_confidence", 0.0)
                result.nearest_neighbors = hc_result.get("nearest_neighbors", [])
                result.classifier_used = "hierarchical_l2"
        except Exception as e:
            logger.debug("[ClassificationEngine] L2 enrichment failed (non-bloquant): %s", e)
        return result

    def _add_llm_rationale(self, text: str, result: ClassificationResult, groq_client) -> ClassificationResult:
        """Ajoute une justification LLM pour les prédictions LOW confidence."""
        try:
            if self._hc:
                hc_result = self._hc.predict_single(text, groq_client=groq_client)
                rationale = hc_result.get("llm_rationale")
                if rationale:
                    result.llm_rationale = rationale
                    result.llm_used = True
        except Exception as e:
            logger.debug("[ClassificationEngine] LLM rationale failed (non-bloquant): %s", e)
        return result

    # ──────────────────────────────────────────────────────────────────────
    # Status / diagnostics
    # ──────────────────────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        self._load()
        ml_info = self._ml.get_info() if self._ml else {"exists": False}
        hc_info = {}
        if self._hc:
            try:
                hc_info = self._hc.get_info() if hasattr(self._hc, "get_info") else {}
            except Exception:
                pass
        return {
            "ready": self.is_ready(),
            "active_pipeline": "flat+l2" if (self._ml and self._ml.model is not None and self._hc and self._hc.is_trained)
                               else "flat" if (self._ml and self._ml.model is not None)
                               else "hierarchical" if (self._hc and self._hc.is_trained)
                               else "none",
            "flat_model": {
                "exists":     ml_info.get("exists", False),
                "trained_at": ml_info.get("trained_at"),
                "macro_f1":   ml_info.get("macro_f1"),
                "ece":        ml_info.get("ece") if ml_info.get("exists") else None,
                "classes":    ml_info.get("classes", []),
                "preprocessing": ml_info.get("preprocessing_enabled", False),
                "per_class_thresholds_count": len(
                    (self._ml.model_card or {}).get("per_class_thresholds", {})
                ) if self._ml and self._ml.model_card else 0,
            },
            "hierarchical_model": {
                "exists":   bool(self._hc and self._hc.is_trained),
                "l2_enrichment_active": bool(self._hc and self._hc.is_trained),
            },
        }


# ─────────────────────────────────────────────────────────────────────────────
# Singleton — UNE SEULE instance partagée dans tout le backend
# ─────────────────────────────────────────────────────────────────────────────

classification_engine = ClassificationEngine()
