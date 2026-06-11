"""
Diagnostic Behavior Module — Anti-hallucination, slot filling, structured diagnostic loop.
Extends chatbot_service.py with structured diagnostic reasoning.

Implements:
  - ConversationPhase / ConversationState: explicit conversation state machine
  - SlotFiller: extracts missing context from conversation
  - DiagnosticReasoner: structures multi-step diagnostic conversations
  - AntiHallucinationGuard: ensures responses stay grounded in KB
  - ResponseFormatter: formats responses using the N3 support template
  - Role-aware response generation (N3 engineer / colleague / depositor)
  - Humanized style directives
"""
import json
import re
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

from app.services.nlp.enricher import ticket_enricher, StructuredTicket
from app.services.nlp.taxonomy import INCIDENT_TAXONOMY
from app.core.logging import get_logger

logger = get_logger(__name__)


# ─────────────────────────────────────────────
# Known application systems (used by context isolation)
# ─────────────────────────────────────────────

KNOWN_SYSTEMS: List[str] = [
    "BRASIL", "ORRAHD", "SEBA", "42C", "ARTEMIS", "IPON",
    "ADELIA", "SCA", "ORCHESTRA", "NECTAR", "TIGRE", "DSLAM",
    "ONT", "OLT", "GPON",
]

# Liste complète des tables du schéma BRASIL (extraite de brasil_db.sql)
# Utilisée pour guider le LLM quand la recherche vectorielle ne trouve pas de résultat exact
BRASIL_SCHEMA_TABLES: List[str] = [
    "encoding_correct",
    "lst_presta_new_offres", "lst_presta_offres", "lst_presta_recap_detail",
    "lst_presta_recap_graph_details", "lst_presta_recap_graph_total",
    "lst_presta_recap_total", "lst_presta_techno", "lst_vlan_usage",
    "t_application_configs", "t_application_parameter_values", "t_application_parameters",
    "t_atm_profiles", "t_bays", "t_card_models", "t_card_national_profiles",
    "t_card_soft_vers", "t_cardmodels_sfp", "t_cards",
    "t_d_booked_ports", "t_d_controlable_rscs", "t_d_dslam_logical_shelfs",
    "t_d_dslam_manelems", "t_d_dslam_xdsl_cards", "t_d_need_new_vcs",
    "t_d_rsc_dslam_tsfs", "t_d_rsc_vcis", "t_d_xdsl_card_stripes",
    "t_distributors", "t_dr", "t_dslam_access_constraints", "t_dslam_assignments",
    "t_dslam_soft_vers", "t_epc_order_lines", "t_epc_vers", "t_epc_vers_comps",
    "t_epc_vers_impacts", "t_epcs", "t_eqpt_shf_mdl_compatibilities",
    "t_equipments", "t_es", "t_es_connexions", "t_es_habilitations",
    "t_es_logs", "t_es_types", "t_ftth_lock_onts", "t_function_codes",
    "t_group_localisation", "t_icc_updates", "t_interfaces", "t_line_profiles",
    "t_link_dr_group_localisation", "t_local_areas", "t_logical_eqpt_models",
    "t_making_files", "t_manufacturers", "t_media_links",
    "t_mrt_access_dslam_vers", "t_mrt_access_dslams", "t_mrt_access_msan_usage",
    "t_mrt_access_service_vers", "t_mrt_access_services", "t_mrt_types",
    "t_mrt_vers_impacts", "t_mutations_requests", "t_net_port_models",
    "t_net_resource_rels", "t_nip_server_assocs", "t_no_back_on_technos",
    "t_nodes", "t_ont_profiles", "t_operators",
    "t_p_intsiam_concat_offers", "t_p_intsiam_offers", "t_p_pcp_repos",
    "t_p_slot_repos", "t_p_talia_logical_bays", "t_p_talia_service_ids",
    "t_p_tech_service_filters", "t_p_tst_to_comp_servs",
    "t_port_groups", "t_ports", "t_prestations", "t_res_prod_controlables",
    "t_res_prod_controlers", "t_res_prod_roles", "t_resource_constraints",
    "t_resource_usages", "t_roles", "t_rooms", "t_rows",
    "t_server_constraints", "t_servers", "t_service_commit", "t_service_profiles",
    "t_sfp_module_port_assocs", "t_sfp_modules", "t_shelf_models", "t_shelfs",
    "t_sites", "t_slot_models", "t_slots", "t_st_components",
    "t_stripe_models", "t_stripes", "t_swap_requests",
    "t_tech_serv_functions", "t_tech_serv_types", "t_tech_services",
    "t_techno_on_card_nat_profiles", "t_technology_types", "t_throughputs",
    "t_tp_ccl_atms", "t_tp_initial_states", "t_tp_shelfs", "t_tps",
    "t_tr_assignments", "t_tr_functions", "t_trs",
    "t_tsf_family_assoc", "t_tsf_usage_assoc", "t_tst_closed_on_cards",
    "t_tst_closed_on_shelfs", "t_tst_on_card_nat_profiles", "t_tst_on_dslams",
    "t_tst_without_mrts", "t_usage_constraints", "t_vc_lock_ranges",
]


# ─────────────────────────────────────────────
# Conversation Phase State Machine
# ─────────────────────────────────────────────

class ConversationPhase(str, Enum):
    DIAGNOSTIC    = "diagnostic"
    INVESTIGATION = "investigation"
    RESOLUTION    = "resolution"
    CLOSING       = "closing"


@dataclass
class ConversationState:
    """
    Tracks the full state of an ongoing support conversation.
    Serialised as JSON in each ChatResponse and restored at the next turn.
    """
    phase: ConversationPhase = ConversationPhase.DIAGNOSTIC
    application: str = ""
    incident_summary: str = ""
    confirmed_root_cause: Optional[str] = None    # locked once confirmed
    confirmed_procedure_id: Optional[str] = None  # procedure that was applied
    resolution_confirmed: bool = False
    audience: str = "n3_engineer"                 # "n3_engineer" | "colleague" | "depositor"
    locked_systems: List[str] = field(default_factory=list)   # systems in scope
    excluded_systems: List[str] = field(default_factory=list) # systems to exclude from RAG
    turn_count: int = 0
    resolution_confirmation_count: int = 0        # auto-close after 3 confirmations
    # Maps a normalised question fingerprint → how many times it was asked unanswered.
    # Used to detect loops (same question repeated ≥ 2 times) and trigger escalation.
    repeated_questions: Dict[str, int] = field(default_factory=dict)

    def register_question(self, question: str) -> int:
        """
        Registers a question and returns the number of times it has been asked.
        The key is a normalised fingerprint (lower-cased, stripped, truncated to 80 chars)
        so minor reformulations of the same question count as one.
        """
        key = question.strip().lower()[:80]
        # Strip common filler words so "c'est quoi t_es" and "dis moi c'est quoi t_es" map to the same key
        key = re.sub(r"^(dis[- ]moi|c'est quoi|qu'est[- ]ce que|pouvez[- ]vous (m')?expliquer|explique[- ]moi)\s+", "", key)
        self.repeated_questions[key] = self.repeated_questions.get(key, 0) + 1
        return self.repeated_questions[key]

    def to_json(self) -> str:
        d = asdict(self)
        d["phase"] = self.phase.value
        return json.dumps(d, ensure_ascii=False)

    @classmethod
    def from_json(cls, s: str) -> "ConversationState":
        try:
            d = json.loads(s)
            d["phase"] = ConversationPhase(d.get("phase", "diagnostic"))
            d.setdefault("repeated_questions", {})
            d.setdefault("resolution_confirmation_count", 0)
            return cls(**d)
        except Exception:
            return cls()


# ─────────────────────────────────────────────
# Phase transition patterns
# ─────────────────────────────────────────────

_TRANSITION_TO_INVESTIGATION = re.compile(
    r"\b(j'ai\s+v[eé]rifi[eé]|les\s+logs\s+montrent|j'ai\s+trouv[eé]|"
    r"j'ai\s+constat[eé]|en\s+regardant|apr[eè]s\s+v[eé]rification|"
    r"la\s+cause\s+semble|le\s+probl[eè]me\s+vient\s+de|j'ai\s+identifi[eé]|"
    r"j'ai\s+remarqu[eé]|on\s+voit\s+que|j'observe)\b",
    re.IGNORECASE,
)

_TRANSITION_TO_RESOLUTION = re.compile(
    r"\b(comment\s+(r[eé]soudre|corriger|proc[eé]der)|quelle\s+(est\s+la\s+)?proc[eé]dure|"
    r"quelles?\s+(sont\s+les\s+)?[eé]tapes|FR\s+pour|appliquer\s+la\s+proc[eé]dure|"
    r"que\s+faire\s+maintenant|que\s+dois[- ]je\s+faire|comment\s+corriger|"
    r"comment\s+r[eé]gler|proc[eé]dure\s+de\s+r[eé]solution)\b",
    re.IGNORECASE,
)

_TRANSITION_TO_CLOSING = re.compile(
    r"\b(message\s+de\s+cl[oô]ture|fermer\s+le\s+ticket|cl[oô]turer|"
    r"informer\s+le\s+d[eé]positaire|[eé]crire\s+au\s+(client|d[eé]positaire|demandeur)|"
    r"g[eé]n[eè]re\s+le\s+message|ticket\s+r[eé]solu|c'est\s+r[eé]solu|"
    r"probl[eè]me\s+r[eé]gl[eé]|r[eé]solution\s+confirm[eé]e|"
    r"notifier\s+(le\s+)?(client|d[eé]positaire)|communiquer\s+(la\s+)?r[eé]solution|"
    r"cl[oô]ture\s+du\s+ticket|ticket\s+[àa]\s+fermer|on\s+peut\s+fermer)\b",
    re.IGNORECASE,
)

