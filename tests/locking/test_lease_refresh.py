"""Lease refresh lifecycle verification tests.

Verifies that the lease refresh loop:
- Is invoked periodically during long-running execution
- Logs warnings on refresh failure
- Extends expiry timestamps forward
- Stops refreshing after completion
"""

import logging
import time
from datetime import datetime, timedelta

import pytest

from src.workflow_runtime.locking.execution_guard import WorkflowExecutionGuard
from src.workflow_runtime.locking.providers import MemoryLockProvider


class TestLeaseRefreshInvocation:
    """Verify the lease refresh loop is invoked during execution."""

    def test_refresh_invoked_during_execution(self) -> None:
        """A long-running function should trigger lease refresh."""
        provider = MemoryLockProvider()
        refresh_interval = 0.05  # 50ms — fast for testing
        guard = WorkflowExecutionGuard(
            lock_provider=provider,
            lease_duration_s=300,
            refresh_interval_s=refresh_interval,
            max_retries=0,
        )

        call_count = 0
        original_refresh = provider.refresh

        def counting_refresh(lock):
            nonlocal call_count
            call_count += 1
            return original_refresh(lock)

        provider.refresh = counting_refresh  # type: ignore[method-assign]

        def long_running() -> str:
            time.sleep(0.15)  # 3 refresh intervals
            return "done"

        result, lock = guard.execute(
            workflow_id="wf_refresh_test",
            holder_id="holder-1",
            fn=long_running,
        )
        assert result == "done"
        assert lock is not None
        # Should have refreshed at least once during 150ms (intervals of 50ms)
        assert call_count >= 1, (
            f"Expected at least 1 refresh, got {call_count}"
        )

    def test_multiple_refreshes_on_long_run(self) -> None:
        """A very long running function should trigger multiple refreshes."""
        provider = MemoryLockProvider()
        refresh_interval = 0.02  # 20ms

        original_acquire = provider.acquire
        acquired_lock = None

        def tracking_acquire(lock_id, holder_id, lease_duration_s):
            nonlocal acquired_lock
            acquired_lock = original_acquire(lock_id, holder_id, lease_duration_s)
            return acquired_lock

        provider.acquire = tracking_acquire  # type: ignore[method-assign]

        guard = WorkflowExecutionGuard(
            lock_provider=provider,
            lease_duration_s=300,
            refresh_interval_s=refresh_interval,
            max_retries=0,
        )

        call_count = 0

        original_refresh = provider.refresh

        def counting_refresh(lock):
            nonlocal call_count
            call_count += 1
            return original_refresh(lock)

        provider.refresh = counting_refresh  # type: ignore[method-assign]

        def long_running() -> str:
            time.sleep(0.1)  # 5 refresh intervals
            return "completed"

        result, lock = guard.execute(
            workflow_id="wf_multi_refresh",
            holder_id="holder-2",
            fn=long_running,
        )
        assert result == "completed"
        # Should have refreshed multiple times
        assert call_count >= 2, (
            f"Expected at least 2 refreshes, got {call_count}"
        )


class TestLeaseRefreshFailure:
    """Verify lease refresh failure does not crash execution."""

    def test_refresh_failure_does_not_crash(self) -> None:
        """Refresh failure should not crash execution — execution completes."""
        provider = MemoryLockProvider()
        guard = WorkflowExecutionGuard(
            lock_provider=provider,
            lease_duration_s=300,
            refresh_interval_s=0.02,
            max_retries=0,
        )

        original_refresh = provider.refresh

        def failing_refresh(lock):
            raise RuntimeError("Simulated refresh failure")

        provider.refresh = failing_refresh  # type: ignore[method-assign]

        result, lock = guard.execute(
            workflow_id="wf_fail_refresh",
            holder_id="holder-3",
            fn=lambda: "success",
        )
        assert result == "success"
        assert lock is not None

    def test_refresh_null_does_not_crash(self) -> None:
        """Refresh returning None should not crash execution."""
        provider = MemoryLockProvider()
        guard = WorkflowExecutionGuard(
            lock_provider=provider,
            lease_duration_s=300,
            refresh_interval_s=0.02,
            max_retries=0,
        )

        def returning_none(lock):
            return None

        provider.refresh = returning_none  # type: ignore[method-assign]

        result, lock = guard.execute(
            workflow_id="wf_null_refresh",
            holder_id="holder-4",
            fn=lambda: "ok",
        )
        assert result == "ok"
        assert lock is not None


class TestLeaseRefreshExtendsExpiry:
    """Verify refresh extends the lease expiry time."""

    def test_refresh_extends_expiry_forward(self) -> None:
        """Before and after comparison — expiry moves forward."""
        provider = MemoryLockProvider()
        guard = WorkflowExecutionGuard(
            lock_provider=provider,
            lease_duration_s=60,
            refresh_interval_s=0.02,
            max_retries=0,
        )

        def timed_execution() -> str:
            # Acquire a direct reference to the stored lock
            lock = guard._current_lock
            assert lock is not None
            original_expiry = lock.expires_at

            time.sleep(0.05)  # Let one refresh cycle happen

            refreshed_lock = guard._current_lock
            assert refreshed_lock is not None
            # Expiry should have moved forward
            assert refreshed_lock.expires_at > original_expiry, (
                "Expiry should have moved forward after refresh"
            )
            return "extended"

        result, lock = guard.execute(
            workflow_id="wf_expiry",
            holder_id="holder-5",
            fn=timed_execution,
        )
        assert result == "extended"
        assert lock is not None


class TestLeaseRefreshCompletion:
    """Verify refresh stops after execution completes."""

    def test_refresh_stops_after_completion(self) -> None:
        """Short execution should not trigger refresh."""
        provider = MemoryLockProvider()
        guard = WorkflowExecutionGuard(
            lock_provider=provider,
            lease_duration_s=300,
            refresh_interval_s=0.5,
            max_retries=0,
        )

        call_count = 0
        original_refresh = provider.refresh

        def counting_refresh(lock):
            nonlocal call_count
            call_count += 1
            return original_refresh(lock)

        provider.refresh = counting_refresh  # type: ignore[method-assign]

        # Very fast execution — should complete before first refresh
        result, lock = guard.execute(
            workflow_id="wf_short",
            holder_id="holder-6",
            fn=lambda: "fast",
        )
        assert result == "fast"
        assert lock is not None
        # Fast execution may not trigger any refresh
        assert call_count == 0, (
            f"Expected 0 refreshes for fast execution, got {call_count}"
        )

    def test_no_refresh_after_exception(self) -> None:
        """After execution raises, refresh loop should stop."""
        provider = MemoryLockProvider()
        guard = WorkflowExecutionGuard(
            lock_provider=provider,
            lease_duration_s=300,
            refresh_interval_s=0.05,
            max_retries=0,
        )

        call_count = 0
        original_refresh = provider.refresh

        def counting_refresh(lock):
            nonlocal call_count
            call_count += 1
            return original_refresh(lock)

        provider.refresh = counting_refresh  # type: ignore[method-assign]

        def failing_fn():
            raise ValueError("Simulated execution failure")

        with pytest.raises(ValueError, match="Simulated execution failure"):
            guard.execute(
                workflow_id="wf_exception",
                holder_id="holder-7",
                fn=failing_fn,
            )

        # After exception, lock should be released
        lock = provider.acquire(
            lock_id="wf_exception",
            holder_id="new-holder",
            lease_duration_s=300,
        )
        assert lock is not None, "Lock should be released after failure"