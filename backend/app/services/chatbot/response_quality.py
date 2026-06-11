"""
response_quality.py
━━━━━━━━━━━━━━━━━━━
Cleans LLM output by removing generic AI filler phrases.

Strips:
  - "N'hésitez pas à..."
  - "Je suis là pour vous aider"
  - "Merci pour votre confiance"
  - "Avez-vous d'autres questions"
  - Generic troubleshooting templates
  - Uncertain hedging language

Preserves:
  - Technical values (eqpt_id, table names, SQL)
  - Deterministic evidence
  - Exact entity names
  - Error codes and timestamps
"""

from __future__ import annotations

import re
from typing import List

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Patterns to REMOVE from LLM output (full line removal)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_REMOVE_LINE_PATTERNS: List[re.Pattern] = [
    # ── French AI filler ────────────────────────────────────────────────────
    re.compile(r"^\s*[-•]?\s*[Nn]['']h[eé]sitez\s+pas\s+[àa]", re.IGNORECASE),
    re.compile(r"^\s*[-•]?\s*[Jj]e\s+suis\s+l[àa]\s+pour\s+vous", re.IGNORECASE),
    re.compile(r"^\s*[-•]?\s*[Mm]erci\s+pour\s+votre\s+(?:confiance|patience|question|message)", re.IGNORECASE),
    re.compile(r"^\s*[-•]?\s*[Aa]vez[\s-]+vous\s+d['']autres?\s+questions?", re.IGNORECASE),
    re.compile(r"^\s*[-•]?\s*[Ss]i\s+vous\s+avez\s+(?:d['']autres?\s+questions?|besoin)", re.IGNORECASE),
    re.compile(r"^\s*[-•]?\s*[Jj]e\s+reste\s+[àa]\s+votre\s+disposition", re.IGNORECASE),
    re.compile(r"^\s*[-•]?\s*[Nn]ous\s+restons\s+[àa]\s+votre", re.IGNORECASE),
    re.compile(r"^\s*[-•]?\s*[Bb]onne\s+(?:chance|continuation|journ[eé]e)", re.IGNORECASE),
    re.compile(r"^\s*[-•]?\s*[Ee]n\s+cas\s+de\s+(?:probl[eè]me|difficult[eé])\s+suppl[eé]mentaire", re.IGNORECASE),
    re.compile(r"^\s*[-•]?\s*[Cc]ontactez?\s+(?:le\s+support|l[''`]?[eé]quipe|votre\s+(?:sup[eé]rieur|manager))", re.IGNORECASE),
    re.compile(r"^\s*[-•]?\s*[Ff]aites[\s-]+moi\s+savoir", re.IGNORECASE),
    re.compile(r"^\s*[-•]?\s*[Jj]e\s+peux\s+vous\s+(?:aider|guider|accompagner)", re.IGNORECASE),
    re.compile(r"^\s*[-•]?\s*[Ss]ouhaitez[\s-]+vous\b", re.IGNORECASE),
    re.compile(r"^\s*[-•]?\s*[Pp]uis[\s-]+je\s+vous\s+aider\b", re.IGNORECASE),
    re.compile(r"^\s*[-•]?\s*[Cc]ordialement[,\s]", re.IGNORECASE),
    re.compile(r"^\s*[-•]?\s*[Ee]n\s+tant\s+qu['']assistant", re.IGNORECASE),
    re.compile(r"^\s*[-•]?\s*[Jj]['']esp[eè]re\s+(?:que\s+)?(?:cela|ça)\s+(?:vous\s+)?(?:aide|r[eé]pond)", re.IGNORECASE),
    re.compile(r"^\s*[-•]?\s*[Dd]ites[\s-]+moi\s+si\s+(?:la|le|l[''])\w+", re.IGNORECASE),
    re.compile(r"^\s*[-•]?\s*[Nn]ous\s+pourrons?\s+passer\s+[àa]\s+la\s+cl[ôo]ture", re.IGNORECASE),
    re.compile(r"^\s*[-•]?\s*[Aa]verti(?:ssez)?[\s-]+moi\s+si\b", re.IGNORECASE),
    # ── English AI filler ───────────────────────────────────────────────────
    re.compile(r"^\s*[-•]?\s*[Ff]eel\s+free\s+to", re.IGNORECASE),
    re.compile(r"^\s*[-•]?\s*[Ii]['']m\s+here\s+to\s+help", re.IGNORECASE),
    re.compile(r"^\s*[-•]?\s*[Ll]et\s+me\s+know\s+if", re.IGNORECASE),
    re.compile(r"^\s*[-•]?\s*[Dd]on['']t\s+hesitate\s+to", re.IGNORECASE),
    re.compile(r"^\s*[-•]?\s*[Hh]ope\s+this\s+helps", re.IGNORECASE),
    re.compile(r"^\s*[-•]?\s*[Pp]lease\s+(?:let\s+me\s+know|feel\s+free)", re.IGNORECASE),
    # ── Generic troubleshooting filler ──────────────────────────────────────
    re.compile(r"^\s*[-•]?\s*[Vv][eé]rifiez?\s+(?:que\s+)?(?:le\s+)?r[eé]seau", re.IGNORECASE),
    re.compile(r"^\s*[-•]?\s*[Rr]ed[eé]marrez?\s+(?:le\s+)?(?:serveur|service|application)(?:\s+si\s+n[eé]cessaire)?\.?\s*$", re.IGNORECASE),
    re.compile(r"^\s*[-•]?\s*[Ee]ssayez?\s+[àa]\s+nouveau\s+(?:plus\s+tard|ult[eé]rieurement)", re.IGNORECASE),
    re.compile(r"^\s*[-•]?\s*[Vv]euillez\s+(?:v[eé]rifier|confirmer|fournir|contacter|noter)", re.IGNORECASE),
    re.compile(r"^\s*[-•]?\s*[Mm]erci\s+de\s+(?:confirmer|v[eé]rifier|fournir|nous\s+contacter)", re.IGNORECASE),
    re.compile(r"^\s*[-•]?\s*[Aa]vez[\s-]+vous\s+v[eé]rifi[eé]\b", re.IGNORECASE),
    # ── Hallucinations: invented CLI commands ───────────────────────────────
    re.compile(r"brasil[-_]cli\s+--", re.IGNORECASE),
    re.compile(r"brasil[-_]cli\s+[a-z]", re.IGNORECASE),
    re.compile(r"sync[-_]brasil[-_]resources\.sh", re.IGNORECASE),
    re.compile(r"\bbrasil[-_]admin\s+--", re.IGNORECASE),
    re.compile(r"\b(?:orchestra|artemis|seba)[-_]cli\s+--", re.IGNORECASE),
    # ── Hallucinations: invented script files ──────────────────────────────
    re.compile(r"\w+\.sh\s+--", re.IGNORECASE),
    re.compile(r"restart[-_]brasil\.(sh|py|bat)", re.IGNORECASE),
    # ── Invented final status closures ─────────────────────────────────────
    re.compile(r"^\s*[Ss]tatut\s+final\s*:\s*[Rr][eé]solu", re.IGNORECASE),
    re.compile(r"^\s*[Ss]i\s+la\s+correction\s+est\s+appliqu[eé]e\s+et\s+que\s+le\s+ND", re.IGNORECASE),
    # ── Weak deterministic language (hedging) ──────────────────────────────
    re.compile(r"^\s*[-•]?\s*[Ii]l\s+(?:semble|semblerait|para[iî]t)\s+que", re.IGNORECASE),
    re.compile(r"^\s*[-•]?\s*[Pp]ossiblement\b", re.IGNORECASE),
    re.compile(r"^\s*[-•]?\s*[Cc]ela\s+pourrait\s+[eê]tre\b", re.IGNORECASE),
    re.compile(r"^\s*[-•]?\s*[Ss]elon\s+le\s+contexte\b", re.IGNORECASE),
    re.compile(r"^\s*[-•]?\s*[Ii]l\s+est\s+possible\s+que\b", re.IGNORECASE),
    re.compile(r"^\s*[-•]?\s*[Pp]robablement\b", re.IGNORECASE),
    re.compile(r"^\s*[-•]?\s*[Ii]l\s+se\s+peut\s+que\b", re.IGNORECASE),
    re.compile(r"^\s*[-•]?\s*[Ee]n\s+g[eé]n[eé]ral\b", re.IGNORECASE),
    re.compile(r"^\s*[-•]?\s*[Gg][eé]n[eé]ralement\b", re.IGNORECASE),
]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SQL READONLY ENFORCEMENT — Phase 6
# Block mutation queries from appearing in any response
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_SQL_MUTATION_KEYWORDS = re.compile(
    r"(?:^|\s)(UPDATE|DELETE\s+FROM|INSERT\s+INTO|ALTER\s+TABLE|DROP\s+TABLE|"
    r"TRUNCATE\s+TABLE|GRANT\s+|REVOKE\s+|CREATE\s+TABLE|DROP\s+INDEX)\b",
    re.IGNORECASE | re.MULTILINE,
)

