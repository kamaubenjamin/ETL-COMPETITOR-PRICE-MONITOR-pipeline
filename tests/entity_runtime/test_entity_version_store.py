"""Tests for EntityVersionStore — versioned CRUD, CAS operations, state transitions."""
from __future__ import annotations

import pytest

from src.entity_runtime.concurrency.errors import EntityConflictError
from src.entity_runtime.store.version_store import EntityVersionRecord, EntityVersionStore


class TestWriteVersion:
    """CAS write operations."""

    def test_write_version_1_new_entity(self, store: EntityVersionStore):
        record = store.write_version(
            entity_version_key="supplier:doc-1:acme",
            data={"name": "ACME Corp"},
            expected_version=0,
            checksum=EntityVersionStore.compute_checksum({"name": "ACME Corp"}),
            entity_type="supplier",
            entity_id="acme",
            created_by="run-001",
        )
        assert record.version == 1
        assert record.state == "active"
        assert record.entity_version_key == "supplier:doc-1:acme"

    def test_write_version_2_cas_success(self, store: EntityVersionStore):
        store.write_version(
            entity_version_key="supplier:doc-1:acme",
            data={"name": "ACME Corp v1"},
            expected_version=0,
            checksum=EntityVersionStore.compute_checksum({"name": "ACME Corp v1"}),
            entity_type="supplier",
            entity_id="acme",
            created_by="run-001",
        )
        record = store.write_version(
            entity_version_key="supplier:doc-1:acme",
            data={"name": "ACME Corp v2"},
            expected_version=1,
            checksum=EntityVersionStore.compute_checksum({"name": "ACME Corp v2"}),
            entity_type="supplier",
            entity_id="acme",
            created_by="run-002",
        )
        assert record.version == 2
        assert record.state == "active"

        # v1 should now be superseded
        v1 = store.read_version("supplier:doc-1:acme", 1)
        assert v1 is not None
        assert v1.state == "superseded"

    def test_write_version_2_cas_conflict(self, store: EntityVersionStore):
        store.write_version(
            entity_version_key="supplier:doc-1:acme",
            data={"name": "ACME Corp"},
            expected_version=0,
            checksum=EntityVersionStore.compute_checksum({"name": "ACME Corp"}),
            entity_type="supplier",
            entity_id="acme",
            created_by="run-001",
        )
        with pytest.raises(EntityConflictError) as exc:
            store.write_version(
                entity_version_key="supplier:doc-1:acme",
                data={"name": "ACME Corp conflict"},
                expected_version=0,
                checksum=EntityVersionStore.compute_checksum({"name": "ACME Corp conflict"}),
                entity_type="supplier",
                entity_id="acme",
                created_by="run-002",
            )
        assert exc.value.expected_version == 0
        assert exc.value.actual_version == 1


class TestReadOperations:
    """Read operations."""

    def test_read_active_version(self, store: EntityVersionStore):
        store.write_version(
            entity_version_key="supplier:doc-1:acme",
            data={"name": "ACME Corp"},
            expected_version=0,
            checksum=EntityVersionStore.compute_checksum({"name": "ACME Corp"}),
            entity_type="supplier",
            entity_id="acme",
            created_by="run-001",
        )
        active = store.read_active("supplier:doc-1:acme")
        assert active is not None
        assert active.version == 1
        assert active.state == "active"

    def test_read_active_nonexistent(self, store: EntityVersionStore):
        assert store.read_active("supplier:doc-1:nonexistent") is None

    def test_read_specific_version(self, store: EntityVersionStore):
        store.write_version(
            entity_version_key="supplier:doc-1:acme",
            data={"name": "v1"},
            expected_version=0,
            checksum=EntityVersionStore.compute_checksum({"name": "v1"}),
            entity_type="supplier",
            entity_id="acme",
            created_by="run-001",
        )
        v1 = store.read_version("supplier:doc-1:acme", 1)
        assert v1 is not None
        assert v1.data == {"name": "v1"}

    def test_read_version_history(self, store: EntityVersionStore):
        for i in range(3):
            store.write_version(
                entity_version_key="supplier:doc-1:acme",
                data={"name": f"v{i+1}"},
                expected_version=i,
                checksum=EntityVersionStore.compute_checksum({"name": f"v{i+1}"}),
                entity_type="supplier",
                entity_id="acme",
                created_by="run-001",
            )
        history = store.read_history("supplier:doc-1:acme")
        assert len(history) == 3
        assert [h.version for h in history] == [1, 2, 3]


