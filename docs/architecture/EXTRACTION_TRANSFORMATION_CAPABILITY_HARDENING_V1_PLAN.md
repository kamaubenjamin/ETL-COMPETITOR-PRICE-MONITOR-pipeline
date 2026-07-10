# Extraction & Transformation Capability Hardening v1 Architecture Plan

**Milestone:** v0.6  
**Status:** Implemented; final release tag pending full-suite environment verification
**Scope:** Deterministic extraction, transformation, validation, sorting, and aggregation capabilities  

## 1. Problem Statement

The repository has useful deterministic extraction and DataFrame transformation logic, but the capabilities are not consistently available through Workflow Runtime. `TransformStage` currently reports configured rules without executing the existing transformation pipeline. Rule handling, regex extraction, and field mapping are code-driven and scattered, data-level validation is absent, and sorting and aggregation are embedded in helpers rather than exposed as reusable workflow stages. Workflow definition validation also maintains a stage-type list separately from the runtime registry, which has already allowed the registered `matching` stage to become inconsistent with validation.

v0.6 must turn these partial capabilities into a small, deterministic, reusable execution layer while preserving runtime boundaries and existing public contracts. Configuration must remain plain JSON-compatible data, validated before execution, and limited to an explicit set of supported operations.

## 2. Current State Summary

- Document Engine deterministically loads, classifies, normalizes, parses, and structurally validates supported documents.
- Entity Runtime deterministically extracts document references, suppliers, customers, financials, and line items using hardcoded labels, table-column heuristics, and regex patterns.
- `src/transforms/pipeline.py` supports rename, null removal, filtering, type coercion, deduplication, product normalization, and constant-column addition for DataFrames.
- `src/transform/engine.py` composes product parsing with the transformation pipeline, but contains overlapping legacy rule methods and broad exception handling.
- `TransformStage` does not invoke either transformation implementation; it returns a pass-through metadata envelope.
- Regex patterns are embedded across product parsing, normalization, intelligence, document parsing, and entity extraction modules.
- Field mapping exists as rename dictionaries and hardcoded table-column detection, but no validated source-to-target mapping contract exists.
- Validation covers workflow structure, document structure, and lightweight entity checks, but not tabular schema, field constraints, or row-level outcomes.
- Sorting and grouping exist only as local DataFrame helper calls.
- Workflow Runtime registers `matching`, but `WorkflowValidator.VALID_STAGE_TYPES` does not accept it.

## 3. Goals

1. Make `TransformStage` execute real deterministic transformation logic and return the transformed artifact.
2. Establish one generic transformation execution path under `src/transforms` for reusable, runtime-independent operations.
3. Define versioned, JSON-compatible contracts for ordered rules, field mappings, regex mappings, data validation, sorting, and aggregation.
4. Replace scattered configuration semantics with validated registries and explicit operation allowlists.
5. Add reusable Workflow Runtime stages for data validation, sorting, and aggregation.
6. Keep extraction and transformation behavior deterministic, ordered, explainable, and locally testable.
7. Ensure workflow stage validation and runtime registration use one authoritative stage-type source.
8. Preserve existing Document, Entity, Matching, and Workflow Runtime ownership boundaries.

## 4. Non-Goals

- OCR or processing of image-only/scanned documents.
- LLM-based extraction, classification, mapping, validation, or correction.
- UI, mapping designer, dashboard, or API work.
- External rule services, plugin execution, arbitrary Python callbacks, or vendor dependencies.
- Full MDM, golden-record creation, survivorship, entity merging, or persistent master-data lifecycle.
- Changes to Matching Runtime strategies or Entity Runtime concurrency behavior.
- Streaming, distributed execution, parallel workflow branches, or large-scale query optimization.
- A general-purpose programming language or complex rules DSL.
- Pivot tables, window functions, or time-series resampling in v1.

## 5. Proposed Architecture

The architecture has three layers:

1. **JSON-compatible configuration contracts** describe ordered operations and their options. Contracts contain data only and carry `contract_version: 1`.
2. **Deterministic executors in `src/transforms`** validate configuration and apply allowlisted operations to tabular artifacts. This layer may depend on Pandas and existing transformation helpers, but must not import Workflow, Document, Entity, Matching, API, Review, or Monitoring Runtime internals.
3. **Workflow operation adapters in `src/workflow_runtime/operations`** resolve input artifacts, invoke the generic executors, and translate results or failures into `StageResult` without changing upstream runtime contracts.

