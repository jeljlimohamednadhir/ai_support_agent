"""
n3_question_router.py
━━━━━━━━━━━━━━━━━━━━━
N3 Question Classification & Routing Engine

PURPOSE
───────
The existing `_detect_tech_inference_intent` in chatbot_service.py only
handles "c'est quoi la table X" style questions with a single regex chain.
This module provides a full 23-category router that:
  1. Classifies any N3 question into a category
  2. Sets routing metadata (urgency, required_tools, suggested_workflows)
  3. Allows chatbot_service.py to adjust system prompt + tool calls based on category

CATEGORIES (23)
───────────────
 1. schema_query          — "c'est quoi la table t_xxx", "describe t_xxx"
 2. deletion_blocked      — "impossible de supprimer", "ne peut pas supprimer DSLAM"
 3. workflow_stuck        — "workflow bloqué", "ordre coincé", "provisioning en attente"
 4. mq_sync_failure       — "JMS", "ACK absent", "DLQ", "message non traité"
 5. nd_incident           — "ND en anomalie", "ND bloqué", "noeud réseau"
 6. epc_lifecycle         — "EPC state", "mouvement EPC", "UMI provisioning"
 7. es_script_stuck       — "script bloqué", "ES script erreur", "script en attente"
 8. vlan_inconsistency    — "VLAN incohérent", "VLAN 0", "connecteur VLAN"
 9. rollback_detected     — "rollback", "annulation transaction", "état incohérent"
10. orphan_detection      — "données résiduelles", "orphelin", "ressource fantôme"
11. temporal_rca          — "séquence d'événements", "chronologie", "quand est-ce que"
12. log_investigation     — "logs", "traces", "stack trace", "exception"
13. server_localization   — "quel serveur", "sur quelle machine", "infra serveur"
14. infra_anomaly         — "anomalie infra", "saturation", "CPU", "mémoire"
15. cross_system_drift    — "désynchronisation BRASIL/42C", "incohérence entre systèmes"
16. mutation_failure      — "mutation refusée", "createMovement fail", "update rejeté"
17. partial_provisioning  — "partiellement configuré", "PARTLY_CONFIGURED", "incomplet"
18. ghost_service         — "service fantôme", "ressource inexistante", "ghost"
19. retry_loop            — "boucle de retry", "tentatives répétées", "même erreur"
20. db_runtime_mismatch   — "DB dit X mais runtime dit Y", "incohérence base/IHM"
21. causal_escalation     — "pourquoi ça bloque", "root cause", "analyse de cause"
22. recurring_incident    — "cet incident se reproduit", "même problème depuis X"
23. intermittent_incident — "parfois ça marche", "aléatoire", "intermittent"
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ROUTING RESULT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class N3RoutingResult:
    """Complete routing decision for a user question."""
    category: str                          # one of the 23 categories
    confidence: float                      # 0.0–1.0
    urgency: str = "normal"               # "low", "normal", "high", "critical"
    requires_schema: bool = False
    requires_rca: bool = False
    requires_temporal: bool = False
    requires_workflow: bool = False
    requires_business_rules: bool = False
    requires_db_query: bool = False
    suggested_workflows: List[str] = field(default_factory=list)
    system_prompt_hint: str = ""           # injected into system prompt
    matched_patterns: List[str] = field(default_factory=list)
    extracted_entity: Optional[str] = None
    secondary_categories: List[str] = field(default_factory=list)

    @property
    def is_high_priority(self) -> bool:
        return self.urgency in ("high", "critical")

    @property
    def needs_intelligence_layer(self) -> bool:
        """True if this question requires more than a simple Qdrant lookup."""
        return (
            self.requires_rca or self.requires_temporal or
            self.requires_workflow or self.requires_business_rules
        )

    def summarize(self) -> str:
        tools = []
        if self.requires_schema:        tools.append("SCHEMA")
        if self.requires_rca:           tools.append("RCA")
        if self.requires_temporal:      tools.append("TEMPORAL")
        if self.requires_workflow:      tools.append("WORKFLOW")
        if self.requires_business_rules: tools.append("BIZ_RULES")
        if self.requires_db_query:      tools.append("DB_QUERY")
        tool_str = "+".join(tools) if tools else "NONE"
        return (
            f"[N3Router] {self.category} (conf={self.confidence:.2f}, "
            f"urgency={self.urgency}, tools={tool_str})"
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ROUTING RULES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class _RoutingRule:
    category: str
    patterns: List[re.Pattern]
    urgency: str = "normal"
    weight: float = 1.0    # higher weight wins when multiple rules match
    requires_schema: bool = False
    requires_rca: bool = False
    requires_temporal: bool = False
    requires_workflow: bool = False
    requires_business_rules: bool = False
    requires_db_query: bool = False
    suggested_workflows: List[str] = field(default_factory=list)
    system_prompt_hint: str = ""


# Each rule has a list of compiled patterns; any match triggers the rule.
# Rules are evaluated in ORDER; first match with highest weight wins (but
# multiple can be stored as secondary_categories).

_ROUTING_RULES: List[_RoutingRule] = [

    _RoutingRule(
        category="schema_query",
        patterns=[
            re.compile(r"c(?:\'|')est quoi\s+(?:la|le|l[\''])\s*table\s+\w+", re.I),
            re.compile(r"describe\s+(?:la table\s+)?t_\w+", re.I),
            re.compile(r"d(?:é|e)cris\s+(?:la table\s+)?t_\w+", re.I),
            re.compile(r"struct(?:ure|ure de)\s+t_\w+", re.I),
            re.compile(r"colonnes?\s+de\s+(?:la table\s+)?t_\w+", re.I),
            re.compile(r"qu(?:e|\'|\')est.ce que t_\w+", re.I),
            re.compile(r"\bt_\w{4,}\b.*(?:table|schema|colonne|champ|clé)", re.I),
        ],
        urgency="low",
        weight=2.0,
        requires_schema=True,
        system_prompt_hint=(
            "L'ingénieur demande la structure d'une table BRASIL. "
            "Fournis le schéma exact (colonnes, types, clés FK) depuis brasil_schema_knowledge. "
            "Ne devine pas — utilise uniquement describe_table()."
        ),
    ),

    _RoutingRule(
        category="deletion_blocked",
        patterns=[
            re.compile(r"(?:impossible|impossible de|ne peut pas|ne peux pas|refus[eé])\s+(?:de\s+)?supprim(?:er|é)", re.I),
            re.compile(r"suppression\s+(?:bloquée?|refusée?|échouée?|fail)", re.I),
            re.compile(r"delete.*(?:fail|error|block|bloqué|refusé)", re.I),
            re.compile(r"EQPT_DEL_\d+|erreur.*suppression.*DSLAM", re.I),
            re.compile(r"(?:DSLAM|équipement|equipment).*(?:ne peut pas|impossible).*supprim", re.I),
        ],
        urgency="high",
        weight=1.5,
        requires_rca=True,
        requires_business_rules=True,
        requires_db_query=True,
        suggested_workflows=["delete_dslam", "delete_equipment"],
        system_prompt_hint=(
            "L'ingénieur ne peut pas supprimer un équipement/DSLAM. "
            "Applique les règles métier: services actifs? liens MRT? statut F? "
            "Consulte les règles EQPT_DEL_001/002/003. "
            "Indique les pré-requis exacts pour débloquer la suppression."
        ),
    ),

    _RoutingRule(
        category="workflow_stuck",
        patterns=[
            re.compile(r"workflow\s+(?:bloqué?|coinc[eé]|suspend[eu]|en attente)", re.I),
            re.compile(r"ordre?\s+(?:bloqué?|coinc[eé]|en attente|gelé)", re.I),
            re.compile(r"provisioning\s+(?:bloqué?|en attente|timeout|failed)", re.I),
            re.compile(r"(?:commande|order)\s+(?:stuck|bloquée?|pending forever)", re.I),
            re.compile(r"replay.*ordre?|rejou.*commande", re.I),
        ],
        urgency="high",
        weight=1.5,
        requires_workflow=True,
        requires_rca=True,
        system_prompt_hint=(
            "Un workflow BRASIL est bloqué. Identifie le workflow exact (EPC/UMI/VLAN/TP/MakingFile), "
            "son étape actuelle, et les conditions de déblocage. "
            "Indique si un replay ou une intervention manuelle est nécessaire."
        ),
    ),

    _RoutingRule(
        category="mq_sync_failure",
        patterns=[
            re.compile(r"(?:JMS|MQ|ActiveMQ|message.queue|queue)\s+(?:err|fail|down|absent|timeout)", re.I),
            re.compile(r"ACK\s+(?:absent|manquant|non reçu|missing|not received)", re.I),
            re.compile(r"(?:DLQ|dead.letter.queue|dead letter)", re.I),
            re.compile(r"message\s+(?:non traité|non livré|not delivered|not processed)", re.I),
            re.compile(r"JMSException|MessageNotDelivered", re.I),
            re.compile(r"broker\s+(?:inaccessible|down|unreachable)", re.I),
        ],
        urgency="critical",
        weight=2.0,
        requires_temporal=True,
        requires_rca=True,
        system_prompt_hint=(
            "Incident MQ/JMS détecté. Analyse: (1) le broker est-il up? "
            "(2) Y a-t-il des messages en DLQ? (3) L'ACK est-il arrivé? "
            "Fournis les commandes de diagnostic MQ et les étapes de rejeu."
        ),
    ),

    _RoutingRule(
        category="nd_incident",
        patterns=[
            re.compile(r"(?:ND|nœud|noeud)\s+(?:en anomalie|bloqué?|désaffecté?|affectation fail)", re.I),
            re.compile(r"(?:ND|node)\s+\w+\s+(?:anomalie|incident|err)", re.I),
            re.compile(r"affectation\s+42C|42C\s+affectation", re.I),
            re.compile(r"t_mrt_access_dslams|DSLAM_AFFECTATION", re.I),
            re.compile(r"noeud\s+(?:réseau|IP)\s+(?:absent|introuvable)", re.I),
        ],
        urgency="high",
        weight=1.5,
        requires_rca=True,
        requires_workflow=True,
        suggested_workflows=["nd_mutation_42c"],
        system_prompt_hint=(
            "Incident sur un Nœud de Desserte (ND) ou affectation 42C. "
            "Vérifie: statut ND, DSLAM affecté, liens t_mrt_access_dslams, "
            "erreur 42C. Propose les étapes de remédiation."
        ),
    ),

    _RoutingRule(
        category="epc_lifecycle",
        patterns=[
            re.compile(r"EPC\s+(?:state|état|bloqu(?:é|e)|stuck|provisioning|lifecycle)", re.I),
            re.compile(r"(?:mouvement|movement)\s+EPC", re.I),
            re.compile(r"UMI\s+(?:create|modify|delete|provisioning|EPC)", re.I),
            re.compile(r"epcv_currentstate|epc.*IN_PROGRESS|EPC.*CONFIGURED", re.I),
            re.compile(r"createMovement|completeMovement|epc.*state machine", re.I),
        ],
        urgency="high",
        weight=1.5,
        requires_workflow=True,
        requires_business_rules=True,
        requires_rca=True,
        suggested_workflows=["umi_epc_create", "umi_epc_modify", "umi_epc_delete"],
        system_prompt_hint=(
            "Incident sur lifecycle EPC/UMI. Analyse l'état FSM actuel "
            "(C/M/X ou IN_PROGRESS/CONFIGURED/ACTIVE), identifie la transition bloquée, "
            "vérifie les règles EPCV_FSM. Propose la correction et le rejeu si applicable."
        ),
    ),

    _RoutingRule(
        category="es_script_stuck",
        patterns=[
            re.compile(r"(?:ES|script)\s+(?:bloqué?|stuck|en attente|timeout|erreur)", re.I),
            re.compile(r"script.*(?:RUNNING|es_state\s*=\s*1|état.*1)", re.I),
            re.compile(r"t_tp_es_scripts?|script.*provisionning", re.I),
            re.compile(r"script.*ne.*termin|script.*jamais.*fini", re.I),
        ],
        urgency="high",
        weight=1.4,
        requires_workflow=True,
        requires_db_query=True,
        suggested_workflows=["es_script_unblock"],
        system_prompt_hint=(
            "Script ES bloqué ou en erreur. Vérifie t_tp_es_scripts (es_state, es_result), "
            "identifie si relance possible, fournis la procédure de déblocage."
        ),
    ),

    _RoutingRule(
        category="vlan_inconsistency",
        patterns=[
            re.compile(r"VLAN\s+(?:0|incohérent|inconsistant|absent|manquant)", re.I),
            re.compile(r"connecteur.*VLAN|VLAN.*connecteur", re.I),
            re.compile(r"ConnectorCreationVlanException", re.I),
            re.compile(r"VLAN\s+\d+\s+(?:inexistant|not found|absent)", re.I),
            re.compile(r"t_vlan|vlan.*désynchronisé", re.I),
        ],
        urgency="high",
        weight=1.4,
        requires_rca=True,
        requires_workflow=True,
        suggested_workflows=["vlan_delete", "create_vlan"],
        system_prompt_hint=(
            "Incohérence VLAN détectée. Vérifie t_vlan et t_connectors, "
            "identifie VLAN orphelin ou à 0, propose la correction (recréation ou suppression propre)."
        ),
    ),

    _RoutingRule(
        category="rollback_detected",
        patterns=[
            re.compile(r"rollback|ROLLBACK|annulation.*transaction", re.I),
            re.compile(r"transaction.*rolled.back|rolled.back.*transaction", re.I),
            re.compile(r"état.*incohérent.*suite.*erreur|incohérence.*rollback", re.I),
            re.compile(r"partiellement\s+annulé?|partial.*rollback", re.I),
        ],
        urgency="high",
        weight=1.6,
        requires_temporal=True,
        requires_rca=True,
        requires_workflow=True,
        suggested_workflows=["partial_rollback_recovery"],
        system_prompt_hint=(
            "Un rollback a été détecté. Vérifie l'état DB APRÈS le rollback, "
            "identifie les tables affectées (t_equipments, t_services, t_vlan, t_epc), "
            "propose une procédure de réconciliation et les requêtes SQL de vérification."
        ),
    ),

    _RoutingRule(
        category="orphan_detection",
        patterns=[
            re.compile(r"(?:données|data|resource)\s+r(?:é|e)siduelles?", re.I),
            re.compile(r"orphelin|orphan|ressource\s+fantôme", re.I),
            re.compile(r"enregistrement\s+(?:résiduel|obsolète|stale|sans parent)", re.I),
            re.compile(r"nettoyage\s+(?:base|BDD|DB)|cleanup.*BRASIL", re.I),
        ],
        urgency="normal",
        weight=1.2,
        requires_rca=True,
        requires_db_query=True,
        suggested_workflows=["orphan_cleanup"],
        system_prompt_hint=(
            "Détection de données orphelines/résiduelles. "
            "Identifie les tables concernées, propose les requêtes SQL de détection, "
            "vérifie les FK contraintes avant suppression."
        ),
    ),

    _RoutingRule(
        category="temporal_rca",
        patterns=[
            re.compile(r"s(?:é|e)quence\s+d(?:\'|\')(?:é|e)v(?:é|e)nements?", re.I),
            re.compile(r"chronologie|timeline|ordre\s+des\s+(?:é|e)v(?:é|e)nements?", re.I),
            re.compile(r"quand\s+(?:est.ce que|a\s+commenc[eé]|s(?:\'|\')est\s+produit)", re.I),
            re.compile(r"avant\s+(?:que|de)\s+.+\s+après\s+(?:que|le)", re.I),
            re.compile(r"d(?:é|e)roul[eé]\s+(?:de\s+l(?:\'|')incident|des\s+(?:é|e)v(?:é|e)nements?)", re.I),
        ],
        urgency="normal",
        weight=1.3,
        requires_temporal=True,
        requires_rca=True,
        system_prompt_hint=(
            "L'ingénieur veut comprendre la séquence temporelle de l'incident. "
            "Reconstruit la chronologie, identifie l'événement déclencheur, "
            "détecte les gaps et boucles. Utilise le module temporal_reasoning."
        ),
    ),

    _RoutingRule(
        category="log_investigation",
        patterns=[
            re.compile(r"\blogs?\b.+(?:show|affich|cherch|analys|investig|trouv)", re.I),
            re.compile(r"(?:stack trace|stacktrace|trace d(?:\'|\')erreur)", re.I),
            re.compile(r"exception.+log|log.+exception", re.I),
            re.compile(r"where.*log|log.*where|dans\s+(?:les\s+)?logs?", re.I),
            re.compile(r"qu(?:e|\'|\')est.ce que dit\s+(?:le\s+)?log", re.I),
        ],
        urgency="normal",
        weight=1.1,
        requires_temporal=True,
        system_prompt_hint=(
            "Analyse de logs demandée. Extrait les événements pertinents, "
            "classe par sévérité, reconstruit la chronologie si possible."
        ),
    ),

    _RoutingRule(
        category="server_localization",
        patterns=[
            re.compile(r"quel\s+serveur|sur\s+quelle\s+machine", re.I),
            re.compile(r"where.*(?:running|deployed|installed)|déployé\s+sur", re.I),
            re.compile(r"IP\s+(?:du\s+)?serveur|hostname|FQDN", re.I),
            re.compile(r"instance\s+(?:BRASIL|Oracle|PostgreSQL|JBoss|Wildfly)", re.I),
        ],
        urgency="low",
        weight=1.0,
        requires_db_query=True,
        system_prompt_hint=(
            "Localisation d'un serveur ou composant infra demandée. "
            "Indique l'IP, hostname, et rôle du composant dans l'architecture BRASIL."
        ),
    ),

    _RoutingRule(
        category="infra_anomaly",
        patterns=[
            re.compile(r"anomalie\s+infra|infra\s+(?:problem|problème|issue)", re.I),
            re.compile(r"saturation|CPU\s+(?:élevé|high)|mémoire\s+(?:pleine|saturée)", re.I),
            re.compile(r"disk\s+full|disque\s+plein|filesystem.*full", re.I),
            re.compile(r"connexion\s+(?:DB|base|oracle|postgres)\s+(?:fail|erreur|refused)", re.I),
        ],
        urgency="critical",
        weight=1.8,
        requires_rca=True,
        system_prompt_hint=(
            "Anomalie d'infrastructure détectée. Évalue l'impact sur BRASIL, "
            "identifie les services affectés, propose les vérifications immédiates."
        ),
    ),

    _RoutingRule(
        category="cross_system_drift",
        patterns=[
            re.compile(r"désync(?:hronisation)?\s+(?:BRASIL|42C|ORCHESTRA|SI)", re.I),
            re.compile(r"incoh(?:é|e)rence\s+entre\s+(?:syst[eè]mes?|bases?)", re.I),
            re.compile(r"BRASIL\s+(?:dit|says?|affiche)\s+.+\s+(?:mais|but|alors que)\s+42C", re.I),
            re.compile(r"42C\s+(?:ne\s+(?:voit|connaît)|unknown)\s+.+\s+(?:mais|but)\s+BRASIL", re.I),
            re.compile(r"(?:référentiel|ref)\s+(?:désynchronisé|out.of.sync)", re.I),
        ],
        urgency="critical",
        weight=1.9,
        requires_rca=True,
        requires_temporal=True,
        suggested_workflows=["sync_reconciliation"],
        system_prompt_hint=(
            "Désynchronisation inter-systèmes (BRASIL/42C/ORCHESTRA). "
            "Identifie quelle base est la source de vérité, propose la procédure "
            "de réconciliation, et liste les requêtes SQL de comparaison."
        ),
    ),

    _RoutingRule(
        category="mutation_failure",
        patterns=[
            re.compile(r"mutation\s+(?:refusée?|échouée?|fail|erreur)", re.I),
            re.compile(r"(?:create|update|delete)Movement\s+fail", re.I),
            re.compile(r"(?:INSERT|UPDATE|DELETE)\s+(?:fail|erreur|rejeté)", re.I),
            re.compile(r"BrasilConstraintException|ConstraintViolationException", re.I),
        ],
        urgency="high",
        weight=1.5,
        requires_rca=True,
        requires_business_rules=True,
        requires_db_query=True,
        system_prompt_hint=(
            "Une mutation DB a été refusée. Analyse la contrainte violée, "
            "vérifie l'état actuel des entités concernées, propose la correction."
        ),
    ),

    _RoutingRule(
        category="partial_provisioning",
        patterns=[
            re.compile(r"PARTLY_CONFIGURED|partiellement\s+configuré", re.I),
            re.compile(r"provisioning\s+incomplet|incomplet.*provisioning", re.I),
            re.compile(r"(?:configuration|config)\s+partielle", re.I),
            re.compile(r"(?:3|PARTLY)\s*PARTLY_CONFIGURED", re.I),
        ],
        urgency="high",
        weight=1.4,
        requires_rca=True,
        requires_temporal=True,
        requires_workflow=True,
        system_prompt_hint=(
            "Provisioning partiellement complété (état PARTLY_CONFIGURED ou équivalent). "
            "Identifie quelle étape a échoué, vérifie l'état des ressources créées, "
            "propose la correction ou la finalisation du provisioning."
        ),
    ),

    _RoutingRule(
        category="ghost_service",
        patterns=[
            re.compile(r"service\s+fantôme|ghost\s+service", re.I),
            re.compile(r"ressource\s+(?:inexistante|fantôme|fantome|ghost)", re.I),
            re.compile(r"service\s+(?:dans\s+BRASIL\s+mais\s+pas\s+(?:en réseau|physiquement))", re.I),
            re.compile(r"apparaît\s+dans\s+(?:la\s+)?(?:base|DB|BRASIL)\s+mais\s+n(?:\'|\')existe\s+pas", re.I),
        ],
        urgency="normal",
        weight=1.2,
        requires_rca=True,
        requires_db_query=True,
        suggested_workflows=["orphan_cleanup"],
        system_prompt_hint=(
            "Service fantôme détecté (existe en DB mais pas physiquement). "
            "Vérifie les tables de services et de ressources, "
            "identifie l'écart, propose la procédure de nettoyage sécurisée."
        ),
    ),

    _RoutingRule(
        category="retry_loop",
        patterns=[
            re.compile(r"boucle\s+de\s+retry|retry\s+loop", re.I),
            re.compile(r"tentatives?\s+r(?:é|e)p(?:é|e)t(?:é|e)es?|(?:même|same)\s+erreur\s+(?:plusieurs fois|repeatedly)", re.I),
            re.compile(r"retry\s+(?:count|compteur)\s+(?:élevé|\d+|high)", re.I),
            re.compile(r"toujours\s+(?:la même|le même)\s+(?:erreur|exception|problème)", re.I),
        ],
        urgency="high",
        weight=1.6,
        requires_temporal=True,
        requires_rca=True,
        system_prompt_hint=(
            "Boucle de retry détectée. Identifie la cause racine AVANT de rejeter plus d'essais. "
            "Vérifie: (1) cause racine résolue? (2) DLQ? (3) seuil de retry atteint?"
        ),
    ),

    _RoutingRule(
        category="db_runtime_mismatch",
        patterns=[
            re.compile(r"(?:DB|base|BDD)\s+(?:dit|affiche|montre)\s+.+\s+(?:mais|but)\s+(?:IHM|UI|interface|runtime)", re.I),
            re.compile(r"(?:IHM|UI|interface)\s+affiche\s+.+\s+(?:mais|but)\s+(?:DB|base|BDD)\s+(?:dit|montre)", re.I),
            re.compile(r"incoh(?:é|e)rence\s+(?:base.runtime|DB.IHM|runtime.DB)", re.I),
            re.compile(r"(?:valeur|valeurs?)\s+(?:différente?s?|incorrecte?s?)\s+(?:entre|dans)\s+(?:DB|la base|l(?:\'|\')IHM)", re.I),
        ],
        urgency="high",
        weight=1.5,
        requires_db_query=True,
        requires_rca=True,
        system_prompt_hint=(
            "Incohérence DB vs runtime/IHM. Identifie la source de vérité, "
            "propose les requêtes SQL de vérification, et la procédure de resynchronisation."
        ),
    ),

    _RoutingRule(
        category="causal_escalation",
        patterns=[
            re.compile(r"pourquoi\s+(?:ça|cela|il|elle)\s+(?:bloque|échoue|plante|ne fonctionne pas)", re.I),
            re.compile(r"(?:root cause|cause racine|root.cause analysis|RCA)", re.I),
            re.compile(r"(?:analyse|analyser)\s+(?:la\s+)?cause", re.I),
            re.compile(r"d(?:\'|\')où vient\s+(?:ce|cet|cette)\s+(?:problème|erreur|incident)", re.I),
            re.compile(r"qu(?:e|\'|\')est.ce qui\s+(?:cause|provoque|déclenche)", re.I),
        ],
        urgency="normal",
        weight=1.3,
        requires_rca=True,
        requires_temporal=True,
        system_prompt_hint=(
            "Analyse de cause racine demandée. Utilise le graphe causal BRASIL: "
            "remonte depuis le symptôme vers la cause initiale. "
            "Distingue cause racine vs cause immédiate."
        ),
    ),

    _RoutingRule(
        category="recurring_incident",
        patterns=[
            re.compile(r"(?:cet incident|ce problème|cette erreur)\s+(?:se reproduit|revient|réapparaît)", re.I),
            re.compile(r"récurrent|recurring|même problème\s+depuis\s+(?:des?\s+)?(?:jours?|semaines?|mois)", re.I),
            re.compile(r"deuxième?|troisième?\s+fois\s+(?:que|ce)", re.I),
            re.compile(r"(?:encore|toujours)\s+(?:le même|la même)\s+(?:problème|incident|erreur)", re.I),
        ],
        urgency="high",
        weight=1.7,
        requires_rca=True,
        requires_temporal=True,
        system_prompt_hint=(
            "Incident récurrent identifié. La cause racine n'a pas été résolue lors "
            "des précédentes occurrences. Analyse en profondeur pour identifier "
            "la cause systémique, pas seulement le symptôme."
        ),
    ),

    _RoutingRule(
        category="intermittent_incident",
        patterns=[
            re.compile(r"(?:parfois|sometimes|aléatoire|intermittent|sporadique)\s+(?:ça|cela)\s+(?:marche|fonctionne|échoue)", re.I),
            re.compile(r"(?:aléatoire|random|intermittent|sporadique)\s+(?:erreur|problème|incident)", re.I),
            re.compile(r"(?:ne\s+se\s+produit\s+pas\s+toujours|pas\s+toujours\s+reproductible)", re.I),
            re.compile(r"(?:parfois|des fois)\s+oui,?\s+(?:parfois|des fois)\s+non", re.I),
        ],
        urgency="normal",
        weight=1.2,
        requires_temporal=True,
        requires_rca=True,
        system_prompt_hint=(
            "Incident intermittent — difficile à reproduire. "
            "Analyse les patterns temporels (heure, charge, conditions), "
            "vérifie race conditions et timeout variables, recommande une stratégie de capture."
        ),
    ),
]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ENTITY EXTRACTION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_ENTITY_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"\b(t_[a-z_]{3,40})\b", re.I), "table"),
    (re.compile(r"\b(DS[A-Z0-9_-]{4,20})\b"), "dslam"),
    (re.compile(r"\b(ND[A-Z0-9_-]{2,20})\b"), "nd"),
    (re.compile(r"\b(EPC[A-Z0-9_-]{2,20})\b"), "epc"),
    (re.compile(r"\b(TP[A-Z0-9_-]{2,20})\b"), "tp"),
    (re.compile(r"\b(VLAN\s*\d{1,4})\b", re.I), "vlan"),
]

def _extract_entity(text: str) -> Optional[str]:
    """Extract the primary entity (table name, DSLAM, ND, etc.) from a question."""
    for pattern, _ in _ENTITY_PATTERNS:
        m = pattern.search(text)
        if m:
            return m.group(1)
    return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# N3 QUESTION ROUTER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class N3QuestionRouter:
    """
    Routes N3 engineer questions to the appropriate intelligence layer.

    Usage:
        result = n3_router.route("impossible de supprimer le DSLAM DSROB362")
        # → N3RoutingResult(category="deletion_blocked", urgency="high", ...)
    """

    def route(self, question: str, context: Optional[Dict] = None) -> N3RoutingResult:
        """
        Route a question to its N3 category.
        Returns N3RoutingResult with all routing metadata.
        """
        context = context or {}
        matches: List[Tuple[float, _RoutingRule, List[str]]] = []

        for rule in _ROUTING_RULES:
            matched_patterns = []
            for pat in rule.patterns:
                if pat.search(question):
                    matched_patterns.append(pat.pattern[:60])

            if matched_patterns:
                # confidence based on number of patterns matched + weight
                conf = min(0.5 + 0.15 * len(matched_patterns), 0.95) * rule.weight
                matches.append((conf, rule, matched_patterns))

        if not matches:
            return self._fallback_result(question)

        # Sort by score descending
        matches.sort(key=lambda x: x[0], reverse=True)
        best_conf, best_rule, best_patterns = matches[0]

        # Normalize confidence to 0-1
        normalized_conf = min(best_conf / 2.0, 0.95)

        result = N3RoutingResult(
            category=best_rule.category,
            confidence=normalized_conf,
            urgency=best_rule.urgency,
            requires_schema=best_rule.requires_schema,
            requires_rca=best_rule.requires_rca,
            requires_temporal=best_rule.requires_temporal,
            requires_workflow=best_rule.requires_workflow,
            requires_business_rules=best_rule.requires_business_rules,
            requires_db_query=best_rule.requires_db_query,
            suggested_workflows=list(best_rule.suggested_workflows),
            system_prompt_hint=best_rule.system_prompt_hint,
            matched_patterns=best_patterns,
            extracted_entity=_extract_entity(question),
            secondary_categories=[r.category for _, r, _ in matches[1:4]],
        )

        logger.debug(result.summarize())
        return result

    def _fallback_result(self, question: str) -> N3RoutingResult:
        """Default routing when no rule matches."""
        entity = _extract_entity(question)
        # Heuristic: if question contains a table name, treat as schema_query
        if entity and entity.lower().startswith("t_"):
            return N3RoutingResult(
                category="schema_query",
                confidence=0.4,
                urgency="low",
                requires_schema=True,
                extracted_entity=entity,
                system_prompt_hint="Possible requête schéma — fournir les informations sur l'entité mentionnée.",
            )
        return N3RoutingResult(
            category="causal_escalation",
            confidence=0.2,
            urgency="normal",
            requires_rca=True,
            extracted_entity=entity,
            system_prompt_hint="Question N3 non catégorisée — applique le raisonnement causal général.",
        )

    def get_system_prompt_addon(self, result: N3RoutingResult) -> str:
        """
        Returns the system prompt section to inject based on routing result.
        For use in chatbot_service.py build_system_prompt().
        """
        if not result.system_prompt_hint:
            return ""
        lines = [
            f"\n## [N3 Router — {result.category.upper()}]",
            result.system_prompt_hint,
        ]
        if result.suggested_workflows:
            lines.append(f"Workflows suggérés: {', '.join(result.suggested_workflows)}")
        if result.urgency in ("high", "critical"):
            lines.append(f"⚡ URGENCE: {result.urgency.upper()} — Priorise la résolution immédiate.")
        return "\n".join(lines)

    def batch_route(self, questions: List[str]) -> List[N3RoutingResult]:
        """Route multiple questions at once."""
        return [self.route(q) for q in questions]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SINGLETON + QUICK HELPER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

n3_router = N3QuestionRouter()


def route_question(question: str, context: Optional[Dict] = None) -> N3RoutingResult:
    """Quick helper for chatbot_service.py."""
    return n3_router.route(question, context)


def get_routing_hint(question: str) -> str:
    """
    Returns just the system prompt hint for a question.
    Empty string if no routing hint available.
    For quick injection in build_system_prompt().
    """
    result = n3_router.route(question)
    return n3_router.get_system_prompt_addon(result)
