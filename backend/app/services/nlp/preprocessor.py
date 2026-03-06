"""
NLP Preprocessor — Language normalization, deduplication, domain glossary expansion
Converts raw ticket text into clean, normalized input for NLP enrichment.

Supports French/English mixed-language BRASIL tickets.
"""
import re
import unicodedata
from typing import Optional

# ─────────────────────────────────────────────
# Domain Glossary — BRASIL-specific abbreviations
# ─────────────────────────────────────────────
DOMAIN_GLOSSARY = {
    # Common ticket abbreviations
    "avp":      "avant-poste",
    "rdv":      "rendez-vous",
    "nd":       "nœud de distribution",
    "nro":      "nœud de raccordement optique",
    "bas":      "boîtier d'accès service",
    "dslam":    "digital subscriber line access multiplexer",
    "vlan":     "virtual local area network",
    "ihm":      "interface homme machine",
    "vc":       "virtual circuit",
    "vp":       "virtual path",
    "bbc":      "boucle locale cuivre",
    "dlm":      "demande de livraison",
    "mep":      "mise en production",
    "umi":      "unité de messagerie interne",
    "dico":     "dictionnaire",
    "mq":       "message queue",
    "toc":      "table des occupations",
    "ccl":      "concentrateur de liens",
    "farid":    "identifiant de fibre",
    "pf31":     "plateforme 31",
    "thd":      "très haut débit",
    "icc":      "identifiant client commun",
    "ope":      "opérateur",
    "upd":      "update",
    "supp":     "suppression",
    "err":      "erreur",
    "pb":       "problème",
    "config":   "configuration",
    "ko":       "hors service",
    "ok":       "opérationnel",
    "maj":      "mise à jour",
    "k.o.":     "hors service",
}

# ─────────────────────────────────────────────
# Noise patterns to strip
# ─────────────────────────────────────────────
NOISE_PATTERNS = [
    r"bonjour[,\s]*",
    r"bonsoir[,\s]*",
    r"salut[,\s]*",
    r"monsieur[,\s]*",
    r"madame[,\s]*",
    r"cordialement[,\s]*",
    r"merci[,\s]*d['e]\s*avance[,\s]*",
    r"merci[,\s]*",
    r"svp[,\s]*",
    r"stp[,\s]*",
    r"s'il vous plaît[,\s]*",
    r"s'il te plaît[,\s]*",
    r"bonne journée[,\s]*",
    r"bonne soirée[,\s]*",
    r"au revoir[,\s]*",
    r"cdlt[,\s]*",
]

# ─────────────────────────────────────────────
# Common typo / shorthand corrections
# ─────────────────────────────────────────────
TYPO_MAP = {
    "suprimmer":  "supprimer",
    "supprimmer": "supprimer",
    "suprimer":   "supprimer",
    "erruer":     "erreur",
    "eurreur":    "erreur",
    "connextion": "connexion",
    "connexion":  "connexion",
    "blokage":    "blocage",
    "bloquage":   "blocage",
    "immpossible":"impossible",
    "imposible":  "impossible",
    "anulation":  "annulation",
    "anulé":      "annulé",
    "créacion":   "création",
    "creaction":  "création",
    "verifier":   "vérifier",
    "verifié":    "vérifié",
    "lancer":     "lancer",
    "configurer": "configurer",
    "brasil":     "BRASIL",
    "seba":       "SEBA",
    "ipon":       "IPON",
    "artemis":    "ARTEMIS",
    "adelia":     "ADELIA",
    "orchestra":  "ORCHESTRA",
    "sca":        "SCA",
}


