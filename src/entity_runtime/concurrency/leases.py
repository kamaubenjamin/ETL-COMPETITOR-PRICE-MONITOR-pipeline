"""LeaseManager — execution lease management for crash recovery.

Leases provide crash recovery for entity write operations:
  1. Acquire lease before writing
  2. Refresh periodically during long writes
  3. Release after write completes
  4. If writer crashes, lease auto-expires and another writer can recover
"""

from __future__ import annotations

import socket
import sqlite3
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from src.entity_runtime.concurrency.config import EntityConcurrencyConfig
from src.entity_runtime.concurrency.errors import EntityLeaseError, EntityLeaseLostError


@dataclass(frozen=True, slots=True)
class LeaseAcquisition:
    """Result of a successful lease acquisition.

    Attributes:
        entity_version_key: The entity key the lease covers.
        holder_id: The unique identifier of the lease holder.
        acquired_at: ISO-8601 timestamp of acquisition.
        expires_at: ISO-8601 timestamp of expiry.
        lease_duration_s: The lease duration in seconds.
    """

    entity_version_key: str
    holder_id: str
    acquired_at: str
    expires_at: str
    lease_duration_s: int


class LeaseManager:
    """Concrete implementation of execution lease management.

    Manages time-bound leases that provide crash recovery for entity writes.
    Leases auto-expire after a configurable duration, allowing other workers
    to detect and recover from crashes.

    Uses the entity_leases table for durable lease storage.
    """

    def __init__(
        self,
        config: EntityConcurrencyConfig,
        db_path: str = "data/entity_version_store.db",
    ) -> None:
        self._config = config
        self._db_path = db_path
        self._local = threading.local()
        self._lock = threading.RLock()

        # Refresh loop tracking
        self._refresh_threads: dict[str, threading.Thread] = {}
        self._refresh_stop: dict[str, threading.Event] = {}
        self._hostname = socket.gethostname()

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(self._db_path, timeout=10)
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        return self._local.conn

    def close(self) -> None:
        if hasattr(self._local, "conn") and self._local.conn is not None:
            self._local.conn.close()
            self._local.conn = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def acquire(
        self,
        entity_version_key: str,
        holder_id: str,
        lease_duration_s: int = 120,
    ) -> LeaseAcquisition:
        """Acquire a lease for the given entity.

        If no active lease exists, acquires one. If a lease exists but is
        expired, acquires it (steals the expired lease). If a lease exists
        and is still valid, raises EntityLeaseError.

        Args:
            entity_version_key: The entity key to acquire the lease for.
            holder_id: Unique identifier for the lease holder.
            lease_duration_s: Lease TTL in seconds.

        Returns:
            LeaseAcquisition with details of the acquired lease.

        Raises:
            EntityLeaseError: If the lease is held by another active holder.
        """
        conn = self._get_connection()
        now = datetime.now(timezone.utc)
        now_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")

        max_retries = self._config.entity_lease_retry_max_attempts
        base_delay_ms = self._config.entity_lease_retry_base_delay_ms

        for attempt in range(max_retries):
            with self._lock:
                try:
                    # Check existing lease
                    cur = conn.execute(
                        "SELECT holder_id, expires_at FROM entity_leases "
                        "WHERE entity_version_key = ?",
                        (entity_version_key,),
                    )
                    row = cur.fetchone()

                    if row is None:
                        # No existing lease — acquire
                        expires_str = (
                            datetime.fromtimestamp(
                                now.timestamp() + lease_duration_s, tz=timezone.utc
                            ).strftime("%Y-%m-%dT%H:%M:%SZ")
                        )
                        conn.execute(
                            """INSERT INTO entity_leases
                               (entity_version_key, holder_id, acquired_at, expires_at,
                                lease_duration_s, last_refreshed_at, refresh_count,
                                hostname, pid)
                               VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)""",
                            (
                                entity_version_key,
                                holder_id,
                                now_str,
                                expires_str,
                                lease_duration_s,
                                now_str,
                                self._hostname,
                                threading.current_thread().ident or 0,
                            ),
                        )
                        conn.commit()
                        return LeaseAcquisition(
                            entity_version_key=entity_version_key,
                            holder_id=holder_id,
                            acquired_at=now_str,
                            expires_at=expires_str,
                            lease_duration_s=lease_duration_s,
                        )

                    # Check if existing lease is expired
                    expires_row = row["expires_at"]
                    if expires_row < now_str:
                        # Lease expired — steal it
                        expires_str = (
                            datetime.fromtimestamp(
                                now.timestamp() + lease_duration_s, tz=timezone.utc
                            ).strftime("%Y-%m-%dT%H:%M:%SZ")
                        )
                        conn.execute(
                            """UPDATE entity_leases SET
                               holder_id = ?, acquired_at = ?, expires_at = ?,
                               lease_duration_s = ?, last_refreshed_at = ?,
                               refresh_count = refresh_count + 1, hostname = ?, pid = ?
                               WHERE entity_version_key = ?""",
                            (
                                holder_id,
                                now_str,
                                expires_str,
                                lease_duration_s,
                                now_str,
                                self._hostname,
                                threading.current_thread().ident or 0,
                                entity_version_key,
                            ),
                        )
                        conn.commit()
                        return LeaseAcquisition(
                            entity_version_key=entity_version_key,
                            holder_id=holder_id,
                            acquired_at=now_str,
                            expires_at=expires_str,
                            lease_duration_s=lease_duration_s,
                        )

                    # Lease held by another
                    raise EntityLeaseError(
                        entity_version_key=entity_version_key,
                        holder_id=row["holder_id"],
                        message=(
                            f"Lease held by {row['holder_id']} on {entity_version_key}, "
                            f"expires at {expires_row}"
                        ),
                    )

                except sqlite3.IntegrityError:
                    # Race condition on insert — retry
                    if attempt < max_retries - 1:
                        delay = (base_delay_ms * (2 ** attempt)) / 1000.0
                        time.sleep(delay)
                        continue
                    raise EntityLeaseError(
                        entity_version_key=entity_version_key,
                        message="Failed to acquire lease after max retries",
                    )

        raise EntityLeaseError(
            entity_version_key=entity_version_key,
            message="Failed to acquire lease after max retries",
        )

    def refresh(
        self,
        entity_version_key: str,
        holder_id: str,
        lease_duration_s: int = 120,
    ) -> bool:
        """Refresh an active lease, extending its expiry time.

        Args:
            entity_version_key: The entity key to refresh the lease for.
            holder_id: The current lease holder identifier.
            lease_duration_s: New lease TTL in seconds.

        Returns:
            True if the lease was refreshed, False if the lease is expired
            or held by a different holder.
        """
        conn = self._get_connection()
        now = datetime.now(timezone.utc)
        now_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        expires_str = (
            datetime.fromtimestamp(
                now.timestamp() + lease_duration_s, tz=timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%SZ")
        )

        try:
            cur = conn.execute(
                """UPDATE entity_leases SET
                   expires_at = ?, last_refreshed_at = ?, refresh_count = refresh_count + 1
                   WHERE entity_version_key = ? AND holder_id = ? AND expires_at > ?""",
                (expires_str, now_str, entity_version_key, holder_id, now_str),
            )
            conn.commit()
            return cur.rowcount > 0
        except sqlite3.OperationalError:
            return False

    def release(self, entity_version_key: str, holder_id: str) -> bool:
        """Explicitly release a lease.

        Idempotent — releasing a lease that doesn't exist or is held by
        another holder returns False without error.

        Args:
            entity_version_key: The entity key to release the lease for.
            holder_id: The current lease holder identifier.

        Returns:
            True if the lease was released, False if it wasn't held by holder_id.
        """
        conn = self._get_connection()
        try:
            cur = conn.execute(
                "DELETE FROM entity_leases "
                "WHERE entity_version_key = ? AND holder_id = ?",
                (entity_version_key, holder_id),
            )
            conn.commit()
            released = cur.rowcount > 0
        except sqlite3.OperationalError:
            return False

        # Stop refresh loop if running
        self.stop_refresh_loop(entity_version_key)

        return released

    def is_expired(self, entity_version_key: str) -> bool:
        """Check if the current lease for an entity is expired.

        Args:
            entity_version_key: The entity key to check.

        Returns:
            True if the lease is expired or doesn't exist, False if active.
        """
        conn = self._get_connection()
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            cur = conn.execute(
                "SELECT expires_at FROM entity_leases WHERE entity_version_key = ?",
                (entity_version_key,),
            )
            row = cur.fetchone()
            if row is None:
                return True  # No lease exists
            return row["expires_at"] < now_str
        except sqlite3.OperationalError:
            return True  # Assume expired if DB error

    def recover(
        self,
        entity_version_key: str,
        holder_id: str,
        lease_duration_s: int = 120,
    ) -> LeaseAcquisition:
        """Recover an entity by acquiring its expired lease.

        Called when a crash is detected (lease expired but not released).

        Args:
            entity_version_key: The entity key to recover.
            holder_id: The new lease holder identifier.
            lease_duration_s: New lease TTL in seconds.

        Returns:
            LeaseAcquisition with details of the recovered lease.

        Raises:
            EntityLeaseError: If the lease is still active (not expired).
        """
        if not self.is_expired(entity_version_key):
            raise EntityLeaseError(
                entity_version_key=entity_version_key,
                message="Cannot recover: lease is still active",
            )

        return self.acquire(
            entity_version_key=entity_version_key,
            holder_id=holder_id,
            lease_duration_s=lease_duration_s,
        )

    def get_holder(self, entity_version_key: str) -> Optional[str]:
        """Get the current lease holder for an entity.

        Args:
            entity_version_key: The entity key to query.

        Returns:
            The holder ID if a lease exists, None otherwise.
        """
        conn = self._get_connection()
        try:
            cur = conn.execute(
                "SELECT holder_id FROM entity_leases WHERE entity_version_key = ?",
                (entity_version_key,),
            )
            row = cur.fetchone()
            return row["holder_id"] if row is not None else None
        except sqlite3.OperationalError:
            return None

    # ------------------------------------------------------------------
    # Refresh loop management
    # ------------------------------------------------------------------

    def start_refresh_loop(
        self,
        entity_version_key: str,
        holder_id: str,
        interval_s: int = 20,
        lease_duration_s: int = 120,
    ) -> None:
        """Start a daemon thread that periodically refreshes the lease.

        Args:
            entity_version_key: The entity key to refresh.
            holder_id: The lease holder identifier.
            interval_s: Interval between refreshes (seconds).
            lease_duration_s: Lease TTL in seconds.
        """
        if entity_version_key in self._refresh_threads:
            return  # Already running

        stop_event = threading.Event()
        self._refresh_stop[entity_version_key] = stop_event

        def refresh_loop() -> None:
            while not stop_event.is_set():
                if stop_event.wait(timeout=interval_s):
                    break
                if not self.refresh(
                    entity_version_key=entity_version_key,
                    holder_id=holder_id,
                    lease_duration_s=lease_duration_s,
                ):
                    # Lease expired or lost — stop refreshing
                    break

        thread = threading.Thread(
            target=refresh_loop,
            name=f"lease-refresh-{entity_version_key[:16]}",
            daemon=True,
        )
        thread.start()
        self._refresh_threads[entity_version_key] = thread

    def stop_refresh_loop(self, entity_version_key: str) -> None:
        """Stop the refresh loop for an entity.

        Args:
            entity_version_key: The entity key to stop refreshing.
        """
        if entity_version_key in self._refresh_stop:
            self._refresh_stop[entity_version_key].set()
            del self._refresh_stop[entity_version_key]

        if entity_version_key in self._refresh_threads:
            del self._refresh_threads[entity_version_key]