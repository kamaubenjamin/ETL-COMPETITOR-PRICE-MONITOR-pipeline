# Business Workflow / Rules Studio v1 Plan

**Milestone:** v0.20
**Status:** Planning complete; Phases 1-6 implemented
**Recommended package:** `src/workflow_studio/`

## Phase 1 Implementation Record

Phase 1 establishes the standard-library-only `src/workflow_studio/` contract boundary. It provides immutable JSON-safe workflow, version, publication, rule, condition, and action definitions; the fixed status catalogs; privacy-safe errors; structural repository/catalog ports; and a deterministic in-memory operation catalog. It does not add a validation engine, repository, publication behavior, compiler, runtime import, preview, API, UI, permission, persistence, migration, or production execution path.

The initial catalog exposes the 30 reviewed business-safe names. Exact existing runtime labels `filter`, `fuzzy_match`, and `compare` are marked available and publication-eligible. The other 27 names remain visible but unavailable and unpublishable until a later compiler phase proves their mapping, schemas, limits, and semantics. Catalog recognition never authorizes execution.

Phase 1 focused verification covers 48 tests for serialization, immutability, statuses, safe rule dependencies, modeled conditions/actions, privacy boundaries, catalog ordering/eligibility, protocols, and forbidden imports. Later plan sections remain prospective.

## Phase 2 Implementation Record

Phase 2 adds a deterministic side-effect-free validation service, fixed validation issue/result contracts, stable dependency and cycle analysis, controlled logical-path validation, condition revalidation, action/catalog compatibility checks, caller-supplied publication-readiness facts, and non-executable Sanifu/Docsift compatibility reporting. Workflow Runtime remains the sole execution authority and is not imported.

Structural validity, preview eligibility, test readiness, and publication eligibility are reported independently. Unavailable or unproven operations can remain structurally modeled while explicitly blocking preview/publication. Required features are evaluated only against caller-supplied labels; the validator does not decide tenant authorization or query security, repositories, files, databases, APIs, or networks.

Legacy input is limited to modeled scalar-safe descriptors. Reports preserve bounded lineage, classify exact labels deterministically, identify candidate Studio mappings and missing proof/ports, and always state that no executable conversion was produced. Phase 2 adds 54 tests, bringing the focused Workflow Studio suite to 102 tests. Later plan sections remain prospective.

## Phase 3 Implementation Record

Phase 3 adds persistence-neutral repository contracts, a deterministic lock-protected in-memory store, optimistic revision envelopes, explicit draft/version transitions, immutable-history cloning, pure publication policy, controlled governed-definition publication/deactivation/archive services, and privacy-safe audit intents. It does not activate Workflow Runtime execution.

Workflow IDs, version IDs, and publication IDs are tenant-scoped; the same workflow ID may exist in different tenants, while identities cannot collide inside a tenant. Version labels are unique per tenant/workflow. Only one current pre-publication draft and one active publication are permitted per tenant/workflow. Pagination is stable and bounded to limits 1-100 and offsets 0-10,000.

Content edits are permitted only while a version is `draft`. Approved, published, superseded, inactive, and archived history cannot be rewritten. Rollback clones prior immutable content into a new draft/version and must traverse validation, test, approval, and publication again. Publication records governed definition availability only; no scheduler/runtime binding, API, UI, database, filesystem, or network behavior was added. Phase 3 adds 45 tests, bringing the focused Workflow Studio suite to 147 tests.

## Phase 4 Implementation Record

Phase 4 adds immutable preview commands, fixtures, policies, limits, safe results, rule/stage projections, trace events, audit intents, an injected runtime port, deterministic no-I/O adapters, and a bounded preview service. It imports no Workflow Runtime implementation and does not activate published workflows.

Inline samples and approved fixture references are normalized into immutable scalar-safe mappings/tuples with fixed depth, collection, field, and string bounds. Validation, dependency, preview eligibility, feature, legacy-review, identity, and workflow size gates run before adapter invocation. Adapter exceptions are replaced by fixed issues; results are re-bounded, protected fields are redacted, values are omitted unless explicitly allowed, and trace/audit projections contain no bodies or raw logs.

