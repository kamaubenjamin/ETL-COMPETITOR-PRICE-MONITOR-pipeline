# Workflow Runtime Locking v1 — Architecture Plan

**Date**: 2026-06-03  
**Author**: Platform Architecture Review  
**Status**: Draft — pending review  
**Milestone**: v0.5-workflow-runtime-locking  
**Version**: 1.0  

---

## Problem Statement

The Workflow Runtime currently has no mechanism to prevent the same workflow from being executed concurrently by multiple invocations. During a single `run()` call, the `WorkflowRunner` is stateless — it creates a fresh `pipeline_run_id`, executes stages sequentially, and returns a result. There is no coordination between overlapping calls for the same `workflow_id`.

This creates several concrete risks:

1. **Duplicate workflow execution**: A scheduled trigger fires at the same time as a manual trigger, or two overlapping scheduled runs occur due to clock skew or scheduler drift. Both invocations proceed independently, duplicating extraction, transformation, matching, and alerting work.

2. **Duplicate downstream side-effects**: Each duplicate execution independently:
   - Writes duplicate extraction artifacts
   - Generates duplicate alert records
   - Produces duplicate report outputs
   - Inserts duplicate debug artifacts (if `debug_path` is configured)

3. **Incorrect aggregated state**: Downstream consumers (entity runtime merges, alert aggregation, dashboard metrics) receive duplicate inputs from overlapping runs, producing incorrect totals, false positive alerts, and stale aggregated reports.

4. **No audit trail for duplicates**: The current audit log records each run independently, but there is no mechanism to correlate or detect which runs are duplicates. Operations has no way to distinguish a legitimate re-run from an unintended concurrent execution.

5. **No execution leasing**: If a workflow crashes mid-execution (e.g., process kill, unhandled exception, timeout), there is no mechanism to detect the stale run, recover the lock, or retrigger the workflow after a grace period.

The absence of locking is listed as the highest-priority known technical debt in both `PLATFORM_ARCHITECTURE_REVIEW.md` ("Lack of distributed locking; potential duplicate job execution") and `NEXT_MILESTONE_RECOMMENDATION.md` (scored 9/10 — highest risk reduction, smallest effort).

---

## Current Workflow Execution Model

### Architecture Overview

The Workflow Runtime v0.2 follows this execution model:

```
Trigger (scheduler / manual / API)
       │
       ▼
 WorkflowRunner.run(definition, initial_artifact, metadata)
       │
       ├── 1. WorkflowValidator.validate_or_raise(definition)
       ├── 2. DAGBuilder.build(definition)         — topo-sort stages
       ├── 3. Create ExecutionContext               — new pipeline_run_id (UUID)
       │      └── pipeline_run_id = uuid4()
       │      └── workflow_id        (from definition)
       │      └── workspace_id       (from definition)
       │
       ├── 4. FOR each stage_def in stages:
       │      ├── stage = STAGE_REGISTRY[type](config)
       │      ├── result = stage.run(input_artifact, context)
       │      ├── IF FAILED → break
       │      └── current_artifact = result.output_artifact
       │
       ├── 5. Build WorkflowResult (overall_status, errors)
       ├── 6. IF debug_path → persist debug artifact
       └── 7. Return WorkflowResult
```

### Key Properties

| Property | Current Behaviour |
|---|---|
| **Stateless** | `WorkflowRunner` has no shared state between `run()` calls |
| **Idempotency** | None — no deduplication key, no execution history check |
| **Locking** | None — no mutex, no file lock, no DB lock, no lease |
| **Concurrency model** | Unbounded — any number of `run()` calls for the same `workflow_id` may execute simultaneously |
| **Run identity** | `pipeline_run_id` is a random UUID — cannot be used for deduplication |
| **Side-effect isolation** | None — duplicate runs produce duplicate I/O (debug files, alerts, reports) |
| **Crash recovery** | None — crashed workflows have no mechanism for detection, recovery, or retry with backoff |
| **Error handling** | Per-stage fail-fast — no retry policy, no dead-letter queue |

### Execution Entry Points

Duplicate execution can originate from these paths:

1. **Scheduler trigger** (`src/scheduler.py` / `src/workflows.py`): Periodic execution of workflow definitions. Overlap can occur if a workflow takes longer than its scheduling interval.

2. **Manual trigger** (`src/api/app.py` / `src/orchestrator.py`): User-initiated workflow execution. Can overlap with a scheduled run if a user triggers a run while one is already in progress.

3. **Automated re-trigger**: Future retry mechanisms, CI tests, or integration-driven triggers that fire while a previous run is still active.

---

## Duplicate Execution Risks

### Risk Matrix

| Scenario | Likelihood | Impact | Severity | Current Mitigation |
|---|---|---|---|---|
| Scheduled run overlaps with itself (long-running workflow) | Medium | High — duplicate extraction, alerts, reports | **Critical** | None |
| Manual trigger while scheduled run is active | Medium | High — operator may not know a run is in progress | **Critical** | None |
| Scheduler clock skew / drift on restart | Low | Medium — near-simultaneous duplicate runs | **High** | None |
| API double-trigger (client retry, race condition) | Low | Medium — two identical API calls in quick succession | **High** | None |
| CI / integration test accidental overlap | Low | Low — test data, non-production | **Low** | None |

### Concrete Consequences

