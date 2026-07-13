from dataclasses import FrozenInstanceError
import json

import pytest

from src.document_state.persistence import (
    AppliedMigration,
    MigrationDefinition,
    PersistenceError,
    validate_applied_migrations,
    validate_migration_sequence,
)


CHECKSUM_1 = "1" * 64
CHECKSUM_2 = "2" * 64
APPLIED_AT = "2026-07-13T09:00:00+00:00"


def _migration(migration_id="0001_initial", sequence=1, checksum=CHECKSUM_1, engine="sqlite"):
    return MigrationDefinition(migration_id, engine, checksum, "Initial durable schema", sequence)


def test_migration_contracts_are_immutable_and_json_compatible():
    migration = _migration()
    ledger = AppliedMigration("0001_initial", "sqlite", CHECKSUM_1, 1, APPLIED_AT)
    with pytest.raises(FrozenInstanceError):
        migration.checksum = CHECKSUM_2
    assert migration.identity == ledger.identity
    json.dumps(migration.to_dict())
    json.dumps(ledger.to_dict())


def test_sequence_validation_orders_deterministically_and_rejects_duplicates():
    second = _migration("add_indexes", 2, CHECKSUM_2)
    assert validate_migration_sequence((second, _migration()), engine="sqlite") == (_migration(), second)
    with pytest.raises(PersistenceError) as duplicate_id:
        validate_migration_sequence((_migration(), _migration(sequence=2)), engine="sqlite")
    assert duplicate_id.value.code == "invalid_migration"
    with pytest.raises(PersistenceError) as duplicate_sequence:
        validate_migration_sequence((_migration(), _migration("other", 1, CHECKSUM_2)), engine="sqlite")
    assert duplicate_sequence.value.code == "invalid_migration"


def test_checksum_and_engine_are_required_and_validated():
    with pytest.raises(PersistenceError) as checksum:
        _migration(checksum="not-a-checksum")
    assert checksum.value.code == "invalid_migration"
    with pytest.raises(PersistenceError) as engine:
        validate_migration_sequence((_migration(),), engine="future_postgres")
    assert engine.value.code == "invalid_migration"
    assert engine.value.field == "engine"


def test_applied_checksum_mismatch_detects_changed_migration():
    changed = AppliedMigration("0001_initial", "sqlite", CHECKSUM_2, 1, APPLIED_AT)
    with pytest.raises(PersistenceError) as raised:
        validate_applied_migrations((_migration(),), (changed,), engine="sqlite")
    assert raised.value.code == "migration_conflict"
    assert raised.value.field == "checksum"


def test_applied_ledger_returns_only_pending_migrations():
    second = _migration("add_indexes", 2, CHECKSUM_2)
    applied = AppliedMigration("0001_initial", "sqlite", CHECKSUM_1, 1, APPLIED_AT)
    assert validate_applied_migrations((_migration(), second), (applied,), engine="sqlite") == (second,)


def test_unknown_applied_identity_is_a_safe_conflict():
    unknown = AppliedMigration("unknown_schema", "sqlite", CHECKSUM_2, 2, APPLIED_AT)
    with pytest.raises(PersistenceError) as raised:
        validate_applied_migrations((_migration(),), (unknown,), engine="sqlite")
    assert raised.value.code == "migration_conflict"
    assert "unknown_schema" not in str(raised.value)


def test_malformed_sequence_and_ledger_entries_fail_safely():
    with pytest.raises(PersistenceError) as definition:
        validate_migration_sequence((object(),), engine="sqlite")
    assert definition.value.code == "invalid_migration"
    with pytest.raises(PersistenceError) as ledger:
        validate_applied_migrations((_migration(),), (object(),), engine="sqlite")
    assert ledger.value.code == "invalid_migration"


def test_applied_ledger_rejects_sequence_gaps():
    second = _migration("0002_indexes", 2, CHECKSUM_2)
    applied_second = AppliedMigration("0002_indexes", "sqlite", CHECKSUM_2, 2, APPLIED_AT)
    with pytest.raises(PersistenceError) as raised:
        validate_applied_migrations((_migration(), second), (applied_second,), engine="sqlite")
    assert raised.value.code == "migration_conflict"
    assert raised.value.field == "sequence"
