# Workflow Runtime Locking v1 — Phase 3 Readiness Review

**Date**: 2026-06-04  
**Author**: Platform Architecture Review  
**Status**: Assessment Complete — awaiting Phase 3 start  
**Milestone**: v0.5-workflow-runtime-locking  
**Current Commit**: `d32e24d` (Phase 2 complete)  
**Tests Passing**: 94 / 94 (locking suite) + full regression suite passes  

---

## Components Completed

### Phase 1 — Foundation (commit `b3dfebb`)

| Component | File | Status |
|-----------|------|--------|
| Locking package skeleton | `src/workflow_runtime/locking/__init__.py` | ✅ Complete |
| Package init (providers) | `src/workflow_runtime/locking/providers/__init__.py` | ✅ Complete |
| `LockAcquisition` data model | `src/workflow_runtime/locking/models.py` | ✅ Complete — frozen dataclass with slots |
| `IdempotencyRecord` data model | `src/workflow_runtime/locking/models.py` | ✅ Complete — frozen dataclass with slots |
| `LockProvider` ABC | `src/workflow_runtime/locking/lock_provider.py` | ✅ Complete — `acquire`, `release`, `refresh` |
| `WorkflowExecutionGuard` ABC | `src/workflow_runtime/locking/execution_guard.py` | ✅ Complete — `execute`, context manager |
| `WorkflowIdempotencyRegistry` ABC | `src/workflow_runtime/locking/idempotency.py` | ✅ Complete — `check`, `record`, `cleanup` |
| `LockAcquisitionError` exception | `src/workflow_runtime/locking/exceptions.py` | ✅ Complete — includes `lock_id`, `current_holder_id`, `expires_at` |
| `IdempotencyRejectionError` exception | `src/workflow_runtime/locking/exceptions.py` | ✅ Complete — includes `idempotency_key`, `existing_status` |
| `LockProviderError` exception | `src/workflow_runtime/locking/exceptions.py` | ✅ Complete — includes `provider_name`, `original_exception` |
| `LeaseRefreshError` exception | `src/workflow_runtime/locking/exceptions.py` | ✅ Complete |
| Migration 006: `workflow_locks` table | `scripts/migrations/006_create_workflow_locks_table.sql` | ✅ Complete — tested on in-memory SQLite |
| Migration 007: `workflow_idempotency` table | `scripts/migrations/007_create_workflow_idempotency_table.sql` | ✅ Complete — tested on in-memory SQLite |
| Configuration defaults | `src/workflow_runtime/locking/config.py` | ✅ Complete — 12 constants with documented defaults |

### Phase 2 — Locking Infrastructure (commit `d32e24d`)

| Component | File | Status |
|-----------|------|--------|
| `MemoryLockProvider` | `src/workflow_runtime/locking/providers/memory_lock_provider.py` | ✅ Complete — thread-safe, dict-based |
| `FileLockProvider` | `src/workflow_runtime/locking/providers/file_lock_provider.py` | ✅ Complete — cross-platform, stale detection, metadata JSON |
| `DBLockProvider` | `src/workflow_runtime/locking/providers/db_lock_provider.py` | ✅ Complete — UPSERT semantics, parameterized queries, stale cleanup |
| `LockProviderRegistry` | `src/workflow_runtime/locking/lock_provider.py` | ✅ Complete — priority ordering, fallback chain (DB → File → Memory → error) |
| `DBIdempotencyRegistry` | `src/workflow_runtime/locking/idempotency.py` | ✅ Complete — atomic INSERT, TTL cleanup |
| `MemoryIdempotencyRegistry` | `src/workflow_runtime/locking/idempotency.py` | ✅ Complete — in-memory dict for testing |
| `WorkflowExecutionGuard` (concrete) | `src/workflow_runtime/locking/execution_guard.py` | ✅ Complete — lock lifecycle, retry with backoff, context manager, idempotency check |
| Lease refresh loop | `src/workflow_runtime/locking/execution_guard.py` | ✅ Complete — thread-based refresh, configurable interval, non-fatal failure |
| Stale lock cleanup | `src/workflow_runtime/locking/providers/db_lock_provider.py` | ✅ Complete — `cleanup_stale()` method |

### Test Coverage (Phase 4 — Partial)

| Test File | Tests | Status |
|-----------|-------|--------|
| `tests/locking/test_models.py` | 21 | ✅ All pass |
| `tests/locking/test_exceptions.py` | 19 | ✅ All pass |
| `tests/locking/test_memory_lock_provider.py` | 12 | ✅ All pass |
| `tests/locking/test_file_lock_provider.py` | 10 | ✅ All pass |
| `tests/locking/test_db_lock_provider.py` | 10 | ✅ All pass |
| `tests/locking/test_lock_provider_registry.py` | 6 | ✅ All pass |
| `tests/locking/test_workflow_idempotency_registry.py` | 10 | ✅ All pass |
| `tests/locking/test_workflow_execution_guard.py` | 6 | ✅ All pass |
| **Total locking tests** | **94** | **✅ All pass (0.54s)** |
| Boundary verification | `scripts/verify_boundaries.py` | ✅ All rules pass |
| Full regression suite | `pytest tests/` | ✅ No failures |

