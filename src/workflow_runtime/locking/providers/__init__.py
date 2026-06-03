"""Lock provider implementations.

This package contains concrete implementations of the ``LockProvider`` ABC:

- ``MemoryLockProvider`` — in-memory lock for testing and development
- ``FileLockProvider`` — file-based advisory lock for single-host deployments
- ``DBLockProvider`` — database-backed lock with execution leases (primary)

These are registered with ``LockProviderRegistry`` and selected via
configuration.
"""

# Provider implementations will be imported here once Phase 2 is complete.
# Phase 1 only defines the ABC — concrete providers are implemented in Phase 2.

__all__: list[str] = []