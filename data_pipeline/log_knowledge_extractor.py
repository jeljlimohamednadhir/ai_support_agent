"""
Log Knowledge Extractor — Transforms raw BRASIL application logs into structured
diagnostic knowledge records ready for RAG indexing.

Algorithm:
  1. Load log events from log_events.json (produced by log_ingester.py)
  2. Run template mining (Drain3-style grouping) to discover error patterns
  3. For each pattern, build a LogKnowledgeRecord with:
       - error_pattern (normalized template)
       - exception (exception class name)
       - application + component
       - probable_root_cause
       - diagnostic_actions + resolution_actions
       - trust_score (based on frequency + validation)
  4. Cross-reference with BRASIL exception catalog
  5. Output: data_pipeline/output/log_knowledge.json

Input : data_pipeline/output/log_events.json
Output: data_pipeline/output/log_knowledge.json

Usage:
  python data_pipeline/log_knowledge_extractor.py
  python data_pipeline/log_knowledge_extractor.py --min-freq 3 --dry-run
"""
import json
import re
import sys
import math
import hashlib
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from collections import Counter, defaultdict

BACKEND_DIR = Path(__file__).parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

INPUT_FILE  = Path(__file__).parent / "output" / "log_events.json"
OUTPUT_FILE = Path(__file__).parent / "output" / "log_knowledge.json"

# Minimum occurrences for a pattern to produce a knowledge record
MIN_FREQUENCY = 2


# ─────────────────────────────────────────────────────────────────────────────
# BRASIL Exception Catalog
# Each entry defines what the engine knows about a specific exception class.
# This is the core domain knowledge encoded by N3 engineers.
# ─────────────────────────────────────────────────────────────────────────────