---

## Components Remaining

The following components must be completed for Phase 3 to be considered done. These correspond to **Phase 3 of the implementation plan** (Workflow Integration) plus **completion of Phase 4** (full testing) and **Phase 5** (documentation and release).

### Phase 3 — Workflow Integration (NOT STARTED)

| # | Component | File(s) | Effort | Dependency |
|---|-----------|---------|--------|------------|
| 3.1 | Add `lock_acquisition` field to `ExecutionContext` | `src/workflow_runtime/contracts/execution_context.py` | ~1h | Phase 2 models |
| 3.2 | Add `idempotency_key` and `lock_status` fields to `WorkflowResult` | `src/workflow_runtime/contracts/workflow_result.py` | ~1h | Phase 2 models |
| 3.3 | Integrate `WorkflowExecutionGuard` into `WorkflowRunner.run()` | `src/workflow_runtime/runtime/workflow_runner.py` | ~6h | 3.1, 3.2, Phase 2 |
| 3.4 | Idempotency key generation for scheduled runs | `src/workflow_runtime/runtime/workflow_runner.py`, trigger code | ~1h | 3.3 |
| 3.5 | Lock acquisition error handling (catch → WorkflowResult) | `src/workflow_runtime/runtime/workflow_runner.py` | ~1.5h | 3.3 |
| 3.6 | Idempotency rejection handling (skip → cached result) | `src/workflow_runtime/runtime/workflow_runner.py` | ~1.5h | 3.3 |

**Total Phase 3 effort**: ~12 hours (2 days) per implementation plan.

### Phase 4 — Testing (Incomplete)

The following tests from the implementation plan have **not yet been written**:

| # | Test File | Scenarios | Effort |
|---|-----------|-----------|--------|
| 4.8 | Lease refresh loop tests | `test_refresh_invoked_during_execution`, `test_refresh_failure_logs_warning`, `test_refresh_extends_expiry`, `test_refresh_stops_after_completion` | ~2h |
| 4.9 | Concurrent execution integration tests | Same workflow concurrent, different workflows, staggered start, scheduled+manual overlap, 10-way | ~3h |
| 4.10 | Crash recovery integration tests | Basic recovery, mid-refresh, graceful after failure, with idempotency | ~2h |
| 4.11 | Provider fallback integration tests | DB→File, File→Memory, all fail, fallback performance | ~2h |
| 4.12 | Idempotency key integration tests | Basic dedup, with lock, concurrent, TTL | ~1.5h |
| 4.13 | Performance benchmarks | 8 benchmarks for latency, throughput, refresh | ~2h |
| 4.14 | Boundary verification (post-Phase 3) | Re-run `verify_boundaries.py` after integration | ~0.5h |

**Total testing remaining**: ~13 hours (1.5 days).

### Phase 5 — Documentation and Release (Incomplete)

| # | Artifact | File | Status | Effort |
|---|----------|------|--------|--------|
| 5.1 | Architecture Summary | `docs/architecture/WORKFLOW_RUNTIME_LOCKING_V1_SUMMARY.md` | ✅ **Written** (Phase 1 handoff version exists — needs update for Phase 2+3) | ~1h to update |
| 5.2 | Handoff Document | `docs/architecture/WORKFLOW_RUNTIME_LOCKING_V1_HANDOFF.md` | ✅ **Written** (Phase 1 only — must be updated for Phases 2, 3, 4) | ~2h to update |
| 5.3 | ADR-008 | `docs/adr/ADR-008-workflow-runtime-locking.md` | ❌ **Not created** | ~2h |
| 5.4 | ROADMAP.md update | `docs/ROADMAP.md` | ❌ **Not updated** | ~0.5h |
| 5.5 | TECHNICAL_DEBT.md update | `TECHNICAL_DEBT.md` | ❌ **Not updated** | ~0.5h |
| 5.6 | V0_5 plan update | `docs/architecture/V0_5_RUNTIME_HARDENING_PLAN.md` | ❌ **Not updated** | ~0.5h |
| 5.7 | CHANGELOG.md update | `CHANGELOG.md` | ❌ **Not updated** | ~0.5h |
| 5.8 | Git commit | Repository | ❌ Pending | ~0.5h |
| 5.9 | Git push + tag | Remote | ❌ Pending | ~0.5h |

**Total documentation remaining**: ~8 hours (1 day).

### Overall Remaining Effort

| Phase | Hours | Days | Status |
|-------|-------|------|--------|
| Phase 3 (Integration) | 12 | 2 | ❌ **Not started** |
| Phase 4 (Testing, remaining) | 13 | 1.5 | ❌ **Unit tests pass; integration tests not written** |
| Phase 5 (Docs + Release) | 8 | 1 | ❌ **Documents exist but need updates; ADR missing** |
| **Total remaining** | **33** | **~4.5** | |

---

## Files Expected To Change

### Files To Modify (Phase 3)

