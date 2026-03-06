"""
Log Ingestion Adapter — Future-ready adapter for server log extraction.
Parses application logs and converts them into structured error events,
linking them to the knowledge pipeline (clusters, procedures, error codes).

Supported log strategies:
  - brasil_api        : BRASIL API REST logs (JSON or text)
  - brasil_scheduler  : RDV/scheduler logs
  - interface         : Integration interface logs (BRASIL↔SEBA, etc.)
  - oracle            : Oracle DB logs
  - nginx             : HTTP gateway logs
  - generic           : Fallback for any structured log

Output: data_pipeline/output/log_events.json

Usage:
  python data_pipeline/log_ingester.py --log-file /path/to/logs/error.log
  python data_pipeline/log_ingester.py --log-dir /var/log/brasil/ --strategy brasil_api
"""
import re
import json
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from collections import Counter

BACKEND_DIR = Path(__file__).parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

OUTPUT_FILE = Path(__file__).parent / "output" / "log_events.json"

# ─────────────────────────────────────────────
# Priority log paths — ranked by importance
# ─────────────────────────────────────────────
PRIORITY_LOG_GUIDE = """
╔══════════════════════════════════════════════════════════════════╗
║        GUIDE D'EXTRACTION DES LOGS PRIORITAIRES                 ║
╚══════════════════════════════════════════════════════════════════╝

PRIORITÉ 1 — Logs Applicatifs BRASIL (haute valeur)
  /var/log/brasil/api/error.log          ← Erreurs API (4002, 500)
  /var/log/brasil/api/access.log         ← Requêtes/réponses, temps
  /var/log/brasil/scheduler/rdv.log      ← Événements RDV/planning
  /var/log/brasil/commands/cmd.log       ← Exécution de commandes

PRIORITÉ 2 — Logs d'Intégration
  /var/log/brasil/interface/seba.log     ← Échanges BRASIL↔SEBA
  /var/log/brasil/interface/ipon.log     ← Échanges BRASIL↔IPON
  /var/log/brasil/interface/artemis.log  ← Échanges BRASIL↔ARTEMIS
  /var/log/brasil/mq/errors.log          ← Échecs MQ/messages

PRIORITÉ 3 — Infrastructure
  /var/log/nginx/error.log               ← Erreurs gateway HTTP
  /var/log/postgresql/postgresql.log     ← Erreurs DB, deadlocks
  /var/log/syslog                        ← Événements système

PRIORITÉ 4 — Applications interfacées
  /var/log/seba/errors.log               ← Refus de commandes SEBA
  /var/log/orchestra/pipeline.log        ← Échecs d'orchestration
  /var/log/adelia/processing.log         ← Erreurs traitement

CHAMPS CLÉS À EXTRAIRE:
  timestamp, level (ERROR/WARN/INFO), service, error_code,
  endpoint, user_id, request_id, message, upstream_system, duration_ms
"""


# ─────────────────────────────────────────────
# Log parsers per strategy
# ─────────────────────name———————————————————
class LogEvent:
    """Structured log event."""
    def __init__(self, raw_line: str = ""):
        self.raw_line = raw_line
        self.timestamp: Optional[str] = None
        self.level: str = "INFO"
        self.service: str = ""
        self.error_code: Optional[str] = None
        self.endpoint: Optional[str] = None
        self.user_id: Optional[str] = None
        self.request_id: Optional[str] = None
        self.message: str = ""
        self.upstream_system: Optional[str] = None
        self.duration_ms: Optional[int] = None
        self.stack_trace: Optional[str] = None
        self.application: str = "BRASIL"
        # Derived after parsing
        self.incident_type: str = ""
        self.matched_error_codes: List[str] = []

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "level": self.level,
            "service": self.service,
            "error_code": self.error_code,
            "endpoint": self.endpoint,
            "user_id": self.user_id,
            "request_id": self.request_id,
            "message": self.message[:500],
            "upstream_system": self.upstream_system,
            "duration_ms": self.duration_ms,
            "application": self.application,
            "incident_type": self.incident_type,
            "matched_error_codes": self.matched_error_codes,
            "raw_line": self.raw_line[:300],
        }


