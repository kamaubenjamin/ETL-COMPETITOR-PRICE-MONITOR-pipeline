# Test Plan — Runtime Boundary Verification
Date: 2026-06-01

## Purpose
Define the test scenarios, harness architecture, mock specifications, and execution strategy for verifying runtime boundary compliance. This plan implements the verification strategy defined in `RUNTIME_BOUNDARY_MAP.md`.

---

## Test Architecture

### Directory Structure
```
tests/boundaries/
├── __init__.py
├── conftest.py                  # Shared fixtures and exemptions
├── test_import_isolation.py     # Tier 1: Static import analysis
├── test_contract_adherence.py   # Tier 2: Contract schema validation
├── test_interactions.py         # Tier 3: Cross-boundary interaction tests
├── exemptions.json              # Registered ADR exemption IDs
└── README.md                    # Test harness usage
```

### Harness Design
- **Framework**: pytest
- **Runner**: pytest with optional markers for tier selection (`pytest -m tier1`, `pytest -m tier2`, `pytest -m tier3`)
- **Exemption mechanism**: pytest markers (`@pytest.mark.exempted(reason="ADR-009-EX-001")`) or JSON-based exemption lookup in `exemptions.json`
- **Mock dependencies**: Minimal mock objects for runtime modules that are not under test (see Mock Specifications below)

---

## Tier 1 — Import Isolation Tests

### Purpose
Verify that no runtime imports a forbidden runtime module.

### Test File
`tests/boundaries/test_import_isolation.py`

### Test Scenarios

| ID | Rule | Source Package | Forbidden Target | Expected |
|---|---|---|---|---|
| TI-01 | R01 | `src/document_engine/` | `src/entity_runtime/` | No imports |
| TI-02 | R01 | `src/document_engine/` | `src/matching_runtime/` | No imports |
| TI-03 | R01 | `src/document_engine/` | `src/review_runtime/` | No imports |
| TI-04 | R02 | `src/entity_runtime/` | `src/matching_runtime/` | No imports |
| TI-05 | R02 | `src/entity_runtime/` | `src/review_runtime/` | No imports |
| TI-06 | R03 | `src/matching_runtime/` | `src/extract/` | No imports |
| TI-07 | R03 | `src/matching_runtime/` | `src/document_engine/` | No imports |
| TI-08 | R04 | `src/review_runtime/` | `src/extract/` | No imports |
| TI-09 | R04 | `src/review_runtime/` | `src/document_engine/` | No imports |
| TI-10 | R04 | `src/review_runtime/` | `src/entity_runtime/` | No imports |
| TI-11 | R05 | `src/api/` | `src/entity_runtime/` | No imports |
| TI-12 | R05 | `src/api/` | `src/matching_runtime/` | No imports |
| TI-13 | R05 | `src/api/` | `src/review_runtime/` | No imports |
| TI-14 | R05 | `src/api/` | `src/document_engine/` | No imports |
| TI-15 | R12 | `src/utils.py` | Any `src/*_runtime/` | No imports |
| TI-16 | R12 | `src/config.py` | Any `src/*_runtime/` | No imports |

### Implementation Approach
1. Walk the AST of every Python file in the source package.
2. Extract all `import X` and `from X import Y` statements.
3. For each source package, check whether any forbidden target package appears in the imports.
4. If an import is found, check the exemption register. If no exemption exists, the test fails.
5. Exempted imports are logged as warnings and do not fail the test.

### Expected Runtime
< 5 seconds.

---

## Tier 2 — Contract Adherence Smoke Tests

### Purpose
Verify that artifacts emitted at each runtime boundary conform to their registered Contract Registry schema.

### Test File
`tests/boundaries/test_contract_adherence.py`

### Test Scenarios

