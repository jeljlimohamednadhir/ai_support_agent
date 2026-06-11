import pytest

from app.services.chatbot.forensic_followup import ForensicFollowupHandler
from app.services.chatbot.workflow_intelligence import workflow_engine
from app.services.chatbot.intent_resolver import intent_resolver, ConversationState, INTENT_UNKNOWN


@pytest.fixture
def handler() -> ForensicFollowupHandler:
    return ForensicFollowupHandler()


def _assert_contract_sections(text: str) -> None:
    assert "### Diagnostic principal" in text
    assert "### Preuves collectées" in text
    assert "### Source code" in text
    assert "### Action N3 ciblée" in text


def test_01_find_code_function_returns_dslam_delete_reference(handler: ForensicFollowupHandler):
    text = handler.handle(
        forensic_intent="find_code_function",
        entity="DSLAM",
        cached_trace={"user_query": "quelle fonction supprime un equipement ?"},
        cached_bundle=None,
    )
    assert text is not None
    _assert_contract_sections(text)
    assert "ManageDslamBusinessImpl.deleteDslam()" in text


def test_02_vlan_workflow_contains_expected_chain():
    rendered = workflow_engine.render_workflow_response("comment créer un VLAN ?", entity="VLAN")
    assert "ManageCreationVlanBusinessImpl.checkInputs()" in rendered
    assert "ManageVlanBusinessImpl.checkVlanAvailability()" in rendered
    assert "ManageCreationVlanBusinessImpl.creerVlan()" in rendered
    assert "ManageVlanBusinessImpl.createVlan()" in rendered


def test_03_logs_without_context_explicitly_no_evidence(handler: ForensicFollowupHandler):
    text = handler.handle(
        forensic_intent="forensic_logs",
        entity="DSLAM-01",
        cached_trace=None,
        cached_bundle=None,
    )
    assert text is not None
    _assert_contract_sections(text)
    assert "no evidence available" in text


def test_04_unknown_fr_query_does_not_hallucinate_intent():
    state = ConversationState()
    result = intent_resolver.resolve("je veux la FR-999999 inconnue", state)
    assert result.intent in {INTENT_UNKNOWN, "forensic_evidence", "forensic_workflow", "forensic_root_cause"}


def test_05_followup_memory_reuses_root_cause(handler: ForensicFollowupHandler):
    trace = {
        "explanation": {
            "root_cause": "fk_violation_t_services",
            "collaborator_summary": "Contrainte FK détectée sur suppression DSLAM",
            "evidence_count": 2,
        }
    }
    text = handler.handle(
        forensic_intent="forensic_root_cause",
        entity="5050111",
        cached_trace=trace,
        cached_bundle=None,
    )
    assert text is not None
    _assert_contract_sections(text)
    assert "fk_violation_t_services" in text


def test_06_sql_safety_blocks_mutation_statements(handler: ForensicFollowupHandler):
    trace = {
        "explanation": {
            "technical_block": "UPDATE t_services SET status='S' WHERE eqpt_id=1;\nSELECT * FROM t_services WHERE eqpt_id=1;"
        }
    }
    text = handler.handle(
        forensic_intent="forensic_evidence",
        entity="DSLAM-X",
        cached_trace=trace,
        cached_bundle=None,
    )
    assert text is not None
    assert "UPDATE t_services" not in text
    assert "mutation SQL removed" in text


def test_07_forbidden_generic_wording_removed(handler: ForensicFollowupHandler):
    trace = {
        "explanation": {
            "technical_block": "N'hésitez pas à me donner plus de détails. Dites-moi si besoin."
        }
    }
    text = handler.handle(
        forensic_intent="forensic_evidence",
        entity="DSLAM-Y",
        cached_trace=trace,
        cached_bundle=None,
    )
    assert text is not None
    assert "N'hésitez pas" not in text
    assert "Dites-moi" not in text


def test_08_dslam_deletion_workflow_is_blocking_and_precise():
    wf = workflow_engine.resolve("comment supprimer un DSLAM ?")
    assert wf is not None
    rendered = wf.render()
    assert "services actifs" in rendered.lower()
    assert "ManageDslamBusinessImpl.deleteDslam()" in rendered


def test_09_guided_n3_response_has_targeted_action(handler: ForensicFollowupHandler):
    text = handler.handle(
        forensic_intent="forensic_workflow",
        entity="DSLAM",
        cached_trace={"explanation": {"workflow": "delete_dslam"}},
        cached_bundle=None,
    )
    assert text is not None
    _assert_contract_sections(text)
    assert "Action N3 ciblée" in text
    assert "contact" not in text.lower() or "contact support" not in text.lower()


@pytest.mark.parametrize(
    "intent",
    [
        "forensic_logs",
        "forensic_timeline",
        "forensic_evidence",
        "forensic_root_cause",
        "find_code_function",
    ],
)
def test_10_contract_applies_to_all_forensic_intents(handler: ForensicFollowupHandler, intent: str):
    text = handler.handle(
        forensic_intent=intent,
        entity="DSLAM-TEST",
        cached_trace={"user_query": "test forensic"},
        cached_bundle=None,
    )
    assert text is not None
    _assert_contract_sections(text)