Duration is a bounded policy/descriptor only because Phase 4 adds no isolated worker or OS-level cancellation. Phase 4 adds 33 tests, bringing the focused Workflow Studio suite to 180 tests. Preview does not publish, persist, mutate repositories/Document State/lifecycle, call ERP/export/alerts/master data, or access files, databases, or networks.

## Phase 5 Implementation Record

Phase 5 adds an app-scoped, process-local Workflow Management API provider and the reviewed definition, version, validation, preview, submit, approval, publication, deactivation, archive, operation-catalog, and audit routes. Responses use the Document Intelligence envelope and bounded safe projections. Reads are tenant-filtered and cross-tenant details are concealed. Mutations fail closed without authenticated authorization and use distinct workflow management permissions; `workflow:read` and `workflow:run` do not grant management authority.

Draft `PATCH` is a complete safe content replacement with `expected_revision`; JSON Patch is not supported. The default preview adapter returns `preview_unavailable`. Publication records governed definition state in app memory only and states: “Published definition governance only; production execution activation is not enabled.” No FlowSync, Streamlit, migration, dependency, Workflow Runtime implementation, production activation, Document State mutation, external service, ERP/export, upload staging, OCR/LLM, competitor-price, or dashboard behavior is changed.

## Phase 6 Implementation Record

Phase 6 adds the FlowSync Business Workflows workspace at `/workflows`, with definition browsing and bounded pagination, guarded creation, definition details, version and audit history, catalog visibility, structured draft rules/conditions/actions, full-replacement optimistic saves, validation, bounded key/value preview, and permission-aware lifecycle controls. The prior runtime activity page remains intact at `/workflow-runs`.

The UI consumes only Phase 5 API routes through a centralized typed service. Known permission labels are optional usability hints and never grant authority. Unavailable operations remain visible but cannot be selected. Immutable versions expose no editor link. Preview-unavailable, revision conflict, access, empty, and API-unavailable states use fixed copy. Publication and deactivation messaging explicitly preserve governance-only and no-fallback semantics. No backend module, direct repository, runtime execution, FlowSync competitor-price surface, Streamlit, dashboard, migration, dependency, OCR/LLM, ERP/export, staging, or external service was added.

## 1. Objective

Deliver a governed business-facing Workflow and Rules Studio above the existing Workflow Runtime. Authorized users may define, validate, test, version, approve, publish, deactivate, archive, inspect, and later roll back workflows through controlled contracts. The Studio never replaces the Workflow Runtime, weakens its DSL/parser/validator/DAG/operation registry, or introduces arbitrary code execution.

The existing Workflow Runtime remains the sole execution authority. The Studio owns definition governance and translates only approved, validated, versioned definitions into runtime-compatible plans through narrow ports.

## 2. Product Boundary

| Component | Ownership |
|---|---|
| Workflow Runtime | Parses, validates runtime DSL, resolves dependencies, builds DAGs, selects registered operations, and executes approved plans. |
| Workflow Definition Registry | Stores tenant-owned workflow identities and immutable version records. |
| Workflow Versioning | Creates editable working versions, immutable published versions, lineage, and change summaries. |
| Workflow Validation | Applies schema, semantic, runtime-compatibility, security, and publication gates. |
| Workflow Test/Preview Runtime | Runs bounded deterministic previews against safe supplied samples or approved fixtures without production mutation. |
| Workflow Publication | Enforces approval and immutable version policy, then records which validated version is active. |
| Business Rules Studio UI | Structured API client for editing, validation, test preview, version/history, publication, and audit views. It is never an execution or authorization authority. |

## 3. Proposed Architecture

```text
FlowSync Rules Studio
  -> Authenticated Workflow Management API
  -> Workflow Definition Service
  -> Workflow DSL validation
  -> Operation / function allowlist
  -> Versioned workflow repository
  -> Dry-run / test execution boundary
  -> Existing Workflow Runtime
  -> Safe execution preview, audit, and publication state
```

The Definition Service is the governance authority. It must validate before compiling or previewing. Runtime adapters accept only an immutable validated version and approved operation descriptors. Publication records an approved runtime-compatible version; it does not bypass runtime validation or directly mutate runtime registries.

## 4. Package Decision

Create a separate `src/workflow_studio/` package:

