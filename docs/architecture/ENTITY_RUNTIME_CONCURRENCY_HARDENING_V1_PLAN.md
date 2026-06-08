# Entity Runtime Concurrency Hardening v1 — Architecture Plan

**Date**: 2026-06-05  
**Author**: Platform Architecture Review  
**Status**: Draft — pending review  
**Milestone**: v0.5-runtime-hardening  
**Version**: 1.0  

---

## Problem Statement

The Entity Runtime v1 currently produces immutable `EntitySet` objects deterministically from Document Runtime output. However, the runtime has no concurrency controls for entity writes, merges, or reconciliation. In a multi-worker or multi-workflow environment, the following concrete risks exist:

### 1. Lost Updates on Entity Merge

When two workflow executions extract entities for the same logical entity (e.g., the same supplier from two different documents), the second extraction can silently overwrite the first without detection. No version checking or conflict detection exists.

### 2. Duplicate Entity Writes

The Matching Runtime and downstream consumers may write resolved/canonical entities without idempotency guarantees. If an entity write is retried (due to network error, timeout, or crash), duplicate entity records accumulate without detection.

### 3. Concurrent Entity Mutations

Multiple runtime components (Entity Runtime extraction, Matching Runtime reconciliation, Review Runtime corrections) can concurrently mutate the same entity record. Without locking or versioning, mutations interleave and corrupt canonical state.

### 4. Crash-Prone Entity Operations

If a process crashes mid-write (e.g., after extracting but before persisting an entity set), there is no mechanism to detect the partial write, recover, or retry. Stale or partial entity state persists.

### 5. No Execution Leasing for Entity Operations

Entity extraction, merging, and reconciliation operations have no lease mechanism. A crashed extraction holds no recoverable state — the operation must be manually detected and retried.

### 6. Hot Entity Contention

Frequently-accessed entities (e.g., high-volume suppliers, popular products) experience contention when multiple workflows attempt concurrent reads and writes. Without escalation to pessimistic locking, contention causes excessive retries and degraded throughput.

### Architecture Assessment References

These deficiencies were identified during the Architecture Review (see `docs/architecture/PLATFORM_ARCHITECTURE_REVIEW.md`). The absence of entity-level concurrency controls is the highest-risk remaining item in the v0.5 Runtime Hardening milestone after Workflow Runtime Locking.

> **Note**: Event Sourcing is explicitly deferred to v2 as per the Architecture Review recommendation. This plan addresses v1 requirements only.

---

## Current Entity Runtime Execution Model

### Architecture Overview

The Entity Runtime v1 follows a stateless extraction model:

```
IngestionPipelineResult (from Document Runtime)
        │
        ▼
  EntityExtractionEngine.extract(pipeline_result)
        │
        ├── 1. EntityExtractor.extract_document_references()
        ├── 2. EntityExtractor.extract_suppliers()
        ├── 3. EntityExtractor.extract_customers()
        ├── 4. EntityExtractor.extract_financials()
        ├── 5. EntityExtractor.extract_line_items()
        │
        ├── 6. EntityValidator.validate(entity_set)
        ├── 7. TextNormalizer.normalize(entity_set)
        ├── 8. ConfidenceScorer.score(entity_set)
        │
        └── 9. Return EntitySet (immutable, in-memory)
```

### Key Properties

| Property | Current Behaviour |
|---|---|
| **Stateless** | `EntityExtractionEngine` has no persistent state between `extract()` calls |
| **Idempotency** | None — no deduplication key, no write history check |
| **Versioning** | None — `EntitySet` has no version field |
| **Locking** | None — no mutex, no DB lock, no lease for entity operations |
| **Concurrency model** | Unbounded — any number of `extract()` calls for the same document may execute simultaneously |
| **Entity identity** | `source_document_id` is the only identifier — cannot differentiate versions |
| **Side-effect isolation** | None — duplicate extracts produce duplicate downstream writes |
| **Crash recovery** | None — crashed extractions have no recovery or retry mechanism |
| **Persistence** | None — `EntitySet` is in-memory only; no entity version store exists |

### Execution Entry Points

Entity mutations can originate from:

1. **Entity Extraction** (`src/entity_runtime/engine.py`): Produces new `EntitySet` from Document Runtime output.

2. **Matching Runtime reconciliation** (`src/matching_runtime/`): Writes resolved/canonical entity matches back to the entity store.

3. **Workflow merge stages** (`src/workflow_runtime/operations/`): Downstream stages that merge entity sets from multiple documents.

4. **Future Review Runtime corrections**: Manual entity corrections that must be persisted as new versions.

---

## Current Persistence Model

### Storage Layer

The current persistence model is minimal:

| Storage | Purpose | Concurrency Controls |
|---|---|---|
| `src/storage/history_store.py` | CSV-based price history snapshots | None |
| `src/storage/history_store.py` | Price change detection | None — DataFrame-based, no row-level locking |
| Debug artifacts (file system) | JSON debug output per workflow run | None |

### No Entity Store

There is **no dedicated entity persistence layer**. Entity sets are:

1. Produced as in-memory objects during workflow execution
2. Passed between workflow stages via `StageResult.output_artifact`
3. Persisted only through downstream consumers (history store, alert engine, dashboard)
4. Not queryable, versionable, or recoverable after workflow completion

### Missing Concurrency Controls

| Concern | Current State |
|---|---|
| **Atomic writes** | No — file writes are not atomic |
| **Version checks** | No — no version field exists on any entity contract |
| **Write ordering** | No — last-writer-wins, no conflict detection |
| **Duplicate detection** | No — no idempotency keys for entity writes |
| **Transaction boundaries** | No — no transactional scope for entity operations |
| **Read isolation** | No — concurrent readers may see partial writes |

### Database Schema Status

The only database tables in the project are:

- `workflow_locks` (from Workflow Runtime Locking v1)
- `workflow_idempotency` (from Workflow Runtime Locking v1)

No entity store tables exist.

---

## Canonical Entity Lifecycle

The proposed v1 concurrency-hardened entity lifecycle:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        CANONICAL ENTITY LIFECYCLE                        │
│                                                                          │
│  ┌──────────┐    ┌───────────┐    ┌──────────┐    ┌──────────────┐     │
│  │ EXTRACT  │───▶│  MERGE    │───▶│  RESOLVE │───▶│   ARCHIVE    │     │
│  │ (v1)     │    │ (v2)      │    │ (v3)     │    │   (TTL)      │     │
│  └──────────┘    └───────────┘    └──────────┘    └──────────────┘     │
│       │               │               │                │               │
│       ▼               ▼               ▼                ▼               │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    ENTITY VERSION STORE                          │   │
│  │  (append-only version history, current version indexed)         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  Stages:                                                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Stage 1: EXTRACT — produce EntitySet from Document Runtime      │   │
│  │   - Assign version v1                                            │   │
│  │   - Acquire execution lease                                      │   │
│  │   - Write with optimistic locking                                │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Stage 2: MERGE — merge EntitySet with existing canonical entity │   │
│  │   - Read current version with version check                     │   │
│  │   - Compute merged fields                                       │   │
│  │   - Compare-and-swap write (version v1→v2)                      │   │
│  │   - Retry on conflict                                           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Stage 3: RESOLVE — apply reconciliation or correction           │   │
│  │   - Read current version (optimistic)                           │   │
│  │   - Escalate to pessimistic lock if contended                   │   │
│  │   - Write correction (version v2→v3)                            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Stage 4: ARCHIVE — garbage collect old versions                 │   │
│  │   - Delete versions beyond retention window                     │   │
│  │   - Compact version history                                     │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Entity State Transitions

```
                  ┌─────────────────┐
                  │   PENDING       │  (extraction in progress, lease held)
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
              ┌──▶│   ACTIVE        │  (current version, available for reads)
              │   └────────┬────────┘
              │            │
              │            ▼  (merge/correction produces new version)
              │   ┌─────────────────┐
              │   │   SUPERSEDED    │  (older version, still in store)
              │   └────────┬────────┘
              │            │
              │            ▼  (retention window exceeded)
              │   ┌─────────────────┐
              └───│   ARCHIVED      │  (compacted/deleted from version store)
                  └─────────────────┘
```

---

## Versioned Entity Architecture

### Version Numbering

Each entity in the Entity Version Store carries a monotonically increasing version number:

```
Format: <entity_type>/<entity_id>/v<version_number>

Examples:
  supplier/acme-corp/v1
  supplier/acme-corp/v2
  line_item/inv-2026-001-item-3/v1
  document_ref/inv-2026-001/v1
```

**Version Number Rules:**

| Rule | Description |
|---|---|
| **Start at 1** | First write of a new entity always sets version = 1 |
| **Monotonic** | Version numbers increase by 1 for each successive write |
| **Gap-free (logical)** | Version numbers should be sequential per entity |
| **Entity-scoped** | Each entity has its own version sequence — no global counter |
| **Immutable reference** | Once written, a version-numbered entity is never mutated in-place |

### Version Field on Contracts

