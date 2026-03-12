"""
Smart N3 Parser — Production-Ready Intelligent Parsing for BRASIL L3 Support
==============================================================================

Replaces the keyword-based parseur with a 7-step enrichment pipeline:

  Step 1 — Encoding normalization   : auto-detect & fix latin-1 mojibake
  Step 2 — Text normalization       : abbreviations, telecom jargon, short messages
  Step 3 — Telecom entity extraction: ND, NRO, DSLAM, AVP, PORT, SLOT, CARD
  Step 4 — Error code detection     : 1300, ERR1300, BR-1300, B4002, AVP 1300
  Step 5 — Intent detection         : embedding-ready semantic classification
  Step 6 — Incident normalization   : structured IncidentContext output
  Step 7 — RAG query generation     : multi-vector query for optimal FR retrieval

Usage:
    from app.services.nlp.smart_n3_parser import SmartN3Parser

    parser = SmartN3Parser()
    incident = parser.parse("nd supprimé brasil avp 1300 bloque commande")
    print(incident.to_dict())
    # → {"intent": "ORDER_BLOCKED", "entities": {"ND": ..., "error": "1300"}, ...}

Author  : ChatBot BRASIL N3 — Orange France
Version : 2.0.0
"""

from __future__ import annotations

import re
import unicodedata
import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# 1. CONSTANTS & DICTIONARIES
# ══════════════════════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────
# Telecom Synonym Dictionary — BRASIL/Orange France N3
# Maps operational jargon → canonical NLP verb
# ─────────────────────────────────────────────────────
TELECOM_SYNONYM_DICT: Dict[str, str] = {
    # ── Re-execution synonyms ──
    "rejouer":         "relancer",
    "rejeu":           "relancer",
    "re-jouer":        "relancer",
    "ré-exécuter":     "relancer",
    "réexécuter":      "relancer",
    "reexécuter":      "relancer",
    "repasser":        "relancer",
    "réintégrer":      "relancer",
    "reprovisionner":  "relancer",
    "forcer":          "relancer",
    "rejouer la tâche":"relancer la tâche",
    # ── Recreate / rebuild synonyms ──
    "recréer":         "supprimer créer",
    "re-créer":        "supprimer créer",
    "reconstruire":    "supprimer créer",
    "réinitialiser":   "supprimer créer",
    "reconfigurer":    "supprimer créer",
    # ── Release / unblock synonyms ──
    "dégager":         "libérer",
    "débloquer":       "libérer",
    "déverrouilller":  "libérer",
    "libérer la commande": "libérer",
    "purger":          "supprimer",
    "vider":           "supprimer",
    # ── Fix / correct synonyms ──
    "régulariser":     "corriger",
    "rectifier":       "corriger",
    "normaliser":      "corriger",
    "dépanner":        "corriger",
    "réparer":         "corriger",
    "régulariser":     "corriger",
    "corriger l'incohérence": "corriger",
    # ── Blocked / failed synonyms ──
    "bloqué":          "bloquée",
    "bloque":          "bloquée",
    "gelé":            "bloquée",
    "en attente":      "bloquée",
    "suspendu":        "bloquée",
    "figé":            "bloquée",
    "planté":          "erreur",
    # ── Check / investigate synonyms ──
    "analyser":        "vérifier",
    "inspecter":       "vérifier",
    "contrôler":       "vérifier",
    "checker":         "vérifier",
    "regarder":        "vérifier",
    "consulter":       "vérifier",
    # ── Access / provision synonyms ──
    "provisionner":    "créer",
    "activer":         "créer",
    "mettre en service": "créer",
    "déclarer":        "créer",
    "enregistrer":     "créer",
    # ── Delete synonyms ──
    "désactiver":      "supprimer",
    "décommissionner": "supprimer",
    "effacer":         "supprimer",
    "retirer":         "supprimer",
    "sortir":          "supprimer",
    "suppr":           "supprimer",
    "supp":            "supprimer",
}

# ─────────────────────────────────────────────────────
# System name canonical mapping
# ─────────────────────────────────────────────────────
SYSTEM_ALIASES: Dict[str, List[str]] = {
    "BRASIL":    ["brasil", "brasil_core", "brasil core", "bdd brasil", "base brasil"],
    "SEBA":      ["seba"],
    "ARTEMIS":   ["artemis"],
    "IPON":      ["ipon"],
    "ADELIA":    ["adelia", "adélia", "adélia"],
    "SCA":       ["sca"],
    "ORCHESTRA": ["orchestra", "orchestration"],
    "XDSL":      ["xdsl", "dsl", "adsl", "vdsl"],
    "FTTH":      ["ftth", "fibre", "fiber"],
}