```text
src/workflow_studio/
  __init__.py
  contracts.py
  definitions.py
  conditions.py
  actions.py
  statuses.py
  validation.py
  registry.py
  versioning.py
  publication.py
  preview.py
  repositories.py
  errors.py
  ports.py
```

This is cleaner than placing management under `workflow_runtime` because drafts, approvals, publication, UI-safe validation, legacy import reports, and audit lineage are governance concerns rather than execution concerns. It also avoids a broad runtime refactor.

The core package should be standard-library and package-local first. Outer adapters may consume narrow existing Workflow Runtime contracts, operation descriptors, security context, repositories, audit writers, and API transport. The Studio must not import API/UI modules, Streamlit, persistence implementations, ERP/export adapters, external services, or arbitrary plugin loaders.

## 5. Workflow Definition Model

### WorkflowDefinition

- `workflow_id`: stable tenant-scoped identity.
- `tenant_id`: trusted server-owned scope; excluded from ordinary public projections.
- `name` and bounded `description`.
- `business_domain` and optional `document_type` hint.
- `status` and immutable `version` identity.
- Ordered `rules` / stages.
- `created_by`, `updated_by`, and UTC timestamps from trusted context.
- Optional `change_summary`.
- Publication metadata: reviewer, approval, published version, activation/deactivation timestamps.
- Safe import lineage and bounded safe metadata.

### RuleDefinition

- `rule_id`, name, stage, bounded description.
- Explicit dependency rule IDs and stable order.
- `enabled` and explicit `skip` policy.
- Optional validated `ConditionDefinition`.
- One or more allowlisted `ActionDefinition` values.
- Input/output contract hints used for validation, never trusted runtime types.
- Bounded scalar-only safe metadata.

### ConditionDefinition

- Safe field/path using a restricted path grammar.
- Operator from a fixed catalog.
- Bounded JSON-safe expected scalar or bounded scalar collection.
- Boolean composition with `all`, `any`, and `not` under fixed depth/item limits.
- Explicit existence and null handling.

Candidate deterministic operators: `equals`, `not_equals`, `greater_than`, `greater_or_equal`, `less_than`, `less_or_equal`, `in`, `not_in`, `contains`, `starts_with`, `ends_with`, `matches_regex`, `exists`, `not_exists`, `is_null`, and `is_not_null`.

### ActionDefinition

- Studio action type and mapped runtime operation descriptor.
- Versioned function/operator code from the catalog.
- Bounded JSON-safe arguments.
- Restricted source and target paths.
- Fixed error policy: fail rule, skip rule, or record validation issue where supported.
- Fixed output policy: replace target, append bounded result, or emit named preview output.

Definitions contain no executable source, imports, SQL, filesystem paths, URLs, credentials, secrets, or unrestricted payloads.

## 6. Status And Transition Model

Initial statuses:

`draft -> validating -> invalid | valid -> test_ready -> testing -> test_failed | test_ready -> approved -> published -> inactive -> archived`

Refine the graph so asynchronous/transient statuses are optional implementation details rather than required durable records. Required policy:

- Only drafts are editable.
- Validation failure returns the working version to `invalid`; edits produce a new validation attempt.
- A valid definition becomes `test_ready` only when runtime compatibility and security validation pass.
- A successful test returns the definition to `test_ready` with immutable successful test evidence; approval requires that evidence and an authorized reviewer where policy requires separation of duties.
- Publishing assigns an immutable version and tenant-specific activation record.
- Published content cannot be edited or overwritten.
- Editing a published workflow creates a new working version derived from it.
- Deactivation changes activation state, not published content.
- Archival preserves history and blocks future activation.
- Rollback later means publishing a new version derived from an old immutable version, never moving history backward or overwriting production.

## 7. Operation And Function Catalog

Maintain two related catalogs:

1. **Runtime operation catalog:** the existing registered executable operations, currently including `ingest`, `transform`, `filter`, `fuzzy_match`, `compare`, `alert`, and `report`.
2. **Studio action catalog:** business-safe functions and configuration schemas that compile into an existing runtime operation or are marked unavailable/deferred.

