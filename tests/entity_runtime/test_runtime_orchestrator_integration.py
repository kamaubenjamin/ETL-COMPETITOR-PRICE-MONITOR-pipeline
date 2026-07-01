from __future__ import annotations

from src.entity_runtime.concurrency.config import EntityConcurrencyConfig
from src.entity_runtime.contracts import EntitySet, Supplier
from src.entity_runtime.orchestration import EntityRuntimeOrchestrator


class DummyEngine:
    def __init__(self, entity_set: EntitySet) -> None:
        self.entity_set = entity_set

    def extract(self, pipeline_result):
        return self.entity_set


def test_orchestrator_initializes_guard_when_enabled(tmp_path):
    db_path = tmp_path / "entity_store.db"
    config = EntityConcurrencyConfig(
        entity_version_store_enabled=True,
        entity_version_store_db_path=str(db_path),
        entity_lease_default_s=30,
        entity_lease_refresh_interval_s=5,
        optimistic_retry_max_attempts=1,
        optimistic_retry_base_delay_ms=1,
        optimistic_retry_max_delay_ms=10,
    )
    entity_set = EntitySet(
        source_document_id="doc-1",
        suppliers=[Supplier(name="Acme")],
    )
    orchestrator = EntityRuntimeOrchestrator(DummyEngine(entity_set), config=config)

    result = orchestrator.run({"payload": "ok"}, pipeline_run_id="run-1", stage_name="entity_extract")

    assert orchestrator.concurrency_enabled is True
    assert result.entity_version == 1
    assert result.suppliers[0].entity_version == 1

    read_back = orchestrator.read_entity(
        f"supplier:doc-1:{orchestrator._entity_natural_key(result.suppliers[0])}"
    )
    assert read_back is not None
    assert read_back.version == 1


def test_orchestrator_uses_environment_flag_when_config_is_omitted(tmp_path, monkeypatch):
    db_path = tmp_path / "entity_store.db"
    monkeypatch.setenv("ENTITY_VERSION_STORE_ENABLED", "true")
    monkeypatch.setenv("ENTITY_VERSION_STORE_DB_PATH", str(db_path))

    orchestrator = EntityRuntimeOrchestrator(DummyEngine(EntitySet(source_document_id="doc-2")))

    assert orchestrator.concurrency_enabled is True
