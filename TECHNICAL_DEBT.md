Technical debt and missing test fixtures

## Extraction & Transformation Capability Hardening v1

### Current Status

**Closed and tagged as `v0.6-extraction-transformation-capability-hardening`.**

Delivered under `src/transforms/` and Workflow Runtime:

- Versioned transform, mapping, validation, sorting, and aggregation contracts
- Deterministic `transform`, `validate_data`, `sort`, and `aggregate` workflow stages
- Strict configuration validation, input immutability, bounded privacy-safe validation results, and deterministic integration coverage
- Legacy transformation compatibility and stage catalog/validator alignment

### Remaining Verification Debt

- The boundary verifier still skips `src/alerts/alert_engine.py` and `src/entity_runtime/engine.py` because of existing U+FEFF characters; these warnings predate v0.6 and should be corrected separately.

### Deferred Capability Debt

- Nested field mapping and persistent/external mapping registries
- Streaming or distributed transformation execution
- Pivoting, window functions, and time-series aggregation
- Full MDM/golden-record lifecycle and survivorship
- OCR and LLM-based extraction remain explicitly outside v0.6

### Reference

- `docs/architecture/EXTRACTION_TRANSFORMATION_CAPABILITY_HARDENING_V1_SUMMARY.md`
- `docs/architecture/EXTRACTION_TRANSFORMATION_CAPABILITY_HARDENING_V1_HANDOFF.md`
- `docs/releases/v0.6-extraction-transformation-capability-hardening.md`

---

## Review / Correction Runtime v1

### Current Status

**Closed and tagged as `v0.7-review-correction-runtime`.**

Resolved in v0.7:

- Canonical eight-state lifecycle and five reviewer decisions
- Field-addressed, lineage-aware controlled corrections
- Ordered append-only audit records for canonical services
- Idempotent creation, optimistic case versions, and declarative dry-run reprocess plans
- Bounded allowlisted metadata and privacy-safe errors/audit summaries

Remaining debt:

- Durable database persistence, atomic multi-process transactions, migrations, retention, and audit signing
- Authenticated/authorized reviewer identity and protected correction-value access
- Workflow review-stage adapter, reprocess acknowledgement, and execution
- Shared neutral stage catalog; the dry-run planner currently mirrors a local safe allowlist
- API, UI, Streamlit, FlowSync, notifications, and observability instrumentation
- Legacy prototype modules remain alongside canonical v1 services and need a future deprecation plan

Closure is documented in:

- `docs/architecture/REVIEW_CORRECTION_RUNTIME_V1_PLAN.md`
- `docs/architecture/REVIEW_CORRECTION_RUNTIME_V1_IMPLEMENTATION_PLAN.md`
- `docs/architecture/REVIEW_CORRECTION_RUNTIME_V1_SUMMARY.md`
- `docs/architecture/REVIEW_CORRECTION_RUNTIME_V1_HANDOFF.md`
- `docs/adr/ADR-013-review-correction-runtime.md`
- `docs/releases/v0.7-review-correction-runtime.md`

---

## Document Intelligence Operator Console v1

### Current Status

**Closed and tagged as `v0.8-document-intelligence-operator-console`; live backend integration remains deferred.**

Remaining debt:

- Replace `LocalOperatorConsoleProvider` fixtures with bounded read-only application-service adapters behind the same display contract
- Replace constructed Review Runtime samples with an authorized read-only repository/service adapter
- Add authenticated operator identity and role-based authorization
- Add protected access rules for sensitive document and correction values
- Implement production upload through a backend-owned ingestion boundary
- Add command submission through runtime services with idempotency and optimistic versions
- Add accessibility, responsive-layout, deployment, and browser-level regression verification
- Validate status/priority labels with operators before treating the display vocabulary as a stable external contract
- Keep the legacy competitor-price `dashboard.py` separate until an explicit retirement milestone

References:

- `docs/architecture/DOCUMENT_INTELLIGENCE_OPERATOR_CONSOLE_V1_PLAN.md`
- `docs/architecture/DOCUMENT_INTELLIGENCE_OPERATOR_CONSOLE_V1_SUMMARY.md`
- `docs/architecture/DOCUMENT_INTELLIGENCE_OPERATOR_CONSOLE_V1_HANDOFF.md`
- `docs/releases/v0.8-document-intelligence-operator-console.md`

