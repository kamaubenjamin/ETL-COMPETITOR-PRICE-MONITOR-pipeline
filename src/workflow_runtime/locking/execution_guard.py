"""Abstract base class for the workflow execution guard.

The ``WorkflowExecutionGuard`` wraps the workflow execution lifecycle with
lock acquisition, lease refresh, and release.

Lifecycle
=========

1. **Idempotency check** (if idempotency_key provided):
   Check the ``WorkflowIdempotencyRegistry``. If the key exists with
   status ``"completed"``, skip execution and return the cached result.

2. **Lock acquisition**:
   Attempt to acquire a lock via the configured ``LockProvider``. If the
   lock is held by another holder, raise ``LockAcquisitionError``.

3. **Execution**:
   Execute the wrapped callable. Periodically refresh the lock lease
   (every ``REFRESH_INTERVAL_S`` seconds).

4. **Lock release**:
   On completion (success or failure), release the lock.

5. **Idempotency recording** (if idempotency_key provided):
   Record the outcome in the ``WorkflowIdempotencyRegistry``.

Context Manager
===============

The guard supports ``with`` statement usage for deterministic lifecycle
management::

    with guard:
        result = do_work()
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Optional, Tuple

from src.workflow_runtime.locking.models import LockAcquisition
from src.workflow_runtime.locking.exceptions import (
    LockAcquisitionError,
    IdempotencyRejectionError,
)


class WorkflowExecutionGuard(ABC):
    """Wraps workflow execution with lock lifecycle management.

    Parameters
    ----------
    lock_provider:
        The ``LockProvider`` to use for lock acquisition/release.
    idempotency_registry:
        Optional ``WorkflowIdempotencyRegistry`` for idempotency key
        deduplication.
    lease_duration_s:
        Default lease duration in seconds. Used when no explicit duration
        is provided via ``execute()``.
    refresh_interval_s:
        Interval in seconds between lease refresh attempts during
        execution.
    max_retries:
        Maximum number of lock acquisition retries.
    retry_delay_s:
        Base delay in seconds between retries (exponential backoff).
    """

    def __init__(
        self,
        lock_provider: Any,  # LockProvider — avoid circular import at runtime
        idempotency_registry: Any | None = None,  # Optional[WorkflowIdempotencyRegistry]
        lease_duration_s: int = 300,
        refresh_interval_s: int = 30,
        max_retries: int = 3,
        retry_delay_s: int = 5,
    ) -> None:
        self._lock_provider = lock_provider
        self._idempotency_registry = idempotency_registry
        self._lease_duration_s = lease_duration_s
        self._refresh_interval_s = refresh_interval_s
        self._max_retries = max_retries
        self._retry_delay_s = retry_delay_s

    @property
    def lock_provider(self) -> Any:
        """The configured ``LockProvider``."""
        return self._lock_provider

    @property
    def idempotency_registry(self) -> Any | None:
        """The configured ``WorkflowIdempotencyRegistry``, if any."""
        return self._idempotency_registry

    @abstractmethod
    def execute(
        self,
        workflow_id: str,
        holder_id: str,
        fn: Callable[[], Any],
        idempotency_key: str | None = None,
        lease_duration_s: int | None = None,
    ) -> Tuple[Any, Optional[LockAcquisition]]:
        """Execute a workflow function with full lock lifecycle.

        The lifecycle is: idempotency check → lock acquire → execute →
        (periodic refresh) → lock release → idempotency record.

        Parameters
        ----------
        workflow_id:
            The workflow identifier to lock on.
        holder_id:
            The identifier of the caller requesting execution.
        fn:
            The callable to execute under lock protection.
        idempotency_key:
            Optional idempotency key for deduplication.
        lease_duration_s:
            Optional override for the lease duration. Falls back to
            ``self._lease_duration_s`` if not provided.

        Returns
        -------
        Tuple[Any, Optional[LockAcquisition]]
            A tuple of ``(fn_result, lock_acquisition)`` where ``fn_result``
            is the return value of the executed callable, and
            ``lock_acquisition`` is the acquired lock or ``None`` if
            idempotency skipping occurred.

        Raises
        ------
        LockAcquisitionError
            If the lock cannot be acquired after all retries.
        IdempotencyRejectionError
            If the idempotency key has already been processed.
        """
        ...

    def __enter__(self) -> "WorkflowExecutionGuard":
        """Context manager entry — no-op for ABC."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> bool | None:
        """Context manager exit — no-op for ABC.

        Concrete implementations should release the lock here.
        """
        return None