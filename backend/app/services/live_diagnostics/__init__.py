"""
live_diagnostics/__init__.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Live Diagnostic Layer — main entry point.

Multi-server architecture:
  BDD (op49mdb11) — PostgreSQL queries via SSH->psql
  WA  (op49mwa11) — Tomcat logs + process checks
  DE  (op49mde11) — Data Extractor batch (optional)

Usage:
    from app.services.live_diagnostics import create_orchestrator_from_settings
    orch = create_orchestrator_from_settings()
    bundle = orch.run(intent="delete_equipment", entity="DSROB362")
    context_blocks = bundle.to_context_blocks()
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.services.live_diagnostics.models.evidence import DiagnosticBundle
from app.services.live_diagnostics.planners.diagnostic_planner import DiagnosticPlanner
from app.services.live_diagnostics.db.db_service import DbDiagnosticService, SshPsqlDbService
from app.services.live_diagnostics.db.db_query_registry import ALLOWED_QUERIES
from app.services.live_diagnostics.logs.log_service import LogService
from app.services.live_diagnostics.normalizers.evidence_normalizer import EvidenceNormalizer
from app.services.live_diagnostics.normalizers.log_normalizer import LogNormalizer
from app.services.live_diagnostics.resolution_engine import ResolutionEngine
from app.services.live_diagnostics.planners.server_router import (
    ServerRole, get_log_searches_for_intent, get_ssh_commands_for_intent,
    get_servers_for_intent,
)

logger = logging.getLogger(__name__)

__all__ = ["LiveDiagnosticOrchestrator", "DiagnosticBundle", "create_orchestrator_from_settings"]


class LiveDiagnosticOrchestrator:
    """
    Main entry point for the Live Diagnostic Layer.
    Multi-server: routes queries/logs/SSH to the correct server.
    """

    def __init__(
        self,
        ssh_clients: Dict[ServerRole, Any] | None = None,
        # Legacy single-client mode (backward compat)
        ssh_client=None,
        db_name: str = "brasil",
        db_user: str = "postgres",
        db_host_remote: str = "localhost",
        db_port: int = 5432,
        psql_bin: str = "/opt/pgsql/na/9.4.4/bin/psql",
        psql_lib: str = "/opt/pgsql/na/9.4.4/lib",
        fr_data_path: str | None = None,
        enable_live_db: bool = True,
        enable_logs:    bool = True,
        enable_ssh:     bool = False,
        engine=None,
        dsn: str | None = None,
    ):
        self._planner    = DiagnosticPlanner()
        self._ev_norm    = EvidenceNormalizer()
        self._log_norm   = LogNormalizer()
        self._resolver   = ResolutionEngine(fr_data_path=fr_data_path)
        self._enable_log = enable_logs
        self._enable_ssh = enable_ssh

        # Multi-server SSH clients
        if ssh_clients:
            self._ssh_clients = ssh_clients
        elif ssh_client:
            # Legacy: single client = BDD server
            self._ssh_clients = {ServerRole.BDD: ssh_client}
        else:
            self._ssh_clients = {}

        # Primary SSH client (BDD) for backward compat
        self._ssh_client = self._ssh_clients.get(ServerRole.BDD)

        # Log service uses WA client if available, fallback to BDD
        _log_ssh = self._ssh_clients.get(ServerRole.WA) or self._ssh_client
        self._log_svc = LogService(log_root="/opt/application/49mapp/current/tomcat/00/logs", ssh_client=_log_ssh)

        # DB service: SSH->psql on BDD server
        if enable_live_db and self._ssh_client:
            self._db_svc = SshPsqlDbService(
                ssh_client=self._ssh_client,
                db_name=db_name,
                db_user=db_user,
                db_host=db_host_remote,
                db_port=db_port,
                psql_bin=psql_bin,
                psql_lib=psql_lib,
            )
            logger.info("[LiveDiag] DB service: SSH->psql mode")
        elif enable_live_db and (engine or dsn):
            self._db_svc = DbDiagnosticService(engine=engine, dsn=dsn)
            logger.info("[LiveDiag] DB service: direct TCP mode")
        else:
            self._db_svc = None
            if enable_live_db:
                logger.warning("[LiveDiag] DB service: disabled (no ssh_client, no engine/dsn)")

        self._enable_db = enable_live_db and self._db_svc is not None

        # Log connected servers
        for role, client in self._ssh_clients.items():
            logger.info(f"[LiveDiag] SSH client [{role.value}]: {client.host}")

    def run(
        self,
        intent:   str,
        entity:   Optional[str] = None,
        symptoms: Optional[List[str]] = None,
        debug:    bool = False,
    ) -> DiagnosticBundle:
        """
        Execute the full diagnostic pipeline synchronously.
        Routes to multiple servers based on intent.
        """
        bundle = DiagnosticBundle(
            intent=intent,
            entity=entity,
            debug_mode=debug,
        )

        # 1. Plan (DB queries)
        plan = self._planner.plan(
            intent=intent,
            entity=entity,
            symptoms=symptoms,
            enable_live_db=self._enable_db,
            enable_logs=self._enable_log,
            enable_ssh=self._enable_ssh,
        )
        if debug:
            bundle.reasoning_trace["plan"] = {
                "db_queries": plan.db_queries,
                "log_searches": plan.log_searches,
                "ssh_commands": plan.ssh_commands,
                "reasoning": plan.reasoning,
            }

        # 2. Execute DB queries (on BDD server)
        if self._enable_db and plan.db_queries:
            try:
                bundle.db_evidence = self._run_db_plan(plan, entity)
            except Exception as e:
                logger.error(f"[LiveDiag] DB plan failed: {e}")

        # 3. Execute log searches (multi-server via server_router)
        if self._enable_log:
            try:
                bundle.log_evidence = self._run_log_plan(intent, entity)
            except Exception as e:
                logger.error(f"[LiveDiag] Log search failed: {e}")

        # 4. Execute SSH commands (multi-server)
        if self._enable_ssh:
            try:
                bundle.ssh_evidence = self._run_ssh_plan(intent)
            except Exception as e:
                logger.error(f"[LiveDiag] SSH plan failed: {e}")

        # 5. Normalize + resolve
        normalized_db = self._ev_norm.normalize_all(bundle.db_evidence)
        candidates = self._resolver.resolve(bundle, normalized_db)

        # Extract resolved eqpt_id for SQL placeholder substitution
        _eqpt_ev = bundle.db_evidence.get("get_equipment_id")
        _resolved_eqpt_id = None
        if _eqpt_ev and getattr(_eqpt_ev, "has_data", False):
            _resolved_eqpt_id = str(_eqpt_ev.rows[0].get("eqpt_id", "")) or None

        runtime_capabilities = {
            "db_available": self._enable_db,
            "logs_available": self._enable_log,
            "ssh_available": self._enable_ssh,
        }
        resolution_blocks = self._resolver.to_context_blocks(
            candidates,
            entity=entity,
            eqpt_id=_resolved_eqpt_id,
            runtime_capabilities=runtime_capabilities,
        )

        if debug:
            bundle.reasoning_trace["db_normalized"] = normalized_db
            bundle.reasoning_trace["resolution_candidates"] = [
                c.to_dict() for c in candidates
            ]

        # Always attach resolution blocks
        bundle.reasoning_trace["resolution_blocks"] = resolution_blocks

        # 6. Parse structured log evidence (forensic engine integration)
        try:
            from app.services.live_diagnostics.logs.log_parser import parse_log_lines
            from app.services.live_diagnostics.logs.log_correlation_engine import log_correlation_engine
            _all_log_lines: list = []
            for _lev in bundle.log_evidence:
                _all_log_lines.extend(getattr(_lev, "matched_lines", []))
            if _all_log_lines:
                _structured = parse_log_lines(_all_log_lines, source="live", min_score=0.30)
                bundle.reasoning_trace["structured_log_events"] = [
                    ev.to_compact_dict() for ev in _structured[:50]
                ]
                _hypotheses = log_correlation_engine.correlate(log_events=_structured)
                if _hypotheses:
                    bundle.reasoning_trace["correlation_hypotheses"] = [
                        h.to_dict() for h in _hypotheses[:5]
                    ]
                    logger.info(
                        f"[LiveDiag] Correlation: {len(_hypotheses)} hypotheses, "
                        f"top={_hypotheses[0].cause} conf={_hypotheses[0].confidence:.2f}"
                    )
        except Exception as _parse_err:
            logger.debug(f"[LiveDiag] Structured log parsing skipped: {_parse_err}")

        # 7. Forensic log structuring (Phase 5 — transforms raw logs into forensic objects)
        try:
            from app.services.live_diagnostics.logs.forensic_structurer import forensic_log_structurer
            _all_raw: list = []
            for _lev in bundle.log_evidence:
                _all_raw.extend(getattr(_lev, "matched_lines", []))
            if _all_raw:
                _eqpt_id = None
                if "get_equipment_id" in bundle.db_evidence:
                    _rows = bundle.db_evidence["get_equipment_id"].rows
                    if _rows:
                        _eqpt_id = _rows[0].get("eqpt_id")
                _forensic = forensic_log_structurer.structure(_all_raw, entity=entity, eqpt_id=_eqpt_id)
                bundle.reasoning_trace["forensic_summary"] = {
                    "severity": _forensic.severity,
                    "exception_chain": _forensic.exception_chain,
                    "error_codes": _forensic.error_codes,
                    "affected_tables": _forensic.affected_tables,
                    "has_rollback": _forensic.has_rollback,
                    "state_transitions": _forensic.state_transitions,
                    "timeline_count": len(_forensic.timeline),
                    "context_for_llm": _forensic.to_deterministic_context(max_lines=6),
                }
                bundle.reasoning_trace["forensic_object"] = _forensic
                logger.info(f"[LiveDiag] Forensic: severity={_forensic.severity}, {len(_forensic.exception_chain)} exceptions")
        except Exception as _fe:
            logger.debug(f"[LiveDiag] Forensic structuring skipped: {_fe}")

        # 8. Explainability chain (Phase 4)
        try:
            from app.services.live_diagnostics.explainability_engine import explainability_engine
            _code_hits = None
            try:
                from app.services.code_intelligence import CODE_INTELLIGENCE_ENABLED
                if CODE_INTELLIGENCE_ENABLED:
                    from app.services.code_intelligence.extractors.brasil_extractor import search_code_knowledge
                    _code_hits = search_code_knowledge(entity=entity, tags=[intent])
            except Exception:
                pass
            _corr_hyps = [
                type("H", (), h) for h in bundle.reasoning_trace.get("correlation_hypotheses", [])
            ] if bundle.reasoning_trace.get("correlation_hypotheses") else None
            _explanation = explainability_engine.explain(
                intent=intent,
                entity=entity,
                db_evidence=bundle.db_evidence if bundle.db_evidence else None,
                log_summary=bundle.reasoning_trace.get("forensic_object"),
                correlation_hypotheses=_corr_hyps,
                code_hits=_code_hits,
                resolution_blocks=resolution_blocks,
            )
            bundle.reasoning_trace["explanation"] = {
                "reasoning_chain_display": _explanation.to_reasoning_display(),
                "technical_block": _explanation.to_technical_block(),
                "collaborator_summary": _explanation.to_collaborator_block(),
                "root_cause": _explanation.root_cause,
                "workflow": _explanation.workflow,
                "source_location": _explanation.source_location,
                "fr_reference": _explanation.fr_reference,
                "evidence_count": _explanation.evidence_count,
            }
            logger.info(f"[LiveDiag] Explainability: root_cause={_explanation.root_cause}, {_explanation.evidence_count} sources")
        except Exception as _ex_err:
            logger.debug(f"[LiveDiag] Explainability skipped: {_ex_err}")

        logger.info(
            f"[LiveDiag] intent={intent} entity={entity} -> "
            f"{len(bundle.db_evidence)} db, {len(bundle.log_evidence)} log, "
            f"{len(bundle.ssh_evidence)} ssh, {len(candidates)} resolutions"
        )

        return bundle

    # ── DB execution ──────────────────────────────────────────────────────────

    def _run_db_plan(self, plan, entity: Optional[str]) -> Dict:
        """Execute DB plan with dynamic eqpt_id resolution."""
        results = {}
        eqpt_id = None
        tp_id   = None

        for qname in plan.db_queries:
            raw_params = plan.db_params_map.get(qname, [])

            # Resolve dynamic placeholders
            params = []
            for p in raw_params:
                if p == "__EQPT_ID__":
                    if eqpt_id is None:
                        logger.warning(f"[LiveDiag] eqpt_id not resolved yet for {qname}")
                        params.append(0)
                    else:
                        params.append(eqpt_id)
                elif p == "__TP_ID__":
                    if tp_id is None:
                        logger.warning(f"[LiveDiag] tp_id not resolved yet for {qname}")
                        params.append(0)
                    else:
                        params.append(tp_id)
                else:
                    params.append(p)

            ev = self._db_svc.execute(qname, params)
            results[qname] = ev

            # Resolve eqpt_id from first successful query
            if qname == "get_equipment_id" and ev.has_data:
                eqpt_id = ev.rows[0].get("eqpt_id")
                logger.info(f"[LiveDiag] Resolved eqpt_id={eqpt_id} for entity='{entity}'")

            if qname == "get_blocked_tps" and ev.has_data:
                tp_id = ev.rows[0].get("tp_id")
                logger.info(f"[LiveDiag] Resolved tp_id={tp_id}")

        return results

    # ── Multi-server log execution ────────────────────────────────────────────

    def _run_log_plan(self, intent: str, entity: Optional[str]) -> List:
        """Execute log searches using server_router to target the right server."""
        from app.services.live_diagnostics.models.evidence import EvidenceType, LogEvidence

        log_evidence = []
        searches = get_log_searches_for_intent(intent, entity)

        for search in searches:
            server_role = search["server"]
            log_path    = search["log_path"]
            patterns    = search["patterns"]
            ssh_client  = self._ssh_clients.get(server_role)

            if not ssh_client:
                logger.debug(f"[LiveDiag] No SSH client for {server_role.value}, skipping log search")
                continue

            # Separate bare patterns (standalone grep) from '+pattern' (piped AND with entity)
            _bare_patterns    = [p for p in patterns if p and not p.startswith("+")]
            _piped_patterns   = [p[1:] for p in patterns if p and p.startswith("+")]

            # Build combined grep commands:
            #   bare   → grep -i 'entity' log  (entity is always the first bare pattern)
            #   piped  → grep -i 'entity' log | grep -i 'secondary'
            # This guarantees every returned line mentions the entity.
            _entity_pattern = _bare_patterns[0] if _bare_patterns else None
            _effective_patterns: list = []
            if _entity_pattern:
                _effective_patterns.append((_entity_pattern, None))   # (primary, secondary)
            for _sec in _piped_patterns:
                if _entity_pattern:
                    _effective_patterns.append((_entity_pattern, _sec))
                else:
                    _effective_patterns.append((_sec, None))

            for pattern, _secondary in _effective_patterns:
                if not pattern:
                    continue
                try:
                    # Direct SSH grep on the target server
                    safe_pattern = pattern.replace("'", "'\"'\"'")
                    if _secondary:
                        safe_sec = _secondary.replace("'", "'\"'\"'")
                        cmd = (
                            f"grep -i '{safe_pattern}' '{log_path}' 2>/dev/null"
                            f" | grep -i '{safe_sec}'"
                            f" | tail -30"
                        )
                    else:
                        cmd = f"grep -m 100 -i '{safe_pattern}' '{log_path}' 2>/dev/null | tail -50"
                    result = ssh_client.exec_command(cmd, timeout_s=10)
                    output = result.get("output", "").strip() if isinstance(result, dict) else ""
                    lines = output.splitlines() if output else []

                    if lines:
                        # Extract error codes and exceptions
                        import re
                        # Only extract codes that appear after code= / err= prefix
                        # to avoid false positives like year 2026 from timestamps
                        _ec_explicit = re.findall(
                            r'(?:code|err(?:or)?|errcode)\s*[=:]\s*(\d{4,6})\b',
                            output, re.IGNORECASE
                        )
                        _ec_prefixed = re.findall(r'\bERR[-_](\d{4,6})\b', output, re.IGNORECASE)
                        error_codes = list(set(_ec_explicit + _ec_prefixed))[:5]
                        exceptions = list(set(re.findall(
                            r'((?:java\.lang\.|com\.orange\.)?\w*Exception\w*)', output
                        )))[:5]
                        constraints = list(set(re.findall(
                            r'(ConstraintViolation\w*|ForeignKey\w*|IntegrityConstraint\w*)', output
                        )))[:3]

                        ev = LogEvidence(
                            evidence_type=EvidenceType.LIVE_LOG,
                            log_file=f"{server_role.value}:{log_path}",
                            search_pattern=f"{pattern}|{_secondary}" if _secondary else pattern,
                            matched_lines=lines[:50],
                            match_count=len(lines),
                            error_codes=error_codes,
                            exceptions=exceptions,
                            detected_constraints=constraints,
                            confidence=0.90 if lines else 0.3,
                            severity="HIGH" if exceptions or constraints else "MEDIUM",
                        )
                        log_evidence.append(ev)
                        logger.info(
                            f"[LiveDiag][{server_role.value}] grep '{pattern}'"
                            f"{(' | grep ' + _secondary) if _secondary else ''} "
                            f"in {log_path} -> {len(lines)} lines"
                        )
                except Exception as e:
                    logger.warning(f"[LiveDiag][{server_role.value}] grep failed: {e}")

        return log_evidence

    # ── Multi-server SSH commands ─────────────────────────────────────────────

    def _run_ssh_plan(self, intent: str) -> List:
        """Execute SSH commands on the correct servers."""
        ssh_evidence = []
        targets = get_ssh_commands_for_intent(intent)

        for target in targets:
            server_role = target["server"]
            commands    = target["commands"]
            ssh_client  = self._ssh_clients.get(server_role)

            if not ssh_client:
                logger.debug(f"[LiveDiag] No SSH client for {server_role.value}, skipping SSH cmds")
                continue

            try:
                from app.services.ssh_operations.streaming.command_executor import CommandExecutor
                executor = CommandExecutor(ssh_client)
                for cmd_name in commands:
                    try:
                        ev = executor.execute(cmd_name)
                        ssh_evidence.append(ev)
                    except Exception as e:
                        logger.warning(f"[LiveDiag][{server_role.value}] cmd {cmd_name} failed: {e}")
            except Exception as e:
                logger.error(f"[LiveDiag][{server_role.value}] CommandExecutor init failed: {e}")

        return ssh_evidence


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Factory — instantiation from settings
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def create_orchestrator_from_settings() -> "LiveDiagnosticOrchestrator | None":
    """
    Instancie LiveDiagnosticOrchestrator avec connexions multi-serveurs.
    BDD + WA + DE (si configures).
    """
    try:
        from app.core.config import settings
    except Exception as e:
        logger.error(f"[LiveDiag] Impossible de charger les settings: {e}")
        return None

    if not settings.SSH_ENABLED:
        logger.info("[LiveDiag] SSH_ENABLED=false -> orchestrateur desactive")
        return None

    if not settings.SSH_BRASIL_HOST:
        logger.warning("[LiveDiag] SSH_BRASIL_HOST non configure -> orchestrateur desactive")
        return None

    from app.services.ssh_operations.client.ssh_client import SshClient
    from app.services.ssh_operations.client.ssh_pool import ssh_pool

    ssh_clients: Dict[ServerRole, SshClient] = {}

    # ── BDD server (pooled session) ──────────────────────────────────────────
    try:
        ssh_clients[ServerRole.BDD] = ssh_pool.get(
            "bdd",
            host=settings.SSH_BRASIL_HOST,
            port=settings.SSH_BRASIL_PORT,
            username=settings.SSH_BRASIL_USER,
            password=settings.SSH_BRASIL_PASSWORD or None,
            private_key_path=settings.SSH_BRASIL_PRIVATE_KEY or None,
            private_key_passphrase=settings.SSH_BRASIL_PRIVATE_KEY_PASS or None,
            connect_timeout_s=settings.SSH_CONNECT_TIMEOUT_S,
        )
        logger.info(f"[LiveDiag] BDD client (pooled) -> {settings.SSH_BRASIL_HOST}")
    except Exception as e:
        logger.error(f"[LiveDiag] BDD SshClient failed: {e}")
        return None

    # ── WA server (pooled session, optional) ─────────────────────────────────
    if getattr(settings, 'SSH_WA_HOST', ''):
        try:
            ssh_clients[ServerRole.WA] = ssh_pool.get(
                "wa",
                host=settings.SSH_WA_HOST,
                port=settings.SSH_WA_PORT,
                username=settings.SSH_WA_USER,
                password=settings.SSH_WA_PASSWORD or None,
                private_key_path=getattr(settings, 'SSH_WA_PRIVATE_KEY', '') or None,
                private_key_passphrase=getattr(settings, 'SSH_WA_PRIVATE_KEY_PASS', '') or None,
                connect_timeout_s=settings.SSH_CONNECT_TIMEOUT_S,
            )
            logger.info(f"[LiveDiag] WA client (pooled) -> {settings.SSH_WA_HOST}")
        except Exception as e:
            logger.warning(f"[LiveDiag] WA SshClient failed (non-blocking): {e}")

    # ── DE server (pooled session, optional) ─────────────────────────────────
    if getattr(settings, 'SSH_DE_HOST', ''):
        try:
            ssh_clients[ServerRole.DE] = ssh_pool.get(
                "de",
                host=settings.SSH_DE_HOST,
                port=settings.SSH_DE_PORT,
                username=settings.SSH_DE_USER,
                password=settings.SSH_DE_PASSWORD or None,
                private_key_path=getattr(settings, 'SSH_DE_PRIVATE_KEY', '') or None,
                private_key_passphrase=getattr(settings, 'SSH_DE_PRIVATE_KEY_PASS', '') or None,
                connect_timeout_s=settings.SSH_CONNECT_TIMEOUT_S,
            )
            logger.info(f"[LiveDiag] DE client (pooled) -> {settings.SSH_DE_HOST}")
        except Exception as e:
            logger.warning(f"[LiveDiag] DE SshClient failed (non-blocking): {e}")

    return LiveDiagnosticOrchestrator(
        ssh_clients=ssh_clients,
        db_name=settings.BRASIL_PSQL_DB_NAME,
        db_user=settings.BRASIL_PSQL_DB_USER,
        db_host_remote=settings.BRASIL_PSQL_DB_HOST,
        psql_bin=settings.BRASIL_PSQL_BIN,
        psql_lib=settings.BRASIL_PSQL_LIB,
        enable_live_db=True,
        enable_logs=True,
        enable_ssh=True,
    )