class TestStateTransition:
    """State transition operations."""

    def test_active_to_superseded(self, store: EntityVersionStore):
        store.write_version(
            entity_version_key="supplier:doc-1:acme",
            data={"name": "v1"},
            expected_version=0,
            checksum=EntityVersionStore.compute_checksum({"name": "v1"}),
            entity_type="supplier",
            entity_id="acme",
            created_by="run-001",
        )
        assert store.transition_state("supplier:doc-1:acme", 1, "superseded")
        v1 = store.read_version("supplier:doc-1:acme", 1)
        assert v1 is not None
        assert v1.state == "superseded"

    def test_superseded_to_archived(self, store: EntityVersionStore):
        store.write_version(
            entity_version_key="supplier:doc-1:acme",
            data={"name": "v1"},
            expected_version=0,
            checksum=EntityVersionStore.compute_checksum({"name": "v1"}),
            entity_type="supplier",
            entity_id="acme",
            created_by="run-001",
        )
        store.transition_state("supplier:doc-1:acme", 1, "superseded")
        assert store.transition_state("supplier:doc-1:acme", 1, "archived")

    def test_invalid_transition(self, store: EntityVersionStore):
        store.write_version(
            entity_version_key="supplier:doc-1:acme",
            data={"name": "v1"},
            expected_version=0,
            checksum=EntityVersionStore.compute_checksum({"name": "v1"}),
            entity_type="supplier",
            entity_id="acme",
            created_by="run-001",
        )
        assert not store.transition_state("supplier:doc-1:acme", 1, "invalid")


class TestConflictLog:
    """Conflict logging operations."""

    def test_log_and_query_conflict(self, store: EntityVersionStore):
        cid = store.log_conflict(
            entity_version_key="supplier:doc-1:acme",
            conflict_type="version_mismatch",
            attempted_version=1,
            current_version=2,
            attempted_by="run-001",
            resolution="retry",
        )
        assert cid > 0
        conflicts = store.get_conflicts("supplier:doc-1:acme")
        assert len(conflicts) == 1
        assert conflicts[0]["conflict_type"] == "version_mismatch"


class TestCompareAndSwap:
    """CAS operation."""

    def test_cas_success(self, store: EntityVersionStore):
        store.write_version(
            entity_version_key="supplier:doc-1:acme",
            data={"name": "v1"},
            expected_version=0,
            checksum=EntityVersionStore.compute_checksum({"name": "v1"}),
            entity_type="supplier",
            entity_id="acme",
            created_by="run-001",
        )
        active = store.read_active("supplier:doc-1:acme")
        success, info = store.compare_and_swap(
            entity_version_key="supplier:doc-1:acme",
            data={"name": "v2"},
            expected_version=active.version,
            expected_checksum=active.checksum,
            entity_type="supplier",
            entity_id="acme",
            created_by="run-002",
            source_document_id="doc-2",
        )
        assert success
        assert info is None

    def test_cas_failure(self, store: EntityVersionStore):
        store.write_version(
            entity_version_key="supplier:doc-1:acme",
            data={"name": "v1"},
            expected_version=0,
            checksum=EntityVersionStore.compute_checksum({"name": "v1"}),
            entity_type="supplier",
            entity_id="acme",
            created_by="run-001",
        )
        success, info = store.compare_and_swap(
            entity_version_key="supplier:doc-1:acme",
            data={"name": "v2"},
            expected_version=999,
            expected_checksum="wrong",
            entity_type="supplier",
            entity_id="acme",
            created_by="run-002",
            source_document_id="doc-2",
        )
        assert not success
        assert info is not None
        assert info["conflict_type"] == "version_mismatch"