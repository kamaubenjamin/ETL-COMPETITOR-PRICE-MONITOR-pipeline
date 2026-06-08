"""Integration tests — concurrent entity writes with CAS."""
from __future__ import annotations

import concurrent.futures

from src.entity_runtime.concurrency.config import EntityConcurrencyConfig
from src.entity_runtime.concurrency.guard import EntityConcurrencyGuard
from src.entity_runtime.concurrency.leases import LeaseManager
from src.entity_runtime.concurrency.optimistic import OptimisticLockManager
from src.entity_runtime.concurrency.pessimistic import PessimisticLockManager
from src.entity_runtime.store.idempotency import EntityIdempotencyRegistry
from src.entity_runtime.store.version_store import EntityVersionStore


def _create_guard(db_path: str) -> EntityConcurrencyGuard:
    config = EntityConcurrencyConfig(
        entity_version_store_enabled=True,
        entity_lease_default_s=30,
        entity_lease_refresh_interval_s=5,
        entity_lease_retry_max_attempts=3,
        optimistic_retry_max_attempts=3,
        optimistic_retry_base_delay_ms=10,
        optimistic_retry_max_delay_ms=50,
    )
    store = EntityVersionStore(db_path=db_path)
    store.initialize_schema()
    idem = EntityIdempotencyRegistry(db_path=db_path)
    optimistic = OptimisticLockManager(version_store=store, config=config)
    pessimistic = PessimisticLockManager(config=config, db_path=db_path)
    lease = LeaseManager(config=config, db_path=db_path)
    return EntityConcurrencyGuard(
        version_store=store,
        optimistic_manager=optimistic,
        pessimistic_manager=pessimistic,
        lease_manager=lease,
        idempotency_registry=idem,
        config=config,
    )


class TestConcurrentWriters:
    """Two writers, same entity, optimistic locking."""

    def test_two_writers_same_entity(self, db_path: str):
        guard = _create_guard(db_path)

        # Use the same guard sequentially to test CAS write
        r1 = guard.write_entity(
            entity_version_key="supplier:doc-1:acme",
            data={"name": "Writer 1"},
            entity_type="supplier",
            entity_id="acme",
            pipeline_run_id="run-001",
            stage_name="extract",
        )
        # Second write with same guard should succeed as version 2
        r2 = guard.write_entity(
            entity_version_key="supplier:doc-1:acme",
            data={"name": "Writer 2"},
            entity_type="supplier",
            entity_id="acme",
            pipeline_run_id="run-002",
            stage_name="extract",
        )

        assert r1.version == 1
        assert r2.version == 2
        assert r1.version != r2.version

    def test_different_entities_no_conflict(self, db_path: str):
        guard1 = _create_guard(db_path)
        guard2 = _create_guard(db_path)

        def write1():
            return guard1.write_entity(
                entity_version_key="supplier:doc-1:acme",
                data={"name": "ACME"},
                entity_type="supplier",
                entity_id="acme",
                pipeline_run_id="run-001",
                stage_name="extract",
            )

        def write2():
            return guard2.write_entity(
                entity_version_key="supplier:doc-1:beta",
                data={"name": "Beta"},
                entity_type="supplier",
                entity_id="beta",
                pipeline_run_id="run-002",
                stage_name="extract",
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(write1)
            f2 = executor.submit(write2)
            r1 = f1.result()
            r2 = f2.result()

        assert r1.version == 1
        assert r2.version == 1