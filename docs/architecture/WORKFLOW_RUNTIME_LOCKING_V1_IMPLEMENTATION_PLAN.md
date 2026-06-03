# Workflow Runtime Locking v1 — Implementation Plan

**Date**: 2026-06-03  
**Author**: Platform Architecture Review  
**Status**: Draft — approved for implementation  
**Milestone**: v0.5-workflow-runtime-locking  
**Version**: 1.0  
**Source Document**: `docs/architecture/WORKFLOW_RUNTIME_LOCKING_V1_PLAN.md`

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
13. [Phase 2 — Locking Infrastructure](#phase-2--locking-infrastructure)
14. [Phase 3 — Workflow Integration](#phase-3--workflow-integration)
15. [Phase 4 — Testing](#phase-4--testing)
16. [Phase 5 — Documentation And Release](#phase-5--documentation-and-release)

---

## Work Breakdown Structure

```
WORKFLOW_RUNTIME_LOCKING_V1
│
├── Phase 1: Foundation (2.5 days)
│   ├── 1.1  Create locking package skeleton
│   ├── 1.2  Define core data models (LockAcquisition, IdempotencyRecord)
│   ├── 1.3  Define LockProvider ABC
│   ├── 1.4  Define WorkflowExecutionGuard ABC
│   ├── 1.5  Define WorkflowIdempotencyRegistry ABC
│   ├── 1.6  Define custom exceptions
│   ├── 1.7  Create database migration scripts
│   └── 1.8  Add configuration parameters
│
├── Phase 2: Locking Infrastructure (3.5 days)
│   ├── 2.1  Implement MemoryLockProvider
│   ├── 2.2  Implement FileLockProvider
│   ├── 2.3  Implement DBLockProvider
│   ├── 2.4  Implement LockProviderRegistry with fallback chain
│   ├── 2.5  Implement WorkflowIdempotencyRegistry
│   ├── 2.6  Implement WorkflowExecutionGuard
│   ├── 2.7  Implement lease refresh loop
│   └── 2.8  Implement stale lock cleanup job
│
├── Phase 3: Workflow Integration (2 days)
│   ├── 3.1  Update ExecutionContext contract
│   ├── 3.2  Update WorkflowResult contract
│   ├── 3.3  Integrate WorkflowExecutionGuard into WorkflowRunner.run()
│   ├── 3.4  Integrate idempotency key generation for scheduled runs
│   ├── 3.5  Add lock acquisition error handling
│   └── 3.6  Add idempotency rejection handling
│
├── Phase 4: Testing (3.5 days)
│   ├── 4.1  Unit tests — LockProvider ABC
│   ├── 4.2  Unit tests — MemoryLockProvider
│   ├── 4.3  Unit tests — FileLockProvider
│   ├── 4.4  Unit tests — DBLockProvider
│   ├── 4.5  Unit tests — LockProviderRegistry
│   ├── 4.6  Unit tests — WorkflowIdempotencyRegistry
│   ├── 4.7  Unit tests — WorkflowExecutionGuard
│   ├── 4.8  Unit tests — lease refresh loop
│   ├── 4.9  Integration tests — concurrent execution scenarios
│   ├── 4.10 Integration tests — crash recovery
│   ├── 4.11 Integration tests — provider fallback chain
│   ├── 4.12 Integration tests — idempotency key deduplication
│   ├── 4.13 Performance benchmarks
│   └── 4.14 Boundary verification
│
└── Phase 5: Documentation And Release (2 days)
    ├── 5.1  Create architecture summary document
    ├── 5.2  Create handoff document
    ├── 5.3  Create ADR-008
    ├── 5.4  Update ROADMAP.md
    ├── 5.5  Update TECHNICAL_DEBT.md
    ├── 5.6  Update V0_5_RUNTIME_HARDENING_PLAN.md
    ├── 5.7  Create release notes
    ├── 5.8  Git commit and push
    └── 5.9  Create milestone tag
```

**Total estimated effort**: ~13.5 person-days (~2.7 person-weeks)

---

## Task Dependencies

### Dependency Graph

```
Phase 1 ──► Phase 2 ──► Phase 3 ──► Phase 4 ──► Phase 5
  │            │            │
  │            │            └── Depends on Phase 2 (lock providers must exist before integration)
  │            │
  │            └── Depends on Phase 1 (models, ABCs, config must exist before implementation)
  │
  └── No internal dependencies — tasks can run in parallel within phase
```

### Detailed Task Dependencies

| Task ID | Task Name | Depends On | Blocking |
|---------|-----------|------------|----------|
| 1.1 | Create locking package skeleton | Nothing | 1.2, 1.3, 1.4, 1.5 |
| 1.2 | Define core data models | 1.1 | 2.1, 2.2, 2.3, 2.5, 2.6 |
| 1.3 | Define LockProvider ABC | 1.1 | 2.1, 2.2, 2.3, 2.4 |
| 1.4 | Define WorkflowExecutionGuard ABC | 1.1 | 2.6 |
| 1.5 | Define WorkflowIdempotencyRegistry ABC | 1.1 | 2.5 |
| 1.6 | Define custom exceptions | 1.1 | 2.6, 3.5, 3.6 |
| 1.7 | Create database migration scripts | Nothing | 2.3, 2.5 |
| 1.8 | Add configuration parameters | Nothing | 2.4, 2.6 |
| 2.1 | Implement MemoryLockProvider | 1.2, 1.3 | 2.4 |
| 2.2 | Implement FileLockProvider | 1.2, 1.3 | 2.4 |
| 2.3 | Implement DBLockProvider | 1.2, 1.3, 1.7 | 2.4 |
| 2.4 | Implement LockProviderRegistry | 2.1, 2.2, 2.3, 1.8 | 2.6 |
| 2.5 | Implement WorkflowIdempotencyRegistry | 1.2, 1.5, 1.7 | 2.6 |
| 2.6 | Implement WorkflowExecutionGuard | 1.4, 1.6, 2.4, 2.5, 1.8 | 3.3 |
| 2.7 | Implement lease refresh loop | 2.6 | 3.3 |
| 2.8 | Implement stale lock cleanup | 2.3 | 2.6 |
| 3.1 | Update ExecutionContext contract | 1.2 | 3.3 |
| 3.2 | Update WorkflowResult contract | 1.2 | 3.3 |
| 3.3 | Integrate guard into run() | 2.6, 2.7, 3.1, 3.2 | 4.7, 4.9 |
| 3.4 | Idempotency key generation | 2.5 | 3.3 |
| 3.5 | Lock acquisition error handling | 1.6 | 3.3 |
| 3.6 | Idempotency rejection handling | 1.6 | 3.3 |
| 4.1–4.8 | Unit tests | 2.1–2.8 | 4.9 |
| 4.9–4.12 | Integration tests | 3.3, 4.1–4.8 | 4.13 |
| 4.13 | Performance benchmarks | 4.9–4.12 | 4.14 |
| 4.14 | Boundary verification | 4.13 | 5.1 |
| 5.1–5.9 | Documentation & release | 4.14 | Nothing |

### Parallelization Opportunities

- Tasks 2.1, 2.2, 2.3 can be implemented in parallel (different lock providers)
- Tasks 3.1 and 3.2 can be done in parallel (contract updates)
- Tasks 4.1–4.8 can be written in parallel once their respective providers are implemented
- Tasks 5.1–5.7 can be written in parallel

---

## Files To Create

### New Package Structure

The entire locking sub-package lives under `src/workflow_runtime/locking/`:

```
src/workflow_runtime/locking/
├── __init__.py                          # Public API exports
├── models.py                            # LockAcquisition, IdempotencyRecord dataclasses
├── exceptions.py                        # LockAcquisitionError, IdempotencyRejectionError
├── execution_guard.py                   # WorkflowExecutionGuard ABC + implementation
├── lock_provider.py                     # LockProvider ABC + LockProviderRegistry
├── idempotency.py                       # WorkflowIdempotencyRegistry implementation
└── providers/
    ├── __init__.py                      # Provider exports
    ├── db_lock_provider.py              # DBLockProvider (database-backed with leases)
    ├── file_lock_provider.py            # FileLockProvider (file-based fallback)
    └── memory_lock_provider.py          # MemoryLockProvider (in-memory, dev/test)
```

### Detailed File Specifications

#### 1. `src/workflow_runtime/locking/__init__.py`

**Purpose**: Public API for the locking module. Exports all classes, exceptions, and helper functions that external code should import.

**Exports**:
- `LockAcquisition`, `IdempotencyRecord` (from `models`)
- `LockAcquisitionError`, `IdempotencyRejectionError`, `LockProviderError` (from `exceptions`)
- `WorkflowExecutionGuard` (from `execution_guard`)
- `LockProvider`, `LockProviderRegistry` (from `lock_provider`)
- `WorkflowIdempotencyRegistry` (from `idempotency`)
- Helper: `acquire_lock`, `release_lock` convenience functions

**Module docstring**: Explains the locking strategy per the architecture plan (DB-backed lock with execution leases + idempotency keys). Includes a worked example.

#### 2. `src/workflow_runtime/locking/models.py`

**Purpose**: Immutable data contracts for lock acquisition state and idempotency records.

**Classes**:
- `LockAcquisition` — frozen dataclass with slots:
  - `lock_id: str` — workflow_id
  - `holder_id: str` — hostname-pid-pipeline_run_id
  - `acquired_at: str` — ISO timestamp
  - `expires_at: str` — ISO timestamp
  - `lease_duration_s: int` — lease TTL in seconds
- `IdempotencyRecord` — frozen dataclass with slots:
  - `idempotency_key: str` — workflow_id-schedule_slot
  - `pipeline_run_id: str` — the run that claimed this key
  - `status: str` — completed | failed | in_progress
  - `created_at: str` — ISO timestamp

#### 3. `src/workflow_runtime/locking/exceptions.py`

**Purpose**: Distinct exception types for lock and idempotency failures.

**Classes**:
- `LockAcquisitionError(Exception)` — raised when lock cannot be acquired. Contains `lock_id`, `current_holder_id`, `expires_at` for the caller to make retry decisions.
- `IdempotencyRejectionError(Exception)` — raised when an idempotency key has already been processed. Contains `idempotency_key`, `existing_status`, `existing_pipeline_run_id`.
- `LockProviderError(Exception)` — raised when a lock provider encounters an unrecoverable error (DB connection failure, disk full, permission denied). Contains `provider_name` and `original_exception`.
- `LeaseRefreshError(Exception)` — raised when lease refresh fails. Non-fatal; execution continues with warning.

#### 4. `src/workflow_runtime/locking/lock_provider.py`

**Purpose**: Abstract base class for lock providers and the registry that selects and chains them.

**Classes**:
- `LockProvider(ABC)` — abstract methods:
  - `acquire(lock_id: str, holder_id: str, lease_duration_s: int) -> Optional[LockAcquisition]`
  - `release(lock: LockAcquisition) -> bool`
  - `refresh(lock: LockAcquisition) -> Optional[LockAcquisition]`
- `LockProviderRegistry` — manages provider chain:
  - `register(provider: LockProvider, priority: int)`
  - `resolve(provider_name: Optional[str] = None) -> LockProvider`
  - Fallback logic: try providers in priority order, fall through if `LockProviderError`

#### 5. `src/workflow_runtime/locking/execution_guard.py`

**Purpose**: Wraps the workflow execution lifecycle with lock acquisition, lease refresh, and release.

**Classes**:
- `WorkflowExecutionGuard`:
  - `__init__(lock_provider: LockProvider, idempotency_registry: Optional[WorkflowIdempotencyRegistry])`
  - `execute(workflow_id: str, holder_id: str, idempotency_key: Optional[str], fn: Callable) -> Tuple[Any, Optional[LockAcquisition]]`
  - Context manager support: `__enter__` acquires lock, `__exit__` releases

**Behaviour**:
1. If idempotency_key provided, check registry → skip if completed
2. Try to acquire lock with retry + exponential backoff
3. Yield to `fn()` for execution
4. Periodically refresh lease (every `REFRESH_INTERVAL_S`)
5. On completion, release lock
6. If idempotency_key provided, record result in registry

#### 6. `src/workflow_runtime/locking/idempotency.py`

**Purpose**: Registry for idempotency key deduplication.

**Classes**:
- `WorkflowIdempotencyRegistry(ABC)` — abstract methods:
  - `check(key: str) -> Optional[IdempotencyRecord]` — returns existing record or None
  - `record(key: str, pipeline_run_id: str, status: str) -> IdempotencyRecord` — atomic insert
  - `cleanup(ttl_days: int) -> int` — remove keys older than TTL
- `DBIdempotencyRegistry` — implementation using `workflow_idempotency` table
- `MemoryIdempotencyRegistry` — in-memory implementation for testing

#### 7. `src/workflow_runtime/locking/providers/__init__.py`

**Purpose**: Convenience exports for all provider implementations.

**Exports**:
- `DBLockProvider`
- `FileLockProvider`
- `MemoryLockProvider`

#### 8. `src/workflow_runtime/locking/providers/db_lock_provider.py`

**Purpose**: Database-backed lock provider using the `workflow_locks` table.

**Implementation details**:
- `acquire()`: `INSERT INTO workflow_locks ... ON CONFLICT (lock_id) DO UPDATE SET holder_id = EXCLUDED.holder_id WHERE expires_at < NOW()`
  - Returns `LockAcquisition` if acquired, `None` if lock is held by another
- `release()`: `DELETE FROM workflow_locks WHERE lock_id = ... AND holder_id = ...`
  - Verifies holder identity before releasing (prevents releasing another's lock)
- `refresh()`: `UPDATE workflow_locks SET expires_at = NOW() + lease_duration_s, last_refreshed_at = NOW(), refresh_count = refresh_count + 1 WHERE lock_id = ... AND holder_id = ...`
- `cleanup_stale()`: `DELETE FROM workflow_locks WHERE expires_at < NOW()` — periodic cleanup

**Configuration**:
- Table name from config (`LOCK_DB_TABLE`)
- Connection via existing `history_store` or configured DB connection

#### 9. `src/workflow_runtime/locking/providers/file_lock_provider.py`

**Purpose**: File-based lock provider using advisory file locking.

**Implementation details**:
- Lock file location: `{workspace_dir}/.locks/{workflow_id}.lock`
- `acquire()`: Create lock file with exclusive access. Write JSON metadata (holder_id, acquired_at, expires_at, hostname, pid). On Windows uses `msvcrt.locking`; on POSIX uses `fcntl.flock`.
- `release()`: Delete lock file if we hold the lock (verify by reading holder_id)
- `refresh()`: Update lock file metadata (expires_at, refresh_count)
- Stale detection: If lock file exists but `expires_at < NOW()`, treat as stale and acquire

#### 10. `src/workflow_runtime/locking/providers/memory_lock_provider.py`

**Purpose**: In-memory lock provider for testing and development. Not suitable for production.

**Implementation details**:
- `acquire()`: Check `_locks` dict for entries that haven't expired. If free, add entry with expiry.
- `release()`: Remove entry from `_locks` dict.
- `refresh()`: Update expiry time in `_locks` dict.
- Thread-safe via `threading.Lock`.

### Test Files To Create

```
tests/locking/
├── __init__.py
├── test_models.py                        # Data model construction, immutability
├── test_exceptions.py                    # Exception types and attributes
├── test_memory_lock_provider.py          # MemoryLockProvider unit tests
├── test_file_lock_provider.py            # FileLockProvider unit tests
├── test_db_lock_provider.py              # DBLockProvider unit tests
├── test_lock_provider.py                 # LockProvider ABC contract tests
├── test_lock_provider_registry.py        # Registry + fallback chain tests
├── test_workflow_idempotency_registry.py # Idempotency registry tests
├── test_workflow_execution_guard.py      # Execution guard unit tests
├── test_lease_refresh.py                 # Lease refresh loop tests
├── test_integration_concurrent.py        # Concurrent execution integration tests
├── test_integration_crash_recovery.py    # Crash recovery integration tests
├── test_integration_fallback.py          # Provider fallback chain integration tests
├── test_integration_idempotency.py       # Idempotency key integration tests
└── test_performance_benchmarks.py        # Lock acquisition latency benchmarks
```

### Database Migration Files

```
scripts/migrations/
├── 006_create_workflow_locks_table.sql
└── 007_create_workflow_idempotency_table.sql
```

### Documentation Files To Create

```
docs/architecture/
├── WORKFLOW_RUNTIME_LOCKING_V1_PLAN.md         (existing — source plan)
├── WORKFLOW_RUNTIME_LOCKING_V1_IMPLEMENTATION.md (this document)
├── WORKFLOW_RUNTIME_LOCKING_V1_SUMMARY.md       (to create)
└── WORKFLOW_RUNTIME_LOCKING_V1_HANDOFF.md       (to create)

docs/adr/
└── ADR-008-workflow-runtime-locking.md          (to create)

.github/workflows/
└── test_locking.yml                             (optional — CI for locking tests)
```

---

## Files To Modify

### 1. `src/workflow_runtime/runtime/workflow_runner.py`

**Changes**:
- Import `WorkflowExecutionGuard`, `LockProviderRegistry`, `WorkflowIdempotencyRegistry`
- Add `_execution_guard` and `_idempotency_registry` attributes to `WorkflowRunner.__init__()`
- Modify `run()` method:
  - Add idempotency key generation logic (if scheduled run)
  - Call `execution_guard.execute()` wrapping the existing execution logic
  - Handle `LockAcquisitionError` — return specific result or raise
  - Handle `IdempotencyRejectionError` — return cached result
- Add lease refresh loop within the execution guard context

**Signature change**: `WorkflowRunner.__init__()` gains optional `execution_guard` and `idempotency_registry` parameters with `None` defaults (backward compatible).

### 2. `src/workflow_runtime/contracts/execution_context.py`

**Changes**:
- Add `lock_acquisition: Optional[LockAcquisition] = None` field to `ExecutionContext`
- Add `idempotency_key: Optional[str] = None` field
- Keep all existing fields unchanged — backward compatible
- Ensure `frozen=True` and `slots=True` are preserved

### 3. `src/workflow_runtime/contracts/workflow_result.py`

**Changes**:
- Add `idempotency_key: Optional[str] = None` field
- Add `lock_status: Optional[str] = None` field (values: `"acquired"`, `"rejected_busy"`, `"rejected_duplicate"`, `"not_locked"`)
- Keep all existing fields unchanged — backward compatible

### 4. `src/storage/history_store.py`

**Changes**:
- Add methods (delegating to DBLockProvider or implementing directly):
  - `acquire_workflow_lock(lock_id, holder_id, lease_duration_s) -> Optional[dict]`
  - `release_workflow_lock(lock_id, holder_id) -> bool`
  - `refresh_workflow_lease(lock_id, holder_id, lease_duration_s) -> bool`
- Add methods for idempotency:
  - `check_idempotency_key(key) -> Optional[dict]`
  - `record_idempotency_key(key, pipeline_run_id, status) -> dict`
  - `cleanup_idempotency_keys(ttl_days) -> int`
- If DBLockProvider is implemented as a standalone class, these methods delegate to it; otherwise, they contain the SQL directly.

### 5. `src/config.py`

**Changes**:
- Add new configuration constants:
  - `LOCK_DEFAULT_LEASE_S: int = 300`
  - `LOCK_REFRESH_INTERVAL_S: int = 30`
  - `LOCK_MAX_RETRIES: int = 3`
  - `LOCK_RETRY_DELAY_S: int = 5`
  - `LOCK_PROVIDER: str = "database"`
  - `LOCK_DB_TABLE: str = "workflow_locks"`
  - `IDEMPOTENCY_ENABLED: bool = True`
  - `IDEMPOTENCY_KEY_TTL_DAYS: int = 7`
  - `IDEMPOTENCY_DB_TABLE: str = "workflow_idempotency"`
  - `LOCK_FILE_DIR: str = ".locks"` (path relative to workspace)

### 6. `src/workflow_runtime/__init__.py`

**Changes**:
- Export `LockAcquisition`, `LockAcquisitionError`, `LockProvider`, `WorkflowExecutionGuard` from the `locking` sub-package
- Ensure backward-compatible public API

### 7. `src/workflow_runtime/contracts/__init__.py`

**Changes**:
- Re-export new fields on existing contracts (no new exports needed)

### 8. `src/scheduler.py` (or equivalent trigger code)

**Changes**:
- Generate deterministic idempotency key for scheduled runs: `f"{workflow_id}-{schedule_date.isoformat()}"`
- Pass idempotency key to `WorkflowRunner.run()` via metadata

### Files NOT Modified (Rationale)

| File | Reason Not Modified |
|------|--------------------|
| `src/workflow_runtime/dsl/workflow_parser.py` | Locking is a runtime concern, not DSL |
| `src/workflow_runtime/dsl/workflow_validator.py` | Validation does not involve runtime state |
| `src/workflow_runtime/dag/builder.py` | DAG building is orchestration, not execution |
| `src/workflow_runtime/operations/*.py` | Stages are unaware of locking |
| `src/workflow_runtime/workspace/workspace_registry.py` | Workspace management is separate |
| Any file outside `src/workflow_runtime/` | Locking lives within Workflow Runtime boundary |

---

## Database Migration Requirements

### Migration 006: Create `workflow_locks` table

**Filename**: `scripts/migrations/006_create_workflow_locks_table.sql`

```sql
-- Migration: 006_create_workflow_locks_table
-- Purpose: Distributed lock table for workflow execution coordination
-- Dependencies: None (new table)
-- Rollback: DROP TABLE IF EXISTS workflow_locks;

CREATE TABLE workflow_locks (
    lock_id            TEXT PRIMARY KEY,
    holder_id          TEXT NOT NULL,
    acquired_at        TIMESTAMP NOT NULL DEFAULT (datetime('now')),
    expires_at         TIMESTAMP NOT NULL,
    lease_duration_s   INTEGER NOT NULL DEFAULT 300,
    hostname           TEXT NOT NULL,
    pid                INTEGER,
    refresh_count      INTEGER NOT NULL DEFAULT 0,
    last_refreshed_at  TIMESTAMP NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_workflow_locks_expires_at ON workflow_locks(expires_at);
CREATE INDEX idx_workflow_locks_holder_id ON workflow_locks(holder_id);
```

**Rollback SQL**:
```sql
DROP TABLE IF EXISTS workflow_locks;
```

### Migration 007: Create `workflow_idempotency` table

**Filename**: `scripts/migrations/007_create_workflow_idempotency_table.sql`

```sql
-- Migration: 007_create_workflow_idempotency_table
-- Purpose: Idempotency key table for deduplicating workflow runs
-- Dependencies: None (new table)
-- Rollback: DROP TABLE IF EXISTS workflow_idempotency;

CREATE TABLE workflow_idempotency (
    idempotency_key    TEXT PRIMARY KEY,
    pipeline_run_id    TEXT NOT NULL,
    status             TEXT NOT NULL CHECK (status IN ('completed', 'failed', 'in_progress')),
    created_at         TIMESTAMP NOT NULL DEFAULT (datetime('now')),
    completed_at       TIMESTAMP,
    result_summary     TEXT
);

CREATE INDEX idx_workflow_idempotency_status ON workflow_idempotency(status);
CREATE INDEX idx_workflow_idempotency_created_at ON workflow_idempotency(created_at);
```

**Rollback SQL**:
```sql
DROP TABLE IF EXISTS workflow_idempotency;
```

### Migration Execution

- Migrations are run as part of the deployment process
- Migration order: 006 first (locks table), then 007 (idempotency table)
- No data migration required — both tables are new
- Existing `history_store` data is unaffected

### Migration Verification

- Run `SELECT COUNT(*) FROM workflow_locks;` — returns 0
- Run `SELECT COUNT(*) FROM workflow_idempotency;` — returns 0
- Tables are empty and ready for first use

---

## Test Plan

### Test Architecture

```
tests/locking/
├── __init__.py                                    # Test package init
├── conftest.py                                    # Shared fixtures:
│   ├── memory_lock_provider_fixture               # Fresh MemoryLockProvider per test
│   ├── temp_directory_fixture                     # Temp dir for file lock tests
│   ├── db_connection_fixture                      # In-memory SQLite for DB lock tests
│   ├── lock_acquisition_fixture                   # Sample valid LockAcquisition
│   ├── idempotency_record_fixture                 # Sample valid IdempotencyRecord
│   └── workflow_runner_fixture                    # Mock WorkflowRunner
│
├── test_models.py                                 # $ref: Task 4.1 (indirect)
├── test_exceptions.py                             # $ref: Task 4.1 (indirect)
├── test_lock_provider.py                          # $ref: Task 4.1
├── test_memory_lock_provider.py                   # $ref: Task 4.2
├── test_file_lock_provider.py                     # $ref: Task 4.3
├── test_db_lock_provider.py                       # $ref: Task 4.4
├── test_lock_provider_registry.py                 # $ref: Task 4.5
├── test_workflow_idempotency_registry.py          # $ref: Task 4.6
├── test_workflow_execution_guard.py               # $ref: Task 4.7
├── test_lease_refresh.py                          # $ref: Task 4.8
├── test_integration_concurrent.py                 # $ref: Task 4.9
├── test_integration_crash_recovery.py             # $ref: Task 4.10
├── test_integration_fallback.py                   # $ref: Task 4.11
├── test_integration_idempotency.py                # $ref: Task 4.12
└── test_performance_benchmarks.py                 # $ref: Task 4.13
```

### Unit Tests

#### 4.1 LockProvider ABC Contract Tests (`test_lock_provider.py`)

Ensures any `LockProvider` implementation conforms to the contract.

| Test Case | Description | Verification |
|-----------|-------------|--------------|
| `test_acquire_returns_lock_when_free` | Acquire an unlocked lock_id | Returns `LockAcquisition` |
| `test_acquire_returns_none_when_held` | Acquire a locked lock_id | Returns `None` |
| `test_acquire_returns_lock_after_expiry` | Acquire an expired lock | Returns `LockAcquisition` |
| `test_release_held_lock` | Release a lock we hold | Returns `True` |
| `test_release_already_released` | Release an already-released lock | Returns `True` (idempotent) |
| `test_release_others_lock` | Release a lock held by someone else | Returns `False` |
| `test_refresh_before_expiry` | Refresh an active lock | Returns updated `LockAcquisition` |
| `test_refresh_after_expiry` | Refresh an expired lock | Returns `None` |
| `test_refresh_others_lock` | Refresh a lock held by someone else | Returns `None` |
| `test_acquire_concurrent_same_id` | Two acquires for same lock_id | Second returns `None` |
| `test_acquire_concurrent_different_id` | Two acquires for different lock_ids | Both return `LockAcquisition` |

#### 4.2 MemoryLockProvider Tests (`test_memory_lock_provider.py`)

- All ABC contract tests (inherited from parametrized test base)
- Thread safety: concurrent acquire/release from multiple threads
- Cleanup on provider destruction
- Memory leak check: no lingering references after release

#### 4.3 FileLockProvider Tests (`test_file_lock_provider.py`)

- All ABC contract tests (inherited from parametrized test base)
- Lock file creation: verify `.lock` file exists in expected location
- Lock file content: contains valid JSON with correct metadata
- Stale lock detection: create old lock file, verify acquire overrides it
- Permission denied: test with read-only directory
- Cross-process: test with separate subprocess
- Windows vs POSIX: test platform-specific locking APIs
- Cleanup: lock file deleted on release

#### 4.4 DBLockProvider Tests (`test_db_lock_provider.py`)

- All ABC contract tests (inherited from parametrized test base)
- SQL injection check: lock_id with special characters
- Transaction rollback: simulate DB error during acquire, verify no partial state
- Connection failure: disconnect DB, verify `LockProviderError`
- Stale lock cleanup: create stale rows, run cleanup, verify deleted
- Concurrent DB access: test with in-memory SQLite with multiple connections

#### 4.5 LockProviderRegistry Tests (`test_lock_provider_registry.py`)

| Test Case | Description | Verification |
|-----------|-------------|--------------|
| `test_resolve_by_name` | Resolve `"database"` | Returns `DBLockProvider` |
| `test_resolve_default` | Resolve with no name | Returns highest priority provider |
| `test_fallback_db_to_file` | DB provider fails, falls to file | Returns `FileLockProvider` |
| `test_fallback_file_to_memory` | File provider fails, falls to memory | Returns `MemoryLockProvider` |
| `test_all_providers_fail` | All providers fail | Raises `LockProviderError` |
| `test_register_priority_order` | Register in different order | Returns correct priority |

#### 4.6 WorkflowIdempotencyRegistry Tests (`test_workflow_idempotency_registry.py`)

| Test Case | Description | Verification |
|-----------|-------------|--------------|
| `test_check_new_key` | Check a key that doesn't exist | Returns `None` |
| `test_check_existing_key` | Check a key that exists | Returns `IdempotencyRecord` |
| `test_record_new_key` | Record a new idempotency key | Returns new `IdempotencyRecord` |
| `test_record_duplicate_key` | Try to record existing key | Raises `IdempotencyRejectionError` |
| `test_record_key_atomic` | Two concurrent records for same key | Only one succeeds |
| `test_cleanup_expired_keys` | Remove keys older than TTL | Returns count of removed keys |
| `test_cleanup_no_expired` | No keys older than TTL | Returns 0 |

#### 4.7 WorkflowExecutionGuard Tests (`test_workflow_execution_guard.py`)

| Test Case | Description | Verification |
|-----------|-------------|--------------|
| `test_execute_success` | Guard wraps function successfully | Function result returned, lock released |
| `test_execute_rejects_duplicate` | Two guards on same lock_id | Second raises `LockAcquisitionError` |
| `test_execute_with_idempotency` | Idempotency key provided | Key recorded after success |
| `test_execute_skips_completed` | Key already completed | Returns cached result, no execution |
| `test_execute_crash_lease_expiry` | Simulate crash, wait for expiry | Second attempt acquires lock |
| `test_execute_context_manager` | `with guard:` syntax | Lock acquired/released correctly |
| `test_execute_retry_on_failure` | Lock acquisition retries | Retries up to max, then raises |
| `test_execute_refresh_during_long_run` | Long execution triggers refresh | Lease refreshed at expected interval |

#### 4.8 Lease Refresh Loop Tests (`test_lease_refresh.py`)

| Test Case | Description | Verification |
|-----------|-------------|--------------|
| `test_refresh_invoked_during_execution` | Long-running function | `refresh()` called at expected intervals |
| `test_refresh_failure_logs_warning` | `refresh()` raises | Warning logged, execution continues |
| `test_refresh_extends_expiry` | Before and after timestamps | Expiry moves forward by lease_duration |
| `test_refresh_stops_after_completion` | Function completes early | No refresh after guard exits |

### Integration Tests

#### 4.9 Concurrent Execution Integration (`test_integration_concurrent.py`)

| Scenario | Setup | Expected Behaviour |
|----------|-------|-------------------|
| **Same workflow, concurrent threads** | 2 threads call `run()` simultaneously with same `workflow_id` | Second caller receives `LockAcquisitionError` |
| **Different workflows, concurrent** | 2 threads call `run()` with different `workflow_id`s | Both succeed |
| **Same workflow, staggered start** | Start run A, wait 100ms, start run B | Run B receives `LockAcquisitionError` |
| **Scheduled + manual overlap** | Start long-running workflow, then trigger manual run | Manual run receives lock rejection |
| **Multiple workflows, no contention** | 10 workflows, each different `workflow_id`, run simultaneously | All 10 succeed |

#### 4.10 Crash Recovery Integration (`test_integration_crash_recovery.py`)

| Scenario | Setup | Expected Behaviour |
|----------|-------|-------------------|
| **Basic crash recovery** | Acquire lock, simulate kill, wait for lease expiry | Second run acquires lock after expiry |
| **Crash recovery during refresh** | Simulate crash mid-refresh | Lease expiry works correctly |
| **Graceful recovery after failure** | Run fails with exception, lock is released | Lock can be re-acquired immediately |
| **Recovery with idempotency** | Failed run has idempotency key, retry with same key | Key updated to new status |

#### 4.11 Provider Fallback Integration (`test_integration_fallback.py`)

| Scenario | Setup | Expected Behaviour |
|----------|-------|-------------------|
| **DB → File fallback** | DB lock_provider raises, file provider available | Falls to file locking, execution proceeds |
| **File → Memory fallback** | DB and file fail, memory available | Falls to memory (dev warning), execution proceeds |
| **All providers fail** | All three providers unavailable | `LockProviderError` raised, execution blocked |
| **Fallback performance** | Measure latency with each provider | File < DB < Memory in latency |

#### 4.12 Idempotency Integration (`test_integration_idempotency.py`)

| Scenario | Setup | Expected Behaviour |
|----------|-------|-------------------|
| **Basic dedup** | Run workflow with idempotency key, run again | Second returns cached result |
| **Idempotency with lock** | Key exists and completed, lock is free | Skip execution, return cached (no lock acquire needed) |
| **Idempotency with concurrent** | Two runs, same key, simultaneous | Only one executes; other gets rejection |
| **Idempotency TTL** | Key older than TTL, re-run | Key cleaned up, execution proceeds |

### Performance Benchmarks

#### 4.13 Performance Benchmarks (`test_performance_benchmarks.py`)

| Benchmark | Measurement | Target |
|-----------|-------------|--------|
| `test_lock_acquire_latency_p50` | Time to acquire lock (DB provider) | <10ms p50 |
| `test_lock_acquire_latency_p99` | Time to acquire lock (DB provider) | <50ms p99 |
| `test_lock_acquire_latency_file_p50` | Time to acquire lock (File provider) | <5ms p50 |
| `test_lock_acquire_latency_memory_p50` | Time to acquire lock (Memory provider) | <1ms p50 |
| `test_release_latency` | Time to release lock | <5ms p50 |
| `test_refresh_latency` | Time to refresh lease | <5ms p50 |
| `test_concurrent_lock_throughput` | Acquire/release cycles with N workflows | >= current throughput (no regression) |
| `test_idempotency_check_latency` | Time to check idempotency key | <5ms p50 |

### Boundary Verification (4.14)

- Run `python scripts/verify_boundaries.py`
- Confirm all existing R01–R05, R12 rules pass
- Verify no new imports cross runtime boundaries from `src/workflow_runtime/locking/`
- The locking module must only import from:
  - `src/workflow_runtime/contracts/` (existing contracts)
  - `src/storage/` (history_store for DB provider)
  - Python standard library (threading, os, fcntl/msvcrt, json, pathlib)
  - External dependencies already declared in `requirements.txt`

---

## Documentation Deliverables

### New Documents

| # | Document | Location | Content | Format | Audience |
|---|----------|----------|---------|--------|----------|
| 5.1 | Architecture Summary | `docs/architecture/WORKFLOW_RUNTIME_LOCKING_V1_SUMMARY.md` | What was built, design decisions, configuration, file layout | Markdown | Future developers, operations |
| 5.2 | Handoff Document | `docs/architecture/WORKFLOW_RUNTIME_LOCKING_V1_HANDOFF.md` | Runbook, rollback steps, migration, monitoring, known issues | Markdown | Operations, next agent |
| 5.3 | ADR-008 | `docs/adr/ADR-008-workflow-runtime-locking.md` | Decision record for v1 locking strategy (DB-backed + leases + idempotency) | Markdown (ADR template) | Architecture review |

### Updated Documents

| # | Document | Update Required |
|---|----------|-----------------|
| 5.4 | `docs/ROADMAP.md` | Mark "Workflow Runtime Locking" as completed under v0.5 Runtime Hardening |
| 5.5 | `TECHNICAL_DEBT.md` | Close "Lack of distributed locking; potential duplicate job execution" item. Add line reference to the plan that resolved it. |
| 5.6 | `docs/architecture/V0_5_RUNTIME_HARDENING_PLAN.md` | Update Workflow Runtime Locking section status from "In Progress" to "Completed" |
| 5.7 | `CHANGELOG.md` | Add entry for v0.5-workflow-runtime-locking milestone |

### Release Artifacts

| # | Artifact | Description |
|---|----------|-------------|
| 5.8 | Git commit | `git commit -m "feat: implement v0.5 workflow runtime locking"` |
| 5.9 | Milestone tag | `git tag -a v0.5-workflow-runtime-locking -m "v0.5 Runtime Hardening — Workflow Runtime Locking"` |
| 5.10 | Git push | `git push origin main --tags` |

---

## Risk Mitigation Tasks

| # | Risk | Mitigation Task | Phase | Owner |
|---|------|-----------------|-------|-------|
| R1 | **Lock contention reduces throughput** | Add `test_concurrent_lock_throughput` benchmark to detect throughput regression. Set `LOCK_REFRESH_INTERVAL_S` to a conservative 30s default. | Phase 4 | Tester |
| R2 | **Lease TTL misconfiguration** | Add validation in `WorkflowExecutionGuard.__init__()` that checks `lease_duration_s >= REFRESH_INTERVAL_S * 3`. Document TTL calculation guidance in handoff. | Phase 2 | Implementer |
| R3 | **Database becomes lock bottleneck** | Add DB lock latency monitoring via the existing telemetry. Set `LOCK_PROVIDER=database` with `FileLockProvider` as fallback. | Phase 2, 3 | Implementer |
| R4 | **File lock fallback unreliable on Windows** | Test `FileLockProvider` on Windows CI. If `msvcrt` locking proves unreliable, fall back to existence-check pattern (lock file presence + stale detection). | Phase 2, 4 | Implementer, Tester |
| R5 | **Idempotency key collision** | Key design must include workflow_id + schedule_slot + trigger_type. Add `test_record_key_atomic` test with concurrent writes. | Phase 2, 4 | Implementer, Tester |
| R6 | **Distributed deadlock** | Not applicable for v1 — each workflow locks only its own `workflow_id`. Add architectural note in handoff. | Phase 5 | Documenter |
| R7 | **Lock table unbounded growth** | Idempotency table uses TTL-based cleanup. Lock table has single row per workflow_id (UPSERT). Add `test_cleanup_expired_keys` test. | Phase 2, 4 | Implementer, Tester |
| R8 | **Existing runs fail on first deploy** | Locking is opt-in. Default to `LOCK_PROVIDER=memory` in first deployment, then switch to `database` after monitoring. Document migration plan in handoff. | Phase 3, 5 | Implementer, Documenter |
| R9 | **Lease refresh failure during execution** | Refresh failure is non-fatal — execution continues with warning. Last successful refresh timestamp is used for stale detection. Test via `test_refresh_failure_logs_warning`. | Phase 2, 4 | Implementer, Tester |
| R10 | **Backward compatibility breakage** | All contract changes use Optional fields with None defaults. `WorkflowRunner.__init__()` accepts optional guard. Existing callers continue to work unchanged. | Phase 3 | Implementer |

### Risk Monitoring

| Risk | Monitoring Approach | Threshold | Action |
|------|---------------------|-----------|--------|
| Lock contention | Track `LockAcquisitionError` rate in logs | >1% of runs | Increase `LOCK_RETRY_DELAY_S` or review workflow duration |
| Lease expiry during execution | Track `LEASE_EXPIRED_DURING_EXECUTION` audit events | >0 events | Increase `LOCK_DEFAULT_LEASE_S` for affected workflows |
| DB lock latency | Track lock acquisition duration in telemetry | >100ms p99 | Review DB performance, consider tuning |
| Provider fallback activation | Track fallback events in logs | Any occurrence | Investigate primary provider failure |

---

## Recommended Implementation Order

### Sequencing Rationale

The implementation order follows a **foundation → infrastructure → integration → verification → release** sequence:

1. **Phase 1 first** — models, ABCs, and config are prerequisites for everything else
2. **Phase 2 next** — all lock providers and registry must exist before integration
3. **Phase 3 after Phase 2** — integration depends on all locking infrastructure
4. **Phase 4 after Phase 3** — tests verify the integrated system
5. **Phase 5 last** — documentation and release are the final steps

### Parallel Execution Within Phases

```
Week 1:
  Mon-Tue:    Phase 1 (2.5 days) — Foundation
  Wed-Fri:    Phase 2 (3.5 days) — Locking Infrastructure
                ├── Wed: MemoryLockProvider + FileLockProvider (parallel)
                ├── Thu: DBLockProvider + IdempotencyRegistry (parallel)
                └── Fri: LockProviderRegistry + ExecutionGuard + LeaseRefresh

Week 2:
  Mon-Tue:    Phase 3 (2 days) — Workflow Integration
  Wed-Fri:    Phase 4 (3.5 days) — Testing
                ├── Wed: Unit tests (parallel)
                ├── Thu: Integration tests (parallel)
                └── Fri: Performance benchmarks + boundary verification

Week 3:
  Mon-Tue:    Phase 5 (2 days) — Documentation And Release
```

### Per-Developer Task Assignment

For a single developer, tasks execute sequentially within phases but can be grouped:

**Developer (full-time, ~13.5 days total)**:
- Day 1–2: Phase 1 (Foundation)
- Day 3–5: Phase 2 (Locking Infrastructure) — providers in order of dependency
- Day 6–7: Phase 3 (Workflow Integration)
- Day 8–10: Phase 4 (Testing) — unit tests during implementation, integration after
- Day 11–12: Phase 5 (Documentation And Release)
- Day 13: Buffer for review, fixes, rollback procedure testing

**Two developers (parallel, ~9 days total)**:
- Dev A: 1.1–1.8 (Phase 1) → 2.3 (DB), 2.5 (Idempotency), 2.6 (Guard) → 3.1–3.6 (Integration) → 4.4, 4.5, 4.6, 4.7, 4.9, 4.10, 4.11, 4.12 (Tests) → 5.4–5.9 (Release)
- Dev B: → 2.1, 2.2 (Memory + File providers), 2.4 (Registry), 2.7, 2.8 (Lease + Cleanup) → 4.1, 4.2, 4.3, 4.8, 4.13, 4.14 (Tests) → 5.1, 5.2, 5.3 (Docs)

---

## Definition of Done

### Code Implementation

- [ ] `LockProvider` ABC defined with `acquire`, `release`, `refresh` abstract methods
- [ ] `DBLockProvider` implementation — acquires lock in `workflow_locks` table, supports leases
- [ ] `FileLockProvider` implementation — file-based lock with stale detection and metadata
- [ ] `MemoryLockProvider` implementation — in-memory lock for tests and dev
- [ ] `LockProviderRegistry` — selects provider by configured priority with fallback chain
- [ ] `WorkflowIdempotencyRegistry` implementation — deduplication via `workflow_idempotency` table
- [ ] `WorkflowExecutionGuard` wraps `WorkflowRunner.run()` with lock lifecycle
- [ ] `ExecutionContext` updated with optional `lock_acquisition` and `idempotency_key` fields
- [ ] `WorkflowResult` updated with optional `idempotency_key` and `lock_status` fields
- [ ] Idempotency key generation for scheduled runs (deterministic per schedule slot)
- [ ] Lock acquisition error handling with distinct `LockAcquisitionError` type
- [ ] Idempotency rejection handling with `IdempotencyRejectionError` type
- [ ] Lease refresh loop in `run()` lifecycle (periodic refresh every `REFRESH_INTERVAL_S`)
- [ ] Stale lock cleanup mechanism (TTL-based expiry or cleanup job)
- [ ] Database schema migration scripts for `workflow_locks` and `workflow_idempotency` tables

### Testing

- [ ] Unit tests for `MemoryLockProvider` (8+ test cases, all pass)
- [ ] Unit tests for `FileLockProvider` (10+ test cases, all pass)
- [ ] Unit tests for `DBLockProvider` (10+ test cases, all pass)
- [ ] Unit tests for `LockProviderRegistry` (6+ test cases, all pass)
- [ ] Unit tests for `WorkflowIdempotencyRegistry` (8+ test cases, all pass)
- [ ] Unit tests for `WorkflowExecutionGuard` (8+ test cases, all pass)
- [ ] Unit tests for lease refresh loop (4+ test cases, all pass)
- [ ] Integration tests for concurrent execution scenarios (5+ scenarios, all pass)
- [ ] Integration tests for crash recovery via lease expiry (4+ scenarios, all pass)
- [ ] Integration tests for provider fallback chain (4+ scenarios, all pass)
- [ ] Integration tests for idempotency key deduplication (4+ scenarios, all pass)
- [ ] Performance benchmarks for lock acquisition latency (p50 <10ms, p99 <50ms for DB provider)
- [ ] `pytest tests/ -v` passes (full test suite, no regressions)
- [ ] `python scripts/verify_boundaries.py` passes (no import boundary regressions)

### Documentation

- [ ] `docs/architecture/WORKFLOW_RUNTIME_LOCKING_V1_SUMMARY.md` created
- [ ] `docs/architecture/WORKFLOW_RUNTIME_LOCKING_V1_HANDOFF.md` created
- [ ] `docs/adr/ADR-008-workflow-runtime-locking.md` created
- [ ] `docs/ROADMAP.md` updated — Workflow Runtime Locking marked complete
- [ ] `TECHNICAL_DEBT.md` updated — locking item closed with reference to plan
- [ ] `docs/architecture/V0_5_RUNTIME_HARDENING_PLAN.md` updated — section status updated
- [ ] `CHANGELOG.md` updated with milestone entry
- [ ] Module docstrings in all new files explaining locking strategy
- [ ] Example usage in `execution_guard.py` module docstring

### Release

- [ ] Git commit completed with appropriate message
- [ ] Git push to remote completed
- [ ] Milestone tag `v0.5-workflow-runtime-locking` created and pushed
- [ ] Future agent can continue from repository documentation alone

---

## Estimated Timeline

### Summary

| Phase | Component | Duration | Calendar Days (single dev) |
|-------|-----------|----------|---------------------------|
| 1 | Foundation | 2.5 days | Days 1–2 |
| 2 | Locking Infrastructure | 3.5 days | Days 3–5 |
| 3 | Workflow Integration | 2 days | Days 6–7 |
| 4 | Testing | 3.5 days | Days 8–10 |
| 5 | Documentation And Release | 2 days | Days 11–12 |
| **Total** | | **13.5 days** | **~12 calendar days (2.5 weeks)** |

### Detailed Timeline (Single Developer)

```
Week 1                      Mon         Tue         Wed         Thu         Fri
────────────────────────────────────────────────────────────────────────────────
Phase 1: Foundation         ████████████
  Locking package skeleton     ██
  Data models                                                  ██
  LockProvider ABC                                 ██
  ExecutionGuard ABC                                            ██
  Idempotency ABC                                                ██
  Custom exceptions                                              ██
  DB migrations                                                  ██
  Configuration params                                                          ██

Phase 2: Locking Infra                                                        ██████████████
  MemoryLockProvider                                                                      ██
  FileLockProvider                                                                        ██
  DBLockProvider                                                                           ██
  LockProviderRegistry                                                                      ██
  IdempotencyRegistry                                                                       ██
  ExecutionGuard                                                                             ██
  Lease refresh                                                                               ██
  Stale cleanup                                                                                ██
```

```
Week 2                      Mon         Tue         Wed         Thu         Fri
────────────────────────────────────────────────────────────────────────────────
Phase 3: Integration         ██████████████
  ExecutionContext update      ██
  WorkflowResult update        ██
  Guard into run()                      ██
  Idempotency key gen                    ██
  Lock error handling                     ██
  Idempotency rejection                   ██

Phase 4: Testing                                                   ██████████████
  Unit tests (7 files)                                                         ████████
  Integration tests (4 files)                                                             ████████
  Performance benchmarks                                                                          ██
  Boundary verification                                                                           ██
```

```
Week 3                      Mon         Tue
────────────────────────────────────────────────
Phase 5: Docs & Release     ██████████████
  Summary document           ██
  Handoff document           ██
  ADR-008                               ██
  ROADMAP update                         ██
  TECHNICAL_DEBT update                  ██
  V0_5 plan update                       ██
  Release notes                          ██
  Git commit/push                        ██
  Milestone tag                          ██
```

### Optimization Scenarios

| Scenario | Duration | Trade-off |
|----------|----------|-----------|
| **Full v1 (recommended)** | 13.5 days / 2.5 weeks | All features, comprehensive tests, full documentation |
| **Minimum Viable Locking** | ~5 days / 1 week | DBLockProvider only, no file/memory fallback, no idempotency, no lease refresh, minimal tests |
| **Two developers** | ~9 days / 1.8 weeks | Parallel development but higher coordination cost |

### Comparison with Estimates

| Source | Estimate | This Plan | Delta | Reason |
|--------|----------|-----------|-------|--------|
| NEXT_MILESTONE_RECOMMENDATION.md | ~1 week | ~2.5 weeks | +1.5 weeks | Original est. assumed simpler single-strategy. Plan includes 3 providers, idempotency, leases, comprehensive testing, governance docs |
| ARCHITECTURE_PLAN.md (Full v1) | ~2.8 person-weeks | ~2.5 person-weeks | -0.3 weeks | Close alignment. Minor difference due to test parallelization assumptions |

---

## Phase 1 — Foundation

### Purpose

Establish the structural foundation for the locking module: package layout, data models, abstract interfaces, exceptions, configuration, and database schema. Phase 1 produces no executable locking logic — it defines contracts that Phase 2 will implement.

### Deliverables

| # | Deliverable | File(s) | Acceptance Criteria |
|---|-------------|---------|---------------------|
| 1.1 | Locking package skeleton | `src/workflow_runtime/locking/__init__.py`, `src/workflow_runtime/locking/providers/__init__.py` | Package can be imported. No runtime errors. |
| 1.2 | Data model contracts | `src/workflow_runtime/locking/models.py` | `LockAcquisition` and `IdempotencyRecord` dataclasses defined, frozen, with slots. Module docstring explains types. |
| 1.3 | LockProvider ABC | `src/workflow_runtime/locking/lock_provider.py` | Abstract class with `acquire`, `release`, `refresh` methods. Type annotations complete. Docstring documents contract for implementers. |
| 1.4 | WorkflowExecutionGuard ABC | `src/workflow_runtime/locking/execution_guard.py` | Abstract class with `execute` method. Context manager support. Docstring documents lifecycle. |
| 1.5 | WorkflowIdempotencyRegistry ABC | `src/workflow_runtime/locking/idempotency.py` | Abstract class with `check`, `record`, `cleanup` methods. |
| 1.6 | Custom exceptions | `src/workflow_runtime/locking/exceptions.py` | `LockAcquisitionError`, `IdempotencyRejectionError`, `LockProviderError`, `LeaseRefreshError` defined. Each has informative attributes. |
| 1.7 | Database migration scripts | `scripts/migrations/006_create_workflow_locks_table.sql`, `scripts/migrations/007_create_workflow_idempotency_table.sql` | SQL scripts tested against empty database. Create and rollback verified. |
| 1.8 | Configuration parameters | `src/config.py` modifications | New constants added with documented defaults. No existing config keys changed. |

### Dependencies

- **Required**: None — Phase 1 is the starting point
- **Consumed By**: Phase 2 (all deliverables), Phase 3 (data models)
- **External**: Python standard library (`dataclasses`, `abc`, `typing`)

### Effort Estimate

| Task | Duration (hours) | Details |
|------|-----------------|---------|
| 1.1 Package skeleton | 0.5 | Create directory structure, `__init__.py` with module docstring |
| 1.2 Data models | 1.0 | Two frozen dataclasses with fields, type annotations, docstrings |
| 1.3 LockProvider ABC | 1.5 | ABC with 3 abstract methods, type annotations, contract docstrings |
| 1.4 ExecutionGuard ABC | 1.0 | ABC with 1 abstract method + context manager protocol |
| 1.5 IdempotencyRegistry ABC | 1.0 | ABC with 3 abstract methods |
| 1.6 Custom exceptions | 0.5 | 4 exception classes with constructors and attributes |
| 1.7 Migration scripts | 1.5 | 2 SQL scripts with create, index, rollback. Tested manually. |
| 1.8 Configuration | 1.0 | 11 constants added to config module. |
| **Total** | **8.0 hours (1 day)** | |

### Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **ABC interface design mistake** | Medium — changes to ABCs after Phase 2 started cause rework | Low | ABCs are minimal (3 methods each). Use architecture plan as specification. |
| **Migration script syntax error** | Low — migration fails on execution | Medium | Test scripts against a fresh SQLite database before committing. |
| **Configuration namespace collision** | Low — config var name conflicts with existing | Low | Prefix all new config vars with `LOCK_` and `IDEMPOTENCY_`. |
| **Missed edge case in data models** | Medium — downstream code may need additional fields | Low | Start with fields from architecture plan. Add fields as needed in Phase 2. |

---

## Phase 2 — Locking Infrastructure

### Purpose

Implement all concrete lock providers, the provider registry with fallback chain, the idempotency registry, the execution guard with lease refresh, and the stale lock cleanup mechanism. Phase 2 produces the complete locking subsystem, ready for integration into the workflow runner.

### Deliverables

| # | Deliverable | File(s) | Acceptance Criteria |
|---|-------------|---------|---------------------|
| 2.1 | MemoryLockProvider | `src/workflow_runtime/locking/providers/memory_lock_provider.py` | Passes all ABC contract tests. Thread-safe. No memory leaks. |
| 2.2 | FileLockProvider | `src/workflow_runtime/locking/providers/file_lock_provider.py` | Passes all ABC contract tests. Correct lock file creation/deletion. Cross-platform (Windows + POSIX). Stale detection works. |
| 2.3 | DBLockProvider | `src/workflow_runtime/locking/providers/db_lock_provider.py` | Passes all ABC contract tests. Uses `workflow_locks` table. UPSERT semantics. Handles DB connection errors. |
| 2.4 | LockProviderRegistry | `src/workflow_runtime/locking/lock_provider.py` | Registers providers with priority. Resolves by name and default. Fallback chain works (DB → File → Memory → error). |
| 2.5 | WorkflowIdempotencyRegistry | `src/workflow_runtime/locking/idempotency.py` | DB-backed implementation. Atomic key insertion. TTL-based cleanup. |
| 2.6 | WorkflowExecutionGuard | `src/workflow_runtime/locking/execution_guard.py` | Wraps function execution with lock lifecycle. Context manager support. Retry with backoff. Skips completed idempotency keys. |
| 2.7 | Lease refresh loop | `src/workflow_runtime/locking/execution_guard.py` | Periodic lease refresh during execution. Non-fatal refresh failures (log warning). Refresh interval configurable. |
| 2.8 | Stale lock cleanup | `src/workflow_runtime/locking/providers/db_lock_provider.py` (method) | Deletes locks where `expires_at < NOW()`. Called periodically or on provider initialization. |

### Implementation Details

#### 2.1 MemoryLockProvider

```python
class MemoryLockProvider(LockProvider):
    """In-memory lock provider. NOT suitable for production — use for tests and dev only."""

    def __init__(self):
        self._locks: dict[str, LockAcquisition] = {}
        self._lock = threading.Lock()

    def acquire(self, lock_id: str, holder_id: str, lease_duration_s: int) -> Optional[LockAcquisition]:
        with self._lock:
            existing = self._locks.get(lock_id)
            if existing and existing.expires_at > datetime.utcnow():
                return None  # lock is held
            # Acquire lock
            acquisition = LockAcquisition(...)
            self._locks[lock_id] = acquisition
            return acquisition

    def release(self, lock: LockAcquisition) -> bool:
        with self._lock:
            if self._locks.get(lock.lock_id)?.holder_id != lock.holder_id:
                return False
            del self._locks[lock.lock_id]
            return True

    def refresh(self, lock: LockAcquisition) -> Optional[LockAcquisition]:
        with self._lock:
            existing = self._locks.get(lock.lock_id)
            if not existing or existing.holder_id != lock.holder_id:
                return None
            # Extend expiry
            new_acquisition = ...  # updated expires_at
            self._locks[lock.lock_id] = new_acquisition
            return new_acquisition
```

#### 2.2 FileLockProvider

```python
class FileLockProvider(LockProvider):
    """File-based lock provider. Suitable for single-host deployments."""

    def __init__(self, lock_dir: str):
        self._lock_dir = Path(lock_dir)
        self._lock_dir.mkdir(parents=True, exist_ok=True)

    def _lock_path(self, lock_id: str) -> Path:
        return self._lock_dir / f"{lock_id}.lock"

    def acquire(self, lock_id: str, holder_id: str, lease_duration_s: int) -> Optional[LockAcquisition]:
        lock_path = self._lock_path(lock_id)
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            # Lock file exists — check if stale
            if self._is_stale(lock_path):
                os.remove(lock_path)  # Clear stale lock
                return self.acquire(lock_id, holder_id, lease_duration_s)  # Retry
            return None
        # Write metadata
        metadata = {...}
        with os.fdopen(fd, 'w') as f:
            json.dump(metadata, f)
        return LockAcquisition(...)

    def release(self, lock: LockAcquisition) -> bool:
        lock_path = self._lock_path(lock.lock_id)
        if not lock_path.exists():
            return True  # Already released
        # Verify holder
        with open(lock_path) as f:
            metadata = json.load(f)
        if metadata['holder_id'] != lock.holder_id:
            return False  # Not our lock
        os.remove(lock_path)
        return True

    def refresh(self, lock: LockAcquisition) -> Optional[LockAcquisition]:
        # Update metadata in lock file
        ...
```

#### 2.3 DBLockProvider

```python
class DBLockProvider(LockProvider):
    """Database-backed lock provider with execution leases."""

    def __init__(self, db_connection, table_name: str = "workflow_locks"):
        self._db = db_connection
        self._table = table_name

    def acquire(self, lock_id: str, holder_id: str, lease_duration_s: int) -> Optional[LockAcquisition]:
        cursor = self._db.cursor()
        # Try UPSERT: if lock exists and NOT expired, UPSERT does nothing (conflict)
        # If lock exists and IS expired, UPSERT replaces it
        cursor.execute(f"""
            INSERT INTO {self._table} (lock_id, holder_id, acquired_at, expires_at, lease_duration_s, hostname, pid)
            VALUES (?, ?, datetime('now'), datetime('now', '+' || ? || ' seconds'), ?, ?, ?)
            ON CONFLICT(lock_id) DO UPDATE SET
                holder_id = EXCLUDED.holder_id,
                acquired_at = EXCLUDED.acquired_at,
                expires_at = EXCLUDED.expires_at,
                hostname = EXCLUDED.hostname,
                pid = EXCLUDED.pid,
                refresh_count = 0,
                last_refreshed_at = datetime('now')
            WHERE workflow_locks.expires_at < datetime('now')
        """, (lock_id, holder_id, lease_duration_s, lease_duration_s, socket.gethostname(), os.getpid()))
        self._db.commit()
        # Check if we actually acquired the lock
        cursor.execute(f"SELECT holder_id FROM {self._table} WHERE lock_id = ?", (lock_id,))
        row = cursor.fetchone()
        if row['holder_id'] != holder_id:
            return None  # Someone else holds the lock
        return LockAcquisition(...)

    def release(self, lock: LockAcquisition) -> bool:
        cursor = self._db.cursor()
        cursor.execute(f"DELETE FROM {self._table} WHERE lock_id = ? AND holder_id = ?",
                       (lock.lock_id, lock.holder_id))
        self._db.commit()
        return cursor.rowcount > 0

    def refresh(self, lock: LockAcquisition) -> Optional[LockAcquisition]:
        cursor = self._db.cursor()
        cursor.execute(f"""
            UPDATE {self._table}
            SET expires_at = datetime('now', '+' || ? || ' seconds'),
                refresh_count = refresh_count + 1,
                last_refreshed_at = datetime('now')
            WHERE lock_id = ? AND holder_id = ?
        """, (lock.lease_duration_s, lock.lock_id, lock.holder_id))
        self._db.commit()
        if cursor.rowcount == 0:
            return None  # Lock lost or expired
        # Return updated acquisition
        return LockAcquisition(...)

    def cleanup_stale(self) -> int:
        cursor = self._db.cursor()
        cursor.execute(f"DELETE FROM {self._table} WHERE expires_at < datetime('now')")
        self._db.commit()
        return cursor.rowcount
```

### Dependencies

- **Requires**: Phase 1 (models, ABCs, exceptions, config, migration scripts)
- **Consumed By**: Phase 3 (integration), Phase 4 (testing of providers)

### Effort Estimate

| Task | Duration (hours) | Details |
|------|-----------------|---------|
| 2.1 MemoryLockProvider | 2.0 | Thread-safe implementation with threading.Lock |
| 2.2 FileLockProvider | 4.0 | Cross-platform file locking, stale detection, metadata |
| 2.3 DBLockProvider | 6.0 | SQL construction, UPSERT logic, error handling, connection management |
| 2.4 LockProviderRegistry | 2.0 | Registry with priority ordering and fallback chain |
| 2.5 WorkflowIdempotencyRegistry | 3.0 | DB-backed implementation, atomic insert, TTL cleanup |
| 2.6 WorkflowExecutionGuard | 4.0 | Lock lifecycle wrapping, retry with backoff, context manager |
| 2.7 Lease refresh loop | 3.0 | Periodic refresh, failure handling, configurable interval |
| 2.8 Stale lock cleanup | 1.0 | Cleanup method on DBLockProvider, periodic trigger |
| **Total** | **25.0 hours (3.5 days)** | |

### Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **File locking cross-platform issues** | Medium — file locks behave differently on Windows | Medium | Test on Windows CI. Implement with platform detection (`sys.platform`). Fallback to existence-check pattern if locking APIs are unreliable. |
| **SQL injection via lock_id** | High — if lock_id contains malicious characters | Low | Use parameterized queries (always). Sanitize table name (use config constant). |
| **DB connection pool exhaustion** | Medium — all workers waiting for lock | Low | Implement connection timeout and retry. File provider fallback mitigates. |
| **Lease refresh timing issues** | Medium — refresh interval vs lease TTL ratio | Medium | Enforce `lease_duration_s >= REFRESH_INTERVAL_S * 3` in guard constructor. |

---

## Phase 3 — Workflow Integration

### Purpose

Integrate the locking infrastructure into the existing Workflow Runtime. Update contracts, modify `WorkflowRunner.run()` to use the execution guard, add idempotency key generation for scheduled runs, and implement error handling for lock/idempotency rejections. Phase 3 produces a fully functional locked workflow runtime.

### Deliverables

| # | Deliverable | Files Modified | Acceptance Criteria |
|---|-------------|----------------|---------------------|
| 3.1 | Updated ExecutionContext | `src/workflow_runtime/contracts/execution_context.py` | New `lock_acquisition` and `idempotency_key` fields. All existing fields unchanged. Backward compatible. |
| 3.2 | Updated WorkflowResult | `src/workflow_runtime/contracts/workflow_result.py` | New `idempotency_key` and `lock_status` fields. All existing fields unchanged. Backward compatible. |
| 3.3 | Guard integrated into run() | `src/workflow_runtime/runtime/workflow_runner.py` | `run()` method uses `WorkflowExecutionGuard`. Lock acquired before execution, released after. |
| 3.4 | Idempotency key generation | `src/workflow_runtime/runtime/workflow_runner.py`, `src/scheduler.py` | Scheduled runs generate deterministic keys. Manual runs skip key generation. |
| 3.5 | Lock acquisition error handling | `src/workflow_runtime/runtime/workflow_runner.py` | `LockAcquisitionError` caught and returned as `WorkflowResult` with `lock_status="rejected_busy"` |
| 3.6 | Idempotency rejection handling | `src/workflow_runtime/runtime/workflow_runner.py` | `IdempotencyRejectionError` caught. Returns cached `WorkflowResult` from idempotency registry. |

### Integration Points

#### 3.3 WorkflowRunner.run() — Modified Lifecycle

```python
def run(self, definition, initial_artifact, metadata=None):
    """Execute workflow with locking."""
    # Phase 1: Validate (unchanged)
    self._validator.validate_or_raise(definition)

    # Phase 2: Build DAG (unchanged)
    stages = self._dag_builder.build(definition)

    # Phase 3: Create context (unchanged)
    context = ExecutionContext(
        pipeline_run_id=str(uuid4()),
        workflow_id=definition.workflow_id,
        workspace_id=definition.workspace_id,
        # NEW: lock fields added
    )

    # Phase 4: Generate idempotency key (if scheduled)
    idempotency_key = None
    if metadata and metadata.get('trigger_type') == 'scheduled':
        schedule_date = metadata.get('schedule_date')
        idempotency_key = f"{definition.workflow_id}-{schedule_date}"

    # Phase 5: Execute with guard
    if self._execution_guard is not None:
        try:
            result = self._execution_guard.execute(
                workflow_id=definition.workflow_id,
                holder_id=context.pipeline_run_id,
                idempotency_key=idempotency_key,
                fn=lambda: self._execute_stages(stages, initial_artifact, context),
            )
            # Unpack result
            artifact, lock_acquisition = result
            context.lock_acquisition = lock_acquisition
        except LockAcquisitionError as e:
            return WorkflowResult(
                overall_status="REJECTED",
                lock_status="rejected_busy",
                error=str(e),
                idempotency_key=idempotency_key,
            )
        except IdempotencyRejectionError as e:
            return WorkflowResult(
                overall_status="SKIPPED",
                lock_status="rejected_duplicate",
                idempotency_key=idempotency_key,
                error=f"Duplicate run: {e.existing_pipeline_run_id}",
            )
    else:
        # No guard configured — execute as before (backward compat)
        artifact = self._execute_stages(stages, initial_artifact, context)

    # Phase 6: Build result (unchanged)
    result = WorkflowResult(
        overall_status="COMPLETED",
        idempotency_key=idempotency_key,
        lock_status="acquired" if self._execution_guard else "not_locked",
    )
    return result
```

#### 3.4 Idempotency Key Generation

```python
# In scheduler.py or trigger code:
def generate_idempotency_key(workflow_id: str, schedule_time: datetime) -> str:
    """Generate deterministic idempotency key for a scheduled run."""
    schedule_slot = schedule_time.strftime("%Y-%m-%dT%H:%M")
    return f"{workflow_id}-scheduled-{schedule_slot}"

# Passed to WorkflowRunner.run() via metadata:
metadata = {
    "trigger_type": "scheduled",
    "schedule_date": schedule_slot,
}
runner.run(definition, initial_artifact, metadata=metadata)
```

### Dependencies

- **Requires**: Phase 2 (all locking infrastructure deliverables)
- **Consumed By**: Phase 4 (integration tests, performance benchmarks)
- **External Testing**: Manual run of existing workflows to confirm backward compatibility

### Effort Estimate

| Task | Duration (hours) | Details |
|------|-----------------|---------|
| 3.1 Update ExecutionContext | 1.0 | Add 2 Optional fields with None defaults |
| 3.2 Update WorkflowResult | 1.0 | Add 2 Optional fields with None defaults |
| 3.3 Integrate guard in run() | 6.0 | Modify execution lifecycle, maintain backward compatibility |
| 3.4 Idempotency key generation | 1.0 | Helper function, update trigger code |
| 3.5 Lock acquisition error handling | 1.5 | Catch exceptions, return appropriate WorkflowResult |
| 3.6 Idempotency rejection handling | 1.5 | Catch exceptions, return cached result |
| **Total** | **12.0 hours (2 days)** | |

### Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Backward compatibility breakage** | High — existing callers break | Low | All changes use Optional fields with None defaults. `__init__()` accepts optional guard. |
| **Integration timing issues** | Medium — lock held too long or released too early | Low | Execution guard uses context manager for reliable acquire/release. |
| **Error handling too aggressive** | Medium — locking errors propagated unnecessarily | Low | Catch lock/idempotency errors at guard boundary. Return as WorkflowResult, not exceptions. |
| **Idempotency key collision with manual runs** | Low — manual runs don't generate keys | Low | Only scheduled runs generate keys. Manual runs remain un-keyed. |

---

## Phase 4 — Testing

### Purpose

Validate the complete locking subsystem through unit tests, integration tests, performance benchmarks, and boundary verification. Phase 4 ensures correctness, robustness, and no regressions in the existing codebase.

### Deliverables

| # | Deliverable | File(s) | Acceptance Criteria |
|---|-------------|---------|---------------------|
| 4.1 | LockProvider ABC contract tests | `tests/locking/test_lock_provider.py` | 10 parametrized test cases. Each concrete provider runs against these. |
| 4.2 | MemoryLockProvider tests | `tests/locking/test_memory_lock_provider.py` | All contract tests pass + thread safety + cleanup tests |
| 4.3 | FileLockProvider tests | `tests/locking/test_file_lock_provider.py` | All contract tests pass + file creation/deletion + cross-platform tests |
| 4.4 | DBLockProvider tests | `tests/locking/test_db_lock_provider.py` | All contract tests pass + SQL injection + connection failure + stale cleanup |
| 4.5 | LockProviderRegistry tests | `tests/locking/test_lock_provider_registry.py` | 6 test cases for resolution, fallback, failure |
| 4.6 | IdempotencyRegistry tests | `tests/locking/test_workflow_idempotency_registry.py` | 8 test cases for check, record, conflict, cleanup |
| 4.7 | ExecutionGuard tests | `tests/locking/test_workflow_execution_guard.py` | 8 test cases for lifecycle, duplicate prevention, crash recovery, context manager |
| 4.8 | Lease refresh tests | `tests/locking/test_lease_refresh.py` | 4 test cases for refresh timing, failure handling |
| 4.9 | Concurrent execution tests | `tests/locking/test_integration_concurrent.py` | 5 scenarios — same workflow, different workflows, staggered, scheduled+manual, 10-way |
| 4.10 | Crash recovery tests | `tests/locking/test_integration_crash_recovery.py` | 4 scenarios — basic recovery, mid-refresh, graceful, with idempotency |
| 4.11 | Provider fallback tests | `tests/locking/test_integration_fallback.py` | 4 scenarios — DB→File, File→Memory, all fail, fallback performance |
| 4.12 | Idempotency integration tests | `tests/locking/test_integration_idempotency.py` | 4 scenarios — basic dedup, with lock, concurrent, TTL |
| 4.13 | Performance benchmarks | `tests/locking/test_performance_benchmarks.py` | 8 benchmarks with verified p50/p99 targets |
| 4.14 | Boundary verification | `scripts/verify_boundaries.py` run | All R01–R05, R12 rules pass. No new violations. |

### Test Data

```python
# conftest.py fixtures

@pytest.fixture
def memory_lock_provider():
    """Fresh MemoryLockProvider instance."""
    return MemoryLockProvider()

@pytest.fixture
def temp_lock_dir(tmp_path):
    """Temporary directory for file lock tests."""
    return tmp_path / ".locks"

@pytest.fixture
def file_lock_provider(temp_lock_dir):
    """Fresh FileLockProvider instance."""
    return FileLockProvider(str(temp_lock_dir))

@pytest.fixture
def db_connection():
    """In-memory SQLite database for DB lock tests."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""CREATE TABLE workflow_locks (...); CREATE TABLE workflow_idempotency (...);""")
    yield conn
    conn.close()

@pytest.fixture
def db_lock_provider(db_connection):
    """Fresh DBLockProvider instance."""
    return DBLockProvider(db_connection)

@pytest.fixture
def sample_lock_acquisition():
    """Sample valid LockAcquisition instance."""
    return LockAcquisition(
        lock_id="test_workflow",
        holder_id="host-1234-abc",
        acquired_at="2026-06-03T08:00:00",
        expires_at="2026-06-03T08:05:00",
        lease_duration_s=300,
    )

@pytest.fixture
def execution_guard(memory_lock_provider):
    """WorkflowExecutionGuard with MemoryLockProvider."""
    return WorkflowExecutionGuard(lock_provider=memory_lock_provider)

@pytest.fixture
def guarded_runner(execution_guard, mock_idempotency_registry):
    """WorkflowRunner with guard configured."""
    runner = WorkflowRunner(execution_guard=execution_guard, idempotency_registry=mock_idempotency_registry)
    return runner
```

### Effort Estimate

| Task | Duration (hours) | Details |
|------|-----------------|---------|
| 4.1 ABC contract tests | 3.0 | Parametrized test base class. 10 scenarios. |
| 4.2 MemoryLockProvider tests | 1.5 | Inherit contract tests + 3 additional |
| 4.3 FileLockProvider tests | 3.0 | Inherit + 5 additional (file I/O, cross-platform) |
| 4.4 DBLockProvider tests | 3.0 | Inherit + 5 additional (SQL, connection, cleanup) |
| 4.5 LockProviderRegistry tests | 1.5 | 6 test cases |
| 4.6 IdempotencyRegistry tests | 2.0 | 8 test cases |
| 4.7 ExecutionGuard tests | 3.0 | 8 test cases (requires mocked WorkflowRunner) |
| 4.8 Lease refresh tests | 2.0 | 4 test cases (time-based, requires mock clock) |
| 4.9 Concurrent execution tests | 3.0 | 5 scenarios (requires threading) |
| 4.10 Crash recovery tests | 2.0 | 4 scenarios (requires time simulation) |
| 4.11 Provider fallback tests | 2.0 | 4 scenarios |
| 4.12 Idempotency integration tests | 1.5 | 4 scenarios |
| 4.13 Performance benchmarks | 2.0 | 8 benchmarks with pytest-benchmark |
| 4.14 Boundary verification | 0.5 | Run existing script, verify output |
| **Total** | **29.5 hours (3.5 days)** | |

### Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Flaky time-based tests** | Medium — lease refresh tests dependent on real time | High | Use `unittest.mock.patch` for `datetime.utcnow()`. Control time deterministically. |
| **Threading test non-determinism** | Medium — concurrent tests may pass/fail intermittently | Medium | Use `threading.Barrier` for synchronized start. Add `timeout` to assertions. Repeat test 5x in CI. |
| **Boundary verification regression** | Low — new module may import from restricted packages | Low | Run `verify_boundaries.py` as a pre-commit hook. Fix violations immediately. |
| **Performance benchmarks flaky in CI** | Low — benchmark numbers vary on shared CI runners | Low | Set generous targets (p50 <10ms, p99 <50ms) that pass even on loaded systems. |

---

## Phase 5 — Documentation And Release

### Purpose

Create all governance-required documentation, update existing project documents, and execute the release process. Phase 5 ensures the milestone is fully documented and released according to project governance rules.

### Deliverables

| # | Deliverable | Location | Acceptance Criteria |
|---|-------------|----------|---------------------|
| 5.1 | Architecture Summary | `docs/architecture/WORKFLOW_RUNTIME_LOCKING_V1_SUMMARY.md` | Documents what was built, design decisions, configuration, file layout. Follows SUMMARY template from previous milestones. |
| 5.2 | Handoff Document | `docs/architecture/WORKFLOW_RUNTIME_LOCKING_V1_HANDOFF.md` | Contains runbook, rollback steps, migration guide, monitoring requirements, known issues. |
| 5.3 | ADR-008 | `docs/adr/ADR-008-workflow-runtime-locking.md` | Decision record documenting: problem, evaluated strategies (6), selected strategy (DB-backed + leases + idempotency), rationale, rejected alternatives. |
| 5.4 | ROADMAP update | `docs/ROADMAP.md` | "Workflow Runtime Locking" marked as completed under v0.5 Runtime Hardening. |
| 5.5 | TECHNICAL_DEBT update | `TECHNICAL_DEBT.md` | "Lack of distributed locking; potential duplicate job execution" — status changed to CLOSED. Resolution reference added. |
| 5.6 | V0_5 plan update | `docs/architecture/V0_5_RUNTIME_HARDENING_PLAN.md` | Workflow Runtime Locking section status updated to "Completed". |
| 5.7 | Release notes | `CHANGELOG.md` | New entry: "v0.5-workflow-runtime-locking — Added distributed locking with leases and idempotency keys". Lists all new files and changes. |
| 5.8 | Git commit | Repository | Commit message: `feat: implement v0.5 workflow runtime locking`. Contains all new and modified files. |
| 5.9 | Git push + tag | Remote repository | Push to main branch. Tag: `v0.5-workflow-runtime-locking`. |

### Document Templates

#### 5.1 Summary Document Structure

```markdown
# Workflow Runtime Locking v1 — Implementation Summary

**Date**: 2026-06-XX
**Author**: [Developer Name]
**Status**: Complete
**Milestone**: v0.5-workflow-runtime-locking

## Problem Solved
[Brief description of the duplicate execution problem]

## Solution
[Database-backed locking with leases + idempotency keys + file fallback]

## Key Design Decisions
1. Database-backed lock as primary strategy
2. Execution leases for crash recovery
3. Idempotency keys for deduplication of completed runs
4. File lock as fallback for single-host deployments
5. In-memory lock for testing and development

## Configuration
[Table of all new config parameters with defaults]

## File Layout
[Directory tree of new and modified files]

## Test Results
[Summary of test counts, pass rates, performance benchmarks]

## Known Issues
[Any unresolved issues or limitations]
```

#### 5.2 Handoff Document Structure

```markdown
# Workflow Runtime Locking v1 — Handoff Document

## Runbook
[How to operate the locking system]

## Migration Guide
[How existing deployments migrate to use locking]

## Rollback Procedure
[Step-by-step rollback for locking]

## Monitoring
[What to monitor: lock errors, latency, fallback events]

## Troubleshooting
[Common issues and resolutions]

## Future Work (v2+)
[Distributed locking, dynamic lease TTL, dead-letter queue]
```

### Dependencies

- **Requires**: Phase 4 (all tests passing, boundaries verified)
- **External**: Git access, repository write permissions

### Effort Estimate

| Task | Duration (hours) | Details |
|------|-----------------|---------|
| 5.1 Summary document | 3.0 | Follow structure from previous milestones. 2-3 pages. |
| 5.2 Handoff document | 3.0 | Operations-focused. Runbook, rollback, monitoring. |
| 5.3 ADR-008 | 2.0 | ADR template. Problem, options, decision, consequences. |
| 5.4 ROADMAP update | 0.5 | Mark item as completed. Update status table. |
| 5.5 TECHNICAL_DEBT update | 0.5 | Close debt item with reference to plan. |
| 5.6 V0_5 plan update | 0.5 | Update section status. |
| 5.7 Release notes | 0.5 | CHANGELOG entry summarizing changes. |
| 5.8 Git commit | 0.5 | Stage all files, commit with standard message format. |
| 5.9 Git push + tag | 0.5 | Push commit and tag to remote. |
| **Total** | **11.0 hours (2 days)** | |

### Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Documentation drift** | Medium — docs may become outdated if code changes during testing | Medium | Write docs last, after all code changes are stable. |
| **GH Actions or Git push failure** | Low — release cannot be completed | Low | Have local backup of all files. Use `git push --force-with-lease` if needed. |
| **Milestone tag already exists** | Low — tag collision | Low | Use `git tag -d` to delete local tag if it exists from a previous attempt. |

---

## Appendix A: Governance Checklist

Per `PROJECT_CONTEXT.md` governance rules, the following artifacts are required:

| Artifact | Status | Location |
|----------|--------|----------|
| Architecture document | ✅ Existing | `docs/architecture/WORKFLOW_RUNTIME_LOCKING_V1_PLAN.md` |
| Implementation document | ✅ This document | `docs/architecture/WORKFLOW_RUNTIME_LOCKING_V1_IMPLEMENTATION_PLAN.md` |
| Summary document | 🔲 Phase 5 | `docs/architecture/WORKFLOW_RUNTIME_LOCKING_V1_SUMMARY.md` |
| Handoff document | 🔲 Phase 5 | `docs/architecture/WORKFLOW_RUNTIME_LOCKING_V1_HANDOFF.md` |
| ADR updates | 🔲 Phase 5 | `docs/adr/ADR-008-workflow-runtime-locking.md` |
| Technical debt update | 🔲 Phase 5 | `TECHNICAL_DEBT.md` |
| Roadmap update | 🔲 Phase 5 | `docs/ROADMAP.md` |
| Release notes | 🔲 Phase 5 | `CHANGELOG.md` |
| Git commit | 🔲 Phase 5 | Repository |
| Git push | 🔲 Phase 5 | Remote repository |
| Milestone tag | 🔲 Phase 5 | `v0.5-workflow-runtime-locking` |

## Appendix B: Related Documents

| Document | Location | Relationship |
|----------|----------|--------------|
| Architecture Plan | `docs/architecture/WORKFLOW_RUNTIME_LOCKING_V1_PLAN.md` | Source plan for this implementation |
| Next Milestone Recommendation | `docs/architecture/NEXT_MILESTONE_RECOMMENDATION.md` | Prioritizes locking as #1 milestone (9/10) |
| Project Context | `docs/architecture/PROJECT_CONTEXT.md` | Governance rules, Definition of Done |
| ROADMAP | `docs/ROADMAP.md` | Milestone tracking |
| Technical Debt | `TECHNICAL_DEBT.md` | Lists locking as known debt |
| V0.5 Runtime Hardening Plan | `docs/architecture/V0_5_RUNTIME_HARDENING_PLAN.md` | Parent milestone plan |
| Boundary Verification Implementation | `docs/architecture/RUNTIME_BOUNDARY_VERIFICATION_V1_IMPLEMENTATION.md` | Preceding milestone pattern to follow |

## Appendix C: Definition of Done Verification Script

The following verification steps should be run before declaring the milestone complete:

```bash
#!/bin/bash
# Definition of Done Verification

echo "=== Phase 1 Verification ==="
# Verify package structure
test -f src/workflow_runtime/locking/__init__.py && echo "✅ Package exists" || echo "❌ Package missing"
test -f src/workflow_runtime/locking/models.py && echo "✅ Models exist" || echo "❌ Models missing"
test -f src/workflow_runtime/locking/lock_provider.py && echo "✅ LockProvider exists" || echo "❌ LockProvider missing"
test -f src/workflow_runtime/locking/execution_guard.py && echo "✅ ExecutionGuard exists" || echo "❌ ExecutionGuard missing"
test -f src/workflow_runtime/locking/idempotency.py && echo "✅ Idempotency exists" || echo "❌ Idempotency missing"
test -f src/workflow_runtime/locking/exceptions.py && echo "✅ Exceptions exist" || echo "❌ Exceptions missing"

echo "=== Phase 2 Verification ==="
test -f src/workflow_runtime/locking/providers/db_lock_provider.py && echo "✅ DBLockProvider exists" || echo "❌ DBLockProvider missing"
test -f src/workflow_runtime/locking/providers/file_lock_provider.py && echo "✅ FileLockProvider exists" || echo "❌ FileLockProvider missing"
test -f src/workflow_runtime/locking/providers/memory_lock_provider.py && echo "✅ MemoryLockProvider exists" || echo "❌ MemoryLockProvider missing"

echo "=== Phase 3 Verification ==="
# Verify integration (compile check)
python -c "from src.workflow_runtime.locking import LockAcquisition, LockAcquisitionError, LockProvider, WorkflowExecutionGuard" && echo "✅ Imports work" || echo "❌ Imports failed"

echo "=== Phase 4 Verification ==="
python -m pytest tests/locking/ -v --tb=short -q | tail -5
python scripts/verify_boundaries.py | tail -3

echo "=== Phase 5 Verification ==="
test -f docs/architecture/WORKFLOW_RUNTIME_LOCKING_V1_SUMMARY.md && echo "✅ Summary exists" || echo "❌ Summary missing"
test -f docs/architecture/WORKFLOW_RUNTIME_LOCKING_V1_HANDOFF.md && echo "✅ Handoff exists" || echo "❌ Handoff missing"
test -f docs/adr/ADR-008-workflow-runtime-locking.md && echo "✅ ADR exists" || echo "❌ ADR missing"

echo "=== Final Check ==="
echo "All checks passed: $(date)"
```

---

## End of Implementation Plan