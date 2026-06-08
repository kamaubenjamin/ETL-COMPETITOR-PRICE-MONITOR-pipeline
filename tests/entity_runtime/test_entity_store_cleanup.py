"""Tests for EntityStoreCleanupJob — cleanup cycle, expiry logic."""
from __future__ import annotations

from src.entity_runtime.concurrency.config import EntityConcurrencyConfig
from src.entity_runtime.concurrency.leases import LeaseManager
from src.entity_runtime.store.cleanup import EntityStoreCleanupJob
from src.entity_runtime.store.idempotency import EntityIdempotencyRegistry


class TestCleanupCycle:
    """Cleanup cycle tests."""

    def test_cleanup_empty_store(self, idempotency_registry: EntityIdempotencyRegistry, db_path: str):
        config = EntityConcurrencyConfig()
        lease_manager = LeaseManager(config=config, db_path=db_path)
        cleanup = EntityStoreCleanupJob(
            idempotency_registry=idempotency_registry,
            lease_manager=lease_manager,
            config=config,
        )
        stats = cleanup.run_cycle()
        assert isinstance(stats, dict)
        assert "idempotency_removed" in stats
        assert "leases_removed" in stats

    def test_start_stop_cleanup(self, idempotency_registry: EntityIdempotencyRegistry, db_path: str):
        config = EntityConcurrencyConfig()
        lease_manager = LeaseManager(config=config, db_path=db_path)
        cleanup = EntityStoreCleanupJob(
            idempotency_registry=idempotency_registry,
            lease_manager=lease_manager,
            config=config,
        )
        cleanup.start(interval_minutes=1)
        cleanup.stop()

    def test_get_cleanup_stats(self, idempotency_registry: EntityIdempotencyRegistry, db_path: str):
        config = EntityConcurrencyConfig()
        lease_manager = LeaseManager(config=config, db_path=db_path)
        cleanup = EntityStoreCleanupJob(
            idempotency_registry=idempotency_registry,
            lease_manager=lease_manager,
            config=config,
        )
        stats = cleanup.get_cleanup_stats()
        assert stats["idempotency_removed"] == 0
        assert stats["leases_removed"] == 0