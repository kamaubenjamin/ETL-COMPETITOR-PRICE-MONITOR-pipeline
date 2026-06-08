"""Tests for EntityIdempotencyRegistry — dedup, TTL, cleanup."""
from __future__ import annotations

from src.entity_runtime.store.idempotency import EntityIdempotencyRegistry


class TestIdempotencyKeyGeneration:
    """Key generation operations."""

    def test_generate_key_deterministic(self, idempotency_registry: EntityIdempotencyRegistry):
        key1 = idempotency_registry.generate_key(
            entity_type="supplier",
            source_document_id="doc-1",
            entity_natural_key="acme",
            workflow_run_id="run-001",
            stage_name="extract",
        )
        key2 = idempotency_registry.generate_key(
            entity_type="supplier",
            source_document_id="doc-1",
            entity_natural_key="acme",
            workflow_run_id="run-001",
            stage_name="extract",
        )
        assert key1 == key2
        assert key1.startswith("entity_write:v1:")

    def test_generate_key_different_inputs(self, idempotency_registry: EntityIdempotencyRegistry):
        key1 = idempotency_registry.generate_key(
            entity_type="supplier",
            source_document_id="doc-1",
            entity_natural_key="acme",
            workflow_run_id="run-001",
            stage_name="extract",
        )
        key2 = idempotency_registry.generate_key(
            entity_type="customer",
            source_document_id="doc-1",
            entity_natural_key="acme",
            workflow_run_id="run-001",
            stage_name="extract",
        )
        assert key1 != key2


class TestCheckAndRecord:
    """Check-and-record operations."""

    def test_first_write_accepted(self, idempotency_registry: EntityIdempotencyRegistry):
        result = idempotency_registry.check_and_record(
            idempotency_key="test-key-1",
            entity_version_key="supplier:doc-1:acme",
            new_version=1,
            pipeline_run_id="run-001",
        )
        assert result.status == "accepted"

    def test_duplicate_write_rejected(self, idempotency_registry: EntityIdempotencyRegistry):
        idempotency_registry.check_and_record(
            idempotency_key="test-key-2",
            entity_version_key="supplier:doc-1:acme",
            new_version=1,
            pipeline_run_id="run-001",
        )
        result = idempotency_registry.check_and_record(
            idempotency_key="test-key-2",
            entity_version_key="supplier:doc-1:acme",
            new_version=1,
            pipeline_run_id="run-001",
        )
        assert result.status == "duplicate"

    def test_get_status(self, idempotency_registry: EntityIdempotencyRegistry):
        idempotency_registry.check_and_record(
            idempotency_key="test-key-3",
            entity_version_key="supplier:doc-1:acme",
            new_version=1,
            pipeline_run_id="run-001",
        )
        result = idempotency_registry.get_status("test-key-3")
        assert result is not None
        assert result.status == "in_progress"

    def test_mark_completed(self, idempotency_registry: EntityIdempotencyRegistry):
        idempotency_registry.check_and_record(
            idempotency_key="test-key-4",
            entity_version_key="supplier:doc-1:acme",
            new_version=1,
            pipeline_run_id="run-001",
        )
        assert idempotency_registry.mark_completed("test-key-4")
        result = idempotency_registry.get_status("test-key-4")
        assert result is not None
        assert result.status == "completed"