| ID | Rule | Producer Runtime | Consumer Runtime | Artifact | Schema Draft |
|---|---|---|---|---|---|
| CA-01 | R06 | Document | Entity | `extracted_entity` | `entity/extracted_entity.schema.json` |
| CA-02 | R06 | Document | Workflow | `document_extraction_event` | `workflow/workflow_stage_result.schema.json` |
| CA-03 | R06 | Entity | Matching | `entity_set` | `entity/entity_set.schema.json` |
| CA-04 | R06 | Matching | Review | `match_proposals` | `matching/match_result.schema.json` |
| CA-05 | R06 | Review | Entity | `correction_event` | `review/review_event.schema.json` |
| CA-06 | R06 | Workflow | API | `workflow_result` | `workflow/workflow_result.schema.json` |

### Implementation Approach
1. For each boundary, use a fixture that produces a sample artifact (from `docs/contracts/examples/`).
2. Validate the artifact against the registered schema using `jsonschema.validate()`.
3. Assert that validation passes with no errors.
4. If an artifact type does not yet have a registered schema, the test is skipped with a note to register the schema first.

### Expected Runtime
< 30 seconds.

---

## Tier 3 — Cross-Boundary Interaction Tests

### Purpose
Verify that allowed interactions succeed and disallowed interactions are blocked.

### Test File
`tests/boundaries/test_interactions.py`

### Test Scenarios

#### Allowed Interactions

| ID | Rule | Actor | Action | Target | Expected Outcome |
|---|---|---|---|---|---|
| IB-01 | R08 | Matching Runtime | Query canonical index (read) | Entity Runtime | Return data, no mutation |
| IB-02 | R09 | Monitoring Runtime | Collect metrics (read) | All runtimes | Return telemetry data only |
| IB-03 | R10 | API Runtime | Submit workflow request | Workflow Runtime | Workflow created, response received |
| IB-04 | R10 | Workflow Runtime | Trigger document extraction | Document Runtime | Extraction starts, status returned |

#### Disallowed Interactions

| ID | Rule | Actor | Action | Target | Expected Outcome |
|---|---|---|---|---|---|
| IB-05 | R08 | Matching Runtime | Write to canonical index | Entity Runtime | Write rejected or no-op |
| IB-06 | R10 | API Runtime | Call Entity Runtime directly | Entity Runtime | Call blocked or error |
| IB-07 | R10 | Document Runtime | Call Matching Runtime directly | Matching Runtime | Call blocked or error |
| IB-08 | R09 | Monitoring Runtime | Start/stop workflow | Workflow Runtime | Control action rejected |
| IB-09 | R11 | Any runtime | Synchronous cross-boundary call without ADR exemption | Any runtime | Test fails if call exists without exemption |
| IB-10 | R07 | Review Runtime | Mutate or delete prior review decision | Review Store | No-op or error |

### Implementation Approach
1. **Allowed interactions**: Exercise the interaction through the documented API or interface. Assert that the expected operation completes successfully and that no side effects violate the boundary (e.g., read-only queries do not create or modify records).
2. **Disallowed interactions**: Exercise the interaction through the same interface. Assert that the operation is rejected, returns an error, or is a no-op.
3. For interaction IB-09, use static analysis to enumerate all synchronous cross-boundary call sites and cross-reference against the exemption register.
4. For interaction IB-10, attempt to modify or delete a prior review decision and assert that the operation fails or is rejected.

### Mock Specifications
For hermetic testing, each runtime under test should have its dependencies mocked:

| Runtime Under Test | Mock Dependencies |
|---|---|
| Document Runtime | Mock storage backend, mock file system |
| Entity Runtime | Mock Document Runtime output, mock storage |
| Matching Runtime | Mock Entity Runtime canonical index, mock storage |
| Review Runtime | Mock Matching Runtime proposals, mock notification |
| Workflow Runtime | Mock all downstream runtimes (Document, Entity, Matching, Review) |
| API Runtime | Mock Workflow Runtime |
| Monitoring Runtime | No mocks (observer only; test with captured telemetry) |

### Expected Runtime
1–5 minutes with mocks.