# ─────────────────────────────────────────────────────
# Telecom entity patterns (ordered by confidence priority)
# ─────────────────────────────────────────────────────
TELECOM_ENTITY_PATTERNS: Dict[str, List[Tuple[str, float]]] = {
    # (regex_pattern, confidence)
    "ND": [
        (r"\b(?:le\s+)?nd\s*[:\-]?\s*(\d{10})\b", 0.99),        # "nd 0563741427"
        (r"\b(\d{10})\b", 0.80),                                  # standalone 10-digit
        (r"\bnd\b", 0.60),                                        # bare "nd" mention
    ],
    "NRO": [
        (r"\bnro[-\s]?([A-Z0-9]{3,12})\b", 0.99),                # "NRO-LIL701"
        (r"\b([A-Z]{2,4}[A-Z0-9]{3,8}\d{3})\b", 0.85),          # "NBLIL701", "NECHR10Z"
        (r"\bnro\b", 0.60),
    ],
    "DSLAM": [
        (r"\b(DSLAM[-\s]?[A-Z0-9]{3,20})\b", 0.99),              # "DSLAM-LIL701-01"
        (r"\bdslam\b", 0.75),
    ],
    "AVP": [
        (r"\bAVP[-\s]?(\d{3,6})\b", 0.99),                       # "AVP 1300", "AVP-1300"
        (r"\bavp\b", 0.70),
    ],
    "PORT": [
        (r"\bport[-\s]?(?:id\s*[:\-]?\s*)?([A-Z0-9\-/]{3,20})\b", 0.90),  # "PORT-0/1/2"
        (r"\bport\s+(\d{1,4})\b", 0.85),                          # "port 24"
    ],
    "SLOT": [
        (r"\bslot[-\s]?(\d{1,3}(?:/\d{1,3})?)\b", 0.90),         # "slot 0/1"
        (r"\bslot\b", 0.65),
    ],
    "CARD": [
        (r"\bcarte[-\s]?([A-Z0-9\-]{2,15})\b", 0.90),            # "carte ADSL-A"
        (r"\bcard[-\s]?([A-Z0-9\-]{2,15})\b", 0.90),
        (r"\bcarte\b", 0.65),
    ],
    "EQUIPMENT": [
        (r"\b([A-Z]{2,5}[A-Z0-9]{2,6}\d{3,6})\b", 0.88),        # "NBLIL701"
        (r"\béquipement[-\s]?([A-Z0-9\-]{3,20})\b", 0.85),
        (r"\bequipement[-\s]?([A-Z0-9\-]{3,20})\b", 0.85),
    ],
    "ORDER_ID": [
        (r"\b(?:commande|cmd|order)[-\s]?(?:n[°º]?\s*)?([A-Z0-9\-]{6,20})\b", 0.95),
        (r"\b([A-Z]{2,4}\d{8,15})\b", 0.80),                     # "CMD20250301001"
    ],
    "USER_ID": [
        (r"\b([a-z]\.[a-z_]{2,20})\b", 0.90),                    # "j.dupont"
        (r"\butilisateur[-\s]?([A-Z0-9_\-]{4,20})\b", 0.85),
    ],
    "IP_ADDRESS": [
        (r"\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b", 0.95),
    ],
    "VLAN_ID": [
        (r"\bvlan[-\s]?(\d{1,4})\b", 0.95),
    ],
    "TRANSACTION_ID": [
        (r"\b(?:transaction|txn)[-\s]?(?:id[-\s]?)?([A-Z0-9\-]{8,30})\b", 0.90),
    ],
}

# ─────────────────────────────────────────────────────
# Error code patterns — ordered by specificity
# ─────────────────────────────────────────────────────
ERROR_CODE_PATTERNS: List[Tuple[str, str, float]] = [
    # (pattern, canonical_prefix, confidence)
    (r"\bB(\d{4})\b",                        "B",     0.99),   # B4002
    (r"\bAVP[-\s]?(\d{3,6})\b",             "AVP",   0.99),   # AVP-1300
    (r"\bORA[-\s](\d{4,6})\b",              "ORA-",  0.99),   # ORA-12170
    (r"\bERR(?:EUR)?[-_\s]?(\d{1,6}[A-Z]?)\b","ERR", 0.95),  # ERR1300, ERREUR 42C
    (r"\bBR[-\s](\d{3,6})\b",               "BR-",   0.95),   # BR-1300
    (r"\b([A-Z]{2,4}[-_]\d{3,6})\b",        "",      0.88),   # XX-1234 format
    (r"\b42C\b",                             "",      0.99),   # special code
    (r"\b(9903)\b",                          "",      0.95),
    (r"\b(1300)\b",                          "",      0.92),
    (r"\b(4002)\b",                          "",      0.92),
    (r"\b(1002)\b",                          "",      0.90),
    (r"\b(1203)\b",                          "",      0.90),
    (r"\b(2025)\b",                          "",      0.85),
    (r"\b(2930)\b",                          "",      0.85),
    (r"\b(\d{4})\b",                         "",      0.70),   # generic 4-digit
    (r"\b(\d{3})\b",                         "",      0.60),   # generic 3-digit
]

# Year patterns to EXCLUDE from error code detection
_YEAR_EXCLUSION = re.compile(r"^(19|20)\d{2}$")

# ─────────────────────────────────────────────────────
# Intent definitions — semantic N3 taxonomy
# ─────────────────────────────────────────────────────
class Intent(str, Enum):
    CREATE_RESOURCE      = "CREATE_RESOURCE"
    DELETE_RESOURCE      = "DELETE_RESOURCE"
    UPDATE_RESOURCE      = "UPDATE_RESOURCE"
    REPLAY_ORDER         = "REPLAY_ORDER"
    CANCEL_ORDER         = "CANCEL_ORDER"
    UNLOCK_ORDER         = "UNLOCK_ORDER"
    ORDER_BLOCKED        = "ORDER_BLOCKED"
    DATA_INCONSISTENCY   = "DATA_INCONSISTENCY"
    LOG_ANALYSIS         = "LOG_ANALYSIS"
    ROOT_CAUSE           = "ROOT_CAUSE"
    PROCEDURE_LOOKUP     = "PROCEDURE_LOOKUP"
    DIAGNOSTIC           = "DIAGNOSTIC"
    SCRIPT_BLOCKED       = "SCRIPT_BLOCKED"
    APPOINTMENT          = "APPOINTMENT"
    CONFIGURATION_ERROR  = "CONFIGURATION_ERROR"
    ACCESS_ISSUE         = "ACCESS_ISSUE"
    DUPLICATE_RESOURCE   = "DUPLICATE_RESOURCE"
    UNKNOWN              = "UNKNOWN"


