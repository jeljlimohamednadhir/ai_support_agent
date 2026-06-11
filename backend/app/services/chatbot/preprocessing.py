"""
preprocessing.py — Normalisation des requêtes utilisateur BRASIL
================================================================
Extrait et normalise:
  - Numéros ND (9 chiffres)
  - Noms d'équipements (DSLAM, NIP, BRAS, etc.)
  - Codes d'erreur numériques
  - IDs de dossiers de fabrication (format VARCHAR 20)
  - IDs EPC
  - Patterns de logs
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional
from .ontology import get_entity_for_query, EntityType


# ─── Patterns regex ───────────────────────────────────────────────────────────


# ND: exactement 9 chiffres (parfois précédé de "nd " ou "ND:")
_ND_PATTERN = re.compile(r'\b(\d{9})\b')

# Équipements réseau: codes typiques BRASIL
_EQUIPMENT_PATTERN = re.compile(
    r'\b([A-Z]{2,6}\d{2,}[A-Z0-9\-]{0,10})\b',  # Ex: DSLAM01, NIP042, BRAS-01
    re.IGNORECASE,
)

# Codes d'erreur: "erreur XXXX", "code XXXX", "error XXXX"
_ERROR_CODE_PATTERN = re.compile(
    r'(?:erreur|error|code|err)\s*[=:#]?\s*(\d{3,5})',
    re.IGNORECASE,
)

# IDs dossiers de fabrication (format mkfl_fileid VARCHAR 20)
_MAKING_FILE_ID_PATTERN = re.compile(
    r'\b(MK\w{4,18}|DL\w{4,18}|[A-Z]{2}\d{6,15})\b',
    re.IGNORECASE,
)

# Exception Java dans un log
_EXCEPTION_PATTERN = re.compile(
    r'\b([A-Z][a-zA-Z]+Exception)\b'
)

# VLAN ID (1-4094)
_VLAN_PATTERN = re.compile(
    r'\bvlan\s*[=:#]?\s*(\d{1,4})\b',
    re.IGNORECASE,
)

# IP address
_IP_PATTERN = re.compile(
    r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b'
)


# ─── Résultat de la normalisation ─────────────────────────────────────────────


@dataclass
class NormalizedQuery:
    raw: str
    nds: List[str] = field(default_factory=list)
    equipment_names: List[str] = field(default_factory=list)
    error_codes: List[str] = field(default_factory=list)
    making_file_ids: List[str] = field(default_factory=list)
    exceptions: List[str] = field(default_factory=list)
    vlans: List[str] = field(default_factory=list)
    ip_addresses: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)   # canonical entity types
    primary_entity_type: Optional[str] = None
    normalized_text: str = ""

    def has_nd(self) -> bool:
        return bool(self.nds)

    def first_nd(self) -> Optional[str]:
        return self.nds[0] if self.nds else None

    def has_error_code(self) -> bool:
        return bool(self.error_codes)

    def has_exception(self) -> bool:
        return bool(self.exceptions)

    def summary(self) -> str:
        parts = []
        if self.nds:
            parts.append(f"ND={self.nds}")
        if self.equipment_names:
            parts.append(f"EQPT={self.equipment_names}")
        if self.error_codes:
            parts.append(f"ERR={self.error_codes}")
        if self.making_file_ids:
            parts.append(f"MKFL={self.making_file_ids}")
        if self.exceptions:
            parts.append(f"EXC={self.exceptions}")
        if self.vlans:
            parts.append(f"VLAN={self.vlans}")
        return " | ".join(parts) if parts else "no structured data"


# ─── Normaliseur ─────────────────────────────────────────────────────────────


class BrasilQueryPreprocessor:
    """Normalise une requête utilisateur en entités BRASIL structurées."""

    # Mots-clés d'équipement connus (filtre les faux positifs regex)
    EQUIPMENT_KEYWORDS = {
        "dslam", "nip", "bras", "olt", "ont", "onu", "ftth", "xdsl",
        "adsl", "vdsl", "gpon", "epon",
    }

    def normalize(self, query: str) -> NormalizedQuery:
        result = NormalizedQuery(raw=query)

        # ND (9 chiffres)
        result.nds = list(dict.fromkeys(_ND_PATTERN.findall(query)))

        # Codes d'erreur
        result.error_codes = list(dict.fromkeys(_ERROR_CODE_PATTERN.findall(query)))

        # Exceptions Java
        result.exceptions = list(dict.fromkeys(_EXCEPTION_PATTERN.findall(query)))

        # VLAN IDs
        result.vlans = list(dict.fromkeys(_VLAN_PATTERN.findall(query)))

        # IP addresses
        result.ip_addresses = list(dict.fromkeys(_IP_PATTERN.findall(query)))

        # Noms d'équipements (filtrer les NDs et les faux positifs)
        raw_eqpts = _EQUIPMENT_PATTERN.findall(query)
        result.equipment_names = [
            e for e in dict.fromkeys(raw_eqpts)
            if not _ND_PATTERN.match(e)
            and any(kw in e.lower() for kw in self.EQUIPMENT_KEYWORDS)
        ]

        # Dossiers de fabrication
        raw_mkfl = _MAKING_FILE_ID_PATTERN.findall(query)
        result.making_file_ids = [
            m for m in dict.fromkeys(raw_mkfl)
            if not _ND_PATTERN.match(m)
        ]

        # Entités canoniques
        matched_entities = get_entity_for_query(query)
        result.entities = [e.entity_type.value for e in matched_entities]

        # Type d'entité primaire (priorité: ND > MAKING_FILE > EPC > EQUIPMENT > VLAN)
        priority = ["ND", "MAKING_FILE", "EPC", "EQUIPMENT", "VLAN", "MRT", "TP"]
        for p in priority:
            if p in result.entities:
                result.primary_entity_type = p
                break

        # Texte normalisé (lowercase, poncuation simplifiée)
        result.normalized_text = query.lower().strip()

        return result

    def extract_nd(self, text: str) -> Optional[str]:
        """Extrait le premier ND trouvé dans le texte."""
        match = _ND_PATTERN.search(text)
        return match.group(1) if match else None

    def extract_error_code(self, text: str) -> Optional[str]:
        """Extrait le premier code d'erreur trouvé."""
        match = _ERROR_CODE_PATTERN.search(text)
        return match.group(1) if match else None

    def is_nd(self, value: str) -> bool:
        """Vérifie si une valeur est un ND valide (9 chiffres)."""
        return bool(re.match(r'^\d{9}$', value.strip()))

    def normalize_equipment_name(self, name: str) -> str:
        """Normalise un nom d'équipement (uppercase, trim)."""
        return name.strip().upper()

    def detect_intent_hints(self, query: NormalizedQuery) -> List[str]:
        """Retourne des hints d'intent basés sur la requête normalisée."""
        hints = []
        text = query.normalized_text

        # Hints basés sur les entités trouvées
        if query.has_nd():
            hints.append("check_nd")
        if query.has_error_code():
            if "1300" in query.error_codes:
                hints.append("error_1300_nd")
            else:
                hints.append("script_failed")
        if query.has_exception():
            for exc in query.exceptions:
                if "Vlan" in exc:
                    hints.append("vlan_issue")
                elif "Epc" in exc:
                    hints.append("check_epc")
                elif "Dslam" in exc:
                    hints.append("dslam_access_issue")

        # Hints basés sur les mots-clés
        keyword_hints = {
            "bloqué": "making_file_blocked",
            "dossier": "check_making_file",
            "making file": "check_making_file",
            "vlan": "vlan_issue",
            "epc": "check_epc",
            "mouvement": "check_epc",
            "tp bloqué": "tp_blocked",
            "script": "script_failed",
            "dlm": "dl_folder_open",
            "ftth": "ftth_scenario",
            "service logique": "sl_not_found",
            "vp": "vp_creation_failed",
        }
        for keyword, hint in keyword_hints.items():
            if keyword in text:
                hints.append(hint)

        return list(dict.fromkeys(hints))  # dedup, preserve order


# Singleton exporté
preprocessor = BrasilQueryPreprocessor()
