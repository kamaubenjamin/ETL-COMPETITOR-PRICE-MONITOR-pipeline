# Extraction & Transformation Capability Hardening v1 Handoff

**Milestone:** v0.6
**State:** Implementation complete; final tag pending full-suite environment verification
**Branch:** `platform/intelligent-document-processing`

## Current State

Phases 1-5 are implemented. Workflow Runtime now executes versioned deterministic transformation plans and exposes `validate_data`, `sort`, and `aggregate` stages. The end-to-end local fixture `transform -> validate_data -> sort -> aggregate` passes and verifies deterministic output, artifact compatibility, metadata privacy, and input immutability.

Targeted regressions and boundary verification pass. The full repository suite does not currently collect in the active Codex interpreter because declared dependencies `rapidfuzz` and `playwright` are not installed. Do not create the final tag until the complete suite is run in a provisioned environment.

## Important Files

- Architecture: `docs/architecture/EXTRACTION_TRANSFORMATION_CAPABILITY_HARDENING_V1_PLAN.md`
- Implementation plan: `docs/architecture/EXTRACTION_TRANSFORMATION_CAPABILITY_HARDENING_V1_IMPLEMENTATION_PLAN.md`
- Decision record: `docs/adr/ADR-012-extraction-transformation-capability-hardening.md`
- Contracts/errors: `src/transforms/contracts.py`, `src/transforms/errors.py`
- Execution: `src/transforms/executor.py`, `src/transforms/pipeline.py`
- Mapping/regex: `src/transforms/field_mapping.py`, `src/transforms/regex_registry.py`
- Validation/sort/aggregation: `src/transforms/validation.py`, `src/transforms/sorting.py`, `src/transforms/aggregation.py`
- Workflow stages: `src/workflow_runtime/operations/transform_stage.py`, `validation_stage.py`, `sort_stage.py`, `aggregation_stage.py`
- Artifact adapter/catalog: `src/workflow_runtime/operations/tabular_artifact_adapter.py`, `stage_catalog.py`
- Integration test: `tests/transforms/test_integration.py`
- Release notes: `docs/releases/v0.6-extraction-transformation-capability-hardening.md`

## How to Run Tests

Use the repository/project Python environment. In the current Codex session, pytest was available at:

```powershell
& 'C:\Users\ASABEN\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest tests/transforms tests/test_transform.py tests/test_workflow_runtime.py tests/test_matching_runtime.py -q
& 'C:\Users\ASABEN\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest tests/boundaries -q
& 'C:\Users\ASABEN\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' scripts/verify_boundaries.py
```

Before release tagging, provision all declared requirements and run:

```powershell
python -m pip install -r requirements.txt
python -m pytest -q
python scripts/verify_boundaries.py
git status --short --branch
git diff --check
```

Dependency installation and browser/runtime provisioning are environment operations, not v0.6 source changes. Review any full-suite failures rather than assuming they are unrelated.

## Extension Guidance

- Add new generic tabular behavior under `src/transforms`; do not import runtime internals there.
- Add new workflow adaptation/orchestration under `src/workflow_runtime/operations`.
- Extend versioned contracts additively and validate unknown fields strictly.
- Preserve plan preflight before mutation and privacy-safe configuration errors.
- Keep operation and stage registries explicit; do not add dynamic discovery or executable callbacks.
- Add deterministic unit, negative, immutability, privacy, integration, and boundary tests for every extension.
- Maintain the distinction between data validation, Document structural validation, and Entity validation.

## What Not to Change

- Do not move document parsing or structural validation into `src/transforms`.
- Do not move entity extraction, validation, persistence, or concurrency into the generic transform layer.
- Do not change Matching Runtime behavior as part of transform extensions.
- Do not remove the legacy transformation compatibility path without a separate deprecation/versioning decision.
- Do not expose raw rows or values in stage metadata or validation messages.
- Do not add OCR, LLM, UI, API, MDM, vendor, or external-service work under the v0.6 milestone.
- Do not tag or push without explicit authorization.

## Known Risks and Deviations

- The full suite is unverified in the current interpreter because `rapidfuzz` and `playwright` are absent despite being declared requirements.
- The boundary scanner skips two existing BOM-affected files and reports warnings for them.
- Versioned normalization avoids injecting a wall-clock timestamp when no timestamp was supplied; legacy normalization is unchanged.
- `min`/`max` validation thresholds are finite numeric values in v1.
- Fieldless aggregation `count` counts rows; field-specific `count` counts non-null values.
- `sum`/`avg` require numeric non-boolean fields.
- Aggregate metadata uses explicit output names as aggregate IDs because v1 contracts have no separate aggregation ID.
- Lists of row dictionaries become DataFrames when transformed, sorted, or aggregated; validation preserves the original artifact type on successful/report-only execution.

## Release Handoff

1. Review Phase 5 test and documentation changes.
2. Provision `requirements.txt` in the release verification environment.
3. Run the complete suite and boundary verifier.
4. Resolve or explicitly document any resulting failures.
5. Commit Phase 5 using the recommended release-closure message.
6. Confirm a clean worktree and release commit at `HEAD`.
7. Create annotated tag `v0.6-extraction-transformation-capability-hardening` only when explicitly authorized.
8. Push branch and tag only when explicitly authorized.
