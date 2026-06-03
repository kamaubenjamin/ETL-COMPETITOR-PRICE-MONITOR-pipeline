# Workflow Runtime Locking v1 — Implementation Summary

**Date**: 2026-06-03  
**Author**: Platform Architecture Review  
**Status**: Phase 1 Complete  
**Milestone**: v0.5-workflow-runtime-locking  
**Phase**: 1 — Foundation

---

## Problem Solved

The Workflow Runtime had no mechanism to prevent the same workflow from being executed concurrently by multiple invocations. This created risks of:

- Duplicate workflow execution (scheduled + manual overlap)
- Duplicate downstream side-effects (alerts, reports, debug artifacts)
- Incorrect aggregated state (entity runtime merges, dashboard metrics)
- No audit trail for duplicate runs
- No execution leasing or crash recovery

## Solution (Phase 1 — Foundation)

Phase 1 establishes the structural foundation for the locking subsystem: package layout, immutable data contracts, abstract interfaces, custom exceptions, database schema, and configuration defaults.

### Strategy

- **Primary**: Database-backed row-level locking with execution leases
- **Fallback**: File-based advisory locking for single-host deployments
- **Development/Test**: In-memory locking
- **Complementary**: Idempotency keys for deduplication of completed runs

## Files Created

### Source Files (8 files)

| File | Purpose |
|------|---------|
| `src/workflow_runtime/locking/__init__.py` | Public API — exports all classes, exceptions, helper types. Module docstring documents strategy. |
| `src/workflow_runtime/locking/models.py` | `LockAcquisition` and `IdempotencyRecord` frozen dataclasses with `__slots__` |
| `src/workflow_runtime/locking/exceptions.py` | `LockAcquisitionError`, `IdempotencyRejectionError`, `LockProviderError`, `LeaseRefreshError` |
| `src/workflow_runtime/locking/lock_provider.py` | `LockProvider` ABC (acquire, release, refresh) + `LockProviderRegistry` with priority ordering |
| `src/workflow_runtime/locking/execution_guard.py` | `WorkflowExecutionGuard` ABC — wraps execution lifecycle with lock lifecycle. Context manager support. |
| `src/workflow_runtime/locking/idempotency.py` | `WorkflowIdempotencyRegistry` ABC (check, record, cleanup) |
| `src/workflow_runtime/locking/providers/__init__.py` | Package init for concrete provider implementations (Phase 2) |
| `src/workflow_runtime/locking/config.py` | 13 configuration constants with documented defaults |

### Migration Scripts (2 files)

| File | Purpose |
|------|---------|
| `scripts/migrations/006_create_workflow_locks_table.sql` | `workflow_locks` table with UPSERT support, indexes on `expires_at` and `holder_id` |
| `scripts/migrations/007_create_workflow_idempotency_table.sql` | `workflow_idempotency` table with CHECK constraint on status, indexes on `created_at` and `status` |

### Modified Files (1 file)

| File | Change |
|------|--------|
| `src/workflow_runtime/__init__.py` | Re-exports all locking classes for convenient importing |

### Test Files (4 files)

| File | Tests |
|------|-------|
| `tests/locking/__init__.py` | Test package init |
| `tests/locking/conftest.py` | Shared fixtures: `sample_lock_acquisition`, `sample_idempotency_record`, expired/in-progress/failed variants |
| `tests/locking/test_models.py` | 21 tests — construction, immutability, slots, equality, repr |
| `tests/locking/test_exceptions.py` | 19 tests — construction, attributes on catch, custom messages, hierarchy |

## Key Design Decisions

### 1. Frozen dataclasses with `__slots__`
- Ensures immutability — once a `LockAcquisition` is created, it cannot be modified
- `__slots__` provides memory efficiency and prevents new attribute creation
- Choice of `@dataclass(frozen=True, slots=True)` over `NamedTuple` for clarity and extensibility

### 2. ABCs for all interfaces
- `LockProvider` ABC defines the three-method contract (`acquire`, `release`, `refresh`)
- `WorkflowExecutionGuard` ABC defines the `execute()` lifecycle
- `WorkflowIdempotencyRegistry` ABC defines key management (`check`, `record`, `cleanup`)
- Enables multiple implementations and test mocking

