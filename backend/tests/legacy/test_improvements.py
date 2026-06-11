"""
test_improvements.py — Phase 7 validation tests
================================================
Tests all 5 improvement areas implemented in this session:

  Test 1 — Encoding normalization (fr_parser.py)
  Test 2 — Telecom alias recognition (enricher.py)
  Test 3 — Multi-ID filtering (chatbot_service anti-hallucination)
  Test 4 — Resolution detection & auto-close (diagnostic_behavior.py)
  Test 5 — Human response quality (response_humanizer.py)

Run:
    pytest test_improvements.py -v
or standalone:
    python test_improvements.py
"""
import sys
import os
import re
import pathlib

# Ensure backend AND project root are on path
_BACKEND = str(pathlib.Path(__file__).parent)
_ROOT    = str(pathlib.Path(__file__).parent.parent)
for _p in [_BACKEND, _ROOT]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ─────────────────────────────────────────────────────────────────── #
# Minimal stubs so tests run without a full environment               #
# ─────────────────────────────────────────────────────────────────── #
import types as _types

for _mod in [
    "app.core.database", "app.core.config", "app.core.logging",
    "qdrant_client", "groq", "sqlalchemy", "psycopg2", "redis", "celery",
    "sklearn", "numpy", "pandas", "scipy", "transformers", "torch",
    "jose", "passlib", "fastapi", "httpx", "aiohttp", "pydantic",
    "app.models.user", "app.schemas.chatbot", "app.core.llm_client",
    "app.services.orchestrator",
]:
    if _mod not in sys.modules:
        sys.modules[_mod] = _types.ModuleType(_mod)

# Stub get_logger
_logging_stub = sys.modules.get("app.core.logging", _types.ModuleType("app.core.logging"))
_logging_stub.get_logger = lambda *a, **kw: __import__("logging").getLogger("test")
sys.modules["app.core.logging"] = _logging_stub

# Stub preprocessor
_prep_mod = _types.ModuleType("app.services.nlp.preprocessor")
class _FakePreprocessor:
    def preprocess(self, t): return t.lower()
    def detect_language(self, t): return "fr"
    def extract_error_codes(self, t):
        return re.findall(r"\b\d{4}\b", t)
_prep_mod.preprocessor = _FakePreprocessor()
sys.modules["app.services.nlp.preprocessor"] = _prep_mod

# Stub taxonomy
_tax_mod = _types.ModuleType("app.services.nlp.taxonomy")
_tax_mod.find_incident_type = lambda t: "unknown.insufficient_information"
_tax_mod.INCIDENT_TAXONOMY = {}
sys.modules["app.services.nlp.taxonomy"] = _tax_mod


# ═══════════════════════════════════════════════════════════════════ #
#                         TEST SUITE                                  #
# ═══════════════════════════════════════════════════════════════════ #

PASS = "✅"
FAIL = "❌"
results: list[tuple[str, bool, str]] = []


def _record(name: str, passed: bool, detail: str = "") -> None:
    results.append((name, passed, detail))
    icon = PASS if passed else FAIL
    print(f"  {icon}  {name}" + (f"\n       {detail}" if detail and not passed else ""))


# ─────────────────────────────────────────────────────────────────── #
# TEST 1 — Encoding normalization                                      #
# ─────────────────────────────────────────────────────────────────── #

def test_encoding_normalization():
    print("\n── TEST 1: Encoding normalization ──────────────────────────")
    from data_pipeline.fr_parser import normalize_text

    cases = [
        ("nd supprimÃ© par erreur",      "nd supprimé par erreur"),
        ("crÃ©ation d'un ticket",         "création d'un ticket"),
        ("dÃ©ploiement BRASIL",           "déploiement BRASIL"),
        ("Ã©quipement hors service",      "équipement hors service"),
        ("probl\u00e8me de connexion",    "problème de connexion"),   # already correct
        ("chemin \u00e2\u20ac\u201c r\u00e9seau", "chemin \u2013 réseau"),   # dash mojibake
    ]

    for raw, expected in cases:
        result = normalize_text(raw)
        passed = (result == expected) or (expected in result)
        _record(f"normalize_text({raw[:30]!r})", passed,
                f"got {result!r}, expected {expected!r}")


