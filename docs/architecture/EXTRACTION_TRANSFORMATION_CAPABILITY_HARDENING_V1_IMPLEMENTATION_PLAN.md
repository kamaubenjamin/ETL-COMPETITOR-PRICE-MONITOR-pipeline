# Extraction & Transformation Capability Hardening v1 Implementation Plan

**Milestone:** v0.6  
**Status:** Phases 1-5 implemented; final tag pending full-suite environment verification
**Architecture:** `docs/architecture/EXTRACTION_TRANSFORMATION_CAPABILITY_HARDENING_V1_PLAN.md`  
**Delivery model:** One phase per Codex session  

## 1. Milestone Overview

v0.6 converts the repository's partial deterministic extraction and transformation capabilities into reusable Workflow Runtime behavior. The milestone makes `TransformStage` execute real transformations, introduces compact JSON-compatible mapping and validation contracts, adds reusable data-validation, sort, and aggregation stages, and removes drift between workflow stage validation and registration.

Implementation remains in-process and deterministic. `src/transforms` owns generic tabular behavior; Workflow Runtime owns artifact adaptation and stage orchestration. Document, Entity, and Matching Runtime contracts and ownership remain unchanged.

The milestone excludes OCR, LLM extraction, UI, API, full MDM/golden-record lifecycle, arbitrary executable rules, network services, and new external dependencies.

## 2. Phase 1: Contracts, Stage Catalog, and ADR

### Objectives

- Record the v0.6 architecture and boundary decision in ADR-012.
- Define immutable or validation-protected v1 contracts for transformation plans, operations, field mappings, regex definitions, validation plans/results, sort plans, and aggregation plans.
- Define stable, path-aware configuration errors that serialize to JSON-compatible dictionaries.
- Introduce a dependency-light authoritative workflow stage catalog.
- Make workflow validation accept exactly the public stage types in the catalog, including existing `matching`.
- Do not implement transformation, validation, sorting, or aggregation execution.

### Expected Files

Create:

- `docs/adr/ADR-012-extraction-transformation-capability-hardening.md`
- `src/transforms/contracts.py`
- `src/transforms/errors.py`
- `src/workflow_runtime/operations/stage_catalog.py`
- `tests/transforms/__init__.py`
- `tests/transforms/test_contracts.py`
- `tests/transforms/test_stage_catalog.py`

Modify:

- `src/transforms/__init__.py`
- `src/workflow_runtime/operations/base.py`
- `src/workflow_runtime/dsl/workflow_validator.py`
- `tests/test_workflow_runtime.py` only if existing validator coverage cannot be cleanly placed in the focused catalog test file.

### Expected Tests

- Contract construction and plain JSON-compatible serialization.
- `contract_version: 1` acceptance and unsupported-version rejection.
- Required/unknown key, duplicate ID/output, invalid enum, and malformed option errors.
- Python-compatible named regex group contract, using `(?P<name>...)` syntax.
- Stable error codes, paths, and safe messages.
- Catalog includes all existing stages, especially `matching`, plus reserved v0.6 names `validate_data`, `sort`, and `aggregate` when their registration policy is defined.
- Workflow validator and public stage catalog consistency.
- No execution behavior tests beyond confirming Phase 1 remains contracts/catalog only.

### Verification Commands

```powershell
python -m pytest tests/transforms/test_contracts.py tests/transforms/test_stage_catalog.py -q
python -m pytest tests/test_workflow_runtime.py -q
python scripts/verify_boundaries.py
git status --short --branch
git diff --check
```

If `scripts/verify_boundaries.py` is unavailable, report that explicitly and run `python -m pytest tests/boundaries -q` if the boundary suite exists.

### Stop Condition

Stop after Phase 1 implementation, targeted tests, and boundary verification. Do not create executors or modify `TransformStage`.

## 3. Phase 2: TransformStage Execution and Mapping Foundation

### Objectives

- Establish `src/transforms` as the canonical generic tabular execution path.
- Add a fixed operation registry with no dynamic discovery or arbitrary callbacks.
- Implement deterministic flat field mapping and named regex mapping.
- Validate the complete plan and input-column preconditions before mutating a copied DataFrame.
- Add a Workflow Runtime adapter for supported tabular artifacts: DataFrame and list of row dictionaries.
- Make `TransformStage` execute the canonical transformation path and return transformed data.
- Preserve current `TransformationPipeline.apply(rules)` behavior and all existing legacy operation names.

