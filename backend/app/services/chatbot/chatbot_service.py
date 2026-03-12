"""
Chatbot Service
Handles conversational AI logic — délègue l'intelligence à l'IntelligenceOrchestrator
Intègre la couche NLP diagnostique (anti-hallucination, slot-filling, trust gate).
"""
from typing import Optional, List, Dict
import re
import uuid
from datetime import datetime
from app.schemas.chatbot import ChatMessage, ChatResponse
from app.core.llm_client import llm_client
from app.core.logging import get_logger
from app.services.orchestrator import intelligence_orchestrator
from app.models.user import ChatConversation, ChatMessage as DBChatMessage

# ── NLP Diagnostic Behavior Layer ─────────────────────────────────────────
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

# ── Incident Context Guard ─────────────────────────────────────────────────
try:
    from app.services.chatbot.incident_context_guard import IncidentContextGuard
    _CONTEXT_GUARD_AVAILABLE = True
except ImportError:
    _CONTEXT_GUARD_AVAILABLE = False
    class IncidentContextGuard:  # type: ignore
        @classmethod
        def from_ticket_text(cls, *a, **kw): return cls()
        def filter_context_blocks(self, blocks): return blocks

try:
    from app.services.diagnostic.diagnostic_engine import (
        diagnostic_engine,
        DiagnosticConfidence,
    )
    _DIAGNOSTIC_ENGINE_AVAILABLE = True
except ImportError:
    _DIAGNOSTIC_ENGINE_AVAILABLE = False

logger = get_logger(__name__)