# Intent keyword profiles — each entry is (keywords, weight)
# Using phrase-first matching before individual keywords
INTENT_PROFILES: Dict[Intent, List[Tuple[List[str], float]]] = {
    Intent.REPLAY_ORDER: [
        (["rejouer", "relancer", "re-lancer", "repasser", "réexécuter",
          "forcer le rejeu", "rejeu", "retenter", "re jouer"], 1.0),
        (["de nouveau", "une nouvelle fois", "à nouveau"], 0.5),
    ],
    Intent.DELETE_RESOURCE: [
        (["supprimer", "suppression", "effacer", "retirer", "désactiver",
          "décommissionner", "supp ", "delete"], 1.0),
        (["nd supprimé", "équipement supprimé", "routeur supprimé", "dslam supprimé"], 1.2),
    ],
    Intent.CREATE_RESOURCE: [
        (["créer", "création", "provisionner", "activer", "mettre en service",
          "créer routeur", "créer dslam", "créer nd", "create"], 1.0),
        (["impossible créer", "impossible de créer", "erreur création"], 0.8),
    ],
    Intent.ORDER_BLOCKED: [
        (["bloqué", "bloquée", "blocage", "gelé", "suspendu", "en attente",
          "commande bloquée", "commande gelée", "order blocked",
          "impossible de passer", "ne part pas"], 1.0),
        (["avp", "avp 1300", "avp-1300", "contrainte avp"], 1.3),
        (["1300", "erreur 1300"], 0.8),
    ],
    Intent.UNLOCK_ORDER: [
        (["débloquer", "libérer", "dégager", "déverrouilller",
          "lever le blocage", "retirer le blocage", "déverrouiller"], 1.0),
        (["commande coincée", "traitement bloqué"], 0.8),
    ],
    Intent.DATA_INCONSISTENCY: [
        (["incohérence", "incohérent", "données incorrectes", "données fausses",
          "ne correspond pas", "données terrain", "écart terrain",
          "brasil terrain", "erreur de données", "données erronées"], 1.0),
        (["n'existe pas", "introuvable en base", "absent de brasil"], 0.8),
    ],
    Intent.LOG_ANALYSIS: [
        (["logs", "log", "traces", "journaux", "stack trace",
          "fichier log", "voir les logs", "logs associés"], 1.0),
        (["déboguer", "debug", "exception", "stack overflow"], 0.8),
    ],
    Intent.SCRIPT_BLOCKED: [
        (["script bloqué", "script en cours", "script lancé", "ihm script",
          "lancement script", "arrêter le script", "mettre en erreur",
          "script suspendu"], 1.0),
    ],
    Intent.ROOT_CAUSE: [
        (["pourquoi", "cause", "cause racine", "d'où vient", "origine",
          "source du problème", "raison", "expliquer l'erreur"], 1.0),
    ],
    Intent.PROCEDURE_LOOKUP: [
        (["procédure", "comment faire", "comment résoudre", "quelles étapes",
          "démarche", "que faire", "guide", "fr ", "fiche de résolution"], 1.0),
    ],
    Intent.DIAGNOSTIC: [
        (["erreur", "error", "exception", "b4002", "4002",
          "problème", "dysfonctionnement", "plantage", "crash",
          "ne fonctionne pas", "ko"], 1.0),
        (["1300", "avp 1300", "42c", "9903"], 0.9),
    ],
    Intent.DUPLICATE_RESOURCE: [
        (["doublon", "duplicate", "déjà existant", "existe déjà",
          "en doublon", "ressource dupliquée"], 1.0),
    ],
    Intent.APPOINTMENT: [
        (["rdv", "rendez-vous", "appointment", "planifier"], 1.0),
    ],
    Intent.CONFIGURATION_ERROR: [
        (["noeud incorrect", "mauvais noeud", "nœud incorrect",
          "noeud du routeur", "corriger le noeud",
          "configuration incorrecte", "mauvaise configuration"], 1.0),
    ],
    Intent.UPDATE_RESOURCE: [
        (["modifier", "mettre à jour", "maj", "update", "changer",
          "paramètre", "corriger", "corriger le noeud"], 1.0),
    ],
    Intent.CANCEL_ORDER: [
        (["annuler", "annulation", "cancel", "abandonner"], 1.0),
    ],
    Intent.ACCESS_ISSUE: [
        (["accès refusé", "droits insuffisants", "pas les droits",
          "permission refusée", "unauthorized", "403", "401"], 1.0),
    ],
}

# Intent priority (higher = checked first, wins ties)
INTENT_PRIORITY: Dict[Intent, int] = {
    Intent.SCRIPT_BLOCKED:     100,
    Intent.DUPLICATE_RESOURCE: 95,
    Intent.ORDER_BLOCKED:      90,
    Intent.UNLOCK_ORDER:       88,
    Intent.REPLAY_ORDER:       85,
    Intent.DATA_INCONSISTENCY: 83,
    Intent.DELETE_RESOURCE:    80,
    Intent.CREATE_RESOURCE:    78,
    Intent.CANCEL_ORDER:       75,
    Intent.CONFIGURATION_ERROR:73,
    Intent.UPDATE_RESOURCE:    70,
    Intent.ACCESS_ISSUE:       68,
    Intent.LOG_ANALYSIS:       65,
    Intent.ROOT_CAUSE:         60,
    Intent.PROCEDURE_LOOKUP:   55,
    Intent.APPOINTMENT:        50,
    Intent.DIAGNOSTIC:         30,
    Intent.UNKNOWN:             0,
}

# ─────────────────────────────────────────────────────
# Noise patterns (politeness, signatures)
# ─────────────────────────────────────────────────────
_NOISE_PATTERNS = re.compile(
    r"(?i)(?:"
    r"bonjour[\s,]*|bonsoir[\s,]*|salut[\s,]*|"
    r"monsieur[\s,]*|madame[\s,]*|"
    r"cordialement[\s,\.]*|cdlt[\s,\.]*|bien cordialement[\s,\.]*|"
    r"bonne journée[\s,\.]*|bonne soirée[\s,\.]*|au revoir[\s,\.]*|"
    r"merci d'avance[\s,\.]*|merci pour votre aide[\s,\.]*|"
    r"merci[\s,\.]*|svp[\s,\.]*|stp[\s,\.]*|"
    r"s'?il\s+vous\s+pla[iî]t[\s,\.]*|s'?il\s+te\s+pla[iî]t[\s,\.]*|"
    r"pouvez-vous[\s,]*|pourriez-vous[\s,]*|"
    r"je\s+vous\s+contacte[\s,]*|"
    r"ci-joint[\s,]*|veuillez[\s,]*"
    r")"
)

# Encoding corruption signatures
_LATIN1_CORRUPTION = re.compile(
    r"(?:"
    r"Ã©|Ã¨|Ã |Ã®|Ã¯|Ã´|Ã¹|Ã»|Ã¢|Ã§|Ã‰|Ã€|Ã‡|"
    r"Ã\x89|Ã\xa9|Ã\xa8|Ã\xa0|Ã\xae|Ã\xaf"
    r")"
)

# ══════════════════════════════════════════════════════════════════════════════
# 2. DATA CLASSES — STRUCTURED OUTPUT
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class TelecomEntity:
    """A detected telecom entity with type, value, confidence and span."""
    entity_type: str            # ND, NRO, DSLAM, AVP, PORT, SLOT, CARD, etc.
    value: str                  # Extracted value (canonical form)
    raw_value: str              # Original text span
    confidence: float = 1.0
    start: int = -1             # Character offset in normalized text
    end: int = -1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.entity_type,
            "value": self.value,
            "raw": self.raw_value,
            "confidence": round(self.confidence, 3),
        }


