"""
NLP Enricher — Ticket Understanding Model
Converts a raw support ticket into a fully structured StructuredTicket object.

Implements all enrichment components:
  - SystemDetector       : Detect BRASIL / SEBA / ARTEMIS / etc.
  - ErrorCodeExtractor   : Regex-based error code extraction
  - IntentClassifier     : Rule-based + LLM-assisted intent detection
  - EntityExtractor      : NER for equipment, users, codes, actions
  - IncidentTypeTagger   : Map to taxonomy
  - ConfidenceScorer     : Per-field confidence estimation
"""
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.services.nlp.preprocessor import preprocessor
from app.services.nlp.taxonomy import find_incident_type, INCIDENT_TAXONOMY
from app.core.logging import get_logger

logger = get_logger(__name__)


# ─────────────────────────────────────────────
# System name catalog — with aliases
# ─────────────────────────────────────────────
KNOWN_SYSTEMS = {
    "BRASIL":    ["brasil", "brasil_core", "brasil core"],
    "SEBA":      ["seba"],
    "ARTEMIS":   ["artemis"],
    "IPON":      ["ipon"],
    "ADELIA":    ["adelia", "adélia"],
    "SCA":       ["sca"],
    "ORCHESTRA": ["orchestra", "orchestration"],
}

# ─────────────────────────────────────────────
# Intent catalog + detection patterns
# ─────────────────────────────────────────────
INTENT_PATTERNS: Dict[str, List[str]] = {
    # ── PRIORITY 1: Diagnostic request ──────────────────────────────────────
    "diagnostic_request":   ["erreur", "error", "exception", "b4002", "4002", "1300", "1002", "42c",
                              "internal error", "ora-", "code retour", "bloqué", "blocage", "impossible",
                              "cannot", "bloquée", "bloque", "en attente", "gelé", "incident",
                              "dysfonctionnement", "ne fonctionne pas", "problème", "plantage", "crash"],
    # ── PRIORITY 2: Procedure lookup ─────────────────────────────────────────
    "procedure_lookup":     ["procédure", "comment faire", "comment résoudre", "how to",
                              "quelle procédure", "donne moi les étapes", "quelles étapes",
                              "démarche", "étapes de résolution", "guide", "documentation",
                              "que faire", "comment traiter"],
    # ── PRIORITY 3: Root cause exploration ───────────────────────────────────
    "root_cause_exploration": ["pourquoi", "cause", "cause racine", "origine du problème",
                                "pourquoi ce problème", "analyse la cause", "d'où vient",
                                "expliquer l'erreur", "raison", "source du problème",
                                "analyse de cause", "root cause"],
    # ── PRIORITY 4: Pattern analysis ─────────────────────────────────────────
    "pattern_analysis":     ["comportement", "comportement anormal", "analyse", "comprendre pourquoi",
                              "comment fonctionne", "pattern", "récurrent", "souvent",
                              "plusieurs fois", "historique", "tendance", "tickets similaires",
                              "incidents similaires"],
    # ── PRIORITY 5: Log investigation ────────────────────────────────────────
    "log_investigation":    ["logs", "log", "traces", "journaux", "fichier log",
                              "est-ce qu'il y a des logs", "y a-t-il des logs",
                              "logs associés", "traces associées", "voir les logs",
                              "consulter les logs", "logs disponibles", "fichiers de trace",
                              "déboguer", "debugger", "debug", "stack trace",
                              "où sont les logs", "quel log"],
    # ── PRIORITY 6: Ticket summary ───────────────────────────────────────────
    "ticket_summary":       ["résumé", "résume", "résumer", "récapituler", "récapitulatif",
                              "synthèse", "en résumé", "bilan", "récap",
                              "résume le problème", "résume la solution", "fais moi un résumé"],
    # ── PRIORITY 7: Ticket closing ───────────────────────────────────────────
    "ticket_closing":       ["message pour le dépositaire", "réponse finale", "message de clôture",
                              "clôturer le ticket", "fermer le ticket", "génère la réponse",
                              "message à mettre dans le ticket", "message ticket",
                              "texte pour le ticket", "rédiger le ticket",
                              "écrire dans le ticket", "message jira", "commentaire jira",
                              "prépare le message", "résumé pour le ticket",
                              "résume la solution pour le ticket"],
    # ── PRIORITY 8: Knowledge lookup ─────────────────────────────────────────
    "knowledge_lookup":     ["vérifier", "verifier", "contrôler", "check", "surveiller",
                              "état de", "statut", "voir si", "quel est l'état",
                              "où en est", "status", "état actuel"],
    # ── PRIORITY 9: Similar ticket search ──────────────────────────────────
    "find_similar_tickets": ["tickets similaires", "incidents similaires", "ticket similaire",
                               "y a-t-il des tickets", "existe-t-il des tickets",
                               "tickets avec le même", "tickets avec cette erreur",
                               "problème similaire", "déjà vu", "déjà rencontré",
                               "autres tickets", "chercher des tickets", "recherche de tickets"],
    # ── PRIORITY 10: Jira search ───────────────────────────────────────────────
    "find_jira": ["jira", "carte jira", "issue jira", "y a-t-il un jira",
                   "existe-t-il un jira", "trouver le jira", "chercher dans jira",
                   "y a-t-il une carte", "y a-t-il un ticket jira",
                   "créer un jira", "ouvrir un jira", "lien jira", "référence jira"],
    # ── PRIORITY 11: Explain / reformulate a Jira ──────────────────────────
    "explain_jira": ["explique ce jira", "explique le jira", "reformule le jira",
                      "reformule cette carte", "résume ce jira", "résume le jira",
                      "explique-moi ce ticket jira", "que dit ce jira",
                      "analyse ce jira", "décrypte ce jira", "interprète ce jira",
                      "explique la carte jira"],
    # ── PRIORITY 12: Explain data model / DB schema ────────────────────────
    "explain_data_model": [
        # Demandes génériques schéma/modèle
        "modèle de données", "modele de données", "modèle de donnees",
        "structure de la base", "structure base de données", "schéma de la base",
        "schema de la base", "schéma bdd", "structure bdd",
        "quelles sont les tables", "tables brasil", "tables de brasil",
        "tables principales", "colonnes de la table", "colonne table",
        "base de données brasil", "bdd brasil", "organisation des données",
        "comment sont organisées les données", "comment sont organisées",
        "structure des données", "dictionnaire de données", "dictionnaire des données",
        "entités brasil", "entité brasil", "relations entre les tables",
        "clé primaire", "clé étrangère", "foreign key", "primary key",
        "modèle entité", "erd brasil", "explique la base", "explique le schéma",
        # Demandes spécifiques à une table
        "explique la table", "explique-moi la table", "explique moi la table",
        "expliquer la table", "expliquer cette table", "explain the table",
        "décris la table", "décris-moi la table", "description de la table",
        "structure de la table", "schema de la table", "schéma de la table",
        "colonnes de", "les colonnes de", "champs de la table",
        "quelles colonnes", "quels champs", "quelles sont les colonnes",
        "clés de la table", "pk de", "fk de",
        # Noms de tables BRASIL connus
        "t_ports", "t_cards", "t_equipments", "t_slots", "t_stripes",
        "t_prestations", "t_nodes", "t_media_links", "t_tech_serv",
        "t_port_groups", "t_d_booked", "t_ftth", "t_mrt",
    ],
    # ── PRIORITY 13: Knowledge gap detection (fallback) ──────────────────────
    "knowledge_gap_detection": ["je ne sais pas", "pas de procédure", "aucune doc",
                                 "pas de solution connue", "pas documenté",
                                 "connaissance manquante", "pas de fr", "pas de fiche"],
    # ── Action requests (operational) ────────────────────────────────────────
    "delete_equipment":     ["supprimer", "suppression", "delete", "effacer", "retirer",
                              "désactivation", "décommissionnement"],
    "create_appointment":   ["créer rdv", "prendre rdv", "nouveau rdv", "planifier rendez-vous"],
    "cancel_appointment":   ["annuler rdv", "annulation rdv", "rdv annulé", "annuler le rendez-vous"],
    "launch_command":       ["lancer commande", "lancer la commande", "exécuter commande",
                              "démarrer commande", "launch"],
    "update_configuration": ["mettre à jour", "modifier", "changer", "update", "maj",
                              "configuration", "paramètre"],
    "reset_account":        ["réinitialiser", "reset", "débloquer compte", "remettre à zéro"],
    "escalate":             ["escalade", "ticket jira", "créer jira", "remonter"],
}

