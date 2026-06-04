"""Unit tests for DBLockProvider."""

import pytest

from src.workflow_runtime.locking.models import LockAcquisition
from src.workflow_runtime.locking.providers import DBLockProvider


class TestDBLockProvider:
    """Tests for DBLockProvider."""

    def test_acquire_returns_lock_when_free(self, db_lock_provider: DBLockProvider) -> None:
        lock = db_lock_provider.acquire("wf1", "holder-1", 300)
        assert lock is not None
        assert lock.lock_id == "wf1"
        assert lock.holder_id == "holder-1"

    def test_acquire_returns_none_when_held(self, db_lock_provider: DBLockProvider) -> None:
        db_lock_provider.acquire("wf1", "holder-1", 300)
        lock = db_lock_provider.acquire("wf1", "holder-2", 300)
        assert lock is None

    def test_acquire_different_ids(self, db_lock_provider: DBLockProvider) -> None:
        lock1 = db_lock_provider.acquire("wf1", "h1", 300)
        lock2 = db_lock_provider.acquire("wf2", "h2", 300)
        assert lock1 is not None
        assert lock2 is not None

    def test_release_held_lock(self, db_lock_provider: DBLockProvider) -> None:
        lock = db_lock_provider.acquire("wf1", "holder-1", 300)
        assert lock is not None
        result = db_lock_provider.release(lock)
        assert result is True

    def test_release_already_released(self, db_lock_provider: DBLockProvider) -> None:
        lock = db_lock_provider.acquire("wf1", "holder-1", 300)
        assert lock is not None
        db_lock_provider.release(lock)
        result = db_lock_provider.release(lock)
        assert result is False  # DB returns rowcount=0 for already-deleted

    def test_release_others_lock(self, db_lock_provider: DBLockProvider) -> None:
        lock = db_lock_provider.acquire("wf1", "holder-1", 300)
        assert lock is not None
        other = LockAcquisition("wf1", "holder-2", "", "", 300)
        result = db_lock_provider.release(other)
        assert result is False

    def test_refresh_before_expiry(self, db_lock_provider: DBLockProvider) -> None:
        lock = db_lock_provider.acquire("wf1", "holder-1", 300)
        assert lock is not None
        import time; time.sleep(0.01)
        updated = db_lock_provider.refresh(lock)
        assert updated is not None
        assert updated.expires_at >= lock.expires_at

    def test_refresh_others_lock(self, db_lock_provider: DBLockProvider) -> None:
        db_lock_provider.acquire("wf1", "holder-1", 300)
        other = LockAcquisition("wf1", "holder-2", "", "", 300)
        updated = db_lock_provider.refresh(other)
        assert updated is None

    def test_cleanup_stale_removes_expired(self, db_lock_provider: DBLockProvider, db_connection) -> None:
        # Insert an expired lock directly into the DB
        import sqlite3
        cursor = db_connection.cursor()
        cursor.execute("""
            INSERT INTO workflow_locks (lock_id, holder_id, expires_at, hostname)
            VALUES (?, ?, datetime('now', '-1 day'), 'test')
        """, ("expired_lock", "old_holder"))
        db_connection.commit()

        # Insert a valid active lock
        db_lock_provider.acquire("wf2", "holder-2", 300)

        count = db_lock_provider.cleanup_stale()
        assert count >= 1

    def test_sql_injection_safe(self, db_lock_provider: DBLockProvider) -> None:
        lock = db_lock_provider.acquire("DROP TABLE workflow_locks", "h1", 300)
        assert lock is not None
        # Table should still exist
        result = db_lock_provider.acquire("wf2", "h2", 300)
        assert result is not None