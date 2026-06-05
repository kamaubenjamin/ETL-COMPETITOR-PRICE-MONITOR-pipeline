"""Idempotency behavior verification tests.

Verifies that:
- Basic deduplication works (completed key skips execution)
- Idempotency with lock (key exists + lock free = skip, no lock acquire)
- Concurrent idempotency (same key, simultaneous = only one executes)
- Idempotency TTL (expired keys are cleaned up)
- Repeated execution with different keys executes each time
- In-progress keys do not skip execution
- Failed keys can be retried
"""

import threading
import time
from datetime import datetime, timedelta

import pytest

from src.workflow_runtime.locking.execution_guard import (
    WorkflowExecutionGuard,
    LockAcquisitionError,
    IdempotencyRejectionError,
)
from src.workflow_runtime.locking.providers import MemoryLockProvider
from src.workflow_runtime.locking.idempotency import (
    MemoryIdempotencyRegistry,
    DBIdempotencyRegistry,
)
from src.workflow_runtime.locking.models import IdempotencyRecord


class TestBasicDeduplication:
    """Verify basic idempotency key deduplication."""

    def test_completed_key_skips_execution(self) -> None:
        """A completed idempotency key should skip execution."""
        provider = MemoryLockProvider()
        registry = MemoryIdempotencyRegistry()
        guard = WorkflowExecutionGuard(
            lock_provider=provider,
            idempotency_registry=registry,
            lease_duration_s=300,
            refresh_interval_s=30,
        )

        key = "wf_dedup-scheduled-2026-06-04T08:00"
        executed = []

        result1, lock1 = guard.execute(
            workflow_id="wf_dedup",
            holder_id="first-run",
            fn=lambda: (executed.append("ran") or "result_1"),
            idempotency_key=key,
        )
        assert result1 == "result_1"
        assert lock1 is not None

        # Second execution with same key — should skip
        result2, lock2 = guard.execute(
            workflow_id="wf_dedup",
            holder_id="second-run",
            fn=lambda: (executed.append("ran") or "result_2"),
            idempotency_key=key,
        )
        assert result2 is None  # Skipped — no result
        assert lock2 is None  # No lock acquired
        assert len(executed) == 1, (
            "Function should have been executed only once"
        )

    def test_different_keys_execute_each_time(self) -> None:
        """Different idempotency keys should each execute."""
        provider = MemoryLockProvider()
        registry = MemoryIdempotencyRegistry()
        guard = WorkflowExecutionGuard(
            lock_provider=provider,
            idempotency_registry=registry,
            lease_duration_s=300,
            refresh_interval_s=30,
        )

        counter = {"count": 0}

        for i in range(5):
            key = f"wf_multi_keys-scheduled-2026-06-04T{8+i:02d}:00"
            result, lock = guard.execute(
                workflow_id="wf_multi_keys",
                holder_id=f"run-{i}",
                fn=lambda c=counter: (
                    c.__setitem__("count", c["count"] + 1) or f"result_{c['count']}"
                ),
                idempotency_key=key,
            )
            assert result is not None
            assert lock is not None

        assert counter["count"] == 5