EXCEPTION_CATALOG: Dict[str, Dict[str, Any]] = {

    "DslamClosedForProductionException": {
        "application": "BRASIL",
        "component": "provisioning_engine",
        "related_systems": ["SEBA", "ORCHESTRA"],
        "incident_type": "provisioning_failure",
        "probable_root_cause": (
            "Le DSLAM cible est marqué comme fermé à la production dans le référentiel NE. "
            "Toute commande de provisioning sur ce DSLAM est bloquée."
        ),
        "diagnostic_actions": [
            "Vérifier le statut du DSLAM dans ORCHESTRA → Référentiel NE → Recherche par DSLAM_ID",
            "Contrôler la date de mise en production et la raison de fermeture",
            "Vérifier la cohérence entre BRASIL et SEBA sur l'état du NE",
            "Identifier si une opération de maintenance est en cours (ticket réseau)",
        ],
        "resolution_actions": [
            "Contacter l'équipe réseau pour confirmation statut DSLAM",
            "Soumettre demande de réouverture via ticket JIRA composant ORCHESTRA-NE",
            "Après confirmation réouverture : corriger le statut dans le référentiel NE",
            "Re-jouer la commande BRASIL après réouverture confirmée",
            "Vérifier synchronisation SEBA après re-jeu",
        ],
        "severity": "high",
    },

    "UnknownMRTIdException": {
        "application": "BRASIL",
        "component": "routing_engine",
        "related_systems": ["SEBA"],
        "incident_type": "data_inconsistency",
        "probable_root_cause": (
            "L'identifiant MRT référencé est introuvable ou a expiré dans le référentiel BRASIL. "
            "Cause typique : migration de données incomplète ou identifiant créé localement sans propagation."
        ),
        "diagnostic_actions": [
            "Rechercher l'identifiant MRT dans BRASIL Admin → Référentiel → MRT",
            "Vérifier si une migration de données a eu lieu récemment",
            "Contrôler la synchronisation entre BRASIL et SEBA sur ce MRT_ID",
            "Vérifier les logs de migration pour ce MRT_ID",
        ],
        "resolution_actions": [
            "Si MRT inexistant : recréer via procédure admin BRASIL",
            "Si MRT expiré : réactiver ou générer un nouvel identifiant",
            "Forcer la synchronisation BRASIL → SEBA après correction",
            "Re-jouer la commande avec le MRT_ID corrigé",
        ],
        "severity": "high",
    },

    "AvailableNetworkResourcesDisallowProductionException": {
        "application": "BRASIL",
        "component": "resource_manager",
        "related_systems": ["ORCHESTRA", "SEBA"],
        "incident_type": "provisioning_failure",
        "probable_root_cause": (
            "Les ressources réseau disponibles sur l'équipement cible sont insuffisantes ou bloquées. "
            "Le DSLAM est peut-être saturé (compteurs à 100%) ou en état de restriction."
        ),
        "diagnostic_actions": [
            "Vérifier le taux d'occupation du DSLAM dans ORCHESTRA",
            "Contrôler les compteurs de ports disponibles sur le NE cible",
            "Vérifier si d'autres commandes simultanées utilisent les mêmes ressources",
            "Analyser les logs ORCHESTRA pour des alertes de saturation",
        ],
        "resolution_actions": [
            "Si saturation : demande d'extension de capacité auprès de l'équipe réseau",
            "Si ressources bloquées temporairement : attendre libération et rejouer",
            "Si compteurs erronés : corriger via admin ORCHESTRA → Gestion NE",
            "Ouvrir un ticket réseau si problème persistant sur ce DSLAM",
        ],
        "severity": "high",
    },

    "DslamUnreachableException": {
        "application": "BRASIL",
        "component": "network_connector",
        "related_systems": ["ORCHESTRA", "SEBA"],
        "incident_type": "network_equipment_issue",
        "probable_root_cause": (
            "Le DSLAM n'est pas joignable depuis BRASIL. "
            "Panne matérielle, problème réseau sur le flux de supervision, ou équipement hors ligne."
        ),
        "diagnostic_actions": [
            "Ping/trace le DSLAM depuis le serveur BRASIL",
            "Vérifier le statut dans ORCHESTRA → Supervision NE",
            "Contacter l'équipe réseau pour diagnostic terrain",
            "Vérifier les alertes NetManager/NMS sur ce DSLAM",
        ],
        "resolution_actions": [
            "Escalader immédiatement à l'équipe réseau si DSLAM down",
            "Si intermittent : programmer une surveillance et rejouer la commande plus tard",
            "Documenter l'indisponibilité pour le rapport d'incident",
        ],
        "severity": "critical",
    },

    "CommandValidationException": {
        "application": "BRASIL",
        "component": "command_processor",
        "related_systems": ["ADELIA", "SEBA"],
        "incident_type": "command_failure",
        "probable_root_cause": (
            "La commande ne respecte pas les règles de validation métier BRASIL. "
            "Le dossier client est incomplet ou les prérequis de la commande ne sont pas satisfaits."
        ),
        "diagnostic_actions": [
            "Consulter le message d'erreur détaillé dans les logs BRASIL pour le champ en erreur",
            "Vérifier la complétude du dossier client dans BRASIL",
            "Contrôler le séquencement : une commande précédente est-elle en attente ?",
            "Vérifier les données ADELIA associées au client",
        ],
        "resolution_actions": [
            "Compléter les champs manquants dans le dossier client",
            "S'assurer que les commandes précédentes sont terminées avant de relancer",
            "Si champ ADELIA manquant : déclencher synchronisation ADELIA → BRASIL",
            "Re-soumettre la commande après correction",
        ],
        "severity": "medium",
    },

    "BusinessRuleViolationException": {
        "application": "BRASIL",
        "component": "business_rules_engine",
        "related_systems": ["ADELIA"],
        "incident_type": "command_failure",
        "probable_root_cause": (
            "Une règle métier BRASIL a été violée. "
            "Le code erreur 1300 est souvent associé à ce type d'exception."
        ),
        "diagnostic_actions": [
            "Identifier la règle violée dans les logs (champ violated_rule)",
            "Vérifier si le code erreur 1300 est présent dans les logs",
            "Contrôler les données du dossier client vs les critères de la règle",
            "Consulter la documentation de la règle métier concernée",
        ],
        "resolution_actions": [
            "Corriger les données en violation de la règle",
            "Si règle incohérente : ouvrir un ticket JIRA BRASIL-RULES",
            "Contacter le responsable métier si la règle doit être assouplie",
        ],
        "severity": "medium",
    },

    "ConnectorUnavailableException": {
        "application": "BRASIL",
        "component": "integration_layer",
        "related_systems": ["SEBA", "IPON", "ARTEMIS", "SCA", "ORCHESTRA"],
        "incident_type": "system_integration_error",
        "probable_root_cause": (
            "Le connecteur vers un système tiers est indisponible. "
            "Causes possibles : système tiers down, timeout réseau, certificat SSL expiré, "
            "mauvaise configuration endpoint."
        ),
        "diagnostic_actions": [
            "Identifier le système tiers concerné dans les logs (champ upstream_system)",
            "Tester la connectivité réseau vers l'endpoint du système tiers",
            "Vérifier le statut du service tiers (supervision)",
            "Contrôler la validité du certificat SSL si HTTPS",
            "Vérifier les logs du système tiers pour des erreurs côté serveur",
        ],
        "resolution_actions": [
            "Si système tiers down : attendre rétablissement ou déclencher une astreinte",
            "Si SSL expiré : renouveler le certificat et redémarrer le connecteur",
            "Si timeout réseau : vérifier les règles de firewall et les proxies",
            "Redémarrer le connecteur BRASIL après résolution",
            "Re-jouer les commandes en attente après rétablissement",
        ],
        "severity": "high",
    },

    "IntegrationTimeoutException": {
        "application": "BRASIL",
        "component": "integration_layer",
        "related_systems": ["SEBA", "ORCHESTRA", "IPON"],
        "incident_type": "system_integration_error",
        "probable_root_cause": (
            "Une requête vers un système tiers a dépassé le délai d'attente configuré. "
            "Le système tiers répond trop lentement ou est surchargé."
        ),
        "diagnostic_actions": [
            "Mesurer le temps de réponse actuel du système tiers",
            "Vérifier la charge du système tiers (CPU/mémoire)",
            "Consulter les logs du système tiers pour des lenteurs",
            "Vérifier si le timeout BRASIL est configuré de façon appropriée",
        ],
        "resolution_actions": [
            "Si surcharge temporaire : attendre et rejouer",
            "Si récurrent : augmenter le timeout configuré dans BRASIL (config connecteur)",
            "Ouvrir un ticket de performance auprès de l'équipe du système tiers",
            "Mettre en place un mécanisme de retry avec backoff exponentiel",
        ],
        "severity": "medium",
    },

    "SessionExpiredException": {
        "application": "BRASIL",
        "component": "access_management",
        "related_systems": [],
        "incident_type": "access_management_error",
        "probable_root_cause": (
            "La session utilisateur a expiré prématurément. "
            "Causes : timeout configuré trop court, inactivité prolongée, problème JWT."
        ),
        "diagnostic_actions": [
            "Vérifier la durée de session configurée dans BRASIL (security config)",
            "Contrôler si le problème est reproductible pour tous les utilisateurs",
            "Vérifier les logs d'accès pour le pattern d'expiration",
            "Contrôler la synchronisation horaire entre les serveurs (NTP)",
        ],
        "resolution_actions": [
            "Faire se reconnecter l'utilisateur immédiatement",
            "Si timeout trop court : ajuster la configuration de session BRASIL",
            "Si problème NTP : synchroniser les horloges serveur",
        ],
        "severity": "low",
    },

    "ProvisioningTimeoutException": {
        "application": "BRASIL",
        "component": "provisioning_engine",
        "related_systems": ["SEBA", "ORCHESTRA"],
        "incident_type": "provisioning_failure",
        "probable_root_cause": (
            "La commande de provisioning n'a pas reçu de confirmation dans le délai imparti. "
            "SEBA ou ORCHESTRA n'a pas répondu à temps."
        ),
        "diagnostic_actions": [
            "Vérifier l'état de la commande dans SEBA",
            "Contrôler les logs ORCHESTRA pour la commande concernée",
            "Vérifier si SEBA traite normalement les autres commandes",
            "Consulter la file d'attente SEBA pour détecter un blocage",
        ],
        "resolution_actions": [
            "Annuler la commande en timeout et la re-jouer",
            "Si SEBA bloqué : redémarrer le service SEBA après analyse",
            "Si ORCHESTRA bloqué : analyser la file de traitement",
            "Augmenter le timeout de provisioning si récurrent (config BRASIL)",
        ],
        "severity": "high",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Exception pattern detection regexes
# ─────────────────────────────────────────────────────────────────────────────

EXCEPTION_PATTERNS = [
    # Java/Spring style: com.brasil.exception.DslamClosedForProductionException
    r"\b([A-Z][a-zA-Z0-9]*Exception)\b",
    # Python style: brasil.errors.UnknownMRTIdException
    r"([A-Z][a-zA-Z0-9]*Error)\b",
]

# Template variables to normalize (replace with placeholders)
TEMPLATE_VARIABLES = [
    # DSLAM IDs: DSCAH114, NBLIL701
    (r"\b([A-Z]{3,5}[A-Z0-9]{2,4}\d{2,6})\b", "<EQUIPMENT_ID>"),
    # IP addresses
    (r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "<IP_ADDRESS>"),
    # UUIDs
    (r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", "<UUID>"),
    # Numeric IDs (long)
    (r"\b\d{6,}\b", "<NUMERIC_ID>"),
    # Timestamps in messages
    (r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}", "<TIMESTAMP>"),
    # Error codes embedded in messages
    (r"\bERREUR?\s+\d{3,5}\b", "<ERROR_CODE>"),
    # File paths
    (r"/[\w./\-_]+\.\w{2,4}", "<FILE_PATH>"),
    # Port numbers
    (r"\bport\s+\d{2,5}\b", "<PORT>"),
]

# System name detection
SYSTEM_NAMES = ["BRASIL", "SEBA", "ARTEMIS", "IPON", "ADELIA", "SCA", "ORCHESTRA"]

# Component detection keywords mapped to component names
COMPONENT_KEYWORDS: Dict[str, str] = {
    "provisioning": "provisioning_engine",
    "broche":       "provisioning_engine",
    "dslam":        "provisioning_engine",
    "commande":     "command_processor",
    "command":      "command_processor",
    "connector":    "integration_layer",
    "connecteur":   "integration_layer",
    "interface":    "integration_layer",
    "session":      "access_management",
    "authentif":    "access_management",
    "login":        "access_management",
    "mrt":          "routing_engine",
    "routing":      "routing_engine",
    "resource":     "resource_manager",
    "ressource":    "resource_manager",
    "scheduler":    "scheduler",
    "rdv":          "scheduler",
    "rendez-vous":  "scheduler",
    "oracle":       "database",
    "sql":          "database",
    "ora-":         "database",
}


# ─────────────────────────────────────────────────────────────────────────────
# Core functions
# ─────────────────────────────────────────────────────────────────────────────

def extract_exception_name(text: str) -> Optional[str]:
    """Extract the exception class name from a log message or stack trace."""
    for pattern in EXCEPTION_PATTERNS:
        matches = re.findall(pattern, text)
        # Prefer known catalog exceptions
        for m in matches:
            if m in EXCEPTION_CATALOG:
                return m
        # Otherwise return first match
        if matches:
            return matches[0]
    return None


def normalize_to_template(message: str) -> str:
    """
    Normalize a log message to a reusable template by replacing variable parts.
    Example:
      "Le Dslam DSCAH114 est fermé" → "Le Dslam <EQUIPMENT_ID> est fermé"
    """
    template = message
    for pattern, placeholder in TEMPLATE_VARIABLES:
        template = re.sub(pattern, placeholder, template, flags=re.IGNORECASE)
    # Remove extra whitespace
    template = re.sub(r"\s+", " ", template).strip()
    return template


def detect_component(text: str) -> str:
    """Detect the BRASIL component involved based on message keywords."""
    text_lower = text.lower()
    for keyword, component in COMPONENT_KEYWORDS.items():
        if keyword in text_lower:
            return component
    return "core"


def detect_related_systems(text: str) -> List[str]:
    """Detect related systems mentioned in a log message."""
    text_upper = text.upper()
    return [s for s in SYSTEM_NAMES if s in text_upper]


def compute_trust_score(
    frequency: int,
    is_in_catalog: bool,
    related_fr_count: int = 0,
    days_since_last: int = 30,
) -> float:
    """
    Compute a trust score for a log-derived knowledge record.

    Formula:
      T = 0.35 * S_source + 0.25 * S_freq + 0.30 * S_valid + 0.10 * S_recency

    Args:
        frequency: Number of occurrences of this pattern
        is_in_catalog: Whether the exception is in the exception catalog
        related_fr_count: Number of FR documents referencing this pattern
        days_since_last: Days since the last occurrence
    """
    # Source score
    s_source = 0.78 if is_in_catalog else 0.45

    # Frequency score (log-normalized, max at 200 occurrences)
    max_freq = 200
    s_freq = min(math.log1p(frequency) / math.log1p(max_freq), 1.0)

    # Validation score
    s_valid = 0.0
    if is_in_catalog:
        s_valid += 0.70
    if related_fr_count > 0:
        s_valid += min(related_fr_count * 0.15, 0.30)
    s_valid = min(s_valid, 1.0)

    # Recency score (linear decay over 365 days)
    s_recency = max(0.0, 1.0 - (days_since_last / 365))

    score = (
        0.35 * s_source
        + 0.25 * s_freq
        + 0.30 * s_valid
        + 0.10 * s_recency
    )
    return round(min(score, 1.0), 4)


def build_knowledge_record(
    pattern_group: Dict[str, Any],
    exception_name: Optional[str],
) -> Dict[str, Any]:
    """
    Build a LogKnowledgeRecord from a grouped pattern and optional catalog entry.

    Returns a structured dict ready for RAG indexing.
    """
    template    = pattern_group["template"]
    messages    = pattern_group["messages"]
    frequency   = pattern_group["frequency"]
    first_seen  = pattern_group.get("first_seen")
    last_seen   = pattern_group.get("last_seen")
    application = pattern_group.get("application", "BRASIL")
    raw_systems = pattern_group.get("systems", [])

    # Determine days since last occurrence (approx)
    days_since_last = 30
    if last_seen:
        try:
            last_dt = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
            delta = datetime.now().replace(tzinfo=last_dt.tzinfo) - last_dt
            days_since_last = max(0, delta.days)
        except Exception:
            pass

    # Pull from catalog if available
    catalog = EXCEPTION_CATALOG.get(exception_name, {}) if exception_name else {}
    is_in_catalog = bool(catalog)

    component       = catalog.get("component") or detect_component(" ".join(messages))
    related_systems = catalog.get("related_systems") or list(set(raw_systems))
    incident_type   = catalog.get("incident_type", "unknown")
    probable_cause  = catalog.get("probable_root_cause", "")
    diag_actions    = catalog.get("diagnostic_actions", [])
    resol_actions   = catalog.get("resolution_actions", [])

    # Fallback: infer from messages if catalog is missing
    if not probable_cause:
        probable_cause = _infer_cause_from_template(template, exception_name)
    if not diag_actions:
        diag_actions = _generic_diagnostic_actions(component, application)
    if not resol_actions:
        resol_actions = _generic_resolution_actions(component, incident_type)

    trust = compute_trust_score(
        frequency=frequency,
        is_in_catalog=is_in_catalog,
        days_since_last=days_since_last,
    )

    record_id = "LOG-" + hashlib.md5(
        (application + template).encode("utf-8")
    ).hexdigest()[:12].upper()

    return {
        "record_id": record_id,
        "error_pattern": template,
        "exception": exception_name or "",
        "application": application,
        "component": component,
        "related_systems": related_systems,
        "incident_type": incident_type,
        "severity": catalog.get("severity", "medium"),
        "probable_root_cause": probable_cause,
        "diagnostic_actions": diag_actions,
        "resolution_actions": resol_actions,
        "trust_score": trust,
        "frequency": frequency,
        "first_seen": first_seen,
        "last_seen": last_seen,
        "messages_sample": messages[:3],
        "source_type": "log_derived",
        "catalog_validated": is_in_catalog,
        "created_at": datetime.utcnow().isoformat(),
    }


def _infer_cause_from_template(template: str, exception: Optional[str]) -> str:
    """Infer a generic probable cause when the exception is not in catalog."""
    template_lower = template.lower()
    if "fermé" in template_lower or "closed" in template_lower:
        return "Équipement ou service fermé/indisponible pour la production"
    if "inconnu" in template_lower or "unknown" in template_lower or "introuvable" in template_lower:
        return "Identifiant ou ressource introuvable dans le référentiel"
    if "timeout" in template_lower or "délai" in template_lower:
        return "Dépassement du délai d'attente — service cible trop lent ou indisponible"
    if "connexion" in template_lower or "connection" in template_lower:
        return "Échec de connexion vers un service ou équipement"
    if "permission" in template_lower or "accès" in template_lower or "unauthorized" in template_lower:
        return "Droits insuffisants ou session expirée"
    if exception:
        # Clean exception name into readable text
        parts = re.findall("[A-Z][a-z]+", exception.replace("Exception", ""))
        if parts:
            return f"Erreur de type '{' '.join(parts)}' détectée dans les logs applicatifs"
    return "Erreur applicative détectée — analyse des logs nécessaire"


def _generic_diagnostic_actions(component: str, application: str) -> List[str]:
    """Fallback diagnostic actions based on component."""
    base = [
        f"Analyser les logs {application} sur la période d'erreur",
        "Identifier le message d'erreur exact et le timestamp",
        "Vérifier si le problème est reproductible",
    ]
    if component == "integration_layer":
        base.append("Tester la connectivité vers les systèmes tiers concernés")
    elif component == "provisioning_engine":
        base.append("Vérifier le statut de l'équipement réseau cible")
    elif component == "database":
        base.append("Vérifier l'état de la base de données et les connexions actives")
    return base


def _generic_resolution_actions(component: str, incident_type: str) -> List[str]:
    """Fallback resolution actions based on incident type."""
    base = ["Documenter le problème et les étapes de résolution"]
    if incident_type == "provisioning_failure":
        base = [
            "Vérifier l'état de l'équipement réseau cible",
            "Re-jouer la commande après correction",
            "Escalader à l'équipe réseau si nécessaire",
        ]
    elif incident_type == "system_integration_error":
        base = [
            "Vérifier la disponibilité du système tiers",
            "Redémarrer le connecteur après rétablissement",
            "Re-jouer les commandes en attente",
        ]
    elif incident_type == "data_inconsistency":
        base = [
            "Corriger les données incohérentes dans le référentiel",
            "Forcer une synchronisation entre les systèmes",
            "Re-jouer la commande après correction",
        ]
    return base


# ─────────────────────────────────────────────────────────────────────────────
# Template mining (Drain3-style grouping)
# Groups log messages by normalized template + exception
# ─────────────────────────────────────────────────────────────────────────────

def mine_templates(events: List[Dict]) -> List[Dict[str, Any]]:
    """
    Group log events by normalized template.
    Returns a list of pattern groups, each with frequency and metadata.
    """
    groups: Dict[str, Dict] = {}

    for event in events:
        message = event.get("message", "") or ""
        if not message:
            continue

        # Normalize to template
        template = normalize_to_template(message)
        exception = extract_exception_name(message)

        # Group key: template + exception (if present)
        key = f"{exception}::{template}" if exception else template

        if key not in groups:
            groups[key] = {
                "template": template,
                "exception": exception,
                "messages": [],
                "frequency": 0,
                "application": event.get("application", "BRASIL"),
                "systems": [],
                "first_seen": event.get("timestamp"),
                "last_seen": event.get("timestamp"),
                "error_codes": [],
                "services": set(),
            }

        g = groups[key]
        g["frequency"] += 1

        # Accumulate samples (max 5)
        if len(g["messages"]) < 5:
            g["messages"].append(message[:300])

        # Track related systems
        for sys in detect_related_systems(message):
            if sys not in g["systems"]:
                g["systems"].append(sys)

        # Track error codes
        for code in event.get("matched_error_codes", []):
            if code not in g["error_codes"]:
                g["error_codes"].append(code)

        # Track services
        svc = event.get("service")
        if svc:
            g["services"].add(svc)

        # Update timestamps
        ts = event.get("timestamp")
        if ts:
            if not g["last_seen"] or ts > g["last_seen"]:
                g["last_seen"] = ts

    # Convert sets to lists
    result = []
    for g in groups.values():
        g["services"] = list(g["services"])
        result.append(g)

    # Sort by frequency descending
    result.sort(key=lambda x: x["frequency"], reverse=True)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Catalog injection — ensure ALL catalog exceptions produce records
# even if not seen in current log batch
# ─────────────────────────────────────────────────────────────────────────────

def inject_catalog_records(
    existing_records: List[Dict],
    min_trust: float = 0.60,
) -> List[Dict]:
    """
    For exceptions in the catalog that were not found in log events,
    generate synthetic records with freq=0 and catalog trust.
    These ensure the chatbot can answer even if logs are not available.
    """
    seen_exceptions = {r["exception"] for r in existing_records if r.get("exception")}
    injected = []

    for exc_name, catalog in EXCEPTION_CATALOG.items():
        if exc_name in seen_exceptions:
            continue

        # Build a synthetic pattern group
        synthetic_group = {
            "template": f"<CATALOG> {exc_name} — aucun log disponible",
            "messages": [],
            "frequency": 0,
            "application": catalog["application"],
            "systems": catalog.get("related_systems", []),
            "first_seen": None,
            "last_seen": None,
        }

        record = build_knowledge_record(synthetic_group, exc_name)
        record["source_type"] = "catalog_only"
        # Catalog-only records get a fixed moderate trust
        record["trust_score"] = 0.65
        injected.append(record)

    return injected


# ─────────────────────────────────────────────────────────────────────────────
# Main pipeline
# ─────────────────────────────────────────────────────────────────────────────

def run(min_frequency: int = MIN_FREQUENCY, dry_run: bool = False) -> bool:
    """
    Main entry point for log knowledge extraction.
    """
    if not INPUT_FILE.exists():
        print(f"  ⚠️  log_events.json introuvable ({INPUT_FILE})")
        print("     Lancer d'abord: python data_pipeline/log_ingester.py --log-file <votre_log>")
        print("     Génération des enregistrements catalog uniquement...")
        events = []
    else:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        events = data.get("events", [])
        print(f"  📂 {len(events)} événements de logs chargés")

    # Step 1: Mine templates from log events
    print("  🔬 Analyse des templates d'erreurs...")
    template_groups = mine_templates(events)
    print(f"     {len(template_groups)} groupes de templates découverts")

    # Step 2: Build knowledge records for groups above min frequency
    records = []
    skipped = 0
    for group in template_groups:
        if group["frequency"] < min_frequency:
            skipped += 1
            continue
        record = build_knowledge_record(group, group.get("exception"))
        records.append(record)

    print(f"  ✅ {len(records)} enregistrements de connaissance générés")
    print(f"     (ignorés: {skipped} groupes < fréquence minimale {min_frequency})")

    # Step 3: Inject catalog records for known exceptions not in logs
    catalog_records = inject_catalog_records(records)
    print(f"  📚 {len(catalog_records)} enregistrements catalog injectés (exceptions connues sans logs)")
    all_records = records + catalog_records

    # Step 4: Trust distribution summary
    high   = sum(1 for r in all_records if r["trust_score"] >= 0.75)
    medium = sum(1 for r in all_records if 0.50 <= r["trust_score"] < 0.75)
    low    = sum(1 for r in all_records if r["trust_score"] < 0.50)
    print(f"\n  📊 Trust distribution:")
    print(f"     Haut (≥0.75): {high} | Moyen (0.50-0.75): {medium} | Faible (<0.50): {low}")

    # Step 5: Top patterns
    if all_records:
        print(f"\n  🏆 Top exceptions:")
        for r in sorted(all_records, key=lambda x: x["trust_score"], reverse=True)[:5]:
            print(
                f"     [{r['exception'] or 'N/A'}] trust={r['trust_score']:.2f} "
                f"freq={r['frequency']} — {r['component']}"
            )

    if dry_run:
        print("  🔍 Mode DRY-RUN — pas d'écriture")
        return True

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "generated_at": datetime.utcnow().isoformat(),
        "total_records": len(all_records),
        "from_logs": len(records),
        "from_catalog": len(catalog_records),
        "min_frequency_used": min_frequency,
        "exception_catalog_size": len(EXCEPTION_CATALOG),
        "records": all_records,
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n  💾 Sauvegardé: {OUTPUT_FILE}")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Log Knowledge Extractor — Transform BRASIL logs into structured knowledge records"
    )
    parser.add_argument(
        "--min-freq", type=int, default=MIN_FREQUENCY,
        help=f"Fréquence minimale pour créer un enregistrement (défaut: {MIN_FREQUENCY})"
    )
    parser.add_argument("--dry-run", action="store_true", help="Ne pas écrire les fichiers de sortie")
    args = parser.parse_args()

    success = run(min_frequency=args.min_freq, dry_run=args.dry_run)
    sys.exit(0 if success else 1)
