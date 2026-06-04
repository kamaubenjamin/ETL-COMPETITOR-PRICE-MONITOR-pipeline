"""Unit tests for LockProviderRegistry."""

import pytest

from src.workflow_runtime.locking.providers import MemoryLockProvider, FileLockProvider, DBLockProvider
from src.workflow_runtime.locking.lock_provider import LockProviderRegistry
from src.workflow_runtime.locking.exceptions import LockProviderError


class TestLockProviderRegistry:
    """Tests for LockProviderRegistry."""

    def test_resolve_by_name(self, registry_with_all_providers: LockProviderRegistry) -> None:
        provider = registry_with_all_providers.resolve("database")
        assert provider.name == "database"

    def test_resolve_default_returns_highest_priority(self, registry_with_all_providers: LockProviderRegistry) -> None:
        provider = registry_with_all_providers.resolve()
        assert provider.name == "database"  # Priority 0

    def test_resolve_nonexistent_raises(self, registry_with_all_providers: LockProviderRegistry) -> None:
        with pytest.raises(LockProviderError):
            registry_with_all_providers.resolve("nonexistent")

    def test_resolve_empty_registry_raises(self) -> None:
        registry = LockProviderRegistry()
        with pytest.raises(LockProviderError):
            registry.resolve()

    def test_register_updates_provider(self) -> None:
        registry = LockProviderRegistry()
        mem = MemoryLockProvider()
        registry.register(mem, 10)
        resolved = registry.resolve("memory")
        assert resolved is mem

    def test_available_providers(self, registry_with_all_providers: LockProviderRegistry) -> None:
        providers = registry_with_all_providers.available_providers
        assert set(providers) == {"database", "file", "memory"}