def _extract_timestamp(line: str) -> Optional[str]:
    """Extract ISO timestamp or common log timestamp formats."""
    patterns = [
        r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)",
        r"(\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2})",     # nginx: 15/Mar/2024:10:32:44
        r"(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})",     # syslog: Mar 15 10:32:44
    ]
    for p in patterns:
        m = re.search(p, line)
        if m:
            return m.group(1)
    return None


def _extract_error_codes(text: str) -> List[str]:
    """Extract BRASIL-specific error codes from log text."""
    codes = []
    patterns = [
        r"\b(B\d{4})\b",           # B4002
        r"\bERREUR?\s+(\d{3,5})\b", # ERREUR 1300
        r"\bcode[:\s]+(\d{3,5})\b", # code: 4002
        r"\b(ORA-\d{4,6})\b",      # ORA-12170
        r"\b(AVP[-\s]?\d+)\b",     # AVP 1300
        r"\b(42C)\b",
        r"\b(1300|9903|1002|4002|42C|300|327|1583)\b",
    ]
    for pattern in patterns:
        found = re.findall(pattern, text, re.IGNORECASE)
        codes.extend(f.upper() for f in found)
    return list(set(codes))


def _detect_level(line: str) -> str:
    """Detect log level from line."""
    line_upper = line.upper()
    for level in ["ERROR", "FATAL", "CRITICAL", "WARN", "WARNING", "INFO", "DEBUG"]:
        if level in line_upper:
            return level if level not in ("WARN",) else "WARNING"
    return "INFO"


def _detect_upstream_system(text: str) -> Optional[str]:
    """Detect referenced upstream system in a log line."""
    text_upper = text.upper()
    for sys_name in ["SEBA", "ARTEMIS", "IPON", "ADELIA", "SCA", "ORCHESTRA"]:
        if sys_name in text_upper:
            return sys_name
    return None


def parse_brasil_api_log(line: str) -> Optional[LogEvent]:
    """
    Parser for BRASIL API logs.
    Handles both JSON format: {"timestamp":...,"level":...,"message":...}
    and text format: 2024-03-15 10:32:44 ERROR [brasil-api] Erreur 4002...
    """
    event = LogEvent(raw_line=line)

    # Try JSON first
    try:
        data = json.loads(line)
        event.timestamp = data.get("timestamp") or data.get("time") or data.get("@timestamp")
        event.level = str(data.get("level", "INFO")).upper()
        event.service = data.get("service", "brasil-api")
        event.message = str(data.get("message", data.get("msg", "")))
        event.error_code = data.get("error_code") or data.get("errorCode")
        event.endpoint = data.get("endpoint") or data.get("path") or data.get("url")
        event.user_id = data.get("user_id") or data.get("userId")
        event.request_id = data.get("request_id") or data.get("requestId")
        event.duration_ms = data.get("duration_ms") or data.get("durationMs")
        if isinstance(event.duration_ms, str):
            event.duration_ms = int(re.sub(r"\D", "", event.duration_ms) or 0)
        event.upstream_system = data.get("upstream_system") or _detect_upstream_system(event.message)
        if not event.error_code:
            codes = _extract_error_codes(event.message)
            event.error_code = codes[0] if codes else None
        event.matched_error_codes = _extract_error_codes(event.message)
        return event
    except (json.JSONDecodeError, Exception):
        pass

    # Text format fallback
    event.timestamp = _extract_timestamp(line)
    event.level = _detect_level(line)
    event.message = line.strip()[:500]
    event.service = "brasil-api"
    event.upstream_system = _detect_upstream_system(line)
    event.matched_error_codes = _extract_error_codes(line)
    event.error_code = event.matched_error_codes[0] if event.matched_error_codes else None

    # Skip pure INFO lines without errors
    if event.level == "INFO" and not event.error_code:
        return None
    return event


