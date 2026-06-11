"""
evidence_provenance.py
━━━━━━━━━━━━━━━━━━━━━━
Structured provenance model for all forensic evidence.

Every piece of evidence displayed to the user MUST carry provenance
metadata that makes it traceable to its source.

Design:
  - Lightweight dataclass — zero runtime cost
  - Serializable to JSON and Markdown
  - Attached to log events, DB results, code intelligence, FR blocks
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class SourceType(str, Enum):
    LIVE_LOG = "LIVE_LOG"       # SSH grep / log extraction
    LIVE_DB = "LIVE_DB"         # PostgreSQL diagnostic query
    CODE = "CODE"               # Source code execution graph
    FR = "FR"                   # Fiche de résolution (KB)
    INCIDENT = "INCIDENT"       # Jira / incident history
    QDRANT = "QDRANT"           # Vector retrieval
    SSH = "SSH"                 # Raw SSH command output
    CORRELATION = "CORRELATION" # Computed correlation hypothesis
    CACHE = "CACHE"             # From local cache (not live)


@dataclass
class EvidenceProvenance:
    """
    Provenance metadata for a single piece of evidence.

    Fields:
      source_type:       Category of evidence source
      source_file:       Log file name, Java source file, FR id, etc.
      timestamp:         Timestamp of the evidence event (from log/DB)
      host:              Server host where evidence was collected
      query:             SQL query or grep pattern used
      line_number:       Line number in source file
      collected_at:      ISO timestamp when evidence was fetched
      correlation_score: Relevance/confidence score (0.0-1.0)
      raw_excerpt:       First N chars of raw evidence text
    """
    source_type: SourceType
    source_file: str = ""
    timestamp: str = ""
    host: str = ""
    query: str = ""
    line_number: int = 0
    collected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))
    correlation_score: float = 0.0
    raw_excerpt: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["source_type"] = self.source_type.value
        return d

    def to_footer_line(self) -> str:
        """Single-line provenance for display in forensic responses."""
        parts = [f"[{self.source_type.value}]"]
        if self.host:
            parts.append(f"host={self.host}")
        if self.source_file:
            parts.append(self.source_file)
        if self.line_number:
            parts.append(f"L{self.line_number}")
        if self.timestamp:
            parts.append(f"@{self.timestamp}")
        if self.correlation_score > 0:
            parts.append(f"score={self.correlation_score:.0%}")
        return " | ".join(parts)

    def to_markdown_badge(self) -> str:
        """Compact markdown badge for inline provenance."""
        icon = {
            SourceType.LIVE_LOG: "📋",
            SourceType.LIVE_DB: "🗄️",
            SourceType.CODE: "📌",
            SourceType.FR: "📘",
            SourceType.INCIDENT: "🎫",
            SourceType.QDRANT: "🔍",
            SourceType.SSH: "🖥️",
            SourceType.CORRELATION: "🔗",
            SourceType.CACHE: "💾",
        }.get(self.source_type, "📎")
        ref = self.source_file or self.host or self.source_type.value
        return f"{icon}`{ref}`"


@dataclass
class EvidenceBlock:
    """
    A block of evidence with full provenance.
    Used throughout the pipeline to carry evidence + metadata.
    """
    title: str
    content: str
    provenance: EvidenceProvenance
    trust_score: float = 0.0
    # Context for LLM injection (bounded)
    context_for_llm: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "content": self.content[:500],
            "provenance": self.provenance.to_dict(),
            "trust_score": self.trust_score,
        }

    def to_display(self, max_content: int = 300) -> str:
        """Format for user display with provenance footer."""
        lines = [f"**{self.title}**"]
        if self.content:
            lines.append(self.content[:max_content])
        lines.append(f"_({self.provenance.to_footer_line()})_")
        return "\n".join(lines)


# ── Factory helpers ───────────────────────────────────────────────────────────

def provenance_from_log(
    log_file: str,
    host: str = "",
    timestamp: str = "",
    grep_pattern: str = "",
    score: float = 0.0,
) -> EvidenceProvenance:
    return EvidenceProvenance(
        source_type=SourceType.LIVE_LOG,
        source_file=log_file,
        host=host or _default_log_host(log_file),
        timestamp=timestamp,
        query=grep_pattern,
        correlation_score=score,
    )


def provenance_from_db(
    query: str,
    host: str = "op49mdb11",
    table: str = "",
) -> EvidenceProvenance:
    return EvidenceProvenance(
        source_type=SourceType.LIVE_DB,
        source_file=table,
        host=host,
        query=query[:200],
    )


def provenance_from_code(
    file_path: str,
    line_number: int = 0,
    method: str = "",
) -> EvidenceProvenance:
    return EvidenceProvenance(
        source_type=SourceType.CODE,
        source_file=file_path.split("\\")[-1].split("/")[-1],
        line_number=line_number,
        query=method,
    )


def provenance_from_fr(fr_id: str, title: str = "") -> EvidenceProvenance:
    return EvidenceProvenance(
        source_type=SourceType.FR,
        source_file=fr_id,
        query=title[:100],
    )


def provenance_from_qdrant(
    collection: str,
    score: float = 0.0,
    doc_id: str = "",
) -> EvidenceProvenance:
    return EvidenceProvenance(
        source_type=SourceType.QDRANT,
        source_file=collection,
        query=doc_id,
        correlation_score=score,
    )


# ── Provenance footer builder ────────────────────────────────────────────────

def build_provenance_footer(provenances: List[EvidenceProvenance], max_lines: int = 5) -> str:
    """
    Build a compact provenance footer for the end of a forensic response.
    
    Output:
      ---
      📎 Sources: [LIVE_DB] host=op49mdb11 | t_equipments | score=92%
                  [LIVE_LOG] host=op49mwa11 | catalina.out | @14:32:01
                  [CODE] DslamDeletionValidator.java | L45
    """
    if not provenances:
        return ""
    lines = ["", "---", "📎 **Sources:**"]
    for prov in provenances[:max_lines]:
        lines.append(f"  {prov.to_footer_line()}")
    return "\n".join(lines)


def _default_log_host(log_file: str) -> str:
    """Infer host from log file name."""
    if "brasil" in log_file.lower() or "catalina" in log_file.lower():
        return "op49mwa11"
    if "connector" in log_file.lower():
        return "op49mwa11"
    if "postgres" in log_file.lower() or "pg_" in log_file.lower():
        return "op49mdb11"
    return ""