| File | Change Type | Impact |
|------|-------------|--------|
| `src/workflow_runtime/contracts/execution_context.py` | **Add fields** — `lock_acquisition: Optional[LockAcquisition]`, `idempotency_key: Optional[str]` | Backward compatible — Optional fields with `None` defaults |
| `src/workflow_runtime/contracts/workflow_result.py` | **Add fields** — `idempotency_key: Optional[str]`, `lock_status: Optional[str]` | Backward compatible — Optional fields with `None` defaults |
| `src/workflow_runtime/runtime/workflow_runner.py` | **Modify `__init__`** — accept optional `execution_guard` and `idempotency_registry` params with `None` defaults | Backward compatible — existing callers unchanged |
| `src/workflow_runtime/runtime/workflow_runner.py` | **Modify `run()`** — integrate guard lifecycle, add idempotency key generation, error handling | New behaviour only when guard configured |
| `src/scheduler.py` (or trigger code) | **Add idempotency key generation** — deterministic key for scheduled runs | Scheduled runs gain dedup; manual runs unaffected |

### Files NOT Modified (Per Plan)

| File | Rationale |
|------|-----------|
| `src/workflow_runtime/dsl/workflow_parser.py` | Locking is a runtime concern, not DSL |
| `src/workflow_runtime/dsl/workflow_validator.py` | Validation does not involve runtime state |
| `src/workflow_runtime/dag/builder.py` | DAG building is orchestration, not execution |
| `src/workflow_runtime/operations/*.py` | Stages are unaware of locking |
| `src/workflow_runtime/workspace/workspace_registry.py` | Workspace management is separate |
| `src/storage/history_store.py` | DBLockProvider encapsulates DB access directly |
| Any file outside `src/workflow_runtime/` | Locking lives within Workflow Runtime boundary |

### Files To Create

| File | Purpose |
|------|---------|
| `tests/locking/test_lease_refresh.py` | Lease refresh loop tests (4 scenarios) |
| `tests/locking/test_integration_concurrent.py` | Concurrent execution integration tests (5 scenarios) |
| `tests/locking/test_integration_crash_recovery.py` | Crash recovery integration tests (4 scenarios) |
| `tests/locking/test_integration_fallback.py` | Provider fallback integration tests (4 scenarios) |
| `tests/locking/test_integration_idempotency.py` | Idempotency key integration tests (4 scenarios) |
| `tests/locking/test_performance_benchmarks.py` | Performance benchmarks (8 benchmarks) |
| `docs/adr/ADR-008-workflow-runtime-locking.md` | Decision record for v1 locking strategy |

---

## Runtime Impact

### Execution Flow Changes (After Phase 3)

| Aspect | Current (Phase 2) | After Phase 3 |
|--------|-------------------|---------------|
| `run()` lifecycle | Validate → Execute → Return | Validate → **Lock** → Execute → **Refresh** → **Release** → **Record** → Return |
| Latency overhead | None | +2 DB round trips (acquire + release) + periodic refresh (~1-5ms each) |
| Failure mode | Direct failure on stage error | `LockAcquisitionError` if busy; `IdempotencyRejectionError` if already run |
| Crash behaviour | Unrecoverable (no retry) | Lease auto-expires → retryable (via `WorkflowExecutionGuard`) |
| Error propagation | Returns `WorkflowResult.FAILED` | Returns `WorkflowResult` with `lock_status="rejected_busy"` or `"rejected_duplicate"` |

### Performance Considerations

- **Lock acquisition overhead**: ~1-5ms per run (single DB round trip for UPSERT). Negligible compared to workflow execution time (seconds to minutes).
- **Lease refresh overhead**: ~1-5ms every 30 seconds via background thread in `WorkflowExecutionGuard`. Negligible.
- **No impact on stage execution**: Stage `run()` methods are unchanged — locking is a wrapper around the execution lifecycle.
- **Concurrency**: Row-level locking in `workflow_locks` table allows concurrent execution of *different* workflows. Only *same* `workflow_id` executions are serialized.

### Thread Safety

- `WorkflowExecutionGuard` uses a daemon thread for lease refresh
- `MemoryLockProvider` uses `threading.Lock()` internally
- `WorkflowRunner.run()` must be thread-safe when guard is configured — currently it is called sequentially by the scheduler, but the guard adds no additional thread-safety concerns beyond what the existing callers expect

### Deployment Considerations

| Concern | Assessment |
|---------|------------|
| **Database schema** | Migrations 006 and 007 must be applied before Phase 3 is deployed |
| **Rolling deploy compatibility** | New `WorkflowRunner.__init__()` accepts optional guard with `None` default — old callers continue to work during rolling deploy |
| **Configuration** | Default `LOCK_PROVIDER=memory` means locking is effectively disabled until explicitly set to `"database"` — safe default for initial deployment |
| **No new infrastructure** | Reuses existing history store database |

---

## Contract Impact

### New Public Contracts (Already Exported from Phase 2)

