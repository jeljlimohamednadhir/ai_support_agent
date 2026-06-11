"""
Multi-Source Correlation Engine — Phase 3
==========================================
Fuses evidence from all chatbot intelligence sources and produces a ranked
list of CorrelationHypothesis objects.  These are injected as an extra
context block into the LLM prompt so the model can answer with cross-source
consistency.

Usage (from chatbot_service.py)::

    from app.services.chatbot.multi_source_correlator import MultiSourceCorrelator
    ...
    correlator = MultiSourceCorrelator()
    hypotheses = correlator.correlate(
        user_message=user_message,
        kb_blocks=kb_blocks,          # list[dict] from KB/RAG
        jira_tickets=jira_tickets,    # list[dict] from Jira
        log_entries=log_entries,      # list[dict] from log analysis
        diagnostic=diagnostic_result, # dict from DiagnosticEngine
        ml_result=ml_result,          # dict from ML classifier
    )
    context_block = correlator.to_context_block(hypotheses)
"""
from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ───────────────────────────── Data model ─────────────────────────── #

@dataclass
class Evidence:
    source: str          # "kb" | "jira" | "log" | "diagnostic" | "ml"
    snippet: str         # human-readable excerpt
    confidence: float    # 0.0 – 1.0
    metadata: dict = field(default_factory=dict)


@dataclass
class CorrelationHypothesis:
    label: str                       # short description, e.g. "PPPoE auth failure"
    confidence: float                # combined, 0.0 – 1.0
    evidence: list[Evidence] = field(default_factory=list)
    recommended_action: str = ""
    source_agreement: float = 0.0    # fraction of sources that support this

    @property
    def supporting_sources(self) -> list[str]:
        return list({e.source for e in self.evidence})

    def add_evidence(self, ev: Evidence) -> None:
        self.evidence.append(ev)
        # Recalculate combined confidence as weighted average
        total_w = sum(e.confidence for e in self.evidence)
        self.confidence = total_w / len(self.evidence) if self.evidence else 0.0


# ─────────────────────────── Signal extractors ────────────────────── #

_RE_TICKET_STATUS = re.compile(r"\b(open|in.progress|resolved|closed|pending)\b", re.I)
_RE_CAUSE_WORDS   = re.compile(
    r"\b(auth|pppoe|dhcp|vlan|fibre|coupure|synchronisation|alerte|"
    r"d[ée]faut|panne|timeout|erreur|exception|overflow|loop|storm)\b",
    re.I,
)
_RE_COMPONENT     = re.compile(
    r"\b(dslam|olt|ont|bsau|nenic|nro\w*|sro\w*|bng|bras|"
    r"adsl|vdsl|gpon|xgspon|ftth|ftto)\b",
    re.I,
)

# Keyword → hypothesis label mapping (order matters — first match wins per keyword)
_KEYWORD_HYPOTHESES: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r"\b(pppoe|auth.*fail|mot de passe|password)\b", re.I),
     "PPPoE authentication failure",
     "Verify AAA server reachability and credentials"),
    (re.compile(r"\b(fibre|coupure|cut|signal|attn?[ué]ation|dbm)\b", re.I),
     "Optical link degradation / fibre cut",
     "Dispatch field tech to measure optical budget"),
    (re.compile(r"\b(synchronis|synchro|vdsl|adsl|dsl.*train|train.*dsl)\b", re.I),
     "DSL sync instability",
     "Check line profile, SNR margin, DSLAM firmware"),
    (re.compile(r"\b(vlan|tag|qinq|trunk|802\.1q)\b", re.I),
     "VLAN mismatch / misconfiguration",
     "Verify end-to-end VLAN provisioning"),
    (re.compile(r"\b(dhcp|ip.*adress|adresse.*ip|lease|pool)\b", re.I),
     "DHCP pool exhaustion or misconfiguration",
     "Check DHCP pool usage and scope settings"),
    (re.compile(r"\b(loop|storm|broadcast|stp|spanning)\b", re.I),
     "Layer-2 loop / broadcast storm",
     "Enable STP BPDUguard; check port MAC counts"),
    (re.compile(r"\b(timeout|latence|latency|d[ée]lai|ping.*loss|loss.*ping)\b", re.I),
     "High latency / packet loss",
     "Run traceroute; check QoS queues and buffering"),
    (re.compile(r"\b(overflow|heap|java|exception|crash|restart)\b", re.I),
     "Software exception / process crash",
     "Collect thread dump; apply hotfix if available"),
    (re.compile(r"\b(provision|activ|d[ée]sactiv|ONT.*creat|GPON.*activ)\b", re.I),
     "Provisioning / activation error",
     "Re-check service order; re-push OLT configuration"),
    (re.compile(r"\b(alerte|alarm|seuil|threshold|major|minor|critical)\b", re.I),
     "Network alarm threshold exceeded",
     "Acknowledge alarm; open P1 incident if service-affecting"),
]


