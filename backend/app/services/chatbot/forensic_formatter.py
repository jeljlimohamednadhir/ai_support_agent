"""
forensic_formatter.py
━━━━━━━━━━━━━━━━━━━━━
Builds structured forensic diagnostic responses for the BRASIL N3 platform.

Output format:
  🧠 Root Cause
  🔍 Runtime Evidence
  📌 Source Validation
  🕓 Forensic Timeline
  ✅ Recommended Resolution
  ⚠️ Confidence

Design:
  - Fully deterministic — assembles sections from pre-computed evidence
  - LLM never generates any of this content
  - Graceful degradation — sections are hidden when evidence is missing
  - DEMO_MODE prioritizes strongest evidence and suppresses noise
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DEMO_MODE — prioritize display quality without faking evidence
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DEMO_MODE = os.environ.get("DEMO_MODE", "").lower() in ("1", "true", "yes")


@dataclass
class ForensicSection:
    """Single section of a forensic response."""
    emoji:   str
    title:   str
    lines:   List[str] = field(default_factory=list)
    visible: bool = True

    def render(self) -> str:
        if not self.visible or not self.lines:
            return ""
        header = f"{self.emoji} **{self.title}**"
        body = "\n".join(self.lines)
        return f"{header}\n{body}"


class ForensicResponseBuilder:
    """
    Assembles a structured forensic response from pre-computed evidence.

    Usage::

        builder = ForensicResponseBuilder()
        response = builder.build(
            intent="delete_equipment",
            entity="DSROB362",
            bundle=diagnostic_bundle,
            resolution_text="...",
            code_hits=[...],
            fr_sources=[...],
        )
        # response.primary  → first message (diagnostic)
        # response.followup → second message (evidence detail)
    """

    def build(
        self,
        intent: str = "",
        entity: Optional[str] = None,
        db_evidence: Optional[Dict[str, Any]] = None,
        log_evidence: Optional[List] = None,
        ssh_summary: Optional[List[str]] = None,
        code_hits: Optional[List] = None,
        correlation_hypotheses: Optional[List] = None,
        forensic_summary: Optional[Dict] = None,
        explanation: Optional[Dict] = None,
        resolution_text: str = "",
        resolution_blocks: Optional[List] = None,
        fr_sources: Optional[List[Dict]] = None,
        confidence: float = 0.0,
        parsed_log_events: Optional[List] = None,
        timeline: Optional[List] = None,
    ) -> "ForensicResponse":
        """Build complete forensic response. Never raises."""
        response = ForensicResponse()
        try:
            response.primary = self._build_primary(
                intent=intent,
                entity=entity,
                db_evidence=db_evidence,
                ssh_summary=ssh_summary,
                code_hits=code_hits,
                correlation_hypotheses=correlation_hypotheses,
                explanation=explanation,
                resolution_text=resolution_text,
                fr_sources=fr_sources,
                confidence=confidence,
            )
            response.followup = self._build_followup(
                entity=entity,
                intent=intent,
                forensic_summary=forensic_summary,
                parsed_log_events=parsed_log_events,
                correlation_hypotheses=correlation_hypotheses,
                timeline=timeline,
                resolution_blocks=resolution_blocks,
                explanation=explanation,
            )
        except Exception as e:
            logger.warning(f"[ForensicFormatter] Build error: {e}")
            if not response.primary:
                response.primary = self._fallback_response(intent, entity)
        return response

    # ── Primary message ───────────────────────────────────────────────────

    def _build_primary(
        self,
        intent: str,
        entity: Optional[str],
        db_evidence: Optional[Dict],
        ssh_summary: Optional[List[str]],
        code_hits: Optional[List],
        correlation_hypotheses: Optional[List],
        explanation: Optional[Dict],
        resolution_text: str,
        fr_sources: Optional[List[Dict]],
        confidence: float,
    ) -> str:
        sections: List[ForensicSection] = []

        # ── 🧠 Root Cause ────────────────────────────────────────────────
        root_section = ForensicSection(emoji="🧠", title="Root Cause")
        root_cause_text = ""
        if explanation and explanation.get("root_cause"):
            root_cause_text = explanation["root_cause"]
            if explanation.get("collaborator_summary"):
                root_section.lines.append(explanation["collaborator_summary"])
            else:
                root_section.lines.append(
                    self._describe_root_cause(root_cause_text, entity)
                )
        elif correlation_hypotheses:
            top = correlation_hypotheses[0]
            desc = getattr(top, "description", "") or top.get("description", "") if isinstance(top, dict) else getattr(top, "description", "")
            root_section.lines.append(desc or f"Cause identifiée: {getattr(top, 'cause', str(top))}")
        else:
            root_section.lines.append(
                self._describe_root_cause_from_intent(intent, entity)
            )
        sections.append(root_section)

        # ── 🔍 Runtime Evidence ──────────────────────────────────────────
        ev_section = ForensicSection(emoji="🔍", title="Runtime Evidence")
        evidence_count = 0

        if db_evidence:
            for qname, ev in db_evidence.items():
                if not hasattr(ev, "has_data") or not ev.has_data:
                    continue
                evidence_count += 1
                table = getattr(ev, "table", None) or qname
                rows = getattr(ev, "row_count", 0)
                eqpt_id = getattr(ev, "eqpt_id", None)
                line = f"- **{rows}** enregistrement(s) dans `{table}`"
                if eqpt_id:
                    line += f" (eqpt_id={eqpt_id})"
                ev_section.lines.append(line)

        if correlation_hypotheses:
            for h in (correlation_hypotheses[:2] if not DEMO_MODE else correlation_hypotheses[:3]):
                cause = h.get("cause", "") if isinstance(h, dict) else getattr(h, "cause", "")
                conf = h.get("confidence", 0) if isinstance(h, dict) else getattr(h, "confidence", 0)
                evidence = h.get("evidence", []) if isinstance(h, dict) else getattr(h, "evidence", [])
                if evidence:
                    for e in evidence[:2]:
                        ev_section.lines.append(f"- `{e}` détecté (corrélation {int(conf*100)}%)")
                    evidence_count += 1

        if ssh_summary:
            for s in ssh_summary:
                ev_section.lines.append(f"- {s}")

        if not ev_section.lines:
            ev_section.lines.append("- Aucune preuve runtime collectée (serveurs non accessibles)")
        sections.append(ev_section)

        # ── 📌 Source Validation ─────────────────────────────────────────
        src_section = ForensicSection(emoji="📌", title="Source Validation")
        if code_hits:
            for hit in code_hits[:3]:
                loc = hit.code_location if hasattr(hit, "code_location") else {}
                file_short = loc.get("file", "").split("\\")[-1].split("/")[-1]
                method = loc.get("method", "?")
                line_no = loc.get("line", "")
                bc = getattr(hit, "blocking_condition", "") or getattr(hit, "exception_class", "")
                if file_short:
                    src_section.lines.append(f"- `{file_short}:{line_no}` → `{method}()`")
                    if bc:
                        src_section.lines.append(f"  Condition: {bc}")
                    evidence_count += 1

        # FR references
        fr_refs = []
        if fr_sources:
            for src in fr_sources[:3]:
                nums = src.get("source_fr_numbers", [])
                title = src.get("title", src.get("name", ""))
                for n in nums[:1]:
                    fr_refs.append(f"FR-{n}")
                    src_section.lines.append(f"- **FR {n}**: {title}")
        if explanation and explanation.get("fr_reference"):
            ref = explanation["fr_reference"]
            if ref not in fr_refs:
                src_section.lines.append(f"- {ref}")

        src_section.visible = bool(src_section.lines)
        sections.append(src_section)

        # ── ✅ Recommended Resolution ────────────────────────────────────
        res_section = ForensicSection(emoji="✅", title="Résolution recommandée")
        if resolution_text:
            res_section.lines.append(resolution_text.strip())
        else:
            res_section.lines.append(self._default_resolution(intent, entity))
        sections.append(res_section)

        # ── ⚠️ Confidence ───────────────────────────────────────────────
        conf_section = ForensicSection(emoji="⚠️", title="Confiance")
        conf_val = confidence or (explanation.get("root_cause_confidence", 0) if explanation else 0)
        conf_label = "HIGH" if conf_val >= 0.8 else "MEDIUM" if conf_val >= 0.5 else "LOW"
        sources = []
        if db_evidence:
            sources.append("DB")
        if correlation_hypotheses:
            sources.append("logs")
        if code_hits:
            sources.append("source code")
        if fr_sources:
            sources.append("FR")
        if ssh_summary:
            sources.append("SSH")
        source_str = " + ".join(sources) if sources else "déterministe"
        conf_section.lines.append(
            f"**{conf_label}** ({conf_val:.2f}) — {evidence_count} preuve(s) — sources: {source_str}"
        )
        sections.append(conf_section)

        # ── Assemble ─────────────────────────────────────────────────────
        rendered = []
        for s in sections:
            r = s.render()
            if r:
                rendered.append(r)
        return "\n\n".join(rendered)

    # ── Follow-up message ─────────────────────────────────────────────────

    def _build_followup(
        self,
        entity: Optional[str],
        intent: str,
        forensic_summary: Optional[Dict],
        parsed_log_events: Optional[List],
        correlation_hypotheses: Optional[List],
        timeline: Optional[List],
        resolution_blocks: Optional[List],
        explanation: Optional[Dict],
    ) -> Optional[str]:
        parts: List[str] = []

        # ── 🕓 Forensic Timeline ────────────────────────────────────────
        if forensic_summary and forensic_summary.get("timeline_count", 0) > 0:
            ctx = forensic_summary.get("context_for_llm", "")
            if ctx:
                parts.append("🔬 **Analyse forensique**")
                parts.append(f"```\n{ctx}\n```")
                parts.append("")

        # ── Log events ───────────────────────────────────────────────────
        if parsed_log_events:
            parts.append("📋 **Lignes de log structurées**")
            for ev in parsed_log_events[:8]:
                line = getattr(ev, "to_forensic_line", None)
                if line:
                    parts.append(line() if callable(line) else str(line))
                else:
                    parts.append(str(ev))
            parts.append("")

        # ── Reasoning chain ──────────────────────────────────────────────
        if explanation:
            chain = explanation.get("reasoning_chain_display", "")
            if chain:
                parts.append(chain)
                parts.append("")

        # ── Resolved SQL ─────────────────────────────────────────────────
        if resolution_blocks:
            sql_lines = []
            for rb in resolution_blocks:
                if isinstance(rb, dict) and rb.get("sql_resolved") and rb.get("sql_hints_raw"):
                    sql_lines.extend(rb["sql_hints_raw"])
            if sql_lines:
                parts.append("🗄️ **Requêtes SQL (valeurs réelles)**")
                for sq in sql_lines[:4]:
                    parts.append(f"```sql\n{sq}\n```")

        return "\n".join(parts) if parts else None

    # ── Helpers ───────────────────────────────────────────────────────────

    def _describe_root_cause(self, cause: str, entity: Optional[str]) -> str:
        eqpt = entity or "l'équipement"
        descriptions = {
            "delete_blocked": f"La suppression de {eqpt} est bloquée par des données résiduelles en base.",
            "residual_data": f"Des enregistrements résiduels empêchent l'opération sur {eqpt}.",
            "active_services": f"Des services actifs sont encore liés à {eqpt}.",
            "foreign_key_violation": "Une contrainte d'intégrité référentielle bloque l'opération.",
            "state_incoherent": f"{eqpt} est dans un état incohérent.",
            "mrt_dependency": f"Des liens MRT actifs bloquent l'opération sur {eqpt}.",
            "business_rule_violation": "Une règle métier fonctionnelle bloque l'opération.",
            "equipment_not_found": f"L'équipement {entity or '?'} est introuvable dans la base.",
        }
        return descriptions.get(cause, f"Cause identifiée: {cause}")

    def _describe_root_cause_from_intent(self, intent: str, entity: Optional[str]) -> str:
        eqpt = entity or "l'équipement"
        intent_descriptions = {
            "delete_equipment": f"La suppression de {eqpt} est probablement bloquée par des dépendances résiduelles.",
            "delete_vlan": f"Le VLAN {entity or '?'} ne peut être supprimé — interfaces ou ressources actives.",
            "diagnose_equipment": f"Problème détecté sur {eqpt} — investigation en cours.",
            "equipment_stuck_state": f"{eqpt} est dans un état bloqué.",
        }
        return intent_descriptions.get(intent, f"Opération '{intent}' sur {entity or '?'} — analyse déterministe.")

    def _default_resolution(self, intent: str, entity: Optional[str]) -> str:
        resolutions = {
            "delete_equipment": (
                "1. Identifier l'eqpt_id dans `t_equipments`\n"
                "2. Vérifier les dépendances résiduelles\n"
                "3. Nettoyer les enregistrements orphelins\n"
                "4. Relancer la suppression"
            ),
            "delete_vlan": (
                "1. Vérifier les VP/VC actifs sur le VLAN\n"
                "2. Libérer les ressources associées\n"
                "3. Relancer la suppression"
            ),
        }
        return resolutions.get(intent, "Consulter la FR applicable pour la procédure détaillée.")

    def _fallback_response(self, intent: str, entity: Optional[str]) -> str:
        return (
            f"🧠 **Diagnostic**\n"
            f"L'opération '{intent}' sur {entity or '?'} a rencontré un problème.\n\n"
            f"⚠️ **Confiance**\n"
            f"**LOW** — Preuves runtime insuffisantes pour un diagnostic certain.\n"
            f"Consultez les logs serveur et la FR applicable."
        )


@dataclass
class ForensicResponse:
    """Complete formatted forensic response."""
    primary:  str = ""
    followup: Optional[str] = None


# Singleton
forensic_formatter = ForensicResponseBuilder()
