"""
tests/test_provenance.py
━━━━━━━━━━━━━━━━━━━━━━━━
Unit tests for the ProvenanceEngine and provenance formatters.

Tests:
  - ProvenanceRecord serialization
  - Factory functions (from_log, from_db, from_code, from_fr, from_qdrant)
  - ProvenanceEngine.add_from_bundle()
  - ProvenanceEngine.add_from_kb_blocks()
  - render_footer() produces expected sections
  - Deduplication works
  - Empty engine returns empty string
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from app.services.chatbot.provenance_engine import (
    ProvenanceRecord,
    ProvenanceEngine,
    make_provenance_engine,
    provenance_from_log_event,
    provenance_from_db_evidence,
    provenance_from_code_node,
    provenance_from_fr,
    provenance_from_qdrant,
    provenance_from_ssh,
    build_response_provenance_footer,
)


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def sample_record():
    return ProvenanceRecord(
        source_type="runtime_log",
        source_name="catalina.out",
        file="catalina.out",
        server="op49mwa11",
        timestamp="2026-05-18T10:30:00",
        confidence=0.9,
    )


@pytest.fixture
def code_record():
    return ProvenanceRecord(
        source_type="source_code",
        source_name="ManageDslamBusinessImpl.deleteDslam()",
        file="ManageDslamBusinessImpl.java",
        class_name="ManageDslamBusinessImpl",
        method="deleteDslam",
        line_number=1787,
        confidence=1.0,
    )


@pytest.fixture
def db_record():
    return ProvenanceRecord(
        source_type="database",
        source_name="PostgreSQL — t_equipments",
        table="t_equipments",
        server="op49mdb11",
        confidence=0.95,
    )


@pytest.fixture
def fr_record():
    return ProvenanceRecord(
        source_type="FR",
        source_name="FR-DSLAM-DELETE-001",
        fr_id="FR-DSLAM-DELETE-001",
        confidence=0.9,
    )


# ── ProvenanceRecord Tests ─────────────────────────────────────────────────

class TestProvenanceRecord:

    def test_to_dict_excludes_none_fields(self, sample_record):
        d = sample_record.to_dict()
        assert "source_type" in d
        assert "file" in d
        assert None not in d.values()

    def test_to_display_line_includes_server(self, sample_record):
        line = sample_record.to_display_line()
        assert "op49mwa11" in line
        assert "catalina.out" in line

    def test_to_display_line_includes_class_method(self, code_record):
        line = code_record.to_display_line()
        assert "ManageDslamBusinessImpl" in line
        assert "deleteDslam" in line

    def test_to_display_line_includes_table(self, db_record):
        line = db_record.to_display_line()
        assert "t_equipments" in line

    def test_to_display_line_includes_fr_id(self, fr_record):
        line = fr_record.to_display_line()
        assert "FR-DSLAM-DELETE-001" in line

    def test_confidence_percentage_in_display(self, sample_record):
        line = sample_record.to_display_line()
        assert "90%" in line  # 0.9 → 90%


# ── Factory Functions Tests ────────────────────────────────────────────────

class TestFactoryFunctions:

    def test_provenance_from_log_event(self):
        class FakeEvent:
            source = "catalina.out"
            timestamp = "2026-05-18T10:00:00"
            server = "op49mwa11"
            relevance_score = 0.85
            message = "ERROR - deletion failed"

        record = provenance_from_log_event(FakeEvent())
        assert record.source_type == "runtime_log"
        assert record.source_name == "catalina.out"
        assert record.server == "op49mwa11"
        assert record.confidence == 0.85

    def test_provenance_from_db_evidence(self):
        db_ev = {
            "t_equipments": [{"id": 1, "name": "DSFEN104"}],
            "t_cards": [{"card_id": 5}],
        }
        records = provenance_from_db_evidence(db_ev)
        assert len(records) == 2
        assert any(r.table == "t_equipments" for r in records)
        assert all(r.source_type == "database" for r in records)

    def test_provenance_from_db_evidence_empty(self):
        records = provenance_from_db_evidence({})
        assert records == []

    def test_provenance_from_code_node(self):
        node = {
            "class": "ManageDslamBusinessImpl",
            "method": "deleteDslam",
            "file": "services/dslam/ManageDslamBusinessImpl.java",
            "line": 1787,
        }
        record = provenance_from_code_node(node)
        assert record.source_type == "source_code"
        assert record.class_name == "ManageDslamBusinessImpl"
        assert record.method == "deleteDslam"
        assert record.line_number == 1787
        assert record.file == "ManageDslamBusinessImpl.java"

    def test_provenance_from_fr(self):
        record = provenance_from_fr("FR-VLAN-204", "Création VLAN procédure")
        assert record.source_type == "FR"
        assert record.fr_id == "FR-VLAN-204"
        assert "FR-VLAN-204" in record.raw_excerpt

    def test_provenance_from_qdrant_block(self):
        block = {
            "fr_id": "FR-1234",
            "title": "Suppression DSLAM — procédure complète",
            "trust_score": 85,
        }
        record = provenance_from_qdrant(block)
        assert record.source_type == "vector_knowledge"
        assert record.fr_id == "FR-1234"
        assert record.confidence == 0.85

    def test_provenance_from_ssh(self):
        node = {"check": "db_residual_check", "server": "op49mdb11"}
        record = provenance_from_ssh(node)
        assert record.source_type == "SSH"
        assert record.server == "op49mdb11"


# ── ProvenanceEngine Tests ─────────────────────────────────────────────────

class TestProvenanceEngine:

    def test_empty_engine_returns_empty_footer(self):
        engine = make_provenance_engine()
        assert engine.render_footer() == ""
        assert engine.render_inline_section() == ""
        assert not engine.has_provenance()

    def test_add_single_record(self, sample_record):
        engine = make_provenance_engine()
        engine.add(sample_record)
        assert engine.has_provenance()

    def test_footer_includes_source_type_section(self, sample_record, db_record):
        engine = make_provenance_engine()
        engine.add(sample_record)
        engine.add(db_record)
        footer = engine.render_footer()
        assert "Sources" in footer
        assert "runtime_log" in footer or "📋" in footer
        assert "database" in footer or "🗄️" in footer

    def test_deduplication_removes_duplicates(self, sample_record):
        engine = make_provenance_engine()
        engine.add(sample_record)
        engine.add(sample_record)  # same record twice
        records = engine._deduplicate(engine.get_records())
        assert len(records) == 1

    def test_reset_clears_records(self, sample_record):
        engine = make_provenance_engine()
        engine.add(sample_record)
        engine.reset()
        assert not engine.has_provenance()

    def test_add_from_kb_blocks(self):
        engine = make_provenance_engine()
        blocks = [
            {"fr_id": "FR-001", "title": "Test FR", "trust_score": 80},
            {"fr_id": "FR-002", "title": "Test FR 2", "trust_score": 75},
        ]
        engine.add_from_kb_blocks(blocks)
        assert engine.has_provenance()
        assert len(engine.get_records()) == 2

    def test_add_from_code_nodes(self):
        engine = make_provenance_engine()
        nodes = [
            {"class": "TestClass", "method": "testMethod", "file": "TestClass.java", "line": 100},
        ]
        engine.add_from_code_nodes(nodes)
        assert engine.has_provenance()
        records = engine.get_records()
        assert records[0].class_name == "TestClass"

    def test_explain_sources_with_data(self, sample_record, db_record):
        engine = make_provenance_engine()
        engine.add(sample_record)
        engine.add(db_record)
        explanation = engine.explain_sources()
        assert "catalina.out" in explanation or "t_equipments" in explanation

    def test_explain_sources_empty(self):
        engine = make_provenance_engine()
        explanation = engine.explain_sources()
        assert "Aucune" in explanation or "aucune" in explanation

    def test_max_records_limit(self):
        engine = make_provenance_engine()
        for i in range(10):
            engine.add(ProvenanceRecord(
                source_type="database",
                source_name=f"table_{i}",
                confidence=0.9,
            ))
        footer = engine.render_footer(max_records=3)
        # Should have at most 3 records in the footer
        assert footer.count("table_") <= 3


# ── build_response_provenance_footer Tests ─────────────────────────────────

class TestBuildProvenanceFooter:

    def test_footer_has_separator(self):
        records = [
            ProvenanceRecord(source_type="runtime_log", source_name="catalina.out", confidence=0.9),
        ]
        footer = build_response_provenance_footer(records)
        assert "---" in footer
        assert "Sources" in footer

    def test_empty_records_returns_empty(self):
        assert build_response_provenance_footer([]) == ""

    def test_groups_by_source_type(self):
        records = [
            ProvenanceRecord(source_type="runtime_log", source_name="catalina.out", confidence=0.9),
            ProvenanceRecord(source_type="source_code", source_name="ManageDslamBusinessImpl", confidence=1.0),
            ProvenanceRecord(source_type="FR", source_name="FR-001", confidence=0.85),
        ]
        footer = build_response_provenance_footer(records)
        assert "runtime_log" in footer
        assert "source_code" in footer
        assert "FR" in footer


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