@dataclass
class ErrorCode:
    """A detected error code with canonical form and confidence."""
    raw: str
    canonical: str
    code_type: str              # BRASIL, AVP, ORA, GENERIC
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw": self.raw,
            "canonical": self.canonical,
            "type": self.code_type,
            "confidence": round(self.confidence, 3),
        }


@dataclass
class IncidentContext:
    """
    Fully structured incident representation — output of SmartN3Parser.
    Ready for consumption by the RAG system and LLM prompt builder.
    """
    # ── Raw input
    raw_text: str = ""
    normalized_text: str = ""
    encoding_fixed: bool = False

    # ── Core NLP output
    intent: Intent = Intent.UNKNOWN
    intent_confidence: float = 0.0
    entities: List[TelecomEntity] = field(default_factory=list)
    error_codes: List[ErrorCode] = field(default_factory=list)
    systems: List[str] = field(default_factory=list)
    primary_system: str = "BRASIL"
    action: str = ""
    language: str = "fr"

    # ── Structured fields (best candidates per type)
    nd_number: Optional[str] = None
    nro_name: Optional[str] = None
    dslam_name: Optional[str] = None
    equipment_name: Optional[str] = None
    primary_error_code: Optional[str] = None

    # ── Quality scores
    confidence: float = 0.0
    trust_score: float = 0.25
    completeness_score: float = 0.0
    requires_human_review: bool = False

    # ── RAG helpers
    rag_query_primary: str = ""
    rag_query_fallback: str = ""
    suggested_fr_ids: List[str] = field(default_factory=list)

    def entities_by_type(self) -> Dict[str, List[str]]:
        """Return entities grouped by type."""
        result: Dict[str, List[str]] = {}
        for e in self.entities:
            result.setdefault(e.entity_type, []).append(e.value)
        return result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent.value,
            "intent_confidence": round(self.intent_confidence, 3),
            "entities": self.entities_by_type(),
            "error_codes": [ec.to_dict() for ec in self.error_codes],
            "systems": self.systems,
            "primary_system": self.primary_system,
            "action": self.action,
            "language": self.language,
            "nd_number": self.nd_number,
            "nro_name": self.nro_name,
            "dslam_name": self.dslam_name,
            "equipment_name": self.equipment_name,
            "primary_error_code": self.primary_error_code,
            "confidence": round(self.confidence, 3),
            "trust_score": round(self.trust_score, 3),
            "completeness_score": round(self.completeness_score, 3),
            "requires_human_review": self.requires_human_review,
            "rag_query_primary": self.rag_query_primary,
            "rag_query_fallback": self.rag_query_fallback,
            "suggested_fr_ids": self.suggested_fr_ids,
            "normalized_text": self.normalized_text,
            "encoding_fixed": self.encoding_fixed,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


# ══════════════════════════════════════════════════════════════════════════════
# 3. STEP IMPLEMENTATIONS
# ══════════════════════════════════════════════════════════════════════════════

class EncodingNormalizer:
    """
    Step 1 — Automatic encoding corruption detection and repair.

    Handles:
    - Latin-1 bytes decoded as UTF-8 (Ã© → é)
    - Windows-1252 corruption
    - Mixed encoding in a single string
    - Unicode control characters
    """

    # Mapping of common Latin-1→UTF-8 mojibake sequences
    _MOJIBAKE_MAP: Dict[str, str] = {
        "Ã©": "é", "Ã¨": "è", "Ã ": "à", "Ã®": "î", "Ã¯": "ï",
        "Ã´": "ô", "Ã¹": "ù", "Ã»": "û", "Ã¢": "â", "Ã§": "ç",
        "Ã‰": "É", "Ã€": "À", "Ã‡": "Ç", "Ã‹": "Ë",
        "Ã¦": "æ", "Å":  "œ", "â€™": "'", "â€œ": "\"", "â€": "\"",
        "â€": "–", "â€": "—", "Â ": " ", "Â°": "°", "Â«": "«",
        "Â»": "»", "â‚¬": "€", "Â£": "£",
    }

    # Compiled replacement regex
    _MOJIBAKE_RE: re.Pattern = re.compile(
        "|".join(re.escape(k) for k in sorted(_MOJIBAKE_MAP.keys(), key=len, reverse=True))
    )

    def normalize(self, text: str) -> Tuple[str, bool]:
        """
        Normalize encoding of input text.
        Returns (normalized_text, was_encoding_fixed).
        """
        if not text or not isinstance(text, str):
            return "", False

        fixed = False

        # 1. Try to fix mojibake sequences via substitution map
        if _LATIN1_CORRUPTION.search(text):
            text = self._MOJIBAKE_RE.sub(lambda m: self._MOJIBAKE_MAP[m.group(0)], text)
            fixed = True

        # 2. Try byte-level round-trip for remaining corruption
        try:
            probe = text.encode("latin-1").decode("utf-8")
            if probe != text and self._looks_valid_french(probe):
                text = probe
                fixed = True
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass

        # 3. Unicode NFC normalization (compose accents)
        text = unicodedata.normalize("NFC", text)

        # 4. Remove control characters (keep printable + whitespace)
        text = "".join(c for c in text if unicodedata.category(c)[0] != "C" or c in "\n\t ")

        return text, fixed

    @staticmethod
    def _looks_valid_french(text: str) -> bool:
        """Heuristic: does this look like valid French after re-decoding?"""
        french_chars = set("éèêëàâçùûüîïôæœÉÈÊËÀÂÇÙÛÜÎÏÔÆŒ")
        return any(c in french_chars for c in text)