| Downstream System | Consequence of Duplicate Run |
|---|---|
| **Entity Runtime** | Duplicate merge operations on entity sets — possible corruption or incorrect canonical state |
| **Alert Engine** | Duplicate price alerts sent — false positives erode trust |
| **Report Engine** | Duplicate report entries — incorrect totals, graphs, aggregates |
| **History Store** | Duplicate workflow history records — confusing audit trail |
| **Debug Artifacts** | Duplicate JSON files in debug directory — hard to distinguish original from duplicate |
| **Dashboard** | Inflated run counts, incorrect success/failure ratios |

---

## Locking Strategy Evaluation

### Evaluation Criteria

Each strategy is evaluated against these dimensions:

- **Advantages**: Benefits for the platform
- **Disadvantages**: Trade-offs and limitations
- **Failure modes**: How the strategy can fail
- **Recovery strategy**: How to detect and recover from failures
- **Scalability impact**: Effect on throughput as the number of workflows/workers increases

---

### 1. In-memory Locking

**Description**: A Python `threading.Lock` or `multiprocessing.Lock` held in the `WorkflowRunner` process memory.

| Dimension | Assessment |
|---|---|
| **Advantages** | — Simplest implementation (one import, no external dependencies)<br>— Zero latency (memory-only)<br>— No infrastructure to manage<br>— Works well for single-process, single-thread architectures |
| **Disadvantages** | — Does NOT prevent duplicate execution across multiple worker processes or hosts<br>— Does NOT survive process restart (locks are lost on crash)<br>— No cross-network coordination<br>— Blocked processes hold no information for monitoring |
| **Failure modes** | — Process crash while holding lock → lock is released (good) but no recovery information is preserved<br>— Thread deadlock → process hangs (requires watchdog)<br>— Does not protect against multiple Gunicorn workers or container replicas |
| **Recovery strategy** | — No explicit recovery needed for single-process (lock vanishes with process)<br>— For deadlocks: process-level timeout + restart (not granular per-workflow) |
| **Scalability impact** | — Horizontal scaling is impossible (multiple processes cannot coordinate)<br>— Single-process throughput limited to sequential execution<br>— Suitable only for development/single-node deployments |

**Verdict**: **Rejected for v1**. Does not address the core risk of duplicate execution across multiple processes or hosts. May be used as a lightweight fallback for single-worker deployments but not as the primary strategy.

---

### 2. File Locking