class TestIdempotencyWithLock:
    """Verify idempotency with lock — completed key skips even if lock free."""

    def test_skip_does_not_acquire_lock(self) -> None:
        """When key is completed, no lock should be acquired."""
        provider = MemoryLockProvider()
        registry = MemoryIdempotencyRegistry()
        guard = WorkflowExecutionGuard(
            lock_provider=provider,
            idempotency_registry=registry,
            lease_duration_s=300,
            refresh_interval_s=30,
        )

        key = "wf_skip_lock-scheduled-2026-06-04T08:00"

        # First run — completes normally
        guard.execute(
            workflow_id="wf_skip_lock",
            holder_id="first",
            fn=lambda: "done",
            idempotency_key=key,
        )

        # Second run — should skip without acquiring lock
        result, lock = guard.execute(
            workflow_id="wf_skip_lock",
            holder_id="second",
            fn=lambda: "should_not_run",
            idempotency_key=key,
        )
        assert result is None  # No execution result
        assert lock is None  # No lock acquired

        # Verify lock is free (can acquire separately)
        new_lock = provider.acquire(
            lock_id="wf_skip_lock",
            holder_id="free-check",
            lease_duration_s=300,
        )
        assert new_lock is not None, "Lock should be free when execution skipped"

    def test_in_progress_does_not_skip(self) -> None:
        """An 'in_progress' key should NOT skip execution — execution proceeds."""
        provider = MemoryLockProvider()
        registry = MemoryIdempotencyRegistry()
        guard = WorkflowExecutionGuard(
            lock_provider=provider,
            idempotency_registry=registry,
            lease_duration_s=300,
            refresh_interval_s=30,
            max_retries=0,
        )

        key = "wf_in_progress-scheduled-2026-06-04T08:00"

        # Manually record an in_progress key
        registry.record(key=key, pipeline_run_id="other-run", status="in_progress")

        # Second run with same key — should NOT skip because status is in_progress
        # Execution should proceed (though lock is free, so it succeeds)
        execution_marker = []
        result, lock = guard.execute(
            workflow_id="wf_in_progress",
            holder_id="second",
            fn=lambda: (execution_marker.append("ran") or "executed"),
            idempotency_key=key,
        )
        assert result == "executed"
        assert lock is not None
        assert len(execution_marker) == 1, "Function should have been executed"

    def test_failed_key_can_retry(self) -> None:
        """A 'failed' idempotency key should allow retry."""
        provider = MemoryLockProvider()
        registry = MemoryIdempotencyRegistry()
        guard = WorkflowExecutionGuard(
            lock_provider=provider,
            idempotency_registry=registry,
            lease_duration_s=300,
            refresh_interval_s=30,
        )

        key = "wf_retry-scheduled-2026-06-04T08:00"

        # Run that fails
        with pytest.raises(ValueError):
            guard.execute(
                workflow_id="wf_retry",
                holder_id="fail-run",
                fn=lambda: (_ for _ in ()).throw(ValueError("Failed!")),
                idempotency_key=key,
            )

        # Retry should succeed (lock was released after failure)
        result, lock = guard.execute(
            workflow_id="wf_retry",
            holder_id="retry-run",
            fn=lambda: "retry_success",
            idempotency_key=key,
        )
        assert result == "retry_success"
        assert lock is not None


class TestConcurrentIdempotency:
    """Verify concurrent idempotency key handling."""

    def test_concurrent_same_key_only_one_executes(self) -> None:
        """Two simultaneous runs with same key — only one executes."""
        provider = MemoryLockProvider()
        registry = MemoryIdempotencyRegistry()
        guard = WorkflowExecutionGuard(
            lock_provider=provider,
            idempotency_registry=registry,
            lease_duration_s=300,
            refresh_interval_s=30,
            max_retries=0,
        )

        key = "wf_concurrent_idem-scheduled-2026-06-04T08:00"
        execution_count = {"count": 0}

        def work() -> str:
            execution_count["count"] += 1
            time.sleep(0.05)
            return "done"

        def run_guarded(result_list, error_list):
            try:
                r, l = guard.execute(
                    workflow_id="wf_concurrent_idem",
                    holder_id=threading.current_thread().name,
                    fn=work,
                    idempotency_key=key,
                )
                result_list.append((r, l))
            except Exception as e:
                error_list.append(e)

        results = []
        thread_errors = []

        t1 = threading.Thread(
            target=run_guarded, args=(results, thread_errors), daemon=True
        )
        t2 = threading.Thread(
            target=run_guarded, args=(results, thread_errors), daemon=True
        )

        t1.start()
        t2.start()
        t1.join(timeout=5)
        t2.join(timeout=5)

        # Only one should have executed
        assert execution_count["count"] == 1, (
            f"Expected 1 execution, got {execution_count['count']}"
        )

    def test_db_idempotency_atomic_insert(self) -> None:
        """DBIdempotencyRegistry should reject duplicate keys atomically."""
        import sqlite3
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.executescript("""
            CREATE TABLE workflow_idempotency (
                idempotency_key TEXT PRIMARY KEY,
                pipeline_run_id TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('completed', 'failed', 'in_progress')),
                created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
                completed_at TIMESTAMP,
                result_summary TEXT
            );
        """)
        registry = DBIdempotencyRegistry(conn)

        # First record
        rec = registry.record(
            key="atomic_key",
            pipeline_run_id="first",
            status="completed",
        )
        assert rec is not None

        # Second record should raise
        with pytest.raises(IdempotencyRejectionError):
            registry.record(
                key="atomic_key",
                pipeline_run_id="second",
                status="completed",
            )
        conn.close()