class TextNormalizer:
    """
    Step 2 — Text normalization for telecom support messages.

    Handles:
    - Noise stripping (politeness, signatures)
    - Abbreviation expansion
    - Synonym normalization via TELECOM_SYNONYM_DICT
    - Short-message completion heuristics
    - Whitespace normalization
    """

    # BRASIL domain abbreviations → full form
    _ABBREVIATIONS: Dict[str, str] = {
        "nd":    "nœud de distribution",
        "nro":   "nœud de raccordement optique",
        "bas":   "boîtier d'accès service",
        "dslam": "digital subscriber line access multiplexer",
        "avp":   "avant-poste",
        "vlan":  "virtual local area network",
        "ihm":   "interface homme machine",
        "dlm":   "demande de livraison",
        "toc":   "table des occupations",
        "ccl":   "concentrateur de liens",
        "mep":   "mise en production",
        "thd":   "très haut débit",
        "ftth":  "fibre jusqu'au domicile",
        "pb":    "problème",
        "ko":    "hors service",
        "ok":    "opérationnel",
        "maj":   "mise à jour",
        "err":   "erreur",
        "supp":  "suppression",
        "rdv":   "rendez-vous",
        "cfg":   "configuration",
        "tx":    "transmission",
    }

    # Compiled synonym pattern (longest phrase first to avoid partial matches)
    _SYNONYM_RE: re.Pattern = re.compile(
        r"\b(" + "|".join(
            re.escape(k) for k in sorted(TELECOM_SYNONYM_DICT.keys(), key=len, reverse=True)
        ) + r")\b",
        re.IGNORECASE,
    )

    def normalize(self, text: str) -> str:
        """Full normalization pipeline."""
        if not text:
            return ""

        # Strip noise
        text = _NOISE_PATTERNS.sub(" ", text)

        # Apply synonym normalization
        text = self._apply_synonyms(text)

        # Normalize whitespace
        text = re.sub(r"[\r\n\t]+", " ", text)
        text = re.sub(r" {2,}", " ", text)

        return text.strip()

    def _apply_synonyms(self, text: str) -> str:
        """Replace telecom synonyms with canonical forms."""
        def replacer(m: re.Match) -> str:
            original = m.group(0)
            key = original.lower()
            return TELECOM_SYNONYM_DICT.get(key, original)
        return self._SYNONYM_RE.sub(replacer, text)

    def expand_abbreviations(self, text: str) -> str:
        """Expand abbreviations — for embedding enrichment only, not for display."""
        tokens = text.split()
        expanded = []
        for token in tokens:
            clean = re.sub(r"[^\w]", "", token.lower())
            if clean in self._ABBREVIATIONS:
                expanded.append(self._ABBREVIATIONS[clean])
            else:
                expanded.append(token)
        return " ".join(expanded)


class TelecomEntityExtractor:
    """
    Step 3 — Named Entity Recognition for telecom infrastructure.

    Extracts: ND, NRO, DSLAM, AVP, PORT, SLOT, CARD, EQUIPMENT,
              ORDER_ID, USER_ID, IP_ADDRESS, VLAN_ID, TRANSACTION_ID
    """

    def extract(self, text: str) -> List[TelecomEntity]:
        """Extract all telecom entities from normalized text."""
        entities: List[TelecomEntity] = []
        text_upper = text.upper()

        for entity_type, patterns in TELECOM_ENTITY_PATTERNS.items():
            for pattern, conf in patterns:
                for m in re.finditer(pattern, text, re.IGNORECASE):
                    # Extract value: group(1) if capture group exists, else group(0)
                    try:
                        raw_val = m.group(1)
                    except IndexError:
                        raw_val = m.group(0)

                    # Skip if value is just the keyword (no actual value captured)
                    if not raw_val or len(raw_val.strip()) < 2:
                        continue

                    canonical = self._canonicalize(entity_type, raw_val.strip())
                    entities.append(TelecomEntity(
                        entity_type=entity_type,
                        value=canonical,
                        raw_value=m.group(0),
                        confidence=conf,
                        start=m.start(),
                        end=m.end(),
                    ))

        # Deduplicate: keep highest confidence per (type, canonical_value)
        return self._deduplicate(entities)

    @staticmethod
    def _canonicalize(entity_type: str, value: str) -> str:
        """Normalize entity value to canonical form."""
        value = value.strip()
        if entity_type in ("ND",):
            return value.replace(" ", "").replace("-", "")
        if entity_type in ("NRO", "DSLAM", "EQUIPMENT"):
            return value.upper().replace(" ", "-")
        if entity_type in ("AVP",):
            return value.upper().replace(" ", "")
        return value.upper()

    @staticmethod
    def _deduplicate(entities: List[TelecomEntity]) -> List[TelecomEntity]:
        """Remove duplicate (type, value) pairs, keeping highest confidence."""
        seen: Dict[Tuple[str, str], TelecomEntity] = {}
        for e in entities:
            key = (e.entity_type, e.value)
            if key not in seen or e.confidence > seen[key].confidence:
                seen[key] = e
        return list(seen.values())


class ErrorCodeDetector:
    """
    Step 4 — Structured error code detection.

    Detects: B4002, AVP-1300, ORA-12170, ERR1300, BR-1300, 42C, 1300, 4002, ...
    Filters: Year numbers (2024, 2025, etc.) — common false positives
    """

    # Known error codes to their canonical families
    _CODE_FAMILY: Dict[str, str] = {
        "1300": "BRASIL",  "B1300": "BRASIL",
        "4002": "BRASIL",  "B4002": "BRASIL",
        "1002": "BRASIL",  "B1002": "BRASIL",
        "1203": "BRASIL",  "B1203": "BRASIL",
        "9903": "BRASIL",
        "42C":  "BRASIL",
        "2025": "BRASIL",  "2930": "BRASIL",
        "2016": "BRASIL",  "2017": "BRASIL",
    }

    def detect(self, text: str) -> List[ErrorCode]:
        """Detect all error codes in text."""
        codes: List[ErrorCode] = []
        seen: set = set()

        for pattern, prefix, conf in ERROR_CODE_PATTERNS:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                try:
                    raw_code = m.group(1)
                except IndexError:
                    raw_code = m.group(0)

                canonical = (prefix + raw_code).upper().replace(" ", "")

                # Filter year false positives
                if _YEAR_EXCLUSION.match(canonical):
                    continue

                if canonical in seen:
                    continue
                seen.add(canonical)

                code_type = self._CODE_FAMILY.get(canonical, "GENERIC")
                if "AVP" in canonical:
                    code_type = "AVP"
                elif "ORA" in canonical:
                    code_type = "ORACLE"
                elif "B" == canonical[0] and canonical[1:].isdigit():
                    code_type = "BRASIL"

                codes.append(ErrorCode(
                    raw=m.group(0),
                    canonical=canonical,
                    code_type=code_type,
                    confidence=conf,
                ))

        # Sort by confidence descending
        return sorted(codes, key=lambda c: c.confidence, reverse=True)