`src/transforms` becomes the canonical home for generic tabular capability. Existing domain-specific product parsing and normalization in `src/transform` remain available through explicit adapter operations; v0.6 does not require a broad package merge. New code must not duplicate transformation semantics across the two packages.

Execution is ordered and fail-fast by default. Every operation has a stable `id`, a supported `type`, and an `options` object. Unknown keys, unsupported operation types, invalid regexes, missing required fields, and incompatible aggregation definitions fail configuration validation before data is mutated. Runtime failures identify the operation and return a failed stage result; partial output is not published as successful output.

The canonical generic input/output artifact is a Pandas `DataFrame`, copied before mutation. Workflow adapters may also accept an explicitly supported list of row dictionaries and convert it to a DataFrame. Document or Entity artifacts require an adapter owned by Workflow Runtime or the producing runtime's public API; `src/transforms` must not inspect runtime-specific objects. Unsupported artifact types fail clearly rather than being wrapped or silently passed through.

## 6. Runtime Boundaries

- **Document Engine** owns document loading, parsing, structural extraction, and structural validation. Its existing contracts are unchanged.
- **Entity Runtime** owns business-entity extraction, lineage, normalization, confidence, and entity validation. It may consume shared mapping contracts later, but v0.6 must not move entity ownership into `src/transforms`.
- **Matching Runtime** owns candidate retrieval, matching strategies, and match confidence. It is unchanged by this milestone.
- **`src/transforms`** owns generic tabular rule execution, regex extraction, field mapping, data validation, sorting, and aggregation semantics. It must remain free of runtime-internal imports.
- **Workflow Runtime** owns stage orchestration, artifact adaptation, stage registration, execution status, and stage metadata.
- Cross-runtime integration uses public contracts or explicit adapters only. No runtime may call another runtime's private repository, store, or orchestration implementation.
- Existing public workflow, document, entity, and matching contracts remain backward compatible. New configuration contracts are additive and versioned.

## 7. New or Updated Components

Proposed component responsibilities, with exact filenames to be finalized in the implementation plan:

| Area | Component | Responsibility |
|---|---|---|
| `src/transforms` | Configuration contracts | Parse and validate versioned JSON-compatible operation definitions. |
| `src/transforms` | Operation registry | Map allowlisted operation names to deterministic executors; reject duplicate or unknown names. |
| `src/transforms` | Transformation executor | Execute ordered rename, coercion, null handling, deduplication, constants, field mapping, and regex mapping operations. |
| `src/transforms` | Regex registry | Validate, compile, and resolve named regex definitions with controlled flags and named groups. |
| `src/transforms` | Field mapper | Apply source-to-target mappings, defaults, coercion, and allowlisted scalar transforms. |
| `src/transforms` | Data validator | Produce structured dataset and row-level validation results without document/entity imports. |
| `src/transforms` | Sort executor | Apply stable single- or multi-column sorting. |
| `src/transforms` | Aggregation executor | Apply group-by operations with an allowlisted aggregate set. |
| Workflow operations | `TransformStage` | Adapt supported artifacts and execute the canonical transformation path. |
| Workflow operations | `ValidationStage` | Run data-level validation and enforce configured failure policy. |
| Workflow operations | `SortStage` | Execute reusable stable sorting. |
| Workflow operations | `AggregationStage` | Execute reusable grouped aggregation. |
| Workflow validation | Stage catalog integration | Validate stage types against the same authoritative catalog used for runtime resolution. |

Registries are in-process, deterministic dictionaries. v1 does not introduce dynamic discovery, entry points, filesystem scanning, or dependency injection frameworks.

## 8. Proposed Contracts / Config Formats

All examples are JSON-compatible dictionaries. Configuration validation is strict and returns path-aware errors.

### Transformation Plan