```python
# New field added to all entity contracts
@dataclass(frozen=True, slots=True)
class VersionedEntityMixin:
    entity_version: int = 1          # Current version number
    entity_created_at: str = ""      # ISO timestamp of v1 creation
    entity_updated_at: str = ""      # ISO timestamp of this version
    entity_previous_version: int = 0 # 0 for v1, else v(n-1)
```

### Version Identity Resolution

Entity identity is resolved through a composite key:

```
entity_version_key = f"{entity_type}:{source_document_id}:{entity_natural_key}"
```

Where:
- `entity_type`: One of `supplier`, `customer`, `line_item`, `document_reference`, `document_financials`
- `source_document_id`: The document from which the entity was extracted (or `canonical` for merged entities)
- `entity_natural_key`: A deterministic key derived from the entity's identifying fields (e.g., supplier name, invoice number, SKU)

For canonical merged entities (after Matching Runtime reconciliation), the key uses `canonical` as the document ID:

```
canonical_entity_version_key = f"supplier:canonical:acme-corp"
```

### Entity Version Record Structure

```python
@dataclass(frozen=True, slots=True)
class EntityVersionRecord:
    """Record in the Entity Version Store."""
    entity_version_key: str          # Composite key
    entity_type: str                 # Entity type discriminator
    entity_id: str                   # Natural key within type
    version: int                     # Monotonic version number
    state: str                       # "active" | "superseded" | "archived"
    data: dict                       # Full entity data (serialized)
    checksum: str                    # SHA-256 of serialized data
    previous_checksum: str           # SHA-256 of version-1 data (empty string for v1)
    created_at: str                  # ISO timestamp
    created_by: str                  # pipeline_run_id or "system"
    lease_holder: str = ""           # pipeline_run_id holding write lease (empty when released)
    lease_expires_at: str = ""       # ISO timestamp of lease expiry
```

---

## Optimistic Locking Architecture

### Overview

Optimistic locking is the **primary concurrency mechanism** for v1. Every entity write uses a compare-and-swap (CAS) pattern: the writer reads the current version, applies changes, and writes only if the version has not changed since the read.

### Compare-and-Swap Semantics

```
┌─────────────────────────────────────────────────────────────────────┐
│                    COMPARE-AND-SWAP WRITE PATTERN                     │
│                                                                      │
│  Writer A                          Writer B                          │
│     │                                 │                              │
│     ├── 1. READ entity v5            │                              │
│     │    (current_version = 5)       │                              │
│     │                                 │                              │
│     ├── 2. COMPUTE new fields        ├── 1. READ entity v5          │
│     │    (based on v5)              │    (current_version = 5)      │
│     │                                 │                              │
│     ├── 3. WRITE with CAS           ├── 2. COMPUTE new fields       │
│     │    WHERE version = 5          │    (based on v5)              │
│     │    SET version = 6            │                                │
│     │    ──────────────────────     ├── 3. WRITE with CAS           │
│     │    ✅ SUCCESS (v6 created)    │    WHERE version = 5          │
│     │                                 │    SET version = 6          │
│     │                                 │    ──────────────────────     │
│     │                                 │    ❌ CONFLICT               │
│     │                                 │    (version 5 no longer      │
│     │                                 │     current, now v6)        │
│     │                                 │                              │
│     │                                 ├── 4. RETRY                  │
│     │                                 │    READ v6                  │
│     │                                 │    COMPUTE based on v6      │
│     │                                 │    WRITE with CAS v6→v7     │
│     │                                 │    ──────────────────────     │
│     │                                 │    ✅ SUCCESS (v7 created)  │
└─────────────────────────────────────────────────────────────────────┘
```

### SQL CAS Pattern

```sql
-- Atomic compare-and-swap write
UPDATE entity_versions
SET
    version = :new_version,
    state = 'superseded',
    data = :new_data,
    checksum = :new_checksum,
    previous_checksum = :current_checksum,
    entity_updated_at = :now
WHERE
    entity_version_key = :entity_version_key
    AND version = :expected_version
    AND state = 'active';

-- If ROW_COUNT = 0, conflict detected → retry
-- If ROW_COUNT = 1, success → insert new version
INSERT INTO entity_versions (
    entity_version_key, entity_type, entity_id, version, state,
    data, checksum, previous_checksum, created_at, created_by
) VALUES (
    :entity_version_key, :entity_type, :entity_id, :new_version, 'active',
    :new_data, :new_checksum, :current_checksum, :now, :created_by
);
```

### Conflict Detection

| Condition | Detection | Behaviour |
|---|---|---|
| **Version mismatch** | `UPDATE` returns 0 rows | CAS conflict — another writer committed a newer version |
| **Data checksum mismatch** | Compare `SHA-256(data)` on read vs write | Data corruption detection — abort with `EntityCorruptionError` |
| **Entity not found** | `SELECT` returns 0 rows | Entity does not exist — treat as first write (version 1) |
| **Stale read** | Version read > 30 seconds ago | Force re-read before CAS write |

### Conflict Types

```python
@dataclass(frozen=True, slots=True)
class ConflictInfo:
    conflict_type: str                   # "version_mismatch" | "checksum_mismatch" | "entity_not_found"
    expected_version: int
    actual_version: int
    expected_checksum: str
    actual_checksum: str
    current_holder: str                  # pipeline_run_id holding the latest version
    last_updated_at: str                 # ISO timestamp
```

### Retry Policy

```
┌───────────────────────────────────────────────────────────┐
│                    RETRY POLICY                            │
│                                                           │
│  Parameters:                                              │
│  ┌─────────────────────────────────────────────┐         │
│  │ OPTIMISTIC_RETRY_MAX_ATTEMPTS     = 3       │         │
│  │ OPTIMISTIC_RETRY_BASE_DELAY_MS   = 50      │         │
│  │ OPTIMISTIC_RETRY_MAX_DELAY_MS    = 500     │         │
│  │ OPTIMISTIC_RETRY_BACKOFF_MULTIPLIER = 2    │         │
│  └─────────────────────────────────────────────┘         │
│                                                           │
│  Algorithm:                                               │
│    1. Attempt CAS write                                   │
│    2. If conflict detected:                               │
│       a. Increment attempt counter                        │
│       b. If attempts >= MAX_ATTEMPTS → raise ConflictError│
│       c. Compute delay:                                   │
│            delay = min(BASE_DELAY * multiplier^attempt,   │
│                        MAX_DELAY)                         │
│            jitter = random(0, delay * 0.1)                │
│       d. Sleep(delay + jitter)                            │
│       e. Re-read current version                          │
│       f. Re-compute write based on new version            │
│       g. Go to step 1                                     │
│    3. If CAS succeeds → return                            │
│    4. If non-CAS error → raise immediately                │
│                                                           │
│  Exponential Backoff (attempt, delay_ms):                  │
│    Attempt 1:  50ms  (±5ms jitter)                        │
│    Attempt 2: 100ms (±10ms jitter)                        │
│    Attempt 3: 200ms (±20ms jitter)                        │
│    ─── Max attempts reached ───                           │
└───────────────────────────────────────────────────────────┘
```

### Escalation Policy

When optimistic locking retries exceed `OPTIMISTIC_RETRY_MAX_ATTEMPTS`, the system escalates:

```python
@dataclass(frozen=True, slots=True)
class EscalationPolicy:
    """When to escalate from optimistic to pessimistic locking."""
    max_optimistic_retries: int = 3       # After this many retries, escalate
    conflict_rate_threshold: float = 0.3  # If >30% of recent writes conflict, escalate
    escalation_window_minutes: int = 5    # Rolling window for conflict rate calculation
    cooldown_minutes: int = 15            # Time before auto-de-escalating to optimistic
```

---

## Idempotent Write Architecture

### Key Generation

Every entity write operation generates a deterministic idempotency key:

```python
def generate_entity_idempotency_key(
    entity_type: str,
    source_document_id: str,
    entity_natural_key: str,
    workflow_run_id: str,
    stage_name: str,
) -> str:
    """Generate a deterministic idempotency key for entity writes."""
    raw = f"{entity_type}:{source_document_id}:{entity_natural_key}:{workflow_run_id}:{stage_name}"
    return hashlib.sha256(raw.encode()).hexdigest()
```

**Key Components:**

