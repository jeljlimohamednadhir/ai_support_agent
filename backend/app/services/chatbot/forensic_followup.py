"""
forensic_followup.py
━━━━━━━━━━━━━━━━━━━━
Handles forensic follow-up queries using conversation context.

When a user asks "montre les logs", "quelle contrainte bloque", etc.
AFTER a diagnostic, this module retrieves the relevant evidence from
the last DiagnosticBundle stored in conversation state.

Design:
  - Deterministic — no LLM reasoning
  - Reads from conversation cache (reasoning_trace)
  - Returns structured forensic responses
  - Graceful fallback when no prior context
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

NO_EVIDENCE_MESSAGE = (
    "### Diagnostic principal\n"
    "Aucune donnée live disponible — diagnostic impossible sans preuve.\n\n"
    "### Preuves collectées\n"
    "❌ Aucune preuve disponible.\n\n"
    "Sources interrogées :\n"
    "* logs\n"
    "* DB\n"
    "* code\n"
    "* FR\n"
    "* Qdrant\n\n"
    "Aucune donnée exploitable n'a été trouvée.\n"
    "no evidence available\n\n"
    "### Workflow\n"
    "Procédure non applicable sans preuve.\n\n"
    "### Validation code source\n"
    "Aucune référence code extraite.\n\n"
    "### Action N3\n"
    "Vérification N3 recommandée en lecture seule.\n\n"
    "📂 **Sources des informations**\n"
    "Provenance : sources interrogées automatiquement (logs, DB, code, FR, Qdrant) — aucune donnée retournée."
)

NO_TIMELINE_MESSAGE = "❌ Aucun événement chronologique disponible."
NO_CODE_MESSAGE = "❌ Aucun élément correspondant trouvé dans le code indexé."
UNKNOWN_TABLE_MESSAGE = "❌ Table non trouvée dans le référentiel indexé."

# Try to import provenance module
try:
    from app.services.live_diagnostics.evidence_provenance import (
        EvidenceProvenance, SourceType, build_provenance_footer,
        provenance_from_log, provenance_from_db, provenance_from_code,
    )
    _PROVENANCE_AVAILABLE = True
except ImportError:
    _PROVENANCE_AVAILABLE = False


class ForensicFollowupHandler:
    """
    Generates deterministic follow-up responses from cached diagnostic evidence.

    The cached evidence is stored in conversation reasoning_trace during
    the initial diagnostic call.
    """

    def handle(
        self,
        forensic_intent: str,
        entity: Optional[str],
        cached_trace: Optional[Dict[str, Any]],
        cached_bundle: Optional[Any] = None,
    ) -> Optional[str]:
        """
        Handle a forensic follow-up intent.
        Returns formatted response or None if no cached data.
        """
        evidence_required_intents = {
            "forensic_logs",
            "forensic_timeline",
            "forensic_evidence",
            "forensic_exceptions",
            "forensic_db_state",
            "forensic_workflow",
            "forensic_root_cause",
            "forensic_rollback",
            "forensic_constraint_chain",
            "show_blocking_method",
            "show_constraint_source",
            "explain_code_constraint",
            "explain_exception_source",
            "check_residual_data",
            "check_active_services",
        }

        if not cached_trace and not cached_bundle:
            if forensic_intent == "find_code_function":
                _raw = self._handle_find_code_function(entity or "", {}, None)
                return self._apply_forensic_contract(forensic_intent, entity, _raw)
            if forensic_intent in evidence_required_intents:
                _raw = NO_EVIDENCE_MESSAGE
            else:
                _raw = self._no_context_response(forensic_intent, entity)
            return self._apply_forensic_contract(forensic_intent, entity, _raw)

        trace = cached_trace or {}

        handlers = {
            "forensic_logs": self._handle_logs,
            "forensic_timeline": self._handle_timeline,
            "forensic_evidence": self._handle_evidence,
            "forensic_exceptions": self._handle_exceptions,
            "forensic_db_state": self._handle_db_state,
            "forensic_workflow": self._handle_workflow,
            "forensic_root_cause": self._handle_root_cause,
            "forensic_transaction": self._handle_transaction,
            "forensic_rollback": self._handle_rollback,
            "forensic_constraint_chain": self._handle_constraint_chain,
            "show_blocking_method": self._handle_blocking_method,
            "show_constraint_source": self._handle_constraint_source,
            "explain_code_constraint": self._handle_code_constraint,
            "explain_exception_source": self._handle_exception_source,
            "check_residual_data": self._handle_residual_data,
            "check_active_services": self._handle_active_services,
            "find_code_function": self._handle_find_code_function,
        }

        handler = handlers.get(forensic_intent, self._handle_generic)
        try:
            result = handler(entity, trace, cached_bundle)
            _raw = result if result else self._no_data_response(forensic_intent, entity)
            if forensic_intent in evidence_required_intents and not self._has_any_evidence(trace, cached_bundle, _raw):
                _raw = NO_EVIDENCE_MESSAGE
            return self._apply_forensic_contract(forensic_intent, entity, _raw)
        except Exception as e:
            logger.warning(f"[ForensicFollowup] Error handling {forensic_intent}: {e}")
            _raw = NO_EVIDENCE_MESSAGE if forensic_intent in evidence_required_intents else self._no_data_response(forensic_intent, entity)
            return self._apply_forensic_contract(forensic_intent, entity, _raw)

    def _has_any_evidence(self, trace: Dict[str, Any], bundle: Any, raw_text: str) -> bool:
        if bundle and hasattr(bundle, "db_evidence"):
            for ev in (bundle.db_evidence or {}).values():
                if getattr(ev, "has_data", False) or (getattr(ev, "row_count", 0) or 0) > 0:
                    return True
        if bundle and hasattr(bundle, "log_evidence"):
            for ev in (bundle.log_evidence or []):
                if getattr(ev, "has_data", False) or bool(getattr(ev, "matched_lines", None)):
                    return True
        if bundle and hasattr(bundle, "ssh_evidence"):
            for ev in (bundle.ssh_evidence or []):
                if getattr(ev, "has_data", False):
                    return True

        expl = (trace or {}).get("explanation", {}) or {}
        if (expl.get("evidence_count") or 0) > 0:
            return True

        forensic = (trace or {}).get("forensic_summary", {}) or {}
        if forensic.get("exception_chain") or forensic.get("state_transitions"):
            return True
        if (trace or {}).get("structured_log_events"):
            return True

        lowered = str(raw_text or "").lower()
        if "aucune preuve" in lowered or "no evidence available" in lowered:
            return False
        return any(k in lowered for k in ("preuve", "log", "exception", "timeline", "source:", "fr:"))

    # ── Handlers ──────────────────────────────────────────────────────────

    def _handle_logs(self, entity: str, trace: Dict, bundle: Any) -> Optional[str]:
        """Show structured log lines from last diagnostic."""
        parts = [f"📋 **Lignes de log extraites** — `{entity or '?'}`", ""]

        # From forensic summary
        forensic = trace.get("forensic_summary", {})
        if forensic:
            parts.append(f"Sévérité: **{forensic.get('severity', '?')}**")
            exc_chain = forensic.get("exception_chain", [])
            if exc_chain:
                parts.append(f"Exceptions: `{'` → `'.join(exc_chain[:5])}`")
            codes = forensic.get("error_codes", [])
            if codes:
                parts.append(f"Codes erreur: {', '.join(codes)}")
            parts.append("")

        # From structured log events
        events = trace.get("structured_log_events", [])
        if events:
            parts.append("**Événements structurés:**")
            for ev in events[:12]:
                ts = ev.get("timestamp", "")
                level = ev.get("level", "")
                exc = ev.get("exception", "")
                msg = ev.get("message", "")[:120]
                code = ev.get("error_code", "")
                icon = "🔴" if level in ("ERROR", "FATAL") else "🟡" if level == "WARN" else "⚪"
                line_parts = [f"{icon}"]
                if ts:
                    line_parts.append(f"[{ts}]")
                if exc:
                    line_parts.append(f"⚡ `{exc}`")
                if code:
                    line_parts.append(f"[code={code}]")
                if msg:
                    line_parts.append(msg)
                parts.append(" ".join(line_parts))
            if len(events) > 12:
                parts.append(f"... +{len(events) - 12} événements")
        elif forensic.get("context_for_llm"):
            parts.append("```")
            parts.append(forensic["context_for_llm"])
            parts.append("```")
        else:
            parts.append("_Aucune ligne de log collectée pour cette session._")

        # Provenance footer
        if _PROVENANCE_AVAILABLE and (events or forensic.get("context_for_llm")):
            _log_prov = provenance_from_log(
                log_file="brasil_app/catalina",
                host="op49mwa11",
                query=entity or "?",
            )
            parts.append(build_provenance_footer([_log_prov]))

        return "\n".join(parts)

    def _handle_timeline(self, entity: str, trace: Dict, bundle: Any) -> Optional[str]:
        """Show forensic timeline."""
        parts = [f"🕓 **Timeline forensique** — `{entity or '?'}`", ""]
        events = trace.get("structured_log_events", []) if isinstance(trace, dict) else []

        if events:
            parts.append("**Événements corrélés (logs réels):**")
            for ev in events[:12]:
                ts = ev.get("timestamp", "?")
                level = ev.get("level", "?")
                msg = str(ev.get("message", "")).strip()[:140]
                src = ev.get("source", ev.get("log_file", "log"))
                parts.append(f"- [{ts}] ({level}) {msg} — source={src}")
            if len(events) > 12:
                parts.append(f"... +{len(events) - 12} événement(s)")
        else:
            parts.append(NO_TIMELINE_MESSAGE)

        if _PROVENANCE_AVAILABLE and events:
            _tl_prov = provenance_from_log(log_file="brasil_app", host="op49mwa11", query=entity or "?")
            parts.append(build_provenance_footer([_tl_prov]))

        return "\n".join(parts)

    def _handle_evidence(self, entity: str, trace: Dict, bundle: Any) -> Optional[str]:
        """Show all runtime evidence."""
        parts = [f"🔍 **Preuves runtime** — `{entity or '?'}`", ""]

        # DB evidence
        if bundle and hasattr(bundle, "db_evidence"):
            parts.append("**Base de données:**")
            for qname, ev in bundle.db_evidence.items():
                if hasattr(ev, "has_data") and ev.has_data:
                    table = getattr(ev, "table", None) or qname
                    rows = getattr(ev, "row_count", 0)
                    eqpt_id = getattr(ev, "eqpt_id", None)
                    parts.append(f"  📊 `{table}`: {rows} ligne(s)" + (f" (eqpt_id={eqpt_id})" if eqpt_id else ""))
                elif hasattr(ev, "error") and ev.error:
                    parts.append(f"  ❌ `{qname}`: {ev.error}")
            parts.append("")

        # Correlation hypotheses
        hyps = trace.get("correlation_hypotheses", [])
        if hyps:
            parts.append("**Corrélation:**")
            for h in hyps[:3]:
                cause = h.get("cause", "?")
                conf = h.get("confidence", 0)
                evidence = h.get("evidence", [])
                parts.append(f"  🔗 `{cause}` ({int(conf*100)}%) — preuves: {', '.join(evidence[:3])}")
            parts.append("")

        # Explanation
        expl = trace.get("explanation", {})
        if expl:
            tech = expl.get("technical_block", "")
            if tech:
                parts.append("**Synthèse technique:**")
                parts.append(tech)

        if len(parts) <= 2:
            parts.append("_Aucune preuve runtime disponible._")

        # Provenance footer
        if _PROVENANCE_AVAILABLE and bundle and hasattr(bundle, "db_evidence") and bundle.db_evidence:
            _ev_provs = [provenance_from_db(query=q, table=getattr(e, 'table', q))
                         for q, e in list(bundle.db_evidence.items())[:3]]
            parts.append(build_provenance_footer(_ev_provs))

        return "\n".join(parts)

    def _handle_exceptions(self, entity: str, trace: Dict, bundle: Any) -> Optional[str]:
        """Show detected exceptions."""
        forensic = trace.get("forensic_summary", {})
        exc_chain = forensic.get("exception_chain", [])

        if not exc_chain:
            # Try from correlation
            hyps = trace.get("correlation_hypotheses", [])
            for h in hyps:
                exc_chain.extend(h.get("evidence", []))

        if not exc_chain:
            return f"⚡ **Exceptions détectées** — `{entity or '?'}`\n\n_Aucune exception Java détectée dans les logs._"

        parts = [f"⚡ **Exceptions détectées** — `{entity or '?'}`", ""]
        for i, exc in enumerate(exc_chain[:8], 1):
            parts.append(f"{i}. `{exc}`")

        # Code intelligence cross-reference
        try:
            from app.services.code_intelligence import CODE_INTELLIGENCE_ENABLED
            if CODE_INTELLIGENCE_ENABLED:
                from app.services.code_intelligence.extractors.brasil_extractor import search_code_knowledge
                parts.append("")
                parts.append("**Localisation dans le code source:**")
                for exc in exc_chain[:3]:
                    hits = search_code_knowledge(exception=exc)
                    for hit in hits[:1]:
                        loc = hit.code_location
                        f = loc.get("file", "").split("\\")[-1].split("/")[-1]
                        m = loc.get("method", "?")
                        l = loc.get("line", "")
                        parts.append(f"  📌 `{exc}` → `{m}()` [`{f}:{l}`]")
        except Exception:
            pass

        # Provenance footer
        if _PROVENANCE_AVAILABLE:
            _exc_prov = provenance_from_log(log_file="catalina.out", host="op49mwa11", query=entity or "?")
            parts.append(build_provenance_footer([_exc_prov]))

        return "\n".join(parts)

    def _handle_db_state(self, entity: str, trace: Dict, bundle: Any) -> Optional[str]:
        """Show DB state evidence."""
        if not bundle or not hasattr(bundle, "db_evidence"):
            return f"📊 **État DB** — `{entity or '?'}`\n\n_Aucune donnée DB collectée._"

        parts = [f"📊 **État base de données** — `{entity or '?'}`", ""]
        for qname, ev in bundle.db_evidence.items():
            if hasattr(ev, "has_data") and ev.has_data:
                rows = getattr(ev, "row_count", 0)
                table = getattr(ev, "table", None) or qname
                eqpt_id = getattr(ev, "eqpt_id", None)
                parts.append(f"✅ `{qname}` → **{rows}** ligne(s) dans `{table}`")
                if eqpt_id:
                    parts.append(f"   eqpt_id = {eqpt_id}")
                # Show first few rows safely
                row_data = getattr(ev, "rows", [])
                if row_data:
                    for row in row_data[:3]:
                        cols = ", ".join(f"{k}={v}" for k, v in list(row.items())[:4])
                        parts.append(f"   → {cols}")
            elif hasattr(ev, "row_count") and ev.row_count == 0:
                parts.append(f"⬚ `{qname}` → aucune donnée résiduelle")
            elif hasattr(ev, "error") and ev.error:
                parts.append(f"❌ `{qname}` → erreur: {ev.error}")

        # Provenance footer
        if _PROVENANCE_AVAILABLE:
            _provs = [provenance_from_db(query=qname, table=getattr(ev, 'table', qname))
                       for qname, ev in bundle.db_evidence.items()
                       if hasattr(ev, 'has_data')]
            if _provs:
                parts.append(build_provenance_footer(_provs[:4]))

        return "\n".join(parts)

    def _handle_workflow(self, entity: str, trace: Dict, bundle: Any) -> Optional[str]:
        """Show workflow state information."""
        expl = trace.get("explanation", {})
        forensic = trace.get("forensic_summary", {})

        parts = [f"🔄 **Workflow** — `{entity or '?'}`", ""]

        workflow = expl.get("workflow")
        if workflow:
            parts.append(f"Workflow: `{workflow}`")

        blocking = expl.get("blocking_validation") if expl else None
        if blocking:
            parts.append(f"Validation bloquante: `{blocking}`")

        transitions = forensic.get("state_transitions", [])
        if transitions:
            parts.append("")
            parts.append("**Transitions d'état détectées:**")
            for t in transitions:
                parts.append(f"  `{t.get('from','?')}` → `{t.get('to','?')}`")

        if len(parts) <= 2:
            parts.append("_Aucune information de workflow disponible._")

        return "\n".join(parts)

    def _handle_root_cause(self, entity: str, trace: Dict, bundle: Any) -> Optional[str]:
        """Show root cause analysis."""
        expl = trace.get("explanation", {})
        if not expl or not expl.get("root_cause") or (expl.get("evidence_count") or 0) <= 0:
            return NO_EVIDENCE_MESSAGE

        parts = [f"🧠 **Root Cause Analysis** — `{entity or '?'}`", ""]
        parts.append(f"**Cause:** `{expl['root_cause']}`")
        if expl.get("collaborator_summary"):
            parts.append(f"\n{expl['collaborator_summary']}")
        if expl.get("workflow"):
            parts.append(f"\n**Workflow:** `{expl['workflow']}`")
        if expl.get("source_location"):
            parts.append(f"**Source:** `{expl['source_location']}`")
        if expl.get("fr_reference"):
            parts.append(f"**FR:** {expl['fr_reference']}")
        parts.append(f"\n**Preuves:** {expl.get('evidence_count', 0)} source(s)")

        # Reasoning chain
        chain = expl.get("reasoning_chain_display", "")
        if chain:
            parts.append("")
            parts.append(chain)

        return "\n".join(parts)

    def _handle_transaction(self, entity: str, trace: Dict, bundle: Any) -> Optional[str]:
        forensic = trace.get("forensic_summary", {})
        parts = [f"💳 **Transaction** — `{entity or '?'}`", ""]
        if forensic.get("has_rollback"):
            parts.append("⏪ **Rollback détecté** — la transaction a été annulée")
        tables = forensic.get("affected_tables", [])
        if tables:
            parts.append(f"Tables impactées: {', '.join(f'`{t}`' for t in tables)}")
        if len(parts) <= 2:
            parts.append("_Aucune information de transaction disponible._")
        return "\n".join(parts)

    def _handle_rollback(self, entity: str, trace: Dict, bundle: Any) -> Optional[str]:
        return self._handle_transaction(entity, trace, bundle)

    def _handle_constraint_chain(self, entity: str, trace: Dict, bundle: Any) -> Optional[str]:
        return self._handle_exceptions(entity, trace, bundle)

    def _handle_blocking_method(self, entity: str, trace: Dict, bundle: Any) -> Optional[str]:
        return self._handle_code_constraint(entity, trace, bundle)

    def _handle_constraint_source(self, entity: str, trace: Dict, bundle: Any) -> Optional[str]:
        return self._handle_code_constraint(entity, trace, bundle)

    def _handle_code_constraint(self, entity: str, trace: Dict, bundle: Any) -> Optional[str]:
        """Show code source validation details — execution graph first, then brasil_extractor."""
        parts = [f"📌 **Validation code source** — `{entity or '?'}`", ""]

        # NEW: execution graph blocking conditions
        try:
            from app.services.code_intelligence.function_knowledge_index import function_knowledge_index
            query = f"contrainte suppression bloquer {entity or ''}"
            block = function_knowledge_index.forensic_block(query, entity=entity, max_chars=600)
            if block:
                parts.append(block)
                parts.append("")
        except Exception:
            pass

        # Execution graph operation path
        try:
            from app.services.code_intelligence.operation_graph import operation_graph
            intent = "delete_equipment" if not entity or "dslam" in (entity or "").lower() else "validate_deletion"
            blocking_list = operation_graph.get_blocking_conditions(intent, entity)
            if blocking_list:
                parts.append("**Conditions bloquantes identifiées:**")
                for cond in blocking_list[:5]:
                    parts.append(f"  ⚠ {cond[:120]}")
                parts.append("")
        except Exception:
            pass

        # Fallback: brasil_extractor (exception-centric)
        try:
            from app.services.code_intelligence import CODE_INTELLIGENCE_ENABLED
            if CODE_INTELLIGENCE_ENABLED:
                from app.services.code_intelligence.extractors.brasil_extractor import search_code_knowledge
                hits = search_code_knowledge(entity=entity, tags=["deletion", "constraint"])
                if not hits:
                    hits = search_code_knowledge(exception="BrasilDeleteException")
                if hits:
                    parts.append("**Validations du code source:**")
                    for hit in hits[:4]:
                        loc = hit.code_location
                        f = loc.get("file", "").split("\\")[-1].split("/")[-1]
                        m = loc.get("method", "?")
                        l = loc.get("line", "")
                        bc = hit.blocking_condition or hit.exception_class
                        parts.append(f"  📌 `{f}:{l}` → `{m}()`")
                        if bc:
                            parts.append(f"     _{bc}_")
        except Exception:
            pass

        if len(parts) <= 2:
            parts.append("_Aucune validation trouvée dans le code source._")

        # Provenance footer for code intelligence
        if _PROVENANCE_AVAILABLE:
            _code_provs = []
            try:
                from app.services.code_intelligence import CODE_INTELLIGENCE_ENABLED
                if CODE_INTELLIGENCE_ENABLED:
                    _code_provs.append(EvidenceProvenance(
                        source_type=SourceType.CODE,
                        source_file="execution_graph_cache.json",
                        query="validate_deletion",
                    ))
            except Exception:
                pass
            if _code_provs:
                parts.append(build_provenance_footer(_code_provs))

        return "\n".join(parts)

    def _handle_exception_source(self, entity: str, trace: Dict, bundle: Any) -> Optional[str]:
        """Show exception sources with execution graph cross-reference."""
        parts = [f"⚡ **Sources d'exceptions** — `{entity or '?'}`", ""]

        # Get exceptions from reasoning trace
        exc_chain = []
        forensic = trace.get("forensic_summary") if trace else None
        if forensic and isinstance(forensic, dict):
            exc_chain = forensic.get("exception_chain", [])

        # Also check explanation identified_exceptions
        expl = trace.get("explanation", {}) if trace else {}
        identified = expl.get("identified_exceptions", []) if expl else []
        all_exceptions = list(set(exc_chain + identified))[:8]

        if all_exceptions:
            parts.append("**Exceptions détectées:**")
            for exc in all_exceptions[:5]:
                parts.append(f"  `{exc}`")
                # Look up source in execution graph
                try:
                    from app.services.code_intelligence.function_knowledge_index import function_knowledge_index
                    source = function_knowledge_index.get_exception_source(exc)
                    if source:
                        parts.append(f"    → {source}")
                except Exception:
                    pass

        # Show full execution graph for relevant operations
        try:
            from app.services.code_intelligence.operation_graph import operation_graph
            intent = "delete_equipment"
            exc_list = operation_graph.get_exceptions_for_intent(intent, entity)
            if exc_list and not all_exceptions:
                parts.append("")
                parts.append("**Exceptions possibles (source code):**")
                for exc in exc_list[:6]:
                    parts.append(f"  `{exc}`")
        except Exception:
            pass

        if len(parts) <= 2:
            return self._handle_exceptions(entity, trace, bundle)

        return "\n".join(parts)

    def _handle_residual_data(self, entity: str, trace: Dict, bundle: Any) -> Optional[str]:
        return self._handle_db_state(entity, trace, bundle)

    def _handle_active_services(self, entity: str, trace: Dict, bundle: Any) -> Optional[str]:
        return self._handle_db_state(entity, trace, bundle)

    def _handle_find_code_function(self, entity: str, trace: Dict, bundle: Any) -> Optional[str]:
        """
        Directly queries the execution graph to answer:
        "quelle fonction supprime un equipement ?", "quel service cree un VLAN ?", etc.
        Works WITHOUT prior diagnostic context.
        """
        parts = [f"🔎 **Fonction dans le code source** — `{entity or 'BRASIL'}`", ""]

        # Parse operation from entity/trace context
        # Try to extract operation from user query or last intent in trace
        last_intent = trace.get("last_intent", "") if trace else ""
        user_query = (trace.get("user_query", "") if trace else "").lower()
        op_hint = ""
        # Parse from user query first (most reliable)
        if any(w in user_query for w in ["supprim", "delete", "effac", "retir"]):
            op_hint = "delete"
        elif any(w in user_query for w in ["cre", "créer", "creer", "creation", "créat"]):
            op_hint = "create"
        elif any(w in user_query for w in ["modif", "chang", "mise a jour", "update"]):
            op_hint = "modify"
        elif any(w in user_query for w in ["valid", "verif", "check", "contraint", "bloqu"]):
            op_hint = "validate"
        elif any(w in user_query for w in ["sync", "orchestra"]):
            op_hint = "sync"
        elif any(w in user_query for w in ["rollback", "annul"]):
            op_hint = "rollback"
        # Fallback to last_intent
        elif any(w in last_intent for w in ["delete", "suppr"]):
            op_hint = "delete"
        elif any(w in last_intent for w in ["create", "creer"]):
            op_hint = "create"
        elif any(w in last_intent for w in ["modify", "modif"]):
            op_hint = "modify"
        elif any(w in last_intent for w in ["validate", "check"]):
            op_hint = "validate"

        try:
            from app.services.code_intelligence.extractors.execution_graph_extractor import get_execution_graph
            from app.services.code_intelligence.operation_graph import operation_graph, INTENT_TO_OPERATION
            from app.services.code_intelligence.function_knowledge_index import function_knowledge_index

            g = get_execution_graph()

            # Extract entity from user query if not provided
            if not entity and user_query:
                import re as _re
                for kw, ent in [("vlan", "Vlan"), ("dslam", "Dslam"), ("msan", "Msan"),
                                ("equipement", "Dslam"), ("equipment", "Dslam"),
                                ("carte", "Card"), ("card", "Card"), ("port", "Port"),
                                ("mrt", "MRT"), ("lien", "MRT")]:
                    if kw in user_query:
                        entity = ent
                        break

            # 1. If entity known — show operation paths for that entity
            entity_lower = (entity or "").lower()
            matched_ops = []
            for op_name, path in g.operations.items():
                if entity_lower and entity_lower not in path.entity.lower() and entity_lower not in op_name:
                    continue
                if op_hint and op_hint not in op_name:
                    continue
                matched_ops.append((op_name, path))

            strict_refs: List[Dict[str, str]] = []
            if matched_ops:
                for op_name, path in matched_ops[:4]:
                    # Main service methods
                    for nid in path.services[:3]:
                        node = g.nodes.get(nid)
                        if node:
                            loc = node.code_location
                            f = loc.get("file", "").split("\\")[-1].split("/")[-1]
                            strict_refs.append({
                                "class": node.class_name,
                                "method": f"{node.method_name}()",
                                "file": f or "?",
                                "line": str(loc.get("line", "?")),
                            })
                    # Validators
                    for nid in path.validators[:2]:
                        node = g.nodes.get(nid)
                        if node:
                            loc = node.code_location
                            f = loc.get("file", "").split("\\")[-1].split("/")[-1]
                            parts.append(f"  ⚠ **Validateur** : `{node.class_name}.{node.method_name}()`")
                            if node.blocking_conditions:
                                parts.append(f"       Condition: _{node.blocking_conditions[0][:90]}_")
            else:
                # Fallback: keyword search on graph
                query = f"{op_hint} {entity or ''}".strip() or "service principal"
                results = function_knowledge_index.search(query, entity=entity, max_results=5)
                if results:
                    for node, score in results:
                        loc = node.code_location
                        f = loc.get("file", "").split("\\")[-1].split("/")[-1]
                        strict_refs.append({
                            "class": node.class_name,
                            "method": f"{node.method_name}()",
                            "file": f or "?",
                            "line": str(loc.get("line", "?")),
                        })

            dedup = []
            seen = set()
            for ref in strict_refs:
                key = (ref["class"], ref["method"], ref["file"], ref["line"])
                if key in seen:
                    continue
                seen.add(key)
                dedup.append(ref)

            if not dedup:
                return NO_CODE_MESSAGE

            parts.append("**Références exactes du code indexé :**")
            for ref in dedup[:8]:
                parts.append(f"Référence : `{ref['class']}.{ref['method']}`")
                parts.append(f"Classe : `{ref['class']}`")
                parts.append(f"Méthode : `{ref['method']}`")
                parts.append(f"Fichier : `{ref['file']}`")
                parts.append(f"Ligne : `{ref['line']}`")
                parts.append("")

        except Exception as e:
            logger.warning(f"[FindCodeFunction] Error: {e}")
            return NO_CODE_MESSAGE

        return "\n".join(parts)

    def _handle_generic(self, entity: str, trace: Dict, bundle: Any) -> Optional[str]:
        """Generic forensic response with all available data."""
        parts = [f"🔍 **Forensic** — `{entity or '?'}`", ""]

        expl = trace.get("explanation", {})
        if expl and expl.get("technical_block"):
            parts.append(expl["technical_block"])
            parts.append("")

        forensic = trace.get("forensic_summary", {})
        if forensic and forensic.get("context_for_llm"):
            parts.append("```")
            parts.append(forensic["context_for_llm"])
            parts.append("```")

        if len(parts) <= 2:
            parts.append("_Aucune donnée forensique disponible pour cette session._")

        return "\n".join(parts)

    # ── Fallbacks ─────────────────────────────────────────────────────────

    def _no_context_response(self, intent: str, entity: Optional[str]) -> str:
        return (
            f"⚠️ **Aucun contexte de diagnostic précédent**\n\n"
            f"Pour afficher les preuves forensiques, lancez d'abord un diagnostic.\n"
            f"Exemple: _\"Suppression équipement {entity or 'XXXX'} impossible\"_"
        )

    def _no_data_response(self, intent: str, entity: Optional[str]) -> str:
        return NO_EVIDENCE_MESSAGE

    # ── Strict forensic contract ─────────────────────────────────────────

    _FORBIDDEN_GENERIC_PATTERNS = [
        r"(?i)n['’]hésitez\s+pas[^\n.]*[\n.]?",
        r"(?i)dites[- ]?moi\s+si[^\n.]*[\n.]?",
        r"(?i)je\s+suis\s+l[àa]\s+pour\s+vous\s+aider[^\n.]*[\n.]?",
        r"(?i)contact(?:ez|er)?\s+le\s+support[^\n.]*[\n.]?",
        r"(?i)escalad(?:er|ez)?\s+vers\s+l['’]?équipe\s+N3[^\n.]*[\n.]?",
    ]

    _MUTATION_SQL_PATTERN = re.compile(
        r"(?im)^.*\b(UPDATE|DELETE\s+FROM|INSERT\s+INTO|DROP\s+TABLE|TRUNCATE\s+TABLE|ALTER\s+TABLE)\b.*$"
    )

    _METHOD_PATTERN = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)\(\)")

    def _apply_forensic_contract(self, intent: str, entity: Optional[str], raw_text: str) -> str:
        cleaned = self._sanitize_forensic_text(raw_text or "")
        diagnostic = self._extract_diagnostic_line(cleaned, intent)
        evidence = self._extract_evidence_block(cleaned)
        source_code = self._extract_source_code_block(cleaned, intent)
        action = self._action_for_intent(intent)

        return (
            f"### Diagnostic principal\n"
            f"{diagnostic}\n\n"
            f"### Preuves collectées\n"
            f"{evidence}\n\n"
            f"### Workflow\n"
            f"Procédure associée : intent=`{intent}` entity=`{entity or '?'}`\n\n"
            f"### Source code\n"
            f"{source_code}\n\n"
            f"### Action N3 ciblée\n"
            f"{action}\n\n"
            f"📂 **Sources des informations**\n"
            f"Provenance : logs, DB, code, FR, Qdrant (sources interrogées automatiquement)"
        )

    def _sanitize_forensic_text(self, text: str) -> str:
        sanitized = self._MUTATION_SQL_PATTERN.sub("[mutation SQL removed - read-only policy]", text)
        for pat in self._FORBIDDEN_GENERIC_PATTERNS:
            sanitized = re.sub(pat, "", sanitized)
        sanitized = self._protect_unindexed_sql_identifiers(sanitized)
        sanitized = re.sub(r"\n{3,}", "\n\n", sanitized).strip()
        return sanitized

    def _protect_unindexed_sql_identifiers(self, text: str) -> str:
        pattern = re.compile(r"\b(t_[a-z0-9_]+|view_[a-z0-9_]+|repository_[a-z0-9_]+)\b", re.I)
        try:
            from app.services.chatbot.brasil_knowledge_base import brasil_kb as brasil_knowledge_base
        except Exception:
            brasil_knowledge_base = None

        def repl(match: re.Match) -> str:
            token = match.group(1)
            low = token.lower()
            if low.startswith("t_") and brasil_knowledge_base is not None:
                try:
                    if brasil_knowledge_base.is_real_table(low):
                        return token
                except Exception:
                    pass
            return UNKNOWN_TABLE_MESSAGE

        return pattern.sub(repl, text)

    def _extract_diagnostic_line(self, text: str, intent: str) -> str:
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("###"):
                continue
            return line
        return f"Diagnostic déterministe disponible pour `{intent}`."

    def _extract_evidence_block(self, text: str) -> str:
        lowered = text.lower()
        has_no_evidence = (
            "aucune preuve" in lowered
            or "aucune donnée" in lowered
            or "aucune ligne de log" in lowered
            or "aucun contexte" in lowered
            or "no evidence available" in lowered
        )
        has_evidence_marker = any(k in lowered for k in [
            "preuve", "log", "timeline", "exception", "select", "table", "events", "événements"
        ])
        if has_no_evidence or not has_evidence_marker:
            return NO_EVIDENCE_MESSAGE
        snippet = text[:900].strip()
        return snippet if snippet else NO_EVIDENCE_MESSAGE

    def _extract_source_code_block(self, text: str, intent: str) -> str:
        methods = []
        seen = set()
        for cls, method in self._METHOD_PATTERN.findall(text):
            key = f"{cls}.{method}()"
            if key not in seen:
                seen.add(key)
                methods.append(key)
        if not methods:
            if intent == "find_code_function":
                return NO_CODE_MESSAGE
            return "Aucune référence code extraite."
        return "\n".join(f"- `{m}`" for m in methods[:8])

    def _action_for_intent(self, intent: str) -> str:
        actions = {
            "forensic_logs": "Exécuter uniquement des requêtes de lecture et confirmer l'horodatage des erreurs.",
            "forensic_timeline": "Valider la séquence d'événements puis isoler la première erreur bloquante.",
            "forensic_evidence": "Consolider les preuves runtime avant toute action corrective.",
            "forensic_root_cause": "Traiter la cause racine la plus probable, pas les symptômes secondaires.",
            "forensic_workflow": "Suivre strictement les étapes du workflow BRASIL validé.",
            "find_code_function": "Vérifier la méthode source puis corréler avec logs et état DB en lecture seule.",
        }
        return actions.get(intent, "Appliquer une vérification N3 ciblée en mode lecture seule, sans hypothèse non prouvée.")


# Singleton
forensic_followup_handler = ForensicFollowupHandler()