| Contract | Type | Defined In |
|----------|------|------------|
| `LockAcquisition` | Frozen dataclass | `src/workflow_runtime/locking/models.py` |
| `IdempotencyRecord` | Frozen dataclass | `src/workflow_runtime/locking/models.py` |
| `LockAcquisitionError` | Exception | `src/workflow_runtime/locking/exceptions.py` |
| `IdempotencyRejectionError` | Exception | `src/workflow_runtime/locking/exceptions.py` |
| `LockProviderError` | Exception | `src/workflow_runtime/locking/exceptions.py` |
| `LeaseRefreshError` | Exception | `src/workflow_runtime/locking/exceptions.py` |
| `WorkflowExecutionGuard` | Class | `src/workflow_runtime/locking/execution_guard.py` |
| `LockProvider` | ABC | `src/workflow_runtime/locking/lock_provider.py` |
| `LockProviderRegistry` | Class | `src/workflow_runtime/locking/lock_provider.py` |
| `WorkflowIdempotencyRegistry` | ABC | `src/workflow_runtime/locking/idempotency.py` |
| `DBLockProvider` | Class | `src/workflow_runtime/locking/providers/db_lock_provider.py` |
| `FileLockProvider` | Class | `src/workflow_runtime/locking/providers/file_lock_provider.py` |
| `MemoryLockProvider` | Class | `src/workflow_runtime/locking/providers/memory_lock_provider.py` |

### Contracts To Modify (Phase 3)

| Contract | Change | Backward Compatible? |
|----------|--------|---------------------|
| `ExecutionContext` | Add `lock_acquisition: Optional[LockAcquisition] = None` | ✅ Yes — Optional field with default |
| `ExecutionContext` | Add `idempotency_key: Optional[str] = None` | ✅ Yes — Optional field with default |
| `WorkflowResult` | Add `idempotency_key: Optional[str] = None` | ✅ Yes — Optional field with default |
| `WorkflowResult` | Add `lock_status: Optional[str] = None` | ✅ Yes — Optional field with default |

### Unchanged Contracts

| Contract | Reason |
|----------|--------|
| `WorkflowDefinition` | Locking is a runtime concern, not a definition concern |
| `WorkflowParser` | No change — parsing does not involve runtime state |
| `WorkflowValidator` | No change — validation does not involve locking |
| `StageDefinition` | No change — stages are unaware of locking |
| `StageResult` | No change — locking is outside stage boundaries |
| `DAGBuilder` | No change — DAG construction is independent of locking |

### Database Schema

Both schema migrations are already created and tested. No additional schema changes are needed for Phase 3.

- **006**: `workflow_locks` table — lock_id (PK), holder_id, acquired_at, expires_at, lease_duration_s, hostname, pid, refresh_count, last_refreshed_at
- **007**: `workflow_idempotency` table — idempotency_key (PK), pipeline_run_id, status, created_at, completed_at, result_summary

Both tables must be applied before Phase 3 is deployed.

---

## Risks

| # | Risk | Likelihood | Impact | Current Mitigation | Phase 3 Mitigation Needed |
|---|------|------------|--------|--------------------|---------------------------|
| R1 | **ExecutionContext field changes break existing callers** | Low | High | Optional fields with `None` defaults in Phase 3 | Verify all existing `ExecutionContext()` construction sites use keyword args or accept new fields |
| R2 | **WorkflowRunner.run() backward compatibility** | Low | High | Guard defaults to `None` → no behaviour change for unmodified callers | Verify all existing `runner.run()` callsites work without changes |
| R3 | **Lease refresh thread not cleaned up on exception** | Medium | Medium | Refresh thread is a daemon thread — terminates on process exit | Add explicit cleanup in guard's `__exit__` path. Current implementation already does this. |
| R4 | **Idempotency key collision for different schedule slots** | Low | High | Key format: `{workflow_id}-scheduled-{YYYY-MM-DDTHH:MM}` — precise to the minute | Verify key generation aligns with actual scheduler granularity |
| R5 | **Lock acquisition in WorkflowRunner.run() blocks indefinitely** | Low | Medium | `_acquire_with_retry()` has configurable `max_retries` (3) and `retry_delay_s` (5) = max 15s wait. | Validate that 15s max wait is acceptable for all trigger paths |
| R6 | **Double locking — scheduler and manual triggers both try to lock** | Low | Medium | Lock is per `workflow_id` — both triggers share the same lock namespace. This is the desired behaviour. | Ensure manual trigger paths acquire lock with correct `holder_id` |
| R7 | **WorkflowExecutionGuard imported into WorkflowRunner creates circular dependency** | Low | High | `locking.execution_guard` does not import `runtime.workflow_runner`. Import direction is one-way: runner → guard. | Verify import order before Phase 3 commit |
| R8 | **Performance regression from lock acquisition in hot path** | Low | Medium | Lock is acquired once per `run()` call, not per stage. Overhead is ~1-5ms. | Add `test_performance_benchmarks.py` before enabling locking in production |
| R9 | **Scheduler duplicating runs before Phase 3 deployed** | Low | Low | Phase 3 is opt-in — no behaviour change until guard is configured. Scheduler continues to work without locking. | N/A — existing behaviour preserved |
| R10 | **Integration tests use real WorkflowRunner — may be flaky** | Medium | Medium | Phase 4 integration tests require careful fixture setup with mocked DB, timing control | Use `MemoryLockProvider` for unit tests; in-memory SQLite for DB provider tests; avoid real file I/O in CI |

