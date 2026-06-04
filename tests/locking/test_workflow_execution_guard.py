"""Unit tests for WorkflowExecutionGuard."""

import pytest

from src.workflow_runtime.locking.execution_guard import WorkflowExecutionGuard
from src.workflow_runtime.locking.exceptions import LockAcquisitionError
from src.workflow_runtime.locking.providers import MemoryLockProvider
from src.workflow_runtime.locking.idempotency import MemoryIdempotencyRegistry


class TestWorkflowExecutionGuard:
    """Tests for WorkflowExecutionGuard."""

    def test_execute_success(self, execution_guard: WorkflowExecutionGuard) -> None:
        result, lock = execution_guard.execute(
            workflow_id="wf1",
            holder_id="holder-1",
            fn=lambda: "done",
        )
        assert result == "done"
        assert lock is not None
        assert lock.lock_id == "wf1"

    def test_execute_rejects_duplicate(self, execution_guard: WorkflowExecutionGuard) -> None:
        import threading
        lock_held = threading.Event()
        proceed = threading.Event()

        def long_running_fn():
            lock_held.set()
            proceed.wait(timeout=5)
            return "done"

        # Start first execution in a thread
        results = {}
        def run_first():
            r, l = execution_guard.execute(
                workflow_id="wf1",
                holder_id="holder-1",
                fn=long_running_fn,
            )
            results["r"] = r

        t = threading.Thread(target=run_first, daemon=True)
        t.start()

        # Wait for first to acquire lock and start executing
        lock_held.wait(timeout=5)

        # Second execution should fail
        with pytest.raises(LockAcquisitionError):
            execution_guard.execute(
                workflow_id="wf1",
                holder_id="holder-2",
                fn=lambda: "done",
            )

        # Let first finish
        proceed.set()
        t.join(timeout=5)

    def test_execute_different_workflows(self, execution_guard: WorkflowExecutionGuard) -> None:
        r1, _ = execution_guard.execute("wf1", "h1", lambda: "r1")
        r2, _ = execution_guard.execute("wf2", "h2", lambda: "r2")
        assert r1 == "r1"
        assert r2 == "r2"

    def test_execute_with_idempotency_skips_completed(
        self,
        execution_guard_with_idempotency: WorkflowExecutionGuard,
    ) -> None:
        """If idempotency key is completed, execution should be skipped."""
        guard = execution_guard_with_idempotency

        # First execution completes normally
        result, lock = guard.execute(
            workflow_id="wf1",
            holder_id="h1",
            fn=lambda: "done",
            idempotency_key="wf1-scheduled-2026-06-03T08:00",
        )
        assert result == "done"
        assert lock is not None

        # Second execution with same key — should skip
        result, lock = guard.execute(
            workflow_id="wf1",
            holder_id="h2",
            fn=lambda: "should_not_run",
            idempotency_key="wf1-scheduled-2026-06-03T08:00",
        )
        assert result is None  # Skipped
        assert lock is None  # No lock acquired

    def test_execute_releases_lock_on_failure(self, execution_guard: WorkflowExecutionGuard) -> None:
        """If the function raises, the lock should be released."""
        with pytest.raises(RuntimeError):
            execution_guard.execute(
                workflow_id="wf1",
                holder_id="h1",
                fn=lambda: (_ for _ in ()).throw(RuntimeError("fail")),
            )

        # Lock should be released — another holder can acquire
        result, lock = execution_guard.execute(
            workflow_id="wf1",
            holder_id="h2",
            fn=lambda: "recovered",
        )
        assert result == "recovered"
        assert lock is not None

    def test_execute_function_exception_propagates(self, execution_guard: WorkflowExecutionGuard) -> None:
        """Exceptions from the wrapped function should propagate."""
        with pytest.raises(ValueError, match="test error"):
            execution_guard.execute(
                workflow_id="wf1",
                holder_id="h1",
                fn=lambda: (_ for _ in ()).throw(ValueError("test error")),
            )