class TestIdempotencyTTL:
    """Verify idempotency key TTL cleanup."""

    def test_db_cleanup_removes_expired_keys(self) -> None:
        """DB cleanup should remove keys older than TTL."""
        import sqlite3
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.executescript("""
            CREATE TABLE workflow_idempotency (
                idempotency_key TEXT PRIMARY KEY,
                pipeline_run_id TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('completed', 'failed', 'in_progress')),
                created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
                completed_at TIMESTAMP,
                result_summary TEXT
            );
        """)
        registry = DBIdempotencyRegistry(conn)

        # Record a key with an old timestamp (simulated via raw insert)
        conn.execute("""
            INSERT INTO workflow_idempotency
                (idempotency_key, pipeline_run_id, status, created_at)
            VALUES (?, ?, ?, ?)
        """, (
            "old_key",
            "old_run",
            "completed",
            (datetime.utcnow() - timedelta(days=10)).isoformat(),
        ))
        conn.commit()

        # Record a key with a recent timestamp
        registry.record(
            key="new_key",
            pipeline_run_id="new_run",
            status="completed",
        )

        # Cleanup with TTL of 7 days — old key should be removed
        removed = registry.cleanup(ttl_days=7)
        assert removed >= 1, f"Expected at least 1 removed key, got {removed}"

        # Old key should be gone
        old = registry.check("old_key")
        assert old is None, "Old key should have been cleaned up"

        # New key should still exist
        new = registry.check("new_key")
        assert new is not None, "New key should still exist"
        conn.close()

    def test_db_cleanup_no_expired(self) -> None:
        """Cleanup with no expired keys returns 0."""
        import sqlite3
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.executescript("""
            CREATE TABLE workflow_idempotency (
                idempotency_key TEXT PRIMARY KEY,
                pipeline_run_id TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('completed', 'failed', 'in_progress')),
                created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
                completed_at TIMESTAMP,
                result_summary TEXT
            );
        """)
        registry = DBIdempotencyRegistry(conn)

        registry.record(
            key="fresh_key",
            pipeline_run_id="fresh_run",
            status="completed",
        )

        # Cleanup with very recent TTL — no keys should be removed
        removed = registry.cleanup(ttl_days=0)
        assert removed == 0, f"Expected 0 removed keys, got {removed}"
        conn.close()

    def test_memory_cleanup_removes_old_keys(self) -> None:
        """Memory registry cleanup should remove keys older than TTL."""
        registry = MemoryIdempotencyRegistry()

        # Record a key with timestamp override via raw data
        now = datetime.utcnow()
        registry._records["old_key"] = IdempotencyRecord(
            idempotency_key="old_key",
            pipeline_run_id="old_run",
            status="completed",
            created_at=(now - timedelta(days=10)).isoformat(),
        )

        registry.record(
            key="new_key",
            pipeline_run_id="new_run",
            status="completed",
        )

        removed = registry.cleanup(ttl_days=7)
        assert removed >= 1, f"Expected at least 1 removed key, got {removed}"

        assert "old_key" not in registry._records
        assert "new_key" in registry._records