class IntentClassifier:
    """
    Step 5 — Intent classification.

    Phase 1: Keyword-phrase matching with scoring (immediate, no deps).
    Phase 2: (Placeholder) Replace with embedding cosine similarity for
             production deployment with sentence-transformers or Qdrant vectors.
    """

    def classify(self, text: str) -> Tuple[Intent, float]:
        """
        Classify intent of normalized text.
        Returns (intent, confidence_0_to_1).
        """
        text_lower = text.lower()
        scores: Dict[Intent, float] = {}

        for intent, phrase_groups in INTENT_PROFILES.items():
            total_score = 0.0
            for phrases, weight in phrase_groups:
                for phrase in phrases:
                    if phrase in text_lower:
                        total_score += weight
            if total_score > 0:
                scores[intent] = total_score

        if not scores:
            return Intent.UNKNOWN, 0.20

        # Pick highest priority intent among those with scores
        best_intent = max(
            scores.keys(),
            key=lambda i: (INTENT_PRIORITY.get(i, 0), scores[i])
        )
        raw_score = scores[best_intent]
        # Normalize to [0.40, 0.97]
        confidence = min(0.40 + raw_score * 0.12, 0.97)

        return best_intent, round(confidence, 3)

    # ── Embedding stub for Phase 2 ─────────────────────────────────────────
    # def classify_with_embeddings(
    #     self,
    #     text: str,
    #     embedder,          # SentenceTransformer or Qdrant client
    #     reference_vectors: Dict[Intent, List[float]],
    # ) -> Tuple[Intent, float]:
    #     """
    #     Classify using cosine similarity against per-intent reference vectors.
    #     reference_vectors: {Intent → embedding vector} (pre-computed)
    #     """
    #     import numpy as np
    #     query_vec = np.array(embedder.encode([text])[0])
    #     best_intent, best_sim = Intent.UNKNOWN, 0.0
    #     for intent, ref_vec in reference_vectors.items():
    #         ref = np.array(ref_vec)
    #         sim = float(np.dot(query_vec, ref) / (np.linalg.norm(query_vec) * np.linalg.norm(ref) + 1e-9))
    #         if sim > best_sim:
    #             best_sim, best_intent = sim, intent
    #     return best_intent, best_sim


class ConfidenceScorer:
    """
    Computes overall confidence and completeness scores for an IncidentContext.

    Confidence formula:
      base = intent_confidence × 0.40
      + has_error_code × 0.20
      + has_nd_or_nro × 0.15
      + has_known_system × 0.10
      + has_additional_entities × 0.10
      + message_length_bonus × 0.05

    Completeness formula (how much N3-critical context is present):
      nd_present × 0.30
      + error_code_present × 0.30
      + system_present × 0.20
      + action_present × 0.20
    """

    def compute(self, ctx: IncidentContext) -> Tuple[float, float]:
        """Returns (confidence, completeness)."""
        conf = ctx.intent_confidence * 0.40

        if ctx.error_codes:
            conf += 0.20
        if ctx.nd_number or ctx.nro_name or ctx.dslam_name:
            conf += 0.15
        if ctx.systems and ctx.primary_system != "BRASIL":
            conf += 0.10
        elif ctx.systems:
            conf += 0.05
        if len(ctx.entities) >= 3:
            conf += 0.10
        if len(ctx.normalized_text) > 50:
            conf += 0.05

        conf = round(min(conf, 0.97), 3)

        # Completeness
        completeness = 0.0
        if ctx.nd_number:
            completeness += 0.30
        if ctx.error_codes:
            completeness += 0.30
        if ctx.systems:
            completeness += 0.20
        if ctx.action and ctx.action != "investigate":
            completeness += 0.20

        return conf, round(min(completeness, 1.0), 3)


class RAGQueryBuilder:
    """
    Step 7 — RAG query generation from structured IncidentContext.

    Generates two queries:
    - primary: specific query using error code + intent + entity
    - fallback: broader query using intent + system for recall
    """

    # FR lookup table: error_code → FR IDs (production mapping)
    _FR_LOOKUP: Dict[str, List[str]] = {
        "1300":  ["FR-130", "FR-201"],
        "AVP1300": ["FR-201", "FR-130"],
        "B4002": ["FR-194"],
        "4002":  ["FR-194"],
        "42C":   ["FR-147B"],
        "9903":  ["FR-130", "FR-001"],
        "1002":  ["FR-012", "FR-013"],
        "1203":  ["FR-201"],
        "2025":  ["FR-101", "FR-194"],
        "2930":  ["FR-189"],
    }

    def build(self, ctx: IncidentContext) -> Tuple[str, str]:
        """
        Build (primary_query, fallback_query) for Qdrant retrieval.
        Returns tuple of two strings.
        """
        parts_primary: List[str] = []
        parts_fallback: List[str] = []

        # Primary: intent + error code
        intent_label = ctx.intent.value.replace("_", " ").lower()
        parts_primary.append(intent_label)
        parts_fallback.append(intent_label)

        if ctx.primary_error_code:
            parts_primary.append(f"erreur {ctx.primary_error_code}")
            parts_fallback.append(f"code {ctx.primary_error_code}")

        if ctx.nd_number:
            parts_primary.append(f"ND {ctx.nd_number}")

        if ctx.nro_name:
            parts_primary.append(f"NRO {ctx.nro_name}")

        if ctx.dslam_name:
            parts_primary.append(f"DSLAM {ctx.dslam_name}")

        if ctx.primary_system != "BRASIL":
            parts_primary.append(ctx.primary_system)
            parts_fallback.append(ctx.primary_system)

        parts_fallback.append("BRASIL")

        # Extract the normalized text (stripped to core 30 words)
        words = ctx.normalized_text.split()
        if words:
            parts_primary.append(" ".join(words[:20]))

        return " ".join(parts_primary), " ".join(parts_fallback)

    def suggest_fr_ids(self, ctx: IncidentContext) -> List[str]:
        """Suggest FR IDs based on detected error codes."""
        suggestions: List[str] = []
        for ec in ctx.error_codes:
            key = ec.canonical
            if key in self._FR_LOOKUP:
                for fr_id in self._FR_LOOKUP[key]:
                    if fr_id not in suggestions:
                        suggestions.append(fr_id)
        return suggestions


# ══════════════════════════════════════════════════════════════════════════════
# 4. MAIN PARSER — SmartN3Parser
# ══════════════════════════════════════════════════════════════════════════════

