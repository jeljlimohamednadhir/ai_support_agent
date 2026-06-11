"""
Layer 7 — Response Generator
================================
Structured diagnostic response builder for N3-level BRASIL support.

Produces responses in two modes:
  - "expert": Full N3 structured format (Diagnostic / Root Cause / Actions / Evidence)
  - "natural": Human-friendly conversational response for non-technical operators

Rules:
  • No generic answers ("je ne sais pas", "essayez de redémarrer")
  • Every response must map to a CorrelationHypothesis or explicitly state
    "insufficient evidence" with a question
  • Evidence blocks must reference INCIDENT or FR source IDs
  • Resolution summaries include: entity, actions taken, confirmation
  • JIRA data NEVER included in any output

Template slots:
  [DIAGNOSTIC]      — What is the suspected problem
  [ROOT_CAUSE]      — Technical root cause from correlation
  [ACTIONS]         — Numbered list of verified actions
  [EVIDENCE]        — Source citations (incident IDs, FR numbers)
  [NEXT_QUESTION]   — Follow-up if insufficient information
"""
from __future__ import annotations

import re
import logging
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from app.services.chatbot.conversation_state import ConversationState
from app.services.chatbot.correlation_engine import CorrelationResult, CorrelationHypothesis
from app.services.chatbot.validation_layer import ValidationResult
from app.services.chatbot.incident_graph import incident_graph
from app.services.chatbot.sfd_reasoning import sfd_reasoning

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# N3 System Prompt — injected into every LLM call
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# N3 Formatter Prompt — LLM acts as formatter ONLY, all reasoning pre-computed
# ─────────────────────────────────────────────────────────────────────────────
# ARCHITECTURE: Deterministic Core + LLM Formatter
#   Layers 1-6 (SFD/KB/State/Intent/Correlation/Validation) → STRUCTURED_RESULT
#   Layer 7 LLM receives ONLY the structured result — NO raw knowledge, NO re-reasoning
#
# Token budget: ~300 tokens system + ~400 tokens structured context = ~700 total
# vs previous: ~1800 tokens (system prompt reasoning + raw KB dump)

N3_SYSTEM_PROMPT = """You are an N3 formatter for BRASIL support.
You receive a FULLY pre-computed diagnostic result.

YOU MUST NOT:
- infer anything
- add any new root cause
- modify the provided root cause
- introduce any reasoning
- hallucinate
- mention JIRA

YOU MUST ONLY:
- rephrase for clarity
- structure the output
- keep it concise and technical
- respond ONLY IN FRENCH

If a field is empty → write "Non applicable"
If data is missing → DO NOT GUESS

FORMAT (strict):
## 🧠 Diagnostic
  {diagnostic}
## 🔍 Cause Racine [{cause_class}]
  {root_cause}
## ⚙️ Condition Bloquante
  {blocking_condition}
## ✅ Plan d'Action
  {resolution_steps}
## 📎 Sources
  {evidence_refs}
## 🤔 Hypothèse Alternative
  {devil_advocate}"""


# ─────────────────────────────────────────────────────────────────────────────
# Symptom → category mapping
# ─────────────────────────────────────────────────────────────────────────────

_SYMPTOM_KEYWORDS: Dict[str, List[str]] = {
    "data_inconsistency": [
        "fantôme", "orphelin", "incohérent", "désynchronisé", "désync",
        "absent dans brasil", "introuvable", "nd inconnu", "données incorrectes",
        "enregistrement résiduel",
    ],
    "constraint_violation": [
        "impossible", "bloqué", "interdit", "refusé", "violation",
        "contrainte", "dépendance", "lié", "en cours", "suppression impossible",
        "ne peut pas supprimer", "ne peut pas créer",
    ],
    "system_error": [
        "erreur", "exception", "crash", "timeout", "deadlock",
        "4002", "1300", "1002", "ora-", "psql", "échec", "failed",
        "AvailableNetworkResources", "BrasilInternalError",
    ],
    "state_lock": [
        "in_progress", "en cours", "verrouillé", "figé", "suspendu",
        "commande bloquée", "dossier bloqué", "ordre en attente",
    ],
}

