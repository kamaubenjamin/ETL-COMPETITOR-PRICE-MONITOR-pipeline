"""In-memory lock provider for testing and development.

This provider stores locks in a dictionary with thread-safe access via
``threading.Lock``. **Not suitable for production** — locks are lost
on process restart and there is no cross-process coordination.

Implementation Details
----------------------
- Locks are stored as ``{lock_id: LockAcquisition}`` in a dict.
- ``acquire()`` checks for existing non-expired locks. If free, creates
  a new ``LockAcquisition`` with expiry = now + lease_duration_s.
- ``release()`` removes the lock entry if we hold it.
- ``refresh()`` extends the expiry time.
- Stale (expired) locks are treated as free — a new acquire overwrites them.
"""

from __future__ import annotations

import threading
from datetime import datetime, timedelta
from typing import Optional

from src.workflow_runtime.locking.models import LockAcquisition
from src.workflow_runtime.locking.lock_provider import LockProvider


class MemoryLockProvider(LockProvider):
    """In-memory lock provider for testing and development.

    Parameters
    ----------
    name:
        Provider name for logging and debugging.
    """

    def __init__(self, name: str = "memory") -> None:
        super().__init__(name=name)
        self._locks: dict[str, LockAcquisition] = {}
        self._lock = threading.Lock()

    def acquire(
        self,
        lock_id: str,
        holder_id: str,
        lease_duration_s: int,
    ) -> Optional[LockAcquisition]:
        """Acquire a lock if free or expired.

        Thread-safe via ``threading.Lock``.
        """
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=lease_duration_s)

        with self._lock:
            existing = self._locks.get(lock_id)

            # Check if lock is held by someone else and not expired
            if existing is not None:
                existing_expiry = datetime.fromisoformat(existing.expires_at)
                if existing_expiry > now:
                    return None  # Lock still held

            # Acquire the lock
            acquisition = LockAcquisition(
                lock_id=lock_id,
                holder_id=holder_id,
                acquired_at=now.isoformat(),
                expires_at=expires_at.isoformat(),
                lease_duration_s=lease_duration_s,
            )
            self._locks[lock_id] = acquisition
            return acquisition

    def release(self, lock: LockAcquisition) -> bool:
        """Release a lock we hold.

        Returns ``True`` if the lock was released, ``False`` if it was
        not held by the caller or already released.
        """
        with self._lock:
            existing = self._locks.get(lock.lock_id)
            if existing is None:
                return True  # Idempotent — already released
            if existing.holder_id != lock.holder_id:
                return False  # Not our lock
            del self._locks[lock.lock_id]
            return True

    def refresh(self, lock: LockAcquisition) -> Optional[LockAcquisition]:
        """Refresh (extend) a lock's lease.

        Returns an updated ``LockAcquisition`` if successful, ``None`` if
        the lock is no longer held by us.
        """
        now = datetime.utcnow()
        new_expires_at = now + timedelta(seconds=lock.lease_duration_s)

        with self._lock:
            existing = self._locks.get(lock.lock_id)
            if existing is None or existing.holder_id != lock.holder_id:
                return None

            updated = LockAcquisition(
                lock_id=lock.lock_id,
                holder_id=lock.holder_id,
                acquired_at=lock.acquired_at,
                expires_at=new_expires_at.isoformat(),
                lease_duration_s=lock.lease_duration_s,
            )
            self._locks[lock.lock_id] = updated
            return updated

    def clear(self) -> None:
        """Clear all locks. Useful for test cleanup."""
        with self._lock:
            self._locks.clear()