---

## Document Intelligence API Foundation v1

### Current Status

**v0.9 architecture and phased implementation planning complete; implementation not started.**

Planning resolves the API ownership direction but does not yet resolve:

- R05-compliant live query aggregation through a public Workflow Runtime facade
- Authentication, authorization, tenant isolation, rate limiting, and public deployment
- Durable runtime providers, caching, cursor pagination, or service-level objectives
- Mutation contracts for upload, corrections, decisions, reprocessing, and workflow execution
- Retirement of four legacy `src/api/app.py` boundary exemptions
- Production CORS, API gateway, TLS, observability, and operational support

References:

- `docs/architecture/DOCUMENT_INTELLIGENCE_API_FOUNDATION_V1_PLAN.md`
- `docs/architecture/DOCUMENT_INTELLIGENCE_API_FOUNDATION_V1_IMPLEMENTATION_PLAN.md`
- `docs/adr/ADR-014-document-intelligence-api-foundation.md`

---

- Missing internal test data files required by `test_pipeline.py`:
  - `data/internal/supplier_prices.csv` (expected by `supplier_price_list` source)
  - `data/internal/erp_export.xlsx` (expected by `erp_inventory` source)
  - Recommendation: add small fixture CSV/XLSX files under `data/internal/` with representative rows (columns: `product_name`, `price`, `source`, `supplier_price` where applicable) or mock the file loader in tests.

- Connectors returning empty DataFrames during test runs:
  - `jumia_electronics` connector returned an empty DataFrame in CI environment.
  - Recommendation: implement connector mocks for tests or include deterministic local HTML fixtures/playwright profiles under `playwright_profiles/` to ensure reproducible extraction.

- Test expectations referencing `supplier_price` column:
  - Some pipeline/test code expects `supplier_price` column present after combining internal/external sources. If canonical pipeline does not produce `supplier_price`, update tests or mapping to use `price` with a `source` qualifier.

- Action items:
  1. Add minimal internal fixtures to `data/internal/` for CI.
  2. Add connector mocks or deterministic playwright fixtures under `playwright_profiles/`.
  3. Update `tests/test_pipeline.py` to mock external dependencies rather than relying on local network or missing files.

These items should be prioritized to make pipeline tests hermetic in CI environments.

---

## Workflow Runtime Locking v1 (CLOSED)

### Current Status

**Resolved in v0.5-workflow-runtime-locking milestone.**

The Workflow Runtime now has a complete locking subsystem that prevents duplicate concurrent execution of the same workflow. The solution includes three lock providers (database-backed with execution leases, file-based advisory locking, and in-memory for development), a pluggable provider registry with fallback chain, idempotency key deduplication for scheduled runs, and lease-based crash recovery.

### Resolution

- **Locking Infrastructure**: `src/workflow_runtime/locking/` package with 13 source files
- **Database Schema**: `scripts/migrations/006_create_workflow_locks_table.sql` and `007_create_workflow_idempotency_table.sql`
- **Configuration**: 13 constants in `src/workflow_runtime/locking/config.py` with documented defaults
- **Test Coverage**: 158 locking-specific tests (all passing) + full regression suite (363/364 passing)
- **Architecture Decision**: ADR-008-workflow-runtime-locking.md
- **Implementation Plan**: `docs/architecture/WORKFLOW_RUNTIME_LOCKING_V1_PLAN.md`

### Effort

~13.5 person-days across 5 phases: Foundation → Infrastructure → Integration → Verification → Documentation & Release

### Reference

- `docs/architecture/WORKFLOW_RUNTIME_LOCKING_V1_SUMMARY.md`
- `docs/adr/ADR-008-workflow-runtime-locking.md`

---

## Contract Registry v1 Follow-Up

### Current Status

Contract Registry v1 is formally closed with repository-owned JSON Schema Draft 07 contracts, example fixtures, local validation tests, and `scripts/validate_contracts.py`. CI Contract Validation v1 now runs the contract pytest suite and standalone validator in GitHub Actions with a minimal dependency install.