class SmartN3Parser:
    """
    Smart N3 Parser — 7-step intelligent parsing pipeline for BRASIL L3 support.

    Usage:
        parser = SmartN3Parser()
        ctx = parser.parse("nd supprimé brasil avp 1300 bloque commande")
        print(ctx.to_json())

    Pipeline:
        1. EncodingNormalizer   → fix latin-1 mojibake
        2. TextNormalizer       → strip noise, apply synonyms
        3. TelecomEntityExtractor → extract ND, NRO, DSLAM, etc.
        4. ErrorCodeDetector    → extract 1300, AVP-1300, B4002, etc.
        5. IntentClassifier     → ORDER_BLOCKED, DELETE_RESOURCE, etc.
        6. ConfidenceScorer     → confidence + completeness
        7. RAGQueryBuilder      → optimized Qdrant queries + FR suggestions
    """

    def __init__(self):
        self._encoding     = EncodingNormalizer()
        self._normalizer   = TextNormalizer()
        self._entity_extractor = TelecomEntityExtractor()
        self._error_detector   = ErrorCodeDetector()
        self._intent_classifier = IntentClassifier()
        self._confidence_scorer = ConfidenceScorer()
        self._rag_builder       = RAGQueryBuilder()

    # ─────────────────────────────────────────────────────
    # Main entry point
    # ─────────────────────────────────────────────────────

    def parse(self, raw_text: str) -> IncidentContext:
        """
        Parse a raw depositor message into a structured IncidentContext.

        Args:
            raw_text: Raw message from the depositor (any encoding)

        Returns:
            IncidentContext with all fields populated, ready for RAG.
        """
        ctx = IncidentContext(raw_text=raw_text)

        # ── Step 1: Encoding normalization ────────────────────────────
        text, ctx.encoding_fixed = self._encoding.normalize(raw_text)

        # ── Step 2: Text normalization ────────────────────────────────
        ctx.normalized_text = self._normalizer.normalize(text)

        # Work on combined text for better recall
        working_text = text + " " + ctx.normalized_text

        # ── Step 3: Telecom entity extraction ─────────────────────────
        ctx.entities = self._entity_extractor.extract(working_text)

        # Populate convenience fields
        nd_entities = [e for e in ctx.entities if e.entity_type == "ND"]
        if nd_entities:
            ctx.nd_number = nd_entities[0].value

        nro_entities = [e for e in ctx.entities if e.entity_type == "NRO"]
        if nro_entities:
            ctx.nro_name = nro_entities[0].value

        dslam_entities = [e for e in ctx.entities if e.entity_type == "DSLAM"]
        if dslam_entities:
            ctx.dslam_name = dslam_entities[0].value

        equip_entities = [e for e in ctx.entities if e.entity_type == "EQUIPMENT"]
        if equip_entities:
            ctx.equipment_name = equip_entities[0].value

        # ── Step 4: Error code detection ──────────────────────────────
        ctx.error_codes = self._error_detector.detect(working_text)
        if ctx.error_codes:
            ctx.primary_error_code = ctx.error_codes[0].canonical

        # ── Step 5: System detection ───────────────────────────────────
        ctx.systems = self._detect_systems(working_text)
        ctx.primary_system = ctx.systems[0] if ctx.systems else "BRASIL"

        # ── Step 6: Intent classification ─────────────────────────────
        ctx.intent, ctx.intent_confidence = self._intent_classifier.classify(working_text)

        # ── Step 6b: Action extraction ─────────────────────────────────
        ctx.action = self._extract_action(ctx.normalized_text, ctx.intent)

        # ── Step 6c: Language detection ────────────────────────────────
        ctx.language = self._detect_language(working_text)

        # ── Step 6d: Confidence + completeness ─────────────────────────
        ctx.confidence, ctx.completeness_score = self._confidence_scorer.compute(ctx)
        ctx.trust_score = self._compute_trust(ctx)
        ctx.requires_human_review = ctx.confidence < 0.55 or ctx.intent == Intent.UNKNOWN

        # ── Step 7: RAG query generation ──────────────────────────────
        ctx.rag_query_primary, ctx.rag_query_fallback = self._rag_builder.build(ctx)
        ctx.suggested_fr_ids = self._rag_builder.suggest_fr_ids(ctx)

        logger.debug(
            "[SmartN3Parser] intent=%s conf=%.2f codes=%s nd=%s",
            ctx.intent.value, ctx.confidence,
            [ec.canonical for ec in ctx.error_codes],
            ctx.nd_number,
        )
        return ctx

    # ─────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────

    @staticmethod
    def _detect_systems(text: str) -> List[str]:
        """Detect all system names mentioned in text."""
        text_lower = text.lower()
        found: List[str] = []
        for system, aliases in SYSTEM_ALIASES.items():
            if any(alias in text_lower for alias in aliases):
                found.append(system)
        if "BRASIL" not in found:
            found.insert(0, "BRASIL")
        return found

    @staticmethod
    def _extract_action(text: str, intent: Intent) -> str:
        """Map intent + text to a canonical action verb."""
        _INTENT_TO_ACTION: Dict[Intent, str] = {
            Intent.DELETE_RESOURCE:   "delete",
            Intent.CREATE_RESOURCE:   "create",
            Intent.UPDATE_RESOURCE:   "update",
            Intent.REPLAY_ORDER:      "replay",
            Intent.CANCEL_ORDER:      "cancel",
            Intent.UNLOCK_ORDER:      "unlock",
            Intent.ORDER_BLOCKED:     "investigate_block",
            Intent.DATA_INCONSISTENCY: "correct_data",
            Intent.LOG_ANALYSIS:      "analyze_logs",
            Intent.SCRIPT_BLOCKED:    "stop_script",
            Intent.CONFIGURATION_ERROR: "correct_config",
            Intent.DIAGNOSTIC:        "diagnose",
            Intent.DUPLICATE_RESOURCE: "resolve_duplicate",
        }
        return _INTENT_TO_ACTION.get(intent, "investigate")

    @staticmethod
    def _detect_language(text: str) -> str:
        """Lightweight FR/EN language detection."""
        fr_markers = {"erreur", "impossible", "supprimer", "bloqué", "commande",
                      "le", "la", "de", "du", "les", "une", "un", "sur", "avec"}
        en_markers = {"error", "cannot", "delete", "blocked", "command",
                      "the", "is", "are", "was", "on", "with", "cannot"}
        tokens = set(re.findall(r"\b\w+\b", text.lower()))
        fr_score = len(tokens & fr_markers)
        en_score = len(tokens & en_markers)
        return "en" if en_score > fr_score else "fr"

    @staticmethod
    def _compute_trust(ctx: IncidentContext) -> float:
        """Compute initial trust score for a raw ticket."""
        base = 0.25
        if ctx.error_codes:
            base += 0.05
        if ctx.nd_number or ctx.nro_name:
            base += 0.05
        if ctx.intent != Intent.UNKNOWN:
            base += 0.05
        if len(ctx.normalized_text) > 40:
            base += 0.03
        return round(min(base, 0.45), 3)


