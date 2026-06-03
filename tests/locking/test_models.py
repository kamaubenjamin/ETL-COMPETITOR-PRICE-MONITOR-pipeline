"""Unit tests for LockAcquisition and IdempotencyRecord data models.

Tests cover:
- Construction with valid arguments
- Immutability (frozen=True)
- Slot-based attribute access
- Field types and values
- Edge cases (empty strings, boundary values)
"""

from datetime import datetime, timedelta

import pytest

from src.workflow_runtime.locking.models import LockAcquisition, IdempotencyRecord


# ── LockAcquisition Tests ──────────────────────────────────────────────


class TestLockAcquisition:
    """Tests for the LockAcquisition frozen dataclass."""

    def test_construct_with_valid_args(self, sample_lock_acquisition: LockAcquisition) -> None:
        """LockAcquisition can be constructed with valid arguments."""
        acquisition = sample_lock_acquisition
        assert acquisition.lock_id == "test_workflow"
        assert acquisition.holder_id == "host-1234-abc-def"
        assert acquisition.lease_duration_s == 300
        assert isinstance(acquisition.acquired_at, str)
        assert isinstance(acquisition.expires_at, str)

    def test_construct_with_edge_values(self) -> None:
        """LockAcquisition handles edge values correctly."""
        acquisition = LockAcquisition(
            lock_id="",
            holder_id="",
            acquired_at="",
            expires_at="",
            lease_duration_s=0,
        )
        assert acquisition.lock_id == ""
        assert acquisition.lease_duration_s == 0

    def test_immutable_cannot_modify_attributes(self, sample_lock_acquisition: LockAcquisition) -> None:
        """LockAcquisition is frozen — attributes cannot be modified."""
        with pytest.raises(AttributeError):
            sample_lock_acquisition.lock_id = "modified"  # type: ignore[misc]

    def test_immutable_cannot_add_attributes(self, sample_lock_acquisition: LockAcquisition) -> None:
        """LockAcquisition does not allow new attributes (slots)."""
        with pytest.raises((AttributeError, TypeError)):
            sample_lock_acquisition.new_field = "value"  # type: ignore[attr-defined]

    def test_lease_duration_type(self, sample_lock_acquisition: LockAcquisition) -> None:
        """lease_duration_s must be an int."""
        assert isinstance(sample_lock_acquisition.lease_duration_s, int)

    def test_timestamps_are_strings(self, sample_lock_acquisition: LockAcquisition) -> None:
        """acquired_at and expires_at must be strings (ISO-8601)."""
        assert isinstance(sample_lock_acquisition.acquired_at, str)
        assert isinstance(sample_lock_acquisition.expires_at, str)

    def test_expires_at_after_acquired_at(self) -> None:
        """expires_at should be after acquired_at for a valid lock."""
        now = datetime.utcnow()
        later = now + timedelta(seconds=300)
        acquisition = LockAcquisition(
            lock_id="test",
            holder_id="host",
            acquired_at=now.isoformat(),
            expires_at=later.isoformat(),
            lease_duration_s=300,
        )
        assert acquisition.expires_at > acquisition.acquired_at

    def test_equality_based_on_all_fields(self) -> None:
        """Two LockAcquisitions with same values should be equal."""
        now = datetime.utcnow().isoformat()
        later = (datetime.utcnow() + timedelta(seconds=300)).isoformat()
        a1 = LockAcquisition("wf1", "h1", now, later, 300)
        a2 = LockAcquisition("wf1", "h1", now, later, 300)
        assert a1 == a2
        assert hash(a1) == hash(a2)

    def test_inequality_when_fields_differ(self) -> None:
        """Two LockAcquisitions with different values should not be equal."""
        now = datetime.utcnow().isoformat()
        later = (datetime.utcnow() + timedelta(seconds=300)).isoformat()
        a1 = LockAcquisition("wf1", "h1", now, later, 300)
        a2 = LockAcquisition("wf2", "h2", now, later, 300)
        assert a1 != a2

    def test_repr_contains_all_fields(self, sample_lock_acquisition: LockAcquisition) -> None:
        """repr() should include all field values."""
        repr_str = repr(sample_lock_acquisition)
        assert "LockAcquisition" in repr_str
        assert sample_lock_acquisition.lock_id in repr_str
        assert sample_lock_acquisition.holder_id in repr_str