### 3. Informative exception types
- Each exception carries structured attributes for retry logic and logging
- `LockAcquisitionError` has `lock_id`, `current_holder_id`, `expires_at`
- `IdempotencyRejectionError` has `idempotency_key`, `existing_status`, `existing_pipeline_run_id`
- All exceptions support optional custom messages

### 4. Separate configuration module
- `src/workflow_runtime/locking/config.py` contains canonical defaults
- All constants prefixed with `LOCK_` or `IDEMPOTENCY_` to avoid namespace collision
- Provider priorities defined as constants for `LockProviderRegistry`

### 5. SQLite-compatible migrations
- Uses `datetime('now')` SQLite function for cross-platform compatibility
- `IF NOT EXISTS` on all CREATE statements for idempotent migration
- Indexes on query-critical columns (`expires_at`, `holder_id`, `created_at`, `status`)

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `LOCK_PROVIDER` | `"database"` | Primary lock provider: database / file / memory |
| `LOCK_DEFAULT_LEASE_S` | `300` | Default lease duration in seconds (5 min) |
| `LOCK_REFRESH_INTERVAL_S` | `30` | Lease refresh interval in seconds |
| `LOCK_MAX_RETRIES` | `3` | Max lock acquisition retries |
| `LOCK_RETRY_DELAY_S` | `5` | Base retry delay in seconds |
| `LOCK_DB_TABLE` | `"workflow_locks"` | Database table for locks |
| `LOCK_FILE_DIR` | `".locks"` | Directory for file-based locks |
| `IDEMPOTENCY_ENABLED` | `True` | Enable idempotency key checking |
| `IDEMPOTENCY_KEY_TTL_DAYS` | `7` | Days to keep completed keys |
| `IDEMPOTENCY_DB_TABLE` | `"workflow_idempotency"` | Database table for idempotency |

## File Layout

```
src/workflow_runtime/locking/
├── __init__.py                          # Public API + module docstring
├── config.py                            # Configuration constants (NEW)
├── models.py                            # LockAcquisition, IdempotencyRecord (NEW)
├── exceptions.py                        # 4 custom exception types (NEW)
├── lock_provider.py                     # LockProvider ABC + Registry (NEW)
├── execution_guard.py                   # WorkflowExecutionGuard ABC (NEW)
├── idempotency.py                       # WorkflowIdempotencyRegistry ABC (NEW)
└── providers/
    └── __init__.py                      # Provider package stub (NEW)

scripts/migrations/
├── 006_create_workflow_locks_table.sql           (NEW)
└── 007_create_workflow_idempotency_table.sql     (NEW)

tests/locking/
├── __init__.py                          (NEW)
├── conftest.py                          (NEW)
├── test_models.py                       (NEW)
└── test_exceptions.py                   (NEW)
```

## Test Results

```
collected 40 items

tests/locking/test_exceptions.py ...............           [ 37%]
  19 passed
tests/locking/test_models.py .....................         [ 100%]
  21 passed
========================================== 40 passed in 0.29s
```

## Remaining Phases

| Phase | Description | Status |
|-------|-------------|--------|
| **Phase 1** | Foundation — package, models, ABCs, exceptions, config, migrations | ✅ Complete |
| **Phase 2** | Locking Infrastructure — MemoryLockProvider, FileLockProvider, DBLockProvider, ExecutionGuard, IdempotencyRegistry | 🔲 Pending |
| **Phase 3** | Workflow Integration — update ExecutionContext/WorkflowResult, integrate guard into WorkflowRunner.run() | 🔲 Pending |
| **Phase 4** | Testing — unit tests, integration tests, performance benchmarks, boundary verification | 🔲 Pending |
| **Phase 5** | Documentation & Release — handoff, ADR, ROADMAP/TECHDEBT updates, git commit/tag | 🔲 Pending |

## Known Issues

- None. Phase 1 produces abstractions only — no executable locking logic yet.

## Related Documents

| Document | Location |
|----------|----------|
| Architecture Plan | `docs/architecture/WORKFLOW_RUNTIME_LOCKING_V1_PLAN.md` |
| Implementation Plan | `docs/architecture/WORKFLOW_RUNTIME_LOCKING_V1_IMPLEMENTATION_PLAN.md` |
| Handoff Document | `docs/architecture/WORKFLOW_RUNTIME_LOCKING_V1_HANDOFF.md` |
| Next Milestone Recommendation | `docs/architecture/NEXT_MILESTONE_RECOMMENDATION.md` |