"""Unit tests for locking exception types.

Tests cover:
- Exception construction with valid arguments
- Exception construction with default arguments
- Attributes on raised/caught exceptions
- String representation (str, repr)
- Edge cases
"""

import pytest

from src.workflow_runtime.locking.exceptions import (
    LockAcquisitionError,
    IdempotencyRejectionError,
    LockProviderError,
    LeaseRefreshError,
)


class TestLockAcquisitionError:
    """Tests for LockAcquisitionError."""

    def test_construct_with_all_args(self) -> None:
        """LockAcquisitionError can be constructed with all arguments."""
        error = LockAcquisitionError(
            lock_id="test_workflow",
            current_holder_id="host-1234-run-abc",
            expires_at="2026-06-03T08:05:00",
        )
        assert error.lock_id == "test_workflow"
        assert error.current_holder_id == "host-1234-run-abc"
        assert error.expires_at == "2026-06-03T08:05:00"
        assert "Lock acquisition failed" in str(error)

    def test_construct_with_minimal_args(self) -> None:
        """LockAcquisitionError can be constructed with only lock_id."""
        error = LockAcquisitionError(lock_id="test_workflow")
        assert error.lock_id == "test_workflow"
        assert error.current_holder_id is None
        assert error.expires_at is None
        assert "Lock acquisition failed" in str(error)

    def test_attributes_on_catch(self) -> None:
        """Attributes are accessible when the exception is caught."""
        try:
            raise LockAcquisitionError(
                lock_id="test_workflow",
                current_holder_id="host-1234-run-abc",
                expires_at="2026-06-03T08:05:00",
            )
        except LockAcquisitionError as e:
            assert e.lock_id == "test_workflow"
            assert e.current_holder_id == "host-1234-run-abc"
            assert e.expires_at == "2026-06-03T08:05:00"

    def test_custom_message(self) -> None:
        """LockAcquisitionError supports custom messages."""
        error = LockAcquisitionError(
            lock_id="test",
            message="Custom error message",
        )
        assert str(error) == "Custom error message"

    def test_repr_contains_class_name(self) -> None:
        """repr() contains the class name."""
        error = LockAcquisitionError(lock_id="test")
        assert "LockAcquisitionError" in repr(error)


class TestIdempotencyRejectionError:
    """Tests for IdempotencyRejectionError."""

    def test_construct_with_all_args(self) -> None:
        """IdempotencyRejectionError can be constructed with all arguments."""
        error = IdempotencyRejectionError(
            idempotency_key="test_workflow-scheduled-2026-06-03T08:00",
            existing_status="completed",
            existing_pipeline_run_id="run-001-abc-def",
        )
        assert error.idempotency_key == "test_workflow-scheduled-2026-06-03T08:00"
        assert error.existing_status == "completed"
        assert error.existing_pipeline_run_id == "run-001-abc-def"
        assert "already processed" in str(error)

    def test_attributes_on_catch(self) -> None:
        """Attributes are accessible when the exception is caught."""
        try:
            raise IdempotencyRejectionError(
                idempotency_key="test-key",
                existing_status="failed",
                existing_pipeline_run_id="run-002",
            )
        except IdempotencyRejectionError as e:
            assert e.idempotency_key == "test-key"
            assert e.existing_status == "failed"
            assert e.existing_pipeline_run_id == "run-002"

    def test_custom_message(self) -> None:
        """IdempotencyRejectionError supports custom messages."""
        error = IdempotencyRejectionError(
            idempotency_key="test-key",
            existing_status="completed",
            existing_pipeline_run_id="run-001",
            message="Custom: duplicate detected",
        )
        assert str(error) == "Custom: duplicate detected"


class TestLockProviderError:
    """Tests for LockProviderError."""

    def test_construct_with_provider_name_only(self) -> None:
        """LockProviderError can be constructed with provider_name only."""
        error = LockProviderError(provider_name="database")
        assert error.provider_name == "database"
        assert error.original_exception is None
        assert "database" in str(error)
        assert "encountered an error" in str(error)

    def test_construct_with_original_exception(self) -> None:
        """LockProviderError wraps an original exception."""
        original = ConnectionError("DB connection refused")
        error = LockProviderError(
            provider_name="database",
            original_exception=original,
        )
        assert error.provider_name == "database"
        assert error.original_exception is original
        assert "DB connection refused" in str(error)

    def test_attributes_on_catch(self) -> None:
        """Attributes are accessible when the exception is caught."""
        original = RuntimeError("disk full")
        try:
            raise LockProviderError(
                provider_name="file",
                original_exception=original,
            )
        except LockProviderError as e:
            assert e.provider_name == "file"
            assert e.original_exception is original


class TestLeaseRefreshError:
    """Tests for LeaseRefreshError."""

    def test_construct_with_all_args(self) -> None:
        """LeaseRefreshError can be constructed with all arguments."""
        error = LeaseRefreshError(
            lock_id="test_workflow",
            holder_id="host-1234-run-abc",
        )
        assert error.lock_id == "test_workflow"
        assert error.holder_id == "host-1234-run-abc"
        assert error.original_exception is None
        assert "Lease refresh failed" in str(error)

    def test_construct_with_original_exception(self) -> None:
        """LeaseRefreshError wraps an original exception."""
        original = TimeoutError("DB timeout")
        error = LeaseRefreshError(
            lock_id="test_workflow",
            holder_id="host-1234",
            original_exception=original,
        )
        assert error.lock_id == "test_workflow"
        assert error.holder_id == "host-1234"
        assert error.original_exception is original
        assert "DB timeout" in str(error)

    def test_attributes_on_catch(self) -> None:
        """Attributes are accessible when the exception is caught."""
        original = ConnectionError("connection lost")
        try:
            raise LeaseRefreshError(
                lock_id="test",
                holder_id="holder-1",
                original_exception=original,
            )
        except LeaseRefreshError as e:
            assert e.lock_id == "test"
            assert e.holder_id == "holder-1"
            assert e.original_exception is original


class TestExceptionHierarchy:
    """Tests that all exceptions inherit from Exception."""

    def test_lock_acquisition_is_exception(self) -> None:
        assert issubclass(LockAcquisitionError, Exception)

    def test_idempotency_rejection_is_exception(self) -> None:
        assert issubclass(IdempotencyRejectionError, Exception)

    def test_lock_provider_error_is_exception(self) -> None:
        assert issubclass(LockProviderError, Exception)

    def test_lease_refresh_error_is_exception(self) -> None:
        assert issubclass(LeaseRefreshError, Exception)

    def test_unique_exception_types(self) -> None:
        """All four exception types are distinct."""
        exceptions = {
            LockAcquisitionError,
            IdempotencyRejectionError,
            LockProviderError,
            LeaseRefreshError,
        }
        assert len(exceptions) == 4