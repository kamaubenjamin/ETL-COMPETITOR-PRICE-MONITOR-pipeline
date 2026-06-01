Technical debt and missing test fixtures

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
