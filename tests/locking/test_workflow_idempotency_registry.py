"""Unit tests for MemoryIdempotencyRegistry and DBIdempotencyRegistry."""

import pytest

from src.workflow_runtime.locking.idempotency import (
    MemoryIdempotencyRegistry,
    DBIdempotencyRegistry,
)
from src.workflow_runtime.locking.exceptions import IdempotencyRejectionError


class TestMemoryIdempotencyRegistry:
    """Tests for MemoryIdempotencyRegistry."""

    def test_check_new_key_returns_none(self, memory_idempotency_registry: MemoryIdempotencyRegistry) -> None:
        assert memory_idempotency_registry.check("new_key") is None

    def test_record_new_key(self, memory_idempotency_registry: MemoryIdempotencyRegistry) -> None:
        record = memory_idempotency_registry.record("key1", "run1", "completed")
        assert record.idempotency_key == "key1"
        assert record.pipeline_run_id == "run1"
        assert record.status == "completed"

    def test_record_duplicate_raises(self, memory_idempotency_registry: MemoryIdempotencyRegistry) -> None:
        memory_idempotency_registry.record("key1", "run1", "completed")
        with pytest.raises(IdempotencyRejectionError):
            memory_idempotency_registry.record("key1", "run2", "in_progress")

    def test_check_existing_key(self, memory_idempotency_registry: MemoryIdempotencyRegistry) -> None:
        memory_idempotency_registry.record("key1", "run1", "completed")
        record = memory_idempotency_registry.check("key1")
        assert record is not None
        assert record.status == "completed"

    def test_cleanup_removes_old_keys(self, memory_idempotency_registry: MemoryIdempotencyRegistry) -> None:
        memory_idempotency_registry.record("old_key", "run1", "completed")
        # Set created_at to be old by overriding directly
        from datetime import datetime, timedelta
        import src.workflow_runtime.locking.models as models
        old_record = models.IdempotencyRecord(
            idempotency_key="old_key",
            pipeline_run_id="run1",
            status="completed",
            created_at=(datetime.utcnow() - timedelta(days=30)).isoformat(),
        )
        memory_idempotency_registry._records["old_key"] = old_record
        memory_idempotency_registry.record("new_key", "run2", "completed")

        count = memory_idempotency_registry.cleanup(ttl_days=7)
        assert count >= 1
        assert memory_idempotency_registry.check("old_key") is None
        assert memory_idempotency_registry.check("new_key") is not None

    def test_cleanup_no_expired(self, memory_idempotency_registry: MemoryIdempotencyRegistry) -> None:
        memory_idempotency_registry.record("key1", "run1", "completed")
        count = memory_idempotency_registry.cleanup(ttl_days=7)
        assert count == 0  # Key is recent


class TestDBIdempotencyRegistry:
    """Tests for DBIdempotencyRegistry."""

    def test_check_new_key_returns_none(self, db_idempotency_registry: DBIdempotencyRegistry) -> None:
        assert db_idempotency_registry.check("new_key") is None

    def test_record_new_key(self, db_idempotency_registry: DBIdempotencyRegistry) -> None:
        record = db_idempotency_registry.record("key1", "run1", "completed")
        assert record.idempotency_key == "key1"
        assert record.pipeline_run_id == "run1"

    def test_record_duplicate_raises(self, db_idempotency_registry: DBIdempotencyRegistry) -> None:
        db_idempotency_registry.record("key1", "run1", "completed")
        with pytest.raises(IdempotencyRejectionError):
            db_idempotency_registry.record("key1", "run2", "in_progress")

    def test_check_existing_key(self, db_idempotency_registry: DBIdempotencyRegistry) -> None:
        db_idempotency_registry.record("key1", "run1", "completed")
        record = db_idempotency_registry.check("key1")
        assert record is not None
        assert record.pipeline_run_id == "run1"