### Remaining Debt

- Schema compatibility checks against a released baseline are not yet implemented.
- ADR enforcement for breaking schema changes is not yet implemented.
- Schema version bump validation is not yet implemented.
- Runtime boundary validation is not yet implemented.
- Runtime producers and consumers do not yet perform mandatory contract validation.

### Recommended Solution

1. Confirm GitHub Actions runs the new contract-validation workflow successfully.
2. Add compatibility diffing for schema changes in a later hardening phase.
3. Require ADR validation for MAJOR schema version changes in a later hardening phase.
4. Implement Runtime Boundary Verification as the next v0.5 hardening objective.

### Priority

Medium (remaining v0.5 Runtime Hardening follow-up).

---

## Entity Runtime Concurrency Hardening (CLOSED)

### Current Status

**Resolved in the v0.5-entity-runtime-concurrency-hardening milestone.**

The Entity Runtime now supports versioned persistence, optimistic locking, pessimistic lock escalation, execution leases, and idempotency protection for entity writes. The implementation includes runtime integration, graceful degradation, and regression coverage for unit, integration, crash-recovery, and verification scenarios.

### Resolution

- Versioned entity persistence and history via `src/entity_runtime/store/`
- Concurrency orchestration via `src/entity_runtime/concurrency/guard.py`
- Runtime integration via `src/entity_runtime/orchestration/orchestrator.py`
- Regression and verification coverage under `tests/entity_runtime/`
- Architecture and handoff documentation under `docs/architecture/` and `docs/adr/`

### Reference

- `docs/architecture/ENTITY_RUNTIME_CONCURRENCY_HARDENING_V1_SUMMARY.md`
- `docs/architecture/ENTITY_RUNTIME_CONCURRENCY_HARDENING_V1_HANDOFF.md`
- `docs/adr/ADR-010-entity-runtime-concurrency-hardening.md`

---

## Scheduler State Separation

### Current Issue

`src/schedules.json` mixes two concerns:
1. **Configuration** (version-controlled): workflow schedule definitions (`frequency`, `time_of_day`, `enabled`)
2. **Runtime State** (ephemeral): execution history (`last_run`, `next_run`, `run_count`)

This causes:
- Frequent, spurious diffs when tests or manual runs update runtime state
- Accidental commits of environment-specific execution history
- Difficulty distinguishing intentional configuration changes from automated state updates

### Root Cause

Scheduler loads and mutates all fields in a single JSON file during runtime, so all updates get reflected in source control when the file is committed.

### Recommended Solution (v0.5+)

Separate configuration from state:

#### Option A: Two Files (Recommended for simplicity)
- **`src/schedules.config.json`** (version-controlled): Configuration only
  ```json
  {
    "electronics_monitoring": {
      "workflow_id": "...",
      "frequency": "daily",
      "time_of_day": "08:00",
      "enabled": true
    }
  }
  ```
- **`src/schedules.state.json`** (auto-generated, add to `.gitignore`): Runtime state only
  ```json
  {
    "electronics_monitoring": {
      "last_run": "2026-05-27T08:00:23.039256",
      "next_run": "2026-05-28T08:00:00",
      "run_count": 5
    }
  }
  ```

#### Option B: Database-Backed State
- Keep `src/schedules.config.json` (version-controlled, config only)
- Store execution history in SQLite (`src/execution_history.db` or shared scheduler DB)
- Add `.db` files to `.gitignore`

#### Option C: Schema Separation (Single File)
```json
{
  "configurations": { /* version-controlled */ },
  "runtime_state": { /* ephemeral, handle separately */ }
}
```

### Implementation Steps

1. Create `src/schedules.config.json` with configuration-only content
2. Update `src/scheduler.py` to load config from `.config.json` and state from `.state.json` (or DB)
3. Add to `.gitignore`:
   ```
   src/schedules.state.json
   src/execution_history.db
   ```
4. Update CI/CD to initialize fresh state files on each run
5. Update developer onboarding docs

### Effort

Low — ~4 hours refactor; minimal impact on scheduler logic

### Priority

Medium (v0.5 or later); does not block v0.4 release
