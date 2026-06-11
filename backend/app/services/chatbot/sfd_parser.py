"""
Layer 1 — SFD HTML Parser
===========================
Converts BRASIL SFD HTML specification files into structured JSON knowledge.

Extracts:
  - entities (Equipment, DSLAM, ONT, Card, Port, Node, etc.)
  - attributes per entity
  - constraints (business rules, validation rules)
  - API operations (methods, parameters, return values)

Output: list of SFDDocument objects, serializable to JSON.
Integrated into reasoning as PRIMARY SOURCE OF TRUTH.

Note: if no SFD files are present, the parser uses the knowledge already
extracted by brasil_knowledge_pipeline.py (brasil_entities.json,
brasil_constraints.json) as a fallback SFD-equivalent source.
"""
from __future__ import annotations

import re
import json
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any

# BeautifulSoup is optional — graceful degradation
try:
    from bs4 import BeautifulSoup  # type: ignore
    _BS4_AVAILABLE = True
except ImportError:
    _BS4_AVAILABLE = False


# ─────────────────────────────────────────────────────────────────────────────
# Data models
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SFDEntity:
    name: str
    entity_type: str
    attributes: List[str] = field(default_factory=list)
    source_file: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "entity_type": self.entity_type,
            "attributes": self.attributes,
            "source_file": self.source_file,
        }


@dataclass
class SFDConstraint:
    rule_id: str
    description: str
    affected_entities: List[str] = field(default_factory=list)
    severity: str = "blocking"   # blocking | warning
    source_file: str = ""

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "description": self.description,
            "affected_entities": self.affected_entities,
            "severity": self.severity,
            "source_file": self.source_file,
        }


@dataclass
class SFDOperation:
    name: str
    method: str          # GET | POST | PUT | DELETE
    path: str
    parameters: List[str] = field(default_factory=list)
    description: str = ""
    source_file: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "method": self.method,
            "path": self.path,
            "parameters": self.parameters,
            "description": self.description,
            "source_file": self.source_file,
        }


@dataclass
class SFDDocument:
    file_id: str
    source_file: str
    title: str
    entities: List[SFDEntity] = field(default_factory=list)
    constraints: List[SFDConstraint] = field(default_factory=list)
    operations: List[SFDOperation] = field(default_factory=list)
    raw_text_excerpt: str = ""

    def to_dict(self) -> dict:
        return {
            "file_id": self.file_id,
            "source_file": self.source_file,
            "title": self.title,
            "entities": [e.to_dict() for e in self.entities],
            "constraints": [c.to_dict() for c in self.constraints],
            "operations": [o.to_dict() for o in self.operations],
            "raw_text_excerpt": self.raw_text_excerpt[:500],
        }


# ─────────────────────────────────────────────────────────────────────────────
# Pattern-based extractors (used when BS4 unavailable or plain text)
# ─────────────────────────────────────────────────────────────────────────────

_ENTITY_WORDS = re.compile(
    r"\b(DSLAM|MSAN|ONT|OLT|GPON|CARD|PORT|SHELF|NODE|NRA|NRO|"
    r"EQUIPMENT|EPC|MRT|CCL|VLAN|MAKING.?FILE|OPERATOR|TSF|VP|VC)\b",
    re.I,
)

_CONSTRAINT_KEYWORDS = re.compile(
    r"(obligatoire|mandatory|interdit|forbidden|impossible|"
    r"cannot|must not|bloqué|ne peut pas|shall not|doit|must be|"
    r"error|erreur|exception|contrainte|constraint|validation)",
    re.I,
)

_HTTP_METHODS = re.compile(r"\b(GET|POST|PUT|DELETE|PATCH)\b")
_API_PATH = re.compile(r"(/[a-zA-Z0-9/_\-\{\}]{5,80})")


def _extract_text_entities(text: str, source: str) -> List[SFDEntity]:
    entities: List[SFDEntity] = []
    seen = set()
    for m in _ENTITY_WORDS.finditer(text):
        name = m.group(0).upper()
        if name not in seen:
            seen.add(name)
            entities.append(SFDEntity(
                name=name,
                entity_type=name,
                attributes=[],
                source_file=source,
            ))
    return entities


