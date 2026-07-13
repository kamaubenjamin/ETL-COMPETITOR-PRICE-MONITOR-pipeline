"""Ordered, transactional SQLite schema migration application."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path
import sqlite3

from ..errors import PersistenceError
from ..migrations import AppliedMigration, MigrationDefinition, validate_applied_migrations
from .connection import SQLiteConnectionFactory


_SCHEMA_PATH = Path(__file__).with_name("schema.sql")
_TENANT_SCOPE_PATH = Path(__file__).with_name("002_add_document_tenant_scope.sql")
_LEDGER_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_id TEXT PRIMARY KEY,
    engine TEXT NOT NULL,
    checksum TEXT NOT NULL,
    description TEXT NOT NULL,
    sequence INTEGER NOT NULL UNIQUE,
    applied_at TEXT NOT NULL
)
"""


def schema_sql() -> str:
    try:
        return _SCHEMA_PATH.read_text(encoding="utf-8")
    except OSError:
        raise PersistenceError("invalid_migration", field="schema") from None


def tenant_scope_sql() -> str:
    try:
        return _TENANT_SCOPE_PATH.read_text(encoding="utf-8")
    except OSError:
        raise PersistenceError("invalid_migration", field="tenant_scope_schema") from None


def default_migrations() -> tuple[MigrationDefinition, ...]:
    sql = schema_sql()
    tenant_sql = tenant_scope_sql()
    return (
        MigrationDefinition(
            migration_id="001_initial_document_state",
            engine="sqlite",
            checksum=hashlib.sha256(sql.encode("utf-8")).hexdigest(),
            description="Create durable Document State tables and indexes.",
            sequence=1,
        ),
        MigrationDefinition(
            migration_id="002_add_document_tenant_scope",
            engine="sqlite",
            checksum=hashlib.sha256(tenant_sql.encode("utf-8")).hexdigest(),
            description="Add tenant and ownership columns to documents.",
            sequence=2,
        ),
    )


def _statements(sql: str) -> tuple[str, ...]:
    statements = tuple(part.strip() for part in sql.split(";") if part.strip())
    if not statements or any(not sqlite3.complete_statement(f"{item};") for item in statements):
        raise PersistenceError("invalid_migration", field="schema")
    return statements


def _applied(connection: sqlite3.Connection) -> tuple[AppliedMigration, ...]:
    rows = connection.execute(
        "SELECT migration_id, engine, checksum, sequence, applied_at "
        "FROM schema_migrations ORDER BY sequence, migration_id"
    ).fetchall()
    try:
        return tuple(AppliedMigration(**dict(row)) for row in rows)
    except (TypeError, ValueError, PersistenceError):
        raise PersistenceError("migration_conflict", field="ledger") from None


def apply_migrations(
    factory: SQLiteConnectionFactory,
    migrations: tuple[MigrationDefinition, ...] | None = None,
    *,
    applied_at: str | None = None,
) -> tuple[AppliedMigration, ...]:
    planned = default_migrations() if migrations is None else migrations
    timestamp = applied_at or datetime.now(timezone.utc).isoformat()
    with factory.transaction(write=True) as connection:
        connection.execute(_LEDGER_SQL)
        pending = validate_applied_migrations(planned, _applied(connection), engine="sqlite")
        sql_by_id = {
            "001_initial_document_state": schema_sql(),
            "002_add_document_tenant_scope": tenant_scope_sql(),
        }
        for migration in pending:
            sql = sql_by_id.get(migration.migration_id)
            if sql is None or hashlib.sha256(sql.encode("utf-8")).hexdigest() != migration.checksum:
                raise PersistenceError("migration_conflict", field="checksum")
            for statement in _statements(sql):
                connection.execute(statement)
            connection.execute(
                "INSERT INTO schema_migrations "
                "(migration_id, engine, checksum, description, sequence, applied_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (migration.migration_id, migration.engine, migration.checksum,
                 migration.description, migration.sequence, timestamp),
            )
        return _applied(connection)