---

## Exemption Test Skip Mechanism

### exemption.json Format
```json
{
  "exemptions": [
    {
      "adr": "ADR-009-EX-001",
      "rule": "R03",
      "scope": "src/matching_runtime/utils.py",
      "reason": "Legacy import of extract helper for memory-only data conversion",
      "target_remediation": "v0.6",
      "created": "2026-06-01",
      "expires": "2026-09-01"
    }
  ]
}
```

### Behaviour
- If a test fails and the failing module/call site is listed in `exemptions.json`, the test is skipped with a warning.
- If an exemption has expired, the test fails with an error message indicating the exemption expiry date.
- Exemptions are loaded at test suite startup from `exemptions.json`.

---

## CI Integration

### Workflow Stages
The boundary verification tests shall run as a separate CI job within the existing `contract-validation` workflow:

```yaml
boundary-verification:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: "3.11"
    - run: python -m pip install pytest jsonschema
    - name: Tier 1 — Import Isolation
      run: python -m pytest tests/boundaries/test_import_isolation.py -m tier1 -v
    - name: Tier 2 — Contract Adherence
      run: python -m pytest tests/boundaries/test_contract_adherence.py -m tier2 -v
    - name: Tier 3 — Interaction Boundaries
      if: ${{ contains(github.event.pull_request.labels.*.name, 'runtime-change') }}
      run: python -m pytest tests/boundaries/test_interactions.py -m tier3 -v
```

### Gating Rules
| Branch / Event | Tier 1 | Tier 2 | Tier 3 |
|---|---|---|---|
| PR (no runtime changes) | Required | Required | Optional |
| PR (runtime changes) | Required | Required | Required |
| push to `main` | Required | Required | Required |
| push to `release/*` | Required | Required | Required |
| Nightly CI | Required | Required | Required |

### Failure Handling
- Tier 1 or Tier 2 failure: Block the PR. Release tag is blocked.
- Tier 3 failure (PR with no runtime changes): Warning only.
- Tier 3 failure (PR with runtime changes or release branch): Block the PR. Release tag is blocked.
- Exempted failures: Warning logged. Not blocked.

---

## Test Data Requirements

### Contract Registry Schemas
All schemas referenced in Tier 2 test scenarios must exist in `docs/contracts/` with examples in `docs/contracts/examples/`. If a schema does not yet exist, the corresponding test is skipped until the schema is registered.

### Mock Artifact Fixtures
- Each test scenario in Tier 2 requires a valid example artifact in `docs/contracts/examples/`.
- If an example does not exist, the test is skipped with a message identifying the missing fixture.

---

## Success Criteria

| Criterion | Target |
|---|---|
| Tier 1 test count | ≥ 16 scenarios |
| Tier 2 test count | ≥ 6 scenarios (or all registered schemas) |
| Tier 3 test count | ≥ 10 scenarios |
| CI execution time (Tier 1 + Tier 2) | < 1 minute |
| CI execution time (Tier 3) | < 5 minutes |
| Exemption bypass accuracy | 100% of registered exemptions are correctly skipped |
| False positive rate | < 5% of failing tests attributable to test harness issues |

---

## Appendix A — Boundary Verification Test Checklist

Use this checklist when adding a new runtime or modifying an existing runtime boundary.

- [ ] New runtime has an entry in the Runtime Dependency Matrix (`RUNTIME_BOUNDARY_MAP.md`)
- [ ] Import isolation tests added for all forbidden dependency pairs (TI-*)
- [ ] Contract adherence test added for each emitted artifact type (CA-*)
- [ ] Allowed interaction test added for each documented interaction (IB-*)
- [ ] Disallowed interaction test added for each documented forbidden interaction (IB-*)
- [ ] Example artifact added to `docs/contracts/examples/`
- [ ] Schema registered in Contract Registry if new artifact type is introduced
- [ ] Exemption filed via ADR if compliance cannot be achieved immediately

End of document.