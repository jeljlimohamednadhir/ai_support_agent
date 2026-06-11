"""
SFD Reasoning Engine
======================
Upgrades SFD usage from validation-only to full reasoning engine.

Capabilities:
  1. enforce_constraint()   — check if operation violates SFD rule
  2. explain_constraint()   — natural-language explanation of WHY a rule exists
  3. simulate_operation()   — what would happen if operation is attempted
  4. get_resolution_steps() — step-by-step path to make operation valid
  5. check_preconditions()  — list all conditions that must be true before an op

BRASIL SFD rules are encoded both from brasil_constraints.json
and from the static knowledge in incident_graph.py.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple, Any

from app.services.chatbot.sfd_parser import sfd_parser, SFDConstraint
from app.services.chatbot.conversation_state import ConversationState, EntityType


# ─────────────────────────────────────────────────────────────────────────────
# Result types
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ConstraintCheck:
    rule_id: str
    passed: bool
    severity: str                 # "blocking" | "warning"
    short_reason: str             # one-liner
    explanation: str              # detailed N3-level explanation
    resolution_steps: List[str]   # how to make the check pass
    fr_reference: str = ""
    simulated_outcome: str = ""   # what would happen if violated


@dataclass
class OperationSimulation:
    operation: str
    entity_name: str
    allowed: bool
    blocking_rules: List[ConstraintCheck]
    warning_rules: List[ConstraintCheck]
    narrative: str                # full story of what would happen
    prerequisites: List[str]      # conditions that must be met first
    estimated_risk: str           # "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"


# ─────────────────────────────────────────────────────────────────────────────
# Static SFD knowledge base (complements brasil_constraints.json)
# ─────────────────────────────────────────────────────────────────────────────

# operation → list of {rule_id, condition, explanation, resolution, fr}
_OPERATION_RULES: Dict[str, List[Dict]] = {
    "DELETE": [
        {
            "rule_id": "CSTR-SQL-001",
            "condition_keyword": ["card", "carte", "t_cards"],
            "explanation": (
                "Selon la règle SFD CSTR-SQL-001, un équipement DSLAM/MSAN ne peut pas être supprimé "
                "tant que des cartes (T-CARD) lui sont encore rattachées dans la table t_cards. "
                "Cette contrainte garantit l'intégrité référentielle de la base BRASIL : "
                "la suppression d'un équipement parent sans désaffecter ses enfants provoquerait "
                "des références orphelines sur les ports et services associés."
            ),
            "resolution": [
                "1. Lister toutes les cartes: SELECT card_id, card_name FROM t_cards WHERE eqpt_id = '<ID>'",
                "2. Pour chaque carte, vérifier les ports actifs: SELECT * FROM t_ports WHERE card_id = '<CARD_ID>'",
                "3. Désaffecter tous les services actifs sur chaque port",
                "4. Supprimer les cartes via IHM BRASIL ou DELETE FROM t_cards WHERE card_id = '<CARD_ID>'",
                "5. Vérifier qu'aucune carte ne reste: SELECT COUNT(*) FROM t_cards WHERE eqpt_id = '<ID>'",
                "6. Relancer la suppression de l'équipement",
            ],
            "fr": "",
            "simulated_outcome": (
                "Si la suppression est forcée avec des cartes actives, PostgreSQL lèvera une violation "
                "de contrainte FK (foreign key violation), la transaction sera annulée, "
                "et l'équipement restera en base avec un statut incohérent."
            ),
            "severity": "blocking",
        },
        {
            "rule_id": "CSTR-SQL-002",
            "condition_keyword": ["port", "service", "actif"],
            "explanation": (
                "La règle SFD CSTR-SQL-002 stipule que les ports actifs d'une carte empêchent "
                "la suppression de la carte parente. Un port 'actif' signifie qu'un service client "
                "(ADSL, VDSL2, GPON) est encore provisionné sur ce port dans t_ports. "
                "Supprimer la carte invaliderait le service client en cours."
            ),
            "resolution": [
                "1. Identifier les services actifs: SELECT * FROM t_ports WHERE card_id = '<CARD_ID>' AND port_status = 'ACTIVE'",
                "2. Déprovisionner chaque service via l'IHM BRASIL (commande de résiliation)",
                "3. Attendre confirmation de déprovisionne­ment dans t_making_files",
                "4. Vérifier que port_status = 'INACTIVE' pour tous les ports",
                "5. Procéder à la suppression de la carte",
            ],
            "fr": "",
            "simulated_outcome": (
                "Forcer la suppression provoquerait une interruption des services clients sur les ports concernés "
                "et laisserait des entrées orphelines dans t_making_files."
            ),
            "severity": "blocking",
        },
    ],
    "CREATE": [
        {
            "rule_id": "CSTR-FR-001",
            "condition_keyword": ["fermé", "prod_status", "production"],
            "explanation": (
                "Selon CSTR-FR-001, toute opération d'allocation (création de service, affectation de port) "
                "requiert que le DSLAM soit ouvert à la production (eqpt_prod_status = 'O'). "
                "Un DSLAM fermé (status 'F') est en maintenance ou hors service — aucune nouvelle ressource "
                "ne peut lui être allouée."
            ),
            "resolution": [
                "1. Vérifier le statut: SELECT eqpt_prod_status FROM t_equipments WHERE eqpt_id = '<ID>'",
                "2. Si status = 'F', vérifier s'il y a une fenêtre de maintenance active",
                "3. Ouvrir le DSLAM via IHM BRASIL: Admin > Équipements > Modifier > Statut Production = 'O'",
                "4. Ou via SQL (autorisation N3): UPDATE t_equipments SET eqpt_prod_status = 'O' WHERE eqpt_id = '<ID>'",
                "5. Vérifier dans Orchestra NE Repository que le DSLAM est bien synchronisé",
            ],
            "fr": "FR-001",
            "simulated_outcome": (
                "Tenter l'allocation sur un DSLAM fermé retournera l'erreur BRASIL-ERR-001 "
                "'Equipment closed for production' et la commande sera rejetée sans retentative."
            ),
            "severity": "blocking",
        },
    ],
    "ALLOCATE": [
        {
            "rule_id": "CSTR-FR-007",
            "condition_keyword": ["port", "broche", "toc", "attribuable"],
            "explanation": (
                "La règle CSTR-FR-007 exige que le compteur port_attribuable soit supérieur à 0 "
                "pour qu'une broche puisse être affectée à un abonné. "
                "Ce compteur représente le nombre de ports physiquement disponibles ET logiquement libres. "
                "Si le compteur est à 0 mais que des ports physiques existent, c'est un signe de "
                "désynchronisation — les compteurs doivent être recalculés."
            ),
            "resolution": [
                "1. Vérifier le compteur: SELECT dxcd_auto_available_port_count FROM t_d_dslam_xdsl_cards WHERE card_id = '<CARD_ID>'",
                "2. Comparer avec les ports réels: SELECT COUNT(*) FROM t_ports WHERE card_id = '<CARD_ID>' AND port_status = 'FREE'",
                "3. Si divergence, lancer CalculerToc.ksh (FR 001) sur le DSLAM",
                "4. Si toujours incohérent, appliquer FR 136b (libérer ports occupés à tort)",
                "5. Recalculer: UPDATE t_d_dslam_xdsl_cards SET dxcd_auto_available_port_count = <valeur_réelle>",
            ],
            "fr": "FR-001",
            "simulated_outcome": (
                "Avec port_attribuable=0, le moteur de recherche de broche retournera 'No port available' "
                "même si des ports physiques existent. La commande client échouera."
            ),
            "severity": "blocking",
        },
    ],
    "CLOSE": [
        {
            "rule_id": "CSTR-FR-001",
            "condition_keyword": ["service", "actif", "port"],
            "explanation": (
                "Avant de fermer un DSLAM à la production, tous les services actifs doivent être "
                "migrés ou déprovision­nés. Fermer un DSLAM avec des services actifs est une opération "
                "de maintenance qui doit être planifiée dans une fenêtre de maintenance autorisée."
            ),
            "resolution": [
                "1. Lister les services actifs: SELECT COUNT(*) FROM t_ports WHERE eqpt_id = '<ID>' AND port_status = 'ACTIVE'",
                "2. Planifier une fenêtre de maintenance",
                "3. Migrer ou résilier les services actifs",
                "4. Fermer le DSLAM: UPDATE t_equipments SET eqpt_prod_status = 'F' WHERE eqpt_id = '<ID>'",
            ],
            "fr": "FR-001",
            "simulated_outcome": (
                "Fermer un DSLAM avec services actifs impactera les abonnés sans préavis "
                "et pourra générer des tickets d'incident automatiques dans le système de supervision."
            ),
            "severity": "warning",
        },
    ],
}

# Constraint IDs that are always blocking for specific entity types
_ALWAYS_BLOCKING: Dict[str, List[str]] = {
    "DSLAM":        ["CSTR-SQL-001", "CSTR-SQL-002"],
    "MSAN":         ["CSTR-SQL-001", "CSTR-SQL-002"],
    "MAKING_FILE":  ["CSTR-FR-008"],
    "CCL":          ["CSTR-FR-003"],
}


# ─────────────────────────────────────────────────────────────────────────────
# SFD Reasoning Engine
# ─────────────────────────────────────────────────────────────────────────────

class SFDReasoningEngine:
    """
    Full SFD reasoning engine: enforce, explain, simulate, resolve.
    """

    # ── Public API ────────────────────────────────────────────────────────────

    def enforce_constraint(
        self,
        operation: str,
        entity_name: str,
        entity_type: str = "",
        context: Optional[str] = None,
    ) -> ConstraintCheck:
        """
        Check if operation is allowed, return a detailed ConstraintCheck.
        """
        op_upper = operation.upper()
        rules = _OPERATION_RULES.get(op_upper, [])

        # Also check SFD parser constraints
        sfd_constraints = sfd_parser.get_all_constraints()

        # Check each rule
        for rule in rules:
            # Check if context or entity_type triggers this rule
            ctx_match = context and any(
                kw in (context + " " + entity_type).lower()
                for kw in rule["condition_keyword"]
            )
            # Check SFD parser for this entity
            sfd_block = self._check_sfd_parser(op_upper, entity_name, sfd_constraints)

            if ctx_match or sfd_block:
                return ConstraintCheck(
                    rule_id=rule["rule_id"],
                    passed=False,
                    severity=rule["severity"],
                    short_reason=f"[{rule['rule_id']}] L'opération {op_upper} sur {entity_name} est bloquée",
                    explanation=rule["explanation"],
                    resolution_steps=rule["resolution"],
                    fr_reference=rule.get("fr", ""),
                    simulated_outcome=rule.get("simulated_outcome", ""),
                )

        return ConstraintCheck(
            rule_id="OK",
            passed=True,
            severity="none",
            short_reason=f"Aucune contrainte SFD ne bloque l'opération {op_upper} sur {entity_name}",
            explanation="L'opération est autorisée selon les règles SFD connues.",
            resolution_steps=[],
        )

    def explain_constraint(self, rule_id: str) -> str:
        """
        Return a full natural-language explanation of a SFD constraint rule.
        """
        # Search static rules
        for op_rules in _OPERATION_RULES.values():
            for rule in op_rules:
                if rule["rule_id"] == rule_id:
                    lines = [
                        f"## Règle SFD: {rule_id}",
                        "",
                        rule["explanation"],
                        "",
                        "**Conséquence si violée:**",
                        rule.get("simulated_outcome", "Comportement indéfini."),
                        "",
                        "**Pour résoudre:**",
                    ]
                    for step in rule["resolution"]:
                        lines.append(f"  {step}")
                    if rule.get("fr"):
                        lines.append(f"\n**Référence FR:** {rule['fr']}")
                    return "\n".join(lines)

        # Fallback to sfd_parser
        for c in sfd_parser.get_all_constraints():
            if c.rule_id == rule_id:
                return (
                    f"## Règle SFD: {rule_id}\n\n"
                    f"{c.description}\n\n"
                    f"Sévérité: {c.severity}\n"
                    f"Entités concernées: {', '.join(c.affected_entities)}"
                )

        return f"Règle {rule_id} non trouvée dans la base SFD."

    def simulate_operation(
        self,
        operation: str,
        entity_name: str,
        state: Optional[ConversationState] = None,
    ) -> OperationSimulation:
        """
        Full simulation: what happens if this operation is attempted now?
        Considers entity hierarchy from ConversationState.
        """
        op_upper = operation.upper()
        blocking: List[ConstraintCheck] = []
        warnings: List[ConstraintCheck] = []
        prerequisites: List[str] = []

        # Infer entity type from state
        entity_type = ""
        if state:
            for e in state.entities.values():
                if e.name.upper() == entity_name.upper():
                    entity_type = e.type.value
                    break
            # Infer relations from SFD hierarchy
            state.infer_relations_from_sfd()

        # Build context from entity relations
        context_parts = [entity_name, entity_type]
        if state:
            entity_obj = next(
                (e for e in state.entities.values() if e.name.upper() == entity_name.upper()),
                None,
            )
            if entity_obj:
                for rtype, targets in entity_obj.relations.items():
                    context_parts.extend(targets)

        context = " ".join(context_parts).lower()

        # Check all applicable rules
        rules = _OPERATION_RULES.get(op_upper, [])
        for rule in rules:
            check = self.enforce_constraint(op_upper, entity_name, entity_type, context)
            if not check.passed:
                if check.severity == "blocking":
                    blocking.append(check)
                    prerequisites.extend(check.resolution_steps[:2])
                else:
                    warnings.append(check)

        # Build narrative
        narrative = self._build_simulation_narrative(
            op_upper, entity_name, entity_type, blocking, warnings, state
        )

        # Estimate risk
        risk = "LOW"
        if blocking:
            risk = "CRITICAL"
        elif warnings:
            risk = "MEDIUM"
        elif op_upper in ("DELETE", "CLOSE"):
            risk = "HIGH"

        return OperationSimulation(
            operation=op_upper,
            entity_name=entity_name,
            allowed=len(blocking) == 0,
            blocking_rules=blocking,
            warning_rules=warnings,
            narrative=narrative,
            prerequisites=prerequisites,
            estimated_risk=risk,
        )

    def get_resolution_steps(
        self,
        rule_id: str,
        entity_name: str,
        entity_type: str = "",
    ) -> List[str]:
        """
        Return ordered resolution steps to make a specific rule pass.
        Replaces entity placeholders with actual entity name.
        """
        for op_rules in _OPERATION_RULES.values():
            for rule in op_rules:
                if rule["rule_id"] == rule_id:
                    steps = rule["resolution"]
                    # Replace placeholders
                    return [
                        s.replace("<ID>", entity_name)
                         .replace("<CARD_ID>", f"{entity_name}_CARD")
                         .replace("<NAME>", entity_name)
                        for s in steps
                    ]
        # Fallback: generic steps
        return [
            f"Vérifier le statut de {entity_name} dans BRASIL",
            f"Consulter la documentation FR pour la règle {rule_id}",
            "Contacter l'équipe N3 si le problème persiste",
        ]

    def check_preconditions(
        self,
        operation: str,
        entity_type: str,
    ) -> List[str]:
        """
        Return all preconditions that MUST be true before attempting an operation.
        Used to proactively guide the operator.
        """
        op_upper = operation.upper()
        preconditions: List[str] = []

        # Always-blocking for entity type
        for etype, rule_ids in _ALWAYS_BLOCKING.items():
            if etype.upper() == entity_type.upper():
                for rule_id in rule_ids:
                    preconditions.append(f"[{rule_id}] Vérifier qu'aucune ressource enfant n'est active")

        # Operation-specific
        if op_upper == "DELETE":
            preconditions += [
                "Tous les services actifs doivent être déprovision­nés",
                "Toutes les cartes doivent être retirées",
                "Tous les ports doivent être en statut INACTIVE",
                "Le DSLAM doit être fermé à la production (eqpt_prod_status='F')",
            ]
        elif op_upper == "CREATE":
            preconditions += [
                "Le DSLAM doit être ouvert à la production (eqpt_prod_status='O')",
                "port_attribuable doit être > 0",
                "Le nœud parent doit exister dans le Référentiel Sites",
            ]
        elif op_upper == "ALLOCATE":
            preconditions += [
                "port_attribuable > 0",
                "Le DSLAM doit être ouvert",
                "La carte cible doit être ouverte à la production",
            ]

        return preconditions

    # ── Internal ──────────────────────────────────────────────────────────────

    def _check_sfd_parser(
        self,
        operation: str,
        entity_name: str,
        constraints: List[SFDConstraint],
    ) -> bool:
        """Return True if SFD parser finds a blocking constraint."""
        entity_upper = entity_name.upper()
        for c in constraints:
            if entity_upper in [e.upper() for e in c.affected_entities]:
                desc_upper = c.description.upper()
                if operation == "DELETE" and any(
                    kw in desc_upper
                    for kw in ["CANNOT DELETE", "NE PEUT PAS", "INTERDIT", "FORBIDDEN", "BLOCKED", "SUPPRESSION"]
                ):
                    return True
        return False

    def _build_simulation_narrative(
        self,
        operation: str,
        entity_name: str,
        entity_type: str,
        blocking: List[ConstraintCheck],
        warnings: List[ConstraintCheck],
        state: Optional[ConversationState],
    ) -> str:
        lines = []

        # Context
        entity_desc = f"{entity_type} **{entity_name}**" if entity_type else f"**{entity_name}**"
        lines.append(f"## Simulation: {operation} sur {entity_desc}\n")

        if not blocking and not warnings:
            lines.append(f"✅ L'opération {operation} est autorisée.")
            lines.append("Aucune contrainte SFD ne bloque cette action.")
            if operation == "DELETE":
                lines.append("\nCependant, vérifiez :")
                lines.append("  • Qu'aucune carte n'est rattachée")
                lines.append("  • Que le DSLAM est fermé à la production")
            return "\n".join(lines)

        if blocking:
            lines.append(f"🚫 **L'opération {operation} est BLOQUÉE** par {len(blocking)} règle(s) SFD:\n")
            for check in blocking[:2]:
                lines.append(f"### Règle {check.rule_id}:")
                lines.append(check.explanation)
                lines.append(f"\n**Ce qui se passerait si forcé:** {check.simulated_outcome}")
                lines.append("\n**Pour débloquer:**")
                for step in check.resolution_steps[:4]:
                    lines.append(f"  {step}")
                lines.append("")

        if warnings:
            lines.append(f"\n⚠️ **Avertissements** ({len(warnings)}):")
            for w in warnings[:2]:
                lines.append(f"  • [{w.rule_id}] {w.short_reason}")

        # Entity hierarchy context
        if state:
            tree = state.get_entity_tree()
            if tree and tree != "(no entity hierarchy)":
                lines.append(f"\n**Hiérarchie des entités concernées:**\n{tree}")

        return "\n".join(lines)


# Singleton
sfd_reasoning = SFDReasoningEngine()
