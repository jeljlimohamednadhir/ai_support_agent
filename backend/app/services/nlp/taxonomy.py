"""
Incident Taxonomy — Complete definition of all incident types for BRASIL N3 support.
Used by the NLP enrichment layer to classify tickets.

Hierarchy:  CATEGORY → incident_type → description + patterns + causes
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class IncidentTypeDefinition:
    """Full definition of one incident type in the taxonomy."""
    id: str                        # e.g. "backend_error.api_error"
    category: str                  # e.g. "backend_error"
    name: str                      # human-readable
    description: str
    typical_patterns: List[str]    # keyword phrases found in tickets
    possible_root_causes: List[str]
    related_systems: List[str]
    severity: str = "medium"       # low | medium | high | critical


# ─────────────────────────────────────────────
# Full Taxonomy
# ─────────────────────────────────────────────

INCIDENT_TAXONOMY: Dict[str, IncidentTypeDefinition] = {

    # ── ACCESS ISSUES ───────────────────────────────────────────────────
    "access_issue.login_failure": IncidentTypeDefinition(
        id="access_issue.login_failure",
        category="access_issue",
        name="Login Failure",
        description="User cannot authenticate to the system.",
        typical_patterns=["connexion impossible", "cannot login", "mot de passe incorrect",
                          "identifiant refusé", "accès refusé", "authentification échouée"],
        possible_root_causes=["Wrong credentials", "LDAP unreachable", "Account locked",
                              "Token expired", "Session timeout"],
        related_systems=["BRASIL", "SEBA", "ARTEMIS", "IPON"],
        severity="medium",
    ),
    "access_issue.permission_denied": IncidentTypeDefinition(
        id="access_issue.permission_denied",
        category="access_issue",
        name="Permission Denied",
        description="User does not have the required permissions for an operation.",
        typical_patterns=["habilitation manquante", "rôle non attribué", "accès refusé",
                          "non autorisé", "permission denied", "403", "droit manquant"],
        possible_root_causes=["Role not assigned in LDAP", "Profile misconfiguration",
                              "Permission propagation delay"],
        related_systems=["BRASIL", "ADELIA"],
        severity="medium",
    ),
    "access_issue.account_locked": IncidentTypeDefinition(
        id="access_issue.account_locked",
        category="access_issue",
        name="Account Locked",
        description="User account is locked after too many failed attempts.",
        typical_patterns=["compte bloqué", "compte verrouillé", "trop de tentatives",
                          "account locked"],
        possible_root_causes=["Multiple failed login attempts", "Admin lockout",
                              "Password policy enforcement"],
        related_systems=["BRASIL"],
        severity="low",
    ),

    # ── COMMAND FAILURES ────────────────────────────────────────────────
    "command_failure.command_blocked": IncidentTypeDefinition(
        id="command_failure.command_blocked",
        category="command_failure",
        name="Command Blocked",
        description="A user command/order is rejected or cannot be launched.",
        typical_patterns=["impossible de lancer", "commande bloquée", "commande impossible",
                          "lancement commande échoué", "échec lancement", "commande refusée",
                          "cannot launch", "commande en erreur"],
        possible_root_causes=["Missing prerequisites", "Status incompatibility",
                              "Integration failure BRASIL↔SEBA", "Access rights issue",
                              "Business rule violation"],
        related_systems=["BRASIL", "SEBA", "IPON"],
        severity="high",
    ),
    "command_failure.command_timeout": IncidentTypeDefinition(
        id="command_failure.command_timeout",
        category="command_failure",
        name="Command Timeout",
        description="A command execution times out before completing.",
        typical_patterns=["timeout commande", "délai dépassé", "commande bloquée en cours",
                          "script bloqué en cours d'exécution", "en attente depuis"],
        possible_root_causes=["Database lock", "Downstream system unreachable",
                              "Infinite loop in processing", "Resource contention"],
        related_systems=["BRASIL", "ORCHESTRA"],
        severity="high",
    ),
    "command_failure.unsupported_command": IncidentTypeDefinition(
        id="command_failure.unsupported_command",
        category="command_failure",
        name="Unsupported Command",
        description="The requested command is not available or not supported in current context.",
        typical_patterns=["commande non disponible", "fonctionnalité absente", "bouton grisé",
                          "option non disponible"],
        possible_root_causes=["Version mismatch", "Feature not activated", "Wrong application mode"],
        related_systems=["BRASIL", "SEBA"],
        severity="low",
    ),

    # ── DATA INCONSISTENCY ──────────────────────────────────────────────
    "data_inconsistency.mapping_error": IncidentTypeDefinition(
        id="data_inconsistency.mapping_error",
        category="data_inconsistency",
        name="Mapping Error",
        description="Equipment or resource mapping is incorrect (DSLAM, port, VC/VP).",
        typical_patterns=["erreur de mapping", "dslam mal mappé", "port incorrect",
                          "incoherence brasil terrain", "compteurs dslam", "recherche de broche en échec",
                          "broche en echec", "port_attribuable erroné"],
        possible_root_causes=["Manual provisioning error", "Sync failure between BRASIL and network equipment",
                              "Counter overflow (DSLAM at 100%)"],
        related_systems=["BRASIL"],
        severity="high",
    ),
    "data_inconsistency.synchronization_lag": IncidentTypeDefinition(
        id="data_inconsistency.synchronization_lag",
        category="data_inconsistency",
        name="Synchronization Lag",
        description="Data is out of sync between BRASIL and an interfaced system.",
        typical_patterns=["synchronisation en retard", "données non synchronisées",
                          "incohérence brasil", "mouvement bbc sans action",
                          "nœud absent dans brasil", "site présent dans référentiel absent dans brasil"],
        possible_root_causes=["Message queue failure", "Batch job delay", "Network partition",
                              "Interface timeout"],
        related_systems=["BRASIL", "SEBA", "ARTEMIS", "IPON"],
        severity="medium",
    ),
    "data_inconsistency.duplicate_record": IncidentTypeDefinition(
        id="data_inconsistency.duplicate_record",
        category="data_inconsistency",
        name="Duplicate Record",
        description="Duplicate entries exist in the database causing conflicts.",
        typical_patterns=["double déclaration", "doublon", "double accès", "réglette en double",
                          "double declaration", "correction en masse"],
        possible_root_causes=["Concurrent insertions", "Failed deduplication job",
                              "Import replay without cleanup"],
        related_systems=["BRASIL"],
        severity="medium",
    ),
    "data_inconsistency.missing_reference": IncidentTypeDefinition(
        id="data_inconsistency.missing_reference",
        category="data_inconsistency",
        name="Missing Reference",
        description="A required reference (node, site, equipment) does not exist in BRASIL.",
        typical_patterns=["nd inconnu", "nd introuvable", "nd absent", "nœud inconnu",
                          "nœud ftth", "nœud adsl", "absent dans brasil",
                          "la contrainte sur le répartiteur n'existe pas",
                          "noeud ou site présent dans référentiel absent dans brasil"],
        possible_root_causes=["Node not provisioned", "Reference data not imported",
                              "Manual deletion without cascade"],
        related_systems=["BRASIL"],
        severity="high",
    ),

    # ── NETWORK EQUIPMENT ISSUES ────────────────────────────────────────
    "network_equipment.router_issue": IncidentTypeDefinition(
        id="network_equipment.router_issue",
        category="network_equipment",
        name="Router Issue",
        description="A router is malfunctioning or needs to be deleted.",
        typical_patterns=["routeur impossible", "suppression routeur", "supprimer le routeur",
                          "bas ou routeur impossible", "routeur bloqué"],
        possible_root_causes=["Residual DB entry after physical removal", "Active service attached",
                              "Operator constraint"],
        related_systems=["BRASIL"],
        severity="medium",
    ),
    "network_equipment.dslam_error": IncidentTypeDefinition(
        id="network_equipment.dslam_error",
        category="network_equipment",
        name="DSLAM Error",
        description="DSLAM-related error: mapping, deletion, or counter overflow.",
        typical_patterns=["dslam", "suppression dslam impossible", "modifier le nœud dslam",
                          "compteurs dslam 100%", "dslam impossible", "dslam bloqué"],
        possible_root_causes=["Port counter at 100%", "Residual link in BRASIL",
                              "Wrong node association", "Physical DSLAM removed, BRASIL not updated"],
        related_systems=["BRASIL"],
        severity="high",
    ),
    "network_equipment.port_unavailable": IncidentTypeDefinition(
        id="network_equipment.port_unavailable",
        category="network_equipment",
        name="Port Unavailable",
        description="A port is occupied, blocked, or incorrectly marked as unavailable.",
        typical_patterns=["port occupé à tort", "port bloqué", "libérer les ports", "port sans service",
                          "port réseau sans service ni extrémité", "définition ports"],
        possible_root_causes=["Ghost service on port", "Incorrect counter", "Sync failure"],
        related_systems=["BRASIL"],
        severity="medium",
    ),
    "network_equipment.deletion_request": IncidentTypeDefinition(
        id="network_equipment.deletion_request",
        category="network_equipment",
        name="Equipment Deletion Request",
        description="Request to delete network equipment (router, DSLAM, card, VLAN).",
        typical_patterns=["supprimer le routeur", "suppression dslam", "suppression vlan",
                          "suppression carte", "suppression en masse", "supprimer"],
        possible_root_causes=["Equipment decommissioned", "Migration", "Provisioning error to correct"],
        related_systems=["BRASIL"],
        severity="low",
    ),

    # ── BACKEND ERRORS ──────────────────────────────────────────────────
    "backend_error.api_error": IncidentTypeDefinition(
        id="backend_error.api_error",
        category="backend_error",
        name="API Error",
        description="An API call returns an error code from BRASIL or an interfaced system.",
        typical_patterns=["erreur 4002", "b4002", "erreur brasil", "erreur 1002",
                          "erreur 1300", "code erreur", "retour erreur", "erreur interne",
                          "brasil internal error", "internal error"],
        possible_root_causes=["Invalid input parameters", "Service temporarily unavailable",
                              "Authentication token expired", "Upstream system unreachable",
                              "Business rule violation"],
        related_systems=["BRASIL", "SEBA", "ARTEMIS"],
        severity="high",
    ),
    "backend_error.database_error": IncidentTypeDefinition(
        id="backend_error.database_error",
        category="backend_error",
        name="Database Error",
        description="Database-level error (Oracle, SQL, deadlock, constraint violation).",
        typical_patterns=["ora-", "oracle", "erreur sql", "deadlock", "contrainte db",
                          "erreur base de données", "timeout bdd", "connexion oracle",
                          "tns:connect timeout"],
        possible_root_causes=["DB server unreachable", "Connection pool exhausted",
                              "Lock timeout", "Constraint violation", "Missing index"],
        related_systems=["BRASIL"],
        severity="critical",
    ),
    "backend_error.service_unavailable": IncidentTypeDefinition(
        id="backend_error.service_unavailable",
        category="backend_error",
        name="Service Unavailable",
        description="A BRASIL service or module is down or unreachable.",
        typical_patterns=["service indisponible", "service down", "hors service",
                          "connexion impossible", "service ko", "503", "500",
                          "ihm bloquée", "ihm bloquee"],
        possible_root_causes=["Application crash", "Restart in progress", "Port conflict",
                              "Memory exhaustion"],
        related_systems=["BRASIL", "ORCHESTRA"],
        severity="critical",
    ),

    # ── SYSTEM INTEGRATION PROBLEMS ────────────────────────────────────
    "system_integration.interface_failure": IncidentTypeDefinition(
        id="system_integration.interface_failure",
        category="system_integration",
        name="Interface Failure",
        description="Communication failure between BRASIL and an interfaced application.",
        typical_patterns=["interface seba", "interface ipon", "interface artemis",
                          "échange de données échoué", "webservice ko", "wsdl erreur",
                          "réponse artemis", "demandes artemis bloquées"],
        possible_root_causes=["Token expired", "SSL certificate issue", "Endpoint URL changed",
                              "Network routing issue", "Middleware down"],
        related_systems=["BRASIL", "SEBA", "ARTEMIS", "IPON", "ADELIA", "SCA", "ORCHESTRA"],
        severity="high",
    ),
    "system_integration.data_exchange_error": IncidentTypeDefinition(
        id="system_integration.data_exchange_error",
        category="system_integration",
        name="Data Exchange Error",
        description="Data sent between systems is malformed, incomplete, or rejected.",
        typical_patterns=["champ obligatoire absent", "format incorrect", "champ erroné",
                          "nifolder", "updatedmrtlist", "erreur de format",
                          "erreur brasil 1002 champ obligatoire"],
        possible_root_causes=["API contract mismatch", "Missing mandatory field",
                              "Encoding issue", "Schema version mismatch"],
        related_systems=["BRASIL", "SEBA", "ARTEMIS"],
        severity="high",
    ),
    "system_integration.message_queue_failure": IncidentTypeDefinition(
        id="system_integration.message_queue_failure",
        category="system_integration",
        name="Message Queue Failure",
        description="Messages stuck in MQ Backout or message queue failure.",
        typical_patterns=["mq backout", "message stocké en backout", "umi-dico",
                          "envoi en masse", "reprise des messages", "queue bloquée"],
        possible_root_causes=["Consumer down", "Message malformed", "Queue full",
                              "Connection to MQ broken"],
        related_systems=["BRASIL"],
        severity="high",
    ),

    # ── APPOINTMENT MANAGEMENT ──────────────────────────────────────────
    "appointment_management.appointment_blocking": IncidentTypeDefinition(
        id="appointment_management.appointment_blocking",
        category="appointment_management",
        name="Appointment Blocking",
        description="A scheduled appointment (RDV) is blocked or cannot be confirmed.",
        typical_patterns=["rdv bloqué", "rdv annulé", "blocage rdv", "avp 1300",
                          "avp blocage", "rendez-vous annulé", "impossible de prendre rdv",
                          "blocage création rendez-vous"],
        possible_root_causes=["AVP constraint not met", "Slot unavailability",
                              "Upstream BRASIL scheduling service blocked",
                              "Data inconsistency in planning module"],
        related_systems=["BRASIL"],
        severity="high",
    ),
    "appointment_management.scheduling_conflict": IncidentTypeDefinition(
        id="appointment_management.scheduling_conflict",
        category="appointment_management",
        name="Scheduling Conflict",
        description="Conflicting appointments or scheduling constraints.",
        typical_patterns=["conflit rdv", "créneau indisponible", "conflit planning",
                          "chevauchement"],
        possible_root_causes=["Double booking", "Resource constraint"],
        related_systems=["BRASIL"],
        severity="medium",
    ),

    # ── CONFIGURATION REQUESTS ──────────────────────────────────────────
    "configuration_request.deletion_request": IncidentTypeDefinition(
        id="configuration_request.deletion_request",
        category="configuration_request",
        name="Deletion Request",
        description="Request to delete or decommission an element (router, DSLAM, VLAN, card).",
        typical_patterns=["merci de supprimer", "suppression demandée", "demande de suppression",
                          "à supprimer", "désactivation", "décommissionnement"],
        possible_root_causes=["Equipment decommissioned", "Migration", "Error correction"],
        related_systems=["BRASIL"],
        severity="low",
    ),
    "configuration_request.parameter_update": IncidentTypeDefinition(
        id="configuration_request.parameter_update",
        category="configuration_request",
        name="Parameter Update",
        description="Request to update a configuration parameter.",
        typical_patterns=["mise à jour paramètre", "modifier la configuration",
                          "changer le mot de passe", "update paramètre", "maj code opérateur"],
        possible_root_causes=["Operational change", "Security policy", "Migration"],
        related_systems=["BRASIL"],
        severity="low",
    ),
    "configuration_request.equipment_provisioning": IncidentTypeDefinition(
        id="configuration_request.equipment_provisioning",
        category="configuration_request",
        name="Equipment Provisioning",
        description="Request to create or provision new network equipment in BRASIL.",
        typical_patterns=["créer réglette", "création nœud", "création réglette fictive",
                          "provisionner", "ajouter équipement"],
        possible_root_causes=["New installation", "Migration", "Replacement"],
        related_systems=["BRASIL"],
        severity="low",
    ),

    # ── VLAN / VC / VP ──────────────────────────────────────────────────
    "vlan_resource.blocked": IncidentTypeDefinition(
        id="vlan_resource.blocked",
        category="vlan_resource",
        name="VLAN/VC/VP Blocked",
        description="A VLAN, VC, or VP is occupied or blocked incorrectly.",
        typical_patterns=["vlan bloqué", "vlan occupé", "vlan impossible", "vlan occupe à tort",
                          "vc vp vlan occupé", "affectation sur ccl vc déjà occupé",
                          "problème compteurs ressources logiques", "erreur 42c"],
        possible_root_causes=["Ghost allocation", "Incorrect counter", "Sync failure",
                              "Failed rollback after error"],
        related_systems=["BRASIL"],
        severity="high",
    ),

    # ── PROVISIONING FAILURES ───────────────────────────────────────────
    "provisioning_failure": IncidentTypeDefinition(
        id="provisioning_failure",
        category="provisioning_failure",
        name="Provisioning Failure",
        description=(
            "Échec d'une commande de provisioning réseau initiée par BRASIL, "
            "impliquant un ou plusieurs systèmes aval (SEBA, ORCHESTRA, ADELIA)."
        ),
        typical_patterns=[
            "commande de provisioning bloquée", "provisioning échoué", "dslam fermé",
            "dslam closed", "ressources réseau insuffisantes", "broche en echec",
            "recherche de broche", "DslamClosedForProductionException",
            "AvailableNetworkResourcesDisallowProductionException",
            "ProvisioningTimeoutException", "ne joignable", "commande seba bloquée",
        ],
        possible_root_causes=[
            "DSLAM fermé ou en maintenance",
            "Ressources réseau insuffisantes ou saturées",
            "Timeout de communication BRASIL → SEBA",
            "Désynchronisation référentiel NE entre BRASIL et ORCHESTRA",
            "Migration réseau non finalisée",
        ],
        related_systems=["BRASIL", "SEBA", "ORCHESTRA"],
        severity="high",
    ),
    "provisioning_failure.dslam_closed": IncidentTypeDefinition(
        id="provisioning_failure.dslam_closed",
        category="provisioning_failure",
        name="DSLAM Closed for Production",
        description="Le DSLAM cible est fermé à la production, bloquant le provisioning.",
        typical_patterns=[
            "dslam fermé", "closed for production", "dslam closed", "ferme production",
            "DslamClosedForProductionException",
        ],
        possible_root_causes=[
            "DSLAM physiquement fermé pour maintenance non signalée",
            "Désynchronisation référentiel BRASIL ↔ ORCHESTRA",
            "Migration réseau non finalisée dans le référentiel",
        ],
        related_systems=["BRASIL", "SEBA", "ORCHESTRA"],
        severity="high",
    ),
    "provisioning_failure.resource_disallowed": IncidentTypeDefinition(
        id="provisioning_failure.resource_disallowed",
        category="provisioning_failure",
        name="Network Resources Disallow Production",
        description="Les ressources réseau sont insuffisantes ou bloquées sur l'équipement cible.",
        typical_patterns=[
            "ressources réseau insuffisantes", "resources disallow", "compteurs dslam saturés",
            "AvailableNetworkResourcesDisallowProductionException",
        ],
        possible_root_causes=[
            "DSLAM saturé (taux d'occupation 100%)",
            "Ressources réseau bloquées par une autre opération",
            "Compteurs NE erronés dans le référentiel",
        ],
        related_systems=["BRASIL", "ORCHESTRA", "SEBA"],
        severity="high",
    ),

    # ── NETWORK EQUIPMENT ISSUES ────────────────────────────────────────
    "network_equipment_issue": IncidentTypeDefinition(
        id="network_equipment_issue",
        category="network_equipment_issue",
        name="Network Equipment Issue",
        description=(
            "Problème physique ou logique sur un équipement réseau (DSLAM, OLT, NRO) "
            "impactant les opérations BRASIL."
        ),
        typical_patterns=[
            "dslam non joignable", "dslam inaccessible", "dslam hors ligne",
            "nro en panne", "équipement réseau en erreur", "port réseau en erreur",
            "DslamUnreachableException", "ne health check failed",
            "supervision nms alerte", "olt injoignable",
        ],
        possible_root_causes=[
            "Panne matérielle équipement réseau",
            "Problème réseau sur le flux de supervision",
            "Saturation de capacité port",
            "DSLAM hors ligne suite à coupure électrique",
            "Problème de configuration NE",
        ],
        related_systems=["BRASIL", "ORCHESTRA", "SEBA"],
        severity="critical",
    ),

    # ── DATA INCONSISTENCY (production variants) ────────────────────────
    "data_inconsistency": IncidentTypeDefinition(
        id="data_inconsistency",
        category="data_inconsistency",
        name="Data Inconsistency",
        description=(
            "Incohérence de données entre deux ou plusieurs systèmes du SI, "
            "entraînant des refus de traitement ou des états contradictoires."
        ),
        typical_patterns=[
            "données incohérentes", "identifiant inconnu", "mrt inconnu",
            "UnknownMRTIdException", "EntityNotFoundException",
            "données manquantes", "champ absent", "synchronisation échouée",
            "désynchronisation brasil seba", "données brasil absentes seba",
        ],
        possible_root_causes=[
            "Flux de synchronisation interrompu entre systèmes",
            "Migration partielle non validée",
            "Identifiant créé localement sans propagation",
            "Référentiel incohérent après incident de production",
        ],
        related_systems=["BRASIL", "SEBA", "ADELIA"],
        severity="high",
    ),

    # ── SYSTEM INTEGRATION ERRORS (production variants) ─────────────────
    "system_integration_error": IncidentTypeDefinition(
        id="system_integration_error",
        category="system_integration_error",
        name="System Integration Error",
        description=(
            "Erreur de communication ou d'intégration entre BRASIL et un système "
            "externe (SEBA, IPON, ARTEMIS, SCA, ORCHESTRA)."
        ),
        typical_patterns=[
            "connecteur indisponible", "ConnectorUnavailableException",
            "IntegrationTimeoutException", "timeout api externe",
            "http 503", "ssl handshake failure", "connexion refusée système tiers",
            "interface seba ko", "seba ne répond plus",
        ],
        possible_root_causes=[
            "Indisponibilité du système tiers",
            "Problème réseau sur flux inter-applicatif",
            "Certificat SSL expiré",
            "Mauvaise configuration endpoint dans BRASIL",
        ],
        related_systems=["BRASIL", "SEBA", "IPON", "ARTEMIS", "SCA", "ORCHESTRA"],
        severity="high",
    ),

    # ── ACCESS MANAGEMENT ERRORS (production variants) ──────────────────
    "access_management_error": IncidentTypeDefinition(
        id="access_management_error",
        category="access_management_error",
        name="Access Management Error",
        description=(
            "Problème d'authentification, d'autorisation ou de gestion des droits "
            "utilisateur dans BRASIL ou les systèmes interfacés."
        ),
        typical_patterns=[
            "SessionExpiredException", "accès refusé", "profil manquant",
            "session expirée", "UnauthorizedAccessException",
            "droits non propagés", "profil utilisateur incomplet",
            "token jwt expiré",
        ],
        possible_root_causes=[
            "Droits non propagés depuis annuaire LDAP",
            "Profil utilisateur mal configuré dans BRASIL",
            "Token JWT expiré côté API",
            "Session expirée prématurément",
        ],
        related_systems=["BRASIL"],
        severity="medium",
    ),

    # ── COMMAND FAILURES (production variants) ──────────────────────────
    "command_failure": IncidentTypeDefinition(
        id="command_failure",
        category="command_failure",
        name="Command Failure",
        description=(
            "Commande métier BRASIL échouée sans erreur réseau ou provisioning, "
            "liée à une logique applicative ou une règle métier violée."
        ),
        typical_patterns=[
            "erreur 1300", "error 1300", "CommandValidationException",
            "BusinessRuleViolationException", "InvalidCommandStateException",
            "commande échouée", "lancement commande impossible",
            "règle métier violée", "prérequis non satisfaits", "dossier incomplet",
        ],
        possible_root_causes=[
            "Dossier client incomplet",
            "Prérequis métier non satisfaits",
            "Séquencement de commandes incorrect",
            "Règle métier plus stricte depuis mise à jour",
        ],
        related_systems=["BRASIL", "ADELIA", "SEBA"],
        severity="medium",
    ),

    # ── CONVERSATIONAL / SYNTHESIS INTENTS ─────────────────────────────────
    "log_investigation": IncidentTypeDefinition(
        id="log_investigation",
        category="investigation",
        name="Log / Debug Investigation",
        description="Engineer asks for logs, traces, debug files, or debugging guidance.",
        typical_patterns=[
            "logs", "log", "traces", "journaux", "fichier log",
            "est-ce qu'il y a des logs", "y a-t-il des logs",
            "logs associés", "traces associées", "voir les logs",
            "stack trace", "déboguer", "debug", "fichiers de trace", "où sont les logs",
        ],
        possible_root_causes=["Log location unknown", "Debug investigation"],
        related_systems=["BRASIL", "SEBA", "ARTEMIS", "IPON", "ADELIA", "SCA", "ORCHESTRA"],
        severity="low",
    ),
    "ticket_summary": IncidentTypeDefinition(
        id="ticket_summary",
        category="synthesis",
        name="Résumé / Synthèse",
        description="Engineer asks for a short structured summary of the problem or diagnosis.",
        typical_patterns=[
            "résumé", "résume", "résumer", "récapitulatif", "récapituler",
            "synthèse", "en résumé", "bilan", "récap",
            "résume le problème", "résume la solution", "fais moi un résumé",
        ],
        possible_root_causes=[],
        related_systems=[],
        severity="low",
    ),
    "ticket_closing": IncidentTypeDefinition(
        id="ticket_closing",
        category="synthesis",
        name="Message de Clôture / Réponse Finale",
        description="Engineer asks to generate the final resolution message for the ticket requester.",
        typical_patterns=[
            "message pour le dépositaire", "réponse finale", "message de clôture",
            "clôturer le ticket", "fermer le ticket", "génère la réponse",
            "message à mettre dans le ticket", "message ticket",
            "texte pour le ticket", "rédiger le ticket", "écrire dans le ticket",
            "prépare le message", "résumé pour le ticket", "message jira", "commentaire jira",
        ],
        possible_root_causes=[],
        related_systems=[],
        severity="low",
    ),
    "find_similar_tickets": IncidentTypeDefinition(
        id="find_similar_tickets",
        category="search",
        name="Recherche de tickets similaires",
        description="Engineer asks the assistant to find tickets with the same error or behaviour.",
        typical_patterns=[
            "tickets similaires", "incidents similaires", "ticket similaire",
            "y a-t-il des tickets", "existe-t-il des tickets",
            "tickets avec le même", "tickets avec cette erreur",
            "problème similaire", "déjà vu", "déjà rencontré",
            "autres tickets", "chercher des tickets", "recherche de tickets",
        ],
        possible_root_causes=[],
        related_systems=[],
        severity="low",
    ),
    "find_jira": IncidentTypeDefinition(
        id="find_jira",
        category="search",
        name="Recherche Jira",
        description="Engineer asks whether a Jira issue exists for this incident.",
        typical_patterns=[
            "jira", "carte jira", "issue jira", "y a-t-il un jira",
            "existe-t-il un jira", "trouver le jira", "chercher dans jira",
            "y a-t-il une carte", "y a-t-il un ticket jira",
            "créer un jira", "ouvrir un jira", "lien jira", "référence jira",
        ],
        possible_root_causes=[],
        related_systems=[],
        severity="low",
    ),
    "explain_jira": IncidentTypeDefinition(
        id="explain_jira",
        category="synthesis",
        name="Explication / Reformulation Jira",
        description="Engineer asks the assistant to explain or reformulate a specific Jira issue via LLM.",
        typical_patterns=[
            "explique ce jira", "explique le jira", "reformule le jira",
            "reformule cette carte", "résume ce jira", "résume le jira",
            "explique-moi ce ticket jira", "que dit ce jira",
            "analyse ce jira", "décrypte ce jira", "interprète ce jira",
            "explique la carte jira",
        ],
        possible_root_causes=[],
        related_systems=[],
        severity="low",
    ),
    "explain_data_model": IncidentTypeDefinition(
        id="explain_data_model",
        category="documentation",
        name="Explication modèle de données / schéma BDD BRASIL",
        description="Engineer asks to explain the BRASIL data model, DB schema, tables, columns or entity relationships.",
        typical_patterns=[
            "modèle de données", "structure de la base", "schéma de la base",
            "quelles sont les tables", "tables brasil", "bdd brasil",
            "dictionnaire de données", "entités brasil", "relations entre les tables",
            "colonne table", "explique la base", "explique le schéma",
            # Demandes directes sur une table
            "explique la table", "explique-moi la table", "explique moi la table",
            "expliquer la table", "description de la table", "structure de la table",
            "schéma de la table", "schema de la table", "colonnes de",
            "quelles colonnes", "quels champs", "quelles sont les colonnes",
            "clé primaire", "clé étrangère", "foreign key", "primary key",
            # Noms de tables BRASIL connus
            "t_ports", "t_cards", "t_equipments", "t_slots", "t_stripes",
            "t_prestations", "t_nodes", "t_media_links", "t_port_groups",
            "t_d_booked", "t_ftth", "t_mrt", "t_tech_serv",
        ],
        possible_root_causes=[],
        related_systems=["BRASIL"],
        severity="low",
    ),
    "unknown.insufficient_information": IncidentTypeDefinition(
        id="unknown.insufficient_information",
        category="unknown",
        name="Unknown / Insufficient Information",
        description="Cannot classify the incident due to insufficient information.",
        typical_patterns=[],
        possible_root_causes=["Ticket too short", "Missing context", "Ambiguous description"],
        related_systems=[],
        severity="low",
    ),
}

# ─────────────────────────────────────────────
# Category-level index for fast lookup
# ─────────────────────────────────────────────
CATEGORIES = list({v.category for v in INCIDENT_TAXONOMY.values()})


def get_taxonomy_by_category(category: str) -> List[IncidentTypeDefinition]:
    """Return all incident types for a given category."""
    return [v for v in INCIDENT_TAXONOMY.values() if v.category == category]


def find_incident_type(text: str) -> Optional[str]:
    """
    Rule-based incident type detection from text.
    Priority order: explain_data_model > explain_jira > find_jira > find_similar_tickets
    > ticket_summary > ticket_closing > log_investigation > procedure_lookup
    > root_cause_exploration > pattern_analysis > diagnostic_request > rest.
    Within same score, higher-priority type wins.
    Returns the best matching incident_type id, or 'unknown.insufficient_information'.
    """
    if not text:
        return "unknown.insufficient_information"
    text_lower = text.lower()

    # Explicit priority order — first type with score > 0 wins in case of tie
    _PRIORITY_ORDER = [
        "explain_data_model",
        "explain_jira",
        "find_jira",
        "find_similar_tickets",
        "ticket_summary",
        "ticket_closing",
        "log_investigation",
        "procedure_lookup",
        "root_cause_exploration",
        "pattern_analysis",
        "diagnostic_request",
        "knowledge_lookup",
        "knowledge_gap_detection",
    ]

    scores: dict = {}
    for type_id, definition in INCIDENT_TAXONOMY.items():
        if type_id == "unknown.insufficient_information":
            continue
        score = sum(1 for p in definition.typical_patterns if p.lower() in text_lower)
        if score > 0:
            scores[type_id] = score

    if not scores:
        return "unknown.insufficient_information"

    best_score = max(scores.values())
    # Among all types with the best score, pick the one highest in _PRIORITY_ORDER
    best_candidates = [t for t, s in scores.items() if s == best_score]
    for priority_type in _PRIORITY_ORDER:
        if priority_type in best_candidates:
            return priority_type
    # Fallback: return any candidate
    return best_candidates[0]
