"""
tests/test_truth_enforcement.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Unit tests for the TruthEnforcementEngine.

Tests:
  - Unknown SQL tables are flagged
  - Known SQL tables pass through
  - SQL mutations (UPDATE/DELETE/INSERT) are blocked
  - Shell commands are blocked
  - SQL placeholders are blocked
  - Known functions pass through
  - Unknown functions are logged (not replaced — flagged only)
  - Empty text returns cleanly
  - Nested/multi-mutation blocks are all caught
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from app.services.chatbot.truth_enforcement import (
    TruthEnforcementEngine,
    truth_engine,
    truth_engine_lenient,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@pytest.fixture
def engine():
    return TruthEnforcementEngine(strict=True)


@pytest.fixture
def lenient():
    return TruthEnforcementEngine(strict=False)


# ── SQL Mutation Tests ─────────────────────────────────────────────────────

class TestSQLMutationBlocking:

    def test_update_in_sql_block_is_blocked(self, engine):
        text = "```sql\nUPDATE t_equipments SET status='DELETED' WHERE id=1\n```"
        report = engine.enforce(text)
        assert "UPDATE" not in report.clean_text
        assert "bloquée" in report.clean_text or "🚫" in report.clean_text
        assert report.has_violations
        assert any(v.kind == "sql_mutation" for v in report.violations)

    def test_delete_from_in_sql_block_is_blocked(self, engine):
        text = "```sql\nDELETE FROM t_cards WHERE card_id = 42\n```"
        report = engine.enforce(text)
        assert report.has_violations
        assert any(v.kind == "sql_mutation" for v in report.violations)

    def test_insert_into_is_blocked(self, engine):
        text = "```sql\nINSERT INTO t_vlan (vlan_id, name) VALUES (100, 'test')\n```"
        report = engine.enforce(text)
        assert report.has_violations

    def test_alter_table_is_blocked(self, engine):
        text = "Vous pouvez exécuter: ```sql\nALTER TABLE t_equipments ADD COLUMN new_col INT\n```"
        report = engine.enforce(text)
        assert report.has_violations

    def test_drop_table_is_blocked(self, engine):
        text = "```sql\nDROP TABLE t_temp_data\n```"
        report = engine.enforce(text)
        assert report.has_violations

    def test_truncate_is_blocked(self, engine):
        text = "```sql\nTRUNCATE TABLE t_making_files\n```"
        report = engine.enforce(text)
        assert report.has_violations

    def test_select_is_allowed(self, engine):
        text = "```sql\nSELECT * FROM t_equipments WHERE eqpt_name = 'DSFEN104'\n```"
        report = engine.enforce(text)
        assert "SELECT" in report.clean_text
        mutation_viols = [v for v in report.violations if v.kind == "sql_mutation"]
        assert len(mutation_viols) == 0

    def test_multiple_mutations_all_blocked(self, engine):
        text = (
            "```sql\nUPDATE t_equipments SET status='X' WHERE id=1\n```\n"
            "```sql\nDELETE FROM t_cards WHERE card_id=2\n```"
        )
        report = engine.enforce(text)
        sql_viols = [v for v in report.violations if v.kind == "sql_mutation"]
        assert len(sql_viols) >= 2


# ── Shell Command Tests ────────────────────────────────────────────────────

class TestShellCommandBlocking:

    def test_bash_block_is_blocked(self, engine):
        text = "```bash\nsudo systemctl restart tomcat\n```"
        report = engine.enforce(text)
        assert report.has_violations
        assert any(v.kind == "shell_cmd" for v in report.violations)

    def test_sh_block_is_blocked(self, engine):
        text = "```sh\nbash deploy.sh --env prod\n```"
        report = engine.enforce(text)
        assert report.has_violations

    def test_rm_command_is_blocked(self, engine):
        text = "```bash\nrm -rf /tmp/brasil_cache\n```"
        report = engine.enforce(text)
        assert report.has_violations


# ── SQL Placeholder Tests ──────────────────────────────────────────────────

class TestSQLPlaceholderBlocking:

    def test_placeholder_in_sql_block_is_blocked(self, engine):
        text = "```sql\nSELECT * FROM t_equipments WHERE eqpt_name = [NOM_EQPT]\n```"
        report = engine.enforce(text)
        assert report.has_violations
        assert any(v.kind == "sql_placeholder" for v in report.violations)

    def test_multiple_placeholders(self, engine):
        text = "```sql\nUPDATE t_equipments SET status=[STATUT] WHERE id=[EQPT_ID]\n```"
        report = engine.enforce(text)
        assert report.has_violations  # both placeholder AND mutation


# ── Table Validation Tests ─────────────────────────────────────────────────

class TestTableValidation:

    def test_known_table_passes(self, engine):
        text = "La table `t_equipments` contient les équipements."
        report = engine.enforce(text)
        assert "t_equipments" in report.clean_text
        table_viols = [v for v in report.violations if v.kind == "table"]
        assert len(table_viols) == 0

    def test_unknown_table_is_flagged(self, engine):
        text = "Vérifiez la table t_services pour les données."
        report = engine.enforce(text)
        # Should be flagged with ⚠️ or warning
        assert "⚠️" in report.clean_text or report.has_violations

    def test_invented_table_is_flagged(self, engine):
        text = "INSERT INTO t_fake_brasil_data VALUES (1, 'test')"
        report = engine.enforce(text)
        # mutation blocked first — but table validation also applies
        assert report.has_violations

    def test_lenient_mode_does_not_flag_tables(self, lenient):
        text = "La table t_invented_table contient des données."
        report = lenient.enforce(text)
        table_viols = [v for v in report.violations if v.kind == "table"]
        assert len(table_viols) == 0


# ── Empty / Edge Cases ─────────────────────────────────────────────────────

class TestEdgeCases:

    def test_empty_text_returns_clean(self, engine):
        report = engine.enforce("")
        assert report.clean_text == ""
        assert not report.has_violations

    def test_none_like_empty_returns_clean(self, engine):
        report = engine.enforce("  ")
        # Should not crash
        assert isinstance(report.clean_text, str)

    def test_clean_response_has_no_violations(self, engine):
        text = (
            "🧠 **Diagnostic**\n"
            "La suppression de l'équipement DSFEN104 est bloquée par des services actifs.\n\n"
            "📌 **Preuves**\n"
            "- `t_equipments` : status = ACTIVE\n"
            "- `t_mrt_access_dslams` : 3 MRT actifs\n\n"
            "✅ **Actions recommandées**\n"
            "1. Supprimer les services MRT actifs\n"
            "2. Relancer la suppression"
        )
        report = engine.enforce(text)
        mutation_viols = [v for v in report.violations if v.kind == "sql_mutation"]
        shell_viols = [v for v in report.violations if v.kind == "shell_cmd"]
        assert len(mutation_viols) == 0
        assert len(shell_viols) == 0

    def test_truth_report_summary_no_violations(self, engine):
        report = engine.enforce("SELECT * FROM t_equipments")
        assert "✅" in report.summary()

    def test_truth_report_summary_with_violations(self, engine):
        report = engine.enforce("```sql\nDELETE FROM t_equipments WHERE id=1\n```")
        assert "violation" in report.summary().lower()

    def test_utility_is_known_table(self, engine):
        assert engine.is_known_table("t_equipments") is True
        assert engine.is_known_table("t_invented_fake_table_xyz") is False

    def test_utility_get_sql_mutations(self, engine):
        text = "UPDATE t_cards SET x=1; DELETE FROM t_ports WHERE id=2"
        mutations = engine.get_sql_mutations(text)
        assert "UPDATE" in mutations
        assert "DELETE" in mutations


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
