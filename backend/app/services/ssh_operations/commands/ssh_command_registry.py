"""
ssh_command_registry.py
━━━━━━━━━━━━━━━━━━━━━━━
Whitelist of ALL allowed remote SSH commands.

SECURITY RULES:
  - ONLY commands defined here can be executed
  - No raw command from user input
  - No shell injection possible (params are positional and sanitized)
  - Command strings are static — params are passed as template substitutions
    with strict validation
"""

from typing import Any, Dict

ALLOWED_COMMANDS: Dict[str, Dict[str, Any]] = {

    # ── Log inspection ────────────────────────────────────────────────────────

    "tail_brasil_logs": {
        "cmd":         "tail -n 200 /logs/brasil/app.log",
        "params":      [],
        "description": "Dernières 200 lignes du log BRASIL",
        "timeout_s":   10,
        "tags":        ["logs", "brasil"],
    },

    "tail_brasil_error": {
        "cmd":         "tail -n 100 /logs/brasil/error.log",
        "params":      [],
        "description": "Dernières 100 lignes du log erreurs BRASIL",
        "timeout_s":   10,
        "tags":        ["logs", "brasil", "error"],
    },

    "tail_wa_logs": {
        "cmd":         "tail -n 200 /logs/brasil/ihm.log",
        "params":      [],
        "description": "Dernières 200 lignes du log IHM BRASIL (serveur WA)",
        "timeout_s":   10,
        "tags":        ["logs", "wa", "ihm"],
    },

    "tail_wa_catalina": {
        "cmd":         "tail -n 200 /opt/tomcat/logs/catalina.out",
        "params":      [],
        "description": "Dernières 200 lignes Tomcat catalina.out (serveur WA)",
        "timeout_s":   10,
        "tags":        ["logs", "wa", "tomcat"],
    },

    "check_active_sessions_db": {
        "cmd":         "who -T",
        "params":      [],
        "description": "Lister les sessions actives sur le serveur DB (diagnostic IHM bloquée)",
        "timeout_s":   5,
        "tags":        ["system", "sessions", "db", "ihm_blocked"],
    },

    "grep_equipment_in_logs": {
        "cmd":         "grep -i '{equipment}' /logs/brasil/app.log | tail -n 100",
        "params":      ["equipment"],
        "description": "Rechercher un équipement dans les logs BRASIL",
        "timeout_s":   15,
        "tags":        ["logs", "equipment", "search"],
    },

    "search_error_1300": {
        "cmd":         "grep '1300' /logs/brasil/app.log | tail -50",
        "params":      [],
        "description": "Rechercher les erreurs 1300 dans les logs BRASIL",
        "timeout_s":   15,
        "tags":        ["logs", "error_1300"],
    },

    "search_error_1002": {
        "cmd":         "grep '1002' /logs/brasil/app.log | tail -50",
        "params":      [],
        "description": "Rechercher les erreurs 1002 dans les logs BRASIL",
        "timeout_s":   15,
        "tags":        ["logs", "error_1002"],
    },

    "search_exception_in_logs": {
        "cmd":         "grep -i 'Exception' /logs/brasil/error.log | tail -50",
        "params":      [],
        "description": "Rechercher les exceptions dans les logs erreurs",
        "timeout_s":   15,
        "tags":        ["logs", "exception"],
    },

    # ── System health ─────────────────────────────────────────────────────────

    "check_java_process": {
        "cmd":         "ps -ef | grep java | grep -v grep",
        "params":      [],
        "description": "Lister les processus Java en cours",
        "timeout_s":   10,
        "tags":        ["system", "java", "process"],
    },

    "check_disk_space": {
        "cmd":         "df -h",
        "params":      [],
        "description": "Vérifier l'espace disque",
        "timeout_s":   10,
        "tags":        ["system", "disk"],
    },

    "check_memory": {
        "cmd":         "free -h",
        "params":      [],
        "description": "Vérifier la mémoire disponible",
        "timeout_s":   10,
        "tags":        ["system", "memory"],
    },

    "check_active_sessions": {
        "cmd":         "who -T",
        "params":      [],
        "description": "Lister les sessions actives sur le serveur",
        "timeout_s":   5,
        "tags":        ["system", "sessions"],
    },

    "check_process_on_session": {
        "cmd":         "ps -ft pts/{session}",
        "params":      ["session"],
        "description": "Lister les processus sur une session pts",
        "timeout_s":   5,
        "tags":        ["system", "process", "session"],
    },

    # ── Database connectivity ─────────────────────────────────────────────────

    "check_db_connectivity": {
        "cmd":         "echo 'SELECT 1;' | psql -d brasil -U brasilowner -h localhost -t",
        "params":      [],
        "description": "Vérifier la connectivité à la base BRASIL",
        "timeout_s":   10,
        "tags":        ["db", "health"],
    },

    "check_db_locks": {
        "cmd": (
            "echo \"SELECT pid, query, state, wait_event_type, wait_event "
            "FROM pg_stat_activity WHERE state='active' LIMIT 20;\" "
            "| psql -d brasil -U brasilowner -h localhost"
        ),
        "params":      [],
        "description": "Vérifier les locks actifs en base BRASIL",
        "timeout_s":   15,
        "tags":        ["db", "locks"],
    },

    # ── psql diagnostic queries (SSH -> psql, parameterized) ──────────────────
    # Ces commandes sont construites par SshPsqlDbService — NE PAS appeler
    # directement via build_command_string (le SQL est injecté dynamiquement
    # depuis le whitelist db_query_registry).

    "psql_query": {
        "cmd":         "psql -U {db_user} -d {db_name} -h localhost -A -F'|' -c {sql_b64}",
        "params":      ["db_user", "db_name", "sql_b64"],
        "description": "Exécuter une requête SQL via psql (usage interne SshPsqlDbService)",
        "timeout_s":   30,
        "tags":        ["db", "psql", "internal"],
    },

    # ── Log rotation / file listing ───────────────────────────────────────────

    "list_log_files": {
        "cmd":         "ls -lh /logs/brasil/",
        "params":      [],
        "description": "Lister les fichiers de log BRASIL",
        "timeout_s":   5,
        "tags":        ["logs", "files"],
    },

    # ── Remote grep (parametrized) ────────────────────────────────────────────

    "grep_log": {
        "cmd":         "grep -i '{pattern}' {log_path} | tail -n {max_lines}",
        "params":      ["pattern", "log_path", "max_lines"],
        "description": "Grep paramétré dans un fichier de log",
        "timeout_s":   20,
        "tags":        ["logs", "search"],
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Intent -> SSH commands routing (used by DiagnosticPlanner)
# ─────────────────────────────────────────────────────────────────────────────

INTENT_SSH_PLAN: Dict[str, list] = {
    "delete_equipment":  ["check_java_process", "grep_equipment_in_logs"],
    "fix_ihm_blocked":   ["check_active_sessions_db", "check_java_process", "tail_wa_logs"],
    "fix_blocked_tp":    ["tail_brasil_logs", "check_java_process"],
    "error_1300":        ["search_error_1300"],
    "error_1002":        ["search_error_1002"],
    "check_system":      ["check_disk_space", "check_memory", "check_java_process"],
    "check_db":          ["check_db_connectivity", "check_db_locks"],
}


def get_command(name: str) -> Dict[str, Any] | None:
    return ALLOWED_COMMANDS.get(name)


def build_command_string(name: str, params: Dict[str, str]) -> str | None:
    """
    Build the final command string with safe parameter substitution.
    Only alphanumeric + limited punctuation allowed in params.
    """
    cmd_def = get_command(name)
    if not cmd_def:
        raise ValueError(f"[SshRegistry] Command '{name}' not in whitelist.")

    cmd = cmd_def["cmd"]
    for key, val in params.items():
        # Strict sanitization: only allow safe chars
        safe_val = _sanitize_param(val)
        cmd = cmd.replace("{" + key + "}", safe_val)

    # Verify no placeholders remain
    if "{" in cmd:
        raise ValueError(f"[SshRegistry] Unresolved placeholder in command: {cmd}")

    return cmd


def _sanitize_param(val: str) -> str:
    """Allow only alphanumeric, dash, underscore, dot, slash for log paths."""
    import re
    if not isinstance(val, str):
        val = str(val)
    if len(val) > 256:
        raise ValueError("SSH command parameter too long.")
    # Allow only safe characters
    if not re.match(r'^[\w\-\./]+$', val):
        raise ValueError(f"Forbidden characters in SSH parameter: '{val}'")
    # Reject shell metacharacters
    FORBIDDEN = [";", "&", "|", ">", "<", "`", "$", "!", "\n", "\r"]
    for c in FORBIDDEN:
        if c in val:
            raise ValueError(f"Forbidden shell metacharacter in SSH parameter: '{c}'")
    return val