_MSG_READONLY_BLOCK = (
    "🚫 **Commande SQL de mutation bloquée** — "
    "le système est en mode forensique lecture seule.\n"
    "Seules les requêtes SELECT sont autorisées pour l'analyse."
)


def enforce_readonly_sql(text: str) -> str:
    """
    Block any SQL mutation commands from appearing in responses.
    Replaces the entire SQL code block containing mutations.
    Applied to ALL responses (LLM and deterministic).
    """
    if not text:
        return text

    def _replace_sql_block(m: re.Match) -> str:
        content = m.group(0)
        if _SQL_MUTATION_KEYWORDS.search(content):
            return f"```sql\n{_MSG_READONLY_BLOCK}\n```"
        return content

    # Replace fenced SQL blocks containing mutations
    text = re.sub(r"```sql[\s\S]*?```", _replace_sql_block, text, flags=re.IGNORECASE)

    # Replace inline mutation keywords outside code blocks (last resort)
    text = _SQL_MUTATION_KEYWORDS.sub(
        lambda m: f" {_MSG_READONLY_BLOCK} ",
        text,
    )
    return text

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SQL placeholder hallucination detector + replacer
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Matches [PLACEHOLDER], [NOM_EQPT], [VALEUR_CORRECTE], etc.
_SQL_PLACEHOLDER_RX = re.compile(r"\[[A-Z][A-Z0-9_]{2,}\]", re.IGNORECASE)

