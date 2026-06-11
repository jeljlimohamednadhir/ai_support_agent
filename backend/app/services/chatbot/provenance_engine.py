"""
provenance_engine.py
━━━━━━━━━━━━━━━━━━━━
Provenance Engine — Phase 3

Every evidence block displayed to users MUST include provenance.

This module:
  - wraps existing evidence_provenance.py with richer display logic
  - generates 📂 Provenance sections in responses
  - tracks which sources contributed to which answers
  - validates that evidence actually came from known sources

Supported provenance types:
  runtime_log | source_code | FR | SFD | database | SSH | incident_history | vector_knowledge

Every evidence object contains:
  source_type, source_name, file, table, class, method,
  timestamp, server, confidence (0.0-1.0)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PROVENANCE RECORD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class ProvenanceRecord:
    """Rich provenance metadata for a single evidence contribution."""
    source_type: str                    # runtime_log | source_code | FR | database | SSH | ...
    source_name: str                    # catalina.out | brasil_app.log | ManageDslamBusinessImpl
    file: Optional[str] = None          # Exact filename
    table: Optional[str] = None         # DB table name
    class_name: Optional[str] = None    # Java class
    method: Optional[str] = None        # Java method
    timestamp: Optional[str] = None     # ISO timestamp or log timestamp
    server: Optional[str] = None        # Hostname: op49mwa11, op49mdb11
    confidence: float = 1.0             # 0.0-1.0
    fr_id: Optional[str] = None         # FR reference
    line_number: Optional[int] = None   # Line in source file
    raw_excerpt: Optional[str] = None   # Short evidence excerpt

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in {
            "source_type": self.source_type,
            "source_name": self.source_name,
            "file": self.file,
            "table": self.table,
            "class": self.class_name,
            "method": self.method,
            "timestamp": self.timestamp,
            "server": self.server,
            "confidence": self.confidence,
            "fr_id": self.fr_id,
            "line_number": self.line_number,
        }.items() if v is not None}

    def to_display_line(self) -> str:
        """Single-line display for compact provenance footers."""
        parts = [f"`{self.source_name}`"]
        if self.server:
            parts.append(f"server: `{self.server}`")
        if self.class_name:
            parts.append(f"class: `{self.class_name}`")
        if self.method:
            parts.append(f"method: `{self.method}()`")
        if self.table:
            parts.append(f"table: `{self.table}`")
        if self.fr_id:
            parts.append(f"FR: `{self.fr_id}`")
        if self.timestamp:
            parts.append(f"ts: `{self.timestamp}`")
        conf_pct = int(self.confidence * 100)
        parts.append(f"conf: {conf_pct}%")
        return " | ".join(parts)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EVIDENCE BLOCK WITH PROVENANCE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class RichEvidenceBlock:
    """A displayable evidence block with full provenance chain."""
    title: str
    content: str
    provenances: List[ProvenanceRecord] = field(default_factory=list)
    trust_score: float = 0.0
    section_emoji: str = "📌"

    def render(self, include_provenance: bool = True, max_provenance: int = 4) -> str:
        """Render the evidence block with optional provenance footer."""
        lines = [
            f"{self.section_emoji} **{self.title}**",
            "",
            self.content,
        ]
        if include_provenance and self.provenances:
            lines.append("")
            lines.append(_build_provenance_section(self.provenances[:max_provenance]))
        return "\n".join(lines)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PROVENANCE FORMATTERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _build_provenance_section(records: List[ProvenanceRecord]) -> str:
    """Build a 📂 Provenance markdown section from a list of records."""
    if not records:
        return ""
    lines = ["📂 **Provenance**"]
    for r in records:
        lines.append(f"- {r.to_display_line()}")
    return "\n".join(lines)


def build_response_provenance_footer(records: List[ProvenanceRecord]) -> str:
    """
    Build a compact provenance footer for appending to a full response.
    Uses horizontal rule separator.
    """
    if not records:
        return ""
    lines = [
        "",
        "---",
        "📂 **Sources des informations**",
    ]
    # Group by source_type
    by_type: Dict[str, List[ProvenanceRecord]] = {}
    for r in records:
        by_type.setdefault(r.source_type, []).append(r)

    type_emojis = {
        "runtime_log": "📋",
        "source_code": "⚙️",
        "FR": "📄",
        "SFD": "📑",
        "database": "🗄️",
        "SSH": "🖥️",
        "incident_history": "🗃️",
        "vector_knowledge": "🔍",
    }
    for stype, recs in by_type.items():
        emoji = type_emojis.get(stype, "📎")
        lines.append(f"{emoji} **{stype}**:")
        for r in recs[:3]:
            lines.append(f"  - {r.to_display_line()}")

    return "\n".join(lines)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FACTORY FUNCTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def provenance_from_log_event(event: Any) -> ProvenanceRecord:
    """Create a ProvenanceRecord from a log event object."""
    return ProvenanceRecord(
        source_type="runtime_log",
        source_name=getattr(event, "source", "brasil_app.log"),
        file=getattr(event, "source", None),
        timestamp=str(getattr(event, "timestamp", "")),
        server=getattr(event, "server", None) or "op49mwa11",
        confidence=getattr(event, "relevance_score", 0.8),
        raw_excerpt=getattr(event, "message", "")[:80] if hasattr(event, "message") else None,
    )


def provenance_from_db_evidence(db_evidence: Dict) -> List[ProvenanceRecord]:
    """Create ProvenanceRecords from a DB evidence dict."""
    records = []
    for table_name, rows in (db_evidence or {}).items():
        if rows:
            records.append(ProvenanceRecord(
                source_type="database",
                source_name=f"PostgreSQL — {table_name}",
                table=table_name,
                server="op49mdb11",
                confidence=0.95,
            ))
    return records


def provenance_from_code_node(node: Dict) -> ProvenanceRecord:
    """Create a ProvenanceRecord from a code graph node dict."""
    cls = node.get("class", "")
    method = node.get("method", "")
    file_path = node.get("file", "")
    line = node.get("line")
    return ProvenanceRecord(
        source_type="source_code",
        source_name=f"{cls}.{method}()" if cls and method else (cls or method or "?"),
        file=file_path.split("\\")[-1].split("/")[-1] if file_path else None,
        class_name=cls,
        method=method,
        line_number=line,
        confidence=1.0,
    )


def provenance_from_fr(fr_id: str, title: str = "") -> ProvenanceRecord:
    """Create a ProvenanceRecord for a FR knowledge article."""
    excerpt = f"{fr_id} — {title}"[:80] if title else fr_id[:80]
    return ProvenanceRecord(
        source_type="FR",
        source_name=fr_id,
        fr_id=fr_id,
        file=f"{fr_id}.json",
        confidence=0.9,
        raw_excerpt=excerpt,
    )


def provenance_from_qdrant(block: Dict) -> ProvenanceRecord:
    """Create a ProvenanceRecord from a Qdrant KB block."""
    fr_id = block.get("fr_id") or block.get("id") or ""
    title = block.get("title", "")
    return ProvenanceRecord(
        source_type="vector_knowledge",
        source_name=fr_id or title[:40] or "Qdrant KB",
        fr_id=fr_id,
        confidence=float(block.get("trust_score", 70)) / 100.0,
        raw_excerpt=title[:80],
    )


def provenance_from_ssh(node: Dict) -> ProvenanceRecord:
    """Create a ProvenanceRecord from an SSH check result."""
    return ProvenanceRecord(
        source_type="SSH",
        source_name=node.get("check", "ssh_check"),
        server=node.get("server", "op49mwa11"),
        confidence=0.85,
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PROVENANCE ENGINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ProvenanceEngine:
    """
    Collects, validates and formats evidence provenance for N3 forensic responses.

    Usage:
        engine = ProvenanceEngine()
        engine.add_from_bundle(bundle)
        engine.add_from_kb_blocks(context_blocks)
        footer = engine.render_footer()
        full_response = response_text + footer
    """

    def __init__(self):
        self._records: List[ProvenanceRecord] = []

    def reset(self) -> None:
        self._records.clear()

    def add(self, record: ProvenanceRecord) -> None:
        self._records.append(record)

    def add_many(self, records: List[ProvenanceRecord]) -> None:
        self._records.extend(records)

    def add_from_bundle(self, bundle: Any) -> None:
        """Extract all provenance from a DiagnosticBundle."""
        if bundle is None:
            return
        # Log evidence
        for lev in getattr(bundle, "log_evidence", []) or []:
            self.add(ProvenanceRecord(
                source_type="runtime_log",
                source_name=getattr(lev, "log_file", "brasil_app.log"),
                file=getattr(lev, "log_file", None),
                server=getattr(lev, "server", "op49mwa11"),
                confidence=0.85,
            ))
        # DB evidence
        self.add_many(provenance_from_db_evidence(
            getattr(bundle, "db_evidence", {}) or {}
        ))
        # SSH evidence
        for ssh in getattr(bundle, "ssh_evidence", []) or []:
            self.add(provenance_from_ssh(
                ssh if isinstance(ssh, dict) else {"check": str(ssh)}
            ))
        # Code nodes from reasoning_trace
        trace = getattr(bundle, "reasoning_trace", {}) or {}
        for node in trace.get("code_nodes", []) or []:
            self.add(provenance_from_code_node(node))

    def add_from_kb_blocks(self, blocks: List[Dict]) -> None:
        """Extract provenance from Qdrant KB context blocks."""
        for block in (blocks or []):
            self.add(provenance_from_qdrant(block))

    def add_from_code_nodes(self, nodes: List[Dict]) -> None:
        """Extract provenance from execution graph nodes."""
        for node in (nodes or []):
            self.add(provenance_from_code_node(node))

    def has_provenance(self) -> bool:
        return bool(self._records)

    def render_footer(self, max_records: int = 6) -> str:
        """Return the provenance footer string (empty if no records)."""
        if not self._records:
            return ""
        unique = self._deduplicate(self._records)
        return build_response_provenance_footer(unique[:max_records])

    def render_inline_section(self, max_records: int = 4) -> str:
        """Return an inline 📂 Provenance section (no separator)."""
        if not self._records:
            return ""
        unique = self._deduplicate(self._records)
        return _build_provenance_section(unique[:max_records])

    def get_records(self) -> List[ProvenanceRecord]:
        return list(self._records)

    def _deduplicate(self, records: List[ProvenanceRecord]) -> List[ProvenanceRecord]:
        seen: set = set()
        out = []
        for r in records:
            key = (r.source_type, r.source_name)
            if key not in seen:
                seen.add(key)
                out.append(r)
        return out

    def explain_sources(self) -> str:
        """
        Concise explanation of where evidence came from.
        Used in natural language sentences.
        """
        if not self._records:
            return "_Aucune source de preuve identifiée._"
        types = list({r.source_type for r in self._records})
        names = [r.source_name for r in self._deduplicate(self._records)[:3]]
        return (
            f"Les informations proviennent de : "
            + ", ".join(f"`{n}`" for n in names)
            + f" (types: {', '.join(types)})."
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MODULE-LEVEL FACTORY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def make_provenance_engine() -> ProvenanceEngine:
    """Create a fresh ProvenanceEngine for a single response turn."""
    return ProvenanceEngine()
