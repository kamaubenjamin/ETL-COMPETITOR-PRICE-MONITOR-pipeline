"""EntityStoreCleanupJob — background cleanup for expired idempotency and lease records.

Runs periodic cleanup cycles to remove stale idempotency keys and expired leases.
"""

from __future__ import annotations

import logging
import threading
from typing import Optional

from src.entity_runtime.concurrency.config import EntityConcurrencyConfig
from src.entity_runtime.concurrency.leases import LeaseManager
from src.entity_runtime.store.idempotency import EntityIdempotencyRegistry

logger = logging.getLogger(__name__)


class EntityStoreCleanupJob:
    """Background cleanup job for entity version store.

    Periodically removes expired idempotency records and stale leases
    to prevent unbounded growth of the entity version store.

    Runs as a daemon thread with configurable interval.
    """

    def __init__(
        self,
        idempotency_registry: EntityIdempotencyRegistry,
        lease_manager: LeaseManager,
        config: EntityConcurrencyConfig,
    ) -> None:
        self._idempotency_registry = idempotency_registry
        self._lease_manager = lease_manager
        self._config = config

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Cumulative stats
        self._total_idempotency_removed = 0
        self._total_leases_removed = 0
        self._stats_lock = threading.RLock()

    def run_cycle(self) -> dict[str, int]:
        """Execute a single cleanup cycle.

        Returns:
            Dict with cleanup stats: {'idempotency_removed': int, 'leases_removed': int}.
        """
        idempotency_removed = 0
        leases_removed = 0

        # Clean up idempotency records
        try:
            idempotency_removed = self._idempotency_registry.cleanup(
                retention_days=self._config.entity_idempotency_retention_days,
                in_progress_ttl_minutes=self._config.entity_idempotency_in_progress_ttl_minutes,
                batch_size=self._config.entity_idempotency_cleanup_batch_size,
            )
        except Exception as e:
            logger.warning("Idempotency cleanup cycle failed: %s", e)

        # Clean up expired leases (delete all expired lease records)
        try:
            conn = self._lease_manager._get_connection()
            cur = conn.execute(
                "DELETE FROM entity_leases WHERE expires_at < datetime('now')"
            )
            leases_removed = cur.rowcount
            conn.commit()
        except Exception as e:
            logger.warning("Lease cleanup cycle failed: %s", e)

        # Update cumulative stats
        with self._stats_lock:
            self._total_idempotency_removed += idempotency_removed
            self._total_leases_removed += leases_removed

        return {
            "idempotency_removed": idempotency_removed,
            "leases_removed": leases_removed,
        }

    def start(self, interval_minutes: int = 60) -> None:
        """Start the background cleanup daemon thread.

        Args:
            interval_minutes: Time between cleanup cycles.
        """
        if self._thread is not None and self._thread.is_alive():
            return  # Already running

        self._stop_event.clear()
        interval_seconds = interval_minutes * 60

        def cleanup_loop() -> None:
            while not self._stop_event.is_set():
                if self._stop_event.wait(timeout=interval_seconds):
                    break
                try:
                    stats = self.run_cycle()
                    if stats["idempotency_removed"] > 0 or stats["leases_removed"] > 0:
                        logger.info(
                            "Cleanup cycle: idempotency=%d, leases=%d",
                            stats["idempotency_removed"],
                            stats["leases_removed"],
                        )
                except Exception as e:
                    logger.error("Cleanup cycle failed: %s", e)

        self._thread = threading.Thread(
            target=cleanup_loop,
            name="entity-store-cleanup",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop the background cleanup daemon thread."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def get_cleanup_stats(self) -> dict[str, int]:
        """Get cumulative cleanup statistics for monitoring.

        Returns:
            Dict with cumulative stats: {'idempotency_removed': int, 'leases_removed': int}.
        """
        with self._stats_lock:
            return {
                "idempotency_removed": self._total_idempotency_removed,
                "leases_removed": self._total_leases_removed,
            }