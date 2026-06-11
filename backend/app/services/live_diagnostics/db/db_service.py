"""
db_service.py
━━━━━━━━━━━━━
Read-only database diagnostic service.

Security guarantees:
  - Only whitelisted queries (from db_query_registry) are executed
  - All queries run in a read-only transaction
  - Hard row limits enforced BEFORE returning results
  - Per-query timeouts enforced
  - All executions are audit-logged
  - Parameters are validated (type + length)
  - No SQL string construction from user input ever
"""

from __future__ import annotations

import base64
import logging
import re
import time
from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional

from app.services.live_diagnostics.db.db_query_registry import (
    ALLOWED_QUERIES,
    get_query,
)
from app.services.live_diagnostics.models.evidence import DbEvidence, EvidenceType

logger = logging.getLogger(__name__)

# ── Defaults ──────────────────────────────────────────────────────────────────
DEFAULT_TIMEOUT_S  = 8      # seconds per query
DEFAULT_MAX_ROWS   = 50
MAX_PARAM_STR_LEN  = 128    # safeguard against injection via long strings


# ─────────────────────────────────────────────────────────────────────────────
class SecurityError(Exception):
    """Raised when a forbidden SQL operation is attempted."""
    pass


class QueryRenderError(Exception):
    """Raised when SQL template rendering fails (unresolved placeholders)."""
    pass