### Expected Files

Create:

- `src/transforms/registry.py`
- `src/transforms/executor.py`
- `src/transforms/field_mapping.py`
- `src/transforms/regex_registry.py`
- `src/workflow_runtime/operations/tabular_artifact_adapter.py`
- `tests/transforms/test_registry.py`
- `tests/transforms/test_executor.py`
- `tests/transforms/test_field_mapping.py`
- `tests/transforms/test_regex_registry.py`

Modify:

- `src/transforms/__init__.py`
- `src/transforms/pipeline.py`
- `src/workflow_runtime/operations/transform_stage.py`
- `tests/test_transform.py`
- `tests/test_workflow_runtime.py`

`src/transform/` should remain unchanged unless a narrowly required public adapter is identified during implementation. Any such change must be justified in the Phase 2 summary and must not duplicate generic executor behavior.

### Required Behavior

- New plans use `{contract_version, operations}` with ordered `{id, type, options}` records.
- New v1 operations: `rename`, `field_map`, `regex_map`, `type_coercion`, `drop_nulls`, `deduplicate`, `add_constant`, and explicitly registered domain normalization.
- Legacy rules retain `rename`, `drop_nulls`, `filter`, `type_coercion`, `deduplicate`, `normalize`, and `add_column` semantics.
- `filter` remains supported only through the legacy compatibility path in v0.6; no new arbitrary expression DSL is added.
- Field mapping supports flat source/target names, required/default behavior, allowlisted coercion, deterministic scalar transforms, and `on_error` policy.
- Regex mappings use prevalidated repository/config patterns, controlled flags, explicit source/target fields, and named capture groups.
- Input data is copied. Failed execution never publishes partial output as success.
- Unsupported artifact types and invalid plans return a failed `StageResult` with privacy-safe errors.
- Successful metadata includes operation IDs, operation count, and rows in/out, but no source values.

### Expected Tests

- Registry allowlist, duplicate registration rejection, and unknown operation rejection.
- Ordered operation execution and deterministic repeated output.
- Legacy rule parity for every currently supported operation.
- DataFrame and list-of-dictionaries artifact adaptation.
- Source artifact immutability.
- Field mapping defaults, required fields, coercion, scalar transforms, and error policies.
- Regex compilation, controlled flags, missing groups, no-match behavior, and representative adversarial patterns.
- Transform-stage success, invalid config, unsupported input, executor failure, metadata privacy, and no silent pass-through.

### Verification Commands

```powershell
python -m pytest tests/transforms/test_registry.py tests/transforms/test_executor.py tests/transforms/test_field_mapping.py tests/transforms/test_regex_registry.py -q
python -m pytest tests/test_transform.py tests/test_workflow_runtime.py -q
python scripts/verify_boundaries.py
git status --short --branch
git diff --check
```

### Stop Condition

Stop after Phase 2 implementation and verification. Do not implement data-level validation, sort, or aggregation.

## 4. Phase 3: Data-Level Validation

### Objectives

- Implement deterministic tabular validation independent of document structural validation and Entity Runtime validation.
- Support `required`, `type`, `regex`, `min`, `max`, `allowed_values`, and `unique` rules.
- Produce bounded, JSON-compatible results with aggregate counts and privacy-safe row issue references.
- Add Workflow Runtime `ValidationStage` under stage type `validate_data`.
- Support `fail_stage` and `report_only` policies.

### Expected Files

Create:

- `src/transforms/validation.py`
- `src/workflow_runtime/operations/validation_stage.py`
- `tests/transforms/test_validation.py`

Modify:

- `src/transforms/contracts.py`
- `src/transforms/__init__.py`
- `src/workflow_runtime/operations/__init__.py`
- `src/workflow_runtime/operations/stage_catalog.py`
- `tests/transforms/test_stage_catalog.py`
- `tests/test_workflow_runtime.py`

### Required Behavior

- Validate plan shape and input columns before evaluating rows.
- Preserve deterministic rule and issue ordering.
- Report `row_index`, `rule_id`, `field`, `severity`, and safe message without full records or raw sensitive values.
- Enforce a documented default issue-detail limit while retaining complete aggregate counts and a truncation marker.
- Under `fail_stage`, error-severity failures return a failed stage; warnings alone do not.
- Under `report_only`, return success with the unchanged input artifact and structured validation metadata/result.
- Never import Document Engine or Entity Runtime validation internals.

