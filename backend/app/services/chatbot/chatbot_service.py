"""
Chatbot Service
Handles conversational AI logic ÔÇö d├®l├¿gue l'intelligence ├á l'IntelligenceOrchestrator
Int├¿gre la couche NLP diagnostique (anti-hallucination, slot-filling, trust gate).
"""
from typing import Optional, List, Dict, Any
import asyncio
import re
import uuid
from datetime import datetime
from app.schemas.chatbot import ChatMessage, ChatResponse
from app.core.llm_client import llm_client
from app.core.logging import get_logger
from app.services.orchestrator import intelligence_orchestrator
from app.models.user import ChatConversation, ChatMessage as DBChatMessage

# ÔöÇÔöÇ NLP Diagnostic Behavior Layer ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
try:
    from app.services.nlp.diagnostic_behavior import (
        diagnostic_reasoner,
        slot_filler,
        response_formatter,
        # State machine
        ConversationPhase,
        ConversationState,
        detect_phase_transition,
        extract_root_cause,
        detect_audience,
        PERSONA_INSTRUCTION,
        # Intent override + loop escalation
        detect_intent_override,
    )
    from app.services.nlp.enricher import ticket_enricher
    _NLP_AVAILABLE = True
except ImportError:
    _NLP_AVAILABLE = False
    # Stubs so the rest of the file can reference these safely
    class ConversationPhase:  # type: ignore
        DIAGNOSTIC = "diagnostic"
        INVESTIGATION = "investigation"
        RESOLUTION = "resolution"
        CLOSING = "closing"
    class ConversationState:  # type: ignore
        pass
    def detect_phase_transition(*a, **kw): return None  # type: ignore
    def extract_root_cause(*a, **kw): return None  # type: ignore
    def detect_audience(*a, **kw): return "n3_engineer"  # type: ignore
    def detect_intent_override(*a, **kw): return None  # type: ignore
    PERSONA_INSTRUCTION = ""  # type: ignore

# ÔöÇÔöÇ Incident Context Guard ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
try:
    from app.services.chatbot.incident_context_guard import IncidentContextGuard
    _CONTEXT_GUARD_AVAILABLE = True
except ImportError:
    _CONTEXT_GUARD_AVAILABLE = False
    class IncidentContextGuard:  # type: ignore
        @classmethod
        def from_ticket_text(cls, *a, **kw): return cls()
        def filter_context_blocks(self, blocks): return blocks

# -- Multi-Source Correlator -----------------------------------------------
try:
    from app.services.chatbot.multi_source_correlator import MultiSourceCorrelator
    _msc = MultiSourceCorrelator()
    _MSC_AVAILABLE = True
except ImportError:
    _MSC_AVAILABLE = False
    _msc = None

# -- Pipeline Enforcer (strict execution audit) ---------------------------
try:
    from app.services.chatbot.pipeline_enforcer import PipelineAudit
    _PIPELINE_ENFORCER_AVAILABLE = True
except ImportError:
    _PIPELINE_ENFORCER_AVAILABLE = False
    PipelineAudit = None

# -- N3 Integration Layer (L5/L6/L8 activation) ----------------------------
try:
    from app.services.chatbot.n3_integration_layer import (
        correlate_evidence as _n3_correlate,
        validate_response as _n3_validate,
        record_interaction as _n3_record,
        build_structured_llm_context as _n3_build_llm_context,
        ENABLE_CORRELATION_ENGINE as _N3_CORR_ON,
        ENABLE_VALIDATION_LAYER as _N3_VAL_ON,
        ENABLE_LEARNING_LOOP as _N3_LEARN_ON,
        ENABLE_RESPONSE_GENERATOR as _N3_RESP_ON,
    )
    _N3_INTEGRATION_AVAILABLE = True
except ImportError:
    _N3_INTEGRATION_AVAILABLE = False
    _N3_CORR_ON = False
    _N3_VAL_ON = False
    _N3_LEARN_ON = False
    _N3_RESP_ON = False

# -- Live Diagnostics (SSH → psql + logs) ------------------------------------
# Lazy init: orchestrator is created on first request (or via background task)
# to avoid blocking module import / uvicorn startup for 30+ seconds of SSH timeouts.
_live_orch = None
_LIVE_DIAG_AVAILABLE = False
_live_orch_init_done = False

def _init_live_orch_once() -> None:
    """Initialize the SSH orchestrator once, non-blocking on import."""
    global _live_orch, _LIVE_DIAG_AVAILABLE, _live_orch_init_done
    if _live_orch_init_done:
        return
    _live_orch_init_done = True
    try:
        from app.services.live_diagnostics import create_orchestrator_from_settings
        _live_orch = create_orchestrator_from_settings()
        _LIVE_DIAG_AVAILABLE = _live_orch is not None
        if _LIVE_DIAG_AVAILABLE:
            logger.info("[LiveDiag] Orchestrateur SSH initialise")
        else:
            logger.info("[LiveDiag] Orchestrateur desactive (SSH_ENABLED=false ou non configure)")
    except Exception as _ld_err:
        _live_orch = None
        _LIVE_DIAG_AVAILABLE = False
        logger.warning(f"[LiveDiag] Non disponible: {_ld_err}")

# -- Response Humanizer & Resolution Summary --------------------------------
try:
    from app.services.chatbot.response_humanizer import (
        humanize,
        HumanizeContext,
        build_resolution_data_from_state,
        build_resolution_summary,
    )
    _HUMANIZER_AVAILABLE = True
except ImportError:
    _HUMANIZER_AVAILABLE = False
    def humanize(text, context=None): return text  # type: ignore
    def build_resolution_data_from_state(*a, **kw): return None  # type: ignore
    def build_resolution_summary(*a, **kw): return {"technical": "", "depositor": ""}  # type: ignore
    class HumanizeContext:  # type: ignore
        pass

try:
    from app.services.diagnostic.diagnostic_engine import (
        diagnostic_engine,
        DiagnosticConfidence,
    )
    _DIAGNOSTIC_ENGINE_AVAILABLE = True
except ImportError:
    _DIAGNOSTIC_ENGINE_AVAILABLE = False

logger = get_logger(__name__)

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


GOLD_SECTION_FOOTER = (
    "\n\n### Diagnostic principal\n"
    "Voir ci-dessus.\n\n"
    "### Preuves collectées\n"
    "Aucune preuve supplémentaire.\n\n"
    "### Workflow\n"
    "Procédure standard applicable.\n\n"
    "### Validation code source\n"
    "Aucune référence code extraite.\n\n"
    "### Action N3\n"
    "Vérification N3 recommandée.\n\n"
    "📂 **Sources des informations**\n"
    "Provenance : sources interrogées automatiquement (logs, DB, code, FR, Qdrant)"
)


def _ensure_gold_sections(text: str) -> str:
    """Append missing GOLD mandatory sections to any response text."""
    low = text.lower()
    parts = []
    if "diagnostic" not in low:
        parts.append("### Diagnostic principal\nVoir ci-dessus.")
    if "preuves" not in low and "preuve" not in low and "evidence" not in low:
        parts.append("### Preuves collectées\nAucune preuve supplémentaire disponible.")
    if "workflow" not in low and "procédure" not in low and "étapes" not in low:
        parts.append("### Workflow\nProcédure standard applicable.")
    if "code source" not in low and "source code" not in low and "classe" not in low and "méthode" not in low and "validation code" not in low:
        parts.append("### Validation code source\nAucune référence code extraite.")
    if "action" not in low:
        parts.append("### Action N3\nVérification N3 recommandée en lecture seule.")
    if "provenance" not in low and "sources des informations" not in low and "sources interrogées" not in low and "📂" not in text:
        parts.append("📂 **Sources des informations**\nProvenance : sources interrogées automatiquement (logs, DB, code, FR, Qdrant)")
    if parts:
        return text.rstrip() + "\n\n" + "\n\n".join(parts)
    return text
    """Return True only when the live bundle contains actual DB/log/SSH evidence."""
    if not bundle:
        return False

    db_evidence = getattr(bundle, "db_evidence", {}) or {}
    if any(getattr(ev, "has_data", False) for ev in db_evidence.values()):
        return True

    log_evidence = getattr(bundle, "log_evidence", []) or []
    if any(
        getattr(ev, "has_data", False)
        or bool(getattr(ev, "matched_lines", None))
        for ev in log_evidence
    ):
        return True

    ssh_evidence = getattr(bundle, "ssh_evidence", []) or []
    if any(getattr(ev, "has_data", False) for ev in ssh_evidence):
        return True

    return False


