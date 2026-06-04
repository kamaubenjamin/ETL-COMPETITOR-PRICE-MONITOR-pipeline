"""Abstract base class and concrete implementations for workflow idempotency registry.

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

import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional

from src.workflow_runtime.locking.models import IdempotencyRecord
from src.workflow_runtime.locking.exceptions import IdempotencyRejectionError


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
        ...

    @abstractmethod
    def record(
        self,
        key: str,
        pipeline_run_id: str,
        status: str,
    ) -> IdempotencyRecord:
        ...

    @abstractmethod
    def cleanup(self, ttl_days: int) -> int:
        ...


class MemoryIdempotencyRegistry(WorkflowIdempotencyRegistry):
    """In-memory idempotency registry for testing and development."""

    def __init__(self, name: str = "memory-idempotency") -> None:
        super().__init__(name=name)
        self._records: dict[str, IdempotencyRecord] = {}

    def check(self, key: str) -> IdempotencyRecord | None:
        return self._records.get(key)

    def record(self, key: str, pipeline_run_id: str, status: str) -> IdempotencyRecord:
        if key in self._records:
            existing = self._records[key]
            raise IdempotencyRejectionError(
                idempotency_key=key,
                existing_status=existing.status,
                existing_pipeline_run_id=existing.pipeline_run_id,
            )
        record = IdempotencyRecord(
            idempotency_key=key,
            pipeline_run_id=pipeline_run_id,
            status=status,
            created_at=datetime.utcnow().isoformat(),
        )
        self._records[key] = record
        return record

    def update_status(self, key: str, new_status: str, pipeline_run_id: str) -> None:
        """Update the status of an existing idempotency record."""
        if key in self._records:
            existing = self._records[key]
            self._records[key] = IdempotencyRecord(
                idempotency_key=key,
                pipeline_run_id=existing.pipeline_run_id,
                status=new_status,
                created_at=existing.created_at,
            )

    def cleanup(self, ttl_days: int) -> int:
        cutoff = datetime.utcnow() - timedelta(days=ttl_days)
        keys_to_delete = [
            k for k, r in self._records.items()
            if r.created_at < cutoff.isoformat()
        ]
        for k in keys_to_delete:
            del self._records[k]
        return len(keys_to_delete)


class DBIdempotencyRegistry(WorkflowIdempotencyRegistry):
    """Database-backed idempotency registry.

    Uses the ``workflow_idempotency`` table for atomic key insertion.
    """

    def __init__(
        self,
        db_connection: sqlite3.Connection,
        table_name: str = "workflow_idempotency",
        name: str = "db-idempotency",
    ) -> None:
        super().__init__(name=name)
        self._db = db_connection
        self._table = table_name

    def check(self, key: str) -> IdempotencyRecord | None:
        cursor = self._db.cursor()
        cursor.execute(
            f"SELECT * FROM {self._table} WHERE idempotency_key = ?",
            (key,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return IdempotencyRecord(
            idempotency_key=row["idempotency_key"],
            pipeline_run_id=row["pipeline_run_id"],
            status=row["status"],
            created_at=row["created_at"],
        )

    def record(self, key: str, pipeline_run_id: str, status: str) -> IdempotencyRecord:
        cursor = self._db.cursor()
        cursor.execute(
            f"SELECT * FROM {self._table} WHERE idempotency_key = ?",
            (key,),
        )
        existing = cursor.fetchone()
        if existing is not None:
            raise IdempotencyRejectionError(
                idempotency_key=key,
                existing_status=existing["status"],
                existing_pipeline_run_id=existing["pipeline_run_id"],
            )
        now = datetime.utcnow().isoformat()
        cursor.execute(
            f"""INSERT INTO {self._table}
                (idempotency_key, pipeline_run_id, status, created_at)
                VALUES (?, ?, ?, ?)""",
            (key, pipeline_run_id, status, now),
        )
        self._db.commit()
        return IdempotencyRecord(
            idempotency_key=key,
            pipeline_run_id=pipeline_run_id,
            status=status,
            created_at=now,
        )

    def cleanup(self, ttl_days: int) -> int:
        cursor = self._db.cursor()
        cursor.execute(
            f"""DELETE FROM {self._table}
                WHERE created_at < datetime('now', '-' || ? || ' days')""",
            (ttl_days,),
        )
        self._db.commit()
        return cursor.rowcount

    def update_status(self, key: str, new_status: str, pipeline_run_id: str) -> None:
        """Update the status of an existing idempotency record."""
        cursor = self._db.cursor()
        completed_at = (
            datetime.utcnow().isoformat() if new_status in ("completed", "failed") else None
        )
        cursor.execute(
            f"""UPDATE {self._table}
                SET status = ?, completed_at = ?
                WHERE idempotency_key = ? AND pipeline_run_id = ?""",
            (new_status, completed_at, key, pipeline_run_id),
        )
        self._db.commit()