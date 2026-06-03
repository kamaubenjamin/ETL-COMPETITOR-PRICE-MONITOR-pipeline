"""Immutable data contracts for lock acquisition state and idempotency records.

These dataclasses define the core data structures exchanged between locking
components. They are intentionally frozen (immutable) and use ``__slots__``
for memory efficiency.

Contracts
---------
- ``LockAcquisition`` — represents a successfully acquired execution lock.
  Contains the lock identity, holder identity, timestamps, and lease
  configuration.

- ``IdempotencyRecord`` — represents a claimed idempotency key. Used by
  the ``WorkflowIdempotencyRegistry`` to prevent duplicate execution of
  already-completed runs.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LockAcquisition:
    """Immutable record of a successfully acquired execution lock.

    Parameters
    ----------
    lock_id:
        The identifier of the locked resource (typically the ``workflow_id``).
    holder_id:
        Identifier of the lock holder, formatted as
        ``"{hostname}-{pid}-{pipeline_run_id}"``.
    acquired_at:
        ISO-8601 timestamp when the lock was acquired.
    expires_at:
        ISO-8601 timestamp when the lock lease expires. After this time,
        another holder may acquire the lock.
    lease_duration_s:
        The duration in seconds for which this lease is valid. Used by
        the lock provider to compute ``expires_at``.
    """

    lock_id: str
    holder_id: str
    acquired_at: str
    expires_at: str
    lease_duration_s: int


@dataclass(frozen=True, slots=True)
class IdempotencyRecord:
    """Immutable record of a claimed idempotency key.

    Parameters
    ----------
    idempotency_key:
        Deterministic key identifying a unique workflow invocation, formatted as
        ``"{workflow_id}-{scope}-{schedule_slot}"``.
    pipeline_run_id:
        The ``pipeline_run_id`` of the workflow run that claimed this key.
    status:
        Current status of the run that claimed this key. One of ``"completed"``,
        ``"failed"``, or ``"in_progress"``.
    created_at:
        ISO-8601 timestamp when the idempotency key was created.
    """

    idempotency_key: str
    pipeline_run_id: str
    status: str
    created_at: str