### Expected Tests

- Passing and failing behavior for every rule type.
- Warning/error severity behavior and both failure policies.
- Deterministic issue ordering and accurate aggregate counts.
- Issue truncation and total-count retention.
- Missing columns, null values, coercion boundaries, duplicate values, and empty DataFrames.
- Input immutability and output serialization.
- Privacy assertions for messages, metadata, and result dictionaries.
- Workflow stage registration and `StageResult` behavior.

### Verification Commands

```powershell
python -m pytest tests/transforms/test_contracts.py tests/transforms/test_validation.py tests/transforms/test_stage_catalog.py -q
python -m pytest tests/test_workflow_runtime.py -q
python scripts/verify_boundaries.py
git status --short --branch
git diff --check
```

### Stop Condition

Stop after Phase 3 implementation and verification. Do not implement sorting or aggregation.

## 5. Phase 4: Sort and Aggregation Stages

### Objectives

- Implement stable single- and multi-column sorting with explicit direction and null placement.
- Implement deterministic grouped and dataset-level aggregation.
- Support only `count`, `sum`, `avg`, `min`, and `max` aggregate functions.
- Add Workflow Runtime `SortStage` and `AggregationStage` under `sort` and `aggregate` stage types.
- Validate input fields, output-name uniqueness, empty inputs, and function/type compatibility.

### Expected Files

Create:

- `src/transforms/sorting.py`
- `src/transforms/aggregation.py`
- `src/workflow_runtime/operations/sort_stage.py`
- `src/workflow_runtime/operations/aggregation_stage.py`
- `tests/transforms/test_sorting.py`
- `tests/transforms/test_aggregation.py`

Modify:

- `src/transforms/contracts.py`
- `src/transforms/__init__.py`
- `src/workflow_runtime/operations/__init__.py`
- `src/workflow_runtime/operations/stage_catalog.py`
- `tests/transforms/test_stage_catalog.py`
- `tests/test_workflow_runtime.py`

### Required Behavior

- Sorting is stable and does not alter columns or values.
- Every sort key declares field, direction, and null placement.
- Aggregation output names are explicit and unique.
- Empty `group_by` produces one dataset-level aggregate row where function semantics allow it.
- Null-group behavior follows `drop_null_groups` explicitly.
- Unsupported functions, missing columns, output collisions, and incompatible types fail clearly.
- Inputs remain unchanged; stages return copied/result artifacts and privacy-safe metadata.

### Expected Tests

- Ascending/descending and mixed multi-column sorts.
- Stable ordering for equal keys and deterministic null placement.
- Empty input, missing sort fields, and invalid sort options.
- Each aggregate function with and without grouping.
- Multiple grouping keys, null groups, empty input, explicit output schema, and deterministic row order.
- Duplicate output names, missing fields, unsupported functions, and incompatible data types.
- Sort/aggregation stage registration, success/failure results, metadata, and input immutability.

### Verification Commands

```powershell
python -m pytest tests/transforms/test_sorting.py tests/transforms/test_aggregation.py tests/transforms/test_stage_catalog.py -q
python -m pytest tests/test_workflow_runtime.py -q
python scripts/verify_boundaries.py
git status --short --branch
git diff --check
```

### Stop Condition

Stop after Phase 4 implementation and verification. Do not start release documentation or tagging.

## 6. Phase 5: Integration Verification and Release

### Objectives

- Add a deterministic end-to-end workflow fixture covering transform -> validate -> sort -> aggregate.
- Run targeted and full available regression suites.
- Verify runtime boundaries, privacy-safe metadata, backward compatibility, and representative in-memory performance.
- Close architecture and release documentation.
- Prepare, but do not automatically create, the final release tag.

### Expected Files

Create:

- `tests/transforms/test_integration.py`
- `docs/architecture/EXTRACTION_TRANSFORMATION_CAPABILITY_HARDENING_V1_SUMMARY.md`
- `docs/architecture/EXTRACTION_TRANSFORMATION_CAPABILITY_HARDENING_V1_HANDOFF.md`
- `docs/releases/v0.6-extraction-transformation-capability-hardening.md`

Modify:

