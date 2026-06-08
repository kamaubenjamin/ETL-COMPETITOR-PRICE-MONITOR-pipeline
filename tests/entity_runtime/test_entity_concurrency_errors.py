"""Tests for entity concurrency exception hierarchy — all 8 exception types."""

import pytest

from src.entity_runtime.concurrency.errors import (
    EntityConflictError,
    EntityCorruptionError,
    EntityDeadlockError,
    EntityDuplicateWriteError,
    EntityLeaseError,
    EntityLeaseLostError,
    EntityLockTimeoutError,
    EntityStoreUnavailableError,
)


class TestEntityConflictError:
    """CAS version mismatch."""

    def test_construct_with_defaults(self):
        err = EntityConflictError()
        assert err.entity_version_key == ""
        assert err.expected_version == 0
        assert err.actual_version == 0
        assert str(err) == "Entity conflict on : expected version 0, actual version 0"

    def test_construct_with_args(self):
        err = EntityConflictError(
            entity_version_key="supplier:doc-1:acme",
            expected_version=1,
            actual_version=2,
        )
        assert err.entity_version_key == "supplier:doc-1:acme"
        assert "expected version 1" in str(err)
        assert "actual version 2" in str(err)

    def test_construct_with_message(self):
        err = EntityConflictError(message="Custom conflict message")
        assert str(err) == "Custom conflict message"

    def test_is_runtime_error(self):
        assert isinstance(EntityConflictError(), RuntimeError)


class TestEntityCorruptionError:
    """Checksum mismatch."""

    def test_construct_with_defaults(self):
        err = EntityCorruptionError()
        assert err.entity_version_key == ""
        assert err.expected_checksum == ""
        assert err.actual_checksum == ""

    def test_construct_with_args(self):
        err = EntityCorruptionError(
            entity_version_key="supplier:doc-1:acme",
            expected_checksum="abc123",
            actual_checksum="def456",
        )
        assert err.entity_version_key == "supplier:doc-1:acme"
        assert "abc123" in str(err)
        assert "def456" in str(err)

    def test_is_runtime_error(self):
        assert isinstance(EntityCorruptionError(), RuntimeError)


class TestEntityLeaseError:
    """Lease acquisition or refresh failure."""

    def test_construct_with_defaults(self):
        err = EntityLeaseError()
        assert err.entity_version_key == ""
        assert err.holder_id == ""

    def test_construct_with_holder(self):
        err = EntityLeaseError(
            entity_version_key="supplier:doc-1:acme",
            holder_id="host-123-pipeline-1",
        )
        assert "holder=host-123-pipeline-1" in str(err)

    def test_is_entity_lease_error(self):
        assert isinstance(EntityLeaseError(), RuntimeError)


class TestEntityLeaseLostError:
    """Lease expired during write."""

    def test_construct(self):
        err = EntityLeaseLostError(
            entity_version_key="supplier:doc-1:acme",
            holder_id="host-123-pipeline-1",
        )
        assert "Lease lost" in str(err)
        assert err.entity_version_key == "supplier:doc-1:acme"

    def test_inherits_from_entity_lease_error(self):
        assert isinstance(EntityLeaseLostError(), EntityLeaseError)

    def test_is_runtime_error(self):
        assert isinstance(EntityLeaseLostError(), RuntimeError)


class TestEntityLockTimeoutError:
    """Pessimistic lock acquisition timeout."""

    def test_construct_with_defaults(self):
        err = EntityLockTimeoutError()
        assert err.entity_version_key == ""
        assert err.timeout_s == 0

    def test_construct_with_args(self):
        err = EntityLockTimeoutError(
            entity_version_key="supplier:doc-1:acme",
            timeout_s=30,
        )
        assert "exceeded 30s" in str(err)

    def test_is_runtime_error(self):
        assert isinstance(EntityLockTimeoutError(), RuntimeError)


class TestEntityDeadlockError:
    """Deadlock detected during pessimistic lock acquisition."""

    def test_construct_with_defaults(self):
        err = EntityDeadlockError()
        assert err.held_locks == []
        assert err.attempted_lock == ""

    def test_construct_with_args(self):
        err = EntityDeadlockError(
            entity_version_key="supplier:doc-1:acme",
            held_locks=["supplier:doc-1:acme", "line_item:doc-1:item-1"],
            attempted_lock="customer:doc-1:quickmart",
        )
        assert "Deadlock detected" in str(err)
        assert "customer:doc-1:quickmart" in str(err)

    def test_is_runtime_error(self):
        assert isinstance(EntityDeadlockError(), RuntimeError)


class TestEntityDuplicateWriteError:
    """Idempotency key collision."""

    def test_construct_with_defaults(self):
        err = EntityDuplicateWriteError()
        assert err.idempotency_key == ""
        assert err.entity_version_key == ""
        assert err.existing_version == 0

    def test_construct_with_args(self):
        err = EntityDuplicateWriteError(
            idempotency_key="a1b2c3d4e5f6",
            entity_version_key="supplier:doc-1:acme",
            existing_version=3,
            existing_run="run-001",
        )
        assert "Duplicate write" in str(err)
        assert "existing_version=3" in str(err)

    def test_is_runtime_error(self):
        assert isinstance(EntityDuplicateWriteError(), RuntimeError)


class TestEntityStoreUnavailableError:
    """Version store connection failure."""

    def test_construct_with_defaults(self):
        err = EntityStoreUnavailableError()
        assert err.db_path == ""
        assert err.operation == ""

    def test_construct_with_args(self):
        err = EntityStoreUnavailableError(
            db_path="data/entity_version_store.db",
            operation="write_version",
        )
        assert "Entity version store unavailable" in str(err)
        assert "data/entity_version_store.db" in str(err)
        assert "write_version" in str(err)

    def test_is_runtime_error(self):
        assert isinstance(EntityStoreUnavailableError(), RuntimeError)