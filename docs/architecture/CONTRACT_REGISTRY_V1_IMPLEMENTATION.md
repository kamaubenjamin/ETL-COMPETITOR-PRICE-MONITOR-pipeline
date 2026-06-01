# Contract Registry v1 Implementation
Date: 2026-06-01

## Objective

Close Contract Registry v1 as the first Runtime Hardening deliverable. The implementation formalizes repository-owned JSON Schema contracts for runtime artifacts and provides deterministic local validation for schema examples.

## Scope Completed

- Created a repository-centric contract registry under `docs/contracts/`.
- Adopted JSON Schema Draft 07 for Contract Registry v1.
- Added canonical schemas for Entity, Matching, Workflow, and Review runtime artifacts.
- Added example fixtures for every registered v1 contract.
- Added Python validation helpers for contract tests.
- Added `scripts/validate_contracts.py` for local contract validation.
- Stabilized local `$ref` resolution for schemas that use URN `$id` values.
- Added contract validation tests under `tests/contracts/`.

## Registry Layout

```text
docs/contracts/
  registry_README.md
  entity_runtime/
    EntitySet.schema.json
  matching_runtime/
    MatchSet.schema.json
  review_runtime/
    ReviewDecision.schema.json
    ReviewRequest.schema.json
  workflow_runtime/
    StageResult.schema.json
    WorkflowArtifact.schema.json
  examples/
    entityset_example.json
    matchset_example.json
    review_decision_example.json
    review_request_example.json
    stageresult_example.json
    workflowartifact_example.json
```

## Implemented Contracts

| Runtime | Contract | Schema Version | Fixture |
|---|---|---:|---|
| Entity Runtime | `EntitySet` | `1.0.0` | `entityset_example.json` |
| Matching Runtime | `MatchSet` | `1.0.0` | `matchset_example.json` |
| Review Runtime | `ReviewRequest` | `1.0.0` | `review_request_example.json` |
| Review Runtime | `ReviewDecision` | `1.0.0` | `review_decision_example.json` |
| Workflow Runtime | `StageResult` | `1.0.0` | `stageresult_example.json` |
| Workflow Runtime | `WorkflowArtifact` | `1.0.0` | `workflowartifact_example.json` |

## Validation Tooling

Local validation entrypoints:

```powershell
pytest tests/contracts -v
python scripts/validate_contracts.py
```

Validation behavior:

- Loads all schemas and examples from `docs/contracts/`.
- Validates each example fixture against its canonical schema.
- Uses `jsonschema.Draft7Validator`.
- Preloads schema documents into the resolver store by file URI, filename, absolute path, and `$id`.
- Adds current-schema fallback handling for URN `$id` plus nested local `$ref` resolution.

## Runtime Boundary Impact

Contract Registry v1 does not introduce new runtime dependencies. It is a governance and validation layer that records public artifact contracts produced or consumed by existing runtimes.

- Document Runtime remains upstream of Entity Runtime.
- Entity Runtime owns `EntitySet` output shape.
- Matching Runtime owns `MatchSet` output shape.
- Workflow Runtime owns stage and workflow artifact shapes.
- Review Runtime owns review request and decision shapes.

## Governance Notes

- Architecture is documented in `docs/architecture/CONTRACT_REGISTRY_V1_ARCHITECTURE.md`.
- Implementation is documented here.
- Summary and handoff documents were created as closure artifacts.
- Existing ADRs were reviewed. No new ADR is required because Contract Registry v1 implements the registry recommendation already captured in runtime ADR future implications and the v0.5 hardening plan without introducing a breaking architectural decision.
- Breaking contract changes still require a MAJOR version bump and an ADR.

## Known Limitations

- CI contract validation is not yet wired into a hosted pipeline.
- Compatibility diffing against a released baseline is not yet implemented.
- Runtime producers and consumers do not yet perform mandatory runtime validation.
- Registry publication remains repository-centric; no external registry API exists in v1.

## Verification

Expected closure verification:

- `pytest tests/contracts -v` passes.
- `python scripts/validate_contracts.py` exits with code `0`.
- Contract Registry v1 documentation is complete enough for future agents to continue without chat context.

## Next Work

The next planned Runtime Hardening objective is CI Contract Validation. That work should add hosted PR/release gating around the existing registry and validation harness without changing the v1 registry layout unless a new ADR justifies the change.

End of document.