def _text_of(obj: Any) -> str:
    """Flatten any dict / list / str into a single searchable string."""
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        return " ".join(_text_of(v) for v in obj.values())
    if isinstance(obj, list):
        return " ".join(_text_of(i) for i in obj)
    return str(obj) if obj else ""


# ───────────────────────── Correlator class ───────────────────────── #

class MultiSourceCorrelator:
    """
    Lightweight, dependency-free correlator.  All computation is O(n) regex
    matching — no ML model required.  Average latency < 5 ms for typical
    chatbot payloads.
    """

    MAX_HYPOTHESES = 4   # maximum number of hypotheses returned
    MIN_CONFIDENCE = 0.15

    # ---------------------------------------------------------------- #

    def correlate(
        self,
        user_message: str = "",
        kb_blocks: list[dict] | None = None,
        jira_tickets: list[dict] | None = None,
        log_entries: list[dict] | None = None,
        diagnostic: dict | None = None,
        ml_result: dict | None = None,
    ) -> list[CorrelationHypothesis]:
        """
        Fuse all available signals and return ranked hypotheses.
        """
        kb_blocks     = kb_blocks     or []
        jira_tickets  = jira_tickets  or []
        log_entries   = log_entries   or []
        diagnostic    = diagnostic    or {}
        ml_result     = ml_result     or {}

        total_sources = sum([
            bool(kb_blocks), bool(jira_tickets),
            bool(log_entries), bool(diagnostic), bool(ml_result),
        ])

        # Collect all text corpora
        all_text = " ".join([
            user_message,
            _text_of(kb_blocks),
            _text_of(jira_tickets),
            _text_of(log_entries),
            _text_of(diagnostic),
            _text_of(ml_result),
        ])

        # Map: hypothesis_label → CorrelationHypothesis
        hypo_map: dict[str, CorrelationHypothesis] = {}

        # ── Step 1: keyword-driven hypotheses ─────────────────────── #
        for pattern, label, action in _KEYWORD_HYPOTHESES:
            matches = pattern.findall(all_text)
            if not matches:
                continue
            if label not in hypo_map:
                hypo_map[label] = CorrelationHypothesis(
                    label=label,
                    confidence=0.0,
                    recommended_action=action,
                )
            hypo = hypo_map[label]
            # Attribute evidence per source
            for src_name, src_text in [
                ("user",       user_message),
                ("kb",         _text_of(kb_blocks)),
                ("jira",       _text_of(jira_tickets)),
                ("log",        _text_of(log_entries)),
                ("diagnostic", _text_of(diagnostic)),
                ("ml",         _text_of(ml_result)),
            ]:
                if src_text and pattern.search(src_text):
                    keyword_hit = pattern.search(src_text).group(0)
                    snippet = self._extract_snippet(src_text, keyword_hit, 120)
                    conf = self._source_confidence(src_name, matches, len(src_text))
                    hypo.add_evidence(Evidence(
                        source=src_name,
                        snippet=snippet,
                        confidence=conf,
                        metadata={"keyword": keyword_hit},
                    ))

        # ── Step 2: ML result agreement ───────────────────────────── #
        if ml_result:
            ml_label    = ml_result.get("label") or ml_result.get("predicted_label", "")
            ml_conf_raw = float(ml_result.get("confidence", ml_result.get("score", 0.5)))
            for hypo in hypo_map.values():
                # Loose match: any keyword in ml_label overlaps hypothesis label
                if any(w in ml_label.lower() for w in hypo.label.lower().split()):
                    hypo.add_evidence(Evidence(
                        source="ml",
                        snippet=f"ML classifier: {ml_label} ({ml_conf_raw:.0%})",
                        confidence=ml_conf_raw,
                        metadata={"ml_label": ml_label},
                    ))

        # ── Step 3: Jira recurrence signal ────────────────────────── #
        if jira_tickets:
            component_hits: dict[str, int] = {}
            for ticket in jira_tickets:
                t_text = _text_of(ticket)
                for m in _RE_COMPONENT.findall(t_text):
                    component_hits[m.upper()] = component_hits.get(m.upper(), 0) + 1
            for comp, count in component_hits.items():
                recurrence_label = f"Recurring issue on {comp}"
                if recurrence_label not in hypo_map and count >= 2:
                    hypo_map[recurrence_label] = CorrelationHypothesis(
                        label=recurrence_label,
                        confidence=min(0.4 + 0.1 * count, 0.85),
                        recommended_action=f"Investigate {comp} history; check firmware/config drift",
                    )
                    hypo_map[recurrence_label].add_evidence(Evidence(
                        source="jira",
                        snippet=f"{count} Jira tickets mention {comp}",
                        confidence=min(0.4 + 0.1 * count, 0.85),
                        metadata={"component": comp, "count": count},
                    ))

        # ── Step 4: Diagnostic engine critical findings ────────────── #
        if diagnostic:
            diag_findings = diagnostic.get("critical_findings") or diagnostic.get("findings", [])
            for finding in (diag_findings if isinstance(diag_findings, list) else []):
                finding_text = _text_of(finding)
                label = f"Diagnostic: {finding_text[:60].rstrip()}"
                if label not in hypo_map:
                    hypo_map[label] = CorrelationHypothesis(
                        label=label,
                        confidence=0.75,
                        recommended_action=diagnostic.get("recommended_action", "Follow diagnostic procedure"),
                    )
                    hypo_map[label].add_evidence(Evidence(
                        source="diagnostic",
                        snippet=finding_text[:200],
                        confidence=0.75,
                        metadata={},
                    ))

        # ── Step 5: Source agreement scoring ──────────────────────── #
        result: list[CorrelationHypothesis] = []
        for hypo in hypo_map.values():
            if hypo.confidence < self.MIN_CONFIDENCE:
                continue
            if total_sources > 0:
                hypo.source_agreement = len(hypo.supporting_sources) / total_sources
            result.append(hypo)

        # Sort by (source_agreement DESC, confidence DESC)
        result.sort(key=lambda h: (h.source_agreement, h.confidence), reverse=True)
        return result[: self.MAX_HYPOTHESES]

    # ---------------------------------------------------------------- #
    # Helpers                                                           #
    # ---------------------------------------------------------------- #

    @staticmethod
    def _extract_snippet(text: str, keyword: str, max_len: int) -> str:
        """Return a short window of text around the keyword."""
        idx = text.lower().find(keyword.lower())
        if idx == -1:
            return text[:max_len]
        start = max(0, idx - max_len // 3)
        end   = min(len(text), idx + max_len * 2 // 3)
        snippet = text[start:end].strip()
        if start > 0:
            snippet = "…" + snippet
        if end < len(text):
            snippet = snippet + "…"
        return snippet

    @staticmethod
    def _source_confidence(source: str, matches: list, text_len: int) -> float:
        """Heuristic confidence per source type."""
        base = {
            "user":       0.5,
            "kb":         0.7,
            "jira":       0.65,
            "log":        0.8,
            "diagnostic": 0.85,
            "ml":         0.75,
        }.get(source, 0.5)
        # More matches → slightly higher confidence (diminishing returns)
        boost = min(0.1 * len(matches), 0.2)
        return min(base + boost, 1.0)

    # ---------------------------------------------------------------- #
    # Output formatter                                                  #
    # ---------------------------------------------------------------- #

    def to_context_block(
        self, hypotheses: list[CorrelationHypothesis], max_chars: int = 800
    ) -> str:
        """
        Render hypotheses as a concise text block to inject into the LLM prompt.
        Returns an empty string if there are no meaningful hypotheses.
        """
        if not hypotheses:
            return ""

        lines: list[str] = [
            "=== CROSS-SOURCE CORRELATION ANALYSIS ===",
        ]
        for i, hypo in enumerate(hypotheses, 1):
            sources_str = ", ".join(sorted(hypo.supporting_sources))
            lines.append(
                f"{i}. [{hypo.confidence:.0%} conf | sources: {sources_str}] "
                f"{hypo.label}"
            )
            if hypo.recommended_action:
                lines.append(f"   → {hypo.recommended_action}")
            # Show top 2 evidence snippets
            for ev in hypo.evidence[:2]:
                snippet = ev.snippet[:100].replace("\n", " ")
                lines.append(f"   [{ev.source}] {snippet}")
        lines.append("==========================================")
        block = "\n".join(lines)
        return block[:max_chars]