def parse_nginx_log(line: str) -> Optional[LogEvent]:
    """
    Parser for nginx access/error logs.
    Format: 127.0.0.1 - - [15/Mar/2024:10:32:44 +0000] "GET /api/v2/... HTTP/1.1" 500 1234
    """
    event = LogEvent(raw_line=line)

    # Only capture error responses (4xx, 5xx)
    status_match = re.search(r'"[A-Z]+ (/[^"]+) HTTP/\S+"\s+(\d{3})', line)
    if status_match:
        event.endpoint = status_match.group(1)[:200]
        status_code = int(status_match.group(2))
        if status_code < 400:
            return None  # Skip success responses
        event.level = "ERROR" if status_code >= 500 else "WARNING"
        event.error_code = str(status_code)
    else:
        return None

    event.timestamp = _extract_timestamp(line)
    event.service = "nginx"
    event.message = f"HTTP {event.error_code} on {event.endpoint}"
    event.matched_error_codes = [event.error_code]
    return event


def parse_oracle_log(line: str) -> Optional[LogEvent]:
    """Parser for Oracle database logs."""
    event = LogEvent(raw_line=line)
    event.service = "oracle-db"
    event.timestamp = _extract_timestamp(line)
    event.level = _detect_level(line)

    ora_codes = re.findall(r"ORA-\d{4,6}", line, re.IGNORECASE)
    if not ora_codes:
        return None

    event.error_code = ora_codes[0]
    event.matched_error_codes = list(set(c.upper() for c in ora_codes))
    event.message = line.strip()[:500]
    return event


def parse_generic_log(line: str) -> Optional[LogEvent]:
    """Generic log parser — catches anything with an error code or ERROR level."""
    event = LogEvent(raw_line=line)
    event.timestamp = _extract_timestamp(line)
    event.level = _detect_level(line)
    event.message = line.strip()[:500]
    event.service = "unknown"
    event.matched_error_codes = _extract_error_codes(line)
    event.error_code = event.matched_error_codes[0] if event.matched_error_codes else None

    # Only keep lines with errors
    if event.level in ("ERROR", "FATAL", "CRITICAL", "WARNING") or event.error_code:
        event.upstream_system = _detect_upstream_system(line)
        return event
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Real BRASIL log formats
# ─────────────────────────────────────────────────────────────────────────────

# Regex to extract exception class names from com.orange.brasil.*
_EXCEPTION_CLASS_RE = re.compile(
    r"(com\.orange\.brasil\.exception\.\S+Exception|"
    r"com\.orange\.brasil\.exception\.\S+Error)",
    re.IGNORECASE,
)

# Known BRASIL exception → short label mapping
_EXCEPTION_SHORT = {
    "DslamClosedForProductionException": "DSLAM_CLOSED",
    "UnknownMRTIdException": "UNKNOWN_MRT",
    "AvailableNetworkResourcesDisallowProductionException": "NET_DISALLOW",
    "DslamUnreachableException": "DSLAM_UNREACHABLE",
    "DslamNotFoundException": "DSLAM_NOT_FOUND",
    "CommandValidationException": "CMD_VALIDATION",
    "BusinessRuleViolationException": "BIZ_RULE",
    "BusinessRuleException": "BIZ_RULE",
    "ConnectorUnavailableException": "CONNECTOR_KO",
    "IntegrationTimeoutException": "INT_TIMEOUT",
    "SessionExpiredException": "SESSION_EXP",
    "ProvisioningTimeoutException": "PROV_TIMEOUT",
    "IdCrcMrtAlreadyUseException": "MRT_DUPLICATE",
    "BrasilInternalErrorException": "INTERNAL_ERROR",
    "DslamAccessMrtFunctionalException": "MRT_NOT_FOUND",
    "CclNotFoundForCEVOfferException": "CCL_NOT_FOUND",
    "UnknownEptException": "UNKNOWN_EPT",
    "EptAlreadyExistsException": "EPT_DUPLICATE",
}

