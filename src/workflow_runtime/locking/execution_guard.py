"""Workflow execution guard — wraps execution with lock lifecycle management.

The ``WorkflowExecutionGuard`` manages the full lock lifecycle around
workflow execution:

1. **Idempotency check** — if an idempotency key is provided and the
   registry reports it as completed, skip execution.
2. **Lock acquisition** — acquire a lock via the configured provider with
   retry + exponential backoff.
3. **Execution** — execute the wrapped callable with periodic lease refresh.
4. **Lock release** — release the lock on completion (success or failure).
5. **Idempotency recording** — record the outcome in the registry.

Context Manager
===============
The guard supports ``with`` statement usage::

    with guard:
        result = do_work()
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Callable, Optional, Tuple

from src.workflow_runtime.locking.models import LockAcquisition
from src.workflow_runtime.locking.exceptions import (
    LockAcquisitionError,
    IdempotencyRejectionError,
    LeaseRefreshError,
)

logger = logging.getLogger(__name__)


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
        execution. Must be at most ``lease_duration_s / 3``.
    max_retries:
        Maximum number of lock acquisition retries.
    retry_delay_s:
        Base delay in seconds between retries (exponential backoff).
    """

    def __init__(
        self,
        lock_provider: Any,  # LockProvider
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
        self._current_lock: LockAcquisition | None = None

        # Validate refresh interval vs lease duration
        if lease_duration_s < refresh_interval_s * 3:
            logger.warning(
                "lease_duration_s=%d is less than 3x refresh_interval_s=%d. "
                "Lease may expire before refresh completes.",
                lease_duration_s,
                refresh_interval_s,
            )

    @property
    def lock_provider(self) -> Any:
        """The configured ``LockProvider``."""
        return self._lock_provider

    @property
    def idempotency_registry(self) -> Any | None:
        """The configured ``WorkflowIdempotencyRegistry``, if any."""
        return self._idempotency_registry

    # ── Lease Refresh Loop ─────────────────────────────────────────────

    def _refresh_lease(self) -> None:
        """Refresh the current lock's lease.

        If refresh fails (non-fatal), logs a warning and continues.
        """
        if self._current_lock is None:
            return

        try:
            updated = self._lock_provider.refresh(self._current_lock)
            if updated is not None:
                self._current_lock = updated
                logger.debug(
                    "Lease refreshed for lock_id=%s, expires_at=%s",
                    updated.lock_id,
                    updated.expires_at,
                )
            else:
                logger.warning(
                    "Lease refresh returned None for lock_id=%s — "
                    "lock may have been lost",
                    self._current_lock.lock_id,
                )
        except Exception as e:
            logger.warning(
                "Lease refresh failed for lock_id=%s: %s",
                self._current_lock.lock_id,
                e,
            )

    def _lease_refresh_loop(
        self,
        fn: Callable[[], Any],
    ) -> Any:
        """Execute a function while periodically refreshing the lock lease.

        The function ``fn`` is executed. Every ``refresh_interval_s`` seconds,
        the lease is refreshed. If the function completes early, the refresh
        loop stops.
        """
        import threading

        result: Any = None
        exception: BaseException | None = None
        completed = threading.Event()

        def _run_with_refresh() -> None:
            nonlocal result, exception
            try:
                result = fn()
            except BaseException as e:
                exception = e
            finally:
                completed.set()

        # Start execution in a separate thread so we can refresh in parallel
        exec_thread = threading.Thread(target=_run_with_refresh, daemon=True)
        exec_thread.start()

        # Periodically refresh while the execution thread is alive
        while not completed.is_set():
            completed.wait(timeout=self._refresh_interval_s)
            if not completed.is_set():
                self._refresh_lease()

        exec_thread.join(timeout=5)

        if exception is not None:
            raise exception

        return result

    # ── Idempotency Check ───────────────────────────────────────────────

    def _check_idempotency(self, idempotency_key: str) -> bool:
        """Check if an idempotency key has already been completed.

        Returns ``True`` if execution should be skipped (key is completed),
        ``False`` if execution should proceed.
        """
        if self._idempotency_registry is None:
            return False

        existing = self._idempotency_registry.check(idempotency_key)
        if existing is not None and existing.status == "completed":
            logger.info(
                "Idempotency key %r already completed (run=%s). Skipping.",
                idempotency_key,
                existing.pipeline_run_id,
            )
            return True

        # If in_progress or failed, we don't skip — we let the caller decide
        return False

    # ── Lock Acquisition with Retry ─────────────────────────────────────

    def _acquire_with_retry(
        self,
        workflow_id: str,
        holder_id: str,
        lease_duration_s: int,
    ) -> LockAcquisition:
        """Acquire a lock with retry + exponential backoff.

        Raises ``LockAcquisitionError`` if all retries fail.
        """
        last_error: LockAcquisitionError | None = None

        for attempt in range(self._max_retries + 1):
            try:
                lock = self._lock_provider.acquire(
                    lock_id=workflow_id,
                    holder_id=holder_id,
                    lease_duration_s=lease_duration_s,
                )
            except Exception as e:
                logger.error(
                    "Lock provider error on attempt %d/%d for workflow_id=%s: %s",
                    attempt + 1,
                    self._max_retries + 1,
                    workflow_id,
                    e,
                )
                last_error = LockAcquisitionError(
                    lock_id=workflow_id,
                    message=f"Lock provider error on attempt {attempt + 1}: {e}",
                )
                continue

            if lock is not None:
                logger.debug(
                    "Lock acquired for workflow_id=%s, holder_id=%s (attempt %d)",
                    workflow_id,
                    holder_id,
                    attempt + 1,
                )
                return lock

            # Lock is held — we need to retry
            if attempt < self._max_retries:
                delay = self._retry_delay_s * (2 ** attempt)
                logger.info(
                    "Lock busy for workflow_id=%s (attempt %d/%d). "
                    "Retrying in %ds...",
                    workflow_id,
                    attempt + 1,
                    self._max_retries + 1,
                    delay,
                )
                time.sleep(delay)

        # All retries exhausted
        if last_error is not None:
            raise last_error

        raise LockAcquisitionError(
            lock_id=workflow_id,
            message=(
                f"Lock acquisition failed for workflow_id={workflow_id!r} "
                f"after {self._max_retries + 1} attempts. "
                f"Lock is held by another holder."
            ),
        )

    # ── Idempotency Recording ───────────────────────────────────────────

    def _record_idempotency(
        self,
        idempotency_key: str,
        holder_id: str,
        status: str,
    ) -> None:
        """Record an idempotency key outcome.

        If a record already exists (from a previous ``in_progress``
        recording), this method updates it. Otherwise, it creates a
        new record.

        For registries that support ``update_status``
        (``DBIdempotencyRegistry``), the update is database-driven.
        For in-memory registries, the record is overwritten.
        """
        if self._idempotency_registry is None:
            return

        try:
            # Check if already recorded (from in_progress)
            existing = self._idempotency_registry.check(idempotency_key)
            if existing is not None:
                # Update status
                if hasattr(self._idempotency_registry, "update_status"):
                    self._idempotency_registry.update_status(
                        key=idempotency_key,
                        new_status=status,
                        pipeline_run_id=holder_id,
                    )
                return

            # Record new
            self._idempotency_registry.record(
                key=idempotency_key,
                pipeline_run_id=holder_id,
                status=status,
            )
        except Exception as e:
            logger.error(
                "Failed to record idempotency key %r: %s",
                idempotency_key,
                e,
            )

    # ── Execute ─────────────────────────────────────────────────────────

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
        actual_lease_duration = lease_duration_s or self._lease_duration_s

        # Step 1: Idempotency check
        if idempotency_key is not None:
            if self._check_idempotency(idempotency_key):
                return None, None  # Skipped — no execution, no lock

        # Step 2: Lock acquisition
        lock = self._acquire_with_retry(
            workflow_id=workflow_id,
            holder_id=holder_id,
            lease_duration_s=actual_lease_duration,
        )
        self._current_lock = lock

        # Step 3: Record in-progress idempotency
        if idempotency_key is not None:
            self._record_idempotency(
                idempotency_key=idempotency_key,
                holder_id=holder_id,
                status="in_progress",
            )

        # Step 4: Execute with lease refresh
        try:
            result = self._lease_refresh_loop(fn)
        except BaseException:
            # Execution failed — release lock and re-raise
            self._release_lock(lock)
            self._current_lock = None
            raise

        # Step 5: Release lock
        self._release_lock(lock)
        self._current_lock = None

        # Step 6: Record completed idempotency
        if idempotency_key is not None:
            self._record_idempotency(
                idempotency_key=idempotency_key,
                holder_id=holder_id,
                status="completed",
            )

        return result, lock

    # ── Lock Release Helper ─────────────────────────────────────────────

    def _release_lock(self, lock: LockAcquisition) -> bool:
        """Release a lock with error handling.

        Logs warnings on failure but does not raise.
        """
        try:
            released = self._lock_provider.release(lock)
            if released:
                logger.debug("Lock released for lock_id=%s", lock.lock_id)
            else:
                logger.warning(
                    "Failed to release lock for lock_id=%s — "
                    "may be held by another holder",
                    lock.lock_id,
                )
            return released
        except Exception as e:
            logger.error(
                "Error releasing lock for lock_id=%s: %s",
                lock.lock_id,
                e,
            )
            return False

    # ── Context Manager ─────────────────────────────────────────────────

    def __enter__(self) -> "WorkflowExecutionGuard":
        """Context manager entry — returns self."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> bool | None:
        """Context manager exit — releases the current lock if held."""
        if self._current_lock is not None:
            self._release_lock(self._current_lock)
            self._current_lock = None
        return None