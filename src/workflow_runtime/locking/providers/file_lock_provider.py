"""File-based lock provider for single-host deployments.

This provider uses filesystem-based advisory locking to coordinate
workflow execution on a single host. Suitable as a fallback when the
database is unavailable.

Implementation Details
----------------------
- Lock files are stored in ``{lock_dir}/{lock_id}.lock``.
- ``acquire()`` atomically creates a lock file with ``O_CREAT | O_EXCL``.
  If the file exists, it checks for stale locks (expired lease). Stale
  locks are removed and acquisition is retried.
- ``release()`` removes the lock file if we are the holder.
- ``refresh()`` updates the metadata JSON in the lock file.
- Stale detection: if the lock file's ``expires_at`` is in the past,
  the lock is treated as stale and can be acquired.

Cross-Platform
--------------
- On POSIX: uses ``os.open`` with ``O_CREAT | O_EXCL`` for atomic creation.
- On Windows: same approach works because ``O_EXCL`` is supported on
  Windows by Python's ``os`` module.
"""

from __future__ import annotations

import json
import os
import socket
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from src.workflow_runtime.locking.models import LockAcquisition
from src.workflow_runtime.locking.lock_provider import LockProvider
from src.workflow_runtime.locking.exceptions import LockProviderError


class FileLockProvider(LockProvider):
    """File-based lock provider for single-host deployments.

    Parameters
    ----------
    lock_dir:
        Directory path where lock files will be stored.
    name:
        Provider name for logging and debugging.
    """

    def __init__(self, lock_dir: str, name: str = "file") -> None:
        super().__init__(name=name)
        self._lock_dir = Path(lock_dir)
        self._lock_dir.mkdir(parents=True, exist_ok=True)

    def _lock_path(self, lock_id: str) -> Path:
        """Return the filesystem path for a given lock_id."""
        return self._lock_dir / f"{lock_id}.lock"

    def _is_stale(self, lock_path: Path) -> bool:
        """Check if a lock file is stale by reading its expires_at.

        A lock is stale if:
        1. The file cannot be read (corrupt) — treat as stale
        2. The expires_at timestamp is in the past
        """
        try:
            with open(lock_path) as f:
                metadata = json.load(f)
            expires_at = datetime.fromisoformat(metadata["expires_at"])
            return expires_at < datetime.utcnow()
        except (FileNotFoundError, json.JSONDecodeError, KeyError, ValueError):
            return True  # Treat unreadable as stale

    def _read_metadata(self, lock_path: Path) -> dict | None:
        """Read metadata from a lock file. Returns None if unreadable."""
        try:
            with open(lock_path) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def acquire(
        self,
        lock_id: str,
        holder_id: str,
        lease_duration_s: int,
    ) -> Optional[LockAcquisition]:
        """Acquire a lock via atomic file creation.

        Returns ``None`` if the lock is held by another holder and not stale.
        """
        lock_path = self._lock_path(lock_id)
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=lease_duration_s)

        try:
            fd = os.open(
                lock_path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                0o644,
            )
        except FileExistsError:
            # Lock file exists — check if stale
            if self._is_stale(lock_path):
                # Remove stale lock and retry
                try:
                    lock_path.unlink()
                except FileNotFoundError:
                    pass  # Race: someone else removed it
                return self.acquire(lock_id, holder_id, lease_duration_s)
            return None  # Lock is held by someone else

        # Write lock metadata
        metadata = {
            "lock_id": lock_id,
            "holder_id": holder_id,
            "acquired_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "lease_duration_s": lease_duration_s,
            "hostname": socket.gethostname(),
            "pid": os.getpid(),
        }

        try:
            with os.fdopen(fd, "w") as f:
                json.dump(metadata, f, indent=2)
        except OSError as e:
            # Clean up the lock file on write failure
            lock_path.unlink(missing_ok=True)
            raise LockProviderError(
                self.name,
                original_exception=e,
                message=f"Failed to write lock file {lock_path}: {e}",
            )

        return LockAcquisition(
            lock_id=lock_id,
            holder_id=holder_id,
            acquired_at=now.isoformat(),
            expires_at=expires_at.isoformat(),
            lease_duration_s=lease_duration_s,
        )

    def release(self, lock: LockAcquisition) -> bool:
        """Release a lock by deleting its file.

        Returns ``True`` if released (or already released), ``False`` if
        the lock is held by another holder.
        """
        lock_path = self._lock_path(lock.lock_id)

        try:
            metadata = self._read_metadata(lock_path)
        except Exception:
            return True  # Idempotent — file doesn't exist

        if metadata is None:
            return True  # Already released

        if metadata.get("holder_id") != lock.holder_id:
            return False  # Lock held by someone else

        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass  # Already deleted (race)
        return True

    def refresh(self, lock: LockAcquisition) -> Optional[LockAcquisition]:
        """Refresh (extend) a lock's lease by updating the lock file.

        Returns an updated ``LockAcquisition`` if successful, ``None`` if
        the lock is no longer held by us.
        """
        lock_path = self._lock_path(lock.lock_id)
        now = datetime.utcnow()

        try:
            metadata = self._read_metadata(lock_path)
        except Exception:
            return None

        if metadata is None:
            return None  # Lock doesn't exist

        if metadata.get("holder_id") != lock.holder_id:
            return None  # Not our lock

        existing_expires_at = datetime.fromisoformat(lock.expires_at)
        new_expires_at = max(now, existing_expires_at) + timedelta(
            seconds=lock.lease_duration_s
        )

        # Update metadata
        metadata["expires_at"] = new_expires_at.isoformat()
        metadata["last_refreshed_at"] = now.isoformat()
        metadata["refresh_count"] = metadata.get("refresh_count", 0) + 1

        try:
            with open(lock_path, "w") as f:
                json.dump(metadata, f, indent=2)
        except OSError as e:
            raise LockProviderError(
                self.name,
                original_exception=e,
                message=f"Failed to refresh lock file {lock_path}: {e}",
            )

        return LockAcquisition(
            lock_id=lock.lock_id,
            holder_id=lock.holder_id,
            acquired_at=lock.acquired_at,
            expires_at=new_expires_at.isoformat(),
            lease_duration_s=lock.lease_duration_s,
        )