- `docs/architecture/EXTRACTION_TRANSFORMATION_CAPABILITY_HARDENING_V1_PLAN.md`
- `docs/architecture/EXTRACTION_TRANSFORMATION_CAPABILITY_HARDENING_V1_IMPLEMENTATION_PLAN.md`
- `docs/adr/ADR-012-extraction-transformation-capability-hardening.md`
- `docs/ROADMAP.md`
- `TECHNICAL_DEBT.md`
- `CHANGELOG.md`

Production code changes are not expected in Phase 5. Any defect discovered during verification must be handled in a separate, narrowly scoped bug-fix session before release documentation is finalized.

### Expected Tests

- End-to-end deterministic tabular workflow.
- Cross-stage artifact and metadata compatibility.
- Legacy transformation-rule regression.
- Registry/catalog consistency across every public stage.
- Privacy, issue-limit, immutability, and runtime-boundary regression.
- Representative DataFrame performance smoke test with documented row count and elapsed time; no distributed-performance claim.

### Verification Commands

```powershell
python -m pytest tests/transforms tests/test_transform.py tests/test_workflow_runtime.py tests/test_matching_runtime.py -q
python -m pytest tests/boundaries -q
python scripts/verify_boundaries.py
python -m pytest -q
git status --short --branch
git diff --check
```

Record pre-existing or environment-dependent failures separately. No failing test may be treated as unrelated without evidence from the baseline or targeted reproduction.

### Stop Condition

Stop after verification and release documentation. Do not commit, push, or tag unless a separate prompt explicitly authorizes those actions.

## 7. Expected Files by Phase

| Phase | Production scope | Test scope | Documentation scope |
|---|---|---|---|
| 1 | Contracts, errors, stage catalog, workflow validator alignment | Contract/catalog/validator tests | ADR-012 |
| 2 | Registry, executor, mapping, regex, artifact adapter, `TransformStage` | Transform unit and workflow integration tests | None expected |
| 3 | Data validator and `ValidationStage` | Validation/privacy/stage tests | None expected |
| 4 | Sort/aggregation executors and stages | Sort/aggregation/stage tests | None expected |
| 5 | No planned production changes | End-to-end and regression verification | Summary, handoff, release notes, roadmap/debt/changelog closure |

Exact filenames may change only when repository structure requires it. Any deviation must be explained in the phase summary and remain within the same ownership boundary.

## 8. Expected Tests by Phase

- **Phase 1:** Contract shape, serialization, configuration errors, stage catalog consistency, workflow validation.
- **Phase 2:** Registry, ordered execution, field/regex mapping, legacy parity, artifact adaptation, `TransformStage` integration.
- **Phase 3:** Validation rules, severity/failure policy, bounded/privacy-safe reports, `ValidationStage` integration.
- **Phase 4:** Stable sorting, allowlisted aggregation, edge cases, both workflow stages.
- **Phase 5:** End-to-end deterministic workflow, regressions, boundaries, privacy, compatibility, performance smoke test.

Tests must use local deterministic fixtures. Network calls, OCR fixtures, model calls, vendor services, UI automation, and external master-data systems are prohibited.

## 9. Verification Commands by Phase

Each phase must run:

1. Its focused tests listed above.
2. `python -m pytest tests/test_workflow_runtime.py -q` when Workflow Runtime changes.
3. `python scripts/verify_boundaries.py` when available.
4. `git status --short --branch`.
5. `git diff --check`.

Phase 5 additionally runs the full available test suite. Test commands must use the repository's configured Python environment; if `python` does not resolve to it, report the exact interpreter used.

## 10. Boundary Requirements

- `src/transforms` may import standard-library modules, Pandas, and existing generic transform helpers only.
- `src/transforms` must not import Workflow, Document, Entity, Matching, Review, API, Monitoring, repository, locking, or persistence internals.
- Workflow Runtime may import public `src.transforms` contracts/executors and public upstream runtime contracts through explicit adapters.
- Document Engine retains document parsing and structural validation ownership.
- Entity Runtime retains entity extraction, lineage, confidence, normalization, validation, stores, and concurrency ownership.
- Matching Runtime remains unchanged.
- Stage catalog modules must remain dependency-light and must not import stage implementation classes.
- Registries are static in-process mappings. No dynamic imports, entry-point discovery, filesystem scanning, or network loading.
- No new boundary exemption is acceptable without a separate architecture decision.

## 11. Backward Compatibility Requirements

