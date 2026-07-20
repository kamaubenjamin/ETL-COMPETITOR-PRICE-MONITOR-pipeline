# Business Workflow / Rules Studio v1 Implementation Plan

**Milestone:** v0.20
**Status:** Phases 1-4 implemented and focused verification passed; Phases 5-7 not started
**Phases:** Seven reviewed phases

## 1. Delivery Rules

- Implement one reviewed phase at a time and stop after its verification evidence.
- Preserve the existing Workflow Runtime as execution authority.
- Keep Studio core policy independent from API, FlowSync, Streamlit, persistence implementations, ERP/export, external services, and arbitrary extension loading.
- Never introduce executable user source, `eval`/`exec`, shell, raw SQL, filesystem, unrestricted HTTP, direct database mutation, credentials, or secrets.
- Do not activate production workflow execution, ERP, export, upload staging, OCR/LLM, or automatic publication by convenience.
- New permissions, persistence schemas, dependencies, and production adapters require explicit phase approval.
- Every phase must record what remains unavailable and must not let API/UI imply activation before it exists.

## 2. Phase 1: Contracts, Statuses, Definitions, And Operation Catalog

**Status:** Complete for the approved Phase 1 scope.

### Deliverables

- Create the standard-library-first `workflow_studio` package foundation.
- Immutable JSON-safe workflow, rule, condition, action, version, author/reviewer, and safe metadata contracts.
- Fixed workflow/version/publication, rule, and operation-availability status catalogs. Transition policy remains Phase 3 work.
- Restricted field/path, condition operator, error policy, and output policy catalogs.
- Operation descriptor/catalog contracts separating Studio actions from existing runtime operations.
- Initial catalog entries marked `available`, `unavailable`, or `deprecated`; only proven exact runtime mappings are publishable.
- Fixed privacy-safe errors. Validation issue contracts remain Phase 2 work.

### Tests

Immutability, serialization, bounded fields/collections/depth, ID/timestamp/status validation, transition table, published immutability, scalar-only metadata, unsafe key/value rejection, operation descriptor consistency, prohibited executable fields, and recursive boundary imports.

### Stop Condition

No service, repository implementation, runtime compiler, preview execution, API, UI, permission change, persistence, or migration.

### Implementation Evidence

- Added nine isolated `workflow_studio` modules using only the standard library and package-local imports.
- Added 48 focused tests across the eight approved test files.
- The catalog contains all 30 reviewed operation names in stable order. `filter`, `fuzzy_match`, and `compare` are the only available, preview-eligible, publication-eligible entries because their exact runtime labels are registered; all compiler-category candidates remain unavailable.
- Metadata is scalar-only, bounded, immutable, and rejects sensitive keys, nested payloads, code-like configuration, external URLs, and physical paths.
- No validation engine, legacy importer, repository, publication behavior, runtime compiler/import, preview, API, UI, dependency, migration, or execution activation was added.

## 3. Phase 2: Validation Engine, Dependency Policy, And Legacy Compatibility Report

**Status:** Complete for the approved Phase 2 scope.

### Deliverables

- Ordered schema, semantic, path, condition, action-argument, dependency, and runtime-compatibility validators.
- Deterministic graph construction, missing-dependency rejection, cycle detection, and stable topological ordering.
- Protected-field and unsafe-path policy.
- Existing structural catalog port reused for operation/version/contract availability.
- Security-validation intent accepting trusted tenant/source capability facts from outer composition.
- Strict modeled legacy descriptor/report interface; no raw parser or executable translation is included.
- Migration report with supported, partially supported, unsupported, and manual-review outcomes plus source lineage.

### Tests

Every issue code/order, duplicate IDs, dependency cycles, disabled/skipped dependency behavior, invalid paths, boolean-depth limits, unknown/unavailable operations, argument errors, protected fields, runtime version mismatch, missing feature port, tenant-source mismatch, deterministic results, and legacy no-silent-conversion fixtures.

### Stop Condition

No legacy definition execution, repository writes, runtime invocation, preview, API, UI, LLM, or production operation registration.