Every catalog entry should include code, version, category, display label, description, deterministic flag, argument schema, input/output hints, resource limits, required feature/port, preview support, publication support, and deprecation state.

### Initial Categories To Evaluate

- Assignment: `set`, `remove_path`, `append`.
- Transformation: `trim`, `normalize`, `uppercase`, `lowercase`, `concat`, `split`, `date_format`, `regex_extract`, `regex_mapper`.
- Filtering: `filter`, `conditional_filter`, duplicate removal.
- Mapping: `map`, bounded deterministic `map_parallel`, `parse_template`.
- Validation: `required`, `type`, `regex`, `min`, `max`, `allowed_values`, `unique`.
- Matching: `fuzzy_match`, `fuzzy_search`, `historical_search`, master-data lookup through approved tenant-scoped ports.
- Aggregation: `count`, `sum`, `avg`, `min`, `max`, bounded `reducer`.
- Units: `convert_units`.
- Classification: deterministic classification only. Semantic classification remains deferred or suggestion-only.
- Runtime orchestration visibility: `ingest`, `transform`, `filter`, `fuzzy_match`, `compare`, `alert`, and `report` are displayed from the existing registry with their actual availability; preview must replace side-effecting alert/report delivery with safe no-I/O outcomes.

An operation is not publishable merely because its name is known. It becomes publishable only after a concrete deterministic runtime mapping, argument validator, contract compatibility, resource limits, privacy review, and tests exist. Unsupported catalog entries must be visibly unavailable and fail validation with fixed codes.

### Prohibited Capabilities

No arbitrary Python, `eval`/`exec`, shell, arbitrary imports, raw SQL, unrestricted HTTP, direct database writes, filesystem access, arbitrary JavaScript, credentials/secrets, unbounded recursion, dynamic module loading, direct ERP calls, export activation, or silent tenant-crossing lookup.

## 8. Validation Model

Validation returns immutable ordered issues with fixed code, severity, safe field/rule reference, and bounded non-reflective summary.

### Schema Validation

- Required fields, stable IDs, status/version shape, maximum rules/actions/dependencies.
- Bounded names, descriptions, arguments, metadata, and sample data.
- Valid condition/action shapes and JSON-safe values.

### Semantic Validation

- Unique rule identities and stable ordering.
- Dependencies exist, are enabled-compatible, and produce no cycles.
- Stage ordering respects dependency topology.
- Input/output references and paths are valid and cannot target protected fields.
- Operations/functions are allowlisted and arguments match catalog schemas.
- No unknown, unsafe, deprecated-blocked, or unavailable operation is accepted.

### Runtime Compatibility Validation

- Runtime operation exists and version is supported.
- Studio action has a deterministic compiler/adapter.
- Input/output contract hints align with the runtime operation contract.
- Required feature ports and approved master-data sources are available.
- Resource limits are compatible with preview and publication policies.

### Security Validation

- Tenant scope comes from trusted context.
- Master-data lookup sources are explicitly tenant-approved.
- Protected fields cannot be read or written by an unauthorized action.
- Service-account constraints and publication permissions are enforced.
- Arguments contain no secret-, credential-, token-, claim-, path-, query-, or endpoint-like data.

### Publication Validation

- Candidate is an immutable validated version.
- Required deterministic dry runs/tests passed against approved fixtures.
- Approval and separation-of-duties policy passed.
- Runtime/catalog versions remain available and non-revoked.
- Publication identity and activation metadata are assigned atomically.

Client-side validation may improve usability but never satisfies an API publication gate.

## 9. Dependency And Ordering Policy

The Studio stores explicit rule dependencies and order hints. Validation constructs a graph, rejects missing dependencies and cycles, and derives deterministic topological order using stable rule IDs/order as tie-breakers. Reordering cannot silently alter dependencies. Disabled/skipped rules must define whether dependants fail validation, skip, or consume a declared fallback; implicit behavior is forbidden.

The validated graph is compiled into the existing Workflow Runtime DSL/DAG shape. The Studio does not add a second execution scheduler.

## 10. Safe Dry-Run And Test Boundary

Define a `WorkflowPreviewPort` that accepts only an immutable validated version plus one of:

- An approved fixture registry ID.
- A bounded inline JSON-safe sample after privacy/path/key checks.
- A future approved tenant-owned test dataset reference.

