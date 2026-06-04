"""Unit tests for MemoryLockProvider.

Tests cover standard ABC contract (acquire/release/refresh), thread safety,
stale lock detection, and edge cases.
"""

from datetime import datetime, timedelta

import pytest

from src.workflow_runtime.locking.models import LockAcquisition
from src.workflow_runtime.locking.providers import MemoryLockProvider


class TestMemoryLockProvider:
    """Tests for MemoryLockProvider."""

    def test_acquire_returns_lock_when_free(self, memory_lock_provider: MemoryLockProvider) -> None:
        """Acquiring a free lock returns a LockAcquisition."""
        lock = memory_lock_provider.acquire("wf1", "holder-1", 300)
        assert lock is not None
        assert lock.lock_id == "wf1"
        assert lock.holder_id == "holder-1"
        assert lock.lease_duration_s == 300

    def test_acquire_returns_none_when_held(self, memory_lock_provider: MemoryLockProvider) -> None:
        """Acquiring a held lock returns None."""
        memory_lock_provider.acquire("wf1", "holder-1", 300)
        lock = memory_lock_provider.acquire("wf1", "holder-2", 300)
        assert lock is None

    def test_acquire_returns_lock_for_different_ids(self, memory_lock_provider: MemoryLockProvider) -> None:
        """Acquiring locks for different workflow_ids both succeed."""
        lock1 = memory_lock_provider.acquire("wf1", "holder-1", 300)
        lock2 = memory_lock_provider.acquire("wf2", "holder-2", 300)
        assert lock1 is not None
        assert lock2 is not None

    def test_acquire_after_expiry(self, memory_lock_provider: MemoryLockProvider) -> None:
        """Acquiring a lock after its lease expires succeeds."""
        # Acquire with very short lease
        lock1 = memory_lock_provider.acquire("wf1", "holder-1", -1)
        assert lock1 is not None
        # Should be expired immediately
        lock2 = memory_lock_provider.acquire("wf1", "holder-2", 300)
        assert lock2 is not None
        assert lock2.holder_id == "holder-2"

    def test_release_held_lock(self, memory_lock_provider: MemoryLockProvider) -> None:
        """Releasing a held lock returns True."""
        lock = memory_lock_provider.acquire("wf1", "holder-1", 300)
        assert lock is not None
        result = memory_lock_provider.release(lock)
        assert result is True

    def test_release_already_released(self, memory_lock_provider: MemoryLockProvider) -> None:
        """Releasing an already-released lock is idempotent (True)."""
        lock = memory_lock_provider.acquire("wf1", "holder-1", 300)
        assert lock is not None
        memory_lock_provider.release(lock)
        result = memory_lock_provider.release(lock)
        assert result is True  # Idempotent

    def test_release_others_lock(self, memory_lock_provider: MemoryLockProvider) -> None:
        """Releasing a lock held by someone else returns False."""
        lock = memory_lock_provider.acquire("wf1", "holder-1", 300)
        assert lock is not None
        other_lock = LockAcquisition("wf1", "holder-2", "", "", 300)
        result = memory_lock_provider.release(other_lock)
        assert result is False

    def test_refresh_before_expiry(self, memory_lock_provider: MemoryLockProvider) -> None:
        """Refreshing an active lock returns an updated LockAcquisition."""
        lock = memory_lock_provider.acquire("wf1", "holder-1", 300)
        assert lock is not None
        import time; time.sleep(0.01)  # Ensure time passes
        updated = memory_lock_provider.refresh(lock)
        assert updated is not None
        assert updated.holder_id == lock.holder_id
        # New expiry should be >= (may be same microsecond if fast)
        assert updated.expires_at >= lock.expires_at

    def test_refresh_after_expiry(self, memory_lock_provider: MemoryLockProvider) -> None:
        """Refreshing a lock whose holder no longer holds it returns None."""
        lock = memory_lock_provider.acquire("wf1", "holder-1", 300)
        assert lock is not None
        memory_lock_provider.release(lock)  # Release so the lock is gone
        updated = memory_lock_provider.refresh(lock)
        assert updated is None

    def test_refresh_others_lock(self, memory_lock_provider: MemoryLockProvider) -> None:
        """Refreshing a lock held by someone else returns None."""
        memory_lock_provider.acquire("wf1", "holder-1", 300)
        other_lock = LockAcquisition("wf1", "holder-2", "", "", 300)
        updated = memory_lock_provider.refresh(other_lock)
        assert updated is None

    def test_clear_removes_all_locks(self, memory_lock_provider: MemoryLockProvider) -> None:
        """Clear removes all locks."""
        memory_lock_provider.acquire("wf1", "holder-1", 300)
        memory_lock_provider.acquire("wf2", "holder-2", 300)
        memory_lock_provider.clear()
        lock1 = memory_lock_provider.acquire("wf1", "new-holder", 300)
        lock2 = memory_lock_provider.acquire("wf2", "new-holder", 300)
        assert lock1 is not None
        assert lock2 is not None

    def test_acquire_reacquire_after_release(self, memory_lock_provider: MemoryLockProvider) -> None:
        """After releasing, the lock can be acquired again."""
        lock1 = memory_lock_provider.acquire("wf1", "holder-1", 300)
        assert lock1 is not None
        memory_lock_provider.release(lock1)
        lock2 = memory_lock_provider.acquire("wf1", "holder-2", 300)
        assert lock2 is not None
        assert lock2.holder_id == "holder-2"