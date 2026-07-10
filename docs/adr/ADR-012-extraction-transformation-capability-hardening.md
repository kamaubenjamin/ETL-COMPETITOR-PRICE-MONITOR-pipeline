# ADR-012: Extraction & Transformation Capability Hardening

- Status: Accepted
- Date: 2026-07-10
- Related Milestone: v0.6 Extraction & Transformation Capability Hardening

## Context

The platform has deterministic document and entity extraction plus reusable DataFrame transformation helpers, but Workflow Runtime does not yet execute those transformations through `TransformStage`. Transformation configuration is only partially declarative, regex and field mappings are scattered, data-level validation is absent, and sorting and aggregation are not reusable workflow stages. Workflow stage validation also maintained a list separate from runtime registration, causing the existing `matching` stage to be registered but rejected by workflow validation.

The v0.6 architecture and implementation plans require a small deterministic foundation before execution behavior is added. The foundation must preserve runtime ownership, current public contracts, and legacy transformation behavior.

## Decision

Adopt versioned, JSON-compatible contracts and a dependency-light workflow stage catalog.

The Phase 1 decision is to:

- define v1 contracts for transformation plans, operations, field mappings, regex definitions, validation plans/results, sort plans, and aggregation plans,
- represent contracts as frozen records with strict `from_dict` validation and plain JSON-compatible `to_dict` serialization,
- report configuration failures with stable error codes and JSONPath-like locations,
- allow only named deterministic operation, coercion, transform, validation, sort, and aggregation values,
- validate regex syntax and require Python named capture groups using `(?P<name>...)`,
- keep generic contracts under `src/transforms` without imports from runtime internals,
- define implemented and reserved workflow stage names in one dependency-light catalog,
- make workflow validation consume that catalog while retaining `VALID_STAGE_TYPES` as a backward-compatible export,
- include `matching` as implemented and reserve `validate_data`, `sort`, and `aggregate` for later v0.6 phases,
- leave reserved stages valid in workflow definitions but unregistered and non-executable until their implementation phases.

## Runtime Boundaries

- `src/transforms` owns generic tabular configuration contracts only in Phase 1.
- Workflow Runtime owns workflow definitions, validation, stage registration, and execution.
- Document Engine retains document parsing and structural validation.
- Entity Runtime retains entity extraction, normalization, confidence, validation, storage, and concurrency.
- Matching Runtime remains unchanged.
- Contracts do not import Workflow, Document, Entity, Matching, Review, API, Monitoring, persistence, or locking internals.
- No new boundary exemption or external dependency is introduced.

## Consequences

### Positive

- Later phases receive stable contracts before runtime behavior changes.
- Configuration failures are deterministic, path-aware, and serializable.
- Workflow validation and stage naming now have one authoritative source.
- Existing `matching` workflows validate correctly.
- Reserved v0.6 names can appear in plans without claiming their implementations exist.
- The configuration model cannot execute arbitrary Python callbacks or dynamic plugins.

### Negative

- Contracts add validation code before any new transformation capability is executable.
- Reserved stages can pass definition validation but will fail runtime resolution until implemented; documentation and tests must keep that distinction explicit.
- Strict unknown-field and enum validation requires contract changes when future options are added.
- Python named capture syntax differs from some regex dialects and must be documented for configuration authors.

## Alternatives Considered

- Derive valid stage names directly from `STAGE_REGISTRY`: rejected because registry contents depend on implementation imports and cannot reserve future stage names safely.
- Keep separate validator and registry lists: rejected because this already caused `matching` drift.
- Add a plugin/discovery framework: rejected as unnecessary and non-deterministic for v1.
- Use a general rule DSL or executable expressions: rejected because v0.6 requires compact JSON-compatible, allowlisted behavior.
- Merge `src/transform` and `src/transforms` in Phase 1: rejected as an unrelated refactor before execution ownership is proven.

## Compliance

- Phase 1 introduces contracts, errors, the stage catalog, validator alignment, tests, and this ADR only.
- Phase 1 does not add executors or change `TransformStage` execution.
- Phase 1 does not implement data validation, sorting, or aggregation runtime behavior.
- Existing public contracts and legacy transformation behavior remain unchanged.
- Targeted contract, catalog, workflow, and boundary verification must pass.

## Follow-up

Phases 2-4 implemented the canonical executor, mapping, real `TransformStage`, data validation, sorting, and aggregation. Phase 5 added deterministic integration verification and release documentation. The implementation follows this decision without new runtime-boundary exemptions or dependencies.

The final tag is pending an environment-complete full regression run because the active interpreter lacks declared requirements `rapidfuzz` and `playwright`.

End of document.