```json
{
  "contract_version": 1,
  "operations": [
    {
      "id": "canonical-fields",
      "type": "field_map",
      "options": {
        "mappings": [
          {"source": "Product Name", "target": "product_name", "required": true},
          {"source": "Unit Price", "target": "price", "coerce": "float", "on_error": "null"}
        ]
      }
    },
    {
      "id": "extract-sku",
      "type": "regex_map",
      "options": {
        "source": "product_name",
        "target": "sku",
        "pattern_id": "product_sku_v1",
        "group": "sku",
        "on_no_match": "null"
      }
    },
    {
      "id": "remove-duplicates",
      "type": "deduplicate",
      "options": {"subset": ["product_name", "sku"], "keep": "first"}
    }
  ]
}
```

Supported v1 operation types are intentionally small: `rename`, `field_map`, `regex_map`, `type_coercion`, `drop_nulls`, `deduplicate`, `add_constant`, and existing named domain normalization where explicitly registered. Rules execute in listed order; `priority`, branching, loops, and arbitrary expressions are excluded.

### Regex Definition

```json
{
  "id": "product_sku_v1",
  "pattern": "\\b(?P<sku>[A-Z]{2,5}-[0-9]{2,8})\\b",
  "flags": ["IGNORECASE"],
  "description": "Deterministic product SKU extraction"
}
```

Only known flags are accepted. Patterns compile during configuration validation. Mappings reference a registered pattern by ID, identify an explicit source and target field, and select a named capture group. Inline patterns may be supported only when validated by the same contract; named registry entries are preferred for reuse and deduplication. Input-dependent pattern generation and executable replacements are forbidden.

### Field Mapping

```json
{
  "source": "supplier_price",
  "target": "price",
  "required": false,
  "default": null,
  "coerce": "float",
  "transforms": ["trim"],
  "on_error": "null"
}
```

Allowed scalar transforms are named, registered, and deterministic, such as `trim`, `lower`, `upper`, and `collapse_whitespace`. v1 supports flat fields only. Nested JSON paths, arbitrary functions, concatenation expressions, and templates are deferred.

### Data Validation Plan and Result

```json
{
  "contract_version": 1,
  "failure_policy": "fail_stage",
  "rules": [
    {"id": "price-required", "type": "required", "field": "price", "severity": "error"},
    {"id": "price-positive", "type": "min", "field": "price", "value": 0, "severity": "error"},
    {"id": "currency-known", "type": "allowed_values", "field": "currency", "values": ["KES", "USD"], "severity": "warning"}
  ]
}
```

The result contains `valid`, aggregate counts, rule summaries, and row issues with `row_index`, `rule_id`, `field`, `severity`, and a safe message. It must not include complete source rows or sensitive values by default. Supported v1 rules are `required`, `type`, `regex`, `min`, `max`, `allowed_values`, and `unique`.

### Sort Plan

```json
{
  "keys": [
    {"field": "supplier", "direction": "asc", "nulls": "last"},
    {"field": "price", "direction": "desc", "nulls": "last"}
  ],
  "stable": true
}
```

### Aggregation Plan

```json
{
  "group_by": ["supplier"],
  "aggregations": [
    {"field": "price", "function": "min", "output": "min_price"},
    {"field": "price", "function": "avg", "output": "avg_price"},
    {"field": "product_name", "function": "count", "output": "product_count"}
  ],
  "drop_null_groups": false
}
```

Allowed aggregate functions are `count`, `sum`, `avg`, `min`, and `max`. Output names must be explicit and unique. Empty `group_by` may produce one dataset-level row. Pivoting and custom aggregate functions are excluded.

## 9. Workflow Stage Changes

### TransformStage

- Accept the existing `rules` list for backward compatibility and the versioned `plan` form for new workflows.
- Convert supported tabular artifacts through a dedicated workflow-owned adapter.
- Execute the canonical `src/transforms` pipeline and return the transformed artifact directly.
- Report operation count, rows in/out, and operation IDs in metadata without recording row values.
- Return a failed `StageResult` for invalid configuration, unsupported artifact type, or operation failure.
- Never report rules as applied unless execution completed successfully.

### ValidationStage

- Stage type: `validate_data`.
- Return the input data plus a structured validation result in an explicit result artifact or stage metadata contract.
- Support `fail_stage` and `report_only` policies. Errors fail the stage under `fail_stage`; warnings never fail it by themselves.
- Keep data-level validation separate from Document Engine structural validation and Entity Runtime validation.

### SortStage

- Stage type: `sort`.
- Apply stable multi-column sorting using declared direction and null placement.
- Preserve columns and row values; only row order changes.

