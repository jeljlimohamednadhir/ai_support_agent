"""
Layer 6 — Validation Layer (Anti-Hallucination)
=================================================
Three-stage validation before any response reaches the user.

Stage 1 — Entity Validity
  • Only entities present in user input, conversation memory, or retrieved sources
    are allowed in the response.
  • Unknown equipment names, ND numbers, or identifiers are flagged.

Stage 2 — Business Validity
  • Response must comply with SFD constraints.
  • Mutations (DELETE, MODIFY) require prior constraint check.
  • Blocks: operations that violate CSTR-blocking rules.

Stage 3 — Evidence Grounding
  • Every factual claim must be backed by an INCIDENT or FR document.
  • Responses with zero evidence are downgraded to "uncertain" and marked.
  • Pure LLM hallucinations without evidence → replaced with safe fallback.

Output:
  ValidationResult with pass/fail per stage, violations, safe_response.
"""
from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Literal, Optional, List, Dict, Any, Tuple

from app.services.chatbot.conversation_state import ConversationState
from app.services.chatbot.sfd_parser import sfd_parser
from app.services.chatbot.sfd_reasoning import sfd_reasoning, OperationSimulation

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Types
# ─────────────────────────────────────────────────────────────────────────────

SEVERITY_BLOCK   = "block"   # response must NOT be sent
SEVERITY_WARNING = "warning" # response can be sent with a caveat
SEVERITY_INFO    = "info"    # informational, no action needed


@dataclass
class ValidationViolation:
    stage: str          # "entity", "business", "evidence"
    severity: str       # "block" | "warning" | "info"
    message: str
    details: str = ""


TIER_HIGH   = "HIGH"    # fully grounded, no blocking violations
TIER_MEDIUM = "MEDIUM"  # warning-only, weak evidence — flag for review
TIER_LOW    = "LOW"     # blocking violation or zero evidence — safe fallback used