# French message patterns → exception code mapping (for messages without FQCN)
_FR_MESSAGE_EXCEPTION_MAP = [
    (re.compile(r"accès client existe déjà|MRTChemin déjà porté", re.I),        "MRT_DUPLICATE"),
    (re.compile(r"Macro Ressource Technique .+ inconnu", re.I),                  "UNKNOWN_MRT"),
    (re.compile(r"MRT Access DSLAM ne correspond",  re.I),                       "MRT_NOT_FOUND"),
    (re.compile(r"DSLAM .+ closed for production|fermé à la production", re.I),  "DSLAM_CLOSED"),
    (re.compile(r"Card .+ closed for production|carte .+ fermée", re.I),         "DSLAM_CLOSED"),
    (re.compile(r"DSLAM .+ (inaccessible|unreachable|joignable)", re.I),         "DSLAM_UNREACHABLE"),
    (re.compile(r"ressources? réseau .+ interdit|disallow.+production", re.I),   "NET_DISALLOW"),
    (re.compile(r"règle métier|businessRule|règle de gestion", re.I),            "BIZ_RULE"),
    (re.compile(r"connecteur .+ indisponible|connector .+ unavailable", re.I),   "CONNECTOR_KO"),
    (re.compile(r"timeout|délai.?dépassé|time.?out", re.I),                      "INT_TIMEOUT"),
    (re.compile(r"session .+(expir|invalid|expiré)", re.I),                      "SESSION_EXP"),
    (re.compile(r"Echec de la recherche de broche", re.I),                       "DSLAM_CLOSED"),
    (re.compile(r"Erreur interne Brasil", re.I),                                 "INTERNAL_ERROR"),
    (re.compile(r"transaction .* status.*KO|rapportTransaction.*KO", re.I),      "TRANSACTION_KO"),
    (re.compile(r"Resources not found for following TechServiceFunction", re.I), "TSF_NOT_FOUND"),
    (re.compile(r"TechServiceFunction.*(not found|introuvable|inexistant)", re.I), "TSF_NOT_FOUND"),
    (re.compile(r"not found|introuvable|non trouvé", re.I),                      "RESOURCE_NOT_FOUND"),
    (re.compile(r"already exists|déjà existant|déjà créé", re.I),               "DUPLICATE_RESOURCE"),
    (re.compile(r"validation (error|fail|échoue)", re.I),                        "CMD_VALIDATION"),
    (re.compile(r"provisioning.*(fail|error|échec)|échec.*(provisioning|provisionn)", re.I), "PROV_FAILURE"),
    (re.compile(r"équipement ne permet pas la production|ne peut pas être mis en production", re.I), "EQUIP_PROD_BLOCKED"),
    (re.compile(r"services? cibles?.*(impossible|interdit|bloqué)|production.*bloquée", re.I), "EQUIP_PROD_BLOCKED"),
    (re.compile(r"Vlan .+ déjà existant|vlan.*already", re.I),                  "VLAN_DUPLICATE"),
    (re.compile(r"port.*(occupé|already used|déjà utilisé)", re.I),              "PORT_CONFLICT"),
    (re.compile(r"broche.*(non trouvé|introuvable|not found)|No port found|Aucune broche", re.I), "PORT_NOT_FOUND"),
    (re.compile(r"erreur.*commande|command.*error|échec.*commande", re.I),       "CMD_ERROR"),
    (re.compile(r"Identifiant de dossier de réalisation .+ inconnu|dossier.*(inconnu|not found)", re.I), "DOSSIER_NOT_FOUND"),
    (re.compile(r"NumeroCCL est obligatoire|CCL.*(manquant|obligatoire|requis)", re.I), "CCL_NOT_FOUND"),
    (re.compile(r"deadlock detected|LockAcquisitionException|Caused by:.*deadlock", re.I), "DB_DEADLOCK"),
    (re.compile(r"current transaction is aborted|commands ignored until end of transaction", re.I), "DB_DEADLOCK"),
    (re.compile(r"PSQLException|postgresql.*error|hibernate.*exception|Caused by:.*PSQLException", re.I), "DB_ERROR"),
    (re.compile(r"VLAN .+ n'existe pas|vlan.*(inexistant|not found|fermé)", re.I), "VLAN_NOT_FOUND"),
    (re.compile(r"TST list not supported|not supported by DSLAM", re.I),         "DSLAM_CAPABILITY"),
    (re.compile(r"identifiant d'EPC .+ déjà utilisé|EPC.*(duplicate|doublon|déjà)", re.I), "EPC_DUPLICATE"),
    (re.compile(r"déjà utilisé|already in use|doublon|duplicate", re.I),        "DUPLICATE_RESOURCE"),
    (re.compile(r"accès est déjà en cours de modification|dossier en cours|accès verrouillé", re.I), "ACCESS_LOCKED"),
    (re.compile(r"en cours de traitement|en attente|locked by another", re.I),  "ACCESS_LOCKED"),
    (re.compile(r"Preparation du rollback|transaction.*(rollback|annulée)|rollback", re.I), "TX_ROLLBACK"),
    (re.compile(r"TX_ROLLBACK", re.I),                                           None),  # placeholder
    (re.compile(r"Initiating transaction (rollback|commit)|AbstractPlatformTransaction", re.I), "TX_ROLLBACK"),
]

