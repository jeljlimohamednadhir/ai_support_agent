"""
timeline_builder.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Incident Timeline Engine — BRASIL Platform
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Builds chronological incident timelines from multi-source evidence:
  - StructuredLogEvidence (log parser output)
  - DbEvidence (live DB queries)
  - SshEvidence (remote command output)
  - FR resolution blocks (knowledge base)

Contract:
  - ONLY real evidence is used — never inferred / hallucinated
  - Events with no timestamp are appended last with label "??:??:??"
  - Duplicate events are merged by message similarity
  - Output is always deterministic for the same inputs
  - Never raises to the caller
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# TimelineEvent
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TimelineEvent:
    time:       str          # HH:MM:SS or "??:??:??" if unknown
    event:      str          # human description
    source:     str          # "log" | "db" | "ssh" | "fr"
    level:      str = "INFO" # ERROR / WARN / INFO
    details:    Optional[str] = None
    raw:        Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"time": self.time, "event": self.event, "source": self.source}
        if self.level != "INFO":
            d["level"] = self.level
        if self.details:
            d["details"] = self.details
        return d


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

_TIME_RX = re.compile(r"(\d{2}:\d{2}:\d{2}(?:[,\.]\d{1,3})?)")

def _extract_time(ts: Optional[str]) -> str:
    if not ts:
        return "??:??:??"
    m = _TIME_RX.search(ts)
    return m.group(1)[:8] if m else ts[:8]


def _sort_key(ev: TimelineEvent) -> str:
    """Sort key — events without time sink to bottom."""
    if ev.time == "??:??:??":
        return "ZZ:ZZ:ZZ"
    return ev.time


def _messages_similar(a: str, b: str) -> bool:
    """True if two event messages are 80%+ token-similar (cheap dedup)."""
    wa = set(a.lower().split())
    wb = set(b.lower().split())
    if not wa or not wb:
        return False
    overlap = len(wa & wb)
    return overlap / max(len(wa), len(wb)) >= 0.80


# ─────────────────────────────────────────────────────────────────────────────
# TimelineBuilder
# ─────────────────────────────────────────────────────────────────────────────

class TimelineBuilder:
    """
    Builds a chronological forensic incident timeline.

    Usage::

        builder = TimelineBuilder()
        timeline = builder.build(
            log_events=structured_log_events,
            db_evidence=bundle.db_evidence,
            ssh_evidence=bundle.ssh_evidence,
            fr_blocks=resolution_blocks,
        )
        for ev in timeline:
            print(ev.time, ev.event)
    """

    # Minimum correlation score for a log event to enter the timeline
    MIN_LOG_SCORE: float = 0.40

    def build(
        self,
        log_events:   List[Any] | None = None,   # List[StructuredLogEvidence]
        db_evidence:  Dict[str, Any] | None = None,
        ssh_evidence: List[Any] | None = None,
        fr_blocks:    List[Dict[str, Any]] | None = None,
        entity:       Optional[str] = None,
    ) -> List[TimelineEvent]:
        """
        Build timeline. Returns list sorted chronologically.

        Parameters
        ----------
        log_events   : output of LogParser.parse_lines()
        db_evidence  : DiagnosticBundle.db_evidence dict
        ssh_evidence : DiagnosticBundle.ssh_evidence list
        fr_blocks    : resolution blocks from reasoning_trace
        entity       : equipment name (for event labeling)
        """
        events: List[TimelineEvent] = []

        try:
            events.extend(self._from_logs(log_events or []))
        except Exception as e:
            logger.debug(f"[Timeline] log events failed: {e}")

        try:
            events.extend(self._from_db(db_evidence or {}, entity))
        except Exception as e:
            logger.debug(f"[Timeline] db evidence failed: {e}")

        try:
            events.extend(self._from_ssh(ssh_evidence or []))
        except Exception as e:
            logger.debug(f"[Timeline] ssh evidence failed: {e}")

        try:
            events.extend(self._from_fr(fr_blocks or []))
        except Exception as e:
            logger.debug(f"[Timeline] fr blocks failed: {e}")

        # Sort chronologically
        events.sort(key=_sort_key)

        # Dedup
        events = self._dedup(events)

        return events

    # ── Source handlers ───────────────────────────────────────────────────────

    def _from_logs(self, log_events: list) -> List[TimelineEvent]:
        result = []
        for ev in log_events:
            score = getattr(ev, "correlation_score", 0.0)
            if score < self.MIN_LOG_SCORE:
                continue

            level = getattr(ev, "level", None) or "INFO"
            ts = getattr(ev, "timestamp", None)
            time = _extract_time(ts)

            # Build event description from deterministic fields only
            parts = []
            exception = getattr(ev, "exception", None)
            error_code = getattr(ev, "error_code", None)
            equipment = getattr(ev, "equipment", None)
            eqpt_id = getattr(ev, "eqpt_id", None)
            message = getattr(ev, "message", "") or ""
            caused_by = getattr(ev, "caused_by", None)

            if exception:
                parts.append(exception)
            if error_code:
                parts.append(f"code={error_code}")
            if equipment:
                parts.append(f"équip={equipment}")
            elif eqpt_id is not None:
                parts.append(f"eqpt_id={eqpt_id}")

            # Short message — first 120 chars
            short_msg = message[:120].strip() if message else getattr(ev, "raw_line", "")[:80]
            if short_msg:
                parts.append(short_msg)

            event_text = "  ".join(parts) if parts else "Événement log détecté"

            details = None
            if caused_by and caused_by != exception:
                details = f"Caused by: {caused_by}"

            result.append(TimelineEvent(
                time=time,
                event=event_text,
                source="log",
                level=level if level in ("ERROR", "FATAL", "WARN") else "INFO",
                details=details,
                raw=getattr(ev, "raw_line", "")[:200],
            ))
        return result

    def _from_db(self, db_evidence: Dict[str, Any], entity: Optional[str]) -> List[TimelineEvent]:
        result = []
        for query_name, ev in db_evidence.items():
            has_data = getattr(ev, "has_data", False)
            row_count = getattr(ev, "row_count", 0)

            if row_count == 0:
                # Still interesting: no residuals = clean state
                result.append(TimelineEvent(
                    time="??:??:??",
                    event=f"DB [{query_name}] : aucune donnée résiduelle trouvée",
                    source="db",
                    level="INFO",
                ))
                continue

            # Build description from rows if available
            rows = getattr(ev, "rows", []) or []
            table = getattr(ev, "table", None) or query_name
            trunc = getattr(ev, "truncated", False)
            trunc_str = " (tronqué)" if trunc else ""

            event_text = (
                f"DB [{table}] : {row_count} enregistrement(s) résiduel(s)"
                f"{trunc_str}"
            )
            if entity:
                event_text += f" pour {entity}"

            # Add first row snippet if useful
            details = None
            if rows:
                first_row = rows[0]
                snippet = " | ".join(f"{k}={v}" for k, v in list(first_row.items())[:4])
                if snippet:
                    details = snippet[:200]

            result.append(TimelineEvent(
                time="??:??:??",
                event=event_text,
                source="db",
                level="WARN" if row_count > 0 else "INFO",
                details=details,
            ))
        return result

    def _from_ssh(self, ssh_evidence: list) -> List[TimelineEvent]:
        result = []
        for ev in ssh_evidence:
            success = getattr(ev, "success", False)
            cmd_name = getattr(ev, "command_name", "ssh_cmd")
            host = getattr(ev, "host", "?")
            output = getattr(ev, "output", "") or ""

            level = "INFO" if success else "ERROR"
            status = "OK" if success else "ERREUR"

            event_text = f"SSH [{cmd_name}] @ {host} : {status}"

            details = None
            if output and success:
                details = output[:200]

            result.append(TimelineEvent(
                time="??:??:??",
                event=event_text,
                source="ssh",
                level=level,
                details=details,
            ))
        return result

    def _from_fr(self, fr_blocks: List[Dict[str, Any]]) -> List[TimelineEvent]:
        result = []
        for block in fr_blocks:
            title = block.get("title") or block.get("fr_id") or "FR"
            content = block.get("content") or ""
            # Extract only step numbers as events
            steps = re.findall(r"(?m)^\s*(\d+)[.)]\s*(.+)$", content)
            if steps:
                for num, step in steps[:5]:
                    result.append(TimelineEvent(
                        time="??:??:??",
                        event=f"[FR] Étape {num}: {step[:120]}",
                        source="fr",
                        level="INFO",
                    ))
            else:
                result.append(TimelineEvent(
                    time="??:??:??",
                    event=f"[FR] {title[:120]}",
                    source="fr",
                    level="INFO",
                    details=content[:300] if content else None,
                ))
        return result

    # ── Dedup ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _dedup(events: List[TimelineEvent]) -> List[TimelineEvent]:
        """Remove near-duplicate events (same time + similar message)."""
        seen: List[TimelineEvent] = []
        for ev in events:
            is_dup = False
            for s in seen:
                if s.time == ev.time and _messages_similar(s.event, ev.event):
                    is_dup = True
                    break
            if not is_dup:
                seen.append(ev)
        return seen


# ─────────────────────────────────────────────────────────────────────────────
# Module-level convenience
# ─────────────────────────────────────────────────────────────────────────────

def build_timeline(
    log_events:   List[Any] | None = None,
    db_evidence:  Dict[str, Any] | None = None,
    ssh_evidence: List[Any] | None = None,
    fr_blocks:    List[Dict[str, Any]] | None = None,
    entity:       Optional[str] = None,
) -> List[TimelineEvent]:
    """Convenience wrapper around TimelineBuilder.build()."""
    return TimelineBuilder().build(
        log_events=log_events,
        db_evidence=db_evidence,
        ssh_evidence=ssh_evidence,
        fr_blocks=fr_blocks,
        entity=entity,
    )


def format_timeline_for_user(timeline: List[TimelineEvent]) -> str:
    """
    Format a timeline as user-facing forensic markdown.
    Exact data only — no summarization or hallucination.
    """
    if not timeline:
        return "_Aucun événement de timeline disponible._"

    lines = []
    lines.append("**⏱ Timeline d'incident**")
    lines.append("")
    for ev in timeline:
        icon = {"ERROR": "🔴", "FATAL": "⛔", "WARN": "🟡", "INFO": "🟢"}.get(ev.level, "⚪")
        src = f"[{ev.source.upper()}]"
        lines.append(f"`{ev.time}` {icon} {src} {ev.event}")
        if ev.details:
            lines.append(f"  ↳ `{ev.details[:150]}`")

    return "\n".join(lines)
