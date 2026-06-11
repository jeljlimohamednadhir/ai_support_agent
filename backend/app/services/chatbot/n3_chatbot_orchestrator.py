"""
N3 Chatbot Orchestrator — Main Pipeline Entry Point
======================================================
Wires all 8 layers together for N3-level BRASIL support.

Layer flow per turn:
  Turn input
    └─► [L1] SFD Parser         — constraint lookup + source of truth
    └─► [L2] Knowledge Layer    — multi-source retrieval (incidents, FR, logs)
    └─► [L3] Conversation State — entity memory + pronoun resolution
    └─► [L4] Intent Resolver    — multi-turn intent continuity
    └─► [L5] Correlation Engine — evidence scoring + hypothesis ranking
    └─► [L6] Validation Layer   — anti-hallucination (entity + business + evidence)
    └─► [L7] Response Generator — structured N3 response builder
    └─► [L8] Learning Loop      — post-resolution pattern storage

Integration points:
  - Exposes `N3ChatbotOrchestrator.chat(session_id, user_text)` → dict
  - Can be called from existing chatbot_service.py
  - Test scenario: run this file directly for self-contained simulation

JIRA guarantee: NEVER used in retrieval, correlation, or response generation.
"""
from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import Optional, Dict, Any, List

# ── Path setup (needed when running standalone) ───────────────────────────────
_THIS_DIR = Path(__file__).parent
_BACKEND  = _THIS_DIR.parents[2]        # backend/
_ROOT     = _BACKEND.parent             # workspace root
for _p in (_ROOT, _BACKEND):
    p_str = str(_p)
    if p_str not in sys.path:
        sys.path.insert(0, p_str)

# ── Layer imports ─────────────────────────────────────────────────────────────
from app.services.chatbot.sfd_parser import sfd_parser                     # L1
from app.services.chatbot.knowledge_layer import knowledge_layer           # L2
from app.services.chatbot.conversation_state import (                      # L3
    ConversationState, ConversationStateStore,
)
from app.services.chatbot.intent_resolver import intent_resolver           # L4
from app.services.chatbot.correlation_engine import correlation_engine     # L5
from app.services.chatbot.validation_layer import validation_layer         # L6
from app.services.chatbot.response_generator import (                      # L7
    response_generator, MODE_NATURAL, MODE_EXPERT, detect_symptoms,
)
from app.services.chatbot.learning_loop import learning_loop               # L8
from app.services.chatbot.incident_graph import incident_graph             # reinforcement

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")


# ─────────────────────────────────────────────────────────────────────────────
# Orchestrator
# ─────────────────────────────────────────────────────────────────────────────