# Intent priority order (lower index = higher priority)
INTENT_PRIORITY: List[str] = [
    "explain_data_model",       # PRIORITY 1 — specific table/schema requests
    "explain_jira",             # PRIORITY 2 — explain a specific Jira card
    "find_jira",                # PRIORITY 3 — search Jira
    "find_similar_tickets",     # PRIORITY 4 — search similar tickets
    "ticket_summary",           # PRIORITY 5
    "ticket_closing",           # PRIORITY 6
    "log_investigation",        # PRIORITY 7
    "procedure_lookup",         # PRIORITY 8
    "root_cause_exploration",   # PRIORITY 9
    "pattern_analysis",         # PRIORITY 10
    "diagnostic_request",       # PRIORITY 11 — generic error/incident
    "knowledge_lookup",         # PRIORITY 12
    "knowledge_gap_detection",  # PRIORITY 13 — fallback
]

# ─────────────────────────────────────────────
# Entity patterns
# ─────────────────────────────────────────────
ENTITY_PATTERNS = {
    "equipment_id":     [
        r"\b([A-Z]{2,5}[A-Z0-9]{2,4}\d{3,6})\b",    # NBLIL701, DSLAM1234
        r"\b(NRO[-\s]?[A-Z0-9]{3,12})\b",             # NRO-XYZ
        r"\b(BAS[-\s]?[A-Z0-9]{3,12})\b",             # BAS-XYZ
    ],
    "error_code":       [
        r"\b(B\d{4})\b",
        r"\b(AVP[-\s]?\d+)\b",
        r"\b(ORA-\d{4,6})\b",
        r"\b(\d{4})\b",
        r"\b(42C)\b",
        r"\b(ERR(?:EUR)?[-_\s]?\d+[A-Z]?)\b",
    ],
    "user_id":          [
        r"\b([a-z]\.[a-z]{2,20})\b",                  # j.dupont
        r"\butilisateur\s+([A-Z0-9_\-]{4,20})\b",
        r"\buser\s+([A-Z0-9_\-]{4,20})\b",
    ],
    "command_name":     [
        r"commande\s+[«\"']?([A-Z_\-]{3,30})[»\"']?",
        r"script\s+[«\"']?([A-Z_\-/]{3,40})[»\"']?",
    ],
    "appointment_ref":  [
        r"\bRDV[-\s]?(\d{6,12})\b",
        r"\brendez-vous\s+(\d{6,12})\b",
    ],
    "constraint_code":  [
        r"\b(AVP[-\s]?\d+)\b",
        r"\b(1300|9903|42C)\b",
    ],
}


