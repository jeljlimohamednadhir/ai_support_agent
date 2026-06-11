"""
Layer 4 — Intent Resolution Layer
====================================
Multi-turn intent continuity engine.

Rules:
  1. Short / ambiguous input → reuse last_intent
  2. Pronoun / reference → resolve via ConversationState
  3. Explicit override → replace intent
  4. Resolution signals → fire 'confirm_resolution' or 'deny_resolution'

Intent taxonomy (BRASIL-specific):
  diagnose_equipment   | delete_equipment  | check_status
  search_port          | fix_counter       | replay_order
  explain_error        | confirm_resolution| deny_resolution
  mutation_request     | generic_question  | list_entities
  check_toc            | mass_replay       | unknown
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple

from app.services.chatbot.conversation_state import ConversationState, EntityType


# ─────────────────────────────────────────────────────────────────────────────
# Intent definitions
# ─────────────────────────────────────────────────────────────────────────────

INTENT_DIAGNOSE         = "diagnose_equipment"
INTENT_DELETE           = "delete_equipment"
INTENT_CHECK_STATUS     = "check_status"
INTENT_SEARCH_PORT      = "search_port"
INTENT_FIX_COUNTER      = "fix_counter"
INTENT_REPLAY_ORDER     = "replay_order"
INTENT_EXPLAIN_ERROR    = "explain_error"
INTENT_CONFIRM_RESOLVED = "confirm_resolution"
INTENT_DENY_RESOLVED    = "deny_resolution"
INTENT_MUTATION         = "mutation_request"
INTENT_GENERIC          = "generic_question"
INTENT_LIST             = "list_entities"
INTENT_CHECK_TOC        = "check_toc"
INTENT_MASS_REPLAY      = "mass_replay"
INTENT_UNKNOWN          = "unknown"

# ── Equipment operations ──────────────────────────────────────────────────
INTENT_FORCE_DELETE       = "force_delete_equipment"
INTENT_EQPT_LOCKED        = "equipment_locked"
INTENT_EQPT_STUCK         = "equipment_stuck_state"
INTENT_EQPT_NOT_FOUND     = "equipment_not_found"
INTENT_EQPT_INCONSISTENT  = "equipment_inconsistent_state"
INTENT_EQPT_ORPHAN        = "equipment_orphan_data"
INTENT_EQPT_CREATE_BLOCKED = "equipment_creation_blocked"

# ── VLAN operations ───────────────────────────────────────────────────────
INTENT_CREATE_VLAN        = "create_vlan"
INTENT_DELETE_VLAN        = "delete_vlan"
INTENT_VLAN_SYNC          = "vlan_sync_issue"
INTENT_VLAN_ORPHAN        = "vlan_orphan_data"

# ── Orchestration / Workflow ──────────────────────────────────────────────
INTENT_WORKFLOW_BLOCKED   = "workflow_blocked"
INTENT_WORKFLOW_STUCK     = "workflow_stuck"
INTENT_ORCH_TIMEOUT       = "orchestration_timeout"
INTENT_ROLLBACK_DETECTED  = "rollback_detected"
INTENT_TRANSACTION_FAILED = "transaction_failed"

# ── Forensic / Runtime diagnostic intents ─────────────────────────────────
INTENT_FORENSIC_LOGS      = "forensic_logs"
INTENT_FORENSIC_TIMELINE  = "forensic_timeline"
INTENT_FORENSIC_EVIDENCE  = "forensic_evidence"
INTENT_FORENSIC_EXCEPTIONS = "forensic_exceptions"
INTENT_FORENSIC_DB_STATE  = "forensic_db_state"
INTENT_FORENSIC_WORKFLOW  = "forensic_workflow"
INTENT_FORENSIC_ROOT_CAUSE = "forensic_root_cause"
INTENT_FORENSIC_ROLLBACK  = "forensic_rollback"
INTENT_FORENSIC_CONSTRAINT = "forensic_constraint_chain"

# ── Source code awareness ─────────────────────────────────────────────────
INTENT_SHOW_BLOCKING_METHOD  = "show_blocking_method"
INTENT_SHOW_CONSTRAINT_SRC   = "show_constraint_source"
INTENT_EXPLAIN_CODE          = "explain_code_constraint"
INTENT_EXPLAIN_EXCEPTION_SRC = "explain_exception_source"
INTENT_FIND_CODE_FUNCTION    = "find_code_function"

# ── DB investigation ──────────────────────────────────────────────────────
INTENT_CHECK_RESIDUAL     = "check_residual_data"
INTENT_CHECK_SERVICES     = "check_active_services"
INTENT_CHECK_MRT          = "check_mrt_links"
INTENT_CHECK_ORPHAN_ROWS  = "check_orphan_rows"
INTENT_CHECK_FK           = "check_foreign_keys"

# ── Incident analysis ────────────────────────────────────────────────────
INTENT_SIMILAR_INCIDENTS  = "similar_incidents"
INTENT_KNOWN_PROBLEM      = "known_problem"
INTENT_INCIDENT_RECURRENCE = "incident_recurrence"

# ── Operational guidance ──────────────────────────────────────────────────
INTENT_GEN_N3_SUMMARY     = "generate_n3_summary"
INTENT_GEN_RCA            = "generate_rca"
INTENT_GEN_POSTMORTEM     = "generate_postmortem"

# ── ML Classification ──────────────────────────────────────────────────────
INTENT_CLASSIFY_TICKET    = "classify_ticket"    # classifier ce ticket inline
INTENT_DRIFT_REPORT       = "drift_report"       # rapport de dérive du modèle ML

FORENSIC_INTENTS = {
    INTENT_FORENSIC_LOGS, INTENT_FORENSIC_TIMELINE, INTENT_FORENSIC_EVIDENCE,
    INTENT_FORENSIC_EXCEPTIONS, INTENT_FORENSIC_DB_STATE, INTENT_FORENSIC_WORKFLOW,
    INTENT_FORENSIC_ROOT_CAUSE, INTENT_FORENSIC_ROLLBACK, INTENT_FORENSIC_CONSTRAINT,
    INTENT_SHOW_BLOCKING_METHOD, INTENT_SHOW_CONSTRAINT_SRC,
    INTENT_EXPLAIN_CODE, INTENT_EXPLAIN_EXCEPTION_SRC, INTENT_FIND_CODE_FUNCTION,
    INTENT_CHECK_RESIDUAL, INTENT_CHECK_SERVICES,
}

INTENTS_WITH_ENTITY = {
    INTENT_DIAGNOSE, INTENT_DELETE, INTENT_CHECK_STATUS,
    INTENT_SEARCH_PORT, INTENT_FIX_COUNTER, INTENT_MUTATION,
    INTENT_FORENSIC_LOGS, INTENT_FORENSIC_EVIDENCE,
    INTENT_FORCE_DELETE, INTENT_EQPT_LOCKED, INTENT_EQPT_STUCK,
    INTENT_EQPT_NOT_FOUND, INTENT_EQPT_INCONSISTENT, INTENT_EQPT_ORPHAN,
    INTENT_EQPT_CREATE_BLOCKED, INTENT_DELETE_VLAN, INTENT_CREATE_VLAN,
    INTENT_FORENSIC_EXCEPTIONS, INTENT_FORENSIC_DB_STATE,
    INTENT_CHECK_RESIDUAL, INTENT_CHECK_SERVICES, INTENT_CHECK_MRT,
}

# ─────────────────────────────────────────────────────────────────────────────
# Pattern → intent mapping (French + English)
# ─────────────────────────────────────────────────────────────────────────────

_INTENT_PATTERNS: List[Tuple[re.Pattern, str]] = [
    # Resolution
    (re.compile(r"\b(probl[eè]me?\s+r[eé]solu|c['']est\s+r[eé]solu|ça\s+marche(\s+maintenant)?|fix[eé]|ok\s+merci|merci\s+ça\s+marche|c['']est\s+bon|oui\s+c['']est\s+r[eé]solu|tout\s+fonctionne)\b", re.I), INTENT_CONFIRM_RESOLVED),
    (re.compile(r"\b(non[,\s]|pas\s+r[eé]solu|ne\s+marche\s+(toujours\s+)?pas|ça\s+ne\s+marche\s+pas|toujours\s+le\s+même|toujours\s+bloqué|[eé]chec|sans\s+succ[eè]s|toujours\s+pas|pas\s+encore)\b", re.I), INTENT_DENY_RESOLVED),

    # ── Forensic intents (high priority — before generic patterns) ─────────

    # Forensic — exceptions / constraints
    (re.compile(
        r"\b(quelle?s?\s+exceptions?|exceptions?\s+d[eé]tect[eé]|quelle?\s+contrainte|"
        r"contrainte\s+bloque|quelle?\s+erreur\s+java|exception\s+source|"
        r"caused\s*by|stacktrace|stack\s+trace|"
        r"montre[rz]?\s+(?:les?\s+)?exceptions?|affich[eé]\s+(?:les?\s+)?exceptions?|"
        r"liste[rz]?\s+(?:les?\s+)?exceptions?|exceptions?\s+lev[eé]es?|"
        r"exceptions?\s+remont[eé]es?|quelles?\s+exceptions?\s+(?:sont|existent|apparaissent))\b",
        re.I,
    ), INTENT_FORENSIC_EXCEPTIONS),

    # Forensic — root cause
    (re.compile(
        r"\b(cause\s+racine|root\s*cause|pourquoi\s+[çc]a\s+bloque|pourquoi\s+impossible|"
        r"pourquoi\s+[eé]chec|quelle?\s+est\s+la\s+cause|d['']o[uù]\s+vient\s+le?)\b",
        re.I,
    ), INTENT_FORENSIC_ROOT_CAUSE),

    # Forensic — DB state
    (re.compile(
        r"\b([eé]tat\s+(?:de\s+la\s+)?(?:base|db|bdd)|donn[eé]es?\s+r[eé]siduelles?|"
        r"quelle?s?\s+tables?\s+(?:pose|bloque)|v[eé]rifier?\s+la\s+base|check\s+db|"
        r"quelle?\s+table\s+(?:pose|a)\s+probl)\b",
        re.I,
    ), INTENT_FORENSIC_DB_STATE),

    # Forensic — workflow
    (re.compile(
        r"\b(quel\s+workflow|workflow\s+bloqu[eé]|quel\s+[eé]tat|"
        r"transition\s+d['']?[eé]tat|state\s+machine|[eé]tat\s+de\s+l)\b",
        re.I,
    ), INTENT_FORENSIC_WORKFLOW),

    # Code source — find function for operation (HIGHEST PRIORITY for code queries)
    (re.compile(
        r"(quelle?\s+(est\s+la?\s+)?(fonction|m[eé]thode|classe|service|impl[eé]mentation)\s+(qui|pour|de|permet)"
        r"|quelle?\s+(m[eé]thode|classe|fonction|service)\s+(java|supprime|cr[eé]e|fait|effectue|g[eè]re|traite|ex[eé]cute|r[eé]alise|permet|lance|appelle)"
        r"|quel\s+service\s+(fait|effectue|g[eè]re|traite|ex[eé]cute|r[eé]alise|permet|appelle|supprime|cree|cr[eé]e)"
        r"|comment\s+(est\s+)?impl[eé]ment[eé]"
        r"|o[uù]\s+est\s+(cod[eé]|impl[eé]ment[eé]|d[eé]fini)\s+la?"
        r"|quelle?\s+code\s+(fait|effectue|g[eè]re|permet))",
        re.I,
    ), INTENT_FIND_CODE_FUNCTION),

    # Code source — blocking method
    (re.compile(
        r"\b(quelle?\s+m[eé]thode\s+bloque|m[eé]thode\s+bloquante|show\s+blocking|"
        r"quel\s+code\s+(?:provoque|bloque|emp[eê]che)|o[uù]\s+(?:est|dans)\s+le\s+code|"
        r"dans\s+quel\s+fichier|source\s+(?:de\s+la?|du)\s+(?:contrainte|erreur|bloqu))\b",
        re.I,
    ), INTENT_SHOW_BLOCKING_METHOD),

    # Forensic — rollback / transaction
    (re.compile(
        r"\b(rollback|transaction\s+(?:annul|[eé]chou|fail)|annulation|"
        r"quelle?\s+transaction)\b",
        re.I,
    ), INTENT_FORENSIC_ROLLBACK),

    # Check residual data
    (re.compile(
        r"\b(donn[eé]es?\s+r[eé]siduelles?|residual|orphelin|d[eé]pendances?\s+r[eé]siduelles?|"
        r"v[eé]rifier?\s+(?:les?\s+)?r[eé]sidus?)\b",
        re.I,
    ), INTENT_CHECK_RESIDUAL),

    # Check active services
    (re.compile(
        r"\b(services?\s+actifs?|services?\s+li[eé]s?|activ[eé]s?\s+li[eé]s?|"
        r"v[eé]rifier?\s+(?:les?\s+)?services?)\b",
        re.I,
    ), INTENT_CHECK_SERVICES),

    # Forensic — logs
    (re.compile(
        r"\b(show\s+logs?|affiche[rz]?\s+logs?|voir\s+les?\s+logs?|extract(?:ion)?\s+logs?|"
        r"montre[rz]?(?:\s*-?\s*moi)?\s+(?:les?\s+)?logs?|"
        r"logs?\s+de\s+l.erreur|logs?\s+pour|logs?\s+de\s+l|affiche[rz]?\s+les?\s+logs?|"
        r"quelles?\s+lignes?\s+(?:prouvent?|montrent?)|montre[rz]?\s+les?\s+lignes?|"
        r"logs?\s+\w+|erreurs?\s+pour\s+\w+|show\s+errors?\s+for\b)",
        re.I,
    ), INTENT_FORENSIC_LOGS),

    # Forensic — timeline
    (re.compile(
        r"\b(show\s+timeline|affiche[rz]?\s+timeline|timeline\s+incident|"
        r"historique\s+incident|chronologie|s[eé]quence\s+d['\s]événements?|"
        r"quand\s+c['']est\s+arriv[eé]|ordre\s+des?\s+[eé]v[eé]nements?)\b",
        re.I,
    ), INTENT_FORENSIC_TIMELINE),

    # Forensic — runtime evidence
    (re.compile(
        r"\b(show\s+(?:runtime\s+)?evidence|affiche[rz]?\s+(?:les?\s+)?preuves?|"
        r"show\s+runtime|preuves?\s+live|runtime\s+forensic|"
        r"données?\s+live|show\s+diagnostic\s+data)\b",
        re.I,
    ), INTENT_FORENSIC_EVIDENCE),

    # Equipment — stuck state / inconsistent
    (re.compile(
        r"\b([eé]quipement\s+bloqu[eé]|[eé]tat\s+incoh[eé]rent|stuck|gel[eé]|fig[eé]|"
        r"ne\s+change\s+pas\s+d['']?[eé]tat)\b",
        re.I,
    ), INTENT_EQPT_STUCK),

    # Equipment — not found
    (re.compile(
        r"\b([eé]quipement\s+introuvable|not\s+found|existe\s+pas|n['']?existe\s+pas|"
        r"introuvable|inconnu\s+dans)\b",
        re.I,
    ), INTENT_EQPT_NOT_FOUND),

    # Workflow blocked / orchestration
    (re.compile(
        r"\b(workflow\s+bloqu[eé]|orchestration\s+(?:bloqu|timeout|[eé]chou)|"
        r"provisioning\s+(?:bloqu|stuck|[eé]chou)|commande\s+(?:non\s+)?re[çc]ue)\b",
        re.I,
    ), INTENT_WORKFLOW_BLOCKED),

    # VLAN creation
    (re.compile(
        r"\b(cr[eé](?:ation|er)\s+(?:de\s+)?vlan)\b",
        re.I,
    ), INTENT_CREATE_VLAN),

    # Generate N3 summary / RCA
    (re.compile(
        r"\b(g[eé]n[eé]rer?\s+(?:un\s+)?(?:r[eé]sum[eé]|rapport|rca|postmortem|compte[\s-]?rendu)|"
        r"r[eé]sum[eé]\s+(?:n3|technique|incident))\b",
        re.I,
    ), INTENT_GEN_N3_SUMMARY),

    # ML Classification — classifier ce ticket inline
    (re.compile(
        r"\b(class(?:e|ifi(?:e|er?|ez))\s+(?:ce\s+)?(?:ticket|incident|demande|probl[eè]me)|"
        r"cat[eé]goris(?:e|er?|ez)\s+(?:ce\s+)?(?:ticket|incident|demande)|"
        r"quel\s+type\s+(?:d[e'])\s*(?:ticket|incident)|"
        r"de\s+quel\s+type\s+est|"
        r"d[eé]termine[rz]?\s+la\s+cat[eé]gorie|"
        r"cat[eé]gorisation\s+(?:automatique|ml)|"
        r"classifier\s+[çc]a|"
        r"analyse[rz]?\s+ce\s+ticket\s+(?:ml|automatiquement))\b",
        re.I,
    ), INTENT_CLASSIFY_TICKET),

    # ML Drift report
    (re.compile(
        r"\b(drift|d[eé]rive\s+(?:du|de\s+la?)\s*mod[eè]le?|"
        r"psi\s+(?:du|de\s+la?)\s*mod[eè]le?|"
        r"rapport\s+de\s+d[eé]rive|"
        r"distribution\s+a\s+(?:chang[eé]|d[eé]riv[eé])|"
        r"mod[eè]le\s+(?:encore\s+)?[àa]\s+jour)\b",
        re.I,
    ), INTENT_DRIFT_REPORT),

    # Similar incidents
    (re.compile(
        r"\b(incidents?\s+similaires?|probl[eè]mes?\s+similaires?|d[eé]j[àa]\s+(?:vu|arriv[eé])|"
        r"cas\s+similaire|r[eé]current|r[eé]currence)\b",
        re.I,
    ), INTENT_SIMILAR_INCIDENTS),

    # Delete / suppress
    (re.compile(r"\b(supprimer?|suppression|effacer?|enlever?|d[eé]sactiver?|retirer?|d[eé]connecter?)\b", re.I), INTENT_DELETE),

    # Status check
    (re.compile(r"\b(statut|status|[eé]tat|v[eé]rifier?|contr[oô]ler?|checker?|v[eé]rif)\b", re.I), INTENT_CHECK_STATUS),

    # Diagnose / troubleshoot
    (re.compile(r"\b(probl[eè]me?|ne\s+marche\s+pas|diagnostic|diagnostiquer?|d[eé]panner?|inspecter?|analyser?|investiguer?|erreur|bloqué|[eé]chec|dysfonction)\b", re.I), INTENT_DIAGNOSE),

    # Search port / broche
    (re.compile(r"\b(broche|port\s+disponible|recherche\s+broche|affecter?\s+port|port\s+libre)\b", re.I), INTENT_SEARCH_PORT),

    # Fix counter
    (re.compile(r"\b(compteur|counter|toc|recalcul|corriger?\s+(compteur|toc)|vc\s+occup[eé]|vlan\s+occup[eé])\b", re.I), INTENT_FIX_COUNTER),

    # Replay order
    (re.compile(r"\b(rejouer?|relancer?|replay|remett?re\s+en\s+(route|service)|re-traiter?)\b", re.I), INTENT_REPLAY_ORDER),

    # Explain error
    (re.compile(r"\b(signifie?|expliquer?|que\s+veut\s+dire|c['']est\s+quoi|d[eé]finition|signification)\b", re.I), INTENT_EXPLAIN_ERROR),

    # Mutation
    (re.compile(r"\b(mutation|d[eé]placer?|changer?\s+de?\s+dslam|migrer?|d[eé]localiser?)\b", re.I), INTENT_MUTATION),

    # TOC
    (re.compile(r"\b(calculer?\s+toc|taux\s+d['']occupation|toc\s+100|saturation)\b", re.I), INTENT_CHECK_TOC),

    # Mass replay
    (re.compile(r"\b(en\s+masse|mass[eé]|batch|liste\s+de\s+nd|umi[-\s]epc\s+envoi)\b", re.I), INTENT_MASS_REPLAY),

    # List
    (re.compile(r"\b(lister?|afficher?|montrer?|liste\s+de|quels?\s+sont)\b", re.I), INTENT_LIST),

    # Generic question
    (re.compile(r"\b(comment|pourquoi|qu['']est.ce|quelle?|quand|where|how|why|what)\b", re.I), INTENT_GENERIC),
]

# Short-input threshold (words)
_SHORT_INPUT_THRESHOLD = 5
# Ambiguous single-word inputs that should reuse context
_AMBIGUOUS_TOKENS = {
    "oui", "non", "ok", "voilà", "voila", "exact", "c'est ça", "bien sûr",
    "d'accord", "le", "la", "les", "il", "elle", "ça", "cela", "lui",
}


# ─────────────────────────────────────────────────────────────────────────────
# IntentResult
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class IntentResult:
    intent: str
    confidence: float
    is_continuation: bool = False          # reused from previous turn
    resolved_entity_name: Optional[str] = None
    requires_entity: bool = False
    metadata: Dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


# ─────────────────────────────────────────────────────────────────────────────
# Intent Resolver
# ─────────────────────────────────────────────────────────────────────────────

class IntentResolver:
    """
    Resolves user intent with multi-turn continuity.

    Algorithm:
      1. Check for explicit resolution signals (highest priority)
      2. Check if input is purely a reference / pronoun → continuation
      3. Pattern match against INTENT_PATTERNS
      4. If no match AND input is short → reuse last_intent (continuation)
      5. Fallback to UNKNOWN
    """

    def resolve(
        self,
        user_text: str,
        state: ConversationState,
    ) -> IntentResult:
        text = user_text.strip()
        words = text.split()
        n_words = len(words)

        # ── 1. Explicit resolution signals (always override) ────────────────
        # deny_resolution only fires if there's already a conversation context
        for i, (pattern, intent) in enumerate(_INTENT_PATTERNS[:2]):  # confirm/deny first
            if pattern.search(text):
                # deny_resolution only meaningful in context of a prior turn
                if intent == INTENT_DENY_RESOLVED and not state.last_intent:
                    continue  # fall through to pattern matching
                return IntentResult(
                    intent=intent,
                    confidence=0.95,
                    is_continuation=False,
                    requires_entity=False,
                )

        # ── 2. Pure pronoun / reference → continuation ──────────────────────
        is_pure_reference = (
            text.lower() in _AMBIGUOUS_TOKENS
            or (n_words <= 3 and _is_pronoun_only(text))
        )
        if is_pure_reference and state.last_intent:
            resolved = state.resolve_reference(text)
            return IntentResult(
                intent=state.last_intent,
                confidence=0.85,
                is_continuation=True,
                resolved_entity_name=resolved.name if resolved else None,
                requires_entity=False,
            )

        # ── 3. Pattern matching ──────────────────────────────────────────────
        matched_intent = None
        for pattern, intent in _INTENT_PATTERNS:
            if pattern.search(text):
                # deny_resolution only valid if there's prior context
                if intent == INTENT_DENY_RESOLVED and not state.last_intent:
                    continue
                matched_intent = intent
                break

        # ── 4. Short input without match → reuse last_intent ────────────────
        if matched_intent is None and n_words <= _SHORT_INPUT_THRESHOLD and state.last_intent:
            resolved = state.resolve_reference(text)
            return IntentResult(
                intent=state.last_intent,
                confidence=0.75,
                is_continuation=True,
                resolved_entity_name=resolved.name if resolved else None,
                requires_entity=matched_intent in INTENTS_WITH_ENTITY,
            )

        # ── 5. Return matched or unknown ────────────────────────────────────
        intent = matched_intent or INTENT_UNKNOWN
        resolved = state.resolve_reference(text) if intent in INTENTS_WITH_ENTITY else None

        return IntentResult(
            intent=intent,
            confidence=0.90 if matched_intent else 0.40,
            is_continuation=False,
            resolved_entity_name=resolved.name if resolved else None,
            requires_entity=intent in INTENTS_WITH_ENTITY,
        )


def _is_pronoun_only(text: str) -> bool:
    """Return True if text is purely pronoun/determiner tokens."""
    stopwords = {
        "le", "la", "les", "il", "elle", "ils", "elles",
        "ça", "cela", "celui", "cet", "ce", "lui", "leur",
        "je", "tu", "nous", "vous", "on", "y", "en",
    }
    tokens = set(re.sub(r"[^\w\s]", "", text.lower()).split())
    return bool(tokens) and tokens.issubset(stopwords)


# Singleton
intent_resolver = IntentResolver()