Preview must:

- Execute through an isolated runtime adapter in explicit dry-run mode.
- Perform no Document State or lifecycle mutation.
- Trigger no export, ERP, real alert/email, production master-data write, external service, or upload staging.
- Use read-only approved master-data fixtures/ports where required.
- Enforce maximum sample bytes, collection items, rules, actions, execution steps, recursion depth, elapsed time, and output size.
- Support deterministic replay using version, fixture, catalog, and preview-policy identities.
- Return bounded rule-level outcome, stage timing bucket, fixed error codes, redacted transformed preview, validation/matching explanations, and truncation indicators.
- Exclude credentials, secrets, protected fields, raw exceptions, stack traces, backend paths, and unrestricted trace payloads.

Preview success does not itself publish or activate a workflow. No automatic background test runs are triggered by editing.

## 11. Legacy Template Compatibility

Historical Sanifu/Docsift definitions are migration references and fixtures, never executable inputs.

Initial compatibility posture:

- Structural candidates: rule/stage/name/description/dependencies/order/enabled/skip/condition/actions map only after schema and ordering validation.
- Direct translation candidates where current semantics are proven: `set`, `remove_path`, `concat`, `filter`, bounded `map`, `regex_mapper`, `regex_extract`, `fuzzy_match`, `convert_units`, `append`, bounded `reducer`, `split`, `date_format`, `parse_template`, duplicate removal, validation, and routing conditions.
- Adapter/manual-review candidates: generic `function` only when it names an exact allowlisted catalog function; bounded `map_parallel`; `fuzzy_extract_n`; `fuzzy_search`; `historical_search`; `get_master_data`; customer/product matching; and any action dependent on tenant-owned reference data.
- Deferred/unsupported execution: `semantic_search` and `semantic_classification` until a separately approved deterministic or suggestion-only policy exists.

This posture is an evaluation list, not a declaration that these operations are implemented or publishable.

Plan a later controlled importer:

```text
Raw legacy reference
  -> Strict legacy parser
  -> Operation-by-operation translation proposal
  -> Current Studio schema validation
  -> Semantic/runtime/security validation
  -> Migration report
  -> Human-reviewed draft
```

The migration report classifies each workflow/rule/action as `supported`, `partially_supported`, `unsupported`, or `requires_manual_review`, with fixed reason codes and source lineage. Supported legacy names map only to a current catalog entry with equivalent proven semantics. Unsupported or ambiguous behavior is rejected; no silent renaming, defaulting, reordering, path reinterpretation, or semantic conversion is permitted.

Legacy source lineage includes bounded source-system/template identifiers and import timestamp, not raw secrets or whole raw documents. Imported definitions begin as drafts and require the same validation, test, approval, and publication gates as native definitions.

## 12. Versioning And Publication

- Separate stable `workflow_id` from immutable `workflow_version_id`.
- Prefer monotonically increasing integer versions per tenant/workflow; reserve semantic display labels for UI if needed.
- Save edits with optimistic expected-version checks.
- A draft may be replaced only under draft concurrency rules; published records are append-only/immutable.
- Store parent/derived-from version and bounded change summary.
- Record author, reviewer, approval decision, activation/deactivation time, and correlation/request ID.
- Only one active published version per tenant/workflow/environment unless an explicit rollout policy is later approved.
- Rollback publishes a new version copied from an older version and records lineage.
- Environment promotion (`draft`, `test`, `pilot`, `production`) remains a later explicit policy; production cannot be inferred from publication alone in early phases.

## 13. Repository Strategy

Define persistence-neutral protocols first:

- Definition/version reader and writer.
- Draft optimistic-update repository.
- Immutable published-version repository.
- Publication/activation repository.
- Preview result summary repository where retention is approved.
- Audit intent writer port.
- Approved fixture registry port.

Use deterministic lock-protected in-memory repositories for early contracts/tests. Evaluate SQLite only in Phase 3 after schema, migration ownership, transactions, tenant uniqueness, immutable version constraints, audit retention, and backend equivalence tests are approved. Planning does not authorize a migration.

