"""
log_normalizer.py
━━━━━━━━━━━━━━━━━
Convert raw LogEvidence into structured, LLM-safe evidence dicts.
Never exposes raw log lines to the LLM.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.services.live_diagnostics.models.evidence import EvidenceType, LogEvidence
from app.services.live_diagnostics.logs.log_patterns import (
    get_pattern_for_error_code,
    get_pattern_for_exception,
)


class LogNormalizer:

    def normalize(self, ev: LogEvidence) -> Dict[str, Any]:
        """Return structured dict safe for LLM context (no raw lines)."""

        # Enrich with pattern knowledge
        pattern_infos = []
        for code in ev.error_codes:
            info = get_pattern_for_error_code(code)
            if info:
                pattern_infos.append({
                    "error_code":    code,
                    "exception":     info.get("exception"),
                    "root_cause":    info.get("root_cause"),
                    "description":   info.get("description"),
                    "resolution_fr": info.get("resolution_fr"),
                })

        for exc in ev.exceptions:
            info = get_pattern_for_exception(exc)
            if info:
                pattern_infos.append({
                    "exception":   exc,
                    "root_cause":  info.get("root_cause"),
                    "description": info.get("description"),
                })

        return {
            "evidence_type":        EvidenceType.LIVE_LOG.value,
            "log_file":             ev.log_file,
            "search_pattern":       ev.search_pattern,
            "match_count":          ev.match_count,
            "error_codes":          ev.error_codes,
            "exceptions":           ev.exceptions,
            "detected_constraints": ev.detected_constraints,
            "severity":             ev.severity,
            "confidence":           ev.confidence,
            "patterns_matched":     pattern_infos,
            "has_data":             ev.has_data,
            # Summary for LLM (no raw lines)
            "summary": self._build_summary(ev, pattern_infos),
        }

    @staticmethod
    def _build_summary(ev: LogEvidence, patterns: List[Dict]) -> str:
        if not ev.has_data:
            return f"Aucune occurrence de '{ev.search_pattern}' trouvée dans {ev.log_file}."

        parts = [f"{ev.match_count} ligne(s) trouvée(s) pour '{ev.search_pattern}'."]

        if ev.error_codes:
            parts.append(f"Codes d'erreur détectés : {', '.join(ev.error_codes)}.")
        if ev.exceptions:
            parts.append(f"Exceptions : {', '.join(ev.exceptions)}.")
        if ev.detected_constraints:
            parts.append(f"Contraintes : {', '.join(ev.detected_constraints[:3])}.")
        if patterns:
            for p in patterns[:2]:
                rc = p.get("root_cause", "?")
                desc = p.get("description", "")
                fr = p.get("resolution_fr", "")
                parts.append(f"Cause racine probable : {rc}. {desc}.")
                if fr:
                    parts.append(f"FR de résolution : {fr}.")

        return " ".join(parts)

    def normalize_all(self, evidence_list: List[LogEvidence]) -> List[Dict[str, Any]]:
        return [self.normalize(ev) for ev in evidence_list]
