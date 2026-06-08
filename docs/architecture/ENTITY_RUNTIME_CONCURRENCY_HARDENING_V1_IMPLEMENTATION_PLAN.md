# Entity Runtime Concurrency Hardening v1 — Implementation Plan

**Date**: 2026-06-05  
**Author**: Platform Architecture Review  
**Status**: Draft — approved for translation  
**Milestone**: v0.5-runtime-hardening  
**Version**: 1.0  
**Source Document**: `docs/architecture/ENTITY_RUNTIME_CONCURRENCY_HARDENING_V1_PLAN.md`

---

## Table of Contents

1. [Work Breakdown Structure](#work-breakdown-structure)
2. [Task Dependencies](#task-dependencies)
3. [Files To Create](#files-to-create)
4. [Files To Modify](#files-to-modify)
5. [Database Migration Requirements](#database-migration-requirements)
6. [Test Plan](#test-plan)
7. [Documentation Deliverables](#documentation-deliverables)
8. [Risk Mitigation Tasks](#risk-mitigation-tasks)
9. [Recommended Implementation Order](#recommended-implementation-order)
10. [Definition of Done](#definition-of-done)
11. [Estimated Timeline](#estimated-timeline)
12. [Phase 1 — Foundation](#phase-1--foundation)
13. [Phase 2 — Concurrency Infrastructure](#phase-2--concurrency-infrastructure)
14. [Phase 3 — Entity Runtime Integration](#phase-3--entity-runtime-integration)
15. [Phase 4 — Verification](#phase-4--verification)
16. [Phase 5 — Documentation & Release](#phase-5--documentation--release)

---

## Work Breakdown Structure

```
ENTITY_RUNTIME_CONCURRENCY_HARDENING_V1
│
├── Phase 1: Foundation (3 days)
│   ├── 1.1  Create concurrency + store package skeletons
│   ├── 1.2  Define EntityConcurrencyConfig (all parameters)
│   ├── 1.3  Define exception hierarchy (8+ exception types)
│   ├── 1.4  Define EntityVersionRecord contract
│   ├── 1.5  Define ConflictInfo, LeaseAcquisition, IdempotencyResult contracts
│   ├── 1.6  Define EntityVersionStore ABC (versioned CRUD operations)
│   ├── 1.7  Define EntityIdempotencyRegistry ABC (key gen, check-and-record)
│   ├── 1.8  Define OptimisticLockManager ABC
│   ├── 1.9  Define PessimisticLockManager ABC
│   ├── 1.10 Define LeaseManager ABC
│   ├── 1.11 Define EntityConcurrencyGuard ABC
│   ├── 1.12 Add entity_version field to entity contracts
│   └── 1.13 Create database migration script (4 tables)
│
├── Phase 2: Concurrency Infrastructure (4.5 days)
│   ├── 2.1  Implement EntityVersionStore — versioned read, write, history, state transitions
│   ├── 2.2  Implement EntityIdempotencyRegistry — key generation, check-and-record, cleanup
│   ├── 2.3  Implement OptimisticLockManager — CAS write, conflict detection, retry policy
│   ├── 2.4  Implement PessimisticLockManager — escalation, lock ordering, deadlock avoidance
│   ├── 2.5  Implement LeaseManager — acquire, refresh, expiry, crash recovery
│   ├── 2.6  Implement EntityConcurrencyGuard — orchestrator coordinating all components
│   ├── 2.7  Implement conflict log (audit trail for concurrency events)
│   ├── 2.8  Implement schema migration runner
│   └── 2.9  Implement background cleanup job for idempotency + expired records
│
├── Phase 3: Entity Runtime Integration (2.5 days)
│   ├── 3.1  Wire EntityConcurrencyGuard into EntityRuntimeOrchestrator
│   ├── 3.2  Add ENTITY_VERSION_STORE_ENABLED configuration flag
│   ├── 3.3  Implement graceful degradation (fallback to in-memory when store unavailable)
│   ├── 3.4  Add workflow adapter (integration with Workflow Runtime stages)
│   ├── 3.5  Add lock/conflict/idempotency error handling in orchestration layer
│   └── 3.6  Add entity_idempotency to idempotency key generation for entity operations
│
├── Phase 4: Verification (4 days)
│   ├── 4.1  Unit tests — EntityVersionStore (CRUD, versioning, state transitions)
│   ├── 4.2  Unit tests — OptimisticLockManager (CAS success, failure, retry)
│   ├── 4.3  Unit tests — PessimisticLockManager (escalation, ordering, deadlock)
│   ├── 4.4  Unit tests — LeaseManager (acquire, refresh, expiry, recovery)
│   ├── 4.5  Unit tests — EntityIdempotencyRegistry (dedup, TTL, cleanup)
│   ├── 4.6  Unit tests — EntityConcurrencyGuard (orchestration, error paths)
│   ├── 4.7  Unit tests — Config + exceptions + contracts
│   ├── 4.8  Integration tests — two writers CAS on same entity
│   ├── 4.9  Integration tests — crash recovery via lease expiry
│   ├── 4.10 Integration tests — escalation to pessimistic locking
│   ├── 4.11 Integration tests — idempotency prevents duplicate writes
│   ├── 4.12 Integration tests — backward compatibility mode (disabled flag)
│   ├── 4.13 Integration tests — graceful degradation (store unavailable)
│   ├── 4.14 Performance benchmarks — CAS write latency, lease overhead
│   └── 4.15 Boundary verification — verify rules pass
│
└── Phase 5: Documentation & Release (2 days)
    ├── 5.1  Create architecture summary document
    ├── 5.2  Create handoff document
    ├── 5.3  Create ADR-009
    ├── 5.4  Update ROADMAP.md — mark entity concurrency hardening as completed
    ├── 5.5  Update TECHNICAL_DEBT.md — close entity concurrency item
    ├── 5.6  Update ENTITY_RUNTIME_V1_ARCHITECTURE.md — add concurrency section
    ├── 5.7  Update CHANGELOG.md
    ├── 5.8  Git commit and push
    └── 5.9  Create milestone tag
```

**Total estimated effort**: ~16 person-days (~3.2 person-weeks)

---

## Task Dependencies

### Dependency Graph

```
Phase 1 ──► Phase 2 ──► Phase 3 ──► Phase 4 ──► Phase 5
  │            │            │
  │            │            └── Depends on Phase 2 (concurrency components must exist before integration)
  │            │
  │            └── Depends on Phase 1 (contracts, config, ABCs must exist before implementation)
  │
  └── No internal dependencies — tasks can run in parallel within phase
```

### Detailed Task Dependencies

| Task ID | Task Name | Depends On | Blocking |
|---------|-----------|------------|----------|
| 1.1 | Create package skeletons | Nothing | 1.2–1.13 |
| 1.2 | EntityConcurrencyConfig | 1.1 | 2.1–2.9 |
| 1.3 | Exception hierarchy | 1.1 | 2.1–2.9, 3.5 |
| 1.4 | EntityVersionRecord contract | 1.1 | 2.1 |
| 1.5 | Supporting contracts (ConflictInfo, LeaseAcquisition, IdempotencyResult) | 1.1 | 2.1, 2.2, 2.3, 2.5 |
| 1.6 | EntityVersionStore ABC | 1.1, 1.4 | 2.1 |
| 1.7 | EntityIdempotencyRegistry ABC | 1.1, 1.5 | 2.2 |
| 1.8 | OptimisticLockManager ABC | 1.1, 1.5 | 2.3 |
| 1.9 | PessimisticLockManager ABC | 1.1, 1.5 | 2.4 |
| 1.10 | LeaseManager ABC | 1.1, 1.5 | 2.5 |
| 1.11 | EntityConcurrencyGuard ABC | 1.1, 1.2, 1.6, 1.7, 1.8, 1.9, 1.10 | 2.6 |
| 1.12 | Entity contract version fields | 1.1 | 2.1 |
| 1.13 | Database migration script | Nothing | 2.1, 2.2, 2.7, 2.9 |
| 2.1 | EntityVersionStore implementation | 1.4, 1.6, 1.13 | 2.3, 2.6 |
| 2.2 | EntityIdempotencyRegistry implementation | 1.5, 1.7, 1.13 | 2.6 |
| 2.3 | OptimisticLockManager implementation | 1.5, 1.8, 2.1 | 2.6 |
| 2.4 | PessimisticLockManager implementation | 1.5, 1.9, 2.3 | 2.6 |
| 2.5 | LeaseManager implementation | 1.5, 1.10, 1.13 | 2.6 |
| 2.6 | EntityConcurrencyGuard implementation | 1.11, 2.1, 2.2, 2.3, 2.4, 2.5, 1.2, 1.3 | 3.1 |
| 2.7 | Conflict log implementation | 1.13 | 2.6 |
| 2.8 | Schema migration runner | 1.13 | 3.1 |
| 2.9 | Background cleanup job | 2.2, 1.13 | 3.1 |
| 3.1 | Wire guard into orchestrator | 2.6, 2.8, 2.9 | 4.6, 4.8 |
| 3.2 | Configuration flag for backward compatibility | 1.2 | 3.1 |
| 3.3 | Graceful degradation | 2.6 | 3.1 |
| 3.4 | Workflow adapter | 2.6 | 3.1 |
| 3.5 | Error handling in orchestration | 1.3 | 3.1 |
| 3.6 | Idempotency key generation | 2.2 | 3.1 |
| 4.1–4.7 | Unit tests | 2.1–2.9 | 4.8 |
| 4.8–4.13 | Integration tests | 3.1, 4.1–4.7 | 4.14 |
| 4.14 | Performance benchmarks | 4.8–4.13 | 4.15 |
| 4.15 | Boundary verification | 4.14 | 5.1 |
| 5.1–5.9 | Documentation & release | 4.15 | Nothing |

### Parallelization Opportunities

- Tasks 2.1 and 2.2 can be implemented in parallel (store vs. idempotency)
- Tasks 2.3, 2.4, 2.5 can be implemented in parallel once 2.1 is complete (different managers)
- Tasks 4.1–4.7 can be written in parallel once their respective components are implemented
- Tasks 5.1–5.7 can be written in parallel

---

## Files To Create

### New Package Structure

```
src/entity_runtime/
├── __init__.py                          # Updated public API exports
├── engine.py                            # Unchanged (extraction logic)
├── contracts/                           # (existing contracts unchanged except version field)
├── extraction/                          # (existing extraction unchanged)
├── validation/                          # (existing validation unchanged)
├── normalization/                       # (existing normalization unchanged)
├── confidence/                          # (existing confidence scorer unchanged)
├── orchestration/                       # (existing orchestrator unchanged)
│
├── concurrency/                         # NEW PACKAGE
│   ├── __init__.py                      # Public API: with_entity_guard, acquire_versioned_write
│   ├── guard.py                         # EntityConcurrencyGuard — orchestrator
│   ├── optimistic.py                    # OptimisticLockManager — CAS + retry
│   ├── pessimistic.py                   # PessimisticLockManager — escalation + deadlock avoidance
│   ├── leases.py                        # LeaseManager — acquire, refresh, expire, recover
│   ├── config.py                        # Concurrency configuration constants
│   └── errors.py                        # ConflictError, LeaseError, DeadlockError, CorruptionError
│
├── store/                               # NEW PACKAGE
│   ├── __init__.py                      # Public API: EntityVersionStore
│   ├── version_store.py                 # EntityVersionStore — versioned CRUD
│   ├── idempotency.py                   # EntityIdempotencyRegistry — dedup
│   ├── migrations.py                    # Schema migration runner
│   └── cleanup.py                       # Background cleanup job for expired records
│
└── integration/                         # NEW PACKAGE (integration with Workflow Runtime)
    ├── __init__.py
    └── workflow_adapter.py              # Adapter hooks EntityConcurrencyGuard into workflow stages
```

### Detailed File Specifications

#### 1. `src/entity_runtime/concurrency/__init__.py`

**Purpose**: Public API for the concurrency module. Exports all classes, exceptions, and helper functions.

**Exports**:
- `EntityConcurrencyGuard` (from `guard`)
- `OptimisticLockManager`, `ConflictInfo` (from `optimistic`)
- `PessimisticLockManager`, `EscalationPolicy`, `PessimisticLockReleasePolicy` (from `pessimistic`)
- `LeaseManager`, `LeaseAcquisition` (from `leases`)
- `EntityConcurrencyConfig` (from `config`)
- `EntityConflictError`, `EntityCorruptionError`, `EntityLeaseError`, `EntityLeaseLostError`, `EntityLockTimeoutError`, `EntityDeadlockError`, `EntityDuplicateWriteError`, `EntityStoreUnavailableError` (from `errors`)

**Module docstring**: Explains the concurrency strategy per the architecture plan (optimistic locking with CAS + pessimistic escalation + execution leases + idempotency). Includes a worked example of a typical entity write lifecycle.

#### 2. `src/entity_runtime/concurrency/config.py`

**Purpose**: All configurable parameters for entity concurrency hardening.

**Classes**:
- `EntityConcurrencyConfig` — frozen dataclass with all configuration parameters (architecture plan lines 1173-1207):
  - Entity Version Store settings
  - Optimistic locking parameters (retry count, delays, backoff)
  - Pessimistic lock escalation thresholds
  - Execution lease parameters
  - Idempotency retention and cleanup settings

#### 3. `src/entity_runtime/concurrency/errors.py`

**Purpose**: Exception hierarchy for all entity concurrency error types.

**Classes** (8 types, architecture plan lines 1233-1242):
- `EntityConflictError(RuntimeError)` — CAS version mismatch
- `EntityCorruptionError(RuntimeError)` — Checksum mismatch on read/write
- `EntityLeaseError(RuntimeError)` — Lease acquisition/refresh failure
- `EntityLeaseLostError(EntityLeaseError)` — Lease expired during write
- `EntityLockTimeoutError(RuntimeError)` — Pessimistic lock acquisition timeout
- `EntityDeadlockError(RuntimeError)` — Deadlock detected
- `EntityDuplicateWriteError(RuntimeError)` — Idempotency key collision
- `EntityStoreUnavailableError(RuntimeError)` — Version store connection failure

#### 4. `src/entity_runtime/store/version_store.py`

**Purpose**: Versioned CRUD operations for entity version store.

**Classes**:
- `EntityVersionRecord` — frozen dataclass (architecture plan lines 275-290):
  - `entity_version_key: str` — Composite key
  - `entity_type: str` — Entity type discriminator
  - `entity_id: str` — Natural key within type
  - `version: int` — Monotonic version number
  - `state: str` — "active" | "superseded" | "archived"
  - `data: dict` — Full entity data (serialized)
  - `checksum: str` — SHA-256 of serialized data
  - `previous_checksum: str` — SHA-256 of version-1 data
  - `created_at: str` — ISO timestamp
  - `created_by: str` — pipeline_run_id or "system"
  - `lease_holder: str` — pipeline_run_id holding write lease
  - `lease_expires_at: str` — ISO timestamp of lease expiry

- `EntityVersionStore` — class with methods:
  - `write_version(entity_version_key, data, expected_version, checksum) -> EntityVersionRecord` — CAS write
  - `read_active(entity_version_key) -> Optional[EntityVersionRecord]` — read current active version
  - `read_version(entity_version_key, version) -> Optional[EntityVersionRecord]` — read specific version
  - `read_history(entity_version_key) -> List[EntityVersionRecord]` — read full version history
  - `transition_state(entity_version_key, version, new_state) -> bool` — state transition
  - `compare_and_swap(entity_version_key, data, expected_version, expected_checksum) -> Tuple[bool, Optional[ConflictInfo]]` — atomic CAS operation

#### 5. `src/entity_runtime/store/idempotency.py`

**Purpose**: Idempotency key generation, check-and-record, and cleanup.

**Classes**:
- `IdempotencyResult` — frozen dataclass:
  - `status: str` — "accepted" | "duplicate"
  - `existing_version: Optional[int]` — for duplicates
  - `existing_run: Optional[str]` — for duplicates

- `EntityIdempotencyRegistry` — class with methods:
  - `generate_key(entity_type, source_document_id, entity_natural_key, workflow_run_id, stage_name) -> str` — deterministic SHA-256 key
  - `check_and_record(idempotency_key, entity_version_key, new_version, pipeline_run_id) -> IdempotencyResult` — atomic check-and-record
  - `cleanup(retention_days, in_progress_ttl_minutes, batch_size) -> int` — TTL-based cleanup
  - `get_status(idempotency_key) -> Optional[IdempotencyResult]` — query existing status

#### 6. `src/entity_runtime/concurrency/optimistic.py`

**Purpose**: CAS write implementation with conflict detection and retry policy.

**Classes**:
- `ConflictInfo` — frozen dataclass (architecture plan lines 373-383):
  - `conflict_type: str` — "version_mismatch" | "checksum_mismatch" | "entity_not_found"
  - `expected_version: int`
  - `actual_version: int`
  - `expected_checksum: str`
  - `actual_checksum: str`
  - `current_holder: str`
  - `last_updated_at: str`

- `OptimisticLockManager` — class with methods:
  - `cas_write(entity_version_key, data, expected_version, expected_checksum) -> EntityVersionRecord` — with retry
  - `_detect_conflict(entity_version_key, expected_version, expected_checksum) -> Optional[ConflictInfo]`
  - `_compute_retry_delay(attempt) -> float` — exponential backoff with jitter

**Retry policy** (architecture plan lines 388-421):
- `OPTIMISTIC_RETRY_MAX_ATTEMPTS = 3`
- `OPTIMISTIC_RETRY_BASE_DELAY_MS = 50`
- `OPTIMISTIC_RETRY_MAX_DELAY_MS = 500`
- `OPTIMISTIC_RETRY_BACKOFF_MULTIPLIER = 2.0`

#### 7. `src/entity_runtime/concurrency/pessimistic.py`

**Purpose**: Escalation to pessimistic locking for hot entities.

**Classes**:
- `EscalationPolicy` — frozen dataclass (architecture plan lines 428-435):
  - `max_optimistic_retries: int = 3`
  - `conflict_rate_threshold: float = 0.3`
  - `escalation_window_minutes: int = 5`
  - `cooldown_minutes: int = 15`

- `PessimisticLockReleasePolicy` — frozen dataclass (architecture plan lines 823-836):
  - All release configuration parameters

- `PessimisticLockManager` — class with methods:
  - `acquire_locks(entity_version_keys: List[str], timeout_s: int) -> bool` — ordered acquisition
  - `release_locks(entity_version_keys: List[str])` — reverse order release
  - `should_escalate(entity_version_key) -> bool` — check thresholds
  - `de_escalate(entity_version_key)` — cool down
  - `_acquire_single(entity_version_key, timeout_s) -> bool` — single lock try

**Lock acquisition rules** (architecture plan lines 768-776):
- Strict ordering: `["supplier", "customer", "document_reference", "document_financials", "line_item"]`
- All-or-nothing acquisition
- Lock acquisition timeout (30s default)
- Release in reverse order

**Deadlock avoidance** (architecture plan lines 780-817):
- Global lock order enforcement
- Lock acquisition timeout (30s)
- Deadlock detection support
- Retry with backoff (max 3 retries)

#### 8. `src/entity_runtime/concurrency/leases.py`

**Purpose**: Execution lease management for crash recovery.

**Classes**:
- `LeaseAcquisition` — frozen dataclass:
  - `entity_version_key: str`
  - `holder_id: str`
  - `acquired_at: str`
  - `expires_at: str`
  - `lease_duration_s: int`

- `LeaseManager` — class with methods:
  - `acquire(entity_version_key, holder_id, lease_duration_s) -> LeaseAcquisition` — with retry
  - `refresh(entity_version_key, holder_id, lease_duration_s) -> bool` — periodic refresh
  - `release(entity_version_key, holder_id) -> bool` — explicit release
  - `is_expired(entity_version_key) -> bool` — check expiry
  - `recover(entity_version_key, holder_id) -> LeaseAcquisition` — acquire expired lease
  - `start_refresh_loop(entity_version_key, holder_id, interval_s, lease_duration_s)` — daemon thread
  - `stop_refresh_loop(entity_version_key)` — stop refresh thread

**Lease parameters** (architecture plan lines 622-634):
- `ENTITY_LEASE_DEFAULT_S = 120` (2 minutes)
- `ENTITY_LEASE_REFRESH_INTERVAL_S = 20` (every 20 seconds)
- `ENTITY_LEASE_REFRESH_GRACE_S = 10` (10s grace period)
- `ENTITY_LEASE_RETRY_MAX_ATTEMPTS = 3`

#### 9. `src/entity_runtime/concurrency/guard.py`

**Purpose**: Orchestrator that coordinates all concurrency components.

**Classes**:
- `EntityConcurrencyGuard` — class with methods:
  - `__init__(version_store, optimistic_manager, pessimistic_manager, lease_manager, idempotency_registry, config)`
  - `write_entity(entity_version_key, data, entity_type, entity_id, pipeline_run_id, stage_name) -> EntityVersionRecord` — full protected write lifecycle
  - `read_entity(entity_version_key) -> Optional[EntityVersionRecord]` — versioned read
  - `read_entity_history(entity_version_key) -> List[EntityVersionRecord]` — full history
  - `merge_entity(entity_version_key, new_data, entity_type, entity_id, pipeline_run_id, stage_name) -> EntityVersionRecord` — merge with CAS
  - `get_conflict_info(entity_version_key) -> Optional[ConflictInfo]` — conflict diagnostics
  - `_determine_locking_strategy(entity_version_key) -> str` — "optimistic" | "pessimistic"
  - `_write_with_optimistic(entity_version_key, data, pipeline_run_id, stage_name) -> EntityVersionRecord` — optimistic write
  - `_write_with_pessimistic(entity_version_key, data, pipeline_run_id, stage_name) -> EntityVersionRecord` — pessimistic write
  - `_log_conflict(conflict_info, resolution)` — record in conflict log

#### 10. `src/entity_runtime/store/migrations.py`

**Purpose**: Schema migration runner for entity version store.

**Classes**:
- `EntityStoreMigration` — class with methods:
  - `run(connection, migration_sql_path)` — execute migration
  - `verify(connection)` — verify migration was applied
  - `rollback(connection)` — rollback migration
  - `get_current_version(connection) -> int` — check applied version

#### 11. `src/entity_runtime/store/cleanup.py`

**Purpose**: Background cleanup job for expired idempotency records and stale leases.

**Classes**:
- `EntityStoreCleanupJob` — class with methods:
  - `__init__(idempotency_registry, lease_manager, config)`
  - `run_cycle()` — single cleanup cycle
  - `start(interval_minutes)` — daemon thread
  - `stop()` — stop daemon thread
  - `get_cleanup_stats() -> dict` — stats for monitoring

**Cleanup strategy** (architecture plan lines 549-575):
- Idempotency: Delete completed/failed records older than 7 days
- In-progress: Expire after 60 minutes TTL
- Leases: Clean up expired leases
- Opportunistic cleanup on write

#### 12. `src/entity_runtime/integration/workflow_adapter.py`

**Purpose**: Adapter that hooks EntityConcurrencyGuard into Workflow Runtime stages.

**Classes**:
- `EntityWorkflowAdapter` — class with methods:
  - `wrap_entity_stage(stage_fn, guard, entity_version_key, entity_type, entity_id, stage_name)` — wraps a stage function with concurrency guard
  - `create_entity_writer(guard, default_config)` — factory for entity write operations
  - `extract_idempotency_key(context, entity_ref)` — extract idempotency key from execution context

### Test Files To Create

```
tests/entity_runtime/
├── __init__.py
├── test_entity_concurrency_config.py        # Config defaults and validation
├── test_entity_concurrency_errors.py         # Exception types and attributes
├── test_entity_version_store.py              # VersionStore CRUD, versioning, states
├── test_optimistic_lock_manager.py           # CAS success, failure, retry
├── test_pessimistic_lock_manager.py          # Escalation, ordering, deadlock
├── test_lease_manager.py                     # Acquire, refresh, expiry, recovery
├── test_entity_idempotency_registry.py       # Dedup, TTL, cleanup
├── test_entity_concurrency_guard.py          # Orchestration, error paths
├── test_entity_store_migrations.py           # Migration execution and verification
├── test_entity_store_cleanup.py              # Cleanup cycle, expiry logic
├── test_adapter_integration.py               # Integration with Workflow Runtime
├── test_integration_concurrent.py            # Two writers CAS on same entity
├── test_integration_crash_recovery.py        # Crash recovery via lease expiry
├── test_integration_escalation.py             # Escalation to pessimistic locking
├── test_integration_idempotency.py           # Idempotency prevents duplicates
├── test_integration_backward_compat.py       # ENTITY_VERSION_STORE_ENABLED=False
├── test_integration_degradation.py           # Store unavailable graceful degradation
└── test_performance_benchmarks.py            # CAS write latency, lease overhead
```

### Database Migration Files

```
scripts/migrations/
└── 008_create_entity_version_store.sql
```

### Documentation Files To Create

```
docs/architecture/
├── ENTITY_RUNTIME_CONCURRENCY_HARDENING_V1_PLAN.md             (existing — source plan)
├── ENTITY_RUNTIME_CONCURRENCY_HARDENING_V1_IMPLEMENTATION.md   (this document)
├── ENTITY_RUNTIME_CONCURRENCY_HARDENING_V1_SUMMARY.md          (to create)
└── ENTITY_RUNTIME_CONCURRENCY_HARDENING_V1_HANDOFF.md          (to create)

docs/adr/
└── ADR-009-entity-concurrency-hardening.md                     (to create)
```

---

## Files To Modify

### 1. `src/entity_runtime/contracts/entity_set.py`

**Changes**:
- Add `entity_version: int = 0` field (default 0 = no versioning)
- Keep all existing fields unchanged — backward compatible
- Ensure `frozen=True` and `slots=True` are preserved (or `@dataclass` decorator unchanged)

### 2. `src/entity_runtime/contracts/supplier.py`

**Changes**:
- Add `entity_version: int = 0` field

### 3. `src/entity_runtime/contracts/customer.py`

**Changes**:
- Add `entity_version: int = 0` field

### 4. `src/entity_runtime/contracts/line_item.py`

**Changes**:
- Add `entity_version: int = 0` field

### 5. `src/entity_runtime/contracts/document_reference.py`

**Changes**:
- Add `entity_version: int = 0` field

### 6. `src/entity_runtime/contracts/document_financials.py`

**Changes**:
- Add `entity_version: int = 0` field

### 7. `src/entity_runtime/__init__.py`

**Changes**:
- Export new concurrency and store modules:
  - `EntityConcurrencyGuard`, `OptimisticLockManager`, `PessimisticLockManager`, `LeaseManager`
  - `EntityVersionStore`, `EntityIdempotencyRegistry`
  - All exception types
  - `EntityConcurrencyConfig`
- Ensure backward-compatible public API

### 8. `src/entity_runtime/orchestration/` (or `src/entity_runtime/orchestrator.py`)

**Changes**:
- Import `EntityConcurrencyGuard`, `EntityVersionStore`, `EntityConcurrencyConfig`
- Add `_concurrency_guard: Optional[EntityConcurrencyGuard]` attribute to orchestrator
- Modify entity creation/extraction flow:
  - After entity extraction, write through `EntityConcurrencyGuard.write_entity()`
  - Read entity history through `EntityVersionStore.read_history()` when needed
  - Handle `EntityConflictError` — retry or escalate
  - Handle `EntityLeaseError` — log and fall back
  - Handle `EntityStoreUnavailableError` — graceful degradation to in-memory
- Add `ENTITY_VERSION_STORE_ENABLED` flag check at startup
- Graceful degradation: if version store is unavailable, emit warning and continue with in-memory entities

### 9. `src/entity_runtime/contracts/__init__.py`

**Changes**:
- Re-export new fields on existing contracts (no new exports needed)
- Ensure `entity_version` field is included in all contract exports

### 10. `src/config.py`

**Changes**:
- Add new configuration constants:
  - `ENTITY_VERSION_STORE_ENABLED: bool = False` — opt-in feature flag
  - `ENTITY_VERSION_STORE_DB_PATH: str = "data/entity_version_store.db"`
  - `OPTIMISTIC_RETRY_MAX_ATTEMPTS: int = 3`
  - `OPTIMISTIC_RETRY_BASE_DELAY_MS: int = 50`
  - `OPTIMISTIC_RETRY_MAX_DELAY_MS: int = 500`
  - `OPTIMISTIC_RETRY_BACKOFF_MULTIPLIER: float = 2.0`
  - `ESCALATION_RETRY_THRESHOLD: int = 3`
  - `ESCALATION_CONFLICT_RATE: float = 0.30`
  - `ESCALATION_ROLLING_WINDOW_MINUTES: int = 5`
  - `ESCALATION_COOLDOWN_MINUTES: int = 15`
  - `PESSIMISTIC_LOCK_ACQUIRE_TIMEOUT_S: int = 30`
  - `PESSIMISTIC_LOCK_MAX_HOLD_S: int = 60`
  - `ENTITY_LEASE_DEFAULT_S: int = 120`
  - `ENTITY_LEASE_REFRESH_INTERVAL_S: int = 20`
  - `ENTITY_LEASE_REFRESH_GRACE_S: int = 10`
  - `ENTITY_LEASE_RETRY_MAX_ATTEMPTS: int = 3`
  - `ENTITY_LEASE_RETRY_BASE_DELAY_MS: int = 100`
  - `ENTITY_IDEMPOTENCY_RETENTION_DAYS: int = 7`
  - `ENTITY_IDEMPOTENCY_IN_PROGRESS_TTL_MINUTES: int = 60`
  - `ENTITY_IDEMPOTENCY_CLEANUP_BATCH_SIZE: int = 1000`
  - `ENTITY_IDEMPOTENCY_CLEANUP_INTERVAL_MINUTES: int = 60`

### 11. `src/workflow_runtime/runtime/workflow_runner.py`

**Changes**:
- Import `EntityWorkflowAdapter` (from `src/entity_runtime/integration/`)
- In entity-related stages, wrap stage execution with entity concurrency guard
- Pass `entity_version_key` and idempotency context to entity write operations
- Handle entity concurrency errors at the workflow level
- Ensure backward compatibility when `ENTITY_VERSION_STORE_ENABLED=False`

### Files NOT Modified (Rationale)

| File | Reason Not Modified |
|------|--------------------|
| `src/entity_runtime/engine.py` | Extraction logic is unchanged; versioning applied at persistence layer |
| `src/entity_runtime/extraction/*.py` | Extraction logic unchanged |
| `src/entity_runtime/validation/*.py` | Validation logic unchanged |
| `src/entity_runtime/normalization/*.py` | Normalization logic unchanged |
| `src/entity_runtime/confidence/*.py` | Confidence scoring unchanged |
| Any file in `src/workflow_runtime/dsl/` | Entity concurrency is a runtime concern, not DSL |
| Any file in `src/workflow_runtime/dag/` | DAG building is orchestration, not execution |
| Any file in `src/workflow_runtime/operations/` | Stages are unaware of entity concurrency |
| `src/storage/history_store.py` | Entity version store is a separate storage layer |

---

## Database Migration Requirements

### Migration 008: Create Entity Version Store

**Filename**: `scripts/migrations/008_create_entity_version_store.sql`

**Purpose**: Create all 4 tables for entity concurrency hardening: entity version history, execution leases, idempotency deduplication, and conflict audit log.

**Dependencies**: None (new tables)
**Rollback**: `DROP TABLE IF EXISTS entity_versions, entity_leases, entity_idempotency, entity_conflict_log;`

#### Table 1: `entity_versions` — Append-only version history

```sql
CREATE TABLE IF NOT EXISTS entity_versions (
    -- Identity
    entity_version_key   TEXT NOT NULL,         -- "{type}:{doc_id}:{natural_key}"
    entity_type          TEXT NOT NULL,          -- "supplier" | "customer" | "line_item" | "document_reference" | "document_financials"
    entity_id            TEXT NOT NULL,          -- Natural key within type
    version              INTEGER NOT NULL,       -- Monotonic version number

    -- State
    state                TEXT NOT NULL DEFAULT 'active',  -- "active" | "superseded" | "archived"

    -- Data
    data                 TEXT NOT NULL,          -- JSON-serialized entity data
    checksum             TEXT NOT NULL,          -- SHA-256 hex digest of data
    previous_checksum    TEXT NOT NULL DEFAULT '',  -- SHA-256 of version-1 data

    -- Provenance
    created_at           TEXT NOT NULL,          -- ISO-8601 timestamp
    created_by           TEXT NOT NULL,          -- pipeline_run_id or "system"
    source_document_id   TEXT NOT NULL DEFAULT '',  -- Document that produced this version

    -- Constraints
    PRIMARY KEY (entity_version_key, version)
);

CREATE INDEX IF NOT EXISTS idx_entity_versions_active
    ON entity_versions (entity_version_key, version DESC)
    WHERE state = 'active';

CREATE INDEX IF NOT EXISTS idx_entity_versions_type
    ON entity_versions (entity_type, state);

CREATE INDEX IF NOT EXISTS idx_entity_versions_source
    ON entity_versions (source_document_id);
```

#### Table 2: `entity_leases` — Execution lease management

```sql
CREATE TABLE IF NOT EXISTS entity_leases (
    entity_version_key   TEXT PRIMARY KEY,      -- Reference to entity
    holder_id            TEXT NOT NULL,          -- "{hostname}-{pid}-{pipeline_run_id}"
    acquired_at          TEXT NOT NULL,          -- ISO-8601 timestamp
    expires_at           TEXT NOT NULL,          -- ISO-8601 timestamp (acquired_at + lease_duration_s)
    lease_duration_s     INTEGER NOT NULL DEFAULT 120,
    last_refreshed_at    TEXT NOT NULL,          -- ISO-8601 timestamp
    refresh_count        INTEGER NOT NULL DEFAULT 0,
    hostname             TEXT NOT NULL DEFAULT '',
    pid                  INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_entity_leases_expired
    ON entity_leases (expires_at)
    WHERE expires_at < CURRENT_TIMESTAMP;
```

#### Table 3: `entity_idempotency` — Duplicate write detection

```sql
CREATE TABLE IF NOT EXISTS entity_idempotency (
    idempotency_key      TEXT PRIMARY KEY,      -- SHA-256 of key components
    entity_version_key   TEXT NOT NULL,          -- Entity being written
    version              INTEGER NOT NULL,       -- Version that was written
    pipeline_run_id      TEXT NOT NULL,          -- Run that performed the write
    status               TEXT NOT NULL DEFAULT 'in_progress',  -- "in_progress" | "completed" | "failed" | "expired"
    created_at           TEXT NOT NULL,          -- ISO-8601 timestamp
    completed_at         TEXT                    -- ISO-8601 timestamp (nullable)
);

CREATE INDEX IF NOT EXISTS idx_entity_idempotency_cleanup
    ON entity_idempotency (status, created_at);
```

#### Table 4: `entity_conflict_log` — Audit trail for concurrency conflicts

```sql
CREATE TABLE IF NOT EXISTS entity_conflict_log (
    conflict_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_version_key   TEXT NOT NULL,
    conflict_type        TEXT NOT NULL,          -- "version_mismatch" | "checksum_mismatch" | "lease_busy" | "deadlock"
    attempted_version    INTEGER NOT NULL,
    current_version      INTEGER NOT NULL,
    attempted_by         TEXT NOT NULL,          -- pipeline_run_id
    current_holder       TEXT NOT NULL DEFAULT '',  -- pipeline_run_id holding current version
    resolution           TEXT NOT NULL DEFAULT '',  -- "retry" | "escalate" | "abort"
    created_at           TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_entity_conflict_log_entity
    ON entity_conflict_log (entity_version_key, created_at DESC);
```

### Migration Verification

- Run `SELECT COUNT(*) FROM entity_versions;` — returns 0
- Run `SELECT COUNT(*) FROM entity_leases;` — returns 0
- Run `SELECT COUNT(*) FROM entity_idempotency;` — returns 0
- Run `SELECT COUNT(*) FROM entity_conflict_log;` — returns 0
- All tables are empty and ready for first use

### Data Backfill (Optional — Post-Migration)

**Filename**: `scripts/migrations/009_backfill_entity_versions.py` (deferred to v1.1)

**Purpose**: Populate version store from existing EntitySet data in history store or debug artifacts.

**Process**:
1. Read entity data from workflow debug artifacts or history store
2. Assign version = 1 for each entity
3. Compute SHA-256 checksum
4. Insert into `entity_versions` with state='active'
5. Record idempotency key
6. Verify entity count matches source data

---

## Test Plan

### Test Architecture

```
tests/entity_runtime/
├── __init__.py
├── conftest.py                              # Shared fixtures:
│   ├── sqlite_in_memory_fixture              # In-memory SQLite for store tests
│   ├── entity_version_store_fixture          # Populated EntityVersionStore
│   ├── entity_idempotency_registry_fixture   # Fresh EntityIdempotencyRegistry
│   ├── sample_entity_version_record_fixture  # Sample valid version record
│   ├── sample_entity_data_fixture            # Sample entity data for tests
│   ├── mock_entity_version_store_fixture     # Mock version store for guard tests
│   ├── mock_lease_manager_fixture            # Mock lease manager
│   └── mock_optimistic_manager_fixture       # Mock optimistic lock manager
│
├── test_entity_concurrency_config.py         # $ref: Task 4.7
├── test_entity_concurrency_errors.py         # $ref: Task 4.7
├── test_entity_version_store.py              # $ref: Task 4.1
├── test_optimistic_lock_manager.py           # $ref: Task 4.2
├── test_pessimistic_lock_manager.py          # $ref: Task 4.3
├── test_lease_manager.py                     # $ref: Task 4.4
├── test_entity_idempotency_registry.py       # $ref: Task 4.5
├── test_entity_concurrency_guard.py          # $ref: Task 4.6
├── test_entity_store_migrations.py           # $ref: Task 4.7
├── test_entity_store_cleanup.py              # $ref: Task 4.7
├── test_adapter_integration.py               # $ref: Task 4.12-4.13
├── test_integration_concurrent.py            # $ref: Task 4.8
├── test_integration_crash_recovery.py        # $ref: Task 4.9
├── test_integration_escalation.py            # $ref: Task 4.10
├── test_integration_idempotency.py           # $ref: Task 4.11
├── test_integration_backward_compat.py       # $ref: Task 4.12
├── test_integration_degradation.py           # $ref: Task 4.13
└── test_performance_benchmarks.py            # $ref: Task 4.14
```

### Unit Tests

#### 4.1 EntityVersionStore Tests (`test_entity_version_store.py`)

| Test Case | Description | Verification |
|-----------|-------------|--------------|
| `test_write_version_1_new_entity` | First write for a new entity | Version 1 created, state='active' |
| `test_write_version_2_cas_success` | CAS write with correct expected version | Version 2 created, v1 state='superseded' |
| `test_write_version_2_cas_conflict` | CAS write with wrong expected version | Returns ConflictInfo, no version created |
| `test_read_active_version` | Read current active version | Returns highest version with state='active' |
| `test_read_specific_version` | Read version 2 specifically | Returns version 2 data |
| `test_read_version_history` | Read all versions for entity | Returns ordered list, all versions |
| `test_read_nonexistent_entity` | Read entity that doesn't exist | Returns None |
| `test_state_transition_active_to_superseded` | Mark active as superseded | State updated, new version becomes active |
| `test_state_transition_superseded_to_archived` | Mark superseded as archived | State updated |
| `test_state_transition_invalid` | Attempt invalid state transition | Returns False or raises error |
| `test_checksum_verification` | Write with correct checksum | Succeeds |
| `test_checksum_mismatch` | Write with incorrect checksum | Returns CorruptionError |
| `test_source_document_provenance` | Write with source_document_id | Source tracked on version record |

#### 4.2 OptimisticLockManager Tests (`test_optimistic_lock_manager.py`)

| Test Case | Description | Verification |
|-----------|-------------|--------------|
| `test_cas_write_success` | CAS write succeeds when version matches | Returns EntityVersionRecord with version+1 |
| `test_cas_write_fails_version_mismatch` | CAS write fails when version mismatches | Returns ConflictInfo with type='version_mismatch' |
| `test_cas_write_fails_checksum_mismatch` | CAS write fails on checksum mismatch | Returns ConflictInfo with type='checksum_mismatch' |
| `test_retry_succeeds_on_2nd_attempt` | First attempt conflicts, retry succeeds | Write succeeds after retry |
| `test_retry_exhausts_after_max_attempts` | All retry attempts fail | Raises EntityConflictError |
| `test_retry_delay_exponential_backoff` | Verify delay increases with each attempt | delay(n+1) >= delay(n) * multiplier |
| `test_retry_delay_jitter` | Verify jitter is applied | delay varies within expected range |
| `test_conflict_info_populated_correctly` | Conflict info fields on failure | All fields populated with correct values |
| `test_no_conflict_different_entities` | Two writers on different entities | Both succeed, no conflict |

#### 4.3 PessimisticLockManager Tests (`test_pessimistic_lock_manager.py`)

| Test Case | Description | Verification |
|-----------|-------------|--------------|
| `test_acquire_lock_correct_order` | Acquire lock in defined order | Locks acquired in ENTITY_LOCK_ORDER |
| `test_acquire_lock_timeout` | Lock acquisition exceeds timeout | Raises EntityLockTimeoutError |
| `test_escalation_triggers_after_threshold` | Retries exceed ESCALATION_RETRY_THRESHOLD | Escalation policy activated |
| `test_de_escalation_after_cooldown` | No conflicts for COOLDOWN_MINUTES | Returns to optimistic mode |
| `test_lock_release_reverse_order` | Release locks in reverse order | Released higher-order first |
| `test_lock_release_all_on_failure` | One release fails, all released | All locks released |
| `test_acquire_with_all_or_nothing` | Partial acquisition fails | No locks held |
| `test_acquire_while_held_by_other` | Lock held by another writer | Returns False or timeout |
| `test_conflict_rate_tracking` | Rolling window conflict rate calculation | Rate correctly calculated |
| `test_escalation_does_not_trigger_below_threshold` | Below conflict rate threshold | No escalation |

#### 4.4 LeaseManager Tests (`test_lease_manager.py`)

| Test Case | Description | Verification |
|-----------|-------------|--------------|
| `test_acquire_lease_when_free` | No existing lease | Returns LeaseAcquisition |
| `test_acquire_lease_when_held` | Lease held by another | Raises EntityLeaseError |
| `test_acquire_lease_after_expiry` | Lease expired, another acquires | Returns LeaseAcquisition |
| `test_refresh_before_expiry` | Refresh active lease | Returns True, expires_at extended |
| `test_refresh_after_expiry` | Refresh expired lease | Returns False, raises EntityLeaseLostError |
| `test_refresh_while_held_by_other` | Refresh lease held by other | Returns False |
| `test_release_held_lease` | Release our own lease | Returns True, lease released |
| `test_release_others_lease` | Release another's lease | Returns False |
| `test_release_already_released` | Double release | Returns True (idempotent) |
| `test_crash_recovery_after_lease_expiry` | Simulate crash, wait, acquire | Acquires after expiry |
| `test_lease_refresh_loop_start_stop` | Start and stop refresh loop | Loop starts and stops cleanly |
| `test_lease_refresh_loop_daemon` | Refresh loop is daemon thread | Thread terminates with process |

#### 4.5 EntityIdempotencyRegistry Tests (`test_entity_idempotency_registry.py`)

| Test Case | Description | Verification |
|-----------|-------------|--------------|
| `test_first_write_accepted` | First write with new key | IdempotencyResult(status='accepted') |
| `test_duplicate_write_rejected` | Same key used again | IdempotencyResult(status='duplicate') |
| `test_different_keys_different_runs` | Same entity, different run | Both accepted |
| `test_different_keys_different_stages` | Same entity, different stage | Both accepted |
| `test_in_progress_ttl_expiry` | Key stuck in_progress, expires | Status changed to 'expired', retry allowed |
| `test_generate_key_deterministic` | Same inputs produce same key | Keys match |
| `test_generate_key_different_entity_type` | Different entity types | Different keys |
| `test_cleanup_removes_old_records` | Records older than retention_days | Deleted, cleanup count > 0 |
| `test_cleanup_preserves_recent_records` | Records newer than retention_days | Not deleted, cleanup count = 0 |
| `test_cleanup_batch_limit` | More records than batch_size | Only batch_size removed per cycle |

#### 4.6 EntityConcurrencyGuard Tests (`test_entity_concurrency_guard.py`)

| Test Case | Description | Verification |
|-----------|-------------|--------------|
| `test_write_entity_optimistic_success` | Full write lifecycle with optimistic lock | Entity written, version incremented, lease released |
| `test_write_entity_pessimistic_escalation` | Optimistic fails, escalates to pessimistic | Write succeeds via pessimistic path |
| `test_write_entity_with_idempotency` | Write with idempotency key | Key recorded, duplicate blocked |
| `test_write_entity_lease_failure` | Lease acquisition fails | Raises EntityLeaseError |
| `test_write_entity_store_unavailable` | Version store goes down | Falls back to in-memory with warning |
| `test_read_entity_active` | Read current version | Returns active EntityVersionRecord |
| `test_read_entity_history` | Read full history | Returns ordered list |
| `test_merge_entity` | Merge new data into existing entity | New version created with merged data |
| `test_merge_entity_conflict` | Merge with concurrent write | Conflict detected, retried |
| `test_get_conflict_info_for_active_entity` | Query conflict diagnostics | Returns ConflictInfo or None |

#### 4.7 Supporting Tests

| Test Category | Test File | Test Cases |
|---------------|-----------|------------|
| **Config** | `test_entity_concurrency_config.py` | Default values valid, override from env, type validation |
| **Errors** | `test_entity_concurrency_errors.py` | All 8 exception types construct correctly, messages formatted, attributes populated |
| **Migrations** | `test_entity_store_migrations.py` | Migration creates 4 tables, migration idempotent, rollback drops tables |
| **Cleanup** | `test_entity_store_cleanup.py` | Cleanup cycle runs, idempotency records cleaned, lease records cleaned, stats returned |

### Integration Tests

#### 4.8 Concurrent Writers (test_integration_concurrent.py)

| Scenario | Setup | Expected Behaviour |
|----------|-------|-------------------|
| **Two writers, same entity, optimistic** | Two threads attempt CAS write on same entity | One succeeds (v1), second retries and succeeds (v2) |
| **Two writers, same entity, simultaneous** | Two threads start CAS write at same time | Only one succeeds at a time, both eventually succeed |
| **Two writers, different entities** | Two threads write different entities | Both succeed (no cross-entity interference) |
| **Multiple writers, same entity, high contention** | 5 threads write same entity concurrently | All succeed, versions 1-5 created, no lost updates |
| **Writer with stale read** | Read entity, wait 30+ seconds, attempt CAS | Force re-read detected, re-read before CAS |

#### 4.9 Crash Recovery (test_integration_crash_recovery.py)

| Scenario | Setup | Expected Behaviour |
|----------|-------|-------------------|
| **Basic crash recovery** | Acquire lease, simulate crash, wait for expiry | Second writer acquires lease after expiry |
| **Crash during write** | Crash mid-write (after lease, before CAS) | Lease expires, second writer recovers and writes |
| **Crash during lease refresh** | Refresh thread dies, lease expires | Lease detected as expired, second writer acquires |
| **Graceful recovery after exception** | Write raises exception, lease released | Lock can be re-acquired immediately |
| **Recovery with idempotency** | Failed write has idempotency key, retry | Idempotency key preserved, retry proceeds |

#### 4.10 Escalation Integration (test_integration_escalation.py)

| Scenario | Setup | Expected Behaviour |
|----------|-------|-------------------|
| **Escalation cascade** | Configure low retry threshold, trigger repeated conflicts | Writer escalates to pessimistic after threshold |
| **De-escalation after cooldown** | Escalated entity, no conflicts for cooldown period | Writer de-escalates to optimistic |
| **Pessimistic lock ordering** | Two writers acquire locks for supplier + line_item | Both acquire in correct order, no deadlock |
| **Lock acquisition timeout** | One writer holds lock, second waits | Second times out with EntityLockTimeoutError |

#### 4.11 Idempotency Integration (test_integration_idempotency.py)

| Scenario | Setup | Expected Behaviour |
|----------|-------|-------------------|
| **Basic duplicate prevention** | Write entity, same write with same key | Second write returns duplicate result, no DB mutation |
| **Idempotency across runs** | Write in run A, same entity+doc in run B | Different keys → both accepted |
| **Idempotency with crash** | Key status='in_progress', writer crashed | After TTL, key expires, retry allowed |
| **Idempotency TTL expiration** | Write with key, wait past TTL, cleanup | Key removed, new write accepted |

#### 4.12 Backward Compatibility (test_integration_backward_compat.py)

| Scenario | Setup | Expected Behaviour |
|----------|-------|-------------------|
| **Flag disabled, entity write** | `ENTITY_VERSION_STORE_ENABLED=False` | Entity write goes to in-memory, no version store interaction |
| **Flag disabled, entity read** | `ENTITY_VERSION_STORE_ENABLED=False` | Entity read returns in-memory EntitySet as before |
| **Flag enabled, existing workflow** | Existing extraction workflow with flag enabled | Entities written to version store transparently |
| **Toggle flag mid-session** | Write with flag disabled, enable, read | Read falls through to appropriate source |

#### 4.13 Graceful Degradation (test_integration_degradation.py)

| Scenario | Setup | Expected Behaviour |
|----------|-------|-------------------|
| **Store DB unavailable on write** | Version store DB connection fails | Warning logged, write proceeds in-memory |
| **Store DB unavailable on read** | Version store DB connection fails | Warning logged, read returns in-memory data |
| **Store recovers after outage** | DB restored mid-session | Next write reconnects, version store resumes |
| **Partial failure (one table unavailable)** | entity_versions table drops | Graceful fallback for that operation |

### Performance Benchmarks

#### 4.14 Performance Benchmarks (test_performance_benchmarks.py)

| Benchmark | Measurement | Target |
|-----------|-------------|--------|
| `test_optimistic_cas_write_latency_p50` | CAS write latency, no conflict | <5ms p50 |
| `test_optimistic_cas_write_latency_p99` | CAS write latency, no conflict | <20ms p99 |
| `test_optimistic_cas_write_with_retry_p50` | CAS write including 1 retry | <200ms p50 |
| `test_optimistic_cas_write_with_retry_p99` | CAS write including 1 retry | <500ms p99 |
| `test_pessimistic_lock_acquire_latency` | Pessimistic lock acquisition (no contention) | <10ms p50, <50ms p99 |
| `test_lease_refresh_overhead` | CPU time per refresh | <1ms |
| `test_concurrent_entity_throughput` | Writes/second with N simultaneous writers | >=100 writes/sec |
| `test_crash_recovery_time` | Lease expiry to new write | <= lease_duration_s + grace_period_s |
| `test_idempotency_check_overhead` | Time per check-and-record | <2ms |
| `test_version_store_read_latency` | Read active version | <3ms p50, <10ms p99 |

### Boundary Verification (4.15)

- Run `python scripts/verify_boundaries.py`
- Confirm all existing boundary rules (R01–R05, R12) pass
- Verify no new imports cross runtime boundaries from `src/entity_runtime/concurrency/` or `src/entity_runtime/store/`
- The concurrency module must only import from:
  - `src/entity_runtime/contracts/` (existing contracts with version field)
  - `src/storage/` (for DB connection utilities)
  - Python standard library (`dataclasses`, `abc`, `typing`, `hashlib`, `threading`, `time`, `json`, `os`, `socket`)
  - External dependencies already declared in `requirements.txt` (e.g. `sqlite3`)

---

## Documentation Deliverables

### New Documents

| # | Document | Location | Content | Format | Audience |
|---|----------|----------|---------|--------|----------|
| 5.1 | Architecture Summary | `docs/architecture/ENTITY_RUNTIME_CONCURRENCY_HARDENING_V1_SUMMARY.md` | What was built, design decisions, configuration, file layout, concurrency strategy overview | Markdown | Future developers, operations |
| 5.2 | Handoff Document | `docs/architecture/ENTITY_RUNTIME_CONCURRENCY_HARDENING_V1_HANDOFF.md` | Runbook, rollback steps, migration guide, monitoring, known issues, troubleshooting | Markdown | Operations, next agent |
| 5.3 | ADR-009 | `docs/adr/ADR-009-entity-concurrency-hardening.md` | Decision record for v1 entity concurrency strategy (optimistic + pessimistic escalation + leases + idempotency) | Markdown (ADR template) | Architecture review |

### Updated Documents

| # | Document | Update Required |
|---|----------|-----------------|
| 5.4 | `docs/ROADMAP.md` | Mark "Entity Runtime Concurrency Hardening" as completed under v0.5 Runtime Hardening |
| 5.5 | `TECHNICAL_DEBT.md` | Close "Entity Runtime Concurrency Controls" item. Add line reference to the plan that resolved it. |
| 5.6 | `docs/architecture/ENTITY_RUNTIME_V1_ARCHITECTURE.md` | Add concurrency hardening section describing versioned entity store, optimistic/pessimistic locking, leases, and idempotency |
| 5.7 | `CHANGELOG.md` | Add entry for v0.5-entity-concurrency-hardening milestone |

### Code Documentation

- Docstrings on all new public classes (`EntityConcurrencyGuard`, `OptimisticLockManager`, `PessimisticLockManager`, `LeaseManager`, `EntityVersionStore`, `EntityIdempotencyRegistry`)
- README section in `src/entity_runtime/concurrency/__init__.py` explaining the concurrency strategy
- Example usage in module docstring for `guard.py` showing typical entity write lifecycle

### Release Artifacts

| # | Artifact | Description |
|---|----------|-------------|
| 5.8 | Git commit | `git commit -m "feat: implement v0.5 entity runtime concurrency hardening"` |
| 5.9 | Milestone tag | `git tag -a v0.5-entity-concurrency-hardening -m "v0.5 Runtime Hardening — Entity Runtime Concurrency Hardening"` |
| 5.10 | Git push | `git push origin main --tags` |

---

## Risk Mitigation Tasks

| # | Risk | Likelihood | Impact | Mitigation Task | Phase | Owner |
|---|------|------------|--------|-----------------|-------|-------|
| R1 | **CAS contention reduces write throughput** | Medium | Medium | Add `test_concurrent_entity_throughput` benchmark. Set conservative retry delays (BASE_DELAY=50ms). Monitor conflict rates via conflict log. | Phase 2, 4 | Implementer, Tester |
| R2 | **Lease TTL misconfiguration** | Medium | High | Add validation in `LeaseManager` that `lease_duration_s >= REFRESH_INTERVAL_S * 3`. Document TTL calculation guidance in handoff. Start with generous default (120s). | Phase 2, 5 | Implementer, Documenter |
| R3 | **Version store becomes bottleneck** | Low | Medium | Use SQLite WAL mode for concurrent readers. Tune indexes for active-version queries. Add `test_version_store_read_latency` benchmark. | Phase 2, 4 | Implementer, Tester |
| R4 | **Deadlock under pessimistic locking** | Low | High | Global lock ordering (`ENTITY_LOCK_ORDER`) prevents cycles. Add deadlock detection and forced retry as safety net. Test with `test_lock_ordering` integration test. | Phase 2, 4 | Implementer, Tester |
| R5 | **Idempotency key collision** | Low | High | Key includes pipeline_run_id — collisions impossible for different runs. Add `test_first_write_accepted` and `test_duplicate_write_rejected` tests. | Phase 2, 4 | Implementer, Tester |
| R6 | **Data corruption from partial write + crash** | Low | High | Triple protection: atomic CAS + lease + checksum. Corruption is detected before commit via checksum verification. Test with `test_crash_during_write` integration test. | Phase 2, 4 | Implementer, Tester |
| R7 | **Migration from non-versioned to versioned entities** | Low | Medium | Feature flag (`ENTITY_VERSION_STORE_ENABLED=False`) for gradual rollout. Backfill script for existing entities (deferred to v1.1). | Phase 3, 5 | Implementer, Documenter |
| R8 | **Rollback complexity (4 new tables)** | Low | Low | Drop tables and disable feature flag. No data loss (append-only). Document rollback procedure in handoff. | Phase 5 | Documenter |
| R9 | **Entity version history unbounded growth** | Low | Low | Archive policy (TTL-based) and compaction via cleanup job. Configurable retention window. Test with `test_cleanup_removes_old_records`. | Phase 2, 4 | Implementer, Tester |
| R10 | **Store unavailable graceful degradation** | Low | Medium | Implement fallback to in-memory write with warning. Test with `test_integration_degradation.py`. Document degradation behaviour in handoff. | Phase 3, 4 | Implementer, Tester |
| R11 | **Backward compatibility breakage** | Low | High | All contract changes use optional fields with `entity_version: int = 0` defaults. Feature flag disables all version store interaction. Existing tests pass without modification. | Phase 1, 3 | Implementer |
| R12 | **False escalation degrading throughput** | Low | Medium | Escalation uses rolling conflict rate window (5 min). De-escalation has cooldown period (15 min). Configurable thresholds. Monitor escalation rate. | Phase 2, 5 | Implementer, Operations |

### Risk Monitoring

| Risk | Monitoring Approach | Threshold | Action |
|------|---------------------|-----------|--------|
| CAS contention | Track `entity_conflict_log` entries per entity | >10% write attempts conflict | Increase OPTIMISTIC_RETRY_MAX_ATTEMPTS or escalate to pessimistic for that entity |
| Lease expiry | Track `LeaseLostError` rate | >0 events per hour | Increase ENTITY_LEASE_DEFAULT_S for affected operations |
| Version store latency | Track store read/write duration in telemetry | >50ms p99 | Review SQLite performance, consider WAL tuning or index optimization |
| Escalation frequency | Track pessimistic lock activations | >5% of entities escalated | Review contention patterns, consider entity-level partitioning |
| Cleanup efficiency | Track cleanup cycle duration and rows affected | No increase in stale rows | Adjust cleanup interval or batch size |

---

## Recommended Implementation Order

### Sequencing Rationale

The implementation order follows a **foundation → infrastructure → integration → verification → release** sequence:

1. **Phase 1 first** — contracts, ABCs, config, and DB schema are prerequisites for everything else
2. **Phase 2 next** — all concurrency components must exist before integration with Entity Runtime
3. **Phase 3 after Phase 2** — integration depends on all concurrency infrastructure
4. **Phase 4 after Phase 3** — tests verify the integrated system
5. **Phase 5 last** — documentation and release are the final steps

### Parallel Execution Within Phases

```
Week 1:
  Mon-Wed:    Phase 1 (3 days) — Foundation
  Thu-Fri:    Phase 2 (4.5 days, starts) — Concurrency Infrastructure
                ├── Thu: EntityVersionStore + EntityIdempotencyRegistry (parallel)
                └── Fri: OptimisticLockManager + PessimisticLockManager (parallel)

Week 2:
  Mon-Wed:    Phase 2 (continues) — Concurrency Infrastructure
                ├── Mon: LeaseManager + ConflictLog (parallel)
                ├── Tue: EntityConcurrencyGuard
                └── Wed: Migration runner + Cleanup job (parallel)
  Thu-Fri:    Phase 3 (2.5 days) — Entity Runtime Integration

Week 3:
  Mon-Thu:    Phase 4 (4 days) — Verification
                ├── Mon: Unit tests (parallel across components)
                ├── Tue: Integration tests (parallel scenarios)
                ├── Wed: Performance benchmarks + boundary verification
                └── Thu: Test iteration, fixes, re-runs
  Fri:        Phase 5 (2 days, starts) — Documentation & Release

Week 4:
  Mon:        Phase 5 (continues) — Documentation & Release
  Tue:        Buffer day (review, fixes, rollback testing)
```

### Per-Developer Task Assignment

**Single developer (full-time, ~16 days total)**:
- Day 1–3: Phase 1 (Foundation)
- Day 4–8: Phase 2 (Concurrency Infrastructure)
- Day 9–10: Phase 3 (Entity Runtime Integration)
- Day 11–14: Phase 4 (Verification)
- Day 15–16: Phase 5 (Documentation & Release)

**Two developers (parallel, ~10 days total)**:
- Dev A: 1.1–1.13 (Phase 1) → 2.1 (VersionStore), 2.3 (Optimistic), 2.6 (Guard), 2.8 (Migrations) → 3.1–3.6 (Integration) → 4.1, 4.2, 4.6, 4.8, 4.9, 4.10, 4.14 (Tests) → 5.4–5.9 (Release)
- Dev B: → 2.2 (Idempotency), 2.4 (Pessimistic), 2.5 (Leases), 2.7 (ConflictLog), 2.9 (Cleanup) → 1.12 (Contract mods) → 4.3, 4.4, 4.5, 4.7, 4.11, 4.12, 4.13, 4.15 (Tests) → 5.1, 5.2, 5.3 (Docs)

---

## Definition of Done

### Code Implementation

- [ ] `EntityConcurrencyConfig` defined with all configurable parameters (4 categories, ~20 constants)
- [ ] `EntityConcurrencyError` exception hierarchy defined (8 types: Conflict, Corruption, Lease, LeaseLost, LockTimeout, Deadlock, DuplicateWrite, StoreUnavailable)
- [ ] `EntityVersionRecord` contract defined (frozen dataclass, 10+ fields)
- [ ] `ConflictInfo`, `LeaseAcquisition`, `IdempotencyResult` supporting contracts defined
- [ ] `EntityVersionStore` implemented — versioned read, write, history, state transitions, CAS operations
- [ ] `OptimisticLockManager` implemented — CAS write with conflict detection
- [ ] `OptimisticLockManager` implemented — retry with exponential backoff and jitter
- [ ] `PessimisticLockManager` implemented — escalation based on retry threshold and conflict rate
- [ ] `PessimisticLockManager` implemented — lock ordering (ENTITY_LOCK_ORDER) and deadlock avoidance
- [ ] `PessimisticLockManager` implemented — lock release semantics (reverse order, all-or-nothing)
- [ ] `LeaseManager` implemented — acquire, refresh, expiry
- [ ] `LeaseManager` implemented — crash recovery (stale lease acquisition after expiry)
- [ ] `LeaseManager` implemented — daemon refresh loop for long-running writes
- [ ] `EntityIdempotencyRegistry` implemented — deterministic key generation (SHA-256)
- [ ] `EntityIdempotencyRegistry` implemented — atomic check-and-record with conflict handling
- [ ] `EntityIdempotencyRegistry` implemented — retention policy and cleanup (TTL-based)
- [ ] `EntityConcurrencyGuard` implemented — orchestrator integrating all components
- [ ] `EntityConcurrencyGuard` implemented — optimistic write path with fallback to pessimistic
- [ ] `EntityConcurrencyGuard` implemented — merge entity operation with CAS
- [ ] Conflict log implemented — records all concurrency events with audit trail
- [ ] Schema migration runner implemented — executes and verifies migration
- [ ] Background cleanup job implemented — idempotency + lease cleanup
- [ ] `entity_version: int = 0` field added to `EntitySet`, `Supplier`, `Customer`, `LineItem`, `DocumentReference`, `DocumentFinancials`
- [ ] `EntityWorkflowAdapter` implemented — hooks concurrency guard into Workflow Runtime stages
- [ ] Database migration script (`scripts/migrations/008_create_entity_version_store.sql`) for all 4 tables
- [ ] Graceful degradation when version store is unavailable (fallback to in-memory with warning)
- [ ] `ENTITY_VERSION_STORE_ENABLED` configuration flag with backward compatibility
- [ ] All existing `pytest tests/ -v` tests pass without modification

### Testing

- [ ] Unit tests for `EntityVersionStore` (12+ test cases, all pass)
- [ ] Unit tests for `OptimisticLockManager` (9+ test cases, all pass)
- [ ] Unit tests for `PessimisticLockManager` (11+ test cases, all pass)
- [ ] Unit tests for `LeaseManager` (12+ test cases, all pass)
- [ ] Unit tests for `EntityIdempotencyRegistry` (9+ test cases, all pass)
- [ ] Unit tests for `EntityConcurrencyGuard` (9+ test cases, all pass)
- [ ] Unit tests for config, exceptions, migrations, cleanup (10+ test cases combined)
- [ ] Integration tests: concurrent writers with CAS on same entity (4+ scenarios, all pass)
- [ ] Integration tests: crash recovery via lease expiry (5+ scenarios, all pass)
- [ ] Integration tests: escalation to pessimistic locking (4+ scenarios, all pass)
- [ ] Integration tests: idempotency prevents duplicate writes (4+ scenarios, all pass)
- [ ] Integration tests: backward compatibility mode (ENTITY_VERSION_STORE_ENABLED=False, 4+ scenarios, all pass)
- [ ] Integration tests: graceful degradation when store unavailable (4+ scenarios, all pass)
- [ ] Performance benchmarks: CAS write latency <5ms p50, <20ms p99
- [ ] Performance benchmarks: concurrent entity throughput >= 100 writes/sec
- [ ] `pytest tests/ -v` passes (full test suite, no regressions)
- [ ] `python scripts/verify_boundaries.py` passes (no import boundary regressions)

### Documentation

- [ ] `docs/architecture/ENTITY_RUNTIME_CONCURRENCY_HARDENING_V1_SUMMARY.md` created
- [ ] `docs/architecture/ENTITY_RUNTIME_CONCURRENCY_HARDENING_V1_HANDOFF.md` created
- [ ] `docs/adr/ADR-009-entity-concurrency-hardening.md` created
- [ ] `docs/ROADMAP.md` updated — Entity Runtime Concurrency Hardening marked complete
- [ ] `TECHNICAL_DEBT.md` updated — entity concurrency item closed with reference to plan
- [ ] `docs/architecture/ENTITY_RUNTIME_V1_ARCHITECTURE.md` updated — add concurrency hardening section
- [ ] `CHANGELOG.md` updated with milestone entry
- [ ] Module docstrings in all new files explaining concurrency strategy
- [ ] Example usage in `guard.py` module docstring

### Release

- [ ] Git commit completed with appropriate message
- [ ] Git push to remote completed
- [ ] Milestone tag `v0.5-entity-concurrency-hardening` created and pushed (or merged into v0.5-runtime-hardening)
- [ ] Future agent can continue from repository documentation alone

---

## Estimated Timeline

### Summary

| Phase | Component | Duration | Calendar Days (single dev) |
|-------|-----------|----------|---------------------------|
| 1 | Foundation | 3 days | Days 1–3 |
| 2 | Concurrency Infrastructure | 4.5 days | Days 4–8 |
| 3 | Entity Runtime Integration | 2.5 days | Days 9–10 |
| 4 | Verification | 4 days | Days 11–14 |
| 5 | Documentation & Release | 2 days | Days 15–16 |
| **Total** | | **16 days** | **~16 calendar days (3.2 weeks)** |

### Detailed Timeline (Single Developer)

```
Week 1                      Mon         Tue         Wed         Thu         Fri
────────────────────────────────────────────────────────────────────────────────
Phase 1: Foundation         █████████████████████████
  Package skeletons           ██
  EntityConcurrencyConfig        ██
  Exception hierarchy               ██
  Contracts (VersionRecord, etc.)         ██
  ABCs (VersionStore, Idempotency)                 ██
  ABCs (Optimistic, Pessimistic, Lease)               ██
  EntityConcurrencyGuard ABC                                   ██
  Entity contract version fields                               ██
  DB migration script                                          ██

Phase 2: Concurrency Infra                                                     ████████████████████████
  EntityVersionStore implementation                                                                   ██████
  EntityIdempotencyRegistry implementation                                                             ██████
  OptimisticLockManager implementation                                                                       ████
  PessimisticLockManager implementation                                                                       ████
```

```
Week 2                      Mon         Tue         Wed         Thu         Fri
────────────────────────────────────────────────────────────────────────────────
Phase 2 (cont.)
  LeaseManager implementation  ████
  Conflict log implementation  ████
  EntityConcurrencyGuard       ████████
  Migration runner             ████
  Cleanup job                  ████

Phase 3: Integration                                      ████████████████████
  Wire guard into orchestrator                               ██████
  Configuration flag                                          ████
  Graceful degradation                                        ████
  Workflow adapter                                            ████
  Error handling                                              ████
  Idempotency key gen                                         ████
```

```
Week 3                      Mon         Tue         Wed         Thu         Fri
────────────────────────────────────────────────────────────────────────────────
Phase 4: Verification        ████████████████████████████████████████████
  Unit tests (11 files)        ██████████████
  Integration tests (7 files)                   ██████████████
  Performance benchmarks                                     ████████
  Boundary verification                                       ██████
  Test iteration & fixes                                         ██████

Phase 5: Docs & Release                                                              ████
  Summary document                                                                     ██
  Handoff document                                                                     ██
```

```
Week 4                      Mon         Tue
────────────────────────────────────────────────
Phase 5 (cont.)
  ADR-009                      ██
  ROADMAP update                ██
  TECHNICAL_DEBT update         ██
  ENTITY_RUNTIME_ARCH update    ██
  CHANGELOG update              ██
  Git commit/push               ██
  Milestone tag                 ██

  Buffer day                               ██████
  (Review, fixes, rollback testing)
```

### Optimization Scenarios

| Scenario | Duration | Trade-off |
|----------|----------|-----------|
| **Full v1 (recommended)** | 16 days / 3.2 weeks | All features, comprehensive tests, full documentation |
| **Minimum Viable (Standard v1 per architecture plan)** | ~12 days / 2.5 weeks | OptimisticLockManager + EntityVersionStore + basic leases + idempotency. Defer pessimistic escalation, conflict log, backfill, performance benchmarks. |
| **Two developers** | ~10 days / 2 weeks | Parallel development but higher coordination cost. See assignment breakdown above. |

### Comparison with Estimates

| Source | Estimate | This Plan | Delta | Reason |
|--------|----------|-----------|-------|--------|
| Architecture Plan (Full v1) | ~17 person-days (~3.5 person-weeks) | ~16 person-days (~3.2 person-weeks) | -1 day | Slight optimization from parallelization within phases and reduced overhead assumptions |
| Architecture Plan (Standard v1) | ~12 person-days (~2.5 person-weeks) | ~12 person-days (Minimum Viable) | 0 | Aligned — Standard v1 defers conflict log, backfill, benchmarks |
| Architecture Plan (Minimum Viable) | ~7 person-days (~1.5 person-weeks) | N/A (not recommended) | — | Full v1 provides production-safety guarantees needed for multi-workflow environments |

---

## Phase 1 — Foundation

### Purpose

Establish the structural foundation for entity concurrency hardening: package layout, data contracts, abstract interfaces, exception hierarchy, configuration parameters, database schema, and entity contract modifications. Phase 1 produces no executable concurrency logic — it defines contracts that Phase 2 will implement.

### Deliverables

| # | Deliverable | File(s) | Acceptance Criteria |
|---|-------------|---------|---------------------|
| 1.1 | Concurrency + store package skeletons | `src/entity_runtime/concurrency/__init__.py`, `src/entity_runtime/store/__init__.py`, `src/entity_runtime/integration/__init__.py` | Packages can be imported. No runtime errors. |
| 1.2 | EntityConcurrencyConfig | `src/entity_runtime/concurrency/config.py` | Frozen dataclass with all configurable parameters. Default values documented. |
| 1.3 | Exception hierarchy | `src/entity_runtime/concurrency/errors.py` | 8 exception types defined with appropriate superclasses and attributes. |
| 1.4 | EntityVersionRecord contract | `src/entity_runtime/store/version_store.py` | Frozen dataclass with 12+ fields. Module docstring explains version record schema. |
| 1.5 | Supporting contracts | `src/entity_runtime/store/idempotency.py`, `src/entity_runtime/concurrency/optimistic.py`, `src/entity_runtime/concurrency/pessimistic.py`, `src/entity_runtime/concurrency/leases.py` | `ConflictInfo`, `LeaseAcquisition`, `IdempotencyResult`, `EscalationPolicy`, `PessimisticLockReleasePolicy` defined as frozen dataclasses. |
| 1.6 | EntityVersionStore ABC | `src/entity_runtime/store/version_store.py` | Abstract class with versioned CRUD methods (write, read, history, transition, CAS). Type annotations complete. |
| 1.7 | EntityIdempotencyRegistry ABC | `src/entity_runtime/store/idempotency.py` | Abstract class with `generate_key`, `check_and_record`, `cleanup`, `get_status` methods. |
| 1.8 | OptimisticLockManager ABC | `src/entity_runtime/concurrency/optimistic.py` | Abstract class with `cas_write` and `detect_conflict` methods. |
| 1.9 | PessimisticLockManager ABC | `src/entity_runtime/concurrency/pessimistic.py` | Abstract class with `acquire_locks`, `release_locks`, `should_escalate`, `de_escalate` methods. |
| 1.10 | LeaseManager ABC | `src/entity_runtime/concurrency/leases.py` | Abstract class with `acquire`, `refresh`, `release`, `is_expired`, `recover` methods. |
| 1.11 | EntityConcurrencyGuard ABC | `src/entity_runtime/concurrency/guard.py` | Abstract class with `write_entity`, `read_entity`, `read_history`, `merge_entity`, `get_conflict_info` methods. |
| 1.12 | Entity contract version fields | `src/entity_runtime/contracts/entity_set.py`, `supplier.py`, `customer.py`, `line_item.py`, `document_reference.py`, `document_financials.py` | `entity_version: int = 0` field added to all 6 contracts. All existing tests pass. |
| 1.13 | Database migration script | `scripts/migrations/008_create_entity_version_store.sql` | SQL script creates all 4 tables. Idempotent (CREATE IF NOT EXISTS). Rollback verified. |

### Dependencies

- **Required**: None — Phase 1 is the starting point
- **Consumed By**: Phase 2 (all deliverables), Phase 3 (contracts, config)
- **External**: Python standard library (`dataclasses`, `abc`, `typing`, `hashlib`, `time`, `threading`)

### Effort Estimate

| Task | Duration (hours) | Details |
|------|-----------------|---------|
| 1.1 Package skeletons | 0.5 | Create 3 directory structures, `__init__.py` with module docstrings |
| 1.2 EntityConcurrencyConfig | 1.0 | Frozen dataclass with 4 categories of configuration parameters |
| 1.3 Exception hierarchy | 0.5 | 8 exception classes with constructors and informative attributes |
| 1.4 EntityVersionRecord contract | 1.0 | Frozen dataclass with 12+ fields, type annotations, docstrings |
| 1.5 Supporting contracts | 1.5 | 5 frozen dataclasses across 4 files |
| 1.6 EntityVersionStore ABC | 1.5 | ABC with 5+ abstract methods, type annotations, contract docstrings |
| 1.7 EntityIdempotencyRegistry ABC | 1.0 | ABC with 4 abstract methods, documentation of idempotency strategy |
| 1.8 OptimisticLockManager ABC | 1.0 | ABC with 2 abstract methods + retry policy documentation |
| 1.9 PessimisticLockManager ABC | 1.0 | ABC with 4 abstract methods + lock ordering documentation |
| 1.10 LeaseManager ABC | 1.0 | ABC with 5 abstract methods + lease lifecycle documentation |
| 1.11 EntityConcurrencyGuard ABC | 1.5 | ABC with 5 abstract methods, orchestrator lifecycle documentation |
| 1.12 Entity contract version fields | 1.0 | Add entity_version to 6 files, verify tests pass |
| 1.13 Database migration script | 1.5 | SQL for 4 tables with indexes. Idempotent. Rollback script. |

**Total Phase 1 effort**: ~14 hours (~2 days)

---

## Phase 2 — Concurrency Infrastructure

### Purpose

Implement all concurrency components defined by the Phase 1 abstractions. Phase 2 produces the executable concurrency infrastructure: version store, idempotency registry, optimistic and pessimistic lock managers, lease manager, concurrency guard, conflict log, migration runner, and cleanup job.

### Deliverables

| # | Deliverable | File(s) | Acceptance Criteria |
|---|-------------|---------|---------------------|
| 2.1 | EntityVersionStore implementation | `src/entity_runtime/store/version_store.py` | Full CRUD implementation against SQLite. CAS writes atomic. State transitions correct. Version history queryable. |
| 2.2 | EntityIdempotencyRegistry implementation | `src/entity_runtime/store/idempotency.py` | Deterministic key generation. Atomic check-and-record. TTL-based cleanup respects batch limits. |
| 2.3 | OptimisticLockManager implementation | `src/entity_runtime/concurrency/optimistic.py` | CAS write with conflict detection and conflict info. Exponential backoff retry with jitter. |
| 2.4 | PessimisticLockManager implementation | `src/entity_runtime/concurrency/pessimistic.py` | Escalation threshold detection. Lock ordering with strict enforcement. Lock timeout and all-or-nothing semantics. |
| 2.5 | LeaseManager implementation | `src/entity_runtime/concurrency/leases.py` | Lease acquire with expiry-aware UPSERT. Refresh with holder verification. Daemon refresh loop. Crash recovery (stale lease acquisition). |
| 2.6 | EntityConcurrencyGuard implementation | `src/entity_runtime/concurrency/guard.py` | Full orchestration: optimistic/pessimistic selection, write lifecycle, merge, conflict logging. |
| 2.7 | Conflict log implementation | `src/entity_runtime/store/version_store.py` (or separate file) | Records all concurrency events. Queryable by entity key and time range. |
| 2.8 | Schema migration runner | `src/entity_runtime/store/migrations.py` | Executes migration SQL. Verifies tables exist. Supports rollback. |
| 2.9 | Background cleanup job | `src/entity_runtime/store/cleanup.py` | Daemon thread. Configurable interval. Cleans idempotency + stale leases. Returns stats. |

### Dependencies

- **Required**: Phase 1 (all deliverables)
- **Consumed By**: Phase 3 (all deliverables)
- **External**: Python standard library, SQLite, hashlib, threading, socket (for hostname), json

### Effort Estimate

| Task | Duration (hours) | Details |
|------|-----------------|---------|
| 2.1 EntityVersionStore | 6 | Full CRUD, CAS operations, state transitions, checksum verification |
| 2.2 EntityIdempotencyRegistry | 3 | Key generation, atomic check-and-record, cleanup, status query |
| 2.3 OptimisticLockManager | 5 | CAS write, conflict detection, retry policy with exponential backoff |
| 2.4 PessimisticLockManager | 5 | Escalation thresholds, lock ordering, deadlock avoidance, timeout |
| 2.5 LeaseManager | 4 | Acquire, refresh, release, expiry, daemon refresh loop, crash recovery |
| 2.6 EntityConcurrencyGuard | 6 | Orchestrator integrating all components, write lifecycle, merge, conflict logging |
| 2.7 Conflict log | 1.5 | Record and query operations |
| 2.8 Migration runner | 1 | Execute, verify, rollback |
| 2.9 Cleanup job | 1.5 | Daemon thread, configurable interval, stats |

**Total Phase 2 effort**: ~33 hours (~4.5 days)

---

## Phase 3 — Entity Runtime Integration

### Purpose

Integrate the concurrency infrastructure with the existing Entity Runtime and Workflow Runtime. Wire the `EntityConcurrencyGuard` into the entity extraction and persistence flow. Add configuration flag for backward compatibility. Implement graceful degradation for store unavailability.

### Deliverables

| # | Deliverable | File(s) | Acceptance Criteria |
|---|-------------|---------|---------------------|
| 3.1 | Guard wired into orchestrator | `src/entity_runtime/orchestration/` or `orchestrator.py` | Entity write flow passes through EntityConcurrencyGuard. All extraction paths covered. |
| 3.2 | Configuration flag | `src/config.py`, `src/entity_runtime/concurrency/config.py` | `ENTITY_VERSION_STORE_ENABLED=False` by default. Flag checked at startup. |
| 3.3 | Graceful degradation | `src/entity_runtime/concurrency/guard.py`, orchestrator | When version store unavailable: warning logged, in-memory write used. No crash. |
| 3.4 | Workflow adapter | `src/entity_runtime/integration/workflow_adapter.py` | Adapter wraps entity stages with concurrency guard. Compatible with existing WorkflowRunner. |
| 3.5 | Error handling | orchestrator, guard | All concurrency error types handled. Conflict → retry. Lease error → warn + fallback. Store unavailable → degrade. |
| 3.6 | Idempotency key generation | orchestrator, adapter | Deterministic keys generated for entity write operations. Key components include entity_type, source_document_id, entity_natural_key, pipeline_run_id, stage_name. |

### Dependencies

- **Required**: Phase 2 (all concurrency components)
- **Consumed By**: Phase 4 (tests)
- **External**: `src/entity_runtime/` existing packages, `src/workflow_runtime/` (for adapter)

### Effort Estimate

| Task | Duration (hours) | Details |
|------|-----------------|---------|
| 3.1 Wire guard into orchestrator | 5 | Modify orchestrator to use guard for entity persistence. Handle all extraction paths. |
| 3.2 Configuration flag | 1 | Add flag check in orchestrator startup. Gate all version store interaction. |
| 3.3 Graceful degradation | 3 | Implement fallback paths for store unavailable. Warning logging. Test all error paths. |
| 3.4 Workflow adapter | 3 | Create adapter that wraps stage functions with guard. Integration with WorkflowRunner. |
| 3.5 Error handling | 2 | Map concurrency errors to orchestration-level responses. Retry logic for conflicts. |
| 3.6 Idempotency key generation | 1.5 | Wire idempotency key generation into entity write operations. |

**Total Phase 3 effort**: ~15.5 hours (~2.5 days)

---

## Phase 4 — Verification

### Purpose

Comprehensive testing of all concurrency components. Unit tests verify individual component behaviour. Integration tests verify multi-component scenarios (concurrent writes, crash recovery, escalation, idempotency, backward compatibility, degradation). Performance benchmarks validate latency targets.

### Deliverables

| # | Deliverable | File(s) | Acceptance Criteria |
|---|-------------|---------|---------------------|
| 4.1 | EntityVersionStore tests | `test_entity_version_store.py` | 12+ test cases, all pass. Covers CRUD, versioning, states, checksums, provenance. |
| 4.2 | OptimisticLockManager tests | `test_optimistic_lock_manager.py` | 9+ test cases, all pass. Covers CAS success/failure, retry, backoff, jitter. |
| 4.3 | PessimisticLockManager tests | `test_pessimistic_lock_manager.py` | 11+ test cases, all pass. Covers escalation, ordering, deadlock, release. |
| 4.4 | LeaseManager tests | `test_lease_manager.py` | 12+ test cases, all pass. Covers acquire, refresh, expiry, recovery, refresh loop. |
| 4.5 | EntityIdempotencyRegistry tests | `test_entity_idempotency_registry.py` | 9+ test cases, all pass. Covers dedup, TTL, cleanup, key generation. |
| 4.6 | EntityConcurrencyGuard tests | `test_entity_concurrency_guard.py` | 9+ test cases, all pass. Covers write lifecycle, merge, conflict, degradation. |
| 4.7 | Supporting tests | Config, errors, migrations, cleanup | 10+ test cases combined, all pass. |
| 4.8 | Concurrent writers integration | `test_integration_concurrent.py` | 5+ scenarios, all pass. Covers same entity, different entities, contention. |
| 4.9 | Crash recovery integration | `test_integration_crash_recovery.py` | 5+ scenarios, all pass. Covers basic crash, crash during write, during refresh. |
| 4.10 | Escalation integration | `test_integration_escalation.py` | 4+ scenarios, all pass. Covers escalation cascade, de-escalation, lock ordering, timeout. |
| 4.11 | Idempotency integration | `test_integration_idempotency.py` | 4+ scenarios, all pass. Covers dedup, across runs, crash-recovery, TTL. |
| 4.12 | Backward compatibility | `test_integration_backward_compat.py` | 4+ scenarios, all pass. Covers flag disabled/enabled, toggle, existing workflows. |
| 4.13 | Graceful degradation | `test_integration_degradation.py` | 4+ scenarios, all pass. Covers DB unavailable, recovery, partial failure. |
| 4.14 | Performance benchmarks | `test_performance_benchmarks.py` | All targets met: CAS write <5ms p50, throughput >=100 writes/sec. |
| 4.15 | Boundary verification | Run `scripts/verify_boundaries.py` | All existing rules pass. No new boundary violations. |

### Dependencies

- **Required**: Phase 3 (integrated system)
- **Consumed By**: Phase 5 (documentation)
- **External**: pytest, time (benchmarks), `scripts/verify_boundaries.py`

### Effort Estimate

| Task | Duration (hours) | Details |
|------|-----------------|---------|
| 4.1 VersionStore tests | 3 | 12+ test cases with SQLite in-memory |
| 4.2 Optimistic tests | 2.5 | 9+ test cases with mock version store |
| 4.3 Pessimistic tests | 2.5 | 11+ test cases with mock escalation policy |
| 4.4 Lease tests | 3 | 12+ test cases with mock DB and timing |
| 4.5 Idempotency tests | 2 | 9+ test cases with in-memory registry |
| 4.6 Guard tests | 2.5 | 9+ test cases with mocked sub-components |
| 4.7 Supporting tests | 1.5 | Config, errors, migrations, cleanup |
| 4.8 Concurrent integration | 2 | 5+ scenarios with threading |
| 4.9 Crash recovery integration | 2 | 5+ scenarios with simulated crashes |
| 4.10 Escalation integration | 1.5 | 4+ scenarios with threshold tuning |
| 4.11 Idempotency integration | 1.5 | 4+ scenarios with duplicate detection |
| 4.12 Backward compat integration | 1.5 | 4+ scenarios with flag toggle |
| 4.13 Degradation integration | 1.5 | 4+ scenarios with simulated failures |
| 4.14 Performance benchmarks | 2 | All latency and throughput targets |
| 4.15 Boundary verification | 0.5 | Run verify_boundaries.py, confirm pass |
| Test iteration + fixes | 4 | Address flaky tests, edge cases, timing issues |

**Total Phase 4 effort**: ~31.5 hours (~4 days)

---

## Phase 5 — Documentation & Release

### Purpose

Create all required documentation per governance rules. Update existing documents (ROADMAP, TECHNICAL_DEBT, architecture docs). Commit and tag the milestone.

### Deliverables

| # | Deliverable | File(s) | Acceptance Criteria |
|---|-------------|---------|---------------------|
| 5.1 | Architecture Summary | `docs/architecture/ENTITY_RUNTIME_CONCURRENCY_HARDENING_V1_SUMMARY.md` | What was built, design decisions, configuration reference, file layout, concurrency flow diagrams |
| 5.2 | Handoff Document | `docs/architecture/ENTITY_RUNTIME_CONCURRENCY_HARDENING_V1_HANDOFF.md` | Runbook, rollback steps, migration guide, monitoring setup, known issues, troubleshooting guide |
| 5.3 | ADR-009 | `docs/adr/ADR-009-entity-concurrency-hardening.md` | Decision record following ADR template. Covers: context, decision, consequences, alternatives considered |
| 5.4 | ROADMAP update | `docs/ROADMAP.md` | Entity Runtime Concurrency Hardening marked as completed under v0.5 |
| 5.5 | TECHNICAL_DEBT update | `TECHNICAL_DEBT.md` | Entity concurrency controls item closed with reference to implementation plan |
| 5.6 | Architecture doc update | `docs/architecture/ENTITY_RUNTIME_V1_ARCHITECTURE.md` | Concurrency hardening section added describing version store, locking, leases, idempotency |
| 5.7 | CHANGELOG update | `CHANGELOG.md` | Entry for v0.5-entity-concurrency-hardening milestone with summary of changes |
| 5.8 | Git commit | — | Commit message: `feat: implement v0.5 entity runtime concurrency hardening` |
| 5.9 | Milestone tag | — | Tag: `v0.5-entity-concurrency-hardening` (or merged into `v0.5-runtime-hardening`) |

### Dependencies

- **Required**: Phase 4 (verified implementation)
- **Consumed By**: Nothing (final phase)
- **External**: Git, Markdown

### Effort Estimate

| Task | Duration (hours) | Details |
|------|-----------------|---------|
| 5.1 Architecture Summary | 3 | Comprehensive summary document (3-5 pages) |
| 5.2 Handoff Document | 3 | Runbook, rollback, migration, monitoring (3-5 pages) |
| 5.3 ADR-009 | 2 | ADR following template (1-2 pages) |
| 5.4 ROADMAP update | 0.5 | Mark milestone as completed |
| 5.5 TECHNICAL_DEBT update | 0.5 | Close item with reference |
| 5.6 Architecture doc update | 1 | Add concurrency section to existing doc |
| 5.7 CHANGELOG update | 0.5 | Add milestone entry |
| 5.8 Git commit | 0.25 | Prepare and execute commit |
| 5.9 Milestone tag | 0.25 | Create and verify tag |

**Total Phase 5 effort**: ~11 hours (~1.5 days)

---

## Appendices

### A. Glossary

| Term | Definition |
|------|------------|
| **Optimistic Locking** | Concurrency control that assumes conflicts are rare; checks version at write time rather than locking resources preemptively |
| **Compare-and-Swap (CAS)** | Atomic operation that updates a value only if it matches an expected version |
| **Pessimistic Locking** | Concurrency control that locks resources before modification to prevent concurrent access |
| **Execution Lease** | Time-bound lock that auto-expires after a configurable duration; provides crash recovery |
| **Idempotency Key** | A deterministic key that uniquely identifies a write operation; prevents duplicate writes |
| **Entity Version Key** | Composite key identifying a specific entity across its version history (`{entity_type}:{source_document_id}:{entity_natural_key}`) |
| **Entity Conflict** | When two writers attempt concurrent CAS writes and one detects a version mismatch |
| **Hot Entity** | An entity that experiences high write contention (multiple concurrent writers) |
| **Lock Escalation** | Automatic transition from optimistic to pessimistic locking for hot entities |
| **Lock Ordering** | A globally-defined sequence for acquiring locks that prevents deadlocks (`ENTITY_LOCK_ORDER`) |
| **Deadlock** | A state where two writers each hold a lock the other needs, causing indefinite blocking |
| **Version Store** | An append-only data store for entity version history (4 tables: `entity_versions`, `entity_leases`, `entity_idempotency`, `entity_conflict_log`) |

### B. Related Documents

| Document | Location | Relationship |
|----------|----------|--------------|
| ENTITY_RUNTIME_CONCURRENCY_HARDENING_V1_PLAN.md | `docs/architecture/` | Source architecture plan — this implementation plan translates it to tasks |
| PLATFORM_ARCHITECTURE_REVIEW.md | `docs/architecture/` | Identifies entity runtime concurrency hardening as highest-risk priority |
| ENTITY_RUNTIME_V1_ARCHITECTURE.md | `docs/architecture/` | Parent architecture document for entity runtime (to be updated) |
| WORKFLOW_RUNTIME_LOCKING_V1_PLAN.md | `docs/architecture/` | Reference pattern — this plan adapts the locking architecture to entity context |
| WORKFLOW_RUNTIME_LOCKING_V1_IMPLEMENTATION.md | `docs/architecture/` | Reference template for this implementation plan structure |
| ADR-008-workflow-runtime-locking.md | `docs/adr/` | Decision record for workflow locking (reference pattern for ADR-009) |
| ADR-009-entity-concurrency-hardening.md (new) | `docs/adr/` | Decision record for entity concurrency hardening |
| NEXT_MILESTONE_RECOMMENDATION.md | `docs/architecture/` | Recommends entity concurrency hardening as next objective |
| ROADMAP.md | `docs/` | Lists entity concurrency hardening as next milestone objective |
| TECHNICAL_DEBT.md | `./` | Tracks concurrency hardening as known debt |

### C. Future Considerations (v2+)

| Feature | Trigger | Strategy |
|---------|---------|----------|
| **Event Sourcing** | Architecture Review recommendation | Replace version store with event-sourced entity history |
| **Distributed entity store (PostgreSQL)** | Multi-host deployment | Migrate from SQLite to PostgreSQL for cross-host coordination |
| **Dynamic lease TTL** | Variable-duration entity operations | Estimate TTL from historical operation times |
| **Dead-letter queue for entity writes** | Persistent write failures | Queue failed entity writes for retry with escalation |
| **Cross-entity atomic transactions** | Multi-entity writes must be atomic | Transactional scope across multiple entity version keys |
| **Entity snapshotting** | Version history becomes too deep | Periodic snapshots of active entity state for fast reads |
| **Read replicas** | Read throughput demand exceeds primary | Version store read replicas for query isolation |
| **Data backfill script** | Existing entities need versioning | `scripts/migrations/009_backfill_entity_versions.py` — deferred from v1 |

---

## End of Implementation Plan