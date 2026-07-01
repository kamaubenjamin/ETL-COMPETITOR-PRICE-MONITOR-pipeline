from __future__ import annotations

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from src.entity_runtime.concurrency.config import EntityConcurrencyConfig
from src.entity_runtime.concurrency.guard import EntityConcurrencyGuard
from src.entity_runtime.concurrency.leases import LeaseManager
from src.entity_runtime.concurrency.optimistic import OptimisticLockManager
from src.entity_runtime.concurrency.pessimistic import PessimisticLockManager
from src.entity_runtime.contracts import EntitySet, Supplier
from src.entity_runtime.orchestration import EntityRuntimeOrchestrator
from src.entity_runtime.store.idempotency import EntityIdempotencyRegistry
from src.entity_runtime.store.version_store import EntityVersionStore


class _DummyEngine:
    def __init__(self, entity_set: EntitySet) -> None:
        self.entity_set = entity_set

    def extract(self, pipeline_result):
        return self.entity_set


def _build_guard(db_path: str, *, lease_s: int = 2, retry_attempts: int = 3) -> EntityConcurrencyGuard:
    config = EntityConcurrencyConfig(
        entity_version_store_enabled=True,
        entity_version_store_db_path=db_path,
        entity_lease_default_s=lease_s,
        entity_lease_refresh_interval_s=1,
        entity_lease_refresh_grace_s=1,
        entity_lease_retry_max_attempts=2,
        optimistic_retry_max_attempts=retry_attempts,
        optimistic_retry_base_delay_ms=5,
        optimistic_retry_max_delay_ms=20,
        escalation_retry_threshold=2,
        escalation_cooldown_minutes=1,
    )
    store = EntityVersionStore(db_path=db_path)
    store.initialize_schema()
    idempotency = EntityIdempotencyRegistry(db_path=db_path)
    optimistic = OptimisticLockManager(version_store=store, config=config)
    pessimistic = PessimisticLockManager(config=config, db_path=db_path)
    lease_manager = LeaseManager(config=config, db_path=db_path)
    return EntityConcurrencyGuard(
        version_store=store,
        optimistic_manager=optimistic,
        pessimistic_manager=pessimistic,
        lease_manager=lease_manager,
        idempotency_registry=idempotency,
        config=config,
    )


def test_concurrent_writes_produce_monotonic_versions(tmp_path):
    guard = _build_guard(str(tmp_path / "concurrent.db"))
    keys = [f"supplier:doc-{i}:acme" for i in range(5)]

    def write_one(index: int):
        return guard.write_entity(
            entity_version_key=keys[index],
            data={"name": f"ACME-{index}"},
            entity_type="supplier",
            entity_id=f"acme-{index}",
            pipeline_run_id=f"run-{index}",
            stage_name="extract",
        )

    with ThreadPoolExecutor(max_workers=5) as executor:
        records = list(executor.map(write_one, range(5)))

    versions = sorted(record.version for record in records)
    assert versions == [1, 1, 1, 1, 1]


def test_lease_expiry_allows_recovery(tmp_path):
    guard = _build_guard(str(tmp_path / "lease.db"), lease_s=1)
    first = guard.write_entity(
        entity_version_key="supplier:doc-1:acme",
        data={"name": "ACME"},
        entity_type="supplier",
        entity_id="acme",
        pipeline_run_id="run-1",
        stage_name="extract",
    )
    assert first.version == 1

    time.sleep(1.2)
    second = guard.write_entity(
        entity_version_key="supplier:doc-1:acme",
        data={"name": "ACME v2"},
        entity_type="supplier",
        entity_id="acme",
        pipeline_run_id="run-2",
        stage_name="extract",
    )
    assert second.version == 2


def test_idempotent_retry_returns_existing_record(tmp_path):
    guard = _build_guard(str(tmp_path / "idem.db"))
    first = guard.write_entity(
        entity_version_key="supplier:doc-1:acme",
        data={"name": "ACME"},
        entity_type="supplier",
        entity_id="acme",
        pipeline_run_id="run-1",
        stage_name="extract",
    )
    duplicate = guard.write_entity(
        entity_version_key="supplier:doc-1:acme",
        data={"name": "ACME"},
        entity_type="supplier",
        entity_id="acme",
        pipeline_run_id="run-1",
        stage_name="extract",
    )

    assert first.version == 1
    assert duplicate.version == 1
    assert duplicate.data == first.data


def test_orchestrator_gracefully_degrades_when_guard_initialization_fails(tmp_path, monkeypatch):
    monkeypatch.setenv("ENTITY_VERSION_STORE_ENABLED", "true")
    monkeypatch.setenv("ENTITY_VERSION_STORE_DB_PATH", str(tmp_path / "missing" / "store.db"))

    orchestrator = EntityRuntimeOrchestrator(_DummyEngine(EntitySet(source_document_id="doc-9")))

    result = orchestrator.run({"payload": "ok"}, pipeline_run_id="run-1", stage_name="entity_extract")

    assert isinstance(result, EntitySet)
    assert result.source_document_id == "doc-9"


def test_pessimistic_escalation_is_triggered_by_conflict_history(tmp_path):
    config = EntityConcurrencyConfig(
        entity_version_store_enabled=True,
        entity_version_store_db_path=str(tmp_path / "escalation.db"),
        entity_lease_default_s=5,
        entity_lease_refresh_interval_s=1,
        entity_lease_refresh_grace_s=1,
        entity_lease_retry_max_attempts=2,
        optimistic_retry_max_attempts=2,
        optimistic_retry_base_delay_ms=5,
        optimistic_retry_max_delay_ms=20,
        escalation_retry_threshold=2,
        escalation_cooldown_minutes=1,
    )
    manager = PessimisticLockManager(config=config, db_path=str(tmp_path / "escalation.db"))
    manager.record_conflict("supplier:doc-1:acme")
    manager.record_conflict("supplier:doc-1:acme")
    manager.record_write_attempt("supplier:doc-1:acme")
    manager.record_write_attempt("supplier:doc-1:acme")

    assert manager.should_escalate("supplier:doc-1:acme") is True


def test_runtime_benchmark_smoke(tmp_path):
    guard = _build_guard(str(tmp_path / "bench.db"))
    start = time.perf_counter()
    for index in range(10):
        guard.write_entity(
            entity_version_key=f"supplier:doc-{index}:acme",
            data={"name": f"ACME-{index}"},
            entity_type="supplier",
            entity_id=f"acme-{index}",
            pipeline_run_id=f"run-{index}",
            stage_name="extract",
        )
    elapsed = time.perf_counter() - start

    assert elapsed < 2.0
