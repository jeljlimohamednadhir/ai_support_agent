"""
Diagnostic Engine — N3 Troubleshooting Reasoning Core

This module implements the full diagnostic reasoning chain:
  User question
    ↓ Intent + entity extraction (from existing NLP enricher)
    ↓ Ticket pattern matching   (from Qdrant clusters)
    ↓ Log pattern matching      (from Qdrant log_patterns)
    ↓ Procedure retrieval       (from Qdrant procedures)
    ↓ Trust-gated fusion        (composite score)
    ↓ Structured diagnostic result

The DiagnosticEngine integrates with the IntelligenceOrchestrator and
enriches its output before LLM generation to:
  1. Identify the incident_type with high confidence
  2. Match known exception / error code patterns
  3. Provide numbered diagnostic steps grounded in real procedures
  4. Cite sources (KB-*, PROC-*, LOG-*) with trust scores
  5. Block hallucination by gating low-trust knowledge

Usage (from orchestrator or chatbot service):
    from app.services.diagnostic.diagnostic_engine import diagnostic_engine

    result = await diagnostic_engine.diagnose(
        query="commande bloquée erreur 1300 dans BRASIL",
        app_id="BRASIL",
        db=db,
    )
    # result.procedure    → matched N3 procedure
    # result.root_causes  → probable root causes
    # result.steps        → numbered diagnostic steps
    # result.trust_score  → composite confidence
    # result.context_text → formatted text for LLM prompt injection
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

from app.core.logging import get_logger
from app.services.nlp.enricher import ticket_enricher, StructuredTicket
from app.services.nlp.taxonomy import find_incident_type, INCIDENT_TAXONOMY
from app.services.knowledge.manager import get_vector_service

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Trust thresholds
# ─────────────────────────────────────────────────────────────────────────────

TRUST_HIGH       = 0.75   # Present as definitive procedure
TRUST_MEDIUM     = 0.50   # Present with "à valider"
TRUST_LOW        = 0.35   # Present as "piste probable"
TRUST_MINIMUM    = 0.35   # Below this: refuse and escalate


# ─────────────────────────────────────────────────────────────────────────────
# Data models
# ─────────────────────────────────────────────────────────────────────────────

class DiagnosticConfidence(str, Enum):
    HIGH         = "high"         # trust ≥ 0.75
    MEDIUM       = "medium"       # trust ≥ 0.50
    LOW          = "low"          # trust ≥ 0.35
    INSUFFICIENT = "insufficient" # trust < 0.35


@dataclass
class DiagnosticStep:
    step: int
    action: str
    tool: str = ""
    expected_output: str = ""

    def to_text(self) -> str:
        lines = [f"{self.step}. {self.action}"]
        if self.tool:
            lines.append(f"   Outil : {self.tool}")
        if self.expected_output:
            lines.append(f"   Attendu : {self.expected_output}")
        return "\n".join(lines)


@dataclass
class DiagnosticResult:
    """Full structured diagnostic output from the engine."""
    query: str
    app_id: str
    incident_type: str
    confidence: DiagnosticConfidence
    trust_score: float

    # Matched knowledge
    procedure_id: Optional[str]        = None
    procedure_title: Optional[str]     = None
    applications_involved: List[str]   = field(default_factory=list)
    symptoms: List[str]                = field(default_factory=list)
    diagnostic_steps: List[DiagnosticStep] = field(default_factory=list)
    root_causes: List[str]             = field(default_factory=list)
    resolution_steps: List[str]        = field(default_factory=list)
    exceptions_matched: List[str]      = field(default_factory=list)
    error_codes_matched: List[str]     = field(default_factory=list)
    escalation_path: str               = ""

    # Source citations
    sources: List[Dict[str, Any]]      = field(default_factory=list)

    # Formatted context for LLM
    context_text: str                  = ""
    llm_instruction: str               = ""

    # Flags
    needs_clarification: bool          = False
    clarification_question: Optional[str] = None

    def is_usable(self) -> bool:
        return self.trust_score >= TRUST_MINIMUM


# ─────────────────────────────────────────────────────────────────────────────
# Exception keyword catalog (fast in-memory lookup without Qdrant)
# ─────────────────────────────────────────────────────────────────────────────

# Maps keywords/error patterns to known exception classes
EXCEPTION_SIGNAL_MAP: Dict[str, str] = {
    "dslam fermé":               "DslamClosedForProductionException",
    "closed for production":     "DslamClosedForProductionException",
    "ferme production":          "DslamClosedForProductionException",
    "dscah":                     "DslamClosedForProductionException",
    "mrt":                       "UnknownMRTIdException",
    "mrt inconnu":               "UnknownMRTIdException",
    "unknown mrt":               "UnknownMRTIdException",
    "ressources réseau":         "AvailableNetworkResourcesDisallowProductionException",
    "network resources":         "AvailableNetworkResourcesDisallowProductionException",
    "ressources disallow":       "AvailableNetworkResourcesDisallowProductionException",
    "dslam inaccessible":        "DslamUnreachableException",
    "dslam non joignable":       "DslamUnreachableException",
    "dslam unreachable":         "DslamUnreachableException",
    "erreur 1300":               "BusinessRuleViolationException",
    "error 1300":                "BusinessRuleViolationException",
    "1300":                      "BusinessRuleViolationException",
    "règle métier":              "BusinessRuleViolationException",
    "validation":                "CommandValidationException",
    "champ manquant":            "CommandValidationException",
    "prérequis":                 "CommandValidationException",
    "connecteur":                "ConnectorUnavailableException",
    "connector unavailable":     "ConnectorUnavailableException",
    "système tiers indisponible":"ConnectorUnavailableException",
    "timeout":                   "IntegrationTimeoutException",
    "délai dépassé":             "IntegrationTimeoutException",
    "session expirée":           "SessionExpiredException",
    "session expired":           "SessionExpiredException",
    "provisioning timeout":      "ProvisioningTimeoutException",
    "commande en attente":       "ProvisioningTimeoutException",
}

# Maps error code strings to incident types
ERROR_CODE_TYPE_MAP: Dict[str, str] = {
    "1300":  "command_failure",
    "B4002": "command_failure",
    "4002":  "command_failure",
    "1002":  "data_inconsistency",
    "42C":   "provisioning_failure",
    "9903":  "system_integration_error",
    "300":   "command_failure",
    "327":   "provisioning_failure",
    "1583":  "data_inconsistency",
}


# ─────────────────────────────────────────────────────────────────────────────
# Inline procedure knowledge (fast fallback, no Qdrant needed)
# Mirrors the exception catalog from log_knowledge_extractor.py
# ─────────────────────────────────────────────────────────────────────────────

INLINE_PROCEDURES: Dict[str, Dict[str, Any]] = {
    "DslamClosedForProductionException": {
        "procedure_id": "PROC-BRASIL-PROV-0001",
        "title": "DSLAM fermé à la production — blocage provisioning",
        "incident_type": "provisioning_failure",
        "applications_involved": ["BRASIL", "SEBA", "ORCHESTRA"],
        "symptoms": [
            "Commande BRASIL en statut PENDING ou FAILED",
            "Log contient DslamClosedForProductionException",
            "ORCHESTRA ne retourne pas de confirmation d'exécution",
        ],
        "diagnostic_steps": [
            {"step": 1, "action": "Vérifier les logs BRASIL pour DslamClosedForProductionException", "tool": "BRASIL Admin Console → Logs → Filtrer par commande_id", "expected_output": "Exception visible avec DSLAM_ID"},
            {"step": 2, "action": "Contrôler le statut du DSLAM dans ORCHESTRA", "tool": "ORCHESTRA → Référentiel NE → Recherche par DSLAM_ID", "expected_output": "Statut = CLOSED ou MAINTENANCE"},
            {"step": 3, "action": "Vérifier la cohérence BRASIL ↔ SEBA sur l'état du NE", "tool": "API SEBA GET /ne/{dslam_id}/status", "expected_output": "Confirmer désynchronisation éventuelle"},
        ],
        "root_causes": [
            "DSLAM physiquement fermé pour maintenance non signalée",
            "Désynchronisation entre référentiel BRASIL et ORCHESTRA",
            "Migration réseau non finalisée dans le référentiel",
        ],
        "resolution_steps": [
            "Contacter l'équipe réseau pour confirmation statut DSLAM",
            "Soumettre demande de réouverture via ticket JIRA composant ORCHESTRA-NE",
            "Après réouverture confirmée : re-jouer la commande BRASIL",
            "Vérifier synchronisation SEBA après re-jeu",
        ],
        "escalation_path": "N3 BRASIL → Équipe Réseau → ORCHESTRA Admin",
        "trust_score": 0.84,
        "source_types": ["catalog_validated"],
    },
    "UnknownMRTIdException": {
        "procedure_id": "PROC-BRASIL-DATA-0001",
        "title": "MRT ID inconnu — incohérence référentiel",
        "incident_type": "data_inconsistency",
        "applications_involved": ["BRASIL", "SEBA"],
        "symptoms": [
            "Commande refusée avec UnknownMRTIdException",
            "Identifiant MRT non trouvé dans le référentiel BRASIL",
        ],
        "diagnostic_steps": [
            {"step": 1, "action": "Rechercher l'identifiant MRT dans BRASIL Admin → Référentiel → MRT", "tool": "BRASIL Admin Console → Référentiel MRT", "expected_output": "MRT absent ou en statut EXPIRÉ"},
            {"step": 2, "action": "Vérifier si une migration de données a eu lieu récemment", "tool": "BRASIL Admin → Journal de migration", "expected_output": "Migration récente visible"},
            {"step": 3, "action": "Contrôler la synchronisation BRASIL ↔ SEBA sur ce MRT_ID", "tool": "API SEBA GET /mrt/{mrt_id}", "expected_output": "Confirmer présence ou absence côté SEBA"},
        ],
        "root_causes": [
            "Identifiant MRT expiré suite à migration",
            "MRT créé localement sans propagation vers SEBA",
            "Données incohérentes entre BRASIL et SEBA",
        ],
        "resolution_steps": [
            "Si MRT inexistant : recréer via procédure admin BRASIL",
            "Si MRT expiré : réactiver ou générer un nouvel identifiant",
            "Forcer la synchronisation BRASIL → SEBA après correction",
            "Re-jouer la commande avec le MRT_ID corrigé",
        ],
        "escalation_path": "N3 BRASIL → Équipe Data → DBA",
        "trust_score": 0.78,
        "source_types": ["catalog_validated"],
    },
    "BusinessRuleViolationException": {
        "procedure_id": "PROC-BRASIL-CMD-0001",
        "title": "Erreur 1300 — violation règle métier",
        "incident_type": "command_failure",
        "applications_involved": ["BRASIL", "ADELIA"],
        "symptoms": [
            "Erreur 1300 dans BRASIL",
            "BusinessRuleViolationException dans les logs",
            "Commande refusée après validation",
        ],
        "diagnostic_steps": [
            {"step": 1, "action": "Identifier la règle violée dans les logs BRASIL (champ violated_rule)", "tool": "BRASIL Admin Console → Logs → Filtrer sur BusinessRuleViolationException", "expected_output": "Nom de la règle violée et champ concerné"},
            {"step": 2, "action": "Vérifier la complétude du dossier client dans BRASIL", "tool": "BRASIL → Dossier Client → Onglet Données", "expected_output": "Champ manquant ou invalide identifié"},
            {"step": 3, "action": "Contrôler les données ADELIA associées au client", "tool": "ADELIA → Consultation dossier", "expected_output": "Incohérence ou champ manquant côté ADELIA"},
        ],
        "root_causes": [
            "Dossier client incomplet — champ obligatoire manquant",
            "Données ADELIA non synchronisées avec BRASIL",
            "Règle métier plus stricte depuis une mise à jour récente",
        ],
        "resolution_steps": [
            "Compléter les champs manquants dans le dossier client",
            "Si champ ADELIA manquant : déclencher synchronisation ADELIA → BRASIL",
            "Re-soumettre la commande après correction",
            "Si règle incohérente : ouvrir un ticket JIRA BRASIL-RULES",
        ],
        "escalation_path": "N3 BRASIL → Responsable Métier",
        "trust_score": 0.76,
        "source_types": ["catalog_validated"],
    },
    "ConnectorUnavailableException": {
        "procedure_id": "PROC-BRASIL-INT-0001",
        "title": "Connecteur système tiers indisponible",
        "incident_type": "system_integration_error",
        "applications_involved": ["BRASIL", "SEBA", "IPON", "ARTEMIS"],
        "symptoms": [
            "ConnectorUnavailableException dans les logs BRASIL",
            "Timeout ou connexion refusée vers un système tiers",
            "Commandes BRASIL bloquées sur envoi",
        ],
        "diagnostic_steps": [
            {"step": 1, "action": "Identifier le système tiers concerné dans les logs (champ upstream_system)", "tool": "BRASIL Admin Console → Logs → Filtrer sur ConnectorUnavailableException", "expected_output": "Nom du système tiers et endpoint"},
            {"step": 2, "action": "Tester la connectivité réseau vers l'endpoint du système tiers", "tool": "curl / telnet depuis serveur BRASIL", "expected_output": "Timeout ou connexion refusée"},
            {"step": 3, "action": "Vérifier le statut du service tiers via supervision", "tool": "Supervision Orange / Nagios / Zabbix", "expected_output": "Service DOWN ou dégradé"},
        ],
        "root_causes": [
            "Système tiers indisponible (maintenance ou panne)",
            "Problème réseau sur flux inter-applicatif",
            "Certificat SSL expiré côté connecteur",
            "Mauvaise configuration endpoint dans BRASIL",
        ],
        "resolution_steps": [
            "Si système tiers down : attendre rétablissement ou déclencher une astreinte",
            "Si SSL expiré : renouveler le certificat et redémarrer le connecteur",
            "Si timeout réseau : vérifier règles firewall et proxies",
            "Redémarrer le connecteur BRASIL après résolution",
            "Re-jouer les commandes en attente après rétablissement",
        ],
        "escalation_path": "N3 BRASIL → Équipe Intégration → Admin système tiers",
        "trust_score": 0.80,
        "source_types": ["catalog_validated"],
    },
    "DslamUnreachableException": {
        "procedure_id": "PROC-BRASIL-NET-0001",
        "title": "DSLAM non joignable — panne équipement réseau",
        "incident_type": "network_equipment_issue",
        "applications_involved": ["BRASIL", "ORCHESTRA", "SEBA"],
        "symptoms": [
            "DslamUnreachableException dans les logs",
            "Commandes de provisioning bloquées sur ce DSLAM",
            "Supervision ORCHESTRA : NE en état DOWN",
        ],
        "diagnostic_steps": [
            {"step": 1, "action": "Vérifier le statut du DSLAM dans ORCHESTRA → Supervision NE", "tool": "ORCHESTRA → Supervision → Recherche DSLAM_ID", "expected_output": "Statut DOWN ou UNREACHABLE"},
            {"step": 2, "action": "Tester la connectivité réseau vers le DSLAM depuis le serveur BRASIL", "tool": "ping / traceroute depuis serveur BRASIL", "expected_output": "Perte de paquets ou inaccessible"},
            {"step": 3, "action": "Vérifier les alertes NMS/NetManager sur ce DSLAM", "tool": "NetManager → Alertes → Filtrer par DSLAM_ID", "expected_output": "Alerte active confirmée"},
        ],
        "root_causes": [
            "Panne matérielle équipement réseau",
            "Problème réseau sur le flux de supervision",
            "DSLAM hors ligne suite à coupure électrique",
        ],
        "resolution_steps": [
            "Escalader immédiatement à l'équipe réseau si DSLAM down",
            "Ouvrir un ticket NOC avec le DSLAM_ID et le timestamp de détection",
            "Si intermittent : programmer surveillance et rejouer la commande plus tard",
            "Documenter l'indisponibilité pour le rapport d'incident",
        ],
        "escalation_path": "N3 BRASIL → Équipe Réseau → NOC",
        "trust_score": 0.82,
        "source_types": ["catalog_validated"],
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Diagnostic Engine
# ─────────────────────────────────────────────────────────────────────────────

class DiagnosticEngine:
    """
    N3 Diagnostic Engine — connects user question to structured procedure.

    Flow:
      1. Parse the query with NLP enricher (extract app, entities, error codes)
      2. Detect exception signals in the query
      3. Try Qdrant retrieval (procedure + log pattern collections)
      4. Fall back to inline catalog if Qdrant unavailable
      5. Fuse results into a DiagnosticResult
      6. Build formatted context text for LLM
    """

    def __init__(self):
        self._vector_service = None

    def _get_vector_service(self):
        if self._vector_service is None:
            try:
                self._vector_service = get_vector_service()
            except Exception:
                pass
        return self._vector_service

    # ─────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────

    async def diagnose(
        self,
        query: str,
        app_id: str = "BRASIL",
        db=None,
        logs: Optional[str] = None,
        stack_trace: Optional[str] = None,
        top_k: int = 3,
    ) -> DiagnosticResult:
        """
        Main diagnostic entry point.

        Args:
            query: User question or ticket description
            app_id: Application context (default BRASIL)
            db: SQLAlchemy session (optional)
            logs: Raw log text (optional)
            stack_trace: Stack trace text (optional)
            top_k: Number of knowledge records to retrieve

        Returns:
            DiagnosticResult with structured diagnostic + LLM context
        """
        # 1. NLP enrichment
        enriched: StructuredTicket = ticket_enricher.enrich(query)
        logger.debug(
            f"[DiagnosticEngine] intent={enriched.intent}, "
            f"app={enriched.application}, "
            f"codes={enriched.error_codes}"
        )

        # 2. Detect exceptions from query + logs
        combined_text = query
        if logs:
            combined_text += "\n" + logs
        if stack_trace:
            combined_text += "\n" + stack_trace

        detected_exceptions = self._detect_exceptions(combined_text)
        detected_codes      = list(enriched.error_codes or [])

        # Infer additional codes from enriched entities
        if hasattr(enriched, "entities") and enriched.entities:
            _ent_src = enriched.entities
            # entities may be a List[ExtractedEntity] or Dict[str, List]
            if isinstance(_ent_src, dict):
                _flat_ents = [ent for ent_list in _ent_src.values() for ent in ent_list]
            elif isinstance(_ent_src, list):
                _flat_ents = _ent_src
            else:
                _flat_ents = []
            for ent in _flat_ents:
                _val = getattr(ent, 'value', ent) if hasattr(ent, 'value') else str(ent)
                if re.match(r"^\d{3,5}$|^B\d{4}$|^ORA-", str(_val)):
                    if str(_val) not in detected_codes:
                        detected_codes.append(str(_val))

        # 3. Determine incident type
        incident_type = enriched.incident_type or ""
        if not incident_type and detected_codes:
            incident_type = ERROR_CODE_TYPE_MAP.get(detected_codes[0], "")
        if not incident_type and detected_exceptions:
            exc_entry = INLINE_PROCEDURES.get(detected_exceptions[0], {})
            incident_type = exc_entry.get("incident_type", "")
        if not incident_type:
            incident_type = find_incident_type(query) or "unknown"

        # 4. Retrieve procedures — try Qdrant first, then inline catalog
        procedure_data, sources = self._retrieve_procedure(
            query=query,
            detected_exceptions=detected_exceptions,
            detected_codes=detected_codes,
            incident_type=incident_type,
            app_id=app_id,
            top_k=top_k,
        )

        # 5. Compute composite trust
        trust = self._compute_trust(
            procedure_data=procedure_data,
            enriched=enriched,
            detected_exceptions=detected_exceptions,
        )

        # 6. Determine if clarification needed
        needs_clarification, clarification_q = self._check_clarification_needed(enriched, incident_type)

        # 7. Build DiagnosticResult
        result = self._build_result(
            query=query,
            app_id=app_id,
            incident_type=incident_type,
            procedure_data=procedure_data,
            enriched=enriched,
            detected_exceptions=detected_exceptions,
            detected_codes=detected_codes,
            sources=sources,
            trust=trust,
            needs_clarification=needs_clarification,
            clarification_q=clarification_q,
        )

        # 8. Build LLM context text
        result.context_text    = self._build_context_text(result)
        result.llm_instruction = self._build_llm_instruction(result)

        logger.info(
            f"[DiagnosticEngine] {app_id} | {incident_type} | "
            f"trust={trust:.2f} | proc={result.procedure_id or 'none'} | "
            f"exc={detected_exceptions[:1]}"
        )

        return result

    # ─────────────────────────────────────────────
    # Exception detection
    # ─────────────────────────────────────────────

    def _detect_exceptions(self, text: str) -> List[str]:
        """Detect known exception classes in the query/logs."""
        found = []
        text_lower = text.lower()

        # Direct exception name match
        for exc_name in INLINE_PROCEDURES:
            if exc_name.lower() in text_lower:
                found.append(exc_name)

        # Signal keyword match
        if not found:
            for signal, exc_name in EXCEPTION_SIGNAL_MAP.items():
                if signal in text_lower and exc_name not in found:
                    found.append(exc_name)

        # Regex fallback for generic exception names
        if not found:
            matches = re.findall(r"\b([A-Z][a-zA-Z0-9]*(?:Exception|Error))\b", text)
            for m in matches:
                if m not in found:
                    found.append(m)

        return found[:3]  # Max 3 exceptions

    # ─────────────────────────────────────────────
    # Procedure retrieval
    # ─────────────────────────────────────────────

    def _retrieve_procedure(
        self,
        query: str,
        detected_exceptions: List[str],
        detected_codes: List[str],
        incident_type: str,
        app_id: str,
        top_k: int,
    ) -> tuple[Optional[Dict], List[Dict]]:
        """
        Retrieve the best matching procedure.
        Priority: 1) Qdrant vector search, 2) inline catalog by exception,
                  3) inline catalog by incident type.
        """
        sources = []

        # Priority 1: Direct exception catalog lookup (most reliable)
        if detected_exceptions:
            for exc in detected_exceptions:
                if exc in INLINE_PROCEDURES:
                    proc = INLINE_PROCEDURES[exc]
                    sources.append({
                        "source_id": proc["procedure_id"],
                        "source_type": "inline_catalog",
                        "trust_score": proc["trust_score"],
                        "exception": exc,
                    })
                    return proc, sources

        # Priority 2: Qdrant vector search
        vs = self._get_vector_service()
        if vs and getattr(vs, "_available", False):
            try:
                qdrant_result = self._qdrant_search(
                    vs, query, app_id, incident_type, top_k
                )
                if qdrant_result:
                    proc, qdrant_sources = qdrant_result
                    sources.extend(qdrant_sources)
                    return proc, sources
            except Exception as e:
                logger.warning(f"[DiagnosticEngine] Qdrant search failed: {e}")

        # Priority 3: Inline catalog by incident type
        for exc, proc in INLINE_PROCEDURES.items():
            if proc.get("incident_type") == incident_type:
                sources.append({
                    "source_id": proc["procedure_id"],
                    "source_type": "inline_catalog",
                    "trust_score": proc["trust_score"],
                    "matched_by": "incident_type",
                })
                return proc, sources

        # Priority 4: Error code match
        for code in detected_codes:
            mapped_type = ERROR_CODE_TYPE_MAP.get(code, "")
            if mapped_type:
                for exc, proc in INLINE_PROCEDURES.items():
                    if proc.get("incident_type") == mapped_type:
                        sources.append({
                            "source_id": proc["procedure_id"],
                            "source_type": "inline_catalog",
                            "trust_score": proc["trust_score"] * 0.85,
                            "matched_by": f"error_code_{code}",
                        })
                        return proc, sources

        return None, []

    def _qdrant_search(
        self,
        vs,
        query: str,
        app_id: str,
        incident_type: str,
        top_k: int,
    ) -> Optional[tuple[Dict, List[Dict]]]:
        """Search Qdrant collections for matching procedures."""
        from qdrant_client.models import Filter, FieldCondition, MatchValue, Range

        try:
            query_vector = vs.embed_text(query)

            # Build filters
            must_filters = []
            if app_id:
                must_filters.append(
                    FieldCondition(key="application", match=MatchValue(value=app_id))
                )
            # Trust gate: only retrieve records with sufficient confidence
            must_filters.append(
                FieldCondition(key="trust_score", range=Range(gte=TRUST_MINIMUM))
            )

            # Try brasil_procedures collection first
            results = vs.client.search(
                collection_name="brasil_procedures",
                query_vector=query_vector,
                query_filter=Filter(must=must_filters) if must_filters else None,
                limit=top_k,
                with_payload=True,
            )

            if results:
                best = results[0]
                payload = best.payload or {}
                sources = [{
                    "source_id": payload.get("procedure_id", ""),
                    "source_type": "qdrant_procedure",
                    "trust_score": payload.get("trust_score", 0.5),
                    "similarity_score": best.score,
                }]
                return payload, sources

        except Exception as e:
            logger.debug(f"[DiagnosticEngine] brasil_procedures search: {e}")

        return None

    # ─────────────────────────────────────────────
    # Trust computation
    # ─────────────────────────────────────────────

    def _compute_trust(
        self,
        procedure_data: Optional[Dict],
        enriched: StructuredTicket,
        detected_exceptions: List[str],
    ) -> float:
        """Compute composite trust for a diagnostic result."""
        if procedure_data is None:
            return 0.0

        base = procedure_data.get("trust_score", 0.50)

        # Bonus: enricher detected a specific application (not just default BRASIL)
        app_bonus = 0.05 if (enriched.application and enriched.application != "BRASIL") else 0.0

        # Bonus: exception was directly detected in user query
        exc_bonus = 0.05 if detected_exceptions else 0.0

        # Penalty: no error codes and no exception → less certain
        code_penalty = -0.05 if not detected_exceptions and not (enriched.error_codes) else 0.0

        score = base + app_bonus + exc_bonus + code_penalty
        return round(min(max(score, 0.0), 1.0), 4)

    # ─────────────────────────────────────────────
    # Clarification check
    # ─────────────────────────────────────────────

    def _check_clarification_needed(
        self,
        enriched: StructuredTicket,
        incident_type: str,
    ) -> tuple[bool, Optional[str]]:
        """Check if we need clarification from the user before diagnosing."""
        # If intent confidence is very low and no specific entity detected
        intent_conf = getattr(enriched, "intent_confidence", 1.0) or 1.0

        if intent_conf < 0.40 and incident_type == "unknown":
            return True, (
                "Pouvez-vous préciser le type de problème rencontré ? "
                "(ex: commande bloquée, erreur de provisioning, accès refusé, DSLAM injoignable)"
            )

        if not getattr(enriched, "application", None) and incident_type == "unknown":
            return True, (
                "Sur quelle application ce problème se produit-il ? "
                "(BRASIL, SEBA, ARTEMIS, IPON, ADELIA, SCA, ORCHESTRA)"
            )

        return False, None

    # ─────────────────────────────────────────────
    # Result builder
    # ─────────────────────────────────────────────

    def _build_result(
        self,
        query: str,
        app_id: str,
        incident_type: str,
        procedure_data: Optional[Dict],
        enriched: StructuredTicket,
        detected_exceptions: List[str],
        detected_codes: List[str],
        sources: List[Dict],
        trust: float,
        needs_clarification: bool,
        clarification_q: Optional[str],
    ) -> DiagnosticResult:
        """Build the structured DiagnosticResult."""
        if trust >= TRUST_HIGH:
            confidence = DiagnosticConfidence.HIGH
        elif trust >= TRUST_MEDIUM:
            confidence = DiagnosticConfidence.MEDIUM
        elif trust >= TRUST_LOW:
            confidence = DiagnosticConfidence.LOW
        else:
            confidence = DiagnosticConfidence.INSUFFICIENT

        if procedure_data:
            raw_steps = procedure_data.get("diagnostic_steps", [])
            steps = [
                DiagnosticStep(
                    step=s.get("step", i + 1),
                    action=s.get("action", ""),
                    tool=s.get("tool", ""),
                    expected_output=s.get("expected_output", ""),
                )
                for i, s in enumerate(raw_steps)
            ]

            return DiagnosticResult(
                query=query,
                app_id=app_id,
                incident_type=incident_type,
                confidence=confidence,
                trust_score=trust,
                procedure_id=procedure_data.get("procedure_id"),
                procedure_title=procedure_data.get("title"),
                applications_involved=procedure_data.get("applications_involved", [app_id]),
                symptoms=procedure_data.get("symptoms", []),
                diagnostic_steps=steps,
                root_causes=procedure_data.get("root_causes", []),
                resolution_steps=procedure_data.get("resolution_steps", []),
                exceptions_matched=detected_exceptions,
                error_codes_matched=detected_codes,
                escalation_path=procedure_data.get("escalation_path", ""),
                sources=sources,
                needs_clarification=needs_clarification,
                clarification_question=clarification_q,
            )
        else:
            return DiagnosticResult(
                query=query,
                app_id=app_id,
                incident_type=incident_type,
                confidence=DiagnosticConfidence.INSUFFICIENT,
                trust_score=0.0,
                exceptions_matched=detected_exceptions,
                error_codes_matched=detected_codes,
                sources=[],
                needs_clarification=needs_clarification,
                clarification_question=clarification_q,
            )

    # ─────────────────────────────────────────────
    # LLM context formatters
    # ─────────────────────────────────────────────

    def _build_context_text(self, result: DiagnosticResult) -> str:
        """Build the context text block to inject into LLM prompt."""
        if not result.is_usable():
            return ""

        lines = []

        lines.append(f"=== DIAGNOSTIC N3 — {result.procedure_title or result.incident_type.upper()} ===")
        lines.append(f"Procédure : {result.procedure_id or 'N/A'} | Confiance : {int(result.trust_score * 100)}%")
        lines.append(f"Applications : {', '.join(result.applications_involved)}")
        lines.append("")

        if result.exceptions_matched:
            lines.append(f"Exceptions détectées : {', '.join(result.exceptions_matched)}")
        if result.error_codes_matched:
            lines.append(f"Codes erreur : {', '.join(result.error_codes_matched)}")
        lines.append("")

        if result.symptoms:
            lines.append("SYMPTÔMES :")
            for s in result.symptoms[:4]:
                lines.append(f"  • {s}")
            lines.append("")

        if result.root_causes:
            lines.append("CAUSES PROBABLES :")
            for i, c in enumerate(result.root_causes[:3], 1):
                lines.append(f"  {i}. {c}")
            lines.append("")

        if result.diagnostic_steps:
            lines.append("ÉTAPES DE DIAGNOSTIC :")
            for step in result.diagnostic_steps:
                lines.append(step.to_text())
            lines.append("")

        if result.resolution_steps:
            lines.append("ÉTAPES DE RÉSOLUTION :")
            for i, s in enumerate(result.resolution_steps[:5], 1):
                lines.append(f"  {i}. {s}")
            lines.append("")

        if result.escalation_path:
            lines.append(f"ESCALADE : {result.escalation_path}")

        if result.sources:
            src = result.sources[0]
            lines.append(
                f"\nSource : {src.get('source_id', 'KB')} "
                f"(confiance : {int(src.get('trust_score', result.trust_score) * 100)}%)"
            )

        return "\n".join(lines)

    def _build_llm_instruction(self, result: DiagnosticResult) -> str:
        """Build the LLM system instruction based on confidence level."""
        base = (
            "Tu es un assistant N3 pour le support applicatif BRASIL (Orange). "
            "Réponds en français. Sois précis et technique. "
        )

        if result.confidence == DiagnosticConfidence.INSUFFICIENT:
            return (
                base
                + "Tu n'as pas de procédure validée pour cette question. "
                + "Dis-le clairement et recommande une escalade N3. "
                + "NE PAS inventer de procédure ou d'étapes techniques."
            )

        if result.confidence == DiagnosticConfidence.HIGH:
            return (
                base
                + f"Utilise UNIQUEMENT les informations du contexte de diagnostic ci-dessus. "
                + f"Cite la procédure {result.procedure_id}. "
                + "Présente les étapes de manière structurée et numérotée."
            )

        if result.confidence == DiagnosticConfidence.MEDIUM:
            return (
                base
                + "Utilise le contexte de diagnostic comme base principale. "
                + "Indique que la procédure est 'à valider selon le contexte exact'. "
                + "NE PAS inventer d'étapes non présentes dans le contexte."
            )

        # LOW confidence
        return (
            base
            + "Présente les informations disponibles comme une 'piste probable, à confirmer'. "
            + "Recommande de compléter le diagnostic avec les logs exacts. "
            + "NE PAS affirmer avec certitude sans logs confirmés."
        )


# Singleton instance
diagnostic_engine = DiagnosticEngine()
