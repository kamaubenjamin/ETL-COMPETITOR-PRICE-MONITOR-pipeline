"""Tests for EntityConcurrencyGuard — orchestration, error paths, write lifecycle."""
from __future__ import annotations

from src.entity_runtime.concurrency.guard import EntityConcurrencyGuard
from src.entity_runtime.store.version_store import EntityVersionStore


class TestGuardWrite:
    """Guard write lifecycle tests."""

    def test_write_entity_optimistic_success(self, guard: EntityConcurrencyGuard, store: EntityVersionStore):
        record = guard.write_entity(
            entity_version_key="supplier:doc-1:acme",
            data={"name": "ACME Corp"},
            entity_type="supplier",
            entity_id="acme",
            pipeline_run_id="run-001",
            stage_name="extract",
        )
        assert record.version == 1
        assert record.state == "active"

    def test_write_entity_disabled_mode(self, config, store, db_path):
        """Test write with disabled version store."""
        from src.entity_runtime.concurrency.config import EntityConcurrencyConfig
        from src.entity_runtime.concurrency.optimistic import OptimisticLockManager
        from src.entity_runtime.concurrency.pessimistic import PessimisticLockManager
        from src.entity_runtime.concurrency.leases import LeaseManager
        from src.entity_runtime.store.idempotency import EntityIdempotencyRegistry

        disabled_config = EntityConcurrencyConfig(entity_version_store_enabled=False)
        optimistic = OptimisticLockManager(version_store=store, config=disabled_config)
        pessimistic = PessimisticLockManager(config=disabled_config, db_path=db_path)
        lease = LeaseManager(config=disabled_config, db_path=db_path)
        idem = EntityIdempotencyRegistry(db_path=db_path)

        g = EntityConcurrencyGuard(
            version_store=store,
            optimistic_manager=optimistic,
            pessimistic_manager=pessimistic,
            lease_manager=lease,
            idempotency_registry=idem,
            config=disabled_config,
        )
        record = g.write_entity(
            entity_version_key="supplier:doc-1:acme",
            data={"name": "ACME Corp"},
            entity_type="supplier",
            entity_id="acme",
            pipeline_run_id="run-001",
            stage_name="extract",
        )
        assert record is not None

    def test_read_entity(self, guard: EntityConcurrencyGuard, store: EntityVersionStore):
        guard.write_entity(
            entity_version_key="supplier:doc-1:acme",
            data={"name": "ACME Corp"},
            entity_type="supplier",
            entity_id="acme",
            pipeline_run_id="run-001",
            stage_name="extract",
        )
        record = guard.read_entity("supplier:doc-1:acme")
        assert record is not None
        assert record.version == 1

    def test_merge_entity(self, guard: EntityConcurrencyGuard, store: EntityVersionStore):
        guard.write_entity(
            entity_version_key="supplier:doc-1:acme",
            data={"name": "ACME Corp"},
            entity_type="supplier",
            entity_id="acme",
            pipeline_run_id="run-001",
            stage_name="extract",
        )
        record = guard.merge_entity(
            entity_version_key="supplier:doc-1:acme",
            new_data={"address": "123 Main St"},
            entity_type="supplier",
            entity_id="acme",
            pipeline_run_id="run-002",
            stage_name="merge",
        )
        assert record.version == 2
        assert record.data["name"] == "ACME Corp"
        assert record.data["address"] == "123 Main St"

    def test_merge_new_entity(self, guard: EntityConcurrencyGuard):
        record = guard.merge_entity(
            entity_version_key="supplier:doc-2:newco",
            new_data={"name": "NewCo"},
            entity_type="supplier",
            entity_id="newco",
            pipeline_run_id="run-001",
            stage_name="merge",
        )
        assert record.version == 1

    def test_get_conflict_info_no_entity(self, guard: EntityConcurrencyGuard):
        info = guard.get_conflict_info("supplier:doc-1:nonexistent")
        assert info is None