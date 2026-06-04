"""Unit tests for FileLockProvider."""

import json
from datetime import datetime, timedelta

import pytest

from src.workflow_runtime.locking.models import LockAcquisition
from src.workflow_runtime.locking.providers import FileLockProvider


class TestFileLockProvider:
    """Tests for FileLockProvider."""

    def test_acquire_returns_lock_when_free(self, file_lock_provider: FileLockProvider, temp_lock_dir) -> None:
        lock = file_lock_provider.acquire("wf1", "holder-1", 300)
        assert lock is not None
        assert lock.lock_id == "wf1"
        lock_file = temp_lock_dir / "wf1.lock"
        assert lock_file.exists()

    def test_acquire_returns_none_when_held(self, file_lock_provider: FileLockProvider) -> None:
        file_lock_provider.acquire("wf1", "holder-1", 300)
        lock = file_lock_provider.acquire("wf1", "holder-2", 300)
        assert lock is None

    def test_acquire_different_ids(self, file_lock_provider: FileLockProvider) -> None:
        lock1 = file_lock_provider.acquire("wf1", "h1", 300)
        lock2 = file_lock_provider.acquire("wf2", "h2", 300)
        assert lock1 is not None
        assert lock2 is not None

    def test_acquire_stale_lock(self, file_lock_provider: FileLockProvider, temp_lock_dir) -> None:
        file_lock_provider.acquire("wf1", "holder-1", -1)
        lock = file_lock_provider.acquire("wf1", "holder-2", 300)
        assert lock is not None
        assert lock.holder_id == "holder-2"

    def test_release_held_lock(self, file_lock_provider: FileLockProvider, temp_lock_dir) -> None:
        lock = file_lock_provider.acquire("wf1", "holder-1", 300)
        assert lock is not None
        result = file_lock_provider.release(lock)
        assert result is True
        lock_file = temp_lock_dir / "wf1.lock"
        assert not lock_file.exists()

    def test_release_already_released(self, file_lock_provider: FileLockProvider) -> None:
        lock = file_lock_provider.acquire("wf1", "holder-1", 300)
        assert lock is not None
        file_lock_provider.release(lock)
        result = file_lock_provider.release(lock)
        assert result is True

    def test_release_others_lock(self, file_lock_provider: FileLockProvider) -> None:
        lock = file_lock_provider.acquire("wf1", "holder-1", 300)
        assert lock is not None
        other = LockAcquisition("wf1", "holder-2", "", "", 300)
        result = file_lock_provider.release(other)
        assert result is False

    def test_refresh_before_expiry(self, file_lock_provider: FileLockProvider) -> None:
        lock = file_lock_provider.acquire("wf1", "holder-1", 300)
        assert lock is not None
        updated = file_lock_provider.refresh(lock)
        assert updated is not None
        assert updated.expires_at > lock.expires_at

    def test_refresh_others_lock(self, file_lock_provider: FileLockProvider) -> None:
        file_lock_provider.acquire("wf1", "holder-1", 300)
        other = LockAcquisition("wf1", "holder-2", "", "", 300)
        updated = file_lock_provider.refresh(other)
        assert updated is None

    def test_lock_file_metadata(self, file_lock_provider: FileLockProvider, temp_lock_dir) -> None:
        lock = file_lock_provider.acquire("wf1", "holder-1", 300)
        assert lock is not None
        lock_file = temp_lock_dir / "wf1.lock"
        with open(lock_file) as f:
            metadata = json.load(f)
        assert metadata["lock_id"] == "wf1"
        assert metadata["holder_id"] == "holder-1"
        assert "hostname" in metadata
        assert "pid" in metadata