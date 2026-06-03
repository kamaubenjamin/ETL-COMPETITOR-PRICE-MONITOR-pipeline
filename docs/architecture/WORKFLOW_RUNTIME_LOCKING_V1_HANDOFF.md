# Workflow Runtime Locking v1 — Handoff Document

**Date**: 2026-06-03  
**Author**: Platform Architecture Review  
**Status**: Phase 1 Complete  
**Milestone**: v0.5-workflow-runtime-locking  
**Phase**: 1 — Foundation

---

## Phase 1 Runbook

### What Was Built

Phase 1 establishes the **structural foundation** for the locking subsystem. It produces only abstractions — no executable locking logic. The following components are defined:

1. **Package structure** — `src/workflow_runtime/locking/` with sub-packages
2. **Data models** — `LockAcquisition` and `IdempotencyRecord` frozen dataclasses
3. **Abstract interfaces** — `LockProvider`, `WorkflowExecutionGuard`, `WorkflowIdempotencyRegistry`
4. **Custom exceptions** — `LockAcquisitionError`, `IdempotencyRejectionError`, `LockProviderError`, `LeaseRefreshError`
5. **Database schema** — `workflow_locks` and `workflow_idempotency` SQL migration scripts
6. **Configuration defaults** — 13 constants in `src/workflow_runtime/locking/config.py`

### How to Verify Phase 1

```bash
# 1. Verify imports work
python -c "from src.workflow_runtime.locking import LockAcquisition, LockProvider, WorkflowExecutionGuard, WorkflowIdempotencyRegistry, LockAcquisitionError, IdempotencyRejectionError, LockProviderError, LeaseRefreshError, LockProviderRegistry; print('OK')"

# 2. Run Phase 1 unit tests
python -m pytest tests/locking/ -v --tb=short

# 3. Verify migration scripts
python -c "
import sqlite3
conn = sqlite3.connect(':memory:')
conn.executescript(open('scripts/migrations/006_create_workflow_locks_table.sql').read())
conn.executescript(open('scripts/migrations/007_create_workflow_idempotency_table.sql').read())
print('Migrations OK')
"
```

### What NOT To Do

- **Do not** start Phase 2 (concrete provider implementations) — the abstractions need to be stable first
- **Do not** modify the ABC method signatures once Phase 2 begins — they are the contract all providers implement
- **Do not** change `frozen=True` or `slots=True` on the models — downstream code depends on immutability
- **Do not** import from `src/workflow_runtime/locking/providers/` yet — the implementations are stubs

---

## Migration Guide

### Database Migration

Run the migrations before any locking logic is deployed:

```bash
# Order: 006 first, then 007
python -c "
import sqlite3
conn = sqlite3.connect('your_history_store.db')
conn.executescript(open('scripts/migrations/006_create_workflow_locks_table.sql').read())
conn.executescript(open('scripts/migrations/007_create_workflow_idempotency_table.sql').read())
conn.commit()
print('Migrations applied')
"
```

**Rollback**:
```sql
DROP TABLE IF EXISTS workflow_locks;
DROP TABLE IF EXISTS workflow_idempotency;
```

### Code Migration

No code migration is needed for Phase 1 — the locking module is purely additive. Existing code continues to work unchanged. The locking is opt-in: `WorkflowRunner.__init__()` will accept optional guard and registry parameters with `None` defaults (implemented in Phase 3).

---

## Configuration

All configuration defaults are in `src/workflow_runtime/locking/config.py`.

For production deployment, override via environment or application config:

| Environment Variable | Config Constant | Default | Recommended |
|---|---|---|---|
| `LOCK_PROVIDER` | `LOCK_PROVIDER` | `"database"` | `"database"` (production) |
| `LOCK_DEFAULT_LEASE_S` | `LOCK_DEFAULT_LEASE_S` | `300` | `300` (5 min) |
| `LOCK_REFRESH_INTERVAL_S` | `LOCK_REFRESH_INTERVAL_S` | `30` | `30` |
| `LOCK_MAX_RETRIES` | `LOCK_MAX_RETRIES` | `3` | `3` |
| `LOCK_DB_TABLE` | `LOCK_DB_TABLE` | `"workflow_locks"` | Customize if table name conflicts |
| `IDEMPOTENCY_ENABLED` | `IDEMPOTENCY_ENABLED` | `True` | `True` |
| `IDEMPOTENCY_KEY_TTL_DAYS` | `IDEMPOTENCY_KEY_TTL_DAYS` | `7` | `7` |

---

## Monitoring (Post-Phase 2+)

Once locking is active, monitor these metrics:

| Metric | Source | Warning | Critical |
|--------|--------|---------|----------|
| `LockAcquisitionError` rate | Logs | >1% of runs | >5% of runs |
| Lease refresh failures | Logs | Any occurrence | >10/min |
| Provider fallback events | Logs | Any occurrence | >5/min |
| Lock acquisition latency | Telemetry | >50ms p99 | >100ms p99 |
| `workflow_locks` row count | DB query | N/A (one row per workflow_id) | Check for unbounded growth |

---

## Troubleshooting

### "ImportError: cannot import name 'LockAcquisition'"
Ensure `src/workflow_runtime/locking/__init__.py` exists and has the correct imports. Run the import verification command above.

### Migration fails with "table already exists"
The migrations use `IF NOT EXISTS` — they are idempotent. If the tables already exist, the migration is a no-op.

### Tests fail on Windows
The `slots=True` tests may raise `TypeError` instead of `AttributeError` on some Python versions. The test suite handles both (`pytest.raises((AttributeError, TypeError))`).

---

## Known Issues

- None. Phase 1 produces abstractions only — no executable logic.

---

## Future Work (Phases 2-5)

| Phase | Description | Dependencies |
|-------|-------------|--------------|
| **Phase 2** | Implement MemoryLockProvider, FileLockProvider, DBLockProvider, ExecutionGuard, IdempotencyRegistry | Phase 1 (complete) |
| **Phase 3** | Update ExecutionContext/WorkflowResult contracts, integrate guard into WorkflowRunner.run() | Phase 2 |
| **Phase 4** | Unit/integration/performance tests, boundary verification | Phase 3 |
| **Phase 5** | Handoff, ADR, ROADMAP/TECHDEBT updates, CHANGELOG, git commit/tag | Phase 4 |

---

## Next Agent Instructions

When starting Phase 2:

1. Read `docs/architecture/WORKFLOW_RUNTIME_LOCKING_V1_PLAN.md` (architecture decisions)
2. Read `docs/architecture/WORKFLOW_RUNTIME_LOCKING_V1_IMPLEMENTATION_PLAN.md` (detailed implementation specs)
3. Read `docs/architecture/WORKFLOW_RUNTIME_LOCKING_V1_SUMMARY.md` (what's already built)
4. Implement providers in this order: MemoryLockProvider → FileLockProvider → DBLockProvider → LockProviderRegistry → IdempotencyRegistry → ExecutionGuard → LeaseRefresh → StaleCleanup
5. Run `python -m pytest tests/locking/ -v` after each provider implementation
6. Update `tests/locking/conftest.py` with provider-specific fixtures as needed