### Risk Scoring After Phase 3

| Risk | Pre-Mitigation Score | Post-Mitigation Score |
|------|---------------------|-----------------------|
| R1 — Contract breakage | 6 (Low × High) | 2 (Low × Low) |
| R2 — Runner backward compat | 6 (Low × High) | 2 (Low × Low) |
| R3 — Thread cleanup | 8 (Medium × Medium) | 4 (Low × Medium) |
| R4 — Key collision | 4 (Low × High) | 2 (Low × Low) |
| R5 — Indefinite blocking | 4 (Low × Medium) | 2 (Low × Low) |
| R6 — Double locking | 4 (Low × Medium) | 2 (Low × Low) |
| R7 — Circular import | 6 (Low × High) | 2 (Low × Low) |
| R8 — Performance regression | 4 (Low × Medium) | 2 (Low × Low) |
| R9 — Scheduler duplicates | 2 (Low × Low) | 1 (None × Low) |
| R10 — Flaky integration tests | 6 (Medium × Medium) | 3 (Low × Medium) |

---

## Migration Requirements

### Database Migration

Migrations 006 and 007 must be applied **before** Phase 3 code is deployed:

```sql
-- Order: 006 first, then 007
CREATE TABLE workflow_locks ( ... );  -- scripts/migrations/006_create_workflow_locks_table.sql
CREATE TABLE workflow_idempotency ( ... );  -- scripts/migrations/007_create_workflow_idempotency_table.sql
```

**Rollback**:
```sql
DROP TABLE IF EXISTS workflow_locks;
DROP TABLE IF EXISTS workflow_idempotency;
```

### Code Migration

| Step | Action | Safe to deploy incrementally? |
|------|--------|-----------------------------|
| 1 | Add `lock_acquisition` and `idempotency_key` fields to `ExecutionContext` | ✅ Yes — Optional fields with `None` defaults; existing construction sites continue to work |
| 2 | Add `idempotency_key` and `lock_status` fields to `WorkflowResult` | ✅ Yes — Optional fields with `None` defaults |
| 3 | Add optional `execution_guard` and `idempotency_registry` params to `WorkflowRunner.__init__()` | ✅ Yes — default `None` means no behaviour change |
| 4 | Modify `WorkflowRunner.run()` to use guard when configured | ✅ Yes — existing callers without guard continue with original lifecycle |
| 5 | Add idempotency key generation in scheduler/trigger code | ✅ Yes — scheduled runs gain dedup; manual runs unaffected |

### Rollback Strategy

```bash
# Immediate rollback (disable locking):
# 1. Set LOCK_PROVIDER=memory in environment configuration
#    This reverts to pre-locking behaviour (no cross-process coordination)
# 2. Restart workflow runtime processes
# 3. Verify all workflows execute without lock errors

# Permanent rollback (remove locking integration):
# 1. Revert WorkflowRunner.run() to pre-locking lifecycle
#    (undo Phase 3 changes to run() and __init__())
# 2. Revert ExecutionContext and WorkflowResult to original contracts
#    (remove optional lock fields)
# 3. Re-verify all existing callers work correctly
```

**Note**: Reverting Phase 3 does **not** require removing the `src/workflow_runtime/locking/` package — the locking infrastructure itself is additive. Only the integration points in `WorkflowRunner`, `ExecutionContext`, and `WorkflowResult` need to be reverted.

---

## Test Strategy

### Current Test Coverage

| Area | Tests | Status |
|------|-------|--------|
| Data model unit tests | 21 | ✅ Passing |
| Exception unit tests | 19 | ✅ Passing |
| MemoryLockProvider unit tests | 12 | ✅ Passing |
| FileLockProvider unit tests | 10 | ✅ Passing |
| DBLockProvider unit tests | 10 | ✅ Passing |
| LockProviderRegistry unit tests | 6 | ✅ Passing |
| IdempotencyRegistry unit tests | 10 | ✅ Passing |
| ExecutionGuard unit tests | 6 | ✅ Passing |
| Boundary verification | 1 script | ✅ Passing |

### Tests To Add for Phase 3

| Priority | Test Area | What to Cover | Expected Count |
|----------|-----------|---------------|----------------|
| **P0** | Lease refresh loop | Refresh invoked, failure logged, expiry extended, stops after completion | 4 tests |
| **P0** | Concurrent execution | Same workflow blocked, different workflows allowed, staggered, scheduled+manual, 10-way | 5 scenarios |
| **P0** | Crash recovery | Basic recovery, mid-refresh, graceful, with idempotency | 4 scenarios |
| **P0** | Provider fallback | DB→File, File→Memory, all fail, fallback latency | 4 scenarios |
| **P0** | Idempotency integration | Basic dedup, with lock, concurrent, TTL | 4 scenarios |
| **P1** | Performance benchmarks | Lock acquire p50/p99, release, refresh, throughput, idempotency check | 8 benchmarks |
| **P1** | WorkflowRunner integration | Guard wraps run(), lock error returns result, idempotency skip returns cached | 3+ tests |