# Messages to discard — operational/framework noise that aren't real errors
_NOISE_PATTERNS = re.compile(
    r"(Preparation du retry suite|retry suite au deadlock|"
    r"Preparation du rollback|Initiating transaction rollback|"
    r"Rollback.*applied|AbstractPlatformTransactionManager|"
    r"No TransactionInfo found.*thread|"
    r"Skipping commit|No value for key.*bound to thread)",
    re.IGNORECASE
)


def _classify_message(message: str) -> Optional[str]:
    """Map a French BRASIL message to a known exception code."""
    for pattern, code in _FR_MESSAGE_EXCEPTION_MAP:
        if pattern.search(message):
            return code
    return None


def _extract_exception_class(text: str) -> Optional[str]:
    """Extract the short exception class name from a FQCN string."""
    m = _EXCEPTION_CLASS_RE.search(text)
    if m:
        fqcn = m.group(1)
        return fqcn.rsplit(".", 1)[-1]
    # simple bare class name like DslamClosedForProductionException
    for cls in _EXCEPTION_SHORT:
        if cls in text:
            return cls
    return None


def parse_brasil_error_log(line: str) -> Optional[LogEvent]:
    """
    Parser for aggregated error files (errors_sample.log).
    Format: <filepath>:<timestamp> LEVEL [thread] class(line) - message
    Also handles bare exception dump lines: <filepath>:com.orange.brasil...Exception: msg
    """
    event = LogEvent(raw_line=line)

    # Strip leading filepath prefix (e.g. /opt/application/.../file.log:)
    filepath_prefix_re = re.match(r"^(/[^:]+\.log):(.+)$", line, re.DOTALL)
    if filepath_prefix_re:
        source_file = filepath_prefix_re.group(1)
        line_body = filepath_prefix_re.group(2).strip()
        # Detect connector/component from path
        fname = source_file.rsplit("/", 1)[-1]
        if "connectorCL" in fname:
            event.service = "connectorCL"
        elif "connectorCreationVlan" in fname:
            event.service = "connectorCreationVlan"
        elif "catalina" in fname:
            event.service = "tomcat-catalina"
        elif "transaction" in fname:
            event.service = "transaction"
        else:
            event.service = fname.replace(".log", "")
    else:
        line_body = line.strip()
        event.service = "brasil-api"

    # Case 1: timestamped log line — 2026-03-05 07:20:36,738 ERROR [thread] class(line) - msg
    ts_re = re.match(
        r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}[,.]\d+)\s+(ERROR|WARN|WARNING|INFO|DEBUG|FATAL)"
        r"\s+\[([^\]]+)\]\s+\S+\s+-\s+(.+)$",
        line_body, re.DOTALL
    )
    if ts_re:
        event.timestamp = ts_re.group(1)
        event.level = ts_re.group(2).upper().replace("WARNING", "WARN")
        event.message = ts_re.group(4).strip()[:500]
        event.matched_error_codes = _extract_error_codes(event.message)
        event.error_code = event.matched_error_codes[0] if event.matched_error_codes else None
        exc_cls = _extract_exception_class(event.message)
        if exc_cls:
            event.error_code = event.error_code or _EXCEPTION_SHORT.get(exc_cls, exc_cls)
            event.matched_error_codes = list(set(event.matched_error_codes + [_EXCEPTION_SHORT.get(exc_cls, exc_cls)]))
        if not event.error_code:
            fr_code = _classify_message(event.message)
            if fr_code:
                event.error_code = fr_code
                event.matched_error_codes = [fr_code]
        event.upstream_system = _detect_upstream_system(event.message)
        # Only keep ERROR/WARN/FATAL
        if event.level in ("ERROR", "WARN", "FATAL", "CRITICAL"):
            # Filter out framework/operational noise
            if _NOISE_PATTERNS.search(event.message):
                return None
            return event
        return None

    # Case 2: pure exception class line — com.orange.brasil.exception.X: message
    exc_line_re = re.match(
        r"(com\.orange\.brasil\.\S+Exception|java\.lang\.\S+Exception):\s*(.+)$",
        line_body
    )
    if exc_line_re:
        event.level = "ERROR"
        event.message = line_body.strip()[:500]
        exc_cls = _extract_exception_class(line_body)
        if exc_cls:
            short = _EXCEPTION_SHORT.get(exc_cls, exc_cls)
            event.error_code = short
            event.matched_error_codes = [short]
        else:
            event.matched_error_codes = _extract_error_codes(line_body)
            event.error_code = event.matched_error_codes[0] if event.matched_error_codes else None
        if not event.error_code:
            fr_code = _classify_message(line_body)
            if fr_code:
                event.error_code = fr_code
                event.matched_error_codes = [fr_code]
        event.upstream_system = _detect_upstream_system(line_body)
        return event

    # Skip Caused by: stack trace continuation lines (they are part of a previous event)
    if line_body.startswith("Caused by:") or line_body.startswith("\tat ") or line_body.startswith("at "):
        return None

    return None


