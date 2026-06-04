"""Workflow Runtime Locking v1 — database-backed locks with execution leases and idempotency keys.

This module provides a pluggable locking subsystem for the Workflow Runtime,
preventing duplicate concurrent execution of the same workflow across processes
and hosts. It implements the strategy defined in
:doc:`/docs/architecture/WORKFLOW_RUNTIME_LOCKING_V1_PLAN.md`.

Strategy
--------
- **Primary**: Database-backed row-level locking with execution leases
  (``DBLockProvider``). The existing ``history_store`` database is used —
  no new external dependencies.
- **Fallback**: File-based advisory locking (``FileLockProvider``) for
  single-host deployments without database access.
- **Development/Test**: In-memory locking (``MemoryLockProvider``).
- **Complementary**: Idempotency keys via ``WorkflowIdempotencyRegistry``
  prevent re-execution of already-completed runs.

Data Contracts
--------------
- ``LockAcquisition`` — immutable record of a successful lock acquisition
- ``IdempotencyRecord`` — immutable record of an idempotency key claim

Exceptions
----------
- ``LockAcquisitionError`` — raised when a lock cannot be acquired
- ``IdempotencyRejectionError`` — raised when an idempotency key has
  already been processed
- ``LockProviderError`` — raised when a lock provider encounters an
  unrecoverable error
- ``LeaseRefreshError`` — raised when lease refresh fails (non-fatal)

Example
-------
    from src.workflow_runtime.locking import (
        LockAcquisition, LockAcquisitionError, LockProvider,
        WorkflowExecutionGuard
    )
"""

from src.workflow_runtime.locking.models import LockAcquisition, IdempotencyRecord
from src.workflow_runtime.locking.exceptions import (
    LockAcquisitionError,
    IdempotencyRejectionError,
    LockProviderError,
    LeaseRefreshError,
)
from src.workflow_runtime.locking.lock_provider import LockProvider, LockProviderRegistry
from src.workflow_runtime.locking.execution_guard import WorkflowExecutionGuard
from src.workflow_runtime.locking.idempotency import (
    WorkflowIdempotencyRegistry,
    MemoryIdempotencyRegistry,
    DBIdempotencyRegistry,
)
from src.workflow_runtime.locking.providers import (
    MemoryLockProvider,
    FileLockProvider,
    DBLockProvider,
)

__all__ = [
    # Models
    "LockAcquisition",
    "IdempotencyRecord",
    # Exceptions
    "LockAcquisitionError",
    "IdempotencyRejectionError",
    "LockProviderError",
    "LeaseRefreshError",
    # Locking abstractions
    "LockProvider",
    "LockProviderRegistry",
    "WorkflowExecutionGuard",
    "WorkflowIdempotencyRegistry",
    # Concrete implementations
    "MemoryLockProvider",
    "FileLockProvider",
    "DBLockProvider",
    "MemoryIdempotencyRegistry",
    "DBIdempotencyRegistry",
]
