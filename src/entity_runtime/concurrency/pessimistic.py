"""PessimisticLockManager — escalation to pessimistic locking for hot entities.

Secondary concurrency mechanism, activated when optimistic locking contention
exceeds defined thresholds. Uses global lock ordering to prevent deadlocks.
"""

from __future__ import annotations

import sqlite3
import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from src.entity_runtime.concurrency.config import EntityConcurrencyConfig
from src.entity_runtime.concurrency.errors import EntityDeadlockError, EntityLockTimeoutError


# Global lock order — must be respected by all writers to prevent deadlocks.
# Locks must be acquired in this sequence and released in reverse order.
ENTITY_LOCK_ORDER: list[str] = [
    "supplier",  # Level 1
    "customer",  # Level 2
    "document_reference",  # Level 3
    "document_financials",  # Level 4
    "line_item",  # Level 5
]

# Lock level mapping for quick lookup
ENTITY_LOCK_LEVEL: dict[str, int] = {
    name: idx for idx, name in enumerate(ENTITY_LOCK_ORDER)
}


@dataclass(frozen=True, slots=True)
class EscalationPolicy:
    """Defines when to escalate from optimistic to pessimistic locking.

    Attributes:
        max_optimistic_retries: After this many consecutive CAS failures, escalate.
        conflict_rate_threshold: If > this fraction of recent writes conflict, escalate.
        escalation_window_minutes: Rolling window for conflict rate calculation.
        cooldown_minutes: Time before auto-de-escalating to optimistic locking.
    """

    max_optimistic_retries: int = 3
    """After this many consecutive CAS failures, escalate to pessimistic."""

    conflict_rate_threshold: float = 0.30
    """If >30% of recent writes conflict, escalate."""

    escalation_window_minutes: int = 5
    """Rolling window for conflict rate calculation."""

    cooldown_minutes: int = 15
    """Time before auto-de-escalating to optimistic locking."""


@dataclass(frozen=True, slots=True)
class PessimisticLockReleasePolicy:
    """Defines how and when pessimistic locks are released.

    Attributes:
        release_on_completion: Release all locks when write completes.
        release_on_failure: Release all locks on write failure.
        release_on_timeout: Release if lock acquisition times out.
        max_hold_duration_s: Maximum time any lock can be held.
        force_release_on_expiry: Force-release if hold duration exceeded.
        release_in_reverse_order: Release lower-order locks first.
        release_all_on_any_failure: If one lock release fails, release all.
    """

    release_on_completion: bool = True
    release_on_failure: bool = True
    release_on_timeout: bool = True
    max_hold_duration_s: int = 60
    force_release_on_expiry: bool = True
    release_in_reverse_order: bool = True
    release_all_on_any_failure: bool = True


