"""Tests for EntityVersionRecord — frozen dataclass contract."""

import pytest

from src.entity_runtime.store.version_store import EntityVersionRecord


class TestEntityVersionRecordConstruction:
    """Verify EntityVersionRecord is a correct frozen dataclass."""

    def test_minimal_construction(self):
        record = EntityVersionRecord(
            entity_version_key="supplier:doc-1:acme",
            entity_type="supplier",
            entity_id="acme",
            version=1,
            state="active",
            data={"name": "ACME Corp"},
            checksum="abc123",
            previous_checksum="",
            created_at="2026-06-05T10:00:00Z",
            created_by="run-001",
        )
        assert record.entity_version_key == "supplier:doc-1:acme"
        assert record.entity_type == "supplier"
        assert record.entity_id == "acme"
        assert record.version == 1
        assert record.state == "active"
        assert record.data == {"name": "ACME Corp"}
        assert record.checksum == "abc123"
        assert record.previous_checksum == ""
        assert record.created_at == "2026-06-05T10:00:00Z"
        assert record.created_by == "run-001"
        assert record.source_document_id == ""
        assert record.lease_holder == ""
        assert record.lease_expires_at == ""

    def test_full_construction(self):
        record = EntityVersionRecord(
            entity_version_key="supplier:doc-1:acme",
            entity_type="supplier",
            entity_id="acme",
            version=2,
            state="active",
            data={"name": "ACME Corp Updated"},
            checksum="def456",
            previous_checksum="abc123",
            created_at="2026-06-05T11:00:00Z",
            created_by="run-002",
            source_document_id="doc-1",
            lease_holder="host-123-run-002",
            lease_expires_at="2026-06-05T11:02:00Z",
        )
        assert record.source_document_id == "doc-1"
        assert record.lease_holder == "host-123-run-002"
        assert record.lease_expires_at == "2026-06-05T11:02:00Z"

    def test_frozen_cannot_modify(self):
        record = EntityVersionRecord(
            entity_version_key="supplier:doc-1:acme",
            entity_type="supplier",
            entity_id="acme",
            version=1,
            state="active",
            data={"name": "ACME Corp"},
            checksum="abc123",
            previous_checksum="",
            created_at="2026-06-05T10:00:00Z",
            created_by="run-001",
        )
        with pytest.raises((AttributeError, TypeError)):
            record.version = 2  # type: ignore[misc]

    def test_frozen_prevents_new_attr(self):
        record = EntityVersionRecord(
            entity_version_key="supplier:doc-1:acme",
            entity_type="supplier",
            entity_id="acme",
            version=1,
            state="active",
            data={"name": "ACME Corp"},
            checksum="abc123",
            previous_checksum="",
            created_at="2026-06-05T10:00:00Z",
            created_by="run-001",
        )
        with pytest.raises((AttributeError, TypeError)):
            record.new_attr = "test"  # type: ignore[attr-defined]

    def test_equality_by_value(self):
        record_a = EntityVersionRecord(
            entity_version_key="supplier:doc-1:acme",
            entity_type="supplier",
            entity_id="acme",
            version=1,
            state="active",
            data={"name": "ACME Corp"},
            checksum="abc123",
            previous_checksum="",
            created_at="2026-06-05T10:00:00Z",
            created_by="run-001",
        )
        record_b = EntityVersionRecord(
            entity_version_key="supplier:doc-1:acme",
            entity_type="supplier",
            entity_id="acme",
            version=1,
            state="active",
            data={"name": "ACME Corp"},
            checksum="abc123",
            previous_checksum="",
            created_at="2026-06-05T10:00:00Z",
            created_by="run-001",
        )
        assert record_a == record_b
        # dict field makes record unhashable; skip hash equality