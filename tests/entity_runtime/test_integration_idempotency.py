"""Integration tests — idempotency prevents duplicate writes."""
from __future__ import annotations

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


class TestIdempotency:
    """Idempotency prevents duplicate writes."""

    def test_first_write_accepted(self, db_path: str):
        guard = _create_guard(db_path)
        guard.write_entity(
            entity_version_key="supplier:doc-1:acme",
            data={"name": "ACME"},
            entity_type="supplier",
            entity_id="acme",
            pipeline_run_id="run-001",
            stage_name="extract",
        )
        result = guard._idempotency_registry.check_and_record(
            idempotency_key=guard._idempotency_registry.generate_key(
                entity_type="supplier",
                source_document_id="doc-1",
                entity_natural_key="acme",
                workflow_run_id="run-001",
                stage_name="extract",
            ),
            entity_version_key="supplier:doc-1:acme",
            new_version=1,
            pipeline_run_id="run-001",
        )
        assert result.status == "duplicate"