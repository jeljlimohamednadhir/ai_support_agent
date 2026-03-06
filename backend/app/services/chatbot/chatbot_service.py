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
    )
    from app.services.nlp.enricher import ticket_enricher
    _NLP_AVAILABLE = True
except ImportError:
    _NLP_AVAILABLE = False

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

            # 1c. Reformuler la requête si question de suivi (ex: "et ce ticket ?" → "ticket DSLAM suppression")
            effective_query = await self._resolve_query(message.content, history)
            if effective_query != message.content:
                logger.info(f"[Chatbot] Requête reformulée: '{message.content[:40]}' → '{effective_query[:60]}'")

            # 1. DÃ©lÃ©guer Ã  l'orchestrateur
            orch_result = await self.orchestrator.process(
                app_id=message.app_id,
                query=effective_query,
                db=db,
                logs=message.logs,
                stack_trace=message.stack_trace,
                ticket_description=message.content,
                top_k=5,
            )

            # 2. Construire le contexte texte pour le LLM
            context_text = self.orchestrator.build_prompt_context(orch_result)

            # 3. Récupérer les garde-fous de réponse (avant off_topic pour avoir app_ctx)
            guard = self.orchestrator.get_response_guard(orch_result)
            llm_instructions = orch_result.get("llm_instructions", "")
            app_ctx = orch_result.get("app_context", {})

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

            # 2d. Détection intention Jira : "y a-t-il une carte Jira ?", "ticket similaire ?", etc.
            if self._detect_jira_intent(message.content):
                jira_response = await self._handle_jira_intent(
                    user_message=message.content,
                    orch_result=orch_result,
                    conversation_id=conversation_id,
                    app_id=message.app_id,
                    app_ctx=app_ctx,
                )
                if jira_response:
                    return jira_response

            # 2d. NLP Enrichment — analyse structurée du message entrant
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
                except Exception as nlp_err:
                    logger.warning(f"[Chatbot][NLP] Enrichissement échoué: {nlp_err}")

            # 2e. Trust gate — refuse if knowledge is insufficient (score < 40)
            # NOTE: contextual intents (summarize / ticket-message / logs) bypass this gate.
            if _NLP_AVAILABLE and not orch_result.get("off_topic"):
                try:
                    can_respond, trust_reason = diagnostic_reasoner.check_trust_gate(
                        orch_result,
                        threshold=40.0,
                        structured_ticket=structured_ticket,
                    )
                    context_blocks = orch_result.get("context_blocks", [])
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
                        system_prompt = diagnostic_reasoner.build_system_prompt(
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
                # Aucun contexte disponible
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
            response_text = await self.llm.generate(
                prompt=full_prompt,
                system_prompt=system_prompt,
            )

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
        r"(^(et|mais|donc|alors|pourquoi|comment|quand|où|quel|quelle|quels)\b"
        r"|\b(ce (problème|truc|bug|cas|point|ticket|erreur)|cela|cet?te|ce|ici|là|[làça]|y)\b"
        r"|\b(pour (qa|ce|cela|a))\b"
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

    # ── ML Analysis intent ──────────────────────────────────────────────────
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
    ) -> Optional[ChatResponse]:
        """
        Handle a Jira intent.
        - Explicit issue key + explain verb  → fetch issue, reformulate via LLM.
        - Everything else                    → keyword/key search, return list.
        """
        issue_key = self._extract_issue_key(user_message)
        keywords  = self._extract_jira_keywords(user_message, orch_result)
        logger.info(f"[Jira] Intent détecté — key={issue_key}, keywords='{keywords}'")

        wants_explanation = issue_key and bool(self._EXPLAIN_VERBS.search(user_message))

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
