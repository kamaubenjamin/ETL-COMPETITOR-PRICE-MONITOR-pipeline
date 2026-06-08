"""EntityStoreMigration — schema migration runner for entity version store.

Provides execute, verify, and rollback operations for the entity version store
database schema (4 tables: entity_versions, entity_leases, entity_idempotency,
entity_conflict_log).
"""

from __future__ import annotations

import os
import sqlite3
from typing import Optional


MIGRATION_VERSION = 8
EXPECTED_TABLES = [
    "entity_versions",
    "entity_leases",
    "entity_idempotency",
    "entity_conflict_log",
]


class EntityStoreMigration:
    """Schema migration runner for entity version store.

    Manages the creation, verification, and rollback of the 4 entity
    concurrency tables.
    """

    def __init__(self, db_path: str = "data/entity_version_store.db") -> None:
        self._db_path = db_path

    def run(self, connection: object, migration_sql_path: str = "") -> bool:
        """Execute the migration against the given database connection.

        Args:
            connection: Database connection object (sqlite3.Connection).
            migration_sql_path: Path to the SQL migration file. If empty,
                uses the embedded SQL from the migration script.

        Returns:
            True if migration was applied, False if already applied.
        """
        conn = connection
        if not isinstance(conn, sqlite3.Connection):
            raise TypeError("connection must be a sqlite3.Connection")

        # Check if already migrated
        if self.verify(conn):
            return False

        if migration_sql_path and os.path.exists(migration_sql_path):
            with open(migration_sql_path, "r") as f:
                sql = f.read()
        else:
            sql = self._get_embedded_sql()

        conn.executescript(sql)
        conn.commit()
        return True

    def verify(self, connection: object) -> bool:
        """Verify that the migration has been applied.

        Args:
            connection: Database connection object.

        Returns:
            True if all 4 tables exist, False otherwise.
        """
        conn = connection
        if not isinstance(conn, sqlite3.Connection):
            raise TypeError("connection must be a sqlite3.Connection")

        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name IN "
            f"({','.join('?' for _ in EXPECTED_TABLES)})",
            EXPECTED_TABLES,
        )
        existing = {row[0] for row in cur.fetchall()}
        return set(EXPECTED_TABLES).issubset(existing)

    def rollback(self, connection: object) -> bool:
        """Rollback the migration (drop all 4 tables).

        Args:
            connection: Database connection object.

        Returns:
            True if rollback was successful.
        """
        conn = connection
        if not isinstance(conn, sqlite3.Connection):
            raise TypeError("connection must be a sqlite3.Connection")

        try:
            for table in reversed(EXPECTED_TABLES):
                conn.execute(f"DROP TABLE IF EXISTS {table}")
            conn.commit()
            return True
        except sqlite3.OperationalError:
            return False

    def get_current_version(self, connection: object) -> int:
        """Get the current migration version applied.

        Args:
            connection: Database connection object.

        Returns:
            Migration version number (8 for entity version store) if all
            tables exist, 0 otherwise.
        """
        if self.verify(connection):
            return MIGRATION_VERSION
        return 0

    @staticmethod
    def _get_embedded_sql() -> str:
        """Return the embedded SQL for creating the entity version store tables."""
        return """
            CREATE TABLE IF NOT EXISTS entity_versions (
                entity_version_key   TEXT NOT NULL,
                entity_type          TEXT NOT NULL,
                entity_id            TEXT NOT NULL,
                version              INTEGER NOT NULL,
                state                TEXT NOT NULL DEFAULT 'active',
                data                 TEXT NOT NULL,
                checksum             TEXT NOT NULL,
                previous_checksum    TEXT NOT NULL DEFAULT '',
                created_at           TEXT NOT NULL,
                created_by           TEXT NOT NULL,
                source_document_id   TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (entity_version_key, version)
            );
            CREATE INDEX IF NOT EXISTS idx_entity_versions_active
                ON entity_versions (entity_version_key, version DESC)
                WHERE state = 'active';
            CREATE INDEX IF NOT EXISTS idx_entity_versions_type
                ON entity_versions (entity_type, state);
            CREATE INDEX IF NOT EXISTS idx_entity_versions_source
                ON entity_versions (source_document_id);

            CREATE TABLE IF NOT EXISTS entity_leases (
                entity_version_key   TEXT PRIMARY KEY,
                holder_id            TEXT NOT NULL,
                acquired_at          TEXT NOT NULL,
                expires_at           TEXT NOT NULL,
                lease_duration_s     INTEGER NOT NULL DEFAULT 120,
                last_refreshed_at    TEXT NOT NULL,
                refresh_count        INTEGER NOT NULL DEFAULT 0,
                hostname             TEXT NOT NULL DEFAULT '',
                pid                  INTEGER NOT NULL DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_entity_leases_expired
                ON entity_leases (expires_at);

            CREATE TABLE IF NOT EXISTS entity_idempotency (
                idempotency_key      TEXT PRIMARY KEY,
                entity_version_key   TEXT NOT NULL,
                version              INTEGER NOT NULL,
                pipeline_run_id      TEXT NOT NULL,
                status               TEXT NOT NULL DEFAULT 'in_progress',
                created_at           TEXT NOT NULL,
                completed_at         TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_entity_idempotency_cleanup
                ON entity_idempotency (status, created_at);

            CREATE TABLE IF NOT EXISTS entity_conflict_log (
                conflict_id          INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_version_key   TEXT NOT NULL,
                conflict_type        TEXT NOT NULL,
                attempted_version    INTEGER NOT NULL,
                current_version      INTEGER NOT NULL,
                attempted_by         TEXT NOT NULL,
                current_holder       TEXT NOT NULL DEFAULT '',
                resolution           TEXT NOT NULL DEFAULT '',
                created_at           TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_entity_conflict_log_entity
                ON entity_conflict_log (entity_version_key, created_at DESC);
        """