def parse_brasil_solicitation_log(line: str) -> Optional[LogEvent]:
    """
    Parser for BRASIL solicitation performance files.
    Format: 2026-03-01 00:05:00 SEBAR_OperationName=count,duration_ms
    These are stats lines — we extract slow calls (duration > 5000ms) as warnings.
    """
    m = re.match(
        r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+(\w+_\w+)=(\d+),(\d+)$",
        line.strip()
    )
    if not m:
        return None
    timestamp, operation, count, duration_ms = m.group(1), m.group(2), int(m.group(3)), int(m.group(4))
    avg_ms = duration_ms // max(count, 1)
    # Only keep slow or high-volume calls as noteworthy events
    if avg_ms < 3000 and count < 50:
        return None
    event = LogEvent(raw_line=line)
    event.timestamp = timestamp
    event.level = "ERROR" if avg_ms > 10000 else "WARN"
    event.service = operation.split("_")[0].upper()  # e.g. SEBAR
    event.message = f"{operation}: {count} appels, durée moy {avg_ms}ms (total {duration_ms}ms)"
    event.error_code = "SLOW_CALL" if avg_ms > 5000 else "HIGH_VOLUME"
    event.matched_error_codes = [event.error_code]
    event.duration_ms = avg_ms
    event.upstream_system = event.service if event.service != "BRASIL" else None
    return event


def parse_brasil_transaction_log(line: str) -> Optional[LogEvent]:
    """
    Parser for BRASIL transaction logs (49mapp_transaction.log).
    Format: <timestamp> ERROR [thread] transaction(line) - <transaction ... status='KO'>...
    Only captures KO (failed) transactions.
    """
    if "status='KO'" not in line and 'status="KO"' not in line:
        return None
    event = LogEvent(raw_line=line)
    event.level = "ERROR"
    event.service = "brasil-transaction"
    event.timestamp = _extract_timestamp(line)
    # Extract operation name from titre attribute
    titre_m = re.search(r"titre='([^']+)'", line)
    if titre_m:
        event.message = f"Transaction KO: {titre_m.group(1)}"
        event.endpoint = titre_m.group(1)
    else:
        event.message = "Transaction KO"
    event.matched_error_codes = _extract_error_codes(line)
    event.error_code = event.matched_error_codes[0] if event.matched_error_codes else "TRANSACTION_KO"
    if not event.error_code:
        event.error_code = "TRANSACTION_KO"
        event.matched_error_codes = ["TRANSACTION_KO"]
    event.upstream_system = _detect_upstream_system(line)
    return event