# ══════════════════════════════════════════════════════════════════════════════
# 5. INCIDENT NORMALIZER — Structured output for RAG prompt builder
# ══════════════════════════════════════════════════════════════════════════════

class IncidentNormalizer:
    """
    Converts a raw depositor message into a fully normalized incident
    usable directly by the RAG system and LLM prompt builder.

    Output is a JSON-serializable dict matching the RAG metadata schema.
    """

    def __init__(self):
        self._parser = SmartN3Parser()

    def normalize(self, raw_message: str, ticket_id: str = "") -> Dict[str, Any]:
        """
        Full normalization pipeline.

        Returns a dict with:
        - intent, confidence
        - entities grouped by type
        - error codes with types
        - systems
        - RAG queries
        - suggested FR IDs
        - metadata for Qdrant payload
        """
        ctx = self._parser.parse(raw_message)

        return {
            # ── Core output ──────────────────────────────────────────
            "ticket_id":           ticket_id or "UNKNOWN",
            "intent":              ctx.intent.value,
            "intent_confidence":   round(ctx.intent_confidence, 3),
            "action":              ctx.action,
            "language":            ctx.language,

            # ── Entities ─────────────────────────────────────────────
            "entities":            ctx.entities_by_type(),
            "nd_number":           ctx.nd_number,
            "nro_name":            ctx.nro_name,
            "dslam_name":          ctx.dslam_name,
            "equipment_name":      ctx.equipment_name,

            # ── Error codes ───────────────────────────────────────────
            "error_codes":         [ec.canonical for ec in ctx.error_codes],
            "primary_error_code":  ctx.primary_error_code,
            "error_code_details":  [ec.to_dict() for ec in ctx.error_codes],

            # ── Systems ───────────────────────────────────────────────
            "primary_system":      ctx.primary_system,
            "related_systems":     ctx.systems,

            # ── Quality ───────────────────────────────────────────────
            "confidence":          round(ctx.confidence, 3),
            "trust_score":         round(ctx.trust_score, 3),
            "completeness_score":  round(ctx.completeness_score, 3),
            "requires_human_review": ctx.requires_human_review,
            "encoding_fixed":      ctx.encoding_fixed,

            # ── RAG helpers ───────────────────────────────────────────
            "rag_query_primary":   ctx.rag_query_primary,
            "rag_query_fallback":  ctx.rag_query_fallback,
            "suggested_fr_ids":    ctx.suggested_fr_ids,

            # ── Text ─────────────────────────────────────────────────
            "raw_text":            ctx.raw_text,
            "normalized_text":     ctx.normalized_text,
        }

    def normalize_batch(
        self,
        messages: List[Dict[str, str]],
        id_field: str = "ticket_id",
        text_field: str = "raw_text",
    ) -> List[Dict[str, Any]]:
        """
        Normalize a batch of messages.
        Each item must have: {id_field: str, text_field: str}
        """
        results = []
        for item in messages:
            ticket_id = item.get(id_field, "")
            raw_text = item.get(text_field, "")
            results.append(self.normalize(raw_text, ticket_id))
        return results


# ══════════════════════════════════════════════════════════════════════════════
# 6. MODULE-LEVEL SINGLETONS (ready to import)
# ══════════════════════════════════════════════════════════════════════════════

# Primary parser instance
smart_parser = SmartN3Parser()

# Incident normalizer instance
incident_normalizer = IncidentNormalizer()


# ══════════════════════════════════════════════════════════════════════════════
# 7. DEMO & SELF-TEST
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import textwrap

    TEST_MESSAGES = [
        # (label, raw_message)
        ("Suppression ND (encoding cassé)",
         "nd supprimÃ© par erreur dans brasil - ND 0563741427"),

        ("AVP 1300 commande bloquée",
         "avp 1300 bloque commande NRO LIL701 impossible de passer"),

        ("Erreur B4002 création DSLAM",
         "impossible créer routeur nro LIL701 erreur B4002 BRASIL"),

        ("Script IHM bloqué",
         "Pouvez-vous arrêter le script en le mettant en erreur - script bloqué IHM"),

        ("Incohérence données terrain",
         "incohérence BRASIL TERRAIN - le noeud du NECHR10Z apparait CHROUX CHX/MSCH or noeud est CHROUX CHX/CHT1"),

        ("Rejouer la commande",
         "bonjour, pouvez-vous rejouer la commande sur le ND 0634581234 svp"),

        ("Message court sans contexte",
         "nd supprimé brasil"),

        ("Message multi-erreurs",
         "erreur 1300 et 42C sur transaction DSLAM-LIL701-01 port 24"),
    ]

    parser = SmartN3Parser()
    normalizer = IncidentNormalizer()

    print("=" * 70)
    print("SmartN3Parser — Self-Test")
    print("=" * 70)

    for label, msg in TEST_MESSAGES:
        print(f"\n▶  {label}")
        print(f"   Input : {msg[:80]!r}")
        ctx = parser.parse(msg)
        d = ctx.to_dict()
        print(f"   Intent: {d['intent']} (conf={d['intent_confidence']:.2f})")
        print(f"   Codes : {d['error_codes']}")
        print(f"   Entities: {d['entities']}")
        print(f"   ND={d['nd_number']}  NRO={d['nro_name']}")
        print(f"   Conf={d['confidence']:.2f}  Complete={d['completeness_score']:.2f}")
        print(f"   FR suggested: {d['suggested_fr_ids']}")
        print(f"   RAG-Q: {d['rag_query_primary'][:80]!r}")
        if d['encoding_fixed']:
            print(f"   ⚠️  Encoding was fixed")
        if d['requires_human_review']:
            print(f"   🔴 Requires human review")
        print()
