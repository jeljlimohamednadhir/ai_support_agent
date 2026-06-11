"""
semantic_intent_router.py
━━━━━━━━━━━━━━━━━━━━━━━━━
Semantic Intent Router V2 — Phase 2

Classifies incoming messages into operational semantic categories
that map to deterministic handler chains.

Supports:
  - French operational language
  - Abbreviated telecom language (DSLAM, VLAN, MRT, EPT, OLT, NRO...)
  - N3 slang and mixed business/technical phrasing
  - Multi-label classification (a query can belong to 1-3 categories)

25 Semantic Categories:
  1.  runtime_diagnostic
  2.  forensic_logs
  3.  forensic_timeline
  4.  workflow_navigation
  5.  operational_procedure
  6.  source_code_lookup
  7.  business_rule_explanation
  8.  runtime_state_analysis
  9.  schema_lookup
  10. sql_lookup
  11. exception_lookup
  12. dependency_analysis
  13. incident_history
  14. ihm_navigation
  15. cross_system_correlation
  16. validation_constraint
  17. rollback_analysis
  18. transaction_analysis
  19. service_dependency
  20. state_machine_analysis
  21. root_cause_explanation
  22. evidence_provenance
  23. function_trace
  24. log_source_identification
  25. workflow_stage_identification

Design:
  - Pure regex + weight scoring — no LLM required
  - Returns ranked list of (category, confidence)
  - Primary category = highest scoring
  - Multi-label when multiple categories score > threshold
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CATEGORY DEFINITIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Canonical category names
CAT_RUNTIME_DIAGNOSTIC         = "runtime_diagnostic"
CAT_FORENSIC_LOGS              = "forensic_logs"
CAT_FORENSIC_TIMELINE          = "forensic_timeline"
CAT_WORKFLOW_NAVIGATION        = "workflow_navigation"
CAT_OPERATIONAL_PROCEDURE      = "operational_procedure"
CAT_SOURCE_CODE_LOOKUP         = "source_code_lookup"
CAT_BUSINESS_RULE              = "business_rule_explanation"
CAT_RUNTIME_STATE              = "runtime_state_analysis"
CAT_SCHEMA_LOOKUP              = "schema_lookup"
CAT_SQL_LOOKUP                 = "sql_lookup"
CAT_EXCEPTION_LOOKUP           = "exception_lookup"
CAT_DEPENDENCY_ANALYSIS        = "dependency_analysis"
CAT_INCIDENT_HISTORY           = "incident_history"
CAT_IHM_NAVIGATION             = "ihm_navigation"
CAT_CROSS_SYSTEM               = "cross_system_correlation"
CAT_VALIDATION_CONSTRAINT      = "validation_constraint"
CAT_ROLLBACK_ANALYSIS          = "rollback_analysis"
CAT_TRANSACTION_ANALYSIS       = "transaction_analysis"
CAT_SERVICE_DEPENDENCY         = "service_dependency"
CAT_STATE_MACHINE              = "state_machine_analysis"
CAT_ROOT_CAUSE                 = "root_cause_explanation"
CAT_EVIDENCE_PROVENANCE        = "evidence_provenance"
CAT_FUNCTION_TRACE             = "function_trace"
CAT_LOG_SOURCE                 = "log_source_identification"
CAT_WORKFLOW_STAGE             = "workflow_stage_identification"

ALL_CATEGORIES = [
    CAT_RUNTIME_DIAGNOSTIC, CAT_FORENSIC_LOGS, CAT_FORENSIC_TIMELINE,
    CAT_WORKFLOW_NAVIGATION, CAT_OPERATIONAL_PROCEDURE, CAT_SOURCE_CODE_LOOKUP,
    CAT_BUSINESS_RULE, CAT_RUNTIME_STATE, CAT_SCHEMA_LOOKUP, CAT_SQL_LOOKUP,
    CAT_EXCEPTION_LOOKUP, CAT_DEPENDENCY_ANALYSIS, CAT_INCIDENT_HISTORY,
    CAT_IHM_NAVIGATION, CAT_CROSS_SYSTEM, CAT_VALIDATION_CONSTRAINT,
    CAT_ROLLBACK_ANALYSIS, CAT_TRANSACTION_ANALYSIS, CAT_SERVICE_DEPENDENCY,
    CAT_STATE_MACHINE, CAT_ROOT_CAUSE, CAT_EVIDENCE_PROVENANCE,
    CAT_FUNCTION_TRACE, CAT_LOG_SOURCE, CAT_WORKFLOW_STAGE,
]

# Maps semantic categories to the existing forensic intent strings
# (so the router can drive the existing handlers)
CATEGORY_TO_FORENSIC_INTENT: Dict[str, str] = {
    CAT_FORENSIC_LOGS:         "forensic_logs",
    CAT_FORENSIC_TIMELINE:     "forensic_timeline",
    CAT_RUNTIME_STATE:         "forensic_evidence",
    CAT_EXCEPTION_LOOKUP:      "forensic_exceptions",
    CAT_SOURCE_CODE_LOOKUP:    "find_code_function",
    CAT_FUNCTION_TRACE:        "find_code_function",
    CAT_VALIDATION_CONSTRAINT: "explain_code_constraint",
    CAT_ROLLBACK_ANALYSIS:     "forensic_rollback",
    CAT_TRANSACTION_ANALYSIS:  "forensic_transaction",
    CAT_DEPENDENCY_ANALYSIS:   "forensic_constraint_chain",
    CAT_LOG_SOURCE:            "forensic_logs",
    CAT_EVIDENCE_PROVENANCE:   "forensic_evidence",
    CAT_ROOT_CAUSE:            "forensic_root_cause",
    CAT_WORKFLOW_NAVIGATION:   "forensic_workflow",
    CAT_WORKFLOW_STAGE:        "forensic_workflow",
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SCORING RULES
# Each rule: (compiled_regex, category, weight)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_I = re.IGNORECASE

_RULES: List[Tuple[re.Pattern, str, float]] = [

    # ── runtime_diagnostic ──────────────────────────────────────────────
    (re.compile(r"\b(?:diagnosti(?:c|quer?)|probl[eè]me|erreur|incident|bloqu[eé]|impossible)\b", _I), CAT_RUNTIME_DIAGNOSTIC, 0.6),
    (re.compile(r"\b(?:suppression|cr[eé]ation|modification)\s+(?:impossible|[eé]chou[eé]|bloqu[eé]e?)\b", _I), CAT_RUNTIME_DIAGNOSTIC, 0.9),
    (re.compile(r"\b(?:pourquoi|why)\s+(?:le|la|les|l[''`])\s*\w+\s+(?:ne\s+fonctionne?\s+pas|[eé]chou[eé]|bloqu[eé])\b", _I), CAT_RUNTIME_DIAGNOSTIC, 0.8),

    # ── forensic_logs ───────────────────────────────────────────────────
    (re.compile(r"\b(?:logs?|journaux?|traces?|catalina|connectorCL|brasil_app)\b", _I), CAT_FORENSIC_LOGS, 0.8),
    (re.compile(r"\b(?:montrer?|affich(?:er?|e)|voir)\s+(?:les?\s+)?logs?\b", _I), CAT_FORENSIC_LOGS, 0.95),
    (re.compile(r"\b(?:lignes?\s+de\s+log|stack\s*trace|erreur\s+dans\s+les?\s+logs?)\b", _I), CAT_FORENSIC_LOGS, 0.85),
    (re.compile(r"\b(?:grep|tail|head)\b", _I), CAT_FORENSIC_LOGS, 0.7),

    # ── forensic_timeline ───────────────────────────────────────────────
    (re.compile(r"\b(?:timeline|chronologie|s[eé]quence|historique|ordre\s+des?\s+[eé]v[eé]nements?)\b", _I), CAT_FORENSIC_TIMELINE, 0.9),
    (re.compile(r"\b(?:quand|[àa]\s+quelle\s+heure|depuis\s+quand|[àa]\s+quel\s+moment)\s+(?:s['`]est|[eé]tait|a)\b", _I), CAT_FORENSIC_TIMELINE, 0.75),

    # ── workflow_navigation ─────────────────────────────────────────────
    (re.compile(r"\b(?:comment|proc[eé]dure|[eé]tapes?|process(?:us)?|workflow)\b", _I), CAT_WORKFLOW_NAVIGATION, 0.5),
    (re.compile(r"\bcomment\s+(?:cr[eé]er?|supprimer?|modifier?|ajouter?|configurer?|d[eé]ployer?)\b", _I), CAT_WORKFLOW_NAVIGATION, 0.9),
    (re.compile(r"\b(?:quelle\s+(?:proc[eé]dure|[eé]tape)|que\s+faut[\s-]+il\s+faire)\b", _I), CAT_WORKFLOW_NAVIGATION, 0.85),
    (re.compile(r"\b(?:IHM|interface|[eé]cran|formulaire|saisie|menu)\b", _I), CAT_IHM_NAVIGATION, 0.7),

    # ── operational_procedure ───────────────────────────────────────────
    (re.compile(r"\b(?:FR|fiche\s+(?:de\s+)?r[eé]solution|proc[eé]dure\s+op[eé]rationnelle|runbook)\b", _I), CAT_OPERATIONAL_PROCEDURE, 0.85),
    (re.compile(r"\b(?:actions?\s+recommand[eé]es?|[eé]tapes?\s+de\s+r[eé]solution|marche\s+[àa]\s+suivre)\b", _I), CAT_OPERATIONAL_PROCEDURE, 0.8),

    # ── source_code_lookup ──────────────────────────────────────────────
    (re.compile(r"\b(?:fonction|m[eé]thode|classe|service\s+java|impl[eé]ment(?:ation)?|impl\b)\b", _I), CAT_SOURCE_CODE_LOOKUP, 0.85),
    (re.compile(r"\bquelle(?:s?\s+(?:est|sont)\s+(?:la|les?)\s+(?:classe|m[eé]thode|fonction|service))\b", _I), CAT_SOURCE_CODE_LOOKUP, 0.9),
    (re.compile(r"\b(?:code\s+source|fichier\s+java|\.java\b|BusinessImpl|ManagerImpl|Controller)\b", _I), CAT_SOURCE_CODE_LOOKUP, 0.8),
    (re.compile(r"\bquel(?:le)?\s+(?:classe|service|composant)\s+(?:g[eé]re|effectue|r[eé]alise|traite|appelle)\b", _I), CAT_SOURCE_CODE_LOOKUP, 0.9),

    # ── function_trace ──────────────────────────────────────────────────
    (re.compile(r"\b(?:cha[iî]ne\s+d[''`]appel|call\s+chain|call\s+stack|appel[eé]e?\s+par|qui\s+appelle)\b", _I), CAT_FUNCTION_TRACE, 0.9),
    (re.compile(r"\b(?:trace\s+d[''`]ex[eé]cution|ex[eé]cution\s+path|chemin\s+d[''`]appel)\b", _I), CAT_FUNCTION_TRACE, 0.9),

    # ── business_rule_explanation ───────────────────────────────────────
    (re.compile(r"\b(?:r[eè]gle\s+(?:m[eé]tier|business)|condition\s+(?:de\s+)?(?:blocage|validation)|pourquoi\s+cette\s+(?:r[eè]gle|contrainte))\b", _I), CAT_BUSINESS_RULE, 0.9),
    (re.compile(r"\b(?:pourquoi\s+(?:faut[\s-]+il|est[\s-]+ce\s+que|doit[\s-]+on))\b", _I), CAT_BUSINESS_RULE, 0.6),

    # ── runtime_state_analysis ──────────────────────────────────────────
    (re.compile(r"\b(?:[eé]tat\s+(?:actuel|courant|en\s+base)|statut\s+(?:du|de\s+l[''`])[eé]quipement|donn[eé]es?\s+(?:en\s+base|DB|BDD))\b", _I), CAT_RUNTIME_STATE, 0.9),
    (re.compile(r"\b(?:qu[''`]est[\s-]+ce\s+qu[''`]il\s+y\s+a\s+en\s+base|contenu\s+(?:de\s+la\s+table|BDD))\b", _I), CAT_RUNTIME_STATE, 0.85),

    # ── schema_lookup ───────────────────────────────────────────────────
    (re.compile(r"\b(?:sch[eé]ma|table\s+SQL|structure\s+(?:de\s+la\s+table|BDD)|colonnes?|champs?)\b", _I), CAT_SCHEMA_LOOKUP, 0.8),
    (re.compile(r"\bquelle(?:s)?\s+table(?:s)?\b", _I), CAT_SCHEMA_LOOKUP, 0.85),
    (re.compile(r"\b(?:t_[a-z][a-z0-9_]+)\b", _I), CAT_SCHEMA_LOOKUP, 0.6),

    # ── sql_lookup ──────────────────────────────────────────────────────
    (re.compile(r"\b(?:requ[eê]te\s+SQL|SELECT|JOIN|WHERE|GROUP\s+BY|HAVING|requ[eê]te\s+de\s+v[eé]rification)\b", _I), CAT_SQL_LOOKUP, 0.85),
    (re.compile(r"\b(?:comment\s+requ[eê]ter?|quelle\s+requ[eê]te|SQL\s+pour)\b", _I), CAT_SQL_LOOKUP, 0.8),

    # ── exception_lookup ────────────────────────────────────────────────
    (re.compile(r"\b(?:exception|erreur\s+java|stacktrace|thrown?|lev[eé]e?)\b", _I), CAT_EXCEPTION_LOOKUP, 0.8),
    (re.compile(r"\b(?:montre[rz]?|affich(?:er?|e)|voir|lister?)\s+(?:les?\s+)?exceptions?\b", _I), CAT_EXCEPTION_LOOKUP, 0.95),
    (re.compile(r"\b(?:quelle(?:s)?\s+exception(?:s)?\s+(?:est|sont|peut|peuvent)\s+(?:lev[eé]e?|thrown?|g[eé]n[eé]r[eé]e?))\b", _I), CAT_EXCEPTION_LOOKUP, 0.95),
    (re.compile(r"\bexception(?:s)?\s+(?:sont|est)\s+lev[eé]e?s?\b", _I), CAT_EXCEPTION_LOOKUP, 0.9),
    (re.compile(r"\blev[eé]e?s?\s+lors\b", _I), CAT_EXCEPTION_LOOKUP, 0.85),
    (re.compile(r"\b(?:BrasilTechnicalException|ConnectorException|BrasilException|NullPointerException)\b"), CAT_EXCEPTION_LOOKUP, 0.95),

    # ── dependency_analysis ─────────────────────────────────────────────
    (re.compile(r"\b(?:d[eé]pendances?|contrainte(?:s)?\s+(?:de\s+)?(?:int[eé]grit[eé]|cl[eé]\s+[eé]trang[eè]re|FK)|cl[eé]s?\s+[eé]trang[eè]res?)\b", _I), CAT_DEPENDENCY_ANALYSIS, 0.9),
    (re.compile(r"\b(?:qui\s+utilise|impact[eé]|bloqu[eé]\s+par|d[eé]pend\s+de|li[eé]\s+[àa])\b", _I), CAT_DEPENDENCY_ANALYSIS, 0.7),
    (re.compile(r"\b(?:services?\s+actifs?|pr[eé]stations?\s+actives?|ressources?\s+occup[eé]es?)\b", _I), CAT_DEPENDENCY_ANALYSIS, 0.8),

    # ── incident_history ────────────────────────────────────────────────
    (re.compile(r"\b(?:incident(?:s)?\s+similaires?|historique\s+(?:des?\s+)?incidents?|tickets?\s+(?:jira|similaires?|pass[eé]s?)|cas\s+similaires?)\b", _I), CAT_INCIDENT_HISTORY, 0.9),
    (re.compile(r"\b(?:d[eé]j[àa]\s+vu|d[eé]j[àa]\s+eu\s+ce\s+probl[eè]me|pass[eé]\s+pr[eé]c[eé]dent)\b", _I), CAT_INCIDENT_HISTORY, 0.8),

    # ── ihm_navigation ──────────────────────────────────────────────────
    (re.compile(r"\b(?:IHM|interface\s+(?:BRASIL|graphique|web)|[eé]cran\s+de|navigation|menu|bouton|onglet|formulaire)\b", _I), CAT_IHM_NAVIGATION, 0.85),
    (re.compile(r"\b(?:o[uù]\s+cliquer?|o[uù]\s+(?:se\s+trouve|[eé]t(?:ait|re))\s+le\s+(?:bouton|menu|lien))\b", _I), CAT_IHM_NAVIGATION, 0.9),

    # ── cross_system_correlation ────────────────────────────────────────
    (re.compile(r"\b(?:corr[eé]lation|lien\s+entre|impact\s+sur|propagation|cascade)\b", _I), CAT_CROSS_SYSTEM, 0.8),
    (re.compile(r"\b(?:BRASIL|ORCHESTRA|SEBA|ARTEMIS|IPON|ADELIA)\s+et\s+(?:BRASIL|ORCHESTRA|SEBA|ARTEMIS|IPON|ADELIA)\b", _I), CAT_CROSS_SYSTEM, 0.95),

    # ── validation_constraint ───────────────────────────────────────────
    (re.compile(r"\b(?:contrainte(?:s)?\s+(?:de\s+)?(?:validation|blocage|m[eé]tier)|v[eé]rification(?:s)?\s+(?:avant|pr[eé]alable))\b", _I), CAT_VALIDATION_CONSTRAINT, 0.9),
    (re.compile(r"\b(?:condition(?:s)?\s+de\s+(?:blocage|suppression|cr[eé]ation|d[eé]ploiement)|pr[eé]requis)\b", _I), CAT_VALIDATION_CONSTRAINT, 0.85),
    (re.compile(r"\b(?:qu[''`]est[\s-]+ce\s+qui\s+(?:bloque|emp[eê]che|interdit))\b", _I), CAT_VALIDATION_CONSTRAINT, 0.8),

    # ── rollback_analysis ───────────────────────────────────────────────
    (re.compile(r"\b(?:rollback|annulation|r[eé]version|retour\s+arri[eè]re|d[eé]faire|undo)\b", _I), CAT_ROLLBACK_ANALYSIS, 0.9),
    (re.compile(r"\b(?:transaction\s+(?:annul[eé]e?|[eé]chou[eé]e?)|commit\s+[eé]chou[eé])\b", _I), CAT_ROLLBACK_ANALYSIS, 0.85),
    (re.compile(r"\btransaction\s+a\s+[eé]t[eé]\s+annul[eé]e?\b", _I), CAT_ROLLBACK_ANALYSIS, 0.95),

    # ── transaction_analysis ────────────────────────────────────────────
    (re.compile(r"\b(?:transaction|commit|autocommit|isolation|verrou|lock(?:ed)?)\b", _I), CAT_TRANSACTION_ANALYSIS, 0.8),
    (re.compile(r"\b(?:enregistrement\s+(?:[eé]chou[eé]|incomplet)|donn[eé]es?\s+r[eé]siduelles?)\b", _I), CAT_TRANSACTION_ANALYSIS, 0.75),

    # ── service_dependency ──────────────────────────────────────────────
    (re.compile(r"\b(?:d[eé]pendance\s+(?:de\s+)?service|service\s+(?:d[eé]pendant|requis|n[eé]cessaire)|services?\s+amont|services?\s+aval)\b", _I), CAT_SERVICE_DEPENDENCY, 0.9),
    (re.compile(r"\b(?:MRT|EPT|OLT|DSLAM|VLAN|NRO)\s+(?:li[eé]|utilis[eé]|d[eé]pend)\b", _I), CAT_SERVICE_DEPENDENCY, 0.8),

    # ── state_machine_analysis ──────────────────────────────────────────
    (re.compile(r"\b(?:machine\s+[aà]\s+[eé]tats?|state\s+machine|[eé]tat\s+(?:initial|final|interm[eé]diaire)|transition\s+d[''`][eé]tat)\b", _I), CAT_STATE_MACHINE, 0.9),
    (re.compile(r"\b(?:[eé]tat\s+(?:AVAILABLE|LOCKED|IN_USE|DELETED|PROVISIONED|ERROR|PENDING))\b", _I), CAT_STATE_MACHINE, 0.85),

    # ── root_cause_explanation ──────────────────────────────────────────
    (re.compile(r"\b(?:cause\s+(?:racine|principale|profonde)|root\s+cause|RCA|analyse\s+(?:de\s+)?cause)\b", _I), CAT_ROOT_CAUSE, 0.9),
    (re.compile(r"\b(?:pourquoi\s+(?:cette?\s+erreur|cela\s+s[''`]est\s+produit|ce\s+probl[eè]me))\b", _I), CAT_ROOT_CAUSE, 0.8),

    # ── evidence_provenance ─────────────────────────────────────────────
    (re.compile(r"\b(?:depuis\s+quels?\s+(?:logs?|fichiers?|sources?)|provenance|d[''`]o[uù]\s+(?:viennent?|vient)\s+(?:ces?\s+)?(?:infos?|donn[eé]es?|r[eé]sultats?))\b", _I), CAT_EVIDENCE_PROVENANCE, 0.95),
    (re.compile(r"\b(?:quelle\s+est\s+la\s+source|sur\s+quelles?\s+(?:donn[eé]es?|preuves?))\b", _I), CAT_EVIDENCE_PROVENANCE, 0.85),

    # ── log_source_identification ───────────────────────────────────────
    (re.compile(r"\b(?:quel(?:s)?\s+(?:fichiers?\s+de\s+)?logs?|o[uù]\s+sont\s+les?\s+logs?|quel\s+fichier\s+consulter)\b", _I), CAT_LOG_SOURCE, 0.9),
    (re.compile(r"\b(?:o[uù]\s+trouver?\s+(?:les?\s+)?(?:logs?|traces?|erreurs?))\b", _I), CAT_LOG_SOURCE, 0.85),

    # ── workflow_stage_identification ────────────────────────────────────
    (re.compile(r"\b(?:[àa]\s+quelle\s+[eé]tape|[eé]tape\s+(?:en\s+cours|actuelle|suivante|pr[eé]c[eé]dente)|stade\s+(?:du|de\s+la)\s+(?:proc[eé]dure|workflow))\b", _I), CAT_WORKFLOW_STAGE, 0.9),
    (re.compile(r"\b(?:o[uù]\s+en\s+est|[eé]tat\s+d[''`]avancement|progression)\b", _I), CAT_WORKFLOW_STAGE, 0.7),
]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RESULT TYPE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class SemanticRouterResult:
    primary: str
    confidence: float
    labels: List[Tuple[str, float]]       # All matched categories with scores
    forensic_intent: Optional[str]        # Maps to existing handler if applicable
    is_multi_label: bool

    def has_category(self, cat: str) -> bool:
        return any(c == cat for c, _ in self.labels)

    def top_n(self, n: int = 3) -> List[Tuple[str, float]]:
        return self.labels[:n]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ROUTER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class SemanticIntentRouter:
    """
    Classifies user messages into semantic categories.

    Usage:
        result = semantic_router.route("quelle fonction supprime un dslam ?")
        result.primary       → "source_code_lookup"
        result.forensic_intent → "find_code_function"
        result.labels        → [("source_code_lookup", 0.85), ("function_trace", 0.9)]
    """

    MULTI_LABEL_THRESHOLD = 0.55   # categories above this score are included in labels
    PRIMARY_THRESHOLD = 0.40       # minimum score to have any category at all

    def route(self, text: str) -> SemanticRouterResult:
        """
        Route a user message to semantic categories.
        Returns a SemanticRouterResult.
        """
        if not text or not text.strip():
            return SemanticRouterResult(
                primary="runtime_diagnostic",
                confidence=0.0,
                labels=[],
                forensic_intent=None,
                is_multi_label=False,
            )

        scores: Dict[str, float] = {}
        for pattern, category, weight in _RULES:
            if pattern.search(text):
                scores[category] = max(scores.get(category, 0.0), weight)

        if not scores:
            return SemanticRouterResult(
                primary="runtime_diagnostic",
                confidence=0.0,
                labels=[],
                forensic_intent=None,
                is_multi_label=False,
            )

        # Sort by score descending
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        primary, primary_conf = ranked[0]

        if primary_conf < self.PRIMARY_THRESHOLD:
            primary = "runtime_diagnostic"
            primary_conf = 0.3

        # Multi-label: all categories above threshold
        labels = [(c, s) for c, s in ranked if s >= self.MULTI_LABEL_THRESHOLD]
        if not labels:
            labels = [(primary, primary_conf)]

        forensic_intent = CATEGORY_TO_FORENSIC_INTENT.get(primary)

        result = SemanticRouterResult(
            primary=primary,
            confidence=primary_conf,
            labels=labels,
            forensic_intent=forensic_intent,
            is_multi_label=len(labels) > 1,
        )

        logger.debug(
            f"[SemanticRouter] '{text[:50]}' → primary={primary} "
            f"conf={primary_conf:.2f} labels={len(labels)}"
        )
        return result

    def get_forensic_intent(self, text: str) -> Optional[str]:
        """Quick helper: just returns the forensic intent string or None."""
        return self.route(text).forensic_intent

    def explain(self, text: str) -> str:
        """Return a human-readable explanation of the routing decision."""
        result = self.route(text)
        lines = [
            f"🧭 **Semantic Route** — `{text[:60]}`",
            f"",
            f"**Primary category**: `{result.primary}` (conf={result.confidence:.0%})",
        ]
        if result.forensic_intent:
            lines.append(f"**Handler**: `{result.forensic_intent}`")
        if result.is_multi_label:
            lines.append(f"**All categories:**")
            for cat, score in result.top_n(5):
                lines.append(f"  - `{cat}` ({score:.0%})")
        return "\n".join(lines)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SINGLETON
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

semantic_router = SemanticIntentRouter()