STRATEGY_PARSERS = {
    "brasil_api":         parse_brasil_api_log,
    "brasil_error":       parse_brasil_error_log,
    "brasil_scheduler":   parse_brasil_api_log,
    "brasil_transaction": parse_brasil_transaction_log,
    "brasil_solicitation": parse_brasil_solicitation_log,
    "interface":          parse_brasil_api_log,
    "nginx":              parse_nginx_log,
    "oracle":             parse_oracle_log,
    "generic":            parse_generic_log,
}

# Auto-detect strategy from filename
_FILENAME_STRATEGY_MAP = [
    (re.compile(r"errors_sample"),                   "brasil_error"),
    (re.compile(r"exceptions_sample"),               "brasil_error"),
    (re.compile(r"connector\w+_\d{8}"),              "brasil_error"),
    (re.compile(r"\d{2}mapp_transaction"),            "brasil_transaction"),
    (re.compile(r"solicitation\w+_\d{6}"),           "brasil_solicitation"),
    (re.compile(r"nginx"),                           "nginx"),
    (re.compile(r"oracle|ORA"),                      "oracle"),
]

# File extensions/names to skip entirely
_SKIP_FILENAMES = re.compile(
    r"(app_tree|log_tree|PLACER_CSV|README|CHEATSHEET|tickets\.csv)",
    re.IGNORECASE
)


def _auto_detect_strategy(filename: str, default: str) -> str:
    """Auto-detect parsing strategy from filename."""
    for pattern, strategy in _FILENAME_STRATEGY_MAP:
        if pattern.search(filename):
            return strategy
    return default


def parse_log_file(
    log_path: Path,
    strategy: str = "generic",
    application: str = "BRASIL",
) -> List[LogEvent]:
    """Parse a log file and return list of LogEvent objects."""
    parser = STRATEGY_PARSERS.get(strategy, parse_generic_log)
    events = []
    errors = 0

    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                event = parser(line)
                if event:
                    event.application = application
                    # Enrich with incident type
                    try:
                        from app.services.nlp.taxonomy import find_incident_type
                        event.incident_type = find_incident_type(event.message)
                    except Exception:
                        pass
                    events.append(event)
            except Exception:
                errors += 1
                continue

    return events