### AggregationStage

- Stage type: `aggregate`.
- Produce a new tabular artifact from declared grouping keys and allowlisted aggregate functions.
- Validate input fields, output-name collisions, and function/type compatibility before execution.

### Registry Consistency

The runtime registry and workflow validator must share one authoritative stage catalog. Import-order side effects must not determine which types validation accepts. The catalog should expose stable stage type names; runtime registration binds implementations to those names and startup/tests verify exact consistency. Existing `matching` is added to the authoritative catalog, and new v0.6 stage types are introduced through the same path.

## 10. Validation Strategy

Validation occurs at three distinct boundaries:

1. **Workflow definition validation:** stage type, required stage config, dependency references, and supported contract version.
2. **Operation configuration validation:** required keys, allowed keys, unique IDs, regex compilation, mapping validity, supported coercions/functions, and cross-reference resolution.
3. **Data validation:** schema and row-level rules applied to the actual tabular artifact.

Configuration validation is deterministic and side-effect free. Errors include a stable code, configuration path, operation/rule ID, and safe message. No raw source values appear in errors by default. Data validation results distinguish warnings from errors and aggregate repeated row issues to avoid unbounded metadata. A configurable issue limit may truncate detail while retaining total counts.

Validation must occur before transformation execution where possible. Operations whose validity depends on input columns perform preflight checks against the DataFrame schema before the first mutation. The executor works on a copy so failed plans do not alter the input artifact.

## 11. Testing Strategy

- Unit tests for every contract validator, supported operation, registry lookup, regex compile/match behavior, field mapping option, validation rule, sort option, and aggregation function.
- Negative tests for unknown keys/types, malformed versions, duplicate IDs/output fields, invalid regexes/groups, missing columns, incompatible types, and unsupported artifact types.
- Determinism tests proving identical input and config produce identical output and ordered issue reports.
- Immutability tests proving source DataFrames and upstream artifacts are not modified.
- Workflow stage tests proving `TransformStage` performs real work and that validation, sort, and aggregation stages return correct `StageResult` status/artifacts/metadata.
- Registry consistency tests proving every declared stage type is registered and every registered public stage type is accepted by workflow validation, including `matching`.
- Boundary tests proving generic transform modules do not import runtime internals and existing runtime direction rules remain compliant.
- Regression tests for existing transformation rules and Workflow, Document, Entity, and Matching Runtime suites.
- Privacy tests proving errors, validation reports, and metadata omit full rows and unapproved sensitive values.
- End-to-end deterministic fixture test covering tabular input -> transform -> validate -> sort -> aggregate.

No OCR, network, external service, UI, or model fixture is required for v0.6 tests.

## 12. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Artifact mismatch between document ingestion output and DataFrame operations | Transform stage cannot safely execute some workflow paths | Define supported artifacts explicitly and keep conversion in workflow-owned adapters; fail unsupported inputs clearly. |
| Breaking existing rule configurations | Existing workflows regress | Preserve the current `rules` list as a v1 compatibility form and add strict tests before deprecation is considered. |
| Two transform packages continue to overlap | Semantics diverge | Make `src/transforms` canonical for generic operations and expose domain-specific `src/transform` behavior only through registered adapters. |
| Arbitrary expressions create security or reproducibility problems | Unsafe or environment-dependent execution | Use allowlisted operators/transforms; do not add Python evaluation, callbacks, or general expression execution. |
| Regex performance or catastrophic backtracking | Runtime latency and denial of service on large fields | Validate patterns, limit supported sources/config sizes, document pattern review rules, and add adversarial tests for repository-owned patterns. |
| Validation issue volume grows with dataset size | Excessive memory and stage metadata | Cap detailed issues, retain aggregate counts, and never embed complete invalid rows. |
| Aggregation changes schema unexpectedly | Downstream stages fail | Require explicit output names and validate resulting schema contracts in tests/configuration. |
| Registry catalog introduces import cycles | Workflow startup failure | Keep stage names in a dependency-light catalog and bind implementations separately. |
| Scope expands into extraction redesign or MDM | Milestone delay | Restrict v0.6 to deterministic config, tabular execution, and workflow exposure; retain explicit deferrals. |

## 13. Phase Breakdown

### Phase 1: Contracts, Catalog, and ADR