# ─────────────────────────────────────────────
# Structured output schema
# ─────────────────────────────────────────────
@dataclass
class ExtractedEntity:
    entity_type: str
    value: str
    confidence: float = 1.0


@dataclass
class StructuredTicket:
    """
    Fully structured representation of a raw support ticket.
    This is the output of the NLP enrichment layer.
    """
    # Identity
    ticket_id: str = ""
    raw_text: str = ""
    preprocessed_text: str = ""
    language: str = "fr"
    source_type: str = "ticket"          # ticket | fr | jira

    # NLP enrichment
    intent: str = "unknown"
    application: str = "BRASIL"
    related_systems: List[str] = field(default_factory=list)
    entities: List[ExtractedEntity] = field(default_factory=list)
    error_codes: List[str] = field(default_factory=list)
    action_requested: str = ""
    incident_type: str = "unknown.insufficient_information"
    confidence: float = 0.0

    # Trust
    trust_score: float = 0.3
    requires_human_review: bool = False

    # Metadata
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    cluster_id: Optional[str] = None
    procedure_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticket_id": self.ticket_id,
            "raw_text": self.raw_text,
            "preprocessed_text": self.preprocessed_text,
            "language": self.language,
            "source_type": self.source_type,
            "intent": self.intent,
            "application": self.application,
            "related_systems": self.related_systems,
            "entities": [{"type": e.entity_type, "value": e.value, "confidence": e.confidence}
                         for e in self.entities],
            "error_codes": self.error_codes,
            "action_requested": self.action_requested,
            "incident_type": self.incident_type,
            "confidence": round(self.confidence, 3),
            "trust_score": round(self.trust_score, 3),
            "requires_human_review": self.requires_human_review,
            "created_at": self.created_at,
            "cluster_id": self.cluster_id,
            "procedure_id": self.procedure_id,
        }