Do not reuse Document State for workflow definitions. Document State owns document processing facts and lifecycle, while workflow definitions have distinct aggregate identity, versioning, approval, retention, and publication semantics. Query Facade integration may later expose safe execution relationships without moving definition ownership.

## 14. API Plan

Potential routes, planning only:

- `GET /api/v1/workflow-definitions`
- `POST /api/v1/workflow-definitions`
- `GET /api/v1/workflow-definitions/{workflow_id}`
- `PATCH /api/v1/workflow-definitions/{workflow_id}`
- `POST /api/v1/workflow-definitions/{workflow_id}/validate`
- `POST /api/v1/workflow-definitions/{workflow_id}/test`
- `GET /api/v1/workflow-definitions/{workflow_id}/versions`
- `POST /api/v1/workflow-definitions/{workflow_id}/versions`
- `POST /api/v1/workflow-definitions/{workflow_id}/publish`
- `POST /api/v1/workflow-definitions/{workflow_id}/deactivate`
- `GET /api/v1/workflow-operations`
- `GET /api/v1/workflow-definitions/{workflow_id}/audit`

Consider a separate archive endpoint and explicit version resource paths before implementation. Avoid action endpoints whose resource/version concurrency semantics are unclear.

The API remains authoritative for identity, tenant, permissions, expected versions, operation catalog, validation, fixture eligibility, test execution, approval, publication, deactivation, concealment, and safe errors. Requests never contain server-owned tenant/actor fields, executable source, credentials, or unrestricted metadata. Mutation endpoints require request/correlation identity, idempotency where applicable, optimistic concurrency, bounded payloads, and audit intent generation.

No endpoint is created during planning.

## 15. Security And Permissions

Evaluate explicit permissions:

- `workflow:read`
- `workflow:create`
- `workflow:edit`
- `workflow:test`
- `workflow:approve`
- `workflow:publish`
- `workflow:deactivate`
- `workflow:admin`

Reuse existing `workflow:read` where semantics already match. Existing `workflow:run` is not sufficient for editing, approval, publication, or administration. Adding permissions requires a separate security-catalog review and compatibility plan.

Rules:

- Tenant isolation is mandatory before repository lookup.
- Cross-tenant platform-admin access must be explicit, separately authorized, and audited.
- Published workflow mutation is forbidden.
- Publication and deactivation require stronger permissions than editing.
- Approval should support reviewer/author separation where configured.
- Tests use safe fixtures and preview-only ports.
- All changes and decisions emit safe audit intents.
- FlowSync never decides access or hides unsafe fields as a substitute for API projection.
- No secrets, credentials, tokens, claims, raw SQL, internal paths, or unrestricted metadata enter definitions or audit.

## 16. FlowSync Rules Studio Plan

Preserve the approved dark-green sidebar, clean white workspace, calm enterprise dashboard, restrained green accents, typography, components, safe request states, and API-authority language.

Suggested navigation:

```text
Workflows
  - Workflow Definitions
  - Drafts
  - Published
  - Test Runs
  - Operation Catalog
  - Audit History
```

Potential pages: workflow list/overview, structured stage/rule editor, condition builder, action builder, dependency view, validation results, dry-run panel, bounded output comparison, version history, publication panel, and audit history.

Start with structured forms and ordered rule cards. Do not require a drag-and-drop canvas in v1. Dependency visualization may be read-only until keyboard-accessible editing semantics are proven.

The editor supports add/reorder/enable/disable rule, select catalog action, configure allowlisted arguments and conditions, select dependencies, validate, test with safe fixture, inspect rule-level errors, save draft, submit for approval, and publish when API-authorized. It safely displays unsupported legacy operation, dependency cycle, invalid path, unknown function, protected field, unavailable master-data source, test failure, and publication-blocked states.

The UI never generates arbitrary code, executes actions locally, bypasses API validation, decides tenant/permission, publishes locally, mutates runtime registries, calls ERP/export/external services, or exposes secrets/internal paths.

## 17. Audit And Lineage

Every future change should emit a bounded audit intent containing workflow ID/version, trusted tenant/actor attribution, fixed event type, changed-field summary, validation/test outcome, approval/publication state, UTC timestamp, correlation/request ID, and import lineage where applicable.