### Existing Tests That May Need Updates

| Test File | Potential Issue | Action |
|-----------|----------------|--------|
| `tests/test_workflow_runtime.py` | Creates `WorkflowRunner()` and `WorkflowResult()` directly — must check if new Optional fields cause issues | Verify all constructions are backward compatible — they should be since fields default to `None` |
| `tests/locking/conftest.py` | `guarded_runner` fixture creates a `WorkflowRunner` mock — may need adjustment if `WorkflowRunner.__init__()` signature changes | Verify the fixture pattern works with new optional params |

### Boundary Verification

- Run `python scripts/verify_boundaries.py` after Phase 3 changes
- The `src/workflow_runtime/locking/` package imports only from:
  - `src.workflow_runtime.models` (LockAcquisition)
  - `src.workflow_runtime.exceptions` (no direct import — separate module)
  - Python standard library (`logging`, `time`, `abc`, `datetime`, `typing`, `threading`, `os`, `json`, `pathlib`, `socket`, `sqlite3`)
  - No cross-runtime boundary violations expected

---

## Rollback Strategy

### Phase 3 Rollback (WorkflowRunner Integration)

```bash
# 1. Revert the WorkflowRunner.__init__() and run() changes
#    (remove execution_guard and idempotency_registry params, remove lock lifecycle)
git revert <phase3-commit-hash>

# 2. Revert ExecutionContext and WorkflowResult contract changes
#    (remove lock_acquisition, idempotency_key, lock_status fields)
#    This is a separate revert if contracts were committed separately

# 3. Re-run full test suite
pytest tests/ -v --tb=short
python scripts/verify_boundaries.py
```

### Database Rollback

```bash
# Drop locking tables (only if no other runtime depends on them)
DROP TABLE IF EXISTS workflow_locks;
DROP TABLE IF EXISTS workflow_idempotency;
```

### Configuration Toggle (No Code Deploy Needed)

```bash
# Disable locking without code change:
# Set in environment:
LOCK_PROVIDER=memory

# Restart workers:
# -- On Windows: restart the Python process or service
# -- All existing workflows execute without locking coordination
```

### Decision Tree

```
Is locking causing issues?
│
├─ Yes → Is it a configuration issue?
│        │
│        ├─ Yes → Toggle LOCK_PROVIDER=memory (immediate fix, no deploy)
│        │
│        └─ No → Rollback Phase 3 code (requires code revert deploy)
│
└─ No → Keep locking enabled, monitor lock metrics
```

---

## Recommended Implementation Order

The implementation plan defines a dependency chain. Below is the recommended order for Phase 3 tasks, accounting for the fact that Phases 1 and 2 are already complete.

### Phase 3 Implementation Order (12 hours / 2 days)

**Day 1 — Contract updates and error handling**:

| Order | Task | Effort | Depends On |
|-------|------|--------|------------|
| 1 | Add `lock_acquisition: Optional[LockAcquisition]` field to `ExecutionContext` | 0.5h | None (Phase 2 models already exist) |
| 2 | Add `idempotency_key: Optional[str]` field to `ExecutionContext` | 0.5h | None |
| 3 | Add `idempotency_key: Optional[str]` and `lock_status: Optional[str]` fields to `WorkflowResult` | 1h | None |
| 4 | Verify all existing `ExecutionContext()` and `WorkflowResult()` construction sites still compile | 0.5h | 1, 2, 3 |
| 5 | Add `execution_guard` and `idempotency_registry` params to `WorkflowRunner.__init__()` | 1h | None |
| 6 | Add idempotency key generation helper function | 0.5h | None |
| 7 | Modify `WorkflowRunner.run()` — add guard lifecycle, idempotency check, lock acquisition | 3h | 1, 2, 3, 4, 5 |
| 8 | Add lock acquisition error handling (`LockAcquisitionError` → `WorkflowResult`) | 1h | 7 |
| 9 | Add idempotency rejection handling (`IdempotencyRejectionError` → cached result) | 1h | 7 |
| 10 | Update scheduler/trigger code to pass idempotency key for scheduled runs | 0.5h | 6, 7 |

**Day 2 — Verify and fix**:

| Order | Task | Effort |
|-------|------|--------|
| 11 | Run existing WorkflowRuntime tests to confirm backward compatibility | 0.5h |
| 12 | Run `scripts/verify_boundaries.py` to confirm no import regressions | 0.5h |
| 13 | Manual smoke test: run a workflow with guard disabled (default) | 0.5h |
| 14 | Manual smoke test: run a workflow with guard enabled (MemoryLockProvider) | 0.5h |
| 15 | Fix any issues found | 1h (buffer) |

### Phase 4 Implementation Order (Remaining tests — 13 hours / 1.5 days)

