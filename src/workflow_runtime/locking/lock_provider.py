"""Abstract base class for lock providers and the provider registry.

LockProvider Contract
=====================

All concrete lock providers must implement the three abstract methods
defined in ``LockProvider``:

- ``acquire(lock_id, holder_id, lease_duration_s) -> Optional[LockAcquisition]``
- ``release(lock: LockAcquisition) -> bool``
- ``refresh(lock: LockAcquisition) -> Optional[LockAcquisition]``

LockProviderRegistry
====================

Manages a priority-ordered chain of lock providers. The registry resolves
the appropriate provider by name or by priority, and supports automatic
fallback: if the primary provider raises ``LockProviderError``, the next
provider in priority order is tried.

Provider priority (highest to lowest):
1. ``"database"`` — ``DBLockProvider`` (primary)
2. ``"file"`` — ``FileLockProvider`` (fallback)
3. ``"memory"`` — ``MemoryLockProvider`` (dev/test fallback)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from src.workflow_runtime.locking.models import LockAcquisition
from src.workflow_runtime.locking.exceptions import LockProviderError


class LockProvider(ABC):
    """Abstract base class for all lock providers.

    Implementations must be thread-safe where applicable and must handle
    stale lock detection per their strategy.

    Parameters
    ----------
    name:
        Human-readable provider name for logging and debugging
        (e.g. ``"database"``, ``"file"``, ``"memory"``).
    """

    def __init__(self, name: str = "unknown") -> None:
        self._name = name

    @property
    def name(self) -> str:
        """Human-readable provider name."""
        return self._name

    @abstractmethod
    def acquire(
        self,
        lock_id: str,
        holder_id: str,
        lease_duration_s: int,
    ) -> Optional[LockAcquisition]:
        """Attempt to acquire a lock.

        Parameters
        ----------
        lock_id:
            The identifier of the resource to lock (typically ``workflow_id``).
        holder_id:
            The identifier of the caller requesting the lock.
        lease_duration_s:
            The lease duration in seconds. The provider must compute
            ``expires_at`` as ``acquired_at + lease_duration_s``.

        Returns
        -------
        Optional[LockAcquisition]
            A ``LockAcquisition`` if the lock was successfully acquired,
            or ``None`` if the lock is held by another holder and has
            not expired.

        Raises
        ------
        LockProviderError
            If an unrecoverable error occurs (e.g. database connection
            failure, disk full, permission denied).
        """
        ...

    @abstractmethod
    def release(self, lock: LockAcquisition) -> bool:
        """Release a previously acquired lock.

        Parameters
        ----------
        lock:
            The ``LockAcquisition`` to release.

        Returns
        -------
        bool
            ``True`` if the lock was successfully released, ``False`` if
            the lock was not held by the caller or was already released.
            The method is idempotent — calling ``release`` on an already-
            released lock returns ``True``.

        Raises
        ------
        LockProviderError
            If an unrecoverable error occurs.
        """
        ...

    @abstractmethod
    def refresh(self, lock: LockAcquisition) -> Optional[LockAcquisition]:
        """Refresh (extend) a lock's lease.

        Parameters
        ----------
        lock:
            The ``LockAcquisition`` whose lease should be refreshed.

        Returns
        -------
        Optional[LockAcquisition]
            An updated ``LockAcquisition`` with the new ``expires_at``
            if the lease was successfully refreshed, or ``None`` if the
            lock is no longer held (expired or released by another holder).

        Raises
        ------
        LockProviderError
            If an unrecoverable error occurs.
        """
        ...


class LockProviderRegistry:
    """Priority-ordered registry of lock providers with fallback support.

    The registry stores providers with an integer priority (lower number =
    higher priority). When resolving a provider, the registry tries them
    in priority order. If a provider raises ``LockProviderError``, the
    next provider in the chain is tried.

    Parameters
    ----------
    providers:
        Optional initial mapping of ``{name: (provider, priority)}``.
    """

    def __init__(
        self,
        providers: dict[str, tuple[LockProvider, int]] | None = None,
    ) -> None:
        self._providers: dict[str, tuple[LockProvider, int]] = {}
        if providers:
            self._providers.update(providers)

    def register(self, provider: LockProvider, priority: int) -> None:
        """Register a lock provider with the given priority.

        Lower ``priority`` values indicate higher precedence. For example,
        priority ``0`` is tried before priority ``1``.

        Parameters
        ----------
        provider:
            The lock provider instance to register.
        priority:
            Integer priority. Lower = higher precedence.
        """
        self._providers[provider.name] = (provider, priority)

    def resolve(self, provider_name: str | None = None) -> LockProvider:
        """Resolve a lock provider by name or by priority.

        If ``provider_name`` is given, that specific provider is returned
        (or raised if not found). If ``provider_name`` is ``None``, the
        providers are tried in priority order; the first one that does not
        raise ``LockProviderError`` is returned.

        Parameters
        ----------
        provider_name:
            Optional name of a specific provider to resolve.

        Returns
        -------
        LockProvider
            A lock provider instance.

        Raises
        ------
        LockProviderError
            If no provider can be resolved.
        """
        if provider_name is not None:
            entry = self._providers.get(provider_name)
            if entry is None:
                raise LockProviderError(
                    provider_name,
                    message=f"Lock provider {provider_name!r} is not registered",
                )
            return entry[0]

        # Try providers in priority order (lowest number first)
        sorted_providers = sorted(
            self._providers.values(),
            key=lambda x: x[1],  # Sort by priority
        )

        last_error: Exception | None = None
        for provider, priority in sorted_providers:
            try:
                # Test the provider by attempting a trivial acquire (no-op)
                # If it raises LockProviderError, try next provider
                lock = provider.acquire(
                    lock_id="__registry_health_check__",
                    holder_id="registry",
                    lease_duration_s=1,
                )
                if lock is not None:
                    provider.release(lock)
                return provider
            except LockProviderError:
                continue
            except Exception as e:
                last_error = e
                continue

        if last_error:
            raise LockProviderError(
                "registry",
                message=f"All lock providers failed. Last error: {last_error}",
                original_exception=last_error,
            )

        raise LockProviderError(
            "registry",
            message="No lock providers are registered",
        )

    @property
    def available_providers(self) -> list[str]:
        """Return the names of all registered providers."""
        return list(self._providers.keys())