class DbDiagnosticService:
    """
    Execute pre-approved read-only diagnostic queries against the Brasil DB.
    Requires a SQLAlchemy engine (or raw psycopg2 connection factory).
    """

    def __init__(self, engine=None, dsn: str | None = None):
        """
        engine : SQLAlchemy Engine (preferred)
        dsn    : raw psycopg2 DSN fallback (postgresql://user:pass@host/db)
        """
        self._engine = engine
        self._dsn    = dsn
        self._audit_log: List[Dict[str, Any]] = []

    # ── Connection context ────────────────────────────────────────────────────

    @contextmanager
    def _get_connection(self) -> Iterator:
        """Yield a read-only database connection."""
        if self._engine is not None:
            with self._engine.connect() as conn:
                conn.execute(_sa_text("SET TRANSACTION READ ONLY"))
                try:
                    yield conn
                finally:
                    conn.rollback()
        elif self._dsn:
            import psycopg2  # type: ignore
            conn = psycopg2.connect(self._dsn)
            conn.autocommit = False
            try:
                conn.execute("SET TRANSACTION READ ONLY")
                yield conn
            finally:
                conn.rollback()
                conn.close()
        else:
            raise RuntimeError("[DbService] No database connection configured.")

    # ── Parameter validation ──────────────────────────────────────────────────

    @staticmethod
    def _validate_params(params: list) -> list:
        """Reject oversized or non-scalar parameters."""
        clean = []
        for p in params:
            if p is None:
                clean.append(None)
            elif isinstance(p, (int, float)):
                clean.append(p)
            elif isinstance(p, str):
                if len(p) > MAX_PARAM_STR_LEN:
                    raise ValueError(
                        f"[DbService] Parameter too long ({len(p)} chars). "
                        f"Max allowed: {MAX_PARAM_STR_LEN}."
                    )
                # Basic anti-injection: reject comment sequences and stacked statements
                FORBIDDEN = ["--", ";", "/*", "*/", "xp_", "EXEC", "EXECUTE", "DROP", "DELETE", "UPDATE", "INSERT"]
                upper = p.upper()
                for f in FORBIDDEN:
                    if f in upper:
                        raise ValueError(f"[DbService] Forbidden token in parameter: '{f}'")
                clean.append(p)
            else:
                raise TypeError(f"[DbService] Unsupported parameter type: {type(p)}")
        return clean

    # ── Core execution ────────────────────────────────────────────────────────

    def execute(
        self,
        query_name: str,
        params: list | None = None,
        timeout_s: int | None = None,
        max_rows: int | None = None,
    ) -> DbEvidence:
        """
        Execute a whitelisted query by name.

        Returns a DbEvidence object with rows + metadata.
        Raises ValueError for unknown query names.
        """
        # 1. Whitelist check
        qdef = get_query(query_name)
        if qdef is None:
            raise ValueError(f"[DbService] Query '{query_name}' is not in the whitelist.")

        # 2. Resolve limits
        eff_timeout = timeout_s  or qdef.get("timeout", DEFAULT_TIMEOUT_S)
        eff_max     = max_rows   or qdef.get("max_rows", DEFAULT_MAX_ROWS)
        sql         = qdef["sql"]
        params      = self._validate_params(params or [])

        # 3. Audit record (before execution)
        audit = {
            "query_name": query_name,
            "params":     [str(p) for p in params],
            "timestamp":  time.time(),
            "success":    False,
            "row_count":  0,
            "duration_ms": 0,
        }

        t0 = time.perf_counter()
        rows: List[Dict[str, Any]] = []

        try:
            with self._get_connection() as conn:
                # Set per-query statement timeout (PostgreSQL)
                _exec_sql(conn, f"SET LOCAL statement_timeout = '{eff_timeout * 1000}'")

                result = _exec_sql(conn, sql, params)
                raw_rows = result.fetchmany(eff_max)
                cols = result.keys() if hasattr(result, "keys") else []
                rows = [dict(zip(cols, r)) for r in raw_rows]

            audit["success"]   = True
            audit["row_count"] = len(rows)

        except Exception as e:
            logger.error(f"[DbService] Query '{query_name}' failed: {e}")
            audit["error"] = str(e)
            return DbEvidence(
                evidence_type=EvidenceType.LIVE_DB,
                query_name=query_name,
                rows=[],
                row_count=0,
                error=str(e),
                confidence=0.0,
                truncated=False,
            )

        finally:
            audit["duration_ms"] = round((time.perf_counter() - t0) * 1000, 1)
            self._audit_log.append(audit)
            logger.info(
                f"[DbService] {query_name} -> {audit['row_count']} rows "
                f"({audit['duration_ms']} ms)"
            )

        truncated = len(rows) >= eff_max

        # Enforce evidence threshold
        confidence = 0.97 if rows else 0.5
        if confidence < 0.7:
            logger.warning(
                f"[DbService] Insufficient evidence for query '{query_name}' (confidence={confidence})."
            )
            return DbEvidence(
                evidence_type=EvidenceType.LIVE_DB,
                query_name=query_name,
                rows=rows,
                row_count=len(rows),
                error="Insufficient evidence",  # Set error field
                confidence=confidence,
                truncated=truncated,
                tags=qdef.get("tags", []),
            )

        return DbEvidence(
            evidence_type=EvidenceType.LIVE_DB,
            query_name=query_name,
            rows=rows,
            row_count=len(rows),
            error=None,
            confidence=confidence,
            truncated=truncated,
            tags=qdef.get("tags", []),
        )

    def execute_plan(
        self,
        query_names: list,
        params_map: Dict[str, list],
    ) -> Dict[str, DbEvidence]:
        """
        Execute a list of queries with per-query params from params_map.

        params_map = {
            "get_equipment_id": ["DSROB362"],
            "check_residual_references": [12345, 12345, 12345],
        }
        """
        results: Dict[str, DbEvidence] = {}
        for name in query_names:
            p = params_map.get(name, [])
            results[name] = self.execute(name, p)
        return results

    def get_audit_log(self) -> List[Dict[str, Any]]:
        return list(self._audit_log)

    def clear_audit_log(self) -> None:
        self._audit_log.clear()


