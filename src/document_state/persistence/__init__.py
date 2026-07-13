"""Public persistence contracts for Durable Document State."""

from .config import (
    ACTIVE_BACKENDS,
    DEFERRED_BACKENDS,
    PersistenceBackend,
    PersistenceConfig,
    require_active_backend,
)
from .errors import PersistenceError, PersistenceErrorCode
from .migrations import (
    AppliedMigration,
    MigrationDefinition,
    MigrationEngine,
    validate_applied_migrations,
    validate_migration_sequence,
)
from .schema import (
    PrivacyClassification,
    SCHEMA_TABLES,
    TABLES_BY_NAME,
    TableMetadata,
    TableSemantics,
)

__all__ = [
    "ACTIVE_BACKENDS", "AppliedMigration", "DEFERRED_BACKENDS", "MigrationDefinition",
    "MigrationEngine", "PersistenceBackend", "PersistenceConfig", "PersistenceError",
    "PersistenceErrorCode", "PrivacyClassification", "SCHEMA_TABLES", "TABLES_BY_NAME",
    "TableMetadata", "TableSemantics", "require_active_backend",
    "validate_applied_migrations", "validate_migration_sequence",
]
