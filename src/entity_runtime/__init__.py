"""Entity Runtime v1 — deterministic entity extraction, validation, and normalization.

Extracts structured entities (LineItem, Supplier, Customer, DocumentReference,
DocumentFinancials) from Document Runtime output. Produces immutable EntitySet.

Consumed by Workflow Runtime stages for transform, filter, match, and compare.

Concurrency hardening (v0.5):
  - EntityConcurrencyGuard: orchestrator for versioned entity writes
  - EntityVersionStore: append-only version history
  - OptimisticLockManager: CAS write with conflict detection
  - PessimisticLockManager: escalation for hot entities
  - LeaseManager: execution leases for crash recovery
  - EntityIdempotencyRegistry: duplicate write detection
"""

from src.entity_runtime.concurrency import (
    ConflictInfo,
    EntityConcurrencyConfig,
    EntityConcurrencyGuard,
    EntityConflictError,
    EntityCorruptionError,
    EntityDeadlockError,
    EntityDuplicateWriteError,
    EntityLeaseError,
    EntityLeaseLostError,
    EntityLockTimeoutError,
    EntityStoreUnavailableError,
    EscalationPolicy,
    LeaseAcquisition,
    LeaseManager,
    OptimisticLockManager,
    PessimisticLockManager,
    PessimisticLockReleasePolicy,
)
from src.entity_runtime.integration import EntityWorkflowAdapter
from src.entity_runtime.confidence import ConfidenceScorer
from src.entity_runtime.contracts import (
    Customer,
    DocumentFinancials,
    DocumentReference,
    EntitySet,
    LineItem,
    SourceLineage,
    Supplier,
)
from src.entity_runtime.engine import EntityExtractionEngine
from src.entity_runtime.extraction import EntityExtractor
from src.entity_runtime.normalization import TextNormalizer
from src.entity_runtime.orchestration import EntityRuntimeOrchestrator
from src.entity_runtime.store import (
    EntityIdempotencyRegistry,
    EntityVersionRecord,
    EntityVersionStore,
    IdempotencyResult,
)
from src.entity_runtime.validation import EntityValidator

__all__ = [
    "ConfidenceScorer",
    "ConflictInfo",
    "Customer",
    "DocumentFinancials",
    "DocumentReference",
    "EntityConcurrencyConfig",
    "EntityConcurrencyGuard",
    "EntityConflictError",
    "EntityCorruptionError",
    "EntityDeadlockError",
    "EntityDuplicateWriteError",
    "EntityExtractionEngine",
    "EntityExtractor",
    "EntityIdempotencyRegistry",
    "EntityLeaseError",
    "EntityLeaseLostError",
    "EntityLockTimeoutError",
    "EntityRuntimeOrchestrator",
    "EntitySet",
    "EntityStoreUnavailableError",
    "EntityVersionRecord",
    "EntityVersionStore",
    "EscalationPolicy",
    "IdempotencyResult",
    "LeaseAcquisition",
    "LeaseManager",
    "LineItem",
    "OptimisticLockManager",
    "PessimisticLockManager",
    "PessimisticLockReleasePolicy",
    "SourceLineage",
    "Supplier",
    "TextNormalizer",
    "EntityValidator",
]