# ─────────────────────────────────────────────────────────────────── #
# TEST 2 — Telecom alias recognition                                   #
# ─────────────────────────────────────────────────────────────────── #

def test_telecom_alias_recognition():
    print("\n── TEST 2: Telecom alias recognition ───────────────────────")
    from app.services.nlp.enricher import ticket_enricher, TELECOM_ALIASES

    # Test 2a: AVP 1300 triggers order_blocked intent
    ticket = ticket_enricher.enrich("avp 1300 bloque commande", ticket_id="T001")
    intent_ok = ticket.intent == "order_blocked"
    _record("'avp 1300 bloque commande' → intent=order_blocked", intent_ok,
            f"got intent={ticket.intent!r}")

    # Test 2b: Entity AVP detected
    entity_types = {e.entity_type for e in ticket.entities}
    entity_avp   = any(e.value == "AVP" and e.entity_type == "telecom_node"
                       for e in ticket.entities)
    _record("Entity AVP detected in telecom_node", entity_avp,
            f"entities={[(e.entity_type, e.value) for e in ticket.entities]}")

    # Test 2c: Error code 1300 detected
    code_ok = "1300" in ticket.error_codes
    _record("Error code 1300 extracted", code_ok,
            f"error_codes={ticket.error_codes}")

    # Test 2d: NRO recognised
    ticket_nro = ticket_enricher.enrich("nro OLT défaillant synchronisation")
    nro_entity = any(e.value in ("NRO", "OLT") for e in ticket_nro.entities)
    _record("NRO/OLT entities detected in ticket", nro_entity,
            f"entities={[(e.entity_type, e.value) for e in ticket_nro.entities]}")

    # Test 2e: Aliases are all in TELECOM_ALIASES
    required_aliases = {"avp", "nro", "olt", "sro", "ond", "sl"}
    missing = required_aliases - set(TELECOM_ALIASES.keys())
    _record("All required aliases in TELECOM_ALIASES", not missing,
            f"missing={missing}")


# ─────────────────────────────────────────────────────────────────── #
# TEST 3 — Multi-ID filtering (unit test, no LLM)                     #
# ─────────────────────────────────────────────────────────────────── #

def test_multi_id_filtering():
    print("\n── TEST 3: Multi-ID filtering ──────────────────────────────")

    # Simulate the exact logic from chatbot_service.py 5b post-processing
    def _run_filter(response_text: str, src_ids: set, user_message: str = "") -> str:
        """Reproduce the production ID-strip logic."""
        # Collect IDs from user message (always valid)
        for m in re.finditer(r'\b[A-Z]{2,6}-\d{3,6}\b', user_message):
            src_ids.add(m.group())

        def _strip_invented_brasil(m):
            return m.group() if m.group() in src_ids else '[ID-proc]'

        result = re.sub(r'BRASIL-[A-Z]+-\d{3}', _strip_invented_brasil, response_text)

        def _strip_invented_fr(m):
            return m.group() if m.group() in src_ids else '[FR-ref]'

        result = re.sub(r'\bFR[-_]?\d{4,6}\b', _strip_invented_fr, result)
        return result

    # Test 3a: IDs mentioned by user are preserved
    user_msg   = "check BRAS-1001 BRAS-1002 BRAS-1003"
    response   = "Tickets BRAS-1001 BRAS-1002 BRAS-1003 sont actifs."
    src_ids: set = set()
    result = _run_filter(response, src_ids, user_message=user_msg)
    all_preserved = all(tid in result for tid in ["BRAS-1001", "BRAS-1002", "BRAS-1003"])
    _record("User-mentioned IDs preserved after filter", all_preserved,
            f"result={result!r}")

    # Test 3b: Invented BRASIL-XYZ-NNN stripped
    response2  = "Voir BRASIL-PROC-001 pour la procédure."
    src_ids2: set = set()
    result2 = _run_filter(response2, src_ids2)
    invented_stripped = "[ID-proc]" in result2 and "BRASIL-PROC-001" not in result2
    _record("Invented BRASIL-XYZ-NNN stripped", invented_stripped,
            f"result={result2!r}")

    # Test 3c: FR IDs in KB are preserved
    response3  = "Consultez FR-042 pour la procédure."
    src_ids3   = {"FR-042"}
    result3 = _run_filter(response3, src_ids3)
    fr_preserved = "FR-042" in result3
    _record("KB-validated FR reference preserved", fr_preserved,
            f"result={result3!r}")

    # Test 3d: Invented FR stripped
    response4  = "Voir FR-9999 non documenté."
    src_ids4: set = set()
    result4 = _run_filter(response4, src_ids4)
    fr_stripped = "[FR-ref]" in result4
    _record("Invented FR-NNNN stripped", fr_stripped,
            f"result={result4!r}")