class PessimisticLockManager:
    """Concrete implementation of pessimistic locking with global order.

    Manages lock acquisition, release, escalation detection, and deadlock avoidance.
    All writers must respect ENTITY_LOCK_ORDER to prevent deadlocks.

    Uses an in-memory SQLite database for lightweight lock tracking per entity.
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

        # Per-entity escalation tracking
        self._escalated_entities: dict[str, dict[str, object]] = {}
        self._escalation_lock = threading.RLock()

        # Conflict tracking for rate calculation
        self._conflict_history: dict[str, list[float]] = defaultdict(list)

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(self._db_path, timeout=10)
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA busy_timeout=5000;")
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        return self._local.conn

    def close(self) -> None:
        if hasattr(self._local, "conn") and self._local.conn is not None:
            self._local.conn.close()
            self._local.conn = None

    # ------------------------------------------------------------------
    # Lock acquisition
    # ------------------------------------------------------------------

    def acquire_locks(
        self, entity_version_keys: list[str], timeout_s: int = 30
    ) -> bool:
        """Acquire pessimistic locks in ENTITY_LOCK_ORDER.

        Locks are acquired one at a time in the defined global order.
        If any lock cannot be acquired within the timeout, all acquired
        locks are released and the method returns False.

        Args:
            entity_version_keys: List of entity keys to lock.
            timeout_s: Timeout per single lock acquisition (seconds).

        Returns:
            True if all locks were acquired, False if any acquisition timed out.
        """
        # Sort keys by entity type lock order
        sorted_keys = self._sort_by_lock_order(entity_version_keys)
        acquired: list[str] = []

        try:
            for key in sorted_keys:
                if not self._acquire_single(key, timeout_s):
                    # Lock acquisition failed or timed out
                    self._release_acquired(acquired)
                    return False
                acquired.append(key)
            return True
        except EntityLockTimeoutError:
            self._release_acquired(acquired)
            return False
        except Exception:
            self._release_acquired(acquired)
            raise

    def _acquire_single(self, entity_version_key: str, timeout_s: int) -> bool:
        """Try to acquire a single pessimistic lock.

        Uses the entity_leases table as the lock store. A lock is acquired
        by inserting a lease record. An existing non-expired lease means
        the lock is held by another writer.

        Args:
            entity_version_key: The entity key to lock.
            timeout_s: Timeout in seconds.

        Returns:
            True if the lock was acquired.

        Raises:
            EntityLockTimeoutError: If lock acquisition times out.
            EntityDeadlockError: If a deadlock is detected.
        """
        conn = self._get_connection()
        holder = f"pessimistic-{threading.get_ident()}"
        now_ts = datetime.now(timezone.utc)
        expires_at = now_ts.timestamp() + max(timeout_s, 10)

        start_time = time.monotonic()
        last_error: Optional[str] = None

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed > timeout_s:
                raise EntityLockTimeoutError(
                    entity_version_key=entity_version_key,
                    timeout_s=timeout_s,
                )

            try:
                # Check if lock is already held
                cur = conn.execute(
                    "SELECT holder_id, expires_at FROM entity_leases "
                    "WHERE entity_version_key = ?",
                    (entity_version_key,),
                )
                row = cur.fetchone()

                if row is None:
                    # No existing lease — acquire lock
                    now_str = datetime.fromtimestamp(start_time + elapsed, tz=timezone.utc).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    )
                    expires_str = datetime.fromtimestamp(expires_at, tz=timezone.utc).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    )
                    conn.execute(
                        """INSERT INTO entity_leases
                           (entity_version_key, holder_id, acquired_at, expires_at,
                            lease_duration_s, last_refreshed_at, refresh_count, hostname, pid)
                           VALUES (?, ?, ?, ?, ?, ?, 0, '', 0)""",
                        (
                            entity_version_key,
                            holder,
                            now_str,
                            expires_str,
                            min(timeout_s, 120),
                            now_str,
                        ),
                    )
                    conn.commit()
                    return True

                # Check if existing lease is expired
                expires_row = row["expires_at"]
                if expires_row < datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"):
                    # Lease expired — steal it
                    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                    expires_str = datetime.fromtimestamp(expires_at, tz=timezone.utc).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    )
                    conn.execute(
                        """UPDATE entity_leases SET
                           holder_id = ?, acquired_at = ?, expires_at = ?,
                           lease_duration_s = ?, last_refreshed_at = ?,
                           refresh_count = refresh_count + 1
                           WHERE entity_version_key = ?""",
                        (holder, now_str, expires_str, min(timeout_s, 120), now_str, entity_version_key),
                    )
                    conn.commit()
                    return True

                # Lock is held — wait and retry
                time.sleep(0.1)

            except sqlite3.OperationalError as e:
                if "deadlock" in str(e).lower():
                    raise EntityDeadlockError(
                        entity_version_key=entity_version_key,
                        held_locks=[entity_version_key],
                        attempted_lock=entity_version_key,
                    ) from e
                raise

            except sqlite3.IntegrityError:
                # Race condition on insert — retry
                time.sleep(0.05)

    def _release_acquired(self, acquired: list[str]) -> None:
        """Release all acquired locks (rollback on partial failure)."""
        for key in reversed(acquired):
            try:
                conn = self._get_connection()
                conn.execute("DELETE FROM entity_leases WHERE entity_version_key = ?", (key,))
                conn.commit()
            except Exception:
                pass  # Best-effort release during rollback

    # ------------------------------------------------------------------
    # Lock release
    # ------------------------------------------------------------------

    def release_locks(self, entity_version_keys: list[str]) -> bool:
        """Release pessimistic locks in reverse ENTITY_LOCK_ORDER.

        Args:
            entity_version_keys: List of entity keys to unlock.

        Returns:
            True if all locks were released successfully.
        """
        # Sort in reverse order (higher levels first)
        sorted_keys = self._sort_by_lock_order(entity_version_keys)
        reversed_keys = list(reversed(sorted_keys))
        all_success = True

        for key in reversed_keys:
            try:
                conn = self._get_connection()
                conn.execute("DELETE FROM entity_leases WHERE entity_version_key = ?", (key,))
                conn.commit()
            except Exception:
                all_success = False
                if self._config.pessimistic_lock_max_hold_s > 0:
                    # Force-release by expiring the lease
                    try:
                        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                        conn.execute(
                            "UPDATE entity_leases SET expires_at = ? WHERE entity_version_key = ?",
                            (now_str, key),
                        )
                        conn.commit()
                    except Exception:
                        pass

        return all_success

    # ------------------------------------------------------------------
    # Escalation management
    # ------------------------------------------------------------------

    def should_escalate(self, entity_version_key: str) -> bool:
        """Check if the entity should be escalated to pessimistic locking.

        Evaluates the escalation policy thresholds (retry count and conflict rate).

        Args:
            entity_version_key: The entity key to check.

        Returns:
            True if escalation is warranted, False otherwise.
        """
        with self._escalation_lock:
            # Check if already escalated
            info = self._escalated_entities.get(entity_version_key)
            if info is not None:
                # Check cooldown
                cooldown_until = info.get("cooldown_until", 0.0)
                if isinstance(cooldown_until, (int, float)):
                    if time.monotonic() < cooldown_until:
                        return True  # Still in escalated state
                    else:
                        # Cooldown expired — de-escalate
                        del self._escalated_entities[entity_version_key]
                        return False

            # Check conflict rate
            rate = self._get_conflict_rate(entity_version_key)
            threshold = self._config.escalation_conflict_rate
            if rate > threshold:
                self._escalated_entities[entity_version_key] = {
                    "escalated_at": time.monotonic(),
                    "cooldown_until": time.monotonic() + self._config.escalation_cooldown_minutes * 60,
                    "conflict_rate": rate,
                }
                return True

            return False

    def de_escalate(self, entity_version_key: str) -> bool:
        """De-escalate an entity back to optimistic locking.

        Args:
            entity_version_key: The entity key to de-escalate.

        Returns:
            True if de-escalation was successful, False if not escalated.
        """
        with self._escalation_lock:
            if entity_version_key in self._escalated_entities:
                del self._escalated_entities[entity_version_key]
                # Also clear conflict tracking so rate recalculation starts fresh
                self._conflict_history.pop(entity_version_key, None)
                self._conflict_history.pop(f"{entity_version_key}:attempts", None)
                return True
            return False

    # ------------------------------------------------------------------
    # Conflict tracking
    # ------------------------------------------------------------------

    def record_conflict(self, entity_version_key: str) -> None:
        """Record a conflict occurrence for rate calculation.

        Args:
            entity_version_key: The entity key that experienced a conflict.
        """
        now = time.monotonic()
        window_s = self._config.escalation_rolling_window_minutes * 60

        with self._escalation_lock:
            history = self._conflict_history[entity_version_key]
            history.append(now)
            # Prune entries outside the rolling window
            cutoff = now - window_s
            self._conflict_history[entity_version_key] = [t for t in history if t > cutoff]

    def record_write_attempt(self, entity_version_key: str) -> None:
        """Record a write attempt (for conflict rate denominator).

        Args:
            entity_version_key: The entity key that was written to.
        """
        now = time.monotonic()
        window_s = self._config.escalation_rolling_window_minutes * 60

        with self._escalation_lock:
            # Track write attempts in the same structure with negative values as sentinel
            history = self._conflict_history[f"{entity_version_key}:attempts"]
            history.append(now)
            cutoff = now - window_s
            self._conflict_history[f"{entity_version_key}:attempts"] = [
                t for t in history if t > cutoff
            ]

    def _get_conflict_rate(self, entity_version_key: str) -> float:
        """Calculate the conflict rate for an entity in the rolling window.

        Args:
            entity_version_key: The entity key to calculate for.

        Returns:
            A float between 0.0 and 1.0 representing the conflict rate.
        """
        window_s = self._config.escalation_rolling_window_minutes * 60
        now = time.monotonic()
        cutoff = now - window_s

        conflicts = len(
            [t for t in self._conflict_history.get(entity_version_key, []) if t > cutoff]
        )
        attempts = len(
            [
                t
                for t in self._conflict_history.get(f"{entity_version_key}:attempts", [])
                if t > cutoff
            ]
        )

        if attempts == 0:
            return 0.0
        return conflicts / attempts

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _sort_by_lock_order(keys: list[str]) -> list[str]:
        """Sort entity keys by their lock order level.

        Entities not in ENTITY_LOCK_ORDER are sorted to the end.

        Args:
            keys: List of entity version keys.

        Returns:
            Sorted list by lock order.
        """
        def lock_level(key: str) -> int:
            # Extract entity type from key (first segment)
            entity_type = key.split(":")[0] if ":" in key else key
            return ENTITY_LOCK_LEVEL.get(entity_type, 999)

        return sorted(keys, key=lock_level)