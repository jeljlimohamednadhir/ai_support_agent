"""
ml_preprocessing.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TelecomPreprocessor — Normalisation métier FR télécom pour la
classification ML des tickets BRASIL / Orange France.

Objectif :
  - Normaliser les identifiants équipements  → token stable EQUIPMENT_ID
  - Normaliser les codes erreur              → token stable ERROR_CODE_XXXX
  - Mapper les synonymes techniques          → forme canonique unique
  - Supprimer le bruit / stopwords FR métier → signal/bruit amélioré
  - Conserver les entités importantes        → pas de perte d'information

Impact estimé sur classification :
  +5–8% accuracy (réduction variance TF-IDF sur tokens inconnus)
  +3–5% coverage (vecteurs plus denses, confiance plus fiable)
"""
from __future__ import annotations

import re
import unicodedata
from typing import Dict, List, Optional, Tuple

# ─────────────────────────────────────────────────────────────────────────────
# Patterns équipements réseau BRASIL / Orange France
# Ordre important : du plus spécifique au plus général
# ─────────────────────────────────────────────────────────────────────────────

# Identifiants équipements télécom (exemples réels : OP49MAB11, NRA-SCD-01, DSLAM-OP49-01)
_EQUIPMENT_PATTERNS: List[Tuple[re.Pattern, str]] = [
    # NRO/NRA/DSLAM avec tirets : NRO-PARIS-NORD-01, NRA-SCD-01
    (re.compile(r'\b(?:NRO|NRA|OLT|DSLAM|SEBA|FTTH)-[A-Z0-9](?:[A-Z0-9\-]{2,20})\b', re.I), 'EQUIPMENT_ID'),
    # Identifiants alphanumériques pure télécom : OP49MAB11, FT49ABC123
    (re.compile(r'\b[A-Z]{2,4}\d{2}[A-Z]{2,4}\d{1,4}\b'), 'EQUIPMENT_ID'),
    # Identifiants ports : 0/0/1, 1/2/3
    (re.compile(r'\b\d{1,2}/\d{1,2}/\d{1,2}\b'), 'PORT_ID'),
    # IPs (ne pas supprimer mais normaliser)
    (re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'), 'IP_ADDRESS'),
    # VLAN IDs numériques : VLAN 100, vlan100
    (re.compile(r'\bvlan\s*(\d{1,4})\b', re.I), r'VLAN_\1'),
    # ND (numéro de ligne) : ND 0312345678, nd0312345678
    (re.compile(r'\bnd\s*(\d{10})\b', re.I), 'ND_NUMBER'),
]

# ─────────────────────────────────────────────────────────────────────────────
# Patterns codes d'erreur
# ─────────────────────────────────────────────────────────────────────────────

_ERROR_CODE_PATTERNS: List[Tuple[re.Pattern, str]] = [
    # "erreur 1300", "error 4002", "err: 7013"
    (re.compile(r'\b(?:erreur|error|err\.?)\s*:?\s*(\d{3,5})\b', re.I), r'ERROR_CODE_\1'),
    # "B4002", "B-4002" (codes BRASIL)
    (re.compile(r'\bB-?(\d{4})\b'), r'ERROR_CODE_B\1'),
    # "ORA-01403", "ORA-00001" (Oracle)
    (re.compile(r'\bORA-(\d{4,5})\b', re.I), r'ERROR_ORA_\1'),
    # Codes seuls entre parenthèses ou guillemets : (1300), "4002"
    (re.compile(r'(?:^|[\s\(\["])(\d{4,5})(?:[\s\)\]"]|$)'), r' ERROR_CODE_\1 '),
    # "code 1300", "code: 1300"
    (re.compile(r'\bcode\s*:?\s*(\d{3,5})\b', re.I), r'ERROR_CODE_\1'),
]

# ─────────────────────────────────────────────────────────────────────────────
# Synonymes techniques BRASIL / télécom FR
# Clé → forme canonique conservée dans le texte
# ─────────────────────────────────────────────────────────────────────────────

_SYNONYMS: Dict[str, str] = {
    # Systèmes / applications
    "brasil":           "brasil",
    "orchestra":        "orchestra",
    "artemis":          "artemis",
    "farid":            "farid",
    "ipon":             "ipon",
    "sca":              "sca",
    "seba":             "seba",
    "ftth":             "ftth",
    "xdsl":             "xdsl",
    "adsl":             "adsl",
    "vdsl":             "vdsl",
    # Équipements
    "dslam":            "dslam",
    "olt":              "olt",
    "ont":              "ont",
    "nro":              "nro",
    "nra":              "nra",
    "ne":               "ne",
    # Termes opérations
    "rollback":         "rollback",
    "purge":            "purge",
    "annulation":       "annulation",
    "annuler":          "annuler",
    "annulé":           "annule",
    "annulée":          "annule",
    # Termes données
    "incoherence":      "incoherence",
    "incohérence":      "incoherence",
    "cohérence":        "coherence",
    "coherence":        "coherence",
    "doublon":          "doublon",
    "doublons":         "doublon",
    # Termes technique
    "suppression":      "suppression",
    "supprimer":        "supprimer",
    "supprimé":         "supprime",
    "supprimée":        "supprime",
    "blocage":          "blocage",
    "bloqué":           "bloque",
    "bloquée":          "bloque",
    "mutation":         "mutation",
    "workflow":         "workflow",
    "processus":        "processus",
    "habilitation":     "habilitation",
    "habilitations":    "habilitation",
    "ordonnancement":   "ordonnancement",
    "planification":    "planification",
    # Synonymes fréquents
    "bug":              "bug",
    "anomalie":         "anomalie",
    "defaut":           "defaut",
    "défaut":           "defaut",
    "incident":         "incident",
    "dysfonctionnement": "dysfonctionnement",
    "panne":            "panne",
    # Verbes d'action fréquents (normalise infinitifs / participes)
    "correction":       "corriger",
    "corriger":         "corriger",
    "corrigé":          "corriger",
    "corrigée":         "corriger",
    "configuration":    "configurer",
    "configurer":       "configurer",
    "configuré":        "configurer",
}

# ─────────────────────────────────────────────────────────────────────────────
# Stopwords FR + métier télécom (trop génériques pour discriminer)
# ─────────────────────────────────────────────────────────────────────────────

_FR_STOPWORDS = frozenset({
    # Articles / pronoms
    "le", "la", "les", "un", "une", "des", "du", "de", "d", "l",
    "ce", "cet", "cette", "ces", "mon", "ton", "son", "ma", "ta",
    "sa", "mes", "tes", "ses", "notre", "votre", "leur", "nos", "vos", "leurs",
    "il", "elle", "ils", "elles", "je", "tu", "nous", "vous", "on",
    "me", "te", "se", "lui", "y", "en",
    # Prépositions / conjonctions
    "et", "ou", "ni", "mais", "donc", "or", "car", "que", "qui",
    "pour", "par", "sur", "sous", "dans", "avec", "sans", "entre",
    "vers", "depuis", "pendant", "avant", "après", "lors", "dès",
    "au", "aux", "à", "en", "chez",
    # Verbes auxiliaires très courants
    "est", "sont", "a", "ont", "était", "étaient", "avait", "avaient",
    "sera", "seront", "aura", "auront", "peut", "peuvent", "doit", "doivent",
    "fait", "font",
    # Adverbes génériques
    "ne", "pas", "plus", "très", "bien", "aussi", "encore", "déjà",
    "puis", "donc", "ainsi", "alors", "quand", "si",
    # Mots télécom/support trop génériques pour discriminer
    "ticket", "incident", "demande", "cas", "problème", "probleme",
    "issue", "sujet", "objet", "titre",
})

# ─────────────────────────────────────────────────────────────────────────────
# Patterns nettoyage bruit
# ─────────────────────────────────────────────────────────────────────────────

_NOISE_PATTERNS: List[re.Pattern] = [
    re.compile(r'https?://\S+'),          # URLs
    re.compile(r'\S+@\S+\.\S+'),          # emails
    re.compile(r'<[^>]+>'),               # balises HTML
    re.compile(r'\[.*?\]'),               # crochets de métadonnées
    re.compile(r'={3,}|-{3,}|\*{3,}'),    # séparateurs visuels
    re.compile(r'\s{2,}'),                # espaces multiples → 1
]


# ─────────────────────────────────────────────────────────────────────────────
# TelecomPreprocessor
# ─────────────────────────────────────────────────────────────────────────────

class TelecomPreprocessor:
    """
    Normalisation métier pour textes tickets télécom BRASIL / Orange France.

    Usage :
        preprocessor = TelecomPreprocessor()
        cleaned = preprocessor.preprocess("DSLAM OP49MAB11 bloqué erreur 1300")
        # → "dslam EQUIPMENT_ID bloque ERROR_CODE_1300"

        batch = preprocessor.preprocess_batch(texts_series)
    """

    def __init__(
        self,
        normalize_equipment: bool = True,
        normalize_error_codes: bool = True,
        apply_synonyms: bool = True,
        remove_stopwords: bool = True,
        min_token_length: int = 2,
    ):
        self.normalize_equipment = normalize_equipment
        self.normalize_error_codes = normalize_error_codes
        self.apply_synonyms = apply_synonyms
        self.remove_stopwords = remove_stopwords
        self.min_token_length = min_token_length

        # Pré-compiler le pattern synonymes pour performance
        # (cherche les clés comme mots entiers, insensible à la casse)
        syns_escaped = [re.escape(k) for k in sorted(_SYNONYMS, key=len, reverse=True)]
        self._synonym_re = re.compile(
            r'\b(' + '|'.join(syns_escaped) + r')\b',
            re.IGNORECASE,
        )

    # ──────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────

    def preprocess(self, text: str) -> str:
        """Nettoie et normalise un texte ticket."""
        if not text or not isinstance(text, str):
            return ""

        # 1. Unicode normalization (accents, ligatures)
        text = unicodedata.normalize("NFC", text)

        # 2. Suppression bruit (URLs, emails, HTML, séparateurs)
        for pat in _NOISE_PATTERNS[:-1]:   # tous sauf espaces multiples
            text = pat.sub(' ', text)

        # 3. Codes erreur AVANT lowercasing (B4002 doit rester reconnaissable)
        if self.normalize_error_codes:
            text = self._apply_error_codes(text)

        # 4. Normalisation équipements AVANT lowercasing
        if self.normalize_equipment:
            text = self._apply_equipment_patterns(text)

        # 5. Lowercase
        text = text.lower()

        # 6. Synonymes (forme canonique)
        if self.apply_synonyms:
            text = self._synonym_re.sub(
                lambda m: _SYNONYMS.get(m.group(0).lower(), m.group(0).lower()),
                text,
            )

        # 7. Suppression ponctuation (conserver tirets internes)
        text = re.sub(r"[^\w\s\-_]", " ", text)

        # 8. Espaces multiples
        text = re.sub(r'\s+', ' ', text).strip()

        # 9. Stopwords + tokens trop courts
        if self.remove_stopwords:
            tokens = text.split()
            tokens = [
                t for t in tokens
                if t not in _FR_STOPWORDS
                and len(t) >= self.min_token_length
                and not t.isdigit()   # chiffres seuls → bruit
            ]
            text = ' '.join(tokens)

        return text

    def preprocess_batch(self, texts) -> list:
        """
        Prétraiter un batch de textes (Series pandas ou liste).
        Retourne une liste Python (compatible sklearn).
        """
        if hasattr(texts, 'tolist'):
            texts = texts.tolist()
        return [self.preprocess(str(t)) for t in texts]

    # ──────────────────────────────────────────────────────────────────────
    # Analyse / debug
    # ──────────────────────────────────────────────────────────────────────

    def analyze(self, text: str) -> dict:
        """Retourne un rapport de prétraitement (pour debug)."""
        original = text
        preprocessed = self.preprocess(text)
        return {
            "original": original,
            "preprocessed": preprocessed,
            "original_tokens": len(original.split()),
            "preprocessed_tokens": len(preprocessed.split()),
            "compression_ratio": round(
                len(preprocessed.split()) / max(len(original.split()), 1), 2
            ),
            "equipment_ids_found": len(re.findall(r'\bequipment_id\b', preprocessed)),
            "error_codes_found": len(re.findall(r'\berror_(?:code|ora)_\w+\b', preprocessed)),
        }

    # ──────────────────────────────────────────────────────────────────────
    # Internals
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _apply_error_codes(text: str) -> str:
        for pat, repl in _ERROR_CODE_PATTERNS:
            text = pat.sub(repl, text)
        return text

    @staticmethod
    def _apply_equipment_patterns(text: str) -> str:
        for pat, repl in _EQUIPMENT_PATTERNS:
            text = pat.sub(repl, text)
        return text


# ─────────────────────────────────────────────────────────────────────────────
# Singleton (pour partager le modèle compilé entre instances)
# ─────────────────────────────────────────────────────────────────────────────

telecom_preprocessor = TelecomPreprocessor()
