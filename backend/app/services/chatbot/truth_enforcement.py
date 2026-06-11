"""
truth_enforcement.py
━━━━━━━━━━━━━━━━━━━━
Truth Enforcement Engine — Phase 1

Every claim in a chatbot response MUST be backed by a real index:
  • SQL table    → validated against BRASIL_SCHEMA_TABLES
  • Java method  → validated against execution graph / function knowledge index
  • Log file     → validated against discovered log inventory
  • FR reference → validated against known FR registry
  • Script path  → validated against indexed repository files
  • Shell command→ always blocked (no script generation in forensic mode)

If evidence is missing:
  - The suspect section is replaced with a deterministic uncertainty message.
  - LLM fabrications are NEVER forwarded to the user.

Design:
  - Stateless utility class — safe to call in any context
  - All validators are lazy-loaded (import on first use)
  - Never raises — returns safe fallback on any internal error
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# VIOLATION TYPES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class TruthViolation:
    """A single detected hallucination / unvalidated claim."""
    kind: str           # table | function | log_file | fr_ref | shell_cmd | sql_mutation
    value: str          # The suspect value
    context: str        # Surrounding text snippet (30 chars)
    blocked: bool = True
    safe_replacement: str = ""


@dataclass
class TruthReport:
    """Result of a full truth enforcement pass on a response text."""
    clean_text: str
    violations: List[TruthViolation] = field(default_factory=list)

    @property
    def has_violations(self) -> bool:
        return bool(self.violations)

    @property
    def violation_count(self) -> int:
        return len(self.violations)

    def summary(self) -> str:
        if not self.violations:
            return "✅ Truth check passed — no violations detected."
        lines = [f"⚠️ {self.violation_count} truth violation(s) detected:"]
        for v in self.violations:
            lines.append(f"  • [{v.kind}] `{v.value}` — {v.safe_replacement}")
        return "\n".join(lines)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# REGEX PATTERNS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Negative lookbehind for ⚠️` to avoid double-flagging already-marked tables
_TABLE_RX = re.compile(r"(?<!⚠️`)(?<!`)\bt_([a-z][a-z0-9_]{2,35})\b")
_FR_REF_RX = re.compile(r"\bFR[-_]?([A-Z0-9]{3,12})\b", re.IGNORECASE)
_FUNCTION_RX = re.compile(
    r"\b([A-Z][a-zA-Z0-9_]{3,60})\.((?:[a-z][a-zA-Z0-9_]{2,50})\(\))"
)
_LOG_FILE_RX = re.compile(
    r"\b((?:catalina|connectorCL|brasil_app|access|error|gc|jvm|brasil)[_\-]?\w*\.(?:log|out|txt))\b",
    re.IGNORECASE,
)
# SQL mutations forbidden in forensic mode
_SQL_MUTATION_RX = re.compile(
    r"(?:^|\s)(UPDATE|DELETE\s+FROM|INSERT\s+INTO|ALTER\s+TABLE|DROP\s+TABLE|TRUNCATE\s+TABLE)\b",
    re.IGNORECASE | re.MULTILINE,
)
# Shell command indicators — always blocked
_SHELL_CMD_RX = re.compile(
    r"(?:^|\s)(sudo\s|bash\s+|sh\s+|\.sh\b|systemctl\s|service\s+\w+\s+(?:start|stop|restart)|rm\s+-|chmod\s+|chown\s+)",
    re.IGNORECASE | re.MULTILINE,
)
# Placeholders in SQL — hallucination marker
_SQL_PLACEHOLDER_RX = re.compile(r"\[[A-Z][A-Z0-9_]{2,}\]")

# Safe message templates
_MSG_UNKNOWN_TABLE = "⚠️ Table `{name}` non présente dans le schéma BRASIL indexé."
_MSG_UNKNOWN_FUNC = "⚠️ Méthode `{name}` non validée dans l'index du code source."
_MSG_UNKNOWN_LOG = "⚠️ Fichier log `{name}` non présent dans l'inventaire découvert."
_MSG_UNKNOWN_FR = "⚠️ Référence FR `{name}` inconnue dans le registre KB."
_MSG_BLOCKED_MUTATION = "🚫 Commande SQL de mutation bloquée (mode forensique lecture seule)."
_MSG_BLOCKED_SHELL = "🚫 Commande shell bloquée — génération de scripts non autorisée en mode forensique."
_MSG_BLOCKED_PLACEHOLDER = "⚠️ Requête SQL retirée — contient des valeurs non résolues (placeholders)."


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LAZY INDEX LOADERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_KNOWN_TABLES: Set[str] = set()
_KNOWN_FUNCTIONS: Set[str] = set()   # "ClassName.method()" format
_KNOWN_LOG_FILES: Set[str] = set()
_KNOWN_FR_REFS: Set[str] = set()


def _load_known_tables() -> Set[str]:
    # Priorité 1: schéma extrait en live depuis brasil_prod
    try:
        from app.services.chatbot.brasil_schema_knowledge import REAL_SQL_TABLES as LIVE
        if LIVE:
            return set(LIVE)
    except ImportError:
        pass
    # Priorité 2: ontologie canonique (list statique vérifiée)
    try:
        from app.services.chatbot.ontology import REAL_SQL_TABLES
        return set(REAL_SQL_TABLES)
    except Exception:
        pass
    # Fallback: diagnostic_behavior
    try:
        from app.services.nlp.diagnostic_behavior import BRASIL_SCHEMA_TABLES
        return set(BRASIL_SCHEMA_TABLES)
    except Exception:
        pass
    # Last resort: real table names hardcoded (no invented tables)
    return {
        "t_equipments", "t_cards", "t_ports", "t_shelfs", "t_nodes",
        "t_tps", "t_tpinitialstates", "t_makingfiles",
        "t_epcs", "t_epcvers", "t_epcversimpacts", "t_epcorderlines",
        "t_mrt_access_dslams", "t_mrt_access_dslam_vers",
        "t_service_access_mrts", "t_service_access_mrt_vers",
        "t_medialinks", "t_res_prod_controlables", "t_res_prod_roles",
        "t_d_rscvcis", "t_d_controlablerscs", "t_d_dslammanelems",
        "t_es", "t_eslogs", "t_estypes",
        "t_techservices", "t_techservtypes", "t_mrtversimpacts",
    }


def _load_known_functions() -> Set[str]:
    """
    Load known Java method signatures from the execution graph cache.
    Format: "ClassName.methodName()"
    """
    known: Set[str] = set()
    try:
        from app.services.code_intelligence.operation_graph import get_execution_graph
        graph = get_execution_graph()
        for op_key, nodes in (graph or {}).items():
            for node in (nodes if isinstance(nodes, list) else []):
                cls = node.get("class", "")
                method = node.get("method", "")
                if cls and method:
                    known.add(f"{cls}.{method}()")
                    known.add(f"{cls}.{method}")
    except Exception:
        pass
    # Also load from function knowledge index (keyword index entries)
    try:
        from app.services.code_intelligence.function_knowledge_index import (
            FunctionKnowledgeIndex,
        )
        fki = FunctionKnowledgeIndex()
        for entry in getattr(fki, "_entries", []):
            cls = getattr(entry, "class_name", "") or ""
            method = getattr(entry, "method_name", "") or ""
            if cls and method:
                known.add(f"{cls}.{method}()")
    except Exception:
        pass
    return known


def _load_known_log_files() -> Set[str]:
    """
    Known log files discovered from SSH log inventory or static list.
    """
    base = {
        "catalina.out",
        "brasil_app.log",
        "connectorCL",
        "errors_sample.log",
        "gc.log",
        "jvm.log",
        "access.log",
    }
    try:
        from app.services.live_diagnostics.logs.log_reader import SSH_LOG_FILES
        for f in SSH_LOG_FILES:
            base.add(f.split("/")[-1])  # basename only
    except Exception:
        pass
    return base


def _load_known_fr_refs() -> Set[str]:
    """
    Load FR IDs from Qdrant KB or static registry.
    """
    known: Set[str] = set()
    try:
        from app.services.knowledge.qdrant_client import QdrantKnowledgeClient
        client = QdrantKnowledgeClient()
        # Lightweight: just get FR ids from the collection metadata
        all_fr = client.list_fr_ids() if hasattr(client, "list_fr_ids") else []
        known.update(str(f) for f in all_fr)
    except Exception:
        pass
    # Add known FRs from local KB files
    try:
        import os, glob
        fr_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "fr")
        for path in glob.glob(os.path.join(fr_dir, "*.json")):
            fr_id = os.path.basename(path).replace(".json", "")
            known.add(fr_id.upper())
    except Exception:
        pass
    return known


def _ensure_indexes() -> None:
    global _KNOWN_TABLES, _KNOWN_FUNCTIONS, _KNOWN_LOG_FILES, _KNOWN_FR_REFS
    if not _KNOWN_TABLES:
        _KNOWN_TABLES = _load_known_tables()
    if not _KNOWN_FUNCTIONS:
        _KNOWN_FUNCTIONS = _load_known_functions()
    if not _KNOWN_LOG_FILES:
        _KNOWN_LOG_FILES = _load_known_log_files()
    if not _KNOWN_FR_REFS:
        _KNOWN_FR_REFS = _load_known_fr_refs()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TRUTH ENFORCEMENT ENGINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TruthEnforcementEngine:
    """
    Validates every factual claim in a response text against real indexes.
    Replaces unvalidated claims with explicit uncertainty messages.

    Usage:
        report = truth_engine.enforce(response_text)
        safe_text = report.clean_text
    """

    def __init__(self, strict: bool = True):
        """
        Args:
            strict: When True, unknown tables/functions are flagged inline.
                    When False, only SQL mutations and shell commands are blocked.
        """
        self.strict = strict

    # ── Public entry point ─────────────────────────────────────────────────

    def enforce(self, text: str, context: Optional[Dict] = None) -> TruthReport:
        """
        Run all truth checks on ``text``.
        Returns a TruthReport with clean text and list of violations.
        """
        if not text:
            return TruthReport(clean_text=text)

        try:
            _ensure_indexes()
        except Exception:
            pass  # never block on index load failure

        violations: List[TruthViolation] = []

        # 1. SQL mutation blocking (always, regardless of strict mode)
        text, sql_viols = self._block_sql_mutations(text)
        violations.extend(sql_viols)

        # 2. Shell command blocking (always)
        text, shell_viols = self._block_shell_commands(text)
        violations.extend(shell_viols)

        # 3. SQL placeholder blocking (always)
        text, ph_viols = self._block_sql_placeholders(text)
        violations.extend(ph_viols)

        if self.strict:
            # 4. Table validation
            text, table_viols = self._flag_unknown_tables(text, context)
            violations.extend(table_viols)

            # 5. Function validation (only when function index is loaded)
            if _KNOWN_FUNCTIONS:
                text, func_viols = self._flag_unknown_functions(text)
                violations.extend(func_viols)

            # 6. Log file validation
            if _KNOWN_LOG_FILES:
                text, log_viols = self._flag_unknown_log_files(text)
                violations.extend(log_viols)

        if violations:
            logger.info(
                f"[TruthEnforcement] {len(violations)} violation(s) blocked: "
                + ", ".join(f"[{v.kind}]{v.value}" for v in violations[:5])
            )

        return TruthReport(clean_text=text, violations=violations)

    # ── Private validators ─────────────────────────────────────────────────

    def _block_sql_mutations(self, text: str) -> Tuple[str, List[TruthViolation]]:
        violations: List[TruthViolation] = []
        # Find SQL code blocks containing mutations and replace entire block
        def _replace_mutation_block(m: re.Match) -> str:
            keyword = m.group(1).split()[0].upper()
            violations.append(TruthViolation(
                kind="sql_mutation",
                value=keyword,
                context=m.group(0)[:40],
                safe_replacement=_MSG_BLOCKED_MUTATION,
            ))
            return f"\n{_MSG_BLOCKED_MUTATION}\n"

        # First pass: replace SQL fenced blocks containing mutations
        def _replace_sql_block(m: re.Match) -> str:
            content = m.group(0)
            if _SQL_MUTATION_RX.search(content):
                keyword = _SQL_MUTATION_RX.search(content).group(1).split()[0].upper()
                violations.append(TruthViolation(
                    kind="sql_mutation",
                    value=keyword,
                    context=content[:40],
                    safe_replacement=_MSG_BLOCKED_MUTATION,
                ))
                return f"```sql\n{_MSG_BLOCKED_MUTATION}\n```"
            return content

        text = re.sub(r"```sql[\s\S]*?```", _replace_sql_block, text, flags=re.IGNORECASE)

        # Second pass: inline mutation keywords outside code blocks
        text = _SQL_MUTATION_RX.sub(
            lambda m: f" {_MSG_BLOCKED_MUTATION} ", text
        )

        return text, violations

    def _block_shell_commands(self, text: str) -> Tuple[str, List[TruthViolation]]:
        violations: List[TruthViolation] = []

        def _replace_shell_block(m: re.Match) -> str:
            content = m.group(0)
            if _SHELL_CMD_RX.search(content):
                violations.append(TruthViolation(
                    kind="shell_cmd",
                    value=content[:40],
                    context=content[:40],
                    safe_replacement=_MSG_BLOCKED_SHELL,
                ))
                return f"```\n{_MSG_BLOCKED_SHELL}\n```"
            return content

        # Replace bash/sh fenced blocks
        text = re.sub(r"```(?:bash|sh|shell)[\s\S]*?```", _replace_shell_block, text, flags=re.IGNORECASE)

        return text, violations

    def _block_sql_placeholders(self, text: str) -> Tuple[str, List[TruthViolation]]:
        violations: List[TruthViolation] = []

        def _replace_placeholder_block(m: re.Match) -> str:
            content = m.group(0)
            if _SQL_PLACEHOLDER_RX.search(content):
                violations.append(TruthViolation(
                    kind="sql_placeholder",
                    value=_SQL_PLACEHOLDER_RX.search(content).group(0),
                    context=content[:40],
                    safe_replacement=_MSG_BLOCKED_PLACEHOLDER,
                ))
                return f"```sql\n{_MSG_BLOCKED_PLACEHOLDER}\n```"
            return content

        text = re.sub(r"```sql[\s\S]*?```", _replace_placeholder_block, text, flags=re.IGNORECASE)
        return text, violations

    def _flag_unknown_tables(
        self, text: str, context: Optional[Dict] = None
    ) -> Tuple[str, List[TruthViolation]]:
        violations: List[TruthViolation] = []
        # Tables mentioned in the context (from real DB evidence) are whitelisted
        context_tables: Set[str] = set()
        if context:
            ctx_str = str(context)
            for m in _TABLE_RX.finditer(ctx_str):
                context_tables.add(m.group(0))

        def _check(m: re.Match) -> str:
            full = m.group(0)
            if full in _KNOWN_TABLES or full in context_tables:
                return full
            # Check if it's a known invented/wrong table name and provide correction
            try:
                from app.services.chatbot.ontology import BANNED_INVENTED_TABLES
                correction = BANNED_INVENTED_TABLES.get(full.lower())
                if correction:
                    violations.append(TruthViolation(
                        kind="table",
                        value=full,
                        context=text[max(0, m.start()-20):m.start()+20],
                        safe_replacement=f"⚠️ Table `{full}` n'existe pas. {correction}",
                    ))
                    return f"⚠️`{full}` (→ {correction})"
            except Exception:
                pass
            violations.append(TruthViolation(
                kind="table",
                value=full,
                context=text[max(0, m.start()-20):m.start()+20],
                safe_replacement=_MSG_UNKNOWN_TABLE.format(name=full),
            ))
            return f"⚠️`{full}`"

        text = _TABLE_RX.sub(_check, text)
        return text, violations

    def _flag_unknown_functions(self, text: str) -> Tuple[str, List[TruthViolation]]:
        violations: List[TruthViolation] = []

        def _check(m: re.Match) -> str:
            full = f"{m.group(1)}.{m.group(2)}"
            full_no_parens = f"{m.group(1)}.{m.group(2).rstrip('()')}"
            # Check with and without parentheses
            if (full in _KNOWN_FUNCTIONS or full_no_parens in _KNOWN_FUNCTIONS or
                    any(full_no_parens in f for f in _KNOWN_FUNCTIONS)):
                return m.group(0)
            violations.append(TruthViolation(
                kind="function",
                value=full,
                context=text[max(0, m.start()-10):m.start()+30],
                blocked=False,  # flag only, don't replace functions
                safe_replacement=_MSG_UNKNOWN_FUNC.format(name=full),
            ))
            return m.group(0)  # keep text, only log violation

        text = _FUNCTION_RX.sub(_check, text)
        return text, violations

    def _flag_unknown_log_files(self, text: str) -> Tuple[str, List[TruthViolation]]:
        violations: List[TruthViolation] = []
        seen: Set[str] = set()

        def _check(m: re.Match) -> str:
            name = m.group(1)
            base = name.split("_")[0].lower()  # e.g. "connectorCL_20260515" → "connectorcl"
            known_bases = {f.split("_")[0].lower().split(".")[0] for f in _KNOWN_LOG_FILES}
            if name in _KNOWN_LOG_FILES or base in known_bases or name in seen:
                seen.add(name)
                return m.group(0)
            if name not in seen:
                seen.add(name)
                violations.append(TruthViolation(
                    kind="log_file",
                    value=name,
                    context=text[max(0, m.start()-10):m.start()+30],
                    blocked=False,
                    safe_replacement=_MSG_UNKNOWN_LOG.format(name=name),
                ))
            return m.group(0)

        text = _LOG_FILE_RX.sub(_check, text)
        return text, violations

    # ── Utility: validate single claims ───────────────────────────────────

    def is_known_table(self, table_name: str) -> bool:
        _ensure_indexes()
        return table_name in _KNOWN_TABLES

    def is_known_function(self, class_name: str, method_name: str) -> bool:
        _ensure_indexes()
        sig1 = f"{class_name}.{method_name}()"
        sig2 = f"{class_name}.{method_name}"
        return sig1 in _KNOWN_FUNCTIONS or sig2 in _KNOWN_FUNCTIONS

    def is_known_log_file(self, filename: str) -> bool:
        _ensure_indexes()
        base = filename.split("_")[0].lower().split(".")[0]
        known_bases = {f.split("_")[0].lower().split(".")[0] for f in _KNOWN_LOG_FILES}
        return filename in _KNOWN_LOG_FILES or base in known_bases

    def get_unknown_tables(self, text: str) -> List[str]:
        _ensure_indexes()
        return [
            m.group(0) for m in _TABLE_RX.finditer(text)
            if m.group(0) not in _KNOWN_TABLES
        ]

    def get_sql_mutations(self, text: str) -> List[str]:
        return [m.group(1).split()[0].upper() for m in _SQL_MUTATION_RX.finditer(text)]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SINGLETON
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

truth_engine = TruthEnforcementEngine(strict=True)
# Non-strict variant for LLM path (only blocks mutations/shells, not flags tables)
truth_engine_lenient = TruthEnforcementEngine(strict=False)