| Order | Task | Effort |
|-------|------|--------|
| 1 | Write lease refresh loop tests (`test_lease_refresh.py`) — 4 scenarios | 2h |
| 2 | Write integration tests: concurrent execution (`test_integration_concurrent.py`) — 5 scenarios | 3h |
| 3 | Write integration tests: crash recovery (`test_integration_crash_recovery.py`) — 4 scenarios | 2h |
| 4 | Write integration tests: provider fallback (`test_integration_fallback.py`) — 4 scenarios | 2h |
| 5 | Write integration tests: idempotency (`test_integration_idempotency.py`) — 4 scenarios | 1.5h |
| 6 | Write performance benchmarks (`test_performance_benchmarks.py`) — 8 benchmarks | 2h |
| 7 | Re-run boundary verification + full test suite | 0.5h |

### Phase 5 Implementation Order (Documentation — 8 hours / 1 day)

| Order | Task | Effort |
|-------|------|--------|
| 1 | Update `WORKFLOW_RUNTIME_LOCKING_V1_SUMMARY.md` — add Phase 2 and Phase 3 results | 1h |
| 2 | Update `WORKFLOW_RUNTIME_LOCKING_V1_HANDOFF.md` — add Phase 2 runbook, update for Phase 3 | 2h |
| 3 | Create `docs/adr/ADR-008-workflow-runtime-locking.md` | 2h |
| 4 | Update `docs/ROADMAP.md` — mark WFR Locking as completed | 0.5h |
| 5 | Update `TECHNICAL_DEBT.md` — close locking item | 0.5h |
| 6 | Update `docs/architecture/V0_5_RUNTIME_HARDENING_PLAN.md` | 0.5h |
| 7 | Update `CHANGELOG.md` — add milestone entry | 0.5h |
| 8 | Git commit, push, and tag `v0.5-workflow-runtime-locking` | 1h |

### Total Remaining Timeline

| Phase | Effort | Calendar Days (single dev) |
|-------|--------|---------------------------|
| Phase 3 — Integration | 12h | 2 days |
| Phase 4 — Remaining tests | 13h | 1.5 days |
| Phase 5 — Docs + Release | 8h | 1 day |
| **Total** | **33h** | **~4.5 days** |

---

## Definition Of Done For Phase 3

The following criteria define when Phase 3 is complete:

### Code Implementation

- [ ] `ExecutionContext` has `lock_acquisition: Optional[LockAcquisition] = None` field
- [ ] `ExecutionContext` has `idempotency_key: Optional[str] = None` field
- [ ] `WorkflowResult` has `idempotency_key: Optional[str] = None` field
- [ ] `WorkflowResult` has `lock_status: Optional[str] = None` field (values: "acquired", "rejected_busy", "rejected_duplicate", "not_locked")
- [ ] `WorkflowRunner.__init__()` accepts optional `execution_guard: Optional[WorkflowExecutionGuard]` param
- [ ] `WorkflowRunner.__init__()` accepts optional `idempotency_registry: Optional[WorkflowIdempotencyRegistry]` param
- [ ] `WorkflowRunner.run()` checks idempotency key before execution (if key provided)
- [ ] `WorkflowRunner.run()` acquires execution lock via guard (if guard configured)
- [ ] `WorkflowRunner.run()` refreshes lease periodically during execution
- [ ] `WorkflowRunner.run()` releases lock after execution completes or fails
- [ ] `WorkflowRunner.run()` records idempotency key after execution (if key provided)
- [ ] `LockAcquisitionError` is caught and returned as `WorkflowResult` with `lock_status="rejected_busy"`
- [ ] `IdempotencyRejectionError` is caught and returned as `WorkflowResult` with `lock_status="rejected_duplicate"`
- [ ] Idempotency key generation function exists: `generate_idempotency_key(workflow_id, schedule_time)`
- [ ] Scheduled trigger code passes idempotency key via `metadata` to `WorkflowRunner.run()`
- [ ] All existing `WorkflowRunner.__init__()` callers continue to work unchanged
- [ ] All existing `ExecutionContext()` construction sites continue to work unchanged
- [ ] All existing `WorkflowResult()` construction sites continue to work unchanged

### Testing

- [ ] Lease refresh loop unit tests pass (4 scenarios)
- [ ] Concurrent execution integration tests pass (5 scenarios)
- [ ] Crash recovery integration tests pass (4 scenarios)
- [ ] Provider fallback integration tests pass (4 scenarios)
- [ ] Idempotency integration tests pass (4 scenarios)
- [ ] Performance benchmarks meet targets (p50 <10ms, p99 <50ms for DB provider)
- [ ] Existing 94 locking tests still pass
- [ ] Full `pytest tests/ -v` pass (no regressions in broader test suite)
- [ ] `python scripts/verify_boundaries.py` pass (no import violations)

### Documentation

- [ ] `WORKFLOW_RUNTIME_LOCKING_V1_SUMMARY.md` updated for Phase 2 and Phase 3
- [ ] `WORKFLOW_RUNTIME_LOCKING_V1_HANDOFF.md` updated for Phase 2 and Phase 3
- [ ] ADR-008 created

### Migration

- [ ] Migration 006 applied to target database
- [ ] Migration 007 applied to target database
- [ ] Rollback procedure verified

