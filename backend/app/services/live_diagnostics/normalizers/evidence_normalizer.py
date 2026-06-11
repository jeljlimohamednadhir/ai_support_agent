"""
evidence_normalizer.py
━━━━━━━━━━━━━━━━━━━━━━
Converts raw DB results into structured, typed evidence objects.
No raw SQL results are ever exposed to the LLM.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.services.live_diagnostics.models.evidence import DbEvidence, EvidenceType

logger = logging.getLogger(__name__)


class EvidenceNormalizer:
    """
    Converts raw DbEvidence rows into semantically rich structured evidence.

    Each normalizer method:
      - reads the DbEvidence rows
      - produces a summary dict with semantic fields
      - sets confidence based on data quality
    """

    def normalize_equipment_id(self, ev: DbEvidence) -> Dict[str, Any]:
        """get_equipment_id -> {eqpt_id, eqpt_name, eqpt_status, found}"""
        if not ev.has_data:
            return {"found": False, "eqpt_id": None, "eqpt_name": None, "eqpt_status": None}
        row = ev.rows[0]
        return {
            "found":       True,
            "eqpt_id":     row.get("eqpt_id"),
            "eqpt_name":   row.get("eqpt_name"),
            "eqpt_status": row.get("eqpt_status"),
            "eqpt_type":   row.get("eqpt_type"),
        }

    def normalize_residual_references(self, ev: DbEvidence) -> Dict[str, Any]:
        """
        check_residual_references -> {has_residuals, table_counts, total}
        """
        if not ev.has_data:
            return {"has_residuals": False, "table_counts": {}, "total": 0}

        table_counts: Dict[str, int] = {}
        total = 0
        for row in ev.rows:
            src = row.get("src", "?")
            cnt = int(row.get("cnt", 0))
            table_counts[src] = cnt
            total += cnt

        return {
            "has_residuals": total > 0,
            "table_counts":  table_counts,
            "total":         total,
            "evidence_type": EvidenceType.LIVE_DB.value,
            "confidence":    0.98,
        }

    def normalize_active_services(self, ev: DbEvidence) -> Dict[str, Any]:
        """check_active_services -> {has_active_services, count, statuses}"""
        if not ev.has_data:
            return {"has_active_services": False, "count": 0}
        statuses = list({r.get("svc_status") for r in ev.rows})
        return {
            "has_active_services": True,
            "count":               ev.row_count,
            "statuses":            statuses,
            "evidence_type":       EvidenceType.LIVE_DB.value,
            "confidence":          0.97,
        }

    def normalize_mrt_links(self, ev: DbEvidence) -> Dict[str, Any]:
        if not ev.has_data:
            return {"has_active_links": False, "count": 0}
        return {
            "has_active_links": True,
            "count":            ev.row_count,
            "truncated":        ev.truncated,
            "evidence_type":    EvidenceType.LIVE_DB.value,
            "confidence":       0.96,
        }

    def normalize_vc_counters(self, ev: DbEvidence) -> Dict[str, Any]:
        if not ev.has_data:
            return {"has_occupied_vc": False, "count": 0}
        return {
            "has_occupied_vc": True,
            "count":           ev.row_count,
            "types":           list({r.get("vc_type") for r in ev.rows}),
            "evidence_type":   EvidenceType.LIVE_DB.value,
            "confidence":      0.96,
        }

    def normalize_blocked_tps(self, ev: DbEvidence) -> Dict[str, Any]:
        if not ev.has_data:
            return {"has_blocked_tp": False, "tp_ids": []}
        tp_ids = [r.get("tp_id") for r in ev.rows]
        return {
            "has_blocked_tp": True,
            "tp_ids":         tp_ids,
            "count":          ev.row_count,
            "evidence_type":  EvidenceType.LIVE_DB.value,
            "confidence":     0.97,
        }

    def normalize_shared_ports(self, ev: DbEvidence) -> Dict[str, Any]:
        if not ev.has_data:
            return {"has_shared_ports": False, "count": 0}
        return {
            "has_shared_ports": True,
            "count":            ev.row_count,
            "port_ids":         [r.get("b_port_id") for r in ev.rows],
            "evidence_type":    EvidenceType.LIVE_DB.value,
            "confidence":       0.96,
        }

    def normalize_port_remarks_anomaly(self, ev: DbEvidence) -> Dict[str, Any]:
        if not ev.has_data:
            return {"has_charset_anomaly": False, "count": 0}
        equipments = list({r.get("eqpt_name") for r in ev.rows})
        return {
            "has_charset_anomaly": True,
            "count":               ev.row_count,
            "affected_equipments": equipments[:10],
            "evidence_type":       EvidenceType.LIVE_DB.value,
            "confidence":          0.93,
        }

    def normalize_blocked_dlm(self, ev: DbEvidence) -> Dict[str, Any]:
        if not ev.has_data:
            return {"has_blocked_dlm": False, "count": 0}
        return {
            "has_blocked_dlm": True,
            "count":           ev.row_count,
            "dlm_ids":         [r.get("dlm_id") for r in ev.rows[:10]],
            "evidence_type":   EvidenceType.LIVE_DB.value,
            "confidence":      0.95,
        }

    # ── Generic dispatcher ────────────────────────────────────────────────────

    _DISPATCH = {
        "get_equipment_id":          "normalize_equipment_id",
        "check_equipment_status":    "normalize_equipment_id",
        "check_residual_references": "normalize_residual_references",
        "check_active_services":     "normalize_active_services",
        "check_mrt_dslam_links":     "normalize_mrt_links",
        "check_vc_counters":         "normalize_vc_counters",
        "get_blocked_tps":           "normalize_blocked_tps",
        "check_shared_port_links":   "normalize_shared_ports",
        "check_port_remarks_anomaly":"normalize_port_remarks_anomaly",
        "check_blocked_dlm":         "normalize_blocked_dlm",
    }

    def normalize(self, ev: DbEvidence) -> Dict[str, Any]:
        """Dispatch normalization based on query_name."""
        method_name = self._DISPATCH.get(ev.query_name)
        if method_name:
            method = getattr(self, method_name, None)
            if method:
                return method(ev)
        # Generic fallback
        return {
            "query_name":    ev.query_name,
            "row_count":     ev.row_count,
            "has_data":      ev.has_data,
            "evidence_type": EvidenceType.LIVE_DB.value,
            "confidence":    ev.confidence,
        }

    def normalize_all(
        self, evidence_map: Dict[str, DbEvidence]
    ) -> Dict[str, Dict[str, Any]]:
        """Normalize a full evidence map from execute_plan()."""
        return {name: self.normalize(ev) for name, ev in evidence_map.items()}