class N3ChatbotOrchestrator:
    """
    Full 8-layer chatbot pipeline for N3 BRASIL support.
    One instance per application; stateful per session via ConversationStateStore.
    """

    def __init__(self, mode: str = MODE_NATURAL):
        self.mode = mode
        self._state_store = ConversationStateStore()
        self._denial_counter: Dict[str, int] = {}   # session_id → denial count

    # ── Main entry point ──────────────────────────────────────────────────────

    def chat(
        self,
        session_id: str,
        user_text: str,
        use_llm: bool = False,
        llm_caller: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """
        Process one user turn through the full 8-layer pipeline.

        Args:
            session_id:  Unique session/conversation identifier.
            user_text:   Raw user message.
            use_llm:     If True, pass context to llm_caller for final response.
            llm_caller:  Optional async/sync callable(prompt: str) → str.

        Returns:
            {
              "session_id": str,
              "turn": int,
              "intent": str,
              "entities": dict,
              "response": str,
              "confidence": float,
              "hypothesis": str | None,
              "follow_up_questions": list,
              "validation_passed": bool,
              "sfd_violations": list,
              "evidence_count": int,
              "resolved": bool | None,
            }
        """
        t0 = time.perf_counter()

        # ── L3: Get / create conversation state ───────────────────────────────
        state: ConversationState = self._state_store.get_or_create(session_id)
        state.add_user_turn(user_text)

        # ── L4: Resolve intent ────────────────────────────────────────────────
        intent_result = intent_resolver.resolve(user_text, state)
        intent = intent_result.intent

        turn_count = len(state.history)
        logger.info(f"[{session_id[:8]}] Turn {turn_count} | intent={intent} | "
                    f"entities={list(state.entities.keys())[:3]}")

        # ── Symptom detection + DEBUG mode priority ───────────────────────────
        detected_symptoms = detect_symptoms(user_text)
        debug_mode = bool(detected_symptoms) or intent in (
            "debug", "delete_equipment", "delete", "diagnose"
        )
        if debug_mode:
            logger.info(
                f"[{session_id[:8]}] DEBUG MODE — symptoms={detected_symptoms} "
                f"| root cause analysis priority activated"
            )

        # ── L2: Retrieve knowledge ────────────────────────────────────────────
        entity_names = list(state.entities.keys())
        retrieved = knowledge_layer.retrieve(
            query=user_text,
            entities=entity_names,
            top_k=4,
        )
        kb_context = knowledge_layer.format_context_block(retrieved)

        # ── L1: SFD constraint lookup for primary entity ──────────────────────
        primary = state.get_primary_equipment()
        sfd_context = ""
        if primary:
            sfd_docs = sfd_parser.load()
            if sfd_docs:
                sfd_context = sfd_parser.to_context_block(primary.name)

        # ── L5: Correlate ─────────────────────────────────────────────────────
        correlation = correlation_engine.correlate(
            query=user_text,
            state=state,
            kb_blocks=retrieved.get("fr", []) + retrieved.get("canonical", []),
            incident_blocks=retrieved.get("incidents", []),
            log_patterns=retrieved.get("logs", []),
            intent=intent,
        )

        # ── Missing entity clarification — ask before running full pipeline ────
        # If a delete/diagnose intent is detected AND an FR matched but no
        # equipment entity is known, return a targeted question immediately.
        if intent in ("delete_equipment", "delete", "diagnose", "debug") and not state.get_primary_equipment():
            _fr_candidates = correlation_engine._match_structured_fr(user_text, None)
            if _fr_candidates:
                # Collect expected equipment examples from the top FR
                _top_fr_raw = _fr_candidates[0][1] if isinstance(_fr_candidates[0], tuple) else None
                # _match_structured_fr returns List[CorrelationEvidence] at this stage,
                # so extract equipment from evidence metadata if available
                _eq_types: list = []
                for _ev in (_top_fr_raw if isinstance(_top_fr_raw, list) else []):
                    pass  # handled below via correlation evidence
                # Use the correlation FR evidence metadata instead
                _fr_evs = [
                    e for h in correlation.hypotheses for e in h.evidence
                    if e.source_type == "fr_document"
                ] or (
                    [e for e in correlation.top_hypothesis.evidence if e.source_type == "fr_document"]
                    if correlation.top_hypothesis else []
                )
                _eq_examples: list = []
                for _ev in _fr_evs[:2]:
                    _eq_examples.extend(
                        [str(ex) for ex in _ev.metadata.get("entities_equipment", [])]
                    )
                # Load raw FR for richer equipment examples
                _raw_frs = correlation_engine._load_structured_frs()
                _matched_raw = [
                    fr for fr in _raw_frs
                    if any(e.metadata.get("fr_id") == fr.get("id") for e in _fr_evs)
                ][:1]
                for _fr in _matched_raw:
                    for _ent in _fr.get("entities", []):
                        if _ent.get("type") == "EQUIPMENT":
                            _eq_examples.extend(_ent.get("examples", [])[:3])
                _eq_examples = list(dict.fromkeys(_eq_examples))[:4]  # unique, cap 4
                if _eq_examples:
                    _eq_list = " / ".join(_eq_examples)
                    _clarif = (
                        f"Pour traiter votre demande, quel type d'équipement souhaitez-vous "
                        f"{'supprimer' if 'delete' in intent else 'analyser'} ?\n"
                        f"**Exemples** : {_eq_list}\n"
                        f"Merci également de préciser l'identifiant ou le nom de l'équipement concerné."
                    )
                    state.add_assistant_turn(_clarif, intent=intent, action="clarification")
                    return {
                        "session_id": session_id,
                        "turn": len(state.history),
                        "intent": intent,
                        "entities": {},
                        "response": _clarif,
                        "confidence": 0.0,
                        "hypothesis": None,
                        "follow_up_questions": [],
                        "validation_passed": True,
                        "sfd_violations": [],
                        "evidence_count": 0,
                        "resolved": None,
                        "clarification_requested": True,
                    }

        # ── L6: Validate ──────────────────────────────────────────────────
        # Validate using correlation result directly (no LLM context needed pre-validation)
        validation = validation_layer.validate(
            response=correlation.top_hypothesis.root_cause if (correlation and correlation.top_hypothesis) else "",
            state=state,
            intent=intent,
            retrieved=retrieved,
            hypothesis_id=correlation.top_hypothesis.id if correlation.top_hypothesis else None,
            correlation_confidence=correlation.confidence,
        )

        # ── L7: Generate response ─────────────────────────────────────────────
        # Always compute the deterministic response first (fallback + structured_result for LLM)
        generated = response_generator.generate(
            intent=intent,
            state=state,
            correlation=correlation,
            validation=validation,
            mode=self.mode,
        )
        final_text = generated.text
        confidence = generated.confidence
        follow_ups = generated.follow_up_questions
        hypothesis_label = (
            correlation.top_hypothesis.label if correlation.top_hypothesis else None
        )

        # Devil's Advocate pre-computed (needed by LLM context builder)
        devil_advocate = self._generate_devil_advocate(
            top_hypothesis=correlation.top_hypothesis,
            all_hypotheses=correlation.hypotheses,
        )

        if use_llm and llm_caller and validation.passed:
            # ── HIGH CONFIDENCE SKIP: deterministic result is authoritative ──
            # When confidence > 0.9 the correlation engine has strong multi-source
            # evidence — the LLM adds no value and only risks instability.
            if confidence > 0.9:
                logger.info(
                    f"[{session_id[:8]}] LLM skip — confidence={confidence:.0%} > 90% "
                    f"(deterministic result used directly)"
                )
            else:
                # LLM path: pass ONLY compact structured result — <300 tokens
                prompt = response_generator.build_llm_context(
                    intent=intent,
                    state=state,
                    correlation=correlation,
                    user_text=user_text,
                    structured_result=generated,
                    devil_advocate=devil_advocate,
                )
                try:
                    llm_text = llm_caller(prompt)
                    llm_validation = validation_layer.validate(
                        response=llm_text,
                        state=state,
                        intent=intent,
                        retrieved=retrieved,
                    )
                    if llm_validation.passed:
                        final_text = llm_text + (llm_validation.warning_message or "")
                        confidence = correlation.confidence
                        follow_ups = []
                    else:
                        logger.warning(
                            f"[{session_id[:8]}] LLM output failed validation "
                            f"— using deterministic fallback"
                        )
                except Exception as e:
                    logger.error(f"LLM call failed: {e} — using deterministic fallback")
                # final_text, confidence, follow_ups already set above

        # Note: warning_message is already appended inside response_generator.generate()
        # Only add it here for the LLM path where we bypass the generator

        # ── L3: Store assistant turn ──────────────────────────────────────
        state.add_assistant_turn(final_text, intent=intent, action=hypothesis_label or "")

        # ── L8: Post-resolution learning ─────────────────────────────────────
        hyp_id = correlation.top_hypothesis.id if correlation.top_hypothesis else ""
        val_score = validation.score
        val_tier = validation.tier

        if intent == "confirm_resolution":
            learning_loop.on_resolution_confirmed(
                state=state,
                hypothesis_id=hyp_id,
                hypothesis_label=hypothesis_label or "",
                actions_taken=(
                    correlation.top_hypothesis.recommended_actions[:3]
                    if correlation.top_hypothesis else []
                ),
                confidence=confidence,
            )
            # ── ADAPTIVE REINFORCEMENT: delta scales with validation score ───
            # HIGH → strong reinforce | MEDIUM → light | LOW → should not confirm
            adaptive_delta = 0.10 * val_score  # e.g. HIGH score=0.95 → delta=0.095
            if hyp_id:
                incident_graph.reinforce(hyp_id, delta=adaptive_delta)

        elif intent == "deny_resolution":
            self._denial_counter[session_id] = self._denial_counter.get(session_id, 0) + 1
            denial_count = self._denial_counter[session_id]
            bug = learning_loop.on_resolution_denied(
                state=state,
                hypothesis_id=hyp_id,
                hypothesis_label=hypothesis_label or "",
                denial_count=denial_count,
            )
            # ── SMART DENIAL: only suppress when validation was already weak ─
            # Suppress if: validation_score < 0.6 (we were already uncertain)
            # Otherwise: just ask follow-up — the hypothesis may still be right
            if hyp_id and denial_count >= 2 and val_score < 0.60:
                suppress_delta = 0.10 * (1.0 - val_score)  # weak evidence → stronger suppress
                incident_graph.suppress(hyp_id, delta=suppress_delta)
                learning_loop.update_hypothesis_stats(hyp_id, outcome="failure", suppression_delta=-0.10)
            elif hyp_id and denial_count >= 3:
                # After 3 denials regardless of score → suppress
                incident_graph.suppress(hyp_id, delta=0.10)

            if bug:
                logger.warning(
                    f"[INTERNAL] Bug suggestion created: {bug.id} | "
                    f"Module: {bug.probable_module} | "
                    f"Fix: {bug.fix_recommendation}"
                )

        # ── MEDIUM tier → store as weak pattern candidate for review ─────────
        elif val_tier == "MEDIUM" and hyp_id:
            learning_loop.store_weak_pattern_candidate(
                session_id=session_id,
                query=user_text,
                response=final_text,
                hypothesis_id=hyp_id,
                entity_name=(
                    state.get_primary_equipment().name
                    if state.get_primary_equipment() else "unknown"
                ),
                validation_score=val_score,
                evidence_count=validation.evidence_count,
            )

        elapsed = (time.perf_counter() - t0) * 1000
        logger.info(f"[{session_id[:8]}] Response generated in {elapsed:.0f}ms")

        # devil_advocate already computed above (before LLM call, used in context)

        return {
            "session_id": session_id,
            "turn": len(state.history),
            "intent": intent,
            "entities": {k: v.type.value for k, v in state.entities.items()},
            "response": final_text,
            "confidence": round(confidence, 3),
            "hypothesis": hypothesis_label,
            "follow_up_questions": follow_ups,
            "validation_passed": validation.passed,
            "validation_tier": validation.tier,
            "validation_score": validation.score,
            "needs_review": validation.needs_review,
            "sfd_violations": correlation.sfd_violations if correlation else [],
            "evidence_count": validation.evidence_count,
            "resolved": state.resolution_status,
            "devil_advocate": devil_advocate,   # alternative hypothesis
            "symptoms": detected_symptoms,       # detected symptom categories
            "debug_mode": debug_mode,            # root cause priority was active
        }

    def end_session(self, session_id: str):
        """Finalize and archive a session."""
        state = self._state_store.get_or_create(session_id)
        learning_loop.on_session_end(state)
        logger.info(f"Session {session_id[:8]} ended. Turns: {len(state.history)}")

    # ── Devil's Advocate ──────────────────────────────────────────────────────

    def _generate_devil_advocate(
        self,
        top_hypothesis,
        all_hypotheses: list,
    ) -> Optional[Dict[str, Any]]:
        """
        Devil's Advocate Mode.

        Takes the second-best hypothesis (if any) and formats it as an
        alternative explanation with its confidence delta vs the top.

        Returns None if:
          - There is no top hypothesis
          - There is no meaningful second hypothesis (confidence < 0.15)
          - The gap between top and second is so large the alternative is irrelevant (> 60%)

        Returns:
          {
            "alternative_hypothesis": str,
            "alternative_id": str,
            "alternative_confidence": float,
            "delta_vs_top": float,   # negative = lower than top
            "root_cause": str,
            "reason": str,           # 1-sentence justification
          }
        """
        if not top_hypothesis or len(all_hypotheses) < 2:
            return None

        # Pick the best alternative: second-ranked with confidence >= 0.15
        alternatives = [
            h for h in all_hypotheses[1:]
            if h.id != top_hypothesis.id and h.confidence >= 0.15
        ]
        if not alternatives:
            return None

        alt = alternatives[0]
        delta = round(alt.confidence - top_hypothesis.confidence, 3)  # negative

        # Don't surface if the gap is huge (alternative is irrelevant noise)
        if abs(delta) > 0.60:
            return None

        # Build a 1-sentence reason from the alternative hypothesis's evidence
        evidence_sources = ", ".join(alt.supporting_sources[:2]) if alt.evidence else "peu de preuves"
        reason = (
            f"Basé sur {evidence_sources} ({len(alt.evidence)} élément(s)), "
            f"la cause pourrait aussi être: {alt.root_cause[:120]}."
        )

        return {
            "alternative_hypothesis": alt.label,
            "alternative_id": alt.id,
            "alternative_confidence": round(alt.confidence, 3),
            "delta_vs_top": delta,
            "root_cause": alt.root_cause[:200],
            "reason": reason,
        }


# Singleton
orchestrator = N3ChatbotOrchestrator(mode=MODE_NATURAL)


# ─────────────────────────────────────────────────────────────────────────────
# Self-test scenario
# ─────────────────────────────────────────────────────────────────────────────

def run_test_scenario():
    """
    3-turn test + resolution + follow-up scenario.
    Runs without LLM — uses template-based response generator only.
    """
    orc = N3ChatbotOrchestrator(mode=MODE_NATURAL)
    session_id = "TEST-SCENARIO-001"
    separator = "─" * 70

    print(f"\n{'═' * 70}")
    print("  N3 CHATBOT ORCHESTRATOR — TEST SCENARIO")
    print(f"  Session: {session_id}")
    print(f"{'═' * 70}\n")

    turns = [
        ("Turn 1 — Problem report (no entity)",
         "je veux supprimer un équipement mais ça ne marche pas"),
        ("Turn 2 — Entity provided",
         "DSLAM222"),
        ("Turn 3 — Pronoun reference + action",
         "je veux le supprimer"),
        ("Turn 4 — Resolution confirmed",
         "problème résolu"),
        ("Turn 5 — New session: Resolution denied",
         None),   # Signal to start denial test
    ]

    # First 4 turns: normal + resolution
    for title, text in turns[:4]:
        print(f"{separator}\n{title}\n")
        print(f"  👤 User: {text}")
        result = orc.chat(session_id, text)
        _print_result(result)

    # End session
    orc.end_session(session_id)

    # Denial test — new session, 2 denials
    print(f"\n{'═' * 70}")
    print("  DENIAL TEST — New session")
    print(f"{'═' * 70}\n")

    session2 = "TEST-SCENARIO-002"
    denial_turns = [
        "DSLAM DSNRD001 ne fonctionne pas, je veux le supprimer",
        "non ça ne marche pas, le DSLAM est toujours là",
        "non toujours pas résolu",
    ]

    for i, text in enumerate(denial_turns):
        t_label = f"Turn {i+1}"
        if i >= 1:
            t_label += " (Denial)"
        print(f"{separator}\n{t_label}\n")
        print(f"  👤 User: {text}")
        # Second denial triggers bug suggestion
        intent_override = None
        if i >= 1:
            result = orc.chat(session2, text)
        else:
            result = orc.chat(session2, text)
        _print_result(result)

    orc.end_session(session2)

    # Learning stats
    stats = learning_loop.get_statistics()
    print(f"\n{separator}")
    print("LEARNING LOOP STATISTICS (internal):")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print(separator)


def _print_result(result: dict):
    tier = result.get("validation_tier", "?")
    score = result.get("validation_score", 0.0)
    needs_review = result.get("needs_review", False)
    tier_icon = {"HIGH": "✅", "MEDIUM": "⚠️", "LOW": "🚫"}.get(tier, "❓")
    print(f"  🤖 Intent: {result['intent']}")
    if result["entities"]:
        print(f"  📦 Entities: {result['entities']}")
    print(f"  📊 Confidence: {result['confidence']:.0%}")
    print(f"  {tier_icon} Validation: {tier} (score={score:.2f}){' — NEEDS REVIEW' if needs_review else ''}")
    if result["hypothesis"]:
        print(f"  🔍 Hypothesis: {result['hypothesis']}")
    if result.get("symptoms"):
        print(f"  🔬 Symptoms: {result['symptoms']}")
    if result.get("debug_mode"):
        print(f"  🚨 DEBUG MODE — root cause priority active")
    if result["sfd_violations"]:
        print(f"  ⚠️  SFD: {result['sfd_violations']}")
    print(f"  📚 Evidence count: {result['evidence_count']}")
    print(f"\n  Response:\n")
    for line in result["response"].split("\n"):
        print(f"    {line}")
    print()


if __name__ == "__main__":
    run_test_scenario()