Do not audit full definitions by default, raw sample documents, preview output bodies, secrets, credentials, protected values, raw exceptions, or unrestricted diffs. Durable audit ownership should reuse the platform audit boundary through an adapter rather than making the Studio its own ungoverned log store.

## 18. LLM Policy

LLM execution is deferred. Future assistance may propose draft rules, explain validation failures, summarize behavior, or propose legacy translations. It cannot publish, approve, execute arbitrary functions, decide permissions, mutate production, or silently reinterpret rules.

Required future chain:

```text
LLM suggestion
  -> Schema validation
  -> Semantic validation
  -> Deterministic dry run
  -> Human review
  -> Authorized publication
```

Suggestions remain untrusted draft input and must be clearly attributed and auditable.

## 19. Testing Strategy

Plan coverage for definition immutability/serialization, status transitions, published-version immutability, optimistic draft concurrency, operation allowlist and unsafe rejection, catalog/runtime compatibility, dependency cycle and stable topological ordering, condition/path validation, action arguments, legacy migration reports, deterministic bounded preview, timeout/step/output limits, protected-field redaction, tenant isolation, permission denial, approval separation, publication/deactivation/rollback policy, audit intents, safe API envelopes, FlowSync access/malformed/error states, and recursive import boundaries.

Explicit negative tests must prove no arbitrary code, imports, shell, filesystem, raw SQL, HTTP, secrets, ERP/export, Document State/lifecycle mutation, production master-data write, real alert/email, OCR/LLM, or tenant-crossing behavior occurs during validation or preview.

## 20. Non-Goals

- No arbitrary code execution or user-defined executable functions.
- No real ERP call or export activation.
- No upload staging implementation.
- No OCR/LLM execution.
- No automatic production publication.
- No drag-and-drop visual programming requirement in v1.
- No external marketplace or plugin system.
- No unbounded workflow execution.
- No silent legacy conversion.
- No replacement or broad refactor of Workflow Runtime.
- No source, endpoint, UI, dependency, or migration change during planning.

## 21. Deferred Work

Production durable repository choice, SQLite migration approval, environment promotion, rollout/canary policy, scheduler binding, production execution activation, queue/workers, distributed locks, durable preview datasets, live master-data adapters, retry/recovery, collaborative editing, comments, visual canvas, reusable subworkflows, parameter libraries, marketplace/plugins, semantic search/classification, LLM suggestions, ERP/export integration, and production operations remain deferred unless explicitly phased later.

## 22. Risks And Open Questions

- The boundary between Studio actions and existing coarse runtime operations needs an explicit compiler/mapping contract.
- Some historical operation names have no proven equivalent and may require manual redesign.
- Field-path typing across stages may be incomplete without richer contract schemas.
- Preview fidelity may diverge from production if adapters or data sources differ.
- Master-data lookup needs tenant-safe source ownership and snapshot/replay policy.
- Publication atomicity and one-active-version constraints need a durable transaction design.
- Long previews need timeout/cancellation and resource accounting.
- Approval separation may conflict with small-team workflows and needs configurable policy.
- Definition diffing must remain useful without leaking protected values.
- Version numbers, environment promotion, archive retention, and rollback semantics need owner decisions.
- Existing `workflow:run` must not be accidentally broadened into management authority.

## 23. Definition Of Done

v0.20 is complete only when approved phases deliver and verify:

- Clear Studio/runtime ownership and one-way adapter boundaries.
- Immutable safe definition, condition, action, version, validation, preview, publication, and audit contracts.
- Explicit catalog with publishable/unavailable status and no arbitrary execution.
- Deterministic dependency, schema, semantic, runtime, security, and publication validation.
- Immutable published versions, editable drafts, approval, deactivation, and lineage-preserving rollback policy.
- Safe bounded deterministic preview with no production mutation or external side effect.
- Legacy import report that never executes or silently translates source templates.
- Tenant-scoped repositories and API authorization with safe envelopes.
- Structured accessible FlowSync Studio using API authority.
- Boundary/privacy tests and required platform regressions.
- Closure summary, handoff, release notes, deferred-work record, and owner-approved tag.

Production publication/execution, external adapters, LLM, and real ERP/export are not implied by milestone completion unless separately approved and implemented.