# ── Resolution confirmation signals (soft — counted, not immediate close) ──
RESOLUTION_CONFIRMATION_SIGNALS = re.compile(
    r"\b("
    r"c'est\s+bon|c\s+est\s+bon|"
    r"[cç]a\s+marche(\s+maintenant)?|[cç]a\s+fonctionne(\s+maintenant)?|"
    r"le\s+probl[eè]me\s+est\s+r[eé]solu|"
    r"probl[eè]me\s+r[eé]solu|incident\s+r[eé]solu|"
    r"tout\s+(fonctionne|marche)\s+(bien|correctement|maintenant)?|"
    r"ok\s+merci|merci\s+[cç]a|[cç]a\s+a\s+march[eé]|"
    r"resolved|fixed|it\s+works(\s+now)?|"
    r"le\s+service\s+(est\s+)?r[eé]tabli|service\s+r[eé]tabli|"
    r"les\s+clients\s+sont\s+(de\s+nouveau\s+)?connect[eé]s|"
    r"tout\s+est\s+(rentré|rentr[eé])\s+dans\s+l'ordre|"
    r"nichts?\s+mehr|probl[eè]me\s+corrig[eé]|"
    r"la\s+correction\s+a\s+fonctionn[eé]"
    r")\b",
    re.IGNORECASE,
)

_ROOT_CAUSE_CONFIRMATION = re.compile(
    r"(?:"
    r"la\s+cause\s+(racine\s+)?(est|[eé]tait|c'est|c'[eé]tait)|"
    r"la\s+cause\s+[eé]tait|"
    r"le\s+probl[eè]me\s+(vient|venait|est|[eé]tait)\s+(de|du|des|d'un|d'une)|"
    r"j'ai\s+(identifi[eé]|confirm[eé]|trouv[eé])\s+(que|la\s+cause)|"
    r"cause\s*[:\-]\s*.{5,}|"
    r"root\s+cause\s*[:\-]\s*.{5,}|"
    r"en\s+cause\s*[:\-]\s*.{5,}"
    r")",
    re.IGNORECASE,
)


# ─────────────────────────────────────────────
# Intent Override Detection
# Forces the correct intent pipeline for well-known signal patterns,
# independently of the ML-based intent classifier confidence.
# Designed to be general — covers all apps / all cases matching the pattern.
# ─────────────────────────────────────────────

# Signals that a script / batch / job is stuck in a running state.
# Applies to any script, batch, job or service described as blocked/running.
_SCRIPT_BLOCKED_PATTERNS: List = [
    re.compile(r"script\s+bloqu[eé]", re.IGNORECASE),
    re.compile(r"bloqu[eé]\s+en\s+cours", re.IGNORECASE),
    re.compile(r"en\s+cours\s+d.ex[eé]cution.*bloqu[eé]", re.IGNORECASE),
    re.compile(r"bloqu[eé].*en\s+cours\s+d.ex[eé]cution", re.IGNORECASE),
    re.compile(r"(batch|traitement|job|processus|script)\s+(est\s+)?bloqu[eé]", re.IGNORECASE),
    re.compile(r"statut.*en\s+cours.*depui[s]?", re.IGNORECASE),
    re.compile(r"(IHM|lancement).*script.*bloqu[eé]", re.IGNORECASE),
    re.compile(r"(d[eé]bloquer|d[eé]blocage).*script", re.IGNORECASE),
    re.compile(r"script.*ne\s+(se\s+)?termin[e]?(pas|plus)", re.IGNORECASE),
    re.compile(r"forcer\s+(la\s+)?fin\s+(du\s+)?script", re.IGNORECASE),
    re.compile(r"remettre\s+(le\s+)?statut", re.IGNORECASE),
    # ── Newly added patterns (from gap analysis) ──────────────────────────
    # User explicitly asks to stop/kill the script (without saying 'bloqué')
    re.compile(r"arr[eê]ter\s+(le\s+)?script", re.IGNORECASE),
    re.compile(r"arr[eê]tez\s+(le\s+)?(script|traitement|batch|job|processus)", re.IGNORECASE),
    re.compile(r"arr[eê]ter\s+(le\s+)?(traitement|batch|job|processus)", re.IGNORECASE),
    # User asks to set the status to error (mettre en erreur)
    re.compile(r"mettre.{0,20}en\s+erreur", re.IGNORECASE),
    re.compile(r"passer.{0,20}en\s+erreur", re.IGNORECASE),
    re.compile(r"forcer.{0,20}(statut|[eé]tat).{0,20}erreur", re.IGNORECASE),
    re.compile(r"(statut|[eé]tat).{0,20}(erreur|en_erreur|error)", re.IGNORECASE),
    # Script/process in a running state without explicitly saying 'bloqué'
    re.compile(r"reste\s+en\s+cours\s+d.ex[eé]cution", re.IGNORECASE),
    re.compile(r"toujours\s+en\s+cours\s+d.ex[eé]cution", re.IGNORECASE),
    re.compile(r"encore\s+en\s+cours\s+d.ex[eé]cution", re.IGNORECASE),
    re.compile(r"(script|traitement|batch|job)\s+.*\s+encore\s+bloqu[eé]", re.IGNORECASE),
    re.compile(r"tuer\s+(le\s+)?(script|processus|batch|job)", re.IGNORECASE),
    re.compile(r"interrompre\s+(le\s+)?(script|traitement|batch|job)", re.IGNORECASE),
    re.compile(r"stopper\s+(le\s+)?(script|traitement|batch|job)", re.IGNORECASE),
]

# Signals that the user is asking about a database table entity.
# Pattern: identifiers of the form t_<word> (BRASIL convention) or
# explicit mentions of 'table' followed by a name.
_DB_TABLE_PATTERN = re.compile(
    r"\b(t_[a-z_]{2,40}\b|table\s+[a-z_]{2,40}|la\s+table\s+[\w_]+|expliqu[e]?\s+(la\s+)?table\s+[\w_]+|c'est\s+quoi\s+(la\s+)?table\s+[\w_]+|d[eé]cri[st]\s+(la\s+)?table\s+[\w_]+)",
    re.IGNORECASE,
)

# Signals that the user is asking about a specific FR / procedure by number or keyword.
_PROCEDURE_LOOKUP_PATTERN = re.compile(
    r"(?:"
    r"\bFR[\s\-_]?\d{2,6}\b"  # FR 164, FR-164, FR_164
    r"|fiche\s+(de\s+)?r[eé]solution\s+\d+"  # fiche de résolution 164
    r"|proc[eé]dure\s+\d+"  # procédure 164
    r"|comment\s+(appliquer|utiliser)\s+(la\s+)?FR"  # comment appliquer la FR
    r"|d[eé]tail[s]?\s+(de\s+(la\s+)?)?FR"  # détails de la FR
    r"|plus\s+de\s+d[eé]tails\s+sur\s+(la\s+)?FR"  # plus de détails sur la FR
    r"|\bsur\s+(la\s+)?FR[\s\-_]?\d{2,6}\b"  # sur FR 164
    r"|d[eé]cri[st]\s+(la\s+)?FR"  # décris la FR
    r"|explique[\s\-]?(la\s+)?FR[\s\-_]?\d{2,6}"  # explique FR 164
    r")",
    re.IGNORECASE,
)


# Signals that the user wants a summary of the ongoing conversation to report to management.
_SUMMARIZE_FOR_SUPERIOR_PATTERN = re.compile(
    r"(?:"
    r"(que|quoi|qu')\s*(dire|rapporter|communiquer|r[eé]pondre|transmettre|envoyer)\s*.{0,20}(sup[eé]rieur|chef|manager|hi[eé]rarchie|n[+]?[12]|direction|responsable|encadrant)"
    r"|je\s+dis\s+quoi"
    r"|(que|quoi)\s+(dire|transmettre|communiquer|rapporter|r[eé]pondre|d[io]re)\s*(\w+\s+){0,3}(sup[eé]rieur|chef|manager|n[+]?[12]|hi[eé]rarchie|direction|responsable)"
    r"|r[eé]sume\s+(moi|la|le|l'|ce|cet|cette|l'incident|la\s+situation|le\s+probl[eè]me)"
    r"|(fais|g[eé]n[eè]re|donne|[eé]cri[st])\s+(moi\s+)?(un\s+)?r[eé]sum[eé]"
    r"|comment\s+(r[eé]sumer|pr[eé]senter|expliquer)\s*(l'|la\s+)?(incident|situation|probl[eè]me)"
    r")",
    re.IGNORECASE,
)


def detect_intent_override(message: str) -> Optional[str]:
    """
    Forces the correct intent when well-known signal patterns are present,
    bypassing the ML classifier.

    Returns one of:
      'procedure_lookup_script_blocked'  — script/batch stuck in a running state
      'tech_inference_schema'            — user is asking about a DB table entity
      'procedure_lookup'                 — user is asking about a specific FR/procedure
      'summarize'                        — user wants a summary to report to management
      None                               — no override; let the classifier decide

    This is intentionally generic: patterns match all apps and all cases,
    not just the example that triggered the fix.
    """
    # Summarize for management — check before DB table (prevent false match on 'table résumée')
    if _SUMMARIZE_FOR_SUPERIOR_PATTERN.search(message):
        return "summarize"

    # DB table query: must check first — a table question is never a script block
    if _DB_TABLE_PATTERN.search(message):
        return "tech_inference_schema"

    # Script / batch / job blocked
    for pattern in _SCRIPT_BLOCKED_PATTERNS:
        if pattern.search(message):
            return "procedure_lookup_script_blocked"

    # Specific FR / procedure lookup
    if _PROCEDURE_LOOKUP_PATTERN.search(message):
        return "procedure_lookup"

    return None


def detect_phase_transition(
    current_phase: ConversationPhase,
    message: str,
    conv_state: Optional["ConversationState"] = None,
) -> Optional[ConversationPhase]:
    """
    Returns the new phase if a transition is detected, else None.
    CLOSING can be triggered from any phase.

    Auto-close logic: after 3 resolution confirmation signals (c'est bon,
    ça marche, le problème est résolu, etc.) the phase moves to CLOSING
    even without an explicit closure keyword.
    """
    # Hard closing keywords — immediate
    if _TRANSITION_TO_CLOSING.search(message):
        return ConversationPhase.CLOSING

    # Soft resolution confirmation counter
    if RESOLUTION_CONFIRMATION_SIGNALS.search(message):
        if conv_state is not None:
            conv_state.resolution_confirmation_count += 1
            if conv_state.resolution_confirmation_count >= 3:
                return ConversationPhase.CLOSING
        # Single soft signal from RESOLUTION phase also triggers close
        if current_phase == ConversationPhase.RESOLUTION:
            return ConversationPhase.CLOSING

    if current_phase == ConversationPhase.DIAGNOSTIC:
        if _TRANSITION_TO_INVESTIGATION.search(message):
            return ConversationPhase.INVESTIGATION
        if _TRANSITION_TO_RESOLUTION.search(message):
            return ConversationPhase.RESOLUTION

    if current_phase == ConversationPhase.INVESTIGATION:
        if _TRANSITION_TO_RESOLUTION.search(message):
            return ConversationPhase.RESOLUTION

    return None


