"""Concurrent execution protection integration tests.

Verifies that the locking infrastructure correctly serializes
concurrent executions of the same workflow while allowing
concurrent executions of different workflows.
"""

import threading
import time
from typing import Any, Dict, List, Optional, Tuple

import pytest

from src.core.execution.status import ExecutionStatus
from src.workflow_runtime.locking.execution_guard import (
    WorkflowExecutionGuard,
    LockAcquisitionError,
)
from src.workflow_runtime.locking.providers import MemoryLockProvider
from src.workflow_runtime.locking.models import LockAcquisition


class TestSameWorkflowConcurrent:
    """Verify same-workflow concurrent execution is blocked."""

    def test_concurrent_threads_same_workflow(self) -> None:
        """Two threads calling run() with same workflow_id — second blocked."""
        provider = MemoryLockProvider()
        guard = WorkflowExecutionGuard(
            lock_provider=provider,
            lease_duration_s=300,
            refresh_interval_s=30,
            max_retries=0,
        )

        results: List[str] = []
        errors: List[Exception] = []

        def run_worker(worker_id: str, expected: str) -> None:
            def work() -> str:
                time.sleep(0.05)
                return expected
            try:
                result, lock = guard.execute(
                    workflow_id="wf_concurrent",
                    holder_id=worker_id,
                    fn=work,
                )
                results.append(str(result))
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(
            target=run_worker, args=("thread-1", "first_done"), daemon=True
        )
        t2 = threading.Thread(
            target=run_worker, args=("thread-2", "second_done"), daemon=True
        )
        t1.start()
        t2.start()
        t1.join(timeout=5)
        t2.join(timeout=5)

        # One should succeed, one should fail with LockAcquisitionError
        successful = len([r for r in results if r])
        assert successful >= 1, "At least one thread should succeed"
        # At most one should succeed for same workflow_id
        assert (
            successful <= 1
        ), f"Expected at most 1 successful execution, got {successful}"

    def test_staggered_start_rejects_second(self) -> None:
        """Start run A, wait 100ms, start run B — B rejected."""
        provider = MemoryLockProvider()
        guard = WorkflowExecutionGuard(
            lock_provider=provider,
            lease_duration_s=300,
            refresh_interval_s=30,
            max_retries=0,
        )

        first_completed = threading.Event()

        def run_first() -> None:
            guard.execute(
                workflow_id="wf_staggered",
                holder_id="thread-a",
                fn=lambda: (
                    time.sleep(0.2) or "first_done"
                ),
            )
            first_completed.set()

        t1 = threading.Thread(target=run_first, daemon=True)
        t1.start()
        time.sleep(0.05)  # Ensure first acquires lock

        # Second should be rejected
        with pytest.raises(LockAcquisitionError):
            guard.execute(
                workflow_id="wf_staggered",
                holder_id="thread-b",
                fn=lambda: "second_done",
            )

        first_completed.wait(timeout=3)

    def test_lock_released_after_sequential_execution(self) -> None:
        """Execute same workflow sequentially — second should succeed."""
        provider = MemoryLockProvider()
        guard = WorkflowExecutionGuard(
            lock_provider=provider,
            lease_duration_s=300,
            refresh_interval_s=30,
            max_retries=0,
        )

        # First execution
        result1, lock1 = guard.execute(
            workflow_id="wf_sequential",
            holder_id="first",
            fn=lambda: "run_1",
        )
        assert result1 == "run_1"
        assert lock1 is not None

        # Second execution — lock should be released after first
        result2, lock2 = guard.execute(
            workflow_id="wf_sequential",
            holder_id="second",
            fn=lambda: "run_2",
        )
        assert result2 == "run_2"
        assert lock2 is not None


