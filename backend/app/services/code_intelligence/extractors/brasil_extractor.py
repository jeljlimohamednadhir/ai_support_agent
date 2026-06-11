"""
brasil_extractor.py
━━━━━━━━━━━━━━━━━━━
Full BRASIL Java source code intelligence extractor.

Scans the brasil-default source tree and extracts:
- Exception hierarchy (class → parent → constraint semantics)
- Deletion constraints (what blocks DSLAM/VLAN/TP/Shelf deletion)
- Workflow states (DslamLifeState, MRT states, EPC states)
- SQL table references embedded in code
- Business rules (RF codes from comments)
- Error code mappings (label.* resource keys)

Output: List[CodeKnowledgeEntry] — deterministic, never sent raw to LLM.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

BRASIL_SOURCE_ROOT = os.getenv(
    "BRASIL_SOURCE_ROOT",
    str(Path(__file__).resolve().parents[5] / "brasil-default" / "brasil-default")
)

# ─────────────────────────────────────────────────────────────────────────────
# Data model
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CodeKnowledgeEntry:
    """Single unit of knowledge extracted from source code."""
    source: str = "code"
    application: str = "BRASIL"
    module: str = ""
    entity: str = ""
    trigger: str = ""
    root_cause: str = ""
    blocking_condition: str = ""
    exception_class: str = ""
    exception_parent: str = ""
    sql_tables: List[str] = field(default_factory=list)
    confidence: float = 0.95
    evidence_refs: List[str] = field(default_factory=list)
    resolution_hint: List[str] = field(default_factory=list)
    code_location: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    workflow_states: List[str] = field(default_factory=list)
    business_rule: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def embedding_text(self) -> str:
        """Text to embed in Qdrant for semantic search."""
        parts = []
        if self.exception_class:
            parts.append(f"Exception: {self.exception_class}")
        if self.entity:
            parts.append(f"Entity: {self.entity}")
        if self.blocking_condition:
            parts.append(f"Blocking: {self.blocking_condition}")
        if self.root_cause:
            parts.append(f"Cause: {self.root_cause}")
        if self.trigger:
            parts.append(f"Trigger: {self.trigger}")
        if self.business_rule:
            parts.append(f"Rule: {self.business_rule}")
        if self.sql_tables:
            parts.append(f"Tables: {', '.join(self.sql_tables)}")
        if self.resolution_hint:
            parts.append(f"Resolution: {'; '.join(self.resolution_hint)}")
        return " | ".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# Regex patterns
# ─────────────────────────────────────────────────────────────────────────────

_THROW_RX = re.compile(
    r'throw\s+new\s+(\w+Exception\w*)\s*\(\s*"([^"]*)"',
    re.MULTILINE
)

_EXCEPTION_CLASS_RX = re.compile(
    r'public\s+class\s+(\w+Exception\w*)\s+extends\s+(\w+)',
    re.MULTILINE
)

_STATE_CHECK_RX = re.compile(
    r'(?:getState|getStatus)\s*\(\s*\)\s*\.equals\s*\(\s*(\w+)\.(\w+)\s*\)',
    re.MULTILINE
)

_TABLE_RX = re.compile(
    r'\b(t_\w+|T_\w+)\b'
)

_RF_COMMENT_RX = re.compile(
    r'//\s*(RF\d+|FSC\s*\d+)[:\s]*(.+?)(?:\n|$)',
    re.IGNORECASE
)

_LABEL_RX = re.compile(
    r'"(label\.\w+Exception[^"]*)"'
)

_IMPORT_EXCEPTION_RX = re.compile(
    r'import\s+([\w.]+Exception\w*)\s*;'
)

_ENTITY_FROM_PATH_RX = re.compile(
    r'(?:dslam|vlan|card|shelf|port|stripe|node|epc|mrt|bay|distributor|'
    r'workOrder|supportLink|equipment|ce)',
    re.IGNORECASE
)


# ─────────────────────────────────────────────────────────────────────────────
# Extraction engine
# ─────────────────────────────────────────────────────────────────────────────

class BrasilCodeExtractor:
    """Statically scan BRASIL Java source and build structured knowledge."""

    def __init__(self, source_root: str = BRASIL_SOURCE_ROOT):
        self.source_root = Path(source_root)
        self._entries: List[CodeKnowledgeEntry] = []
        self._exception_hierarchy: Dict[str, str] = {}  # class -> parent
        self._exception_packages: Dict[str, str] = {}   # class -> package

    def run(self) -> List[CodeKnowledgeEntry]:
        """Full extraction pipeline."""
        if not self.source_root.exists():
            logger.warning(f"[CodeIntel] Source root not found: {self.source_root}")
            return []

        logger.info(f"[CodeIntel] Scanning {self.source_root} ...")

        # Phase 1: Build exception hierarchy
        self._scan_exception_classes()
        logger.info(f"[CodeIntel] Found {len(self._exception_hierarchy)} exception classes")

        # Phase 2: Scan business logic for throw sites, constraints, states
        self._scan_business_logic()
        logger.info(f"[CodeIntel] Extracted {len(self._entries)} knowledge entries")

        return self._entries

    # ── Phase 1: Exception hierarchy ─────────────────────────────────────────

    def _scan_exception_classes(self):
        """Build class → parent mapping for all *Exception*.java files."""
        for java_file in self.source_root.rglob("*Exception*.java"):
            try:
                content = java_file.read_text(encoding="utf-8", errors="replace")
                for m in _EXCEPTION_CLASS_RX.finditer(content):
                    cls_name = m.group(1)
                    parent = m.group(2)
                    self._exception_hierarchy[cls_name] = parent

                    # Extract package
                    pkg_match = re.search(r'^package\s+([\w.]+)\s*;', content)
                    if pkg_match:
                        self._exception_packages[cls_name] = pkg_match.group(1)

                    # Derive entity from package path
                    entity = self._entity_from_path(str(java_file))

                    # Build constraint semantics from class name
                    constraint = self._constraint_from_name(cls_name)

                    self._entries.append(CodeKnowledgeEntry(
                        module=self._module_from_path(str(java_file)),
                        entity=entity,
                        exception_class=cls_name,
                        exception_parent=parent,
                        blocking_condition=constraint,
                        root_cause=self._root_cause_from_exception(cls_name),
                        tags=self._tags_from_exception(cls_name, entity),
                        code_location={
                            "file": str(java_file.relative_to(self.source_root)),
                            "class": cls_name,
                        },
                        confidence=0.92,
                    ))
            except Exception as e:
                logger.debug(f"[CodeIntel] Skip {java_file.name}: {e}")

    # ── Phase 2: Business logic scan ────────────────────────────────────────

    def _scan_business_logic(self):
        """Scan Impl/Business files for throw sites, state checks, SQL tables."""
        patterns = ["*Impl.java", "*Business*.java", "*Service*.java", "*Manager*.java"]
        scanned: Set[Path] = set()

        for pattern in patterns:
            for java_file in self.source_root.rglob(pattern):
                if java_file in scanned:
                    continue
                scanned.add(java_file)
                try:
                    content = java_file.read_text(encoding="utf-8", errors="replace")
                    self._extract_throw_sites(java_file, content)
                    self._extract_state_checks(java_file, content)
                    self._extract_business_rules(java_file, content)
                except Exception as e:
                    logger.debug(f"[CodeIntel] Skip {java_file.name}: {e}")

    def _extract_throw_sites(self, java_file: Path, content: str):
        """Extract throw new XxxException("label...") sites."""
        for m in _THROW_RX.finditer(content):
            exc_class = m.group(1)
            label_key = m.group(2)

            # Find method context
            method = self._find_enclosing_method(content, m.start())
            entity = self._entity_from_path(str(java_file))

            # Find SQL tables in same method context
            method_start = content.rfind('{', 0, m.start())
            method_end = content.find('}', m.start())
            method_block = content[max(0, method_start):min(len(content), method_end + 200)]
            tables = list(set(_TABLE_RX.findall(method_block)))

            # Count line number
            line_no = content[:m.start()].count('\n') + 1

            self._entries.append(CodeKnowledgeEntry(
                module=self._module_from_path(str(java_file)),
                entity=entity,
                trigger=f"{method}()" if method else "",
                exception_class=exc_class,
                exception_parent=self._exception_hierarchy.get(exc_class, ""),
                blocking_condition=self._constraint_from_label(label_key),
                root_cause=self._root_cause_from_exception(exc_class),
                sql_tables=tables[:5],
                evidence_refs=[label_key] if label_key else [],
                code_location={
                    "file": str(java_file.relative_to(self.source_root)),
                    "class": java_file.stem,
                    "method": method or "",
                    "line": line_no,
                },
                tags=self._tags_from_exception(exc_class, entity),
                confidence=0.95,
            ))

    def _extract_state_checks(self, java_file: Path, content: str):
        """Extract state machine checks (getState().equals(Enum.VALUE))."""
        for m in _STATE_CHECK_RX.finditer(content):
            enum_class = m.group(1)
            state_value = m.group(2)
            entity = self._entity_from_path(str(java_file))
            method = self._find_enclosing_method(content, m.start())

            # Only create entries for states in conditional contexts
            self._entries.append(CodeKnowledgeEntry(
                module=self._module_from_path(str(java_file)),
                entity=entity,
                trigger=f"{method}()" if method else "",
                root_cause=f"state_check_{state_value.lower()}",
                blocking_condition=f"state must be {state_value} ({enum_class})",
                workflow_states=[f"{enum_class}.{state_value}"],
                code_location={
                    "file": str(java_file.relative_to(self.source_root)),
                    "class": java_file.stem,
                    "method": method or "",
                    "line": content[:m.start()].count('\n') + 1,
                },
                tags=[entity.lower(), "workflow", "state_machine"] if entity else ["workflow"],
                confidence=0.88,
            ))

    def _extract_business_rules(self, java_file: Path, content: str):
        """Extract RF/FSC business rule comments."""
        for m in _RF_COMMENT_RX.finditer(content):
            rule_id = m.group(1).strip()
            rule_desc = m.group(2).strip()
            entity = self._entity_from_path(str(java_file))

            self._entries.append(CodeKnowledgeEntry(
                module=self._module_from_path(str(java_file)),
                entity=entity,
                business_rule=f"{rule_id}: {rule_desc}",
                root_cause=f"rule_{rule_id.lower().replace(' ', '_')}",
                code_location={
                    "file": str(java_file.relative_to(self.source_root)),
                    "line": content[:m.start()].count('\n') + 1,
                },
                tags=[entity.lower(), "business_rule", rule_id.lower()] if entity else ["business_rule"],
                confidence=0.90,
            ))

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _entity_from_path(self, path: str) -> str:
        """Infer entity from file path — prefer the deepest/most-specific match."""
        path_lower = path.lower().replace("\\", "/")
        # Ordered by specificity (longer patterns first)
        _ENTITY_PRIORITY = [
            ("dslammanager", "DslamManager"),
            ("dslamshelf", "DslamShelf"),
            ("dslamcard", "DslamCard"),
            ("dslam", "Dslam"),
            ("vlaninterface", "VlanInterface"),
            ("vlan", "Vlan"),
            ("supportlink", "SupportLink"),
            ("sripinterface", "SrIpInterface"),
            ("workorder", "WorkOrder"),
            ("portgroup", "PortGroup"),
            ("stripe", "Stripe"),
            ("shelf", "Shelf"),
            ("card", "Card"),
            ("distributor", "Distributor"),
            ("node", "Node"),
            ("bay", "Bay"),
            ("mrt", "MRT"),
            ("epc", "EPC"),
            ("port", "Port"),
            ("equipment", "Equipment"),
            ("ce/", "CE"),
        ]
        # Check file name first (most reliable), then full path
        filename = path_lower.split("/")[-1]
        for token, entity in _ENTITY_PRIORITY:
            if token in filename:
                return entity
        for token, entity in _ENTITY_PRIORITY:
            if token in path_lower:
                return entity
        return ""

    def _module_from_path(self, path: str) -> str:
        """Extract Maven module name from path."""
        path_str = path.replace("\\", "/")
        for part in path_str.split("/"):
            if part.startswith("brasil-"):
                return part
        return "unknown"

    def _constraint_from_name(self, cls_name: str) -> str:
        """Derive human-readable constraint from exception class name."""
        # DslamDeleteConstraintException -> dslam cannot be deleted due to constraints
        name = cls_name.replace("Exception", "")
        # Split CamelCase
        parts = re.findall(r'[A-Z][a-z]+|[A-Z]+(?=[A-Z][a-z])', name)
        if not parts:
            return ""
        return " ".join(parts).lower()

    def _constraint_from_label(self, label: str) -> str:
        """Extract constraint description from label key."""
        if not label:
            return ""
        # label.dslamDeleteConstraintException.dslam.supportLink
        # -> support link prevents dslam deletion
        parts = label.replace("label.", "").split(".")
        return " ".join(parts).replace("Exception", "").lower()

    def _root_cause_from_exception(self, cls_name: str) -> str:
        """Map exception class to root cause category."""
        name = cls_name.lower()
        if "deleteconstraint" in name:
            return "delete_blocked_by_constraint"
        elif "notfound" in name:
            return "entity_not_found"
        elif "unicityconstraint" in name or "uniqueconstraint" in name:
            return "duplicate_entity"
        elif "closedforproduction" in name:
            return "closed_for_production"
        elif "incoherent" in name or "incompatible" in name:
            return "state_incoherent"
        elif "mapping" in name:
            return "mapping_error"
        elif "toomanyfound" in name:
            return "ambiguous_search"
        elif "notfree" in name or "alreadyused" in name or "occupied" in name:
            return "resource_already_occupied"
        elif "saturated" in name or "threshold" in name:
            return "resource_exhausted"
        elif "functional" in name or "rule" in name or "validation" in name:
            return "business_rule_violation"
        elif "technical" in name or "internal" in name:
            return "technical_error"
        return "constraint_violation"

    def _tags_from_exception(self, cls_name: str, entity: str) -> List[str]:
        """Generate tags from exception class and entity."""
        tags = []
        if entity:
            tags.append(entity.lower())
        name = cls_name.lower()
        if "delete" in name:
            tags.append("deletion")
        if "constraint" in name:
            tags.append("constraint")
        if "vlan" in name:
            tags.append("vlan")
        if "dslam" in name:
            tags.append("dslam")
        if "card" in name:
            tags.append("card")
        if "shelf" in name:
            tags.append("shelf")
        if "port" in name:
            tags.append("port")
        if "mrt" in name:
            tags.append("mrt")
        if "epc" in name:
            tags.append("epc")
        if "workorder" in name:
            tags.append("workorder")
        if "vp" in name or "vc" in name:
            tags.append("network_resource")
        return tags

    def _find_enclosing_method(self, content: str, pos: int) -> str:
        """Find the method name that encloses position `pos`."""
        # Search backward for method signature
        chunk = content[max(0, pos - 2000):pos]
        matches = list(re.finditer(
            r'(?:public|private|protected)\s+\w+(?:<[^>]+>)?\s+(\w+)\s*\(',
            chunk
        ))
        if matches:
            return matches[-1].group(1)
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# Module-level singleton runner
# ─────────────────────────────────────────────────────────────────────────────

_cached_entries: Optional[List[CodeKnowledgeEntry]] = None
_CACHE_FILE = Path(__file__).resolve().parent.parent / "code_knowledge_cache.json"


def get_code_knowledge(force_refresh: bool = False) -> List[CodeKnowledgeEntry]:
    """Return cached code knowledge entries (lazy init with file cache)."""
    global _cached_entries
    if _cached_entries is not None and not force_refresh:
        return _cached_entries

    # Try loading from file cache first (fast: ~0.5s vs 64s full scan)
    if not force_refresh and _CACHE_FILE.exists():
        try:
            import json
            data = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
            _cached_entries = [CodeKnowledgeEntry(**d) for d in data]
            logger.info(f"[CodeIntel] Loaded {len(_cached_entries)} entries from cache")
            return _cached_entries
        except Exception as e:
            logger.warning(f"[CodeIntel] Cache load failed: {e}")

    # Full scan
    extractor = BrasilCodeExtractor()
    _cached_entries = extractor.run()

    # Persist to file cache
    try:
        import json
        _CACHE_FILE.write_text(
            json.dumps([e.to_dict() for e in _cached_entries], ensure_ascii=False),
            encoding="utf-8"
        )
        logger.info(f"[CodeIntel] Cached {len(_cached_entries)} entries to {_CACHE_FILE.name}")
    except Exception as e:
        logger.warning(f"[CodeIntel] Cache write failed: {e}")

    return _cached_entries


def search_code_knowledge(
    exception: Optional[str] = None,
    entity: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> List[CodeKnowledgeEntry]:
    """Filter cached knowledge by exception/entity/tags."""
    entries = get_code_knowledge()
    results = []
    for e in entries:
        if exception and exception.lower() not in e.exception_class.lower():
            continue
        if entity and entity.lower() not in e.entity.lower():
            continue
        if tags and not any(t in e.tags for t in tags):
            continue
        results.append(e)
    return results[:50]