# SQL UPDATE/DELETE blocks that contain placeholders → entire block suspicious
_SQL_HALLUCINATED_UPDATE_RX = re.compile(
    r"```sql[^`]*(?:UPDATE|DELETE|INSERT)[^`]*\[[A-Z_]+\][^`]*```",
    re.DOTALL | re.IGNORECASE,
)

# Invented shell commands
_INVENTED_CMD_RX = re.compile(
    r"`[^`]*(?:brasil-cli|sync_brasil|restart_brasil|orchestra-cli|seba-cli)[^`]*`",
    re.IGNORECASE,
)


# Patterns to STRIP (inline removal, preserving rest of line)
_STRIP_INLINE_PATTERNS: List[re.Pattern] = [
    re.compile(r"\s*,?\s*n'h[eé]sitez\s+pas\s+[àa][^.]*\.", re.IGNORECASE),
    re.compile(r"\s*\.\s*[Jj]e\s+reste\s+[àa]\s+votre\s+disposition[^.]*\.?", re.IGNORECASE),
    re.compile(r"\s*\.\s*[Ss]i\s+le\s+probl[eè]me\s+persiste[^.]*\.?", re.IGNORECASE),
]


def clean_llm_response(text: str) -> str:
    """
    Remove generic AI filler phrases from LLM output.
    Preserves all technical content.

    Safe to call on any text — never modifies technical values.
    """
    if not text:
        return text

    lines = text.split("\n")
    cleaned_lines = []

    for line in lines:
        # Check if entire line should be removed
        should_remove = False
        for pattern in _REMOVE_LINE_PATTERNS:
            if pattern.search(line):
                should_remove = True
                break

        if should_remove:
            continue

        # Strip inline filler from the line
        cleaned = line
        for pattern in _STRIP_INLINE_PATTERNS:
            cleaned = pattern.sub("", cleaned)

        cleaned_lines.append(cleaned)

    # Remove trailing empty lines that result from removals
    result = "\n".join(cleaned_lines)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def strip_sql_hallucinations(text: str) -> str:
    """
    Remove SQL/command blocks that contain placeholder patterns like [NOM_EQPT],
    [VALEUR_CORRECTE], invented CLI commands, etc.
    Returns cleaned text with a warning comment where blocks were removed.
    """
    if not text:
        return text

    # Remove full SQL blocks with placeholders
    text = _SQL_HALLUCINATED_UPDATE_RX.sub(
        "```sql\n-- ⚠️ Requête retirée : contient des placeholders non résolus\n```",
        text
    )

    # Remove inline invented commands
    text = _INVENTED_CMD_RX.sub("[commande non validée]", text)

    # Flag remaining placeholder tokens inline
    def _flag_placeholder(m: re.Match) -> str:
        return f"⚠️`{m.group(0)}`"
    text = _SQL_PLACEHOLDER_RX.sub(_flag_placeholder, text)

    return text