# ─────────────────────────────────────────────
# NLP Enricher — Main class
# ─────────────────────────────────────────────
class TicketEnricher:
    """
    Converts a raw ticket text into a StructuredTicket.

    Pipeline:
    1. Preprocess text
    2. Detect language
    3. Extract error codes
    4. Detect systems (BRASIL, SEBA, ...)
    5. Extract entities (equipment IDs, user IDs, etc.)
    6. Classify intent
    7. Tag incident type from taxonomy
    8. Compute confidence score
    """

    def enrich(
        self,
        raw_text: str,
        ticket_id: str = "",
        fallback_application: str = "BRASIL",
    ) -> StructuredTicket:
        """
        Main enrichment entry point.
        Returns a StructuredTicket with all fields populated.
        """
        ticket = StructuredTicket(
            ticket_id=ticket_id,
            raw_text=raw_text,
        )

        # 1. Preprocess
        ticket.preprocessed_text = preprocessor.preprocess(raw_text)
        combined = raw_text + " " + ticket.preprocessed_text

        # 2. Language
        ticket.language = preprocessor.detect_language(raw_text)

        # 3. Error codes
        ticket.error_codes = preprocessor.extract_error_codes(combined)

        # 4. Detect systems
        detected_systems = self._detect_systems(combined)
        if detected_systems:
            ticket.application = detected_systems[0]    # Primary system
            ticket.related_systems = detected_systems
        else:
            ticket.application = fallback_application

        # 5. Extract entities
        ticket.entities = self._extract_entities(combined, ticket.error_codes)

        # 6. Classify intent
        ticket.intent, intent_conf = self._classify_intent(combined)
        ticket.action_requested = self._extract_action(combined)

        # 7. Tag incident type
        ticket.incident_type = find_incident_type(combined)

        # 8. Compute confidence
        ticket.confidence = self._compute_confidence(ticket, intent_conf)

        # 9. Trust score (raw tickets are LOW trust by default)
        ticket.trust_score = self._compute_trust(ticket)

        # 10. Flag for review if confidence is low
        ticket.requires_human_review = ticket.confidence < 0.55

        logger.debug(
            f"[Enricher] ticket={ticket_id} intent={ticket.intent} "
            f"app={ticket.application} type={ticket.incident_type} "
            f"conf={ticket.confidence:.2f}"
        )
        return ticket

    # ─────────────────────────────────────────────
    # Step implementations
    # ─────────────────────────────────────────────

    def _detect_systems(self, text: str) -> List[str]:
        """Detect all system names mentioned in the text."""
        text_lower = text.lower()
        found = []
        for system, aliases in KNOWN_SYSTEMS.items():
            if any(alias in text_lower for alias in aliases):
                found.append(system)
        # Default: BRASIL is always the primary system
        if not found:
            found = ["BRASIL"]
        elif "BRASIL" not in found:
            found.insert(0, "BRASIL")
        return found

    def _extract_entities(self, text: str, error_codes: List[str]) -> List[ExtractedEntity]:
        """Extract all entities from text."""
        entities: List[ExtractedEntity] = []

        # Error codes from preprocessor (high confidence)
        for code in error_codes:
            entities.append(ExtractedEntity("error_code", code, 0.95))

        # Other entity types via regex
        for entity_type, patterns in ENTITY_PATTERNS.items():
            if entity_type == "error_code":
                continue  # Already handled above
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    value = match.strip() if isinstance(match, str) else match[0].strip()
                    if value and len(value) >= 2:
                        entities.append(ExtractedEntity(entity_type, value.upper(), 0.80))

        # Action verbs
        action_verbs = ["supprimer", "créer", "modifier", "lancer", "vérifier",
                        "annuler", "relancer", "configurer", "démarrer", "arrêter"]
        text_lower = text.lower()
        for verb in action_verbs:
            if verb in text_lower:
                entities.append(ExtractedEntity("action_verb", verb, 0.90))

        # System names as entities
        for system, aliases in KNOWN_SYSTEMS.items():
            if any(alias in text_lower for alias in aliases):
                entities.append(ExtractedEntity("system_name", system, 0.99))

        # Deduplicate: keep unique (type, value) pairs
        seen = set()
        deduped = []
        for e in entities:
            key = (e.entity_type, e.value.upper())
            if key not in seen:
                seen.add(key)
                deduped.append(e)
        return deduped

    def _classify_intent(self, text: str) -> tuple:
        """
        Priority-aware intent classification.
        When multiple intents match, the one with the highest priority wins.
        Returns (intent_name, confidence).
        """
        text_lower = text.lower()
        scores: Dict[str, int] = {}
        for intent, patterns in INTENT_PATTERNS.items():
            score = sum(1 for p in patterns if p in text_lower)
            if score > 0:
                scores[intent] = score

        if not scores:
            return "unknown", 0.3

        # Respect INTENT_PRIORITY order: pick highest-priority matching intent,
        # then use score only as tiebreaker among same-priority intents.
        for priority_intent in INTENT_PRIORITY:
            if priority_intent in scores:
                total_matches = scores[priority_intent]
                confidence = min(0.40 + total_matches * 0.15, 0.95)
                return priority_intent, confidence

        # Fallback: any non-priority intent with highest score
        best_intent = max(scores, key=scores.get)
        confidence = min(0.40 + scores[best_intent] * 0.15, 0.95)
        return best_intent, confidence

    def _extract_action(self, text: str) -> str:
        """Extract the primary action verb phrase from the text."""
        action_map = {
            "supprimer":  "delete",
            "suppression": "delete",
            "créer":      "create",
            "création":   "create",
            "modifier":   "update",
            "mettre à jour": "update",
            "lancer":     "launch",
            "annuler":    "cancel",
            "vérifier":   "check",
            "relancer":   "restart",
            "bloquer":    "block",
        }
        text_lower = text.lower()
        for fr_action, en_action in action_map.items():
            if fr_action in text_lower:
                return en_action
        return "investigate"

    def _compute_confidence(self, ticket: StructuredTicket, intent_conf: float) -> float:
        """
        Compute overall confidence score based on:
        - Intent classification confidence
        - Number of entities found
        - Error codes present
        - Incident type found (not unknown)
        """
        score = intent_conf * 0.40

        # Entity contribution
        entity_types = {e.entity_type for e in ticket.entities}
        entity_bonus = min(len(entity_types) * 0.05, 0.20)
        score += entity_bonus

        # Error code bonus
        if ticket.error_codes:
            score += 0.15

        # Incident type known
        if ticket.incident_type != "unknown.insufficient_information":
            score += 0.20

        # Application detected (not default fallback)
        if len(ticket.related_systems) > 0:
            score += 0.05

        return round(min(score, 0.97), 3)

    def _compute_trust(self, ticket: StructuredTicket) -> float:
        """
        Compute trust score for a raw ticket.
        Raw tickets always start low; enriched by clustering/FR later.
        """
        base = 0.25
        # More info = slightly higher trust
        if ticket.error_codes:
            base += 0.05
        if ticket.incident_type != "unknown.insufficient_information":
            base += 0.05
        if len(ticket.preprocessed_text) > 30:
            base += 0.05
        return round(min(base, 0.40), 3)


# Singleton
ticket_enricher = TicketEnricher()