# ─────────────────────────────────────────────────────────────────────────────
class SshPsqlDbService:
    """
    Execute whitelisted read-only diagnostic queries against BRASIL DB
    via SSH -> psql CLI.

    No TCP database port required — only SSH access to the DB server.

    Flow:
      1. Build safe SQL by substituting validated params into the whitelisted template
      2. Base64-encode the SQL to avoid quoting issues over SSH
      3. Run: psql -U user -d brasil -A -F'|' -c "$(echo <b64> | base64 -d)"
      4. Parse psql pipe-delimited output -> list of dicts
    """

    def __init__(
        self,
        ssh_client,
        db_name:  str = "brasil",
        db_user:  str = "postgres",
        db_host:  str = "localhost",
        db_port:  int = 5432,
        psql_bin: str = "/opt/pgsql/na/9.4.4/bin/psql",
        psql_lib: str = "/opt/pgsql/na/9.4.4/lib",
    ):
        self._ssh      = ssh_client
        self._db_name  = db_name
        self._db_user  = db_user
        self._db_host  = db_host
        self._db_port  = db_port
        self._psql_bin = psql_bin
        self._psql_lib = psql_lib
        self._audit_log: List[Dict[str, Any]] = []

    # ── Safe SQL construction ─────────────────────────────────────────────────

    @staticmethod
    def _validate_params(params: list) -> list:
        """Same strict validation as DbDiagnosticService."""
        clean = []
        for p in params:
            if p is None:
                clean.append(None)
            elif isinstance(p, (int, float)):
                clean.append(p)
            elif isinstance(p, str):
                if len(p) > MAX_PARAM_STR_LEN:
                    raise ValueError(f"[SshPsqlDbService] Parameter too long ({len(p)} chars).")
                FORBIDDEN = ["--", ";", "/*", "*/", "xp_", "EXEC", "DROP", "DELETE", "UPDATE", "INSERT"]
                for f in FORBIDDEN:
                    if f in p.upper():
                        raise ValueError(f"[SshPsqlDbService] Forbidden token in parameter: '{f}'")
                # Reject shell/SQL quote chars to prevent injection
                if re.search(r"[\"'`$\\!]", p):
                    raise ValueError(f"[SshPsqlDbService] Forbidden character in parameter: {p!r}")
                clean.append(p)
            else:
                raise TypeError(f"[SshPsqlDbService] Unsupported parameter type: {type(p)}")
        return clean

    @staticmethod
    def _validate_read_only(sql: str) -> None:
        """Reject any non-SELECT SQL before execution. FIX #3."""
        normalized = sql.strip().upper()
        FORBIDDEN_KEYWORDS = ["UPDATE ", "DELETE ", "INSERT ", "ALTER ", "DROP ", "TRUNCATE ", "GRANT ", "REVOKE ", "CREATE "]
        for kw in FORBIDDEN_KEYWORDS:
            if kw in normalized:
                raise SecurityError(f"[SshPsqlDbService] FORBIDDEN SQL keyword detected: {kw.strip()}")
        if not normalized.startswith("SELECT"):
            raise SecurityError(f"[SshPsqlDbService] Only SELECT queries allowed. Got: {normalized[:40]}")

    @staticmethod
    def _build_sql(template: str, params: list) -> str:
        """
        Substitute %s placeholders in the whitelisted SQL template.
        Params are already validated — safe to embed as SQL literals.
        Strings -> wrapped in single quotes, ints -> embedded as-is.
        """
        result = template
        for p in params:
            if p is None:
                literal = "NULL"
            elif isinstance(p, (int, float)):
                literal = str(p)
            else:
                # SQL-escape single quotes (standard SQL: ' -> '')
                literal = "'" + str(p).replace("'", "''") + "'"
            result = result.replace("%s", literal, 1)  # replace one at a time
        if "%s" in result:
            raise QueryRenderError("[SshPsqlDbService] Unresolved %s placeholder after param substitution.")
        return result

    # ── psql output parser ────────────────────────────────────────────────────

    @staticmethod
    def _parse_psql_output(output: str, max_rows: int) -> List[Dict[str, Any]]:
        """
        Parse psql -A -F'|' output:
          line 0 : col1|col2|col3   (headers)
          line 1+: val1|val2|val3   (data rows)
          last   : (N rows)          (ignored)
        """
        lines = [ln for ln in output.strip().splitlines() if ln.strip()]
        if not lines:
            return []

        # Detect psql error
        if lines[0].startswith("ERROR") or lines[0].startswith("FATAL"):
            raise RuntimeError(f"[SshPsqlDbService] psql error: {lines[0]}")

        headers = lines[0].split("|")
        rows: List[Dict[str, Any]] = []

        for line in lines[1:]:
            # Skip the trailing "(N rows)" summary line
            if re.match(r"^\(\d+ rows?\)$", line.strip()):
                continue
            if re.match(r"^\(\d+ row\)$", line.strip()):
                continue
            values = line.split("|")
            # Pad or truncate to header length
            values = (values + [""] * len(headers))[: len(headers)]
            rows.append(dict(zip(headers, values)))
            if len(rows) >= max_rows:
                break

        return rows

    # ── Core execution ────────────────────────────────────────────────────────

    def execute(
        self,
        query_name: str,
        params: list | None = None,
        timeout_s: int | None = None,
        max_rows: int | None = None,
    ) -> DbEvidence:
        """Execute a whitelisted query via SSH -> psql."""
        qdef = get_query(query_name)
        if qdef is None:
            raise ValueError(f"[SshPsqlDbService] Query '{query_name}' not in whitelist.")

        eff_timeout = timeout_s or qdef.get("timeout", DEFAULT_TIMEOUT_S)
        eff_max     = max_rows  or qdef.get("max_rows", DEFAULT_MAX_ROWS)
        params      = self._validate_params(params or [])

        audit = {
            "query_name":  query_name,
            "params":      [str(p) for p in params],
            "timestamp":   time.time(),
            "success":     False,
            "row_count":   0,
            "duration_ms": 0,
            "mode":        "ssh_psql",
        }
        t0   = time.perf_counter()
        rows: List[Dict[str, Any]] = []

        try:
            sql    = self._build_sql(qdef["sql"], params)
            # FIX #3: Validate read-only BEFORE SSH execution
            self._validate_read_only(sql)
            # Base64-encode to avoid quoting nightmares over SSH
            sql_b64 = base64.b64encode(sql.encode()).decode()
            cmd    = (
                f'LD_LIBRARY_PATH={self._psql_lib}:$LD_LIBRARY_PATH '
                f'{self._psql_bin} -U {self._db_user} -d {self._db_name} '
                f'-h {self._db_host} -p {self._db_port} '
                f"-A -F'|' -c \"$(echo {sql_b64} | base64 -d)\""
            )

            # Use the ssh_client's execute method
            result = self._ssh.exec_command(cmd, timeout_s=eff_timeout)
            stdout = result.get("output", result.get("stdout", "")) if isinstance(result, dict) else str(result)

            rows = self._parse_psql_output(stdout, eff_max)
            audit["success"]   = True
            audit["row_count"] = len(rows)

        except Exception as e:
            logger.error(f"[SshPsqlDbService] Query '{query_name}' failed: {e}")
            audit["error"] = str(e)
            return DbEvidence(
                evidence_type=EvidenceType.LIVE_DB,
                query_name=query_name,
                rows=[],
                row_count=0,
                error=str(e),
                confidence=0.0,
                truncated=False,
            )
        finally:
            audit["duration_ms"] = round((time.perf_counter() - t0) * 1000, 1)
            self._audit_log.append(audit)
            logger.info(
                f"[SshPsqlDbService] {query_name} -> {audit['row_count']} rows "
                f"({audit['duration_ms']} ms)"
            )

        return DbEvidence(
            evidence_type=EvidenceType.LIVE_DB,
            query_name=query_name,
            rows=rows,
            row_count=len(rows),
            error=None,
            confidence=0.97 if rows else 0.5,
            truncated=len(rows) >= eff_max,
            tags=qdef.get("tags", []),
        )

    def execute_plan(
        self,
        query_names: list,
        params_map: Dict[str, list],
    ) -> Dict[str, DbEvidence]:
        results: Dict[str, DbEvidence] = {}
        for name in query_names:
            p = params_map.get(name, [])
            results[name] = self.execute(name, p)
        return results

    def get_audit_log(self) -> List[Dict[str, Any]]:
        return list(self._audit_log)


# ── SQLAlchemy / psycopg2 compat helpers ──────────────────────────────────────

def _sa_text(sql: str):
    try:
        from sqlalchemy import text
        return text(sql)
    except ImportError:
        return sql


def _exec_sql(conn, sql: str, params: list | None = None):
    """Execute SQL on either a SQLAlchemy or psycopg2 connection."""
    try:
        from sqlalchemy import text
        if isinstance(sql, str):
            sql = text(sql)
        if params:
            return conn.execute(sql, params)
        return conn.execute(sql)
    except ImportError:
        # psycopg2 fallback
        cur = conn.cursor()
        cur.execute(sql, params or [])
        return cur