_DEBUG_INTENTS = {"debug", "delete_equipment", "delete", "diagnose", "query"}


def detect_symptoms(text: str) -> List[str]:
    """Classify detected symptoms from user text."""
    text_lower = text.lower()
    found = []
    for category, keywords in _SYMPTOM_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            found.append(category)
    return found


# ─────────────────────────────────────────────────────────────────────────────
# Response types
# ─────────────────────────────────────────────────────────────────────────────

MODE_EXPERT  = "expert"
MODE_NATURAL = "natural"


@dataclass
class GeneratedResponse:
    text: str
    mode: str
    has_hypothesis: bool
    confidence: float
    follow_up_questions: List[str]
    summary_for_memory: str     # compressed summary stored in ConversationState

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "mode": self.mode,
            "has_hypothesis": self.has_hypothesis,
            "confidence": self.confidence,
            "follow_up_questions": self.follow_up_questions,
        }

    def to_compact_dict(
        self,
        correlation: Optional["CorrelationResult"] = None,
        devil_advocate: Optional[dict] = None,
    ) -> dict:
        """
        Minimal structured payload passed to the LLM formatter.
        Target: < 250 tokens total.
        Fields: diagnostic, root_cause, cause_class, blocking_condition,
                resolution (max 3 steps), confidence, evidence_refs, devil_advocate.
        """
        # ── Root cause + class ────────────────────────────────────────────
        root_cause = ""
        cause_class = "FR / Pattern"
        blocking: str = ""
        resolution: list = []
        evidence_refs: str = ""
        diagnostic: str = ""

        if correlation and correlation.top_hypothesis:
            h = correlation.top_hypothesis
            gr = correlation.graph_reasoning
            root_cause = (gr.root_cause.label if (gr and gr.root_cause) else h.root_cause)[:120]
            if gr and gr.blocking_constraints:
                cause_class = "SFD"
            elif any(w in root_cause.lower() for w in ("ghost", "orphan", "désync", "fantôme")):
                cause_class = "Data"
            elif any(w in root_cause.lower() for w in ("prérequis", "dépendance")):
                cause_class = "Dependency"
            # Blocking (1 line max)
            if correlation.sfd_violations:
                blocking = correlation.sfd_violations[0][:100]
            elif gr and gr.blocking_constraints:
                bc = gr.blocking_constraints[0]
                blocking = f"[{bc.metadata.get('rule_id','')}] {bc.label}"[:100]
            # Resolution (max 3 steps, 80 chars each)
            raw_actions = ([a.label for a in gr.recommended_actions[:3]] if (gr and gr.recommended_actions)
                           else h.recommended_actions[:3])
            resolution = [a[:80] for a in raw_actions]
            # Evidence (source IDs only)
            fr_refs = (gr.fr_references[:3] if gr and gr.fr_references else [])
            ev_types = list({e.source_type for e in h.evidence})
            parts = []
            if fr_refs:
                parts.append("FR: " + ", ".join(fr_refs))
            if ev_types:
                parts.append(", ".join(ev_types))
            evidence_refs = " | ".join(parts)[:120]
            diagnostic = f"{h.label} ({h.confidence:.0%})"[:100]
        else:
            diagnostic = "Insufficient evidence"
            root_cause = "Undetermined"
            resolution = ["Provide: equipment ID, error code, operation attempted"]

        return {
            "diagnostic": diagnostic,
            "root_cause": root_cause,
            "cause_class": cause_class,
            "blocking_condition": blocking or "None",
            "resolution": resolution,
            "confidence": round(self.confidence, 3),
            "evidence_refs": evidence_refs or "None",
            "devil_advocate": (
                f"{devil_advocate['hypothesis']} ({devil_advocate.get('confidence', 0):.0%})"
                if devil_advocate and devil_advocate.get("hypothesis") else "None"
            ),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Follow-up question bank (when evidence is insufficient)
# ─────────────────────────────────────────────────────────────────────────────

_FOLLOWUP_NO_EQUIPMENT = [
    "Quel est l'identifiant de l'équipement concerné ? (ex: DSLAM DSXXX999, ND 9 chiffres)",
    "S'agit-il d'un DSLAM, d'un nœud, d'une carte, ou d'un EPC ?",
]

_FOLLOWUP_NO_ERROR = [
    "Quel est le message d'erreur exact reçu dans les logs ou l'IHM ?",
    "Y a-t-il un code erreur visible dans la console ou le fichier de log ?",
]

_FOLLOWUP_NO_CONTEXT = [
    "Quelle opération essayez-vous d'effectuer ? (création, suppression, modification, provisionnement...)",
    "Quel est le dossier de réalisation concerné (NIFolderID ou ID Making File) ?",
    "Le problème est-il apparu suite à une maintenance récente ?",
]

_FOLLOWUP_RESOLUTION_PARTIAL = [
    "Quelle étape exactement n'a pas fonctionné ?",
    "Le message d'erreur a-t-il changé après l'action effectuée ?",
    "Avez-vous pu vérifier les compteurs dans la base BRASIL ?",
]


# ─────────────────────────────────────────────────────────────────────────────
# Resolution templates
# ─────────────────────────────────────────────────────────────────────────────

_RESOLUTION_TEMPLATE = """✅ **Problème résolu** — Résumé N3

**Équipement concerné** : {entity}
**Problème initial** : {problem}
**Actions réalisées** :
{actions}

**Résolution confirmée par** : {confirmed_by}
"""

_UNRESOLVED_TEMPLATE = """⚠️ **Problème non résolu** — Analyse complémentaire requise

**Symptôme persistant** : {symptom}
**Hypothèse initiale** : {hypothesis}

**Questions de diagnostic complémentaires** :
{questions}

Si le problème persiste, vérifiez :
- Les logs UMI-EPC et ConnectorCL pour la période concernée
- L'état des files d'attente de commandes dans t_making_files
- La cohérence des compteurs via FR 136b/136c
"""


# ─────────────────────────────────────────────────────────────────────────────
# Response Generator
# ─────────────────────────────────────────────────────────────────────────────

class ResponseGenerator:
    """
    Generates structured N3-level diagnostic responses.
    Does NOT call any LLM — purely rule/template-based.
    The LLM integration point is in the orchestrator (n3_chatbot_orchestrator.py)
    which calls this to build the structured prompt context.
    """

    def generate(
        self,
        intent: str,
        state: ConversationState,
        correlation: Optional[CorrelationResult],
        validation: Optional[ValidationResult],
        mode: str = MODE_NATURAL,
        extra_context: str = "",
    ) -> GeneratedResponse:
        """
        Generate a response based on intent + correlation + validation.
        """
        # ── Intent: resolution confirmed ──────────────────────────────────────
        if intent in ("confirm_resolution",):
            return self._build_resolution_response(state)

        # ── Intent: resolution denied ─────────────────────────────────────────
        if intent in ("deny_resolution",):
            return self._build_unresolved_response(state, correlation)

        # ── Validation failed — use safe response ─────────────────────────────
        if validation and not validation.passed and validation.safe_response:
            return GeneratedResponse(
                text=validation.safe_response,
                mode=mode,
                has_hypothesis=False,
                confidence=0.0,
                follow_up_questions=[],
                summary_for_memory=f"Validation failed: {validation.violations[0].message if validation.violations else 'unknown'}",
            )

        # ── No correlation result ─────────────────────────────────────────────
        if not correlation or not correlation.top_hypothesis:
            return self._build_insufficient_evidence_response(state, intent)

        # ── Build diagnostic response ─────────────────────────────────────────
        if mode == MODE_EXPERT:
            return self._build_expert_response(state, correlation, validation)
        else:
            return self._build_natural_response(state, correlation, validation)

    # ─────────────────────────────────────────────────────────────────────────

    def build_llm_context(
        self,
        intent: str,
        state: ConversationState,
        correlation: Optional[CorrelationResult],
        kb_context: str = "",      # kept for signature compat — NOT injected into LLM
        user_text: str = "",
        structured_result: Optional["GeneratedResponse"] = None,
        devil_advocate: Optional[dict] = None,
    ) -> str:
        """
        Build the LLM formatter prompt.

        Architecture: Deterministic Core + LLM Formatter
        ALL reasoning is pre-computed by layers 1-6.
        LLM receives ONLY the structured result — no raw KB, no re-reasoning.

        Token budget: ~700 tokens total (vs ~1800 previously)
        """
        lines: List[str] = [N3_SYSTEM_PROMPT, "━" * 55, "## RÉSULTAT PIPELINE — À FORMATER", "━" * 55]

        # ── Pre-computed context (deterministic, no re-reasoning needed) ─────
        primary = state.get_primary_equipment()
        entity_name = primary.name if primary else "Équipement non identifié"
        symptoms = detect_symptoms(user_text) if user_text else []  # single call

        lines.append(f"equipement: {entity_name}")
        lines.append(f"intent: {intent}")
        if symptoms:
            lines.append(f"symptomes_detectes: {', '.join(symptoms)}")

        # ── Structured result from correlation + validation (pre-computed) ───
        if correlation and correlation.top_hypothesis:
            h = correlation.top_hypothesis
            gr = correlation.graph_reasoning

            # Root cause (already classified by _build_expert_response logic)
            root_cause_label = gr.root_cause.label if (gr and gr.root_cause) else h.root_cause
            cause_type = "FR / Pattern incident"
            if gr and gr.blocking_constraints:
                cause_type = "SFD (contrainte système)"
            elif any(w in root_cause_label.lower() for w in ("ghost", "orphan", "désync", "fantôme")):
                cause_type = "Data (incohérence / donnée fantôme)"
            elif any(w in root_cause_label.lower() for w in ("prérequis", "dépendance")):
                cause_type = "Dépendance manquante"

            lines.append(f"\nresume_diagnostic: Hypothèse '{h.label}' — confiance {h.confidence:.0%}")
            lines.append(f"cause_racine: {root_cause_label}")
            lines.append(f"classe_cause: {cause_type}")
            lines.append(f"score_confiance: {h.confidence:.0%}")

            # Blocking conditions (pre-validated)
            blocking: List[str] = []
            if correlation.sfd_violations:
                blocking = correlation.sfd_violations[:3]
            elif gr and gr.blocking_constraints:
                blocking = [f"[{c.metadata.get('rule_id','')}] {c.label}" for c in gr.blocking_constraints[:2]]
            if blocking:
                lines.append("blocking_conditions:")
                for b in blocking:
                    lines.append(f"  - {b}")

            # Resolution steps (pre-computed by correlation)
            actions = ([a.label for a in gr.recommended_actions[:6]] if (gr and gr.recommended_actions)
                       else h.recommended_actions[:6])
            if actions:
                lines.append("resolution_steps:")
                for i, a in enumerate(actions, 1):
                    lines.append(f"  {i}. {a}")

            # Evidence references (source IDs only — no raw content)
            ev_sources = list({e.source_type for e in h.evidence})
            fr_refs = (gr.fr_references[:4] if gr and gr.fr_references else [])
            if ev_sources or fr_refs:
                refs: List[str] = []
                if fr_refs:
                    refs.append("FR: " + ", ".join(fr_refs))
                if ev_sources:
                    refs.append("Sources: " + ", ".join(ev_sources))
                lines.append(f"evidence_refs: {' | '.join(refs)}")

        else:
            lines.append("resume_diagnostic: Aucune hypothèse identifiée — preuves insuffisantes")
            lines.append("cause_racine: Non déterminée")
            lines.append("resolution_steps: Demander précisions (équipement, code erreur, opération)")

        # ── FR procedure steps — injected directly from best-matching FR evidence ─
        if correlation:
            fr_evidences = [
                e for h in correlation.hypotheses for e in h.evidence
                if e.source_type == "fr_document" and e.metadata.get("resolution")
            ]
            if not fr_evidences and correlation.top_hypothesis:
                fr_evidences = [
                    e for e in correlation.top_hypothesis.evidence
                    if e.source_type == "fr_document" and e.metadata.get("resolution")
                ]
            if fr_evidences:
                best_fr = fr_evidences[0]  # already sorted by confidence
                res_steps = best_fr.metadata.get("resolution", [])
                if res_steps:
                    lines.append("\nFR_PROCEDURE (étapes validées — à utiliser en priorité):")
                    for i, step in enumerate(res_steps[:5], 1):
                        lines.append(f"  {i}. {str(step)[:150]}")
                fr_id = best_fr.metadata.get("fr_id", "")
                if fr_id:
                    lines.append(f"fr_source: {fr_id} — {best_fr.metadata.get('fr_title', '')}")

        # ── Structured fallback text (always available if LLM fails) ────────
        if structured_result:
            lines.append("\n[FALLBACK_TEXT — utiliser si formatage impossible]")
            lines.append(structured_result.text[:600])

        # ── Devil's advocate (optional — pre-computed by orchestrator) ────────
        if devil_advocate and devil_advocate.get("hypothesis"):
            lines.append(f"\ndevil_advocate: {devil_advocate['hypothesis']} ({devil_advocate.get('confidence', 0):.0%})")

        return "\n".join(lines)

    # ─────────────────────────────────────────────────────────────────────────
    # Response builders
    # ─────────────────────────────────────────────────────────────────────────

    def _build_expert_response(
        self,
        state: ConversationState,
        correlation: CorrelationResult,
        validation: Optional[ValidationResult],
    ) -> GeneratedResponse:
        h = correlation.top_hypothesis
        primary = state.get_primary_equipment()
        entity_name = primary.name if primary else "Équipement non identifié"
        gr = correlation.graph_reasoning

        actions_block = self._format_actions_with_fr(
            actions=(
                [act.label for act in gr.recommended_actions[:6]] if (gr and gr.recommended_actions)
                else h.recommended_actions[:6]
            ),
            fr_references=gr.fr_references if gr else None,
            evidence=h.evidence,
        )
        evidence_block = self._format_evidence(h)
        warning_block = ""
        if validation and validation.warning_message:
            warning_block = f"\n{validation.warning_message}"

        # Graph-based causal chain
        graph_section = ""
        if gr and gr.causal_chain and len(gr.causal_chain) > 1:
            chain_lines = ["\n**Chaîne causale (graphe d'incidents):**"]
            for step in gr.causal_chain[1:5]:
                chain_lines.append(step.explain())
            graph_section = "\n".join(chain_lines)

        # SFD constraints section
        sfd_section = ""
        if gr and gr.blocking_constraints:
            sfd_lines = ["\n**Règles SFD applicables:**"]
            for cstr in gr.blocking_constraints[:3]:
                rule_id = cstr.metadata.get("rule_id", "")
                sfd_lines.append(f"  [{rule_id}] {cstr.label}")
                sfd_lines.append(f"    → {cstr.description}")
            sfd_section = "\n".join(sfd_lines)

        fr_section = ""
        if gr and gr.fr_references:
            fr_section = f"\n**Références FR:** {', '.join(gr.fr_references)}"

        root_cause_label = gr.root_cause.label if (gr and gr.root_cause) else h.root_cause

        # ── Classify root cause type ───────────────────────────────────────
        cause_type = "FR / Pattern incident"
        if gr and gr.blocking_constraints:
            cause_type = "SFD (contrainte système)"
        elif "ghost" in root_cause_label.lower() or "orphan" in root_cause_label.lower() or "désync" in root_cause_label.lower():
            cause_type = "Data (incohérence / donnée fantôme)"
        elif "prérequis" in root_cause_label.lower() or "dépendance" in root_cause_label.lower():
            cause_type = "Dépendance manquante"

        # ── Section 3 — Evidence ───────────────────────────────────────────
        evidence_block = self._format_evidence(h)
        sfd_rule_block = ""
        if gr and gr.blocking_constraints:
            sfd_rules_lines = []
            for cstr in gr.blocking_constraints[:3]:
                rule_id = cstr.metadata.get("rule_id", "")
                sfd_rules_lines.append(f"  [{rule_id}] {cstr.label}: {cstr.description}")
            sfd_rule_block = "\n**Règles SFD (source de vérité):**\n" + "\n".join(sfd_rules_lines)

        fr_section = ""
        if gr and gr.fr_references:
            fr_section = f"\n**Références FR:** {', '.join(gr.fr_references)}"

        # ── Section 4 — Why it fails ───────────────────────────────────────
        blocking_section = ""
        if correlation.sfd_violations:
            blocking_section = (
                "\n## ⚙️ Pourquoi l'opération échoue\n"
                + "\n".join(f"  - {v}" for v in correlation.sfd_violations)
            )
        elif gr and gr.blocking_constraints:
            bc = gr.blocking_constraints[0]
            blocking_section = (
                f"\n## ⚙️ Condition bloquante\n"
                f"  Contrainte SFD [{bc.metadata.get('rule_id', '')}] : {bc.label}\n"
                f"  _{bc.description}_"
            )

        warning_block = ""
        if validation and validation.warning_message:
            warning_block = f"\n{validation.warning_message}"

        text = f"""## 🧠 Résumé Diagnostic — {entity_name}

**Hypothèse** : {h.label} | **Confiance** : {h.confidence:.0%}
**Intents détectés** : {h.id}{graph_section}

## 🔍 Cause Racine
**Cause** : {root_cause_label}
**Classe** : `{cause_type}`

## 🔗 Preuves
{evidence_block}{sfd_rule_block}{fr_section}{blocking_section}

## ✅ Étapes de Résolution
{actions_block}{warning_block}"""

        if correlation.sfd_violations:
            text += "\n\n⚠️ **BLOQUÉ par SFD** :\n" + "\n".join(
                f"  - {v}" for v in correlation.sfd_violations
            )

        # Entity tree
        entity_tree = state.get_entity_tree()
        if entity_tree and entity_tree != "(no entity hierarchy)":
            text += f"\n\n**Hiérarchie entités:**\n{entity_tree}"

        follow_ups = self._build_follow_up_questions(state, h)
        return GeneratedResponse(
            text=text,
            mode=MODE_EXPERT,
            has_hypothesis=True,
            confidence=h.confidence,
            follow_up_questions=follow_ups,
            summary_for_memory=f"Hypothesis: {h.label} | Cause: {root_cause_label[:50]}",
        )

    def _build_natural_response(
        self,
        state: ConversationState,
        correlation: CorrelationResult,
        validation: Optional[ValidationResult],
    ) -> GeneratedResponse:
        h = correlation.top_hypothesis
        primary = state.get_primary_equipment()
        entity_name = primary.name if primary else "l'équipement"
        gr = correlation.graph_reasoning

        # SFD block — use full simulation narrative
        if correlation.sfd_violations:
            if primary:
                simulation = sfd_reasoning.simulate_operation("DELETE", primary.name, state)
                text = simulation.narrative
            else:
                sfd_reason = correlation.sfd_violations[0]
                text = (
                    f"⚠️ Je ne peux pas effectuer cette opération sur **{entity_name}**.\n\n"
                    f"{sfd_reason}\n\n"
                    f"Consultez la documentation FR correspondante pour les prérequis."
                )
            return GeneratedResponse(
                text=text,
                mode=MODE_NATURAL,
                has_hypothesis=True,
                confidence=h.confidence,
                follow_up_questions=[],
                summary_for_memory=f"SFD block on {entity_name}",
            )

        # Build causal chain section if graph reasoning available
        causal_section = ""
        if gr and gr.root_cause:
            causal_section = (
                f"\n\n**Analyse causale :**\n"
                f"{gr.explanation}"
            )

        actions_summary = h.recommended_actions[:4]
        # Override with graph actions if richer
        if gr and gr.recommended_actions:
            actions_summary = [a.label for a in gr.recommended_actions[:5]]

        actions_text = self._format_actions_with_fr(
            actions=actions_summary,
            fr_references=gr.fr_references if gr else None,
            evidence=h.evidence,
        )
        evidence_refs = self._format_evidence_brief(h)

        # SFD rule explanation if constraints present
        sfd_section = ""
        if gr and gr.blocking_constraints:
            cstr = gr.blocking_constraints[0]
            rule_id = cstr.metadata.get("rule_id", "")
            sfd_section = (
                f"\n\n**Règle SFD [{rule_id}]:** {cstr.label}\n"
                f"_{cstr.description}_"
            )

        # FR references
        fr_section = ""
        if gr and gr.fr_references:
            fr_section = f"\n\n**Références FR:** {', '.join(gr.fr_references)}"

        text = (
            f"Pour **{entity_name}**, le problème identifié est : **{h.label}**.\n\n"
            f"*{h.root_cause}*"
            f"{causal_section}"
            f"{sfd_section}"
            f"\n\n**Plan d'action recommandé :**\n{actions_text}"
            f"{fr_section}"
        )

        if evidence_refs:
            text += f"\n\n📎 Référence : {evidence_refs}"

        if validation and validation.warning_message:
            text += validation.warning_message

        follow_ups = self._build_follow_up_questions(state, h)
        return GeneratedResponse(
            text=text,
            mode=MODE_NATURAL,
            has_hypothesis=True,
            confidence=h.confidence,
            follow_up_questions=follow_ups,
            summary_for_memory=f"Diagnosed: {h.label}",
        )

    def _build_resolution_response(self, state: ConversationState) -> GeneratedResponse:
        primary = state.get_primary_equipment()
        entity_name = primary.name if primary else "l'équipement"

        # Gather actual actions from conversation (filter out questions)
        assistant_turns = [t for t in state.history if t.role == "assistant"]
        actions = []
        for t in assistant_turns[-3:]:
            # Extract numbered actions — skip lines ending with '?' (questions)
            for line in t.content.split("\n"):
                stripped = line.strip()
                if (re.match(r"\s*\d+\.\s+", line)
                        and not stripped.endswith("?")
                        and "Quel" not in stripped
                        and "Avez" not in stripped
                        and "Pouvez" not in stripped):
                    actions.append(stripped)

        actions_block = "\n".join(actions[:5]) if actions else "  - Actions de diagnostic effectuées"
        summary_data = state.summary()
        problem = (
            summary_data.get("last_intent", "") or
            f"{summary_data.get('entities_count', 0)} entité(s) traitée(s)"
        ) or "Problème de support N3 BRASIL"

        text = _RESOLUTION_TEMPLATE.format(
            entity=entity_name,
            problem=problem[:150],
            actions=actions_block,
            confirmed_by="l'opérateur",
        )

        # Mark resolution in state
        state.set_resolution(True)

        return GeneratedResponse(
            text=text,
            mode=MODE_NATURAL,
            has_hypothesis=True,
            confidence=1.0,
            follow_up_questions=[],
            summary_for_memory=f"RESOLVED: {entity_name}",
        )

    def _build_unresolved_response(
        self,
        state: ConversationState,
        correlation: Optional[CorrelationResult],
    ) -> GeneratedResponse:
        primary = state.get_primary_equipment()
        entity_name = primary.name if primary else "l'équipement"
        hypothesis = correlation.top_hypothesis.label if (correlation and correlation.top_hypothesis) else "Non déterminé"

        # Build follow-up questions based on context
        questions: List[str] = []
        if not state.entities:
            questions.extend(_FOLLOWUP_NO_EQUIPMENT[:2])
        questions.extend(_FOLLOWUP_RESOLUTION_PARTIAL[:2])

        questions_text = "\n".join(f"  {i+1}. {q}" for i, q in enumerate(questions[:4]))

        last_msg = state.history[-1].content if state.history else "Problème non spécifié"
        text = _UNRESOLVED_TEMPLATE.format(
            symptom=last_msg[:120],
            hypothesis=hypothesis,
            questions=questions_text,
        )

        state.set_resolution(False)
        return GeneratedResponse(
            text=text,
            mode=MODE_NATURAL,
            has_hypothesis=correlation is not None and correlation.top_hypothesis is not None,
            confidence=0.0,
            follow_up_questions=questions,
            summary_for_memory=f"UNRESOLVED: {entity_name} — {hypothesis}",
        )

    def _build_insufficient_evidence_response(
        self, state: ConversationState, intent: str
    ) -> GeneratedResponse:
        """No correlation found — ask clarifying questions."""
        questions: List[str] = []
        if not any(e.type.value in ("DSLAM", "EQUIPMENT", "NODE") for e in state.entities.values()):
            questions.extend(_FOLLOWUP_NO_EQUIPMENT)
        if not any(e.type.value == "ERROR_CODE" for e in state.entities.values()):
            questions.extend(_FOLLOWUP_NO_ERROR[:1])
        questions.extend(_FOLLOWUP_NO_CONTEXT[:1])

        questions_text = "\n".join(f"  {i+1}. {q}" for i, q in enumerate(questions[:3]))
        text = (
            "Je n'ai pas pu identifier de pattern correspondant dans la base de connaissances BRASIL.\n\n"
            "Pour affiner le diagnostic, pourriez-vous préciser :\n"
            f"{questions_text}"
        )
        return GeneratedResponse(
            text=text,
            mode=MODE_NATURAL,
            has_hypothesis=False,
            confidence=0.0,
            follow_up_questions=questions,
            summary_for_memory="Insufficient evidence — asked for clarification",
        )

    # ─────────────────────────────────────────────────────────────────────────────
    # Formatting helpers
    # ─────────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _format_actions_with_fr(
        actions: List[str],
        fr_references: Optional[List[str]] = None,
        evidence: Optional[list] = None,
        max_actions: int = 6,
    ) -> str:
        """
        Format a numbered action list with FR source annotations.

        For each action, tries to find the matching FR reference:
        - From the action text itself (e.g. "apply FR 136b")
        - From fr_references list (distributed evenly)
        - Falls back to no annotation

        Returns a markdown-formatted numbered list.
        """
        import re as _re

        # Build FR pool from both the action text and explicit fr_references
        fr_pool = list(fr_references or [])

        # Also extract FR numbers embedded in evidence snippets
        if evidence:
            for ev in evidence:
                snippet = ev.snippet if hasattr(ev, "snippet") else str(ev)
                for match in _re.findall(r'\bFR\s*[\d]+[a-zA-Z]*\b', snippet, _re.IGNORECASE):
                    clean = match.strip().upper().replace(" ", " ")
                    if clean not in fr_pool:
                        fr_pool.append(clean)

        lines = []
        fr_pool_idx = 0  # rolling index into fr_pool for actions without inline FR

        for i, action in enumerate(actions[:max_actions]):
            # Try to find FR in the action text itself
            inline_fr = _re.findall(r'\bFR\s*[\d]+[a-zA-Z]*\b', action, _re.IGNORECASE)
            if inline_fr:
                # Normalize and keep as-is (already in text)
                fr_tag = f" `[{inline_fr[0].strip().upper()}]`"
            elif fr_pool and fr_pool_idx < len(fr_pool):
                # Attach next available FR from pool
                fr_tag = f" `[{fr_pool[fr_pool_idx].strip().upper()}]`"
                fr_pool_idx += 1
            else:
                fr_tag = ""

            lines.append(f"  {i+1}. {action}{fr_tag}")

        return "\n".join(lines)
        if not h.evidence:
            return "  - Aucune source documentaire retrouvée"
        lines = []
        for ev in h.evidence[:4]:
            src = ev.source_type.replace("_", " ").upper()
            lines.append(f"  - [{src}] {ev.snippet[:80]}")
        return "\n".join(lines)

    @staticmethod
    def _format_evidence_brief(h: CorrelationHypothesis) -> str:
        sources = {ev.source_type for ev in h.evidence}
        if not sources:
            return ""
        labels = []
        if "incident" in sources:
            labels.append("incidents historiques")
        if "fr_document" in sources:
            labels.append("documentation FR")
        if "log_pattern" in sources:
            labels.append("patterns de logs")
        return ", ".join(labels)

    @staticmethod
    def _build_follow_up_questions(
        state: ConversationState, h: CorrelationHypothesis
    ) -> List[str]:
        """Generate targeted follow-up questions based on hypothesis."""
        questions = []
        if h.confidence < 0.6:
            questions.append("Pouvez-vous confirmer le message d'erreur exact ?")
        if "PORT" in h.related_entities and not any(
            e.type.value == "PORT" for e in state.entities.values()
        ):
            questions.append("Avez-vous le numéro de port ou de carte concerné ?")
        if h.id in ("HYP-004", "HYP-005"):
            questions.append("Quel est l'identifiant exact du dossier de réalisation (NIFolderID) ?")
        return questions[:2]


# Singleton
response_generator = ResponseGenerator()