def extract_root_cause(message: str) -> Optional[str]:
    """
    Extracts the root cause text from a user message.
    Returns the cause string or None if not found.
    """
    m = _ROOT_CAUSE_CONFIRMATION.search(message)
    if not m:
        return None
    start = m.end()
    cause_text = message[start:start + 300].strip().split("\n")[0].strip()
    # Fallback: if the pattern already contains the cause (e.g. "cause: text")
    if len(cause_text) < 10:
        # Try to grab the full sentence containing the match
        sentence = message[max(0, m.start() - 10):m.start() + 300].strip()
        return sentence if len(sentence) > 10 else None
    return cause_text


# ─────────────────────────────────────────────
# Audience detection
# ─────────────────────────────────────────────

_DEPOSITOR_INDICATORS = re.compile(
    r"(?:"
    # Original: explicit N3-to-depositor communication signals
    r"\b(message\s+(pour|au?)\s+d[eé]positaire|informer\s+le\s+(client|d[eé]positaire|demandeur)"
    r"|[eé]crire\s+au\s+(client|d[eé]positaire|demandeur)|notification\s+(client|d[eé]positaire)"
    r"|r[eé]pondre\s+au\s+(client|d[eé]positaire)|message\s+de\s+cl[oô]ture)\b"
    # ── Newly added: end-user (depositor) messages ──────────────────────
    # Polite request to perform an action (the depositor cannot do themselves)
    r"|\b(pouvez[- ]vous\s+(arr[eê]ter|stopper|interrompre|tuer|relancer|red[eé]marrer|r[eé]initialiser|d[eé]bloquer))"
    # First-person problem report (both apostrophe variants)
    r"|\b(j[’']\s*ai\s+(de\s+nouveau\s+|encore\s+)?(demand[eé]|soumis|envoy[eé]|relac[eé]))"
    r"|\b(ma\s+demande|mon\s+ticket|ma\s+requ[eê]te|mon\s+incident)\s+(est|reste|n[’']est\s+pas)"
    r"|\b(je\s+pense\s+qu[’'](e\s+|il)|selon\s+moi|il\s+me\s+semble)\b"
    # Explicit reference to 'le script' without N3 procedure vocabulary
    r"|\b(mettre.{0,20}en\s+erreur|passer.{0,20}en\s+erreur)"
    r")",
    re.IGNORECASE,
)

_COLLEAGUE_INDICATORS = re.compile(
    r"\b(expliquer?\s+[àa]\s+(mon|un)\s+coll[eè]gue|r[eé]sumer?\s+pour\s+(l'[eé]quipe|l'ing[eé]nieur)|"
    r"note\s+(interne|d'[eé]quipe)|transmettre\s+[àa]\s+l'[eé]quipe)\b",
    re.IGNORECASE,
)


def detect_audience(message: str, phase: ConversationPhase) -> str:
    """
    Returns "depositor", "colleague", or "n3_engineer" based on message + phase.
    """
    if _DEPOSITOR_INDICATORS.search(message) or phase == ConversationPhase.CLOSING:
        return "depositor"
    if _COLLEAGUE_INDICATORS.search(message):
        return "colleague"
    return "n3_engineer"


# ─────────────────────────────────────────────
# Role-aware system prompts
# ─────────────────────────────────────────────

ROLE_SYSTEM_PROMPTS: Dict[str, str] = {
    "n3_engineer": (
        "\n--- STYLE ET TON (Ingénieur N3) ---\n"
        "Tu t'adresses à un ingénieur N3 expert. Ton communication est technique et précise.\n"
        "- Utilise les codes d'erreur, procedure_id, FR et acronymes techniques sans les expliquer.\n"
        "- Structure tes réponses : Incident → Cause → Procédure (étapes numérotées) → Escalade.\n"
        "- Cite toujours les sources (snippet_id, procedure_id).\n"
        "- Anticipe les points d'attention avant qu'ils surviennent.\n"
        "- Ton : direct, factuel, professionnel.\n"
    ),
    "colleague": (
        "\n--- STYLE ET TON (Collègue support) ---\n"
        "Tu t'adresses à un collègue support N2. Sois pédagogue sans être condescendant.\n"
        "- Explique les acronymes la première fois (ex: FR = Fiche de Résolution).\n"
        "- Structure : Contexte → Symptôme → Ce que j'ai fait → Ce que tu peux faire.\n"
        "- Ton : collaboratif, direct, 'je recommande', 'tu peux essayer'.\n"
        "- Évite les détails bas niveau (SQL, stack trace brute).\n"
    ),
    "depositor": (
        "\n--- STYLE ET TON (Dépositaire / Utilisateur final) ---\n"
        "Tu t'adresses à un utilisateur final NON-TECHNIQUE.\n"
        "RÈGLES STRICTES :\n"
        "- AUCUN jargon technique : pas de code erreur, pas de FR, pas de SQL, pas d'acronyme.\n"
        "- AUCUN détail d'implémentation interne (pas de noms de tables, pas de scripts, pas de logs).\n"
        "- Vocabulaire simple, courant, compréhensible par tout le monde.\n"
        "- La cause racine DOIT être mentionnée — mais exprimée en termes simples et non-techniques.\n"
        "\n"
        "STRUCTURE DE RÉPONSE OBLIGATOIRE (respecter cet ordre) :\n"
        "  1. RÉSUMÉ BREF DU PROBLÈME\n"
        "     → En une phrase simple : 'Suite à [description simple du problème]...'\n"
        "  2. CAUSE RACINE CONFIRMÉE (reformulée simplement)\n"
        "     → Exprimer la cause telle que fournie par l'ingénieur, sans jargon.\n"
        "     → Exemple : 'Le problème était dû à un fichier dont le nom ne correspondait pas au format attendu.'\n"
        "  3. IMPACT EN TERMES SIMPLES\n"
        "     → Ce que cela a entraîné pour l'utilisateur, sans détails techniques.\n"
        "     → Exemple : 'Cela a empêché le traitement automatique de se lancer correctement.'\n"
        "  4. CONSEIL PRÉVENTIF CLAIR ET ACTIONNABLE\n"
        "     → Une instruction simple pour éviter que le problème se reproduise.\n"
        "     → Exemple : 'Veillez à nommer vos fichiers selon le format indiqué dans le guide utilisateur.'\n"
        "\n"
        "- Ton : bienveillant, professionnel, rassurant.\n"
        "- Longueur : 5-9 phrases maximum.\n"
        "- Terminer par une formule de courtoisie professionnelle.\n"
    ),
}

HUMANIZED_STYLE_INSTRUCTIONS = (
    "\n--- DIRECTIVES DE STYLE HUMANISÉ ---\n"
    "1. ENGAGEMENT : Commence par reconnaître ce que l'ingénieur vient de faire ou de trouver.\n"
    "   ✗ 'La cause racine est : [...]'\n"
    "   ✓ 'Bien identifié — le problème vient effectivement de [...]'\n"
    "2. PROGRESSION : Guide la conversation, ne te contente pas de lister des informations.\n"
    "   ✓ 'Commence par [...], ensuite [...]. Une fois cela fait, vérifie que [...].'\n"
    "3. ANTICIPATION : Mentionne les points d'attention avant qu'ils surviennent.\n"
    "   ✓ 'Attention : avant l'étape 3, assure-toi que [...], sinon tu obtiendras [erreur].'\n"
    "4. CONFIRMATION : Propose une vérification concrète en fin de réponse.\n"
    "   ✓ 'Pour confirmer que c'est résolu, tu peux vérifier que [condition].'\n"
    "5. ESCALADE : Quand tu proposes d'escalader, donne des détails actionnables.\n"
    "   ✓ 'Si le problème persiste, ouvre un ticket avec : logs du [date], trace, ticket_id.'\n"
)