**Description**: A platform-level advisory file lock (e.g., Python's `fcntl.flock` on POSIX or `msvcrt.locking` on Windows) on a `.lock` file in the workspace directory.

| Dimension | Assessment |
|---|---|
| **Advantages** | — Cross-process coordination on single host<br>— No external infrastructure (just the filesystem)<br>— Survives Python process restarts (lock file persists on disk)<br>— Simple to implement and debug<br>— Works on any filesystem (local, NFS, SSHFS) |
| **Disadvantages** | — Does NOT work across multiple hosts (NFS locking is unreliable)<br>— File descriptor management is tricky (orphaned locks on improper cleanup)<br>— Race condition on lock file creation (TOCTOU)<br>— Windows vs POSIX locking semantics differ<br>— Blocking on file I/O is slower than in-memory<br>— No built-in timeout (must implement manually) |
| **Failure modes** | — Lock file left behind after crash → subsequent runs may false-positive detect a lock<br>— NFS lock timeouts on network filesystems → spurious lock acquisition failures<br>— Permission errors → lock acquisition fails<br>— Disk full → cannot create or update lock file |
| **Recovery strategy** | — Stale lock detection: embed a timestamp + hostname + PID in the lock file; if older than `MAX_LOCK_AGE`, treat as stale and acquire<br>— Periodic cleanup job: scan workspace for orphaned `.lock` files older than threshold<br>— On crash: supervisor process monitors PID and cleans up associated lock files |
| **Scalability impact** | — Single-host only — cannot scale to multi-host deployments<br>— File lock contention on a single file per workflow is acceptable for moderate concurrency (tens of workflows)<br>— NFS-based locks for shared filesystems degrade under high I/O load |

**Verdict**: **Acceptable for v1** but limited to single-host deployments. Best suited as the primary mechanism when deployment is on a single node, with a clear migration path to a distributed strategy later.

---

### 3. Database Locking

**Description**: Row-level lock or atomic compare-and-swap in a shared database (e.g., SQLite advisory lock, PostgreSQL `pg_try_advisory_lock()`, or a row in `history_store` with `INSERT ... ON CONFLICT` semantics).

| Dimension | Assessment |
|---|---|
| **Advantages** | — Cross-process and cross-host coordination (if all workers share a DB)<br>— Atomic operations guarantee correctness (no TOCTOU)<br>— Built-in timeout support (e.g., `NOWAIT` / `SKIP LOCKED`)<br>— Integrates naturally with existing `history_store` contracts<br>— Survives worker crashes (lock is released on connection close or transaction rollback)<br>— Auditable — lock acquisition/release can be recorded in the same DB |
| **Disadvantages** | — Requires database connectivity (adds DB dependency to workflow runtime)<br>— Database becomes a single point of failure for lock coordination<br>— Lock contention under high throughput may degrade DB performance<br>— Schema migration required (new table or new columns)<br>— Transactional overhead for each lock acquisition/release |
| **Failure modes** | — Database connection loss → lock cannot be acquired or released<br>— Transaction stall → lock held indefinitely (requires DB-side timeout)<br>— Deadlock detection → PostgreSQL detects and kills one transaction, potentially losing work<br>— Connection pool exhaustion → all workers stall waiting for lock acquisition |
| **Recovery strategy** | — DB-side lock timeout (e.g., `lock_timeout` in PostgreSQL)<br>— Retry with exponential backoff on connection failure<br>— Health check before run: verify DB connectivity before attempting lock<br>— Dead-letter queue for workflows that fail lock acquisition after max retries |
| **Scalability impact** | — Scales to multiple hosts as long as the database can handle lock throughput<br>— Database locking is typically sub-millisecond (fast enough for workflow orchestration cadence)<br>— Can become a bottleneck at thousands of concurrent workflows — mitigate with sharded lock tables or reduced lock granularity |

**Verdict**: **Recommended for v1** as the primary strategy. The platform already has a `src/storage/history_store.py` for persistence, making this a natural extension. Supports cross-host coordination with atomic guarantees.

---

### 4. Distributed Locking

**Description**: External lock service such as Redis (`SET NX EX`), ZooKeeper (ephemeral znodes), etcd (leases), or AWS DynamoDB (conditional writes).

| Dimension | Assessment |
|---|---|
| **Advantages** | — True distributed coordination across any number of hosts<br>— Built-in TTL/lease expiry (no stale locks)<br>— Highly available if the lock service is clustered<br>— Mature client libraries (redis-py, kazoo, etcd3)<br>— Fits future multi-host deployment architecture |
| **Disadvantages** | — **New infrastructure dependency** — adds ops burden (deploy, monitor, backup Redis/ZK/etcd)<br>— Network latency for every lock acquisition/release<br>— Split-brain scenarios if the lock service network partitions<br>— Over-engineered for v1 — current deployment is single-host<br>— Client library versioning and compatibility management |
| **Failure modes** | — Lock service unavailable → no workflow can execute (hard dependency)<br>— Network partition between worker and lock service → false lock release or indefinite blocking<br>— Clock skew if using TTL-based leasing (Redis) → premature lock release or extended hold<br>— Resource exhaustion (Redis maxmemory, ZK session limits) → lock acquisition fails |
| **Recovery strategy** | — Circuit breaker: fall back to file locking if lock service is unreachable<br>— Redundant lock service cluster (e.g., Redis Sentinel / Cluster)<br>— Monitoring and alerting on lock service availability and latency<br>— Graceful degradation: if lock cannot be acquired, queue the run for later retry |
| **Scalability impact** | — Excellent — scales to many hosts and high throughput<br>— Redis can handle 100k+ lock operations/sec<br>— Minimal overhead for workflow orchestration cadence (seconds between runs) |

**Verdict**: **Deferred to v2**. Appropriate for multi-host production deployments but introduces unnecessary infrastructure complexity for v1. The recommended migration path is DB locking in v1 → Redis/etcd distributed locking in v2 when multi-host deployment is needed.

---

### 5. Idempotency Keys

**Description**: Assign a deterministic, unique key to each workflow invocation (e.g., `{workflow_id}-{date}-{scheduled_slot}`). The runner rejects any run whose key has already been processed.

| Dimension | Assessment |
|---|---|
| **Advantages** | — No lock infrastructure required<br>— Very lightweight — just a key check before execution<br>— Works across processes and hosts with a shared key store<br>— Natural fit for scheduled workflows (daily run has key `daily-2026-06-03`)<br>— Prevents duplicates even for overlapping calls |
| **Disadvantages** | — Requires a shared key store (in-memory dict, filesystem, or DB)<br>— Key expiry must be managed (how long to remember processed keys?)<br>— Does NOT prevent concurrent execution of the same workflow — both calls can start before the key is written<br>— Only prevents the *second* invocation from completing if first finishes first<br>— Not a lock — does not serialize execution, only deduplicates post-facto |
| **Failure modes** | — Key store becomes unavailable → all runs proceed without deduplication<br>— Key collision for genuinely different runs (poor key design)<br>— Key store fills up → memory pressure or storage exhaustion<br>— Two runs start simultaneously before either writes the key → both complete (race on key insertion) |
| **Recovery strategy** | — Key store compaction: expire keys older than `MAX_RUN_WINDOW` (e.g., 7 days)<br>— Fallback to in-memory set if key store is unreachable (single-process only)<br>— Idempotency key must be created atomically (e.g., DB `INSERT ... ON CONFLICT DO NOTHING`)<br>— Audit log must capture key generation and deduplication events |
| **Scalability impact** | — Excellent — key checks are O(1) operations<br>— No contention between different workflow runs<br>— Key store size grows linearly with unique workflow invocations (manageable with TTL) |

**Verdict**: **Recommended as a complementary strategy**, not a replacement for locking. Idempotency keys solve the deduplication problem for completed runs but do not prevent concurrent in-flight execution. Best combined with database locking: locking prevents concurrent execution, idempotency keys prevent re-execution of already-completed runs.

---

### 6. Execution Leases

**Description**: A time-bound lease on workflow execution. The lease is acquired before execution begins, periodically refreshed during execution, and released (or expires) on completion. If the lease expires, another worker may acquire it and retry the workflow.

| Dimension | Assessment |
|---|---|
| **Advantages** | — Handles crash recovery natively (expired lease → retryable)<br>— Bounded execution time prevents stuck workflows from blocking forever<br>— Provides visibility (lease metadata: started_at, host, worker_id)<br>— Can coexist with other locking strategies |
| **Disadvantages** | — Requires lease refresh logic in the runner (periodic heartbeat)<br>— Lease TTL must be longer than the maximum expected execution time<br>— Determining the correct TTL is hard for variable-duration workflows<br>— Lease refresh adds complexity to the execution loop<br>— Stale lease detection requires a background monitor |
| **Failure modes** | — Lease refresh fails → lock expired → another worker may start a duplicate run while first is still executing<br>— Lease TTL too short → premature duplicate execution for legitimate long-running workflows<br>— Lease TTL too long → long delay before crash is detected and execution can resume<br>— Clock skew between workers → inconsistent lease expiry calculations |
| **Recovery strategy** | — Lease refresh retry with exponential backoff before the TTL expires<br>— Graceful degradation: if lease refresh fails consistently, complete the workflow without lease protection and emit a warning<br>— Lease monitor: background process checks for expired leases and triggers retry or alert<br>— Audit trail records lease events (acquire, refresh, expire, release) |
| **Scalability impact** | — Good — lease overhead is minimal (one DB write per refresh interval)<br>— Refresh interval can be tuned (e.g., every 30 seconds for a 5-minute TTL)<br>— No lock contention between different workflow runs |

**Verdict**: **Recommended for v1** as an enhancement to database locking. Leases solve the crash recovery gap that pure locking leaves unaddressed. Without leases, a crashed workflow holds a lock forever (until manual cleanup). Leases provide automatic recovery with a bounded window.

---

### Strategy Comparison Summary

| Strategy | Cross-Process | Cross-Host | Crash Recovery | External Deps | Complexity | v1 Recommendation |
|---|---|---|---|---|---|---|
| In-memory locking | No | No | No | None | Very Low | **Rejected** |
| File locking | Yes | No | Manual (stale detection) | Filesystem | Low | **Acceptable fallback** |
| Database locking | Yes | Yes | Manual (timeout) | Database (existing) | Medium | **Primary strategy** |
| Distributed locking | Yes | Yes | Built-in (TTL) | Redis/ZK/etcd | High | **Deferred to v2** |
| Idempotency keys | Yes | Yes | N/A | Key store (DB) | Low | **Complementary** |
| Execution leases | Yes | Yes | Built-in (lease expiry) | Database | Medium | **Enhancement to DB locking** |

---

## Recommended Architecture

### v1 Strategy: Database-Backed Lock with Execution Lease

The primary locking strategy for v1 is **database-backed row-level locking with execution leases**, combined with **idempotency keys** as a complementary deduplication mechanism.

**Rationale**:

1. **Database locking** uses the existing `history_store` infrastructure — no new external dependencies. It provides cross-process and cross-host coordination with atomic guarantees.

2. **Execution leases** add crash recovery — a crashed workflow's lock auto-expires, allowing retry without manual intervention.

3. **Idempotency keys** prevent re-execution of already-completed runs, even if the idempotency key is presented after the lock is released.

4. **File locking** is available as a fallback strategy for environments without database connectivity (development, CI).

### Architecture Components

```
┌─────────────────────────────────────────────────────────────────────┐
│                      WorkflowRuntimeLocking                          │
│                                                                      │
│  ┌──────────────────────────┐    ┌─────────────────────────────────┐ │
│  │   WorkflowExecutionGuard  │    │   WorkflowIdempotencyRegistry   │ │
│  │   (Lock Interface)        │    │   (Deduplication Interface)     │ │
│  └──────────┬───────────────┘    └──────────┬──────────────────────┘ │
│             │                               │                         │
│  ┌──────────▼───────────────────────────────▼──────────────────────┐ │
│  │                     LockProviderRegistry                         │ │
│  │                                                                  │ │
│  │  ┌─────────────┐   ┌────────────┐   ┌──────────────────────┐   │ │
│  │  │  DBBacked    │   │  FileBased  │   │  InMemoryFallback   │   │ │
│  │  │  LockProvider│   │ LockProvider│   │  LockProvider       │   │ │
│  │  └─────────────┘   └────────────┘   └──────────────────────┘   │ │
│  └──────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### Core Contracts

```python
# New: Lock acquisition/release contract
@dataclass(frozen=True, slots=True)
class LockAcquisition:
    lock_id: str              # "{workflow_id}" (scope = workflow)
    holder_id: str            # "{hostname}-{pid}-{pipeline_run_id}"
    acquired_at: str          # ISO timestamp
    expires_at: str           # ISO timestamp (acquired_at + lease_ttl)
    lease_duration_s: int     # How long the lease is valid

# New: Idempotency record
@dataclass(frozen=True, slots=True)
class IdempotencyRecord:
    idempotency_key: str      # "{workflow_id}-{scope}-{schedule_slot}"
    pipeline_run_id: str      # The run that claimed this key
    status: str               # "completed" | "failed" | "in_progress"
    created_at: str           # ISO timestamp
```

### Modified: `WorkflowRunner.run()` lifecycle

```
WorkflowRunner.run(definition, initial_artifact, metadata)
│
├── 0. RESOLVE lock provider from registry
│      (DB → File → InMemory priority order)
│
├── 1. GENERATE idempotency key (if scheduled run)
│      key = f"{workflow_id}-{schedule_date}"
│
├── 2. CHECK idempotency (if key provided)
│      IF key exists AND status == "completed" → skip, return cached result
│
├── 3. ACQUIRE execution lock
│      lock = lock_provider.acquire(
│          lock_id=workflow_id,
│          holder_id=context.pipeline_run_id,
│          lease_duration_s=DEFAULT_LEASE_S,
│      )
│      IF lock is None → raise LockAcquisitionError (workflow busy)
│
├── 4. EXECUTE stages (unchanged from current model)
│      ├── FOR each stage_def in stages:
│      │     ├── stage = STAGE_REGISTRY[type](config)
│      │     ├── result = stage.run(input_artifact, context)
│      │     ├── IF FAILED → break
│      │     └── current_artifact = result.output_artifact
│      │
│      └── Periodic lease refresh (every REFRESH_INTERVAL_S)
│             lock_provider.refresh(lock)
│
├── 5. RELEASE lock
│      lock_provider.release(lock)
│
├── 6. RECORD idempotency (if key provided)
│      idempotency_registry.record(
│          key=idempotency_key,
│          pipeline_run_id=context.pipeline_run_id,
│          status=overall_status,
│      )
│
├── 7. Build WorkflowResult, persist debug artifact
└── 8. Return WorkflowResult
```

### Error Handling

| Scenario | Behaviour |
|---|---|
| **Lock acquisition failure** | Raise `LockAcquisitionError` with details (who holds the lock, when it expires). Caller decides whether to retry or queue. |
| **Lease refresh failure** | Log warning, continue execution. The last successful refresh timestamp is used for stale detection. |
| **Lease expiry during execution** | Current execution finishes, but the lock is potentially available for another worker. Audit trail records `LEASE_EXPIRED_DURING_EXECUTION`. |
| **Crash before lock release** | Lease auto-expires after `lease_duration_s`. A subsequent run will acquire the lock after expiry + grace period. |
| **Idempotency key collision** | Atomic `INSERT ... ON CONFLICT DO NOTHING` ensures only one run claims the key. Second run receives `IdempotencyRejectionError`. |

### Configuration

```python
# New configuration parameters
LOCK_DEFAULT_LEASE_S: int = 300        # 5 minutes — covers most workflows
LOCK_REFRESH_INTERVAL_S: int = 30      # Refresh every 30 seconds
LOCK_MAX_RETRIES: int = 3              # Max lock acquisition retries
LOCK_RETRY_DELAY_S: int = 5            # Base delay for retry backoff
LOCK_PROVIDER: str = "database"        # "database" | "file" | "memory"
LOCK_DB_TABLE: str = "workflow_locks"  # Database table name

IDEMPOTENCY_ENABLED: bool = True       # Enable idempotency key checking
IDEMPOTENCY_KEY_TTL_DAYS: int = 7      # Keep completed keys for 7 days
IDEMPOTENCY_DB_TABLE: str = "workflow_idempotency"
```

### File Layout

```
src/workflow_runtime/locking/
├── __init__.py                          # Public API: acquire_lock, release_lock
├── execution_guard.py                   # WorkflowExecutionGuard class
├── lock_provider.py                     # LockProvider ABC + registry
├── providers/
│   ├── __init__.py
│   ├── db_lock_provider.py              # Database-backed lock with leases
│   ├── file_lock_provider.py            # File-based lock (fallback)
│   └── memory_lock_provider.py          # In-memory lock (dev/test fallback)
├── idempotency.py                       # WorkflowIdempotencyRegistry
└── models.py                            # LockAcquisition, IdempotencyRecord dataclasses

Modified files:
├── src/workflow_runtime/runtime/workflow_runner.py
│   └── Integrate lock acquisition/release into run() lifecycle
├── src/workflow_runtime/contracts/execution_context.py
│   └── Add lock_acquisition field (Optional[LockAcquisition])
├── src/storage/history_store.py
│   └── Add lock management methods (acquire_lock, release_lock, refresh_lease)
```

---

## Runtime Impact

### Execution Flow Changes

| Aspect | Before | After |
|---|---|---|
| `run()` lifecycle | Validate → Execute → Return | Validate → Lock → Execute → Refresh → Release → Record → Return |
| Latency overhead | None | +2 DB round trips (acquire + release) + periodic refresh (~1-5ms each) |
| Failure mode | Direct failure on stage error | `LockAcquisitionError` if busy; `IdempotencyRejectionError` if already run |
| Crash behaviour | Unrecoverable (no retry) | Lease auto-expires → retryable |
| Debug artifacts | Always written | Written only if lock was acquired (prevents half-written artifacts on rejected runs) |
| Error propagation | Returns `WorkflowResult.FAILED` | Raises or returns specific lock rejection result |

### Performance Considerations

- **Lock acquisition overhead**: ~1-5ms per run (DB round trip). Negligible compared to workflow execution time (seconds to minutes).
- **Lease refresh overhead**: ~1-5ms every 30 seconds. Negligible.
- **No impact on stage execution**: Stage `run()` methods are unchanged — locking is a wrapper around the execution lifecycle.
- **Concurrency**: Database row-level locking allows concurrent execution of *different* workflows. Only *same* workflow_id executions are serialized.

### Deployment Impact

- **Database schema migration**: New `workflow_locks` and `workflow_idempotency` tables required.
- **No new infrastructure**: Reuses existing database (history_store).
- **No API changes**: `WorkflowRunner.run()` signature is unchanged.
- **No configuration changes for existing deployments**: Lock provider defaults to `database`; falls back to `file` if DB is unavailable.

---

## Contract Impact

### New Public Contracts

| Contract | Type | Scope |
|---|---|---|
| `LockAcquisition` | Dataclass (frozen) | `src/workflow_runtime/locking/models.py` |
| `IdempotencyRecord` | Dataclass (frozen) | `src/workflow_runtime/locking/models.py` |
| `LockAcquisitionError` | Exception | `src/workflow_runtime/locking/__init__.py` |
| `IdempotencyRejectionError` | Exception | `src/workflow_runtime/locking/__init__.py` |
| `WorkflowExecutionGuard` | ABC | `src/workflow_runtime/locking/execution_guard.py` |
| `LockProvider` | ABC | `src/workflow_runtime/locking/lock_provider.py` |
| `WorkflowIdempotencyRegistry` | ABC | `src/workflow_runtime/locking/idempotency.py` |

### Modified Contracts

| Contract | Change |
|---|---|
| `ExecutionContext` | Add optional `lock_acquisition: Optional[LockAcquisition]` field |
| `WorkflowResult` | Add optional `idempotency_key: Optional[str]` and `lock_status: Optional[str]` fields |

### Unchanged Contracts

| Contract | Reason |
|---|---|
| `WorkflowDefinition` | No change — locking is a runtime concern, not a definition concern |
| `StageDefinition` | No change — stages are unaware of locking |
| `StageResult` | No change — locking is outside stage boundaries |
| `WorkflowValidator` | No change — validation does not involve runtime state |

### Database Schema

```sql
-- New: workflow_locks table
CREATE TABLE workflow_locks (
    lock_id            TEXT PRIMARY KEY,          -- workflow_id
    holder_id          TEXT NOT NULL,             -- pipeline_run_id
    acquired_at        TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at         TIMESTAMP NOT NULL,
    lease_duration_s   INTEGER NOT NULL DEFAULT 300,
    hostname           TEXT NOT NULL,
    pid                INTEGER,
    refresh_count      INTEGER NOT NULL DEFAULT 0,
    last_refreshed_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

-- New: workflow_idempotency table
CREATE TABLE workflow_idempotency (
    idempotency_key    TEXT PRIMARY KEY,          -- "{workflow_id}-{schedule_slot}"
    pipeline_run_id    TEXT NOT NULL,
    status             TEXT NOT NULL,              -- "completed" | "failed" | "in_progress"
    created_at         TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at       TIMESTAMP,
    result_summary     TEXT                        -- JSON summary of WorkflowResult
);
```

---

## Testing Strategy

### Unit Tests

| Test Category | Test Cases | Priority |
|---|---|---|
| **Lock acquisition** | — Acquire lock when free<br>— Acquire lock fails when held<br>— Acquire lock retries with backoff<br>— Lock timeout (lease expires) | P0 |
| **Lock release** | — Release held lock<br>— Release already-released lock (idempotent)<br>— Release lock held by another holder (error) | P0 |
| **Lease refresh** | — Refresh before expiry succeeds<br>— Refresh after expiry fails<br>— Refresh for expired lock returns error | P0 |
| **Idempotency** | — Unique key passes<br>— Duplicate key rejected<br>— Key TTL expiry cleanup<br>— Key collision atomicity (concurrent writes) | P0 |
| **Lock provider fallback** | — DB provider fails → fallback to file<br>— File provider fails → fallback to memory<br>— All providers fail → error | P1 |
| **Execution guard** | — Guard wraps run() successfully<br>— Guard rejects duplicate execution<br>— Guard recovers from crash (lease expiry)<br>— Guard with idempotency key skips completed runs | P0 |

### Integration Tests

| Scenario | Setup | Expected Behaviour |
|---|---|---|
| **Same workflow, concurrent triggers** | Two threads call `run()` simultaneously with same `workflow_id` | Second caller receives `LockAcquisitionError` |
| **Different workflows, concurrent** | Two threads call `run()` simultaneously with different `workflow_id`s | Both succeed (no cross-workflow interference) |
| **Scheduled + manual overlap** | Start a long-running workflow, then trigger manual run | Manual run receives lock rejection |
| **Crash recovery** | Acquire lock, simulate process kill, wait for lease expiry, then run again | Second run acquires lock after lease expiry |
| **Idempotency key dedup** | Run workflow with idempotency key, run it again with same key | Second run returns cached result (no execution) |
| **Lock provider fallback** | Shut down database, run workflow | Falls back to file locking, or fails gracefully with error message |

### Performance Tests

| Test | Measurement | Target |
|---|---|---|
| Lock acquisition latency (p50/p99) | Time to acquire lock | <10ms p50, <50ms p99 |
| Lease refresh overhead | CPU time per refresh | <1ms |
| Concurrent workflow throughput | Runs/second with N simultaneous workflows | >= current throughput |
| Crash recovery time | Time from crash to retryable | <= lease_duration_s + grace_period_s |

### Boundary Verification

No changes to import boundaries are expected — the locking module lives within `src/workflow_runtime/`, which is already within the Workflow Runtime boundary. Existing boundary verification tests (`scripts/verify_boundaries.py`) must continue to pass.

---

## Documentation Requirements

### New Documents

| Document | Location | Content |
|---|---|---|
| Architecture Plan | `docs/architecture/WORKFLOW_RUNTIME_LOCKING_V1_PLAN.md` | This document |
| Implementation Summary | `docs/architecture/WORKFLOW_RUNTIME_LOCKING_V1_SUMMARY.md` | What was built, design decisions, configuration |
| Handoff Document | `docs/architecture/WORKFLOW_RUNTIME_LOCKING_V1_HANDOFF.md` | Runbook, rollback steps, monitoring |
| ADR | `docs/adr/ADR-008-workflow-runtime-locking.md` | Decision record for v1 locking strategy |

### Updated Documents

| Document | Update |
|---|---|
| `docs/ROADMAP.md` | Mark "Workflow Runtime Locking" as completed |
| `TECHNICAL_DEBT.md` | Close "Lack of distributed locking; potential duplicate job execution" item |
| `docs/architecture/V0_5_RUNTIME_HARDENING_PLAN.md` | Update status of Workflow Runtime Locking section |

### Code Documentation

- Docstrings on all public classes (`WorkflowExecutionGuard`, `LockProvider`, `WorkflowIdempotencyRegistry`)
- README section in `src/workflow_runtime/locking/__init__.py` explaining the locking strategy
- Example usage in module docstring for `execution_guard.py`

---

## Definition of Done

- [ ] `LockProvider` ABC defined with `acquire`, `release`, `refresh` methods
- [ ] `DBLockProvider` implementation — acquires lock in `workflow_locks` table, supports leases
- [ ] `FileLockProvider` implementation — file-based lock with stale detection
- [ ] `MemoryLockProvider` implementation — in-memory lock (for tests and dev)
- [ ] `LockProviderRegistry` — selects provider by configured priority
- [ ] `WorkflowIdempotencyRegistry` implementation — deduplication via `workflow_idempotency` table
- [ ] `WorkflowExecutionGuard` wraps `WorkflowRunner.run()` with lock lifecycle
- [ ] `ExecutionContext` updated with optional `lock_acquisition` field
- [ ] `WorkflowResult` updated with optional `idempotency_key` and `lock_status`
- [ ] Idempotency key generation for scheduled runs (deterministic per schedule slot)
- [ ] Lock acquisition error handling (distinct error types)
- [ ] Idempotency rejection handling (returns cached result)
- [ ] Lease refresh loop in `run()` lifecycle
- [ ] Stale lock cleanup mechanism (cleanup job or TTL-based expiry)
- [ ] Database schema migration for `workflow_locks` and `workflow_idempotency` tables
- [ ] Unit tests for all lock providers (DB, File, Memory)
- [ ] Unit tests for idempotency registry
- [ ] Integration tests:
  - [ ] Same workflow concurrent execution prevention
  - [ ] Different workflow concurrent execution allowed
  - [ ] Crash recovery via lease expiry
  - [ ] Idempotency key deduplication
  - [ ] Lock provider fallback chain
- [ ] Performance benchmarks for lock acquisition latency
- [ ] `pytest tests/ -v` passes
- [ ] `python scripts/verify_boundaries.py` passes (no regressions)
- [ ] `docs/architecture/WORKFLOW_RUNTIME_LOCKING_V1_SUMMARY.md` created
- [ ] `docs/architecture/WORKFLOW_RUNTIME_LOCKING_V1_HANDOFF.md` created
- [ ] `docs/adr/ADR-008-workflow-runtime-locking.md` created
- [ ] `docs/ROADMAP.md` updated
- [ ] `TECHNICAL_DEBT.md` updated — locking item closed
- [ ] `docs/architecture/V0_5_RUNTIME_HARDENING_PLAN.md` updated
- [ ] Git commit and push completed
- [ ] Milestone tag `v0.5-workflow-runtime-locking` created
- [ ] Future agent can continue from repository documentation alone

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **Lock contention reduces throughput** | Low | Medium | Row-level locking per workflow_id — different workflows are unaffected. Monitor lock acquisition latency. |
| **Lease TTL misconfiguration** | Medium | High | Start with generous default (300s). Make configurable. Add monitoring for lease refresh failures. |
| **Database becomes lock bottleneck** | Low | Medium | Lock operations are lightweight. If needed, add connection pooling and monitoring. |
| **File lock fallback unreliable on Windows** | Medium | Low | Windows has different file locking semantics (`msvcrt` vs `fcntl`). Test on Windows CI. |
| **Idempotency key collision for different runs** | Low | High | Key design must include scope (schedule slot, trigger type). Key collision should be impossible for different workflow instances. |
| **Distributed deadlock across workflows** | Low | Medium | No cross-workflow lock dependencies exist. Each workflow locks only its own `workflow_id`. |
| **Lock table grows unbounded** | Low | Low | Each workflow has a single row (UPSERT pattern). Idempotency table uses TTL cleanup. |
| **Existing runs fail on first deploy** | Low | Low | Backward-compatible: locking is opt-in for v1. Old `run()` calls without locking continue to work. Migration path documented in handoff. |

---

## Effort Estimate

| Component | Effort (person-days) | Dependencies |
|---|---|---|
| `LockProvider` ABC + `DBLockProvider` | 2 | History store access, schema migration |
| `FileLockProvider` | 1 | File I/O, stale detection |
| `MemoryLockProvider` | 0.5 | Simple dict-based implementation |
| `LockProviderRegistry` + fallback chain | 0.5 | Configuration |
| `WorkflowIdempotencyRegistry` | 1 | Schema migration, key TTL cleanup |
| `WorkflowExecutionGuard` + `run()` integration | 1.5 | Must not break existing callers |
| Lease refresh loop | 1 | Background task or inline refresh |
| Error handling + distinct exception types | 0.5 | Rejected run differentiation |
| Database schema migration | 0.5 | `workflow_locks`, `workflow_idempotency` tables |
| Unit tests | 2 | All providers, guard, idempotency |
| Integration tests | 1.5 | Concurrent scenarios, crash recovery |
| Performance benchmarks | 0.5 | latency, throughput measurements |
| Documentation (summary, handoff, ADR, ROADMAP, TECHDEBT) | 1.5 | Per governance rules |
| **Total** | **~14 person-days (~2.8 person-weeks)** | |

**Comparison with NEXT_MILESTONE_RECOMMENDATION.md estimate**: The recommendation estimated ~1 week. The detailed estimate above is ~2.8 person-weeks due to the inclusion of multiple lock providers (DB + File + Memory), the idempotency registry, lease refresh logic, comprehensive test coverage, and governance documentation. The original estimate may have assumed a simpler single-strategy implementation.

**Optimization options**:
- **Minimum Viable Locking (1 week)**: Implement only `DBLockProvider` + `WorkflowExecutionGuard` + basic unit tests. Defer file fallback, idempotency, lease refresh, and performance benchmarks to v1.1.
- **Full v1 (2.8 weeks)**: All components as described above.

Recommendation: **Full v1** for production safety. The incremental effort (1.8 additional weeks) significantly reduces risk across all failure modes.

---

## Release Plan

### Phase 1: Implementation (Weeks 1-2)

1. Schema migration — create `workflow_locks` and `workflow_idempotency` tables
2. Implement `LockProvider` ABC and all providers (DB → File → Memory)
3. Implement `WorkflowExecutionGuard`
4. Implement `WorkflowIdempotencyRegistry`
5. Integrate guard into `WorkflowRunner.run()`
6. Add lease refresh loop
7. Add error handling and distinct exception types

### Phase 2: Testing (Week 2-3)

1. Unit tests for all lock providers
2. Unit tests for idempotency registry
3. Integration tests for concurrent execution scenarios
4. Integration tests for crash recovery and lease expiry
5. Integration tests for provider fallback chain
6. Performance benchmarks
7. Verify boundary compliance (`scripts/verify_boundaries.py`)

### Phase 3: Documentation & Deployment (Week 3)

1. Create architecture summary document
2. Create handoff document
3. Create ADR-008
4. Update ROADMAP.md, TECHNICAL_DEBT.md, V0_5_RUNTIME_HARDENING_PLAN.md
5. Configuration review and default tuning
6. Deploy to staging environment
7. Run full test suite in staging
8. Deploy to production with monitoring
9. Rollback plan: toggle `LOCK_PROVIDER` to `"memory"` (disables cross-process locking) or `"file"` (single-host lock only)

### Rollback Procedure

```bash
# Immediate rollback (disable locking):
# 1. Set LOCK_PROVIDER=memory in environment configuration
#    This reverts to the pre-locking behaviour (no cross-process coordination)
# 2. Restart workflow runtime processes
# 3. Verify all workflows execute without lock errors

# Permanent rollback (remove locking):
# 1. Revert WorkflowRunner.run() to pre-locking lifecycle
# 2. Remove src/workflow_runtime/locking/ package
# 3. Drop workflow_locks and workflow_idempotency tables
# 4. Revert ExecutionContext and WorkflowResult to original contracts
```

### Migration for Existing Runs

- Locking is **opt-in** — existing `run()` calls without locking continue to work
- The `WorkflowExecutionGuard` is transparent to callers when not configured
- Migration plan:
  1. Deploy locking code with `LOCK_PROVIDER=memory` (no change in behaviour)
  2. Switch to `LOCK_PROVIDER=database` for new environments first
  3. Monitor for `LockAcquisitionError` logs
  4. Enable locking in production after monitoring period

---

## Appendices

### A. Glossary

| Term | Definition |
|---|---|
| **Lock** | A mechanism that prevents concurrent execution of the same workflow |
| **Lease** | A time-bound lock that auto-expires after a configurable duration |
| **Idempotency key** | A deterministic key that identifies a unique workflow invocation; prevents duplicate execution |
| **Lock provider** | A pluggable implementation of lock semantics (DB, file, in-memory) |
| **Execution guard** | The wrapper around `run()` that manages the lock lifecycle |
| **Stale lock** | A lock whose lease has expired but has not been released |
| **TOCTOU** | Time-of-check-to-time-of-use — a race condition between checking and acquiring a resource |

### B. Related Documents

| Document | Location | Relationship |
|---|---|---|
| PLATFORM_ARCHITECTURE_REVIEW.md | `docs/architecture/` | Identifies locking as high-priority technical debt |
| V0_5_RUNTIME_HARDENING_PLAN.md | `docs/architecture/` | Parent milestone plan for v0.5 |
| NEXT_MILESTONE_RECOMMENDATION.md | `docs/architecture/` | Recommends Workflow Runtime Locking as next milestone |
| ROADMAP.md | `docs/` | Lists Workflow Runtime Locking as next objective |
| TECHNICAL_DEBT.md | `./` | Tracks locking as known debt to be closed |
| PROJECT_CONTEXT.md | `docs/architecture/` | Governance rules and Definition of Done |
| ADR-008 (new) | `docs/adr/` | Decision record for v1 locking strategy |

### C. Future Considerations (v2+)

| Feature | Trigger | Strategy |
|---|---|---|
| Distributed locking (Redis/etcd) | Multi-host deployment | Replace `DBLockProvider` with `RedisLockProvider` |
| Lock-free execution via event sourcing | High-throughput requirements | Replace locking with deterministic event-sourced execution ordering |
| Dynamic lease TTL | Variable-duration workflows | Estimate TTL from historical execution times |
| Dead-letter queue | Persistent lock failures | Migrate failed runs to a separate retry queue with escalation |
| Cross-workflow lock ordering | Workflow dependencies | Define lock acquisition order to prevent distributed deadlocks |

---

## End of Plan