def validate_no_hallucination_phrases(text: str) -> List[str]:
    """
    Check for suspicious AI-generated phrases.
    Returns list of warnings (empty = clean).
    """
    warnings = []

    # Check for invented timestamps
    invented_ts = re.findall(
        r"à\s+(\d{2}:\d{2}:\d{2})\s+(?:le|du)\s+\d{2}/\d{2}/\d{4}",
        text
    )
    if invented_ts:
        warnings.append(f"Suspicious timestamp: {invented_ts[0]}")

    # Check for claiming to run commands
    if re.search(r"j'ai\s+(?:exécuté|lancé|vérifié)", text, re.IGNORECASE):
        warnings.append("LLM claims to have executed commands")

    # Check for invented row counts
    if re.search(r"j'ai\s+trouvé\s+\d+\s+(?:lignes?|enregistrements?)", text, re.IGNORECASE):
        warnings.append("LLM claims to have found specific row counts")

    return warnings


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Hallucinated table / FR validation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Known BRASIL schema tables (synced from diagnostic_behavior.BRASIL_SCHEMA_TABLES)
_KNOWN_TABLES: set = set()

def _load_known_tables() -> set:
    """Load known table names from the authoritative schema list (priority: generated pack → ontology → static)."""
    # Priority 1: generated pack from live brasil_prod extraction
    try:
        from app.services.chatbot.brasil_schema_knowledge import REAL_SQL_TABLES
        if REAL_SQL_TABLES:
            return set(REAL_SQL_TABLES)
    except Exception:
        pass
    # Priority 2: diagnostic_behavior static list
    try:
        from app.services.nlp.diagnostic_behavior import BRASIL_SCHEMA_TABLES
        return set(BRASIL_SCHEMA_TABLES)
    except ImportError:
        return {
            "t_equipments", "t_cards", "t_ports", "t_shelfs", "t_nodes",
            "t_logical_eqpt_models", "t_vlan", "t_interfaces",
            "t_res_prod_controlables", "t_media_links", "t_mrt_access_dslams",
            "t_epcs", "t_making_files", "t_mutations_requests", "t_tech_services",
            "t_tps", "t_trs", "t_prestations", "t_operators", "t_servers",
        }

_TABLE_NAME_RX = re.compile(r"(?<!⚠️`)(?<!`)\bt_([a-z][a-z0-9_]{2,30})\b")


def validate_table_references(text: str) -> str:
    """
    Check for hallucinated table names in response text.
    Replaces unknown t_xxx references with a warning.
    """
    global _KNOWN_TABLES
    if not _KNOWN_TABLES:
        _KNOWN_TABLES = _load_known_tables()

    def _check_table(m: re.Match) -> str:
        full = m.group(0)
        if full in _KNOWN_TABLES:
            return full
        return f"⚠️`{full}`"
    return _TABLE_NAME_RX.sub(_check_table, text)


def full_quality_check(text: str) -> str:
    """
    Run ALL quality checks in sequence:
    1. enforce_readonly_sql (block mutations — Phase 6, always first)
    2. clean_llm_response (filler + hedging removal — Phase 7)
    3. strip_sql_hallucinations (placeholder removal)
    4. validate_table_references (flag unknown tables)
    5. validate_no_hallucination_phrases (warnings logged)
    """
    text = enforce_readonly_sql(text)
    text = clean_llm_response(text)
    text = strip_sql_hallucinations(text)
    text = validate_table_references(text)
    warnings = validate_no_hallucination_phrases(text)
    if warnings:
        import logging
        logging.getLogger(__name__).warning(f"[QualityCheck] {warnings}")
    return text