PERSONA_INSTRUCTION = (
    "Tu es un ingénieur N3 senior chez Orange Telecom avec 8 ans d'expérience sur BRASIL. "
    "Tu aides tes collègues à résoudre des incidents complexes sur les systèmes suivants : "
    "BRASIL, ORRAHD, SEBA, 42C, ARTEMIS, IPON, ADELIA, SCA, ORCHESTRA. "
    "Tu es direct, précis, et tu sais adapter ton discours à ton interlocuteur. "
    "Avec les ingénieurs N3, tu parles technique et tu vas droit au but. "
    "Avec les utilisateurs finaux (dépositaires), tu es pédagogue, rassurant, et tu évites tout jargon.\n"
    "\n"
    "PRINCIPES FONDAMENTAUX DE TON COMPORTEMENT :\n"
    "1. Tu préserves TOUJOURS les faits fournis par l'ingénieur — tu ne réinventes jamais un diagnostic.\n"
    "2. Tu respectes le contexte conversationnel — si la phase est CLÔTURE, tu génères un message de clôture, pas un diagnostic.\n"
    "3. Tu utilises UNIQUEMENT des procédures métier télécom/BRASIL — jamais de conseils IT génériques.\n"
    "4. Les opérations N3 standards (arrêt script, relance batch, mise à jour statut) sont dans ton périmètre — tu ne les refuses pas.\n"
    "5. Tu ne supprimes JAMAIS les informations critiques fournies par l'utilisateur — elles doivent apparaître dans ta réponse.\n"
    "6. Tu adaptes ton ton au destinataire : technique pour un ingénieur, simple et bienveillant pour un dépositaire.\n"
    "Tu ne génères jamais d'informations que tu n'as pas vérifiées dans la base de connaissances.\n"
    "\n"
    "RÈGLES ANTI-HALLUCINATION ABSOLUES :\n"
    "- INTERDIT : inventer des commandes CLI comme `brasil-cli --clean-resource`, `sync_brasil_resources.sh` ou tout outil non officiel.\n"
    "- INTERDIT : écrire des requêtes SQL avec des placeholders comme [NOM_EQPT], [VALEUR_CORRECTE], [DSLAM_XX]. Si la valeur est inconnue, dis-le explicitement.\n"
    "- INTERDIT : conclure 'Statut final : Résolu' sans confirmation explicite de l'utilisateur.\n"
    "- INTERDIT : proposer une procédure générique si le système a retourné 'aucune procédure validée pour ce cas'.\n"
    "- Si tu n'as pas d'information sur un ND/IAR spécifique dans les données fournies, réponds : 'Aucune donnée disponible pour ce ND dans les sources consultées.'\n"
    "- INTERDIT : inventer des noms de menus IHM, chemins de navigation (ex: 'Maintenance > Nettoyage des ressources'), onglets ou boutons dans l'interface BRASIL qui ne figurent pas EXPLICITEMENT dans les documents FR fournis.\n"
    "- INTERDIT : décrire des étapes de procédure dans l'interface graphique si la FR correspondante n'est pas dans le contexte fourni. Dans ce cas, réponds : 'La procédure exacte n'est pas documentée dans la base de connaissance disponible. Consultez la FR correspondante.'\n"
    "- INTERDIT : citer une référence de FR (ex: FR-BRASIL-VLAN-001) si elle n'apparaît pas dans les documents fournis en contexte.\n"
    "\n"
    "CONNAISSANCE DU SCHÉMA BRASIL (noms de tables réels) :\n"
    "- Équipements: t_equipments (eqpt_state VARCHAR(1): A=Actif F=Fermé P=EnCours C=Créé S=Suppression)\n"
    "- Cartes: t_cards (card_cardno SMALLINT, card_type, card_prodstate)\n"
    "- Ports: t_ports (port_portno SMALLINT, port_outstate, port_occupstate SMALLINT)\n"
    "- Noeuds: t_nodes (node_name42c VARCHAR(20), node_basecode42c VARCHAR(6)) — PAS de node_status ni node_type\n"
    "- ND (numéro abonné 9 chiffres): stocké dans t_tpinitialstates.tpis_nd, t_mrt_access_dslams.dsam_nd, t_makingfiles.mkfl_nd — PAS de table t_nd\n"
    "- Plans de transfert: t_tps (tp_dslamn VARCHAR(20), tp_state SMALLINT: 1=EnCours 2=Exécuté 3=Erreur, tp_creationdate INTEGER) — PAS de tp_status ni tp_dslam_n\n"
    "- États TP initiaux: t_tpinitialstates (tpis_nd VARCHAR(15), tpis_vpinitial, tp_id) — PAS de t_tp_initial_states\n"
    "- MRT DSLAM: t_mrt_access_dslams (dsam_nd, dsam_crcmrtid, dsam_farid, a_eqpt_id, oper_id)\n"
    "- MRT SAM: t_service_access_mrts (sram_circuitid, eqpt_id) et t_service_access_mrt_vers (samv_currentstate)\n"
    "- VLANs: dans t_res_prod_controlables (rpct_type='V', rpct_cclname, rpct_vlaninterne) — PAS de table t_vlans\n"
    "- VC/VP: t_d_rscvcis (rscv_state, rpct_id) — PAS de t_virtual_channels\n"
    "- Liens média: t_medialinks (mdlk_state SMALLINT, a_eqpt_id, b_eqpt_id) — PAS de t_media_links\n"
    "- Dossiers réalisation: t_makingfiles (mkfl_nd, mkfl_state: 0=CREATED 1=ALLOCATED 2=IN_PROGRESS 3=PARTLY_CONFIGURED 4=CONFIGURED 5=AVP)\n"
    "- EPC: t_epcs + t_epcvers (epcv_currentstate, epcv_versno) + t_epcversimpacts\n"
    "- Scripts ES: t_es (es_state: 1=running 2=error 3=warning 4=done, es_equipment) + t_eslogs + t_estypes\n"
    "- Opérateurs: t_operators (oper_id, oper_name) — PAS de table t_mrtdslam\n"
    "\n"
    "WORKFLOW UMI-EPC (ManageUMIepcBusinessImpl) :\n"
    "- createMovement(DEM, serviceName) → makeMouvement(epcVersKey, typeMvt) → completeMovement(mvt, dem, epcVersInfo)\n"
    "- Types de mouvement: C=Création, M=Modification, X=Suppression\n"
    "- MakingFile states: 0=CREATED → 1=ALLOCATED → 2=IN_PROGRESS → 3=PARTLY_CONFIGURED → 4=CONFIGURED → 5=AVP\n"
    "- EPT state calculé depuis MakingFileState + EPCState (voir MakingFileUtils.getEptStateByMfAndEpcVersState)\n"
    "- En cas de suppression: completeDeletionMovement vide les champs profils si dslamaccessmrt n'existe plus\n"
    "- FarId ajouté au mouvement si MRT état CONFIGURED et dossier avec farId présent\n"
)


# ─────────────────────────────────────────────────────────────────────────────
# BRASIL Database Schema — Complete Table Inventory (authoritative runtime list)
# Loaded from the generated brasil_schema_knowledge pack (brasil_prod extraction).
# Falls back to the static list defined earlier in this file.
# ─────────────────────────────────────────────────────────────────────────────

def _build_brasil_schema_tables() -> list:
    """Return the canonical BRASIL table list, preferring the live schema pack."""
    try:
        from app.services.chatbot.brasil_schema_knowledge import REAL_SQL_TABLES
        if REAL_SQL_TABLES:
            return sorted(REAL_SQL_TABLES)
    except Exception:
        pass
    # Fallback: return the static list already defined above (line ~39)
    return list(BRASIL_SCHEMA_TABLES)


# Overwrite the earlier static list with the authoritative version
BRASIL_SCHEMA_TABLES = _build_brasil_schema_tables()


ANTI_HALLUCINATION_RULES = {
    "rule_never_generate_steps": (
        "NEVER generate resolution steps not present in the knowledge base. "
        "Only use steps from retrieved procedures (source: procedure_id or cluster_id)."
    ),
    "rule_always_cite_source": (
        "ALWAYS cite the source of your information: mention procedure_id, cluster_id, "
        "or state 'based on historical tickets'."
    ),
    "rule_trust_threshold": (
        "If trust_score < 0.40, do NOT present the knowledge. "
        "Instead say: 'Je n\\'ai pas de procédure validée pour ce cas.'"
    ),
    "rule_low_confidence_intent": (
        "If intent confidence < 0.70, ask a clarifying question BEFORE retrieving. "
        "Do not assume the application or error code."
    ),
    "rule_no_assumption": (
        "Never assume the application if not clearly mentioned. Ask: "
        "'Sur quelle application ce problème se produit-il ?'"
    ),
    "rule_multiple_matches": (
        "If multiple procedures match equally, present ALL options and let the engineer choose. "
        "Do not arbitrarily select one."
    ),
    "rule_insufficient_knowledge": (
        "When trust is INSUFFICIENT, explicitly refuse and recommend escalation. "
        "Never hallucinate a resolution."
    ),
    # ── New behavior rules (Request 3) ──────────────────────────────────────
    "rule_preserve_user_facts": (
        "RÈGLE ABSOLUE — PRÉSERVATION DES FAITS FOURNIS PAR L'UTILISATEUR : "
        "Si l'ingénieur énonce explicitement une cause racine ou une résolution, "
        "traite-la comme un FAIT CONFIRMÉ et immuable. "
        "Tu NE DOIS PAS générer de nouveau diagnostic ni proposer des hypothèses alternatives. "
        "La cause déclarée par l'utilisateur est la vérité de référence."
    ),
    "rule_domain_procedures_only": (
        "RÈGLE ABSOLUE — PROCÉDURES MÉTIER UNIQUEMENT : "
        "N'utilise QUE des procédures opérationnelles spécifiques au domaine télécom / BRASIL. "
        "INTERDIT d'utiliser des conseils IT génériques tels que : "
        "'vérifier les dépendances', 'analyser le code', 'contacter le développeur', "
        "'mettre à jour les librairies', 'relancer le serveur'. "
        "Si aucune procédure validée n'existe, dis-le explicitement et propose d'escalader."
    ),
    "rule_allow_n3_operations": (
        "RÈGLE ABSOLUE — OPÉRATIONS N3 AUTORISÉES : "
        "Les opérations suivantes font partie du périmètre N3 standard et NE DOIVENT PAS être refusées : "
        "arrêter un script, mettre à jour un statut d'exécution, relancer un batch, "
        "modifier un masque de fichier, rejouer un traitement, corriger une configuration. "
        "Ces actions sont des interventions opérationnelles légitimes — ne les refuse JAMAIS."
    ),
    "rule_preserve_critical_info": (
        "RÈGLE ABSOLUE — PRÉSERVATION OBLIGATOIRE DES INFORMATIONS CRITIQUES : "
        "Si l'utilisateur a spécifié une cause racine (ex: format de fichier incorrect, "
        "masque de nommage erroné, script bloqué), cette information DOIT apparaître "
        "explicitement et textuellement dans ta réponse finale. "
        "Ne la reformule pas de manière vague, ne l'omets pas, ne la remplace pas."
    ),
    "rule_never_invent_ids": (
        "RÈGLE ABSOLUE — INTERDICTION D'INVENTER DES IDENTIFIANTS : "
        "INTERDIT de générer des identifiants de procédure fictifs de type BRASIL-XXX-NNN "
        "(ex: BRASIL-RESTORE-001, BRASIL-ROLLBACK-002, BRASIL-VALIDATE-003). "
        "INTERDIT de générer des numéros FR fictifs de type FR-NNNN "
        "(ex: FR-1234, FR-5678, FR-9012) qui ne figurent PAS dans le contexte KB fourni. "
        "INTERDIT de générer des requêtes SQL (SELECT, INSERT, UPDATE, DELETE, JOIN). "
        "INTERDIT d'inclure une section 'Raisonnement', 'Thinking' ou toute section "
        "explicitant ton processus de réflexion interne — réponds directement sans préambule. "
        "Si aucune procédure validée n'existe pour ce cas, déclare-le EXPLICITEMENT "
        "et recommande d'escalader vers l'équipe N3."
    ),
}