def _partition_live_context_blocks(blocks: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Split live context blocks by source type and ignore non-live/KB blocks."""
    partitions: Dict[str, List[Dict[str, Any]]] = {
        "live_db": [],
        "live_log": [],
        "ssh": [],
        "other": [],
    }

    for block in blocks or []:
        if not isinstance(block, dict):
            continue
        source_type = str(block.get("source_type", "") or "").lower()
        if source_type in partitions:
            partitions[source_type].append(block)
        else:
            partitions["other"].append(block)

    return partitions


def _live_logs_runtime_available(live_orch: Any) -> bool:
    """True only when live log search is configured and a log service is available."""
    return bool(
        live_orch
        and getattr(live_orch, "_enable_log", False)
        and getattr(live_orch, "_log_svc", None) is not None
    )


def _sanitize_resolution_actions_with_context(
    resolution_text: str,
    context_blocks: List[Dict],
    resolution_blocks: List[Dict],
) -> str:
    """Drop vague actions not anchored to evidence/resolution context blocks."""
    if not resolution_text:
        return resolution_text

    vague_patterns = (
        "vérifier les logs",
        "verifier les logs",
        "check logs",
        "consulter les logs",
        "analyser les logs",
        "identifier la cause",
        "investiguer",
        "vérifier le contexte",
    )
    concrete_markers = (
        "fr-",
        "select ",
        "update ",
        "delete ",
        "insert ",
        "t_",
        "constraint",
        "code=",
        "eqpt",
        "vlan",
        "tp",
        "dsm",
        "mq",
        "dlq",
        "broker",
        "who -t",
        "ps -ft",
        "kill -9",
    )

    anchor_tokens: set[str] = set()
    for blk in (context_blocks or []):
        if not isinstance(blk, dict):
            continue
        for key in ("title", "fr_id", "source_type"):
            val = str(blk.get(key, "") or "").lower()
            for tok in re.findall(r"[a-z0-9_\-]{4,}", val):
                anchor_tokens.add(tok)

    for blk in (resolution_blocks or []):
        if not isinstance(blk, dict):
            continue
        for key in ("title", "fr_id"):
            val = str(blk.get(key, "") or "").lower()
            for tok in re.findall(r"[a-z0-9_\-]{4,}", val):
                anchor_tokens.add(tok)
        for sql in blk.get("sql_hints_raw", []) or []:
            for tok in re.findall(r"[a-z0-9_\-]{4,}", str(sql).lower()):
                anchor_tokens.add(tok)

    has_linkable_blocks = bool(context_blocks or resolution_blocks)
    kept_lines: List[str] = []
    removed_action_lines = 0

    for line in resolution_text.splitlines():
        stripped = line.strip()
        lower_line = stripped.lower()
        is_action_line = bool(re.match(r"^(?:[-•]|\d+\.)\s+", stripped))

        if is_action_line:
            is_vague = any(p in lower_line for p in vague_patterns)
            has_concrete_marker = any(m in lower_line for m in concrete_markers)
            has_anchor_token = any(tok in lower_line for tok in anchor_tokens)
            if is_vague and (not has_linkable_blocks or (not has_concrete_marker and not has_anchor_token)):
                removed_action_lines += 1
                continue

        kept_lines.append(line)

    if removed_action_lines > 0 and not any(re.match(r"^\s*(?:[-•]|\d+\.)\s+", ln.strip()) for ln in kept_lines):
        kept_lines.append("  1. Actions non proposées: non reliées à des preuves/résolution validées.")

    return "\n".join(kept_lines).strip()


def _sanitize_llm_response_actions_with_context(
    response_text: str,
    context_blocks: List[Dict],
    resolution_blocks: List[Dict],
) -> str:
    """Sanitize only the LLM 'Actions recommandées' section using context linkage rules."""
    if not response_text:
        return response_text

    section_rx = re.compile(
        r"(?is)(?P<header>✅\s*\*\*Actions recommandées\*\*|\*\*Actions recommandées\*\*)(?P<body>.*?)(?=(?:\n(?:✅\s*\*\*|🔍\s*\*\*|📌\s*\*\*|⚠️\s*\*\*|🧠\s*\*\*|📊\s*\*\*|🗄️\s*\*\*|⏱️\s*\*\*|\*\*[^\n]+\*\*|##\s+))|\Z)",
    )

    def _replace(match: re.Match) -> str:
        header = match.group("header").strip()
        body = (match.group("body") or "").strip("\n")
        cleaned_body = _sanitize_resolution_actions_with_context(
            body,
            context_blocks=context_blocks,
            resolution_blocks=resolution_blocks,
        )
        if not cleaned_body:
            cleaned_body = "  1. Actions non proposées: non reliées à des preuves/résolution validées."
        return f"{header}\n{cleaned_body}\n"

    return section_rx.sub(_replace, response_text)


def _protect_unindexed_sql_identifiers(text: str) -> str:
    if not text:
        return text
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
        return "❌ Table non trouvée dans le référentiel indexé."

    return pattern.sub(repl, text)


class ChatbotService:
    """
    Service chatbot context-aware multi-tenant.
    D├â┬®l├â┬¿gue la recherche de connaissance ├â┬á l'IntelligenceOrchestrator
    qui route vers le bon pipeline selon le profil de l'application.
    """

    def __init__(self):
        self.llm = llm_client
        self.orchestrator = intelligence_orchestrator
        logger.info("[OK] ChatbotService initialis├® avec IntelligenceOrchestrator")
        if _NLP_AVAILABLE:
            logger.info("[OK] Couche NLP diagnostique activ├®e (anti-hallucination + slot-filling)")
        else:
            logger.warning("[WARN] Couche NLP diagnostique indisponible ÔÇö mode d├®grad├®")
        if _DIAGNOSTIC_ENGINE_AVAILABLE:
            logger.info("[OK] Moteur diagnostic N3 activ├® (log patterns + proc├®dures N3)")
        else:
            logger.warning("[WARN] Moteur diagnostic N3 indisponible ÔÇö mode d├®grad├®")

    def _history_has_verifiable_evidence(self, history_text: str) -> bool:
        lowered = (history_text or "").lower()
        if not lowered.strip():
            return False
        evidence_markers = (
            "fr ", "fr:", "fr-", "exception", "stack", "trace", "log", "timestamp",
            "code=", "t_", "select ", "classe", "méthode", "fichier", "ligne",
            "workflow", "source", "provenance",
        )
        return any(marker in lowered for marker in evidence_markers)

    def _response_has_evidence(
        self,
        response_text: str,
        sources: List[Dict[str, Any]],
        live_bundle: Any,
        reasoning_trace: Dict[str, Any],
    ) -> bool:
        if sources:
            return True
        if live_bundle is not None and _has_real_live_evidence(live_bundle):
            return True
        if isinstance(reasoning_trace, dict):
            expl = reasoning_trace.get("explanation", {}) or {}
            if (expl.get("evidence_count") or 0) > 0:
                return True
            if reasoning_trace.get("structured_log_events"):
                return True
        lowered = (response_text or "").lower()
        if "aucune preuve" in lowered or "no evidence available" in lowered:
            return False
        return any(k in lowered for k in ("source", "provenance", "fr:", "classe", "méthode", "fichier", "ligne", "log", "exception"))

    async def process_message(self, message: ChatMessage, db=None) -> ChatResponse:
        """
        Traite un message utilisateur via le pipeline adapt├â┬® ├â┬á l'application.

        Flux :
        1. Orchestrateur r├â┬®sout le profil app ├óÔÇáÔÇÖ pipeline adapt├â┬®
        2. Pipeline recherche et score le contexte
        3. LLM g├â┬®n├â┬¿re la r├â┬®ponse avec le contexte structur├â┬®
        4. R├â┬®ponse enrichie avec m├â┬®tadonn├â┬®es trust
        """
        try:
            logger.info(f"[Chatbot] app={message.app_id}, message='{message.content[:60]}...'")

            conversation_id = message.conversation_id or str(uuid.uuid4())

            # 1b. Charger l'historique conversationnel depuis la DB
            history = self._load_history(message, db)

            # 1c. Reconstruct conversation state from history
            conv_state = self._reconstruct_state(history)
            conv_state.turn_count += 1

            # 1c-bis. Register the current question and detect loops.
            # If the same question has been asked >= 2 times without resolution,
            # we escalate intelligently instead of returning the same empty response.
            intent_override = detect_intent_override(message.content) if _NLP_AVAILABLE else None
            repetition_count = 0
            if _NLP_AVAILABLE and hasattr(conv_state, "register_question"):
                repetition_count = conv_state.register_question(message.content)
                if repetition_count >= 2:
                    logger.info(
                        f"[State] Loop d├®tect├®: question pos├®e {repetition_count}x ÔÇö "
                        f"escalade intelligente d├®clench├®e (override={intent_override})"
                    )
                    app_ctx_for_loop = {"display_name": message.app_id}
                    try:
                        _loop_orch = await self.orchestrator.process(
                            app_id=message.app_id, query=message.content, db=db, top_k=3
                        )
                        app_ctx_for_loop = _loop_orch.get("app_context", app_ctx_for_loop)
                    except Exception:
                        pass
                    escalation_msg = response_formatter.format_escalation_loop(
                        question=message.content,
                        repetition_count=repetition_count,
                        application=app_ctx_for_loop.get("display_name", message.app_id),
                        intent_override=intent_override,
                    )
                    return ChatResponse(
                        message=escalation_msg,
                        sources=[],
                        suggestions=[
                            "Cr├®er une FR pour documenter ce cas",
                            "Rechercher des tickets Jira similaires",
                            "Escalader vers l'├®quipe N3 avec les logs",
                        ],
                        confidence=0.0,
                        conversation_id=conversation_id,
                        app_id=message.app_id,
                        pipeline_mode="ESCALATION_LOOP",
                        trust_score=0,
                        trust_label="knowledge_gap",
                        diagnostic_available=False,
                    )

            # 1d. Detect phase transitions (pass conv_state for soft resolution counter)
            new_phase = detect_phase_transition(conv_state.phase, message.content, conv_state)
            if new_phase and new_phase != conv_state.phase:
                logger.info(f"[State] Phase transition: {conv_state.phase.value} ÔåÆ {new_phase.value}")
                conv_state.phase = new_phase

            # 1e. Lock root cause if user confirms it in this message
            rc = extract_root_cause(message.content)
            if rc and conv_state.confirmed_root_cause is None:
                conv_state.confirmed_root_cause = rc
                conv_state.resolution_confirmed = True
                logger.info(f"[State] Root cause locked: '{rc[:80]}'")

            # 1f. Detect audience
            conv_state.audience = detect_audience(message.content, conv_state.phase)

            # 1g. Short-circuit for CLOSING phase ÔÇö no RAG needed
            if conv_state.phase == ConversationPhase.CLOSING:
                logger.info("[State] Phase CLOSING ÔÇö bypassing RAG, generating closing message")
                return await self._handle_closing_phase(
                    message=message,
                    conv_state=conv_state,
                    conversation_id=conversation_id,
                    history=history,
                    db=db,
                )

            # 1g-bis. Short-circuit for SUMMARIZE intent ÔÇö bypass RAG entirely
            if intent_override == "summarize":
                logger.info("[Chatbot] Intent SUMMARIZE detected ÔÇö bypassing RAG, generating management summary")
                return await self._handle_summarize_intent(
                    message=message,
                    history=history,
                    conversation_id=conversation_id,
                )

            # 1h. Reformuler la requ├¬te si question de suivi (ex: "et ce ticket ?" ÔåÆ "ticket DSLAM suppression")
            effective_query = await self._resolve_query(message.content, history)
            if effective_query != message.content:
                logger.info(f"[Chatbot] Requ├¬te reformul├®e: '{message.content[:40]}' ÔåÆ '{effective_query[:60]}'")

            # 1. D├®l├®guer ├á l'orchestrateur
            orch_result = await self.orchestrator.process(
                app_id=message.app_id,
                query=effective_query,
                db=db,
                logs=message.logs,
                stack_trace=message.stack_trace,
                ticket_description=message.content,
                top_k=5,
            )

            # 1i. Initialise context guard (once, from first-turn ticket text)
            if _CONTEXT_GUARD_AVAILABLE:
                # Seed locked/excluded systems from first user message in history or current message
                first_user_text = message.content
                for m in (history or []):
                    if m.get("role") == "user":
                        first_user_text = m["content"]
                        break
                if not conv_state.locked_systems:
                    ctx_guard = IncidentContextGuard.from_ticket_text(
                        first_user_text, phase=conv_state.phase
                    )
                    conv_state.locked_systems = ctx_guard.locked_systems
                    conv_state.excluded_systems = ctx_guard.excluded_systems
                else:
                    ctx_guard = IncidentContextGuard(
                        locked_systems=conv_state.locked_systems,
                        excluded_systems=conv_state.excluded_systems,
                        phase=conv_state.phase,
                    )
            else:
                ctx_guard = None

            # 2. Construire le contexte texte pour le LLM
            # Apply context guard BEFORE building the prompt
            if ctx_guard is not None:
                raw_blocks = orch_result.get("context_blocks", [])
                orch_result["context_blocks"] = ctx_guard.filter_context_blocks(raw_blocks)

            # ── Historical Cases enrichment (Phase 8) ─────────────────────────
            try:
                from app.services.chatbot.historical_cases_retriever import (
                    historical_cases_retriever, compute_historical_case_score,
                )
                _hist_cases = historical_cases_retriever(
                    query=message.content,
                    intent=locals().get("_early_forensic_intent") or locals().get("_live_intent"),
                    entity=locals().get("_raw_user_entity"),
                    max_results=1,
                )
                # Only inject if high confidence match and no cross-contamination risk
                _hist_cases = [hc for hc in _hist_cases if hc.get("score", 0) >= 2.0]
                if _hist_cases:
                    # Sanitize: remove SQL mutations from historical case content
                    import re as _re_hist
                    _SQL_MUT = _re_hist.compile(r"(?i)\b(UPDATE|DELETE\s+FROM|INSERT\s+INTO|DROP\s+TABLE|TRUNCATE|ALTER\s+TABLE)\b[^;]*;?")
                    def _sanitize_hist(text: str) -> str:
                        return _SQL_MUT.sub("[SQL redacted]", text)[:150]
                    
                    _hist_block = {
                        "title": "Historical N3 Cases",
                        "content": "\n".join(
                            f"- {hc['intent']}: {_sanitize_hist(', '.join(hc.get('root_causes', [])[:2]))} "
                            f"(freq={hc['frequency']}, FR={hc.get('related_fr', [])})"
                            for hc in _hist_cases
                        ),
                        "source_type": "historical_cases",
                        "trust_score": int(_hist_cases[0].get("confidence", 0.5) * 100),
                    }
                    existing = orch_result.get("context_blocks", [])
                    orch_result["context_blocks"] = existing + [_hist_block]
                    logger.debug(f"[HistoricalCases] Injected {len(_hist_cases)} case(s)")
            except Exception as _hc_err:
                logger.debug(f"[HistoricalCases] Skipped: {_hc_err}")

            context_text = self.orchestrator.build_prompt_context(orch_result)

            # 3. R├®cup├®rer les garde-fous de r├®ponse (avant off_topic pour avoir app_ctx)
            guard = self.orchestrator.get_response_guard(orch_result)
            llm_instructions = orch_result.get("llm_instructions", "")
            # Limiter llm_instructions pour ne pas exploser le TPM Groq (6000 tokens)
            if llm_instructions and len(llm_instructions) > 1200:
                llm_instructions = llm_instructions[:1200]
            app_ctx = orch_result.get("app_context", {})

            # 3b. Forward state data into orch_result for build_system_prompt
            if conv_state.confirmed_root_cause:
                orch_result["confirmed_root_cause"] = conv_state.confirmed_root_cause
            if conv_state.locked_systems:
                orch_result["locked_systems"] = conv_state.locked_systems
            if conv_state.excluded_systems:
                orch_result["excluded_systems"] = conv_state.excluded_systems
            orch_result["audience"] = conv_state.audience
            orch_result["conversation_phase"] = conv_state.phase.value if hasattr(conv_state.phase, 'value') else str(conv_state.phase)

            # 2b. Cas hors-contexte : r├®ponse directe sans base de connaissance
            if orch_result.get("off_topic"):
                response_text = await self.llm.generate(
                    prompt=message.content,
                    system_prompt=(
                        f"Tu es un assistant support pour l'application {app_ctx.get('display_name', message.app_id)} (Orange). "
                        f"R├®ponds de fa├ºon concise et naturelle. "
                        f"Si c'est une salutation, r├®ponds poliment et invite l'utilisateur ├á d├®crire son probl├¿me technique."
                    ),
                )
                return ChatResponse(
                    message=response_text,
                    sources=[],
                    suggestions=["D├®crivez votre probl├¿me technique", "Indiquez le code d'erreur rencontr├®", "Pr├®cisez l'├®quipement concern├®"],
                    confidence=0.0,
                    conversation_id=conversation_id,
                    app_id=message.app_id,
                    pipeline_mode=orch_result.get("mode"),
                    trust_score=0,
                    trust_label="off_topic",
                    diagnostic_available=False,
                )

            # 2c. D├®tection intention ML Analysis : "causes principales", "analyse ML", etc.
            if self._detect_ml_analysis_intent(message.content):
                ml_response = await self._handle_ml_analysis_intent(
                    user_message=message.content,
                    conversation_id=conversation_id,
                    app_id=message.app_id,
                    orch_result=orch_result,
                )
                if ml_response:
                    return ml_response

            # 2c-quater. Classification ML directe d'un ticket
            if self._detect_classify_ticket_intent(message.content):
                classify_response = await self._handle_classify_ticket_intent(
                    user_message=message.content,
                    conversation_id=conversation_id,
                    app_id=message.app_id,
                    history=history,
                )
                if classify_response:
                    return classify_response

            # 2c-bis. D├®tection recherche ND dans les logs
            nd_number = self._extract_nd_number(message.content)
            if nd_number:
                nd_response = await self._handle_nd_log_intent(
                    nd_number=nd_number,
                    user_message=message.content,
                    conversation_id=conversation_id,
                    app_id=message.app_id,
                )
                if nd_response:
                    return nd_response

            # 2c-ter. D├®tection recherche ├®quipement dans les logs (DSLAM, NRO, ONT, ch├óssis)
            equip_name = self._extract_equipment_name(message.content)
            if equip_name:
                equip_response = await self._handle_equipment_log_intent(
                    equipment=equip_name,
                    user_message=message.content,
                    conversation_id=conversation_id,
                    app_id=message.app_id,
                )
                if equip_response:
                    return equip_response

            # 2d. D├®tection intention Jira : "y a-t-il une carte Jira ?", "ticket similaire ?", etc.
            if self._detect_jira_intent(message.content):
                jira_response = await self._handle_jira_intent(
                    user_message=message.content,
                    orch_result=orch_result,
                    conversation_id=conversation_id,
                    app_id=message.app_id,
                    app_ctx=app_ctx,
                    history=history,
                )
                if jira_response:
                    return jira_response

            # 2e. D├®tection intention inf├®rence technique : "c'est quoi ManageTechnicalConfigurationService"
            tech_symbol = self._detect_tech_inference_intent(message.content)
            if tech_symbol:
                logger.info(f"[TechInference] Symbole d├®tect├®: '{tech_symbol}'")
                return await self._handle_tech_inference_intent(
                    symbol=tech_symbol,
                    user_message=message.content,
                    orch_result=orch_result,
                    conversation_id=conversation_id,
                    app_id=message.app_id,
                    app_ctx=app_ctx,
                )

            # 2e-bis. Redaction message depositaire / client
            if self._detect_write_ticket_intent(message.content):
                logger.info('[WriteTicket] Intention redaction message depositaire detectee')
                return await self._handle_write_ticket_intent(
                    user_message=message.content,
                    conv_state=conv_state,
                    conversation_id=conversation_id,
                    app_id=message.app_id,
                    history=history,
                )

            # 2f. NLP Enrichment ÔÇö analyse structur├®e du message entrant
            structured_ticket = None
            clarifying_question = None

            # Conversation memory: inject prior procedure so trust gate / prompt builder
            # can enforce the no-contradiction rule.
            if _NLP_AVAILABLE:
                try:
                    from app.services.nlp.diagnostic_behavior import extract_prior_procedure_from_history
                    prior_proc = extract_prior_procedure_from_history(history)
                    if prior_proc:
                        orch_result["prior_procedure_id"] = prior_proc
                        logger.info(f"[Chatbot][Memory] Proc├®dure ant├®rieure d├®tect├®e: {prior_proc}")
                except Exception:
                    pass

            if _NLP_AVAILABLE:
                try:
                    structured_ticket = ticket_enricher.enrich(
                        raw_text=effective_query,
                        ticket_id="runtime_query",
                        fallback_application=message.app_id,
                    )
                    # Slot-filling: check if we need clarification
                    filled_slots, clarifying_question = slot_filler.analyze_slots(
                        structured_ticket, history
                    )
                    logger.info(
                        f"[Chatbot][NLP] type={structured_ticket.incident_type}, "
                        f"conf={structured_ticket.confidence:.2f}, "
                        f"slots={list(filled_slots.keys())}"
                    )
                    # ÔöÇÔöÇ Intent Override: force correct intent when ML classifier misses
                    # well-known signal patterns (script blocked, DB table query, etc.).
                    # This is general ÔÇö not specific to a single case.
                    if intent_override and structured_ticket:
                        original_intent = structured_ticket.incident_type
                        structured_ticket.incident_type = intent_override
                        logger.info(
                            f"[Chatbot][IntentOverride] '{original_intent}' ÔåÆ '{intent_override}' "
                            f"(signal pattern matched)"
                        )
                except Exception as nlp_err:
                    logger.warning(f"[Chatbot][NLP] Enrichissement ├®chou├®: {nlp_err}")

            # 2e. Trust gate ÔÇö refuse if knowledge is insufficient (score < 40)
            # NOTE: contextual intents (summarize / ticket-message / logs) bypass this gate.
            # NOTE: conversational follow-ups (ask for source date, clarification, etc.) also bypass.
            # NOTE: if context_blocks exist (even at low trust), the gate is also bypassed:
            #       blocks already found must be presented to the LLM rather than refusing.
            if _NLP_AVAILABLE and not orch_result.get("off_topic"):
                try:
                    can_respond, trust_reason = diagnostic_reasoner.check_trust_gate(
                        orch_result,
                        threshold=40.0,
                        structured_ticket=structured_ticket,
                        history=history,
                        raw_query=effective_query,
                    )
                    context_blocks = orch_result.get("context_blocks", [])
                    # Only refuse when BOTH trust is low AND there are no context blocks at all.
                    # If blocks exist we push them to the LLM regardless of the score
                    # so retrieved knowledge is never silently discarded.
                    if not can_respond and not context_blocks:
                        # Graceful refusal
                        app_name = app_ctx.get("display_name", message.app_id)
                        inc_type = structured_ticket.incident_type if structured_ticket else ""
                        refusal_msg = response_formatter.format_insufficient_knowledge(
                            query=effective_query,
                            application=app_name,
                            detected_type=inc_type,
                        )
                        logger.info(f"[Chatbot][Trust] Refus gracieux ÔÇö {trust_reason}")
                        return ChatResponse(
                            message=refusal_msg,
                            sources=[],
                            suggestions=[
                                "V├®rifier l'existence d'une FR pour ce cas",
                                "Consulter les tickets JIRA similaires",
                                "Fournir les logs de l'application pour analyse",
                            ],
                            confidence=0.0,
                            conversation_id=conversation_id,
                            app_id=message.app_id,
                            pipeline_mode=orch_result.get("mode"),
                            trust_score=0,
                            trust_label="insufficient",
                            diagnostic_available=False,
                        )
                    elif not can_respond and context_blocks:
                        logger.info(
                            f"[Chatbot][Trust] Score bas ({trust_reason}) mais {len(context_blocks)} "
                            f"bloc(s) KB disponible(s) ÔÇö passage au LLM maintenu"
                        )
                except Exception as tg_err:
                    logger.warning(f"[Chatbot][Trust] Trust gate error: {tg_err}")

            # 2f. Diagnostic Engine N3 ÔÇö raisonnement sur exception + proc├®dures
            diagnostic_result = None
            if _DIAGNOSTIC_ENGINE_AVAILABLE:
                try:
                    diagnostic_result = await diagnostic_engine.diagnose(
                        query=effective_query,
                        app_id=message.app_id,
                        db=db,
                        logs=message.logs,
                        stack_trace=message.stack_trace,
                    )
                    if diagnostic_result and diagnostic_result.is_usable():
                        logger.info(
                            f"[Chatbot][DiagEngine] proc={diagnostic_result.procedure_id}, "
                            f"trust={diagnostic_result.trust_score:.2f}, "
                            f"exc={diagnostic_result.exceptions_matched[:1]}"
                        )
                        # Inject diagnostic context into orch_result context blocks
                        if diagnostic_result.context_text:
                            existing_blocks = orch_result.get("context_blocks", [])
                            orch_result["context_blocks"] = [
                                {
                                    "title": f"Diagnostic N3 ÔÇö {diagnostic_result.procedure_title or diagnostic_result.incident_type}",
                                    "content": diagnostic_result.context_text,
                                    "trust_score": diagnostic_result.trust_score,
                                    "source_type": "diagnostic_engine",
                                    "procedure_id": diagnostic_result.procedure_id,
                                }
                            ] + existing_blocks
                        # Inject LLM instruction override from diagnostic engine
                        if diagnostic_result.llm_instruction:
                            orch_result["llm_instructions"] = (
                                diagnostic_result.llm_instruction
                                + "\n\n"
                                + orch_result.get("llm_instructions", "")
                            )
                except Exception as diag_err:
                    logger.warning(f"[Chatbot][DiagEngine] Diagnostic engine error: {diag_err}")

            # 4. Construire le prompt enrichi
            # Resume compact du contexte conversationnel (~20 tokens max)
            ctx_summary = self._build_context_summary(history)

            # Tronquer le contexte pour rester sous la limite TPM de Groq (6000 tokens)
            # Use stability guard sanitizer for safe truncation
            try:
                from app.services.live_diagnostics.stability_guards import sanitize_for_llm
                if context_text:
                    context_text = sanitize_for_llm(context_text, max_chars=3000)
            except ImportError:
                if context_text and len(context_text) > 3000:
                    context_text = context_text[:3000] + "\n[...tronqué...]"

            if context_text:
                # Utiliser le system prompt diagnostique enrichi si NLP disponible
                if _NLP_AVAILABLE and structured_ticket:
                    try:
                        system_prompt = PERSONA_INSTRUCTION + diagnostic_reasoner.build_system_prompt(
                            app_id=app_ctx.get("display_name", message.app_id),
                            orch_result=orch_result,
                            structured_ticket=structured_ticket,
                        )
                        if ctx_summary:
                            system_prompt += f"\n{ctx_summary}"
                        if llm_instructions:
                            system_prompt += f"\n\n{llm_instructions}"
                    except Exception as sp_err:
                        logger.warning(f"[Chatbot][NLP] System prompt enrichissement ├®chou├®: {sp_err}")
                        system_prompt = (
                            f"Tu es un assistant expert de l'application {app_ctx.get('display_name', message.app_id)} "
                            f"(Orange). Tu aides les techniciens N3 a diagnostiquer et resoudre les incidents. "
                            f"Tu utilises exclusivement les informations de la base de connaissance fournie. "
                            f"Tu ne repetes jamais deux fois la meme information dans ta reponse."
                            + (f"\n{ctx_summary}" if ctx_summary else "")
                            + (f"\n\n{llm_instructions}" if llm_instructions else "")
                        )
                else:
                    # llm_instructions dans le system_prompt (pas dans le user prompt)
                    # => evite que le LLM reformule le contexte deux fois
                    system_prompt = (
                        f"Tu es un assistant expert de l'application {app_ctx.get('display_name', message.app_id)} "
                        f"(Orange). Tu aides les techniciens N3 a diagnostiquer et resoudre les incidents. "
                        f"Tu utilises exclusivement les informations de la base de connaissance fournie. "
                        f"Tu ne repetes jamais deux fois la meme information dans ta reponse."
                        + (f"\n{ctx_summary}" if ctx_summary else "")
                        + (f"\n\n{llm_instructions}" if llm_instructions else "")
                    )
                full_prompt = f"""{context_text}

Question : {message.content}"""
            else:
                # Aucun contexte KB disponible.
                # Si c'est une question de suivi (follow-up), utiliser l'historique conversationnel.
                if history:
                    # Intent summarize d├®tect├® ÔåÆ prompt sp├®cialis├® r├®sum├® pour hi├®rarchie
                    _is_summarize = (intent_override == "summarize") or (
                        structured_ticket and structured_ticket.incident_type in ("summarize", "ticket_summary")
                    )
                    if _is_summarize:
                        system_prompt = (
                            f"Tu es un assistant support N3 pour l'application {app_ctx.get('display_name', message.app_id)} (Orange). "
                            f"L'ing├®nieur a besoin d'un r├®sum├® structur├® de la situation pour le communiquer ├á sa hi├®rarchie. "
                            f"R├êGLES IMP├ëRATIVES :\n"
                            f"- Utilise UNIQUEMENT les informations pr├®sentes dans l'historique de la conversation.\n"
                            f"- Ne g├®n├¿re PAS de nouvelles hypoth├¿ses ou proc├®dures.\n"
                            f"- Ne mentionne PAS de syst├¿mes qui ne sont pas dans l'historique.\n"
                            f"- Structure : (1) Situation client, (2) Anomalies d├®tect├®es, (3) Diagnostic, (4) Actions recommand├®es / escalade.\n"
                            f"- Ton professionnel, concis (8-12 lignes max). R├®ponds en fran├ºais."
                            + (f"\n{ctx_summary}" if ctx_summary else "")
                        )
                    else:
                        system_prompt = (
                            f"Tu es un assistant support expert pour l'application {app_ctx.get('display_name', message.app_id)} (Orange). "
                            f"R├®ponds ├á la question de l'utilisateur en t'appuyant sur l'historique de la conversation ci-dessous. "
                            f"Sois pr├®cis et concis. Si la r├®ponse n'est pas dans l'historique, dis-le clairement."
                            + (f"\n{ctx_summary}" if ctx_summary else "")
                        )
                    full_prompt = message.content
                else:
                    system_prompt = (
                        f"Tu es un assistant support pour l'application {app_ctx.get('display_name', message.app_id)}. "
                        f"Tu n'as pas de base de connaissance disponible pour cette requete."
                        + (f"\n{ctx_summary}" if ctx_summary else "")
                    )
                    full_prompt = (
                        f"{message.content}\n\n"
                        f"Aucune connaissance structuree disponible. "
                        f"Indique clairement que le diagnostic necessite des donnees supplementaires. "
                        f"Ne genere pas de conseils generiques."
                    )

            # 5b-live. Live Diagnostics (SSH -> psql Brasil DB)
            # FIX #1/#4/#5/#6/#7/#10/#11: Full deterministic evidence pipeline
            _live_diag_response = None   # will hold deterministic response if confidence high
            _follow_up_message: str = ""  # second chat bubble: log evidence + timeline
            _live_bundle = None
            _reasoning_trace: dict = {}  # internal debug trace — NEVER sent to LLM or user
            _early_forensic_intent: str = ""   # forensic intent resolved before DB pipeline
            _early_forensic_entity: str = ""   # entity extracted from user message

            # ── FORENSIC MEMORY: Load persisted evidence from prior turns ─────
            _forensic_mem = None
            try:
                from app.services.chatbot.forensic_memory import forensic_memory_store
                _forensic_mem = forensic_memory_store.get_or_create(conversation_id)
            except Exception:
                pass

            # ── PRE-STEP: Resolve forensic intents via IntentResolver (always runs) ───────────
            # This is SEPARATE from intent_from_message() which only knows DB/diagnostic intents.
            # Must run before the SSH guard so forensic commands work even without live SSH.
            try:
                from app.services.chatbot.intent_resolver import (
                    _INTENT_PATTERNS, FORENSIC_INTENTS, INTENT_UNKNOWN
                )
                from app.services.chatbot.conversation_state import ConversationState as _CS
                _ir_matched = next(
                    (intent for pattern, intent in _INTENT_PATTERNS if pattern.search(message.content)),
                    None,
                )
                if _ir_matched and _ir_matched in FORENSIC_INTENTS:
                    _early_forensic_intent = _ir_matched
                    # Extract entity from message — equipment name OR ND number
                    import re as _re2
                    _eqpt_match = _re2.search(
                        r'\b((?:DS|NB|MX|SW|RO|OLT|DSLAM|ONU|BNG|SRB|FTTH)[A-Z0-9_\-]{2,20})\b',
                        message.content, _re2.IGNORECASE
                    )
                    if _eqpt_match:
                        _early_forensic_entity = _eqpt_match.group(1).upper()
                    else:
                        # ND / IAR / dossier number (7-10 digits, after keyword)
                        _nd_match = _re2.search(
                            r'\b(?:ND|IAR|dossier|order|commande|num[eé]ro)\s*[:\s#]?\s*(\d{7,10})\b',
                            message.content, _re2.IGNORECASE
                        )
                        if not _nd_match:
                            # Standalone 7-10 digit number (likely ND/IAR)
                            _nd_match = _re2.search(r'\b(\d{7,10})\b', message.content)
                        if _nd_match:
                            _early_forensic_entity = _nd_match.group(1)
            except Exception as _ir_err:
                logger.debug(f"[IntentResolver pre-check] {_ir_err}")

            # ── Semantic Intent Router V2 ──────────────────────────────────────────
            # Supplements the IntentResolver with 25-category semantic classification.
            # Only upgrades _early_forensic_intent when the existing resolver missed.
            _semantic_route = None
            try:
                from app.services.chatbot.semantic_intent_router import semantic_router
                _semantic_route = semantic_router.route(message.content)
                # If IntentResolver didn't catch a forensic intent but semantic router did
                if not _early_forensic_intent and _semantic_route.forensic_intent:
                    from app.services.chatbot.intent_resolver import FORENSIC_INTENTS
                    if _semantic_route.forensic_intent in FORENSIC_INTENTS:
                        _early_forensic_intent = _semantic_route.forensic_intent
                        logger.info(
                            f"[SemanticRouter] Promoted intent: {_semantic_route.forensic_intent} "
                            f"(primary={_semantic_route.primary} conf={_semantic_route.confidence:.2f})"
                        )
            except Exception as _sr_err:
                logger.debug(f"[SemanticRouter] skipped: {_sr_err}")

            # Lazy SSH init — first request triggers connection (non-blocking for import)
            _init_live_orch_once()

            if _LIVE_DIAG_AVAILABLE and _live_orch is not None:
                try:
                    from app.services.live_diagnostics.planners.diagnostic_planner import intent_from_message
                    from app.services.chatbot.intent_resolver import FORENSIC_INTENTS
                    _live_intent = None
                    _live_entity = None
                    if 'structured_ticket' in dir() and structured_ticket:
                        _live_intent = getattr(structured_ticket, 'intent', None)
                        _live_entity = (getattr(structured_ticket, 'equipment_id', None)
                                     or getattr(structured_ticket, 'entity', None))
                    _msg_intent, _msg_entity = intent_from_message(message.content, _live_entity)
                    # FIX #1: Prefer specific diag intent; ALWAYS preserve original entity
                    _GENERIC_INTENTS = {"order_blocked", "check_node", "unknown", None}
                    if not _live_intent or _live_intent.lower() in _GENERIC_INTENTS:
                        _live_intent = _msg_intent
                    if not _live_entity:
                        _live_entity = _msg_entity
                    # FIX #1: Store raw entity - NEVER replace with DB-resolved name
                    _raw_user_entity = _live_entity or _early_forensic_entity or None

                    # Forensic intent from pre-step overrides diagnostic planner output
                    # (intent_from_message never returns forensic_* intents)
                    _resolved_intent = _early_forensic_intent or _msg_intent or _live_intent or ""

                    # ── Populate initial reasoning trace (debug only) ──────────────
                    _reasoning_trace = {
                        "intent":    _live_intent,
                        "entity":    _raw_user_entity,
                        "phase":     getattr(conv_state, "phase", {}).value if _NLP_AVAILABLE and conv_state and hasattr(conv_state, "phase") else "unknown",
                    }

                    # ── FORENSIC INTENT HANDLER ────────────────────────────────────
                    # Handle forensic_logs / forensic_timeline / forensic_evidence
                    # before the regular diagnostic pipeline.
                    _resolved_intent = _early_forensic_intent or _msg_intent or _live_intent or ""
                    if _resolved_intent in FORENSIC_INTENTS:
                        # find_code_function: answer directly from execution graph — no SSH, no LLM
                        if _resolved_intent == "find_code_function":
                            try:
                                from app.services.chatbot.forensic_followup import forensic_followup_handler
                                _entity_for_fn = _raw_user_entity or _early_forensic_entity or None
                                _live_diag_response = forensic_followup_handler.handle(
                                    forensic_intent="find_code_function",
                                    entity=_entity_for_fn,
                                    cached_trace={"user_query": message.content},
                                    cached_bundle=None,
                                )
                            except Exception as _fcf_err:
                                logger.warning(f"[FindCodeFunction] {_fcf_err}")
                            # Skip SSH + LLM entirely — jump to response assembly
                            _skip_ssh_pipeline = True
                        try:
                            from app.services.live_diagnostics.logs.log_parser import (
                                format_evidence_for_user,
                            )
                            from app.services.live_diagnostics.logs.log_correlation_engine import (
                                format_hypotheses_for_user, log_correlation_engine,
                            )
                            from app.services.live_diagnostics.timeline.timeline_builder import (
                                format_timeline_for_user, build_timeline,
                            )

                            _forensic_entity = _raw_user_entity or _live_entity or ""
                            _forensic_response_parts = []

                            if _resolved_intent == "forensic_logs":
                                if _live_logs_runtime_available(_live_orch):
                                    # Extract structured log evidence for the entity
                                    _forensic_log_events = []
                                    _forensic_log_files = ["brasil_app", "catalina", "connectorCL"]
                                    for _lf in _forensic_log_files:
                                        try:
                                            if _forensic_entity:
                                                _evs = _live_orch._log_svc.grep_equipment(
                                                    _forensic_entity, log_file=_lf,
                                                    max_lines=50, tail_lines=300,
                                                )
                                            else:
                                                _evs = _live_orch._log_svc.extract_structured(
                                                    log_file=_lf, tail_lines=200, min_score=0.60,
                                                )
                                            _forensic_log_events.extend(_evs)
                                        except Exception:
                                            pass

                                    _reasoning_trace["forensic_log_events"] = len(_forensic_log_events)
                                    if _forensic_log_events:
                                        _forensic_response_parts.append(
                                            f"**📋 Logs forensiques**"
                                            + (f" — `{_forensic_entity}`" if _forensic_entity else "")
                                        )
                                        _forensic_response_parts.append("")
                                        _forensic_response_parts.append(format_evidence_for_user(_forensic_log_events, max_events=15))
                                        # Correlation
                                        _hyps = log_correlation_engine.correlate(log_events=_forensic_log_events)
                                        if _hyps:
                                            _forensic_response_parts.append("")
                                            _forensic_response_parts.append(format_hypotheses_for_user(_hyps))
                                            _reasoning_trace["top_hypothesis"] = _hyps[0].cause if _hyps else None
                                    else:
                                        _forensic_response_parts.append(
                                            f"**📋 Logs forensiques**\n"
                                            f"_Aucune ligne de log trouvée"
                                            + (f" pour `{_forensic_entity}`" if _forensic_entity else "")
                                            + "._"
                                        )
                                else:
                                    _forensic_response_parts.append(
                                        f"**📋 Logs forensiques**"
                                        + (f" — `{_forensic_entity}`" if _forensic_entity else "")
                                        + "\n"
                                        "_Analyse live des logs indisponible : aucun serveur de logs connecté pour cette requête._"
                                    )

                            elif _resolved_intent == "forensic_timeline":
                                # Build incident timeline from any available bundle
                                _timeline_bundle = None
                                if _live_intent and (_forensic_entity or _live_entity):
                                    try:
                                        _timeline_bundle = _live_orch.run(
                                            intent=_live_intent or "diagnose_equipment",
                                            entity=_forensic_entity,
                                        )
                                    except Exception:
                                        pass

                                _tl_logs = []
                                if _timeline_bundle:
                                    try:
                                        from app.services.live_diagnostics.logs.log_parser import parse_log_lines
                                        for _lev in (_timeline_bundle.log_evidence or []):
                                            _tl_logs.extend(
                                                parse_log_lines(
                                                    getattr(_lev, "matched_lines", []),
                                                    source=getattr(_lev, "log_file", "log"),
                                                )
                                            )
                                    except Exception:
                                        pass

                                _tl = build_timeline(
                                    log_events=_tl_logs or [],
                                    db_evidence=_timeline_bundle.db_evidence if _timeline_bundle else {},
                                    ssh_evidence=_timeline_bundle.ssh_evidence if _timeline_bundle else [],
                                    fr_blocks=_timeline_bundle.reasoning_trace.get("resolution_blocks", []) if _timeline_bundle else [],
                                    entity=_forensic_entity,
                                )
                                _reasoning_trace["timeline_events"] = len(_tl)
                                _forensic_response_parts.append(format_timeline_for_user(_tl))

                            elif _resolved_intent == "forensic_evidence":
                                # Show all runtime evidence from the last diagnostic bundle
                                # Run a fresh diagnostic if entity is known
                                _ev_bundle = None
                                if _forensic_entity:
                                    try:
                                        _ev_bundle = _live_orch.run(
                                            intent=_live_intent or "diagnose_equipment",
                                            entity=_forensic_entity,
                                        )
                                    except Exception:
                                        pass

                                if _ev_bundle:
                                    _forensic_response_parts.append(
                                        f"**🔍 Runtime Evidence** — `{_forensic_entity}`"
                                    )
                                    _forensic_response_parts.append("")
                                    _ctx_blocks = _ev_bundle.to_context_blocks()
                                    if _ctx_blocks:
                                        for _cb in _ctx_blocks:
                                            _cb_title = _cb.get("title", "Evidence")
                                            _cb_content = _cb.get("content", "")
                                            _cb_trust = _cb.get("trust_score", 0)
                                            _forensic_response_parts.append(
                                                f"**{_cb_title}** (trust={_cb_trust}%)\n```\n{_cb_content[:400]}\n```"
                                            )
                                    else:
                                        _forensic_response_parts.append(
                                            "_Aucune donnée runtime disponible pour cet équipement._"
                                        )
                                    _reasoning_trace["evidence_blocks"] = len(_ctx_blocks)
                                else:
                                    _forensic_response_parts.append(
                                        "**🔍 Runtime Evidence**\n"
                                        "_Aucune donnée disponible — préciser le nom de l'équipement._"
                                    )

                            if _forensic_response_parts:
                                _live_diag_response = "\n".join(_forensic_response_parts)
                                logger.info(
                                    f"[Forensic] intent={_resolved_intent} entity={_forensic_entity} "
                                    f"trace={_reasoning_trace}"
                                )
                        except Exception as _forensic_err:
                            logger.warning(f"[Forensic] Handler error (non-blocking): {_forensic_err}")

                    elif not locals().get("_skip_ssh_pipeline") and _live_intent and (_live_intent != "check_node" or _live_entity):
                        _bundle = _live_orch.run(intent=_live_intent, entity=_live_entity)
                        _live_bundle = _bundle
                        _live_blocks = _bundle.to_context_blocks() if _bundle else []

                        # FIX #7: Build evidence correlation summary
                        _resolution_blocks = _bundle.reasoning_trace.get("resolution_blocks", []) if _bundle else []
                        _max_conf = _bundle.highest_confidence() if _bundle else 0.0

                        # ── N3 REASONING LAYER: Business Rules + FSM + Sync + RCA ──────────────
                        # These engines run BEFORE the LLM call and inject deterministic
                        # constraint verdicts, state diagnoses, sync anomalies, and causal
                        # chains into the context — replacing retrieval with actual reasoning.
                        _n3_reasoning_blocks: list = []
                        try:
                            from app.services.chatbot.business_rule_engine import (
                                get_business_rule_engine, EvidenceContext,
                            )
                            from app.services.chatbot.state_machine import get_state_machine
                            from app.services.chatbot.sync_anomaly_detector import get_sync_anomaly_detector
                            from app.services.chatbot.causal_rca import get_rca_engine

                            # Build evidence context from live bundle
                            _db_ev = (
                                _bundle.db_evidence[0]
                                if (_bundle and getattr(_bundle, 'db_evidence', None))
                                else None
                            )
                            _log_ev = (
                                _bundle.log_evidence[0]
                                if (_bundle and getattr(_bundle, 'log_evidence', None))
                                else None
                            )
                            _ev_ctx = EvidenceContext.from_db_evidence(_db_ev, _log_ev)

                            # 1. Business Rule Engine — executable constraint evaluation
                            _bre = get_business_rule_engine()
                            _bre_result = _bre.evaluate(
                                intent=_live_intent or _early_forensic_intent,
                                evidence=_ev_ctx,
                            )
                            if _bre_result.blocked or _bre_result.warning_rules:
                                _n3_reasoning_blocks.append(_bre_result.to_context_block())
                                _reasoning_trace["bre_blocked"] = _bre_result.blocked
                                _reasoning_trace["bre_fired"] = [r.rule_id for r in _bre_result.fired_rules]

                            # 2. State Machine — FSM analysis + orphan/inconsistency detection
                            _fsm = get_state_machine()
                            _fsm_diag = _fsm.analyze_equipment(
                                entity_name=_live_entity or _raw_user_entity or "?",
                                current_status=_ev_ctx.eqpt_status,
                                target_operation=(
                                    "delete" if "delete" in (_live_intent or "") else
                                    "modify" if "mutation" in (_live_intent or "") else None
                                ),
                                active_services=_ev_ctx.active_services_count or 0,
                                active_links=_ev_ctx.active_links_count or 0,
                                mq_ack_present=_ev_ctx.mq_ack_present,
                                orchestra_status=_ev_ctx.orchestra_status,
                            )
                            if (_fsm_diag.is_orphan or _fsm_diag.is_inconsistent
                                    or not _fsm_diag.transition_allowed):
                                _n3_reasoning_blocks.append(_fsm_diag.to_context_block())
                                _reasoning_trace["fsm_orphan"] = _fsm_diag.is_orphan
                                _reasoning_trace["fsm_inconsistent"] = _fsm_diag.is_inconsistent

                            # 3. Sync Anomaly Detector — DB/MQ/ORCHESTRA/42C divergences
                            _all_log_signals: list = []
                            for _lev in (getattr(_bundle, 'log_evidence', None) or []):
                                _all_log_signals.extend(getattr(_lev, 'matched_lines', []))
                            _sync_det = get_sync_anomaly_detector()
                            _sync_result = _sync_det.analyze(
                                entity_name=_live_entity or _raw_user_entity,
                                db_status=_ev_ctx.eqpt_status,
                                mq_ack_present=_ev_ctx.mq_ack_present,
                                orchestra_status=_ev_ctx.orchestra_status,
                                log_lines=_all_log_signals[:100],
                                detected_exceptions=_ev_ctx.detected_exceptions,
                                intent=_live_intent or _early_forensic_intent,
                                active_services=_ev_ctx.active_services_count or 0,
                                active_links=_ev_ctx.active_links_count or 0,
                            )
                            if _sync_result.anomalies:
                                _n3_reasoning_blocks.append(_sync_result.to_context_block())
                                _reasoning_trace["sync_anomalies"] = len(_sync_result.anomalies)
                                _reasoning_trace["sync_critical"] = _sync_result.has_critical

                            # 4. Causal RCA Engine — multi-hop backward traversal
                            _rca_eng = get_rca_engine()
                            _rca_result = _rca_eng.analyze(
                                entity_name=_live_entity or _raw_user_entity,
                                intent=_live_intent or _early_forensic_intent,
                                active_rule_ids=[r.rule_id for r in _bre_result.fired_rules]
                                    + [r.rule_id for r in _bre_result.warning_rules],
                                sync_anomaly_types=[a.anomaly_type.value for a in _sync_result.anomalies],
                                detected_exceptions=_ev_ctx.detected_exceptions,
                                log_signals=_all_log_signals[:50],
                                db_status=_ev_ctx.eqpt_status,
                                active_services=_ev_ctx.active_services_count or 0,
                                active_links=_ev_ctx.active_links_count or 0,
                            )
                            if _rca_result.hypotheses:
                                _n3_reasoning_blocks.append(_rca_result.to_context_block())
                                _reasoning_trace["rca_hypotheses"] = len(_rca_result.hypotheses)
                                if _rca_result.top_hypothesis:
                                    _reasoning_trace["rca_top"] = _rca_result.top_hypothesis.root_cause_id

                            # Prepend N3 reasoning blocks to live context blocks
                            if _n3_reasoning_blocks:
                                _live_blocks = _n3_reasoning_blocks + _live_blocks

                        except Exception as _n3_err:
                            logger.warning(f"[N3Reasoning] Non-blocking error: {_n3_err}")
                        # ── END N3 REASONING LAYER ─────────────────────────────────────────────

                        # Update reasoning trace with evidence stats (debug only)
                        _reasoning_trace.update({
                            "live_blocks":      len(_live_blocks),
                            "resolution_blocks": len(_resolution_blocks),
                            "max_confidence":   round(_max_conf, 3),
                        })

                        # Log-based correlation enrichment
                        try:
                            from app.services.live_diagnostics.logs.log_correlation_engine import log_correlation_engine
                            from app.services.live_diagnostics.logs.log_parser import parse_log_lines
                            _all_log_lines: list = []
                            for _lev in (_bundle.log_evidence if _bundle else []):
                                _all_log_lines.extend(getattr(_lev, "matched_lines", []))
                            if _all_log_lines:
                                _parsed_log_events = parse_log_lines(_all_log_lines, source="live")
                                _hypotheses = log_correlation_engine.correlate(log_events=_parsed_log_events)
                                if _hypotheses:
                                    _reasoning_trace["top_hypothesis"] = _hypotheses[0].cause
                                    _reasoning_trace["hypothesis_conf"] = round(_hypotheses[0].confidence, 3)
                                    # Inject correlation into system prompt later if LLM path taken
                                    _live_blocks = _live_blocks  # keep existing blocks
                                    if not hasattr(_bundle, "_corr_hypotheses"):
                                        object.__setattr__(_bundle, "_corr_hypotheses", _hypotheses)
                        except Exception:
                            pass

                        if _live_blocks or _resolution_blocks:
                            _live_partitions = _partition_live_context_blocks(_live_blocks)
                            _db_live_blocks = _live_partitions["live_db"]
                            _log_live_blocks = _live_partitions["live_log"]

                            # Build structured evidence text (FIX #6 format)
                            _db_evidence_parts = []
                            for b in _db_live_blocks:
                                _bc = b.get('content', str(b)) if isinstance(b, dict) else str(b)
                                _db_evidence_parts.append(_bc)
                            _log_evidence_parts = []
                            for b in _log_live_blocks:
                                _bc = b.get('content', str(b)) if isinstance(b, dict) else str(b)
                                _log_evidence_parts.append(_bc)
                            _resolution_text = ""
                            for rb in _resolution_blocks:
                                _rc = rb.get('content', str(rb)) if isinstance(rb, dict) else str(rb)
                                _resolution_text += _rc + "\n"
                            _resolution_text = _sanitize_resolution_actions_with_context(
                                _resolution_text,
                                _live_blocks,
                                _resolution_blocks,
                            )

                            _live_text = "\n".join(_db_evidence_parts + _log_evidence_parts)

                            # FIX #11: Skip LLM entirely if confidence >= 0.90 AND live evidence exists
                            if _max_conf >= 0.90 and _live_text.strip() and _resolution_text.strip():
                                # ── Build enriched forensic diagnostic response ─────────────────────────────
                                _det_parts = []
                                _det_parts.append(f"## 🧠 Diagnostic — `{_raw_user_entity or _live_intent}`")
                                _det_parts.append("")

                                # ── Cause racine ────────────────────────────────────────────
                                _det_parts.append("🔍 **Cause racine**")
                                for rb in _resolution_blocks:
                                    _title = rb.get('title', '') if isinstance(rb, dict) else ''
                                    if _title:
                                        _det_parts.append(f"**{_title}**")
                                _det_parts.append("")

                                # ── Parse log evidence into structured events ────────────────
                                _parsed_for_diag = []
                                _log_source_map = {}  # event index -> source log file
                                try:
                                    from app.services.live_diagnostics.logs.log_parser import (
                                        parse_log_lines, format_evidence_for_user
                                    )
                                    from app.services.live_diagnostics.timeline.timeline_builder import (
                                        build_timeline, format_timeline_for_user
                                    )
                                    from app.services.live_diagnostics.logs.log_correlation_engine import (
                                        format_hypotheses_for_user, log_correlation_engine as _lce
                                    )
                                    for _lev in (_bundle.log_evidence if _bundle else []):
                                        _src_file = getattr(_lev, 'log_file', 'log')
                                        _llines = getattr(_lev, 'matched_lines', [])
                                        _evs = parse_log_lines(_llines, source=_src_file, min_score=0.30)
                                        for _ev in _evs:
                                            _log_source_map[len(_parsed_for_diag)] = _src_file
                                            _parsed_for_diag.append(_ev)
                                except Exception:
                                    pass

                                # ── DB evidence summary (stays in first message) ─────────────
                                _det_parts.append("📌 **Preuves DB**")
                                if _db_evidence_parts:
                                    for ep in _db_evidence_parts:
                                        _det_parts.append(f"- {ep}")
                                else:
                                    _det_parts.append("- Aucune preuve live DB disponible.")

                                if _log_evidence_parts:
                                    _det_parts.append("")
                                    _det_parts.append("📋 **Preuves logs**")
                                    for ep in _log_evidence_parts[:3]:
                                        _det_parts.append(f"- {ep}")

                                # ── SSH system status (separate line, only if relevant) ──────
                                _ssh_summary = _bundle.to_ssh_summary() if _bundle else []
                                if _ssh_summary:
                                    _det_parts.append("")
                                    _det_parts.append("🖥️ **État système**")
                                    for _sl in _ssh_summary:
                                        _det_parts.append(f"- {_sl}")

                                # ── Code source validation (Phase 2) ─────────────────────────
                                try:
                                    from app.services.code_intelligence import CODE_INTELLIGENCE_ENABLED
                                    if CODE_INTELLIGENCE_ENABLED:
                                        from app.services.code_intelligence.extractors.brasil_extractor import search_code_knowledge
                                        _code_hits = search_code_knowledge(
                                            entity="Dslam" if "dslam" in (_raw_user_entity or "").lower() else None,
                                            tags=["deletion", "constraint"] if _live_intent == "delete_equipment" else None,
                                        )
                                        if _code_hits:
                                            _det_parts.append("")
                                            _det_parts.append("📌 **Validation code source**")
                                            for _ch in _code_hits[:3]:
                                                _loc = _ch.code_location
                                                _method = _loc.get("method", "")
                                                _file = _loc.get("file", "").split("\\")[-1]
                                                _line = _loc.get("line", "")
                                                _bc = _ch.blocking_condition or _ch.exception_class
                                                _src_ref = f"`{_file}:{_line}`" if _line else f"`{_file}`"
                                                _det_parts.append(
                                                    f"- {_bc} → `{_method}()` ({_src_ref})"
                                                )
                                except Exception:
                                    pass

                                _det_parts.append("")

                                # ── Resolution actions (first message) ─────────────────────
                                _det_parts.append("✅ **Actions recommandées**")
                                _det_parts.append(_resolution_text.strip())
                                _live_diag_response = "\n".join(_det_parts)

                                # ── Second message: log lines + correlation + timeline ───────
                                # Only emit follow-up if there is real content to show
                                _follow_up_parts = []

                                if _parsed_for_diag:
                                    _follow_up_parts.append(
                                        f"📊 **Preuves live** — `{_raw_user_entity or _live_intent}`"
                                    )
                                    _follow_up_parts.append("")
                                    _follow_up_parts.append("**Lignes de log extraites**")
                                    _prev_src = None
                                    for _i, _ev in enumerate(_parsed_for_diag[:10]):
                                        _src = _log_source_map.get(_i, '')
                                        if _src != _prev_src:
                                            _src_short = _src.split(':')[-1] if ':' in _src else _src
                                            _follow_up_parts.append(f"`{_src_short}`")
                                            _prev_src = _src
                                        _follow_up_parts.append(_ev.to_forensic_line())
                                    _follow_up_parts.append("")

                                    # Correlation hypotheses
                                    try:
                                        _diag_hyps = _lce.correlate(log_events=_parsed_for_diag)
                                        if _diag_hyps:
                                            _follow_up_parts.append("🔗 **Corrélation runtime**")
                                            for _h in _diag_hyps[:2]:
                                                _follow_up_parts.append(
                                                    f"- `{_h.cause}` (conf={int(_h.confidence*100)}%) "
                                                    f"— {_h.description[:80]}"
                                                )
                                            _follow_up_parts.append("")
                                    except Exception:
                                        pass

                                    # Timeline
                                    try:
                                        _tl = build_timeline(
                                            log_events=_parsed_for_diag,
                                            db_evidence=_bundle.db_evidence if _bundle else {},
                                            fr_blocks=_resolution_blocks,
                                            entity=_raw_user_entity,
                                        )
                                        if _tl:
                                            _follow_up_parts.append(format_timeline_for_user(_tl[:8]))
                                    except Exception:
                                        pass

                                # ── Explainability chain (Phase 4) ───────────────────
                                try:
                                    _expl_data = (_bundle.reasoning_trace or {}).get("explanation") if _bundle else None
                                    if _expl_data:
                                        _reasoning_display = _expl_data.get("reasoning_chain_display", "")
                                        _tech_block = _expl_data.get("technical_block", "")
                                        if _reasoning_display:
                                            if not _follow_up_parts:
                                                _follow_up_parts.append(f"📊 **Analyse forensique** — `{_raw_user_entity or _live_intent}`")
                                                _follow_up_parts.append("")
                                            _follow_up_parts.append(_reasoning_display)
                                        elif _tech_block:
                                            if not _follow_up_parts:
                                                _follow_up_parts.append(f"📊 **Analyse forensique** — `{_raw_user_entity or _live_intent}`")
                                                _follow_up_parts.append("")
                                            _follow_up_parts.append(_tech_block)
                                except Exception:
                                    pass

                                # ── Forensic log summary (Phase 5) ───────────────────
                                try:
                                    _forensic_data = (_bundle.reasoning_trace or {}).get("forensic_summary") if _bundle else None
                                    if _forensic_data and _forensic_data.get("severity") in ("CRITICAL", "HIGH"):
                                        _ctx_llm = _forensic_data.get("context_for_llm", "")
                                        if _ctx_llm:
                                            if not _follow_up_parts:
                                                _follow_up_parts.append(f"📊 **Analyse forensique** — `{_raw_user_entity or _live_intent}`")
                                                _follow_up_parts.append("")
                                            _follow_up_parts.append("🔬 **Analyse forensique des logs**")
                                            _follow_up_parts.append(f"```\n{_ctx_llm}\n```")
                                            _follow_up_parts.append("")
                                except Exception:
                                    pass

                                # Attach resolved SQL queries to follow-up (only when eqpt_id known)
                                _sql_lines = []
                                for _rb in _resolution_blocks:
                                    if isinstance(_rb, dict) and _rb.get("sql_resolved") and _rb.get("sql_hints_raw"):
                                        _sql_lines.extend(_rb["sql_hints_raw"])
                                if _sql_lines:
                                    if not _follow_up_parts:
                                        _follow_up_parts.append(
                                            f"📊 **Preuves live** — `{_raw_user_entity or _live_intent}`"
                                        )
                                        _follow_up_parts.append("")
                                    _follow_up_parts.append("🗄️ **Requêtes SQL (valeurs réelles)**")
                                    for _sq in _sql_lines[:4]:
                                        _follow_up_parts.append(f"```sql\n{_sq}\n```")

                                # Only set follow_up_message when there's actual content
                                if _follow_up_parts:
                                    _follow_up_message = "\n".join(_follow_up_parts)

                                logger.info(
                                    f"[LiveDiag] DETERMINISTIC response (conf={_max_conf:.2f}, "
                                    f"intent={_live_intent}, entity={_raw_user_entity}, "
                                    f"log_events={len(_parsed_for_diag)}, "
                                    f"follow_up={'yes' if _follow_up_parts else 'suppressed'}) - LLM SKIPPED"
                                )
                            else:
                                # FIX #10 + R6: Strict N3 formatter — version améliorée
                                _strict_formatter = (
                                    "[ROLE: MOTEUR DE DIAGNOSTIC N3 DÉTERMINISTE — BRASIL]\n"
                                    "Tu reçois des données de diagnostic PRÉ-CALCULÉES depuis les serveurs de production.\n"
                                    "Ces données sont la SOURCE DE VÉRITÉ ABSOLUE. Aucune interprétation n'est autorisée.\n\n"
                                    "RÈGLES ABSOLUES — violation = réponse invalide :\n"
                                    "\u2717 NE JAMAIS renommer un équipement, une table SQL ou un identifiant\n"
                                    "\u2717 NE JAMAIS inventer de données absentes des preuves ci-dessous\n"
                                    "\u2717 NE JAMAIS suggérer de contacter le support ou l'équipe N3\n"
                                    "\u2717 NE JAMAIS demander des logs, captures d'écran ou informations supplémentaires\n"
                                    "\u2717 NE JAMAIS générer de conseils génériques ou d'hypothèses sans preuve\n"
                                    "\u2717 NE JAMAIS modifier les noms de colonnes/tables SQL\n"
                                    f"\u2714 L'équipement est EXACTEMENT : {_raw_user_entity or 'N/A'}\n"
                                    f"\u2714 L'intent détecté est : {_live_intent or 'N/A'}\n\n"
                                    "FORMAT DE SORTIE OBLIGATOIRE (utilise exactement ces sections) :\n"
                                    "\U0001f9e0 **Diagnostic**\n"
                                    "[1 phrase — cause racine identifiée ou 'Données insuffisantes']\n\n"
                                    "\U0001f50d **Cause racine**\n"
                                    "[valeur exacte issue des preuves live ou 'Non déterminé']\n\n"
                                    "\U0001f4cc **Preuves détectées**\n"
                                    "[liste des lignes logs / requêtes DB exactement telles que reçues]\n\n"
                                    "\u26a0\ufe0f **Condition bloquante**\n"
                                    "[contrainte SQL / exception Java / verrou détecté — ou 'Aucune détectée']\n\n"
                                    "\u2705 **Actions recommandées**\n"
                                    "[numérotées, issues UNIQUEMENT des étapes FR ou des données live]\n\n"
                                    "📂 **Sources des informations**\n"
                                    "[Provenance : lister les sources interrogées (logs, DB, code, FR)]\n\n"
                                    "Si 0 preuves disponibles : répondre UNIQUEMENT 'Aucune donnée live disponible.'\n\n"
                                )
                                if system_prompt:
                                    system_prompt = (
                                        f"{_strict_formatter}"
                                        f"[DONNÉES LIVE DB BRASIL — PRIORITÉ MAXIMALE]\n"
                                        f"Entité : {_raw_user_entity or 'N/A'} | Intent : {_live_intent or 'N/A'}\n"
                                        f"{_live_text}\n\n"
                                        f"[ÉTAPES DE RÉSOLUTION FR]\n"
                                        f"{_resolution_text}\n\n"
                                        f"{system_prompt}"
                                    )
                                logger.info(
                                    f"[LiveDiag] {len(_live_blocks)} bloc(s) + "
                                    f"{len(_resolution_blocks)} resolution(s) injected "
                                    f"(intent={_live_intent}, entity={_raw_user_entity}, conf={_max_conf:.2f})"
                                )
                        else:
                            # R7-FIX: zero evidence — réponse structurée déterministe
                            # plutôt que laisser le LLM halluciner une réponse générique
                            if _live_intent and (_raw_user_entity or _live_entity):
                                _zero_entity = _raw_user_entity or _live_entity or "?"
                                # Vérifier si des FRs KB sont disponibles pour cet intent
                                _kb_fr_hint = ""
                                _kb_blocks = orch_result.get("context_blocks", []) or []
                                _kb_suggestions = [
                                    b for b in _kb_blocks
                                    if isinstance(b, dict)
                                    and str(b.get("source_type", "") or "").lower() not in ("live_log", "live_db", "ssh")
                                    and int(b.get("trust_score", 0) or 0) >= 85
                                ][:2]
                                if _kb_suggestions:
                                    _kb_lines = []
                                    for _kb in _kb_suggestions:
                                        _fr_id = _kb.get("fr_id") or _kb.get("id") or ""
                                        _fr_title = _kb.get("title", "")
                                        if _fr_id or _fr_title:
                                            _kb_lines.append(f"- {_fr_id} — {_fr_title}".strip())
                                    if _kb_lines:
                                        _kb_fr_hint = (
                                            "\n\n\U0001f4da **Références documentaires possibles (non confirmées)**\n"
                                            + "\n".join(_kb_lines)
                                        )
                                # ── Entity-type-aware zero-evidence fallback ──────────
                                # Detect entity type to give correct table / guidance
                                _ze_is_nd = bool(re.match(r'^\d{9}$', str(_zero_entity).strip()))
                                _ze_is_numeric = bool(re.match(r'^\d+$', str(_zero_entity).strip()))
                                if _ze_is_nd:
                                    # ND (Noeud de Distribution) — 9-digit subscriber number
                                    _ze_table_hint = (
                                        f"1. Rechercher le ND `{_zero_entity}` dans:\n"
                                        f"   - `t_nd` ou `t_tp_initial_states.nd_id` (identifiant ND)\n"
                                        f"   - `t_tps.tp_dslam_n` pour les plans de transfert associés\n"
                                        f"   - `t_services` pour les services sur ce ND\n"
                                        f"2. Vérifier dans BRASIL IHM : Gestion ND → rechercher `{_zero_entity}`\n"
                                        f"3. Consulter les logs WA : `catalina.out` | grep `{_zero_entity}`\n"
                                        f"4. Contrôler la connectivité SSH vers `op49mwa11`"
                                    )
                                    _ze_entity_label = f"ND `{_zero_entity}`"
                                    _ze_entity_type = "Noeud de Distribution (ND)"
                                elif _ze_is_numeric:
                                    _ze_table_hint = (
                                        f"1. Identifier le type de cet identifiant numérique\n"
                                        f"2. Rechercher dans `t_nd`, `t_tps`, `t_services`, `t_epcs`\n"
                                        f"3. Vérifier les logs : `catalina.out` | grep `{_zero_entity}`"
                                    )
                                    _ze_entity_label = f"`{_zero_entity}`"
                                    _ze_entity_type = "Identifiant numérique (type inconnu)"
                                else:
                                    _ze_table_hint = (
                                        f"1. Confirmer que `{_zero_entity}` existe dans `t_equipments`\n"
                                        f"   (colonnes `eqpt_name` / `code_eqpt` / `lib_eqpt`)\n"
                                        f"2. Vérifier les logs WA : `catalina.out`, "
                                        f"`connectorCL_{{date}}.log`\n"
                                        f"3. Contrôler la connectivité SSH vers `op49mdb11` et `op49mwa11`"
                                    )
                                    _ze_entity_label = f"`{_zero_entity}`"
                                    _ze_entity_type = "Équipement (DSLAM/OLT/routeur)"
                                _live_diag_response = (
                                    f"\U0001f9e0 **Diagnostic**\n"
                                    f"Aucune donnée live disponible pour {_ze_entity_label}.\n"
                                    f"*(Les serveurs Brasil ne sont pas accessibles en ce moment.)*\n"
                                    f"*Type détecté : {_ze_entity_type}*\n\n"
                                    f"\U0001f50d **Cause racine**\n"
                                    f"Non déterminée — les serveurs BDD/WA n'ont pas retourné de preuves.\n\n"
                                    f"\U0001f4cc **Preuves détectées**\n"
                                    f"Aucune ligne de log ni résultat DB disponible.\n\n"
                                    f"\u26a0\ufe0f **Vérifications à effectuer en accès direct**\n"
                                    f"{_ze_table_hint}"
                                    f"{_kb_fr_hint}"
                                )
                                logger.info(
                                    f"[LiveDiag][R7] Zero-evidence structured fallback "
                                    f"(intent={_live_intent}, entity={_zero_entity})"
                                )
                except Exception as _ld_e:
                    logger.warning(f"[LiveDiag] Erreur non bloquante: {_ld_e}")

            # 5b-forensic-fallback. Forensic intent when SSH/live-orch is unavailable
            # OR when the forensic handler threw an exception — reuse existing bundle evidence.
            if _early_forensic_intent and not _live_diag_response:
                _fo_entity = (_early_forensic_entity
                              or (locals().get('_raw_user_entity') or None)
                              or "?")
                _logs_actually_up = _live_logs_runtime_available(_live_orch)
                _reuse_bundle = locals().get('_live_bundle') or None

                # ── FORENSIC MEMORY: reuse persisted evidence from prior turns ──
                _reuse_trace = None
                if not _reuse_bundle and _forensic_mem:
                    _reuse_bundle = _forensic_mem.get_last_bundle()
                    _reuse_trace = _forensic_mem.get_reasoning_trace()
                    if not _fo_entity or _fo_entity == "?":
                        _mem_entity = _forensic_mem.get_entity()
                        if _mem_entity:
                            _fo_entity = _mem_entity
                    if _reuse_bundle:
                        logger.info(f"[ForensicMemory] Reusing persisted bundle for {_early_forensic_intent}")

                if _early_forensic_intent == "forensic_logs":
                    if _logs_actually_up and _reuse_bundle and _reuse_bundle.log_evidence:
                        # SSH is up — reuse already-collected log evidence from this turn
                        try:
                            from app.services.live_diagnostics.logs.log_parser import parse_log_lines
                            from app.services.live_diagnostics.logs.log_correlation_engine import (
                                format_hypotheses_for_user, log_correlation_engine as _lce2
                            )
                            _reuse_events = []
                            for _lev in _reuse_bundle.log_evidence:
                                _src = getattr(_lev, 'log_file', 'log')
                                _lines = getattr(_lev, 'matched_lines', [])
                                _reuse_events.extend(parse_log_lines(_lines, source=_src, min_score=0.20))

                            _fo_parts = [
                                f"📊 **Logs forensiques**"
                                + (f" — `{_fo_entity}`" if _fo_entity != "?" else ""),
                                "",
                            ]
                            if _reuse_events:
                                _src_groups: dict = {}
                                for _e in _reuse_events:
                                    _g = getattr(_e, 'source', 'log')
                                    _src_groups.setdefault(_g, []).append(_e)
                                for _gsrc, _gevs in _src_groups.items():
                                    _gsrc_short = _gsrc.split(':')[-1] if ':' in _gsrc else _gsrc
                                    _fo_parts.append(f"📄 **Source: `{_gsrc_short}`**")
                                    for _ge in _gevs[:8]:
                                        _fo_parts.append(_ge.to_forensic_line())
                                    _fo_parts.append("")
                                _fo_hyps = _lce2.correlate(log_events=_reuse_events)
                                if _fo_hyps:
                                    _fo_parts.append(format_hypotheses_for_user(_fo_hyps[:2]))
                            else:
                                _fo_parts.append(
                                    f"_Aucune ligne de log trouvée pour `{_fo_entity}`._"
                                )
                                if _fo_entity != "?":
                                    _fo_parts.append(
                                        f"\n**Commande SSH directe :**"
                                        f"\n```\ntail -n 500 catalina.out | grep {_fo_entity}\n```"
                                    )
                            _live_diag_response = "\n".join(_fo_parts)
                        except Exception as _rr:
                            logger.warning(f"[Forensic-Reuse] {_rr}")
                            _live_diag_response = (
                                f"📊 **Logs forensiques** — `{_fo_entity}`\n\n"
                                f"_Erreur lors de l'extraction: {_rr}_"
                            )
                    elif not _logs_actually_up:
                        # Runtime logs indisponible — fournir une guidance explicite sans prétendre
                        # avoir consulté des serveurs connectés.
                        _log_entity_part = f"pour `{_fo_entity}`" if _fo_entity != "?" else "BRASIL"
                        # Choisir la guidance selon l'entité et l'intent
                        _fo_entity_upper = str(_fo_entity).upper()
                        _is_umi_epc = any(k in _fo_entity_upper for k in ("UMI", "EPC", "UMIEPC"))
                        _is_nd = bool(re.match(r'^\d{9}$', str(_fo_entity).strip()))
                        if _is_umi_epc or "UMI" in (_early_forensic_intent or "").upper():
                            _log_guidance = (
                                "**Logs UMI-EPC — emplacements et commandes:**\n\n"
                                "| Log | Chemin | Contenu |\n"
                                "|-----|--------|---------|\n"
                                "| `umi_epc.log` | `/logs/umi-epc/app.log` | Mouvements UMI/EPC, erreurs |\n"
                                "| `catalina.out` | `/opt/tomcat/logs/catalina.out` | Logs JVM WA |\n"
                                "| `brasil_app.log` | `/logs/brasil/app.log` | Logs applicatifs |\n\n"
                                "**Commandes directes (serveur `op49mwa11`) :**\n"
                                "```bash\n"
                                f"grep -i '{_fo_entity}' /logs/umi-epc/app.log | tail -50\n"
                                "grep -i 'UMI\\|EPC\\|mouvement' /logs/brasil/app.log | tail -50\n"
                                "grep -i 'UMIEPC\\|mouvement.*UMI' /logs/was/SystemOut.log | tail -30\n"
                                "```\n\n"
                                "**Patterns d'erreurs UMI-EPC à rechercher :**\n"
                                "- `EnvoiMouvementUMIEPCException`\n"
                                "- `MouvementUMIEPCFailedException`\n"
                                "- `UMIEPC.*ERROR` / `UMIEPC.*WARN`\n"
                                "- Codes erreur: `UMI-001`, `UMI-002`, `EPC-404`"
                            )
                        elif _is_nd:
                            _log_guidance = (
                                f"**Logs pour ND `{_fo_entity}` — emplacements :**\n\n"
                                "| Log | Chemin |\n"
                                "|-----|--------|\n"
                                "| `catalina.out` | `/opt/tomcat/logs/catalina.out` |\n"
                                "| `connectorCL_{date}.log` | `/logs/brasil/connectorCL_YYYYMMDD.log` |\n"
                                "| `brasil_app.log` | `/logs/brasil/app.log` |\n\n"
                                "**Commandes directes (serveur `op49mwa11`) :**\n"
                                "```bash\n"
                                f"grep -i '{_fo_entity}' /opt/tomcat/logs/catalina.out | tail -100\n"
                                f"grep -i '{_fo_entity}' /logs/brasil/connectorCL_$(date +%Y%m%d).log | tail -50\n"
                                "```\n\n"
                                "**Rappel :** Un ND (9 chiffres) est un Noeud de Distribution, "
                                "pas un équipement. Chercher dans les tables `t_nd`, `t_tp_initial_states`, "
                                "`t_services` — pas dans `t_equipments`."
                            )
                        else:
                            _log_guidance = (
                                f"**Logs BRASIL pour `{_fo_entity}` :**\n\n"
                                "| Log | Chemin | Rôle |\n"
                                "|-----|--------|------|\n"
                                "| `catalina.out` | `/opt/tomcat/logs/catalina.out` | JVM, stack traces, exceptions |\n"
                                "| `connectorCL_{date}.log` | `/logs/brasil/connectorCL_YYYYMMDD.log` | Connecteur CL, commandes |\n"
                                "| `brasil_app.log` | `/logs/brasil/app.log` | Logs applicatifs BRASIL |\n"
                                "| `brasil_error.log` | `/logs/brasil/error.log` | Erreurs applicatives |\n"
                                "| `SystemOut.log` | `/logs/was/SystemOut.log` | WAS / WildFly |\n\n"
                                "**Commandes directes :**\n"
                                "```bash\n"
                                + (f"grep -i '{_fo_entity}' /opt/tomcat/logs/catalina.out | tail -100\n"
                                   f"grep -i '{_fo_entity}' /logs/brasil/app.log | tail -50\n"
                                   if _fo_entity != "?" else
                                   "tail -200 /opt/tomcat/logs/catalina.out\n"
                                   "grep -i 'ERROR\\|WARN\\|Exception' /logs/brasil/app.log | tail -50\n")
                                + "```\n\n"
                                "**Patterns d'erreurs critiques à chercher :**\n"
                                "- `BrasilBusinessException` / `BrasilInternalException`\n"
                                "- `ConstraintViolationException` (→ erreur 1300)\n"
                                "- `JMSException` / `MQException` (→ désync MQ)\n"
                                "- `TimeoutException` (→ opération bloquée)"
                            )
                        _live_diag_response = (
                            f"📊 **Logs forensiques {_log_entity_part}**\n\n"
                            "⚠️ **Analyse live indisponible**\n"
                            "Les serveurs de logs connectés ne sont pas disponibles pour cette requête.\n\n"
                            + _log_guidance
                        )
                    else:
                        _live_diag_response = (
                            f"📊 **Logs forensiques** — `{_fo_entity}`\n\n"
                            "_Lancer d'abord un diagnostic pour collecter les preuves, "
                            "puis demander les logs._"
                        )

                elif _early_forensic_intent == "forensic_timeline":
                    if _reuse_bundle and (_reuse_bundle.log_evidence or _reuse_bundle.db_evidence):
                        try:
                            from app.services.live_diagnostics.logs.log_parser import parse_log_lines
                            from app.services.live_diagnostics.timeline.timeline_builder import (
                                build_timeline, format_timeline_for_user
                            )
                            _tl_events = []
                            for _lev in _reuse_bundle.log_evidence:
                                _tl_events.extend(
                                    parse_log_lines(getattr(_lev, 'matched_lines', []),
                                                    source=getattr(_lev, 'log_file', 'log'))
                                )
                            _tl_res = _reuse_bundle.reasoning_trace.get("resolution_blocks", [])
                            _tl = build_timeline(
                                log_events=_tl_events,
                                db_evidence=_reuse_bundle.db_evidence,
                                fr_blocks=_tl_res,
                                entity=_fo_entity if _fo_entity != "?" else None,
                            )
                            _live_diag_response = (
                                format_timeline_for_user(_tl[:12]) if _tl
                                else "⏱ **Timeline**\n\n_Aucun événement reconstituable._"
                            )
                        except Exception as _te:
                            _live_diag_response = f"⏱ **Timeline**\n\n_Erreur: {_te}_"
                    else:
                        _live_diag_response = (
                            "⏱ **Timeline d'incident**\n\n"
                            "_Lancer d'abord un diagnostic pour collecter les preuves._"
                        )

                elif _early_forensic_intent == "forensic_evidence":
                    # Use the new forensic follow-up handler for all evidence-type intents
                    try:
                        from app.services.chatbot.forensic_followup import forensic_followup_handler
                        _cached_trace = _reuse_bundle.reasoning_trace if _reuse_bundle else None
                        _live_diag_response = forensic_followup_handler.handle(
                            forensic_intent=_early_forensic_intent,
                            entity=_fo_entity if _fo_entity != "?" else None,
                            cached_trace=_cached_trace,
                            cached_bundle=_reuse_bundle,
                        )
                    except Exception:
                        _live_diag_response = (
                            "🔍 **Runtime Evidence**\n\n"
                            + ("_Lancer d'abord un diagnostic pour collecter les preuves live._"
                               if not _reuse_bundle
                               else "\n".join(
                                   f"- {b.get('title','?')}: {b.get('content','')[:150]}"
                                   for b in (_reuse_bundle.to_context_blocks() if _reuse_bundle else [])[:5]
                               ) or "_Aucune preuve disponible._")
                        )

                # ── Generic forensic follow-up handler for all expanded intents ──
                elif _early_forensic_intent not in ("forensic_logs", "forensic_timeline", "forensic_evidence"):
                    # Workflow intent → use WorkflowIntelligenceEngine first
                    if _early_forensic_intent == "forensic_workflow":
                        try:
                            from app.services.chatbot.workflow_intelligence import workflow_engine
                            _wf_op = None
                            _wf_ent = None
                            if _semantic_route:
                                # Use semantic router context if available
                                pass
                            _wf_response = workflow_engine.render_workflow_response(
                                query=message.content,
                                entity=_fo_entity if _fo_entity != "?" else None,
                            )
                            _live_diag_response = _wf_response
                        except Exception as _wf_err:
                            logger.debug(f"[WorkflowIntelligence] {_wf_err}")
                    if not _live_diag_response:
                        try:
                            from app.services.chatbot.forensic_followup import forensic_followup_handler
                            _cached_trace = _reuse_bundle.reasoning_trace if _reuse_bundle else None
                            _live_diag_response = forensic_followup_handler.handle(
                                forensic_intent=_early_forensic_intent,
                                entity=_fo_entity if _fo_entity != "?" else None,
                                cached_trace=_cached_trace,
                                cached_bundle=_reuse_bundle,
                            )
                        except Exception as _ffh_err:
                            logger.warning(f"[ForensicFollowup] Error: {_ffh_err}")
                            _live_diag_response = (
                                f"🔍 **{_early_forensic_intent}** — `{_fo_entity}`\n\n"
                                f"_Lancer d'abord un diagnostic pour collecter les preuves._"
                            )

                logger.info(
                    f"[Forensic-Fallback] intent={_early_forensic_intent} entity={_fo_entity} "
                    f"logs={_logs_actually_up} bundle={'yes' if _reuse_bundle else 'no'}"
                )

            # 5b-bis. Multi-Source Correlation injection
            # ── N3 LAYER 5: Full Correlation Engine ───────────────────────────
            # ENFORCER FIX 1: correlation runs ALWAYS — not gated on _live_diag_response
            _n3_correlation = None
            if _N3_INTEGRATION_AVAILABLE and _N3_CORR_ON:
                try:
                    _live_log_ev = []
                    if '_live_bundle' in dir() and _live_bundle and getattr(_live_bundle, 'log_evidence', None):
                        for _lev in _live_bundle.log_evidence:
                            _live_log_ev.append({
                                "content": "\n".join(getattr(_lev, 'matched_lines', [])[:20]),
                                "source_type": "live_log",
                                "log_file": getattr(_lev, 'log_file', 'log'),
                            })
                    _live_db_ev = []
                    if '_live_bundle' in dir() and _live_bundle and getattr(_live_bundle, 'db_evidence', None):
                        for _qname, _dbev in (_live_bundle.db_evidence or {}).items():
                            if getattr(_dbev, 'has_data', False):
                                _live_db_ev.append({
                                    "content": str(getattr(_dbev, 'rows', [])[:5]),
                                    "source_type": "live_db",
                                    "query_name": _qname,
                                })
                    _n3_correlation = _n3_correlate(
                        query=message.content,
                        context_blocks=orch_result.get('context_blocks', []) or [],
                        live_db_evidence=_live_db_ev,
                        live_log_evidence=_live_log_ev,
                        jira_tickets=orch_result.get('jira_tickets', []) or [],
                        intent=locals().get('_live_intent') or locals().get('_early_forensic_intent') or '',
                        conv_state=conv_state if '_NLP_AVAILABLE' in dir() and _NLP_AVAILABLE else None,
                    )
                    if _n3_correlation and _n3_correlation.hypotheses_block:
                        if system_prompt:
                            system_prompt = system_prompt + '\n\n' + _n3_correlation.hypotheses_block
                        logger.info(
                            f"[N3Integration][L5] Correlation: top={_n3_correlation.top_hypothesis}, "
                            f"conf={_n3_correlation.confidence:.2f}, ev={_n3_correlation.evidence_count}"
                        )
                except Exception as _n3c_err:
                    logger.debug(f"[N3Integration][L5] skipped: {_n3c_err}")

            # ── N3 LAYER 7: Response Generator (structured LLM context) ───────
            if _N3_INTEGRATION_AVAILABLE and _N3_RESP_ON and _n3_correlation and _n3_correlation.raw_result and not _live_diag_response:
                try:
                    _l7_context = _n3_build_llm_context(
                        query=message.content,
                        intent=locals().get('_live_intent') or locals().get('_early_forensic_intent') or '',
                        correlation_raw_result=_n3_correlation.raw_result,
                        conv_state=conv_state if '_NLP_AVAILABLE' in dir() and _NLP_AVAILABLE else None,
                    )
                    if _l7_context and system_prompt:
                        # Replace raw KB dump with structured deterministic context
                        system_prompt = _l7_context
                        logger.info("[N3Integration][L7] ResponseGenerator injected structured context")
                except Exception as _l7_err:
                    logger.debug(f"[N3Integration][L7] skipped: {_l7_err}")

            # ── Legacy MSC (kept as fallback if L5 produced nothing) ──────────
            if _MSC_AVAILABLE and _msc is not None and not (_n3_correlation and _n3_correlation.hypotheses_block):
                try:
                    _jira_list = orch_result.get('jira_tickets', []) or []
                    _log_list  = orch_result.get('log_entries', []) or []
                    # FIX: populate log_entries from live bundle if available
                    if not _log_list and '_live_bundle' in dir() and _live_bundle:
                        for _lev in (getattr(_live_bundle, 'log_evidence', None) or []):
                            _matched = getattr(_lev, 'matched_lines', [])
                            if _matched:
                                _log_list.append({
                                    "content": "\n".join(_matched[:10]),
                                    "source": getattr(_lev, 'log_file', 'live'),
                                    "level": "INFO",
                                })
                    # ENFORCER FIX 3: log empty MSC sources
                    _msc_empty = []
                    if not _jira_list: _msc_empty.append('jira')
                    if not _log_list:  _msc_empty.append('logs')
                    if _msc_empty:
                        logger.warning(f'[Pipeline][MSC] Empty sources passed to correlator: {_msc_empty}')
                    _diag_dict = diagnostic_result.__dict__ if 'diagnostic_result' in dir() and diagnostic_result else {}
                    _ml_dict   = orch_result.get('ml_result', {}) or {}
                    _kb_blocks = orch_result.get('context_blocks', []) or []
                    _hypotheses = _msc.correlate(
                        user_message=message.content,
                        kb_blocks=_kb_blocks,
                        jira_tickets=_jira_list,
                        log_entries=_log_list,
                        diagnostic=_diag_dict,
                        ml_result=_ml_dict,
                    )
                    _corr_block = _msc.to_context_block(_hypotheses)
                    if _corr_block and system_prompt:
                        system_prompt = system_prompt + '\n\n' + _corr_block
                except Exception as _corr_err:
                    logger.debug(f'[Correlator] skipped: {_corr_err}')

            # 5. Appel LLM - ou bypass si diagnostic deterministe
            # FIX #11: Skip LLM when deterministic response is available
            if _live_diag_response:
                response_text = _live_diag_response
                thinking_content = None
                logger.info("[Chatbot] LLM SKIPPED - deterministic live diagnostic response used")
            else:
                llm_result = await self.llm.generate(
                    prompt=full_prompt,
                    system_prompt=system_prompt,
                    with_thinking=True,
                )
                if isinstance(llm_result, tuple):
                    response_text, thinking_content = llm_result
                else:
                    response_text, thinking_content = llm_result, None

            # 5b. Post-processing anti-hallucination
            # Strip ## Raisonnement / Thinking sections leaked by the LLM
            response_text = re.sub(
                r'(?m)^#{1,3}\s*(?:Raisonnement|Thinking|R\u00e9flexion|Analyse\s+interne)[^\n]*\n[\s\S]*?(?=\n#{1,3}\s|\Z)',
                '', response_text
            ).strip()
            # Collect legitimate IDs from ALL available sources:
            #   • KB context blocks  • Jira ticket results  • conversation history
            _src_ids: set = set()
            # KB blocks
            for _blk in orch_result.get('context_blocks', []):
                _blk_str = str(_blk)
                for _m in re.finditer(r'BRASIL-[A-Z]+-\d{3}', _blk_str):
                    _src_ids.add(_m.group())
                for _m in re.finditer(r'\bFR[-_]?\d{3,6}\b', _blk_str):
                    _src_ids.add(_m.group())
                # Generic Jira-style IDs in KB text
                for _m in re.finditer(r'\b[A-Z]{2,6}-\d{3,6}\b', _blk_str):
                    _src_ids.add(_m.group())
            # Jira results from orchestrator
            for _tkt in orch_result.get('jira_tickets', []):
                _tkt_str = str(_tkt)
                for _m in re.finditer(r'\b[A-Z]{2,6}-\d{3,6}\b', _tkt_str):
                    _src_ids.add(_m.group())
            # Conversation history — IDs the user themselves mentioned are valid
            for _hmsg in (history or []):
                for _m in re.finditer(r'\b[A-Z]{2,6}-\d{3,6}\b', str(_hmsg.get('content', ''))):
                    _src_ids.add(_m.group())
            # IDs in the user's current message are always valid
            for _m in re.finditer(r'\b[A-Z]{2,6}-\d{3,6}\b', message.content):
                _src_ids.add(_m.group())

            def _strip_invented_brasil(m):
                return m.group() if m.group() in _src_ids else '[ID-proc]'
            response_text = re.sub(r'BRASIL-[A-Z]+-\d{3}', _strip_invented_brasil, response_text)

            def _strip_invented_fr(m):
                return m.group() if m.group() in _src_ids else '[FR-ref]'
            response_text = re.sub(r'\bFR[-_]?\d{4,6}\b', _strip_invented_fr, response_text)

            # Generic Jira-style IDs: only strip if NOT in any validated source
            def _strip_invented_jira_id(m):
                return m.group() if m.group() in _src_ids else m.group()  # keep; flag only BRASIL/FR above
            # (Jira IDs like BRAS-1001 are kept as-is; only BRASIL-XYZ-NNN and FR-NNNN are stripped)

            # FIX #5 + F8: Strip generic support phrases AND generic AI chatbot language
            # Applied in N3 mode: whenever live diag is configured, or forensic intent was triggered,
            # or any live/deterministic response was generated.
            _n3_mode_active = (
                _LIVE_DIAG_AVAILABLE
                or bool(_early_forensic_intent)
                or _live_bundle is not None
                or _live_diag_response is not None
            )
            if _n3_mode_active:
                _BANNED_PHRASES = [
                    r"(?i)contact(?:ez|er)?\s+(?:le\s+)?(?:support|l'(?:e|é)quipe|l'administration)",
                    r"(?i)fournir?\s+(?:des\s+)?(?:logs?|captures?|d(?:e|é)tails?|informations?)",
                    r"(?i)capture[s]?\s+d'(?:e|é)cran",
                    r"(?i)droits?\s+(?:administratif|admin)",
                    r"(?i)investigation\s+manuelle",
                    r"(?i)n'h(?:e|é)sitez\s+pas\s+(?:a|à)\s+me\s+donner",
                    r"(?i)plus\s+de\s+d(?:e|é)tails?\s+sur\s+le\s+contexte",
                    r"(?i)probl(?:e|è)me\s+de\s+configuration",
                    r"(?i)d(?:e|é)pendance[s]?\s+non\s+r(?:e|é)solue",
                    # F8: Generic AI chatbot phrases — never appropriate in N3 diagnostic mode
                    # Note: [''\u2019] matches both ASCII apostrophe and Unicode right single quote
                    r"(?i)merci\s+pour\s+votre\s+(?:confiance|question|message|patience)[^.\n]*[.\n]?",
                    r"(?i)[n\u006e][\u2019']h(?:e|\u00e9)sitez\s+pas\s+[a\u00e0]\s+(?:me\s+)?(?:contacter|revenir|poser|donner)[^.\n]*[.\n]?",
                    r"(?i)je\s+suis\s+(?:l[a\u00e0]\s+pour|disponible\s+pour)\s+vous\s+aider[^.\n]*[.\n]?",
                    r"(?i)avez-vous\s+d[\u2019']autres?\s+questions[^?\n]*[?.\n]?",
                    r"(?i)puis-je\s+vous\s+aider\s+(?:avec\s+autre\s+chose|autrement)[^?\n]*[?.\n]?",
                    r"(?i)j[\u2019']esp[e\u00e8]re\s+(?:que\s+)?(?:cela|\u00e7a)\s+(?:vous\s+)?(?:aide|r\u00e9pond)[^.\n]*[.\n]?",
                    r"(?i)dites-moi\s+si\s+(?:la|le|l[\u2019'])(?:\s+\w+){0,6}\s+(?:a\s+bien|a\s+fonctionn)[^.\n]*[.\n]?",
                    r"(?i)nous\s+pourrons?\s+passer\s+[a\u00e0]\s+la\s+cl[o\u00f4]ture[^.\n]*[.\n]?",
                    r"(?i)bonne\s+(?:continuation|journ[e\u00e9]e|chance)[^.\n]*[.\n]?",
                    r"(?i)cordialement[,\s][^\n]*\n?",
                    r"(?i)en\s+tant\s+qu[\u2019']assistant[^.\n]*[.\n]?",
                ]
                for _bp in _BANNED_PHRASES:
                    response_text = re.sub(_bp + r"[^.\n]*[.\n]?", "", response_text)
                # Remove orphan empty lines from stripping
                response_text = re.sub(r"\n{3,}", "\n\n", response_text).strip()

            if not _live_diag_response:
                _ctx_blocks_for_guard = orch_result.get("context_blocks", []) or []
                _res_blocks_for_guard = []
                if _live_bundle and getattr(_live_bundle, "reasoning_trace", None):
                    _res_blocks_for_guard = (
                        _live_bundle.reasoning_trace.get("resolution_blocks", []) or []
                    )
                elif "_resolution_blocks" in locals():
                    _res_blocks_for_guard = locals().get("_resolution_blocks", []) or []

                response_text = _sanitize_llm_response_actions_with_context(
                    response_text,
                    context_blocks=_ctx_blocks_for_guard,
                    resolution_blocks=_res_blocks_for_guard,
                )

            # ── Response quality cleanup (Phase 7 hardened) ───────────────────
            try:
                from app.services.chatbot.response_quality import full_quality_check
                response_text = full_quality_check(response_text)
            except ImportError:
                try:
                    from app.services.chatbot.response_quality import clean_llm_response, strip_sql_hallucinations
                    response_text = clean_llm_response(response_text)
                    response_text = strip_sql_hallucinations(response_text)
                except ImportError:
                    pass

            # ── SQL identifier protection (indexed-schema only) ───────────────
            response_text = _protect_unindexed_sql_identifiers(response_text)

            # ── Truth Enforcement (Phase 1) ───────────────────────────────────
            # Run AFTER quality cleanup. Uses lenient mode (only block mutations/shells)
            # on LLM-generated responses; strict mode on deterministic responses.
            try:
                from app.services.chatbot.truth_enforcement import (
                    truth_engine, truth_engine_lenient
                )
                _te = truth_engine if _live_diag_response else truth_engine_lenient
                _te_ctx = _reasoning_trace if '_reasoning_trace' in dir() else None
                _truth_report = _te.enforce(response_text, context=_te_ctx)
                response_text = _truth_report.clean_text
                if _truth_report.has_violations:
                    logger.info(
                        f"[TruthEnforcement] {_truth_report.violation_count} violation(s) blocked"
                    )
            except Exception as _te_err:
                logger.debug(f"[TruthEnforcement] skipped: {_te_err}")

            # ── N3 LAYER 6: Validation Layer (post-LLM anti-hallucination) ────
            # ENFORCER FIX 2: validation runs ALWAYS — not gated on _live_diag_response
            if _N3_INTEGRATION_AVAILABLE and _N3_VAL_ON:
                try:
                    _n3_val = _n3_validate(
                        response_text=response_text,
                        query=message.content,
                        intent=locals().get('_live_intent') or locals().get('_early_forensic_intent') or '',
                        context_blocks=orch_result.get('context_blocks', []) or [],
                        correlation_confidence=(_n3_correlation.confidence if _n3_correlation else 0.0),
                        conv_state=conv_state if _NLP_AVAILABLE else None,
                    )
                    if _n3_val and not _n3_val.passed and _n3_val.safe_response:
                        logger.info(
                            f"[N3Integration][L6] Validation BLOCKED: tier={_n3_val.tier}, "
                            f"violations={_n3_val.violations[:2]}"
                        )
                        response_text = _n3_val.safe_response
                    elif _n3_val and _n3_val.violations:
                        logger.info(
                            f"[N3Integration][L6] Validation warnings: {_n3_val.violations[:2]}"
                        )
                except Exception as _n3v_err:
                    logger.debug(f"[N3Integration][L6] skipped: {_n3v_err}")

            # ── Provenance footer (Phase 3) — append only when real live evidence ──
            # N'affiche le footer que si on a des preuves DB/log/SSH réelles
            # (pas uniquement vector_knowledge qui nuit à la lisibilité)
            if _live_diag_response and _early_forensic_intent:
                try:
                    from app.services.chatbot.provenance_engine import make_provenance_engine
                    _prov_eng = make_provenance_engine()
                    if '_live_bundle' in dir() and _live_bundle:
                        _prov_eng.add_from_bundle(_live_bundle)
                    # N'ajouter les blocs KB (vector_knowledge) que si on a déjà des preuves live
                    _has_live_evidence = _has_real_live_evidence(_live_bundle)
                    if _has_live_evidence and orch_result.get("context_blocks"):
                        _prov_eng.add_from_kb_blocks(orch_result["context_blocks"][:3])
                    # Filtrer : ne rendre le footer que si sources autres que vector_knowledge
                    _prov_footer = _prov_eng.render_footer(max_records=4)
                    _SKIP_IF_ONLY_VECTOR = not _has_live_evidence
                    if _prov_footer and not _SKIP_IF_ONLY_VECTOR and len(response_text) < 3000:
                        response_text = response_text + "\n" + _prov_footer
                except Exception as _prov_err:
                    logger.debug(f"[Provenance] skipped: {_prov_err}")

            # FIX #1: Entity name protection — never replace user's entity with something else
            if '_raw_user_entity' in dir() and _raw_user_entity:
                # Prevent the LLM from replacing DSROB362 with DSLAM_01 etc.
                _HALLUCINATED_NAMES = ["DSLAM_01", "DSLAM_02", "EQUIPMENT_01", "EQP_TEST"]
                for _hn in _HALLUCINATED_NAMES:
                    if _hn in response_text and _hn not in message.content:
                        response_text = response_text.replace(_hn, _raw_user_entity)

            # 5c. Human interaction layer — make response natural and collaborative
            # SKIP in N3 mode: deterministic/forensic responses must not be "humanized"
            # (humanizer adds generic endings like "Dites-moi si..." that are banned in N3)
            _skip_humanizer = (
                _live_diag_response is not None   # deterministic response already set
                or bool(_early_forensic_intent)   # forensic command was dispatched
                or _live_bundle is not None        # live DB evidence was used
            )
            if _HUMANIZER_AVAILABLE and not _skip_humanizer:
                try:
                    _h_ctx = HumanizeContext(
                        has_error_code=bool(structured_ticket and structured_ticket.error_codes) if _NLP_AVAILABLE and structured_ticket else False,
                        has_procedure_steps=bool(re.search(r'^\s*[1-9]\.\s', response_text, re.MULTILINE)),
                        phase=conv_state.phase.value if _NLP_AVAILABLE and conv_state else "diagnostic",
                        error_code=(structured_ticket.error_codes[0] if _NLP_AVAILABLE and structured_ticket and structured_ticket.error_codes else ""),
                        entity=app_ctx.get("display_name", "") if app_ctx else "",
                    )
                    response_text = humanize(response_text, _h_ctx)
                except Exception as _hum_err:
                    logger.debug(f"[Humanizer] skipped: {_hum_err}")

            # 5d. Final banned-phrase sweep — runs AFTER humanizer to catch anything added
            # Applied in N3 mode regardless of whether humanizer ran
            if _n3_mode_active:
                _FINAL_BANNED = [
                    r"(?i)[n\u006e][\u2019\x27]h(?:e|\xe9)sitez\s+pas\s+[a\xe0]\s+(?:me\s+)?(?:contacter|revenir|poser|donner)[^\.\n]*[\.\n]?",
                    r"(?i)dites-moi\s+si\s+(?:la|le|l[\u2019\x27])(?:\s+\w+){0,6}\s+(?:a\s+bien|a\s+fonctionn)[^\.\n]*[\.\n]?",
                    r"(?i)nous\s+pourrons?\s+passer\s+[a\xe0]\s+la\s+cl[o\xf4]ture[^\.\n]*[\.\n]?",
                    r"(?i)merci\s+pour\s+votre\s+(?:confiance|question|message|patience)[^\.\n]*[\.\n]?",
                    r"(?i)avez-vous\s+d[\u2019\x27]autres?\s+questions[^?\n]*[?.\n]?",
                    r"(?i)puis-je\s+vous\s+aider\s+(?:avec\s+autre\s+chose|autrement)[^?\n]*[?.\n]?",
                    r"(?i)bonne\s+(?:continuation|journ[e\xe9]e|chance)[^\.\n]*[\.\n]?",
                    r"(?i)cordialement[,\s][^\n]*\n?",
                ]
                for _fb in _FINAL_BANNED:
                    response_text = re.sub(_fb, "", response_text)
                response_text = re.sub(r"\n{3,}", "\n\n", response_text).strip()

            # 5e. Record forensic snapshot for cross-turn memory
            if _forensic_mem and (_live_bundle or _early_forensic_intent):
                try:
                    _fm_exceptions = []
                    _fm_trace = locals().get('_reasoning_trace', {})
                    _fm_forensic = _fm_trace.get('forensic_summary', {}) if isinstance(_fm_trace, dict) else {}
                    if isinstance(_fm_forensic, dict):
                        _fm_exceptions = _fm_forensic.get('exception_chain', [])
                    _forensic_mem.record_diagnostic(
                        turn_idx=conv_state.turn_count if conv_state else 0,
                        intent=_early_forensic_intent or locals().get('_live_intent', ''),
                        entity=locals().get('_raw_user_entity', '') or _early_forensic_entity,
                        operation=locals().get('_live_intent', ''),
                        reasoning_trace=_fm_trace if isinstance(_fm_trace, dict) else {},
                        bundle=_live_bundle,
                        exceptions=_fm_exceptions,
                    )
                except Exception as _fm_err:
                    logger.debug(f"[ForensicMemory] Record error: {_fm_err}")

            # 6. Extraire trust
            trust_score_obj = orch_result.get("trust_score")
            trust_score = trust_score_obj.score if trust_score_obj else 0
            trust_label = trust_score_obj.label.value if trust_score_obj else "insufficient"

            # 7. Construire les sources ÔÇö normalisation pour le frontend
            raw_sources = orch_result.get("sources", [])
            sources = []
            for s in raw_sources:
                # R├®soudre le nom affich├®
                name = (
                    s.get("name")
                    or s.get("title")
                    or s.get("source_id")
                    or s.get("id")
                    or "Source inconnue"
                )
                # R├®soudre le type affich├®
                src_type = (
                    s.get("type")
                    or s.get("source_type")
                    or ("resolution_fiche" if s.get("source_fr_numbers") else "procedure")
                )
                # Construire un contenu court pour le "cite in chat"
                fr_nums = s.get("source_fr_numbers") or []
                content_snippet = s.get("content") or (
                    f"FR : {', '.join(fr_nums)}" if fr_nums else ""
                )
                sources.append({
                    **s,
                    "name": name,
                    "type": src_type,
                    "content_snippet": content_snippet,
                    "relevance": round(s.get("trust_score", 0) / 100, 2) if s.get("trust_score") else s.get("score", 0),
                })

            # ── TruthGate (strict) for forensic / RCA / summaries ─────────────
            _strict_intents = {
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
                "generate_n3_summary",
                "generate_rca",
            }
            _intent_for_truth_gate = (
                locals().get("_early_forensic_intent")
                or locals().get("_live_intent")
                or ""
            )
            _reasoning_for_truth = locals().get("_reasoning_trace", {}) or {}
            if _intent_for_truth_gate in _strict_intents:
                if not self._response_has_evidence(response_text, sources, locals().get("_live_bundle"), _reasoning_for_truth):
                    response_text = NO_EVIDENCE_MESSAGE
                    sources = []

            # 8. Suggestions selon le mode
            suggestions = self._build_suggestions(orch_result.get("mode", ""), guard)

            logger.info(
                f"[Chatbot] Reponse generee - mode={orch_result.get('mode')}, "
                f"trust={trust_score}/100, sources={len(sources)}"
            )

            # 9. Auto-trigger validation N3 si trust insuffisant
            if db is not None:
                try:
                    from app.services.validation.validation_service import ValidationService as _ValSvc
                    _inc_type = (
                        structured_ticket.incident_type
                        if structured_ticket else "unknown"
                    )
                    _app = app_ctx.get("display_name", message.app_id) or message.app_id
                    task_id = _ValSvc(db).create_chatbot_task(
                        user_question   = message.content,
                        bot_response    = response_text,
                        trust_score     = trust_score / 100,
                        incident_type   = _inc_type,
                        application     = _app,
                        conversation_id = conversation_id,
                    )
                    if task_id:
                        logger.info(
                            f"[Chatbot][Validation] T├óche N3 cr├®├®e: #{task_id} "
                            f"(trust={trust_score}/100, inc={_inc_type})"
                        )
                except Exception as _ve:
                    logger.debug(f"[Chatbot][Validation] Skip auto-task: {_ve}")

            # ── N3 LAYER 8: Learning Loop — record interaction ────────────────
            if _N3_INTEGRATION_AVAILABLE and _N3_LEARN_ON:
                try:
                    _n3_record(
                        session_id=conversation_id,
                        query=message.content,
                        response=response_text,
                        intent=locals().get('_live_intent') or locals().get('_early_forensic_intent') or '',
                        entity=locals().get('_raw_user_entity') or '',
                        confidence=trust_score / 100,
                        evidence_count=len(sources),
                        hypothesis=(_n3_correlation.top_hypothesis if _n3_correlation else '') or '',
                        resolution_confirmed=getattr(conv_state, 'resolution_confirmed', False) if conv_state else False,
                        conv_state=conv_state if _NLP_AVAILABLE else None,
                    )
                except Exception as _n3l_err:
                    logger.warning(f"[N3Integration][L8] Learning record failed: {_n3l_err}")

            # ── ENFORCER FIX 5: Pipeline audit log ───────────────────────────
            if _PIPELINE_ENFORCER_AVAILABLE:
                try:
                    _pa = PipelineAudit(
                        session_id=conversation_id,
                        message=message.content[:80],
                    )
                    _pa.intent_ran      = True
                    _pa.retrieval_ran   = True
                    _pa.correlation_ran = _n3_correlation is not None
                    _pa.evidence_built  = _n3_correlation is not None
                    _pa.llm_ran         = _live_diag_response is None
                    _pa.validation_ran  = _N3_VAL_ON
                    _pa.learning_ran    = _N3_LEARN_ON
                    _pa.fr_count        = len(orch_result.get('context_blocks', []) or [])
                    _pa.jira_count      = len(orch_result.get('jira_tickets', []) or [])
                    _pa.log_count       = len(getattr(_live_bundle, 'log_evidence', None) or []) if '_live_bundle' in dir() and _live_bundle else 0
                    _pa.db_count        = len(getattr(_live_bundle, 'db_evidence', None) or {}) if '_live_bundle' in dir() and _live_bundle else 0
                    _pa.hypothesis_count = len(getattr(_n3_correlation, 'hypotheses_block', '') or '')
                    _pa.correlation_score = getattr(_n3_correlation, 'confidence', 0.0) if _n3_correlation else 0.0
                    _pa.audit(trust_score=trust_score, response_length=len(response_text), pipeline_mode=orch_result.get("mode"))
                except Exception as _pa_err:
                    logger.debug(f"[Pipeline][Audit] skipped: {_pa_err}")

            return ChatResponse(
                message=response_text,
                sources=sources,
                suggestions=suggestions,
                confidence=trust_score / 100,
                conversation_id=conversation_id,
                app_id=message.app_id,
                pipeline_mode=orch_result.get("mode"),
                trust_score=trust_score,
                trust_label=trust_label,
                diagnostic_available=guard.get("can_diagnose", False),
                thinking_content=thinking_content or None,
                follow_up_message=_follow_up_message or None,
                # Diagnostic engine enrichment
                procedure_id=(
                    diagnostic_result.procedure_id
                    if diagnostic_result and diagnostic_result.is_usable()
                    else None
                ),
                exceptions_detected=(
                    diagnostic_result.exceptions_matched
                    if diagnostic_result and diagnostic_result.exceptions_matched
                    else []
                ),
            )

        except Exception as e:
            logger.error(f"[Chatbot] Erreur dans process_message: {e}")
            raise

    # -----------------------------------------------------------------------
    # Conversation State Machine
    # -----------------------------------------------------------------------

    def _reconstruct_state(self, history: List[Dict]) -> "ConversationState":
        """
        Rebuild ConversationState from the conversation history.
        The last assistant message may carry a JSON state blob in a hidden
        metadata field; if not found we reconstruct from text heuristics.
        """
        if not _NLP_AVAILABLE:
            return ConversationState()  # type: ignore[call-arg]

        # Try to find a serialised state in the last assistant message
        for msg in reversed(history or []):
            if msg.get("role") != "assistant":
                continue
            content = msg.get("content", "")
            # State blob is stored as <!-- STATE:{...} --> in the content
            m = re.search(r"<!--\s*STATE:(\{.*?\})\s*-->", content, re.DOTALL)
            if m:
                try:
                    return ConversationState.from_json(m.group(1))
                except Exception:
                    pass
            break

        # Fallback: reconstruct phase from history keywords
        state = ConversationState()
        for msg in history or []:
            text = msg.get("content", "")
            new_phase = detect_phase_transition(state.phase, text)
            if new_phase:
                state.phase = new_phase
            # Lock root cause if found in history
            if state.confirmed_root_cause is None:
                rc = extract_root_cause(text)
                if rc:
                    state.confirmed_root_cause = rc
                    state.resolution_confirmed = True
        return state

    # -----------------------------------------------------------------------
    # Phase CLOSING ÔÇö no RAG, root-cause-locked closing message generator
    # -----------------------------------------------------------------------

    async def _handle_summarize_intent(
        self,
        message: "ChatMessage",
        history: List[Dict],
        conversation_id: str,
    ) -> "ChatResponse":
        """
        Generates a structured management summary from conversation history only.
        NO RAG retrieval, NO new hypotheses, NO invented procedure IDs.
        Triggered when intent_override == "summarize".
        """
        app_name = message.app_id

        # Build a readable history text for the LLM
        history_text = ""
        for turn in (history or []):
            role = turn.get("role", "")
            content = turn.get("content", "")
            if role == "user":
                history_text += f"[Technicien] {content}\n\n"
            elif role == "assistant":
                history_text += f"[Assistant] {content}\n\n"

        if not self._history_has_verifiable_evidence(history_text):
            return ChatResponse(
                message=NO_EVIDENCE_MESSAGE,
                thinking_content=None,
                sources=[],
                suggestions=[
                    "Relancer un diagnostic avec logs/DB/code/FR disponibles",
                    "Vérifier la disponibilité des sources runtime",
                    "Régénérer le résumé après collecte de preuves",
                ],
                confidence=0.0,
                conversation_id=conversation_id,
                app_id=message.app_id,
                pipeline_mode="SUMMARIZE_MANAGEMENT",
                trust_score=0,
                trust_label="no_evidence",
                diagnostic_available=False,
            )

        system_prompt = (
            f"Tu es un assistant support N3 pour l'application {app_name} (Orange Telecom).\n"
            f"L'ing├®nieur demande un r├®sum├® structur├® de la situation pour le communiquer ├á sa hi├®rarchie.\n\n"
            f"R├êGLES ABSOLUES :\n"
            f"1. Utilise UNIQUEMENT les informations pr├®sentes dans l'historique ci-dessous.\n"
            f"2. Ne g├®n├¿re AUCUNE nouvelle hypoth├¿se, proc├®dure ou requ├¬te SQL.\n"
            f"3. Ne mentionne AUCUN syst├¿me informatique absent de l'historique.\n"
            f"4. Ne g├®n├¿re JAMAIS d'identifiant de proc├®dure invent├® (ex: BRASIL-PROC-XXXX).\n"
            f"5. Structure en 4 sections num├®rot├®es :\n"
            f"   1. Situation client (qui, quoi, quand)\n"
            f"   2. Anomalies d├®tect├®es (sympt├┤mes observ├®s)\n"
            f"   3. Diagnostic (cause racine identifi├®e ou suspect├®e)\n"
            f"   4. Actions recommand├®es / statut escalade\n"
            f"6. Ton professionnel, concis (10 lignes max). R├®ponds uniquement en fran├ºais.\n\n"
            f"HISTORIQUE DE LA CONVERSATION :\n"
            f"{history_text}"
        )

        prompt = f"G├®n├¿re le r├®sum├® pour la hi├®rarchie."

        try:
            llm_result = await self.llm.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                with_thinking=True,
            )
            if isinstance(llm_result, tuple):
                response_text, thinking_content = llm_result
            else:
                response_text, thinking_content = llm_result, None
        except Exception as e:
            logger.error(f"[Summarize] LLM error: {e}")
            response_text = (
                "Je n'ai pas pu g├®n├®rer le r├®sum├®. "
                "Veuillez r├®essayer ou r├®diger manuellement un r├®sum├® bas├® sur l'historique."
            )
            thinking_content = None

        return ChatResponse(
            message=response_text,
            thinking_content=thinking_content,
            sources=[],
            suggestions=[
                "Envoyer ce r├®sum├® par email au N+1",
                "Cr├®er un ticket de suivi",
                "Escalader vers l'├®quipe sp├®cialis├®e si non r├®solu",
            ],
            confidence=1.0,
            conversation_id=conversation_id,
            app_id=message.app_id,
            pipeline_mode="SUMMARIZE_MANAGEMENT",
            trust_score=90,
            trust_label="history_based",
            diagnostic_available=False,
        )

    async def _handle_closing_phase(
        self,
        message: "ChatMessage",
        conv_state: "ConversationState",
        conversation_id: str,
        history: List[Dict],
        db=None,
    ) -> "ChatResponse":
        """
        Generates a closing message without any RAG retrieval.
        Uses only the confirmed root cause and conversation history.
        Phase 6: also injects a structured technical report + depositor message
        built by response_humanizer.build_resolution_summary().
        """
        audience = conv_state.audience or "depositor"
        root_cause = (
            conv_state.confirmed_root_cause
            or extract_root_cause(message.content)
            or "cause identifiée au cours de l'investigation"
        )
        procedure = conv_state.confirmed_procedure_id or "procédure manuelle"
        app_name = message.app_id

        # Phase 6 — Build structured resolution data
        resolution_summary: dict = {"technical": "", "depositor": ""}
        if _HUMANIZER_AVAILABLE:
            try:
                _res_data = build_resolution_data_from_state(
                    conv_state=conv_state,
                    history=history,
                    application=app_name,
                )
                _res_data.root_cause = root_cause
                resolution_summary = build_resolution_summary(_res_data)
            except Exception as _rs_err:
                logger.debug(f"[ResolutionSummary] skipped: {_rs_err}")

        _closing_evidence_text = "\n".join(m.get("content", "") for m in (history or []))
        if resolution_summary.get("technical"):
            _closing_evidence_text += "\n" + resolution_summary["technical"]
        if not self._history_has_verifiable_evidence(_closing_evidence_text):
            return ChatResponse(
                message=NO_EVIDENCE_MESSAGE,
                sources=[],
                suggestions=[
                    "Confirmer les preuves logs/DB/code/FR avant clôture",
                    "Relancer un diagnostic live",
                    "Rejouer la synthèse une fois les preuves disponibles",
                ],
                confidence=0.0,
                conversation_id=conversation_id,
                app_id=message.app_id,
                pipeline_mode="CLOSING",
                trust_score=0,
                trust_label="no_evidence",
                diagnostic_available=False,
            )

        closing_system_prompt = (
            f"{PERSONA_INSTRUCTION}\n"
            f"🔒 MODE CLÔTURE — AUCUN DIAGNOSTIC, AUCUNE RECHERCHE KB.\n\n"
            f"INCIDENT TRAITÉ :\n"
            f"- Application : {app_name}\n"
            f"- Cause racine confirmée : {root_cause}\n"
            f"- Procédure appliquée : {procedure}\n\n"
            f"AUDIENCE : {audience}\n\n"
            f"INSTRUCTIONS — génère DEUX sections distinctes :\n"
            f"  SECTION 1 — Résumé technique N3 (pour les archives) :\n"
            f"    Incident | Cause racine | Action effectuée | Résultat\n"
            f"  SECTION 2 — Message pour le dépositaire :\n"
            f"    Ton bienveillant, AUCUN jargon technique, phrases courtes.\n"
            f"    Structure : confirmation de résolution → cause simple →\n"
            f"    conseil préventif → formule de courtoisie.\n"
            f"- Réponds en français.\n"
            f"- Ne mentionne AUCUN système non lié à l'incident.\n"
            f"- Ne génère AUCUNE hypothèse ou diagnostic supplémentaire.\n"
        )

        # If we have a pre-built resolution summary, inject it as additional context
        if resolution_summary["technical"]:
            closing_system_prompt += (
                f"\n\nCONTEXTE RÉSOLUTION PRÉ-ANALYSÉ (utilise ces données) :\n"
                + resolution_summary["technical"]
            )

        closing_prompt = (
            f"Message de clôture demandé.\n"
            f"Cause confirmée : {root_cause}"
        )

        try:
            response_text = await self.llm.generate(
                prompt=closing_prompt,
                system_prompt=closing_system_prompt,
            )
        except Exception as e:
            logger.error(f"[Closing] LLM error: {e}")
            # Fallback: use pre-built summary directly
            if resolution_summary["technical"]:
                response_text = (
                    resolution_summary["technical"]
                    + "\n\n---\n\n"
                    + resolution_summary["depositor"]
                )
            else:
                response_text = (
                    f"**Résumé technique N3**\n"
                    f"Incident : {app_name} — Cause : {root_cause}\n\n"
                    f"**Message dépositaire**\n"
                    + (resolution_summary["depositor"] or
                       f"Bonjour, votre demande a été traitée et le problème est résolu. "
                       f"La cause était liée à {root_cause}. Cordialement.")
                )

        # Auto-validation task
        if db is not None:
            try:
                from app.services.validation.validation_service import ValidationService as _ValSvc
                _ValSvc(db).create_chatbot_task(
                    user_question=message.content,
                    bot_response=response_text,
                    trust_score=1.0,
                    incident_type="ticket_closing",
                    application=app_name,
                    conversation_id=conversation_id,
                )
            except Exception:
                pass

        return ChatResponse(
            message=response_text,
            sources=[],
            suggestions=[
                "Cr├®er une FR pr├®ventive pour ce type d'incident",
                "Notifier l'├®quipe de la r├®solution",
                "Analyser les tickets similaires",
            ],
            confidence=1.0,
            conversation_id=conversation_id,
            app_id=message.app_id,
            pipeline_mode="CLOSING",
            trust_score=100,
            trust_label="closing_confirmed",
            diagnostic_available=False,
        )

    def _build_suggestions(self, mode: str, guard: Dict) -> List[str]:
        """Suggestions contextuelles selon le mode et le trust"""
        if not guard.get("can_diagnose"):
            return [
                "Fournir les logs d├â┬®taill├â┬®s pour affiner l'analyse",
                "Pr├â┬®ciser le code d'erreur exact",
                "D├â┬®crire les ├â┬®tapes qui ont pr├â┬®c├â┬®d├â┬® l'incident",
            ]
        if mode == "FR_RICH":
            return [
                "Afficher la proc├â┬®dure compl├â┬¿te de r├â┬®solution",
                "Quels sont les risques de cette intervention ?",
                "Existe-t-il des cas similaires r├â┬®solus ?",
            ]
        if mode == "FR_WEAK":
            return [
                "Valider cette proc├â┬®dure avec l'├â┬®quipe N3",
                "Consulter les tickets similaires",
                "Quelles v├â┬®rifications pr├â┬®alables effectuer ?",
            ]
        # LOG_BASED
        return [
            "Analyser les logs d├â┬®taill├â┬®s",
            "V├â┬®rifier les d├â┬®pendances du module",
            "Consulter l'historique des incidents similaires",
        ]

    # -----------------------------------------------------------------------
    # M├®moire conversationnelle
    # -----------------------------------------------------------------------

    def _load_history(self, message: ChatMessage, db) -> List[Dict]:
        """
        Charge les N derniers messages d'une conversation depuis la DB.
        Retourne une liste [{"role": "user"|"assistant", "content": "..."}].
        Priorise l'historique envoy├® directement par le frontend (message.conversation_history).
        """
        # Priorit├® 1 : historique fourni par le frontend ÔÇö on garde 8 messages max (4 ├®changes)
        if message.conversation_history:
            return message.conversation_history[-8:]

        # Priorit├® 2 : charger depuis la DB si conversation_id est un entier
        if not db or not message.conversation_id:
            return []

        try:
            conv_id_int = int(message.conversation_id)
        except (ValueError, TypeError):
            return []

        try:
            rows = (
                db.query(DBChatMessage)
                .filter(DBChatMessage.conversation_id == conv_id_int)
                .order_by(DBChatMessage.timestamp.desc())  # plus r├®cents d'abord
                .limit(8)  # 4 ├®changes suffisent pour la reformulation
                .all()
            )
            history = [
                {"role": row.role, "content": row.content}
                for row in reversed(rows)  # remettre dans l'ordre chronologique
                if row.role in ("user", "assistant") and row.content
            ]
            if history:
                logger.info(f"[Chatbot] Historique charg├® : {len(history)} messages pour conv#{conv_id_int}")
            return history
        except Exception as e:
            logger.warning(f"[Chatbot] Impossible de charger l'historique: {e}")
            return []

    # Patterns d'entit├®s techniques ├á extraire pour le r├®sum├® de contexte
    _ENTITY_PATTERNS = re.compile(
        r"\b("
        r"DSLAM\w*|VLAN\w*|ONT\w*|OLT\w*|DSL\w*|GPON\w*|ADSL\w*|VDSL\w*"  # ├®quipements r├®seau
        r"|FR[:\s]?\d+|BR\d+|BRASIL[-\s]?\d+"  # r├®f├®rences proc├®dures/tickets
        r"|[A-Z]{2,}[-_]?\d{3,}"  # codes erreur (ex: B4002, ERR_1300)
        r"|erreur\s+\d+|code\s+\d+|error\s+\d+"  # erreurs num├®riques
        r"|suppression|modification|cr├®ation|activation|d├®sactivation|migration"  # actions
        r"|impossible|├®chec|bloqu├®|timeout|unreachable"  # sympt├┤mes
        r")",
        re.IGNORECASE,
    )

    def _build_context_summary(self, history: List[Dict]) -> str:
        """
        Extrait les entit├®s techniques cl├®s des derniers ├®changes en une ligne compacte.
        Exemple : "Contexte: suppression DSLAM280, proc├®dure FR:189, erreur impossible"
        Inject├® dans le system_prompt ÔÇö co├╗te ~20 tokens au lieu de 400+.
        """
        if not history:
            return ""

        # Concat├®ner le texte de tout l'historique (tronqu├®)
        full_text = " ".join(
            m["content"][:300] for m in history if m.get("content")
        )

        entities = self._ENTITY_PATTERNS.findall(full_text)
        # D├®dupliquer en pr├®servant l'ordre
        seen: set = set()
        unique = []
        for e in entities:
            key = e.lower()
            if key not in seen:
                seen.add(key)
                unique.append(e)

        if not unique:
            return ""

        return "Contexte de la conversation en cours : " + ", ".join(unique[:8])

    # Patterns d├®tectant une question de suivi (r├®f├®rence implicite au contexte pr├®c├®dent)
    _FOLLOWUP_PATTERNS = re.compile(
        # Connecteurs de suivi : "et", "mais", "donc", "alors" seuls en d├®but de phrase
        r"(^(et|mais|donc|alors|pourquoi|quand|o├╣|quel|quelle|quels)\b"
        # "comment" seulement avec un r├®f├®rent contextuel explicite (pas "comment je peux extraire...")
        r"|^comment\s+(├ºa|cela|ce|cet|cette|il|elle|on|faire\s+├ºa|r├®soudre\s+├ºa|corriger\s+├ºa|d├®bloquer\s+├ºa)\b"
        # R├®f├®rents d├®ictiques ("ce probl├¿me", "cela", "cet/cette", etc.)
        r"|\b(ce (probl├¿me|truc|bug|cas|point|ticket|erreur)|cela|cet?te)\b"
        r"|\b(ici|l├á|[l├á├ºa])\b"
        r"|\b(pour (ce|cela))\b"
        r"|^(y a[- ]t[-\s]?il|existe[- ]t[-\s]?il|c'est quoi|qu'est[-\s]?ce)"
        r"|^(tu peux|peux[- ]tu|pourrais[- ]tu|donne[- ]moi|montre[- ]moi)\b"
        r"|(ticket|carte|issue|jira)\s*(pour|de|li├®|correspondant|similaire))",
        re.IGNORECASE,
    )

    async def _resolve_query(self, query: str, history: List[Dict]) -> str:
        """
        Si la question semble ├¬tre un suivi (r├®f├®rence implicite au contexte pr├®c├®dent),
        demande au LLM de la reformuler en requ├¬te autonome avant la recherche vectorielle.
        """
        if not history or not self._FOLLOWUP_PATTERNS.search(query):
            return query

        # Pr├®parer un r├®sum├® de l'historique r├®cent
        recent = history[-6:]
        history_text = "\n".join(
            f"{m['role'].upper()}: {m['content'][:200]}" for m in recent
        )

        reformulation_prompt = (
            f"Historique de la conversation :\n{history_text}\n\n"
            f"Nouvelle question : {query}\n\n"
            f"Reformule cette question en une requ├¬te de recherche autonome et compl├¿te (max 20 mots), "
            f"en fran├ºais, sans faire r├®f├®rence ├á 'ce probl├¿me' ou 'cela'. "
            f"R├®ponds UNIQUEMENT avec la requ├¬te reformul├®e, sans guillemets ni explication."
        )
        try:
            reformulated = await self.llm.generate(
                prompt=reformulation_prompt,
                system_prompt="Tu es un assistant de reformulation. Tu reformules des questions de suivi en requ├¬tes autonomes.",
                max_tokens=60,
            )
            reformulated = reformulated.strip().strip('"').strip("'").strip()
            # S├®curit├® : si le LLM renvoie une r├®ponse trop longue, garder l'original
            if reformulated and len(reformulated) < 200:
                return reformulated
        except Exception as e:
            logger.warning(f"[Chatbot] Reformulation ├®chou├®e: {e}")

        return query

    # -----------------------------------------------------------------------
    # M├®thodes Jira
    # -----------------------------------------------------------------------

    _JIRA_INTENT_PATTERNS = re.compile(
        r"("
        r"\bjira\b|carte\s+jira"
        r"|(?:existe[- ]t[-\s]il|y\s*[\u00e0a']\s*t[-\s]il)\s+(un|une|des)\s+(ticket|carte|issue|bogue)\s+jira"
        r"|cr[e\u00e9]+[e\u00e9]+r?\s+(un|une)\s+(ticket|carte|issue)\s+jira"
        r"|ouvrir?\s+(un|une)\s+(ticket|carte|issue)\s+jira"
        r"|signaler?\s+[\u00e0a]\s+jira"
        r"|lien\s+jira|r\u00e9f\u00e9rence\s+jira"
        r"|(?:date|quand)\s+(?:de\s+)?(?:cr\u00e9ation|cr\u00e9[e\u00e9]|ouverture|mise\s+[\u00e0a]\s+jour|modification|cl\u00f4ture|r\u00e9solution)"
        r"|(?:depuis\s+quand|il\s+y\s+a\s+combien|depuis\s+combien).*ticket"
        r"|(?:quel\s+(?:est|\u00e9tait)\s+(?:le|la|son))\s+(?:statut|\u00e9tat|priorit\u00e9|assignee|responsable|description)"
        r"|(?:qui\s+(?:est|a)\s+(?:assign[\u00e9e]|responsable|en\s+charge|trait[\u00e9e]|cr\u00e9[\u00e9e]))"
        r"|(?:commentaires?|notes?|historique|activit\u00e9s?)\s+(?:du|de|sur|pour)\s+(?:ce\s+)?ticket"
        r"|ticket\s+(?:ouvert|ferm[e\u00e9]|r\u00e9solu|en\s+cours|bloqu[e\u00e9]|annul[e\u00e9])"
        r"|tickets?\s+(?:similaires?|li[e\u00e9]s?|reli[e\u00e9]s?|connexes?|duplicat[a-z]*)"
        r"|tickets?\s+(?:haute?\s+priorit[e\u00e9]|critiques?|urgents?|bloquants?)"
        r"|(?:liste|liste-moi|montre|affiche|donne)\s+(?:les|des|tous\s+les)?\s+tickets?"
        r"|(?:combien|nombre)\s+(?:de\s+)?tickets?"
        r"|(?:dernier|premier)\s+(?:ticket|mise\s+[\u00e0a]\s+jour|commentaire)"
        r")",
        re.IGNORECASE,
    )

    # Detects a standalone Jira issue key like BRASIL-10861 anywhere in the message
    _JIRA_KEY_PATTERN = re.compile(r"\b([A-Z][A-Z0-9_]+-\d+)\b")

    # Verbs that indicate the user wants an explanation of a specific issue
    _EXPLAIN_VERBS = re.compile(
        r"\b(explique|reformule|r\u00e9sume|d\u00e9crypte|analyse|interpr\u00e8te|que\s+dit|d\u00e9taille)\b",
        re.IGNORECASE,
    )

    # ── Jira sub-intent patterns ─────────────────────────────────────────────
    _JIRA_SUBINTENT_DATE_CREATION = re.compile(
        r"date\s+(?:de\s+)?cr[e\u00e9][e\u00e9]"
        r"|(?:cr[e\u00e9][e\u00e9]|ouvert|soumis)\s+(?:le|quand|depuis)"
        r"|quand\s+(?:a[- ]t[-\s]il\s+)?[e\u00e9]t[e\u00e9]\s+(?:cr[e\u00e9][e\u00e9]|ouvert)"
        r"|depuis\s+quand|il\s+y\s+a\s+combien",
        re.IGNORECASE,
    )
    _JIRA_SUBINTENT_DATE_UPDATED = re.compile(
        r"(?:derni[e\u00e8]re\s+)?(?:mise\s+[a\u00e0]\s+jour|modification|update|mis\s+[a\u00e0]\s+jour)",
        re.IGNORECASE,
    )
    _JIRA_SUBINTENT_ASSIGNEE = re.compile(
        r"(?:qui\s+est|quel\s+est)\s+(?:l'|le\s+|la\s+)?(?:assign[e\u00e9]|responsable|en\s+charge|technicien)"
        r"|assign[e\u00e9]e?\s+[a\u00e0]",
        re.IGNORECASE,
    )
    _JIRA_SUBINTENT_STATUS = re.compile(
        r"(?:quel\s+est|quel\s+\u00e9tait)\s+(?:le\s+)?(?:statut|[e\u00e9]tat)"
        r"|statut\s+actuel|est[-\s](?:il|ce)\s+(?:r[e\u00e9]solu|ferm[e\u00e9]|ouvert|en\s+cours)",
        re.IGNORECASE,
    )
    _JIRA_SUBINTENT_PRIORITY = re.compile(
        r"(?:quelle\s+est|quel\s+est)\s+(?:la\s+|le\s+)?(?:priorit[e\u00e9]|urgence)"
        r"|priorit[e\u00e9]\s+(?:du|de\s+ce|de\s+ce\s+ticket)",
        re.IGNORECASE,
    )
    _JIRA_SUBINTENT_DESCRIPTION = re.compile(
        r"(?:quelle\s+est|donne[- ]moi|montre|affiche)\s+(?:la\s+)?description"
        r"|d[e\u00e9]cription\s+(?:du|de\s+ce|compl[e\u00e8]te)"
        r"|de\s+quoi\s+(?:parle|traite|s'agit)",
        re.IGNORECASE,
    )
    _JIRA_SUBINTENT_COMMENTS = re.compile(
        r"commentaires?|notes?\s+(?:du|de\s+ce|sur|pour)\s+ticket"
        r"|derni[e\u00e8]re?s?\s+(?:note|activit[e\u00e9]|commentaire|message)"
        r"|historique\s+(?:du|de\s+ce|des\s+)ticket",
        re.IGNORECASE,
    )
    _JIRA_SUBINTENT_SIMILAR = re.compile(
        r"tickets?\s+(?:similaires?|li[e\u00e9]s?|reli[e\u00e9]s?|connexes?|duplicat[a-z]*)"
        r"|(?:autres?\s+tickets?)\s+(?:du\s+m[e\u00ea]me|similaires?|li[e\u00e9]s?)"
        r"|y\s+a[-\s]t[-\s]il\s+d'autres",
        re.IGNORECASE,
    )
    _JIRA_SUBINTENT_OPEN = re.compile(
        r"tickets?\s+(?:ouverts?|non\s+r[e\u00e9]solus?|en\s+cours|actifs?|non\s+ferm[e\u00e9]s?)"
        r"|lister?\s+(?:les\s+)?tickets?\s+ouverts?"
        r"|quels?\s+tickets?\s+(?:sont|restent?)\s+(?:ouverts?|en\s+attente)",
        re.IGNORECASE,
    )
    _JIRA_SUBINTENT_PRIORITY_FILTER = re.compile(
        r"tickets?\s+(?:haute?\s+priorit[e\u00e9]|critiques?|urgents?|bloquants?|P[01])"
        r"|(?:haute?\s+priorit[e\u00e9]|critiques?)\s+tickets?",
        re.IGNORECASE,
    )
    _JIRA_SUBINTENT_COUNT = re.compile(
        r"(?:combien|nombre)\s+(?:de\s+)?tickets?"
        r"|compter?\s+(?:les\s+)?tickets?",
        re.IGNORECASE,
    )

    def _detect_jira_sub_intent(self, text: str) -> str:
        """Returns a sub-intent string for the Jira branch."""
        if self._JIRA_SUBINTENT_DATE_CREATION.search(text):   return "date_creation"
        if self._JIRA_SUBINTENT_DATE_UPDATED.search(text):    return "date_updated"
        if self._JIRA_SUBINTENT_ASSIGNEE.search(text):        return "assignee"
        if self._JIRA_SUBINTENT_STATUS.search(text):          return "status"
        if self._JIRA_SUBINTENT_PRIORITY.search(text):        return "priority"
        if self._JIRA_SUBINTENT_DESCRIPTION.search(text):     return "description"
        if self._JIRA_SUBINTENT_COMMENTS.search(text):        return "comments"
        if self._JIRA_SUBINTENT_SIMILAR.search(text):         return "similar"
        if self._JIRA_SUBINTENT_OPEN.search(text):            return "open_tickets"
        if self._JIRA_SUBINTENT_PRIORITY_FILTER.search(text): return "priority_filter"
        if self._JIRA_SUBINTENT_COUNT.search(text):           return "count"
        if self._EXPLAIN_VERBS.search(text):                   return "explain"
        return "search"

    def _extract_issue_key(self, text: str) -> Optional[str]:
        """Return the first Jira issue key found in text (e.g. BRASIL-10861), or None."""
        m = self._JIRA_KEY_PATTERN.search(text)
        return m.group(1) if m else None

    def _detect_jira_intent(self, text: str) -> bool:
        """Return True when the message targets Jira via keywords OR an explicit issue key."""
        return (
            bool(self._JIRA_INTENT_PATTERNS.search(text))
            or bool(self._JIRA_KEY_PATTERN.search(text))
        )

    # ÔöÇÔöÇ ND Log Search intent ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    _ND_PATTERN = re.compile(
        r"(?:nd|num[e├®]ro\s+de\s+demande|num[e├®]ro\s+nd|demande)[\s:=#]*"
        r"(0?[0-9]{8,10})",
        re.IGNORECASE,
    )
    _ND_RAW_PATTERN = re.compile(r"\b(0[0-9]{9})\b")  # 10-digit starting with 0

    def _extract_nd_number(self, text: str) -> Optional[str]:
        """Extrait un num├®ro ND du texte. Retourne le num├®ro sans le 0 initial (format interne)."""
        m = self._ND_PATTERN.search(text)
        if m:
            return m.group(1).lstrip("0")
        m2 = self._ND_RAW_PATTERN.search(text)
        if m2:
            return m2.group(1).lstrip("0")
        return None

    async def _handle_nd_log_intent(
        self,
        nd_number: str,
        user_message: str,
        conversation_id: str,
        app_id: str,
    ) -> Optional[ChatResponse]:
        """Recherche un ND dans les fichiers log index├®s et retourne une analyse structur├®e."""
        import re as _re
        from pathlib import Path
        from collections import Counter

        # Locate log files to search ÔÇö prioritise recently uploaded files
        base = Path(__file__).parents[4]
        search_dirs = [
            base / "data_pipeline" / "input",
            base / "backend" / "data_pipeline" / "input",
        ]
        log_files = []
        for d in search_dirs:
            if d.exists():
                log_files += [f for f in d.glob("*.log") if f.stat().st_size > 0]
        # Deduplicate
        seen: set = set()
        log_files = [f for f in log_files if f.name not in seen and not seen.add(f.name)]  # type: ignore

        if not log_files:
            return None

        events: list = []
        found_in: list = []

        for log_file in log_files:
            try:
                with open(log_file, encoding="utf-8", errors="ignore") as fh:
                    for line in fh:
                        if nd_number not in line:
                            continue
                        ts      = _re.search(r'horodatage="([^"]+)"', line)
                        mvt     = _re.search(r'typeMouvement="([^"]+)"', line)
                        num_mvt = _re.search(r'numeroMouvement="([^"]+)"', line)
                        epc     = _re.search(r'idEpc="([^"]+)"', line)
                        etat    = _re.search(r'etatCourantVersion="([^"]+)"', line)
                        avant   = _re.search(r'etatAvantModification="([^"]+)"', line)
                        st      = _re.search(r'libelleServiceTechnique="([^"]+)"', line)
                        dslam   = _re.search(r'nomEquipementLogiqueDslam="([^"]+)"', line)
                        nro     = _re.search(r'libelle42C="([^"]+)"', line)
                        etatEpt = _re.search(r'etatEpt="([^"]+)"', line)
                        nom_cli = _re.search(r'nomClient="([^"]+)"', line)
                        far_id  = _re.search(r'farId="([^"]+)"', line)
                        events.append({
                            "ts":      ts.group(1) if ts else "",
                            "num_mvt": num_mvt.group(1)[-8:] if num_mvt else "",
                            "type":    mvt.group(1) if mvt else "",
                            "epc":     epc.group(1) if epc else "",
                            "etat":    etat.group(1) if etat else "",
                            "avant":   avant.group(1) if avant else "",
                            "st":      st.group(1) if st else "",
                            "dslam":   dslam.group(1) if dslam else "",
                            "nro":     nro.group(1) if nro else "",
                            "etatEpt": etatEpt.group(1) if etatEpt else "",
                            "nom_cli": nom_cli.group(1) if nom_cli else "",
                            "far_id":  far_id.group(1) if far_id else "",
                        })
                if events:
                    found_in.append(log_file.name)
                    break  # stop at first file that has the ND
            except Exception as e:
                logger.warning(f"[ND-Search] Erreur lecture {log_file.name}: {e}")

        if not events:
            return None

        # ÔöÇÔöÇ Build structured summary ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
        ETAT = {"C": "Command├®", "E": "En service", "A": "├Ç venir", "S": "Supprim├®", "R": "R├®sili├®", "D": "D├®sactiv├®"}
        EPT  = {"ES": "En service", "AFF": "Affect├®", "LIB": "Lib├®r├®"}

        first = events[0]
        last  = events[-1]
        timestamps = Counter(e["ts"][:19] for e in events if e["ts"])
        sts        = Counter(e["st"]  for e in events if e["st"])
        trans      = Counter(f"{e['avant']}ÔåÆ{e['etat']}" for e in events)
        epts       = Counter(e["etatEpt"] for e in events if e["etatEpt"])

        batches_str = "\n".join(
            f"  - {ts}  ├ù{cnt} mouvement(s)"
            for ts, cnt in sorted(timestamps.items())
        )
        sts_str = "\n".join(f"  - {k}: ├ù{v}" for k, v in sts.most_common(6))
        trans_str = "\n".join(
            f"  - {p.split('ÔåÆ')[0]}({ETAT.get(p.split('ÔåÆ')[0],'?')}) ÔåÆ "
            f"{p.split('ÔåÆ')[1]}({ETAT.get(p.split('ÔåÆ')[1],'?')}): ├ù{c}"
            for p, c in trans.most_common()
        )
        ept_str = ", ".join(f"{k}({EPT.get(k,k)}): ├ù{v}" for k, v in epts.most_common())

        context = f"""ANALYSE ND 0{nd_number} ÔÇö {found_in[0] if found_in else 'logs'}

CLIENT     : {first['nom_cli']} (farId: {first['far_id']})
DSLAM      : {first['dslam']}
NRO        : {first['nro']}
MOUVEMENTS : {len(events)} au total
FICHIER    : {', '.join(found_in)}

CHRONOLOGIE DES BATCHS:
{batches_str}

SERVICES TECHNIQUES CONCERN├ëS:
{sts_str}

TRANSITIONS D'├ëTAT:
{trans_str}

├ëTATS EPT: {ept_str}

PREMIER MOUVEMENT: {first['ts']} | {first['type']} | {first['st']} | {first['avant']}ÔåÆ{first['etat']}
DERNIER MOUVEMENT: {last['ts']}  | {last['type']}  | {last['st']} | {last['avant']}ÔåÆ{last['etat']} | etatEpt={last['etatEpt']}
"""

        prompt = f"""Tu es un expert BRASIL Network Management. Voici les donn├®es brutes extraites des logs pour le ND 0{nd_number}.

Utilise UNIQUEMENT ces donn├®es pour r├®pondre. Ne fabrique rien.

{context}

Question: {user_message}

R├®ponds en fran├ºais de fa├ºon structur├®e :
1. Identit├® du client et ├®quipement
2. Chronologie des ├®v├®nements
3. Services techniques impact├®s
4. Diagnostic / interpr├®tation de l'├®tat actuel
"""
        try:
            llm_answer = await llm_client.generate(prompt)
        except Exception as e:
            logger.error(f"[ND-Search] LLM error: {e}")
            llm_answer = context  # fallback: return raw data

        return ChatResponse(
            message=llm_answer,
            confidence=0.95,
            conversation_id=conversation_id,
            trust_score=95,
            trust_label="nd_log_search",
            sources=[{"type": "log", "file": f, "nd": nd_number, "events": len(events)} for f in found_in],
            suggestions=[
                f"Quels services techniques sont actifs pour le ND 0{nd_number} ?",
                f"Y a-t-il des erreurs associ├®es au DSLAM {first['dslam']} ?",
                "Rechercher la FR associ├®e ├á ce type de migration",
            ],
            diagnostic_available=False,
        )

    # ÔöÇÔöÇ Equipment Log Search intent ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    # D├®tecte : DSLAM (DS[A-Z]{2,5}[0-9]{2,4}), NRO (libell├®), ONT (numSerie), ch├óssis
    _EQUIP_DSLAM_PATTERN = re.compile(
        r"\b(DS[A-Z]{2,6}[0-9]{2,4}(?:-C[0-9]+)?)\b",
        re.IGNORECASE,
    )
    _EQUIP_CHASSIS_PATTERN = re.compile(
        r"\b(DS[A-Z]{2,6}[0-9]{2,4}-C[0-9]+)\b",
        re.IGNORECASE,
    )
    _EQUIP_ONT_PATTERN = re.compile(
        r"(?:ont|num[e├®]ro\s+ont|serie\s+ont|numSerie)[:\s]+([A-Z0-9]{10,16})\b",
        re.IGNORECASE,
    )
    _EQUIP_NIP_PATTERN = re.compile(
        r"\b(BSAU[A-Z0-9]+|NENIC[A-Z0-9]+)\b",
        re.IGNORECASE,
    )
    _EQUIP_NRO_PATTERN = re.compile(
        r"\b(NRO\w+|SRO\w+|OLT\w+|NB[A-Z]{2,5}[0-9]{3,6})\b",
        re.IGNORECASE,
    )
    _EQUIP_INTENT_PATTERN = re.compile(
        r"\b(dslam|nro|sro|olt|ont|chassis|châssis|équipement|nip|bsau|nenic"
        r"|port|carte|alvéole|gestionnaire|adresse\s+ip|routeur|boucle"
        r"|nblil|supprimer|retirer)\b",
        re.IGNORECASE,
    )

    # Patterns qui indiquent une question sur une PROC├ëDURE, pas sur un ├®quipement r├®el
    _PROC_CONTEXT_PATTERN = re.compile(
        r"\b(procedure|proc[e├®]dure|FR\s*\d+|exception|comment|[e├®]tape|d[e├®]bloquer"
        r"|impossible|suppression|cause|racine|r[e├®]soudre|r[e├®]soudre|escalader"
        r"|v[e├®]rifier|coh[e├®]rence|analyser|probl[e├®]me|incident|diagnos"
        r"|m[e\xe9]thode|fonction|classe|service\s+java|impl[e\xe9]ment|code\s+source"
        r"|quel(?:le)?\s+(?:fonction|m[e\xe9]thode|classe|service))",
        re.IGNORECASE,
    )
    # Noms d'exceptions Java/BRASIL (CamelCase se terminant par Exception)
    _JAVA_EXCEPTION_PATTERN = re.compile(
        r"[A-Z][a-z]+(?:[A-Z][a-z]+)+Exception\b"
    )

    # ── Write-ticket / customer-message intent ──────────────────────────────
    _WRITE_TICKET_PATTERNS = re.compile(
        r"("
        r"r[e\u00e9]dig[\u00e9e]?\s+(un|une|le|la|ce)\s+(message|mail|email|r[e\u00e9]ponse|note|communication)"
        r"|[e\u00e9]cri[st]?\s+(un|une|le)\s+(message|mail|email|r[e\u00e9]ponse|note)"
        r"|formule[rz]?\s+(un|une|la)?\s*(r[e\u00e9]ponse|communication|message)"
        r"|(?:message|mail|email)\s+(?:pour|[a\u00e0]|au)\s+(?:le\s+)?(?:d[e\u00e9]positaire|client|demandeur|utilisateur)"
        r"|informer?\s+(?:le\s+)?(?:d[e\u00e9]positaire|client|demandeur|utilisateur)"
        r"|(?:notifier?|pr[e\u00e9]venir?)\s+(?:le\s+)?(?:d[e\u00e9]positaire|client)"
        r"|envoyer?\s+(un|une)\s+(message|mail|r[e\u00e9]ponse|notification)"
        r"|communication\s+(pour|au|[a\u00e0])\s+(?:le\s+)?(?:client|d[e\u00e9]positaire)"
        r")",
        re.IGNORECASE,
    )

    def _detect_write_ticket_intent(self, text: str) -> bool:
        """Return True when the user wants to draft a message for the depositor/client."""
        return bool(self._WRITE_TICKET_PATTERNS.search(text))

    async def _handle_write_ticket_intent(
        self,
        user_message: str,
        conv_state: "ConversationState",
        conversation_id: str,
        app_id: str,
        history: List[Dict],
    ) -> "ChatResponse":
        """Draft a professional update message for the ticket depositor/client."""
        root_cause = getattr(conv_state, "confirmed_root_cause", None)
        procedure  = getattr(conv_state, "confirmed_procedure_id", None)
        app_name   = app_id

        history_text = ""
        for turn in (history or [])[-10:]:
            role    = turn.get("role", "")
            content = turn.get("content", "")
            if role == "user":
                history_text += f"[Technicien] {content}\n"
            elif role == "assistant":
                history_text += f"[Assistant] {content}\n"

        root_section = (f"\n\nCAUSE RACINE CONFIRM\u00c9E : {root_cause}" if root_cause else "")
        procedure_section = (f"\nPROC\u00c9DURE APPLIQU\u00c9E : {procedure}" if procedure else "")

        system_prompt = (
            f"Tu es un assistant support N3 pour l'application {app_name} (Orange Telecom).\n"
            f"R\u00e8gles : ton professionnel et bienveillant, AUCUN jargon technique, phrases courtes.\n"
            f"Structure en 3 parties : prise en charge | statut actuel | prochaine \u00e9tape.\n"
            f"Termine par une formule de courtoisie.\n"
            f"R\u00e9ponds UNIQUEMENT en fran\u00e7ais. Ne g\u00e9n\u00e8re AUCUN identifiant fictif.\n"
            f"CONTEXTE DE L'INCIDENT :{root_section}{procedure_section}\n\n"
            f"HISTORIQUE R\u00c9CENT :\n{history_text}"
        )
        prompt = f"R\u00e9dige le message de mise \u00e0 jour pour le d\u00e9positaire.\n\nDemande : {user_message}"

        try:
            llm_result = await self.llm.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                with_thinking=True,
                max_tokens=400,
            )
            if isinstance(llm_result, tuple):
                response_text, thinking_content = llm_result
            else:
                response_text, thinking_content = llm_result, None
        except Exception as e:
            logger.error(f"[WriteTicket] LLM error: {e}")
            response_text = (
                "Bonjour,\n\nNous avons bien pris en compte votre demande. "
                "Une investigation est en cours et nous vous tiendrons inform\u00e9(e) "
                "dans les meilleurs d\u00e9lais.\n\nCordialement,\nL'\u00e9quipe Support N3"
            )
            thinking_content = None

        logger.info("[WriteTicket] Message d\u00e9positaire g\u00e9n\u00e9r\u00e9")
        return ChatResponse(
            message=response_text,
            thinking_content=thinking_content,
            sources=[],
            suggestions=[
                "Envoyer ce message dans le ticket Jira",
                "G\u00e9n\u00e9rer le message de cl\u00f4ture",
                "R\u00e9sum\u00e9 technique pour la hi\u00e9rarchie",
            ],
            confidence=0.95,
            conversation_id=conversation_id,
            app_id=app_id,
            pipeline_mode="write_ticket_message",
            trust_score=85,
            trust_label="contextual",
            diagnostic_available=False,
        )

    def _extract_equipment_name(self, text: str) -> Optional[str]:
        """Extrait un nom d'├®quipement BRASIL (DSLAM, ONT, NIP) du texte."""
        # Ne pas d├®clencher si un ND a d├®j├á ├®t├® d├®tect├®
        if self._extract_nd_number(text):
            return None
        # Ne pas d├®clencher si la query parle d'une proc├®dure, d'une ├®tape ou d'une exception Java
        if self._PROC_CONTEXT_PATTERN.search(text):
            return None
        if self._JAVA_EXCEPTION_PATTERN.search(text):
            return None
        for pat in (self._EQUIP_CHASSIS_PATTERN, self._EQUIP_DSLAM_PATTERN,
                    self._EQUIP_ONT_PATTERN, self._EQUIP_NIP_PATTERN,
                    self._EQUIP_NRO_PATTERN):
            m = pat.search(text)
            if m:
                # Only return if query also has intent keywords
                if self._EQUIP_INTENT_PATTERN.search(text):
                    return m.group(1)
        # Fallback: any all-caps token 4-12 chars if intent keyword present
        if self._EQUIP_INTENT_PATTERN.search(text):
            m = re.search(r"\b([A-Z]{2,4}[A-Z0-9]{2,10})\b", text)
            if m:
                return m.group(1)
        return None

    async def _handle_equipment_log_intent(
        self,
        equipment: str,
        user_message: str,
        conversation_id: str,
        app_id: str,
    ) -> Optional[ChatResponse]:
        """Recherche un ├®quipement dans les fichiers log et retourne une analyse structur├®e."""
        import re as _re
        from pathlib import Path
        from collections import Counter, defaultdict

        base = Path(__file__).parents[4]
        search_dirs = [
            base / "data_pipeline" / "input",
            base / "backend" / "data_pipeline" / "input",
        ]
        log_files = []
        for d in search_dirs:
            if d.exists():
                log_files += [f for f in d.glob("*.log") if f.stat().st_size > 0]
        seen_names: set = set()
        log_files = [f for f in log_files if f.name not in seen_names and not seen_names.add(f.name)]  # type: ignore

        if not log_files:
            return None

        equip_upper = equipment.upper()
        events: list = []
        found_in: list = []
        MAX_EVENTS = 200  # cap to avoid huge responses

        for log_file in log_files:
            try:
                with open(log_file, encoding="utf-8", errors="ignore") as fh:
                    for line in fh:
                        if equip_upper not in line.upper():
                            continue
                        ts      = _re.search(r'horodatage="([^"]+)"', line)
                        mvt     = _re.search(r'typeMouvement="([^"]+)"', line)
                        nd      = _re.search(r'nd="([^"]+)"', line)
                        nom_cli = _re.search(r'nomClient="([^"]+)"', line)
                        dslam   = _re.search(r'nomEquipementLogiqueDslam="([^"]+)"', line)
                        chassis = _re.search(r'nomChassisLogique="([^"]+)"', line)
                        port    = _re.search(r'numeroPort="([^"]+)"', line)
                        carte   = _re.search(r'numeroCarte="([^"]+)"', line)
                        st      = _re.search(r'libelleServiceTechnique="([^"]+)"', line)
                        etat    = _re.search(r'etatCourantVersion="([^"]+)"', line)
                        avant   = _re.search(r'etatAvantModification="([^"]+)"', line)
                        etatEpt = _re.search(r'etatEpt="([^"]+)"', line)
                        nip     = _re.search(r'referenceNip="([^"]+)"', line)
                        ont_ser = _re.search(r'numSerie="([^"]+)"', line)
                        events.append({
                            "ts":      ts.group(1)[:19] if ts else "",
                            "type":    mvt.group(1) if mvt else "",
                            "nd":      nd.group(1) if nd else "",
                            "client":  nom_cli.group(1) if nom_cli else "",
                            "dslam":   dslam.group(1) if dslam else "",
                            "chassis": chassis.group(1) if chassis else "",
                            "port":    port.group(1) if port else "",
                            "carte":   carte.group(1) if carte else "",
                            "st":      st.group(1) if st else "",
                            "etat":    etat.group(1) if etat else "",
                            "avant":   avant.group(1) if avant else "",
                            "etatEpt": etatEpt.group(1) if etatEpt else "",
                            "nip":     nip.group(1) if nip else "",
                            "ont_ser": ont_ser.group(1) if ont_ser else "",
                        })
                        if len(events) >= MAX_EVENTS:
                            break
                if events:
                    found_in.append(log_file.name)
                    break
            except Exception as e:
                logger.warning(f"[Equip-Search] Erreur lecture {log_file.name}: {e}")

        if not events:
            return None

        # ÔöÇÔöÇ Build structured summary ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
        from collections import Counter
        ETAT = {"C": "Command├®", "E": "En service", "A": "├Ç venir", "S": "Supprim├®", "D": "D├®sactiv├®"}
        EPT  = {"ES": "En service", "AFF": "Affect├®", "LIB": "Lib├®r├®"}

        nds_impacted  = Counter(e["nd"]     for e in events if e["nd"])
        clients       = Counter(e["client"] for e in events if e["client"])
        sts           = Counter(e["st"]     for e in events if e["st"])
        ports         = Counter(e["port"]   for e in events if e["port"])
        chassis_seen  = Counter(e["chassis"] for e in events if e["chassis"])
        nips          = Counter(e["nip"]    for e in events if e["nip"])
        epts          = Counter(e["etatEpt"] for e in events if e["etatEpt"])
        timestamps    = Counter(e["ts"][:10] for e in events if e["ts"])

        nds_str     = "\n".join(f"  - ND {nd}: ├ù{cnt}" for nd, cnt in nds_impacted.most_common(10))
        clients_str = ", ".join(f"{c}(├ù{v})" for c, v in clients.most_common(5))
        sts_str     = "\n".join(f"  - {k}: ├ù{v}" for k, v in sts.most_common(8))
        ports_str   = ", ".join(f"port {p}(├ù{v})" for p, v in ports.most_common(6))
        chassis_str = ", ".join(f"{c}(├ù{v})" for c, v in chassis_seen.most_common(4))
        nips_str    = ", ".join(f"{n}(├ù{v})" for n, v in nips.most_common(4))
        ept_str     = ", ".join(f"{k}({EPT.get(k,k)}): ├ù{v}" for k, v in epts.most_common())
        days_str    = ", ".join(f"{d}(├ù{v})" for d, v in sorted(timestamps.items()))

        context = f"""ANALYSE ├ëQUIPEMENT : {equip_upper}
Fichier    : {', '.join(found_in)}
├ëv├®nements : {len(events)} (sur {MAX_EVENTS} max extraits)
Jours actifs : {days_str}

NDs IMPACT├ëS (top 10) :
{nds_str}

CLIENTS : {clients_str}

SERVICES TECHNIQUES :
{sts_str}

PORTS UTILIS├ëS : {ports_str}
CH├éSSIS        : {chassis_str}
NIPs ASSOCI├ëS  : {nips_str}
├ëTATS EPT      : {ept_str}

PREMIER ├ëV├ëNEMENT : {events[0]['ts']} | ND={events[0]['nd']} | {events[0]['st']} | {events[0]['avant']}ÔåÆ{events[0]['etat']}
DERNIER ├ëV├ëNEMENT : {events[-1]['ts']} | ND={events[-1]['nd']} | {events[-1]['st']} | {events[-1]['avant']}ÔåÆ{events[-1]['etat']}
"""

        prompt = f"""Tu es un expert BRASIL Network Management. Voici les donn├®es extraites des logs pour l'├®quipement {equip_upper}.

Utilise UNIQUEMENT ces donn├®es pour r├®pondre. Ne fabrique rien.

{context}

Question: {user_message}

R├®ponds en fran├ºais de fa├ºon structur├®e :
1. Identification de l'├®quipement et sa localisation
2. Activit├® r├®sum├®e (NDs trait├®s, clients, services)
3. ├ëtat actuel et ports occup├®s
4. Points d'attention ou anomalies ├®ventuelles
"""
        try:
            llm_answer = await llm_client.generate(prompt)
        except Exception as e:
            logger.error(f"[Equip-Search] LLM error: {e}")
            llm_answer = context

        top_nd = nds_impacted.most_common(1)[0][0] if nds_impacted else ""
        return ChatResponse(
            message=llm_answer,
            confidence=0.93,
            conversation_id=conversation_id,
            trust_score=93,
            trust_label="equipment_log_search",
            sources=[{"type": "log", "file": f, "equipment": equip_upper, "events": len(events)} for f in found_in],
            suggestions=[
                f"Analyser le ND {top_nd} sur cet ├®quipement" if top_nd else f"Quels NDs sont sur {equip_upper} ?",
                f"Quels ports sont occup├®s sur {equip_upper} ?",
                f"Y a-t-il des erreurs sur les NIPs associ├®s ├á {equip_upper} ?",
            ],
            diagnostic_available=False,
        )
    _ML_ANALYSIS_PATTERNS = re.compile(
        r"\b(causes\s+principales|top\s+causes|top\s+cat[e├®]gories|analyse\s+ml|"
        r"r[e├®]sum[e├®]\s+ml|anomalies\s+temporelles|volume\s+de\s+tickets|"
        r"classification\s+tickets|statistiques\s+tickets|insights\s+ml|"
        r"r[e├®]partition\s+(des\s+)?causes|distribution\s+tickets|"
        r"mttr\s+moyen|temps\s+de\s+r[e├®]solution\s+moyen|score\s+de\s+criticit[e├®]|"
        r"quelles?\s+sont\s+les\s+causes|causes\s+r[e├®]currentes|incidents\s+r[e├®]currents|"
        r"rapport\s+ml|rapport\s+de\s+classification|tendances\s+tickets|"
        r"principales?\s+cat[e├®]gories)\b",
        re.IGNORECASE,
    )

    def _detect_ml_analysis_intent(self, text: str) -> bool:
        """Return True when the message asks about ML classification stats or insights."""
        return bool(self._ML_ANALYSIS_PATTERNS.search(text))

    # ── Classify Ticket intent ────────────────────────────────────────────────
    _CLASSIFY_TICKET_PATTERNS = re.compile(
        r"\b(class(?:e|ifi(?:e|er?|ez))\s+(?:ce\s+)?(?:ticket|incident|demande|probl[eè]me)|"
        r"cat[eé]goris(?:e|er?|ez)\s+(?:ce\s+)?(?:ticket|incident|demande)|"
        r"quel\s+type\s+(?:d[e'])\s*(?:ticket|incident)|"
        r"de\s+quel\s+type\s+est|"
        r"d[eé]termine[rz]?\s+la\s+cat[eé]gorie|"
        r"cat[eé]gorisation\s+(?:automatique|ml)|"
        r"classifier\s+[çc]a|"
        r"analyse[rz]?\s+ce\s+ticket\s+(?:ml|automatiquement))\b",
        re.IGNORECASE,
    )

    def _detect_classify_ticket_intent(self, text: str) -> bool:
        """Return True when the user asks to classify a specific ticket text."""
        return bool(self._CLASSIFY_TICKET_PATTERNS.search(text))

    async def _handle_classify_ticket_intent(
        self,
        user_message: str,
        conversation_id: str,
        app_id: str,
        history: list,
    ) -> Optional[ChatResponse]:
        """Classify a ticket text using ClassifierBridge and return formatted markdown."""
        try:
            from app.services.chatbot.classifier_bridge import classifier_bridge

            # If the message is a short command, look for ticket text in recent history
            short_cmd = bool(re.search(
                r"^(classe[rz]?|cat[eé]goris[ez]?|classifier)\s*(ce\s*)?(ticket|incident|[çc]a|cela)?\.?\s*$",
                user_message.strip(), re.I,
            ))
            text_to_classify = user_message
            if short_cmd and history:
                for m in reversed(history):
                    if m.get("role") == "user" and len(m.get("content", "")) > 20:
                        text_to_classify = m["content"]
                        break

            if not classifier_bridge.is_trained():
                response_text = (
                    "⚠️ **Modèle ML non disponible**\n\n"
                    "Le classifieur n'a pas encore été entraîné. "
                    "Veuillez importer des tickets via **Module ML → Entraînement** avant d'utiliser la classification inline."
                )
                return ChatResponse(
                    message=response_text,
                    sources=[],
                    suggestions=["Accéder au module ML", "Importer des données d'entraînement"],
                    confidence=0.0,
                    conversation_id=conversation_id,
                    app_id=app_id,
                    pipeline_mode="ml_classify_ticket",
                    trust_score=0,
                    trust_label="ml_classifier",
                    diagnostic_available=False,
                )

            response_text = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: classifier_bridge.format_for_chatbot(text_to_classify, groq_client=None),
            )
            status = classifier_bridge.get_status()

            return ChatResponse(
                message=response_text,
                sources=[{"title": "ML Classifier", "type": "ml_classification", "score": 1.0}],
                suggestions=[
                    "Voir les tickets similaires dans Jira",
                    "Corriger cette classification si incorrecte",
                    "Rapport de dérive du modèle ML",
                ],
                confidence=0.9 if status.get("active_model") not in (None, "none") else 0.0,
                conversation_id=conversation_id,
                app_id=app_id,
                pipeline_mode="ml_classify_ticket",
                trust_score=85 if status.get("active_model") == "hierarchical" else 70,
                trust_label="ml_classifier",
                diagnostic_available=False,
            )
        except Exception as e:
            logger.error(f"[ClassifyTicket] Handler failed: {e}")
            return None

    # ── Technical Inference intent ────────────────────────────────────────────
    # D├®tecte "c'est quoi X", "qu'est-ce que X", "explique X", "├á quoi sert X"
    # o├╣ X est un identifiant technique (CamelCase, snake_case, ALL_CAPS, etc.)
    _TECH_INFERENCE_PATTERNS = re.compile(
        r"(?:"
        r"c'est\s+quoi\s+(?:l[ea]?\s+)?"
        r"|qu'est[- ]ce\s+que\s+(?:l[ea]?\s+)?"
        r"|(?:explique|d\u00e9taille|d\u00e9cris|pr\u00e9sente|d\u00e9crypte)\s+(?:l[ea]?\s+)?"
        r"|\u00e0\s+quoi\s+sert\s+(?:l[ea]?\s+)?"
        r"|que\s+fait\s+(?:l[ea]?\s+)?"
        r"|comment\s+fonctionne\s+(?:l[ea]?\s+)?"
        r"|quel\s+est\s+le\s+r\u00f4le\s+de\s+(?:l[ea]?\s+)?"
        r")"
        r"([A-Z][a-zA-Z0-9]{3,}(?:[A-Z][a-zA-Z0-9]+)+"
        r"|[a-z][a-z0-9_]{2,}(?:_[a-z0-9]+)+"
        r"|[A-Z_]{3,}(?:_[A-Z0-9]+)+"
        r"|[A-Za-z0-9][A-Za-z0-9_\-\.]{4,}(?:Service|Manager|Handler|Controller|Repository|Processor|Connector|Engine|Helper|Utils?|Factory|Builder|Adapter|Gateway|Client|Provider|Listener|Scheduler|Worker|Job|Task|Module|Component|Interface|Impl|Bean|Dao|Api|Dto|Config|Filter|Interceptor|Validator|Converter|Parser|Serializer)"
        r")",
        re.IGNORECASE,
    )

    # ├ëgalement : questions directes sans verbe introductif sur un symbole technique connu
    _TECH_SYMBOL_PATTERN = re.compile(
        r"^(?:le?a?\s+)?([A-Z][a-zA-Z0-9]{3,}(?:[A-Z][a-zA-Z0-9]+)+)\s*[\?!]?\s*$"
    )

    def _detect_tech_inference_intent(self, text: str) -> Optional[str]:
        """
        Retourne le nom du symbole technique si la question est de type
        'c\'est quoi ManageTechnicalConfigurationService' ou 'qu\'est-ce que X'.
        Retourne None sinon.
        """
        m = self._TECH_INFERENCE_PATTERNS.search(text)
        if m:
            return m.group(m.lastindex or 1).strip()
        m2 = self._TECH_SYMBOL_PATTERN.match(text.strip())
        if m2:
            return m2.group(1)
        return None

    async def _handle_tech_inference_intent(
        self,
        symbol: str,
        user_message: str,
        orch_result: dict,
        conversation_id: str,
        app_id: str,
        app_ctx: dict,
    ) -> ChatResponse:
        """
        Le LLM inf├¿re ce qu'est un symbole technique (classe, service, m├®thode)
        en se basant sur son nom, le contexte de l'application et la base de connaissance disponible.
        Pas de refus par trust gate ÔÇö le LLM raisonne et pr├®cise l'incertitude lui-m├¬me.
        """
        app_name = app_ctx.get("display_name", app_id) or app_id

        # Contexte KB disponible (proc├®dures, sch├®mas de tables, etc.)
        context_text = self.orchestrator.build_prompt_context(orch_result)
        context_blocks = orch_result.get("context_blocks", [])

        # ── Direct schema resolution from brasil_schema_knowledge (always first) ──
        # Bypasses Qdrant availability issues: if the symbol is a real BRASIL table,
        # inject its full describe_table() output regardless of vector search results.
        _direct_schema_text: str = ""
        try:
            from app.services.chatbot.brasil_schema_knowledge import (
                REAL_SQL_TABLES, TABLE_ALIAS_TO_CANONICAL, describe_table, is_real_table,
            )
            _sym_lower = symbol.lower().strip()
            _canonical = TABLE_ALIAS_TO_CANONICAL.get(_sym_lower, _sym_lower)
            if is_real_table(_canonical):
                _direct_schema_text = describe_table(_canonical)
                logger.info(f"[TechInference] Direct schema resolve: {_canonical} ({len(_direct_schema_text)} chars)")
        except Exception as _dsr_err:
            logger.debug(f"[TechInference] Direct schema resolve skipped: {_dsr_err}")

        # D├®tecter si la KB contient un sch├®ma de table pour ce symbole
        kb_has_schema = bool(_direct_schema_text) or any(
            b.get("type") == "partial_canonical"
            and symbol.lower() in (b.get("title") or "").lower()
            and len(b.get("content", "")) > 80
            for b in context_blocks
        )

        if _direct_schema_text:
            # Prefer the direct schema over the FR_WEAK context block (which may be empty)
            context_section = f"\n\n```\n{_direct_schema_text}\n```"
        elif context_text:
            context_section = f"\n\n{context_text[:4000]}"
        else:
            context_section = ""

        if kb_has_schema:
            # Mode KB-first : le sch├®ma est disponible, le LLM doit s'en servir
            inference_prompt = (
                f"Un ing├®nieur te demande : **{user_message}**\n\n"
                f"La base de connaissance BRASIL contient les informations suivantes sur `{symbol}` :\n"
                f"{context_section}\n\n"
                f"En te basant EXCLUSIVEMENT sur ces informations, r├®ponds de fa├ºon pr├®cise et structur├®e :\n"
                f"1. **Description** de la table (r├┤le m├®tier selon son nom et ses colonnes)\n"
                f"2. **Structure** : cl├® primaire, colonnes principales et leurs types\n"
                f"3. **Relations** ├®ventuelles avec d'autres tables (cl├®s ├®trang├¿res)\n"
                f"4. **Utilisation** probable dans l'application\n\n"
                f"IMPORTANT : Utilise uniquement les donn├®es du sch├®ma fourni ci-dessus. Ne g├®n├¿re pas d'informations hypoth├®tiques."
            )
            system_prompt_text = (
                f"Tu es un expert base de donn├®es de la plateforme {app_name} (Orange). "
                f"Quand un sch├®ma de table est fourni dans la base de connaissance, tu l'utilises INT├ëGRALEMENT et EXCLUSIVEMENT pour r├®pondre. "
                f"Tu ne g├®n├¿res jamais de colonnes ou de structures hypoth├®tiques si le sch├®ma r├®el est disponible. "
                f"Tu r├®ponds en fran├ºais technique pr├®cis et structur├®."
            )
        else:
            # Mode inf├®rence : pas de sch├®ma en KB, raisonner sur le nom
            inference_prompt = (
                f"Un ing├®nieur te demande : **{user_message}**\n\n"
                f"Le symbole technique en question est : `{symbol}`\n"
                f"Contexte de l'application : {app_name} (plateforme Orange Telecom, domaine acc├¿s r├®seau/DSLAM/VLAN/FTTH)."
                f"{context_section}\n\n"
                f"R├®ponds de fa├ºon structur├®e :\n"
                f"1. **Ce que tu sais avec certitude** (bas├® sur le nom, les conventions de nommage, le contexte)\n"
                f"2. **Ce que tu peux inf├®rer** (logique m├®tier probable selon le domaine)\n"
                f"3. **Ce qui reste incertain** (ce qu'il faudrait confirmer dans le code source)\n\n"
                f"Si le nom contient des indices clairs, exploite-les pleinement. Reste pr├®cis et technique."
            )
            system_prompt_text = (
                f"Tu es un expert technique de la plateforme {app_name} (Orange). "
                f"Quand on te demande ce qu'est un symbole technique (classe, service, interface, m├®thode, table), "
                f"tu analyses son nom, ses conventions de nommage et le contexte applicatif pour inf├®rer son r├┤le. "
                f"Tu structures clairement : ce qui est certain, ce qui est probable, ce qui est incertain. "
                f"Tu ne refuses jamais de r├®pondre ÔÇö tu signales l'incertitude dans ta r├®ponse. "
                f"Tu r├®ponds en fran├ºais technique pr├®cis."
            )

        try:
            response_text = await self.llm.generate(
                prompt=inference_prompt,
                system_prompt=system_prompt_text,
                max_tokens=600,
            )
        except Exception as e:
            logger.error(f"[TechInference] LLM error: {e}")
            response_text = f"Impossible de g├®n├®rer l'inf├®rence pour `{symbol}` : {e}"

        logger.info(f"[TechInference] Inf├®rence g├®n├®r├®e pour '{symbol}'")
        return ChatResponse(
            message=response_text,
            sources=(
                [{"title": b.get("title", ""), "type": b.get("source_type", "kb"), "score": b.get("trust_score", 0) / 100}
                 for b in orch_result.get("context_blocks", [])[:3]]
                if orch_result.get("context_blocks") else []
            ),
            suggestions=[
                f"O├╣ est utilis├® {symbol} dans l'application ?",
                "Y a-t-il un ticket Jira li├® ├á ce composant ?",
                "Quelles sont les d├®pendances de ce service ?",
            ],
            confidence=0.7,
            conversation_id=conversation_id,
            app_id=app_id,
            pipeline_mode="tech_inference",
            trust_score=65,
            trust_label="inference",
            diagnostic_available=False,
        )

    async def _handle_ml_analysis_intent(
        self,
        user_message: str,
        conversation_id: str,
        app_id: str,
        orch_result: dict,
    ) -> Optional[ChatResponse]:
        """
        Handle an ML analysis request:
        1. Try to get the exec-summary from the ML API (calls the endpoint function directly)
        2. Format a rich markdown response from the summary
        3. Fall back to Qdrant ml_insight if no live data
        """
        try:
            # ÔöÇÔöÇ Attempt live exec-summary ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
            summary = None
            try:
                from app.api.v1.endpoints.classification_ml import get_exec_summary, _uploaded_data
                if _uploaded_data is not None:
                    summary = await get_exec_summary(ai=True)
            except Exception as _e:
                logger.debug(f"[ML-Intent] exec-summary live call failed: {_e}")

            if summary:
                # Build response from live summary
                lines = [f"­ƒôè **Analyse ML Tickets BRASIL** ÔÇö {summary.date_range or 'derni├¿re p├®riode'}\n"]

                # KPIs
                lines.append(
                    f"­ƒÄ½ **{summary.volume}** tickets analys├®s | "
                    f"ÔÅ▒´©Å MTTR m├®dian : **{summary.mttr_med:.1f}j**"
                )

                # AI Narrative
                if summary.ai_narrative:
                    lines.append(f"\n---\n{summary.ai_narrative}")

                # Top causes
                if summary.top_causes:
                    lines.append("\n\n**­ƒöØ Top causes :**")
                    for c in summary.top_causes[:5]:
                        lines.append(f"  ÔÇó {c.get('label', c)} ÔÇö {c.get('count', '')} tickets")

                # Criticality scores
                if summary.criticality_scores:
                    lines.append("\n\n**ÔÜá´©Å Scores de criticit├® :**")
                    for cs in summary.criticality_scores[:4]:
                        badge = cs.category if isinstance(cs, dict) else cs.category
                        score = cs.score if isinstance(cs, dict) else cs.score
                        lines.append(f"  ÔÇó **{badge}** ÔÇö score {score:.0f}/100 {cs.rationale if hasattr(cs, 'rationale') else ''}")

                # Temporal anomalies
                if summary.temporal_anomalies:
                    lines.append("\n\n**­ƒôê Anomalies temporelles :**")
                    for a in summary.temporal_anomalies[:3]:
                        icon = "­ƒôê" if getattr(a, "direction", "") == "spike" else "­ƒôë"
                        lines.append(
                            f"  {icon} **{a.period}** ÔÇö {a.volume} tickets "
                            f"({'+' if a.delta_pct > 0 else ''}{a.delta_pct:.1f}%) ÔÇö {a.hypothesis}"
                        )

                # Top recommendations
                if summary.ai_recommendations:
                    lines.append("\n\n**­ƒÆí Recommandations prioritaires :**")
                    for rec in summary.ai_recommendations[:3]:
                        priority = rec.priority if hasattr(rec, "priority") else "P?"
                        action = rec.action if hasattr(rec, "action") else str(rec)
                        lines.append(f"  [{priority}] {action}")

                response_text = "\n".join(lines)
                return ChatResponse(
                    message=response_text,
                    sources=[{"title": "Module ML Classification", "type": "ml_insight", "score": 1.0}],
                    suggestions=[
                        "Exporter le rapport PDF complet",
                        "Injecter ces insights dans la base de connaissance",
                        "Afficher les anomalies temporelles d├®taill├®es",
                    ],
                    confidence=0.95,
                    conversation_id=conversation_id,
                    app_id=app_id,
                    pipeline_mode="ml_analysis",
                    trust_score=90,
                    trust_label="ml_live",
                    diagnostic_available=False,
                )

            # ÔöÇÔöÇ Fallback: search ml_insight in Qdrant ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
            context_blocks = orch_result.get("context_blocks", [])
            ml_blocks = [b for b in context_blocks if b.get("source_type") == "ml_insight"]
            if ml_blocks:
                content = ml_blocks[0].get("content", "")
                return ChatResponse(
                    message=f"­ƒôè **Insights ML (base de connaissance) :**\n\n{content}",
                    sources=[{"title": "ML Insight Qdrant", "type": "ml_insight", "score": 0.8}],
                    suggestions=[
                        "Aller dans le module ML pour voir les d├®tails",
                        "Y a-t-il des anomalies temporelles r├®centes ?",
                    ],
                    confidence=0.8,
                    conversation_id=conversation_id,
                    app_id=app_id,
                    pipeline_mode="ml_analysis",
                    trust_score=75,
                    trust_label="ml_qdrant",
                    diagnostic_available=False,
                )

            # ÔöÇÔöÇ No data available ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
            return ChatResponse(
                message=(
                    "­ƒôè **Analyse ML non disponible**\n\n"
                    "Aucune donn├®e de classification n'est actuellement charg├®e. "
                    "Pour obtenir une analyse ML compl├¿te :\n"
                    "1. Allez dans le **module Classification ML**\n"
                    "2. Uploadez votre CSV de tickets\n"
                    "3. Entra├«nez le mod├¿le\n"
                    "4. Cliquez sur *Injecter dans le Chatbot* depuis l'onglet R├®sum├® Ex├®cutif"
                ),
                sources=[],
                suggestions=[
                    "Acc├®der au module Classification ML",
                    "Comment fonctionne la classification automatique ?",
                ],
                confidence=0.0,
                conversation_id=conversation_id,
                app_id=app_id,
                pipeline_mode="ml_analysis",
                trust_score=0,
                trust_label="no_data",
                diagnostic_available=False,
            )

        except Exception as e:
            logger.error(f"[ML-Intent] _handle_ml_analysis_intent failed: {e}")
            return None

    def _extract_jira_keywords(self, user_message: str, orch_result: dict) -> str:
        """
        Extract keywords for JQL.
        When the message contains an explicit issue key (e.g. BRASIL-10861),
        return it verbatim so the search uses key = X directly.

        Also handles:
        - Year/date filters: "JIRA avec date 2022" → "created >= 2022-01-01 AND created <= 2022-12-31"
        - Relative date: "dernier mois", "cette semaine"
        - Pure technical terms and meaningful content words
        """
        # Priority: explicit issue key -> return as-is for direct key lookup
        issue_key = self._extract_issue_key(user_message)
        if issue_key:
            return issue_key

        # ── Year/date detection ─────────────────────────────────────────────
        # Detect 4-digit years like 2022, 2023, 2024
        year_match = re.search(r'\b(20[12][0-9])\b', user_message)
        if year_match:
            year = year_match.group(1)
            return f'created >= "{year}-01-01" AND created <= "{year}-12-31"'

        # Detect relative date phrases → JQL relative dates
        if re.search(r'\b(cette\s+semaine|cette\s+week)\b', user_message, re.IGNORECASE):
            return 'created >= -1w'
        if re.search(r'\b(ce\s+mois|mois[-\s]ci)\b', user_message, re.IGNORECASE):
            return 'created >= -4w'
        if re.search(r'\b(dernier\s+mois|mois\s+dernier)\b', user_message, re.IGNORECASE):
            return 'created >= -8w AND created <= -4w'
        if re.search(r'\b(aujourd.hui|aujourd\'hui|aujoud\'hui)\b', user_message, re.IGNORECASE):
            return 'created >= -1d'

        # ── Keyword extraction ──────────────────────────────────────────────
        # True stopwords: only pure functional words, NOT meaningful nouns/verbs
        stopwords = {
            # Articles & prepositions
            "le", "la", "les", "de", "du", "des", "un", "une", "et", "ou",
            "en", "au", "aux", "ce", "se", "sa", "son", "sur", "par", "pour",
            "avec", "dans", "est", "sont", "que", "qui", "il", "elle", "ils",
            "elles", "nous", "vous", "on", "me", "te", "lui", "leur", "leurs",
            "mon", "ton", "mes", "tes", "ses", "nos", "vos",
            # Jira meta-words (not content)
            "jira", "carte", "ticket", "tickets", "issue", "bogue", "anomalie",
            "existe", "creer", "ouvrir",
            # Polite filler words
            "peut", "peux", "pourrait", "pouvoir", "veux", "vouloir",
            "donner", "donne", "montrer", "montre", "afficher", "affiche",
            "chercher", "cherche", "trouver", "trouve",
            "liste", "lister",
            # Interrogative filler
            "quels", "quelle", "quelles", "quel", "quoi", "comment",
            # Short articles / determiners
            "the", "les",
        }

        # Words from user message (>=3 chars, non-stopwords)
        user_tokens = []
        seen_lower: set = set()
        for w in re.findall(r"[a-zA-Z\u00c0-\u00ff0-9_\-]{3,}", user_message):
            wl = w.lower()
            if wl not in stopwords and wl not in seen_lower:
                seen_lower.add(wl)
                user_tokens.append(w)

        # Words from procedure titles returned by the orchestrator
        proc_tokens: list = []
        for block in orch_result.get("context_blocks", []):
            title = block.get("title", "")
            for w in re.findall(r"[a-zA-Z\u00c0-\u00ff0-9_\-]{3,}", title):
                wl = w.lower()
                if wl not in stopwords and wl not in seen_lower:
                    seen_lower.add(wl)
                    proc_tokens.append(w)

        # Priority: user tokens first, then procedure tokens (max 6 total)
        combined = user_tokens[:4] + proc_tokens[:2]
        return " ".join(combined[:6])

    def _search_jira_tickets(self, keywords: str, max_results: int = 5, jql_override: str | None = None) -> list:
        """
        Search Jira tickets.
        When `keywords` is a single issue key (e.g. BRASIL-10861) use
        JQL `key = X` for an exact lookup.  Otherwise do a full-text search.
        Pass `jql_override` to use a completely custom JQL query.
        """
        try:
            from app.services.collector.jira_collector import jira_collector

            if not jira_collector.jira_client:
                if not jira_collector._connect():
                    logger.warning("[Jira] Client non disponible pour la recherche")
                    return []

            # Custom JQL override takes priority
            if jql_override:
                jql = jql_override
            else:
                safe_kw = keywords.strip()
                if not safe_kw:
                    return []

                # Direct key lookup when the whole keyword IS an issue key
                if self._JIRA_KEY_PATTERN.fullmatch(safe_kw):
                    jql = f'key = "{safe_kw}"'
                # JQL snippet from date/year detection (contains AND, >=, <=, -1w etc.)
                elif re.search(r'\b(created|updated|AND|>=|<=|-[0-9]+[dwmy])\b', safe_kw):
                    jql = f'project = BRASIL AND {safe_kw} ORDER BY updated DESC'
                else:
                    clean_kw = safe_kw.replace('"', '')
                    jql = (
                        f'project = BRASIL AND text ~ "{clean_kw}" '
                        f'ORDER BY updated DESC'
                    )
            logger.info(f"[Jira] JQL: {jql}")

            raw_issues = jira_collector.jira_client.search_issues(
                jql,
                maxResults=max_results,
                fields="summary,status,priority,assignee,created,updated,issuetype,description",
            )

            results = []
            for issue in raw_issues:
                fields = issue.fields
                results.append({
                    "key": issue.key,
                    "summary": fields.summary,
                    "description": getattr(fields, "description", "") or "",
                    "status": fields.status.name if hasattr(fields.status, "name") else str(fields.status),
                    "priority": (
                        fields.priority.name
                        if fields.priority and hasattr(fields.priority, "name")
                        else None
                    ),
                    "assignee": fields.assignee.displayName if fields.assignee else None,
                    "url": f"{jira_collector.jira_url}/browse/{issue.key}",
                })

            logger.info(f"[Jira] {len(results)} ticket(s) trouv├®(s) pour JQL: '{jql[:80]}'")
            return results

        except Exception as exc:
            logger.error(f"[Jira] Erreur recherche tickets: {exc}")
            return []

    def _format_jira_response(self, tickets: list, keywords: str) -> str:
        """Formate la liste de tickets Jira en r├®ponse lisible."""
        if not tickets:
            # Display a clean message — don't expose raw JQL or internal keywords
            if re.search(r'\b(created|updated|AND|>=|<=|-[0-9]+[dwmy])\b', keywords):
                return (
                    "🔍 Aucun ticket Jira trouvé dans le projet **BRASIL** "
                    "pour cette période.\n\n"
                    "Vous pouvez affiner la recherche ou vérifier la période demandée."
                )
            display_kw = keywords if not self._JIRA_KEY_PATTERN.fullmatch(keywords) else keywords
            return (
                f"🔍 Aucun ticket Jira trouvé dans le projet **BRASIL** "
                f"pour : *{display_kw}*.\n\n"
                f"Vous pouvez créer un nouveau ticket pour signaler ce problème."
            )

        # Build a display-friendly label for the keywords
        if re.search(r'\b(created|updated|AND|>=|<=|-[0-9]+[dwmy])\b', keywords):
            kw_display = "cette période"
        else:
            kw_display = keywords

        lines = [
            f"📋 **{len(tickets)} ticket(s) Jira trouvé(s)** dans BRASIL "
            f"pour *{kw_display}* :\n"
        ]
        for t in tickets:
            status_icon = {
                "Open": "­ƒö┤", "To Do": "ÔÜ¬", "In Progress": "­ƒƒí",
                "Resolved": "­ƒƒó", "Closed": "Ô£à", "Done": "Ô£à",
            }.get(t["status"], "­ƒöÁ")

            prio = f" ÔÇö priorit├® **{t['priority']}**" if t.get("priority") else ""
            assignee = f" (assign├® : {t['assignee']})" if t.get("assignee") else ""

            lines.append(
                f"{status_icon} **[{t['key']}]({t['url']})** ÔÇö {t['summary']}\n"
                f"   Statut : *{t['status']}*{prio}{assignee}"
            )

        lines.append(
            f"\n­ƒöù [Voir tous les tickets BRASIL]"
            f"({tickets[0]['url'].rsplit('/browse/', 1)[0]}/projects/BRASIL/issues)"
        )
        return "\n".join(lines)

    def _jira_followup_suggestions(self, issue_key, sub_intent):
        """Return context-aware follow-up suggestions per Jira sub-intent."""
        key = issue_key or "ce ticket"
        mapping = {
            "date_creation":   [f"Qui est assigné à {key} ?", f"Quel est le statut de {key} ?", "Tickets similaires ?"],
            "date_updated":    [f"Quelle est la description de {key} ?", f"Les commentaires de {key} ?", "Tickets similaires ?"],
            "assignee":        [f"Quel est le statut de {key} ?", f"Quelle est la priorité de {key} ?", "Tickets similaires ?"],
            "status":          [f"Quelle est la cause racine de {key} ?", f"Description complète de {key} ?", "Tickets similaires ?"],
            "priority":        [f"Qui est assigné à {key} ?", f"Quel est le statut de {key} ?", "Tickets haute priorité ouverts ?"],
            "description":     [f"Les commentaires de {key} ?", f"Tickets similaires à {key} ?", "Quelle est la procédure de résolution ?"],
            "comments":        [f"Quel est le statut de {key} ?", "Génère le message de clôture", "Procédure de résolution ?"],
            "similar":         ["Analyse les tickets similaires", f"Description de {key} ?", "Quelle est la procédure ?"],
            "open_tickets":    ["Tickets haute priorité ouverts ?", "Combien de tickets ouverts ?", "Assigner un ticket ?"],
            "priority_filter": ["Combien de tickets critiques ?", "Qui est assigné aux tickets critiques ?", "Procédure d'escalade ?"],
            "count":           ["Tickets haute priorité ouverts ?", "Tickets ouverts non assignés ?", "Évolution des tickets ?"],
            "explain":         ["Quelle est la procédure de résolution ?", "Tickets similaires ?", "Génère le message de clôture"],
            "search":          ["Afficher la procédure de résolution", "Créer un nouveau ticket Jira", "Tickets prioritaires ouverts ?"],
        }
        return mapping.get(sub_intent, ["Procédure de résolution ?", "Tickets similaires ?", "Résumé technique"])

    async def _handle_jira_intent(
        self,
        user_message: str,
        orch_result: dict,
        conversation_id: str,
        app_id: str,
        app_ctx: dict,
        history=None,
    ):
        """
        Handle a Jira intent with full sub-intent routing.
        Sub-intents: date_creation, date_updated, assignee, status, priority,
                     description, comments, similar, open_tickets, priority_filter,
                     count, explain, search.
        """
        issue_key = self._extract_issue_key(user_message)
        if not issue_key and history:
            for msg in reversed(history):
                found = self._extract_issue_key(msg.get("content", ""))
                if found:
                    issue_key = found
                    logger.info(f"[Jira] Cl\u00e9 trouv\u00e9e dans l'historique: {found}")
                    break

        sub_intent = self._detect_jira_sub_intent(user_message)
        keywords   = self._extract_jira_keywords(user_message, orch_result)
        if not keywords and issue_key:
            keywords = issue_key
        logger.info(f"[Jira] sub_intent={sub_intent}, key={issue_key}, kw='{keywords}'")

        # ── Field sub-intents ──────────────────────────────────────────────────
        if sub_intent in ("date_creation", "date_updated", "assignee", "status",
                          "priority", "description", "comments"):
            tickets = self._search_jira_tickets(keywords or (issue_key or ""), max_results=3)
            if not tickets:
                return ChatResponse(
                    message="Aucun ticket Jira trouv\u00e9 pour extraire ce champ.",
                    sources=[],
                    suggestions=self._jira_followup_suggestions(issue_key, sub_intent),
                    confidence=0.2, conversation_id=conversation_id, app_id=app_id,
                    pipeline_mode="jira", trust_score=20, trust_label="jira_no_result",
                    diagnostic_available=False,
                )
            ticket = tickets[0]
            field_map = {
                "date_creation": ("Date de cr\u00e9ation",       ticket.get("created",     "Non disponible")),
                "date_updated":  ("Derni\u00e8re mise \u00e0 jour", ticket.get("updated", "Non disponible")),
                "assignee":      ("Assign\u00e9 \u00e0",         ticket.get("assignee",    "Non assign\u00e9")),
                "status":        ("Statut",                        ticket.get("status",      "Inconnu")),
                "priority":      ("Priorit\u00e9",                ticket.get("priority",    "Non d\u00e9finie")),
                "description":   ("Description",                   (ticket.get("description") or "Aucune description")[:1500]),
                "comments":      ("Commentaires",                  ticket.get("comments",    "Aucun commentaire disponible")),
            }
            label, value = field_map[sub_intent]
            msg = (
                "\U0001f4cb **" + ticket["key"] + " \u2014 " + ticket["summary"] + "**\n"
                "\U0001f517 [Voir sur Jira](" + ticket["url"] + ")\n\n"
                "**" + label + "** : " + str(value)
            )
            return ChatResponse(
                message=msg,
                sources=[{"title": ticket["key"], "content": ticket["summary"],
                          "url": ticket["url"], "score": 1.0}],
                suggestions=self._jira_followup_suggestions(ticket["key"], sub_intent),
                confidence=1.0, conversation_id=conversation_id, app_id=app_id,
                pipeline_mode="jira", trust_score=90,
                trust_label="jira_" + sub_intent,
                diagnostic_available=False,
            )

        # ── Similar tickets ─────────────────────────────────────────────────
        if sub_intent == "similar":
            base_kw = keywords or (issue_key or "")
            tickets = self._search_jira_tickets(base_kw, max_results=8)
            if issue_key:
                tickets = [t for t in tickets if t["key"] != issue_key][:5]
            if tickets:
                header = "\U0001f4cb **Tickets similaires** (" + str(len(tickets)) + ") :\n"
                body   = "\n".join(
                    "\u2022 **" + t["key"] + "** \u2014 " + t["summary"] +
                    " *(Statut : " + t["status"] + ")*"
                    for t in tickets
                )
                msg = header + body
            else:
                msg = "Aucun ticket similaire trouv\u00e9."
            return ChatResponse(
                message=msg,
                sources=[{"title": t["key"], "content": t["summary"],
                          "url": t["url"], "score": 1.0} for t in tickets],
                suggestions=self._jira_followup_suggestions(issue_key, "similar"),
                confidence=1.0 if tickets else 0.2,
                conversation_id=conversation_id, app_id=app_id,
                pipeline_mode="jira",
                trust_score=85 if tickets else 20, trust_label="jira_similar",
                diagnostic_available=False,
            )

        # ── Open tickets ───────────────────────────────────────────────────────
        if sub_intent == "open_tickets":
            jql = "project = " + app_id + " AND status not in (Done, Closed) ORDER BY priority ASC"
            tickets = self._search_jira_tickets(keywords or "", max_results=10, jql_override=jql)
            if tickets:
                header = "\U0001f4cb **Tickets ouverts** (" + str(len(tickets)) + ") :\n"
                body   = "\n".join(
                    "\u2022 **" + t["key"] + "** | " + t["status"] +
                    " | " + str(t.get("priority", "?")) + " | " + t["summary"]
                    for t in tickets
                )
                msg = header + body
            else:
                msg = "Aucun ticket ouvert trouv\u00e9."
            return ChatResponse(
                message=msg,
                sources=[{"title": t["key"], "content": t["summary"],
                          "url": t["url"], "score": 1.0} for t in tickets],
                suggestions=self._jira_followup_suggestions(None, "open_tickets"),
                confidence=1.0, conversation_id=conversation_id, app_id=app_id,
                pipeline_mode="jira", trust_score=85, trust_label="jira_open",
                diagnostic_available=False,
            )

        # ── Priority filter ───────────────────────────────────────────────────
        if sub_intent == "priority_filter":
            jql = ("project = " + app_id +
                   " AND priority in (Highest, High, Critique, Bloquant)"
                   " AND status not in (Done, Closed) ORDER BY priority ASC")
            tickets = self._search_jira_tickets(keywords or "", max_results=10, jql_override=jql)
            if tickets:
                header = "\U0001f6a8 **Tickets haute priorit\u00e9 ouverts** (" + str(len(tickets)) + ") :\n"
                body   = "\n".join(
                    "\u2022 **" + t["key"] + "** | " +
                    str(t.get("priority", "?")) + " | " + t["summary"]
                    for t in tickets
                )
                msg = header + body
            else:
                msg = "Aucun ticket haute priorit\u00e9 ouvert trouv\u00e9."
            return ChatResponse(
                message=msg,
                sources=[{"title": t["key"], "content": t["summary"],
                          "url": t["url"], "score": 1.0} for t in tickets],
                suggestions=self._jira_followup_suggestions(None, "priority_filter"),
                confidence=1.0, conversation_id=conversation_id, app_id=app_id,
                pipeline_mode="jira", trust_score=85, trust_label="jira_priority",
                diagnostic_available=False,
            )

        # ── Count ──────────────────────────────────────────────────────────────
        if sub_intent == "count":
            import re as _re
            year_m = _re.search(r"\b(20\d{2})\b", user_message)
            if year_m:
                y = year_m.group(1)
                year_filter = " AND created >= '" + y + "-01-01' AND created <= '" + y + "-12-31'"
                period = "en " + y
            else:
                year_filter = ""
                period = "actuellement"
            jql = "project = " + app_id + " AND status not in (Done, Closed)" + year_filter
            tickets = self._search_jira_tickets(keywords or "", max_results=200, jql_override=jql)
            msg = "\U0001f4ca Il y a **" + str(len(tickets)) + " ticket(s) ouvert(s)** " + period + " dans le projet " + app_id + "."
            return ChatResponse(
                message=msg, sources=[],
                suggestions=self._jira_followup_suggestions(None, "count"),
                confidence=1.0, conversation_id=conversation_id, app_id=app_id,
                pipeline_mode="jira", trust_score=85, trust_label="jira_count",
                diagnostic_available=False,
            )

        # ── Explain path (LLM reformulation) ──────────────────────────────────────
        wants_explanation = sub_intent == "explain" or bool(
            self._EXPLAIN_VERBS.search(user_message)
        )
        tickets = self._search_jira_tickets(keywords, max_results=5)

        if wants_explanation and tickets:
            ticket = tickets[0]
            description = ticket.get("description") or "(aucune description)"
            description = description[:2000]
            explain_prompt = (
                "Voici le contenu de la carte Jira **" + ticket["key"] + "** :\n\n"
                "**Titre** : " + ticket["summary"] + "\n"
                "**Statut** : " + ticket["status"] + "\n"
                "**Description** :\n" + description + "\n\n"
                "Reformule et explique ce ticket en fran\u00e7ais clair et structur\u00e9 "
                "pour un ing\u00e9nieur N3 :\n"
                "(1) Contexte / Syst\u00e8me impact\u00e9\n"
                "(2) Probl\u00e8me d\u00e9crit\n"
                "(3) Actions d\u00e9j\u00e0 effectu\u00e9es si mentionn\u00e9es\n"
                "(4) Ce qui reste \u00e0 faire selon toi\n"
                "Sois factuel. Ne compl\u00e8te que ce qui est pr\u00e9sent dans le ticket."
            )
            try:
                explanation = await self.llm.generate(
                    prompt=explain_prompt,
                    system_prompt=(
                        "Tu es un assistant de support N3 (Orange Telecom). "
                        "Tu reformules des tickets Jira en langage technique clair. "
                        "Ne fabrique aucune information absente du ticket fourni."
                    ),
                    max_tokens=600,
                )
            except Exception as e:
                logger.error(f"[Jira] LLM explain error: {e}")
                explanation = "Impossible de g\u00e9n\u00e9rer l'explication : " + str(e)

            response_text = (
                "\U0001f4cb **Explication de " + ticket["key"] + " \u2014 " + ticket["summary"] + "**\n"
                "\U0001f517 [Voir sur Jira](" + ticket["url"] + ") | Statut : *" + ticket["status"] + "*\n\n"
                + explanation
            )
            return ChatResponse(
                message=response_text,
                sources=[{"title": ticket["key"], "content": ticket["summary"],
                          "url": ticket["url"], "score": 1.0}],
                suggestions=self._jira_followup_suggestions(ticket["key"], "explain"),
                confidence=1.0, conversation_id=conversation_id, app_id=app_id,
                pipeline_mode=orch_result.get("mode"),
                trust_score=90, trust_label="jira_explain",
                diagnostic_available=False,
            )

        # ── Standard search result ────────────────────────────────────────────────
        response_text = self._format_jira_response(tickets, keywords)
        return ChatResponse(
            message=response_text,
            sources=[
                {"title": t["key"], "content": t["summary"],
                 "url": t["url"], "score": 1.0}
                for t in tickets
            ],
            suggestions=self._jira_followup_suggestions(None, "search"),
            confidence=1.0 if tickets else 0.3,
            conversation_id=conversation_id, app_id=app_id,
            pipeline_mode=orch_result.get("mode"),
            trust_score=90 if tickets else 30, trust_label="jira_search",
            diagnostic_available=False,
        )


    async def get_conversation_history(self, conversation_id: str):
        """Retrieve conversation history"""
        # TODO: Implement avec DB
        pass

    async def save_feedback(self, conversation_id: str, message_id: str, feedback: dict):
        """Save user feedback for improvement"""
        # TODO: Implement -- feedback alimente le TrustEngine
        pass
