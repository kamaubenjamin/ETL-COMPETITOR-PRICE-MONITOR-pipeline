"""Entity Runtime Concurrency Hardening — optimistic locking, pessimistic escalation,
execution leases, and idempotent writes for entity operations.

Strategy overview (per architecture plan):
  1. Primary: Optimistic locking with compare-and-swap (CAS) writes.
     Readers never block; writers check version at write time.
  2. Secondary: Pessimistic locking escalation for hot entities.
     Activated when optimistic retries exceed threshold or conflict rate >30%.
  3. Crash recovery: Execution leases with configurable TTL and daemon refresh loop.
     Expired leases allow other workers to recover and complete writes.
  4. Idempotency: Deterministic SHA-256 keys prevent duplicate writes across retries.

Worked example — typical entity write lifecycle:
  1. acquire_lease(entity_version_key)       # Get exclusive write lease
  2. check_and_record(idempotency_key)       # Idempotency check
  3. read_active(entity_version_key)          # Read current version
  4. cas_write(data, expected_version, cksum) # Atomic CAS write
  5. release_lease(entity_version_key)        # Release lease
"""

from src.entity_runtime.concurrency.config import EntityConcurrencyConfig
from src.entity_runtime.concurrency.errors import (
    EntityConflictError,
    EntityCorruptionError,
    EntityDeadlockError,
    EntityDuplicateWriteError,
    EntityLeaseError,
    EntityLeaseLostError,
    EntityLockTimeoutError,
    EntityStoreUnavailableError,
)
from src.entity_runtime.concurrency.guard import EntityConcurrencyGuard
from src.entity_runtime.concurrency.leases import LeaseAcquisition, LeaseManager
from src.entity_runtime.concurrency.optimistic import ConflictInfo, OptimisticLockManager
from src.entity_runtime.concurrency.pessimistic import (
    EscalationPolicy,
    PessimisticLockManager,
    PessimisticLockReleasePolicy,
)

__all__ = [
    "ConflictInfo",
    "EntityConcurrencyConfig",
    "EntityConcurrencyGuard",
    "EntityConflictError",
    "EntityCorruptionError",
    "EntityDeadlockError",
    "EntityDuplicateWriteError",
    "EntityLeaseError",
    "EntityLeaseLostError",
    "EntityLockTimeoutError",
    "EntityStoreUnavailableError",
    "EscalationPolicy",
    "LeaseAcquisition",
    "LeaseManager",
    "OptimisticLockManager",
    "PessimisticLockManager",
    "PessimisticLockReleasePolicy",
]