# ── IdempotencyRecord Tests ────────────────────────────────────────────


class TestIdempotencyRecord:
    """Tests for the IdempotencyRecord frozen dataclass."""

    def test_construct_with_valid_args(self, sample_idempotency_record: IdempotencyRecord) -> None:
        """IdempotencyRecord can be constructed with valid arguments."""
        record = sample_idempotency_record
        assert record.idempotency_key == "test_workflow-scheduled-2026-06-03T08:00"
        assert record.pipeline_run_id == "run-001-abc-def"
        assert record.status == "completed"
        assert isinstance(record.created_at, str)

    def test_construct_with_edge_values(self) -> None:
        """IdempotencyRecord handles edge values correctly."""
        record = IdempotencyRecord(
            idempotency_key="",
            pipeline_run_id="",
            status="",
            created_at="",
        )
        assert record.idempotency_key == ""
        assert record.status == ""

    def test_immutable_cannot_modify_attributes(self, sample_idempotency_record: IdempotencyRecord) -> None:
        """IdempotencyRecord is frozen — attributes cannot be modified."""
        with pytest.raises(AttributeError):
            sample_idempotency_record.status = "modified"  # type: ignore[misc]

    def test_immutable_cannot_add_attributes(self, sample_idempotency_record: IdempotencyRecord) -> None:
        """IdempotencyRecord does not allow new attributes (slots)."""
        with pytest.raises((AttributeError, TypeError)):
            sample_idempotency_record.new_field = "value"  # type: ignore[attr-defined]

    def test_status_string_type(self, sample_idempotency_record: IdempotencyRecord) -> None:
        """status must be a string."""
        assert isinstance(sample_idempotency_record.status, str)

    def test_pipeline_run_id_string_type(self, sample_idempotency_record: IdempotencyRecord) -> None:
        """pipeline_run_id must be a string."""
        assert isinstance(sample_idempotency_record.pipeline_run_id, str)

    def test_equality_based_on_all_fields(self) -> None:
        """Two IdempotencyRecords with same values should be equal."""
        now = datetime.utcnow().isoformat()
        r1 = IdempotencyRecord("key1", "run1", "completed", now)
        r2 = IdempotencyRecord("key1", "run1", "completed", now)
        assert r1 == r2
        assert hash(r1) == hash(r2)

    def test_inequality_when_fields_differ(self) -> None:
        """Two IdempotencyRecords with different values should not be equal."""
        now = datetime.utcnow().isoformat()
        r1 = IdempotencyRecord("key1", "run1", "completed", now)
        r2 = IdempotencyRecord("key2", "run2", "failed", now)
        assert r1 != r2

    def test_completed_vs_in_progress_statuses(
        self,
        sample_idempotency_record: IdempotencyRecord,
        sample_in_progress_idempotency_record: IdempotencyRecord,
    ) -> None:
        """Different status values produce different records."""
        assert sample_idempotency_record.status == "completed"
        assert sample_in_progress_idempotency_record.status == "in_progress"
        assert sample_idempotency_record != sample_in_progress_idempotency_record

    def test_failed_status(self, sample_failed_idempotency_record: IdempotencyRecord) -> None:
        """failed status is valid."""
        assert sample_failed_idempotency_record.status == "failed"

    def test_repr_contains_all_fields(self, sample_idempotency_record: IdempotencyRecord) -> None:
        """repr() should include all field values."""
        repr_str = repr(sample_idempotency_record)
        assert "IdempotencyRecord" in repr_str
        assert sample_idempotency_record.idempotency_key in repr_str
        assert sample_idempotency_record.status in repr_str