### Implementation Evidence

- Added seven standard-library/package-local validation modules and 54 Phase 2 tests; the combined Workflow Studio suite passes 102 tests.
- Required focused regressions pass unchanged, and the full practical regression passes 1,879 tests with 9 skips.
- Dependency validation detects missing, self, duplicate, and cyclic references, reports only actual strongly connected cycle members, and produces a stable lexical topological order when valid.
- Condition/path checks enforce modeled operators, value shapes, depth/width, controlled `[]` collection segments, protected namespaces, and rejection of physical, URL, SQL, shell, traversal, wildcard, and expression paths.
- Operation compatibility distinguishes structural validity from preview/publication readiness, validates versions, declared arguments, path requirements, determinism, mappings, and caller-supplied required features.
- Legacy reports classify exact proven mappings as supported, semantic candidates as partial, generic wrappers as manual review, and unavailable semantic/external capabilities as unsupported. They do not return executable workflows.
- No repository, version lifecycle, publication mutation, preview, runtime import/invocation, API, UI, dependency, migration, or production activation was added.

## 4. Phase 3: Versioned Repository, Draft Lifecycle, And Publication Policy

**Status:** Complete for the approved Phase 3 scope.

### Deliverables

- Persistence-neutral reader/writer protocols for workflow identity, immutable versions, drafts, publication/activation, and audit intents.
- Deterministic lock-protected in-memory implementation for tests/local composition.
- Unique tenant/workflow/version identities and optimistic draft updates.
- Immutable published versions and append-only derivation lineage.
- Pure approval, publish, deactivate, archive, and rollback-as-new-version policies.
- One-active-version policy per tenant/workflow/environment where enabled.
- Safe version queries, bounded pagination, stable ordering, and concealed tenant reads.
- SQLite schema/transactions remain deferred pending explicit approval and migration review.

### Tests

Tenant isolation, optimistic conflicts, unique versions, immutable publication, edit-derived draft behavior, author/reviewer separation, approval gates, atomic activation claims, deactivation/archive, rollback lineage, deterministic pages, concurrent claims, and in-memory/approved-backend equivalence if a durable adapter is included.

### Stop Condition

No runtime execution, API, UI, production persistence selection, automatic promotion, or direct Document State reuse.

### Implementation Evidence

- Added eight standard-library/package-local Phase 3 modules and 45 tests; the combined Workflow Studio suite passes 147 tests.
- Required focused regressions pass unchanged, and the full practical regression passes 1,924 tests with 9 skips.
- Added tenant-scoped read/write/publication protocols and a lock-protected, non-durable in-memory store with stable bounded pagination and optimistic revisions.
- Tenant-scoped workflow/version/publication identities, unique workflow version labels, one current pre-publication draft, one active publication, and cross-workflow reference checks are enforced.
- Content updates are draft-only. Store- and service-level transition tables prevent direct reopening or content rewriting of approved/published/superseded/inactive/archived history.
- Publication policy consumes supplied validation, test, approval, permission, feature, legacy-review, tenant, and revision facts without querying security or repositories itself.
- Controlled publication atomically creates an active record, supersedes the previous active record/version when explicitly allowed, updates definition references, and emits safe audit intents. Deactivation never auto-activates another version; archival retains history.
- No durable persistence, migration, runtime execution/activation, preview, API, UI, external audit writer, dependency, OCR/LLM, ERP/export, or upload staging was added.

## 5. Phase 4: Safe Dry-Run Boundary And Audit Intents

**Status:** Complete for the approved Phase 4 scope.

### Deliverables

- Immutable preview command, fixture reference, bounded inline sample, policy limits, trace summary, rule/stage result, redacted output, and preview result contracts.
- `WorkflowPreviewPort` plus a controlled adapter into the existing Workflow Runtime dry-run composition.
- Compiler from a validated immutable Studio version to existing runtime DSL/operation descriptors; no second scheduler.
- Explicit no-side-effect ports/placeholders for alerts, master data, export, ERP, Document State, and lifecycle.
- Maximum sample/output size, rules/actions/steps, collection items, duration, recursion, and trace events.
- Deterministic replay identity and timeout/cancellation outcomes.
- Safe audit intents for definition, validation, preview, approval, publication, deactivation, archival, and import activity.

