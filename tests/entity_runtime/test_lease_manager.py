"""Tests for LeaseManager — acquire, refresh, expiry, recovery."""
from __future__ import annotations

import time

import pytest

from src.entity_runtime.concurrency.errors import EntityLeaseError
from src.entity_runtime.concurrency.leases import LeaseManager


class TestAcquire:
    """Lease acquisition tests."""

    def test_acquire_lease_when_free(self, lease_manager: LeaseManager):
        lease = lease_manager.acquire("supplier:doc-1:acme", "holder-1", lease_duration_s=5)
        assert lease.entity_version_key == "supplier:doc-1:acme"
        assert lease.holder_id == "holder-1"
        assert lease.lease_duration_s == 5

    def test_acquire_lease_fails_when_held(self, lease_manager: LeaseManager):
        lease_manager.acquire("supplier:doc-1:acme", "holder-1", lease_duration_s=5)
        with pytest.raises(EntityLeaseError):
            lease_manager.acquire("supplier:doc-1:acme", "holder-2", lease_duration_s=5)

    def test_acquire_after_release(self, lease_manager: LeaseManager):
        lease_manager.acquire("supplier:doc-1:acme", "holder-1", lease_duration_s=5)
        lease_manager.release("supplier:doc-1:acme", "holder-1")
        lease = lease_manager.acquire("supplier:doc-1:acme", "holder-2", lease_duration_s=5)
        assert lease.holder_id == "holder-2"


class TestRefresh:
    """Lease refresh tests."""

    def test_refresh_before_expiry(self, lease_manager: LeaseManager):
        lease_manager.acquire("supplier:doc-1:acme", "holder-1", lease_duration_s=10)
        assert lease_manager.refresh("supplier:doc-1:acme", "holder-1", lease_duration_s=10)

    def test_refresh_after_expiry(self, lease_manager: LeaseManager):
        lease_manager.acquire("supplier:doc-1:acme", "holder-1", lease_duration_s=1)
        time.sleep(1.1)
        assert not lease_manager.refresh("supplier:doc-1:acme", "holder-1", lease_duration_s=5)

    def test_refresh_others_lease(self, lease_manager: LeaseManager):
        lease_manager.acquire("supplier:doc-1:acme", "holder-1", lease_duration_s=10)
        assert not lease_manager.refresh("supplier:doc-1:acme", "holder-2", lease_duration_s=10)


class TestRelease:
    """Lease release tests."""

    def test_release_held_lease(self, lease_manager: LeaseManager):
        lease_manager.acquire("supplier:doc-1:acme", "holder-1", lease_duration_s=10)
        assert lease_manager.release("supplier:doc-1:acme", "holder-1")

    def test_release_others_lease(self, lease_manager: LeaseManager):
        lease_manager.acquire("supplier:doc-1:acme", "holder-1", lease_duration_s=10)
        assert not lease_manager.release("supplier:doc-1:acme", "holder-2")

    def test_double_release_idempotent(self, lease_manager: LeaseManager):
        lease_manager.acquire("supplier:doc-1:acme", "holder-1", lease_duration_s=10)
        assert lease_manager.release("supplier:doc-1:acme", "holder-1")
        assert not lease_manager.release("supplier:doc-1:acme", "holder-1")


class TestRecovery:
    """Crash recovery tests."""

    def test_recover_after_manual_expiry(self, lease_manager: LeaseManager):
        lease = lease_manager.acquire("supplier:doc-1:acme", "holder-1", lease_duration_s=5)
        # Release manually to simulate expired state
        lease_manager.release("supplier:doc-1:acme", "holder-1")
        # Now the lease is gone (no active lease = expired)
        assert lease_manager.is_expired("supplier:doc-1:acme")
        # Recover should work since no active lease exists
        new_lease = lease_manager.acquire("supplier:doc-1:acme", "holder-2", lease_duration_s=5)
        assert new_lease.holder_id == "holder-2"

    def test_recover_active_lease_raises(self, lease_manager: LeaseManager):
        lease_manager.acquire("supplier:doc-1:acme", "holder-1", lease_duration_s=10)
        with pytest.raises(EntityLeaseError):
            lease_manager.recover("supplier:doc-1:acme", "holder-2", lease_duration_s=5)


class TestHelpers:
    """Helper method tests."""

    def test_is_expired_no_lease(self, lease_manager: LeaseManager):
        assert lease_manager.is_expired("supplier:doc-1:nonexistent")

    def test_get_holder(self, lease_manager: LeaseManager):
        lease_manager.acquire("supplier:doc-1:acme", "holder-1", lease_duration_s=10)
        assert lease_manager.get_holder("supplier:doc-1:acme") == "holder-1"

    def test_get_holder_no_lease(self, lease_manager: LeaseManager):
        assert lease_manager.get_holder("supplier:doc-1:nonexistent") is None