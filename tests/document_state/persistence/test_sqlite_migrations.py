from dataclasses import replace
import sqlite3

import pytest

from src.document_state.persistence import PersistenceConfig, PersistenceError
from src.document_state.persistence.sqlite import (
    SQLiteConnectionFactory, apply_migrations, default_migrations,
)


def _factory(tmp_path):
    return SQLiteConnectionFactory(
        PersistenceConfig("sqlite", sqlite_path=str(tmp_path / "migrations.sqlite3"))
    )


def test_migrations_create_all_tables_and_populate_ledger(tmp_path):
    factory = _factory(tmp_path)
    applied = apply_migrations(factory, applied_at="2026-07-13T12:00:00+00:00")
    assert [item.migration_id for item in applied] == ["001_initial_document_state"]
    with factory.transaction() as connection:
        tables = {
            row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
    assert {
        "documents", "document_lifecycle_events", "processing_snapshots",
        "validation_issues", "matching_summaries", "review_summaries",
        "correction_summaries", "reprocess_plans", "workflow_runs",
        "audit_events", "schema_migrations",
    } <= tables


def test_migration_rerun_is_idempotent_and_checksum_drift_is_rejected(tmp_path):
    factory = _factory(tmp_path)
    first = apply_migrations(factory, applied_at="2026-07-13T12:00:00+00:00")
    assert apply_migrations(factory, applied_at="2026-07-13T13:00:00+00:00") == first
    changed = replace(default_migrations()[0], checksum="0" * 64)
    with pytest.raises(PersistenceError) as raised:
        apply_migrations(factory, (changed,))
    assert raised.value.code == "migration_conflict"
    assert "sqlite" not in str(raised.value).lower()


def test_migration_is_transactional(tmp_path):
    factory = _factory(tmp_path)
    apply_migrations(factory)
    with factory.transaction(write=True) as connection:
        connection.execute("DELETE FROM schema_migrations")
        connection.execute("DROP TABLE audit_events")
    with pytest.raises(PersistenceError):
        apply_migrations(factory)
    with factory.transaction() as connection:
        count = connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]
    assert count == 0
