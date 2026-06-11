"""
business_rule_engine.py
━━━━━━━━━━━━━━━━━━━━━━━
Executable Business Rule Engine — N3 Layer

Gap corrected: the previous architecture stored business rules as static strings
in PERSONA_INSTRUCTION / log_patterns / resolution_engine. The LLM was expected
to "reason" from those strings. That is retrieval, NOT reasoning.

This engine evaluates business rules DETERMINISTICALLY from structured DB evidence
BEFORE the LLM is called. The LLM receives a pre-computed constraint verdict,
not raw DB counts.

Architecture:
  Rule = {condition: Callable[[EvidenceContext], bool], ...}
  Engine.evaluate(intent, evidence_context) → RuleEvaluationResult

Rules defined here are the actual executable BRASIL business constraints extracted
from Java validator source analysis:
  - EquipementService.validateDeletion()
  - VlanService.validateDeletion()
  - NdService.validateMutation()
  - PortService.validateAttribution()
  - SynchronisationService.validateSync()
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EVIDENCE CONTEXT
# Normalised view of DB + log evidence fed to rule conditions.
# The LLM NEVER sees raw DB results — only this projection.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class EvidenceContext:
    """Structured projection of live DB + log evidence.

    Fields are set by the diagnostic planner from DbEvidence/LogEvidence.
    All fields are Optional — the rule evaluator handles None gracefully.
    """
    # Equipment
    eqpt_status: Optional[str] = None          # 'A', 'F', 'P', 'C', 'S', ...
    eqpt_type:   Optional[str] = None          # 'DSLAM', 'OLT', 'ROUTER', ...
    eqpt_id:     Optional[str] = None

    # Active services on this equipment
    active_services_count: Optional[int] = None
    active_service_statuses: List[str] = field(default_factory=list)

    # MRT / link data
    active_links_count: Optional[int] = None
    link_statuses: List[str] = field(default_factory=list)

    # Cards
    active_cards_count: Optional[int] = None

    # VLAN-specific
    vlan_status: Optional[str] = None
    vlan_attached_resources: Optional[int] = None
    vlan_orchestra_synced: Optional[bool] = None

    # ND-specific
    nd_status: Optional[str] = None
    nd_affectation_42c: Optional[bool] = None

    # Port-specific
    port_attribuable: Optional[bool] = None
    port_broche_status: Optional[str] = None

    # Sync state
    mq_ack_present: Optional[bool] = None       # True = MQ ACK received
    orchestra_status: Optional[str] = None      # status in ORCHESTRA

    # Log evidence
    detected_exceptions: List[str] = field(default_factory=list)
    detected_error_codes: List[str] = field(default_factory=list)
    log_mentions_entity: bool = False

    # Arbitrary extra fields (from DB query results)
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_db_evidence(cls, db_evidence: Any, log_evidence: Any = None) -> "EvidenceContext":
        """Build EvidenceContext from live_diagnostics DiagnosticBundle."""
        ctx = cls()
        try:
            # DB evidence
            if db_evidence and hasattr(db_evidence, 'rows'):
                rows = db_evidence.rows or []
                for row in rows:
                    if isinstance(row, dict):
                        if 'eqpt_status' in row:
                            ctx.eqpt_status = str(row['eqpt_status']).strip()
                        if 'eqpt_type' in row:
                            ctx.eqpt_type = str(row.get('eqpt_type', '')).strip()
                        if 'eqpt_id' in row:
                            ctx.eqpt_id = str(row['eqpt_id'])
                        if 'vlan_status' in row:
                            ctx.vlan_status = str(row['vlan_status']).strip()
                        if 'nd_status' in row:
                            ctx.nd_status = str(row['nd_status']).strip()
                        if 'svc_status' in row:
                            ctx.active_service_statuses.append(str(row['svc_status']))
                        if 'mdlk_status' in row:
                            ctx.link_statuses.append(str(row['mdlk_status']))

                # Aggregate
                ctx.active_services_count = len([
                    s for s in ctx.active_service_statuses if s not in ('C', 'S')
                ])
                ctx.active_links_count = len([
                    l for l in ctx.link_statuses if l not in ('S',)
                ])

            # Log evidence
            if log_evidence and hasattr(log_evidence, 'error_codes'):
                ctx.detected_error_codes = list(log_evidence.error_codes or [])
            if log_evidence and hasattr(log_evidence, 'exceptions'):
                ctx.detected_exceptions = list(log_evidence.exceptions or [])

        except Exception as e:
            logger.warning(f"[BRE] EvidenceContext.from_db_evidence failed: {e}")
        return ctx


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RULE DEFINITIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class BusinessRule:
    """A single executable BRASIL business constraint."""
    rule_id: str
    description: str
    intents: List[str]              # which intents this rule applies to
    condition: Callable[[EvidenceContext], bool]  # True = rule BLOCKS the action
    blocking: bool = True           # if True, action is blocked; if False, it's a warning
    fr_id: Optional[str] = None     # backing FR document
    message: str = ""               # human-readable blocking message
    corrective_action: str = ""     # what to do to unblock


# Actual extracted BRASIL business rules
BRASIL_BUSINESS_RULES: List[BusinessRule] = [

    # ── Equipment Deletion Rules ──────────────────────────────────────────────

    BusinessRule(
        rule_id="EQPT_DEL_001",
        description="Suppression impossible: services actifs liés à l'équipement",
        intents=["delete_equipment", "force_delete_equipment", "equipment_stuck_state"],
        condition=lambda c: (c.active_services_count or 0) > 0,
        blocking=True,
        fr_id="FR-DSLAM-DELETION-189",
        message=(
            "🔴 **RÈGLE MÉTIER BLOQUANTE — EQPT_DEL_001**\n"
            "La suppression est **impossible** car {active_services_count} service(s) actif(s) "
            "sont encore liés à cet équipement (statut non-clôturé).\n"
            "Colonnes vérifiées: `t_services.svc_status NOT IN ('C','S')`"
        ),
        corrective_action=(
            "1. Clôturer tous les services actifs (`t_services`) liés à cet équipement\n"
            "2. Vérifier `t_mrtdslam` pour les liens MRT résiduels\n"
            "3. Relancer la suppression depuis l'IHM BRASIL\n"
            "📋 Référence: FR-DSLAM-DELETION-189"
        ),
    ),

    BusinessRule(
        rule_id="EQPT_DEL_002",
        description="Suppression impossible: liens MRT/media actifs",
        intents=["delete_equipment", "force_delete_equipment"],
        condition=lambda c: (c.active_links_count or 0) > 0,
        blocking=True,
        fr_id="FR-DSLAM-DELETION-189",
        message=(
            "🔴 **RÈGLE MÉTIER BLOQUANTE — EQPT_DEL_002**\n"
            "{active_links_count} lien(s) MRT/media non-supprimé(s) empêchent la suppression.\n"
            "Colonnes vérifiées: `t_media_links.mdlk_status != 'S'`"
        ),
        corrective_action=(
            "1. Supprimer les liens MRT via l'IHM BRASIL (onglet Liens)\n"
            "2. Vérifier `t_mrtdslam` et `t_media_links`\n"
            "📋 Référence: FR-DSLAM-DELETION-189"
        ),
    ),

    BusinessRule(
        rule_id="EQPT_DEL_003",
        description="Suppression impossible: équipement en statut fermé (F)",
        intents=["delete_equipment"],
        condition=lambda c: c.eqpt_status == 'F',
        blocking=True,
        fr_id="FR-NOEUD-IP-ABSENT-1300",
        message=(
            "🔴 **RÈGLE MÉTIER BLOQUANTE — EQPT_DEL_003**\n"
            "L'équipement est en statut `F` (Fermé à la production).\n"
            "La suppression nécessite une procédure de réouverture préalable."
        ),
        corrective_action=(
            "1. Vérifier la raison de la fermeture (erreur 1300 dans les logs ?)\n"
            "2. Appliquer la procédure de réouverture si justifiée\n"
            "📋 Référence: FR-NOEUD-IP-ABSENT-1300"
        ),
    ),

    BusinessRule(
        rule_id="EQPT_DEL_004",
        description="Avertissement: équipement en cours de configuration",
        intents=["delete_equipment", "check_status"],
        condition=lambda c: c.eqpt_status in ('P', 'EN_COURS', 'PENDING'),
        blocking=False,  # Warning only
        message=(
            "⚠️ **AVERTISSEMENT — EQPT_DEL_004**\n"
            "L'équipement est en statut transitoire `{eqpt_status}` (configuration en cours).\n"
            "La suppression peut échouer si un workflow est en attente de confirmation."
        ),
        corrective_action=(
            "1. Attendre la fin du workflow de configuration en cours\n"
            "2. Vérifier les logs pour un ACK MQ manquant\n"
            "3. Si bloqué depuis > 30min: escalader en N3"
        ),
    ),

    # ── VLAN Rules ────────────────────────────────────────────────────────────

    BusinessRule(
        rule_id="VLAN_DEL_001",
        description="Suppression VLAN impossible: ressources attachées",
        intents=["delete_vlan", "vlan_orphan_data"],
        condition=lambda c: (c.vlan_attached_resources or 0) > 0,
        blocking=True,
        fr_id="FR-VLAN-DELETION-190",
        message=(
            "🔴 **RÈGLE MÉTIER BLOQUANTE — VLAN_DEL_001**\n"
            "{vlan_attached_resources} ressource(s) attachée(s) au VLAN empêchent sa suppression."
        ),
        corrective_action=(
            "1. Désaffecter toutes les ressources du VLAN\n"
            "2. Vérifier la synchronisation avec ORCHESTRA\n"
            "📋 Référence: FR-VLAN-DELETION-190"
        ),
    ),

    BusinessRule(
        rule_id="VLAN_SYNC_001",
        description="VLAN non synchronisé avec ORCHESTRA",
        intents=["vlan_sync_issue", "create_vlan", "delete_vlan"],
        condition=lambda c: c.vlan_orchestra_synced is False,
        blocking=True,
        message=(
            "🔴 **RÈGLE MÉTIER BLOQUANTE — VLAN_SYNC_001**\n"
            "Le VLAN n'est pas synchronisé avec ORCHESTRA.\n"
            "Toute opération de suppression/modification est bloquée tant que la synchro est KO."
        ),
        corrective_action=(
            "1. Vérifier l'état de synchronisation dans ORCHESTRA\n"
            "2. Forcer une synchronisation si nécessaire (procédure N3)\n"
            "3. Vérifier les logs MQ pour les ACK manquants"
        ),
    ),

    # ── ND / Affectation Rules ─────────────────────────────────────────────────

    BusinessRule(
        rule_id="ND_AFF_001",
        description="Affectation ND bloquée par incohérence BRASIL/42C",
        intents=["mutation_request", "check_toc"],
        condition=lambda c: c.nd_affectation_42c is False,
        blocking=True,
        fr_id="FR-DSLAM-AFFECTATION-147B",
        message=(
            "🔴 **RÈGLE MÉTIER BLOQUANTE — ND_AFF_001**\n"
            "L'affectation du ND est bloquée par une incohérence entre BRASIL et 42C.\n"
            "Code erreur attendu: 42C / AffectationException"
        ),
        corrective_action=(
            "1. Vérifier la cohérence du ND entre BRASIL et 42C\n"
            "2. Appliquer la procédure de réconciliation\n"
            "📋 Référence: FR-DSLAM-AFFECTATION-147B"
        ),
    ),

    # ── Port / Broche Rules ───────────────────────────────────────────────────

    BusinessRule(
        rule_id="PORT_ATT_001",
        description="Port non attribuable: broche non libre",
        intents=["search_port", "fix_counter"],
        condition=lambda c: c.port_attribuable is False,
        blocking=True,
        fr_id="FR-BROCHE-ERROR-1583",
        message=(
            "🔴 **RÈGLE MÉTIER BLOQUANTE — PORT_ATT_001**\n"
            "Le port/broche n'est pas attribuable.\n"
            "Erreurs attendues: 300 / 327 (BrocheSearchException)"
        ),
        corrective_action=(
            "1. Libérer la broche si elle est réservée à tort\n"
            "2. Vérifier `port_attribuable` dans `t_ports`\n"
            "📋 Référence: FR-BROCHE-ERROR-1583"
        ),
    ),

    # ── Sync / MQ Rules ──────────────────────────────────────────────────────

    BusinessRule(
        rule_id="SYNC_MQ_001",
        description="Anomalie de synchronisation: DB=ACTIVE mais MQ ACK absent",
        intents=["workflow_blocked", "workflow_stuck", "orchestration_timeout"],
        condition=lambda c: (
            c.eqpt_status in ('A', 'ACTIVE')
            and c.mq_ack_present is False
        ),
        blocking=False,
        message=(
            "⚠️ **ANOMALIE DE SYNCHRONISATION — SYNC_MQ_001**\n"
            "L'équipement est ACTIF en DB mais l'ACK MQ est absent.\n"
            "➜ Syndrome classique de désynchronisation BRASIL/ARTEMIS."
        ),
        corrective_action=(
            "1. Vérifier les dead-letter queues MQ pour les messages non consommés\n"
            "2. Vérifier les logs ARTEMIS pour les ACK manquants\n"
            "3. Forcer une re-synchronisation si nécessaire (procédure N3)"
        ),
    ),

    # ── Extended Rules ────────────────────────────────────────────────────────

    # EPC FSM Rules
    BusinessRule(
        rule_id="EPCV_FSM_001",
        description="EPC ne peut pas être modifié: état IN_PROGRESS en cours",
        intents=["modify_epc", "epc_lifecycle", "umi_epc_modify"],
        condition=lambda c: c.raw.get("epcv_currentstate") in ("IN_PROGRESS", "2", 2),
        blocking=True,
        message=(
            "🔴 **RÈGLE MÉTIER BLOQUANTE — EPCV_FSM_001**\n"
            "L'EPC est en état `IN_PROGRESS` — un mouvement est déjà en cours.\n"
            "Toute nouvelle modification est bloquée jusqu'à la fin du mouvement actuel."
        ),
        corrective_action=(
            "1. Attendre la fin du mouvement en cours (completeMovement)\n"
            "2. Si bloqué > 30 min: vérifier les logs pour un ACK MQ manquant\n"
            "3. Vérifier t_tp_es_scripts pour des scripts bloqués liés à cet EPC"
        ),
    ),

    BusinessRule(
        rule_id="EPCV_FSM_002",
        description="EPC ne peut pas être supprimé: état IN_PROGRESS",
        intents=["delete_epc", "umi_epc_delete", "epc_lifecycle"],
        condition=lambda c: c.raw.get("epcv_currentstate") in ("IN_PROGRESS", "2", 2),
        blocking=True,
        message=(
            "🔴 **RÈGLE MÉTIER BLOQUANTE — EPCV_FSM_002**\n"
            "La suppression EPC est impossible: l'EPC est en mouvement (IN_PROGRESS).\n"
            "Attendre la fin du mouvement ou annuler le mouvement en cours."
        ),
        corrective_action=(
            "1. Vérifier si le mouvement peut être annulé (cancelMovement)\n"
            "2. Si annulation impossible: attendre la fin naturelle ou escalader\n"
            "3. Vérifier les ACK MQ manquants dans les logs ARTEMIS"
        ),
    ),

    BusinessRule(
        rule_id="EPCV_FSM_003",
        description="Transition FSM EPC invalide détectée",
        intents=["epc_lifecycle", "workflow_stuck", "causal_escalation"],
        condition=lambda c: "epc_fsm_invalid_transition" in (c.detected_exceptions or []),
        blocking=True,
        message=(
            "🔴 **RÈGLE MÉTIER BLOQUANTE — EPCV_FSM_003**\n"
            "Une transition d'état invalide a été détectée sur l'EPC.\n"
            "États EPC valides: C (Créé) → M (Modifié) → X (Supprimé)."
        ),
        corrective_action=(
            "1. Identifier l'état actuel dans t_epc (epcv_currentstate)\n"
            "2. Vérifier la transition tentée dans les logs\n"
            "3. Corriger l'état manuellement si nécessaire (procédure N3 uniquement)\n"
            "⚠️ Toute modification manuelle de l'état EPC requiert validation N3"
        ),
    ),

    # MakingFile Rules
    BusinessRule(
        rule_id="MKFL_001",
        description="MakingFile bloqué en IN_PROGRESS (état 2)",
        intents=["workflow_stuck", "making_file_blocked", "provisioning_blocked"],
        condition=lambda c: c.raw.get("mkfl_state") in ("2", 2, "IN_PROGRESS"),
        blocking=True,
        message=(
            "🔴 **RÈGLE MÉTIER BLOQUANTE — MKFL_001**\n"
            "Le MakingFile est bloqué en état 2 (IN_PROGRESS).\n"
            "Cause probable: script ES bloqué ou ACK MQ absent."
        ),
        corrective_action=(
            "1. Vérifier t_tp_es_scripts pour les scripts associés (es_state=1 ou 2)\n"
            "2. Vérifier les ACK MQ en attente\n"
            "3. Si script ES bloqué: appliquer la procédure es_script_unblock\n"
            "4. Une fois débloqué: le MakingFile progressera automatiquement"
        ),
    ),

    BusinessRule(
        rule_id="MKFL_002",
        description="MakingFile en PARTLY_CONFIGURED (état 3) — configuration incomplète",
        intents=["partial_provisioning", "workflow_stuck"],
        condition=lambda c: c.raw.get("mkfl_state") in ("3", 3, "PARTLY_CONFIGURED"),
        blocking=False,
        message=(
            "⚠️ **AVERTISSEMENT — MKFL_002**\n"
            "Le MakingFile est partiellement configuré (état 3: PARTLY_CONFIGURED).\n"
            "Une ou plusieurs étapes de provisioning ont échoué ou sont incomplètes."
        ),
        corrective_action=(
            "1. Identifier quelle étape a échoué (vérifier les logs de provisioning)\n"
            "2. Corriger la ressource concernée (VLAN, port, script ES)\n"
            "3. Le MakingFile reprendra à l'étape suivante après correction"
        ),
    ),

    BusinessRule(
        rule_id="MKFL_003",
        description="MakingFile non terminé (non-AVP) depuis trop longtemps",
        intents=["workflow_stuck", "provisioning_blocked", "recurring_incident"],
        condition=lambda c: (
            c.raw.get("mkfl_state") not in ("5", 5, "AVP", None)
            and (c.raw.get("mkfl_age_hours") or 0) > 24
        ),
        blocking=False,
        message=(
            "⚠️ **AVERTISSEMENT — MKFL_003**\n"
            "Le MakingFile n'a pas atteint l'état AVP (5) depuis plus de 24h.\n"
            "État actuel: {mkfl_state} — peut indiquer un blocage prolongé."
        ),
        corrective_action=(
            "1. Analyser la séquence complète des états depuis la création\n"
            "2. Identifier l'étape bloquante (scripts ES, ACK MQ, contraintes 42C)\n"
            "3. Escalader si le blocage dépasse 48h"
        ),
    ),

    # ND Affectation Rules
    BusinessRule(
        rule_id="ND_AFF_002",
        description="ND sans DSLAM associé dans t_mrt_access_dslams",
        intents=["nd_incident", "check_nd", "orphan_detection"],
        condition=lambda c: (
            c.nd_status is not None
            and (c.raw.get("dslam_count") or 0) == 0
        ),
        blocking=False,
        message=(
            "⚠️ **AVERTISSEMENT — ND_AFF_002**\n"
            "Le ND existe en base mais aucun DSLAM n'est associé dans `t_mrt_access_dslams`.\n"
            "Ce ND peut être orphelin ou en cours d'affectation."
        ),
        corrective_action=(
            "1. Vérifier si le DSLAM a été supprimé sans désaffecter le ND\n"
            "2. Requête: SELECT * FROM t_mrt_access_dslams WHERE nd_id = ?\n"
            "3. Si orphelin confirmé: procéder au nettoyage ND"
        ),
    ),

    # VLAN Extended Rules
    BusinessRule(
        rule_id="VLAN_DEL_002",
        description="VLAN à 0 ou VLAN ID invalide sur connecteur",
        intents=["vlan_inconsistency", "create_vlan", "delete_vlan"],
        condition=lambda c: c.raw.get("vlan_id") in ("0", 0),
        blocking=True,
        message=(
            "🔴 **RÈGLE MÉTIER BLOQUANTE — VLAN_DEL_002**\n"
            "VLAN ID = 0 détecté sur un connecteur — valeur invalide.\n"
            "Cela indique une création VLAN échouée ou un rollback partiel."
        ),
        corrective_action=(
            "1. Identifier le connecteur avec VLAN=0: SELECT * FROM t_connectors WHERE vlan_id=0\n"
            "2. Vérifier l'historique de création du VLAN dans les logs\n"
            "3. Supprimer le connecteur orphelin et recréer le VLAN proprement\n"
            "⚠️ Ne pas laisser de connecteurs avec VLAN=0 en production"
        ),
    ),

    # ES Script Rules
    BusinessRule(
        rule_id="ES_SCR_001",
        description="Script ES bloqué depuis trop longtemps (es_state=1)",
        intents=["es_script_stuck", "workflow_stuck", "provisioning_blocked"],
        condition=lambda c: (
            c.raw.get("es_state") in ("1", 1, "RUNNING")
            and (c.raw.get("es_running_hours") or 0) > 1
        ),
        blocking=True,
        message=(
            "🔴 **RÈGLE MÉTIER BLOQUANTE — ES_SCR_001**\n"
            "Le script ES est en état RUNNING (1) depuis plus d'1 heure.\n"
            "Durée normale: < 15 minutes. Ce script est considéré bloqué."
        ),
        corrective_action=(
            "1. Vérifier si le process réseau est toujours actif côté équipement\n"
            "2. Consulter es_result et es_error_message dans t_tp_es_scripts\n"
            "3. Si process mort: mettre es_state=2 (ERROR) et traiter comme erreur\n"
            "4. Après correction: relancer avec es_state=1"
        ),
    ),

    # Orphan Detection Rules
    BusinessRule(
        rule_id="ORPHAN_001",
        description="Service sans équipement parent détecté",
        intents=["orphan_detection", "ghost_service", "cleanup"],
        condition=lambda c: c.raw.get("service_without_parent", False),
        blocking=False,
        message=(
            "⚠️ **AVERTISSEMENT — ORPHAN_001**\n"
            "Un ou plusieurs services existent sans équipement parent dans `t_equipments`.\n"
            "Ces services sont des données résiduelles (rollback partiel ou suppression incomplète)."
        ),
        corrective_action=(
            "1. Requête d'identification: SELECT s.* FROM t_services s "
            "WHERE NOT EXISTS (SELECT 1 FROM t_equipments e WHERE e.eqpt_id = s.svc_eqpt_id)\n"
            "2. Valider manuellement avant suppression\n"
            "3. Supprimer dans l'ordre: services → puis vérifier les dépendances"
        ),
    ),

    BusinessRule(
        rule_id="ORPHAN_002",
        description="VLAN sans connecteur associé (VLAN orphelin)",
        intents=["orphan_detection", "vlan_inconsistency", "cleanup"],
        condition=lambda c: c.raw.get("vlan_without_connector", False),
        blocking=False,
        message=(
            "⚠️ **AVERTISSEMENT — ORPHAN_002**\n"
            "Un VLAN existe dans `t_vlan` sans aucun connecteur associé dans `t_connectors`.\n"
            "Ce VLAN est potentiellement orphelin."
        ),
        corrective_action=(
            "1. Requête: SELECT v.* FROM t_vlan v "
            "WHERE NOT EXISTS (SELECT 1 FROM t_connectors c WHERE c.vlan_id = v.vlan_id)\n"
            "2. Vérifier si le VLAN est encore utilisé réseau\n"
            "3. Si confirmé orphelin: supprimer proprement"
        ),
    ),

    BusinessRule(
        rule_id="ORPHAN_003",
        description="EPC sans service actif associé (EPC fantôme)",
        intents=["orphan_detection", "ghost_service", "epc_lifecycle"],
        condition=lambda c: c.raw.get("epc_without_service", False),
        blocking=False,
        message=(
            "⚠️ **AVERTISSEMENT — ORPHAN_003**\n"
            "Un EPC existe dans `t_epc` sans service actif associé.\n"
            "Peut indiquer un provisioning incomplet ou une suppression partielle."
        ),
        corrective_action=(
            "1. Vérifier l'état de l'EPC (epcv_currentstate)\n"
            "2. Si EPC en état terminal et sans service: suppression sécurisée\n"
            "3. Si EPC en état actif sans service: investiguer le provisioning"
        ),
    ),

    # Retry Accumulation Rule
    BusinessRule(
        rule_id="RETRY_001",
        description="Seuil de retry dépassé — escalade DLQ requise",
        intents=["retry_loop", "mq_sync_failure", "workflow_stuck"],
        condition=lambda c: (c.raw.get("retry_count") or 0) >= 3,
        blocking=True,
        message=(
            "🔴 **RÈGLE MÉTIER BLOQUANTE — RETRY_001**\n"
            "Le seuil de retry ({retry_count} tentatives) a été dépassé.\n"
            "Les messages sont probablement dans la Dead Letter Queue (DLQ).\n"
            "STOP: ne pas relancer manuellement sans corriger la cause racine."
        ),
        corrective_action=(
            "1. STOP — Ne pas ajouter de nouvelles tentatives\n"
            "2. Identifier et corriger la cause racine (ACK absent, service down, data invalide)\n"
            "3. Vider la DLQ uniquement après correction confirmée\n"
            "4. Relancer le workflow depuis le début (pas depuis l'étape bloquante)"
        ),
    ),
]

# Index for fast lookup
_RULE_BY_INTENT: Dict[str, List[BusinessRule]] = {}
for _r in BRASIL_BUSINESS_RULES:
    for _i in _r.intents:
        _RULE_BY_INTENT.setdefault(_i, []).append(_r)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RULE EVALUATION RESULT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class RuleEvaluationResult:
    """Result of evaluating all applicable rules for an intent + evidence."""
    intent: str
    blocked: bool = False                          # True if ANY blocking rule fired
    fired_rules: List[BusinessRule] = field(default_factory=list)
    warning_rules: List[BusinessRule] = field(default_factory=list)
    verdict_text: str = ""                         # ready for LLM injection

    def to_context_block(self) -> dict:
        """Format as a chatbot context block for LLM injection."""
        return {
            "source": "business_rule_engine",
            "type": "constraint_verdict",
            "blocked": self.blocked,
            "text": self.verdict_text,
            "fired_rule_ids": [r.rule_id for r in self.fired_rules],
            "warning_rule_ids": [r.rule_id for r in self.warning_rules],
        }

    def render_for_user(self, evidence_ctx: "EvidenceContext") -> str:
        """Render a complete user-facing constraint verdict."""
        if not self.fired_rules and not self.warning_rules:
            return ""
        parts = []
        for rule in self.fired_rules:
            msg = rule.message.format(
                active_services_count=evidence_ctx.active_services_count or 0,
                active_links_count=evidence_ctx.active_links_count or 0,
                vlan_attached_resources=evidence_ctx.vlan_attached_resources or 0,
                eqpt_status=evidence_ctx.eqpt_status or "inconnu",
            )
            parts.append(msg)
            parts.append(f"\n📋 **Action corrective:**\n{rule.corrective_action}\n")
        for rule in self.warning_rules:
            msg = rule.message.format(
                active_services_count=evidence_ctx.active_services_count or 0,
                eqpt_status=evidence_ctx.eqpt_status or "inconnu",
            )
            parts.append(msg)
            parts.append(f"\n📋 **Recommandation:**\n{rule.corrective_action}\n")
        return "\n".join(parts)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BUSINESS RULE ENGINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class BusinessRuleEngine:
    """
    Evaluates executable BRASIL business constraints from structured evidence.

    Usage:
        from app.services.chatbot.business_rule_engine import BusinessRuleEngine, EvidenceContext
        bre = BusinessRuleEngine()
        ctx = EvidenceContext.from_db_evidence(db_ev, log_ev)
        result = bre.evaluate(intent="delete_equipment", evidence=ctx)
        if result.blocked:
            # inject result.verdict_text into LLM prompt as a HARD constraint
    """

    def evaluate(
        self,
        intent: str,
        evidence: EvidenceContext,
    ) -> RuleEvaluationResult:
        """Evaluate all applicable rules for the given intent and evidence."""
        result = RuleEvaluationResult(intent=intent)
        applicable_rules = _RULE_BY_INTENT.get(intent, [])

        for rule in applicable_rules:
            try:
                fired = rule.condition(evidence)
            except Exception as e:
                logger.debug(f"[BRE] Rule {rule.rule_id} condition error: {e}")
                fired = False

            if fired:
                if rule.blocking:
                    result.blocked = True
                    result.fired_rules.append(rule)
                else:
                    result.warning_rules.append(rule)

        result.verdict_text = self._build_verdict_text(result, evidence)
        return result

    def _build_verdict_text(
        self,
        result: RuleEvaluationResult,
        evidence: EvidenceContext,
    ) -> str:
        if not result.fired_rules and not result.warning_rules:
            return ""
        return result.render_for_user(evidence)


# Singleton
_bre_instance: Optional[BusinessRuleEngine] = None

def get_business_rule_engine() -> BusinessRuleEngine:
    global _bre_instance
    if _bre_instance is None:
        _bre_instance = BusinessRuleEngine()
    return _bre_instance
