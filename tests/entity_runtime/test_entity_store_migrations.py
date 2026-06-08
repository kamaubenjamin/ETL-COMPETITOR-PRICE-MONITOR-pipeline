"""Tests for EntityStoreMigration — migration execution and verification."""
from __future__ import annotations

import sqlite3

import pytest

from src.entity_runtime.store.migrations import EntityStoreMigration, EXPECTED_TABLES


@pytest.fixture
def conn() -> sqlite3.Connection:
    """Create an in-memory SQLite connection."""
    c = sqlite3.connect(":memory:")
    return c


class TestMigration:
    """Migration operations."""

    def test_migration_creates_tables(self, conn: sqlite3.Connection):
        migration = EntityStoreMigration()
        applied = migration.run(conn)
        assert applied
        for table in EXPECTED_TABLES:
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            )
            assert cur.fetchone() is not None

    def test_migration_idempotent(self, conn: sqlite3.Connection):
        migration = EntityStoreMigration()
        migration.run(conn)
        applied = migration.run(conn)
        assert not applied

    def test_verify_passes_after_migration(self, conn: sqlite3.Connection):
        migration = EntityStoreMigration()
        migration.run(conn)
        assert migration.verify(conn)

    def test_verify_fails_before_migration(self, conn: sqlite3.Connection):
        migration = EntityStoreMigration()
        assert not migration.verify(conn)

    def test_rollback_drops_tables(self, conn: sqlite3.Connection):
        migration = EntityStoreMigration()
        migration.run(conn)
        assert migration.rollback(conn)
        for table in EXPECTED_TABLES:
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            )
            assert cur.fetchone() is None

    def test_get_current_version_after_migration(self, conn: sqlite3.Connection):
        migration = EntityStoreMigration()
        migration.run(conn)
        assert migration.get_current_version(conn) == 8

    def test_get_current_version_before_migration(self, conn: sqlite3.Connection):
        migration = EntityStoreMigration()
        assert migration.get_current_version(conn) == 0