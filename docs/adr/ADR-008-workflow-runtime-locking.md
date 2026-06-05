# Status
Accepted

# Context
The Workflow Runtime (v0.2+) had no mechanism to prevent the same workflow from being executed concurrently by multiple invocations. Each `run()` call was stateless — creating a fresh `pipeline_run_id`, executing stages sequentially, and returning a result — with no coordination between overlapping calls for the same `workflow_id`.

This created concrete risks:
- Duplicate workflow execution (scheduled + manual overlap)
- Duplicate downstream side-effects (alerts, reports, debug artifacts)
- Incorrect aggregated state (entity runtime merges, dashboard metrics)
- No audit trail for duplicate runs
- No execution leasing or crash recovery

The absence of locking was listed as the highest-priority known technical debt in both PLATFORM_ARCHITECTURE_REVIEW.md and NEXT_MILESTONE_RECOMMENDATION.md (scored 9/10 — highest risk reduction, smallest effort).

Six locking strategies were evaluated: in-memory locking, file locking, database locking, distributed locking, idempotency keys, and execution leases.

# Decision
Workflow Runtime Locking v1 adopts a **database-backed row-level locking with execution leases** as the primary strategy, with **file-based locking** as fallback, **in-memory locking** for development/testing, and **idempotency keys** as a complementary deduplication mechanism.

## Strategy Rationale

1. **Database locking** uses the existing history_store infrastructure — no new external dependencies. It provides cross-process and cross-host coordination with atomic UPSERT guarantees.

2. **Execution leases** add crash recovery — a crashed workflow's lock auto-expires after a configurable TTL, allowing retry without manual intervention.

3. **Idempotency keys** prevent re-execution of already-completed runs, even if the idempotency key is presented after the lock is released.

4. **File locking** is available as a fallback for environments without database connectivity (development, CI).

## Architecture Components

The locking subsystem comprises four layers:

### Lock Providers (pluggable)
- `MemoryLockProvider` — thread-safe, dict-based (dev/test only)
- `FileLockProvider` — cross-platform advisory locking with stale detection
- `DBLockProvider` — UPSERT semantics on `workflow_locks` table with parameterized queries

### LockProviderRegistry
- Priority-ordered provider chain: DB → File → Memory → error
- Fallback logic: tries providers in priority order, catches `LockProviderError` to fall through

### WorkflowExecutionGuard
- Wraps the `run()` lifecycle: idempotency check → lock acquisition → lease refresh → lock release → idempotency recording
- Retry with exponential backoff on lock contention
- Context manager support (`with guard:`)
- Background daemon thread for periodic lease refresh

### WorkflowIdempotencyRegistry
- `DBIdempotencyRegistry` — atomic INSERT on `workflow_idempotency` table
- `MemoryIdempotencyRegistry` — in-memory dict for testing
- TTL-based cleanup of expired keys (default 7 days)

## Lock Status Values
- `"acquired"` — lock acquired, execution proceeded
- `"rejected_busy"` — another execution holds the lock
- `"rejected_duplicate"` — idempotency key already completed
- `"not_locked"` — no guard configured (original behaviour)

# Consequences

## Benefits
- Eliminates duplicate workflow execution across overlapping triggers
- Provides crash recovery via lease auto-expiry
- Enables deterministic idempotency key deduplication for scheduled runs
- Backward compatible — all contract changes use Optional fields with None defaults
- No new infrastructure dependencies — reuses existing database
- Pluggable provider architecture supports future distributed locking (v2)

## Tradeoffs
- Two new database tables required (`workflow_locks`, `workflow_idempotency`) with schema migration
- Lock acquisition adds ~1-5ms latency per workflow run
- Lease TTL misconfiguration can cause premature duplicate execution (TTL too short) or delayed crash recovery (TTL too long)
- File lock fallback has known Windows timing precision limitations

## Future Implications
- Multi-host deployments should replace DBLockProvider with Redis/etcd distributed locking (v2)
- Dynamic lease TTL estimation from historical execution times
- Lock-free execution via event sourcing for high-throughput requirements
- Dead-letter queue for persistent lock failures
- Cross-workflow lock ordering for workflow dependency graphs

# Compliance
- Locking module lives entirely within `src/workflow_runtime/locking/` — no boundary violations
- All 363/364 regression tests pass (1 pre-existing Windows timing issue)
- 158/158 locking-specific tests pass
- Boundary verification: COMPLIANT — no violations detected