def _extract_text_constraints(text: str, source: str) -> List[SFDConstraint]:
    constraints: List[SFDConstraint] = []
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if _CONSTRAINT_KEYWORDS.search(line) and len(line.strip()) > 15:
            uid = hashlib.md5(line.encode()).hexdigest()[:8].upper()
            entities = [m.group(0).upper() for m in _ENTITY_WORDS.finditer(line)]
            constraints.append(SFDConstraint(
                rule_id=f"SFD-{uid}",
                description=line.strip()[:200],
                affected_entities=list(set(entities)),
                severity="blocking",
                source_file=source,
            ))
    return constraints


def _extract_text_operations(text: str, source: str) -> List[SFDOperation]:
    operations: List[SFDOperation] = []
    for m_method in _HTTP_METHODS.finditer(text):
        # Look for a path near the method
        nearby = text[m_method.start():m_method.start() + 200]
        path_m = _API_PATH.search(nearby)
        if path_m:
            operations.append(SFDOperation(
                name=f"{m_method.group(0)} {path_m.group(0)}",
                method=m_method.group(0),
                path=path_m.group(0),
                source_file=source,
            ))
    return operations


# ─────────────────────────────────────────────────────────────────────────────
# Main parser
# ─────────────────────────────────────────────────────────────────────────────

