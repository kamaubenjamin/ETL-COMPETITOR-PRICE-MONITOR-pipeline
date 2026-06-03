"""Abstract base class for the workflow idempotency registry.

The ``WorkflowIdempotencyRegistry`` prevents duplicate execution of
already-completed workflow runs by maintaining a registry of idempotency
keys. Each scheduled workflow invocation generates a deterministic key
(e.g. ``"{workflow_id}-scheduled-{schedule_slot}"``), and the registry
ensures that key is only executed once.

Contract
========

All concrete implementations must implement the three abstract methods:

- ``check(key: str) -> Optional[IdempotencyRecord]``
  Returns the existing record for a key, or ``None`` if the key is new.

- ``record(key: str, pipeline_run_id: str, status: str) -> IdempotencyRecord``
  Atomically insert a new idempotency key. Raises
  ``IdempotencyRejectionError`` if the key already exists.

- ``cleanup(ttl_days: int) -> int``
  Remove keys older than ``ttl_days``. Returns the number of removed keys.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.workflow_runtime.locking.models import IdempotencyRecord


class WorkflowIdempotencyRegistry(ABC):
    """Abstract base class for idempotency key registries.

    Parameters
    ----------
    name:
        Human-readable registry name for logging and debugging.
    """

    def __init__(self, name: str = "unknown") -> None:
        self._name = name

    @property
    def name(self) -> str:
        """Human-readable registry name."""
        return self._name

    @abstractmethod
    def check(self, key: str) -> IdempotencyRecord | None:
        """Check if an idempotency key exists in the registry.

        Parameters
        ----------
        key:
            The idempotency key to check.

        Returns
        -------
        IdempotencyRecord | None
            The existing record, or ``None`` if the key is not found.
        """
        ...

    @abstractmethod
    def record(
        self,
        key: str,
        pipeline_run_id: str,
        status: str,
    ) -> IdempotencyRecord:
        """Atomically record a new idempotency key.

        Parameters
        ----------
        key:
            The idempotency key to record.
        pipeline_run_id:
            The ``pipeline_run_id`` of the run claiming this key.
        status:
            The status of the run. Must be one of ``"completed"``,
            ``"failed"``, or ``"in_progress"``.

        Returns
        -------
        IdempotencyRecord
            The created record.

        Raises
        ------
        IdempotencyRejectionError
            If the key already exists in the registry.
        """
        ...

    @abstractmethod
    def cleanup(self, ttl_days: int) -> int:
        """Remove idempotency keys older than ``ttl_days``.

        Parameters
        ----------
        ttl_days:
            Keys older than this many days will be removed.

        Returns
        -------
        int
            The number of keys removed.
        """
        ...