### Tests

Deterministic replay, rule-by-rule outcomes, stable timing buckets where deterministic, step/item/output/time limits, cancellation, redaction, safe errors, fixture eligibility, unavailable port behavior, and proofs of no Document State/lifecycle/export/ERP/alert/email/master-data mutation, network, filesystem, secrets, or raw trace leakage.

### Stop Condition

Preview only: no production workflow run, scheduler binding, external adapter, durable raw preview output, API, or UI.

### Implementation Evidence

- Added eight isolated preview modules and 33 tests; the combined Workflow Studio suite passes 180 tests.
- Required focused regressions pass unchanged, and the full practical regression passes 1,956 tests with 9 skips.
- Fixed limits cover rules/actions/dependency depth/steps, input/output collections, trace/issues/output fields, strings, nested depth, and duration policy.
- Modeled inline samples and approved in-memory fixture references are normalized immutably and reject sensitive keys, executable objects, raw bytes, excessive nesting/collections/fields, and oversized strings.
- The injected runtime Protocol receives only an immutable version, normalized fixture, limits, and policy. Deterministic success/failure/unavailable/limit adapters perform no I/O.
- The service blocks invalid/ineligible workflows before invocation, catches adapter exceptions safely, re-bounds rule/stage/trace/issue output, and applies stable omission/redaction.
- No production execution, repository/publication/Document State mutation, runtime implementation import, external adapter, API, UI, dependency, migration, alert/email, ERP/export, master-data write, staging, OCR/LLM, filesystem, database, or network behavior was added.

## 6. Phase 5: Guarded Workflow Management API

**Status:** Complete for the approved Phase 5 scope.

### Implementation Record

- Added an app-scoped provider composing only the in-memory Studio store, operation catalog, validator, draft lifecycle, publication service, safe audit summaries, and placeholder preview boundary.
- Added all required read and mutation routes with standard envelopes, bounded pagination, tenant concealment, API-owned attribution, strict request allowlists, and optimistic full draft replacement.
- Added distinct management permissions. Operations managers receive create/edit/test/approve/deactivate; tenant admins additionally receive publish/admin; platform admins retain the full catalog; service accounts receive none.
- Default preview remains honestly unavailable; successful preview can only be supplied through an injected no-I/O Phase 4 adapter. Governed publication does not bind or activate Workflow Runtime.
- Added focused route, mutation, security, preview, publication, privacy, and boundary tests. No FlowSync, Streamlit, migration, dependency, runtime implementation, external adapter, OCR/LLM, ERP/export, upload staging, competitor-price, or dashboard change was made.

### Deliverables

- App-scoped provider/service boundary over approved Studio services.
- Tenant-scoped read contracts for definitions, details, versions, operations, preview summaries, and audit history.
- Guarded create/edit/new-version/validate/test/approve/publish/deactivate/archive contracts as approved.
- Exact expected-version and idempotency semantics for mutations.
- API-authoritative permission, tenant, catalog, fixture, validation, approval, publication, and concealment behavior.
- Fixed safe envelopes and non-reflective errors.
- No client-supplied tenant/actor, executable source, secrets, raw samples beyond approved bounded preview schema, or unrestricted metadata.

### Permissions To Evaluate

`workflow:read`, `workflow:create`, `workflow:edit`, `workflow:test`, `workflow:approve`, `workflow:publish`, `workflow:deactivate`, and `workflow:admin`. Reuse `workflow:run` only for actual runtime execution semantics, not Studio management.

### Tests

Authentication, permission matrix, tenant narrowing/concealment, platform-admin audit, payload limits, unsafe fields, draft concurrency, published mutation denial, validate/test gates, approval separation, publication/deactivation idempotency, safe errors, operation catalog reads, malformed requests, method restrictions, and no direct runtime/ERP/export/Document State mutation.

### Stop Condition