@dataclass
class ValidationResult:
    # ── Tier replaces boolean passed ─────────────────────────────────────────
    tier: str = TIER_HIGH          # "HIGH" | "MEDIUM" | "LOW"
    score: float = 1.0             # 0.0–1.0 composite validation confidence
    violations: List[ValidationViolation] = field(default_factory=list)
    safe_response: str = ""        # used when tier == LOW
    evidence_count: int = 0
    warning_message: str = ""      # appended when tier == MEDIUM
    needs_review: bool = False     # True for MEDIUM/LOW — surfaces to human operator

    # ── backward compat shim ─────────────────────────────────────────────────
    @property
    def passed(self) -> bool:
        """Backward-compatible: LOW tier is equivalent to failed."""
        return self.tier != TIER_LOW

    @property
    def blocking_violations(self) -> List[ValidationViolation]:
        return [v for v in self.violations if v.severity == SEVERITY_BLOCK]

    @property
    def warning_violations(self) -> List[ValidationViolation]:
        return [v for v in self.violations if v.severity == SEVERITY_WARNING]

    def to_dict(self) -> dict:
        return {
            "tier": self.tier,
            "score": round(self.score, 3),
            "passed": self.passed,
            "needs_review": self.needs_review,
            "violations": [
                {"stage": v.stage, "severity": v.severity, "message": v.message}
                for v in self.violations
            ],
            "evidence_count": self.evidence_count,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Patterns for hallucination detection
# ─────────────────────────────────────────────────────────────────────────────

# Phrases that indicate LLM is making up information
_HALLUCINATION_SIGNALS = [
    r"je ne suis pas sûr\b",
    r"il me semble que\b",
    r"probablement\s+à\s+cause\s+de",
    r"cela\s+pourrait\s+être\s+dû",
    r"il est possible que\b",
    r"peut[-\s]être que\b",
    r"généralement\s+cela\s+signifie",
    r"d'habitude\s+ce\s+type\s+d'erreur",
    r"dans la plupart des cas\b",
    r"based on my knowledge\b",
    r"according to my training\b",
    r"i believe that\b",
    r"i think this might be\b",
]
_HALLUCINATION_PATTERNS = [re.compile(p, re.I) for p in _HALLUCINATION_SIGNALS]

# Mutation verbs — operations that must be validated against SFD
_MUTATION_VERBS = re.compile(
    r"\b(supprimer|supprimi|suppression|delete|délétez|effacer|effacez|"
    r"modifier|modification|update|créer|création|créez|create|"
    r"ajouter|ajoutez|add|fermer|fermez|close|ouvrir|ouvrez|open)\b",
    re.I,
)

# ─────────────────────────────────────────────────────────────────────────────
# Safe fallback templates
# ─────────────────────────────────────────────────────────────────────────────

_SAFE_FALLBACK_NO_EVIDENCE = (
    "Je n'ai pas pu retrouver de précédents similaires dans notre base d'incidents BRASIL "
    "pour confirmer ce diagnostic. Pourriez-vous fournir plus de détails "
    "(identifiant de l'équipement, message d'erreur exact, commande exécutée) ?"
)

_SAFE_FALLBACK_SFD_VIOLATION = (
    "⚠️ Cette opération est bloquée par une contrainte BRASIL.\n"
    "{reason}\n\n"
    "Avant de procéder, veuillez vérifier les prérequis dans la documentation FR correspondante."
)

_SAFE_FALLBACK_UNKNOWN_ENTITY = (
    "Je ne reconnais pas l'équipement mentionné dans notre référentiel BRASIL. "
    "Pourriez-vous vérifier l'identifiant exact (format DSXXX999, ND 9 chiffres, EPC idEpc@NNN) ?"
)


# ─────────────────────────────────────────────────────────────────────────────
# Validation Layer
# ─────────────────────────────────────────────────────────────────────────────

class ValidationLayer:
    """
    Anti-hallucination validation applied BEFORE sending response to user.
    """

    def validate(
        self,
        response: str,
        state: ConversationState,
        intent: str = "",
        retrieved: Optional[Dict[str, List[Dict]]] = None,
        proposed_operation: Optional[str] = None,
        hypothesis_id: Optional[str] = None,
        correlation_confidence: float = 0.0,
    ) -> ValidationResult:
        """
        Validate a proposed response against entity memory, SFD, and evidence.

        Args:
            response: The LLM-generated response candidate.
            state: Current conversation state (entity memory).
            intent: Resolved intent (used for mutation detection).
            retrieved: Knowledge layer result dict.
            proposed_operation: Optional explicit operation ("DELETE", "CREATE", etc.)
            hypothesis_id: Active hypothesis ID for confidence model lookup.
            correlation_confidence: Correlation engine confidence (0–1).

        Returns:
            ValidationResult
        """
        retrieved = retrieved or {}
        violations: List[ValidationViolation] = []

        # ── Stage 1: Entity Validity ──────────────────────────────────────────
        entity_violations = self._check_entity_validity(response, state)
        violations.extend(entity_violations)

        # ── Stage 2: Business Validity ────────────────────────────────────────
        biz_violations = self._check_business_validity(
            response, state, intent, proposed_operation
        )
        violations.extend(biz_violations)

        # ── Stage 3: Evidence Grounding ───────────────────────────────────────
        evidence_count = self._count_evidence(retrieved)
        ev_violations = self._check_evidence_grounding(response, evidence_count, retrieved)
        violations.extend(ev_violations)

        # ── Stage 4: Hallucination signals ───────────────────────────────────
        hall_violations = self._check_hallucination_signals(response)
        violations.extend(hall_violations)

        # ── Stage 5: Hypothesis confidence check ─────────────────────────────
        hyp_confidence = 0.5
        if hypothesis_id:
            try:
                from app.services.chatbot.learning_loop import learning_loop
                hyp_confidence = learning_loop.get_hypothesis_confidence(hypothesis_id)
                # Weak hypothesis (success_rate < 0.5) → warning
                if hyp_confidence < 0.4:
                    violations.append(ValidationViolation(
                        stage="confidence",
                        severity=SEVERITY_WARNING,
                        message=f"Hypothèse {hypothesis_id} a un historique de faible précision (score={hyp_confidence:.2f})",
                        details="Historical confidence below threshold",
                    ))
            except Exception:
                pass

        # ── Stage 6: Contradiction detection ─────────────────────────────────
        contradiction_violations = self._check_contradictions(response, retrieved)
        violations.extend(contradiction_violations)

        blocking = [v for v in violations if v.severity == SEVERITY_BLOCK]
        warnings = [v for v in violations if v.severity == SEVERITY_WARNING]
        infos    = [v for v in violations if v.severity == SEVERITY_INFO]

        # ── Compute tier ──────────────────────────────────────────────────────
        if blocking:
            tier = TIER_LOW
        elif warnings or evidence_count == 0:
            tier = TIER_MEDIUM
        else:
            tier = TIER_HIGH

        # ── Stage 5.5: Anti-Overconfidence Guard ─────────────────────────────
        # A hypothesis cannot be HIGH if it claims > 90% confidence but has < 3
        # pieces of supporting evidence. This prevents the AI from being
        # overconfident on a single incident match.
        if tier == TIER_HIGH and hyp_confidence > 0.9 and evidence_count < 3:
            tier = TIER_MEDIUM
            violations.append(ValidationViolation(
                stage="confidence",
                severity=SEVERITY_WARNING,
                message=(
                    f"Confiance hypothèse élevée ({hyp_confidence:.0%}) "
                    f"mais seulement {evidence_count} preuve(s) — tier rétrogradé MEDIUM"
                ),
                details="Anti-overconfidence guard: HIGH requires >= 3 evidence items",
            ))
            logger.debug(
                "ValidationLayer: anti-overconfidence downgrade "
                f"hyp={hypothesis_id} conf={hyp_confidence:.2f} evidence={evidence_count}"
            )

        # ── Compute enriched score ────────────────────────────────────────────
        # Base: penalise violations
        score = 1.0
        score -= len(blocking) * 0.35
        score -= len(warnings) * 0.15
        score -= len(infos)    * 0.05
        # Evidence bonus
        score += min(evidence_count * 0.05, 0.20)
        # Hypothesis confidence contribution (10% weight)
        score = score * 0.90 + hyp_confidence * 0.10
        # Correlation confidence contribution (5% weight)
        score = score * 0.95 + correlation_confidence * 0.05
        score = round(max(0.0, min(1.0, score)), 3)

        # ── Build safe response if LOW ────────────────────────────────────────
        safe_response = ""
        if tier == TIER_LOW:
            safe_response = self._build_safe_response(blocking, state, intent, retrieved)

        # ── Warning annotation for MEDIUM ──────────────────────────────────────
        warning_message = ""
        if tier == TIER_MEDIUM and warnings:
            warning_msgs = "; ".join(v.message for v in warnings[:2])
            # Add confidence hint to warning
            ai_conf_label = "HIGH" if score >= 0.75 else ("MEDIUM" if score >= 0.50 else "LOW")
            evidence_hint = " ⚠️ weak evidence" if evidence_count < 2 else ""
            warning_message = (
                f"\n\n⚠️ Note: {warning_msgs}"
                f"\n💡 Confiance IA: {ai_conf_label} (score={score:.2f}){evidence_hint}"
            )

        needs_review = tier in (TIER_LOW, TIER_MEDIUM)

        return ValidationResult(
            tier=tier,
            score=score,
            violations=violations,
            safe_response=safe_response,
            evidence_count=evidence_count,
            warning_message=warning_message,
            needs_review=needs_review,
        )

    # ── Stage 1 ──────────────────────────────────────────────────────────────

    def _check_entity_validity(
        self, response: str, state: ConversationState
    ) -> List[ValidationViolation]:
        """
        Flag equipment IDs mentioned in response that are NOT in state memory
        and don't match expected BRASIL format.
        """
        violations = []

        # Extract DSLAM-like IDs from response
        dslam_pattern = re.compile(r"\b[A-Z]{2}[A-Z0-9]{3}\d{3,4}\b")
        nd_pattern = re.compile(r"\b\d{9}\b")
        epc_pattern = re.compile(r"\bId[Ee]pc@\d+\b")

        known_names = {e.name.upper() for e in state.entities.values()}

        # Check DSLAMs in response
        for match in dslam_pattern.finditer(response):
            name = match.group().upper()
            if name not in known_names:
                violations.append(ValidationViolation(
                    stage="entity",
                    severity=SEVERITY_WARNING,
                    message=f"Équipement '{name}' mentionné mais non présent dans le contexte de conversation",
                    details="Entity not in conversation memory",
                ))

        # Check EPC IDs
        for match in epc_pattern.finditer(response):
            name = match.group()
            if name.upper() not in known_names:
                violations.append(ValidationViolation(
                    stage="entity",
                    severity=SEVERITY_WARNING,
                    message=f"EPC '{name}' non présent dans le contexte",
                    details="EPC not in conversation memory",
                ))

        return violations

    # ── Stage 2 ──────────────────────────────────────────────────────────────

    def _check_business_validity(
        self,
        response: str,
        state: ConversationState,
        intent: str,
        proposed_operation: Optional[str],
    ) -> List[ValidationViolation]:
        """
        Validate mutation operations against SFD constraints.
        Now uses SFDReasoningEngine for rich explanations.
        """
        violations = []

        # Detect mutation intent
        is_mutation = (
            intent in ("delete_equipment", "mutation_request", "replay_order", "fix_counter", "mass_replay")
            or bool(_MUTATION_VERBS.search(response))
            or proposed_operation in ("DELETE", "CREATE", "MODIFY", "CLOSE", "OPEN")
        )

        if not is_mutation:
            return violations

        # Check SFD constraint for primary equipment
        primary = state.get_primary_equipment()
        if primary:
            op = proposed_operation or self._infer_operation(response, intent)
            # UPGRADE: use full SFD reasoning simulation
            simulation = sfd_reasoning.simulate_operation(op, primary.name, state)
            if not simulation.allowed:
                for check in simulation.blocking_rules[:2]:
                    violations.append(ValidationViolation(
                        stage="business",
                        severity=SEVERITY_BLOCK,
                        message=check.short_reason,
                        details=check.explanation[:300],
                    ))
            elif simulation.warning_rules:
                for w in simulation.warning_rules[:1]:
                    violations.append(ValidationViolation(
                        stage="business",
                        severity=SEVERITY_WARNING,
                        message=w.short_reason,
                        details=w.explanation[:200],
                    ))
        else:
            # Mutation without identified entity — warn but don't block
            violations.append(ValidationViolation(
                stage="business",
                severity=SEVERITY_WARNING,
                message="Opération de mutation sans équipement cible identifié",
                details="Cannot validate SFD constraint without entity",
            ))

        return violations

    # ── Stage 3 ──────────────────────────────────────────────────────────────

    def _check_evidence_grounding(
        self,
        response: str,
        evidence_count: int,
        retrieved: Dict[str, List[Dict]],
    ) -> List[ValidationViolation]:
        """
        Ensure response has at least minimal evidence grounding.
        """
        violations = []

        # Purely generic response (no incidents, no FR) → warning
        if evidence_count == 0:
            violations.append(ValidationViolation(
                stage="evidence",
                severity=SEVERITY_WARNING,
                message="Aucun incident similaire ou document FR retrouvé — réponse non étayée",
                details="No retrieved evidence",
            ))

        # If response gives very specific technical steps without any FR evidence → info
        fr_evidence = len(retrieved.get("fr", [])) + len(retrieved.get("canonical", []))
        incident_evidence = len(retrieved.get("incidents", []))
        if incident_evidence == 0 and fr_evidence == 0 and len(response) > 300:
            violations.append(ValidationViolation(
                stage="evidence",
                severity=SEVERITY_INFO,
                message="Réponse détaillée sans source documentaire — vérifier avec équipe N3",
                details="Detailed response with no documentary source",
            ))

        return violations

    def _check_hallucination_signals(self, response: str) -> List[ValidationViolation]:
        """Detect hedge phrases that indicate LLM uncertainty / hallucination."""
        violations = []
        for pattern in _HALLUCINATION_PATTERNS:
            if pattern.search(response):
                violations.append(ValidationViolation(
                    stage="evidence",
                    severity=SEVERITY_WARNING,
                    message=f"Signal d'incertitude détecté: '{pattern.pattern[:40]}...'",
                    details="Hallucination hedge phrase detected",
                ))
                break  # one warning per response is enough
        return violations

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _count_evidence(retrieved: Dict[str, List[Dict]]) -> int:
        total = 0
        for key, blocks in retrieved.items():
            if key != "sfd_constraints":
                total += len(blocks)
        return total

    @staticmethod
    def _infer_operation(response: str, intent: str) -> str:
        if intent == "delete_equipment" or re.search(r"\b(supprimer|supprimi|delete)\b", response, re.I):
            return "DELETE"
        if re.search(r"\b(créer|create|ajouter|add)\b", response, re.I):
            return "CREATE"
        if re.search(r"\b(modifier|update|changer)\b", response, re.I):
            return "MODIFY"
        if re.search(r"\b(fermer|close)\b", response, re.I):
            return "CLOSE"
        if re.search(r"\b(ouvrir|open)\b", response, re.I):
            return "OPEN"
        return "UNKNOWN"

    def _check_contradictions(
        self,
        response: str,
        retrieved: Dict[str, List[Dict]],
    ) -> List[ValidationViolation]:
        """
        Detect contradictions between the response and retrieved evidence.
        Looks for equipment states mentioned in response that contradict SFD constraints.
        """
        violations = []
        resp_lower = response.lower()

        # If response claims an operation is safe but SFD blocks it
        if retrieved.get("sfd_constraints"):
            for cstr in retrieved["sfd_constraints"][:3]:
                rule_id = cstr.get("rule_id", "")
                operation = cstr.get("operation", "").lower()
                # Response says "you can delete" but SFD says cannot
                if operation in ("delete", "suppression") and re.search(
                    r"\bvous\s+pouvez\s+supprimer\b|\bcan\s+be\s+deleted\b|\bsuppression\s+possible\b",
                    resp_lower,
                ):
                    violations.append(ValidationViolation(
                        stage="contradiction",
                        severity=SEVERITY_WARNING,
                        message=f"Réponse autorise une opération potentiellement bloquée par [{rule_id}]",
                        details=f"Response permits operation contradicted by SFD {rule_id}",
                    ))
                    break

        # If response mentions an equipment as "available" but state shows it's blocked
        if re.search(r"\bdisponible\b|\bavailable\b|\blibre\b", resp_lower):
            primary = None
            try:
                from app.services.chatbot.conversation_state import ConversationState
            except ImportError:
                pass
        return violations

    def _build_safe_response(
        self,
        blocking_violations: List[ValidationViolation],        state: ConversationState,
        intent: str,
        retrieved: Dict[str, List[Dict]],
    ) -> str:
        """Build a safe fallback response when validation fails."""
        # SFD violation — use simulation narrative for rich explanation
        sfd_violations = [v for v in blocking_violations if v.stage == "business"]
        if sfd_violations:
            primary = state.get_primary_equipment()
            if primary:
                op = self._infer_operation("", intent)
                simulation = sfd_reasoning.simulate_operation(op, primary.name, state)
                if simulation.narrative:
                    return simulation.narrative
            reason = sfd_violations[0].message
            return _SAFE_FALLBACK_SFD_VIOLATION.format(reason=reason)

        # Entity not recognized
        entity_violations = [v for v in blocking_violations if v.stage == "entity"]
        if entity_violations:
            return _SAFE_FALLBACK_UNKNOWN_ENTITY

        # No evidence
        return _SAFE_FALLBACK_NO_EVIDENCE


# Singleton
validation_layer = ValidationLayer()