- Record the deterministic configuration and runtime-boundary decision in an ADR.
- Define v1 JSON-compatible contracts and validation errors.
- Establish the authoritative workflow stage catalog and resolve the existing `matching` inconsistency.
- Add contract, catalog, and boundary tests.

### Phase 2: Transformation Execution and Mapping Foundation

- Make `src/transforms` the canonical generic executor.
- Implement operation registry, field mapping, regex registry/mapping, and compatibility for existing transformation rules.
- Integrate real execution into `TransformStage` through supported artifact adapters.
- Verify no source artifact mutation and no silent pass-through behavior.

### Phase 3: Data-Level Validation

- Implement validation contracts, deterministic rules, bounded reports, and privacy-safe errors.
- Add `ValidationStage` with `fail_stage` and `report_only` policies.
- Verify separation from document structural and entity validation.

### Phase 4: Sorting and Aggregation

- Implement stable sort and allowlisted aggregation executors.
- Add and register `SortStage` and `AggregationStage`.
- Verify schema, null, empty-input, type, and deterministic ordering behavior.

### Phase 5: Integration Verification and Release

- Add end-to-end deterministic workflow fixtures and regression coverage.
- Run observability/privacy and runtime-boundary verification where available.
- Update architecture summary, ADR status, roadmap, technical debt, changelog, and v0.6 release notes.
- Confirm milestone closure and release/tag readiness; tagging remains a manual release action.

Each phase is implemented and verified independently. Completion of one phase does not authorize starting the next.

## 14. Definition of Done

- `TransformStage` executes supported transformations and returns transformed data rather than a pass-through envelope.
- Generic transformation behavior has one canonical execution path with ordered, allowlisted operations.
- Versioned JSON-compatible contracts exist for transformation, regex mapping, field mapping, validation, sorting, and aggregation.
- Invalid configuration is rejected before mutation with stable, privacy-safe errors.
- Regex definitions are validated and reusable through a central registry; new v0.6 mappings are not scattered inline.
- Field mapping supports flat source/target fields, required/default behavior, coercion, and allowlisted scalar transforms.
- Data-level validation produces bounded structured results with severity and row/rule references.
- `validate_data`, `sort`, and `aggregate` are reusable Workflow Runtime stages.
- Workflow validation and stage registration are consistent, including the existing `matching` stage.
- Existing public runtime contracts remain compatible and runtime boundary verification passes.
- Unit, negative, integration, determinism, immutability, privacy, boundary, and regression tests pass.
- OCR, LLM extraction, UI, API, and full MDM/golden-record lifecycle remain unimplemented and explicitly deferred.
- Architecture, ADR, roadmap, technical debt, changelog, release notes, and verification summary accurately describe the delivered behavior.

## 15. Release Readiness Criteria

v0.6 is ready for release when:

- All five phases are completed, reviewed, and documented.
- The targeted transformation and workflow test suites pass with deterministic fixtures.
- Full available regression tests show no unexplained failures.
- Runtime boundary verification reports no new violations.
- No production stage silently accepts invalid configuration or unsupported input artifacts.
- Backward-compatibility tests cover existing transformation rule forms and public workflow contracts.
- Privacy checks confirm stage errors and validation metadata do not expose full records or sensitive values.
- Performance smoke tests establish acceptable behavior for representative in-memory DataFrames and record the tested dataset sizes; no distributed-performance claim is made.
- The roadmap and technical debt distinguish completed v0.6 work from deferred OCR, MDM, UI, API, LLM, streaming, and advanced analytics work.
- A release summary and `docs/releases/v0.6-extraction-transformation-capability-hardening.md` are prepared.
- The working tree is clean after the release commit, and the final tag is created manually only after verification.

## 16. Completion Status

Phases 1-5 are implemented. Deterministic end-to-end coverage for `transform -> validate_data -> sort -> aggregate` passes, along with 210 targeted regression tests, 22 boundary tests, and a compliant standalone boundary scan. See `EXTRACTION_TRANSFORMATION_CAPABILITY_HARDENING_V1_SUMMARY.md` for delivered behavior and exact verification results.

The final release tag remains pending because the active verification interpreter lacks declared requirements `rapidfuzz` and `playwright`, causing nine full-suite collection errors. Provision the declared dependencies and complete `python -m pytest -q` before tagging.