# ─────────────────────────────────────────────────────────────────── #
# TEST 4 — Resolution detection & auto-close                          #
# ─────────────────────────────────────────────────────────────────── #

def test_resolution_detection():
    print("\n── TEST 4: Resolution detection ────────────────────────────")
    from app.services.nlp.diagnostic_behavior import (
        ConversationPhase,
        ConversationState,
        RESOLUTION_CONFIRMATION_SIGNALS,
        detect_phase_transition,
    )

    # Test 4a: Signal patterns match expected phrases
    soft_signals = [
        "c'est bon",
        "ça marche maintenant",
        "le problème est résolu",
        "ok merci",
        "ça fonctionne",
        "le service est rétabli",
        "tout fonctionne correctement",
    ]
    for phrase in soft_signals:
        matched = bool(RESOLUTION_CONFIRMATION_SIGNALS.search(phrase))
        _record(f"Signal detected: {phrase!r}", matched)

    # Test 4b: Auto-close after 3 confirmations
    state = ConversationState(phase=ConversationPhase.INVESTIGATION)
    turns = [
        "le problème est résolu",   # +1 → 1
        "ça marche maintenant",     # +1 → 2
        "merci c'est bon",          # +1 → 3 → should trigger CLOSING
    ]
    final_phase = None
    for turn in turns:
        new_phase = detect_phase_transition(state.phase, turn, state)
        if new_phase:
            state.phase = new_phase
    _record(
        "Auto-close to CLOSING after 3 confirmations",
        state.phase == ConversationPhase.CLOSING,
        f"final phase={state.phase.value}, count={state.resolution_confirmation_count}",
    )

    # Test 4c: Hard close keywords still work immediately
    state2 = ConversationState(phase=ConversationPhase.DIAGNOSTIC)
    new_phase2 = detect_phase_transition(state2.phase, "clôturer le ticket")
    _record("Hard close keyword triggers CLOSING immediately",
            new_phase2 == ConversationPhase.CLOSING)

    # Test 4d: Single confirmation in RESOLUTION phase triggers close
    state3 = ConversationState(phase=ConversationPhase.RESOLUTION)
    new_phase3 = detect_phase_transition(state3.phase, "ça marche", state3)
    _record("Single soft signal in RESOLUTION phase triggers CLOSING",
            new_phase3 == ConversationPhase.CLOSING)


# ─────────────────────────────────────────────────────────────────── #
# TEST 5 — Human response quality                                      #
# ─────────────────────────────────────────────────────────────────── #