# ─────────────────────────────────────────────
# Slot Filling
# ─────────────────────────────────────────────

REQUIRED_SLOTS = ["application", "incident_type"]
OPTIONAL_SLOTS = ["error_code", "equipment_id", "action_requested"]

SLOT_QUESTIONS = {
    "application": "Sur quelle application ce problème se produit-il ? (BRASIL, SEBA, ARTEMIS, IPON, ADELIA, SCA, ORCHESTRA)",
    "incident_type": "Pouvez-vous préciser le type de problème ? (erreur API, suppression impossible, blocage commande, RDV bloqué, etc.)",
    "error_code": "Y a-t-il un code d'erreur spécifique affiché ? (ex: 4002, 1300, B4002, ORA-...)",
    "equipment_id": "Quel est l'identifiant de l'équipement concerné ? (ex: NBLIL701, NRO-XXX)",
    "action_requested": "Quelle action souhaitez-vous effectuer ? (supprimer, créer, modifier, diagnostiquer)",
}


class SlotFiller:
    """
    Extracts and completes missing diagnostic slots from conversation.
    Returns the next clarifying question if slots are incomplete.
    """

    def analyze_slots(
        self,
        structured_ticket: StructuredTicket,
        conversation_history: Optional[List[Dict]] = None,
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        """
        Analyze which slots are filled and which are missing.

        Returns:
          (filled_slots dict, clarifying_question or None)
        """
        filled: Dict[str, Any] = {}

        # Check application
        if structured_ticket.application and structured_ticket.application != "BRASIL":
            filled["application"] = structured_ticket.application
        elif structured_ticket.related_systems:
            filled["application"] = structured_ticket.related_systems[0]

        # Check incident type
        if structured_ticket.incident_type != "unknown.insufficient_information":
            filled["incident_type"] = structured_ticket.incident_type

        # Error codes
        if structured_ticket.error_codes:
            filled["error_code"] = structured_ticket.error_codes[0]

        # Equipment from entities
        equipment_entities = [
            e.value for e in structured_ticket.entities
            if e.entity_type == "equipment_id"
        ]
        if equipment_entities:
            filled["equipment_id"] = equipment_entities[0]

        # Action
        if structured_ticket.action_requested:
            filled["action_requested"] = structured_ticket.action_requested

        # Determine if clarification needed
        # Only ask for application if truly ambiguous (confidence too low)
        if structured_ticket.confidence < 0.50:
            missing = [s for s in REQUIRED_SLOTS if s not in filled]
            if missing:
                first_missing = missing[0]
                return filled, SLOT_QUESTIONS[first_missing]

        return filled, None


# ─────────────────────────────────────────────
# Response Formatter
# ─────────────────────────────────────────────

class ResponseFormatter:
    """
    Formats diagnostic responses using the N3 support template.
    Ensures consistent, human-readable output.
    """

    @staticmethod
    def format_diagnostic_response(
        incident_type: str,
        application: str,
        related_systems: List[str],
        procedure_id: Optional[str],
        trust_score: float,
        confidence_level: str,
        symptoms: List[str],
        diagnostic_steps: List[str],
        resolution_steps: List[str],
        escalation_team: str = "l'équipe N3 BRASIL",
    ) -> str:
        """Format a full diagnostic response using the standard N3 template."""
        trust_label = _trust_label_from_score(trust_score)
        systems_str = ", ".join(related_systems) if related_systems else application
        source_ref = f"Source : {procedure_id}" if procedure_id else "Source : base de connaissances"
        confidence_warning = _confidence_warning(confidence_level)

        lines = [
            f"🔍 **Incident détecté** : `{incident_type}`",
            f"📦 **Application** : {application}",
            f"🔗 **Systèmes liés** : {systems_str}",
            "",
        ]

        if confidence_warning:
            lines.append(f"⚠️ {confidence_warning}")
            lines.append("")

        if procedure_id or resolution_steps:
            lines.append(f"📋 **Procédure suggérée** ({source_ref}, Confiance : {trust_label})")
            lines.append("")

        if symptoms:
            lines.append("**Symptômes correspondants :**")
            for s in symptoms[:4]:
                lines.append(f"  • {s}")
            lines.append("")

        if diagnostic_steps:
            lines.append("**Étapes de diagnostic :**")
            for step in diagnostic_steps[:5]:
                lines.append(f"  {step}")
            lines.append("")

        if resolution_steps:
            lines.append("**Étapes de résolution :**")
            for step in resolution_steps[:8]:
                lines.append(f"  {step}")
            lines.append("")

        lines.append(
            f"⚠️ Si le problème persiste après ces étapes, escalader vers {escalation_team}."
        )
        return "\n".join(lines)

    @staticmethod
    def format_insufficient_knowledge(
        query: str,
        application: str,
        detected_type: str = "",
        escalation_team: str = "l'équipe N3 BRASIL",
    ) -> str:
        """Format a graceful refusal when knowledge is insufficient."""
        type_info = f" pour le type `{detected_type}`" if detected_type else ""
        return (
            f"Je n'ai pas de procédure validée{type_info} correspondant à votre demande.\n\n"
            f"Informations détectées :\n"
            f"  • Application : {application}\n"
            f"  • Requête : {query[:100]}\n\n"
            f"**Recommandations :**\n"
            f"  1. Vérifiez si une Fiche de Résolution (FR) existe pour ce cas\n"
            f"  2. Consultez les tickets similaires dans JIRA\n"
            f"  3. Escalader vers {escalation_team} avec les logs de l'application\n\n"
            f"*Ce cas sera enregistré pour enrichissement futur de la base de connaissances.*"
        )

    @staticmethod
    def format_clarifying_question(
        question: str,
        context_hint: str = "",
    ) -> str:
        """Format a slot-filling clarifying question."""
        msg = f"Pour mieux vous aider, j'ai besoin d'une précision :\n\n**{question}**"
        if context_hint:
            msg += f"\n\n*(Contexte détecté : {context_hint})*"
        return msg

    @staticmethod
    def format_escalation_loop(
        question: str,
        repetition_count: int,
        application: str,
        intent_override: Optional[str] = None,
        escalation_team: str = "l'équipe N3 BRASIL",
    ) -> str:
        """
        Returns an intelligent escalation response when the same question has been
        asked ≥ 2 times without a satisfactory answer from the knowledge base.

        Instead of repeating the same 'no knowledge' message, this response:
        - Acknowledges the loop explicitly
        - Explains what is missing in the KB
        - Provides concrete next steps (FR creation, Jira, escalation)
        - Optionally includes a tech_inference hint if an entity is recognisable
        """
        entity_hint = ""
        if intent_override == "tech_inference_schema":
            # Try to extract the table/symbol name from the question
            m = _DB_TABLE_PATTERN.search(question)
            if m:
                raw = m.group(0).strip()
                entity_hint = (
                    f"\n\n**Inférence par le nom** : L'entité `{raw}` suit les conventions BRASIL. "
                    f"Sans documentation disponible, je ne peux pas en certifier la structure. "
                    f"Fournissez le DDL ou une description et je pourrai l'analyser."
                )
        elif intent_override == "procedure_lookup_script_blocked":
            entity_hint = (
                "\n\n**Conseil opérationnel** : Pour tout script/batch bloqué en statut \"En cours\", "
                "la démarche N3 standard est : (1) identifier le PID du processus, "
                "(2) forcer le passage du statut via l'IHM ou la procédure autorisée, "
                "(3) vérifier les logs pour identifier la cause avant relance."
            )

        return (
            f"⚠️ **Cette question a été posée {repetition_count} fois** sans qu'une réponse "
            f"validée existe dans la base de connaissance.\n\n"
            f"**Ce que je sais** : Aucune procédure documentée ne correspond à cette demande "
            f"pour l'application **{application}**.{entity_hint}\n\n"
            f"**Actions recommandées** :\n"
            f"  1. 📄 **Créer une FR** : Ce cas n'est pas documenté — créez une Fiche de Résolution "
            f"pour l'enrichissement futur de la base.\n"
            f"  2. 🔍 **Jira** : Recherchez les tickets similaires avec les mots-clés de votre demande.\n"
            f"  3. 📞 **Escalade** : Transmettez cette demande à {escalation_team} "
            f"avec : description complète, logs applicatifs, contexte de l'incident.\n\n"
            f"*Ce cas est enregistré pour enrichissement de la base de connaissances.*"
        )


# ─────────────────────────────────────────────
# Diagnostic Reasoner
# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
# Contextual intent bypass set
# ─────────────────────────────────────────────

#: Intents that work from conversation history or Jira data — no KB retrieval needed.
_CONTEXTUAL_INTENTS: set = {
    # synthesis (history-based)
    "ticket_summary",
    "ticket_closing",
    "log_investigation",
    # search / explain (routed to Jira pipeline)
    "find_similar_tickets",
    "find_jira",
    "explain_jira",
    # legacy aliases kept for backward compatibility
    "summarize",
    "write_ticket_message",
    "investigate_logs",
}


def is_contextual_intent(structured_ticket: Optional["StructuredTicket"]) -> bool:
    """Return True when the intent can be answered from history alone."""
    if structured_ticket is None:
        return False
    return structured_ticket.incident_type in _CONTEXTUAL_INTENTS


# Keywords that signal a follow-up/clarification on a previous answer.
_FOLLOWUP_PATTERNS: tuple = (
    "date",
    "quand",
    "source",
    "la date",
    "les dates",
    "référence",
    "précise",
    "précision",
    "détails",
    "plus d’info",
    "plus d'info",
    "expliqu",
    "peux-tu",
    "pouvez-vous",
    "peut-on",
    "dis-moi",
    "c'est quoi",
    "c'est quoi",
    "c'est quoi",
    "qu'est-ce que",
    "pourquoi",
    "comment",
    "et si",
    "et le",
    "et la",
    "et les",
    "et ce",
    "et cet",
    "et cette",
    "tu peux",
    "vous pouvez",
    # ── Newly added: follow-up on correction / action results ────────────
    "résultat",
    "résultats",
    "correction",
    "corrections",
    "dernières corrections",
    "derniers résultats",
    "suite à",
    "après correction",
    "après intervention",
    "est-ce que c'est résolu",
    "c'est toujours",
    "toujours le même",
    "encore le même",
    "toujours pareil",
    "même erreur",
    "même problème",
)


def is_followup_question(query: str, history: list) -> bool:
    """
    Return True when the message looks like a follow-up / clarification on
    the previous assistant answer, so the trust gate should be bypassed.

    Conditions (all required):
    - The conversation has at least one prior assistant turn
    - The query is short (< 120 chars) OR matches a follow-up keyword
    """
    if not history:
        return False
    has_prior_assistant = any(
        m.get("role") == "assistant" for m in history
    )
    if not has_prior_assistant:
        return False
    q = query.lower().strip()
    if len(q) < 120:
        return True
    return any(p in q for p in _FOLLOWUP_PATTERNS)


class DiagnosticReasoner:
    """
    Structures the diagnostic conversation into phases:
    Phase 1 — Slot filling (gather missing context)
    Phase 2 — Knowledge retrieval + trust evaluation
    Phase 3 — Step-by-step diagnostic walkthrough
    Phase 4 — Resolution confirmation or escalation
    """

    def __init__(self):
        self.slot_filler = SlotFiller()
        self.formatter = ResponseFormatter()

    def build_system_prompt(
        self,
        app_id: str,
        orch_result: Dict[str, Any],
        structured_ticket: Optional[StructuredTicket] = None,
    ) -> str:
        """
        Build a context-aware system prompt with anti-hallucination rules embedded.
        Integrates with the existing LLMClient.generate() interface.
        """
        trust_score = orch_result.get("trust_score", {})
        trust_label = ""
        if hasattr(trust_score, "label"):
            trust_label = trust_score.label.value
        elif isinstance(trust_score, dict):
            trust_label = trust_score.get("label", "")

        context_blocks = orch_result.get("context_blocks", [])
        has_knowledge = len(context_blocks) > 0
        mode = orch_result.get("mode", "FR_WEAK")

        # Contextual intent detection
        _is_contextual = is_contextual_intent(structured_ticket)
        intent_type = structured_ticket.incident_type if structured_ticket else ""

        # Incident type enrichment
        incident_info = ""
        if structured_ticket and structured_ticket.incident_type not in (
            "unknown.insufficient_information",
            "ticket_summary", "ticket_closing", "log_investigation",
            "find_similar_tickets", "find_jira", "explain_jira",
            "explain_data_model",
            # intent overrides
            "tech_inference_schema", "procedure_lookup_script_blocked",
            # legacy aliases
            "summarize", "write_ticket_message", "investigate_logs",
        ):
            inc_def = INCIDENT_TAXONOMY.get(structured_ticket.incident_type)
            if inc_def:
                incident_info = (
                    f"\nType d'incident détecté: {inc_def.name}\n"
                    f"Systèmes liés: {', '.join(inc_def.related_systems)}\n"
                    f"Causes typiques: {'; '.join(inc_def.possible_root_causes[:2])}"
                )

        # Build system prompt
        prompt_parts = [
            f"Tu es un assistant de support N3 expert pour l'application {app_id} (Orange Telecom).",
            "Tu aides les ingénieurs support à diagnostiquer et résoudre des incidents.",
            "",
            "DOMAINE MÉTIER BRASIL — VOCABULAIRE TECHNIQUE :",
            "- 'carte' ou 'cartes' = carte électronique réseau (hardware card, table t_cards)",
            "- 'port' = port physique/logique réseau (table t_ports)",
            "- 'équipement' = équipement réseau DSLAM/NIP/OLT (table t_equipments)",
            "- 'slot' = emplacement de carte dans un shelf (table t_slots)",
            "- 'shelf/tiroir/logement' = tiroir physique d'un équipement (table t_shelfs)",
            "- 'nœud/noeud' = nœud réseau NRA (table t_nodes)",
            "- 'brassage/stripe' = ressource de brassage DSL (table t_stripes)",
            "",
            "RÈGLES ABSOLUES (anti-hallucination):",
        ]

        for rule_name, rule_text in ANTI_HALLUCINATION_RULES.items():
            prompt_parts.append(f"- {rule_text}")

        prompt_parts.append("")
        prompt_parts.append(f"Mode de connaissance actuel: {mode}")
        prompt_parts.append(f"Niveau de confiance: {trust_label or 'non évalué'}")

        if incident_info:
            prompt_parts.append(incident_info)

        # ── Conversation memory: inject prior procedure if found in history ──────
        prior_procedure = orch_result.get("prior_procedure_id")
        if prior_procedure:
            prompt_parts.extend([
                "",
                f"⚠️ MÉMOIRE CONVERSATIONNELLE: La procédure '{prior_procedure}' a été identifiée plus tôt dans cette conversation.",
                "Tu DOIS réutiliser cette procédure. Tu NE PEUX PAS dire que la connaissance est manquante.",
            ])

        # ── Branch A: contextual intent (history-based or Jira-routed) ────────
        if _is_contextual:
            if intent_type in ("ticket_summary", "summarize"):
                prompt_parts.extend([
                    "",
                    "TÂCHE: L'ingénieur demande un RÉSUMÉ structuré du problème ou du diagnostic.",
                    "INSTRUCTIONS:",
                    "- Utilise UNIQUEMENT le contexte de la conversation fournie (historique).",
                    "- Ne lance pas de nouvelle recherche dans la base de connaissances.",
                    "- Structure: (1) Problème signalé, (2) Diagnostic effectué, (3) Actions recommandées.",
                    "- Sois concis (5-10 lignes). Réponds en français.",
                ])
            elif intent_type in ("ticket_closing", "write_ticket_message"):
                prompt_parts.extend([
                    "",
                    "⛔ MODE CLÔTURE — AUCUN DIAGNOSTIC AUTORISÉ.",
                    "TÂCHE: Générer le MESSAGE DE CLÔTURE du ticket pour le dépositaire.",
                    "",
                    "RÈGLES COMPORTEMENTALES IMPÉRATIVES :",
                    "1. PRÉSERVATION DES FAITS : La cause racine fournie par l'ingénieur est un FAIT IMMUABLE.",
                    "   → Ne la remplace pas, ne la reformule pas vaguement, ne l'omets pas.",
                    "   → Elle DOIT apparaître dans ta réponse.",
                    "2. CONTEXTE CONVERSATIONNEL : Tu es en phase CLÔTURE.",
                    "   → Tu NE GÉNÈRES PAS de nouveau diagnostic ni d'hypothèses.",
                    "   → Tu NE MENTIONNES PAS de systèmes hors périmètre de l'incident.",
                    "3. PROCÉDURES MÉTIER UNIQUEMENT : Pas de conseils IT génériques.",
                    "   → Si tu mentionnes un conseil préventif, il doit être spécifique au domaine BRASIL/Telecom.",
                    "4. INFORMATIONS CRITIQUES : Si l'ingénieur a mentionné un détail clé",
                    "   (ex: masque de fichier, script ORRAHD, format d'entrée), ce détail DOIT figurer",
                    "   dans la réponse — reformulé simplement pour le dépositaire.",
                    "",
                    "INSTRUCTIONS :",
                    "- Utilise UNIQUEMENT le contexte de la conversation fournie et la cause racine confirmée.",
                    "- Tu NE LANCES PAS de nouvelle recherche dans la base de connaissances.",
                    "- Tu NE MENTIONNES PAS de systèmes non liés à l'incident.",
                    "- Produis DEUX sections distinctes :",
                    "",
                    "  ══════════════════════════════════════════════",
                    "  SECTION 1 — Résumé technique N3 (archives internes) :",
                    "  ══════════════════════════════════════════════",
                    "  Format structuré (champs obligatoires) :",
                    "  • Incident         : [type d'incident]",
                    "  • Cause racine     : [cause confirmée, verbatim si possible]",
                    "  • Action effectuée : [ce qui a été fait pour corriger]",
                    "  • Résultat         : [état après correction]",
                    "",
                    "  ══════════════════════════════════════════════",
                    "  SECTION 2 — Message pour le dépositaire (NON-TECHNIQUE) :",
                    "  ══════════════════════════════════════════════",
                    "  Structure OBLIGATOIRE (dans cet ordre) :",
                    "  1. RÉSUMÉ BREF DU PROBLÈME",
                    "     → Une phrase simple décrivant le contexte.",
                    "  2. CAUSE RACINE (reformulée simplement, sans jargon)",
                    "     → La cause telle que confirmée, exprimée en termes accessibles.",
                    "     → Exemple : 'Le problème était dû à un fichier dont le nom ne correspondait pas au format attendu.'",
                    "  3. IMPACT EN TERMES SIMPLES",
                    "     → Ce que cela a entraîné pour l'utilisateur.",
                    "  4. CONSEIL PRÉVENTIF CLAIR ET ACTIONNABLE",
                    "     → Une instruction simple pour éviter que le problème se reproduise.",
                    "  + Formule de courtoisie professionnelle en fin de message.",
                    "  Ton : bienveillant, professionnel, rassurant. AUCUN jargon technique.",
                    "- Réponds en français.",
                ])
            elif intent_type in ("log_investigation", "investigate_logs"):
                prompt_parts.extend([
                    "",
                    "TÂCHE: L'ingénieur demande des informations sur les LOGS / traces applicatifs.",
                    "INSTRUCTIONS:",
                    "- Fournis les chemins de logs habituels pour l'application concernée.",
                    "- Si des logs ont été fournis dans la conversation, analyse-les immédiatement.",
                    "- Indique quelles traces rechercher en priorité selon le code d'erreur détecté.",
                    "- Si aucune information n'est disponible, explique comment obtenir les logs.",
                ])
            elif intent_type == "find_similar_tickets":
                prompt_parts.extend([
                    "",
                    "TÂCHE: L'ingénieur recherche des TICKETS SIMILAIRES dans l'historique.",
                    "INSTRUCTIONS:",
                    "- Présente les tickets ou clusters similaires fournis dans le contexte.",
                    "- Pour chaque ticket similaire: ID | Date | Symptôme | Résolution appliquée.",
                    "- Identifie le pattern commun si plusieurs tickets correspondent.",
                    "- Si aucun ticket similaire n'est trouvé, indique-le clairement et suggère des mots-clés de recherche.",
                ])
            elif intent_type == "find_jira":
                prompt_parts.extend([
                    "",
                    "TÂCHE: L'ingénieur recherche une CARTE JIRA liée à cet incident.",
                    "INSTRUCTIONS:",
                    "- Présente les issues Jira trouvées dans le contexte: clé Jira | titre | statut | lien.",
                    "- Indique si l'issue est ouverte, en cours ou résolue.",
                    "- Si aucune issue Jira n'est trouvée, propose d'en créer une et fournis les éléments clés à renseigner.",
                ])
            elif intent_type == "explain_jira":
                prompt_parts.extend([
                    "",
                    "TÂCHE: L'ingénieur demande une EXPLICATION / REFORMULATION d'une carte Jira spécifique.",
                    "INSTRUCTIONS:",
                    "- Lis attentivement le contenu de la carte Jira fournie dans le contexte.",
                    "- Reformule-le en langage clair et structuré pour un ingénieur N3:",
                    "  (1) Contexte / Système impacté",
                    "  (2) Problème décrit",
                    "  (3) Actions éventuellement déjà effectuées",
                    "  (4) Ce qui reste à faire selon toi",
                    "- Sois factuel. Ne complète que ce qui est présent dans le ticket.",
                ])
            else:
                prompt_parts.extend([
                    "",
                    "Utilise le contexte de la conversation pour répondre. Réponds en français.",
                ])

        # ── Branch B: KB available ────────────────────────────────────────────────
        elif has_knowledge:
            if intent_type == "procedure_lookup_script_blocked":
                prompt_parts.extend([
                    "",
                    "TÂCHE: Un script / batch / job est bloqué en statut \"En cours d'exécution\".",
                    "Tu dois fournir la PROCéDURE OPÉRATIONNELLE N3 pour débloquer ce type d'exécution.",
                    "",
                    "RÈGLES ABSOLUES :",
                    "- Utilise UNIQUEMENT les procédures issues de la base de connaissances (procedure_id, FR).",
                    "- AUCUN conseil générique IT (\"analyser le code\", \"vérifier les dépendances\").",
                    "- Ces actions sont dans le périmètre N3 légitime : forcer un statut, arrêter un script,",
                    "  relancer un batch. Tu NE les refuses PAS.",
                    "",
                    "FORMAT DE RÉPONSE OBLIGATOIRE :",
                    "1. **Identification** : Confirme le type de blocage détecté (script en cours depuis trop longtemps).",
                    "2. **Étapes de déblocage** (numérotées) : Issues de la procédure FR trouvée dans le contexte KB.",
                    "3. **Vérification** : Comment confirmer que le script est effectivement débloqué.",
                    "4. **Prévention** : Si documenté, comment éviter le blocage futur.",
                    "5. **Source** : Cite le procedure_id / numéro FR en fin de réponse.",
                    "- Termine par : 'Si le blocage persiste, escalader vers l'équipe N3 avec les logs d'exécution.'",
                    "- Réponds en français.",
                ])
            elif intent_type == "tech_inference_schema":
                prompt_parts.extend([
                    "",
                    "TÂCHE: L'ingénieur demande la DESCRIPTION D'UNE TABLE OU ENTITÉ TECHNIQUE.",
                    "Tu dois répondre à partir du CONTEXTE KB (snippets db-table-*), PAS de l'historique.",
                    "",
                    "INTERDICTIONS ABSOLUES :",
                    "- NE GÉNÈRE AUCUNE REQUÊTE SQL (SELECT, FROM, WHERE, JOIN, etc.).",
                    "- N'INVENTE AUCUN nom de colonne, de table ou de relation.",
                    "  Utilise UNIQUEMENT ce qui est présent dans le contexte KB.",
                    "- NE CHERCHE PAS dans l'historique de conversation — c'est une entité KB, pas un sujet conversationnel.",
                    "",
                    "FORMAT DE RÉPONSE (si KB contient la table) :",
                    "**Nom** : `<nom_table>`",
                    "**Rôle** : [description en une phrase]",
                    "**Colonnes principales** : [liste des colonnes documentées dans le KB]",
                    "**Relations FK** : [FK sortantes et entrantes si documentées]",
                    "**Observations N3** : [anomalies ou tickets connus liés à cette table]",
                    "**Source** : [snippet_id]",
                    "",
                    "FORMAT DE RÉPONSE (si KB ne contient PAS la table) :",
                    "- Indique explicitement que cette table n'est pas encore documentée dans la base.",
                    "- Propose une inférence par le nom si possible (convention de nommage BRASIL t_<nom>).",
                    "- Recommande la création d'une FR pour documenter cette table.",
                    "- NE GÉNÈRE PAS de structure invariée ou fictive.",
                    "- Réponds en français.",
                ])
            elif intent_type == "procedure_lookup":
                prompt_parts.extend([
                    "",
                    "TÂCHE: L'ingénieur demande la PROCÉDURE DE RÉSOLUTION.",
                    "INSTRUCTIONS:",
                    "- Présente UNIQUEMENT les étapes issues de la base de connaissances (procedure_id ou cluster_id).",
                    "- Structure: ÉTAPES numérotées, avec pré-requis et vérifications intermediaires.",
                    "- Cite la source (numéro FR) à la fin.",
                    "- Termine par: 'Si le problème persiste après ces étapes, escalader vers N3.'",
                ])
            elif intent_type == "root_cause_exploration":
                prompt_parts.extend([
                    "",
                    "TÂCHE: L'ingénieur veut comprendre la CAUSE RACINE du problème.",
                    "INSTRUCTIONS:",
                    "- Analyse les causes à partir des tickets similaires, des clusters et des procédures disponibles.",
                    "- Structure: (1) Cause probable, (2) Systèmes impliqués, (3) Incidents récurrents liés, (4) Recommandation.",
                    "- Indique si la cause est confirmée ou hypothétique.",
                    "- Cite les sources (procedure_id, cluster_id ou tickets).",
                ])
            elif intent_type == "explain_data_model":
                prompt_parts.extend([
                    "",
                    "TÂCHE: L'ingénieur demande une EXPLICATION DU SCHÉMA DE TABLE BRASIL.",
                    "",
                    "INTERDICTIONS ABSOLUES :",
                    "- NE GÉNÈRE AUCUNE REQUÊTE SQL (SELECT, FROM, WHERE, JOIN, etc.).",
                    "- NE GÉNÈRE AUCUNE expression régulière (regex), séquence hexadécimale ou commande shell.",
                    "- N'INVENTE AUCUN nom de colonne, de table ou de relation — utilise UNIQUEMENT ce qui est présent dans le contexte KB (snippet_id: db-table-*).",
                    "- NE RÉPÈTE PAS deux fois la même section.",
                    "",
                    "FORMAT DE RÉPONSE OBLIGATOIRE — respecte exactement cet ordre :",
                    "",
                    "**Titre** : Explication Table `<nom_table>` — Synthèse N3",
                    "",
                    "**Vue d'ensemble** : [rôle de la table en une phrase, ex: stocke les ports réseau et les associe à une carte, un slot et un équipement]",
                    "",
                    "**Clé primaire** : [nom exact de la colonne PK telle qu'elle apparaît dans le KB]",
                    "",
                    "**Colonnes** (noms exacts extraits du KB) :",
                    "- colonne_1 (type) — description si disponible dans le KB",
                    "- colonne_2 (type) — FK vers table_cible.colonne si c'est une clé étrangère",
                    "[liste EXHAUSTIVE de toutes les colonnes documentées dans le KB — ne pas tronquer]",
                    "",
                    "**Relations (FK)** :",
                    "  *FK sortantes (cette table référence d'autres tables) :*",
                    "  - colonne_locale → table_cible.colonne_cible",
                    "  [si aucune FK sortante documentée : écrire 'Aucune FK sortante répertoriée dans les sources']",
                    "",
                    "  *FK entrantes (tables qui référencent cette table) :*",
                    "  - table_source.colonne_source → cette_table.colonne_locale",
                    "  [si aucune FK entrante documentée : écrire 'Aucune FK entrante répertoriée dans les sources']",
                    "",
                    "**Observations** : [anomalies, incidents connus ou tickets Jira liés à cette table présents dans le KB]",
                    "[si rien : écrire 'Aucune observation particulière dans les sources disponibles']",
                    "",
                    "**Vérifications N3 recommandées** (TEXTE UNIQUEMENT — sans SQL, sans commande, sans regex) :",
                    "1. [description textuelle de la vérification à effectuer, ex: 'Vérifier la cohérence entre port_num et card_id via l'interface d'administration BRASIL']",
                    "2. [etc.]",
                    "",
                    "**Sources** : [liste des snippet_id, procedure_id et liens Jira présents dans le contexte — une seule fois]",
                    "",
                    "**Confiance** : MOYEN — informations à valider par l'ingénieur N3 avant toute action corrective",
                ])
            else:
                prompt_parts.extend([
                    "",
                    "UTILISE UNIQUEMENT les informations présentes dans le contexte KB ci-dessus.",
                    "Cite les sources par leur snippet_id ou procedure_id EXACT (tel qu'il apparaît dans le KB).",
                    "Présente les étapes de manière structurée et numérotée.",
                    "",
                    "⛔ INTERDICTIONS ABSOLUES — HALLUCINATION D'IDENTIFIANTS :",
                    "- INTERDIT d'inventer des identifiants de procédure de type BRASIL-XXX-NNN",
                    "  (ex: BRASIL-RESTORE-001, BRASIL-ROLLBACK-002, BRASIL-VALIDATE-003).",
                    "- INTERDIT d'inventer des numéros FR de type FR-NNNN",
                    "  (ex: FR-1234, FR-5678, FR-9012) qui ne figurent PAS dans le contexte KB.",
                    "- INTERDIT de générer des requêtes SQL (SELECT, INSERT, UPDATE, DELETE).",
                    "- Si aucune procédure validée n'existe dans le contexte pour ce cas :",
                    "  → Déclare-le EXPLICITEMENT : 'Aucune procédure validée dans la base de connaissances.'",
                    "  → Recommande de créer une FR ou d'escalader vers l'équipe N3.",
                    "  → NE GÉNÈRE PAS de procédure fictive sous aucun prétexte.",
                    "",
                    "⛔ INTERDIT d'inclure une section 'Raisonnement', 'Thinking' ou toute section",
                    "   expliquant ton processus de réflexion interne — réponds directement.",
                ])

        # ── Branch C: no KB, not contextual → knowledge_gap or intent-specific fallback ─
        else:
            if intent_type == "tech_inference_schema":
                # Lister les tables dont le nom contient des mots-clés de la requête
                # pour guider le LLM vers la bonne table
                _schema_list = ", ".join(BRASIL_SCHEMA_TABLES)
                prompt_parts.extend([
                    "",
                    "CONTEXTE: Le schéma BRASIL contient les tables suivantes (liste exhaustive) :",
                    _schema_list,
                    "",
                    "TÂCHE: La requête de l'ingénieur porte sur une table ou entité BRASIL.",
                    "INSTRUCTIONS :",
                    "1. Cherche dans la liste ci-dessus la table qui correspond le mieux à la demande.",
                    "   Si la demande utilise un terme français (ex: 'équipements'), cherche la table",
                    "   anglaise correspondante (ex: 't_equipments').",
                    "2. Si tu identifies une correspondance probable, dis-le clairement :",
                    "   'La table qui correspond à [terme] est probablement [t_nom_table] dans le schéma BRASIL.'",
                    "3. Si aucune table ne correspond, déclare que tu ne peux pas identifier la table",
                    "   et recommande de consulter le schéma complet.",
                    "4. NE GÉNÈRE PAS de colonnes inventées. NE GÉNÈRE PAS d'IDs de procédure.",
                    "5. Réponds en français.",
                ])
            elif intent_type == "procedure_lookup_script_blocked":
                prompt_parts.extend([
                    "",
                    "TÂCHE: La procédure spécifique de déblocage de script N'EST PAS dans la base de connaissance.",
                    "INSTRUCTIONS :",
                    "- Déclare explicitement qu'aucune FR validée n'existe pour ce cas précis.",
                    "- Fournis la démarche opérationnelle N3 générique pour un script bloqué :",
                    "  (1) Identifier le statut du processus en base ou via l'IHM",
                    "  (2) Forcer le passage du statut si la durée d'exécution est anormale",
                    "  (3) Vérifier les logs pour identifier la cause avant relance",
                    "  (4) Relancer le script après correction si nécessaire",
                    "- Recommande de créer une FR pour ce cas.",
                    "- NE REFUSE PAS l'opération : arrêter / relancer un script est une action N3 légitime.",
                    "- Réponds en français.",
                ])
            else:
                prompt_parts.extend([
                    "",
                    "TÂCHE: KNOWLEDGE GAP DETECTION — Aucune procédure validée n'existe pour cette demande.",
                    "INSTRUCTIONS:",
                    "- Explique clairement qu'aucune connaissance validée n'est disponible pour ce cas.",
                    "- Propose des étapes d'investigation: (1) vérifier les FRs existantes, (2) consulter les tickets JIRA similaires, (3) collecter les logs applicatifs.",
                    "- Recommande la création d'une FR si ce cas n'est pas encore documenté.",
                    "- NE GÉNÈRE PAS de procédure inventoriée. Ne jamais halluciner une solution.",
                ])

        # ── Root Cause Lock — if confirmed, forbid new diagnostics ──────────
        confirmed_root_cause = orch_result.get("confirmed_root_cause")
        if confirmed_root_cause:
            prompt_parts.extend([
                "",
                "⛔ CAUSE RACINE VERROUILLÉE — FAIT ÉTABLI ET IMMUABLE :",
                f'"{confirmed_root_cause}"',
                "",
                "RÈGLES ABSOLUES (Root Cause Lock) :",
                "1. Tu NE PEUX PAS remettre en question cette cause racine.",
                "2. Tu NE PEUX PAS proposer d'hypothèses alternatives ou un nouveau diagnostic.",
                "3. Tu NE PEUX PAS mentionner des systèmes non liés à l'incident.",
                "4. TOUTES tes réponses doivent partir de ce fait établi.",
                "5. Si une question te demande de diagnostiquer, rappelle que la cause est déjà"
                "   identifiée et redirige vers l'action appropriée (clôture, prévention, etc.).",
            ])

        # ── Context isolation — restrict to in-scope systems only ─────────
        locked_systems = orch_result.get("locked_systems", [])
        excluded_systems = orch_result.get("excluded_systems", [])
        if locked_systems:
            prompt_parts.extend([
                "",
                f"PÉRIMÈTRE DE L'INCIDENT (à respecter strictement) :",
                f"- Systèmes concernés : {', '.join(locked_systems)}",
                "- Tu NE DOIS PAS mentionner ni utiliser d'informations sur d'autres systèmes.",
                "- Si un bloc de contexte mentionne un système hors périmètre, IGNORE CE BLOC.",
                "- Ne génère AUCUNE hypothèse impliquant des systèmes non mentionnés dans le ticket.",
            ])

        prompt_parts.extend([
            "",
            "FORMAT DE RÉPONSE:",
            "- Commence par confirmer le type d'incident détecté",
            "- Cite les systèmes impliqués",
            "- Présente les étapes de diagnostic puis de résolution",
            "- Termine par la recommandation d'escalade si nécessaire",
            "- Réponds TOUJOURS en français",
        ])

        # ── Role-aware style + humanized tone ────────────────────────────
        audience = orch_result.get("audience", "n3_engineer")
        prompt_parts.append(ROLE_SYSTEM_PROMPTS.get(audience, ROLE_SYSTEM_PROMPTS["n3_engineer"]))
        prompt_parts.append(HUMANIZED_STYLE_INSTRUCTIONS)

        return "\n".join(prompt_parts)

    def check_trust_gate(
        self,
        orch_result: Dict[str, Any],
        threshold: float = 40.0,
        structured_ticket: Optional[StructuredTicket] = None,
        history: Optional[list] = None,
        raw_query: str = "",
    ) -> Tuple[bool, str]:
        """
        Check if knowledge trust is sufficient to present a response.
        Returns (can_respond: bool, reason: str)

        Contextual intents (summarize, write_ticket_message, investigate_logs)
        bypass the trust gate because they work from conversation history,
        not from KB retrieval.

        Follow-up / clarification questions on a previous answer also bypass
        the gate — they should be answered from conversation context.
        """
        # Bypass for intents that need no KB
        if is_contextual_intent(structured_ticket):
            return True, "contextual_bypass"

        # Bypass for conversational follow-ups (clarification, date of source, etc.)
        if is_followup_question(raw_query, history or []):
            return True, "followup_bypass"

        trust_score = orch_result.get("trust_score")

        if trust_score is None:
            return False, "no_trust_score"

        # Handle TrustScore objects
        score_value = 0
        if hasattr(trust_score, "score"):
            score_value = trust_score.score
        elif isinstance(trust_score, (int, float)):
            score_value = float(trust_score)
        elif isinstance(trust_score, dict):
            score_value = trust_score.get("score", 0)

        if score_value >= threshold:
            return True, "sufficient"
        return False, f"trust_too_low:{score_value:.0f}"

    def enrich_orch_result(
        self,
        orch_result: Dict[str, Any],
        raw_query: str,
        app_id: str,
    ) -> Dict[str, Any]:
        """
        Enrich the orchestrator result with NLP-derived context.
        Adds structured_ticket, slot analysis, and incident type resolution.
        """
        structured = ticket_enricher.enrich(
            raw_text=raw_query,
            ticket_id="runtime_query",
            fallback_application=app_id,
        )

        orch_result["structured_ticket"] = structured.to_dict()
        orch_result["detected_incident_type"] = structured.incident_type
        orch_result["detected_entities"] = [
            {"type": e.entity_type, "value": e.value}
            for e in structured.entities
        ]
        orch_result["detected_error_codes"] = structured.error_codes
        orch_result["nlp_confidence"] = structured.confidence

        return orch_result


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _trust_label_from_score(trust_score: float) -> str:
    if trust_score >= 0.80:
        return "🟢 Haute confiance"
    elif trust_score >= 0.60:
        return "🟡 Confiance moyenne"
    elif trust_score >= 0.40:
        return "🟠 Confiance faible — à vérifier"
    return "🔴 Très faible"


def _confidence_warning(confidence_level: str) -> str:
    warnings = {
        "low":      "Confiance faible — vérifiez ces étapes avant de les appliquer.",
        "very_low": "Confiance très faible — procédure partiellement validée. Escalade recommandée.",
        "medium":   "",
        "high":     "",
    }
    return warnings.get(confidence_level, "")


def extract_prior_procedure_from_history(
    history: Optional[List[Dict]],
) -> Optional[str]:
    """
    Scan the conversation history for a previously cited procedure_id or FR number.
    Returns the first match found, or None.

    Used to enforce the Conversation Memory Rule: if a procedure was already
    identified earlier in the conversation, the assistant must reuse it
    and cannot claim knowledge is missing.
    """
    if not history:
        return None
    # Patterns: "FR-1234", "FR_1234", "proc_id: ...", "procedure_id: ..."
    _PROC_PATTERN = re.compile(
        r"\b(FR[-_]?\d{3,6})\b|procedure_id\s*[=:]\s*([\w\-]+)",
        re.IGNORECASE,
    )
    for msg in history:
        content = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
        if not isinstance(content, str):
            continue
        m = _PROC_PATTERN.search(content)
        if m:
            return m.group(1) or m.group(2)
    return None


# Singletons
slot_filler = SlotFiller()
response_formatter = ResponseFormatter()
diagnostic_reasoner = DiagnosticReasoner()

__all__ = [
    # State machine
    "ConversationPhase",
    "ConversationState",
    "detect_phase_transition",
    "extract_root_cause",
    "detect_audience",
    "KNOWN_SYSTEMS",
    # Intent override detection
    "detect_intent_override",
    # Role/style
    "ROLE_SYSTEM_PROMPTS",
    "HUMANIZED_STYLE_INSTRUCTIONS",
    "PERSONA_INSTRUCTION",
    # Core components
    "SlotFiller",
    "ResponseFormatter",
    "DiagnosticReasoner",
    "slot_filler",
    "response_formatter",
    "diagnostic_reasoner",
    # Helpers
    "is_contextual_intent",
    "is_followup_question",
    "extract_prior_procedure_from_history",
]