class SFDParser:
    """
    Parses SFD HTML files from a directory.
    Falls back to brasil_entities.json + brasil_constraints.json if no HTML found.
    """

    def __init__(
        self,
        sfd_dir: Optional[Path] = None,
        fallback_data_dir: Optional[Path] = None,
    ):
        self.sfd_dir = sfd_dir
        self.fallback_data_dir = fallback_data_dir or Path(__file__).parents[3] / "data"
        self._documents: List[SFDDocument] = []
        self._loaded = False

    def load(self) -> List[SFDDocument]:
        if self._loaded:
            return self._documents

        html_files: List[Path] = []
        if self.sfd_dir and self.sfd_dir.exists():
            html_files = list(self.sfd_dir.glob("**/*.html")) + list(self.sfd_dir.glob("**/*.htm"))

        if html_files:
            for html_file in html_files:
                doc = self._parse_html_file(html_file)
                if doc:
                    self._documents.append(doc)
        else:
            # Fallback: load brasil_entities.json + brasil_constraints.json
            self._documents = self._load_from_pipeline_outputs()

        self._loaded = True
        return self._documents

    def get_all_constraints(self) -> List[SFDConstraint]:
        docs = self.load()
        result = []
        for doc in docs:
            result.extend(doc.constraints)
        return result

    def get_all_entities(self) -> List[SFDEntity]:
        docs = self.load()
        result = []
        for doc in docs:
            result.extend(doc.entities)
        return result

    def get_entity_by_name(self, name: str) -> Optional[SFDEntity]:
        for entity in self.get_all_entities():
            if entity.name.upper() == name.upper():
                return entity
        return None

    def validate_operation(self, operation: str, entity_name: str) -> tuple[bool, str]:
        """
        Check if operation is allowed on entity per SFD constraints.
        Returns (is_valid, reason).
        """
        constraints = self.get_all_constraints()
        op_upper = operation.upper()
        entity_upper = entity_name.upper()

        for cstr in constraints:
            if entity_upper in [e.upper() for e in cstr.affected_entities]:
                desc_upper = cstr.description.upper()
                if "DELETE" in op_upper or "SUPPRIMER" in op_upper:
                    if any(kw in desc_upper for kw in ["CANNOT DELETE", "NE PEUT PAS", "INTERDIT", "FORBIDDEN", "BLOCKED"]):
                        return False, cstr.description
        return True, "OK"

    def to_context_block(self, entity_name: Optional[str] = None) -> str:
        """Return a compact text block for LLM context injection."""
        lines = ["## SFD SOURCE OF TRUTH"]
        constraints = self.get_all_constraints()
        if entity_name:
            constraints = [c for c in constraints if entity_name.upper() in [e.upper() for e in c.affected_entities]]

        if constraints:
            lines.append("### Relevant Constraints:")
            for c in constraints[:10]:
                lines.append(f"- [{c.rule_id}] {c.description}")

        entities = self.get_all_entities()
        if entity_name:
            entities = [e for e in entities if e.name.upper() == entity_name.upper()]
        if entities[:5]:
            lines.append("### Known Entities:")
            for e in entities[:5]:
                lines.append(f"- {e.name} ({e.entity_type}): attrs={e.attributes[:5]}")

        return "\n".join(lines)

    # ── Private ──────────────────────────────────────────────────────────────

    def _parse_html_file(self, path: Path) -> Optional[SFDDocument]:
        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return None

        if _BS4_AVAILABLE:
            soup = BeautifulSoup(raw, "html.parser")
            title = soup.title.string if soup.title else path.stem
            text = soup.get_text(separator="\n", strip=True)
        else:
            # Strip HTML tags
            text = re.sub(r"<[^>]+>", " ", raw)
            text = re.sub(r"\s+", " ", text)
            title = path.stem

        file_id = hashlib.md5(str(path).encode()).hexdigest()[:8].upper()
        return SFDDocument(
            file_id=file_id,
            source_file=str(path),
            title=title,
            entities=_extract_text_entities(text, str(path)),
            constraints=_extract_text_constraints(text, str(path)),
            operations=_extract_text_operations(text, str(path)),
            raw_text_excerpt=text[:1000],
        )

    def _load_from_pipeline_outputs(self) -> List[SFDDocument]:
        """Build SFD-equivalent docs from brasil_knowledge_pipeline.py outputs."""
        docs: List[SFDDocument] = []

        # Load entities
        entities_file = self.fallback_data_dir / "brasil_entities.json"
        sfd_entities: List[SFDEntity] = []
        if entities_file.exists():
            try:
                data = json.loads(entities_file.read_text(encoding="utf-8"))
                for e in data.get("entities", []):
                    sfd_entities.append(SFDEntity(
                        name=e.get("name", ""),
                        entity_type=e.get("type", "UNKNOWN"),
                        attributes=e.get("columns", e.get("attributes", [])),
                        source_file="brasil_entities.json",
                    ))
            except Exception:
                pass

        # Load constraints
        constraints_file = self.fallback_data_dir / "brasil_constraints.json"
        sfd_constraints: List[SFDConstraint] = []
        if constraints_file.exists():
            try:
                data = json.loads(constraints_file.read_text(encoding="utf-8"))
                for c in data.get("constraints", []):
                    sfd_constraints.append(SFDConstraint(
                        rule_id=c.get("id", "SFD-???"),
                        description=c.get("description", ""),
                        affected_entities=c.get("affected_entities", []),
                        severity=c.get("severity", "blocking"),
                        source_file="brasil_constraints.json",
                    ))
            except Exception:
                pass

        if sfd_entities or sfd_constraints:
            docs.append(SFDDocument(
                file_id="BRASIL-DB-SFD",
                source_file="brasil_knowledge_pipeline_output",
                title="BRASIL Database + FR Specification (Auto-extracted)",
                entities=sfd_entities,
                constraints=sfd_constraints,
                operations=[],
                raw_text_excerpt="Auto-extracted from brasil_db.sql + FR docs via knowledge pipeline",
            ))

        return docs


# ─────────────────────────────────────────────────────────────────────────────
# Singleton (lazy-loaded)
# ─────────────────────────────────────────────────────────────────────────────

_DATA_DIR = Path(__file__).parents[3] / "data"
_SFD_DIR  = _DATA_DIR.parent / "data" / "sfd"   # /data/sfd/ if exists

sfd_parser = SFDParser(
    sfd_dir=_SFD_DIR if _SFD_DIR.exists() else None,
    fallback_data_dir=_DATA_DIR,
)