| Component | Source | Purpose |
|---|---|---|
| `entity_type` | Entity class name | Type-scoped uniqueness |
| `source_document_id` | Document Runtime ID | Document-scoped uniqueness |
| `entity_natural_key` | Entity identifying fields (e.g., supplier name, invoice #) | Entity-scoped uniqueness |
| `workflow_run_id` | `ExecutionContext.pipeline_run_id` | Run-scoped uniqueness |
| `stage_name` | Workflow stage name (e.g., `entity_extract`) | Stage-scoped uniqueness |

### Idempotency Key Structure

```
┌─────────────────────────────────────────────────────────────────────┐
│                   IDEMPOTENCY KEY STRUCTURE                          │
│                                                                      │
│  entity_write:v1:{sha256(entity_type:source_doc_id:natural_key:     │
│                       pipeline_run_id:stage_name)}                   │
│                                                                      │
│  Example:                                                             │
│  entity_write:v1:a1b2c3d4e5f6...                                     │
│                                                                      │
│  Uniqueness guarantee:                                                │
│  - Same entity + same document + same run + same stage              │
│    = SAME key → duplicate rejected                                   │
│  - Same entity + same document + DIFFERENT run                     │
│    = DIFFERENT key → write allowed                                   │
│  - Same entity + DIFFERENT document                                 │
│    = DIFFERENT key → write allowed                                   │
└─────────────────────────────────────────────────────────────────────┘
```

### Duplicate Detection

```python
class EntityIdempotencyRegistry:
    """Detects and rejects duplicate entity writes."""

    def check_and_record(
        self,
        idempotency_key: str,
        entity_version_key: str,
        new_version: int,
        pipeline_run_id: str,
    ) -> IdempotencyResult:
        """
        Atomic check-and-record for idempotency.

        Returns:
            IdempotencyResult(status="accepted") if first write
            IdempotencyResult(status="duplicate", existing_version=..., existing_run=...) if duplicate
        """
        # SQL: INSERT INTO entity_idempotency (key, entity_version_key, version, pipeline_run_id, status)
        #      VALUES (?, ?, ?, ?, 'completed')
        #      ON CONFLICT(key) DO NOTHING
        #      RETURNING status;
        #
        # If INSERT succeeded → status = "accepted"
        # If INSERT failed (conflict) → status = "duplicate"
```

**Detection Scenarios:**

| Scenario | Key | Result |
|---|---|---|
| First write for entity | Unique | `accepted` |
| Same write retried (crash before commit) | Same key | `accepted` (if previous was `in_progress`) |
| Same write retried (crash after commit) | Same key | `duplicate` |
| Two different runs, same entity, same operation | Different keys | Both `accepted` |
| Two workflows, same entity, different stage | Different keys | Both `accepted` |

### Retention Policy

```python
@dataclass(frozen=True, slots=True)
class EntityIdempotencyConfig:
    """Configuration for entity idempotency retention."""
    retention_days: int = 7                    # Keep completed keys for 7 days
    in_progress_ttl_minutes: int = 60          # Expire in-progress keys after 60 minutes
    cleanup_batch_size: int = 1000             # Delete up to 1000 keys per cleanup cycle
    cleanup_interval_minutes: int = 60         # Run cleanup every 60 minutes
```

| State | Retention | Rationale |
|---|---|---|
| `completed` | 7 days | Covers typical retry windows across business days |
| `failed` | 7 days | Same as completed — allows diagnosis and manual retry |
| `in_progress` | 60 minutes (TTL) | If lease expired, the write should be retryable |

### Cleanup Strategy

```
┌─────────────────────────────────────────────────────────────────────┐
│                    IDEMPOTENCY CLEANUP STRATEGY                       │
│                                                                      │
│  Scheduled cleanup (background thread):                              │
│                                                                      │
│  1. Every CLEANUP_INTERVAL_MINUTES:                                 │
│     a. DELETE FROM entity_idempotency                               │
│        WHERE status IN ('completed', 'failed')                      │
│        AND created_at < NOW() - retention_days                      │
│        LIMIT cleanup_batch_size                                     │
│     b. UPDATE entity_idempotency                                    │
│        SET status = 'expired'                                       │
│        WHERE status = 'in_progress'                                 │
│        AND created_at < NOW() - in_progress_ttl_minutes             │
│                                                                      │
│  On-write cleanup (opportunistic):                                   │
│                                                                      │
│  1. After successful write, attempt:                                │
│     DELETE FROM entity_idempotency                                  │
│     WHERE entity_version_key = :key                                 │
│     AND created_at < NOW() - retention_days                         │
│                                                                      │
│  Safety:                                                             │
│  - Never delete in_progress records that are still within TTL      │
│  - Never delete records for entities that still have active leases  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Execution Lease Architecture

### Overview

Execution leases provide crash recovery for entity write operations. Every write acquires a lease before execution and releases it after completion. If the writer crashes, the lease expires and another worker can acquire it.

### Lease Acquisition

```
┌─────────────────────────────────────────────────────────────────────┐
│                     LEASE ACQUISITION                                 │
│                                                                      │
│  Precondition: No active lease exists on this entity version key    │
│                                                                      │
│  1. Generate holder_id = f"{hostname}-{pid}-{pipeline_run_id}"     │
│  2. Set lease_duration = ENTITY_LEASE_DEFAULT_S (default: 120s)    │
│  3. Atomic UPSERT:                                                   │
│       INSERT INTO entity_leases (                                    │
│           entity_version_key, holder_id, acquired_at,               │
│           expires_at, lease_duration_s                              │
│       ) VALUES (?, ?, NOW(), NOW() + :duration_s, :duration_s)      │
│       ON CONFLICT(entity_version_key) DO UPDATE                      │
│       SET holder_id = :holder_id,                                   │
│           acquired_at = NOW(),                                      │
│           expires_at = NOW() + :duration_s                          │
│       WHERE entity_leases.expires_at < NOW()                        │
│       RETURNING status;                                             │
│                                                                      │
│  4. If RETURNING status == 'conflict':                               │
│       Lease held by another writer → raise LeaseAcquisitionError    │
│  5. If RETURNING status == 'acquired':                               │
│       Proceed with entity write                                     │
│                                                                      │
│  Lease acquisition failure:                                          │
│  - Retry with exponential backoff (up to LEASE_RETRY_MAX_ATTEMPTS)  │
│  - If all retries fail: raise EntityBusyError with holder info     │
└─────────────────────────────────────────────────────────────────────┘
```

### Lease Refresh

```
┌─────────────────────────────────────────────────────────────────────┐
│                      LEASE REFRESH CYCLE                              │
│                                                                      │
│  Parameters:                                                         │
│  ┌─────────────────────────────────────────────┐                    │
│  │ ENTITY_LEASE_DEFAULT_S           = 120      │ (2 minutes)         │
│  │ ENTITY_LEASE_REFRESH_INTERVAL_S  = 20       │ (every 20 seconds)  │
│  │ ENTITY_LEASE_REFRESH_GRACE_S     = 10       │ (10s grace period)  │
│  └─────────────────────────────────────────────┘                    │
│                                                                      │
│  Refresh loop (daemon thread per write operation):                    │
│                                                                      │
│  while write_in_progress:                                            │
│      sleep(REFRESH_INTERVAL_S)                                       │
│      UPDATE entity_leases                                            │
│      SET expires_at = NOW() + :duration_s,                          │
│          last_refreshed_at = NOW(),                                  │
│          refresh_count = refresh_count + 1                           │
│      WHERE entity_version_key = :key                                │
│      AND holder_id = :holder_id                                     │
│      AND expires_at > NOW()                                          │
│                                                                      │
│      if ROW_COUNT == 0:                                              │
│          # Lease expired or stolen                                   │
│          log.warning("Lease lost for entity")                        │
│          raise LeaseLostError                                        │
│                                                                      │
│  Edge cases:                                                         │
│  - Refresh fails due to DB connection loss:                         │
│    Continue execution (best-effort). Grace period allows recovery.   │
│  - Refresh fails repeatedly:                                         │
│    After GRACE_S without refresh, lease may expire.                  │
│    Writer should complete as quickly as possible.                    │
│  - DB restored after outage:                                         │
│    Attempt emergency refresh. If expired, abort with LeaseLostError. │
└─────────────────────────────────────────────────────────────────────┘
```

### Lease Expiry

| Scenario | Expiry Behaviour | Recovery |
|---|---|---|
| Write completed normally | Lease released explicitly | N/A |
| Process crash | Lease auto-expires after `LEASE_DURATION_S` | Next writer acquires after expiry |
| Network partition | Lease refresh fails | After GRACE_S + LEASE_DURATION_S, another writer can acquire |
| Long-running write | Lease refreshed periodically | No expiry while refresh loop is healthy |
| Stale lease (writer alive but refresh thread dead) | Lease expires | Next writer detects expired lease, acquires, writes new version |

### Crash Recovery

```
┌─────────────────────────────────────────────────────────────────────┐
│                     CRASH RECOVERY FLOW                               │
│                                                                      │
│  Writer A crashes mid-write:                                         │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ 1. Writer A acquires lease (expires at T+120s)                  ││
│  │ 2. Writer A begins entity write                                  ││
│  │ 3. Writer A CRASHES (process kill, unhandled exception)         ││
│  │ 4. Lease is NOT released (no cleanup code executes)             ││
│  │ 5. After 120s: lease expires in DB                             ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                      │
│  Writer B detects and recovers:                                      │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ 1. Writer B calls acquire_lease(entity_version_key)             ││
│  │ 2. DB returns 'conflict' (lease held by Writer A, expires at T+120)│
│  │ 3. Writer B checks expires_at < NOW():                          ││
│  │    - If YES: lease expired → Writer B acquires lease            ││
│  │    - If NO: Writer B retries with backoff                       ││
│  │ 4. Writer B acquires lease                                      ││
│  │ 5. Writer B reads entity version store to check state:          ││
│  │    - If entity write was completed: skip (idempotency check)    ││
│  │    - If entity write was partial: redo the write                ││
│  │ 6. Writer B completes write and releases lease                  ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                      │
│  Crash detection thresholds:                                         │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ ENTITY_LEASE_DEFAULT_S      = 120  │ Normal expiry              ││
│  │ ENTITY_LEASE_GRACE_PERIOD_S = 30   │ Additional grace before    ││
│  │                                    │ another writer can acquire ││
│  │ Total crash-to-recoverable = 150s  │ ~2.5 minutes max delay     ││
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

---

## Pessimistic Lock Escalation

### Overview

Pessimistic locking is the **secondary concurrency mechanism**, activated only when optimistic locking contention exceeds defined thresholds. This prevents hot entities from degrading system throughput through excessive retries.

### Escalation Thresholds

```
┌─────────────────────────────────────────────────────────────────────┐
│                  ESCALATION THRESHOLDS                               │
│                                                                      │
│  ┌─────────────────────────────────────────────┐                    │
│  │ ESCALATION_RETRY_THRESHOLD        = 3       │ After 3 consecutive│
│  │                                            │ CAS failures,       │
│  │                                            │ escalate to pessim. │
│  │                                            │                     │
│  │ ESCALATION_CONFLICT_RATE         = 0.30    │ If >30% of writes   │
│  │                                            │ in rolling 5-min    │
│  │                                            │ window conflict,    │
│  │                                            │ escalate            │
│  │                                            │                     │
│  │ ESCALATION_ROLLING_WINDOW_MINUTES = 5      │ Rolling window for  │
│  │                                            │ conflict rate calc  │
│  │                                            │                     │
│  │ ESCALATION_COOLDOWN_MINUTES       = 15     │ After 15 min with-  │
│  │                                            │ out conflicts,      │
│  │                                            │ de-escalate to      │
│  │                                            │ optimistic          │
│  └─────────────────────────────────────────────┘                    │
│                                                                      │
│  Escalation state machine:                                           │
│                                                                      │
│  ┌──────────┐    retry > threshold    ┌──────────────┐              │
│  │ OPTIMISTIC│ ──────────────────────▶│  PESSIMISTIC │              │
│  │ (default) │                        │  (escalated) │              │
│  └──────────┘ ◀──────────────────────┘              │              │
│                 cooldown elapsed       └──────────────┘              │
│                 AND no recent conflicts                              │
└─────────────────────────────────────────────────────────────────────┘
```

### Lock Ordering

When pessimistic locking is active, entities are locked in a **global order** to prevent deadlocks:

```python
# Global lock order (must be respected by all writers)
ENTITY_LOCK_ORDER = [
    "supplier",          # Level 1
    "customer",          # Level 2
    "document_reference", # Level 3
    "document_financials", # Level 4
    "line_item",         # Level 5
]
```

**Lock acquisition rules:**

| Rule | Description |
|---|---|
| **Strict ordering** | Locks must be acquired in `ENTITY_LOCK_ORDER` sequence |
| **All-or-nothing** | All required locks must be acquired before any write begins |
| **No lock downgrade** | If a higher-level lock is held, you cannot acquire a lower-level lock (prevents cycle) |
| **Timeout** | Each lock acquisition has a `LOCK_ACQUIRE_TIMEOUT_S` (default: 30s) |
| **Fail fast** | If a lock cannot be acquired within timeout, release all acquired locks and retry |

### Deadlock Avoidance

```
┌─────────────────────────────────────────────────────────────────────┐
│                     DEADLOCK AVOIDANCE                                │
│                                                                      │
│  Strategy 1: Global Lock Order                                       │
│  ────────────────────────────────────────────────────────────────    │
│  All writers acquire locks in ENTITY_LOCK_ORDER. No writer ever     │
│  acquires a lower-level lock after holding a higher-level lock.     │
│                                                                      │
│  Strategy 2: Lock Acquisition Timeout                               │
│  ────────────────────────────────────────────────────────────────    │
│  Each lock acquisition has a timeout (default 30s). If timeout      │
│  expires, the acquisition fails. The writer releases all held       │
│  locks and retries from the beginning.                              │
│                                                                      │
│  Strategy 3: Deadlock Detection (PostgreSQL-specific)                │
│  ────────────────────────────────────────────────────────────────    │
│  If using PostgreSQL, enable deadlock detection:                     │
│  SET deadlock_timeout = '5s';                                        │
│  If a deadlock is detected, PostgreSQL kills one transaction.       │
│  The killed writer releases all locks and retries.                  │
│                                                                      │
│  Strategy 4: Retry with Backoff                                      │
│  ────────────────────────────────────────────────────────────────    │
│  If lock acquisition fails (timeout or deadlock victim):            │
│  1. Release all acquired locks                                      │
│  2. Wait random delay (jittered)                                     │
│  3. Retry from first lock in order                                   │
│  4. Max retries: 3                                                   │
│                                                                      │
│  Bad patterns (FORBIDDEN):                                          │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ ✗ Acquiring locks in different order across writers          │   │
│  │ ✗ Holding locks while waiting for user input                 │   │
│  │ ✗ Nested lock acquisition without timeout                    │   │
│  │ ✗ Attempting to acquire a lock already held by self          │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### Release Semantics

```python
@dataclass(frozen=True, slots=True)
class PessimisticLockReleasePolicy:
    """Defines how and when pessimistic locks are released."""

    release_on_completion: bool = True         # Release all locks when write completes
    release_on_failure: bool = True            # Release all locks on write failure
    release_on_timeout: bool = True            # Release if lock acquisition times out
    max_hold_duration_s: int = 60              # Maximum time any lock can be held
    force_release_on_expiry: bool = True       # Force-release if hold duration exceeded

    # Lock hierarchy management
    release_in_reverse_order: bool = True      # Release lower-order locks first
    release_all_on_any_failure: bool = True    # If one lock release fails, release all
```

**Release sequence:**

```
1. Write completes (or fails)
2. Release locks in REVERSE order (line_item → financials → reference → customer → supplier)
3. Each lock release logs: released_at, duration_held_s, refresh_count
4. If any release fails (DB error), retry with backoff
5. If release fails after max retries, force-release with admin note
6. Update entity lease: set state = 'released', released_at = NOW()
```

---

## Entity Version Store

### Schema Design

```sql
-- ============================================================
-- Entity Version Store — append-only version history
-- ============================================================

CREATE TABLE entity_versions (
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

-- Current version index (fast lookup for active entities)
CREATE INDEX idx_entity_versions_active
    ON entity_versions (entity_version_key, version DESC)
    WHERE state = 'active';

-- Entity type query index
CREATE INDEX idx_entity_versions_type
    ON entity_versions (entity_type, state);

-- Source document provenance index
CREATE INDEX idx_entity_versions_source
    ON entity_versions (source_document_id);

-- ============================================================
-- Entity Leases — execution lease management
-- ============================================================

CREATE TABLE entity_leases (
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

-- Expired lease index (for crash recovery scanning)
CREATE INDEX idx_entity_leases_expired
    ON entity_leases (expires_at)
    WHERE expires_at < CURRENT_TIMESTAMP;

-- ============================================================
-- Entity Idempotency — duplicate write detection
-- ============================================================

CREATE TABLE entity_idempotency (
    idempotency_key      TEXT PRIMARY KEY,      -- SHA-256 of key components
    entity_version_key   TEXT NOT NULL,          -- Entity being written
    version              INTEGER NOT NULL,       -- Version that was written
    pipeline_run_id      TEXT NOT NULL,          -- Run that performed the write
    status               TEXT NOT NULL DEFAULT 'in_progress',  -- "in_progress" | "completed" | "failed" | "expired"
    created_at           TEXT NOT NULL,          -- ISO-8601 timestamp
    completed_at         TEXT                    -- ISO-8601 timestamp (nullable)
);

-- Cleanup index
CREATE INDEX idx_entity_idempotency_cleanup
    ON entity_idempotency (status, created_at);

-- ============================================================
-- Entity Conflict Log — audit trail for concurrency conflicts
-- ============================================================

CREATE TABLE entity_conflict_log (
    conflict_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_version_key   TEXT NOT NULL,
    conflict_type        TEXT NOT NULL,          -- "version_mismatch" | "checksum_mismatch" | "lease_busy" | "deadlock"
    attempted_version    INTEGER NOT NULL,
    current_version      INTEGER NOT NULL,
    attempted_by         TEXT NOT NULL,          -- pipeline_run_id
    current_holder       TEXT NOT NULL DEFAULT '',  -- pipeline_run_id holding the current version
    resolution           TEXT NOT NULL DEFAULT '',  -- "retry" | "escalate" | "abort"
    created_at           TEXT NOT NULL
);

-- Conflict query index
CREATE INDEX idx_entity_conflict_log_entity
    ON entity_conflict_log (entity_version_key, created_at DESC);
```

### Storage Model

```
┌─────────────────────────────────────────────────────────────────────┐
│                   ENTITY VERSION STORE — STORAGE MODEL                │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  TABLE: entity_versions                                       │   │
│  │                                                               │   │
│  │  Append-only. Each write inserts a new row.                  │   │
│  │  No rows are ever UPDATED (state transitions use REPLACE).   │   │
│  │  The "active" row for each entity is the highest version      │   │
│  │  with state='active'.                                         │   │
│  │                                                               │   │
│  │  Example for supplier "acme-corp":                            │   │
│  │  ┌──────────────────────────┬─────────┬───────┬────────┐     │   │
│  │  │ entity_version_key       │ version │ state │ data   │     │   │
│  │  ├──────────────────────────┼─────────┼───────┼────────┤     │   │
│  │  │ supplier:canonical:acme  │    1    │ super │ {...}  │     │   │
│  │  │ supplier:canonical:acme  │    2    │ super │ {...}  │     │   │
│  │  │ supplier:canonical:acme  │    3    │ active│ {...}  │     │   │
│  │  │ supplier:canonical:acme  │    4    │ arch  │ {...}  │     │   │
│  │  └──────────────────────────┴─────────┴───────┴────────┘     │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  PHYSICAL STORAGE                                             │   │
│  │                                                               │   │
│  │  Primary: SQLite (embedded, single-host)                      │   │
│  │    Path: data/entity_version_store.db                         │   │
│  │    WAL mode for concurrent readers: PRAGMA journal_mode=WAL;  │   │
│  │                                                               │   │
│  │  Upgradable to: PostgreSQL (multi-host)                       │   │
│  │    For v2 when distributed locking is needed                   │   │
│  │                                                               │   │
│  │  Index growth:                                                │   │
│  │    - ~1KB per entity version row                              │   │
│  │    - ~100k versions/day @ 1000 entities/day × 100 versions   │   │
│  │    - ~100MB/year (negligible for SQLite)                      │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### Migration Strategy

```
┌─────────────────────────────────────────────────────────────────────┐
│                      MIGRATION STRATEGY                               │
│                                                                      │
│  Phase 1: Schema Creation                                           │
│  ────────────────────────────────────────────────────────────────    │
│  File: scripts/migrations/008_create_entity_version_store.sql       │
│                                                                      │
│  Contents: CREATE TABLE statements for:                              │
│  - entity_versions                                                   │
│  - entity_leases                                                     │
│  - entity_idempotency                                                │
│  - entity_conflict_log                                               │
│                                                                      │
│  Execution:                                                          │
│  - Run as part of v0.5 entity hardening deployment                  │
│  - Idempotent (CREATE IF NOT EXISTS)                                 │
│  - No data migration needed (new tables, no existing data)           │
│                                                                      │
│  Phase 2: Data Backfill (if previous EntitySet data exists)         │
│  ────────────────────────────────────────────────────────────────    │
│  Script: scripts/migrations/009_backfill_entity_versions.py          │
│                                                                      │
│  For each EntitySet in history:                                      │
│  1. Read entity data from workflow debug artifacts or history store │
│  2. Assign version = 1                                               │
│  3. Compute checksum                                                 │
│  4. Insert into entity_versions                                     │
│  5. Record idempotency key                                           │
│                                                                      │
│  Phase 3: Verification                                               │
│  ────────────────────────────────────────────────────────────────    │
│  - Verify entity count matches source data                           │
│  - Verify checksums are consistent                                   │
│  - Verify version sequences start at 1                               │
│  - Verify all active entities have state='active'                   │
└─────────────────────────────────────────────────────────────────────┘
```

### Backward Compatibility

| Concern | Strategy |
|---|---|
| **Existing code reads EntitySet** | Unchanged — EntitySet contracts retain their existing fields. `entity_version` is optional and defaults to 0 for code that doesn't specify it. |
| **Existing workflow stages** | Unchanged — stages that produce EntitySet are unaware of version store. Versioning is applied at the persistence layer. |
| **Existing EntityRuntimeOrchestrator** | Backward-compatible — the orchestrator continues to return `EntitySet` objects. Version store writes are opt-in through a configuration flag. |
| **Existing Matching Runtime** | Unchanged — the matching runtime reads `EntitySet` objects. If version store is enabled, it reads versioned data transparently. |
| **Existing tests** | All existing tests pass without modification. New tests cover version store behaviour. |
| **Rollback** | If version store is rolled back, entity reads fall through to the previous data source (history store or debug artifacts). No data loss occurs because the version store is append-only. |

**Configuration flag for backward compatibility:**

```python
ENTITY_VERSION_STORE_ENABLED: bool = False   # Default: disabled
# When enabled:
#   All entity writes go through version store + optimistic locking
#   All entity reads come from version store (active version)
# When disabled:
#   No behavioural change from v1 entity runtime
```

---

## Runtime Impact

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ENTITY RUNTIME — CONCURRENCY HARDENED                      │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                     EntityConcurrencyGuard                             │   │
│  │  ┌─────────────────────┐  ┌─────────────────┐  ┌───────────────────┐ │   │
│  │  │ OptimisticLockManager│  │ PessimisticLock  │  │ LeaseManager      │ │   │
│  │  │ - CAS write          │  │ Escalation       │  │ - acquire         │ │   │
│  │  │ - conflict detection │  │ - lock ordering  │  │ - refresh         │ │   │
│  │  │ - retry policy       │  │ - deadlock avoid │  │ - release         │ │   │
│  │  └─────────┬───────────┘  └────────┬────────┘  └────────┬──────────┘ │   │
│  │            │                       │                     │            │   │
│  │            └───────────────────────┴─────────────────────┘            │   │
│  │                                    │                                    │   │
│  │  ┌─────────────────────────────────▼────────────────────────────────┐ │   │
│  │  │                     EntityVersionStore                             │ │   │
│  │  │  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐   │ │   │
│  │  │  │ VersionedRead  │  │ VersionedWrite │  │ IdempotencyCheck │   │ │   │
│  │  │  └────────────────┘  └────────────────┘  └──────────────────┘   │ │   │
│  │  └──────────────────────────────────────────────────────────────────┘ │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                     EntityRuntimeOrchestrator                          │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │   │
│  │  │ EntityExtrac-│  │EntityValidator│  │TextNormalizer│  │Confidence│ │   │
│  │  │ tionEngine   │  │              │  │              │  │ Scorer   │ │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────┘ │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                        Entity Version Store DB                         │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │   │
│  │  │entity_vers-  │  │entity_leases │  │entity_idempo-│  │entity_con-│ │   │
│  │  │ ions         │  │              │  │ tency        │  │ flict_log │ │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────┘ │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Execution Flow Changes

| Aspect | Before (v1) | After (v1 Hardened) |
|---|---|---|
| **Entity write** | In-memory only, no persistence | Persisted to version store with version assignment |
| **Concurrency model** | None — unbounded parallel writes | Optimistic locking with CAS semantics |
| **Crash resilience** | None — partial writes invisible | Leases auto-expire; writer can retry after expiry |
| **Duplicate detection** | None | Idempotency keys prevent duplicate writes |
| **Conflict resolution** | Last-writer-wins (silent data loss) | CAS conflict detection with retry |
| **Hot entity handling** | None — all entities treated equally | Escalation to pessimistic locking after threshold |
| **Latency per write** | ~0ms (in-memory) | +2-5ms (version check + CAS write + lease refresh) |
| **Storage per entity** | 0 bytes | ~1KB per version (increases linearly with versions) |

### New Components

| Component | File | Responsibility |
|---|---|---|
| `EntityConcurrencyGuard` | `src/entity_runtime/concurrency/guard.py` | Orchestrates optimistic/pessimistic locking, leases, idempotency |
| `OptimisticLockManager` | `src/entity_runtime/concurrency/optimistic.py` | CAS write, conflict detection, retry logic |
| `PessimisticLockManager` | `src/entity_runtime/concurrency/pessimistic.py` | Escalation, lock ordering, deadlock avoidance |
| `LeaseManager` | `src/entity_runtime/concurrency/leases.py` | Lease acquisition, refresh, expiry, crash recovery |
| `EntityVersionStore` | `src/entity_runtime/store/version_store.py` | Versioned read/write, schema management |
| `EntityIdempotencyRegistry` | `src/entity_runtime/store/idempotency.py` | Idempotency key generation, check, record, cleanup |
| `EntityConcurrencyConfig` | `src/entity_runtime/concurrency/config.py` | All configurable parameters (thresholds, timeouts) |
| `EntityConcurrencyError` | `src/entity_runtime/concurrency/errors.py` | Exception types (Conflict, Lease, Deadlock, Corruption) |

### File Layout

```
src/entity_runtime/
├── __init__.py                          # Updated public API
├── engine.py                            # Unchanged (extraction logic)
├── contracts/                           # (existing contracts unchanged)
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
    └── workflow_adapter.py              # Adapter that hooks EntityConcurrencyGuard into workflow stages
```

### Configuration

```python
# src/entity_runtime/concurrency/config.py

# === Entity Version Store ===
ENTITY_VERSION_STORE_ENABLED: bool = False      # Opt-in for v1
ENTITY_VERSION_STORE_DB_PATH: str = "data/entity_version_store.db"
ENTITY_VERSION_STORE_DB_TYPE: str = "sqlite"    # "sqlite" | "postgresql"

# === Optimistic Locking ===
OPTIMISTIC_RETRY_MAX_ATTEMPTS: int = 3
OPTIMISTIC_RETRY_BASE_DELAY_MS: int = 50
OPTIMISTIC_RETRY_MAX_DELAY_MS: int = 500
OPTIMISTIC_RETRY_BACKOFF_MULTIPLIER: float = 2.0

# === Pessimistic Lock Escalation ===
ESCALATION_RETRY_THRESHOLD: int = 3
ESCALATION_CONFLICT_RATE: float = 0.30
ESCALATION_ROLLING_WINDOW_MINUTES: int = 5
ESCALATION_COOLDOWN_MINUTES: int = 15
PESSIMISTIC_LOCK_ACQUIRE_TIMEOUT_S: int = 30
PESSIMISTIC_LOCK_MAX_HOLD_S: int = 60

# === Execution Leases ===
ENTITY_LEASE_DEFAULT_S: int = 120
ENTITY_LEASE_REFRESH_INTERVAL_S: int = 20
ENTITY_LEASE_REFRESH_GRACE_S: int = 10
ENTITY_LEASE_RETRY_MAX_ATTEMPTS: int = 3
ENTITY_LEASE_RETRY_BASE_DELAY_MS: int = 100

# === Idempotency ===
ENTITY_IDEMPOTENCY_RETENTION_DAYS: int = 7
ENTITY_IDEMPOTENCY_IN_PROGRESS_TTL_MINUTES: int = 60
ENTITY_IDEMPOTENCY_CLEANUP_BATCH_SIZE: int = 1000
ENTITY_IDEMPOTENCY_CLEANUP_INTERVAL_MINUTES: int = 60
```

---

## Contract Impact

### New Public Contracts

| Contract | Type | Scope |
|---|---|---|
| `EntityConcurrencyGuard` | Class | `src/entity_runtime/concurrency/guard.py` |
| `OptimisticLockManager` | Class | `src/entity_runtime/concurrency/optimistic.py` |
| `PessimisticLockManager` | Class | `src/entity_runtime/concurrency/pessimistic.py` |
| `LeaseManager` | Class | `src/entity_runtime/concurrency/leases.py` |
| `EntityVersionStore` | Class | `src/entity_runtime/store/version_store.py` |
| `EntityIdempotencyRegistry` | Class | `src/entity_runtime/store/idempotency.py` |
| `EntityVersionRecord` | Dataclass (frozen) | `src/entity_runtime/store/version_store.py` |
| `IdempotencyResult` | Dataclass (frozen) | `src/entity_runtime/store/idempotency.py` |
| `ConflictInfo` | Dataclass (frozen) | `src/entity_runtime/concurrency/optimistic.py` |
| `LeaseAcquisition` | Dataclass (frozen) | `src/entity_runtime/concurrency/leases.py` |
| `EscalationPolicy` | Dataclass (frozen) | `src/entity_runtime/concurrency/pessimistic.py` |
| `PessimisticLockReleasePolicy` | Dataclass (frozen) | `src/entity_runtime/concurrency/pessimistic.py` |
| `EntityConcurrencyConfig` | Dataclass (frozen) | `src/entity_runtime/concurrency/config.py` |

### New Exception Types

| Exception | Superclass | Trigger |
|---|---|---|
| `EntityConflictError` | `RuntimeError` | CAS version mismatch |
| `EntityCorruptionError` | `RuntimeError` | Checksum mismatch on read/write |
| `EntityLeaseError` | `RuntimeError` | Lease acquisition/refresh failure |
| `EntityLeaseLostError` | `EntityLeaseError` | Lease expired during write |
| `EntityLockTimeoutError` | `RuntimeError` | Pessimistic lock acquisition timeout |
| `EntityDeadlockError` | `RuntimeError` | Deadlock detected |
| `EntityDuplicateWriteError` | `RuntimeError` | Idempotency key collision |
| `EntityStoreUnavailableError` | `RuntimeError` | Version store connection failure |

### Modified Contracts

| Contract | Change |
|---|---|
| `EntitySet` | Add optional `entity_version: int = 0` field (default 0 = no versioning) |
| `Supplier` | Add optional `entity_version: int = 0` field |
| `Customer` | Add optional `entity_version: int = 0` field |
| `LineItem` | Add optional `entity_version: int = 0` field |
| `DocumentReference` | Add optional `entity_version: int = 0` field |
| `DocumentFinancials` | Add optional `entity_version: int = 0` field |

### Unchanged Contracts

| Contract | Reason |
|---|---|
| `SourceLineage` | No versioning needed — provenance metadata |
| `ExtractionMetadata` | No versioning needed — extraction context |
| All Workflow Runtime contracts | Entity concurrency is orthogonal to workflow execution |
| All Document Runtime contracts | Entity concurrency is downstream of document processing |

---

## Storage Impact

### New Database Tables

| Table | Size Estimate | Growth Rate | Retention |
|---|---|---|---|
| `entity_versions` | ~1KB/row | ~100K rows/year @ 1000 entities/day | Indefinite (append-only) |
| `entity_leases` | ~256 bytes/row | 1 row/active entity write | TTL-based (lease duration) |
| `entity_idempotency` | ~128 bytes/row | ~100K rows/year | 7-day TTL |
| `entity_conflict_log` | ~512 bytes/row | ~10K rows/year | Indefinite (audit) |

### Storage Projections

| Metric | Projection |
|---|---|
| Annual entity versions | ~100,000 (1000 entities/day × 100 avg versions/entity) |
| Annual idempotency records | ~100,000 (same as versions) |
| Annual conflict log entries | ~10,000 (10% of versions trigger conflict) |
| Total annual storage | ~150MB (negligible for SQLite or PostgreSQL) |
| Peak lease rows | ~100 (concurrent entity writes) |

### Migration Script

```sql
-- scripts/migrations/008_create_entity_version_store.sql
-- Migration: Create Entity Version Store for v1 concurrency hardening

BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS entity_versions (
    entity_version_key   TEXT NOT NULL,
    entity_type          TEXT NOT NULL,
    entity_id            TEXT NOT NULL,
    version              INTEGER NOT NULL,
    state                TEXT NOT NULL DEFAULT 'active',
    data                 TEXT NOT NULL,
    checksum             TEXT NOT NULL,
    previous_checksum    TEXT NOT NULL DEFAULT '',
    created_at           TEXT NOT NULL,
    created_by           TEXT NOT NULL,
    source_document_id   TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (entity_version_key, version)
);

CREATE INDEX IF NOT EXISTS idx_entity_versions_active
    ON entity_versions (entity_version_key, version DESC)
    WHERE state = 'active';

CREATE INDEX IF NOT EXISTS idx_entity_versions_type
    ON entity_versions (entity_type, state);

CREATE INDEX IF NOT EXISTS idx_entity_versions_source
    ON entity_versions (source_document_id);

CREATE TABLE IF NOT EXISTS entity_leases (
    entity_version_key   TEXT PRIMARY KEY,
    holder_id            TEXT NOT NULL,
    acquired_at          TEXT NOT NULL,
    expires_at           TEXT NOT NULL,
    lease_duration_s     INTEGER NOT NULL DEFAULT 120,
    last_refreshed_at    TEXT NOT NULL,
    refresh_count        INTEGER NOT NULL DEFAULT 0,
    hostname             TEXT NOT NULL DEFAULT '',
    pid                  INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_entity_leases_expired
    ON entity_leases (expires_at)
    WHERE expires_at < CURRENT_TIMESTAMP;

CREATE TABLE IF NOT EXISTS entity_idempotency (
    idempotency_key      TEXT PRIMARY KEY,
    entity_version_key   TEXT NOT NULL,
    version              INTEGER NOT NULL,
    pipeline_run_id      TEXT NOT NULL,
    status               TEXT NOT NULL DEFAULT 'in_progress',
    created_at           TEXT NOT NULL,
    completed_at         TEXT
);

CREATE INDEX IF NOT EXISTS idx_entity_idempotency_cleanup
    ON entity_idempotency (status, created_at);

CREATE TABLE IF NOT EXISTS entity_conflict_log (
    conflict_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_version_key   TEXT NOT NULL,
    conflict_type        TEXT NOT NULL,
    attempted_version    INTEGER NOT NULL,
    current_version      INTEGER NOT NULL,
    attempted_by         TEXT NOT NULL,
    current_holder       TEXT NOT NULL DEFAULT '',
    resolution           TEXT NOT NULL DEFAULT '',
    created_at           TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_entity_conflict_log_entity
    ON entity_conflict_log (entity_version_key, created_at DESC);

COMMIT;
```

---

## Testing Strategy

### Unit Tests

| Test Category | Test Cases | Priority |
|---|---|---|
| **Optimistic Lock Manager** | — CAS write succeeds when version matches<br>— CAS write fails when version mismatches<br>— Retry with exponential backoff succeeds on 2nd attempt<br>— Retry exhausts after max attempts<br>— Checksum mismatch detection<br>— Conflict info correctly populated | P0 |
| **Pessimistic Lock Manager** | — Acquire lock in correct order<br>— Acquire lock timeout<br>— Deadlock detection and retry<br>— Escalation triggers after retry threshold<br>— De-escalation after cooldown<br>— Lock release in reverse order | P0 |
| **Lease Manager** | — Acquire lease when free<br>— Acquire lease fails when held<br>— Lease refresh before expiry<br>— Lease refresh after expiry fails<br>— Lease auto-expiry after TTL<br>— Crash recovery after lease expiry<br>— Lease holder identification | P0 |
| **Entity Version Store** | — Write version 1 (new entity)<br>— Write version 2 (CAS success)<br>— Write version 2 (CAS conflict)<br>— Read active version<br>— Read specific version<br>— Read version history<br>— State transition (active→superseded→archived) | P0 |
| **Idempotency Registry** | — First write accepted<br>— Duplicate write rejected<br>— Key collision atomicity (concurrent)<br>— In-progress TTL expiry<br>— Retention-based cleanup<br>— Cleanup batch limits respected | P0 |
| **Conflict Log** | — Conflict recorded on CAS failure<br>— Conflict resolution tracked<br>— Query by entity key<br>— Query by time range | P1 |
| **Configuration** | — Default values valid<br>— Override from environment<br>— Type validation | P1 |

### Integration Tests

| Scenario | Setup | Expected Behaviour |
|---|---|---|
| **Two writers, same entity, optimistic** | Two threads attempt CAS write on same entity | One succeeds (v1), second retries and succeeds (v2) |
| **Two writers, same entity, pessimistic** | Two threads attempt pessimistic write on same entity | First acquires lock, second waits or times out |
| **Crash recovery with lease** | Acquire lease, simulate crash, wait for expiry, third party writes | Third party acquires lease after expiry, writes new version |
| **Escalation cascade** | Configure low retry threshold, trigger repeated conflicts | Writer escalates to pessimistic after threshold |
| **Idempotency prevents duplicate** | Write entity with idempotency key, repeat with same key | Second write returns duplicate result (no DB mutation) |
| **Concurrent different entities** | Two threads write different entities simultaneously | Both succeed (no cross-entity interference) |
| **Backward compatibility disabled** | `ENTITY_VERSION_STORE_ENABLED=False` | All existing entity runtime behaviour unchanged |
| **Store unavailable graceful degradation** | Version store DB goes down during write | Fallback to in-memory write with warning (no crash) |
| **Conflict log audit trail** | Repeated CAS conflicts on same entity | All conflicts recorded with timestamps and resolution |

### Performance Benchmarks

| Test | Measurement | Target |
|---|---|---|
| Optimistic CAS write latency (p50/p99) | Time for CAS write with no conflict | <5ms p50, <20ms p99 |
| Optimistic CAS write with retry (p50/p99) | Time including retry delay | <200ms p50, <500ms p99 |
| Pessimistic lock acquisition latency | Time to acquire lock (no contention) | <10ms p50, <50ms p99 |
| Lease refresh overhead | CPU time per refresh | <1ms |
| Concurrent entity throughput | Writes/second with N simultaneous writers | >=100 writes/sec |
| Crash recovery time | Time from lease expiry to new write | <= lease_duration_s + grace_period_s |
| Idempotency check overhead | Time per check-and-record | <2ms |

### Boundary Verification

No changes to import boundaries are expected — the concurrency module lives within `src/entity_runtime/concurrency/` and `src/entity_runtime/store/`, both within the Entity Runtime boundary. Existing boundary verification tests (`scripts/verify_boundaries.py`) must continue to pass.

---

## Documentation Requirements

### New Documents

| Document | Location | Content |
|---|---|---|
| Architecture Plan | `docs/architecture/ENTITY_RUNTIME_CONCURRENCY_HARDENING_V1_PLAN.md` | This document |
| Implementation Summary | `docs/architecture/ENTITY_RUNTIME_CONCURRENCY_HARDENING_V1_SUMMARY.md` | What was built, design decisions, configuration |
| Handoff Document | `docs/architecture/ENTITY_RUNTIME_CONCURRENCY_HARDENING_V1_HANDOFF.md` | Runbook, rollback steps, monitoring |
| ADR | `docs/adr/ADR-009-entity-concurrency-hardening.md` | Decision record for v1 entity concurrency strategy |

### Updated Documents

| Document | Update |
|---|---|
| `docs/ROADMAP.md` | Mark "Entity Runtime Concurrency Hardening" as completed |
| `TECHNICAL_DEBT.md` | Add "Entity Runtime Concurrency Controls" section (close after implementation) |
| `docs/architecture/ENTITY_RUNTIME_V1_ARCHITECTURE.md` | Add concurrency hardening section |

### Code Documentation

- Docstrings on all new public classes (`EntityConcurrencyGuard`, `OptimisticLockManager`, `PessimisticLockManager`, `LeaseManager`, `EntityVersionStore`, `EntityIdempotencyRegistry`)
- README section in `src/entity_runtime/concurrency/__init__.py` explaining the concurrency strategy
- Example usage in module docstring for `guard.py`

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **CAS contention reduces write throughput** | Medium | Medium | Retry with exponential backoff; escalate to pessimistic for hot entities. Monitor conflict rates. |
| **Lease TTL misconfiguration** | Medium | High | Start with generous default (120s). Make configurable. Add monitoring for lease expiry rates. |
| **Deadlock under pessimistic locking** | Low | High | Global lock ordering prevents cycles. Deadlock detection and forced retry as safety net. |
| **Version store becomes bottleneck** | Low | Medium | SQLite WAL mode for concurrent readers. Indexes tuned for active-version queries. |
| **Idempotency key collision** | Low | High | Key includes pipeline_run_id — collisions impossible for different runs of same entity. |
| **Data corruption from partial write + crash** | Low | High | Atomic CAS + lease + checksum triple protection. Corruption is detected before commit. |
| **Migration from non-versioned to versioned entities** | Low | Medium | Backfill script for existing entities. Feature flag for gradual rollout. |
| **Rollback complexity (4 new tables)** | Low | Low | Drop tables and disable feature flag. No data loss (append-only). |
| **False deadlock detection slowing throughput** | Low | Medium | Deadlock_timeout configurable. Monitor false positive rate. |
| **Entity version history unbounded growth** | Low | Low | Archive policy (TTL-based) and compaction. Configurable retention window. |

---

## Effort Estimate

### Component Breakdown

| Component | Effort (person-days) | Dependencies |
|---|---|---|
| `EntityVersionStore` — versioned read/write, schema | 2 | Database access, migration script |
| `OptimisticLockManager` — CAS write, conflict detection, retry | 2 | EntityVersionStore, configuration |
| `PessimisticLockManager` — escalation, lock ordering, deadlock avoidance | 2 | OptimisticLockManager, configuration |
| `LeaseManager` — acquire, refresh, expiry, crash recovery | 1.5 | Database, configuration |
| `EntityIdempotencyRegistry` — key generation, dedup, cleanup | 1 | Database, configuration |
| `EntityConcurrencyGuard` — orchestrator, integration with existing runtime | 1.5 | All above components |
| `EntityConcurrencyConfig` — configuration constants | 0.5 | None |
| `EntityConcurrencyError` — exception types | 0.5 | None |
| Conflict log (audit trail) | 0.5 | EntityVersionStore |
| Entity contract modifications (version fields) | 0.5 | EntitySet and sub-contracts |
| Database schema migration (4 tables) | 0.5 | Migration script |
| Data backfill script (optional) | 0.5 | Existing entity data |
| Unit tests | 3 | All components |
| Integration tests | 2 | All components, full entity runtime |
| Performance benchmarks | 0.5 | Integration test environment |
| Documentation (summary, handoff, ADR, ROADMAP, TECHDEBT) | 1.5 | Per governance rules |
| **Total** | **~17 person-days (~3.5 person-weeks)** | |

### Optimization Options

| Option | Effort | Scope |
|---|---|---|
| **Minimum Viable (1.5 weeks)** | ~7 person-days | OptimisticLockManager + EntityVersionStore + basic leases. Defer pessimistic escalation, idempotency cleanup, conflict log, backfill. |
| **Standard v1 (2.5 weeks)** | ~12 person-days | Above + PessimisticLockManager + EntityIdempotencyRegistry + unit tests. Defer conflict log, backfill, performance benchmarks. |
| **Full v1 (3.5 weeks)** | ~17 person-days | Complete implementation as described above. |

**Recommendation**: **Standard v1** (2.5 weeks) for balancing production safety with delivery speed. Add pessimistic escalation for hot entities and idempotency for duplicate prevention. Defer conflict log audit trail and data backfill to v1.1 if needed.

---

## Release Plan

### Phase 1: Foundation (Week 1)

1. Create database migration script (4 tables)
2. Implement `EntityConcurrencyConfig` with all constants
3. Implement `EntityConcurrencyError` exception types
4. Implement `EntityVersionStore` — versioned CRUD operations
5. Implement `EntityIdempotencyRegistry` — key generation, check-and-record
6. Add entity_version field to entity contracts (EntitySet + sub-contracts)
7. Write unit tests for VersionStore and IdempotencyRegistry

### Phase 2: Locking Infrastructure (Week 1-2)

1. Implement `OptimisticLockManager` — CAS write, conflict detection, retry policy
2. Implement `PessimisticLockManager` — escalation thresholds, lock ordering, deadlock avoidance
3. Implement `LeaseManager` — acquire, refresh, expiry, crash recovery
4. Implement `EntityConcurrencyGuard` — orchestrator that coordinates all components
5. Write unit tests for all locking managers
6. Integration test: concurrent writes with CAS

### Phase 3: Integration & Verification (Week 2-3)

1. Wire `EntityConcurrencyGuard` into `EntityRuntimeOrchestrator`
2. Add configuration flag `ENTITY_VERSION_STORE_ENABLED` for backward compatibility
3. Implement graceful degradation (fallback to in-memory when store unavailable)
4. Integration tests:
   - Idempotency prevents duplicate writes
   - Crash recovery via lease expiry
   - Escalation to pessimistic locking
   - Backward compatibility mode
5. Performance benchmarks for CAS write latency, lease overhead
6. Verify boundary compliance (`scripts/verify_boundaries.py`)

### Phase 4: Documentation & Deployment (Week 3)

1. Create architecture summary document
2. Create handoff document
3. Create ADR-009
4. Update ROADMAP.md, TECHNICAL_DEBT.md, ENTITY_RUNTIME_V1_ARCHITECTURE.md
5. Configuration review and default tuning
6. Deploy to staging environment with `ENTITY_VERSION_STORE_ENABLED=False` (no change)
7. Enable version store in staging, run full test suite
8. Enable version store in production with monitoring

### Rollback Procedure

```bash
# Immediate rollback (disable version store):
# 1. Set ENTITY_VERSION_STORE_ENABLED=False in environment configuration
#    This reverts to the pre-versioning behaviour (in-memory entities)
# 2. Restart entity runtime processes
# 3. Verify all entity extraction and matching works without errors

# Permanent rollback (remove version store):
# 1. Set ENTITY_VERSION_STORE_ENABLED=False
# 2. Revert entity contract changes (remove entity_version fields)
# 3. Remove src/entity_runtime/concurrency/ and src/entity_runtime/store/ packages
# 4. Drop entity_versions, entity_leases, entity_idempotency, entity_conflict_log tables
# 5. Restore original entity contracts
```

### Migration for Existing Entities

- Version store is **opt-in** — existing entity extraction continues to work without versioning
- Migration plan:
  1. Deploy concurrency hardening code with `ENTITY_VERSION_STORE_ENABLED=False`
  2. Run backfill script (`scripts/migrations/009_backfill_entity_versions.py`) to populate version store from existing data
  3. Enable version store for new entity extractions (v1 entities, no CAS conflicts yet)
  4. Enable CAS writes for existing entities after backfill is complete
  5. Monitor conflict rates after enabling CAS writes

---

## Definition of Done

### Implementation

- [ ] `EntityConcurrencyConfig` defined with all configurable parameters
- [ ] `EntityConcurrencyError` exception hierarchy defined (6+ types)
- [ ] `EntityVersionStore` implemented — versioned read, write, history, state transitions
- [ ] `OptimisticLockManager` implemented — CAS write with conflict detection
- [ ] `OptimisticLockManager` implemented — retry with exponential backoff
- [ ] `PessimisticLockManager` implemented — escalation based on retry threshold
- [ ] `PessimisticLockManager` implemented — lock ordering and deadlock avoidance
- [ ] `PessimisticLockManager` implemented — lock release semantics
- [ ] `LeaseManager` implemented — acquire, refresh, expiry
- [ ] `LeaseManager` implemented — crash recovery (stale lease acquisition)
- [ ] `EntityIdempotencyRegistry` implemented — key generation, check-and-record
- [ ] `EntityIdempotencyRegistry` implemented — retention policy and cleanup
- [ ] `EntityConcurrencyGuard` implemented — orchestrator for all components
- [ ] `entity_version` field added to `EntitySet`, `Supplier`, `Customer`, `LineItem`, `DocumentReference`, `DocumentFinancials`
- [ ] Database migration script for 4 new tables created
- [ ] Graceful degradation when version store is unavailable
- [ ] `ENTITY_VERSION_STORE_ENABLED` configuration flag with backward compatibility

### Testing

- [ ] Unit tests for `EntityVersionStore` (CRUD, versioning, states)
- [ ] Unit tests for `OptimisticLockManager` (CAS success, failure, retry)
- [ ] Unit tests for `PessimisticLockManager` (escalation, ordering, deadlock)
- [ ] Unit tests for `LeaseManager` (acquire, refresh, expiry, recovery)
- [ ] Unit tests for `EntityIdempotencyRegistry` (dedup, TTL, cleanup)
- [ ] Integration tests: two writers CAS on same entity
- [ ] Integration tests: crash recovery via lease expiry
- [ ] Integration tests: escalation to pessimistic locking
- [ ] Integration tests: idempotency prevents duplicate writes
- [ ] Integration tests: backward compatibility mode
- [ ] Performance benchmarks for CAS write latency
- [ ] `pytest tests/ -v` passes
- [ ] `python scripts/verify_boundaries.py` passes (no regressions)

### Documentation

- [ ] `docs/architecture/ENTITY_RUNTIME_CONCURRENCY_HARDENING_V1_SUMMARY.md` created
- [ ] `docs/architecture/ENTITY_RUNTIME_CONCURRENCY_HARDENING_V1_HANDOFF.md` created
- [ ] `docs/adr/ADR-009-entity-concurrency-hardening.md` created
- [ ] `docs/ROADMAP.md` updated — mark Entity Runtime Concurrency Hardening as completed
- [ ] `TECHNICAL_DEBT.md` updated — entity concurrency item added/closed
- [ ] `docs/architecture/ENTITY_RUNTIME_V1_ARCHITECTURE.md` updated — add concurrency section
- [ ] Docstrings on all new public classes and methods

### Release

- [ ] Git commit completed
- [ ] Git push completed
- [ ] Milestone tag `v0.5-entity-concurrency-hardening` created (or merged into v0.5-runtime-hardening)
- [ ] Future agent can continue from repository documentation alone

---

## Appendices

### A. Glossary

| Term | Definition |
|---|---|
| **Optimistic Locking** | Concurrency control that assumes conflicts are rare; checks version at write time rather than locking resources preemptively |
| **Compare-and-Swap (CAS)** | Atomic operation that updates a value only if it matches an expected version |
| **Pessimistic Locking** | Concurrency control that locks resources before modification to prevent concurrent access |
| **Execution Lease** | Time-bound lock that auto-expires after a configurable duration; provides crash recovery |
| **Idempotency Key** | A deterministic key that uniquely identifies a write operation; prevents duplicate writes |
| **Entity Version Key** | Composite key identifying a specific entity across its version history |
| **Entity Conflict** | When two writers attempt concurrent CAS writes and one detects a version mismatch |
| **Hot Entity** | An entity that experiences high write contention (multiple concurrent writers) |
| **Lock Escalation** | Automatic transition from optimistic to pessimistic locking for hot entities |
| **Lock Ordering** | A globally-defined sequence for acquiring locks that prevents deadlocks |
| **Deadlock** | A state where two writers each hold a lock the other needs, causing indefinite blocking |
| **Version Store** | An append-only data store for entity version history |

### B. Related Documents

| Document | Location | Relationship |
|---|---|---|
| PLATFORM_ARCHITECTURE_REVIEW.md | `docs/architecture/` | Identifies entity runtime concurrency hardening as priority |
| ENTITY_RUNTIME_V1_ARCHITECTURE.md | `docs/architecture/` | Parent architecture document for entity runtime |
| WORKFLOW_RUNTIME_LOCKING_V1_PLAN.md | `docs/architecture/` | Reference pattern — this plan adapts the locking architecture |
| ADR-008-workflow-runtime-locking.md | `docs/adr/` | Decision record for workflow locking (reference pattern) |
| ADR-009-entity-concurrency-hardening.md (new) | `docs/adr/` | Decision record for entity concurrency hardening |
| NEXT_MILESTONE_RECOMMENDATION.md | `docs/architecture/` | Recommends entity concurrency hardening as next objective |
| ROADMAP.md | `docs/` | Lists entity concurrency hardening as next milestone objective |
| TECHNICAL_DEBT.md | `./` | Tracks concurrency hardening as known debt |

### C. Future Considerations (v2+)

| Feature | Trigger | Strategy |
|---|---|---|
| **Event Sourcing** | Architecture Review recommendation | Replace version store with event-sourced entity history |
| **Distributed entity store (PostgreSQL)** | Multi-host deployment | Migrate from SQLite to PostgreSQL for cross-host coordination |
| **Dynamic lease TTL** | Variable-duration entity operations | Estimate TTL from historical operation times |
| **Dead-letter queue for entity writes** | Persistent write failures | Queue failed entity writes for retry with escalation |
| **Cross-entity atomic transactions** | Multi-entity writes must be atomic | Transactional scope across multiple entity version keys |
| **Entity snapshotting** | Version history becomes too deep | Periodic snapshots of active entity state for fast reads |
| **Read replicas** | Read throughput demand exceeds primary | Version store read replicas for query isolation |

---

## End of Plan