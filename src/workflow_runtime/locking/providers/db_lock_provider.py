"""Database-backed lock provider with execution leases.

This is the **primary** lock provider for production deployments. It uses
the ``workflow_locks`` table with UPSERT semantics to atomically acquire
and release locks across processes and hosts.

Implementation Details
----------------------
- ``acquire()``: Uses ``INSERT ... ON CONFLICT(lock_id) DO UPDATE ... WHERE
  expires_at < NOW()``. If the lock exists and is NOT expired, the UPSERT
  condition is false and nothing changes. If the lock IS expired, the
  UPSERT replaces the holder.
- ``release()``: ``DELETE FROM workflow_locks WHERE lock_id=? AND holder_id=?``
  Verifies holder identity before releasing.
- ``refresh()``: ``UPDATE workflow_locks SET expires_at = NOW() + ? WHERE
  lock_id=? AND holder_id=?``
- ``cleanup_stale()``: ``DELETE FROM workflow_locks WHERE expires_at < NOW()``
  Removes all expired locks.
"""

from __future__ import annotations

import os
import socket
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

from src.workflow_runtime.locking.models import LockAcquisition
from src.workflow_runtime.locking.lock_provider import LockProvider
from src.workflow_runtime.locking.exceptions import LockProviderError


class DBLockProvider(LockProvider):
    """Database-backed lock provider with execution leases.

    Parameters
    ----------
    db_connection:
        A SQLite database connection with ``row_factory = sqlite3.Row``.
    table_name:
        Name of the workflow_locks table (default: ``"workflow_locks"``).
    name:
        Provider name for logging and debugging.
    """

    def __init__(
        self,
        db_connection: sqlite3.Connection,
        table_name: str = "workflow_locks",
        name: str = "database",
    ) -> None:
        super().__init__(name=name)
        self._db = db_connection
        self._table = table_name

    def acquire(
        self,
        lock_id: str,
        holder_id: str,
        lease_duration_s: int,
    ) -> Optional[LockAcquisition]:
        """Acquire a lock using UPSERT semantics.

        If the lock exists and is NOT expired, the UPSERT conflict clause
        ``WHERE expires_at < datetime('now')`` prevents overwriting.
        If expired, the lock is replaced with the new holder.
        """
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=lease_duration_s)

        try:
            cursor = self._db.cursor()

            cursor.execute(f"""
                INSERT INTO {self._table}
                    (lock_id, holder_id, acquired_at, expires_at,
                     lease_duration_s, hostname, pid, refresh_count,
                     last_refreshed_at)
                VALUES (?, ?, datetime('now'), datetime('now', '+' || ? || ' seconds'),
                        ?, ?, ?, 0, datetime('now'))
                ON CONFLICT(lock_id) DO UPDATE SET
                    holder_id = EXCLUDED.holder_id,
                    acquired_at = EXCLUDED.acquired_at,
                    expires_at = EXCLUDED.expires_at,
                    hostname = EXCLUDED.hostname,
                    pid = EXCLUDED.pid,
                    refresh_count = 0,
                    last_refreshed_at = datetime('now')
                WHERE {self._table}.expires_at < datetime('now')
            """, (
                lock_id,
                holder_id,
                lease_duration_s,
                lease_duration_s,
                socket.gethostname(),
                os.getpid(),
            ))

            self._db.commit()

            # Check if we actually got the lock
            cursor.execute(
                f"SELECT holder_id FROM {self._table} WHERE lock_id = ?",
                (lock_id,),
            )
            row = cursor.fetchone()

            if row is None or row["holder_id"] != holder_id:
                return None  # Someone else holds the lock

            return LockAcquisition(
                lock_id=lock_id,
                holder_id=holder_id,
                acquired_at=now.isoformat(),
                expires_at=expires_at.isoformat(),
                lease_duration_s=lease_duration_s,
            )

        except (sqlite3.OperationalError, sqlite3.ProgrammingError) as e:
            raise LockProviderError(
                self.name,
                original_exception=e,
                message=f"DB error acquiring lock {lock_id!r}: {e}",
            )

    def release(self, lock: LockAcquisition) -> bool:
        """Release a lock by deleting its row.

        Verifies holder identity before releasing.
        """
        try:
            cursor = self._db.cursor()
            cursor.execute(
                f"DELETE FROM {self._table} WHERE lock_id = ? AND holder_id = ?",
                (lock.lock_id, lock.holder_id),
            )
            self._db.commit()
            return cursor.rowcount > 0

        except sqlite3.OperationalError as e:
            raise LockProviderError(
                self.name,
                original_exception=e,
                message=f"DB error releasing lock {lock.lock_id!r}: {e}",
            )

    def refresh(self, lock: LockAcquisition) -> Optional[LockAcquisition]:
        """Refresh (extend) a lock's lease.

        Returns an updated ``LockAcquisition`` if successful, ``None`` if
        the lock is no longer held by us.
        """
        now = datetime.utcnow()
        new_expires_at = now + timedelta(seconds=lock.lease_duration_s)

        try:
            cursor = self._db.cursor()
            cursor.execute(f"""
                UPDATE {self._table}
                SET expires_at = datetime('now', '+' || ? || ' seconds'),
                    refresh_count = refresh_count + 1,
                    last_refreshed_at = datetime('now')
                WHERE lock_id = ? AND holder_id = ?
            """, (lock.lease_duration_s, lock.lock_id, lock.holder_id))
            self._db.commit()

            if cursor.rowcount == 0:
                return None  # Lock lost or expired

            return LockAcquisition(
                lock_id=lock.lock_id,
                holder_id=lock.holder_id,
                acquired_at=lock.acquired_at,
                expires_at=new_expires_at.isoformat(),
                lease_duration_s=lock.lease_duration_s,
            )

        except sqlite3.OperationalError as e:
            raise LockProviderError(
                self.name,
                original_exception=e,
                message=f"DB error refreshing lock {lock.lock_id!r}: {e}",
            )

    def cleanup_stale(self) -> int:
        """Remove all expired locks.

        Returns the number of rows deleted.
        """
        try:
            cursor = self._db.cursor()
            cursor.execute(
                f"DELETE FROM {self._table} WHERE expires_at < datetime('now')",
            )
            self._db.commit()
            return cursor.rowcount

        except sqlite3.OperationalError as e:
            raise LockProviderError(
                self.name,
                original_exception=e,
                message=f"DB error cleaning up stale locks: {e}",
            )