def aggregate_patterns(events: List[LogEvent]) -> List[Dict]:
    """
    Aggregate log events by error code → count occurrences.
    Returns patterns sorted by frequency.
    """
    patterns: Dict[str, Dict] = {}
    for e in events:
        key = e.error_code or e.level
        if key not in patterns:
            patterns[key] = {
                "error_code": e.error_code,
                "level": e.level,
                "count": 0,
                "services": set(),
                "endpoints": set(),
                "messages_sample": [],
                "upstream_systems": set(),
                "incident_types": set(),
                "first_seen": e.timestamp,
                "last_seen": e.timestamp,
            }
        p = patterns[key]
        p["count"] += 1
        if e.service:
            p["services"].add(e.service)
        if e.endpoint:
            p["endpoints"].add(e.endpoint)
        if e.upstream_system:
            p["upstream_systems"].add(e.upstream_system)
        if e.incident_type:
            p["incident_types"].add(e.incident_type)
        if len(p["messages_sample"]) < 3:
            p["messages_sample"].append(e.message[:200])
        if e.timestamp:
            if not p["last_seen"] or e.timestamp > p["last_seen"]:
                p["last_seen"] = e.timestamp

    # Convert sets to lists and sort by count
    result = []
    for key, p in sorted(patterns.items(), key=lambda x: x[1]["count"], reverse=True):
        p["services"] = list(p["services"])
        p["endpoints"] = list(p["endpoints"])
        p["upstream_systems"] = list(p["upstream_systems"])
        p["incident_types"] = list(p["incident_types"])
        # Compute trust score for log-derived patterns
        count = p["count"]
        if count >= 20:
            p["trust_score"] = 0.60
            p["recommended_action"] = "Créer une procédure canonique (fréquence élevée)"
        elif count >= 5:
            p["trust_score"] = 0.50
            p["recommended_action"] = "Ajouter au cluster existant ou créer un cluster"
        else:
            p["trust_score"] = 0.35
            p["recommended_action"] = "Surveiller — fréquence trop faible pour clustering"
        result.append(p)

    return result


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def run(
    log_files: List[Path] = None,
    log_dir: Optional[Path] = None,
    strategy: str = "generic",
    application: str = "BRASIL",
    show_guide: bool = False,
    dry_run: bool = False,
) -> bool:
    if show_guide:
        print(PRIORITY_LOG_GUIDE)
        return True

    # Collect log files
    files_to_parse = []
    if log_files:
        files_to_parse = [f for f in log_files if f.exists()]
    elif log_dir and log_dir.exists():
        for pattern in ["*.log", "*.txt"]:
            files_to_parse.extend(log_dir.glob(pattern))

    if not files_to_parse:
        print("  ⚠️  Aucun fichier de log fourni")
        print("  💡 Utilisez --guide pour voir les chemins de logs prioritaires")
        print("  💡 Exemple: python data_pipeline/log_ingester.py --log-file /var/log/brasil/api/error.log")
        return False

    all_events = []
    for lf in sorted(files_to_parse):
        # Skip non-log helper files
        if _SKIP_FILENAMES.search(lf.name):
            print(f"  ⏭️  Ignoré:  {lf.name}")
            continue
        effective_strategy = _auto_detect_strategy(lf.name, strategy)
        print(f"  📄 Parsing: {lf.name} (stratégie: {effective_strategy})")
        events = parse_log_file(lf, strategy=effective_strategy, application=application)
        print(f"     {len(events)} événements extraits")
        all_events.extend(events)

    if not all_events:
        print("  ✅ Aucun événement d'erreur détecté dans les logs fournis")
        return True

    patterns = aggregate_patterns(all_events)

    print(f"\n  📊 Résumé:")
    print(f"     Événements total : {len(all_events)}")
    print(f"     Patterns uniques : {len(patterns)}")
    print(f"     Top 5 patterns:")
    for p in patterns[:5]:
        print(f"       [{p.get('error_code','?')}] x{p['count']} — {p.get('messages_sample', [''])[0][:60]}")

    if dry_run:
        print("  🔍 Mode DRY-RUN — pas d'écriture")
        return True

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "generated_at": datetime.utcnow().isoformat(),
        "source_files": [str(f) for f in files_to_parse],
        "strategy": strategy,
        "application": application,
        "total_events": len(all_events),
        "total_patterns": len(patterns),
        "patterns": patterns,
        "events": [e.to_dict() for e in all_events[:500]],  # Cap at 500 for output
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n  💾 Sauvegardé: {OUTPUT_FILE}")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Log Ingestion Adapter — Extract structured error events from server logs"
    )
    parser.add_argument("--log-file", type=Path, action="append", dest="log_files",
                        help="Path to a log file (repeatable)")
    parser.add_argument("--log-dir", type=Path, help="Directory to scan for .log files")
    parser.add_argument("--strategy", default="auto",
                        choices=list(STRATEGY_PARSERS.keys()) + ["auto"],
                        help="Parsing strategy (default: auto-detect from filename)")
    parser.add_argument("--application", default="BRASIL", help="Application name")
    parser.add_argument("--guide", action="store_true", dest="show_guide",
                        help="Show the priority log extraction guide")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    success = run(
        log_files=args.log_files or [],
        log_dir=args.log_dir,
        strategy=args.strategy if args.strategy != "auto" else "generic",
        application=args.application,
        show_guide=args.show_guide,
        dry_run=args.dry_run,
    )
    sys.exit(0 if success else 1)