class TextPreprocessor:
    """
    Text preprocessing pipeline for BRASIL support tickets.

    Steps:
    1. Decode / normalize unicode
    2. Strip politeness noise
    3. Lowercase (except system names and error codes)
    4. Fix common typos via domain map
    5. Expand domain abbreviations
    6. Normalize whitespace
    """

    def __init__(self):
        self._noise_re = re.compile(
            "|".join(NOISE_PATTERNS), re.IGNORECASE
        )

    # ─────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────

    def preprocess(self, text: str) -> str:
        """
        Full preprocessing pipeline.
        Returns a clean, normalized string ready for NLP.
        """
        if not text or not isinstance(text, str):
            return ""

        text = self._normalize_unicode(text)
        text = self._strip_noise(text)
        text = self._fix_typos(text)
        text = self._normalize_whitespace(text)
        return text.strip()

    def extract_error_codes(self, text: str) -> list:
        """Extract all error codes from raw or preprocessed text."""
        if not text:
            return []
        codes = []
        # BRASIL specific: B4002, 1300, 1002, 42C, 9903, AVP-1300, ORA-xxxxx
        patterns = [
            r"\bB\d{4}\b",                    # B4002
            r"\bAVP[-\s]?\d+\b",              # AVP 1300, AVP-1300
            r"\bORA-\d{4,6}\b",               # ORA-12170
            r"\bERR(?:EUR)?[-_\s]?\d+\b",     # ERREUR 1002, ERR-42C
            r"\b\d{3,5}\b",                    # plain numeric codes 3-5 digits
            r"\b[A-Z]{2,4}[-_]\d{2,6}\b",     # XX-1234 format
            r"\b42C\b",                        # special: 42C
        ]
        for pattern in patterns:
            found = re.findall(pattern, text, re.IGNORECASE)
            codes.extend(f.upper() for f in found)
        # Deduplicate, keep order
        seen = set()
        result = []
        for c in codes:
            if c not in seen:
                seen.add(c)
                result.append(c)
        return result

    def detect_language(self, text: str) -> str:
        """
        Simple heuristic language detector (fr/en).
        Good enough for short telecom tickets.
        """
        if not text:
            return "fr"
        fr_words = {
            "erreur", "impossible", "supprimer", "blocage", "connexion",
            "commande", "lancer", "vérifier", "création", "problème",
            "merci", "bonjour", "svp", "le", "la", "les", "de", "du",
            "annulé", "depuis", "dans", "sur", "avec", "une", "un",
        }
        en_words = {
            "error", "cannot", "delete", "block", "connection",
            "command", "launch", "check", "create", "problem",
            "please", "hello", "the", "is", "are", "was", "on", "with",
        }
        text_lower = text.lower()
        tokens = set(re.findall(r"\b\w+\b", text_lower))
        fr_score = len(tokens & fr_words)
        en_score = len(tokens & en_words)
        return "en" if en_score > fr_score else "fr"

    def expand_abbreviations(self, text: str) -> str:
        """Expand domain-specific abbreviations."""
        tokens = text.split()
        expanded = []
        for token in tokens:
            lower = token.lower().rstrip(".,;:!?")
            if lower in DOMAIN_GLOSSARY:
                expanded.append(DOMAIN_GLOSSARY[lower])
            else:
                expanded.append(token)
        return " ".join(expanded)

    # ─────────────────────────────────────────────
    # Private helpers
    # ─────────────────────────────────────────────

    def _normalize_unicode(self, text: str) -> str:
        """Normalize unicode: keep accents for French, remove control chars."""
        # NFC normalization (compose accents)
        text = unicodedata.normalize("NFC", text)
        # Remove control characters but keep printable + spaces
        text = "".join(c for c in text if unicodedata.category(c)[0] != "C" or c in "\n\t")
        return text

    def _strip_noise(self, text: str) -> str:
        """Remove politeness phrases and salutations."""
        return self._noise_re.sub(" ", text)

    def _fix_typos(self, text: str) -> str:
        """Fix common typos using the domain typo map."""
        tokens = text.split()
        fixed = []
        for token in tokens:
            # Preserve punctuation
            clean = token.lower().strip(".,;:!?()")
            if clean in TYPO_MAP:
                # Preserve original casing style
                replacement = TYPO_MAP[clean]
                fixed.append(replacement)
            else:
                fixed.append(token)
        return " ".join(fixed)

    def _normalize_whitespace(self, text: str) -> str:
        """Collapse multiple spaces/newlines into single space."""
        text = re.sub(r"[\r\n\t]+", " ", text)
        text = re.sub(r" {2,}", " ", text)
        return text


# Singleton
preprocessor = TextPreprocessor()
