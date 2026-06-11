"""
execution_graph_extractor.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BRASIL Source Code Execution Graph Builder.

Scans the Java source tree and extracts:
- Service classes with their methods, dependencies, and exception throws
- Repository/DAO classes with SQL queries and table references
- Controller/WS entry points and their service calls
- Validator classes and blocking conditions
- Full operation execution chains: Controller→Service→Validator→Repository→SQL→Exception

Output: ExecutionGraph — deterministic, cached, never sent raw to LLM.

Design:
  - Pure regex-based (no AST, no external parsers)
  - File cache compatible (JSON serializable)
  - Python 3.13 compatible (no torch, no ML)
  - Additive to existing brasil_extractor.py
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

BRASIL_SOURCE_ROOT = os.getenv(
    "BRASIL_SOURCE_ROOT",
    str(Path(__file__).resolve().parents[5] / "brasil-default" / "brasil-default")
)

_GRAPH_CACHE_FILE = Path(__file__).resolve().parent.parent / "execution_graph_cache.json"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Regex patterns
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Class declaration
_CLASS_RX = re.compile(
    r'public\s+(?:abstract\s+)?class\s+(\w+)\s*(?:extends\s+\w+)?\s*(?:implements\s+[^{]+)?\s*\{',
    re.MULTILINE
)

# Method declarations (public/protected/private, captures return type + name + params)
_METHOD_RX = re.compile(
    r'(?:public|protected|private)\s+(?:static\s+)?(?:final\s+)?'
    r'(?:<[^>]+>\s+)?(\w+(?:<[^>]+>)?)\s+(\w+)\s*\(([^)]*)\)',
    re.MULTILINE
)

# @Inject / @Autowired / @EJB field injections — captures type + field name
_INJECT_RX = re.compile(
    r'@(?:Inject|Autowired|EJB|Resource)\s+(?:private\s+|protected\s+)?(\w+)\s+(\w+)\s*;',
    re.MULTILINE
)

# @Local / @Remote interface used in EJBs
_LOCAL_INTERFACE_RX = re.compile(
    r'@(?:Local|Remote|Stateless|Singleton)\b'
)

# @Query / @NativeQuery SQL annotations
_QUERY_ANNOTATION_RX = re.compile(
    r'@(?:Named)?(?:Native)?Query\s*\(\s*(?:name\s*=\s*"[^"]+"\s*,\s*)?query\s*=\s*"([^"]+)"',
    re.MULTILINE | re.IGNORECASE
)

# JPA JPQL entity names (FROM EntityName)
_JPQL_FROM_RX = re.compile(
    r'\bFROM\s+(\w+)\b', re.IGNORECASE
)

# Native SQL table refs
_SQL_TABLE_RX = re.compile(
    r'\b(t_[a-z_]+)\b', re.IGNORECASE
)

# Method calls to other services: someService.someMethod(
_METHOD_CALL_RX = re.compile(
    r'(\w+(?:Service|Business|Manager|Repository|DAO|Dao|Validator|Handler))\s*\.\s*(\w+)\s*\(',
    re.MULTILINE
)

# Exception throws
_THROW_METHOD_RX = re.compile(
    r'throw\s+new\s+(\w+Exception\w*)\s*\(',
    re.MULTILINE
)

# Validation/check conditions before throwing
_IF_CONDITION_RX = re.compile(
    r'if\s*\(([^)]{5,100})\)\s*\{[^}]*throw\s+new\s+(\w+Exception\w*)',
    re.MULTILINE | re.DOTALL
)

# Logger statements (capture the log message for pattern matching)
_LOG_RX = re.compile(
    r'(?:log|logger|LOG|LOGGER)\s*\.\s*(?:error|warn|info|debug)\s*\(\s*"([^"]{10,200})"',
    re.MULTILINE
)

# Method annotation (for detecting lifecycle/transaction)
_TRANSACTIONAL_RX = re.compile(
    r'@(?:Transactional|javax\.transaction\.Transactional)',
    re.MULTILINE
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Data models
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class ExecutionNode:
    """
    A single node in the execution graph: one method in one class.
    Represents what a method does, what it calls, and what can go wrong.
    """
    node_id:          str        # "ClassName.methodName"
    class_name:       str
    method_name:      str
    node_type:        str        # "controller" | "service" | "repository" | "validator" | "business"
    entity:           str        # "Dslam" | "Vlan" | etc.
    operation:        str        # "delete" | "create" | "modify" | "validate" | "check"
    exceptions_thrown: List[str] = field(default_factory=list)
    sql_tables:       List[str] = field(default_factory=list)
    calls:            List[str] = field(default_factory=list)  # node_ids of called methods
    blocking_conditions: List[str] = field(default_factory=list)
    log_patterns:     List[str] = field(default_factory=list)
    is_transactional: bool = False
    code_location:    Dict[str, Any] = field(default_factory=dict)
    dependencies:     List[str] = field(default_factory=list)  # injected service types

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ExecutionNode":
        return cls(**d)

    def to_summary(self) -> str:
        """One-line forensic summary for LLM context."""
        parts = [f"`{self.node_id}`"]
        if self.operation:
            parts.append(f"op={self.operation}")
        if self.exceptions_thrown:
            parts.append(f"throws=[{', '.join(self.exceptions_thrown[:2])}]")
        if self.sql_tables:
            parts.append(f"tables=[{', '.join(self.sql_tables[:3])}]")
        if self.blocking_conditions:
            parts.append(f"blocks=[{self.blocking_conditions[0][:60]}]")
        loc = self.code_location
        if loc.get("file"):
            f = loc["file"].split("\\")[-1].split("/")[-1]
            parts.append(f"[{f}:{loc.get('line', '?')}]")
        return " | ".join(parts)


@dataclass
class OperationPath:
    """
    Full execution path for a high-level business operation.
    Example: delete_equipment → DslamServiceImpl.deleteDslam()
                              → DslamDeletionValidator.validate()
                              → DslamRepository.deleteById()
    """
    operation:    str            # "delete_equipment"
    entity:       str            # "Dslam"
    entrypoints:  List[str]      # controller/WS method node_ids
    services:     List[str]      # service method node_ids
    validators:   List[str]      # validator method node_ids
    repositories: List[str]      # repository method node_ids
    exceptions:   List[str]      # all possible exceptions
    sql_tables:   List[str]      # all SQL tables touched
    blocking_conditions: List[str]
    log_patterns: List[str]
    code_locations: List[Dict]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "OperationPath":
        return cls(**d)

    def to_forensic_summary(self) -> str:
        """Compact multi-line forensic summary."""
        lines = [f"**{self.operation}** — entity: `{self.entity}`"]
        if self.entrypoints:
            lines.append(f"  Entry: `{'`, `'.join(self.entrypoints[:2])}`")
        if self.services:
            lines.append(f"  Services: `{'`, `'.join(self.services[:3])}`")
        if self.validators:
            lines.append(f"  Validators: `{'`, `'.join(self.validators[:2])}`")
        if self.exceptions:
            lines.append(f"  Exceptions: `{'`, `'.join(self.exceptions[:4])}`")
        if self.blocking_conditions:
            lines.append(f"  Blocks: {'; '.join(self.blocking_conditions[:2])}")
        if self.sql_tables:
            lines.append(f"  Tables: `{'`, `'.join(self.sql_tables[:5])}`")
        return "\n".join(lines)


@dataclass
class ExecutionGraph:
    """Complete execution graph for the BRASIL application."""
    nodes:     Dict[str, ExecutionNode]    # node_id → ExecutionNode
    operations: Dict[str, OperationPath]  # operation → OperationPath
    exception_to_nodes: Dict[str, List[str]]  # exception_class → [node_ids]
    table_to_nodes: Dict[str, List[str]]       # table_name → [node_ids]
    total_files_scanned: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "operations": {k: v.to_dict() for k, v in self.operations.items()},
            "exception_to_nodes": self.exception_to_nodes,
            "table_to_nodes": self.table_to_nodes,
            "total_files_scanned": self.total_files_scanned,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ExecutionGraph":
        return cls(
            nodes={k: ExecutionNode.from_dict(v) for k, v in d.get("nodes", {}).items()},
            operations={k: OperationPath.from_dict(v) for k, v in d.get("operations", {}).items()},
            exception_to_nodes=d.get("exception_to_nodes", {}),
            table_to_nodes=d.get("table_to_nodes", {}),
            total_files_scanned=d.get("total_files_scanned", 0),
        )

    def find_nodes_by_exception(self, exc_class: str) -> List[ExecutionNode]:
        """Find all nodes that throw a given exception."""
        node_ids = self.exception_to_nodes.get(exc_class, [])
        return [self.nodes[n] for n in node_ids if n in self.nodes]

    def find_nodes_by_table(self, table: str) -> List[ExecutionNode]:
        """Find all nodes that access a given SQL table."""
        node_ids = self.table_to_nodes.get(table.lower(), [])
        return [self.nodes[n] for n in node_ids if n in self.nodes]

    def find_nodes_by_operation(self, operation: str, entity: str = "") -> List[ExecutionNode]:
        """Find all nodes matching an operation keyword and optional entity."""
        op_lower = operation.lower()
        entity_lower = entity.lower()
        results = []
        for node in self.nodes.values():
            if op_lower and op_lower not in node.operation:
                continue
            if entity_lower and entity_lower not in node.entity.lower():
                continue
            results.append(node)
        return sorted(results, key=lambda n: (
            1 if n.node_type == "service" else
            2 if n.node_type == "validator" else
            3 if n.node_type == "repository" else 4
        ))

    def get_operation_path(self, operation: str) -> Optional[OperationPath]:
        return self.operations.get(operation)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Extraction Engine
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Operation keyword patterns (method name → operation category)
_OPERATION_KEYWORDS = {
    "delete": ["delete", "remove", "suppress", "clean", "purge"],
    "create": ["create", "add", "insert", "build", "provision"],
    "modify": ["update", "modify", "change", "set", "patch"],
    "validate": ["validate", "check", "verify", "assert", "control"],
    "get": ["get", "find", "search", "list", "query", "fetch", "load"],
    "sync": ["sync", "synchronize", "propagate", "push"],
    "rollback": ["rollback", "undo", "cancel", "abort"],
    "activate": ["activate", "enable", "start", "init"],
    "deactivate": ["deactivate", "disable", "stop"],
}

# Entity extraction from class/method names
_ENTITY_KEYWORDS = {
    "Dslam": ["dslam", "Dslam", "DSLAM"],
    "Vlan": ["vlan", "Vlan", "VLAN"],
    "Card": ["card", "Card"],
    "Shelf": ["shelf", "Shelf"],
    "Port": ["port", "Port"],
    "MRT": ["mrt", "Mrt", "MRT"],
    "EPC": ["epc", "Epc", "EPC"],
    "WorkOrder": ["workorder", "WorkOrder", "workOrder"],
    "SupportLink": ["supportlink", "SupportLink", "supportLink"],
    "VlanInterface": ["vlaninterface", "VlanInterface"],
    "SrIpInterface": ["sripinterface", "SrIpInterface", "srIp"],
    "Equipment": ["equipment", "Equipment"],
    "Node": ["node", "Node"],
    "Bay": ["bay", "Bay"],
    "Stripe": ["stripe", "Stripe"],
}

# Node type detection from class name patterns
_NODE_TYPE_MAP = {
    "service": ["Service", "Business", "BusinessService"],
    "repository": ["Repository", "DAO", "Dao", "Mapper"],
    "validator": ["Validator", "Checker", "Verifier", "Guard"],
    "controller": ["Controller", "WS", "Endpoint", "Resource", "Facade"],
    "business": ["Manager", "Handler", "Processor", "Executor", "Orchestrator"],
}

# Business operation → method name keywords
_OPERATION_METHOD_MAP = {
    # Équipement / DSLAM
    "delete_equipment":         ["deleteDslam", "suppressionDslam", "deleteDslamManager", "removeEquipment", "supprimerDslam"],
    "force_delete_equipment":   ["forceDelete", "forceSuppression", "forceRemove"],
    "create_equipment":         ["createDslam", "createEquipment", "addDslam", "creerDslam", "instancierDslam"],
    "modify_equipment":         ["updateDslam", "modifyDslam", "mutateDslam", "modifierDslam"],
    "activate_equipment":       ["activateDslam", "activerDslam", "activateEquipment", "mettreEnService"],
    "deactivate_equipment":     ["deactivateDslam", "desactiverDslam", "deactivateEquipment"],
    "synchronize_equipment":    ["synchronizeDslam", "syncDslam", "synchroniserDslam", "orrahdSync"],
    "lock_equipment":           ["lockDslam", "lockEquipment", "bloquerDslam"],
    "unlock_equipment":         ["unlockDslam", "unlockEquipment", "debloquerDslam"],
    # VLAN
    "create_vlan":              ["createVlan", "creerVlan", "addVlan", "ajouterVlan"],
    "delete_vlan":              ["deleteVlan", "supprimerVlan", "removeVlan"],
    "modify_vlan":              ["updateVlan", "modifyVlan", "modifierVlan"],
    "vlan_provisioning":        ["provisionVlan", "deployVlan", "propagateVlan"],
    # Services / VC
    "delete_service":           ["deleteService", "supprimerService", "removeService"],
    "create_service":           ["createService", "creerService", "addService"],
    "close_service":            ["closeService", "fermerService", "cloturerService"],
    "activate_service":         ["activateService", "activerService"],
    # MRT / Liens
    "delete_mrt":               ["deleteMrt", "supprimerMrt", "removeMrt", "deleteMrtLink"],
    "create_mrt":               ["createMrt", "creerMrt", "addMrt"],
    "check_mrt":                ["checkMrt", "verifierMrt", "getMrtLinks", "findMrtByEqpt"],
    # Cartes / Chassis
    "delete_card":              ["deleteCard", "supprimerCarte", "removeCard"],
    "delete_shelf":             ["deleteShelf", "supprimerChassis", "removeShelf"],
    "create_card":              ["createCard", "creerCarte", "addCard"],
    # Validation / Contraintes
    "validate_deletion":        ["validateDeletion", "validerSuppression", "checkDeletionConstraints", "assertCanDelete", "checkDeletion", "assertDeletable", "canDelete"],
    "validate_creation":        ["validateCreation", "validerCreation", "checkCreationConstraints"],
    "validate_state":           ["validateState", "validerEtat", "checkState", "assertState"],
    "check_residual_data":      ["checkResidual", "verifierResidus", "findResidual", "hasResidualData"],
    "check_dependencies":       ["checkDependencies", "verifierDependances", "getDependencies"],
    # Workflow / Orchestration
    "workflow_blocked":         ["blockWorkflow", "bloquerWorkflow", "workflowBlocked", "setWorkflowBlocked", "setState"],
    "workflow_rollback":        ["rollback", "annulerWorkflow", "revertWorkflow", "rollbackTransaction", "cancelOperation", "undoOperation", "executeRollback", "doRollback"],
    "restart_workflow":         ["restartWorkflow", "relancerWorkflow", "retryWorkflow", "resumeWorkflow"],
    "provisioning":             ["provision", "provisionner", "deployWorkflow", "executeProvisioning", "startProvisioning", "runProvisioning"],
    "activation":               ["activate", "activer", "executeActivation", "startActivation", "processActivation"],
    "deactivation":             ["deactivate", "desactiver", "executeDeactivation", "processDeactivation"],
    # Orchestration ARTEMIS / ORCHESTRA / SEBA
    "artemis_command":          ["sendArtemisCommand", "artemisRequest", "artemisSync", "sendToArtemis", "processArtemis", "executeArtemis"],
    "orchestra_sync":           ["orchestraSync", "syncOrchestra", "orchestraUpdate", "propagateOrchestra", "pushOrchestra", "sendOrchestra", "notifyOrchestra"],
    "seba_sync":                ["sebaSync", "syncSeba", "sebaUpdate", "sebaReference", "sendSeba", "notifySeba", "processSeba"],
    # WorkOrder
    "create_workorder":         ["createWorkOrder", "creerWorkOrder", "addWorkOrder", "openWorkOrder", "generateWorkOrder"],
    "close_workorder":          ["closeWorkOrder", "fermerWorkOrder", "completeWorkOrder", "terminateWorkOrder"],
    "cancel_workorder":         ["cancelWorkOrder", "annulerWorkOrder", "abortWorkOrder"],
    # Commandes / Replay
    "replay_order":             ["replayOrder", "rejouerOrdre", "replayCommand", "retryOrder", "replayMessage", "retraitementOrdre"],
    "send_command":             ["sendCommand", "envoyerCommande", "dispatchCommand", "submitCommand", "executeCommand"],
    # Réseau / Port / Ressource
    "search_port":              ["searchPort", "rechercherBroche", "findPort", "allocatePort", "getAvailablePort", "findAvailablePort"],
    "allocate_resource":        ["allocateResource", "reserverRessource", "allocateNetworkTR", "reserveResource"],
    "release_resource":         ["releaseResource", "libererRessource", "deallocate", "freeResource", "libererPorte"],
    # Compteurs / TOC
    "fix_counter":              ["fixCounter", "corrigerCompteur", "recalcToc", "updateToc", "recalculer", "recalculateToc", "correctCounter"],
    "check_toc":                ["getToc", "calculerToc", "checkToc", "verifierToc", "computeToc", "calculateToc"],
    # Mutation DSLAM
    "mutate_dslam":             ["mutateDslam", "mutationDslam", "deplacerDslam", "migrateDslam", "executeMutation", "processMutation"],
    # ND / Noeud
    "release_nd":               ["releaseNd", "libererNd", "freeNd", "removeNd", "detachNd", "unlinkNd"],
    "check_nd":                 ["checkNd", "verifierNd", "getNdState", "findNd", "validateNd"],
    # Diagnostics
    "diagnose_equipment":       ["diagnose", "diagnoser", "getDiagnostic", "runDiagnostic", "executeDiagnostic", "performDiagnostic"],
    # Résidus / Nettoyage
    "clean_residual":           ["cleanResidual", "nettoyerResidus", "purgeResidual", "deleteResidual", "removeResidual", "cleanOrphan"],
    # Synchronisation générale
    "sync_data":                ["syncData", "synchronizeData", "propagateData", "pushData", "alignData"],
}


_VALIDATION_METHOD_PREFIXES = (
    "assert", "check", "validate", "verify", "verif",
    "control", "ensure", "candelete", "candeprovision",
    "checkdeletion", "assertrf", "checkrf", "checkconstraint",
    "checkfunctionalrules", "checkroles", "checkequip",
    "checkinputs", "checkstate",
)


class ExecutionGraphExtractor:
    """
    Scans the BRASIL Java source tree and builds an ExecutionGraph.

    Extracts:
    - All service/repository/controller/validator methods
    - Exception throw sites with enclosing method context
    - SQL table references per method
    - Dependency injection chains
    - Operation → execution path mappings
    """

    def __init__(self, source_root: str = BRASIL_SOURCE_ROOT):
        self.source_root = Path(source_root)
        self._nodes: Dict[str, ExecutionNode] = {}
        self._exc_to_nodes: Dict[str, List[str]] = {}
        self._table_to_nodes: Dict[str, List[str]] = {}
        self._files_scanned = 0

    def run(self) -> ExecutionGraph:
        """Full extraction pipeline. Returns ExecutionGraph."""
        if not self.source_root.exists():
            logger.warning(f"[GraphExtractor] Source root not found: {self.source_root}")
            return ExecutionGraph({}, {}, {}, {})

        logger.info(f"[GraphExtractor] Scanning {self.source_root} ...")

        # Phase 1: Scan all service/repository/validator/controller files
        self._scan_files()
        logger.info(f"[GraphExtractor] {len(self._nodes)} nodes from {self._files_scanned} files")

        # Phase 2: Build operation paths
        operations = self._build_operation_paths()
        logger.info(f"[GraphExtractor] {len(operations)} operation paths built")

        return ExecutionGraph(
            nodes=self._nodes,
            operations=operations,
            exception_to_nodes=self._exc_to_nodes,
            table_to_nodes=self._table_to_nodes,
            total_files_scanned=self._files_scanned,
        )

    def _scan_files(self):
        """Scan all relevant Java files for execution nodes."""
        # Patterns ordered by priority (most specific first)
        patterns = [
            # Core service layer
            ("*ServiceImpl.java",      "service"),
            ("*BusinessImpl.java",     "service"),
            ("*ManagerImpl.java",      "business"),
            # Validators & constraints
            ("*Validator*.java",       "validator"),
            ("*Checker*.java",         "validator"),
            ("*Verif*.java",           "validator"),
            ("*Constraint*.java",      "validator"),
            ("*Guard*.java",           "validator"),
            # Persistence
            ("*Repository*.java",      "repository"),
            ("*DAO*.java",             "repository"),
            ("*Dao*.java",             "repository"),
            ("*Mapper*.java",          "repository"),
            # Controllers / entry points
            ("*WS*.java",              "controller"),
            ("*Controller*.java",      "controller"),
            ("*Facade*.java",          "controller"),
            ("*Endpoint*.java",        "controller"),
            ("*Resource*.java",        "controller"),
            # Workflow / orchestration
            ("*Workflow*.java",        "business"),
            ("*Rollback*.java",        "business"),
            ("*Provisioning*.java",    "business"),
            ("*Activation*.java",      "business"),
            ("*Deactivation*.java",    "business"),
            ("*Orchestr*.java",        "business"),
            ("*Artemis*.java",         "business"),
            ("*Seba*.java",            "business"),
            ("*Dispatcher*.java",      "business"),
            # Handlers / Processors
            ("*Handler*.java",         "business"),
            ("*Processor*.java",       "business"),
            ("*Executor*.java",        "business"),
            # Domain-specific
            ("*Mutation*.java",        "business"),
            ("*WorkOrder*.java",       "business"),
            ("*Toc*.java",             "business"),
            ("*Counter*.java",         "business"),
            ("*Replay*.java",          "business"),
            ("*Command*.java",         "business"),
            # Generic service (last — catches remaining)
            ("*Service*.java",         "service"),
            ("*Business*.java",        "service"),
            ("*Manager*.java",         "business"),
        ]

        scanned: Set[Path] = set()
        for pattern, node_type_hint in patterns:
            for java_file in self.source_root.rglob(pattern):
                if java_file in scanned or java_file.stat().st_size > 500_000:
                    continue
                scanned.add(java_file)
                try:
                    content = java_file.read_text(encoding="utf-8", errors="replace")
                    self._extract_nodes_from_file(java_file, content, node_type_hint)
                    self._files_scanned += 1
                except Exception as e:
                    logger.debug(f"[GraphExtractor] Skip {java_file.name}: {e}")

    def _extract_nodes_from_file(self, java_file: Path, content: str, node_type_hint: str):
        """Extract all execution nodes from a single Java file."""
        # Detect class name
        class_match = _CLASS_RX.search(content)
        class_name = class_match.group(1) if class_match else java_file.stem

        # Detect node type from class name
        node_type = self._detect_node_type(class_name) or node_type_hint

        # Detect entity from file path
        entity = self._entity_from_class(class_name, str(java_file))

        # Get injected dependencies
        dependencies = [m.group(1) for m in _INJECT_RX.finditer(content)]

        # Find SQL queries from @Query annotations
        query_tables: Set[str] = set()
        for m in _QUERY_ANNOTATION_RX.finditer(content):
            sql = m.group(1)
            query_tables.update(t.lower() for t in _SQL_TABLE_RX.findall(sql))
            # Also extract JPQL entity names
            for jpql_entity in _JPQL_FROM_RX.findall(sql):
                query_tables.add(jpql_entity.lower())

        # Detect transactional methods
        is_transactional_class = bool(_TRANSACTIONAL_RX.search(content[:2000]))

        # Extract methods by finding method boundaries
        self._extract_methods(
            java_file=java_file,
            content=content,
            class_name=class_name,
            node_type=node_type,
            entity=entity,
            dependencies=dependencies,
            class_level_tables=list(query_tables),
            is_transactional_class=is_transactional_class,
        )

    def _extract_methods(
        self,
        java_file: Path,
        content: str,
        class_name: str,
        node_type: str,
        entity: str,
        dependencies: List[str],
        class_level_tables: List[str],
        is_transactional_class: bool,
    ):
        """Extract method-level execution nodes."""
        method_positions = list(_METHOD_RX.finditer(content))

        for i, m in enumerate(method_positions):
            return_type = m.group(1)
            method_name = m.group(2)

            # Skip getters/setters/constructors/trivial
            if method_name in (class_name, "get", "set", "is", "toString", "equals", "hashCode"):
                continue
            if re.match(r'^get[A-Z]|^set[A-Z]|^is[A-Z]', method_name) and not any(
                kw in method_name for kw in ["State", "Status", "Error"]
            ):
                continue

            # Determine method boundary (content until next method or end of class)
            method_start = m.start()
            method_end = method_positions[i + 1].start() if i + 1 < len(method_positions) else len(content)
            method_body = content[method_start:min(method_end, method_start + 3000)]

            # Skip abstract methods (no body)
            if method_body.count("{") == 0:
                continue

            operation = self._detect_operation(method_name)
            line_no = content[:method_start].count("\n") + 1

            # Extract exceptions thrown in this method
            exceptions = list(set(m2.group(1) for m2 in _THROW_METHOD_RX.finditer(method_body)))

            # Extract SQL tables referenced in method body
            tables = list(set(
                t.lower() for t in _SQL_TABLE_RX.findall(method_body)
                if len(t) > 3
            ))

            # Extract service calls (what other services does this method call)
            calls = [
                f"{m2.group(1)}.{m2.group(2)}"
                for m2 in _METHOD_CALL_RX.finditer(method_body)
            ][:10]

            # Extract blocking conditions (if statements before throws)
            blocking = []
            for m2 in _IF_CONDITION_RX.finditer(method_body):
                condition = m2.group(1).strip()
                exc = m2.group(2)
                if len(condition) > 5:
                    blocking.append(f"if ({condition[:80]}) → throws {exc}")

            # Extract log patterns
            log_patterns = [m2.group(1)[:100] for m2 in _LOG_RX.finditer(method_body)][:3]

            # Detect transactional
            is_transactional = is_transactional_class or bool(
                re.search(r'@Transactional', content[max(0, method_start-200):method_start])
            )

            node_id = f"{class_name}.{method_name}"

            # Reclassify: service methods with validation names → validator
            effective_node_type = node_type
            mn_lower = method_name.lower()
            if node_type in ("service", "business") and any(
                mn_lower.startswith(p) for p in _VALIDATION_METHOD_PREFIXES
            ):
                effective_node_type = "validator"

            node = ExecutionNode(
                node_id=node_id,
                class_name=class_name,
                method_name=method_name,
                node_type=effective_node_type,
                entity=entity,
                operation=operation,
                exceptions_thrown=exceptions,
                sql_tables=list(set(tables + class_level_tables))[:8],
                calls=calls,
                blocking_conditions=blocking[:5],
                log_patterns=log_patterns,
                is_transactional=is_transactional,
                code_location={
                    "file": str(java_file.relative_to(self.source_root)),
                    "class": class_name,
                    "method": method_name,
                    "line": line_no,
                },
                dependencies=dependencies[:10],
            )

            # Deduplicate: keep highest-quality node per node_id
            if node_id not in self._nodes or (
                len(node.exceptions_thrown) > len(self._nodes[node_id].exceptions_thrown)
            ):
                self._nodes[node_id] = node

            # Build indexes
            for exc in exceptions:
                self._exc_to_nodes.setdefault(exc, [])
                if node_id not in self._exc_to_nodes[exc]:
                    self._exc_to_nodes[exc].append(node_id)

            for tbl in tables:
                self._table_to_nodes.setdefault(tbl, [])
                if node_id not in self._table_to_nodes[tbl]:
                    self._table_to_nodes[tbl].append(node_id)

    def _build_operation_paths(self) -> Dict[str, OperationPath]:
        """Build high-level operation → execution path mappings."""
        operations: Dict[str, OperationPath] = {}

        for op_name, method_keywords in _OPERATION_METHOD_MAP.items():
            entity = op_name.split("_")[1].capitalize() if "_" in op_name else ""
            # Find entity-specific entity name
            if entity == "Equipment":
                entity = "Dslam"  # BRASIL: Equipment is primarily Dslam

            entrypoints, services, validators, repos = [], [], [], []
            all_exceptions: List[str] = []
            all_tables: List[str] = []
            all_conditions: List[str] = []
            all_logs: List[str] = []
            all_locations: List[Dict] = []

            for node in self._nodes.values():
                # Match by operation keyword in method name
                matches_op = any(kw.lower() in node.method_name.lower() for kw in method_keywords)

                if not matches_op:
                    continue

                # Match by entity — validators/business may have generic names,
                # so we relax the filter for them (keep only if entity matches OR no entity)
                matches_entity = (
                    not entity
                    or entity.lower() in node.entity.lower()
                    or entity.lower() in node.class_name.lower()
                    or node.node_type in ("validator", "business")  # validators are cross-entity
                    or node.code_location.get("file", "").lower().find(entity.lower()) != -1
                )

                if not matches_entity:
                    continue

                # Categorize node — validator detection by method name prefix
                mn_lower = node.method_name.lower()
                is_validation_method = any(
                    mn_lower.startswith(p) for p in _VALIDATION_METHOD_PREFIXES
                )
                if node.node_type == "controller":
                    entrypoints.append(node.node_id)
                elif node.node_type == "validator" or (is_validation_method and node.blocking_conditions):
                    validators.append(node.node_id)
                elif node.node_type == "repository":
                    repos.append(node.node_id)
                elif node.node_type in ("service", "business"):
                    services.append(node.node_id)

                all_exceptions.extend(node.exceptions_thrown)
                all_tables.extend(node.sql_tables)
                all_conditions.extend(node.blocking_conditions)
                all_logs.extend(node.log_patterns)
                if node.code_location:
                    all_locations.append(node.code_location)

            if services or entrypoints or validators:
                operations[op_name] = OperationPath(
                    operation=op_name,
                    entity=entity,
                    entrypoints=list(set(entrypoints))[:5],
                    services=list(set(services))[:8],
                    validators=list(set(validators))[:5],
                    repositories=list(set(repos))[:5],
                    exceptions=list(set(all_exceptions))[:10],
                    sql_tables=list(set(all_tables))[:10],
                    blocking_conditions=list(set(all_conditions))[:8],
                    log_patterns=list(set(all_logs))[:6],
                    code_locations=all_locations[:6],
                )

        # ── Pass 2: attach entity-matching validators to each operation path ──
        # BRASIL validators (assertRF036, checkEquipCompatibility, etc.) live in
        # BusinessImpl classes and never match operation keywords directly.
        # We attach them by entity + blocking_conditions presence.
        for op_name, op_path in operations.items():
            if not op_path.entity:
                continue
            ent_lower = op_path.entity.lower()
            op_lower = op_name.split("_")[0]  # "delete", "create", etc.
            seen = set(op_path.validators)
            extra_vals: List[str] = []
            extra_conds: List[str] = []
            extra_exc: List[str] = []
            for node in self._nodes.values():
                if node.node_id in seen:
                    continue
                if node.node_type != "validator":
                    continue
                if not node.blocking_conditions:
                    continue
                # Entity match via class name, file path, or entity field
                entity_match = (
                    ent_lower in node.class_name.lower()
                    or ent_lower in node.entity.lower()
                    or ent_lower in node.code_location.get("file", "").lower()
                )
                if not entity_match:
                    continue
                # Operation relevance: constraint/check/assert methods apply to
                # delete/validate; create/activate methods apply to create/activate
                mn_lower = node.method_name.lower()
                op_relevant = (
                    op_lower in ("delete", "validate", "force")
                    or op_lower in mn_lower
                    or any(kw in mn_lower for kw in ("constraint", "check", "assert", "verify", "rule"))
                )
                if not op_relevant:
                    continue
                seen.add(node.node_id)
                extra_vals.append(node.node_id)
                extra_conds.extend(node.blocking_conditions)
                extra_exc.extend(node.exceptions_thrown)

            if extra_vals:
                op_path.validators = (op_path.validators + extra_vals)[:8]
                new_conds = list(set(op_path.blocking_conditions + extra_conds))[:10]
                op_path.blocking_conditions = new_conds
                new_exc = list(set(op_path.exceptions + extra_exc))[:12]
                op_path.exceptions = new_exc

        return operations

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _detect_node_type(self, class_name: str) -> str:
        for node_type, suffixes in _NODE_TYPE_MAP.items():
            for suffix in suffixes:
                if suffix in class_name:
                    return node_type
        return "service"

    def _detect_operation(self, method_name: str) -> str:
        method_lower = method_name.lower()
        for op, keywords in _OPERATION_KEYWORDS.items():
            if any(method_lower.startswith(kw) or kw in method_lower for kw in keywords):
                return op
        return "unknown"

    def _entity_from_class(self, class_name: str, path: str) -> str:
        class_lower = class_name.lower()
        # Check full path (package dirs reveal entity context)
        path_lower = path.lower().replace("\\", "/")
        for entity, keywords in _ENTITY_KEYWORDS.items():
            for kw in keywords:
                kw_l = kw.lower()
                if kw_l in class_lower:
                    return entity
                # Check last 3 path segments (package context)
                path_parts = path_lower.split("/")
                for part in path_parts[-4:]:
                    if kw_l in part:
                        return entity
        return ""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Singleton + cache
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_cached_graph: Optional[ExecutionGraph] = None
_graph_building: bool = False  # True while background thread is scanning


def get_execution_graph(force_refresh: bool = False) -> ExecutionGraph:
    """Return cached execution graph (lazy init with file cache).

    IMPORTANT: If no cache exists, starts a background thread to build it
    and returns an EMPTY graph immediately — never blocks the event loop.
    """
    global _cached_graph, _graph_building
    if _cached_graph is not None and not force_refresh:
        return _cached_graph

    # Try file cache
    if not force_refresh and _GRAPH_CACHE_FILE.exists():
        try:
            data = json.loads(_GRAPH_CACHE_FILE.read_text(encoding="utf-8"))
            _cached_graph = ExecutionGraph.from_dict(data)
            logger.info(
                f"[GraphExtractor] Loaded graph: {len(_cached_graph.nodes)} nodes, "
                f"{len(_cached_graph.operations)} operations from cache"
            )
            return _cached_graph
        except Exception as e:
            logger.warning(f"[GraphExtractor] Cache load failed: {e}")

    # No cache — start background extraction (non-blocking)
    if not _graph_building:
        _graph_building = True
        import threading

        def _build_in_background():
            global _cached_graph, _graph_building
            try:
                logger.info("[GraphExtractor] Starting background scan...")
                extractor = ExecutionGraphExtractor()
                graph = extractor.run()
                _cached_graph = graph
                # Save to cache
                try:
                    _GRAPH_CACHE_FILE.write_text(
                        json.dumps(graph.to_dict(), ensure_ascii=False, indent=None),
                        encoding="utf-8",
                    )
                    logger.info(
                        f"[GraphExtractor] Background scan complete: "
                        f"{len(graph.nodes)} nodes → {_GRAPH_CACHE_FILE.name}"
                    )
                except Exception as e:
                    logger.warning(f"[GraphExtractor] Cache save failed: {e}")
            except Exception as e:
                logger.error(f"[GraphExtractor] Background scan failed: {e}")
            finally:
                _graph_building = False

        t = threading.Thread(target=_build_in_background, daemon=True, name="graph-extractor")
        t.start()
        logger.info("[GraphExtractor] Background scan started — returning empty graph")

    # Return empty graph while building
    return ExecutionGraph(nodes={}, operations={}, exception_to_nodes={}, table_to_nodes={})


def search_execution_graph(
    exception: Optional[str] = None,
    operation: Optional[str] = None,
    entity: Optional[str] = None,
    table: Optional[str] = None,
    max_results: int = 5,
) -> List[ExecutionNode]:
    """
    Search the execution graph by exception, operation, entity, or table.
    Returns ranked list of matching ExecutionNodes.
    """
    graph = get_execution_graph()

    if exception:
        # Direct exception → node lookup (most precise)
        nodes = graph.find_nodes_by_exception(exception)
        if nodes:
            return nodes[:max_results]
        # Fallback: substring search
        nodes = [n for n in graph.nodes.values() if exception.lower() in " ".join(n.exceptions_thrown).lower()]
        return nodes[:max_results]

    if table:
        return graph.find_nodes_by_table(table)[:max_results]

    if operation or entity:
        return graph.find_nodes_by_operation(operation or "", entity or "")[:max_results]

    return []


def get_operation_path(operation: str) -> Optional[OperationPath]:
    """Get the full execution path for a known operation."""
    graph = get_execution_graph()
    return graph.get_operation_path(operation)
