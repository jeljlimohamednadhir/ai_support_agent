"""
ML AI Analyst Service
Génère via Groq : narratif exécutif, recommandations contextualisées,
scores de criticité, détection d'anomalies temporelles.
"""
import json
import re
from typing import Any, Dict, List, Optional
import pandas as pd

from app.core.llm_client import llm_client
from app.core.logging import get_logger

logger = get_logger(__name__)

# ── Prompt système commun ─────────────────────────────────────────────────────
_SYSTEM_PROMPT = """Tu es un expert data analyst senior spécialisé dans la gestion des incidents
télécom (Orange). Tu analyses des données de tickets de support N3 pour l'application BRASIL.
Tes réponses sont concises, factuelles, orientées action, en français.
Tu NE génères JAMAIS de SQL ni de code. Tu répondras UNIQUEMENT en JSON valide quand demandé."""


class MLAIAnalyst:
    """Génère des insights IA à partir du résumé exécutif ML."""

    # ── 1. Narratif exécutif + recommandations + criticité ──────────────────
    async def generate_executive_insights(
        self,
        volume: int,
        mttr_med: Optional[float],
        top_causes: List[Dict[str, Any]],
        top_categories: List[Dict[str, Any]],
        top_codes: List[Dict[str, Any]],
        date_range: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Appelle le LLM pour générer :
        - narratif exécutif (5-8 lignes)
        - recommandations priorisées (5 max)
        - scores de criticité par catégorie
        """
        date_str = ""
        if date_range:
            date_str = f"Période analysée : {date_range.get('start', '?')} → {date_range.get('end', '?')}\n"

        causes_txt = "\n".join(
            f"  - {c['cause']}: {c['volume']} tickets ({c['pct']}%)"
            for c in top_causes[:8]
        ) or "  (aucune cause détectée)"

        cats_txt = "\n".join(
            f"  - {c['category']}: {c['volume']} tickets ({c['pct']}%)"
            for c in top_categories[:8]
        ) or "  (aucune catégorie détectée)"

        codes_txt = ", ".join(c["code"] for c in top_codes[:5]) or "aucun"
        mttr_str = f"{mttr_med:.1f} jours" if mttr_med else "non calculé"

        prompt = f"""Voici les KPIs d'un lot de tickets de support N3 BRASIL :

{date_str}Volume total : {volume} tickets
MTTR médian : {mttr_str}
Codes d'erreur saillants : {codes_txt}

Top causes :
{causes_txt}

Top catégories :
{cats_txt}

Génère un JSON avec exactement cette structure (pas d'explication autour, JSON pur) :
{{
  "narrative": "<5 à 8 lignes de synthèse managériale en français, claire et factuelle>",
  "recommendations": [
    {{"priority": 1, "action": "<action concrète>", "impact": "high|medium|low", "category": "<catégorie concernée>"}},
    {{"priority": 2, "action": "...", "impact": "...", "category": "..."}},
    {{"priority": 3, "action": "...", "impact": "...", "category": "..."}},
    {{"priority": 4, "action": "...", "impact": "...", "category": "..."}},
    {{"priority": 5, "action": "...", "impact": "...", "category": "..."}}
  ],
  "criticality_scores": [
    {{"category": "<nom>", "score": <0-100>, "badge": "high|medium|low", "rationale": "<1 phrase>"}}
  ]
}}"""

        try:
            raw = await llm_client.generate(
                prompt=prompt,
                system_prompt=_SYSTEM_PROMPT,
                temperature=0.3,
                max_tokens=1200,
            )
            result = self._parse_json_response(raw)
            return result
        except Exception as e:
            logger.error(f"[MLAIAnalyst] generate_executive_insights failed: {e}")
            return {
                "narrative": None,
                "recommendations": [],
                "criticality_scores": [],
            }

    # ── 2. Détection d'anomalies temporelles ────────────────────────────────
    async def detect_temporal_anomalies(
        self,
        timeseries: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Détecte les pics / creux significatifs dans la timeseries
        et demande au LLM une hypothèse de cause.
        """
        if not timeseries or len(timeseries) < 3:
            return []

        try:
            # Agréger par date
            df = pd.DataFrame(timeseries)
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df = df.dropna(subset=["date"]).groupby("date")["volume"].sum().reset_index()
            df = df.sort_values("date")

            volumes = df["volume"].values
            mean_v = float(pd.Series(volumes).mean())
            std_v = float(pd.Series(volumes).std()) or 1.0

            anomalies_raw = []
            for i, row in df.iterrows():
                z = (row["volume"] - mean_v) / std_v
                if abs(z) >= 1.8:
                    direction = "spike" if z > 0 else "drop"
                    delta_pct = round((row["volume"] - mean_v) / mean_v * 100, 1)
                    anomalies_raw.append({
                        "period": str(row["date"].date()),
                        "volume": int(row["volume"]),
                        "delta_pct": delta_pct,
                        "direction": direction,
                    })

            if not anomalies_raw:
                return []

            # Envoyer au LLM pour hypothèses
            anomalies_txt = "\n".join(
                f"  - {a['period']} : {a['volume']} tickets ({'+' if a['delta_pct'] > 0 else ''}{a['delta_pct']}% vs moyenne)"
                for a in anomalies_raw[:5]
            )
            prompt = f"""Dans une série temporelle de tickets de support N3 BRASIL, les périodes suivantes
sont statistiquement anormales (z-score ≥ 1.8) :
{anomalies_txt}

Pour chaque anomalie, propose une hypothèse courte (15 mots max) sur la cause probable
(ex: MEP applicative, campagne de migration, panne infra, etc.).

Réponds UNIQUEMENT en JSON valide, tableau d'objets :
[
  {{"period": "YYYY-MM-DD", "hypothesis": "<hypothèse courte>"}},
  ...
]"""

            raw = await llm_client.generate(
                prompt=prompt,
                system_prompt=_SYSTEM_PROMPT,
                temperature=0.2,
                max_tokens=400,
            )
            hypotheses = self._parse_json_response(raw)
            hyp_map = {}
            if isinstance(hypotheses, list):
                for h in hypotheses:
                    hyp_map[h.get("period", "")] = h.get("hypothesis", "")

            result = []
            for a in anomalies_raw:
                a["hypothesis"] = hyp_map.get(a["period"], "Anomalie détectée — investigation requise")
                result.append(a)
            return result

        except Exception as e:
            logger.error(f"[MLAIAnalyst] detect_temporal_anomalies failed: {e}")
            return []

    # ── 3. Génération de contexte pour le chatbot (collection Qdrant) ────────
    def build_qdrant_payload(
        self,
        summary: Dict[str, Any],
        narrative: Optional[str],
        recommendations: List[Dict],
        criticality_scores: List[Dict],
        temporal_anomalies: List[Dict],
        date_range: Optional[Dict] = None,
    ) -> str:
        """Construit le texte à injecter dans Qdrant pour que le chatbot puisse répondre."""
        lines = ["=== ANALYSE ML TICKETS BRASIL ===\n"]
        if date_range:
            lines.append(f"Période : {date_range.get('start', '?')} → {date_range.get('end', '?')}")
        lines.append(f"Volume total : {summary.get('volume', '?')} tickets")
        if summary.get("mttr_med"):
            lines.append(f"MTTR médian : {summary['mttr_med']:.1f} jours")

        if narrative:
            lines.append(f"\n--- SYNTHÈSE MANAGÉRIALE ---\n{narrative}")

        if criticality_scores:
            lines.append("\n--- CRITICITÉ PAR CATÉGORIE ---")
            for cs in criticality_scores[:8]:
                lines.append(
                    f"  [{cs.get('badge', '?').upper()}] {cs.get('category', '?')} "
                    f"— score {cs.get('score', '?')}/100 — {cs.get('rationale', '')}"
                )

        if summary.get("top_causes"):
            lines.append("\n--- TOP CAUSES ---")
            for c in summary["top_causes"][:6]:
                lines.append(f"  - {c.get('cause', '?')} : {c.get('volume', '?')} tickets ({c.get('pct', '?')}%)")

        if summary.get("top_categories"):
            lines.append("\n--- TOP CATÉGORIES ---")
            for c in summary["top_categories"][:6]:
                lines.append(f"  - {c.get('category', '?')} : {c.get('volume', '?')} tickets ({c.get('pct', '?')}%)")

        if recommendations:
            lines.append("\n--- RECOMMANDATIONS PRIORITAIRES ---")
            for r in recommendations[:5]:
                impact = r.get("impact", "?").upper()
                lines.append(f"  P{r.get('priority', '?')} [{impact}] {r.get('action', '?')}")

        if temporal_anomalies:
            lines.append("\n--- ANOMALIES TEMPORELLES ---")
            for a in temporal_anomalies[:5]:
                direction = "📈 PIC" if a.get("direction") == "spike" else "📉 CHUTE"
                lines.append(
                    f"  {direction} {a.get('period', '?')} : {a.get('volume', '?')} tickets "
                    f"({a.get('delta_pct', '?')}%) — {a.get('hypothesis', '')}"
                )

        return "\n".join(lines)

    # ── Helpers ──────────────────────────────────────────────────────────────
    def _parse_json_response(self, raw: str) -> Any:
        """Extrait le premier bloc JSON valide d'une réponse LLM."""
        if not raw:
            return {}
        # Chercher entre ``` si présents
        block = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", raw)
        text = block.group(1) if block else raw.strip()
        # Tenter le parse direct
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Essayer d'extraire juste le premier objet/tableau
            m = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
            if m:
                try:
                    return json.loads(m.group(1))
                except Exception:
                    pass
        logger.warning("[MLAIAnalyst] Could not parse JSON from LLM response")
        return {}


# Singleton
ml_ai_analyst = MLAIAnalyst()
