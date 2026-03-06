"""
Diagnostic Behavior Module — Anti-hallucination, slot filling, structured diagnostic loop.
Extends chatbot_service.py with structured diagnostic reasoning.

Implements:
  - SlotFiller: extracts missing context from conversation
  - DiagnosticReasoner: structures multi-step diagnostic conversations
  - AntiHallucinationGuard: ensures responses stay grounded in KB
  - ResponseFormatter: formats responses using the N3 support template
"""
import re
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from app.services.nlp.enricher import ticket_enricher, StructuredTicket
from app.services.nlp.taxonomy import INCIDENT_TAXONOMY
from app.core.logging import get_logger

logger = get_logger(__name__)


# ─────────────────────────────────────────────
# Anti-Hallucination Rules
# ─────────────────────────────────────────────

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
                    "TÂCHE: Générer le MESSAGE DE CLÔTURE du ticket pour le dépositaire.",
                    "INSTRUCTIONS:",
                    "- Utilise UNIQUEMENT le contexte de la conversation fournie.",
                    "- Produis DEUX sections distinctes:",
                    "  SECTION 1 — Résumé technique N3: Incident | Cause | Action effectuée | Résultat.",
                    "  SECTION 2 — Message pour le dépositaire: message professionnel confirmant la résolution.",
                    "- Ton professionnel, neutre, en français.",
                    "- Ne lance pas de nouvelle recherche KB.",
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
            if intent_type == "procedure_lookup":
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
                prompt_parts.append(
                    "\nUTILISE UNIQUEMENT les informations ci-dessus pour formuler ta réponse. "
                    "Cite toujours la source (procedure_id ou cluster_id). "
                    "Présente les étapes de manière structurée et numérotée."
                )

        # ── Branch C: no KB, not contextual → knowledge_gap_detection ───────────────────
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

        prompt_parts.extend([
            "",
            "FORMAT DE RÉPONSE:",
            "- Commence par confirmer le type d'incident détecté",
            "- Cite les systèmes impliqués",
            "- Présente les étapes de diagnostic puis de résolution",
            "- Termine par la recommandation d'escalade si nécessaire",
            "- Réponds TOUJOURS en français",
        ])

        return "\n".join(prompt_parts)

    def check_trust_gate(
        self,
        orch_result: Dict[str, Any],
        threshold: float = 40.0,
        structured_ticket: Optional[StructuredTicket] = None,
    ) -> Tuple[bool, str]:
        """
        Check if knowledge trust is sufficient to present a response.
        Returns (can_respond: bool, reason: str)

        Contextual intents (summarize, write_ticket_message, investigate_logs)
        bypass the trust gate because they work from conversation history,
        not from KB retrieval.
        """
        # Bypass for intents that need no KB
        if is_contextual_intent(structured_ticket):
            return True, "contextual_bypass"

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
