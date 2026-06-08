"""Integration tests — backward compatibility mode (flag disabled)."""
from __future__ import annotations

from src.entity_runtime.concurrency.config import EntityConcurrencyConfig
from src.entity_runtime.concurrency.guard import EntityConcurrencyGuard
from src.entity_runtime.concurrency.leases import LeaseManager
from src.entity_runtime.concurrency.optimistic import OptimisticLockManager
from src.entity_runtime.concurrency.pessimistic import PessimisticLockManager
from src.entity_runtime.store.idempotency import EntityIdempotencyRegistry
from src.entity_runtime.store.version_store import EntityVersionStore


class TestBackwardCompat:
    """Backward compatibility mode."""

    def test_disabled_flag_writes_without_guard(self, db_path: str):
        config = EntityConcurrencyConfig(
            entity_version_store_enabled=False,
        )
        store = EntityVersionStore(db_path=db_path)
        store.initialize_schema()
        idem = EntityIdempotencyRegistry(db_path=db_path)
        optimistic = OptimisticLockManager(version_store=store, config=config)
        pessimistic = PessimisticLockManager(config=config, db_path=db_path)
        lease = LeaseManager(config=config, db_path=db_path)
        guard = EntityConcurrencyGuard(
            version_store=store,
            optimistic_manager=optimistic,
            pessimistic_manager=pessimistic,
            lease_manager=lease,
            idempotency_registry=idem,
            config=config,
        )

        record = guard.write_entity(
            entity_version_key="supplier:doc-1:acme",
            data={"name": "ACME"},
            entity_type="supplier",
            entity_id="acme",
            pipeline_run_id="run-001",
            stage_name="extract",
        )
        assert record is not None
        assert record.version >= 1

    def test_enabled_flag_uses_guard(self, db_path: str):
        config = EntityConcurrencyConfig(
            entity_version_store_enabled=True,
            entity_lease_default_s=30,
        )
        store = EntityVersionStore(db_path=db_path)
        store.initialize_schema()
        idem = EntityIdempotencyRegistry(db_path=db_path)
        optimistic = OptimisticLockManager(version_store=store, config=config)
        pessimistic = PessimisticLockManager(config=config, db_path=db_path)
        lease = LeaseManager(config=config, db_path=db_path)
        guard = EntityConcurrencyGuard(
            version_store=store,
            optimistic_manager=optimistic,
            pessimistic_manager=pessimistic,
            lease_manager=lease,
            idempotency_registry=idem,
            config=config,
        )

        record = guard.write_entity(
            entity_version_key="supplier:doc-1:acme",
            data={"name": "ACME"},
            entity_type="supplier",
            entity_id="acme",
            pipeline_run_id="run-001",
            stage_name="extract",
        )
        assert record is not None
        assert record.version == 1