---

## Readiness Assessment

### Verdict: **Ready for Phase 3 — with conditions**

| Criterion | Status | Assessment |
|-----------|--------|------------|
| Phase 1 (Foundation) | ✅ **Complete** | All ABCs, models, exceptions, config, migrations defined |
| Phase 2 (Infrastructure) | ✅ **Complete** | All 3 lock providers, registry, guard, idempotency, lease refresh, stale cleanup implemented |
| Phase 2 Unit Tests | ✅ **94 passing** | All provider tests, guard tests, registry tests, model and exception tests pass |
| Boundary Verification | ✅ **Passing** | No import boundary violations — locking lives within Workflow Runtime |
| **Phase 3 (Integration)** | ❌ **Not started** | **ExecutionContext, WorkflowResult, WorkflowRunner unmodified** |
| Phase 4 (Full Testing) | ⚠️ **Partial** | Unit tests complete. **Integration tests, lease refresh tests, performance benchmarks not written** |
| Phase 5 (Docs + Release) | ⚠️ **Partial** | Summary and handoff exist (Phase 1 only). **ADR-008, ROADMAP, TECHDEBT, CHANGELOG not updated** |
| Milestone Tag | ❌ **Not created** | No `v0.5-workflow-runtime-locking` tag exists |

### Go/No-Go Conditions

| Condition | Met? | Required By |
|-----------|------|-------------|
| All Phase 2 tests pass | ✅ Yes | Phase 3 start |
| Boundary verification passes | ✅ Yes | Phase 3 start |
| Migration scripts verified | ✅ Yes | Phase 3 start |
| Locking infrastructure complete | ✅ Yes | Phase 3 start |
| `ExecutionContext` and `WorkflowResult` not yet modified | ✅ Yes (prerequisite for Phase 3) | Phase 3 start |
| `WorkflowRunner.run()` not yet modified | ✅ Yes (scope boundary) | Phase 3 start |
| No circular imports introduced | ✅ Verified | Phase 3 completion |
| Integration tests pass | ❌ Not yet | Phase 4 completion |
| Performance benchmarks meet targets | ❌ Not yet | Phase 4 completion |
| ADR-008 created | ❌ Not yet | Phase 5 completion |
| ROADMAP/TECHDEBT updated | ❌ Not yet | Phase 5 completion |

### Recommended Actions Before Starting Phase 3

1. ✅ **Foundation is solid** — Proceed with Phase 3 immediately. No blockers exist.

2. **Set `LOCK_PROVIDER=memory` initially** — Deploy Phase 3 with memory-only locking to validate integration works before enabling distributed locking.

3. **Create ADR-008 before Phase 3 begins** — Ensures the design decision is recorded before implementation. This satisfies the governance requirement that decisions be recorded before implementation.

4. **Apply migrations 006 and 007** — The database tables must exist before any locking code runs. They can be applied now without deploying Phase 3 code.

5. **Plan integration test approach** — Integration tests require careful fixture design (in-memory SQLite for DB provider, mock time for lease expiry). Align on test patterns before writing Phase 3 code to avoid rework.

### Phase 3 Entry Checklist

- [x] Locking package `src/workflow_runtime/locking/` is complete
- [x] All 3 lock providers are implemented and tested
- [x] `WorkflowExecutionGuard` is complete with lease refresh
- [x] `WorkflowIdempotencyRegistry` (DB + memory) is complete
- [x] `LockProviderRegistry` with fallback chain is complete
- [x] 94 locking unit tests pass
- [x] Boundary verification passes
- [x] Migration scripts exist and are tested
- [x] Configuration defaults are defined
- [ ] Migrations 006 and 007 applied to target database
- [ ] `ExecutionContext` contract to be modified (add lock fields)
- [ ] `WorkflowResult` contract to be modified (add lock fields)
- [ ] `WorkflowRunner` to be modified (add optional guard)
- [ ] Scheduler/trigger code to be modified (add idempotency key)

### Summary

**The foundation and infrastructure for Workflow Runtime Locking v1 are solid.** Phase 1 (abstract contracts) and Phase 2 (concrete lock providers, execution guard, idempotency registry) are fully implemented with 94 passing tests and clean boundary verification.

**Phase 3 is the integration layer** — wiring the existing locking infrastructure into the WorkflowRunner's execution lifecycle. This is estimated at 2 days of work for a single developer, followed by ~1.5 days of remaining integration tests and ~1 day of documentation updates.

**The highest risks for Phase 3 are:**
1. Ensuring backward compatibility of `ExecutionContext`, `WorkflowResult`, and `WorkflowRunner` (mitigated by Optional fields with `None` defaults)
2. Correct lease refresh thread lifecycle in the guard wrapper (mitigated by daemon thread + explicit cleanup)
3. Proper error propagation — lock errors must become `WorkflowResult` returns, not unhandled exceptions (mitigated by try/except in `run()`)

**Go decision**: **Proceed with Phase 3.** Apply migrations 006 and 007 now, then begin the integration work in the order specified in the Recommended Implementation Order section above.

---

*End of Phase 3 Readiness Review*