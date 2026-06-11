"""
models/evidence.py
━━━━━━━━━━━━━━━━━━
Shared evidence data models for all live diagnostic sources.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class EvidenceType(str, Enum):
    LIVE_DB   = "live_db"
    LIVE_LOG  = "live_log"
    SSH       = "ssh"
    CODE      = "code"       # reserved – Phase 2
    FR        = "fr"
    SFD       = "sfd"
    INCIDENT  = "incident"
    LEARNED   = "learned"


# Weighted truth hierarchy (higher = more trusted)
EVIDENCE_WEIGHTS: Dict[EvidenceType, int] = {
    EvidenceType.LIVE_DB:  100,
    EvidenceType.LIVE_LOG:  90,
    EvidenceType.SSH:       85,
    EvidenceType.CODE:      80,   # Phase 2
    EvidenceType.SFD:       70,
    EvidenceType.FR:        60,
    EvidenceType.INCIDENT:  50,
    EvidenceType.LEARNED:   30,
}


@dataclass
class DbEvidence:
    """Evidence derived from a live read-only database query."""
    evidence_type: EvidenceType
    query_name:    str
    rows:          List[Dict[str, Any]]
    row_count:     int
    error:         Optional[str]
    confidence:    float              # 0.0 – 1.0
    truncated:     bool               # True if row_count == max_rows
    tags:          List[str] = field(default_factory=list)
    # Optional normalised summary fields
    table:         Optional[str] = None
    residual_rows: Optional[int] = None
    eqpt_id:       Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_type":  self.evidence_type.value,
            "query_name":     self.query_name,
            "row_count":      self.row_count,
            "truncated":      self.truncated,
            "confidence":     self.confidence,
            "error":          self.error,
            "tags":           self.tags,
            "table":          self.table,
            "residual_rows":  self.residual_rows,
            "eqpt_id":        self.eqpt_id,
            "rows":           self.rows,
        }

    @property
    def has_data(self) -> bool:
        return self.row_count > 0 and not self.error

    @property
    def weight(self) -> int:
        return EVIDENCE_WEIGHTS[self.evidence_type]


@dataclass
class LogEvidence:
    """Evidence derived from live server log analysis."""
    evidence_type:        EvidenceType
    log_file:             str
    search_pattern:       str
    matched_lines:        List[str]
    match_count:          int
    error_codes:          List[str]
    exceptions:           List[str]
    detected_constraints: List[str]
    confidence:           float
    error:                Optional[str] = None
    severity:             str = "UNKNOWN"   # HIGH / MEDIUM / LOW / UNKNOWN
    tags:                 List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_type":        self.evidence_type.value,
            "log_file":             self.log_file,
            "search_pattern":       self.search_pattern,
            "match_count":          self.match_count,
            "error_codes":          self.error_codes,
            "exceptions":           self.exceptions,
            "detected_constraints": self.detected_constraints,
            "confidence":           self.confidence,
            "severity":             self.severity,
            "error":                self.error,
        }

    @property
    def has_data(self) -> bool:
        return self.match_count > 0 and not self.error

    @property
    def weight(self) -> int:
        return EVIDENCE_WEIGHTS[self.evidence_type]


@dataclass
class SshEvidence:
    """Evidence derived from an SSH remote command execution."""
    evidence_type:  EvidenceType
    command_name:   str
    host:           str
    success:        bool
    output:         str
    error:          str
    duration_ms:    float
    confidence:     float
    tags:           List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_type": self.evidence_type.value,
            "command_name":  self.command_name,
            "host":          self.host,
            "success":       self.success,
            "output":        self.output[:2000],   # truncate for safety
            "error":         self.error,
            "duration_ms":   self.duration_ms,
            "confidence":    self.confidence,
        }

    @property
    def has_data(self) -> bool:
        return self.success and bool(self.output)

    @property
    def weight(self) -> int:
        return EVIDENCE_WEIGHTS[self.evidence_type]


@dataclass
class CodeEvidence:
    """
    Evidence derived from source code intelligence (Phase 2).
    Populated by code_intelligence module when BRASIL_SOURCE_ROOT is set.
    """
    evidence_type:   EvidenceType = EvidenceType.CODE
    operation:       Optional[str] = None
    source_file:     Optional[str] = None
    method:          Optional[str] = None
    validations:     List[Dict] = field(default_factory=list)
    dependencies:    List[str]  = field(default_factory=list)
    queries:         List[str]  = field(default_factory=list)
    exceptions:      List[str]  = field(default_factory=list)
    confidence:      float = 0.0
    enabled:         bool  = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_type": self.evidence_type.value,
            "enabled":       self.enabled,
            "operation":     self.operation,
            "source_file":   self.source_file,
            "method":        self.method,
            "validations":   self.validations[:5],
            "dependencies":  self.dependencies[:5],
            "exceptions":    self.exceptions[:5],
        }

    @property
    def has_data(self) -> bool:
        return self.enabled and bool(self.validations or self.dependencies)

    @property
    def weight(self) -> int:
        return EVIDENCE_WEIGHTS[self.evidence_type]


@dataclass
class DiagnosticBundle:
    """
    Complete evidence bundle for one user request.
    Passed to the correlation engine.
    """
    intent:          str
    entity:          Optional[str]
    db_evidence:     Dict[str, DbEvidence]   = field(default_factory=dict)
    log_evidence:    List[LogEvidence]        = field(default_factory=list)
    ssh_evidence:    List[SshEvidence]        = field(default_factory=list)
    code_evidence:   Optional[CodeEvidence]   = None
    debug_mode:      bool = False
    reasoning_trace: Dict[str, Any] = field(default_factory=dict)

    def all_evidence(self) -> list:
        ev = list(self.db_evidence.values()) + self.log_evidence + self.ssh_evidence
        if self.code_evidence and self.code_evidence.has_data:
            ev.append(self.code_evidence)
        return ev

    def highest_confidence(self) -> float:
        all_ev = self.all_evidence()
        if not all_ev:
            return 0.0
        return max(e.confidence for e in all_ev if hasattr(e, "confidence"))

    def to_context_blocks(self) -> list:
        """Convert evidence into chatbot context_blocks format.

        SSH evidence is excluded from this output — it is a system health check,
        not a diagnostic proof, and should never appear in the "Preuves DB" section.
        """
        blocks = []
        for ev in self.all_evidence():
            if not ev.has_data:
                continue
            # Skip SSH evidence — shown separately if needed
            if getattr(ev, 'evidence_type', None) in (EvidenceType.SSH,):
                continue
            d = ev.to_dict()
            blocks.append({
                "title":        f"[{d['evidence_type'].upper()}] Diagnostic",
                "content":      _format_evidence_content(d),
                "trust_score":  round(ev.confidence * 100),
                "source_type":  d["evidence_type"],
                "type":         "live_diagnostic",
            })
        return blocks

    def to_ssh_summary(self) -> list:
        """Return SSH evidence as compact status lines (for separate display)."""
        lines = []
        for ev in self.ssh_evidence:
            if not ev.has_data:
                continue
            ok = "✅" if ev.success else "❌"
            lines.append(f"{ok} `{ev.command_name}` sur `{ev.host}`")
        return lines


@dataclass
class StructuredLogEvidence:
    """
    Single structured log event — output of LogParser.
    Mirrors log_parser.StructuredLogEvidence but lives in evidence.py
    for cross-service imports without circular dependency.
    Prefer importing from log_parser directly; use this for bundles.
    """
    timestamp:         Optional[str]       = None
    level:             Optional[str]       = None
    source:            Optional[str]       = None
    equipment:         Optional[str]       = None
    exception:         Optional[str]       = None
    message:           str                 = ""
    error_code:        Optional[str]       = None
    correlation_score: float               = 0.0
    raw_line:          str                 = ""
    eqpt_id:           Optional[int]       = None
    stack_frames:      List[str]           = field(default_factory=list)
    caused_by:         Optional[str]       = None

    def to_compact_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {}
        if self.timestamp:  d["timestamp"]  = self.timestamp
        if self.level:      d["level"]      = self.level
        if self.source:     d["source"]     = self.source
        if self.equipment:  d["equipment"]  = self.equipment
        if self.exception:  d["exception"]  = self.exception
        d["message"] = self.message[:300]
        if self.error_code: d["error_code"] = self.error_code
        d["correlation_score"] = round(self.correlation_score, 3)
        if self.eqpt_id is not None: d["eqpt_id"] = self.eqpt_id
        if self.caused_by:  d["caused_by"]  = self.caused_by
        if self.stack_frames: d["stack_frames"] = self.stack_frames[:5]
        return d

    def to_forensic_line(self) -> str:
        parts = []
        if self.timestamp: parts.append(f"[{self.timestamp}]")
        if self.level:     parts.append(self.level)
        if self.exception: parts.append(self.exception)
        if self.error_code: parts.append(f"code={self.error_code}")
        if self.equipment: parts.append(f"eqpt={self.equipment}")
        if self.eqpt_id is not None: parts.append(f"eqpt_id={self.eqpt_id}")
        parts.append((self.message or self.raw_line)[:200])
        return "  ".join(parts)

    @property
    def has_data(self) -> bool:
        return bool(self.message or self.exception or self.error_code)

    @property
    def weight(self) -> int:
        return EVIDENCE_WEIGHTS.get(EvidenceType.LIVE_LOG, 90)


def _format_evidence_content(d: Dict[str, Any]) -> str:
    """Human-readable summary of evidence for LLM context (no raw data)."""
    et = d.get("evidence_type", "?")
    if et == "live_db":
        rows = d.get("row_count", 0)
        qn   = d.get("query_name", "?")
        trunc = " (tronqué)" if d.get("truncated") else ""
        if rows == 0:
            return f"Requête {qn} : aucune donnée résiduelle trouvée."
        return f"Requête {qn} : {rows} enregistrement(s) trouvé(s){trunc}."
    elif et == "live_log":
        n = d.get("match_count", 0)
        codes = ", ".join(d.get("error_codes", [])) or "N/A"
        exc   = ", ".join(d.get("exceptions", [])) or "N/A"
        return f"Logs : {n} ligne(s) correspondante(s). Codes: {codes}. Exceptions: {exc}."
    elif et == "ssh":
        ok = "OK" if d.get("success") else "ERREUR"
        return f"Commande SSH [{d.get('command_name','?')}] : {ok}."
    return str(d)