class TestDifferentWorkflowsConcurrent:
    """Verify different-workflow concurrent execution is allowed."""

    def test_two_different_workflows(self) -> None:
        """Two different workflow IDs should both succeed."""
        provider = MemoryLockProvider()
        guard = WorkflowExecutionGuard(
            lock_provider=provider,
            lease_duration_s=300,
            refresh_interval_s=30,
            max_retries=0,
        )

        results: Dict[str, str] = {}

        def run_wf_a() -> None:
            r, _ = guard.execute(
                workflow_id="wf_a",
                holder_id="thread-a",
                fn=lambda: "result_a",
            )
            results["a"] = str(r)

        def run_wf_b() -> None:
            r, _ = guard.execute(
                workflow_id="wf_b",
                holder_id="thread-b",
                fn=lambda: "result_b",
            )
            results["b"] = str(r)

        t1 = threading.Thread(target=run_wf_a, daemon=True)
        t2 = threading.Thread(target=run_wf_b, daemon=True)
        t1.start()
        t2.start()
        t1.join(timeout=5)
        t2.join(timeout=5)

        assert results.get("a") == "result_a"
        assert results.get("b") == "result_b"

    def test_ten_different_workflows(self) -> None:
        """10 different workflow IDs should all execute successfully."""
        provider = MemoryLockProvider()
        guard = WorkflowExecutionGuard(
            lock_provider=provider,
            lease_duration_s=300,
            refresh_interval_s=30,
            max_retries=0,
        )

        results: Dict[str, str] = {}
        errors: List[str] = []
        rlock = threading.Lock()

        def run_wf(wf_id: str, expected: str) -> None:
            try:
                r, _ = guard.execute(
                    workflow_id=wf_id,
                    holder_id=f"thread-{wf_id}",
                    fn=lambda e=expected: e,
                )
                with rlock:
                    results[wf_id] = str(r)
            except Exception as e:
                with rlock:
                    errors.append(f"{wf_id}: {e}")

        threads = []
        for i in range(10):
            wf_id = f"wf_multi_{i}"
            t = threading.Thread(
                target=run_wf, args=(wf_id, f"result_{i}"), daemon=True
            )
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert len(errors) == 0, f"Unexpected errors: {errors}"
        assert len(results) == 10, (
            f"Expected 10 results, got {len(results)}"
        )
        for i in range(10):
            assert results[f"wf_multi_{i}"] == f"result_{i}"


class TestScheduledManualOverlap:
    """Verify scheduled + manual trigger overlap is handled."""

    def test_manual_while_scheduled_in_progress(self) -> None:
        """Manual trigger while scheduled run is in progress — manual blocked."""
        provider = MemoryLockProvider()
        guard = WorkflowExecutionGuard(
            lock_provider=provider,
            lease_duration_s=300,
            refresh_interval_s=30,
            max_retries=0,
        )

        scheduled_completed = threading.Event()

        def scheduled_run() -> str:
            time.sleep(0.15)
            return "scheduled_done"

        def manual_run() -> None:
            # Try to execute while scheduled is still running
            with pytest.raises(LockAcquisitionError):
                guard.execute(
                    workflow_id="wf_overlap",
                    holder_id="manual-trigger",
                    fn=lambda: "manual_done",
                )
            scheduled_completed.set()

        # Start scheduled run
        t_scheduled = threading.Thread(
            target=lambda: guard.execute(
                workflow_id="wf_overlap",
                holder_id="scheduler",
                fn=scheduled_run,
            ),
            daemon=True,
        )
        t_scheduled.start()

        # Let scheduled acquire lock, then try manual
        time.sleep(0.05)
        t_manual = threading.Thread(target=manual_run, daemon=True)
        t_manual.start()

        scheduled_completed.wait(timeout=3)
        t_scheduled.join(timeout=3)
        t_manual.join(timeout=3)

    def test_lock_released_for_next_scheduled_slot(self) -> None:
        """A completed scheduled run releases lock for next slot."""
        provider = MemoryLockProvider()
        guard = WorkflowExecutionGuard(
            lock_provider=provider,
            lease_duration_s=300,
            refresh_interval_s=30,
            max_retries=0,
        )

        # First scheduled execution
        r1, l1 = guard.execute(
            workflow_id="wf_slot",
            holder_id="slot-1",
            fn=lambda: "slot_1_complete",
        )
        assert r1 == "slot_1_complete"
        assert l1 is not None

        # Second scheduled execution — different holder, should succeed
        r2, l2 = guard.execute(
            workflow_id="wf_slot",
            holder_id="slot-2",
            fn=lambda: "slot_2_complete",
        )
        assert r2 == "slot_2_complete"
        assert l2 is not None