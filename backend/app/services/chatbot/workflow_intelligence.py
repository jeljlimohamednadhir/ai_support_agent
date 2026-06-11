"""
workflow_intelligence.py
━━━━━━━━━━━━━━━━━━━━━━━━
Workflow Intelligence Engine — Phase 4

Infers operational workflows from:
  - FR knowledge (procedure steps)
  - Source code controller/service call chains
  - State machine transitions
  - Validation sequences

Supports questions like:
  - "Comment créer un VLAN ?"
  - "Comment supprimer un équipement ?"
  - "Quelles sont les étapes de déploiement d'un DSLAM ?"
  - "Quel est le workflow de modification d'un port ?"

Design rules:
  - NEVER hallucinate workflow steps
  - If workflow unknown → explicit uncertainty message
  - Steps come ONLY from indexed FR procedures or code analysis
  - IHM navigation paths are marked as UNVERIFIED unless from FR
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# WORKFLOW STEP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class WorkflowStep:
    """A single step in an operational workflow."""
    index: int
    description: str
    source: str                          # "FR", "code", "inferred"
    source_ref: Optional[str] = None     # FR ID, Java class, etc.
    validated: bool = True               # False = inferred, not from index
    condition: Optional[str] = None      # Blocking condition for this step
    technical_detail: Optional[str] = None  # Java method / SQL / config key

    def render(self) -> str:
        unvalidated = " ⚠️_[non validé]_" if not self.validated else ""
        line = f"{self.index}. {self.description}{unvalidated}"
        if self.technical_detail:
            line += f"\n   _→ `{self.technical_detail}`_"
        if self.condition:
            line += f"\n   ⚠️ Condition: _{self.condition}_"
        return line


@dataclass
class Workflow:
    """A complete operational workflow."""
    name: str
    operation: str                        # delete_equipment, create_vlan, ...
    entity: Optional[str]                 # DSLAM, VLAN, Port, ...
    steps: List[WorkflowStep] = field(default_factory=list)
    source: str = "unknown"              # "FR" | "code" | "hybrid" | "unknown"
    fr_id: Optional[str] = None
    confidence: float = 0.0
    uncertainty_message: Optional[str] = None

    @property
    def is_validated(self) -> bool:
        return self.source in ("FR", "code", "hybrid") and self.confidence >= 0.5

    def render(self) -> str:
        if not self.steps and self.uncertainty_message:
            return (
                f"🧩 **Workflow** — {self.name}\n\n"
                f"⚠️ {self.uncertainty_message}"
            )
        lines = [f"🧩 **Workflow** — {self.name}"]
        if self.fr_id:
            lines.append(f"_Source: {self.source} — {self.fr_id}_")
        elif self.source != "unknown":
            lines.append(f"_Source: {self.source}_")
        lines.append("")
        for step in self.steps:
            lines.append(step.render())
        if not self.is_validated:
            lines.append("")
            lines.append("⚠️ _Ce workflow est basé sur une analyse du code source et n'a pas été validé par une FR._")
        return "\n".join(lines)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STATIC WORKFLOW REGISTRY
# (Built from FR analysis + code graph — updated manually when FRs are added)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Format: operation_key → Workflow
_WORKFLOW_REGISTRY: Dict[str, Workflow] = {

    "delete_dslam": Workflow(
        name="Suppression d'un DSLAM",
        operation="delete_equipment",
        entity="DSLAM",
        source="code",
        confidence=0.85,
        steps=[
            WorkflowStep(1, "Vérifier l'absence de services actifs sur le DSLAM", source="code",
                         technical_detail="ManageDslamBusinessImpl.checkProductionInfoIsPresent()",
                         condition="Si services actifs → suppression bloquée"),
            WorkflowStep(2, "Contrôler les dépendances MRT", source="code",
                         technical_detail="ManageDslamBusinessImpl.checkMrtDependencies()"),
            WorkflowStep(3, "Vérifier l'absence de données résiduelles en base", source="code",
                         technical_detail="SELECT count(*) FROM t_mrt_access_dslams WHERE a_eqpt_id = ?"),
            WorkflowStep(4, "Lancer la suppression via le service métier", source="code",
                         technical_detail="ManageDslamBusinessImpl.deleteDslam()"),
            WorkflowStep(5, "Confirmer la suppression en base (t_equipments)", source="code",
                         technical_detail="SELECT * FROM t_equipments WHERE eqpt_name = ?"),
            WorkflowStep(6, "Vérifier le retrait des ressources associées (cartes, ports, VLANs)", source="code"),
        ],
    ),

    "create_vlan": Workflow(
        name="Création d'un VLAN",
        operation="create_vlan",
        entity="VLAN",
        source="code",
        confidence=0.85,
        steps=[
            WorkflowStep(1, "Vérifier les paramètres d'entrée (numéro de châssis, type de VLAN)", source="code",
                         technical_detail="ManageCreationVlanBusinessImpl.checkInputs()",
                         condition="Si numéro de châssis null → ConnectorCreationVlanException"),
            WorkflowStep(2, "Contrôler la disponibilité du VLAN sur le châssis", source="code",
                         technical_detail="ManageVlanBusinessImpl.checkVlanAvailability()"),
            WorkflowStep(3, "Créer le VLAN via le connecteur", source="code",
                         technical_detail="ManageCreationVlanBusinessImpl.creerVlan()"),
            WorkflowStep(4, "Générer le rapport de création en masse si applicable", source="code",
                         technical_detail="FileManager.writeRapportMassCreateVlan()"),
            WorkflowStep(5, "Enregistrer le VLAN en base (t_res_prod_controlables)", source="code",
                         technical_detail="ManageVlanBusinessImpl.createVlan()"),
        ],
    ),

    "delete_equipment": Workflow(
        name="Suppression d'un équipement générique",
        operation="delete_equipment",
        entity=None,
        source="code",
        confidence=0.75,
        steps=[
            WorkflowStep(1, "Identifier le type d'équipement (DSLAM, MSAN, OLT, ...)", source="code"),
            WorkflowStep(2, "Vérifier les services actifs et dépendances", source="code",
                         condition="Présence de services actifs → blocage"),
            WorkflowStep(3, "Contrôler les contraintes métier (MRT, EPT, ...)", source="code"),
            WorkflowStep(4, "Supprimer via le service métier approprié", source="code"),
            WorkflowStep(5, "Confirmer la suppression en base", source="code"),
        ],
    ),

    "create_equipment": Workflow(
        name="Création d'un équipement",
        operation="create_equipment",
        entity=None,
        source="code",
        confidence=0.7,
        steps=[
            WorkflowStep(1, "Valider les paramètres de création (type, localisation, modèle)", source="code"),
            WorkflowStep(2, "Vérifier la disponibilité du slot/châssis", source="code"),
            WorkflowStep(3, "Créer l'équipement via le service métier", source="code"),
            WorkflowStep(4, "Provisionner les ressources initiales", source="code"),
            WorkflowStep(5, "Enregistrer en base (t_equipments)", source="code"),
        ],
    ),

    "replay_order": Workflow(
        name="Rejeu d'une commande bloquée",
        operation="replay_order",
        entity=None,
        source="code",
        confidence=0.7,
        steps=[
            WorkflowStep(1, "Identifier l'ND/commande bloquée", source="code"),
            WorkflowStep(2, "Analyser la cause du blocage (logs, DB)", source="code"),
            WorkflowStep(3, "Corriger la cause racine (données résiduelles, verrou, ...)", source="code"),
            WorkflowStep(4, "Rejouer la commande via l'IHM Brasil ou le service de rejeu", source="code",
                         validated=False),
            WorkflowStep(5, "Vérifier le résultat en base et dans les logs", source="code"),
        ],
    ),

    # ── Extended workflows (EPC/UMI, MakingFile, ES Script, etc.) ──────────

    "umi_epc_create": Workflow(
        name="Création EPC/UMI (provisioning)",
        operation="create",
        entity="epc",
        source="code",
        confidence=0.75,
        steps=[
            WorkflowStep(1, "Valider les paramètres UMI (ID, type, ND, service associé)", source="code",
                         technical_detail="UmiEpcBusinessImpl.validateCreateInputs()"),
            WorkflowStep(2, "Vérifier l'état du ND destinataire (doit être ACTIVE)", source="code",
                         condition="ND en anomalie → création bloquée"),
            WorkflowStep(3, "Envoyer le message MQ de provisioning", source="code",
                         technical_detail="UmiEpcMqSender.sendCreateRequest()",
                         condition="Broker MQ doit être accessible"),
            WorkflowStep(4, "Attendre l'ACK MQ (délai max 30s)", source="code",
                         condition="ACK absent → boucle de retry → DLQ si 3 échecs"),
            WorkflowStep(5, "Créer l'entrée en base (t_epc, epcv_currentstate = IN_PROGRESS)", source="code",
                         technical_detail="INSERT INTO t_epc ..."),
            WorkflowStep(6, "Exécuter le script ES si requis (t_tp_es_scripts)", source="code",
                         condition="Si es_required = true → attendre es_state = 4 (DONE)"),
            WorkflowStep(7, "Mettre à jour l'état EPC → CONFIGURED/ACTIVE", source="code",
                         technical_detail="UPDATE t_epc SET epcv_currentstate = 'CONFIGURED'"),
            WorkflowStep(8, "Notifier ORCHESTRA via MQ", source="code"),
            WorkflowStep(9, "Vérifier cohérence finale (DB = réseau = ORCHESTRA)", source="code"),
        ],
    ),

    "umi_epc_modify": Workflow(
        name="Modification EPC/UMI",
        operation="modify",
        entity="epc",
        source="code",
        confidence=0.70,
        steps=[
            WorkflowStep(1, "Vérifier l'état actuel de l'EPC (doit être ACTIVE ou CONFIGURED)", source="code",
                         condition="EPC en IN_PROGRESS → modification bloquée"),
            WorkflowStep(2, "Passer l'EPC en état IN_PROGRESS (verrou FSM)", source="code",
                         technical_detail="UPDATE t_epc SET epcv_currentstate = 'IN_PROGRESS'"),
            WorkflowStep(3, "Créer le mouvement (createMovement)", source="code",
                         technical_detail="UmiEpcBusinessImpl.createMovement()"),
            WorkflowStep(4, "Appliquer les modifications (MQ + scripts ES si requis)", source="code"),
            WorkflowStep(5, "Compléter le mouvement (completeMovement)", source="code",
                         technical_detail="UmiEpcBusinessImpl.completeMovement()"),
            WorkflowStep(6, "Remettre l'EPC à l'état ACTIVE", source="code"),
            WorkflowStep(7, "Synchroniser ORCHESTRA et 42C", source="code"),
        ],
    ),

    "umi_epc_delete": Workflow(
        name="Suppression EPC/UMI",
        operation="delete",
        entity="epc",
        source="code",
        confidence=0.70,
        steps=[
            WorkflowStep(1, "Vérifier l'état de l'EPC (ne doit pas être IN_PROGRESS)", source="code",
                         condition="EPC en mouvement → suppression bloquée"),
            WorkflowStep(2, "Vérifier absence de services actifs liés à l'EPC", source="code",
                         technical_detail="SELECT count(*) FROM t_services WHERE epc_id = ? AND svc_status != 'S'"),
            WorkflowStep(3, "Envoyer demande de suppression MQ", source="code"),
            WorkflowStep(4, "Attendre ACK et confirmation réseau", source="code"),
            WorkflowStep(5, "Supprimer l'EPC en base", source="code",
                         technical_detail="DELETE FROM t_epc WHERE epc_id = ?"),
            WorkflowStep(6, "Nettoyer les ressources associées (scripts ES, VLANs orphelins)", source="code"),
        ],
    ),

    "making_file_lifecycle": Workflow(
        name="Cycle de vie MakingFile (0→5)",
        operation="provision",
        entity="making_file",
        source="code",
        confidence=0.80,
        steps=[
            WorkflowStep(1, "État 0 — CREATED: MakingFile créé, ressources non allouées", source="code",
                         technical_detail="INSERT INTO t_making_file (mkfl_state=0)"),
            WorkflowStep(2, "État 1 — ALLOCATED: Ressources réservées (ports, VLANs, DSLAMs)", source="code"),
            WorkflowStep(3, "État 2 — IN_PROGRESS: Configuration en cours", source="code",
                         condition="Si script ES requis → attendre es_state=4 avant de progresser"),
            WorkflowStep(4, "État 3 — PARTLY_CONFIGURED: Configuration partielle", source="code",
                         condition="Blocage ici = script ES en erreur OU ACK MQ manquant"),
            WorkflowStep(5, "État 4 — CONFIGURED: Toutes les ressources configurées", source="code"),
            WorkflowStep(6, "État 5 — AVP: Acceptation, workflow terminé", source="code"),
            WorkflowStep(7, "En cas de blocage: vérifier t_tp_es_scripts, MQ ACK, et logs provisioning", source="code",
                         validated=False),
        ],
    ),

    "es_script_unblock": Workflow(
        name="Déblocage d'un script ES",
        operation="unblock",
        entity="es_script",
        source="code",
        confidence=0.75,
        steps=[
            WorkflowStep(1, "Identifier le script bloqué: SELECT * FROM t_tp_es_scripts WHERE es_state IN (1,2)", source="code",
                         technical_detail="SELECT es_id, es_state, es_result, es_dslam FROM t_tp_es_scripts WHERE es_state IN (1,2)"),
            WorkflowStep(2, "Analyser l'erreur: es_result et es_error_message", source="code"),
            WorkflowStep(3, "Si es_state=1 (RUNNING trop longtemps): vérifier si process vivant côté réseau", source="code",
                         condition="Timeout > 1h → considérer comme bloqué"),
            WorkflowStep(4, "Si es_state=2 (ERROR): identifier la cause racine dans les logs", source="code"),
            WorkflowStep(5, "Corriger la cause (ressource manquante, param invalide, accès réseau)", source="code"),
            WorkflowStep(6, "Relancer le script: UPDATE t_tp_es_scripts SET es_state=1 WHERE es_id=?", source="code",
                         validated=False,
                         condition="Uniquement après correction de la cause"),
            WorkflowStep(7, "Attendre es_state=4 (DONE) et vérifier la suite du MakingFile", source="code"),
        ],
    ),

    "vlan_delete": Workflow(
        name="Suppression d'un VLAN",
        operation="delete",
        entity="vlan",
        source="code",
        confidence=0.72,
        steps=[
            WorkflowStep(1, "Vérifier que le VLAN n'est plus utilisé (pas de connecteurs actifs)", source="code",
                         technical_detail="SELECT count(*) FROM t_connectors WHERE vlan_id=? AND conn_status!='S'"),
            WorkflowStep(2, "Vérifier absence de services actifs sur ce VLAN", source="code"),
            WorkflowStep(3, "Supprimer les connecteurs résiduels si présents", source="code",
                         condition="Connecteurs orphelins → supprimer avant VLAN"),
            WorkflowStep(4, "Supprimer le VLAN via le service métier", source="code",
                         technical_detail="ManageVlanBusinessImpl.deleteVlan()"),
            WorkflowStep(5, "Confirmer suppression en base (t_vlan)", source="code",
                         technical_detail="SELECT * FROM t_vlan WHERE vlan_id=? — doit être vide"),
        ],
    ),

    "nd_mutation_42c": Workflow(
        name="Mutation ND / affectation 42C",
        operation="modify",
        entity="nd",
        source="code",
        confidence=0.68,
        steps=[
            WorkflowStep(1, "Vérifier l'état du ND dans BRASIL (t_nd_infra)", source="code",
                         technical_detail="SELECT nd_id, nd_status, nd_42c_id FROM t_nd_infra WHERE nd_name=?"),
            WorkflowStep(2, "Vérifier la cohérence avec 42C (l'ID doit correspondre)", source="code",
                         condition="Si désynchronisation → procédure de réconciliation requise"),
            WorkflowStep(3, "Lancer la mutation via AffectationManager", source="code",
                         technical_detail="AffectationManager.mutateDslam42c()",
                         condition="42C doit être accessible"),
            WorkflowStep(4, "Attendre la confirmation 42C (ACK ou callback)", source="code"),
            WorkflowStep(5, "Mettre à jour t_mrt_access_dslams avec le nouveau ND", source="code"),
            WorkflowStep(6, "Vérifier la cohérence finale BRASIL/42C", source="code",
                         validated=False),
        ],
    ),

    "partial_rollback_recovery": Workflow(
        name="Récupération après rollback partiel",
        operation="recover",
        entity=None,
        source="code",
        confidence=0.65,
        steps=[
            WorkflowStep(1, "Identifier les tables affectées par le rollback (logs + DB audit)", source="code",
                         technical_detail="Vérifier: t_equipments, t_services, t_vlan, t_epc, t_making_file"),
            WorkflowStep(2, "Comparer l'état DB avec l'état attendu (avant l'opération)", source="code"),
            WorkflowStep(3, "Identifier les enregistrements orphelins créés partiellement", source="code",
                         technical_detail="SELECT * FROM t_services WHERE svc_eqpt_id NOT IN (SELECT eqpt_id FROM t_equipments)"),
            WorkflowStep(4, "Supprimer les données résiduelles dans l'ordre FK correct", source="code",
                         condition="Respecter l'ordre: services → VLAN → EPC → équipement"),
            WorkflowStep(5, "Relancer l'opération originale depuis le début", source="code",
                         validated=False),
            WorkflowStep(6, "Vérifier la cohérence finale (BRASIL + 42C + ORCHESTRA)", source="code"),
        ],
    ),

    "orphan_cleanup": Workflow(
        name="Nettoyage données orphelines",
        operation="cleanup",
        entity=None,
        source="code",
        confidence=0.70,
        steps=[
            WorkflowStep(1, "Détecter les services sans équipement parent", source="code",
                         technical_detail="SELECT * FROM t_services s WHERE NOT EXISTS (SELECT 1 FROM t_equipments e WHERE e.eqpt_id = s.svc_eqpt_id)"),
            WorkflowStep(2, "Détecter les VLANs non référencés dans t_connectors", source="code",
                         technical_detail="SELECT * FROM t_vlan v WHERE NOT EXISTS (SELECT 1 FROM t_connectors c WHERE c.vlan_id = v.vlan_id)"),
            WorkflowStep(3, "Détecter les ND sans DSLAM associé", source="code",
                         technical_detail="SELECT * FROM t_nd_infra WHERE nd_id NOT IN (SELECT nd_id FROM t_mrt_access_dslams)"),
            WorkflowStep(4, "Valider manuellement chaque orphelin avant suppression", source="code",
                         condition="NE PAS automatiser — risque de suppression de données valides"),
            WorkflowStep(5, "Supprimer dans l'ordre FK (enfants avant parents)", source="code"),
            WorkflowStep(6, "Vérifier l'intégrité référentielle après nettoyage", source="code"),
        ],
    ),

    "sync_reconciliation": Workflow(
        name="Réconciliation BRASIL ↔ 42C ↔ ORCHESTRA",
        operation="reconcile",
        entity=None,
        source="code",
        confidence=0.65,
        steps=[
            WorkflowStep(1, "Identifier la source de vérité (généralement BRASIL DB)", source="code"),
            WorkflowStep(2, "Extraire l'état BRASIL pour les entités concernées", source="code",
                         technical_detail="SELECT eqpt_id, eqpt_status, eqpt_name FROM t_equipments WHERE ..."),
            WorkflowStep(3, "Comparer avec l'état 42C via l'interface de consultation", source="code",
                         validated=False),
            WorkflowStep(4, "Comparer avec l'état ORCHESTRA", source="code",
                         validated=False),
            WorkflowStep(5, "Identifier les écarts (BRASIL=A mais 42C=inconnu, etc.)", source="code"),
            WorkflowStep(6, "Appliquer la correction: resynchroniser le système déviant", source="code",
                         condition="Toujours valider manuellement avant correction"),
            WorkflowStep(7, "Relancer les workflows suspendus une fois la cohérence rétablie", source="code"),
        ],
    ),

    "mrt_activation": Workflow(
        name="Activation service MRT",
        operation="create",
        entity="mrt",
        source="code",
        confidence=0.65,
        steps=[
            WorkflowStep(1, "Vérifier la disponibilité du lien MRT (t_media_links)", source="code",
                         technical_detail="SELECT mdlk_id, mdlk_status FROM t_media_links WHERE mdlk_name=?"),
            WorkflowStep(2, "Vérifier les DSLAMs des deux extrémités du lien", source="code",
                         condition="Les deux équipements doivent être en statut A (ACTIVE)"),
            WorkflowStep(3, "Créer le service MRT via ManageMrtBusinessImpl", source="code",
                         technical_detail="ManageMrtBusinessImpl.createMrtService()"),
            WorkflowStep(4, "Provisionner le lien côté réseau (MQ + script ES)", source="code"),
            WorkflowStep(5, "Vérifier l'état final dans t_mrt_access_dslams", source="code"),
        ],
    ),

    "tp_creation": Workflow(
        name="Création d'un TP (travaux de provisioning)",
        operation="create",
        entity="tp",
        source="code",
        confidence=0.65,
        steps=[
            WorkflowStep(1, "Créer le TP avec état 1 (EN_COURS)", source="code",
                         technical_detail="INSERT INTO t_tp (tp_state=1, tp_type=...)"),
            WorkflowStep(2, "Associer les scripts ES requis (t_tp_es_scripts)", source="code"),
            WorkflowStep(3, "Exécuter les scripts ES (es_state passe 1→4)", source="code",
                         condition="Si es_state=2 (ERROR) → corriger avant de continuer"),
            WorkflowStep(4, "Valider les résultats des scripts", source="code"),
            WorkflowStep(5, "Passer le TP à l'état 2 (EXÉCUTÉ) si tout OK, ou 3 (ERREUR)", source="code",
                         technical_detail="UPDATE t_tp SET tp_state=2 WHERE tp_id=?"),
            WorkflowStep(6, "Déclencher les actions post-TP (provisioning suite, MQ, ORCHESTRA)", source="code"),
        ],
    ),
}

# Synonym mapping for entity/operation lookup
_OPERATION_SYNONYMS: Dict[str, str] = {
    "supprimer": "delete", "suppression": "delete", "effacer": "delete",
    "retirer": "delete", "enlever": "delete",
    "créer": "create", "creation": "create", "creer": "create", "ajouter": "create",
    "modifier": "modify", "modification": "modify", "changer": "modify",
    "rejouer": "replay", "relancer": "replay", "replay": "replay",
    "déployer": "deploy", "deployer": "deploy", "provisionner": "provision",
}

_ENTITY_SYNONYMS: Dict[str, str] = {
    "dslam": "dslam", "msan": "dslam",
    "vlan": "vlan",
    "équipement": "equipment", "equipement": "equipment", "equip": "equipment",
    "port": "port", "carte": "card", "card": "card",
    "epc": "epc", "umi": "epc", "epcv": "epc",
    "makingfile": "making_file", "making_file": "making_file", "making file": "making_file",
    "script es": "es_script", "es_script": "es_script", "script": "es_script",
    "nd": "nd", "noeud": "nd", "nœud": "nd", "node": "nd",
    "mrt": "mrt", "media link": "mrt", "lien mrt": "mrt",
    "tp": "tp", "travaux": "tp",
    "orphan": "orphan", "orphelin": "orphan", "résiduel": "orphan",
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# WORKFLOW INTELLIGENCE ENGINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class WorkflowIntelligenceEngine:
    """
    Resolves operational workflows from user questions.

    Usage:
        wf = workflow_engine.resolve("comment supprimer un DSLAM ?")
        if wf:
            response = wf.render()
    """

    def resolve(self, query: str, operation: Optional[str] = None,
                entity: Optional[str] = None) -> Optional[Workflow]:
        """
        Resolve a workflow from a user query.
        Returns the best matching Workflow or None.
        """
        op = operation or self._detect_operation(query)
        ent = entity or self._detect_entity(query)
        if isinstance(ent, str) and ent:
            ent_l = ent.lower().strip()
            ent = _ENTITY_SYNONYMS.get(ent_l, ent_l)

        # EPC/UMI special routing — keys use 'umi_epc_X' not 'X_epc'
        if ent == "epc":
            epc_key_map = {
                "create":  "umi_epc_create",
                "modify":  "umi_epc_modify",
                "delete":  "umi_epc_delete",
            }
            if op and op in epc_key_map:
                return _WORKFLOW_REGISTRY.get(epc_key_map[op])

        # ES script special routing
        if ent == "es_script":
            if op in ("unblock", "fix", "debug", "repair", None):
                return _WORKFLOW_REGISTRY.get("es_script_unblock")

        # Making file routing
        if ent == "making_file":
            return _WORKFLOW_REGISTRY.get("making_file_lifecycle")

        # Orphan/cleanup routing
        if ent == "orphan" or op == "cleanup":
            return _WORKFLOW_REGISTRY.get("orphan_cleanup")

        # Try specific entity+operation key first
        if op and ent:
            key = f"{op}_{ent}"
            if key in _WORKFLOW_REGISTRY:
                return _WORKFLOW_REGISTRY[key]

        # Try generic operation
        if op:
            generic_key = f"{op}_equipment"
            if generic_key in _WORKFLOW_REGISTRY:
                return _WORKFLOW_REGISTRY[generic_key]
            for k, wf in _WORKFLOW_REGISTRY.items():
                if k.startswith(op):
                    return wf

        # Try by entity only
        if ent:
            for k, wf in _WORKFLOW_REGISTRY.items():
                if ent in k:
                    return wf

        return None

    def resolve_or_unknown(self, query: str, operation: Optional[str] = None,
                           entity: Optional[str] = None) -> Workflow:
        """
        Like resolve() but always returns a Workflow.
        Returns an uncertainty workflow if not found.
        """
        wf = self.resolve(query, operation, entity)
        if wf:
            return wf

        op = operation or self._detect_operation(query) or "?"
        ent = entity or self._detect_entity(query) or "?"
        return Workflow(
            name=f"{op} {ent}".strip(),
            operation=op,
            entity=ent,
            source="unknown",
            confidence=0.0,
            uncertainty_message=(
                f"Workflow pour `{op} {ent}` non indexé.\n"
                f"Les étapes exactes ne peuvent pas être déterminées sans FR ou analyse de code.\n"
                f"Consultez la base de connaissance ou soumettez un diagnostic avec l'entité concernée."
            ),
        )

    def get_all_operations(self) -> List[str]:
        return list(_WORKFLOW_REGISTRY.keys())

    def render_workflow_response(self, query: str, operation: Optional[str] = None,
                                 entity: Optional[str] = None) -> str:
        """
        Generate a complete workflow response string for a user query.
        """
        wf = self.resolve_or_unknown(query, operation, entity)
        return wf.render()

    # ── Private helpers ───────────────────────────────────────────────

    def _detect_operation(self, query: str) -> Optional[str]:
        q_lower = query.lower()
        for fr_word, en_op in _OPERATION_SYNONYMS.items():
            if fr_word in q_lower:
                return en_op
        return None

    def _detect_entity(self, query: str) -> Optional[str]:
        q_lower = query.lower()
        for fr_word, en_ent in _ENTITY_SYNONYMS.items():
            if fr_word in q_lower:
                return en_ent
        return None

    def add_workflow(self, key: str, workflow: Workflow) -> None:
        """Register a new workflow at runtime (e.g. from FR analysis)."""
        _WORKFLOW_REGISTRY[key] = workflow
        logger.info(f"[WorkflowIntelligence] Registered workflow: {key}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SINGLETON
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

workflow_engine = WorkflowIntelligenceEngine()