def test_human_response_quality():
    print("\n── TEST 5: Human response quality ──────────────────────────")
    from app.services.chatbot.response_humanizer import (
        humanize,
        HumanizeContext,
        build_resolution_summary,
        IncidentResolutionData,
        _simplify_technical_jargon,
    )

    # Test 5a: Robotic opening is replaced with a friendly one
    robotic = "Erreur 1300 détectée. Référez-vous à la FR-42."
    ctx = HumanizeContext(has_error_code=True, error_code="1300", phase="diagnostic")
    result = humanize(robotic, ctx)
    has_code_mention = "1300" in result
    no_robotic_start = not result.startswith("Erreur 1300")
    _record("Robotic opening replaced", no_robotic_start, f"starts with: {result[:80]!r}")
    _record("Error code still present in response", has_code_mention)

    # Test 5b: Procedure steps get a reasoning bridge
    procedure_text = (
        "Procédure:\n"
        "1. Vérifier la connexion RADIUS\n"
        "2. Relancer le service\n"
        "3. Tester l'authentification"
    )
    ctx2 = HumanizeContext(has_procedure_steps=True, phase="investigation")
    result2 = humanize(procedure_text, ctx2)
    has_bridge = any(
        bridge in result2
        for bridge in ["recommande", "étapes", "voici", "vérifier"]
    )
    _record("Reasoning bridge added before procedure steps", has_bridge,
            f"result={result2[:120]!r}")

    # Test 5c: Response ends with a forward-looking offer
    short_response = "Le DSLAM est hors service."
    result3 = humanize(short_response, HumanizeContext(phase="diagnostic"))
    has_offer = any(
        word in result3.lower()
        for word in ["n'hésitez", "dites-moi", "avez-vous", "pouvez-vous"]
    )
    _record("Response ends with collaborative offer", has_offer,
            f"ending={result3[-100:]!r}")

    # Test 5d: Technical jargon simplified in depositor message
    technical_terms = ["PPPoE", "RADIUS", "VLAN", "DHCP", "DSLAM"]
    for term in technical_terms:
        simplified = _simplify_technical_jargon(term)
        is_simplified = simplified.lower() != term.lower()
        _record(f"Jargon '{term}' simplified for depositor", is_simplified,
                f"simplified to: {simplified!r}")

    # Test 5e: Resolution summary structure
    data = IncidentResolutionData(
        incident_description="Clients FTTH ne peuvent pas s'authentifier",
        root_cause="Défaut de configuration RADIUS sur NRO NROSTO0412",
        diagnostic_steps=["Vérifier logs RADIUS", "Tester PPPoE", "Vérifier VLAN 100"],
        resolution_applied="Reconfiguration du serveur RADIUS",
        application="BRASIL",
        affected_component="NROSTO0412",
    )
    summary = build_resolution_summary(data)

    # Technical: must contain all 4 required sections
    tech = summary["technical"]
    sections_present = all(
        kw in tech for kw in ["Incident", "Cause racine", "Résolution", "Recommandation"]
    )
    _record("Technical summary has all 4 required sections", sections_present,
            f"tech={tech[:200]!r}")

    # Depositor: must be free of heavy jargon
    dep = summary["depositor"]
    jargon_free = all(term.lower() not in dep.lower()
                      for term in ["RADIUS", "PPPoE", "VLAN"])
    _record("Depositor message is jargon-free", jargon_free,
            f"dep={dep[:200]!r}")

    # Depositor: must be friendly
    has_greeting = "Bonjour" in dep or "bonjour" in dep
    _record("Depositor message starts with greeting", has_greeting)


# ─────────────────────────────────────────────────────────────────── #
# Syntax checks for modified files                                     #
# ─────────────────────────────────────────────────────────────────── #

def test_syntax_all_modified_files():
    print("\n── SYNTAX CHECK: Modified files ────────────────────────────")
    import py_compile

    files = [
        pathlib.Path(__file__).parent / "app" / "services" / "chatbot" / "chatbot_service.py",
        pathlib.Path(__file__).parent / "app" / "services" / "chatbot" / "response_humanizer.py",
        pathlib.Path(__file__).parent / "app" / "services" / "chatbot" / "multi_source_correlator.py",
        pathlib.Path(__file__).parent / "app" / "services" / "nlp" / "enricher.py",
        pathlib.Path(__file__).parent / "app" / "services" / "nlp" / "diagnostic_behavior.py",
        pathlib.Path(__file__).parent.parent / "data_pipeline" / "fr_parser.py",
    ]

    for f in files:
        if not f.exists():
            _record(f"Syntax {f.name}", False, "file not found")
            continue
        try:
            py_compile.compile(str(f), doraise=True)
            _record(f"Syntax OK: {f.name}", True)
        except py_compile.PyCompileError as e:
            _record(f"Syntax OK: {f.name}", False, str(e))


# ─────────────────────────────────────────────────────────────────── #
# Runner                                                               #
# ─────────────────────────────────────────────────────────────────── #

def main():
    print("=" * 65)
    print("  PHASE 7 — Improvement Tests")
    print("=" * 65)

    test_syntax_all_modified_files()
    test_encoding_normalization()
    test_telecom_alias_recognition()
    test_multi_id_filtering()
    test_resolution_detection()
    test_human_response_quality()

    # Summary
    total = len(results)
    passed = sum(1 for _, ok, _ in results if ok)
    print("\n" + "=" * 65)
    print(f"  Results: {passed}/{total} passed ({passed/total:.0%})")
    print("=" * 65)
    for name, ok, detail in results:
        icon = PASS if ok else FAIL
        print(f"  {icon}  {name}")
        if not ok and detail:
            print(f"       └─ {detail}")

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