- Preserve `TransformationPipeline(df).apply(rules)` and its DataFrame return type.
- Preserve existing legacy rule names and behavior: `rename`, `drop_nulls`, `filter`, `type_coercion`, `deduplicate`, `normalize`, and `add_column`.
- Preserve existing Workflow, `StageDefinition`, `WorkflowDefinition`, `StageResult`, Document, Entity, and Matching public contracts.
- Existing workflow definitions remain valid; `matching` becomes valid rather than rejected.
- New stage types and versioned plan formats are additive.
- Do not silently reinterpret legacy `filter` expressions as the new structured rule format.
- Do not mutate input DataFrames or upstream runtime artifacts.
- Existing stage result status conventions and error handling remain intact.
- Any unavoidable incompatibility requires a separate ADR and explicit user approval before implementation.

## 12. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Document/entity artifacts are not naturally tabular | Support only explicit adapter inputs in v0.6 and fail unsupported artifacts clearly. |
| Legacy rules regress when routed through the executor | Add operation-by-operation parity tests before changing `TransformStage`. |
| `src/transform` and `src/transforms` diverge further | Keep generic behavior in `src/transforms`; modify the domain package only through a justified adapter. |
| Stage catalog creates import-order or cycle problems | Store names in a dependency-light module and bind implementations separately. |
| Regex contracts use syntax unsupported by Python | Validate compilation at contract load and standardize named groups as `(?P<name>...)`. |
| Arbitrary filters or transforms become executable code | Keep new contracts allowlisted; preserve legacy filter behavior only for compatibility. |
| Validation reports expose data or grow without bound | Omit raw values, cap detailed issues, and retain aggregate totals plus truncation state. |
| Aggregation output breaks downstream assumptions | Require explicit unique outputs and cover schema changes in integration tests. |
| Full-suite failures obscure milestone quality | Establish targeted results first and classify broader failures against evidence/baseline. |
| Scope expands into OCR, MDM, UI, API, or LLM work | Treat all as explicit non-goals and reject them from phase changes. |

## 13. Definition of Done

- All five phases are implemented in separate sessions and verified before advancing.
- `TransformStage` executes deterministic transformations and never reports unapplied rules as successful.
- Generic transform execution has one canonical path under `src/transforms`.
- Versioned JSON-compatible contracts cover transformations, mappings, regex, validation, sorting, and aggregation.
- Field/regex mapping is validated, reusable, deterministic, and limited to flat fields in v1.
- Data-level validation returns bounded, privacy-safe structured results.
- `validate_data`, `sort`, and `aggregate` stages are registered, validated, and tested.
- Workflow validator and runtime stage catalog are consistent, including `matching`.
- Existing legacy transformation rules and public runtime contracts remain compatible.
- Inputs are not mutated and failed plans do not publish partial successful output.
- Targeted, integration, boundary, privacy, determinism, and available regression tests pass or have evidence-backed baseline exceptions.
- No new dependencies or boundary exemptions are introduced.
- OCR, LLM extraction, UI, API, and full MDM/golden-record lifecycle remain deferred.
- ADR, architecture summary, handoff, roadmap, technical debt, changelog, and release notes describe the delivered state.

## 14. Commit and Tag Strategy

Commits and tags are manual actions and require explicit authorization. Recommended checkpoints:

1. Phase 1: `feat: add v0.6 transform contracts and stage catalog`
2. Phase 2: `feat: execute deterministic workflow transformations`
3. Phase 3: `feat: add deterministic data validation stage`
4. Phase 4: `feat: add workflow sort and aggregation stages`
5. Phase 5: `docs: close v0.6 extraction transformation hardening`

Before each commit, review `git status`, confirm only phase-scoped files are included, and record targeted verification results. Do not combine incomplete phases into a closure commit.

After Phase 5 verification and release documentation are complete:

- Create the final release commit only when explicitly requested.
- Confirm the working tree is clean and the release commit is at `HEAD`.
- Create annotated tag `v0.6-extraction-transformation-capability-hardening` only when explicitly requested.
- Push the branch and tag only when explicitly requested.

No phase automatically starts, commits, pushes, or tags the next phase.

## Completion Record

All five implementation phases are complete. Phase 5 added deterministic integration coverage and closure documentation. Targeted regression (210 tests), boundary tests (22), and the standalone boundary verifier pass. The full suite is blocked during collection in the active interpreter because declared requirements `rapidfuzz` and `playwright` are not installed; the release tag must wait for a provisioned full-suite pass.
