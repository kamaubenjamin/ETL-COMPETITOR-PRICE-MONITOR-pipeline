"""Immutable migration metadata and validation; no migration execution."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..privacy import bounded_string, positive_version, utc_timestamp
from .errors import PersistenceError


class MigrationEngine(str, Enum):
    SQLITE = "sqlite"
    FUTURE_POSTGRES = "future_postgres"


def _engine(value: MigrationEngine | str, field: str = "engine") -> str:
    try:
        return value.value if isinstance(value, MigrationEngine) else MigrationEngine(value).value
    except (TypeError, ValueError):
        raise PersistenceError("invalid_migration", field=field) from None


def _checksum(value: object) -> str:
    if not isinstance(value, str) or len(value) != 64 or value.lower() != value:
        raise PersistenceError("invalid_migration", field="checksum")
    if any(character not in "0123456789abcdef" for character in value):
        raise PersistenceError("invalid_migration", field="checksum")
    return value


def _migration_id(value: object) -> str:
    try:
        safe = bounded_string(value, "migration_id", maximum=128)
    except ValueError:
        raise PersistenceError("invalid_migration", field="migration_id") from None
    if safe.lower() != safe or not safe.replace("_", "").isalnum():
        raise PersistenceError("invalid_migration", field="migration_id")
    return safe


@dataclass(frozen=True, slots=True)
class MigrationDefinition:
    migration_id: str
    engine: MigrationEngine | str
    checksum: str
    description: str
    sequence: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "migration_id", _migration_id(self.migration_id))
        object.__setattr__(self, "engine", _engine(self.engine))
        object.__setattr__(self, "checksum", _checksum(self.checksum))
        try:
            description = bounded_string(self.description, "description", maximum=256)
            sequence = positive_version(self.sequence)
        except ValueError:
            raise PersistenceError("invalid_migration", field="definition") from None
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "sequence", sequence)

    @property
    def identity(self) -> tuple[str, int, str]:
        return self.engine, self.sequence, self.migration_id

    def to_dict(self) -> dict[str, str | int]:
        return {
            "migration_id": self.migration_id,
            "engine": self.engine,
            "checksum": self.checksum,
            "description": self.description,
            "sequence": self.sequence,
        }


@dataclass(frozen=True, slots=True)
class AppliedMigration:
    migration_id: str
    engine: MigrationEngine | str
    checksum: str
    sequence: int
    applied_at: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "migration_id", _migration_id(self.migration_id))
        object.__setattr__(self, "engine", _engine(self.engine))
        object.__setattr__(self, "checksum", _checksum(self.checksum))
        try:
            sequence = positive_version(self.sequence)
            applied_at = utc_timestamp(self.applied_at, "applied_at")
        except ValueError:
            raise PersistenceError("invalid_migration", field="ledger") from None
        object.__setattr__(self, "sequence", sequence)
        object.__setattr__(self, "applied_at", applied_at)

    @property
    def identity(self) -> tuple[str, int, str]:
        return self.engine, self.sequence, self.migration_id

    def to_dict(self) -> dict[str, str | int]:
        return {
            "migration_id": self.migration_id,
            "engine": self.engine,
            "checksum": self.checksum,
            "sequence": self.sequence,
            "applied_at": self.applied_at,
        }


def validate_migration_sequence(
    migrations: tuple[MigrationDefinition, ...],
    *,
    engine: MigrationEngine | str,
) -> tuple[MigrationDefinition, ...]:
    safe_engine = _engine(engine)
    if not isinstance(migrations, tuple):
        raise PersistenceError("invalid_migration", field="migrations")
    if any(not isinstance(migration, MigrationDefinition) for migration in migrations):
        raise PersistenceError("invalid_migration", field="migrations")
    ordered = tuple(sorted(migrations, key=lambda migration: (migration.sequence, migration.migration_id)))
    ids: set[str] = set()
    sequences: set[int] = set()
    for migration in ordered:
        if migration.engine != safe_engine:
            raise PersistenceError("invalid_migration", field="engine")
        if migration.migration_id in ids or migration.sequence in sequences:
            raise PersistenceError("invalid_migration", field="migration_id")
        ids.add(migration.migration_id)
        sequences.add(migration.sequence)
    if ordered and tuple(migration.sequence for migration in ordered) != tuple(range(1, len(ordered) + 1)):
        raise PersistenceError("invalid_migration", field="sequence")
    return ordered


def validate_applied_migrations(
    planned: tuple[MigrationDefinition, ...],
    applied: tuple[AppliedMigration, ...],
    *,
    engine: MigrationEngine | str,
) -> tuple[MigrationDefinition, ...]:
    safe_engine = _engine(engine)
    ordered = validate_migration_sequence(planned, engine=safe_engine)
    if not isinstance(applied, tuple):
        raise PersistenceError("invalid_migration", field="ledger")
    if any(not isinstance(item, AppliedMigration) for item in applied):
        raise PersistenceError("invalid_migration", field="ledger")
    applied_by_id: dict[str, AppliedMigration] = {}
    applied_sequences: set[int] = set()
    for item in sorted(applied, key=lambda migration: (migration.sequence, migration.migration_id)):
        if item.engine != safe_engine:
            raise PersistenceError("invalid_migration", field="engine")
        if item.migration_id in applied_by_id or item.sequence in applied_sequences:
            raise PersistenceError("migration_conflict", field="migration_id")
        applied_by_id[item.migration_id] = item
        applied_sequences.add(item.sequence)
    if applied_sequences and applied_sequences != set(range(1, len(applied_sequences) + 1)):
        raise PersistenceError("migration_conflict", field="sequence")
    planned_by_id = {item.migration_id: item for item in ordered}
    for migration_id, ledger_item in applied_by_id.items():
        definition = planned_by_id.get(migration_id)
        if definition is None:
            raise PersistenceError("migration_conflict", field="migration_id")
        if definition.sequence != ledger_item.sequence or definition.checksum != ledger_item.checksum:
            raise PersistenceError("migration_conflict", field="checksum")
    return tuple(item for item in ordered if item.migration_id not in applied_by_id)
