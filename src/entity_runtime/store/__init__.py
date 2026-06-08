"""Entity Version Store — append-only version history for entity concurrency hardening.

Provides the persistence layer for versioned entity operations:
  - EntityVersionRecord: immutable version record dataclass
  - EntityVersionStore (ABC): versioned CRUD with compare-and-swap
  - EntityIdempotencyRegistry (ABC): idempotency key management
  - IdempotencyResult: result of idempotency check

Version records are append-only: each write creates a new row,
previous versions are marked 'superseded'.
"""

from src.entity_runtime.store.idempotency import EntityIdempotencyRegistry, IdempotencyResult
from src.entity_runtime.store.version_store import EntityVersionRecord, EntityVersionStore

__all__ = [
    "EntityIdempotencyRegistry",
    "EntityVersionRecord",
    "EntityVersionStore",
    "IdempotencyResult",
]