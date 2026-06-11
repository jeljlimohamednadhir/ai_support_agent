"""
explainability_engine.py
━━━━━━━━━━━━━━━━━━━━━━━━
Deterministic reasoning chain generator.

Produces structured forensic explanations from evidence without any LLM reasoning.
The LLM only reformats the output — it never generates the reasoning.

Outputs:
  - WHY the incident happened
  - WHICH workflow failed
  - WHICH validation blocked
  - WHICH DB rows caused the issue
  - WHICH logs confirm the issue
  - WHICH exception triggered
  - WHICH source file contains the logic
  - WHICH FR validates the resolution

Design:
  - Fully deterministic
  - Evidence-backed only (no invented reasoning)
  - Graceful degradation (returns partial when evidence is incomplete)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ReasoningLink:
    """Single link in the reasoning chain."""
    step:        int
    category:    str        # "symptom" | "evidence" | "validation" | "constraint" | "root_cause" | "resolution"
    title:       str
    detail:      str
    confidence:  float = 0.0
    source_type: str = ""   # "db" | "log" | "code" | "fr" | "ssh"
    ref:         str = ""   # reference (file:line, FR-XXX, table name...)

    def to_display(self) -> str:
        icons = {
            "symptom":    "🔍",
            "evidence":   "📊",
            "validation": "🔒",
            "constraint": "⛔",
            "root_cause": "🧠",
            "resolution": "✅",
        }
        icon = icons.get(self.category, "•")
        conf = f" ({int(self.confidence*100)}%)" if self.confidence > 0 else ""
        ref_str = f" — `{self.ref}`" if self.ref else ""
        return f"{icon} **{self.title}**{conf}{ref_str}\n   {self.detail}"


@dataclass
class ForensicExplanation:
    """Complete forensic explanation for one diagnostic."""
    reasoning_chain:     List[ReasoningLink] = field(default_factory=list)
    technical_summary:   str = ""
    collaborator_summary: str = ""
    root_cause:          Optional[str] = None
    root_cause_confidence: float = 0.0
    workflow:            Optional[str] = None
    blocking_validation: Optional[str] = None
    source_location:     Optional[str] = None
    fr_reference:        Optional[str] = None
    evidence_count:      int = 0
    identified_exceptions: List[str] = field(default_factory=list)

    def to_reasoning_display(self) -> str:
        """Full reasoning chain for user display."""
        if not self.reasoning_chain:
            return ""
        parts = ["**🔗 Chaîne de raisonnement forensique**", ""]
        for link in self.reasoning_chain:
            parts.append(link.to_display())
            parts.append("")
        return "\n".join(parts)

    def to_technical_block(self) -> str:
        """Technical summary block."""
        parts = []
        if self.root_cause:
            parts.append(f"🧠 **Root Cause**: {self.root_cause}")
        if self.workflow:
            parts.append(f"🔄 **Workflow**: {self.workflow}")
        if self.blocking_validation:
            parts.append(f"⛔ **Validation bloquante**: {self.blocking_validation}")
        if self.source_location:
            parts.append(f"📌 **Source**: `{self.source_location}`")
        if self.fr_reference:
            parts.append(f"📋 **FR**: {self.fr_reference}")
        if self.evidence_count:
            parts.append(f"📊 **Preuves**: {self.evidence_count} source(s)")
        return "\n".join(parts) if parts else ""

    def to_collaborator_block(self) -> str:
        """Simple explanation for non-technical collaborators."""
        return self.collaborator_summary or self.technical_summary


class ExplainabilityEngine:
    """
    Generates deterministic reasoning chains from diagnostic evidence.

    Usage::
        engine = ExplainabilityEngine()
        explanation = engine.explain(
            intent="delete_equipment",
            entity="DSROB362",
            db_evidence={...},
            log_evidence=[...],
            correlation_hypotheses=[...],
            code_hits=[...],
            resolution_blocks=[...],
        )
        print(explanation.to_reasoning_display())
    """

    def explain(
        self,
        intent: str,
        entity: Optional[str] = None,
        db_evidence: Optional[Dict[str, Any]] = None,
        log_summary: Optional[Any] = None,  # ForensicSummary
        correlation_hypotheses: Optional[List[Any]] = None,
        code_hits: Optional[List[Any]] = None,
        resolution_blocks: Optional[List[Any]] = None,
        fr_sources: Optional[List[Dict]] = None,
    ) -> ForensicExplanation:
        """
        Build a complete forensic explanation from all evidence sources.
        Never raises — returns partial explanation on error.
        """
        explanation = ForensicExplanation()
        step = 0

        try:
            # ── Step 1: Symptom ─────────────────────────────────────────
            step += 1
            symptom_detail = self._describe_symptom(intent, entity)
            explanation.reasoning_chain.append(ReasoningLink(
                step=step,
                category="symptom",
                title="Symptôme déclaré",
                detail=symptom_detail,
                source_type="user",
            ))

            # ── Step 2: DB Evidence ─────────────────────────────────────
            if db_evidence:
                for qname, ev in db_evidence.items():
                    if not hasattr(ev, "has_data") or not ev.has_data:
                        continue
                    step += 1
                    explanation.evidence_count += 1
                    detail = f"{ev.row_count} enregistrement(s) dans `{ev.table or qname}`"
                    if ev.eqpt_id:
                        detail += f" (eqpt_id={ev.eqpt_id})"
                    explanation.reasoning_chain.append(ReasoningLink(
                        step=step,
                        category="evidence",
                        title=f"Preuve DB: {qname}",
                        detail=detail,
                        confidence=ev.confidence,
                        source_type="db",
                        ref=ev.table or qname,
                    ))

            # ── Step 3: Log Evidence ────────────────────────────────────
            if log_summary and hasattr(log_summary, "exception_chain"):
                if log_summary.exception_chain:
                    step += 1
                    explanation.evidence_count += 1
                    chain_str = " → ".join(log_summary.exception_chain[:4])
                    explanation.reasoning_chain.append(ReasoningLink(
                        step=step,
                        category="evidence",
                        title="Chaîne d'exceptions runtime",
                        detail=f"Exceptions détectées: {chain_str}",
                        confidence=0.9,
                        source_type="log",
                    ))

                if log_summary.has_rollback:
                    step += 1
                    explanation.reasoning_chain.append(ReasoningLink(
                        step=step,
                        category="evidence",
                        title="Rollback détecté",
                        detail="Transaction annulée — opération n'a pas abouti",
                        confidence=0.95,
                        source_type="log",
                    ))

                if log_summary.affected_tables:
                    step += 1
                    explanation.reasoning_chain.append(ReasoningLink(
                        step=step,
                        category="constraint",
                        title="Tables impactées",
                        detail=", ".join(log_summary.affected_tables[:5]),
                        source_type="log",
                    ))

            # ── Step 4: Code Validation ─────────────────────────────────
            if code_hits:
                for hit in code_hits[:3]:
                    step += 1
                    explanation.evidence_count += 1
                    loc = hit.code_location if hasattr(hit, "code_location") else {}
                    file_short = loc.get("file", "").split("\\")[-1].split("/")[-1]
                    method = loc.get("method", "?")
                    line_no = loc.get("line", "")
                    ref = f"{method}() [{file_short}:{line_no}]" if file_short else ""

                    blocking = getattr(hit, "blocking_condition", "") or ""
                    detail = blocking if blocking else f"Exception: {getattr(hit, 'exception', '?')}"

                    explanation.reasoning_chain.append(ReasoningLink(
                        step=step,
                        category="validation",
                        title=f"Validation code source",
                        detail=detail,
                        confidence=getattr(hit, "confidence", 0.8),
                        source_type="code",
                        ref=ref,
                    ))

                    # Capture first code location
                    if not explanation.source_location and ref:
                        explanation.source_location = ref
                    if not explanation.blocking_validation and blocking:
                        explanation.blocking_validation = blocking

            # ── Step 4b: Execution Graph Chain ──────────────────────────
            try:
                from app.services.code_intelligence.operation_graph import operation_graph
                chain_context = operation_graph.to_forensic_context(intent, entity, max_chars=600)
                if chain_context:
                    step += 1
                    explanation.reasoning_chain.append(ReasoningLink(
                        step=step,
                        category="validation",
                        title="Chaîne d'exécution source",
                        detail=chain_context[:400],
                        confidence=0.85,
                        source_type="code",
                        ref="execution_graph",
                    ))
                    # Extract blocking conditions from operation path
                    blocking_list = operation_graph.get_blocking_conditions(intent, entity)
                    if blocking_list and not explanation.blocking_validation:
                        explanation.blocking_validation = blocking_list[0]
                    # Extract exceptions from operation path
                    exc_list = operation_graph.get_exceptions_for_intent(intent, entity)
                    if exc_list:
                        explanation.identified_exceptions = exc_list[:4]
            except Exception as _eg_e:
                logger.debug(f"[ExplainabilityEngine] Execution graph step skipped: {_eg_e}")

            # ── Step 5: Correlation → Root Cause ────────────────────────
            if correlation_hypotheses:
                top = correlation_hypotheses[0] if correlation_hypotheses else None
                if top:
                    step += 1
                    explanation.root_cause = top.cause
                    explanation.root_cause_confidence = top.confidence
                    explanation.reasoning_chain.append(ReasoningLink(
                        step=step,
                        category="root_cause",
                        title=f"Cause racine: {top.cause}",
                        detail=top.description or f"Confiance: {int(top.confidence*100)}%",
                        confidence=top.confidence,
                        source_type="correlation",
                        ref=", ".join(top.fr_ids) if top.fr_ids else "",
                    ))

                    if top.fr_ids:
                        explanation.fr_reference = ", ".join(top.fr_ids)

            # ── Step 6: Resolution Path ─────────────────────────────────
            if resolution_blocks:
                step += 1
                actions = []
                for block in resolution_blocks[:3]:
                    title = block.get("title", "")
                    if title:
                        actions.append(title)
                explanation.reasoning_chain.append(ReasoningLink(
                    step=step,
                    category="resolution",
                    title="Résolution recommandée",
                    detail="; ".join(actions) if actions else "Voir procédure FR",
                    source_type="fr",
                    ref=explanation.fr_reference or "",
                ))

            # ── Step 7: FR Sources ──────────────────────────────────────
            if fr_sources:
                for src in fr_sources[:2]:
                    fr_num = src.get("source_fr_numbers", [""])[0] if src.get("source_fr_numbers") else ""
                    if fr_num:
                        if not explanation.fr_reference:
                            explanation.fr_reference = f"FR-{fr_num}"
                        step += 1
                        explanation.reasoning_chain.append(ReasoningLink(
                            step=step,
                            category="resolution",
                            title=f"FR {fr_num}: {src.get('title', '')}",
                            detail="Fiche de résolution validée par l'équipe N3",
                            source_type="fr",
                            ref=f"FR-{fr_num}",
                        ))
                        break  # Only the best FR

            # ── Generate summaries ──────────────────────────────────────
            explanation.workflow = self._infer_workflow(intent)
            explanation.technical_summary = self._build_technical_summary(explanation)
            explanation.collaborator_summary = self._build_collaborator_summary(explanation, entity)

        except Exception as e:
            logger.warning(f"[ExplainabilityEngine] Error building explanation: {e}")

        return explanation

    def _describe_symptom(self, intent: str, entity: Optional[str]) -> str:
        """Human-readable symptom description."""
        intent_map = {
            "delete_equipment": f"Impossible de supprimer l'équipement {entity or '?'}",
            "delete_vlan": f"Suppression du VLAN {entity or '?'} bloquée",
            "create_equipment": f"Création de l'équipement {entity or '?'} en échec",
            "modify_equipment": f"Modification de l'équipement {entity or '?'} impossible",
            "blocked_script": f"Script IHM bloqué pour {entity or '?'}",
        }
        return intent_map.get(intent, f"Opération '{intent}' impossible sur {entity or '?'}")

    def _infer_workflow(self, intent: str) -> Optional[str]:
        """Map intent to BRASIL workflow name."""
        workflow_map = {
            "delete_equipment": "EquipmentDeletionWorkflow",
            "delete_vlan": "VlanDeletionWorkflow",
            "create_equipment": "EquipmentCreationWorkflow",
            "modify_equipment": "EquipmentModificationWorkflow",
            "blocked_script": "IhmScriptWorkflow",
        }
        return workflow_map.get(intent)

    def _build_technical_summary(self, expl: ForensicExplanation) -> str:
        """One-paragraph technical summary."""
        parts = []
        if expl.root_cause:
            parts.append(f"Cause: {expl.root_cause}")
        if expl.blocking_validation:
            parts.append(f"Validation bloquante: {expl.blocking_validation}")
        if expl.source_location:
            parts.append(f"Source: {expl.source_location}")
        if expl.fr_reference:
            parts.append(f"Réf: {expl.fr_reference}")
        return " | ".join(parts) if parts else "Diagnostic en cours"

    def _build_collaborator_summary(self, expl: ForensicExplanation, entity: Optional[str]) -> str:
        """Simple explanation for collaborators."""
        if expl.root_cause == "delete_blocked":
            return (
                f"L'équipement {entity or '?'} ne peut pas être supprimé car "
                "des données associées existent encore dans la base. "
                "Il faut d'abord nettoyer ces dépendances."
            )
        if expl.root_cause == "residual_data":
            return (
                f"Des enregistrements résiduels empêchent l'opération sur {entity or '?'}. "
                "Un nettoyage ciblé est nécessaire."
            )
        if expl.root_cause:
            return f"L'opération est bloquée par: {expl.root_cause}."
        return "Le diagnostic est en cours d'analyse."


# Singleton
explainability_engine = ExplainabilityEngine()