class ChatbotService:
    """
    Service chatbot context-aware multi-tenant.
    DÃ©lÃ¨gue la recherche de connaissance Ã  l'IntelligenceOrchestrator
    qui route vers le bon pipeline selon le profil de l'application.
    """

    def __init__(self):
        self.llm = llm_client
        self.orchestrator = intelligence_orchestrator
        logger.info("[OK] ChatbotService initialisé avec IntelligenceOrchestrator")
        if _NLP_AVAILABLE:
            logger.info("[OK] Couche NLP diagnostique activée (anti-hallucination + slot-filling)")
        else:
            logger.warning("[WARN] Couche NLP diagnostique indisponible — mode dégradé")
        if _DIAGNOSTIC_ENGINE_AVAILABLE:
            logger.info("[OK] Moteur diagnostic N3 activé (log patterns + procédures N3)")
        else:
            logger.warning("[WARN] Moteur diagnostic N3 indisponible — mode dégradé")

    async def process_message(self, message: ChatMessage, db=None) -> ChatResponse:
        """
        Traite un message utilisateur via le pipeline adaptÃ© Ã  l'application.

        Flux :
        1. Orchestrateur rÃ©sout le profil app â†’ pipeline adaptÃ©
        2. Pipeline recherche et score le contexte
        3. LLM gÃ©nÃ¨re la rÃ©ponse avec le contexte structurÃ©
        4. RÃ©ponse enrichie avec mÃ©tadonnÃ©es trust
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
                        f"[State] Loop détecté: question posée {repetition_count}x — "
                        f"escalade intelligente déclenchée (override={intent_override})"
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
                            "Créer une FR pour documenter ce cas",
                            "Rechercher des tickets Jira similaires",
                            "Escalader vers l'équipe N3 avec les logs",
                        ],
                        confidence=0.0,
                        conversation_id=conversation_id,
                        app_id=message.app_id,
                        pipeline_mode="ESCALATION_LOOP",
                        trust_score=0,
                        trust_label="knowledge_gap",
                        diagnostic_available=False,
                    )

            # 1d. Detect phase transitions
            new_phase = detect_phase_transition(conv_state.phase, message.content)
            if new_phase and new_phase != conv_state.phase:
                logger.info(f"[State] Phase transition: {conv_state.phase.value} → {new_phase.value}")
                conv_state.phase = new_phase

            # 1e. Lock root cause if user confirms it in this message
            rc = extract_root_cause(message.content)
            if rc and conv_state.confirmed_root_cause is None:
                conv_state.confirmed_root_cause = rc
                conv_state.resolution_confirmed = True
                logger.info(f"[State] Root cause locked: '{rc[:80]}'")

            # 1f. Detect audience
            conv_state.audience = detect_audience(message.content, conv_state.phase)

            # 1g. Short-circuit for CLOSING phase — no RAG needed
            if conv_state.phase == ConversationPhase.CLOSING:
                logger.info("[State] Phase CLOSING — bypassing RAG, generating closing message")
                return await self._handle_closing_phase(
                    message=message,
                    conv_state=conv_state,
                    conversation_id=conversation_id,
                    history=history,
                    db=db,
                )

            # 1g-bis. Short-circuit for SUMMARIZE intent — bypass RAG entirely
            if intent_override == "summarize":
                logger.info("[Chatbot] Intent SUMMARIZE detected — bypassing RAG, generating management summary")
                return await self._handle_summarize_intent(
                    message=message,
                    history=history,
                    conversation_id=conversation_id,
                )

            # 1h. Reformuler la requête si question de suivi (ex: "et ce ticket ?" → "ticket DSLAM suppression")
            effective_query = await self._resolve_query(message.content, history)
            if effective_query != message.content:
                logger.info(f"[Chatbot] Requête reformulée: '{message.content[:40]}' → '{effective_query[:60]}'")

            # 1. Déléguer à l'orchestrateur
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

            context_text = self.orchestrator.build_prompt_context(orch_result)

            # 3. Récupérer les garde-fous de réponse (avant off_topic pour avoir app_ctx)
            guard = self.orchestrator.get_response_guard(orch_result)
            llm_instructions = orch_result.get("llm_instructions", "")
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

            # 2b. Cas hors-contexte : réponse directe sans base de connaissance
            if orch_result.get("off_topic"):
                response_text = await self.llm.generate(
                    prompt=message.content,
                    system_prompt=(
                        f"Tu es un assistant support pour l'application {app_ctx.get('display_name', message.app_id)} (Orange). "
                        f"Réponds de façon concise et naturelle. "
                        f"Si c'est une salutation, réponds poliment et invite l'utilisateur à décrire son problème technique."
                    ),
                )
                return ChatResponse(
                    message=response_text,
                    sources=[],
                    suggestions=["Décrivez votre problème technique", "Indiquez le code d'erreur rencontré", "Précisez l'équipement concerné"],
                    confidence=0.0,
                    conversation_id=conversation_id,
                    app_id=message.app_id,
                    pipeline_mode=orch_result.get("mode"),
                    trust_score=0,
                    trust_label="off_topic",
                    diagnostic_available=False,
                )

            # 2c. Détection intention ML Analysis : "causes principales", "analyse ML", etc.
            if self._detect_ml_analysis_intent(message.content):
                ml_response = await self._handle_ml_analysis_intent(
                    user_message=message.content,
                    conversation_id=conversation_id,
                    app_id=message.app_id,
                    orch_result=orch_result,
                )
                if ml_response:
                    return ml_response

            # 2c-bis. Détection recherche ND dans les logs
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

            # 2c-ter. Détection recherche équipement dans les logs (DSLAM, NRO, ONT, châssis)
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

            # 2d. Détection intention Jira : "y a-t-il une carte Jira ?", "ticket similaire ?", etc.
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

            # 2e. Détection intention inférence technique : "c'est quoi ManageTechnicalConfigurationService"
            tech_symbol = self._detect_tech_inference_intent(message.content)
            if tech_symbol:
                logger.info(f"[TechInference] Symbole détecté: '{tech_symbol}'")
                return await self._handle_tech_inference_intent(
                    symbol=tech_symbol,
                    user_message=message.content,
                    orch_result=orch_result,
                    conversation_id=conversation_id,
                    app_id=message.app_id,
                    app_ctx=app_ctx,
                )

            # 2f. NLP Enrichment — analyse structurée du message entrant
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
                        logger.info(f"[Chatbot][Memory] Procédure antérieure détectée: {prior_proc}")
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
                    # ── Intent Override: force correct intent when ML classifier misses
                    # well-known signal patterns (script blocked, DB table query, etc.).
                    # This is general — not specific to a single case.
                    if intent_override and structured_ticket:
                        original_intent = structured_ticket.incident_type
                        structured_ticket.incident_type = intent_override
                        logger.info(
                            f"[Chatbot][IntentOverride] '{original_intent}' → '{intent_override}' "
                            f"(signal pattern matched)"
                        )
                except Exception as nlp_err:
                    logger.warning(f"[Chatbot][NLP] Enrichissement échoué: {nlp_err}")

            # 2e. Trust gate — refuse if knowledge is insufficient (score < 40)
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
                        logger.info(f"[Chatbot][Trust] Refus gracieux — {trust_reason}")
                        return ChatResponse(
                            message=refusal_msg,
                            sources=[],
                            suggestions=[
                                "Vérifier l'existence d'une FR pour ce cas",
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
                            f"bloc(s) KB disponible(s) — passage au LLM maintenu"
                        )
                except Exception as tg_err:
                    logger.warning(f"[Chatbot][Trust] Trust gate error: {tg_err}")

            # 2f. Diagnostic Engine N3 — raisonnement sur exception + procédures
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
                                    "title": f"Diagnostic N3 — {diagnostic_result.procedure_title or diagnostic_result.incident_type}",
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
                        logger.warning(f"[Chatbot][NLP] System prompt enrichissement échoué: {sp_err}")
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
                    # Intent summarize détecté → prompt spécialisé résumé pour hiérarchie
                    _is_summarize = (intent_override == "summarize") or (
                        structured_ticket and structured_ticket.incident_type in ("summarize", "ticket_summary")
                    )
                    if _is_summarize:
                        system_prompt = (
                            f"Tu es un assistant support N3 pour l'application {app_ctx.get('display_name', message.app_id)} (Orange). "
                            f"L'ingénieur a besoin d'un résumé structuré de la situation pour le communiquer à sa hiérarchie. "
                            f"RÈGLES IMPÉRATIVES :\n"
                            f"- Utilise UNIQUEMENT les informations présentes dans l'historique de la conversation.\n"
                            f"- Ne génère PAS de nouvelles hypothèses ou procédures.\n"
                            f"- Ne mentionne PAS de systèmes qui ne sont pas dans l'historique.\n"
                            f"- Structure : (1) Situation client, (2) Anomalies détectées, (3) Diagnostic, (4) Actions recommandées / escalade.\n"
                            f"- Ton professionnel, concis (8-12 lignes max). Réponds en français."
                            + (f"\n{ctx_summary}" if ctx_summary else "")
                        )
                    else:
                        system_prompt = (
                            f"Tu es un assistant support expert pour l'application {app_ctx.get('display_name', message.app_id)} (Orange). "
                            f"Réponds à la question de l'utilisateur en t'appuyant sur l'historique de la conversation ci-dessous. "
                            f"Sois précis et concis. Si la réponse n'est pas dans l'historique, dis-le clairement."
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
                        f"Reponds de facon generique en recommandant une investigation manuelle."
                    )

            # 5. Appel LLM - contexte conversationnel résumé dans system_prompt
            llm_result = await self.llm.generate(
                prompt=full_prompt,
                system_prompt=system_prompt,
                with_thinking=True,
            )
            if isinstance(llm_result, tuple):
                response_text, thinking_content = llm_result
            else:
                response_text, thinking_content = llm_result, None

            # 6. Extraire trust
            trust_score_obj = orch_result.get("trust_score")
            trust_score = trust_score_obj.score if trust_score_obj else 0
            trust_label = trust_score_obj.label.value if trust_score_obj else "insufficient"

            # 7. Construire les sources — normalisation pour le frontend
            raw_sources = orch_result.get("sources", [])
            sources = []
            for s in raw_sources:
                # Résoudre le nom affiché
                name = (
                    s.get("name")
                    or s.get("title")
                    or s.get("source_id")
                    or s.get("id")
                    or "Source inconnue"
                )
                # Résoudre le type affiché
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
                            f"[Chatbot][Validation] Tâche N3 créée: #{task_id} "
                            f"(trust={trust_score}/100, inc={_inc_type})"
                        )
                except Exception as _ve:
                    logger.debug(f"[Chatbot][Validation] Skip auto-task: {_ve}")

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
    # Phase CLOSING — no RAG, root-cause-locked closing message generator
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

        system_prompt = (
            f"Tu es un assistant support N3 pour l'application {app_name} (Orange Telecom).\n"
            f"L'ingénieur demande un résumé structuré de la situation pour le communiquer à sa hiérarchie.\n\n"
            f"RÈGLES ABSOLUES :\n"
            f"1. Utilise UNIQUEMENT les informations présentes dans l'historique ci-dessous.\n"
            f"2. Ne génère AUCUNE nouvelle hypothèse, procédure ou requête SQL.\n"
            f"3. Ne mentionne AUCUN système informatique absent de l'historique.\n"
            f"4. Ne génère JAMAIS d'identifiant de procédure inventé (ex: BRASIL-PROC-XXXX).\n"
            f"5. Structure en 4 sections numérotées :\n"
            f"   1. Situation client (qui, quoi, quand)\n"
            f"   2. Anomalies détectées (symptômes observés)\n"
            f"   3. Diagnostic (cause racine identifiée ou suspectée)\n"
            f"   4. Actions recommandées / statut escalade\n"
            f"6. Ton professionnel, concis (10 lignes max). Réponds uniquement en français.\n\n"
            f"HISTORIQUE DE LA CONVERSATION :\n"
            f"{history_text}"
        )

        prompt = f"Génère le résumé pour la hiérarchie."

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
                "Je n'ai pas pu générer le résumé. "
                "Veuillez réessayer ou rédiger manuellement un résumé basé sur l'historique."
            )
            thinking_content = None

        return ChatResponse(
            message=response_text,
            thinking_content=thinking_content,
            sources=[],
            suggestions=[
                "Envoyer ce résumé par email au N+1",
                "Créer un ticket de suivi",
                "Escalader vers l'équipe spécialisée si non résolu",
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
        """
        audience = conv_state.audience or "depositor"
        root_cause = (
            conv_state.confirmed_root_cause
            or extract_root_cause(message.content)
            or "cause identifiée au cours de l'investigation"
        )
        procedure = conv_state.confirmed_procedure_id or "procédure manuelle"
        app_name = message.app_id

        closing_system_prompt = (
            f"{PERSONA_INSTRUCTION}\n"
            f"⛔ MODE CLÔTURE — AUCUN DIAGNOSTIC, AUCUNE RECHERCHE KB.\n\n"
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
            response_text = (
                f"**Résumé technique N3**\n"
                f"Incident : {app_name} — Cause : {root_cause}\n\n"
                f"**Message dépositaire**\n"
                f"Bonjour, votre demande a été traitée et le problème est résolu. "
                f"La cause était liée à {root_cause}. Cordialement."
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
                "Créer une FR préventive pour ce type d'incident",
                "Notifier l'équipe de la résolution",
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
                "Fournir les logs dÃ©taillÃ©s pour affiner l'analyse",
                "PrÃ©ciser le code d'erreur exact",
                "DÃ©crire les Ã©tapes qui ont prÃ©cÃ©dÃ© l'incident",
            ]
        if mode == "FR_RICH":
            return [
                "Afficher la procÃ©dure complÃ¨te de rÃ©solution",
                "Quels sont les risques de cette intervention ?",
                "Existe-t-il des cas similaires rÃ©solus ?",
            ]
        if mode == "FR_WEAK":
            return [
                "Valider cette procÃ©dure avec l'Ã©quipe N3",
                "Consulter les tickets similaires",
                "Quelles vÃ©rifications prÃ©alables effectuer ?",
            ]
        # LOG_BASED
        return [
            "Analyser les logs dÃ©taillÃ©s",
            "VÃ©rifier les dÃ©pendances du module",
            "Consulter l'historique des incidents similaires",
        ]

    # -----------------------------------------------------------------------
    # Mémoire conversationnelle
    # -----------------------------------------------------------------------

    def _load_history(self, message: ChatMessage, db) -> List[Dict]:
        """
        Charge les N derniers messages d'une conversation depuis la DB.
        Retourne une liste [{"role": "user"|"assistant", "content": "..."}].
        Priorise l'historique envoyé directement par le frontend (message.conversation_history).
        """
        # Priorité 1 : historique fourni par le frontend — on garde 8 messages max (4 échanges)
        if message.conversation_history:
            return message.conversation_history[-8:]

        # Priorité 2 : charger depuis la DB si conversation_id est un entier
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
                .order_by(DBChatMessage.timestamp.desc())  # plus récents d'abord
                .limit(8)  # 4 échanges suffisent pour la reformulation
                .all()
            )
            history = [
                {"role": row.role, "content": row.content}
                for row in reversed(rows)  # remettre dans l'ordre chronologique
                if row.role in ("user", "assistant") and row.content
            ]
            if history:
                logger.info(f"[Chatbot] Historique chargé : {len(history)} messages pour conv#{conv_id_int}")
            return history
        except Exception as e:
            logger.warning(f"[Chatbot] Impossible de charger l'historique: {e}")
            return []

    # Patterns d'entités techniques à extraire pour le résumé de contexte
    _ENTITY_PATTERNS = re.compile(
        r"\b("
        r"DSLAM\w*|VLAN\w*|ONT\w*|OLT\w*|DSL\w*|GPON\w*|ADSL\w*|VDSL\w*"  # équipements réseau
        r"|FR[:\s]?\d+|BR\d+|BRASIL[-\s]?\d+"  # références procédures/tickets
        r"|[A-Z]{2,}[-_]?\d{3,}"  # codes erreur (ex: B4002, ERR_1300)
        r"|erreur\s+\d+|code\s+\d+|error\s+\d+"  # erreurs numériques
        r"|suppression|modification|création|activation|désactivation|migration"  # actions
        r"|impossible|échec|bloqué|timeout|unreachable"  # symptômes
        r")",
        re.IGNORECASE,
    )

    def _build_context_summary(self, history: List[Dict]) -> str:
        """
        Extrait les entités techniques clés des derniers échanges en une ligne compacte.
        Exemple : "Contexte: suppression DSLAM280, procédure FR:189, erreur impossible"
        Injecté dans le system_prompt — coûte ~20 tokens au lieu de 400+.
        """
        if not history:
            return ""

        # Concaténer le texte de tout l'historique (tronqué)
        full_text = " ".join(
            m["content"][:300] for m in history if m.get("content")
        )

        entities = self._ENTITY_PATTERNS.findall(full_text)
        # Dédupliquer en préservant l'ordre
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

    # Patterns détectant une question de suivi (référence implicite au contexte précédent)
    _FOLLOWUP_PATTERNS = re.compile(
        # Connecteurs de suivi : "et", "mais", "donc", "alors" seuls en début de phrase
        r"(^(et|mais|donc|alors|pourquoi|quand|où|quel|quelle|quels)\b"
        # "comment" seulement avec un référent contextuel explicite (pas "comment je peux extraire...")
        r"|^comment\s+(ça|cela|ce|cet|cette|il|elle|on|faire\s+ça|résoudre\s+ça|corriger\s+ça|débloquer\s+ça)\b"
        # Référents déictiques ("ce problème", "cela", "cet/cette", etc.)
        r"|\b(ce (problème|truc|bug|cas|point|ticket|erreur)|cela|cet?te)\b"
        r"|\b(ici|là|[làça])\b"
        r"|\b(pour (ce|cela))\b"
        r"|^(y a[- ]t[-\s]?il|existe[- ]t[-\s]?il|c'est quoi|qu'est[-\s]?ce)"
        r"|^(tu peux|peux[- ]tu|pourrais[- ]tu|donne[- ]moi|montre[- ]moi)\b"
        r"|(ticket|carte|issue|jira)\s*(pour|de|lié|correspondant|similaire))",
        re.IGNORECASE,
    )

    async def _resolve_query(self, query: str, history: List[Dict]) -> str:
        """
        Si la question semble être un suivi (référence implicite au contexte précédent),
        demande au LLM de la reformuler en requête autonome avant la recherche vectorielle.
        """
        if not history or not self._FOLLOWUP_PATTERNS.search(query):
            return query

        # Préparer un résumé de l'historique récent
        recent = history[-6:]
        history_text = "\n".join(
            f"{m['role'].upper()}: {m['content'][:200]}" for m in recent
        )

        reformulation_prompt = (
            f"Historique de la conversation :\n{history_text}\n\n"
            f"Nouvelle question : {query}\n\n"
            f"Reformule cette question en une requête de recherche autonome et complète (max 20 mots), "
            f"en français, sans faire référence à 'ce problème' ou 'cela'. "
            f"Réponds UNIQUEMENT avec la requête reformulée, sans guillemets ni explication."
        )
        try:
            reformulated = await self.llm.generate(
                prompt=reformulation_prompt,
                system_prompt="Tu es un assistant de reformulation. Tu reformules des questions de suivi en requêtes autonomes.",
                max_tokens=60,
            )
            reformulated = reformulated.strip().strip('"').strip("'").strip()
            # Sécurité : si le LLM renvoie une réponse trop longue, garder l'original
            if reformulated and len(reformulated) < 200:
                return reformulated
        except Exception as e:
            logger.warning(f"[Chatbot] Reformulation échouée: {e}")

        return query

    # -----------------------------------------------------------------------
    # Méthodes Jira
    # -----------------------------------------------------------------------

    _JIRA_INTENT_PATTERNS = re.compile(
        r"(\bjira\b|carte\s+jira"
        r"|(?:existe[- ]t[-\s]il|y\s*[\u00e0a']\s*t[-\s]il)\s+(un|une|des)\s+(ticket|carte|issue|bogue)\s+jira"
        r"|cr[e\u00e9]+[e\u00e9]+r?\s+(un|une)\s+(ticket|carte|issue)\s+jira"
        r"|ouvrir?\s+(un|une)\s+(ticket|carte|issue)\s+jira"
        r"|signaler?\s+[\u00e0a]\s+jira"
        r"|lien\s+jira|r\u00e9f\u00e9rence\s+jira)",
        re.IGNORECASE,
    )

    # Detects a standalone Jira issue key like BRASIL-10861 anywhere in the message
    _JIRA_KEY_PATTERN = re.compile(r"\b([A-Z][A-Z0-9_]+-\d+)\b")

    # Verbs that indicate the user wants an explanation of a specific issue
    _EXPLAIN_VERBS = re.compile(
        r"\b(explique|reformule|r\u00e9sume|d\u00e9crypte|analyse|interpr\u00e8te|que\s+dit|d\u00e9taille)\b",
        re.IGNORECASE,
    )

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

    # ── ND Log Search intent ─────────────────────────────────────────────────────
    _ND_PATTERN = re.compile(
        r"(?:nd|num[eé]ro\s+de\s+demande|num[eé]ro\s+nd|demande)[\s:=#]*"
        r"(0?[0-9]{8,10})",
        re.IGNORECASE,
    )
    _ND_RAW_PATTERN = re.compile(r"\b(0[0-9]{9})\b")  # 10-digit starting with 0

    def _extract_nd_number(self, text: str) -> Optional[str]:
        """Extrait un numéro ND du texte. Retourne le numéro sans le 0 initial (format interne)."""
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
        """Recherche un ND dans les fichiers log indexés et retourne une analyse structurée."""
        import re as _re
        from pathlib import Path
        from collections import Counter

        # Locate log files to search — prioritise recently uploaded files
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

        # ── Build structured summary ───────────────────────────────────────────────
        ETAT = {"C": "Commandé", "E": "En service", "A": "À venir", "S": "Supprimé", "R": "Résilié", "D": "Désactivé"}
        EPT  = {"ES": "En service", "AFF": "Affecté", "LIB": "Libéré"}

        first = events[0]
        last  = events[-1]
        timestamps = Counter(e["ts"][:19] for e in events if e["ts"])
        sts        = Counter(e["st"]  for e in events if e["st"])
        trans      = Counter(f"{e['avant']}→{e['etat']}" for e in events)
        epts       = Counter(e["etatEpt"] for e in events if e["etatEpt"])

        batches_str = "\n".join(
            f"  - {ts}  ×{cnt} mouvement(s)"
            for ts, cnt in sorted(timestamps.items())
        )
        sts_str = "\n".join(f"  - {k}: ×{v}" for k, v in sts.most_common(6))
        trans_str = "\n".join(
            f"  - {p.split('→')[0]}({ETAT.get(p.split('→')[0],'?')}) → "
            f"{p.split('→')[1]}({ETAT.get(p.split('→')[1],'?')}): ×{c}"
            for p, c in trans.most_common()
        )
        ept_str = ", ".join(f"{k}({EPT.get(k,k)}): ×{v}" for k, v in epts.most_common())

        context = f"""ANALYSE ND 0{nd_number} — {found_in[0] if found_in else 'logs'}

CLIENT     : {first['nom_cli']} (farId: {first['far_id']})
DSLAM      : {first['dslam']}
NRO        : {first['nro']}
MOUVEMENTS : {len(events)} au total
FICHIER    : {', '.join(found_in)}

CHRONOLOGIE DES BATCHS:
{batches_str}

SERVICES TECHNIQUES CONCERNÉS:
{sts_str}

TRANSITIONS D'ÉTAT:
{trans_str}

ÉTATS EPT: {ept_str}

PREMIER MOUVEMENT: {first['ts']} | {first['type']} | {first['st']} | {first['avant']}→{first['etat']}
DERNIER MOUVEMENT: {last['ts']}  | {last['type']}  | {last['st']} | {last['avant']}→{last['etat']} | etatEpt={last['etatEpt']}
"""

        prompt = f"""Tu es un expert BRASIL Network Management. Voici les données brutes extraites des logs pour le ND 0{nd_number}.

Utilise UNIQUEMENT ces données pour répondre. Ne fabrique rien.

{context}

Question: {user_message}

Réponds en français de façon structurée :
1. Identité du client et équipement
2. Chronologie des événements
3. Services techniques impactés
4. Diagnostic / interprétation de l'état actuel
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
                f"Y a-t-il des erreurs associées au DSLAM {first['dslam']} ?",
                "Rechercher la FR associée à ce type de migration",
            ],
            diagnostic_available=False,
        )

    # ── Equipment Log Search intent ──────────────────────────────────────────
    # Détecte : DSLAM (DS[A-Z]{2,5}[0-9]{2,4}), NRO (libellé), ONT (numSerie), châssis
    _EQUIP_DSLAM_PATTERN = re.compile(
        r"\b(DS[A-Z]{2,6}[0-9]{2,4}(?:-C[0-9]+)?)\b",
        re.IGNORECASE,
    )
    _EQUIP_CHASSIS_PATTERN = re.compile(
        r"\b(DS[A-Z]{2,6}[0-9]{2,4}-C[0-9]+)\b",
        re.IGNORECASE,
    )
    _EQUIP_ONT_PATTERN = re.compile(
        r"(?:ont|num[eé]ro\s+ont|serie\s+ont|numSerie)[:\s]+([A-Z0-9]{10,16})\b",
        re.IGNORECASE,
    )
    _EQUIP_NIP_PATTERN = re.compile(
        r"\b(BSAU[A-Z0-9]+|NENIC[A-Z0-9]+)\b",
        re.IGNORECASE,
    )
    _EQUIP_INTENT_PATTERN = re.compile(
        r"\b(dslam|nro|ont|chassis|ch[aâ]ssis|[eé]quipement|nip|bsau|nenic"
        r"|port|carte|alv[eé]ole|gestionnaire|adresse\s+ip)\b",
        re.IGNORECASE,
    )

    # Patterns qui indiquent une question sur une PROCÉDURE, pas sur un équipement réel
    _PROC_CONTEXT_PATTERN = re.compile(
        r"\b(procedure|proc[eé]dure|FR\s*\d+|exception|comment|[eé]tape|d[eé]bloquer"
        r"|impossible|suppression|cause|racine|r[eé]soudre|r[eé]soudre|escalader"
        r"|v[eé]rifier|coh[eé]rence|analyser|probl[eé]me|incident|diagnos)",
        re.IGNORECASE,
    )
    # Noms d'exceptions Java/BRASIL (CamelCase se terminant par Exception)
    _JAVA_EXCEPTION_PATTERN = re.compile(
        r"[A-Z][a-z]+(?:[A-Z][a-z]+)+Exception\b"
    )

    def _extract_equipment_name(self, text: str) -> Optional[str]:
        """Extrait un nom d'équipement BRASIL (DSLAM, ONT, NIP) du texte."""
        # Ne pas déclencher si un ND a déjà été détecté
        if self._extract_nd_number(text):
            return None
        # Ne pas déclencher si la query parle d'une procédure, d'une étape ou d'une exception Java
        if self._PROC_CONTEXT_PATTERN.search(text):
            return None
        if self._JAVA_EXCEPTION_PATTERN.search(text):
            return None
        for pat in (self._EQUIP_CHASSIS_PATTERN, self._EQUIP_DSLAM_PATTERN,
                    self._EQUIP_ONT_PATTERN, self._EQUIP_NIP_PATTERN):
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
        """Recherche un équipement dans les fichiers log et retourne une analyse structurée."""
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

        # ── Build structured summary ──────────────────────────────────────
        from collections import Counter
        ETAT = {"C": "Commandé", "E": "En service", "A": "À venir", "S": "Supprimé", "D": "Désactivé"}
        EPT  = {"ES": "En service", "AFF": "Affecté", "LIB": "Libéré"}

        nds_impacted  = Counter(e["nd"]     for e in events if e["nd"])
        clients       = Counter(e["client"] for e in events if e["client"])
        sts           = Counter(e["st"]     for e in events if e["st"])
        ports         = Counter(e["port"]   for e in events if e["port"])
        chassis_seen  = Counter(e["chassis"] for e in events if e["chassis"])
        nips          = Counter(e["nip"]    for e in events if e["nip"])
        epts          = Counter(e["etatEpt"] for e in events if e["etatEpt"])
        timestamps    = Counter(e["ts"][:10] for e in events if e["ts"])

        nds_str     = "\n".join(f"  - ND {nd}: ×{cnt}" for nd, cnt in nds_impacted.most_common(10))
        clients_str = ", ".join(f"{c}(×{v})" for c, v in clients.most_common(5))
        sts_str     = "\n".join(f"  - {k}: ×{v}" for k, v in sts.most_common(8))
        ports_str   = ", ".join(f"port {p}(×{v})" for p, v in ports.most_common(6))
        chassis_str = ", ".join(f"{c}(×{v})" for c, v in chassis_seen.most_common(4))
        nips_str    = ", ".join(f"{n}(×{v})" for n, v in nips.most_common(4))
        ept_str     = ", ".join(f"{k}({EPT.get(k,k)}): ×{v}" for k, v in epts.most_common())
        days_str    = ", ".join(f"{d}(×{v})" for d, v in sorted(timestamps.items()))

        context = f"""ANALYSE ÉQUIPEMENT : {equip_upper}
Fichier    : {', '.join(found_in)}
Événements : {len(events)} (sur {MAX_EVENTS} max extraits)
Jours actifs : {days_str}

NDs IMPACTÉS (top 10) :
{nds_str}

CLIENTS : {clients_str}

SERVICES TECHNIQUES :
{sts_str}

PORTS UTILISÉS : {ports_str}
CHÂSSIS        : {chassis_str}
NIPs ASSOCIÉS  : {nips_str}
ÉTATS EPT      : {ept_str}

PREMIER ÉVÉNEMENT : {events[0]['ts']} | ND={events[0]['nd']} | {events[0]['st']} | {events[0]['avant']}→{events[0]['etat']}
DERNIER ÉVÉNEMENT : {events[-1]['ts']} | ND={events[-1]['nd']} | {events[-1]['st']} | {events[-1]['avant']}→{events[-1]['etat']}
"""

        prompt = f"""Tu es un expert BRASIL Network Management. Voici les données extraites des logs pour l'équipement {equip_upper}.

Utilise UNIQUEMENT ces données pour répondre. Ne fabrique rien.

{context}

Question: {user_message}

Réponds en français de façon structurée :
1. Identification de l'équipement et sa localisation
2. Activité résumée (NDs traités, clients, services)
3. État actuel et ports occupés
4. Points d'attention ou anomalies éventuelles
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
                f"Analyser le ND {top_nd} sur cet équipement" if top_nd else f"Quels NDs sont sur {equip_upper} ?",
                f"Quels ports sont occupés sur {equip_upper} ?",
                f"Y a-t-il des erreurs sur les NIPs associés à {equip_upper} ?",
            ],
            diagnostic_available=False,
        )
    _ML_ANALYSIS_PATTERNS = re.compile(
        r"\b(causes\s+principales|top\s+causes|top\s+cat[eé]gories|analyse\s+ml|"
        r"r[eé]sum[eé]\s+ml|anomalies\s+temporelles|volume\s+de\s+tickets|"
        r"classification\s+tickets|statistiques\s+tickets|insights\s+ml|"
        r"r[eé]partition\s+(des\s+)?causes|distribution\s+tickets|"
        r"mttr\s+moyen|temps\s+de\s+r[eé]solution\s+moyen|score\s+de\s+criticit[eé]|"
        r"quelles?\s+sont\s+les\s+causes|causes\s+r[eé]currentes|incidents\s+r[eé]currents|"
        r"rapport\s+ml|rapport\s+de\s+classification|tendances\s+tickets|"
        r"principales?\s+cat[eé]gories)\b",
        re.IGNORECASE,
    )

    def _detect_ml_analysis_intent(self, text: str) -> bool:
        """Return True when the message asks about ML classification stats or insights."""
        return bool(self._ML_ANALYSIS_PATTERNS.search(text))

    # ── Technical Inference intent ──────────────────────────────────────────
    # Détecte "c'est quoi X", "qu'est-ce que X", "explique X", "à quoi sert X"
    # où X est un identifiant technique (CamelCase, snake_case, ALL_CAPS, etc.)
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

    # Également : questions directes sans verbe introductif sur un symbole technique connu
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
        Le LLM infère ce qu'est un symbole technique (classe, service, méthode)
        en se basant sur son nom, le contexte de l'application et la base de connaissance disponible.
        Pas de refus par trust gate — le LLM raisonne et précise l'incertitude lui-même.
        """
        app_name = app_ctx.get("display_name", app_id) or app_id

        # Contexte KB disponible (procédures, schémas de tables, etc.)
        context_text = self.orchestrator.build_prompt_context(orch_result)
        context_blocks = orch_result.get("context_blocks", [])

        # Détecter si la KB contient un schéma de table pour ce symbole
        kb_has_schema = any(
            b.get("type") == "partial_canonical"
            and symbol.lower() in (b.get("title") or "").lower()
            for b in context_blocks
        )

        if context_text:
            context_section = f"\n\n{context_text[:4000]}"
        else:
            context_section = ""

        if kb_has_schema:
            # Mode KB-first : le schéma est disponible, le LLM doit s'en servir
            inference_prompt = (
                f"Un ingénieur te demande : **{user_message}**\n\n"
                f"La base de connaissance BRASIL contient les informations suivantes sur `{symbol}` :\n"
                f"{context_section}\n\n"
                f"En te basant EXCLUSIVEMENT sur ces informations, réponds de façon précise et structurée :\n"
                f"1. **Description** de la table (rôle métier selon son nom et ses colonnes)\n"
                f"2. **Structure** : clé primaire, colonnes principales et leurs types\n"
                f"3. **Relations** éventuelles avec d'autres tables (clés étrangères)\n"
                f"4. **Utilisation** probable dans l'application\n\n"
                f"IMPORTANT : Utilise uniquement les données du schéma fourni ci-dessus. Ne génère pas d'informations hypothétiques."
            )
            system_prompt_text = (
                f"Tu es un expert base de données de la plateforme {app_name} (Orange). "
                f"Quand un schéma de table est fourni dans la base de connaissance, tu l'utilises INTÉGRALEMENT et EXCLUSIVEMENT pour répondre. "
                f"Tu ne génères jamais de colonnes ou de structures hypothétiques si le schéma réel est disponible. "
                f"Tu réponds en français technique précis et structuré."
            )
        else:
            # Mode inférence : pas de schéma en KB, raisonner sur le nom
            inference_prompt = (
                f"Un ingénieur te demande : **{user_message}**\n\n"
                f"Le symbole technique en question est : `{symbol}`\n"
                f"Contexte de l'application : {app_name} (plateforme Orange Telecom, domaine accès réseau/DSLAM/VLAN/FTTH)."
                f"{context_section}\n\n"
                f"Réponds de façon structurée :\n"
                f"1. **Ce que tu sais avec certitude** (basé sur le nom, les conventions de nommage, le contexte)\n"
                f"2. **Ce que tu peux inférer** (logique métier probable selon le domaine)\n"
                f"3. **Ce qui reste incertain** (ce qu'il faudrait confirmer dans le code source)\n\n"
                f"Si le nom contient des indices clairs, exploite-les pleinement. Reste précis et technique."
            )
            system_prompt_text = (
                f"Tu es un expert technique de la plateforme {app_name} (Orange). "
                f"Quand on te demande ce qu'est un symbole technique (classe, service, interface, méthode, table), "
                f"tu analyses son nom, ses conventions de nommage et le contexte applicatif pour inférer son rôle. "
                f"Tu structures clairement : ce qui est certain, ce qui est probable, ce qui est incertain. "
                f"Tu ne refuses jamais de répondre — tu signales l'incertitude dans ta réponse. "
                f"Tu réponds en français technique précis."
            )

        try:
            response_text = await self.llm.generate(
                prompt=inference_prompt,
                system_prompt=system_prompt_text,
                max_tokens=600,
            )
        except Exception as e:
            logger.error(f"[TechInference] LLM error: {e}")
            response_text = f"Impossible de générer l'inférence pour `{symbol}` : {e}"

        logger.info(f"[TechInference] Inférence générée pour '{symbol}'")
        return ChatResponse(
            message=response_text,
            sources=(
                [{"title": b.get("title", ""), "type": b.get("source_type", "kb"), "score": b.get("trust_score", 0) / 100}
                 for b in orch_result.get("context_blocks", [])[:3]]
                if orch_result.get("context_blocks") else []
            ),
            suggestions=[
                f"Où est utilisé {symbol} dans l'application ?",
                "Y a-t-il un ticket Jira lié à ce composant ?",
                "Quelles sont les dépendances de ce service ?",
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
            # ── Attempt live exec-summary ──────────────────────────────────────
            summary = None
            try:
                from app.api.v1.endpoints.classification_ml import get_exec_summary, _uploaded_data
                if _uploaded_data is not None:
                    summary = await get_exec_summary(ai=True)
            except Exception as _e:
                logger.debug(f"[ML-Intent] exec-summary live call failed: {_e}")

            if summary:
                # Build response from live summary
                lines = [f"📊 **Analyse ML Tickets BRASIL** — {summary.date_range or 'dernière période'}\n"]

                # KPIs
                lines.append(
                    f"🎫 **{summary.volume}** tickets analysés | "
                    f"⏱️ MTTR médian : **{summary.mttr_med:.1f}j**"
                )

                # AI Narrative
                if summary.ai_narrative:
                    lines.append(f"\n---\n{summary.ai_narrative}")

                # Top causes
                if summary.top_causes:
                    lines.append("\n\n**🔝 Top causes :**")
                    for c in summary.top_causes[:5]:
                        lines.append(f"  • {c.get('label', c)} — {c.get('count', '')} tickets")

                # Criticality scores
                if summary.criticality_scores:
                    lines.append("\n\n**⚠️ Scores de criticité :**")
                    for cs in summary.criticality_scores[:4]:
                        badge = cs.category if isinstance(cs, dict) else cs.category
                        score = cs.score if isinstance(cs, dict) else cs.score
                        lines.append(f"  • **{badge}** — score {score:.0f}/100 {cs.rationale if hasattr(cs, 'rationale') else ''}")

                # Temporal anomalies
                if summary.temporal_anomalies:
                    lines.append("\n\n**📈 Anomalies temporelles :**")
                    for a in summary.temporal_anomalies[:3]:
                        icon = "📈" if getattr(a, "direction", "") == "spike" else "📉"
                        lines.append(
                            f"  {icon} **{a.period}** — {a.volume} tickets "
                            f"({'+' if a.delta_pct > 0 else ''}{a.delta_pct:.1f}%) — {a.hypothesis}"
                        )

                # Top recommendations
                if summary.ai_recommendations:
                    lines.append("\n\n**💡 Recommandations prioritaires :**")
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
                        "Afficher les anomalies temporelles détaillées",
                    ],
                    confidence=0.95,
                    conversation_id=conversation_id,
                    app_id=app_id,
                    pipeline_mode="ml_analysis",
                    trust_score=90,
                    trust_label="ml_live",
                    diagnostic_available=False,
                )

            # ── Fallback: search ml_insight in Qdrant ────────────────────────
            context_blocks = orch_result.get("context_blocks", [])
            ml_blocks = [b for b in context_blocks if b.get("source_type") == "ml_insight"]
            if ml_blocks:
                content = ml_blocks[0].get("content", "")
                return ChatResponse(
                    message=f"📊 **Insights ML (base de connaissance) :**\n\n{content}",
                    sources=[{"title": "ML Insight Qdrant", "type": "ml_insight", "score": 0.8}],
                    suggestions=[
                        "Aller dans le module ML pour voir les détails",
                        "Y a-t-il des anomalies temporelles récentes ?",
                    ],
                    confidence=0.8,
                    conversation_id=conversation_id,
                    app_id=app_id,
                    pipeline_mode="ml_analysis",
                    trust_score=75,
                    trust_label="ml_qdrant",
                    diagnostic_available=False,
                )

            # ── No data available ────────────────────────────────────────────
            return ChatResponse(
                message=(
                    "📊 **Analyse ML non disponible**\n\n"
                    "Aucune donnée de classification n'est actuellement chargée. "
                    "Pour obtenir une analyse ML complète :\n"
                    "1. Allez dans le **module Classification ML**\n"
                    "2. Uploadez votre CSV de tickets\n"
                    "3. Entraînez le modèle\n"
                    "4. Cliquez sur *Injecter dans le Chatbot* depuis l'onglet Résumé Exécutif"
                ),
                sources=[],
                suggestions=[
                    "Accéder au module Classification ML",
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
        """
        # Priority: explicit issue key -> return as-is for direct key lookup
        issue_key = self._extract_issue_key(user_message)
        if issue_key:
            return issue_key

        stopwords = {
            "le", "la", "les", "de", "du", "des", "un", "une", "et", "ou",
            "en", "au", "aux", "ce", "se", "sa", "son", "sur", "par", "pour",
            "avec", "dans", "est", "sont", "que", "qui", "il", "elle",
            "jira", "carte", "ticket", "issue", "bogue", "anomalie",
            "existe", "y", "t", "il", "a", "creer", "ouvrir",
            "similaire", "correspondant", "problème", "pb",
            "explique", "reformule", "résume", "décrypte", "analyse",
            "trouve", "cherche", "trouver", "chercher", "montre",
        }

        # Words from user message (>=3 chars, non-stopwords)
        user_tokens = set(
            w.lower() for w in re.findall(r"[a-zA-ZÀ-ÿ0-9_\-]{3,}", user_message)
            if w.lower() not in stopwords
        )

        # Words from procedure titles returned by the orchestrator
        proc_tokens: set = set()
        for block in orch_result.get("context_blocks", []):
            title = block.get("title", "")
            for w in re.findall(r"[a-zA-ZÀ-ÿ0-9_\-]{3,}", title):
                if w.lower() not in stopwords:
                    proc_tokens.add(w)

        # Priority: user tokens first, then procedure tokens (max 6 total)
        combined = list(user_tokens)[:4] + [t for t in proc_tokens if t.lower() not in user_tokens][:2]
        return " ".join(combined[:6])

    def _search_jira_tickets(self, keywords: str, max_results: int = 5) -> list:
        """
        Search Jira tickets.
        When `keywords` is a single issue key (e.g. BRASIL-10861) use
        JQL `key = X` for an exact lookup.  Otherwise do a full-text search.
        """
        try:
            from app.services.collector.jira_collector import jira_collector

            if not jira_collector.jira_client:
                if not jira_collector._connect():
                    logger.warning("[Jira] Client non disponible pour la recherche")
                    return []

            safe_kw = keywords.replace('"', '').strip()
            if not safe_kw:
                return []

            # Direct key lookup when the whole keyword IS an issue key
            if self._JIRA_KEY_PATTERN.fullmatch(safe_kw):
                jql = f'key = "{safe_kw}"'
            else:
                jql = (
                    f'project = BRASIL AND text ~ "{safe_kw}" '
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

            logger.info(f"[Jira] {len(results)} ticket(s) trouvé(s) pour '{safe_kw}'")
            return results

        except Exception as exc:
            logger.error(f"[Jira] Erreur recherche tickets: {exc}")
            return []

    def _format_jira_response(self, tickets: list, keywords: str) -> str:
        """Formate la liste de tickets Jira en réponse lisible."""
        if not tickets:
            return (
                f"🔍 Aucun ticket Jira trouvé dans le projet **BRASIL** "
                f"pour les mots-clés : *{keywords}*.\n\n"
                f"Vous pouvez créer un nouveau ticket pour signaler ce problème."
            )

        lines = [
            f"📋 **{len(tickets)} ticket(s) Jira trouvé(s)** dans BRASIL "
            f"pour *{keywords}* :\n"
        ]
        for t in tickets:
            status_icon = {
                "Open": "🔴", "To Do": "⚪", "In Progress": "🟡",
                "Resolved": "🟢", "Closed": "✅", "Done": "✅",
            }.get(t["status"], "🔵")

            prio = f" — priorité **{t['priority']}**" if t.get("priority") else ""
            assignee = f" (assigné : {t['assignee']})" if t.get("assignee") else ""

            lines.append(
                f"{status_icon} **[{t['key']}]({t['url']})** — {t['summary']}\n"
                f"   Statut : *{t['status']}*{prio}{assignee}"
            )

        lines.append(
            f"\n🔗 [Voir tous les tickets BRASIL]"
            f"({tickets[0]['url'].rsplit('/browse/', 1)[0]}/projects/BRASIL/issues)"
        )
        return "\n".join(lines)

    async def _handle_jira_intent(
        self,
        user_message: str,
        orch_result: dict,
        conversation_id: str,
        app_id: str,
        app_ctx: dict,
        history: Optional[List[Dict]] = None,
    ) -> Optional[ChatResponse]:
        """
        Handle a Jira intent.
        - Explicit issue key + explain verb  → fetch issue, reformulate via LLM.
        - Explain verb without key           → look for key in conversation history.
        - Everything else                    → keyword/key search, return list.
        """
        issue_key = self._extract_issue_key(user_message)

        # If no key in message, try to find one in conversation history
        if not issue_key and history:
            for msg in reversed(history):
                found = self._extract_issue_key(msg.get("content", ""))
                if found:
                    issue_key = found
                    logger.info(f"[Jira] Clé trouvée dans l'historique: {issue_key}")
                    break

        keywords  = self._extract_jira_keywords(user_message, orch_result)
        if not keywords and issue_key:
            keywords = issue_key
        logger.info(f"[Jira] Intent détecté — key={issue_key}, keywords='{keywords}'")

        wants_explanation = bool(self._EXPLAIN_VERBS.search(user_message)) or bool(
            re.search(
                r"(?:explique|r\u00e9sume|d\u00e9taille|d\u00e9crypte|c'est\s+quoi|que\s+dit)\s+(cette?|le|la|ce)\s+(carte|ticket|issue)",
                user_message, re.IGNORECASE
            )
        )

        tickets = self._search_jira_tickets(keywords, max_results=5)

        # ── Explain path: fetch one issue and reformulate via LLM ───────────────
        if wants_explanation and tickets:
            ticket = tickets[0]
            description = ticket.get("description") or "(aucune description)"
            description = description[:2000]

            explain_prompt = (
                f"Voici le contenu de la carte Jira **{ticket['key']}** :\n\n"
                f"**Titre** : {ticket['summary']}\n"
                f"**Statut** : {ticket['status']}\n"
                f"**Description** :\n{description}\n\n"
                "Reformule et explique ce ticket en français clair et structuré "
                "pour un ingénieur N3 :\n"
                "(1) Contexte / Système impacté\n"
                "(2) Problème décrit\n"
                "(3) Actions déjà effectuées si mentionnées\n"
                "(4) Ce qui reste à faire selon toi\n"
                "Sois factuel. Ne complète que ce qui est présent dans le ticket."
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
                explanation = f"Impossible de générer l'explication : {e}"

            response_text = (
                f"\U0001f4cb **Explication de {ticket['key']} — {ticket['summary']}**\n"
                f"\U0001f517 [Voir sur Jira]({ticket['url']}) | Statut : *{ticket['status']}*\n\n"
                f"{explanation}"
            )
            return ChatResponse(
                message=response_text,
                sources=[{"title": ticket["key"], "content": ticket["summary"], "url": ticket["url"], "score": 1.0}],
                suggestions=[
                    "Quelle est la procédure de résolution associée ?",
                    "Y a-t-il des tickets similaires ?",
                    "Génère le message de clôture pour ce ticket",
                ],
                confidence=1.0,
                conversation_id=conversation_id,
                app_id=app_id,
                pipeline_mode=orch_result.get("mode"),
                trust_score=90,
                trust_label="jira_explain",
                diagnostic_available=False,
            )

        # ── Standard search result ──────────────────────────────────────────────────
        response_text = self._format_jira_response(tickets, keywords)
        return ChatResponse(
            message=response_text,
            sources=[
                {"title": t["key"], "content": t["summary"], "url": t["url"], "score": 1.0}
                for t in tickets
            ],
            suggestions=[
                "Afficher la procédure de résolution associée",
                "Créer un nouveau ticket Jira",
                "Quels sont les tickets prioritaires ouverts ?",
            ],
            confidence=1.0 if tickets else 0.3,
            conversation_id=conversation_id,
            app_id=app_id,
            pipeline_mode=orch_result.get("mode"),
            trust_score=90 if tickets else 30,
            trust_label="jira_search",
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