No FlowSync changes, production scheduler activation, external service, automatic publication, or broad existing API behavior change.

## 7. Phase 6: FlowSync Rules Studio UI Foundation

### Deliverables

- Preserve v0.17 visual identity and current shell/access/error patterns.
- Workflow definitions list with draft/published/status filters supplied by API.
- Structured workflow overview and stage/rule editor.
- Condition and allowlisted action builders driven by the API operation catalog.
- Dependency selection/reorder experience with accessible validation feedback.
- Validation results, safe fixture test panel, bounded rule-level preview, version history, publication panel, and audit history.
- Safe unsupported legacy operation, cycle, invalid path, unknown function, protected field, unavailable source, test-failed, and publication-blocked states.
- API-authoritative access; no local publication, runtime registry mutation, arbitrary code editor, secret input, ERP/export call, or client execution.

### UX Decision

Use structured forms, ordered cards, and a read-only dependency visualization first. A drag-and-drop programming canvas is not required and should not be introduced until keyboard accessibility, dependency semantics, and maintainability are justified.

### Tests

Source validation, strict typecheck/build, route registration, parser allowlists, loading/empty/access/unavailable/malformed states, keyboard and screen-reader semantics, mobile layout, operation catalog behavior, explicit actions only, no browser credential storage, no arbitrary code or unsafe fields, no fixture fallback, and no ERP/export/runtime-direct imports or requests.

### Stop Condition

No production execution activation, LLM assistance, collaborative editing, external plugin system, or visual canvas requirement.

## 8. Phase 7: Verification, Closure, Handoff, And Tag

### Deliverables

- Architecture summary, handoff, release notes, roadmap/debt/ADR/plan/changelog closure.
- Focused Studio contract/validation/versioning/preview/repository/API/security/FlowSync evidence.
- Existing Workflow Runtime, locking, Query Facade, Review Runtime, Document State, platform, export, upload, API, Streamlit, and full regression evidence proportionate to changes.
- Boundary/privacy/arbitrary-execution scans and production-unavailable statement.
- Deferred work, activation prerequisites, risks, and v0.21 recommendation.
- Owner-reviewed tag recommendation; suggested tag `v0.20-business-workflow-rules-studio`.

## 9. Verification Matrix

Each phase should run its focused suites and applicable compatibility suites. Candidate closure matrix:

```text
python -m pytest tests/workflow_studio -q
python -m pytest tests/workflow_runtime -q
python -m pytest tests/workflow_runtime/query_facade tests/review_runtime -q
python -m pytest tests/api/document_intelligence -q
python -m pytest tests/security -q
python -m pytest tests/platform_runtime -q
python -m pytest tests/document_state -q
python -m pytest tests/export_runtime tests/upload_runtime -q
python -m pytest tests/ui/streamlit -q
python scripts/verify_boundaries.py

cd apps/flowsync-document-intelligence
npm run validate
npm run typecheck
npm run build

git diff --check
git status --short --branch
```

Run `python -m pytest -q` at closure when practical. Exact paths may be refined only after Phase 1 creates the package/tests.

## 10. Dependency, Migration, And Activation Gates

No parser library, expression engine, graph library, database migration, editor framework, LLM client, plugin runtime, queue, or external adapter is authorized by this planning phase. Any proposed dependency or migration requires ownership, threat review, compatibility, deterministic behavior, failure modes, operations, rollback, and explicit approval.

Production workflow publication must remain distinct from production execution activation. Do not bind published definitions to schedules or live events until durable repository, authentication, operation adapters, rollback, monitoring, and operational controls are approved.

## 11. Recommended Commit Sequence

1. `feat(workflow-studio): add governed definition contracts and catalog`
2. `feat(workflow-studio): add validation and legacy compatibility reporting`
3. `feat(workflow-studio): add version and publication policies`
4. `feat(workflow-studio): add bounded deterministic preview boundary`
5. `feat(api): add guarded workflow management contracts`
6. `feat(flowsync): add structured rules studio views`
7. `docs: close v0.20 business workflow rules studio`
